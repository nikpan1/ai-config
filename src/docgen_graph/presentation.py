import re

from markdown_it import MarkdownIt

from docgen_graph.source_links import CITATION_GROUP, citation_labels
from docgen_graph.storage import digest


def compact_citations(markdown: str) -> str:
    def compact(block: str) -> str:
        matches = list(CITATION_GROUP.finditer(block))
        removed = set()
        for first, second in zip(matches, matches[1:], strict=False):
            if first.group() == second.group():
                removed.add(first.start())
        return (
            CITATION_GROUP.sub(
                lambda match: "" if match.start() in removed else match.group(), block
            )
            .replace("  ", " ")
            .replace(" .", ".")
            .strip()
        )

    return "\n".join(
        compact(line) if CITATION_GROUP.search(line) else line for line in markdown.split("\n")
    )


def group_repeated_list_citations(markdown: str) -> tuple[str, list[tuple[str, str]]]:
    reference = re.compile(r"\[\d+\]\(<\.\./evidence/[^>]+>\)")
    lines = markdown.splitlines()
    output, replacements = [], []
    index = 0
    while index < len(lines):
        end = index
        while end < len(lines) and re.match(r"^\s*(?:[*+-]|\d+\.)\s+", lines[end]):
            end += 1
        group = lines[index:end]
        citations = [reference.findall(line) for line in group]
        if len(group) > 1 and citations[0] and all(item == citations[0] for item in citations):
            for line in group:
                replacement = reference.sub("", line).replace("  ", " ").replace(" .", ".").rstrip()
                replacements.append((line, replacement))
                output.append(replacement)
            output.extend(["", "Sources: " + " ".join(citations[0])])
            index = end
        else:
            output.append(lines[index])
            index += 1
    return "\n".join(output), replacements


def exact_support(evidence: dict, quote: str) -> dict:
    if not quote or quote not in evidence["text"]:
        raise ValueError(f"Missing exact support quote: {evidence['label']}")
    if evidence["text"].count(quote) != 1:
        raise ValueError(f"Ambiguous support quote: {evidence['label']}")
    start = evidence["text"].index(quote)
    first = evidence["start_line"] + evidence["text"][:start].count("\n")
    return {
        "target_id": digest([evidence["id"], start, quote])[:20],
        "snapshot_hash": evidence["file_hash"],
        "source_path": evidence["path"],
        "evidence_id": evidence["id"],
        "exact_quote": quote,
        "start_line": first,
        "end_line": first + quote.count("\n"),
        "start_char_in_evidence": start,
        "end_char_in_evidence": start + len(quote),
    }


def support_findings(mappings: list[dict], evidence: dict) -> list[str]:
    findings = []
    for mapping in mapping_occurrences(mappings):
        for label in mapping["citation_ids"]:
            item = evidence.get(label)
            if item is None:
                findings.append(f"Unknown evidence: {label}")
                continue
            try:
                exact_support(item, mapping.get("support_quotes", {}).get(label, ""))
            except ValueError as error:
                findings.append(
                    f"{error}; fact {mapping.get('obligation_id', 'unknown')}; "
                    f"passage: {mapping.get('passage', '')}"
                )
    return findings


def mapping_occurrences(mappings: list[dict]) -> list[dict]:
    return [
        occurrence
        for mapping in mappings
        for occurrence in [mapping]
        + [
            {**mapping, **extra, "additional_passages": []}
            for extra in mapping.get("additional_passages", [])
        ]
    ]


def unmapped_citation_findings(
    markdown: str, mappings: list[dict], visual_blocks: list[str]
) -> list[str]:
    ranges = []
    for item in mapping_occurrences(mappings):
        passage = item["passage"]
        start = markdown.find(passage)
        if passage and start >= 0:
            ranges.append((start, start + len(passage), set(item["citation_ids"])))
    for block in visual_blocks:
        start = markdown.find(block)
        if block and start >= 0:
            ranges.append((start, start + len(block), set(citation_labels(block))))
    findings = []
    for match in CITATION_GROUP.finditer(markdown):
        labels = set(citation_labels(match.group()))
        supported = set().union(
            *(labels for start, end, labels in ranges if start <= match.start() < end)
        )
        if labels - supported:
            line = markdown[: match.start()].count("\n") + 1
            findings.append(
                f"Citation at line {line} lacks a local exact-quote mapping: {match.group()}. "
                "Add an additional_passages occurrence to the relevant fact mapping."
            )
    return findings


def merge_mapping_occurrences(mappings: list[dict], additions: list[dict]) -> list[dict]:
    result = [dict(item) for item in mappings]
    by_id = {item["obligation_id"]: item for item in result}
    for item in additions:
        existing = by_id.get(item["obligation_id"])
        if existing is None:
            result.append(dict(item))
            by_id[item["obligation_id"]] = result[-1]
        else:
            existing["additional_passages"] = existing.get("additional_passages", []) + [
                {key: item[key] for key in ("passage", "citation_ids", "support_quotes")}
            ]
    return result


def business_prose_findings(markdown: str, template: str) -> list[str]:
    if "Business Behavior Contract" not in template:
        return []
    visible = re.sub(
        r"```mermaid\s*\n(.*?)\n```",
        lambda match: " ".join(re.findall(r'"([^"]+)"', match[1])),
        markdown,
        flags=re.S,
    )
    patterns = (
        r"\b\w+(?:Exception|Repository|Controller|Service)\b",
        r"\b(?:[A-Z][a-z]+ ){2,4}Service\b",
        r"\b(?:[Ii]dempotent|[Ii]dempotency|provider calls?|evaluation calls?)\b",
        r"\b(?:repositor(?:y|ies)|database|runtime|annotation)\b",
        r"\blocked (?:draft|questionnaire)\b",
        r"\b[a-zA-Z_]\w*\.[a-zA-Z_]\w*\s*\(",
        r"\b(?:throws?|invokes?|calls?)\s+`",
        r"@Transactional\b|\bHTTP\s+[1-5]\d\d\b",
        r"\bTICKET-\d+\b|\b(?:QF|BR)\d+(?:_\d+)?\b",
        r"```(?:sql|java|python|json|typescript|javascript)\b",
        r"\b[a-z]+(?:[A-Z][a-z0-9]+){2,}\b",
        r"\b(?:uninspected|runtime reachability|verified service evidence|"
        r"implementation internals)\b",
        r"\b[Cc]laim(?:ing|ed)? (?:a |the )?(?:[Ss]ubmission |idempotency )?[Kk]ey\b",
    )
    findings = [
        f"Implementation detail is outside the business template: {match.group()}"
        for pattern in patterns
        for match in re.finditer(pattern, visible)
    ]
    for line in markdown.splitlines():
        if line.strip().startswith(">") and line.strip() in template:
            if re.search(r"Instruction|Contract|Cross-Reference|Preview image|Goal|Check", line):
                findings.append("Copied template instruction in reader prose")
    return findings


def uncited_business_passages(markdown: str, template: str) -> list[str]:
    if "Business Behavior Contract" not in template:
        return []
    tokens = MarkdownIt().enable("table").parse(markdown)
    findings = []
    for index, token in enumerate(tokens):
        if token.type != "inline" or tokens[index - 1].type != "paragraph_open":
            continue
        text = token.content
        if citation_labels(text) or any(child.type == "image" for child in token.children or []):
            continue
        if re.search(
            r"(?:supplied|current|available|source) evidence (?:does not|provides no)|"
            r"(?:not established|not specified|not documented) (?:by|in) "
            r"(?:the )?(?:supplied|source)|"
            r"^\s*(?:See|For details|Refer to)\s.*(?:Section|\]\(#)",
            text,
            re.I,
        ):
            continue
        if re.fullmatch(
            r"For [^.!?]+, (?:see|refer to) Section [^!?]+\.?",
            text,
            re.I,
        ):
            continue
        findings.append(f"Reader passage lacks precise evidence citations: {text[:160]}")
    rows = re.findall(r"^\|.+\|\s*$", markdown, re.M)
    for index, row in enumerate(rows):
        if re.fullmatch(r"[\s|:\-]+", row):
            continue
        if index + 1 < len(rows) and re.fullmatch(r"[\s|:\-]+", rows[index + 1]):
            continue
        if not citation_labels(row):
            findings.append(f"Business table row lacks precise evidence citations: {row[:160]}")
    return findings


def render_subprocess_catalog(records: list[dict]) -> tuple[str, list[dict], list[dict]]:
    lines = [
        "| Subprocess | Business Purpose | Participants | Business Result |",
        "| --- | --- | --- | --- |",
    ]
    mappings, catalog = [], []
    for record in records:
        labels = list(
            dict.fromkeys(key for item in record["mappings"] for key in item["citation_ids"])
        )
        citations = " ".join(
            f"[{'Code' if key.startswith('C') else 'Legacy'} {key}]" for key in labels
        )
        cells = [
            record[key].replace("|", "&#124;").replace("\n", " ")
            for key in ("title", "purpose", "participants", "result")
        ]
        cells[-1] += " " + citations
        row = "| " + " | ".join(cells) + " |"
        lines.append(row)
        located = [
            {**item, "passage": row, "disposition": "overview"} for item in record["mappings"]
        ]
        mappings.extend(located)
        catalog.append(
            {
                **record,
                "id": digest(sorted(item["obligation_id"] for item in located))[:20],
                "mappings": located,
            }
        )
    return "\n".join(lines), mappings, catalog


def replace_subsection(markdown: str, title: str, content: str) -> str:
    match = re.search(rf"^###\s+{re.escape(title)}\s*$", markdown, re.M)
    if not match:
        return markdown.rstrip() + f"\n\n### {title}\n\n{content}"
    following = re.search(r"^#{1,3}\s+", markdown[match.end() :], re.M)
    end = match.end() + following.start() if following else len(markdown)
    return markdown[: match.end()] + "\n\n" + content + "\n\n" + markdown[end:]


def strip_authored_visuals(markdown: str) -> str:
    suffix = rf"(?:\s*{CITATION_GROUP.pattern})*"

    def strip_table(match: re.Match) -> str:
        return "" if re.search(r"!\[|```mermaid|<img\b", match.group()) else match.group()

    markdown = re.sub(r"<table\b[^>]*>.*?</table>" + suffix, strip_table, markdown, flags=re.S)
    markdown = re.sub(r"```mermaid\s*\n.*?\n```" + suffix, "", markdown, flags=re.S)
    markdown = re.sub(r"!\[[^\]]*\]\([^\n)]+\)" + suffix, "", markdown)
    markdown = re.sub(r"<img\b[^>]*>", "", markdown)
    return re.sub(r"\n{3,}", "\n\n", markdown).strip()


def visual_support_requirements(visuals: list[dict]) -> list[dict]:
    result = []
    for visual in visuals:
        diagram = visual.get("diagram")
        elements = (
            diagram["nodes"] + diagram["edges"]
            if diagram
            else [
                {
                    "id": "caption",
                    "label": visual["purpose"],
                    "evidence_ids": visual["evidence_ids"],
                }
            ]
        )
        used = {key for element in elements for key in element["evidence_ids"]}
        remaining = [key for key in visual["evidence_ids"] if key not in used]
        if remaining:
            elements.append(
                {"id": "caption", "label": visual["purpose"], "evidence_ids": remaining}
            )
        for element in elements:
            for key in element["evidence_ids"]:
                result.append(
                    {
                        "support_id": digest([visual["id"], element["id"], key])[:20],
                        "visual_id": visual["id"],
                        "element_id": element["id"],
                        "evidence_id": key,
                        "label": element["label"],
                    }
                )
    return result
