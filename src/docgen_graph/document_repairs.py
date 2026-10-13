import re
from copy import deepcopy

from markdown_it import MarkdownIt

from docgen_graph.presentation import (
    exact_support,
    render_subprocess_catalog,
    replace_subsection,
    strip_authored_visuals,
)
from docgen_graph.quality import position_visuals, render_visuals
from docgen_graph.source_links import CITATION_GROUP, citation_labels


def unique_visual_quote(source_text: str, quote: str) -> str:
    if not quote:
        return quote
    first = source_text.find(quote)
    last = source_text.rfind(quote)
    if first < 0 or first == last:
        return quote
    expanded = source_text[first : last + len(quote)]
    return expanded if source_text.find(expanded) == source_text.rfind(expanded) else quote


def _plain_heading(title: str) -> str:
    return re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", title).strip().casefold()


def _restore_headings(markdown: str, fixed_headings: list[str]) -> tuple[str, list[dict]]:
    targets = {}
    for title in fixed_headings:
        targets.setdefault(_plain_heading(title), []).append(title)
    tokens = MarkdownIt().parse(markdown)
    lines = markdown.splitlines()
    repairs = []
    titles = [
        tokens[index + 1].content
        for index, token in enumerate(tokens)
        if token.type == "heading_open"
    ]
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        title = tokens[index + 1].content
        candidates = targets.get(_plain_heading(title), [])
        if len(candidates) != 1 or title == candidates[0]:
            continue
        if sum(_plain_heading(other) == _plain_heading(title) for other in titles) != 1:
            continue
        line = token.map[0]
        lines[line] = "#" * int(token.tag[1:]) + " " + candidates[0]
        repairs.append({"kind": "fixed_heading", "before": title, "after": candidates[0]})
    return ("\n".join(lines) if repairs else markdown), repairs


def _supported_occurrences(mappings: list[dict], evidence: dict, assertions: dict) -> list[dict]:
    occurrences = []
    for mapping in mappings:
        assertion = assertions.get(mapping["obligation_id"])
        if assertion is None or mapping.get("disposition") == "out_of_scope":
            continue
        allowed = set(assertion.get("evidence_ids", []))
        for occurrence in [mapping] + mapping.get("additional_passages", []):
            labels = occurrence["citation_ids"]
            if not labels:
                continue
            try:
                for label in labels:
                    source = evidence[label]
                    if source["id"] not in allowed:
                        raise ValueError("Unapproved evidence")
                    exact_support(source, occurrence.get("support_quotes", {}).get(label, ""))
            except (KeyError, ValueError):
                continue
            occurrences.append(occurrence)
    return occurrences


def _restore_citations(markdown: str, occurrences: list[dict]) -> tuple[str, list[dict]]:
    groups = {}
    for occurrence in occurrences:
        candidate = occurrence["passage"]
        if not candidate.strip():
            continue
        if candidate not in markdown:
            candidate = CITATION_GROUP.sub("", candidate).strip()
        if not candidate or markdown.count(candidate) != 1:
            continue
        groups.setdefault(candidate, []).append(occurrence)
    repairs = []
    for candidate, group in groups.items():
        labels = sorted({label for item in group for label in item["citation_ids"]})
        missing = [label for label in labels if label not in citation_labels(candidate)]
        if not missing:
            continue
        citations = " ".join(
            f"[{'Code' if label.startswith('C') else 'Legacy'} {label}]" for label in missing
        )
        replacement = candidate.rstrip() + " " + citations
        if candidate.rstrip().endswith("|"):
            replacement = candidate.rstrip()[:-1].rstrip() + " " + citations + " |"
        markdown = markdown.replace(candidate, replacement, 1)
        for occurrence in group:
            occurrence["passage"] = replacement
        repairs.append(
            {"kind": "local_citation", "before": candidate, "after": replacement, "labels": missing}
        )
    return markdown, repairs


def _repair_citation_ownership(
    mappings: list[dict], evidence: dict, assertions: dict
) -> list[dict]:
    groups = {}
    for mapping in mappings:
        if mapping.get("disposition") == "out_of_scope":
            continue
        for occurrence in [mapping] + mapping.get("additional_passages", []):
            groups.setdefault(occurrence["passage"], []).append((mapping, occurrence))
    repairs = []
    for passage, group in groups.items():
        if len(group) < 2:
            continue
        ownership = []
        valid_quotes = True
        for mapping, occurrence in group:
            allowed = set(assertions.get(mapping["obligation_id"], {}).get("evidence_ids", []))
            owned = []
            for label in occurrence["citation_ids"]:
                source = evidence.get(label)
                if not source or source["id"] not in allowed:
                    continue
                try:
                    exact_support(source, occurrence.get("support_quotes", {}).get(label, ""))
                except ValueError:
                    valid_quotes = False
                    continue
                owned.append(label)
            ownership.append(owned)
        required = set(citation_labels(passage)) | {
            label for _, occurrence in group for label in occurrence["citation_ids"]
        }
        if (
            not valid_quotes
            or not all(ownership)
            or required != {label for labels in ownership for label in labels}
        ):
            continue
        for (mapping, occurrence), owned in zip(group, ownership, strict=True):
            if occurrence["citation_ids"] == owned:
                continue
            repairs.append(
                {
                    "kind": "shared_passage_citation_ownership",
                    "obligation_id": mapping["obligation_id"],
                    "before": occurrence["citation_ids"],
                    "after": owned,
                }
            )
            occurrence["citation_ids"] = owned
    return repairs


def _unique_enclosing_passages(markdown: str, passage: str) -> list[str]:
    matches = list(re.finditer(re.escape(passage), markdown))
    if len(matches) < 2:
        return []
    lines = markdown.splitlines(keepends=True)
    starts, offset = [], 0
    for line in lines:
        starts.append(offset)
        offset += len(line)
    labels = set(citation_labels(passage))
    expanded = []
    for match in matches:
        first = max(index for index, start in enumerate(starts) if start <= match.start())
        last = max(index for index, start in enumerate(starts) if start < match.end())
        found = None
        for width in range(last - first + 1, len(lines) + 1):
            for left in range(max(0, last - width + 1), min(first + 1, len(lines) - width + 1)):
                candidate = "".join(lines[left : left + width]).strip()
                if markdown.count(candidate) == 1 and set(citation_labels(candidate)) == labels:
                    found = candidate
                    break
            if found is not None:
                break
        if found is None:
            return []
        expanded.append(found)
    return list(dict.fromkeys(expanded))


def _repair_passage_locations(
    markdown: str, mappings: list[dict], supported: list[dict]
) -> list[dict]:
    supported_ids = {id(item) for item in supported}
    repairs = []
    for mapping in mappings:
        occurrences = [mapping] + mapping.get("additional_passages", [])
        located = []
        changed = False
        for occurrence in occurrences:
            passage = occurrence["passage"]
            expanded = (
                _unique_enclosing_passages(markdown, passage)
                if passage
                and id(occurrence) in supported_ids
                and set(occurrence["citation_ids"]).issubset(citation_labels(passage))
                else []
            )
            if expanded:
                changed = True
                repairs.append(
                    {
                        "kind": "all_passage_occurrences",
                        "obligation_id": mapping["obligation_id"],
                        "before": passage,
                        "after": expanded,
                    }
                )
            for value in expanded or [passage]:
                item = {
                    key: deepcopy(occurrence[key])
                    for key in ("passage", "citation_ids", "support_quotes")
                    if key in occurrence
                }
                item["passage"] = value
                if item not in located:
                    located.append(item)
        if changed:
            mapping.update(located[0])
            mapping["additional_passages"] = located[1:]
    return repairs


def repair_document_draft(
    draft: dict,
    *,
    evidence: list[dict],
    assertions: list[dict],
    fixed_headings: list[str] = (),
    visuals: list[dict] = (),
    assets: list[dict] = (),
    subprocess_records: list[dict] = (),
) -> tuple[dict, list[dict]]:
    repaired = deepcopy(draft)
    markdown, repairs = _restore_headings(repaired["markdown"], fixed_headings)
    evidence_by_label = {item["label"]: item for item in evidence}
    assertions_by_id = {item["id"]: item for item in assertions}
    repairs.extend(
        _repair_citation_ownership(
            repaired.get("mappings", []), evidence_by_label, assertions_by_id
        )
    )
    occurrences = _supported_occurrences(
        repaired.get("mappings", []),
        evidence_by_label,
        assertions_by_id,
    )
    markdown, citation_repairs = _restore_citations(markdown, occurrences)
    repairs.extend(citation_repairs)
    if subprocess_records:
        table, _, _ = render_subprocess_catalog(subprocess_records)
        if table not in markdown:
            markdown = replace_subsection(markdown, "4.2 Key Subprocesses", table)
            repairs.append(
                {"kind": "approved_subprocess_catalog", "records": len(subprocess_records)}
            )
    rendered = render_visuals(visuals, assets, evidence)
    composed = strip_authored_visuals(markdown)
    if rendered:
        composed += "\n\n" + rendered
        composed = position_visuals(composed, visuals, assets, evidence)
    if composed != markdown.strip():
        repairs.append({"kind": "approved_visuals", "visual_ids": [item["id"] for item in visuals]})
        markdown = composed
    repairs.extend(_repair_passage_locations(markdown, repaired.get("mappings", []), occurrences))
    repaired["markdown"] = markdown
    return repaired, repairs


def restore_verified_editorial_section(
    section: dict, findings: list[str]
) -> tuple[dict, list[dict]]:
    return (
        {"markdown": section["markdown"], "mappings": deepcopy(section["mappings"])},
        [{"kind": "restore_verified_editorial_content", "findings": list(findings)}],
    )
