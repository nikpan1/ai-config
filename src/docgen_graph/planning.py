import json
import re
from copy import deepcopy

from pydantic import BaseModel, Field, field_validator, model_validator


def bounded_source_overview(
    sources: list[dict], facts: list[dict], max_characters: int = 12000
) -> tuple[list[dict], bool]:
    if max_characters < 2:
        raise ValueError("Overview budget must fit an empty JSON list")
    by_id = {source["id"]: source for source in sources}
    by_path = {}
    for source in sources:
        content = by_path.setdefault(source["path"], {"evidence_ids": set(), "statements": []})
        content["evidence_ids"].add(source["id"])
    for fact in facts:
        for source_id in fact["evidence_ids"]:
            if source_id in by_id:
                by_path[by_id[source_id]["path"]]["statements"].append(fact["statement"])
    overview = []
    incomplete = False
    for path, content in sorted(by_path.items()):
        summary = " ".join(dict.fromkeys(content["statements"]))
        entry = {
            "path": path,
            "navigation_summary": summary[:1000],
            "evidence_ids": sorted(content["evidence_ids"]),
        }
        if len(summary) > 1000:
            incomplete = True
        if len(json.dumps([*overview, entry], ensure_ascii=False)) > max_characters:
            incomplete = True
            continue
        overview.append(entry)
    return overview, incomplete


class SourcePlanSection(BaseModel):
    id: str = Field(min_length=1)
    parent_id: str = ""
    title: str = Field(min_length=1)
    purpose: str = ""
    evidence_ids: list[str] = []
    proposed_visuals: list[str] = []


class SourcePlan(BaseModel):
    title: str
    sections: list[SourcePlanSection] = Field(min_length=1)
    questions: list[str] = []

    @field_validator("sections")
    @classmethod
    def enforce_section_limit(cls, sections):
        if len(sections) > 40:
            raise ValueError("Documentation plans must contain at most 40 sections")
        return sections

    @model_validator(mode="before")
    @classmethod
    def normalize_sections(cls, value):
        if not isinstance(value, dict):
            return value
        sections = []
        for index, section in enumerate(value.get("sections", []), 1):
            if isinstance(section, str):
                section = {"title": section}
            if isinstance(section, dict):
                section = {"id": f"section-{index}", **section}
            sections.append(section)
        return {**value, "sections": sections}


def section_queries(section: dict | str) -> list[str]:
    if isinstance(section, str):
        return [section]
    return [str(section.get(key, "")) for key in ("title", "purpose") if section.get(key)]


def section_evidence_ids(section: dict | str) -> list[str]:
    return [] if isinstance(section, str) else list(dict.fromkeys(section.get("evidence_ids", [])))


def plan_findings(plan: dict, evidence: list[dict]) -> list[str]:
    allowed = {source["id"] for source in evidence}
    findings = hierarchy_findings(
        [section.model_dump() for section in SourcePlan.model_validate(plan).sections]
    )
    seen = set()
    for section in SourcePlan.model_validate(plan).sections:
        if section.id in seen:
            findings.append(f"Duplicate planned section ID: {section.id}")
        seen.add(section.id)
        if not section.evidence_ids:
            findings.append(f"Planned section has no source references: {section.id}")
        for source_id in section.evidence_ids:
            if source_id not in allowed:
                findings.append(f"Unknown planned source reference: {section.id}: {source_id}")
    return findings


def planned_section_findings(plan: dict, document: dict) -> list[str]:
    expected = SourcePlan.model_validate(plan).sections
    actual = {}
    findings = []
    for section in document.get("sections", []):
        identifier = section.get("id", "")
        if identifier in actual:
            findings.append(f"Duplicate document section ID: {identifier}")
        actual[identifier] = section
    for section in expected:
        if section.id not in actual:
            findings.append(f"Missing planned section: {section.id}: {section.title}")
        elif actual[section.id].get("parent_id", "") != section.parent_id:
            findings.append(f"Changed planned parent: {section.id}")
        elif (
            not actual[section.id].get("paragraphs")
            and not actual[section.id].get("visuals")
            and not any(item.parent_id == section.id for item in expected)
        ):
            findings.append(f"Empty planned section: {section.id}: {section.title}")
    return findings


def clean_section_title(title: str) -> str:
    return re.sub(r"^\s*(?:#{1,6}\s*)?(?:\d+(?:\.\d+)*[.)]?\s+)?", "", title).strip()


def hierarchy_findings(sections: list[dict]) -> list[str]:
    by_id = {section.get("id", ""): section for section in sections}
    findings = []
    for section in sections:
        current, visited = section, {section.get("id", "")}
        while parent_id := current.get("parent_id", ""):
            if parent_id not in by_id:
                findings.append(f"Unknown section parent: {section.get('id')}: {parent_id}")
                break
            if parent_id in visited:
                findings.append(f"Cyclic section parent: {section.get('id')}")
                break
            visited.add(parent_id)
            current = by_id[parent_id]
    return findings


def normalize_plan_hierarchy(plan: dict) -> dict:
    result = deepcopy(plan)
    sections = result["sections"]
    identifiers = {
        section.get("id", ""): f"section-{index}" for index, section in enumerate(sections, 1)
    }
    for index, section in enumerate(sections, 1):
        section["parent_id"] = identifiers.get(section.get("parent_id", ""), "")
        section["id"] = f"section-{index}"
        section["title"] = clean_section_title(section["title"])
    if hierarchy_findings(sections):
        for section in sections:
            section["parent_id"] = ""
    result["sections"] = [item for item, _, _ in section_outline(sections)]
    return result


def section_outline(sections: list[dict]) -> list[tuple[dict, str, int]]:
    by_id = {section.get("id", ""): section for section in sections}
    children = {}
    for section in sections:
        parent = section.get("parent_id", "")
        if parent not in by_id or parent == section.get("id"):
            parent = ""
        children.setdefault(parent, []).append(section)
    result, visited = [], set()

    def visit(items, prefix):
        for index, section in enumerate(items, 1):
            key = id(section)
            if key in visited:
                continue
            visited.add(key)
            number = f"{prefix}.{index}" if prefix else str(index)
            result.append((section, number, number.count(".") + 2))
            visit(children.get(section.get("id"), []), number)

    visit(children.get("", []), "")
    visit([section for section in sections if id(section) not in visited], "")
    return result


def render_source_plan(plan: dict) -> str:
    lines = [f"# {plan['title']}", ""]
    for section, number, level in section_outline(plan["sections"]):
        lines.extend(
            [f"{'#' * min(level, 6)} {number}. {clean_section_title(section['title'])}", ""]
        )
        if section.get("purpose"):
            lines.extend([section["purpose"], ""])
        if section.get("evidence_ids"):
            lines.extend(["Sources: " + ", ".join(section["evidence_ids"]), ""])
        for visual in section.get("proposed_visuals", []):
            lines.extend([f"Proposed visual: {visual}", ""])
    if plan.get("questions"):
        lines.extend(
            ["## Questions for review", "", *[f"- {item}" for item in plan["questions"]], ""]
        )
    return "\n".join(lines)
