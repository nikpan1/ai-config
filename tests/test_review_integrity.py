import pytest
from conftest import FixtureModel
from langgraph.types import Command
from test_pipeline import config, initial

from docgen.contracts import Finding
from docgen.review import validate_decisions
from docgen.validation import validate_duplicate_chains
from docgen.workflow import Pipeline, persistent_graph


def test_conflict_decision_preserves_rejected_claims(tmp_path, settings, store):
    def transform(stage, payload, result):
        if stage == "extract":
            result.findings = [
                Finding(
                    kind="conflict",
                    description="Contradictory fixture rules",
                    block_ids=[item["id"] for item in payload["owned"]],
                    record_ids=[claim.id for claim in result.claims],
                )
            ]
        return result

    model = FixtureModel(transform)
    with persistent_graph(Pipeline(settings, store, model)) as graph:
        graph.invoke(initial(tmp_path), config())
        issue = graph.get_state(config()).interrupts[0].value["issues"][0]
        selected = issue["record_ids"][0]
        assert ":" in selected
        decision = {
            "issue_id": issue["id"],
            "revision": issue["revision"],
            "action": "select_authority",
            "claim_ids": [selected],
            "reviewer": "automated fixture",
            "rationale": "Exercise authority selection",
        }
        result = graph.invoke(Command(resume={"decisions": [decision]}), config())
    bundle = store.get(result["bundle_ref"])
    assert len(bundle["claims"]) == 2
    eligible = [claim for claim in bundle["claims"] if claim["review_status"] != "ineligible"]
    assert [claim["id"] for claim in eligible] == [selected]
    assert len(bundle["resolved_issues"]) == 1


def test_final_integrity_cannot_be_waived():
    issue = {"id": "i1", "revision": "r1", "kind": "source_issue", "stage": "finalize_knowledge"}
    decision = {
        "issue_id": "i1",
        "revision": "r1",
        "action": "acknowledge_unknown",
        "reviewer": "fixture",
        "rationale": "Acknowledge",
    }
    with pytest.raises(ValueError, match="cannot be waived"):
        validate_decisions([decision], [issue], "r1")


def test_duplicate_cycles_cannot_satisfy_coverage():
    first = {"block_id": "a", "disposition": "duplicate", "duplicate_of": "b"}
    second = {"block_id": "b", "disposition": "duplicate", "duplicate_of": "a"}
    assert not validate_duplicate_chains([first, second])
    second["disposition"] = "represented"
    assert validate_duplicate_chains([first, second])
