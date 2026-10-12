import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "old-approach" / "src"))

from docgen.cli import run_config
from docgen.config import Settings
from docgen.ingestion import estimate_tokens
from docgen.planning import PlanningPipeline
from docgen.planning_helpers import bounded_groups
from docgen.signatures import runtime_signature
from docgen.storage import Artifacts, encode, read_json, write_json
from docgen.workflow import persistent_graph


run_id = "furniture-old-plan-v4"
settings = Settings()
assert settings.output_tokens == 50000
assert settings.planning_tokens == 40000
store = Artifacts(settings.workspace)
config = run_config(run_id)
metadata_path = store.path(f"runs/{run_id}/workflow.json")
metadata = read_json(metadata_path)
assert metadata["workflow"] == "documentation_planning"
previous_settings = settings.model_copy(update={"planning_tokens": 30000})
previous_signature = runtime_signature(previous_settings, "documentation_planning")
new_signature = runtime_signature(settings, "documentation_planning")
assert previous_signature != new_signature

with persistent_graph(PlanningPipeline(settings, store, None)) as graph:
    before = graph.get_state(config)
    assert before.values["signature"] == previous_signature
    assert metadata["signature"] == previous_signature
    assert before.values["status"] == "running"
    assert before.values["work_key"] == "synthesize_units"
    assert before.values["work_index"] == 2
    assert before.values["synthesis_round"] == 4
    assert list(before.next) == ["discover_documentation_units"]
    assert store.get(before.values["work_ref"])["count"] == 2
    candidates = list(store.iter_table(before.values["candidates_ref"]))
    assert len(candidates) == 88
    assert len(list(bounded_groups(candidates, settings.planning_tokens))) == 1
    estimated_tokens = sum(estimate_tokens(encode(row)) for row in candidates)
    preserved = {
        key: before.values[key]
        for key in (
            "inputs_ref",
            "components_ref",
            "discovery_ref",
            "candidates_ref",
            "candidate_map_ref",
        )
    }
    work_ref = store.put_table(
        [{"id": "0", "candidates": candidates}], "plan-global-synthesis-work"
    )
    updated = graph.update_state(
        config,
        {
            "signature": new_signature,
            "route": "discover_documentation_units",
            "work_ref": work_ref,
            "work_index": 0,
            "results_ref": "",
            "attempt": 0,
            "feedback_ref": "",
            "correction_ref": "",
        },
        as_node="discover_documentation_units",
    )
    after = graph.get_state(updated)
    assert after.values["signature"] == new_signature
    assert list(after.next) == ["discover_documentation_units"]
    assert {key: after.values[key] for key in preserved} == preserved
    assert after.values["work_index"] == 0
    assert after.values["work_ref"] == work_ref
    assert store.get(work_ref)["count"] == 1
    write_json(metadata_path, {**metadata, "signature": new_signature})
    store.event(
        run_id,
        stage="checkpoint_migration",
        event="global_synthesis_requeued",
        previous_signature=previous_signature,
        new_signature=new_signature,
        previous_planning_tokens=30000,
        new_planning_tokens=settings.planning_tokens,
        previous_work_ref=before.values["work_ref"],
        new_work_ref=work_ref,
        candidate_count=len(candidates),
        estimated_candidate_tokens=estimated_tokens,
        synthesis_round=after.values["synthesis_round"],
    )
    print(
        json.dumps(
            {
                "run_id": run_id,
                "candidate_count": len(candidates),
                "estimated_candidate_tokens": estimated_tokens,
                "previous_work_ref": before.values["work_ref"],
                "new_work_ref": work_ref,
                "next": list(after.next),
            },
            indent=2,
        )
    )
