import json
import sqlite3
from contextlib import closing
from types import SimpleNamespace

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver

from docgen_graph.cli import parser
from docgen_graph.ingestion import document_spans
from docgen_graph.knowledge import normalized_assertion
from docgen_graph.semantic_graph import semantic_records
from docgen_graph.storage import ArtifactStore, digest
from docgen_graph.workflow import Pipeline

SOURCE = (
    "Registration requires all conditions: a valid email and accepted terms. "
    "Invited users are exempt from accepting terms."
)
CONDITIONS = ["a valid email", "accepted terms"]
EXCEPTION = "Invited users are exempt from accepting terms."


class GraphModel:
    def __init__(self, corrupt_logic=False, missing_audit_coverage=False):
        self.settings = SimpleNamespace(content_repair_limit=1)
        self.calls = []
        self.corrupt_logic = corrupt_logic
        self.missing_audit_coverage = missing_audit_coverage

    def call(self, stage, payload, schema=None):
        self.calls.append((stage, payload))
        if stage == "inventory_aspects":
            return {
                "aspects": [
                    {
                        "evidence_id": block["id"],
                        "quote": block["text"],
                        "kind": "obligation",
                        "description": block["text"],
                    }
                    for block in payload["blocks"]
                ],
                "non_substantive": [],
            }
        if stage == "extract_document":
            return {
                "assertions": [
                    {
                        "statement": block["text"],
                        "evidence_ids": [block["id"]],
                        "subject": "User registration",
                        "predicate": "requires",
                        "scope": "Customer portal",
                        "modality": "necessary",
                        "conditions": CONDITIONS,
                        "exceptions": [EXCEPTION],
                    }
                    for block in payload["blocks"]
                ],
                "excluded": [],
            }
        if stage == "verify_document":
            return {"accepted": True, "findings": []}
        if stage == "audit_source_coverage":
            return {
                "decisions": [
                    {
                        "aspect_id": aspect["id"],
                        "fact_ids": [
                            fact["id"]
                            for fact in payload["facts"]
                            if aspect["evidence_id"] in fact["evidence_ids"]
                        ],
                        "status": "represented",
                        "reason": "All fixture requirements and exceptions are retained",
                    }
                    for aspect in payload["aspects"]
                ],
                "findings": [],
            }
        if stage == "semantic_graph":
            source = payload["sources"][0]

            def quote(text):
                start = source["text"].index(text)
                return {
                    "evidence_id": source["id"],
                    "start": start,
                    "end": start + len(text),
                    "text": text,
                }

            return {
                "topics": [
                    {
                        "key": "registration",
                        "name": "User registration",
                        "scope": "Customer portal",
                        "quotes": [quote("Registration")],
                    }
                ],
                "rules": [
                    {
                        "key": "eligibility",
                        "topic_key": "registration",
                        "statement": payload["facts"][0]["statement"],
                        "scope": "Customer portal",
                        "modality": "necessary",
                        "fact_ids": [fact["id"] for fact in payload["facts"]],
                        "quotes": [quote(SOURCE)],
                        "topic_quotes": [quote("Registration")],
                        "condition_groups": [
                            {
                                "operator": "any" if self.corrupt_logic else "all",
                                "quotes": [quote("requires all conditions")],
                                "conditions": [
                                    {"statement": condition, "quotes": [quote(condition)]}
                                    for condition in CONDITIONS
                                ],
                            }
                        ],
                        "exceptions": [{"statement": EXCEPTION, "quotes": [quote(EXCEPTION)]}],
                    }
                ],
                "findings": [],
            }
        if stage == "audit_semantic_graph":
            accepted = all(
                group["operator"] == "all"
                for rule in payload["draft"]["rules"]
                for group in rule["condition_groups"]
            )
            return {
                "accepted": accepted,
                "findings": []
                if accepted
                else ["Source requires all conditions, not alternatives"],
                "covered_obligation_ids": []
                if self.missing_audit_coverage
                else [fact["id"] for fact in payload["facts"]],
            }
        raise AssertionError(f"Unexpected document-generation stage: {stage}")


def initial_state(tmp_path):
    document = tmp_path / "registration.md"
    document.write_text(SOURCE, encoding="utf-8")
    return {
        "run_id": "graph-test",
        "docs": str(document),
        "graph_only": True,
        "brief": "",
        "mode": "autopilot",
    }


def build_pipeline(tmp_path, model, stop_at=None):
    store = ArtifactStore(tmp_path / "runtime")
    pipeline = Pipeline(store, model, "graph-test")
    if stop_at:

        def crash(state):
            raise RuntimeError("Simulated process restart")

        setattr(pipeline, stop_at, crash)
    connection = sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)
    graph = pipeline.build(SqliteSaver(connection))
    return store, pipeline, connection, graph


@pytest.mark.parametrize(
    "stop_at", ["audit_semantic_graph", "publish_semantic_graph", "finalize_graph"]
)
def test_graph_only_resumes_persistent_semantic_checkpoints_without_replaying_model_calls(
    tmp_path, stop_at
):
    model = GraphModel()
    config = {"configurable": {"thread_id": "graph-test"}, "recursion_limit": 150}
    store, _, connection, graph = build_pipeline(tmp_path, model, stop_at)
    with closing(connection):
        with pytest.raises(RuntimeError, match="Simulated process restart"):
            graph.invoke(initial_state(tmp_path), config)
        saved = graph.get_state(config)
        assert saved.next == (stop_at,)
        assert saved.values["semantic_draft_ref"]
        if stop_at != "audit_semantic_graph":
            assert saved.values["semantic_audit_ref"]
        before = [stage for stage, _ in model.calls]
    _, _, connection, graph = build_pipeline(tmp_path, model)
    with closing(connection):
        result = graph.invoke(None, config)
        assert result["status"] == "graph_complete"
        assert not graph.get_state(config).next
        stages = {
            snapshot.values.get("stage_record", {}).get("stage")
            for snapshot in graph.get_state_history(config)
        }
        assert {
            "propose_semantic_graph",
            "audit_semantic_graph",
            "publish_semantic_graph",
        } <= stages
        assert "compile_template" not in stages
        after = [stage for stage, _ in model.calls]
        assert after.count("semantic_graph") == before.count("semantic_graph") == 1
        assert after.count("audit_semantic_graph") == 1
        assert after.count("extract_document") == 1
        assert "template" not in result
        assert "plan_ref" not in result
        quality = json.loads((store.root / "runs/graph-test/graph-quality.json").read_text())
        assert quality["accepted"]
        assert quality["source_coverage"]["graph_revision"] == result["graph_revision"]
        assert (store.root / "graphs" / result["graph_revision"] / "graph.sqlite").is_file()


@pytest.mark.parametrize("failure", ["incorrect_logic", "uncovered_fact"])
def test_independent_semantic_audit_blocks_publication_after_bounded_retries(tmp_path, failure):
    model = GraphModel(
        corrupt_logic=failure == "incorrect_logic",
        missing_audit_coverage=failure == "uncovered_fact",
    )
    store, pipeline, connection, graph = build_pipeline(tmp_path, model)
    config = {"configurable": {"thread_id": "graph-test"}, "recursion_limit": 150}
    with closing(connection):
        graph.invoke(initial_state(tmp_path), config)
        state = graph.get_state(config)
        assert state.values["status"] == "incomplete"
        assert not state.next
        issue = store.get(state.values["issue_ref"])
        assert issue["stage"] == "audit_semantic_graph"
        assert semantic_records(pipeline.graph) == ([], [])
        assert "graph_revision" not in state.values
        stages = [stage for stage, _ in model.calls]
        assert stages.count("semantic_graph") == 2
        assert stages.count("audit_semantic_graph") == 2


def context_state(tmp_path, model):
    store = ArtifactStore(tmp_path / "runtime")
    pipeline = Pipeline(store, model, "context-test")
    text = SOURCE + " " * (8000 - len(SOURCE)) + "Additional source context. " + SOURCE
    spans = document_spans({"kind": "docs", "path": "source.md", "hash": digest(text)}, text)
    owned, context = spans
    inventory = {
        "spans": spans,
        "document_batches": [[owned["id"]]],
        "document_context_batches": [{"context_block_ids": [context["id"]]}],
    }
    state = {"inventory_ref": store.put(inventory), "document_index": 0, "attempt": 1}
    return pipeline, state, owned, context


def test_extracted_fact_cannot_claim_only_context_sources(tmp_path):
    model = GraphModel()
    pipeline, state, owned, context = context_state(tmp_path, model)
    state["draft_ref"] = pipeline.store.put(
        {
            "assertions": [{"statement": SOURCE, "evidence_ids": [context["id"]]}],
            "excluded": [
                {"evidence_id": owned["id"], "reason": "Invalid fixture omits owned source"}
            ],
        }
    )
    result = pipeline.verify_document_batch(state)
    issue = pipeline.store.get(result["issue_ref"])
    assert any("owned source block" in finding for finding in issue["findings"])
    assert model.calls == []


def test_source_context_reaches_extraction_and_independent_source_audits(tmp_path):
    model = GraphModel()
    pipeline, state, owned, context = context_state(tmp_path, model)
    state["source_aspect_index"] = 0
    pipeline.inventory_source_aspects(state)
    extracted = pipeline.extract_document_batch(state)
    state.update(extracted)
    pipeline.verify_document_batch(state)
    fact = normalized_assertion(
        {"statement": SOURCE, "evidence_ids": [owned["id"], context["id"]]},
        {owned["id"], context["id"]},
    )
    state["pending_document_ref"] = pipeline.store.put({"records": [fact], "excluded": []})
    pipeline.audit_source_coverage(state)
    stages = {stage: payload for stage, payload in model.calls}
    for stage in (
        "inventory_aspects",
        "extract_document",
        "verify_document",
        "audit_source_coverage",
    ):
        assert stages[stage]["context_blocks"] == [context]
        assert stages[stage]["blocks"] == [owned]


def test_graph_only_cli_accepts_documents_without_template():
    arguments = parser().parse_args(
        ["run", "--docs", "source.md", "--thread-id", "graph-test", "--graph-only"]
    )
    assert arguments.graph_only
    assert arguments.template is None


def test_graph_freeze_rejects_missing_semantic_fact_allocation(tmp_path):
    model = GraphModel()
    store, pipeline, connection, graph = build_pipeline(tmp_path, model, "propose_semantic_graph")
    config = {"configurable": {"thread_id": "graph-test"}, "recursion_limit": 150}
    with closing(connection):
        with pytest.raises(RuntimeError, match="Simulated process restart"):
            graph.invoke(initial_state(tmp_path), config)
        state = graph.get_state(config).values
        result = pipeline.finalize_graph(state)
        assert "graph_revision" not in result
        issue = store.get(result["issue_ref"])
        assert any("no semantic rule" in finding for finding in issue["findings"])
