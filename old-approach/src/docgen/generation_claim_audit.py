import re

from markdown_it import MarkdownIt

from docgen.generation_export import source_catalog
from docgen.ingestion import estimate_tokens
from docgen.planning_helpers import require_exact
from docgen.storage import digest, encode

SOURCE_LABEL = re.compile(r"\[(S\d+)\]")
DIAGRAM_NODE = re.compile(r'^\s*(\w+)\["(.+)"\]$')
DIAGRAM_EDGE = re.compile(r'^\s*(\w+) -->\|"(.+)"\| (\w+)$')


def page_claims(path, markdown):
    tokens = MarkdownIt("commonmark").enable("table").parse(markdown)
    claims = []
    heading = ""
    in_table_head = False
    in_table_row = False
    row = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            heading = tokens[index + 1].content
        elif token.type == "thead_open":
            in_table_head = True
        elif token.type == "thead_close":
            in_table_head = False
        elif token.type == "tr_open":
            in_table_row = True
            row = []
        elif token.type == "tr_close":
            if not in_table_head and row:
                add_claim(claims, path, heading, "table_row", " | ".join(row))
            in_table_row = False
        elif token.type == "inline":
            if in_table_row:
                row.append(token.content)
            elif index and tokens[index - 1].type == "paragraph_open":
                add_claim(claims, path, heading, "passage", token.content)
        elif token.type == "fence" and token.info == "mermaid":
            nodes = {}
            for line in token.content.splitlines():
                node = DIAGRAM_NODE.fullmatch(line)
                if node:
                    nodes[node.group(1)] = node.group(2)
            following = tokens[index + 2].content if index + 2 < len(tokens) else ""
            citations = (
                SOURCE_LABEL.findall(following) if following.startswith("Diagram source:") else []
            )
            for line in token.content.splitlines():
                edge = DIAGRAM_EDGE.fullmatch(line)
                if edge:
                    text = (
                        f"{nodes.get(edge.group(1), edge.group(1))} -> "
                        f"{nodes.get(edge.group(3), edge.group(3))}: {edge.group(2)}"
                    )
                    add_claim(claims, path, heading, "diagram_edge", text, citations)
    return claims


def add_claim(claims, path, heading, kind, text, citations=None):
    stripped = text.strip()
    if not stripped or stripped.startswith(
        ("Related:", "Diagram source:", "Source quotation:", "[Sources]", "[Attachments]")
    ):
        return
    if kind == "table_row" and stripped.split(" | ", 1)[0] in {
        "Audience",
        "Knowledge revision",
        "Document revision",
        "Last reviewed",
        "Source set",
    }:
        return
    citations = sorted(set(citations if citations is not None else SOURCE_LABEL.findall(stripped)))
    claims.append(
        {
            "id": digest([path, len(claims), kind, stripped])[:20],
            "path": path,
            "section": heading,
            "kind": kind,
            "text": stripped,
            "citations": citations,
        }
    )


def audit_jobs(pipeline, state):
    pages = pipeline.read(state, "pages_ref")
    content = [page["path"] for page in pipeline.rows(state, "pages") if page["role"] != "sources"]
    claims = [claim for path in content for claim in page_claims(path, pages[path])]
    labels = pipeline.read(state, "source_labels_ref")
    catalog = source_catalog(pipeline, state)
    blocks = {
        block["id"]: block
        for block in pipeline.store.iter_table(pipeline.planning_inputs(state).blocks_ref)
    }
    sources = {
        label: {
            "excerpt": catalog[key]["excerpt"],
            "source_path": blocks[catalog[key]["block_id"]]["path"],
            "source_content": blocks[catalog[key]["block_id"]]["content"],
        }
        for key, label in labels.items()
        if key in catalog
    }
    jobs = []
    limit = min(30000, pipeline.settings.request_tokens - pipeline.settings.output_tokens - 8000)
    for claim in claims:
        if set(claim["citations"]) - sources.keys():
            raise ValueError("Claim audit encountered an unknown source label")
        selected = [sources[label] | {"label": label} for label in claim["citations"]]
        candidate = {"claims": [claim], "sources": selected}
        if estimate_tokens(encode(candidate)) > limit:
            raise ValueError("One reader claim exceeds the factual audit request limit")
        if jobs:
            current = jobs[-1]
            combined_claims = [*current["claims"], claim]
            labels_used = {label for item in combined_claims for label in item["citations"]}
            combined = {
                "claims": combined_claims,
                "sources": [sources[label] | {"label": label} for label in sorted(labels_used)],
            }
            diagram = claim["kind"] == "diagram_edge"
            same_kind = (current["claims"][0]["kind"] == "diagram_edge") == diagram
            batch_size = 4 if diagram else 8
            if (
                same_kind
                and len(combined_claims) <= batch_size
                and estimate_tokens(encode(combined)) <= limit
            ):
                jobs[-1] = combined
                continue
        jobs.append(candidate)
    return jobs


def validate_audit(result, job):
    checks = [check.model_dump() for check in result.checks]
    require_exact(
        [check["claim_id"] for check in checks], [c["id"] for c in job["claims"]], "Factual audit"
    )
    by_id = {claim["id"]: claim for claim in job["claims"]}
    for check in checks:
        claim = by_id[check["claim_id"]]
        if set(check["supporting_labels"]) - set(claim["citations"]):
            raise ValueError("Factual audit attributes a claim to an uncited source")
        if check["verdict"] == "supported" and not check["supporting_labels"]:
            raise ValueError("Supported factual claim lacks local source evidence")
        if check["verdict"] in {"unsupported", "unclear"} and not check["reason"]:
            raise ValueError("Factual audit finding lacks a reason")
    return checks


def remove_section_diagrams(markdown, sections):
    lines = markdown.splitlines(keepends=True)
    kept = []
    heading = ""
    removed = 0
    index = 0
    while index < len(lines):
        line = lines[index]
        match = re.fullmatch(r"#{1,6} (.+?)\s*", line.strip())
        if match:
            heading = match.group(1)
        if heading in sections and line.strip() == "```mermaid":
            index += 1
            while index < len(lines) and lines[index].strip() != "```":
                index += 1
            if index == len(lines):
                raise ValueError("Unsupported diagram has no closing fence")
            index += 1
            while index < len(lines) and not lines[index].strip():
                index += 1
            if index == len(lines) or not lines[index].startswith("Diagram source:"):
                raise ValueError("Unsupported diagram has no adjacent source note")
            index += 1
            removed += 1
            continue
        kept.append(line)
        index += 1
    return "".join(kept), removed
