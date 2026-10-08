import re
from collections import defaultdict

from docgen.config import Settings
from docgen.contracts import Batch, Block
from docgen.ingestion import estimate_tokens
from docgen.storage import digest, encode


def plan_batches(snapshot: dict, settings: Settings) -> list[Batch]:
    blocks = [Block.model_validate(item) for item in snapshot["blocks"]]
    by_id = {block.id: block for block in blocks}
    neighbors = {}
    headings, tables, definitions = {}, defaultdict(list), defaultdict(list)
    for index, block in enumerate(blocks):
        neighbors[block.id] = [
            other.id
            for other in blocks[max(0, index - 1) : index + 2]
            if other.path == block.path and other.id != block.id
        ]
        if block.kind == "heading":
            headings[block.path, tuple(block.headings)] = block.id
        if block.table_id and block.table_row in {0, 1}:
            tables[block.table_id].append(block.id)
        if any(word in " ".join(block.headings).lower() for word in ("glossary", "definition")):
            for term in re.findall(r"\b[a-z][a-z_-]{3,}\b", block.content.lower()):
                definitions[term].append(block.id)
    groups, current, size = [], [], 0
    for block in blocks:
        count = estimate_tokens(block.content)
        if current and size + count > settings.batch_tokens:
            groups.append(current)
            current, size = [], 0
        current.append(block.id)
        size += count
    if current:
        groups.append(current)
    batches = []
    for group in groups:
        candidates = []
        for block_id in group:
            block = by_id[block_id]
            candidates.extend(tables[block.table_id])
            for depth in range(1, len(block.headings) + 1):
                heading = headings.get((block.path, tuple(block.headings[:depth])))
                if heading:
                    candidates.append(heading)
            candidates.extend(
                link["block_id"]
                for link in snapshot["links"].get(block_id, [])
                if link.get("block_id")
            )
            candidates.extend(neighbors[block_id])
            for term in set(re.findall(r"\b[a-z][a-z_-]{3,}\b", block.content.lower())):
                candidates.extend(definitions.get(term, []))
        context, omitted, budget = [], [], 0
        for candidate in dict.fromkeys(candidates):
            if candidate in group:
                continue
            count = estimate_tokens(encode(by_id[candidate]))
            if budget + count <= settings.context_tokens:
                context.append(candidate)
                budget += count
            else:
                omitted.append(candidate)
        batches.append(
            Batch(
                id="batch-" + digest([group, context, settings.signature()])[:16],
                owned=group,
                context=context,
                dependencies=[],
                omitted_context=omitted,
                source_tokens=sum(estimate_tokens(by_id[key].content) for key in group),
                context_tokens=budget,
                output_tokens=settings.output_tokens,
            )
        )
    ownership = {key: batch.id for batch in batches for key in batch.owned}
    for batch in batches:
        batch.dependencies = sorted(
            {
                ownership[key]
                for key in batch.context + batch.omitted_context
                if ownership[key] != batch.id
            }
        )
    if len(ownership) != len(blocks):
        raise ValueError("Not every source block has exactly one extraction owner")
    return batches


def split_batch(batch: Batch, blocks: dict[str, Block], context_limit=4000) -> list[Batch]:
    if len(batch.owned) < 2:
        raise ValueError("Single-block output does not fit; source needs smaller ingestion blocks")
    half = len(batch.owned) // 2
    children = []
    for owned in (batch.owned[:half], batch.owned[half:]):
        relevant_tables = {blocks[key].table_id for key in owned if blocks[key].table_id}
        candidates = [
            key
            for key in batch.owned
            if key not in owned
            and (
                blocks[key].kind == "heading"
                or (blocks[key].table_id in relevant_tables and blocks[key].table_row in {0, 1})
            )
        ]
        candidates.extend(batch.context)
        candidates.extend([batch.owned[half - 1], batch.owned[half]])
        context, omitted, used = [], list(batch.omitted_context), 0
        for key in dict.fromkeys(candidates):
            if key in owned:
                continue
            cost = estimate_tokens(encode(blocks[key]))
            if used + cost <= context_limit:
                context.append(key)
                used += cost
            else:
                omitted.append(key)
        children.append(
            batch.model_copy(
                update={
                    "id": "batch-" + digest([batch.id, owned])[:16],
                    "owned": owned,
                    "source_tokens": sum(estimate_tokens(blocks[key].content) for key in owned),
                    "context": context,
                    "context_tokens": used,
                    "omitted_context": list(dict.fromkeys(omitted)),
                    "split_from": batch.id,
                    "attempts": 0,
                    "status": "pending",
                }
            )
        )
    return children
