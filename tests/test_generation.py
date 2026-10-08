from copy import deepcopy
from pathlib import Path

import pytest
from langgraph.types import Command
from planning_fixtures import knowledge_fixture, planning_state, run_plan

from docgen.generation import STAGES, GenerationPipeline
from docgen.generation_contracts import WritingFragment
from docgen.generation_export import citations, evidence_id, mermaid_text
from docgen.generation_inputs import load_plan
from docgen.generation_validation import markdown_report, validate_fragment
from docgen.storage import digest, read_json
from docgen.workflow import persistent_graph


class GenerationModel:
    def __init__(self, reject=False):
        self.calls = []
        self.reject = reject

    def call(self, stage, payload, schema):
        self.calls.append(stage)
        if stage == "gen_write":
            job = payload["job"]
            obligations = {o["id"]: o for o in payload["context"]["originals"]["obligations"]}
            value = {
                "job_id": job["id"],
                "section_id": job["section_id"],
                "covered_obligation_ids": job["obligation_ids"],
                "passages": [
                    {
                        "text": o["evidence"][0]["excerpt"],
                        "kind": "quote",
                        "obligation_ids": [o["id"]],
                        "evidence": o["evidence"],
                    }
                    for o in obligations.values()
                ],
                "tables": [
                    {
                        "index": t["index"],
                        "rows": [
                            {
                                "id": r["id"],
                                "cells": [
                                    {
                                        "text": "Source requirement"
                                        if r["obligation_ids"]
                                        else "Document metadata",
                                        "obligation_ids": r["obligation_ids"],
                                        "evidence": [
                                            e
                                            for key in r["obligation_ids"]
                                            for e in obligations[key]["evidence"]
                                        ],
                                    }
                                    for _ in t["columns"]
                                ],
                            }
                            for r in t["rows"]
                        ],
                    }
                    for t in payload["tables"]
                ],
            }
        elif stage == "gen_verify":
            value = {
                "checked_obligation_ids": payload["job"]["obligation_ids"],
                "checked_table_rows": [
                    f"{t['index']}:{r['id']}" for t in payload["tables"] for r in t["rows"]
                ],
                "checked_diagram_ids": payload["diagram_ids"],
                "findings": [
                    {
                        "kind": "qualification",
                        "description": "Correct this fragment",
                        "obligation_ids": payload["job"]["obligation_ids"],
                        "blocking": True,
                    }
                ]
                if self.reject
                else [],
                "language_review_scope": "Deterministic fixture only, not semantic acceptance",
            }
        elif stage == "gen_polish":
            passages, coverage = [], []
            for obligation in payload["originals"]["obligations"]:
                excerpt = obligation["evidence"][0]["excerpt"].strip()
                passages.append(
                    excerpt + " " + citations(obligation["evidence"], payload["page"]["path"])
                )
                coverage.append(
                    {
                        "obligation_id": obligation["id"],
                        "excerpt": excerpt,
                        "evidence_ids": [evidence_id(e) for e in obligation["evidence"]],
                    }
                )
            value = {
                "page_id": payload["page"]["id"],
                "markdown": payload["markdown"] + "\n\n" + "\n\n".join(passages),
                "coverage": coverage,
                "changes": ["Fixture only; does not demonstrate real editorial quality"],
            }
        else:
            value = {
                "checked_section_ids": payload["page"]["section_ids"],
                "findings": [],
                "readability": "Fixture only",
                "checked_obligation_ids": [o["id"] for o in payload["originals"]["obligations"]],
                "template_assessments": [
                    {"span_id": key, "satisfied": True, "explanation": "Fixture only"}
                    for key in payload["applicable_template_span_ids"]
                ],
                "narrative_flows": True,
                "repetition_controlled": True,
                "source_links_readable": True,
            }
        return schema.model_validate(value)


@pytest.fixture
def generation(tmp_path, settings, store):
    bundle = knowledge_fixture(tmp_path, settings, store, ("Archive", "Delivery"), count=1)
    state = planning_state(tmp_path, bundle)
    state["signature"] = "a" * 64
    result, _, _ = run_plan(state, settings, store)
    assert result["status"] == "ready_for_generation"
    model = GenerationModel()
    pipeline = GenerationPipeline(settings, store, model)
    initial = {
        "run_id": "generation",
        "workflow": "documentation_generation",
        "signature": "b" * 64,
        "plan": result["plan_ref"],
        "cache_mode": "off",
    }
    config = {"configurable": {"thread_id": "generation"}, "recursion_limit": 10000}
    return pipeline, model, initial, config


def test_generation_publishes_only_markdown_and_requires_human_release(generation, store):
    pipeline, model, initial, config = generation
    with persistent_graph(pipeline) as graph:
        result = graph.invoke(initial, config, durability="sync")
        assert result["status"] == "ready_for_review", pipeline.read(result, "issues_ref")
        assert graph.get_state(config).interrupts
    output = Path(result["export_path"])
    assert {p.suffix for p in output.rglob("*") if p.is_file()} == {".md"}
    manifest = read_json(Path(result["manifest_path"]))
    assert all(
        digest((output / key).read_bytes()) == value for key, value in manifest["files"].items()
    )
    assert pipeline.read(result, "validation_ref")["coverage"]["passed"]
    count = len(model.calls)
    issue = pipeline.read(result, "issues_ref")[0]
    with persistent_graph(pipeline) as graph:
        final = graph.invoke(
            Command(
                resume={
                    "decisions": [
                        {
                            "issue_id": issue["id"],
                            "revision": issue["revision"],
                            "action": "approve_release",
                            "reviewer": "Fixture reviewer",
                            "rationale": "Test only",
                            "reviewed_scope": [
                                "content_accuracy",
                                "reader_usefulness",
                                "language",
                                "markdown",
                            ],
                        }
                    ]
                }
            ),
            config,
            durability="sync",
        )
    assert final["status"] == "complete"
    assert output.exists() and final["export_path"] != str(output)
    assert len(model.calls) == count


@pytest.mark.parametrize("stage", [s for s in STAGES if s != "review_generation"])
def test_restart_each_generation_node(generation, stage):
    pipeline, model, initial, config = generation
    with persistent_graph(pipeline, stage) as graph:
        stopped = graph.invoke(initial, config, durability="sync")
    fragments = pipeline.read(stopped, "fragments_ref", {})
    with persistent_graph(pipeline) as graph:
        result = graph.invoke(None, config, durability="sync")
    assert result["status"] == "ready_for_review", result
    assert all(
        pipeline.read(result, "fragments_ref")[key] == value for key, value in fragments.items()
    )


def test_revision_bound_correction_and_resume(generation):
    pipeline, model, initial, config = generation
    model.reject = True
    with persistent_graph(pipeline) as graph:
        result = graph.invoke(initial, config, durability="sync")
    assert result["status"] == "awaiting_review"
    assert model.calls.count("gen_write") == 3
    issues = pipeline.read(result, "issues_ref")
    decisions = [
        {
            "issue_id": i["id"],
            "revision": i["revision"],
            "action": "correct",
            "reviewer": "Fixture reviewer",
            "rationale": "Correct reviewed text",
            "correction_ref": result["draft_ref"],
        }
        for i in issues
    ]
    stale = deepcopy(decisions)
    stale[0]["revision"] = "stale"
    with persistent_graph(pipeline) as graph:
        with pytest.raises(ValueError, match="Stale"):
            graph.invoke(Command(resume={"decisions": stale}), config)
    model.reject = False
    with persistent_graph(pipeline) as graph:
        graph.update_state(config, {"route": "review_generation"}, as_node="verify_writing_job")
        graph.invoke(None, config)
        result = graph.invoke(Command(resume={"decisions": decisions}), config)
    assert result["status"] == "ready_for_review", result


def test_corrupt_plan_and_changed_provenance_rejected(generation, store):
    pipeline, _, initial, _ = generation
    ref, plan, inputs, _ = load_plan(pipeline.settings, store, initial["plan"])
    changed = {**plan, "revision": "stale"}
    with pytest.raises(ValueError, match="revision"):
        load_plan(pipeline.settings, store, store.put(changed))
    path = store.path(ref)
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="integrity"):
        load_plan(pipeline.settings, store, ref)


def test_fragment_rejects_missing_coverage_and_false_evidence(generation):
    pipeline, model, initial, config = generation
    with persistent_graph(pipeline, "draft_writing_job") as graph:
        result = graph.invoke(initial, config)
        while not pipeline.read(result, "draft_ref")["passages"]:
            result = graph.invoke(None, config)
    job = pipeline.job(result)
    context = pipeline.store.get_object(job["context_ref"])
    fragment = WritingFragment.model_validate(pipeline.read(result, "draft_ref"))
    fragment.covered_obligation_ids.append("invented")
    with pytest.raises(ValueError, match="coverage"):
        validate_fragment(fragment, job, context, pipeline.read(result, "language_ref"))
    fragment.covered_obligation_ids.remove("invented")
    fragment.passages[0].evidence[0].excerpt = "Invented evidence"
    with pytest.raises(ValueError, match="exact"):
        validate_fragment(fragment, job, context, pipeline.read(result, "language_ref"))


def test_markdown_checks_broken_unsafe_links_html_and_headings(tmp_path, store):
    pages = {
        "index.md": "# Title\n\n### Skipped\n\n[Bad](missing.md)\n\n"
        "[Unsafe](../../../secret.md)\n\n<div>Bad</div>\n"
    }
    report = markdown_report(pages, tmp_path.resolve(), store, [])
    assert not report["passed"]
    assert len(report["findings"]) >= 4


def test_mermaid_renderer_preserves_unknowns_and_escapes_labels():
    spec = {
        "nodes": [{"id": "unsafe-id", "label": 'Check "state" < 2'}],
        "edges": [],
        "unknown_transitions": ["Unknown success state"],
    }
    output = mermaid_text(spec)
    assert "n0[" in output and "#quot;" in output and "#60;" in output
    assert "-->" not in output


def test_missing_asset_enters_review_before_paid_calls(generation, tmp_path):
    from docgen.storage import write_json

    pipeline, model, initial, config = generation
    brief = tmp_path / "generation-brief.json"
    write_json(
        brief,
        {"assets": [{"path": "missing.png", "purpose": "Required diagram", "disposition": "link"}]},
    )
    initial["brief"] = str(brief)
    with persistent_graph(pipeline) as graph:
        result = graph.invoke(initial, config)
    assert result["review_stage"] == "prepare_assets"
    assert not model.calls


@pytest.mark.parametrize(
    "defect", ["duplicate_row", "missing_cell", "unowned_cell", "invented_excerpt"]
)
def test_table_cell_integrity(defect):
    evidence = {"block_id": "b1", "excerpt": "Run only when approved."}
    context = {
        "originals": {
            "obligations": [{"id": "o1", "evidence": [evidence]}],
            "source_blocks": [{"id": "b1", "content": evidence["excerpt"]}],
        },
        "brief": {
            "content": {
                "tables": [
                    {
                        "columns": ["Condition"],
                        "rows": [{"id": "r1", "obligation_ids": ["o1"], "editorial": False}],
                    }
                ]
            }
        },
    }
    job = {"id": "j1", "section_id": "s1", "obligation_ids": ["o1"], "fragment": 0}
    fragment = WritingFragment.model_validate(
        {
            "job_id": "j1",
            "section_id": "s1",
            "covered_obligation_ids": ["o1"],
            "passages": [],
            "tables": [
                {
                    "index": 0,
                    "rows": [
                        {
                            "id": "r1",
                            "cells": [
                                {
                                    "text": "Approved",
                                    "obligation_ids": ["o1"],
                                    "evidence": [evidence],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    )
    validate_fragment(fragment, job, context, {"quote_policy": "exact_labeled"})
    rows = fragment.tables[0].rows
    if defect == "duplicate_row":
        rows.append(rows[0].model_copy(deep=True))
    elif defect == "missing_cell":
        rows[0].cells.clear()
    elif defect == "unowned_cell":
        rows[0].cells[0].obligation_ids = ["other"]
    else:
        rows[0].cells[0].evidence[0].excerpt = "Invented"
    with pytest.raises(ValueError):
        validate_fragment(fragment, job, context, {"quote_policy": "exact_labeled"})


def test_snapshot_link_requires_authorized_unchanged_asset(tmp_path, store):
    asset = tmp_path / "snapshot.png"
    asset.write_bytes(b"original source")
    root = tmp_path / "documentation"
    pages = {"index.md": "# Source image\n\n![Source diagram](../snapshot.png)\n"}
    assets = [{"target": str(asset), "hash": digest(asset.read_bytes())}]
    assert markdown_report(pages, root, store, assets)["passed"]
    asset.write_bytes(b"changed")
    assert not markdown_report(pages, root, store, assets)["passed"]
    assert not markdown_report(pages, root, store, [])["passed"]


def test_escaped_source_quotation_is_not_raw_html(tmp_path, store):
    pages = {"index.md": "# Source\n\nSource quotation:\n\n> \\<tag\\> is literal text.\n"}
    assert markdown_report(pages, tmp_path, store, [])["passed"]


def test_page_semantic_findings_block_publication(generation):
    pipeline, model, initial, config = generation
    original = model.call

    def with_page_finding(stage, payload, schema):
        result = original(stage, payload, schema)
        if stage == "gen_page_review":
            value = result.model_dump()
            value["findings"] = [
                {
                    "kind": "qualification",
                    "description": "A known condition was called unknown",
                    "obligation_ids": [],
                    "blocking": True,
                }
            ]
            return schema.model_validate(value)
        return result

    model.call = with_page_finding
    with persistent_graph(pipeline) as graph:
        result = graph.invoke(initial, config)
    assert result["status"] == "awaiting_review"
    assert result["review_stage"] == "verify_editorial_revision"
    assert not result.get("export_path")
    assert not pipeline.store.path("runs/generation/documentation").exists()
