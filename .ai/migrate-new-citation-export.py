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
old_candidate = "6ab106589c55a0ef45596b4a44a4135bc3e4d345bacdbaef59eb7d150232ed56"
settings = Settings.load(None)
store = ArtifactStore(settings.workspace)
pipeline = Pipeline(store, GeminiModel(settings, store, run_id), run_id)
config = {"configurable": {"thread_id": run_id}, "recursion_limit": 100000}

with closing(
    sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)
) as connection:
    graph = pipeline.build(SqliteSaver(connection))
    before = graph.get_state(config)
    assert before.values["status"] == "ready_for_review"
    assert before.values["plan_hash"] == plan_hash
    assert before.values["candidate_ref"] == old_candidate
    assert list(before.next) == ["review_release"]
    new_signature = pipeline.runtime_signature()
    assert before.values["runtime_signature"] != new_signature
    updated = graph.update_state(
        config,
        {
            "runtime_signature": new_signature,
            "route": "export_candidate",
            "status": "generating",
        },
        as_node="audit_documentation",
    )
    assert list(graph.get_state(updated).next) == ["export_candidate"]
    graph.invoke(None, config)
    after = graph.get_state(config)
    assert after.values["plan_hash"] == plan_hash
    assert after.values["candidate_ref"] != old_candidate
    assert after.values["status"] == "ready_for_review"
    assert list(after.next) == ["review_release"]
    assert after.tasks[0].interrupts
    store.event(
        run_id,
        stage="checkpoint_migration",
        event="citation_export_migrated",
        previous_signature=before.values["runtime_signature"],
        new_signature=new_signature,
        previous_candidate=old_candidate,
        new_candidate=after.values["candidate_ref"],
        plan_hash=plan_hash,
    )
    print(
        json.dumps(
            {
                "run_id": run_id,
                "previous_signature": before.values["runtime_signature"],
                "new_signature": new_signature,
                "previous_candidate": old_candidate,
                "new_candidate": after.values["candidate_ref"],
                "plan_hash": plan_hash,
                "next": list(after.next),
            },
            indent=2,
        )
    )
