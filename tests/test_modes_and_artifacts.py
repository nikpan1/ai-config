import sqlite3
from contextlib import closing

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from test_pipeline_restart import FixtureModel

from docgen_graph.storage import ArtifactStore
from docgen_graph.workflow import Pipeline


def build(tmp_path, mode):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text("# Guide\n\nReturn the supplied value.\n", encoding="utf-8")
    template = tmp_path / "template.md"
    template.write_text("## Behavior\n\n## Sources\n", encoding="utf-8")
    store = ArtifactStore(tmp_path / "runtime")
    connection = sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)
    graph = Pipeline(store, FixtureModel(), "example").build(SqliteSaver(connection))
    config = {"configurable": {"thread_id": "example"}}
    inputs = {
        "run_id": "example",
        "docs": str(docs),
        "code": "",
        "template": str(template),
        "brief": "",
        "mode": mode,
        "policy_version": "v2",
        "status": "running",
    }
    return store, connection, graph, config, inputs


def test_manual_review_is_checkpointed_after_each_artifact(tmp_path):
    store, connection, graph, config, inputs = build(tmp_path, "manual")
    with closing(connection):
        graph.invoke(inputs, config)
        first = graph.get_state(config)
        review = first.tasks[0].interrupts[0].value
        assert review["kind"] == "stage"
        assert review["stage"] == "snapshot_inputs"
        assert (store.root / "runs" / "example" / "step1" / "sources.md").is_file()
        assert (store.root / "runs" / "example" / "step1" / "manifest.json").is_file()
        graph.invoke(
            Command(
                resume={
                    "action": "approve",
                    "stage": review["stage"],
                    "item": review["item"],
                    "hash": review["hash"],
                    "reviewer": "Tester",
                    "rationale": "Checked",
                }
            ),
            config,
        )
        second = graph.get_state(config).tasks[0].interrupts[0].value
        assert second["kind"] == "stage"
        assert second["stage"] == "inventory_sources"
        assert second["next"] == "inventory_source_aspects"
        assert not (store.root / "runs" / "example" / "step3").exists()


def test_autopilot_reaches_release_with_attributed_decisions(tmp_path):
    store, connection, graph, config, inputs = build(tmp_path, "autopilot")
    with closing(connection):
        graph.invoke(inputs, config)
        state = graph.get_state(config)
        assert not state.tasks
        assert state.values["status"] == "complete"
        candidate = state.values["candidate_ref"]
        bundle = store.root / "runs" / "example" / "step22" / "candidates" / candidate
        assert (bundle / "candidate-manifest.json").is_file()
        assert (store.root / "runs" / "example" / "step24" / "release.json").is_file()
        plan = store.get(state.values["approval_ref"])
        release = store.get(state.values["release_ref"])
        assert plan["actor_type"] == release["actor_type"] == "policy"


def test_final_receipt_gate_sets_complete_only_after_approval(tmp_path, monkeypatch):
    store = ArtifactStore(tmp_path)
    pipeline = Pipeline(store, None, "receipt")
    record = {
        "stage": "finalize_release",
        "item": "run",
        "hash": "receipt-hash",
        "path": "receipt.md",
    }
    state = {
        "mode": "manual",
        "stage_record": record,
        "route": "__end__",
        "completion_status": "complete",
    }
    monkeypatch.setattr(
        "docgen_graph.workflow.interrupt",
        lambda request: {
            "action": "approve",
            "stage": request["stage"],
            "item": request["item"],
            "hash": request["hash"],
            "reviewer": "Tester",
            "rationale": "Checked receipt",
        },
    )
    update = pipeline.review_stage(state)
    assert update["status"] == "complete"


def test_autopilot_accounts_for_unverified_document_batch(tmp_path):
    store = ArtifactStore(tmp_path)
    pipeline = Pipeline(store, None, "excluded")
    span = {
        "id": "e1",
        "kind": "docs",
        "path": "rules.md",
        "file_hash": "a" * 64,
        "start_line": 4,
        "end_line": 4,
        "text": "An unverified rule.",
    }
    inventory_ref = store.put({"document_batches": [["e1"]], "spans": [span]})
    draft_ref = store.put({"assertions": [], "excluded": []})
    issue_ref = store.put(
        {
            "stage": "verify_document_batch",
            "revision": "issue-1",
            "findings": ["Document blocks lack coverage: ['e1']"],
        }
    )
    state = {
        "mode": "autopilot",
        "policy_version": "v2",
        "issue_ref": issue_ref,
        "inventory_ref": inventory_ref,
        "document_index": 0,
        "draft_ref": draft_ref,
        "assertions_ref": store.put([]),
        "exclusions_ref": store.put([]),
    }
    repair = pipeline.resolve_issues_automatically(state)
    assert repair["status"] == "incomplete"
    records = store.get(repair["unresolved_ref"])
    assert records[0]["path"] == "rules.md"
    assert records[0]["decision_ref"]
    assert store.get(state["exclusions_ref"]) == []
    assert (store.root / "runs" / "excluded" / "unresolved.json").is_file()


def test_autopilot_does_not_exclude_an_ambiguous_entire_batch(tmp_path):
    store = ArtifactStore(tmp_path)
    pipeline = Pipeline(store, None, "unresolved")
    spans = [
        {
            "id": key,
            "kind": "docs",
            "path": "rules.md",
            "file_hash": "a" * 64,
            "start_line": line,
            "end_line": line,
            "text": f"Rule {key}.",
        }
        for key, line in (("e1", 4), ("e2", 5))
    ]
    state = {
        "mode": "autopilot",
        "policy_version": "v2",
        "issue_ref": store.put(
            {
                "stage": "verify_document_batch",
                "revision": "issue-2",
                "findings": ["Independent verification rejected a disputed assertion"],
            }
        ),
        "inventory_ref": store.put({"document_batches": [["e1", "e2"]], "spans": spans}),
        "document_index": 0,
        "draft_ref": store.put({"assertions": [], "excluded": []}),
        "assertions_ref": store.put([]),
        "exclusions_ref": store.put([]),
    }
    result = pipeline.resolve_issues_automatically(state)
    assert result["status"] == "incomplete"
    assert len(store.get(result["unresolved_ref"])) == 2
    assert not (store.root / "runs" / "unresolved" / "exclusions.json").exists()
