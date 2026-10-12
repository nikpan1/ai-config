from docgen_graph.source_coverage import (
    audit_decisions,
    editorial_findings,
    validate_aspect_inventory,
)


def test_all_facts_used_does_not_cover_missing_source_condition():
    spans = {"e": {"text": "The system proposes a substitute only after customer acceptance."}}
    aspects, findings = validate_aspect_inventory(
        [
            {
                "evidence_id": "e",
                "quote": "only after customer acceptance",
                "kind": "condition",
                "description": "Acceptance required",
            }
        ],
        spans,
    )
    assert not findings
    facts = [{"id": "f", "statement": "The system proposes a substitute.", "evidence_ids": ["e"]}]
    result = audit_decisions(
        aspects,
        [
            {
                "aspect_id": aspects[0]["id"],
                "status": "unresolved",
                "fact_ids": [],
                "reason": "Acceptance absent",
            }
        ],
        facts,
    )
    assert result


def test_editorial_risk_keeps_units_modality_and_causality_visible():
    assert editorial_findings(
        "Users may proceed only after 10 days.", "Users must proceed for security."
    )
    assert not editorial_findings(
        "Users may proceed after 10 days.", "After 10 days, users may proceed."
    )
