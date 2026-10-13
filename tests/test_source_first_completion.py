import json
import sqlite3
import time
from contextlib import closing
from dataclasses import replace

from langgraph.checkpoint.sqlite import SqliteSaver

from docgen_graph.completion import (
    citation_findings,
    quarantine_document,
    quote_locations,
    render_grounded_document,
)
from docgen_graph.config import Settings
from docgen_graph.storage import ArtifactStore
from docgen_graph.workflow import Pipeline


class SourceModel:
    def __init__(self, path, fail_stage=None, audit_findings=None):
        self.settings = replace(Settings.load(path), source_first=True, fast_mode=False)
        self.calls = []
        self.fail_stage = fail_stage
        self.audit_findings = audit_findings or []
        self.deadlines = []

    def set_deadline(self, deadline):
        self.deadlines.append(deadline)

    def call(self, stage, payload, schema=None):
        self.calls.append(stage)
        if stage == self.fail_stage:
            raise RuntimeError("Provider unavailable")
        if stage == "extract_document":
            return {
                "assertions": [
                    {"statement": block["text"], "evidence_ids": [block["id"]]}
                    for block in payload["blocks"]
                ],
                "excluded": [],
            }
        if stage == "semantic_graph":
            return {"concepts": [], "relationships": [], "findings": []}
        if stage == "source_plan":
            return {"title": "Account registration", "sections": ["Behavior"], "questions": []}
        if stage == "source_document":
            return {
                "title": "Account registration",
                "sections": [
                    {
                        "title": "Behavior",
                        "paragraphs": [
                            {
                                "text": source["text"],
                                "sources": [{"evidence_id": source["id"], "quote": source["text"]}],
                                "uncertainty": "",
                            }
                            for source in payload["sources"]["evidence"]
                        ],
                        "image_hashes": [],
                    }
                ],
                "limitations": [],
            }
        if stage == "audit_source_document":
            return {
                "accepted": not self.audit_findings,
                "findings": self.audit_findings,
                "coverage_estimate": 1,
                "coverage_explanation": "Controlled fixture only",
            }
        raise AssertionError(stage)


def run_inputs(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "requirements.md").write_text(
        "Registration requires email verification. Temporary guests are exempt.", "utf-8"
    )
    template = tmp_path / "template.md"
    template.write_text("# Account registration\n\n## Behavior", "utf-8")
    return {
        "run_id": "source-run",
        "docs": str(docs),
        "template": str(template),
        "mode": "autopilot",
        "deadline": time.time() + 1200,
    }


def execute(tmp_path, model, inputs):
    store = ArtifactStore(tmp_path / "runtime")
    config = {"configurable": {"thread_id": "source-run"}, "recursion_limit": 150}
    with closing(sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)) as db:
        graph = Pipeline(store, model, "source-run").build(SqliteSaver(db))
        result = graph.invoke(inputs, config)
        assert not graph.get_state(config).next
        assert not graph.get_state(config).tasks
    return store, result


def test_source_first_completes_once_with_original_context_and_one_final_audit(tmp_path):
    model = SourceModel(tmp_path / ".env")
    store, result = execute(tmp_path, model, run_inputs(tmp_path))
    assert result["status"] == "complete"
    assert model.calls.count("audit_source_document") == 1
    assert not {"verify_document", "audit_semantic_graph", "verify_section"} & set(model.calls)
    output = store.root / "runs/source-run/output"
    markdown = (output / "documentation.md").read_text("utf-8")
    assert "Temporary guests are exempt" in markdown
    assert "[^1]" in markdown
    assert (output / "originals/requirements.md").exists()
    assert model.deadlines[-1] <= result["deadline"] - 20


def test_provider_failure_preserves_sources_and_finishes_without_interrupt(tmp_path):
    model = SourceModel(tmp_path / ".env", fail_stage="source_document")
    store, result = execute(tmp_path, model, run_inputs(tmp_path))
    assert result["status"] == "degraded_source_bundle"
    assert model.calls.count("source_document") == 2
    report = json.loads((store.root / "runs/source-run/output/report.json").read_text("utf-8"))
    assert report["semantic_audit"] is None
    assert any("not completed documentation" in item for item in report["limitations"])


def test_graph_failure_does_not_block_original_source_writing(tmp_path):
    model = SourceModel(tmp_path / ".env", fail_stage="semantic_graph")
    store, result = execute(tmp_path, model, run_inputs(tmp_path))
    assert result["status"] == "complete_with_limitations"
    assert "source_document" in model.calls
    assert store.get(result["candidate_ref"])["sections"][0]["paragraphs"]


def test_deadline_reserve_bypasses_graph_and_still_writes(tmp_path):
    model = SourceModel(tmp_path / ".env")
    inputs = {**run_inputs(tmp_path), "deadline": time.time() + 150}
    _, result = execute(tmp_path, model, inputs)
    assert result["status"] == "complete_with_limitations"
    assert "extract_document" not in model.calls
    assert model.calls == ["source_document", "audit_source_document"]


def test_unsupported_paragraph_is_quarantined_not_published(tmp_path):
    findings = [
        {
            "section_index": 0,
            "paragraph_index": 0,
            "severity": "unsupported",
            "explanation": "Unsupported fixture claim",
        }
    ]
    model = SourceModel(tmp_path / ".env", audit_findings=findings)
    store, result = execute(tmp_path, model, run_inputs(tmp_path))
    assert result["status"] == "degraded_source_bundle"
    document = store.get(result["candidate_ref"])
    assert document["sections"][0]["title"] == "Preserved source extracts"
    assert document["sections"][0]["paragraphs"][0]["uncertainty"]
    report = json.loads((store.root / "runs/source-run/output/report.json").read_text("utf-8"))
    assert report["semantic_audit_matches_exported_content"] is False
    assert report["exported_coverage_estimate"] is None


def test_exact_quote_mismatch_is_not_accepted_as_source_support():
    evidence = [{"id": "a", "text": "Only verified customers can register."}]
    document = {
        "title": "Registration",
        "sections": [
            {
                "title": "Behavior",
                "paragraphs": [
                    {
                        "text": "Everyone can register.",
                        "sources": [{"evidence_id": "a", "quote": "Everyone can register."}],
                    }
                ],
            }
        ],
    }
    assert citation_findings(document, evidence)
    cleaned, removed = quarantine_document(document, evidence, None)
    assert removed and cleaned["sections"][0]["paragraphs"] == []


def test_restart_continues_after_plan_without_repeating_completed_calls(tmp_path):
    model = SourceModel(tmp_path / ".env")
    inputs = run_inputs(tmp_path)
    store = ArtifactStore(tmp_path / "runtime")
    config = {"configurable": {"thread_id": "source-run"}, "recursion_limit": 150}
    database = store.root / "checkpoints.sqlite"
    with closing(sqlite3.connect(database, check_same_thread=False)) as db:
        graph = Pipeline(store, model, "source-run").build(SqliteSaver(db))
        graph.invoke(inputs, config, interrupt_after=["plan_source_document"])
    original_calls = list(model.calls)
    with closing(sqlite3.connect(database, check_same_thread=False)) as db:
        graph = Pipeline(store, model, "source-run").build(SqliteSaver(db))
        result = graph.invoke(None, config)
    assert result["status"] == "complete"
    assert model.calls == original_calls + ["source_document", "audit_source_document"]
    assert result["deadline"] == inputs["deadline"]


def test_audit_provider_failure_does_not_claim_semantic_acceptance(tmp_path):
    model = SourceModel(tmp_path / ".env", fail_stage="audit_source_document")
    store, result = execute(tmp_path, model, run_inputs(tmp_path))
    assert result["status"] == "complete_with_limitations"
    report = json.loads((store.root / "runs/source-run/output/report.json").read_text("utf-8"))
    assert report["semantic_audit"] is None
    assert "Final semantic audit was not completed" in report["limitations"]


def test_global_unsupported_finding_withholds_all_generated_paragraphs():
    evidence = [{"id": "a", "text": "Only verified customers can register."}]
    document = {
        "title": "Registration",
        "sections": [
            {
                "title": "Behavior",
                "paragraphs": [
                    {
                        "text": "Everyone can register.",
                        "sources": [{"evidence_id": "a", "quote": evidence[0]["text"]}],
                    }
                ],
            }
        ],
    }
    audit = {"findings": [{"section_index": -1, "paragraph_index": -1, "severity": "unsupported"}]}
    cleaned, removed = quarantine_document(document, evidence, audit)
    assert removed and cleaned["sections"][0]["paragraphs"] == []


def test_oversized_sources_are_explicitly_incomplete_not_claimed_fully_audited(tmp_path):
    model = SourceModel(tmp_path / ".env")
    model.settings = replace(model.settings, request_tokens=18000)
    inputs = run_inputs(tmp_path)
    from pathlib import Path

    (Path(inputs["docs"]) / "additional.md").write_text(
        "Independent retention policy. " * 500, "utf-8"
    )
    store, result = execute(tmp_path, model, inputs)
    assert result["status"] == "complete_with_limitations"
    report = json.loads((store.root / "runs/source-run/output/report.json").read_text("utf-8"))
    assert any("bounded context" in item for item in report["limitations"])
    assert report["semantic_audit"]["accepted"] is False


def test_partial_completion_retains_accepted_sections_when_later_draft_is_invalid(tmp_path):
    store = ArtifactStore(tmp_path / "runtime")
    pipeline = Pipeline(store, SourceModel(tmp_path / ".env"), "source-run")
    span = {
        "id": "a",
        "text": "Guests are exempt.",
        "path": "source.md",
        "start_line": 1,
        "end_line": 1,
        "file_hash": "f" * 64,
    }
    section = {
        "title": "Completed section",
        "paragraphs": [
            {
                "text": span["text"],
                "sources": [{"evidence_id": "a", "quote": span["text"]}],
                "uncertainty": "",
            }
        ],
        "image_hashes": [],
    }
    invalid = {
        "title": "Later section",
        "paragraphs": [
            {
                "text": "Invented statement",
                "sources": [{"evidence_id": "a", "quote": "Not present"}],
                "uncertainty": "",
            }
        ],
        "image_hashes": [],
    }
    state = {
        "inventory_ref": store.put({"spans": [span]}),
        "completion_sections_ref": store.put([section]),
        "completion_draft_ref": store.put(
            {"title": "Documentation", "sections": [invalid], "limitations": []}
        ),
    }
    result = pipeline.finalize_source_document(state)
    cleaned = store.get(result["candidate_ref"])
    assert cleaned["sections"][0] == section
    assert cleaned["sections"][1]["paragraphs"] == []
    assert result["status"] == "complete_with_limitations"


def test_final_audit_sees_only_candidate_with_valid_exact_citations(tmp_path):
    class InvalidCitationModel(SourceModel):
        def call(self, stage, payload, schema=None):
            response = super().call(stage, payload, schema)
            if stage == "source_document":
                response["sections"][0]["paragraphs"].append(
                    {
                        "text": "A fabricated requirement must not reach the final audit.",
                        "sources": [{"evidence_id": "unknown", "quote": "Missing source"}],
                        "uncertainty": "",
                    }
                )
            if stage == "audit_source_document":
                self.audited_document = payload["document"]
                assert not citation_findings(payload["document"], payload["sources"]["evidence"])
                assert len(payload["document"]["sections"][0]["paragraphs"]) == 1
            return response

    model = InvalidCitationModel(tmp_path / ".env")
    store, result = execute(tmp_path, model, run_inputs(tmp_path))
    assert result["status"] == "complete_with_limitations"
    report = json.loads((store.root / "runs/source-run/output/report.json").read_text("utf-8"))
    assert report["semantic_audit_matches_exported_content"] is True
    assert report["exported_coverage_estimate"] == 1
    assert report["withheld_paragraphs"] == ["Withheld paragraph 1.2"]
    assert store.get(result["candidate_ref"])["sections"] == model.audited_document["sections"]


def test_quote_locations_preserve_multiple_occurrences_and_midline_window_offset():
    span = {
        "text": "Rule.\nAnother rule.\nRule.",
        "start_line": 8,
        "start_column": 7,
        "source_start_char": 120,
    }
    locations = quote_locations(span, "Rule.")
    assert locations == [
        {
            "start_line": 8,
            "end_line": 8,
            "start_column": 7,
            "end_column": 11,
            "source_start_char": 120,
            "source_end_char": 125,
        },
        {
            "start_line": 10,
            "end_line": 10,
            "start_column": 1,
            "end_column": 5,
            "source_start_char": 140,
            "source_end_char": 145,
        },
    ]


def test_renderer_omits_empty_sections_and_none_uncertainty_and_locates_quote():
    evidence = [
        {
            "id": "a",
            "path": "source.md",
            "text": "Heading\n\nThe rule.",
            "start_line": 1,
            "end_line": 3,
        }
    ]
    paragraph = {
        "text": "The rule.",
        "sources": [{"evidence_id": "a", "quote": "The rule."}],
        "uncertainty": "None.",
    }
    document = {
        "title": "Documentation",
        "sections": [
            {"title": "Empty", "paragraphs": [], "image_hashes": []},
            {"title": "Behavior", "paragraphs": [paragraph], "image_hashes": []},
        ],
        "limitations": [],
    }
    markdown = render_grounded_document(document, evidence, {})
    assert "## Empty" not in markdown
    assert "Uncertainty:" not in markdown
    assert "source.md, L3:1-L3:9" in markdown
