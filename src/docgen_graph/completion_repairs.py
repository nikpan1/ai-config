import re
from copy import deepcopy

from pydantic import BaseModel, Field

from docgen_graph.completion import GroundedParagraph, citation_findings
from docgen_graph.storage import digest


class ParagraphRepair(BaseModel):
    target_id: str
    paragraphs: list[GroundedParagraph] = Field(min_length=1)


class DocumentRepairs(BaseModel):
    repairs: list[ParagraphRepair]


def assign_document_ids(document: dict) -> dict:
    result = deepcopy(document)
    used = set()
    for section_index, section in enumerate(result["sections"]):
        identifier = section.get("id")
        if not identifier or identifier in used:
            identifier = "section-" + digest([section_index, section["title"]])[:16]
        section["id"] = identifier
        used.add(identifier)
        for paragraph_index, paragraph in enumerate(section["paragraphs"]):
            identifier = paragraph.get("id")
            if not identifier or identifier in used:
                identifier = (
                    "paragraph-" + digest([section["id"], paragraph_index, paragraph["text"]])[:16]
                )
            paragraph["id"] = identifier
            used.add(identifier)
    return result


def valid_citations(sources: list[dict], evidence: list[dict]) -> list[dict]:
    available = {item["id"]: item for item in evidence}
    return [
        item
        for item in sources
        if item.get("evidence_id") in available
        and item.get("quote")
        and item["quote"] in available[item["evidence_id"]]["text"]
    ]


def citation_targets(document: dict, evidence: list[dict]) -> list[dict]:
    targets = []
    for section in document["sections"]:
        for paragraph in section["paragraphs"]:
            sources = paragraph.get("sources", [])
            if sources and len(valid_citations(sources, evidence)) == len(sources):
                continue
            targets.append(
                {
                    "target_id": paragraph["id"],
                    "section_id": section["id"],
                    "paragraph": paragraph,
                    "issue": "Repair the missing or invalid exact source citations and claim.",
                    "sources": sources,
                }
            )
    return targets


def preserve_planned_sections(
    document: dict, plan: dict, evidence: list[dict]
) -> tuple[dict, list[dict]]:
    result = assign_document_ids(document)
    available = {item["id"]: item for item in evidence}
    targets = []
    for index, planned in enumerate(plan.get("sections", [])):
        title = planned if isinstance(planned, str) else planned["title"]
        identifier = planned.get("id") if isinstance(planned, dict) else None
        section = next(
            (
                item
                for item in result["sections"]
                if (identifier and item["id"] == identifier)
                or item["title"].strip().casefold() == title.strip().casefold()
            ),
            None,
        )
        if section is None:
            section = {
                "id": identifier or "section-" + digest([index, title])[:16],
                "title": title,
                "paragraphs": [],
                "image_hashes": [],
            }
            result["sections"].append(section)
        elif identifier:
            section["id"] = identifier
        if section["paragraphs"]:
            continue
        evidence_ids = planned.get("evidence_ids", []) if isinstance(planned, dict) else []
        targets.append(
            {
                "target_id": "omission-" + section["id"],
                "section_id": section["id"],
                "paragraph": None,
                "issue": "Write the missing planned section from its sources.",
                "sources": [
                    {"evidence_id": item, "quote": available[item]["text"]}
                    for item in evidence_ids
                    if item in available
                ],
            }
        )
    return result, targets


def audit_targets(
    document: dict, audit: dict, evidence: list[dict]
) -> tuple[list[dict], list[dict]]:
    targets, diagnostics = [], []
    for ordinal, finding in enumerate(audit.get("findings", [])):
        severity = finding["severity"]
        sources = valid_citations(finding.get("sources", []), evidence)
        section_id, paragraph_id = finding.get("section_id"), finding.get("paragraph_id")
        sections = document["sections"]
        section = next((item for item in sections if item["id"] == section_id), None)
        if not section_id:
            index = finding.get("section_index", -1)
            section = sections[index] if 0 <= index < len(sections) else None
            if index == -1 and severity == "omission" and sources and sections:
                source_ids = {item["evidence_id"] for item in sources}
                section = max(
                    sections,
                    key=lambda item: len(
                        source_ids
                        & {
                            source["evidence_id"]
                            for paragraph in item["paragraphs"]
                            for source in paragraph["sources"]
                        }
                    ),
                )
        if section is None:
            diagnostics.append({"finding": finding, "reason": "Unknown section target"})
            continue
        paragraphs = section["paragraphs"]
        paragraph = next((item for item in paragraphs if item["id"] == paragraph_id), None)
        if not paragraph_id:
            index = finding.get("paragraph_index", -1)
            paragraph = paragraphs[index] if 0 <= index < len(paragraphs) else None
        if severity == "uncertain":
            diagnostics.append({"finding": finding, "reason": "Uncertainty retained for review"})
            continue
        if severity == "omission":
            if not sources:
                diagnostics.append({"finding": finding, "reason": "Omission has no exact source"})
                continue
            target_id = f"omission-{digest([section['id'], ordinal, sources])[:16]}"
            paragraph = None
        elif paragraph is None:
            diagnostics.append({"finding": finding, "reason": "Unknown paragraph target"})
            continue
        else:
            target_id = paragraph["id"]
        target = next((item for item in targets if item["target_id"] == target_id), None)
        if target:
            target["issue"] += "\n" + finding["explanation"]
            target["sources"].extend(sources)
        else:
            targets.append(
                {
                    "target_id": target_id,
                    "section_id": section["id"],
                    "paragraph": paragraph,
                    "issue": finding["explanation"],
                    "sources": sources or (paragraph or {}).get("sources", []),
                }
            )
    return targets, diagnostics


def source_fallback(target: dict, section: dict, evidence: list[dict]) -> list[dict]:
    authored = [
        item
        for item in evidence
        if item.get("role") != "generated_image_description"
        and item.get("source_kind") != "generated_image_description"
        and item.get("text", "").strip()
    ]
    exact = valid_citations(target.get("sources", []), authored)
    if exact:
        return [{"text": item["quote"], "sources": [item], "uncertainty": ""} for item in exact]
    cited_ids = {item.get("evidence_id") for item in target.get("sources", [])}
    image_sources = [
        item
        for item in evidence
        if item["id"] in cited_ids
        and item.get("fallback_text")
        and item["fallback_text"] in item["text"]
    ]
    if image_sources:
        return [
            {
                "text": item["fallback_text"],
                "sources": [{"evidence_id": item["id"], "quote": item["fallback_text"]}],
                "uncertainty": "",
            }
            for item in image_sources
        ]
    pertinent = [item for item in authored if item["id"] in cited_ids]
    if not pertinent and not image_sources:
        section_sources = {
            source["evidence_id"]
            for paragraph in section["paragraphs"]
            for source in valid_citations(paragraph.get("sources", []), authored)
        }
        pertinent = [item for item in authored if item["id"] in section_sources]
    if not pertinent and authored:
        terms = set(
            re.findall(
                r"\w+",
                (
                    section["title"] + " " + (target.get("paragraph") or {}).get("text", "")
                ).casefold(),
            )
        )
        best = max(
            authored,
            key=lambda item: len(terms & set(re.findall(r"\w+", item["text"].casefold()))),
        )
        if terms & set(re.findall(r"\w+", best["text"].casefold())):
            pertinent = [best]
    return [
        {
            "text": item["text"],
            "sources": [{"evidence_id": item["id"], "quote": item["text"]}],
            "uncertainty": "",
        }
        for item in pertinent
    ]


def apply_repairs(
    document: dict, targets: list[dict], response: dict, evidence: list[dict]
) -> tuple[dict, list[dict]]:
    result = deepcopy(document)
    repairs = response.get("repairs", [])
    records = []
    for target in targets:
        section = next(item for item in result["sections"] if item["id"] == target["section_id"])
        proposed = [item for item in repairs if item.get("target_id") == target["target_id"]]
        paragraphs = proposed[0].get("paragraphs", []) if len(proposed) == 1 else []
        valid = bool(paragraphs) and not citation_findings(
            {"sections": [{"paragraphs": paragraphs}]}, evidence
        )
        if not valid:
            paragraphs = source_fallback(target, section, evidence)
        unavailable = not paragraphs
        if unavailable:
            paragraphs = [
                {
                    "text": "This topic requires clarification from the source owner.",
                    "sources": [],
                    "uncertainty": "No verifiable source passage available",
                }
            ]
        paragraphs = deepcopy(paragraphs)
        for index, paragraph in enumerate(paragraphs):
            paragraph["id"] = (
                target["target_id"] if index == 0 else f"{target['target_id']}-{index + 1}"
            )
        original_index = next(
            (
                index
                for index, paragraph in enumerate(section["paragraphs"])
                if paragraph["id"] == target["target_id"]
            ),
            None,
        )
        if original_index is None:
            section["paragraphs"].extend(paragraphs)
        else:
            section["paragraphs"][original_index : original_index + 1] = paragraphs
        records.append(
            {
                "target_id": target["target_id"],
                "section_id": section["id"],
                "outcome": "repaired"
                if valid
                else "source_extract_fallback"
                if not unavailable
                else "unresolved_no_authored_source",
                "replacement_ids": [item["id"] for item in paragraphs],
            }
        )
    return result, records
