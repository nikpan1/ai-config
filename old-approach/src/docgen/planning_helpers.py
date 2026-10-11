import re
import unicodedata
from collections import Counter
from pathlib import PurePosixPath

from docgen.ingestion import estimate_tokens
from docgen.model import RequestTooLarge
from docgen.storage import digest, encode


def bounded_groups(rows, limit, payload=lambda row: row):
    group, size = [], 0
    for row in rows:
        cost = estimate_tokens(encode(payload(row)))
        if cost > limit:
            raise RequestTooLarge("One complete planning item exceeds its configured token bound")
        if group and size + cost > limit:
            yield group
            group, size = [], 0
        group.append(row)
        size += cost
    if group:
        yield group


def require_exact(actual, expected, description):
    actual, expected = list(actual), list(expected)
    if Counter(actual) != Counter(expected) or len(set(actual)) != len(actual):
        missing = sorted(set(expected) - set(actual))
        unexpected = sorted(set(actual) - set(expected))
        duplicate = sorted(key for key, count in Counter(actual).items() if count > 1)
        raise ValueError(
            f"{description}: missing={missing}, unexpected={unexpected}, duplicate={duplicate}"
        )


def safe_slug(value):
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")[:64] or "topic"


def validate_paths(pages):
    seen = set()
    reserved = {
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{i}" for i in range(1, 10)),
        *(f"lpt{i}" for i in range(1, 10)),
    }
    for page in pages:
        value = page["path"]
        path = PurePosixPath(value)
        key = unicodedata.normalize("NFC", value).casefold()
        if (
            key in seen
            or path.is_absolute()
            or "\\" in value
            or str(path) != value
            or not value.endswith(".md")
            or any(
                part in {".", ".."}
                or part.endswith((".", " "))
                or part.split(".")[0].casefold() in reserved
                or re.search(r'[<>:"|?*\x00-\x1f]', part)
                for part in path.parts
            )
        ):
            raise ValueError(f"Unsafe or colliding documentation path: {value}")
        seen.add(key)


def validate_dag(nodes, edges):
    identifiers = set(nodes)
    children = {key: [] for key in identifiers}
    degrees = Counter({key: 0 for key in identifiers})
    for source, target in edges:
        if source not in identifiers or target not in identifiers:
            raise ValueError("Graph edge references a missing target")
        children[source].append(target)
        degrees[target] += 1
    queue = [key for key in identifiers if degrees[key] == 0]
    visited = []
    while queue:
        key = queue.pop()
        visited.append(key)
        for target in children[key]:
            degrees[target] -= 1
            if degrees[target] == 0:
                queue.append(target)
    if len(visited) != len(identifiers):
        raise ValueError("Graph contains a cycle")
    return visited


def evidence_context(store, inputs, obligations):
    record_ids = sorted({row["record_id"] for row in obligations})
    records = store.table_rows(inputs.records_ref, record_ids)
    block_ids = sorted({e["block_id"] for row in obligations for e in row["evidence"]})
    blocks = store.table_rows(inputs.blocks_ref, block_ids)
    return {"obligations": obligations, "records": records, "source_blocks": blocks}


def bounded_context_groups(store, inputs, rows, limit):
    group, record_costs, block_costs, size = [], {}, {}, 100
    for row in rows:
        record_id = row["record_id"]
        block_ids = {e["block_id"] for e in row["evidence"]}
        record_cost = record_costs.get(record_id)
        if record_cost is None:
            record = store.table_rows(inputs.records_ref, [record_id])[0]
            record_cost = estimate_tokens(encode(record)) + 1
        costs = {key: block_costs[key] for key in block_ids if key in block_costs}
        costs.update(
            {
                block["id"]: estimate_tokens(encode(block)) + 1
                for block in store.table_rows(inputs.blocks_ref, sorted(block_ids - costs.keys()))
            }
        )
        owned_cost = estimate_tokens(encode(row)) + 1
        single_size = 100 + owned_cost + record_cost + sum(costs.values())
        if single_size > limit:
            raise RequestTooLarge("One complete planning item exceeds its configured token bound")
        added = (
            owned_cost
            + (0 if record_id in record_costs else record_cost)
            + sum(cost for key, cost in costs.items() if key not in block_costs)
        )
        if group and size + added > limit:
            yield group
            group, record_costs, block_costs, size = [], {}, {}, 100
            added = single_size - 100
        group.append(row)
        record_costs[record_id] = record_cost
        block_costs.update(costs)
        size += added
    if group:
        yield group


def stable_id(prefix, *values):
    return prefix + "-" + digest(values)[:20]
