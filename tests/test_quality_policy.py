import pytest

from docgen_graph.quality_policy import coverage_audit_findings, evaluate_coverage
from docgen_graph.source_coverage import audit_decisions, coverage_report, source_audit_findings


def source_records(count=10):
    aspects = [
        {
            "id": f"a{index}",
            "evidence_id": f"e{index}",
            "kind": "condition" if index == count - 1 else "obligation",
            "quote": f"Original source statement {index}",
        }
        for index in range(count)
    ]
    facts = [{"id": f"f{index}", "evidence_ids": [f"e{index}"]} for index in range(count)]
    decisions = [
        {
            "aspect_id": aspect["id"],
            "status": "represented",
            "fact_ids": [facts[index]["id"]],
            "reason": "Verified against source",
        }
        for index, aspect in enumerate(aspects)
    ]
    return aspects, facts, decisions


def report(aspects, facts, decisions, **kwargs):
    return coverage_report(
        aspects, decisions, {fact["id"] for fact in facts}, "snapshot", "revision", [], **kwargs
    )


def test_exact_ninety_percent_accepts_explicit_omission_without_claiming_completeness():
    aspects, facts, decisions = source_records()
    decisions[-1].update(status="unresolved", fact_ids=[], reason="Not retained in final prose")
    result = report(aspects, facts, decisions, minimum_coverage=0.9)
    assert result["accepted"]
    assert not result["complete"]
    assert result["coverage_ratio"] == 0.9
    assert result["omitted_aspects"] == [
        {**aspects[-1], "reason": "Not retained in final prose", "fact_ids": []}
    ]
    assert result["qualifiers"]["coverage_ratio"] == 0
    assert not audit_decisions(aspects, decisions, facts, minimum_coverage=0.9)
    assert audit_decisions(aspects, decisions, facts)
    assert not report(aspects, facts, decisions)["accepted"]


@pytest.mark.parametrize("total, retained", [(3, 2), (9, 8), (19, 17), (1000, 899)])
def test_coverage_threshold_does_not_round_up(total, retained):
    result = evaluate_coverage(map(str, range(total)), map(str, range(retained)), 0.9)
    assert not result["accepted"]


def test_duplicate_decisions_cannot_inflate_reported_coverage():
    aspects, facts, decisions = source_records()
    decisions[-1] = decisions[0]
    result = report(aspects, facts, decisions, minimum_coverage=0.9)
    assert result["aspects"]["represented"] == 9
    assert not result["accepted"]
    assert result["integrity_findings"]
    assert audit_decisions(aspects, decisions, facts, minimum_coverage=0.9)


def test_omissions_require_explicit_decisions():
    aspects, facts, decisions = source_records()
    assert not report(aspects, facts, decisions[:-1], minimum_coverage=0.9)["accepted"]


def test_foreign_decision_cannot_count_as_source_information():
    aspects, facts, decisions = source_records()
    decisions[-1]["aspect_id"] = "invented"
    result = report(aspects, facts, decisions, minimum_coverage=0.9)
    assert result["aspects"]["represented"] == 9
    assert not result["accepted"]


def test_invalid_source_mapping_stays_a_blocker_even_at_ninety_percent():
    aspects, facts, decisions = source_records()
    decisions[-1]["fact_ids"] = [facts[0]["id"]]
    assert audit_decisions(aspects, decisions, facts, minimum_coverage=0.9) == [
        "Aspect mapping lacks its original source: a9"
    ]


def test_unknown_disposition_stays_a_blocker_even_without_facts():
    aspects, facts, decisions = source_records()
    decisions[-1].update(status="excluded", fact_ids=[])
    assert audit_decisions(aspects, decisions, facts, minimum_coverage=0.9) == [
        "Unknown source aspect disposition: a9"
    ]
    assert not report(aspects, facts, decisions, minimum_coverage=0.9)["accepted"]


def test_unresolved_attachments_are_not_covered_by_text_omission_allowance():
    aspects, facts, decisions = source_records()
    result = coverage_report(
        aspects,
        decisions,
        {fact["id"] for fact in facts},
        "snapshot",
        "revision",
        [{"path": "diagram.png", "status": "unresolved"}],
        minimum_coverage=0.9,
    )
    assert not result["accepted"]
    assert result["coverage_ratio"] == 1


def test_empty_inventory_has_defined_coverage_without_division_by_zero():
    result = report([], [], [], minimum_coverage=0.9)
    assert result["accepted"] and result["complete"]
    assert result["coverage_ratio"] == 1


def test_tolerance_never_suppresses_free_form_semantic_audit_findings():
    findings = [
        "Unresolved source aspect: a9",
        "The source condition is missing and the resulting claim is too broad",
        "Unsupported source citation: e9",
        "Unresolved source aspect: another",
    ]
    assert coverage_audit_findings(findings, ["a9"], accepted=True) == findings[1:]
    assert coverage_audit_findings(findings, ["a9"], accepted=False) == findings


@pytest.mark.parametrize("threshold", [0, -0.1, 1.01, float("nan"), float("inf")])
def test_invalid_coverage_threshold_fails_explicitly(threshold):
    with pytest.raises(ValueError, match="Minimum coverage"):
        evaluate_coverage([], [], threshold)


def test_repeated_identifiers_do_not_inflate_the_policy_denominator():
    result = evaluate_coverage(["a"] * 9 + ["b"], ["a"], 0.9)
    assert result["total"] == 2
    assert result["coverage_ratio"] == 0.5
    assert not result["accepted"]


def test_batch_omission_uses_global_allowance_without_charging_unaudited_aspects():
    aspects, facts, decisions = source_records()
    decisions[0].update(status="unresolved", fact_ids=[])
    assert not source_audit_findings(
        aspects[:1],
        decisions[:1],
        facts[:1],
        all_aspects=aspects,
        prior_decisions=[],
        minimum_coverage=0.9,
    )


def test_global_omission_allowance_cannot_be_reused_in_the_next_batch():
    aspects, facts, decisions = source_records()
    decisions[0].update(status="unresolved", fact_ids=[])
    decisions[1].update(status="unresolved", fact_ids=[])
    assert source_audit_findings(
        aspects[1:2],
        decisions[1:2],
        facts[1:2],
        all_aspects=aspects,
        prior_decisions=decisions[:1],
        minimum_coverage=0.9,
    ) == ["Unresolved source aspect: a1"]


def test_global_allowance_preserves_source_mapping_errors():
    aspects, facts, decisions = source_records()
    decisions[0]["fact_ids"] = ["unknown"]
    assert source_audit_findings(
        aspects[:1],
        decisions[:1],
        facts[:1],
        all_aspects=aspects,
        prior_decisions=[],
        minimum_coverage=0.9,
    ) == ["Aspect mapping lacks its original source: a0"]


def test_global_allowance_does_not_hide_missing_batch_accounting():
    aspects, facts, _ = source_records()
    assert source_audit_findings(
        aspects[:1],
        [],
        facts[:1],
        all_aspects=aspects,
        prior_decisions=[],
        minimum_coverage=0.9,
    ) == ["Source audit must account for every aspect exactly once"]


def test_global_allowance_rejects_repeated_batch_accounting():
    aspects, facts, decisions = source_records()
    assert source_audit_findings(
        aspects[:1],
        decisions[:1],
        facts[:1],
        all_aspects=aspects,
        prior_decisions=decisions[:1],
        minimum_coverage=0.9,
    ) == ["Source audit batches must account for distinct original aspects"]
