import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "old-approach" / "src"))

from docgen.cli import run_config
from docgen.config import Settings
from docgen.planning import PlanningPipeline
from docgen.planning_contracts import UnitDiscovery
from docgen.planning_helpers import require_exact
from docgen.storage import Artifacts, write_json
from docgen.workflow import persistent_graph


run_id = "furniture-old-plan-v4"
response_ref = "objects/response-b94eb151485d9572291a77c3268dc4a03d3b8989890ee37abce49282504d5a90.json"
unexpected_id = "afca8f9f5b6579760919db2a"
settings = Settings()
store = Artifacts(settings.workspace)
pipeline = PlanningPipeline(settings, store, None)
run_path = store.path(f"runs/{run_id}")

with persistent_graph(pipeline) as graph:
    snapshot = graph.get_state(run_config(run_id))
    state = snapshot.values
    assert list(snapshot.next) == ["review_plan"]
    assert state["review_stage"] == "discover_documentation_units"
    assert state["work_index"] == 37
    issues = store.get(state["issues_ref"])
    assert len(issues) == 1
    issue = issues[0]
    assert issue["kind"] == "invalid_planning_artifact"
    assert issue["revision"] == state["review_revision"]
    task = pipeline.current_work(state)
    expected_ids = task["obligation_ids"]
    response = store.get(response_ref)
    raw = response["parsed"] or json.loads(response["candidates"][0]["content"]["parts"][0]["text"])
    original = UnitDiscovery.model_validate(raw)
    actual_ids = [row.obligation_id for row in original.assignments]
    assert set(actual_ids) - set(expected_ids) == {unexpected_id}
    assert set(expected_ids) - set(actual_ids) == set()
    assert len(actual_ids) == len(expected_ids) + 1
    corrected = original.model_copy(
        update={
            "assignments": [
                row for row in original.assignments if row.obligation_id != unexpected_id
            ]
        }
    )
    corrected = UnitDiscovery.model_validate(corrected.model_dump())
    require_exact(
        [row.obligation_id for row in corrected.assignments], expected_ids, "Unit ownership"
    )
    keys = [unit.key for unit in corrected.units]
    require_exact(keys, set(keys), "Candidate unit keys")
    for unit in corrected.units:
        assert set(unit.evidence_obligation_ids) <= set(expected_ids)
        assert unit.purpose and unit.outcome
    obligations = {row["id"]: row for row in pipeline.context(state, expected_ids)["obligations"]}
    for row in corrected.assignments:
        assert row.owner_key in set(keys) | {None}
        assert set(row.consumers) <= set(keys)
        assert row.reason
        expected = obligations[row.obligation_id]["eligibility"]
        if expected != "eligible":
            assert row.disposition == expected
        else:
            assert row.disposition == "included"
    correction_ref = store.put(corrected.model_dump(), "plan-discovery-correction")
    trial = pipeline.discover_documentation_units({**state, "correction_ref": correction_ref})
    assert trial["work_index"] == state["work_index"] + 1
    assert trial["route"] == "discover_documentation_units"
    decision = {
        "decisions": [
            {
                "issue_id": issue["id"],
                "revision": issue["revision"],
                "action": "correct",
                "rationale": "Remove one assignment for an obligation outside this task; preserve all 21 required assignments and the source-backed unit.",
                "reviewer": "user",
                "origin": "reviewer",
                "correction_ref": correction_ref,
            }
        ]
    }
    write_json(run_path / "plan-37-decision.json", decision)
    write_json(
        run_path / "plan-37-correction-proposal.json",
        {
            "run_id": run_id,
            "issue_id": issue["id"],
            "revision": issue["revision"],
            "work_index": state["work_index"],
            "response_ref": response_ref,
            "correction_ref": correction_ref,
            "removed_obligation_id": unexpected_id,
            "expected_assignment_count": len(expected_ids),
            "original_assignment_count": len(actual_ids),
            "corrected_assignment_count": len(corrected.assignments),
            "unit_count": len(corrected.units),
            "validation": "UnitDiscovery schema, source task coverage, ownership scope, eligibility, and planning node trial passed",
            "decision_file": "plan-37-decision.json",
        },
    )
    print(json.dumps({"correction_ref": correction_ref, "issue": issue["id"], "validated": True}))
