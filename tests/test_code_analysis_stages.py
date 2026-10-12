from typing import TypedDict

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from docgen_graph.code_analysis import stages
from docgen_graph.ingestion import inventory
from docgen_graph.knowledge import KnowledgeGraph
from docgen_graph.storage import ArtifactStore


class CodeState(TypedDict, total=False):
    snapshot_ref: str
    inventory_ref: str
    code_scope_ref: str
    code_history_ref: str
    code_provenance_ref: str
    code_relations_ref: str
    code_candidate_ref: str
    draft_ref: str
    verified_code_ref: str
    classified_code_ref: str
    code_classification_verified_ref: str
    assertions_ref: str
    feedback_ref: str
    code_index: int
    attempt: int
    route: str


class OfflineModel:
    def __init__(self):
        self.calls = []
        self.fail_classification = True

    def call(self, stage, payload, schema):
        self.calls.append(stage)
        if stage == "analyze_code":
            return schema.model_validate(
                {
                    "report": "Approval rule",
                    "details": [
                        {
                            "statement": "Approve requires enabled flag",
                            "evidence_ids": [payload["spans"][0]["id"]],
                            "conditions": ["enabled flag"],
                            "source_role": "implementation",
                        }
                    ],
                }
            ).model_dump()
        if stage == "analyze_code_classification":
            return schema.model_validate(
                {
                    "report": "Product rule",
                    "details": [
                        {
                            "id": fact["id"],
                            "audience_scope": "selected audience",
                            "categories": ["PRODUCT_FEATURE", "PRODUCT_CONFIGURATION"],
                            "classification_reason": "Flag controls product action",
                            "relevance": "essential",
                            "relevance_reason": "Required condition for the selected audience",
                            "support_status": "direct",
                        }
                        for fact in payload["facts"]
                    ],
                }
            ).model_dump()
        if stage == "verify_code_classification" and self.fail_classification:
            self.fail_classification = False
            raise RuntimeError("Simulated process restart before audit")
        return schema.model_validate({"accepted": True}).model_dump()


class StagePipeline:
    def __init__(self, root, model):
        self.store = ArtifactStore(root)
        self.graph = KnowledgeGraph(root / "graph.sqlite")
        self.model = model
        self.run_id = "persistent-code"

    def read(self, state, name, default=None):
        return self.store.get(state[name]) if state.get(name) else default

    def call(self, stage, payload, schema):
        return self.model.call(stage, payload, schema)

    def spans(self, state):
        return {span["id"]: span for span in self.read(state, "inventory_ref")["spans"]}

    def assertions(self, state):
        return self.read(state, "assertions_ref", [])

    def repair_limit(self):
        return 1

    def issue(self, state, stage, findings, retry):
        raise AssertionError((stage, findings, retry))


def build(pipeline, saver):
    graph = StateGraph(CodeState)
    previous = START
    for name in stages.CODE_STAGE_NAMES:
        function = getattr(stages, name)
        graph.add_node(name, lambda state, function=function: function(pipeline, state))
        graph.add_edge(previous, name)
        previous = name
    graph.add_edge(previous, END)
    return graph.compile(checkpointer=saver)


def test_code_stages_resume_without_repeating_completed_provider_call(tmp_path):
    model = OfflineModel()
    pipeline = StagePipeline(tmp_path, model)
    source_hash = pipeline.store.put_bytes(b"if (enabled) approve();\n")
    snapshot = {
        "files": [{"kind": "code", "path": "Rule.java", "hash": source_hash}],
        "revision": "fixture",
    }
    snapshot_ref = pipeline.store.put(snapshot)
    source_inventory = inventory(pipeline.store, snapshot)
    pipeline.graph.add_evidence(source_inventory["spans"])
    state = {"snapshot_ref": snapshot_ref, "inventory_ref": pipeline.store.put(source_inventory)}
    config = {"configurable": {"thread_id": "task3-restart"}}
    database = str(tmp_path / "checkpoints.sqlite")
    with SqliteSaver.from_conn_string(database) as saver:
        graph = build(pipeline, saver)
        with pytest.raises(RuntimeError, match="restart"):
            graph.invoke(state, config)
        assert graph.get_state(config).next == ("verify_code_classification",)
    with SqliteSaver.from_conn_string(database) as saver:
        result = build(StagePipeline(tmp_path, model), saver).invoke(None, config)
    facts = pipeline.store.get(result["assertions_ref"])
    assert model.calls.count("analyze_code") == 1
    assert model.calls.count("analyze_code_classification") == 1
    assert facts[0]["categories"] == ["PRODUCT_FEATURE", "PRODUCT_CONFIGURATION"]
    assert facts[0]["conditions"] == ["enabled flag"]
    assert facts[0]["review_status"] == "verified"
    assert facts[0]["provenance_ids"]


def test_primary_fact_can_cite_verified_supporting_context(tmp_path):
    class ContextModel(OfflineModel):
        def call(self, stage, payload, schema):
            response = super().call(stage, payload, schema)
            if stage == "analyze_code":
                response["details"][0]["evidence_ids"].append(payload["context"][0]["id"])
            return response

    model = ContextModel()
    model.fail_classification = False
    pipeline = StagePipeline(tmp_path, model)
    key = pipeline.store.put_bytes(("if (enabled) approve();\n" * 220).encode())
    snapshot = {
        "files": [{"kind": "code", "path": "Rule.java", "hash": key}],
        "revision": "fixture",
    }
    source_inventory = inventory(pipeline.store, snapshot)
    pipeline.graph.add_evidence(source_inventory["spans"])
    state = {
        "snapshot_ref": pipeline.store.put(snapshot),
        "inventory_ref": pipeline.store.put(source_inventory),
    }
    for name in stages.CODE_STAGE_NAMES:
        state.update(getattr(stages, name)(pipeline, state))
    facts = pipeline.store.get(state["assertions_ref"])
    assert len(facts[0]["evidence_ids"]) == 2
    assert facts[0]["review_status"] == "verified"
