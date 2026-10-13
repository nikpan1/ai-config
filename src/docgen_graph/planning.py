import json

from pydantic import BaseModel, Field, model_validator


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
    title: str = Field(min_length=1)
    purpose: str = ""
    evidence_ids: list[str] = []


class SourcePlan(BaseModel):
    title: str
    sections: list[SourcePlanSection] = Field(min_length=1, max_length=12)
    questions: list[str] = []

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
    findings = []
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
        elif not actual[section.id].get("paragraphs"):
            findings.append(f"Empty planned section: {section.id}: {section.title}")
    return findings
