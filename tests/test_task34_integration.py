import sqlite3
from contextlib import closing

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver
from test_pipeline_restart import FixtureModel

from docgen_graph.storage import ArtifactStore
from docgen_graph.workflow import Pipeline


class ToolFixtureModel(FixtureModel):
    def tool_turn(self, payload, messages, declarations):
        self.calls.append("authoring_action")
        if not messages:
            return {
                "content": {
                    "role": "model",
                    "parts": [
                        {
                            "function_call": {
                                "name": "search_original_sources",
                                "args": {"query": "acceptance", "limit": 2},
                                "id": "call-1",
                            },
                            "thought_signature": "AP8=",
                        }
                    ],
                },
                "calls": [
                    {
                        "name": "search_original_sources",
                        "args": {"query": "acceptance", "limit": 2},
                        "id": "call-1",
                    }
                ],
            }
        assert messages[-1]["parts"][0]["function_response"]["response"]["status"] == "ok"
        return {
            "content": {
                "role": "model",
                "parts": [{"text": "The source explicitly requires acceptance."}],
            },
            "calls": [],
        }


@pytest.mark.parametrize(
    "failure_stage", ["execute_authoring_tool", "verify_tool_result", "audit_source_to_document"]
)
def test_tools_resume_at_checkpoint_without_replanning(tmp_path, failure_stage):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "rules.md").write_text(
        "Customer acceptance is required before substitution.\n", encoding="utf-8"
    )
    template = tmp_path / "template.md"
    template.write_text("## Rules\n", encoding="utf-8")
    store = ArtifactStore(tmp_path / "runtime")
    model = ToolFixtureModel()
    config = {"configurable": {"thread_id": "tools"}}
    inputs = {
        "docs": str(docs),
        "template": str(template),
        "run_id": "tools",
        "brief": "",
        "mode": "autopilot",
    }
    with closing(
        sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)
    ) as connection:
        pipeline = Pipeline(store, model, "tools")

        def crash(state):
            raise RuntimeError("Injected checkpoint crash")

        setattr(pipeline, failure_stage, crash)
        graph = pipeline.build(SqliteSaver(connection))
        with pytest.raises(RuntimeError, match="Injected"):
            graph.invoke(inputs, config)
        saved_calls = len(model.calls)
        saved_state = graph.get_state(config).values
        assert saved_state["authoring_ref"]
    with closing(
        sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)
    ) as connection:
        graph = Pipeline(store, model, "tools").build(SqliteSaver(connection))
        graph.invoke(None, config)
        state = graph.get_state(config).values
        assert state["status"] == "complete"
        assert len(model.calls) >= saved_calls
        assert store.get(state["source_coverage_ref"])["complete"]


class MissingConditionModel(FixtureModel):
    def call(self, stage, payload, schema=None):
        if stage == "extract_document":
            return {
                "assertions": [
                    {
                        "statement": "A substitute is proposed.",
                        "subject": "system",
                        "predicate": "proposes",
                        "evidence_ids": [payload["blocks"][0]["id"]],
                    }
                ],
                "excluded": [],
            }
        if stage == "audit_source_coverage":
            return {
                "decisions": [
                    {
                        "aspect_id": aspect["id"],
                        "fact_ids": [],
                        "status": "unresolved",
                        "reason": "Customer acceptance qualifier omitted",
                    }
                    for aspect in payload["aspects"]
                ],
                "findings": [],
            }
        return super().call(stage, payload, schema)


def test_missing_source_qualifier_blocks_autopilot_before_planning(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "rules.md").write_text(
        "A substitute is proposed only after customer acceptance.\n", encoding="utf-8"
    )
    template = tmp_path / "template.md"
    template.write_text("## Rules\n", encoding="utf-8")
    store = ArtifactStore(tmp_path / "runtime")
    model = MissingConditionModel()
    with closing(
        sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)
    ) as connection:
        graph = Pipeline(store, model, "coverage").build(SqliteSaver(connection))
        result = graph.invoke(
            {
                "docs": str(docs),
                "template": str(template),
                "run_id": "coverage",
                "mode": "autopilot",
            },
            {"configurable": {"thread_id": "coverage"}},
        )
    assert result["status"] == "incomplete"
    assert "draft_plan" not in model.calls
    assert store.get(result["exclusions_ref"]) == []
