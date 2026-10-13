import sqlite3
from contextlib import closing
from dataclasses import replace

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from test_source_first_completion import SourceModel, run_inputs

from docgen_graph.storage import ArtifactStore
from docgen_graph.workflow import Pipeline


def decision(result, action="approve", **overrides):
    record = result["__interrupt__"][0].value
    return Command(
        resume={
            "stage": record["stage"],
            "item": record["item"],
            "hash": record["hash"],
            "action": action,
            "reviewer": "business-owner",
            "rationale": "The scope and source-grounded content match the requested purpose.",
            **overrides,
        }
    )


def test_manual_source_first_has_only_plan_and_final_review_across_restart(tmp_path):
    model = SourceModel(tmp_path / ".env")
    inputs = {**run_inputs(tmp_path), "mode": "manual"}
    store = ArtifactStore(tmp_path / "runtime")
    config = {"configurable": {"thread_id": "source-run"}, "recursion_limit": 150}
    database = store.root / "checkpoints.sqlite"
    with closing(sqlite3.connect(database, check_same_thread=False)) as db:
        graph = Pipeline(store, model, "source-run").build(SqliteSaver(db))
        plan = graph.invoke(inputs, config)
        assert plan["__interrupt__"][0].value["stage"] == "plan_source_document"
        assert "source_document" not in model.calls
    preparation_calls = list(model.calls)
    with closing(sqlite3.connect(database, check_same_thread=False)) as db:
        graph = Pipeline(store, model, "source-run").build(SqliteSaver(db))
        final = graph.invoke(decision(plan), config)
        assert final["__interrupt__"][0].value["stage"] == "finalize_source_document"
        assert final["status"] == "awaiting_manual_review"
        assert final["deadline"] == inputs["deadline"]
        assert model.calls[: len(preparation_calls)] == preparation_calls
        before_approval = list(model.calls)
        result = graph.invoke(decision(final), config)
        assert result["status"] == result["completion_status"]
        assert not graph.get_state(config).next
        assert model.calls == before_approval


def test_manual_review_rejects_stale_approval_and_can_reject_document(tmp_path):
    model = SourceModel(tmp_path / ".env")
    store = ArtifactStore(tmp_path / "runtime")
    config = {"configurable": {"thread_id": "source-run"}, "recursion_limit": 150}
    with closing(sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)) as db:
        graph = Pipeline(store, model, "source-run").build(SqliteSaver(db))
        plan = graph.invoke({**run_inputs(tmp_path), "mode": "manual"}, config)
        stale = graph.invoke(decision(plan, hash="wrong-hash"), config)
        assert stale["__interrupt__"][0].value["stage"] == "plan_source_document"
        assert "source_document" not in model.calls
        final = graph.invoke(decision(stale), config)
        assert final["__interrupt__"][0].value["stage"] == "finalize_source_document"
        rejected = graph.invoke(decision(final, action="reject"), config)
        assert rejected["status"] == "rejected"
        assert not graph.get_state(config).next


def test_legacy_manual_still_reviews_first_technical_stage(tmp_path):
    model = SourceModel(tmp_path / ".env")
    model.settings = replace(model.settings, source_first=False)
    store = ArtifactStore(tmp_path / "runtime")
    config = {"configurable": {"thread_id": "source-run"}, "recursion_limit": 150}
    with closing(sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)) as db:
        graph = Pipeline(store, model, "source-run").build(SqliteSaver(db))
        result = graph.invoke({**run_inputs(tmp_path), "mode": "manual"}, config)
        assert result["__interrupt__"][0].value["stage"] == "snapshot_inputs"
        assert model.calls == []


def test_manual_document_correction_preserves_preparation_and_original_deadline(tmp_path):
    model = SourceModel(tmp_path / ".env")
    store = ArtifactStore(tmp_path / "runtime")
    inputs = {**run_inputs(tmp_path), "mode": "manual"}
    config = {"configurable": {"thread_id": "source-run"}, "recursion_limit": 150}
    with closing(sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)) as db:
        graph = Pipeline(store, model, "source-run").build(SqliteSaver(db))
        plan = graph.invoke(inputs, config)
        final = graph.invoke(decision(plan), config)
        corrected = graph.invoke(
            decision(final, action="request_correction", rationale="Explain the guest exception."),
            config,
        )
        assert corrected["__interrupt__"][0].value["stage"] == "finalize_source_document"
        assert corrected["status"] == "awaiting_manual_review"
        assert corrected["deadline"] == inputs["deadline"]
        assert model.calls.count("source_plan") == 1
        assert model.calls.count("extract_document") == 1
        assert model.calls.count("source_document") == 2
        assert store.get(corrected["feedback_ref"]) == ["Explain the guest exception."]


def test_manual_graph_failure_recovers_without_extra_human_gate(tmp_path):
    model = SourceModel(tmp_path / ".env", fail_stage="semantic_graph")
    store = ArtifactStore(tmp_path / "runtime")
    config = {"configurable": {"thread_id": "source-run"}, "recursion_limit": 150}
    with closing(sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)) as db:
        graph = Pipeline(store, model, "source-run").build(SqliteSaver(db))
        plan = graph.invoke({**run_inputs(tmp_path), "mode": "manual"}, config)
        assert plan["__interrupt__"][0].value["stage"] == "plan_source_document"
        final = graph.invoke(decision(plan), config)
        assert final["__interrupt__"][0].value["stage"] == "finalize_source_document"
        assert final["completion_status"] == "complete_with_limitations"
