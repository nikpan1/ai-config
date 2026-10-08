import re
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

from docgen.planning_helpers import require_exact
from docgen.storage import digest, file_digest


def table_specs(context, job):
    specs = []
    for index, table in enumerate(context["brief"]["content"]["tables"]):
        rows = [
            row
            for row in table["rows"]
            if (
                set(row["obligation_ids"]) & set(job["obligation_ids"])
                or row["editorial"]
                and job["fragment"] == 0
            )
        ]
        if rows:
            specs.append({"index": index, "columns": table["columns"], "rows": rows})
    return specs


def diagram_ids(context, job):
    return (
        [
            f"{job['brief_id']}:{index}"
            for index, _ in enumerate(context["brief"]["content"]["diagrams"])
        ]
        if job["fragment"] == 0
        else []
    )


def validate_annotation(item, allowed, obligations, blocks, editorial=False, location="Text"):
    if set(item["obligation_ids"]) - allowed:
        raise ValueError(f"{location}: fragment references an unassigned obligation")
    if not editorial and (not item["obligation_ids"] or not item["evidence"]):
        raise ValueError(
            f"{location}: factual text lacks assigned obligation IDs or exact source evidence. "
            "Cite the relevant assigned evidence, or correct an unsupported statement. "
            "Only a nonfactual description of document organization can be editorial."
        )
    evidence_allowed = {
        digest(e) for key in item["obligation_ids"] for e in obligations[key]["evidence"]
    }
    for evidence in item["evidence"]:
        block = blocks.get(evidence["block_id"])
        if block is None or evidence["excerpt"] not in block["content"]:
            raise ValueError(f"{location}: citation is not an exact original source excerpt")
        if digest(evidence) not in evidence_allowed:
            raise ValueError(f"{location}: citation is not evidence of the assigned obligation")


def check_inline(text):
    tokens = MarkdownIt("commonmark").enable("table").parse(text)
    if has_raw_html(tokens):
        raise ValueError("Raw HTML is not permitted")
    if any(
        t.type in {"heading_open", "fence", "code_block", "table_open", "blockquote_open"}
        for t in tokens
    ):
        raise ValueError("Passages must not introduce headings, tables, quotes or code fences")
    for token in tokens:
        if any(c.type in {"link_open", "image", "html_inline"} for c in token.children or []):
            raise ValueError(
                "Links and images must come from validated source and navigation records"
            )


def validate_fragment(fragment, job, context, contract):
    value = fragment.model_dump()
    if value["job_id"] != job["id"] or value["section_id"] != job["section_id"]:
        raise ValueError("Fragment identity differs from its writing job")
    require_exact(value["covered_obligation_ids"], job["obligation_ids"], "Fragment coverage")
    obligations = {o["id"]: o for o in context["originals"]["obligations"]}
    blocks = {b["id"]: b for b in context["originals"]["source_blocks"]}
    allowed, used = set(job["obligation_ids"]), set()
    for passage_index, passage in enumerate(value["passages"]):
        validate_annotation(
            passage,
            allowed,
            obligations,
            blocks,
            passage["kind"] == "editorial",
            f"Passage {passage_index + 1} ({passage['text'][:100]})",
        )
        if passage["kind"] == "editorial" and passage["obligation_ids"]:
            raise ValueError("An obligation cannot be fulfilled by editorial text")
        if passage["kind"] == "quote":
            if contract["quote_policy"] == "none" or not any(
                passage["text"] == e["excerpt"] for e in passage["evidence"]
            ):
                raise ValueError("Source quotation was modified or not authorized")
        else:
            check_inline(passage["text"])
        used.update(passage["obligation_ids"])
    specs = {s["index"]: s for s in table_specs(context, job)}
    require_exact([t["index"] for t in value["tables"]], specs, "Planned tables")
    for table in value["tables"]:
        spec = specs[table["index"]]
        rows = {r["id"]: r for r in spec["rows"]}
        require_exact([r["id"] for r in table["rows"]], rows, "Planned table rows")
        for row in table["rows"]:
            original = rows[row["id"]]
            if len(row["cells"]) != len(spec["columns"]):
                raise ValueError("Table cell count differs from specified columns")
            for cell_index, cell in enumerate(row["cells"]):
                validate_annotation(
                    cell,
                    allowed,
                    obligations,
                    blocks,
                    original["editorial"],
                    f"Table {table['index']}, row {row['id']}, column {cell_index + 1}",
                )
                if set(cell["obligation_ids"]) - set(original["obligation_ids"]):
                    raise ValueError("Table cell evidence belongs to another row")
                check_inline(cell["text"])
                used.update(cell["obligation_ids"])
    require_exact(sorted(used), job["obligation_ids"], "Evidence-backed treatment")
    return value


def validate_verification(result, job, context):
    require_exact(result.checked_obligation_ids, job["obligation_ids"], "Semantic verification")
    require_exact(
        result.checked_table_rows,
        [f"{t['index']}:{r['id']}" for t in table_specs(context, job) for r in t["rows"]],
        "Verified table rows",
    )
    require_exact(result.checked_diagram_ids, diagram_ids(context, job), "Verified diagrams")
    if any(set(f.obligation_ids) - set(job["obligation_ids"]) for f in result.findings):
        raise ValueError("Verification finding references another job")


def heading_slug(text):
    text = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"\s", "-", text)


def has_raw_html(tokens):
    return any(
        token.type == "html_block"
        or any(child.type == "html_inline" for child in token.children or [])
        for token in tokens
    )


def markdown_report(pages, output_root, store, assets):
    findings, links, anchors = [], [], {}
    parser = MarkdownIt("commonmark").enable("table")
    for name, text in pages.items():
        tokens = parser.parse(text)
        headings, previous, slugs, counts = [], 0, set(), Counter()
        if has_raw_html(tokens):
            findings.append(f"{name}: raw HTML")
        if text.count("```") % 2:
            findings.append(f"{name}: unclosed code fence")
        for index, token in enumerate(tokens):
            if token.type == "heading_open":
                level = int(token.tag[1:])
                if level > previous + 1:
                    findings.append(f"{name}: skipped heading level")
                previous = level
                headings.append(level)
                slug = heading_slug(tokens[index + 1].content)
                actual = slug if counts[slug] == 0 else f"{slug}-{counts[slug]}"
                counts[slug] += 1
                slugs.add(actual)
            if token.type == "fence" and token.info == "mermaid":
                if not token.content.startswith("flowchart TD\n"):
                    findings.append(f"{name}: unsupported Mermaid syntax")
            for child in token.children or []:
                if child.type in {"link_open", "image"}:
                    href = child.attrGet("href") or child.attrGet("src")
                    if child.type == "image" and not child.content.strip():
                        findings.append(f"{name}: image lacks alternative text")
                    links.append((name, href))
        if not headings or headings[0] != 1 or headings.count(1) != 1:
            findings.append(f"{name}: require exactly one page title")
        anchors[name] = slugs
    allowed_assets = {Path(a["target"]).resolve(): a["hash"] for a in assets if a.get("target")}
    for name, href in links:
        parsed = urlsplit(href)
        if parsed.scheme or parsed.netloc:
            findings.append(f"{name}: external link is not an authorized immutable asset: {href}")
            continue
        target = (output_root / name).parent.joinpath(unquote(parsed.path)).resolve()
        if not parsed.path:
            target = (output_root / name).resolve()
        if target.is_relative_to(output_root):
            key = target.relative_to(output_root).as_posix()
            if (
                key not in pages
                or parsed.fragment
                and unquote(parsed.fragment) not in anchors.get(key, set())
            ):
                findings.append(f"{name}: broken page link: {href}")
        elif target in allowed_assets:
            if not target.is_file() or file_digest(target) != allowed_assets[target]:
                findings.append(f"{name}: missing or changed source asset: {href}")
        else:
            findings.append(f"{name}: unauthorized local link: {href}")
    return {
        "passed": not findings,
        "findings": findings,
        "checked_links": len(links),
        "pages": len(pages),
        "format": "commonmark_gfm",
        "rendered_publication": False,
    }
