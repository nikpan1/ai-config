import re
from typing import Literal

from pydantic import BaseModel, Field

from docgen_graph.storage import digest


class SourceCitation(BaseModel):
    evidence_id: str
    quote: str = Field(min_length=1)


class GroundedParagraph(BaseModel):
    text: str = Field(min_length=1)
    sources: list[SourceCitation] = Field(min_length=1)
    uncertainty: str = ""


class GroundedSection(BaseModel):
    title: str
    paragraphs: list[GroundedParagraph]
    image_hashes: list[str] = []


class GroundedDocument(BaseModel):
    title: str
    sections: list[GroundedSection]
    limitations: list[str] = []


class SourcePlan(BaseModel):
    title: str
    sections: list[str] = Field(min_length=1, max_length=12)
    questions: list[str] = []


class SourceFinding(BaseModel):
    section_index: int
    paragraph_index: int
    severity: Literal["unsupported", "contradiction", "omission", "uncertain"]
    explanation: str


class SourceDocumentAudit(BaseModel):
    accepted: bool
    findings: list[SourceFinding]
    coverage_estimate: float = Field(ge=0, le=1)
    coverage_explanation: str


def document_content_hash(document: dict) -> str:
    return digest({"title": document["title"], "sections": document["sections"]})


def quote_locations(span: dict, quote: str) -> list[dict]:
    locations = []
    offset = 0
    while quote and (start := span["text"].find(quote, offset)) >= 0:
        end = start + len(quote)
        first_prefix = span["text"][:start]
        last_prefix = span["text"][: end - 1]
        locations.append(
            {
                "start_line": span["start_line"] + first_prefix.count("\n"),
                "end_line": span["start_line"] + last_prefix.count("\n"),
                "start_column": (
                    len(first_prefix.rsplit("\n", 1)[-1]) + 1
                    if "\n" in first_prefix
                    else span.get("start_column", 1) + start
                ),
                "end_column": (
                    len(last_prefix.rsplit("\n", 1)[-1]) + 1
                    if "\n" in last_prefix
                    else span.get("start_column", 1) + end - 1
                ),
                "source_start_char": span.get("source_start_char", 0) + start,
                "source_end_char": span.get("source_start_char", 0) + end,
            }
        )
        offset = start + 1
    return locations


def citation_findings(document: dict, evidence: list[dict]) -> list[str]:
    available = {span["id"]: span for span in evidence}
    findings = []
    for section_index, section in enumerate(document["sections"]):
        for paragraph_index, paragraph in enumerate(section["paragraphs"]):
            if not paragraph["sources"]:
                findings.append(f"Missing sources at {section_index}:{paragraph_index}")
            for source in paragraph["sources"]:
                span = available.get(source["evidence_id"])
                if not span or not source["quote"] or source["quote"] not in span["text"]:
                    findings.append(f"Invalid exact citation at {section_index}:{paragraph_index}")
    if not any(section["paragraphs"] for section in document["sections"]):
        findings.append("Document contains no grounded paragraphs")
    return findings


def quarantine_document(
    document: dict, evidence: list[dict], audit: dict | None
) -> tuple[dict, list[str]]:
    available = {span["id"]: span for span in evidence}
    rejected_findings = [
        item
        for item in (audit or {}).get("findings", [])
        if item["severity"] in {"unsupported", "contradiction"}
    ]
    blocked = {(item["section_index"], item["paragraph_index"]) for item in rejected_findings}
    global_rejection = any(item["section_index"] < 0 for item in rejected_findings)
    sections, removed = [], []
    for section_index, section in enumerate(document["sections"]):
        paragraphs = []
        for paragraph_index, paragraph in enumerate(section["paragraphs"]):
            valid = paragraph["sources"] and all(
                source["evidence_id"] in available
                and bool(source["quote"])
                and source["quote"] in available[source["evidence_id"]]["text"]
                for source in paragraph["sources"]
            )
            if (
                not valid
                or global_rejection
                or (section_index, paragraph_index) in blocked
                or (section_index, -1) in blocked
            ):
                removed.append(f"Withheld paragraph {section_index + 1}.{paragraph_index + 1}")
                continue
            paragraphs.append(paragraph)
        sections.append({**section, "paragraphs": paragraphs})
    return {**document, "sections": sections}, removed


def render_grounded_document(
    document: dict, evidence: list[dict], image_paths: dict[str, str]
) -> str:
    available = {span["id"]: span for span in evidence}
    lines, notes = [f"# {document['title']}", ""], []
    for section in document["sections"]:
        if not section["paragraphs"] and not any(
            image_hash in image_paths for image_hash in section.get("image_hashes", [])
        ):
            continue
        lines.extend([f"## {section['title']}", ""])
        for paragraph in section["paragraphs"]:
            citations = []
            for source in paragraph["sources"]:
                span = available[source["evidence_id"]]
                number = len(notes) + 1
                citations.append(f"[^{number}]")
                quote = re.sub(r"\s+", " ", source["quote"]).strip()
                location = "; ".join(
                    f"L{item['start_line']}:{item['start_column']}-"
                    f"L{item['end_line']}:{item['end_column']}"
                    for item in quote_locations(span, source["quote"])
                )
                notes.append(
                    f"[^{number}]: [{span['path']}, {location}](evidence/{span['id']}.md): {quote}"
                )
            lines.extend([paragraph["text"] + " " + " ".join(citations), ""])
            if paragraph.get("uncertainty", "").strip().casefold().rstrip(".") not in {
                "",
                "none",
                "not applicable",
                "n/a",
            }:
                lines.extend([f"Uncertainty: {paragraph['uncertainty']}", ""])
        for image_hash in section.get("image_hashes", []):
            if image_hash in image_paths:
                lines.extend([f"![Source illustration]({image_paths[image_hash]})", ""])
    if document.get("limitations"):
        lines.extend(["## Limitations", ""])
        lines.extend(f"- {item}" for item in document["limitations"])
        lines.append("")
    return "\n".join(lines + notes) + "\n"
