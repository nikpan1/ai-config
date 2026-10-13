import json
import sqlite3
import time
from contextlib import closing
from dataclasses import replace

from langgraph.checkpoint.sqlite import SqliteSaver
from test_pipeline_restart import FixtureModel

from docgen_graph.config import Settings
from docgen_graph.storage import ArtifactStore
from docgen_graph.workflow import Pipeline


class FastFixtureModel(FixtureModel):
    def __init__(self, env):
        super().__init__()
        self.settings = replace(
            Settings.load(env), fast_mode=True, minimum_coverage=0.9, source_first=False
        )
        self.batches = []
        self.deadlines = []

    def call_many(self, stage, payloads, schema=None):
        self.batches.append((stage, len(payloads)))
        return [self.call(stage, payload, schema) for payload in payloads]

    def set_deadline(self, deadline):
        self.deadlines.append(deadline)

    def tool_turn(self, payload, messages, declarations):
        raise AssertionError("Fast mode must use the prepared evidence packet")


def fast_inputs(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "registration.md").write_text(
        "# Registration\n\nRegistration requires a verified email address.\n\n"
        + "\n\n".join(f"Registration records preference {index}." for index in range(5)),
        "utf-8",
    )
    (docs / "cancellation.md").write_text(
        "# Cancellation\n\nThe account owner can cancel registration before approval.\n\n"
        + "\n\n".join(f"Cancellation retains audit record {index}." for index in range(5)),
        "utf-8",
    )
    template = tmp_path / "template.md"
    template.write_text("## Behavior\n\n## Sources\n", "utf-8")
    return {
        "run_id": "fast-run",
        "docs": str(docs),
        "template": str(template),
        "brief": "",
        "mode": "autopilot",
        "policy_version": "v2",
        "status": "running",
        "deadline": time.time() + 1200,
    }


def test_fast_pipeline_finishes_with_source_links_and_without_readiness_or_edit_calls(tmp_path):
    model = FastFixtureModel(tmp_path / ".env")
    inputs = fast_inputs(tmp_path)
    store = ArtifactStore(tmp_path / "runtime")
    config = {"configurable": {"thread_id": "fast-run"}, "recursion_limit": 300}
    with closing(sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)) as db:
        graph = Pipeline(store, model, "fast-run").build(SqliteSaver(db))
        result = graph.invoke(inputs, config)
        assert result["status"] == "complete"
        assert not graph.get_state(config).tasks
    assert ("inventory_aspects", 1) in model.batches
    assert ("extract_document", 1) in model.batches
    assert not {"authoring_action", "edit_page", "verify_page"}.intersection(model.calls)
    assert {"verify_section", "audit_source_to_document"}.issubset(model.calls)
    sections = store.get(result["edited_ref"])
    mappings = [mapping for section in sections for mapping in section["mappings"]]
    facts = store.get(result["assertions_ref"])
    assert {mapping["obligation_id"] for mapping in mappings} == {fact["id"] for fact in facts}
    assert all(mapping["citation_ids"] and mapping["support_quotes"] for mapping in mappings)
    bundle = store.root / "runs/fast-run/candidates" / result["candidate_ref"]
    evidence = list((bundle / "evidence").glob("*.md"))
    assert evidence
    pages = list((bundle / "documentation").rglob("*.md"))
    assert pages
    assert any(
        "Registration requires a verified email address." in page.read_text("utf-8")
        for page in pages
    )
    events = [
        json.loads(line)
        for line in (store.root / "runs/fast-run/events.jsonl").read_text("utf-8").splitlines()
    ]
    assert not any(event.get("repair") for event in events)


def test_expired_pipeline_records_terminal_checkpoint_without_model_calls(tmp_path):
    inputs = {**fast_inputs(tmp_path), "deadline": time.time() - 1}
    model = FastFixtureModel(tmp_path / ".env")
    store = ArtifactStore(tmp_path / "runtime")
    config = {"configurable": {"thread_id": "fast-run"}, "recursion_limit": 100}
    checkpoint = store.root / "checkpoints.sqlite"
    with closing(sqlite3.connect(checkpoint, check_same_thread=False)) as db:
        graph = Pipeline(store, model, "fast-run").build(SqliteSaver(db))
        result = graph.invoke(inputs, config)
        assert result["status"] == "timed_out"
        assert not graph.get_state(config).next
    with closing(sqlite3.connect(checkpoint, check_same_thread=False)) as db:
        restarted = Pipeline(store, model, "fast-run").build(SqliteSaver(db))
        persisted = restarted.get_state(config)
        assert persisted.values["deadline"] == inputs["deadline"]
        assert persisted.values["status"] == "timed_out"
        assert not persisted.next
    assert not model.calls
    receipt = json.loads((store.root / "runs/fast-run/runtime-limit.json").read_text("utf-8"))
    assert receipt["stage"] == "snapshot_inputs"
    assert receipt["completed"] is False


def test_resumed_pipeline_preserves_original_deadline(tmp_path, monkeypatch):
    inputs = fast_inputs(tmp_path)
    model = FastFixtureModel(tmp_path / ".env")
    store = ArtifactStore(tmp_path / "runtime")
    config = {"configurable": {"thread_id": "fast-run"}, "recursion_limit": 100}
    checkpoint = store.root / "checkpoints.sqlite"
    with closing(sqlite3.connect(checkpoint, check_same_thread=False)) as db:
        graph = Pipeline(store, model, "fast-run").build(SqliteSaver(db))
        graph.invoke(inputs, config, interrupt_after=["snapshot_inputs"])
        assert graph.get_state(config).values["deadline"] == inputs["deadline"]
    from datetime import UTC, datetime

    class LaterTime:
        @staticmethod
        def now(zone):
            return datetime.fromtimestamp(inputs["deadline"] + 1, UTC)

    monkeypatch.setattr("docgen_graph.workflow.datetime", LaterTime)
    with closing(sqlite3.connect(checkpoint, check_same_thread=False)) as db:
        restarted = Pipeline(store, model, "fast-run").build(SqliteSaver(db))
        result = restarted.invoke(None, config)
        assert result["deadline"] == inputs["deadline"]
        assert result["status"] == "timed_out"
        assert not restarted.get_state(config).next
    assert not model.calls


def test_model_timeout_becomes_terminal_pipeline_result(tmp_path, monkeypatch):
    inputs = fast_inputs(tmp_path)
    model = FastFixtureModel(tmp_path / ".env")

    def timeout(*args, **kwargs):
        raise TimeoutError("Request exceeded remaining run time")

    monkeypatch.setattr(model, "call_many", timeout)
    store = ArtifactStore(tmp_path / "runtime")
    config = {"configurable": {"thread_id": "fast-run"}, "recursion_limit": 100}
    with closing(sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)) as db:
        graph = Pipeline(store, model, "fast-run").build(SqliteSaver(db))
        result = graph.invoke(inputs, config)
        assert result["status"] == "timed_out"
        assert not graph.get_state(config).next
    receipt = json.loads((store.root / "runs/fast-run/runtime-limit.json").read_text("utf-8"))
    assert receipt["stage"] == "inventory_source_aspects"
