import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "old-approach" / "src"))

from docgen.cli import run_config
from docgen.config import Settings
from docgen.model import GeminiModel
from docgen.signatures import runtime_signature
from docgen.storage import Artifacts, read_json, run_lock, write_json
from docgen.workflow import Pipeline, persistent_graph

run_id = "furniture-old-knowledge-v2"
expected_revision = "objects/entity-comparison-ab4f5d0346a8bce25d56d8c36736ef48cfdb2e9040da3266ccaab521c3a2e7b1.json"
settings = Settings(_env_file=".env")
store = Artifacts(settings.workspace)
pipeline = Pipeline(settings, store, GeminiModel(settings, store, run_id))
config = run_config(run_id)
new_signature = runtime_signature(settings, "knowledge")

with run_lock(store, run_id), persistent_graph(pipeline) as graph:
    before = graph.get_state(config)
    values = before.values
    assert values["status"] == "review"
    assert values["review_stage"] == "reconcile_entities"
    assert values["review_revision"] == expected_revision
    assert list(before.next) == ["review_issues"]
    assert not values.get("manual_comparison_ref")
    assert values["signature"] != new_signature
    updated = graph.update_state(config, {"signature": new_signature}, as_node="reconcile_entities")
    after = graph.get_state(updated)
    assert after.values["signature"] == new_signature
    assert after.values["review_revision"] == expected_revision
    assert list(after.next) == ["review_issues"]
    metadata_path = store.path(f"runs/{run_id}/workflow.json")
    metadata = read_json(metadata_path)
    assert metadata["workflow"] == "knowledge"
    metadata["signature"] = new_signature
    write_json(metadata_path, metadata)
    store.event(
        run_id,
        stage="checkpoint_migration",
        event="review_checkpoint_migrated",
        previous_signature=values["signature"],
        new_signature=new_signature,
        previous_checkpoint=before.config["configurable"]["checkpoint_id"],
        new_checkpoint=after.config["configurable"]["checkpoint_id"],
        review_revision=expected_revision,
    )
    print(
        json.dumps(
            {
                "run_id": run_id,
                "previous_signature": values["signature"],
                "new_signature": new_signature,
                "previous_checkpoint": before.config["configurable"]["checkpoint_id"],
                "new_checkpoint": after.config["configurable"]["checkpoint_id"],
                "next": list(after.next),
                "review_revision": after.values["review_revision"],
            },
            indent=2,
        )
    )
