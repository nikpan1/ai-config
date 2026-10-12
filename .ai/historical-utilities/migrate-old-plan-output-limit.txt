import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "old-approach" / "src"))

from docgen.cli import run_config
from docgen.config import Settings
from docgen.planning import PlanningPipeline
from docgen.signatures import runtime_signature
from docgen.storage import Artifacts, read_json, write_json
from docgen.workflow import persistent_graph


run_id = "furniture-old-plan-v4"
settings = Settings()
assert settings.output_tokens == 50000
store = Artifacts(settings.workspace)
config = run_config(run_id)
metadata_path = store.path(f"runs/{run_id}/workflow.json")
metadata = read_json(metadata_path)
assert metadata["workflow"] == "documentation_planning"
previous_settings = settings.model_copy(update={"output_tokens": 24000})
previous_signature = runtime_signature(previous_settings, "documentation_planning")
new_signature = runtime_signature(settings, "documentation_planning")
assert previous_signature != new_signature

with persistent_graph(PlanningPipeline(settings, store, None)) as graph:
    before = graph.get_state(config)
    assert before.values["signature"] == previous_signature
    assert metadata["signature"] == previous_signature
    assert before.values["status"] == "running"
    assert before.values["work_key"] == "synthesize_units"
    assert before.values["work_index"] == 0
    assert before.values["synthesis_round"] == 1
    assert list(before.next) == ["discover_documentation_units"]
    preserved = {
        key: before.values[key]
        for key in ("inputs_ref", "components_ref", "discovery_ref", "candidates_ref", "work_ref")
    }
    updated = graph.update_state(
        config,
        {"signature": new_signature, "route": "discover_documentation_units"},
        as_node="discover_documentation_units",
    )
    after = graph.get_state(updated)
    assert after.values["signature"] == new_signature
    assert list(after.next) == ["discover_documentation_units"]
    assert {key: after.values[key] for key in preserved} == preserved
    assert after.values["work_index"] == 0
    write_json(metadata_path, {**metadata, "signature": new_signature})
    store.event(
        run_id,
        stage="checkpoint_migration",
        event="planning_output_limit_increased",
        previous_signature=previous_signature,
        new_signature=new_signature,
        previous_output_tokens=24000,
        new_output_tokens=settings.output_tokens,
        work_ref=preserved["work_ref"],
        work_index=after.values["work_index"],
        synthesis_round=after.values["synthesis_round"],
    )
    print(
        json.dumps(
            {
                "run_id": run_id,
                "previous_signature": previous_signature,
                "new_signature": new_signature,
                "next": list(after.next),
                "work_ref": preserved["work_ref"],
                "work_index": after.values["work_index"],
            },
            indent=2,
        )
    )
