from copy import deepcopy
from typing import Literal

from pydantic import BaseModel

from docgen_graph.completion import (
    GroundedParagraph,
    GroundedVisual,
    SourceCitation,
    SourceDocumentAudit,
    citation_findings,
    document_content_hash,
    document_structure_findings,
    visual_findings,
)
from docgen_graph.completion_repairs import assign_document_ids, audit_targets


class EditorialFinding(BaseModel):
    section_id: str
    paragraph_id: str = ""
    category: Literal["clarity", "consistency", "unsupported", "omission", "visual"]
    explanation: str
    requested_change: str
    sources: list[SourceCitation] = []


class EditorialReview(BaseModel):
    findings: list[EditorialFinding]
    summary: str


class ParagraphRevision(BaseModel):
    paragraph_id: str
    paragraph: GroundedParagraph


class ParagraphAddition(BaseModel):
    section_id: str
    paragraph: GroundedParagraph


class VisualRevision(BaseModel):
    section_id: str
    visuals: list[GroundedVisual]


class DocumentRevision(BaseModel):
    paragraphs: list[ParagraphRevision] = []
    additions: list[ParagraphAddition] = []
    visuals: list[VisualRevision] = []


class RevisionVerification(BaseModel):
    preserves_supported_information: bool
    no_new_unsupported_claims: bool
    resolves_requested_changes: bool
    explanation: str
    lost_or_changed_information: list[str] = []
    remaining_editorial_findings: list[EditorialFinding] = []
    audit: SourceDocumentAudit


def outstanding_audit_findings(
    document: dict, audit: dict | None, evidence: list[dict]
) -> tuple[list[dict], list[dict]]:
    if not audit:
        return [], []
    if audit.get("document_content_hash") != document_content_hash(document):
        return [], [{"reason": "Factual audit belongs to a different document version"}]
    targets, diagnostics = audit_targets(document, audit, evidence)
    return [
        {
            "section_id": target["section_id"],
            "paragraph_id": target["paragraph"]["id"] if target["paragraph"] else "",
            "category": "unsupported" if target["paragraph"] else "omission",
            "explanation": target["issue"],
            "requested_change": (
                "Recheck this unresolved factual audit finding against original sources. "
                "Correct only source-confirmed defects and preserve supported information. "
                "The audit explanation is diagnostic feedback, never source evidence."
            ),
            "sources": target["sources"],
        }
        for target in targets
    ], diagnostics


def merge_editorial_findings(review: dict, outstanding: list[dict]) -> dict:
    result = deepcopy(review)
    for finding in outstanding:
        current = next(
            (
                item
                for item in result["findings"]
                if finding["paragraph_id"] and item.get("paragraph_id") == finding["paragraph_id"]
            ),
            None,
        )
        if not current:
            result["findings"].append(deepcopy(finding))
            continue
        current["category"] = finding["category"]
        current["explanation"] += "\nOutstanding factual audit feedback: " + finding["explanation"]
        current["requested_change"] += "\n" + finding["requested_change"]
        current["sources"] = list(
            {
                (source["evidence_id"], source["quote"]): source
                for source in current.get("sources", []) + finding["sources"]
            }.values()
        )
    return result


def unchanged_audit_targets(original: dict, candidate: dict, outstanding: list[dict]) -> list[str]:
    def claims(document):
        return {
            paragraph["id"]: (
                paragraph["text"],
                sorted(
                    {(source["evidence_id"], source["quote"]) for source in paragraph["sources"]}
                ),
            )
            for section in document["sections"]
            for paragraph in section["paragraphs"]
        }

    before, after = claims(original), claims(candidate)
    return list(
        dict.fromkeys(
            item["paragraph_id"]
            for item in outstanding
            if item.get("paragraph_id")
            and before.get(item["paragraph_id"]) == after.get(item["paragraph_id"])
        )
    )


def apply_editorial_revision(document: dict, revision: dict, review: dict) -> dict:
    result = deepcopy(document)
    paragraphs = {
        paragraph["id"]: paragraph
        for section in result["sections"]
        for paragraph in section["paragraphs"]
    }
    sections = {section["id"]: section for section in result["sections"]}
    allowed_paragraphs = {
        finding["paragraph_id"] for finding in review["findings"] if finding.get("paragraph_id")
    }
    allowed_additions = {
        finding["section_id"] for finding in review["findings"] if finding["category"] == "omission"
    }
    allowed_visuals = {
        finding["section_id"] for finding in review["findings"] if finding["category"] == "visual"
    }
    changed = set()
    for item in revision.get("paragraphs", []):
        key = item["paragraph_id"]
        if key not in paragraphs or key not in allowed_paragraphs or key in changed:
            raise ValueError(
                "Editorial revision addresses an unknown, untargeted or duplicate paragraph"
            )
        paragraphs[key].clear()
        paragraphs[key].update({**item["paragraph"], "id": key})
        changed.add(key)
    for item in revision.get("additions", []):
        key = item["section_id"]
        if key not in sections or key not in allowed_additions:
            raise ValueError(
                "Editorial addition must address a sourced omission in an existing section"
            )
        sections[key]["paragraphs"].append({**item["paragraph"], "id": ""})
    changed_visuals = set()
    for item in revision.get("visuals", []):
        key = item["section_id"]
        if key not in sections or key not in allowed_visuals or key in changed_visuals:
            raise ValueError("Editorial visual revision must address a unique targeted section")
        sections[key]["visuals"] = item["visuals"]
        changed_visuals.add(key)
    return assign_document_ids(result)


def revision_findings(
    original: dict, candidate: dict, evidence: list[dict], image_paths: dict[str, str]
) -> list[str]:
    findings = citation_findings(candidate, evidence)
    findings += document_structure_findings(candidate)
    findings += visual_findings(candidate, evidence, image_paths)
    if [
        (item["id"], item["title"], item.get("parent_id", "")) for item in original["sections"]
    ] != [(item["id"], item["title"], item.get("parent_id", "")) for item in candidate["sections"]]:
        findings.append("Revision changed the approved section structure")
    for section in original["sections"]:
        current = next((item for item in candidate["sections"] if item["id"] == section["id"]), {})
        previous_ids = {item["id"] for item in section["paragraphs"]}
        candidate_ids = {item["id"] for item in current.get("paragraphs", [])}
        if previous_ids - candidate_ids:
            findings.append(f"Revision lost paragraph identities in {section['id']}")
    return findings


def revision_accepted(verification: dict) -> bool:
    return bool(
        verification.get("preserves_supported_information")
        and verification.get("no_new_unsupported_claims")
        and verification.get("resolves_requested_changes")
        and not verification.get("lost_or_changed_information")
        and verification.get("audit", {}).get("accepted")
        and not any(
            item.get("severity") in {"unsupported", "contradiction", "omission"}
            for item in verification.get("audit", {}).get("findings", [])
        )
    )
