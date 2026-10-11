import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "new-approach" / "src"))

from docgen_graph.config import Settings
from docgen_graph.model import GeminiModel
from docgen_graph.storage import ArtifactStore
from docgen_graph.workflow import Pipeline
from langgraph.checkpoint.sqlite import SqliteSaver

run_id = "furniture-new-v5"
plan_hash = "58a987411a92b0e2a5992248f9bd0de11fa9d860aa34ae8a552777c942352285"
settings = Settings.load(None)
store = ArtifactStore(settings.workspace)
pipeline = Pipeline(store, GeminiModel(settings, store, run_id), run_id)
config = {"configurable": {"thread_id": run_id}, "recursion_limit": 100000}

with closing(
    sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)
) as connection:
    graph = pipeline.build(SqliteSaver(connection))
    before = graph.get_state(config)
    assert before.values["status"] == "awaiting_issue_review"
    assert before.values["plan_hash"] == plan_hash
    assert before.values["section_index"] == 0
    assert before.values["unit_index"] == 2
    assert list(before.next) == ["review_issues"]
    issue = store.get(before.values["issue_ref"])
    assert issue["stage"] == "verify_section"
    new_signature = pipeline.runtime_signature()
    assert before.values["runtime_signature"] != new_signature
    updated = graph.update_state(
        config, {"runtime_signature": new_signature}, as_node="verify_section"
    )
    after = graph.get_state(updated)
    assert after.values["plan_hash"] == plan_hash
    assert list(after.next) == ["review_issues"]
    graph.invoke(None, config)
    reviewed = graph.get_state(config)
    assert list(reviewed.next) == ["review_issues"]
    assert reviewed.tasks[0].interrupts
    store.event(
        run_id,
        stage="checkpoint_migration",
        event="support_audit_review_migrated",
        previous_signature=before.values["runtime_signature"],
        new_signature=new_signature,
        previous_checkpoint=before.config["configurable"]["checkpoint_id"],
        new_checkpoint=reviewed.config["configurable"]["checkpoint_id"],
        issue_revision=issue["revision"],
        plan_hash=plan_hash,
    )
    print(
        json.dumps(
            {
                "run_id": run_id,
                "previous_signature": before.values["runtime_signature"],
                "new_signature": new_signature,
                "next": list(reviewed.next),
                "issue": issue,
            },
            indent=2,
        )
    )
