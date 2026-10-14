import json
import sqlite3
from contextlib import closing
from copy import deepcopy
from dataclasses import replace

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver
from test_source_first_completion import SourceModel, execute, run_inputs
from test_source_first_manual import decision

from docgen_graph.completion import document_content_hash
from docgen_graph.config import Settings
from docgen_graph.editorial import apply_editorial_revision, revision_accepted, revision_findings
from docgen_graph.model import response_schema
from docgen_graph.planning import SourcePlan
from docgen_graph.storage import ArtifactStore
from docgen_graph.workflow import Pipeline


class EditorialModel(SourceModel):
    def __init__(self, path, *, regression=False, remaining=False, unknown=False):
        super().__init__(path)
        self.settings = replace(self.settings, editorial_review=True)
        self.regression = regression
        self.remaining = remaining
        self.unknown = unknown
        self.verified = 0

    def finding(self, document):
        section = document["sections"][0]
        return {
            "section_id": section["id"],
            "paragraph_id": section["paragraphs"][0]["id"],
            "category": "clarity",
            "explanation": "Use a concise, explicit exception.",
            "requested_change": "Improve readability without changing the exception.",
            "sources": [],
        }

    def call(self, stage, payload, schema=None):
        if stage == "source_editorial":
            self.calls.append(stage)
            return {"findings": [self.finding(payload["document"])], "summary": "One improvement"}
        if stage == "source_revision":
            self.calls.append(stage)
            original = payload["document"]["sections"][0]["paragraphs"][0]
            paragraph = {
                **original,
                "text": "Registration requires email verification; temporary guests are exempt."
                + " " * self.verified,
            }
            return {
                "paragraphs": [
                    {
                        "paragraph_id": "unknown" if self.unknown else original["id"],
                        "paragraph": paragraph,
                    }
                ],
                "additions": [],
                "visuals": [],
            }
        if stage == "verify_source_revision":
            self.calls.append(stage)
            self.verified += 1
            return {
                "preserves_supported_information": not self.regression,
                "no_new_unsupported_claims": True,
                "resolves_requested_changes": True,
                "explanation": "Controlled test of revision routing",
                "lost_or_changed_information": ["An exception was lost"] if self.regression else [],
                "remaining_editorial_findings": [self.finding(payload["candidate"])]
                if self.remaining
                else [],
                "audit": {
                    "accepted": True,
                    "findings": [],
                    "coverage_estimate": 1,
                    "coverage_explanation": "Controlled fixture",
                },
            }
        return super().call(stage, payload, schema)


def test_accepted_revision_is_published_with_matching_audit_and_persisted_history(tmp_path):
    model = EditorialModel(tmp_path / ".env")
    store, result = execute(tmp_path, model, run_inputs(tmp_path))
    document = store.get(result["candidate_ref"])
    audit = store.get(result["completion_audit_ref"])
    history = store.get(result["editorial_history_ref"])
    assert document_content_hash(document) == audit["document_content_hash"]
    assert history[0]["outcome"] == "accepted"
    assert history[0]["baseline_hash"] != history[0]["candidate_hash"]
    assert result["editorial_round"] == 1
    assert model.calls.count("extract_document") == 1
    assert model.calls.count("source_editorial") == 1
    assert (store.root / "runs/source-run/step52/manifest.json").exists()
    assert (store.root / "runs/source-run/output/documentation.html").exists()


@pytest.mark.parametrize("unknown", [False, True])
def test_rejected_revision_retains_baseline_without_restarting_graph(tmp_path, unknown):
    model = EditorialModel(tmp_path / ".env", regression=not unknown, unknown=unknown)
    store, result = execute(tmp_path, model, run_inputs(tmp_path))
    history = store.get(result["editorial_history_ref"])
    document = store.get(result["candidate_ref"])
    assert document_content_hash(document) == history[0]["baseline_hash"]
    assert history[0]["outcome"].startswith("rejected_")
    assert model.calls.count("extract_document") == 1
    assert model.calls.count("source_revision") == 1
    assert model.calls.count("verify_source_revision") == (0 if unknown else 1)
    report = json.loads((store.root / "runs/source-run/output/report.json").read_text("utf-8"))
    assert report["semantic_audit_matches_exported_content"]
    assert report["paragraph_repairs"] == []


def test_editorial_round_limit_stops_after_three_accepted_corrections(tmp_path):
    model = EditorialModel(tmp_path / ".env", remaining=True)
    store, result = execute(tmp_path, model, run_inputs(tmp_path))
    assert model.calls.count("source_revision") == 3
    assert model.calls.count("verify_source_revision") == 3
    assert model.calls.count("source_document") == 1
    assert result["editorial_round"] == 3
    assert len(store.get(result["editorial_history_ref"])) == 3


def test_editorial_revision_cannot_remove_other_paragraphs_or_section_structure():
    original = {
        "title": "Rules",
        "sections": [
            {
                "id": "section-1",
                "title": "Access",
                "parent_id": "",
                "visuals": [],
                "paragraphs": [
                    {
                        "id": "p1",
                        "text": "Email is required.",
                        "sources": [{"evidence_id": "e", "quote": "Email is required."}],
                    },
                    {
                        "id": "p2",
                        "text": "Guests are exempt.",
                        "sources": [{"evidence_id": "e", "quote": "Guests are exempt."}],
                    },
                ],
            }
        ],
    }
    candidate = apply_editorial_revision(
        original,
        {
            "paragraphs": [
                {
                    "paragraph_id": "p1",
                    "paragraph": {
                        **original["sections"][0]["paragraphs"][0],
                        "id": "replace-id",
                        "text": "Provide email.",
                    },
                }
            ]
        },
        {"findings": [{"paragraph_id": "p1", "section_id": "section-1", "category": "clarity"}]},
    )
    assert candidate["sections"][0]["paragraphs"][1] == original["sections"][0]["paragraphs"][1]
    assert candidate["sections"][0]["paragraphs"][0]["id"] == "p1"
    broken = deepcopy(candidate)
    broken["sections"][0]["paragraphs"].pop()
    evidence = [{"id": "e", "text": "Email is required. Guests are exempt."}]
    assert any(
        "lost paragraph" in item for item in revision_findings(original, broken, evidence, {})
    )
    assert original["sections"][0]["paragraphs"][0]["text"] == "Email is required."


def test_revision_acceptance_requires_all_semantic_guards():
    result = {
        "preserves_supported_information": True,
        "no_new_unsupported_claims": True,
        "resolves_requested_changes": True,
        "lost_or_changed_information": [],
        "audit": {"accepted": True, "findings": []},
    }
    assert revision_accepted(result)
    for key in (
        "preserves_supported_information",
        "no_new_unsupported_claims",
        "resolves_requested_changes",
    ):
        assert not revision_accepted({**result, key: False})
    assert not revision_accepted({**result, "lost_or_changed_information": ["Exception"]})
    assert not revision_accepted(
        {**result, "audit": {"accepted": True, "findings": [{"severity": "unsupported"}]}}
    )


def test_authoring_reasoning_defaults_high_and_editorial_limits_are_validated(
    tmp_path, monkeypatch
):
    for key in (
        "DOCGEN_AUTHORING_THINKING_LEVEL",
        "DOCGEN_EDITORIAL_REVIEW",
        "DOCGEN_EDITORIAL_ROUND_LIMIT",
    ):
        monkeypatch.delenv(key, raising=False)
    settings = Settings.load(tmp_path / "absent.env")
    assert settings.authoring_thinking_level == "high"
    assert settings.authoring_output_tokens == 65536
    assert settings.authoring_timeout_seconds == 420
    assert settings.editorial_review
    assert settings.editorial_round_limit == 3
    monkeypatch.setenv("DOCGEN_EDITORIAL_ROUND_LIMIT", "4")
    with pytest.raises(ValueError, match="between 1 and 3"):
        Settings.load(tmp_path / "absent.env")


def test_editorial_manual_workflow_keeps_two_business_gates_across_restart(tmp_path):
    model = EditorialModel(tmp_path / ".env")
    store = ArtifactStore(tmp_path / "runtime")
    inputs = {**run_inputs(tmp_path), "mode": "manual"}
    config = {"configurable": {"thread_id": "source-run"}, "recursion_limit": 150}
    database = store.root / "checkpoints.sqlite"
    with closing(sqlite3.connect(database, check_same_thread=False)) as db:
        graph = Pipeline(store, model, "source-run").build(SqliteSaver(db))
        plan = graph.invoke(inputs, config)
        assert plan["__interrupt__"][0].value["stage"] == "plan_source_document"
    with closing(sqlite3.connect(database, check_same_thread=False)) as db:
        graph = Pipeline(store, model, "source-run").build(SqliteSaver(db))
        final = graph.invoke(decision(plan), config)
        assert final["__interrupt__"][0].value["stage"] == "finalize_source_document"
        assert final["editorial_round"] == 1
        assert model.calls.count("extract_document") == 1
        calls = list(model.calls)
        result = graph.invoke(decision(final), config)
        assert result["status"] == "complete"
        assert model.calls == calls


def test_editorial_stops_early_when_no_correction_is_needed(tmp_path):
    class QuietModel(EditorialModel):
        def call(self, stage, payload, schema=None):
            if stage == "source_editorial":
                self.calls.append(stage)
                return {"findings": [], "summary": "No actionable defects"}
            return super().call(stage, payload, schema)

    model = QuietModel(tmp_path / ".env")
    _, result = execute(tmp_path, model, run_inputs(tmp_path))
    assert result["status"] == "complete"
    assert "source_revision" not in model.calls
    assert "verify_source_revision" not in model.calls


def test_editorial_stops_without_spending_verification_on_unchanged_candidate(tmp_path):
    class UnchangedModel(EditorialModel):
        def call(self, stage, payload, schema=None):
            if stage == "source_revision":
                self.calls.append(stage)
                return {"paragraphs": [], "additions": [], "visuals": []}
            return super().call(stage, payload, schema)

    model = UnchangedModel(tmp_path / ".env")
    store, result = execute(tmp_path, model, run_inputs(tmp_path))
    assert model.calls.count("source_revision") == 1
    assert "verify_source_revision" not in model.calls
    assert store.get(result["editorial_history_ref"])[0]["outcome"] == "retained_unchanged"


def test_plan_section_limit_is_local_and_provider_schema_avoids_rejected_upper_bound():
    sections = [{"id": f"s-{index}", "title": f"Topic {index}"} for index in range(40)]
    assert len(SourcePlan.model_validate({"title": "Plan", "sections": sections}).sections) == 40
    with pytest.raises(ValueError, match="at most 40"):
        SourcePlan.model_validate(
            {"title": "Plan", "sections": sections + [{"id": "extra", "title": "Extra"}]}
        )
    schema = response_schema(SourcePlan)["properties"]["sections"]
    assert schema["minItems"] == 1
    assert "maxItems" not in schema
