from copy import deepcopy

import pytest
from test_editorial_workflow import EditorialModel
from test_source_first_completion import execute, run_inputs

from docgen_graph.completion import document_content_hash
from docgen_graph.editorial import (
    merge_editorial_findings,
    outstanding_audit_findings,
    unchanged_audit_targets,
)


def fixture():
    evidence = [{"id": "source", "text": "Email is required. Guests are exempt."}]
    document = {
        "title": "Registration",
        "sections": [
            {
                "id": "s",
                "title": "Registration",
                "paragraphs": [
                    {
                        "id": "p1",
                        "text": "Email guarantees access.",
                        "sources": [{"evidence_id": "source", "quote": "Email is required."}],
                    },
                    {
                        "id": "p2",
                        "text": "Guests cannot register.",
                        "sources": [{"evidence_id": "source", "quote": "Guests are exempt."}],
                    },
                ],
            }
        ],
    }
    audit = {
        "document_content_hash": document_content_hash(document),
        "findings": [
            {
                "section_id": "s",
                "paragraph_id": "p1",
                "severity": "unsupported",
                "explanation": "Necessary was changed to sufficient.",
            },
            {
                "section_id": "s",
                "paragraph_id": "p2",
                "severity": "contradiction",
                "explanation": "Guest exception was reversed.",
            },
        ],
    }
    return document, audit, evidence


def test_visual_only_editorial_review_cannot_drop_outstanding_factual_targets():
    document, audit, evidence = fixture()
    outstanding, diagnostics = outstanding_audit_findings(document, audit, evidence)
    review = {
        "summary": "Improve diagram",
        "findings": [
            {
                "section_id": "s",
                "paragraph_id": "",
                "category": "visual",
                "explanation": "Clarify labels",
                "requested_change": "Edit diagram",
                "sources": [],
            }
        ],
    }
    merged = merge_editorial_findings(review, outstanding)
    assert not diagnostics
    assert len(merged["findings"]) == 3
    assert {item["paragraph_id"] for item in merged["findings"]} == {"", "p1", "p2"}
    assert len(review["findings"]) == 1
    assert all(
        "never source evidence" in item["requested_change"] for item in merged["findings"][1:]
    )


def test_existing_style_target_keeps_factual_diagnostic_and_exact_sources():
    document, audit, evidence = fixture()
    outstanding, _ = outstanding_audit_findings(document, audit, evidence)
    review = {
        "summary": "Improve clarity",
        "findings": [
            {
                "section_id": "s",
                "paragraph_id": "p1",
                "category": "clarity",
                "explanation": "Use shorter prose",
                "requested_change": "Shorten carefully",
                "sources": [],
            }
        ],
    }
    merged = merge_editorial_findings(review, outstanding)
    first = merged["findings"][0]
    assert len(merged["findings"]) == 2
    assert first["category"] == "unsupported"
    assert "Use shorter prose" in first["explanation"]
    assert "Necessary was changed to sufficient" in first["explanation"]
    assert first["sources"] == document["sections"][0]["paragraphs"][0]["sources"]


def test_stale_unknown_uncertain_and_unsourced_omission_audits_are_not_repair_targets():
    document, audit, evidence = fixture()
    stale = {**audit, "document_content_hash": "obsolete"}
    assert outstanding_audit_findings(document, stale, evidence)[0] == []
    invalid = {
        **audit,
        "findings": [
            {
                "section_id": "12",
                "paragraph_id": "12.1",
                "severity": "unsupported",
                "explanation": "Unknown",
            },
            {
                "section_id": "s",
                "paragraph_id": "",
                "severity": "omission",
                "explanation": "No source",
            },
            {
                "section_id": "s",
                "paragraph_id": "p1",
                "severity": "uncertain",
                "explanation": "Uncertain",
            },
        ],
    }
    findings, diagnostics = outstanding_audit_findings(document, invalid, evidence)
    assert findings == []
    assert len(diagnostics) == 3


def test_source_grounded_omission_survives_empty_editorial_review():
    document, audit, evidence = fixture()
    audit["findings"] = [
        {
            "section_id": "s",
            "paragraph_id": "",
            "severity": "omission",
            "explanation": "Include exception.",
            "sources": [{"evidence_id": "source", "quote": "Guests are exempt."}],
        }
    ]
    outstanding, _ = outstanding_audit_findings(document, audit, evidence)
    merged = merge_editorial_findings({"summary": "No issues", "findings": []}, outstanding)
    assert len(merged["findings"]) == 1
    assert merged["findings"][0]["category"] == "omission"
    assert merged["findings"][0]["sources"] == audit["findings"][0]["sources"]


def test_unchanged_guard_allows_citation_repair_but_not_duplicate_source_reordering():
    document, audit, evidence = fixture()
    outstanding, _ = outstanding_audit_findings(document, audit, evidence)
    candidate = deepcopy(document)
    candidate["sections"][0]["paragraphs"][0]["sources"][0]["quote"] = evidence[0]["text"]
    assert unchanged_audit_targets(document, candidate, outstanding) == ["p2"]
    candidate = deepcopy(document)
    candidate["sections"][0]["paragraphs"][0]["sources"] *= 2
    assert unchanged_audit_targets(document, candidate, outstanding) == ["p1", "p2"]


@pytest.mark.parametrize("visual_only", [False, True])
def test_full_pipeline_carries_remaining_factual_audit_through_editorial_and_verification(
    tmp_path, visual_only
):
    class RemainingAuditModel(EditorialModel):
        def __init__(self, path):
            super().__init__(path)
            self.editorial_payload = None
            self.verification_payload = None

        def call(self, stage, payload, schema=None):
            if stage == "audit_source_document":
                self.calls.append(stage)
                paragraph = payload["document"]["sections"][0]["paragraphs"][0]
                return {
                    "accepted": False,
                    "coverage_estimate": 1,
                    "coverage_explanation": "Controlled routing fixture",
                    "findings": [
                        {
                            "section_id": payload["document"]["sections"][0]["id"],
                            "paragraph_id": paragraph["id"],
                            "severity": "unsupported",
                            "explanation": "Review the qualifier against the original source.",
                        }
                    ],
                }
            if stage == "source_editorial":
                self.calls.append(stage)
                self.editorial_payload = deepcopy(payload)
                return {
                    "summary": "No prose defects",
                    "findings": [
                        {
                            "section_id": payload["document"]["sections"][0]["id"],
                            "paragraph_id": "",
                            "category": "visual",
                            "explanation": "Add a useful visual",
                            "requested_change": "Add a sourced diagram",
                            "sources": [],
                        }
                    ]
                    if visual_only
                    else [],
                }
            if stage == "source_revision" and visual_only:
                self.calls.append(stage)
                section = payload["document"]["sections"][0]
                return {
                    "paragraphs": [],
                    "additions": [],
                    "visuals": [
                        {
                            "section_id": section["id"],
                            "visuals": [
                                {
                                    "kind": "mermaid",
                                    "mermaid": 'flowchart TD\n A["Guest exception"]',
                                    "caption": "Guest exception",
                                    "alt": "Guest exception",
                                    "sources": section["paragraphs"][0]["sources"],
                                }
                            ],
                        }
                    ],
                }
            if stage == "verify_source_revision":
                self.verification_payload = deepcopy(payload)
            return super().call(stage, payload, schema)

    model = RemainingAuditModel(tmp_path / ".env")
    store, result = execute(tmp_path, model, run_inputs(tmp_path))
    assert model.calls.count("audit_source_document") == 2
    assert model.calls.count("source_revision") == 1
    assert model.editorial_payload["outstanding_factual_findings"]
    assert model.verification_payload["outstanding_factual_findings"]
    assert model.verification_payload["requested_changes"]["findings"]
    history = store.get(result["editorial_history_ref"])
    if visual_only:
        assert history[0]["outcome"] == "rejected_unresolved_factual_targets"
        assert history[0]["unchanged_factual_targets"]
        assert not store.get(result["completion_audit_ref"])["accepted"]
        assert store.get(history[0]["verification_ref"])["audit"]["accepted"]
    else:
        assert history[0]["outcome"] == "accepted"
        assert store.get(result["completion_audit_ref"])[
            "document_content_hash"
        ] == document_content_hash(store.get(result["candidate_ref"]))
