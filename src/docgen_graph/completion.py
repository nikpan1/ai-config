from typing import Literal
from urllib.parse import unquote

from markdown_it import MarkdownIt
from markdown_it.rules_inline.image import image as parse_image
from pydantic import BaseModel, Field

from docgen_graph.planning import SourcePlan as SourcePlan
from docgen_graph.storage import digest


class SourceCitation(BaseModel):
    evidence_id: str
    quote: str = Field(min_length=1)


class GroundedParagraph(BaseModel):
    id: str = ""
    text: str = Field(min_length=1)
    sources: list[SourceCitation] = Field(min_length=1)
    uncertainty: str = ""


class GroundedSection(BaseModel):
    id: str = ""
    title: str
    paragraphs: list[GroundedParagraph]
    image_hashes: list[str] = []


class GroundedDocument(BaseModel):
    title: str
    sections: list[GroundedSection]
    limitations: list[str] = []


class SourceFinding(BaseModel):
    section_id: str = ""
    paragraph_id: str = ""
    section_index: int = -1
    paragraph_index: int = -1
    severity: Literal["unsupported", "contradiction", "omission", "uncertain"]
    explanation: str
    sources: list[SourceCitation] = []


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
    citation_numbers = {}
    for section in document["sections"]:
        if not section["paragraphs"] and not any(
            image_hash in image_paths for image_hash in section.get("image_hashes", [])
        ):
            continue
        lines.extend([f"## {section['title']}", ""])
        displayed_images = set()
        for paragraph in section["paragraphs"]:
            citations = []
            for source in paragraph["sources"]:
                span = available[source["evidence_id"]]
                citation_key = (source["evidence_id"], source["quote"])
                if citation_key in citation_numbers:
                    citation = f"[^{citation_numbers[citation_key]}]"
                    if citation not in citations:
                        citations.append(citation)
                    continue
                number = len(notes) + 1
                citation_numbers[citation_key] = number
                citations.append(f"[^{number}]")
                location = "; ".join(
                    f"L{item['start_line']}:{item['start_column']}-"
                    f"L{item['end_line']}:{item['end_column']}"
                    for item in quote_locations(span, source["quote"])
                )
                notes.append(
                    f"[^{number}]: [{span.get('source_image_path') or span['path']}, {location}]"
                    f"({citation_target(source)})"
                )
            text, _ = resolve_paragraph_images(
                paragraph["text"], evidence, image_paths, displayed_images
            )
            lines.extend([text + " " + " ".join(citations), ""])
        for image_hash in section.get("image_hashes", []):
            if image_hash in image_paths and image_hash not in displayed_images:
                displayed_images.add(image_hash)
                lines.extend([f"![Source illustration]({image_paths[image_hash]})", ""])
    return "\n".join(lines + notes) + "\n"


def resolve_paragraph_images(
    text: str, evidence: list[dict], image_paths: dict[str, str], displayed: set[str]
) -> tuple[str, list[dict]]:
    aliases = {}
    for image_hash, path in image_paths.items():
        aliases.setdefault(path, set()).add(image_hash)
    for span in evidence:
        image_hash, path = span.get("source_image_hash"), span.get("source_image_path")
        if image_hash in image_paths and path:
            for alias in (path, path.rsplit("/", 1)[-1], "originals/" + path):
                aliases.setdefault(alias, set()).add(image_hash)

    def image_with_range(state, silent):
        start = state.pos
        matched = parse_image(state, silent)
        if matched and not silent:
            state.tokens[-1].meta["source_range"] = [start, state.pos]
        return matched

    parser = MarkdownIt("commonmark", {"html": False}).enable("table")
    parser.inline.ruler.at("image", image_with_range)
    text = text.replace("\r\n", "\n")
    offsets = [0]
    for line in text.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    edits, records = [], []
    start, stop = 0, len(text)
    cursors = {}
    for token in parser.parse(text):
        if token.map:
            start, stop = (offsets[index] for index in token.map)
        if token.type != "inline":
            continue
        position = text.find(token.content, cursors.get((start, stop), start), stop)
        if position < 0:
            continue
        cursors[(start, stop)] = position + len(token.content)
        for child in token.children or []:
            if child.type != "image":
                continue
            target = unquote(child.attrGet("src") or "").removeprefix("./")
            matches = aliases.get(target, set())
            image_hash = next(iter(matches)) if len(matches) == 1 else None
            replacement = child.content
            outcome = "unknown_or_ambiguous_reference"
            if image_hash:
                outcome = "duplicate_caption_preserved" if image_hash in displayed else "resolved"
                if image_hash not in displayed:
                    alt = child.content.replace("[", "\\[").replace("]", "\\]")
                    replacement = f"![{alt}]({image_paths[image_hash]})"
                    displayed.add(image_hash)
            first, last = child.meta["source_range"]
            edits.append((position + first, position + last, replacement))
            records.append({"reference": target, "image_hash": image_hash, "outcome": outcome})
    for start, stop, replacement in sorted(edits, reverse=True):
        text = text[:start] + replacement + text[stop:]
    return text, records


def citation_target(source: dict) -> str:
    return "evidence/quote-" + digest((source["evidence_id"], source["quote"])) + ".md"


def citation_excerpt_files(document: dict, evidence: list[dict]) -> dict[str, str]:
    available = {span["id"]: span for span in evidence}
    files = {}
    for section in document["sections"]:
        for paragraph in section["paragraphs"]:
            for source in paragraph["sources"]:
                span = available[source["evidence_id"]]
                location = "; ".join(
                    f"L{item['start_line']}:{item['start_column']}-"
                    f"L{item['end_line']}:{item['end_column']}"
                    for item in quote_locations(span, source["quote"])
                )
                quote = "\n".join("> " + line for line in source["quote"].splitlines())
                files[citation_target(source)] = (
                    f"# Source excerpt\n\n{span['path']}, {location}\n\n{quote}\n\n"
                    f"[Read surrounding source context]({span['id']}.md)\n"
                )
    return files


def document_verification(
    document: dict, evidence: list[dict], image_paths: dict[str, str] | None = None
) -> dict:
    available = {span["id"]: span for span in evidence}
    paragraphs = []
    for section in document["sections"]:
        displayed_images = set()
        for paragraph in section["paragraphs"]:
            citations = []
            for source in paragraph["sources"]:
                span = available.get(source["evidence_id"], {})
                locations = quote_locations(span, source["quote"]) if span else []
                citations.append(
                    {
                        **source,
                        "excerpt_path": citation_target(source),
                        "path": span.get("path"),
                        "locations": locations,
                        "exact_quote_found": bool(locations),
                        "source_kind": span.get("source_kind", span.get("role", "original")),
                        "source_image_path": span.get("source_image_path"),
                        "source_image_hash": span.get("source_image_hash"),
                        "provider": span.get("provider"),
                        "model": span.get("model"),
                        "interpretation_ref": span.get("interpretation_ref"),
                    }
                )
            paragraphs.append(
                {
                    "section_id": section.get("id", ""),
                    "section_title": section["title"],
                    "paragraph_id": paragraph.get("id", ""),
                    "text": paragraph["text"],
                    "uncertainty": paragraph.get("uncertainty", ""),
                    "citations": citations,
                    "image_reference_resolutions": resolve_paragraph_images(
                        paragraph["text"], evidence, image_paths or {}, displayed_images
                    )[1],
                }
            )
    return {
        "document_hash": document_content_hash(document),
        "citation_check": "Exact quote matching does not establish semantic entailment.",
        "paragraphs": paragraphs,
        "limitations": document.get("limitations", []),
    }
