from types import SimpleNamespace

import pytest
from conftest import FixtureModel
from langgraph.types import Command

from docgen.cli import selected_decisions
from docgen.contracts import Finding
from docgen.generation import GenerationPipeline
from docgen.generation_claim_audit import page_claims, remove_section_diagrams, validate_audit
from docgen.generation_contracts import ClaimAudit, EditorialPage, WritingFragment
from docgen.generation_editorial import validate_editorial_page
from docgen.generation_export import citations, evidence_id, source_labels
from docgen.generation_validation import validate_fragment
from docgen.planning_inputs import validate_knowledge
from docgen.reconciliation import comparison_tasks, split_comparison
from docgen.review import validate_decisions
from docgen.workflow import Pipeline, persistent_graph


def entity(identifier, definition="Same definition"):
    return {
        "id": identifier,
        "canonical_name": "Policy",
        "aliases": [],
        "kind": "object",
        "scope": "tenant-a",
        "version": "v1",
        "definition": definition,
        "evidence": [{"block_id": "b1", "excerpt": definition}],
        "review_status": "verified",
    }


def pairs(tasks):
    result = set()
    for task in tasks:
        left, right = task["left"], task["right"]
        if right:
            result.update(tuple(sorted((a, b))) for a in left for b in right)
        else:
            result.update(
                tuple(sorted((left[i], left[j])))
                for i in range(len(left))
                for j in range(i + 1, len(left))
            )
    return result


def test_exact_comparison_policy_preserves_original_members_and_qualifications():
    records = [entity("a"), entity("b"), entity("c", "Different definition")]
    strict = comparison_tasks(records, "entities", 1024)
    exact = comparison_tasks(records, "entities", 1024, policy="exact")
    assert pairs(strict["tasks"]) == {("a", "b"), ("a", "c"), ("b", "c")}
    assert exact["representative_members"]["a"] == ["a", "b"]
    assert exact["representative_members"]["c"] == ["c"]
    assert exact["exact_pairs_discharged"] == 1
    assert pairs(exact["tasks"]) == {("a", "c")}
    assert exact["unperformed"] == []


def test_required_pair_ledger_discharges_overlapping_groups_once():
    records = [entity(f"e{index}", f"Definition {index}") for index in range(12)]
    plan = comparison_tasks(records, "entities", 1024, policy="exact")
    expected = {
        tuple(sorted((records[i]["id"], records[j]["id"])))
        for i in range(len(records))
        for j in range(i + 1, len(records))
    }
    checked = [tuple(sorted(pair)) for task in plan["tasks"] for pair in task["required_pairs"]]
    assert set(checked) == expected
    assert len(checked) == len(expected) == plan["required_relationships"]
    assert all(
        task["group"] in task["shared_contexts"] or task["group"] in contexts
        for task in plan["tasks"]
        for contexts in task["pair_contexts"]
    )
    assert plan["exact_pairs_discharged"] == 0
    first = plan["tasks"][0]
    if len(first["left"] + first["right"]) > 2:
        children = split_comparison(first)
        assert sorted(
            tuple(sorted(pair)) for child in children for pair in child["required_pairs"]
        ) == sorted(tuple(sorted(pair)) for pair in first["required_pairs"])
        assert sorted(
            sorted(set(child["shared_contexts"]) | set(contexts))
            for child in children
            for contexts in child["pair_contexts"]
        ) == sorted(
            sorted(set(first["shared_contexts"]) | set(contexts))
            for contexts in first["pair_contexts"]
        )


def test_compact_source_labels_keep_exact_evidence_identity():
    evidence = [
        {"block_id": "b2", "excerpt": "Second source."},
        {"block_id": "b1", "excerpt": "First source."},
    ]
    context = {"originals": {"obligations": [{"evidence": evidence}]}}
    store = SimpleNamespace(get_object=lambda ref: context)
    pipeline = SimpleNamespace(
        store=store,
        rows=lambda state, kind: (
            [{"id": "o1", "evidence": evidence}]
            if kind == "content-obligations"
            else [{"obligation_ids": ["o1"]}]
        ),
    )
    labels = source_labels(pipeline, {})
    result = citations(evidence, "index.md", labels)
    assert set(labels) == {evidence_id(item) for item in evidence}
    assert "[S1](sources/index.md#s1)" in result
    assert "[S2](sources/index.md#s2)" in result


def test_editorial_reader_text_rejects_internal_ids_but_preserves_link_targets():
    selection = "objects/selection-" + "a" * 64 + ".json"
    original = "# Sources\n\n[Source index](snapshots/" + "b" * 64 + "/source.md)\n"
    payload = {
        "page": {"id": "page-1"},
        "markdown": original,
        "originals": {"obligations": [], "source_blocks": []},
        "source_catalog": {},
        "source_labels": {},
        "knowledge_revision": "c" * 64,
        "selection_ref": selection,
    }
    clean = EditorialPage(page_id="page-1", markdown=original, coverage=[], changes=[])
    validate_editorial_page(clean, payload)
    leaked = EditorialPage(
        page_id="page-1",
        markdown=original + "\n| Source set | " + selection + " |\n",
        coverage=[],
        changes=[],
    )
    with pytest.raises(ValueError, match="internal artifact"):
        validate_editorial_page(leaked, payload)
    suffix = EditorialPage(
        page_id="page-1",
        markdown=original + "\n| Source set | " + selection.rsplit("/", 1)[-1] + " |\n",
        coverage=[],
        changes=[],
    )
    with pytest.raises(ValueError, match="internal artifact"):
        validate_editorial_page(suffix, payload)


def test_writing_fragment_rejects_internal_source_reference():
    selection = "objects/selection-" + "a" * 64 + ".json"
    job = {
        "id": "job-1",
        "section_id": "section-1",
        "brief_id": "brief-1",
        "fragment": 0,
        "obligation_ids": [],
    }
    context = {
        "originals": {"obligations": [], "source_blocks": []},
        "brief": {"content": {"tables": [], "diagrams": []}},
        "inherited_references": {"selection": selection},
    }
    fragment = WritingFragment(
        job_id="job-1",
        section_id="section-1",
        passages=[
            {
                "text": "Source set " + selection,
                "kind": "editorial",
                "obligation_ids": [],
                "evidence": [],
            }
        ],
        tables=[],
        covered_obligation_ids=[],
    )
    with pytest.raises(ValueError, match="internal artifact"):
        validate_fragment(fragment, job, context, {"quote_policy": "none"})
    fragment.passages[0].text = "Source set " + selection.rsplit("/", 1)[-1]
    with pytest.raises(ValueError, match="internal artifact"):
        validate_fragment(fragment, job, context, {"quote_policy": "none"})


def test_consolidated_snapshot_defers_source_review_until_barrier(settings, store, monkeypatch):
    settings = settings.model_copy(update={"review_policy": "consolidated"})
    snapshot = {
        "blocks": [],
        "inventory": [],
        "problems": [{"kind": "unreadable", "path": "missing.md", "description": "Unreadable"}],
    }
    monkeypatch.setattr("docgen.workflow.snapshot_sources", lambda *args: snapshot)
    pipeline = Pipeline(settings, store, None)
    result = pipeline.snapshot_sources({"run_id": "run", "source": "unused"})
    assert result["route"] == "plan_batches"
    barrier = pipeline.finalize_knowledge({"run_id": "run", **result})
    assert barrier["route"] == "review_issues"
    assert barrier["review_return_stage"] == "finalize_knowledge"


def test_cli_selected_authority_uses_interrupt_revision():
    issue = {
        "id": "issue-1",
        "kind": "conflict",
        "record_ids": ["a", "b"],
        "revision": "revision-1",
    }
    snapshot = SimpleNamespace(
        values={"review_revision": "revision-1"},
        interrupts=[SimpleNamespace(value={"issues": [issue]})],
    )
    args = SimpleNamespace(
        select_authority=["issue-1=a"],
        keep_distinct=None,
        retain_unknown=None,
        exclude=None,
        explain_asset=None,
        approve_release=False,
        reviewer="reviewer",
        rationale="Dated source is authoritative",
    )
    decisions = selected_decisions(args, snapshot, "knowledge")["decisions"]
    assert decisions == [
        {
            "issue_id": "issue-1",
            "revision": "revision-1",
            "action": "select_authority",
            "claim_ids": ["a"],
            "reviewer": "reviewer",
            "rationale": "Dated source is authoritative",
        }
    ]
    args.reviewer = None
    with pytest.raises(ValueError, match="reviewer"):
        selected_decisions(args, snapshot, "knowledge")


def test_consolidated_review_accepts_issue_specific_revisions():
    issues = [
        {"id": "first", "kind": "conflict", "record_ids": ["a", "b"], "revision": "r1"},
        {"id": "second", "kind": "conflict", "record_ids": ["c", "d"], "revision": "r2"},
    ]
    decisions = [
        {
            "issue_id": issue["id"],
            "revision": issue["revision"],
            "action": "select_authority",
            "claim_ids": [issue["record_ids"][0]],
            "reviewer": "reviewer",
            "rationale": "Source authority checked",
        }
        for issue in issues
    ]
    assert len(validate_decisions(decisions, issues, "package-revision")) == 2
    decisions[1]["revision"] = "r1"
    with pytest.raises(ValueError, match="revision"):
        validate_decisions(decisions, issues, "package-revision")


def test_consolidated_comparison_review_waits_for_final_barrier(tmp_path, settings, store):
    settings = settings.model_copy(
        update={"comparison_policy": "exact", "review_policy": "consolidated"}
    )
    source = tmp_path / "source.md"
    source.write_text("First rule applies.\n\nSecond rule applies.\n", encoding="utf-8")

    def conflicts(stage, payload, result):
        if stage == "claims":
            pair = payload["required_pairs"][0]
            block_id = payload["source_blocks"][0]["id"]
            result.findings = [
                Finding.model_validate(
                    {
                        "kind": "conflict",
                        "description": f"Conflict {index}",
                        "block_ids": [block_id],
                        "record_ids": pair,
                    }
                )
                for index in range(2)
            ]
        return result

    with persistent_graph(Pipeline(settings, store, FixtureModel(conflicts))) as graph:
        config = {"configurable": {"thread_id": "consolidated-conflicts"}}
        graph.invoke(
            {"run_id": "consolidated-conflicts", "source": str(source), "signature": "fixture"},
            config,
        )
        state = graph.get_state(config)
    assert state.values["status"] == "review"
    assert state.values["review_stage"] == "finalize_knowledge"
    assert state.values["claim_index"] == store.get(state.values["claim_plan_ref"])["task_count"]
    assert len(state.interrupts[0].value["issues"]) == 2
    decisions = [
        {
            "issue_id": issue["id"],
            "revision": issue["revision"],
            "action": "select_authority",
            "claim_ids": [issue["record_ids"][0]],
            "reviewer": "reviewer",
            "rationale": "Source authority checked",
        }
        for issue in state.interrupts[0].value["issues"]
    ]
    with persistent_graph(Pipeline(settings, store, FixtureModel(conflicts))) as graph:
        graph.invoke(Command(resume={"decisions": decisions}), config)
        assert graph.get_state(config).values["status"] == "complete"


def test_exact_pair_checks_survive_graph_completion_and_knowledge_import(tmp_path, settings, store):
    settings = settings.model_copy(
        update={"comparison_policy": "exact", "review_policy": "consolidated"}
    )
    source = tmp_path / "source.md"
    source.write_text("First rule applies.\n\nSecond rule applies.\n", encoding="utf-8")
    with persistent_graph(Pipeline(settings, store, FixtureModel())) as graph:
        result = graph.invoke(
            {"run_id": "exact-knowledge", "source": str(source), "signature": "fixture"},
            {"configurable": {"thread_id": "exact-knowledge"}},
        )
    assert result["status"] == "complete"
    bundle = store.get(result["bundle_ref"])
    assert bundle["schema_version"] == "2"
    assert bundle["comparison_coverage"]["claim"]["required_relationships"] == 1
    assert validate_knowledge(bundle, store)["blocks"]


def test_claim_audit_separates_diagram_edges_and_table_rows():
    markdown = (
        "# Guide\n\n## Flow\n\n"
        '```mermaid\nflowchart TD\n    a["Daily run"]\n'
        '    b["Check tenant scope"]\n'
        '    a -->|"Initiates"| b\n```\n\n'
        "Diagram source: [S1](sources/index.md#s1) [S2](sources/index.md#s2)\n\n"
        "| Step | Behavior | Source |\n| --- | --- | --- |\n"
        "| Replay | Retrieves a stored record | [S3](sources/index.md#s3) |\n"
    )
    claims = page_claims("index.md", markdown)
    edge = next(claim for claim in claims if claim["kind"] == "diagram_edge")
    row = next(claim for claim in claims if claim["kind"] == "table_row")
    assert edge["text"] == "Daily run -> Check tenant scope: Initiates"
    assert edge["citations"] == ["S1", "S2"]
    assert "Retrieves a stored record" in row["text"]
    assert row["citations"] == ["S3"]


def test_claim_audit_rejects_unchecked_or_uncited_support():
    claim = {
        "id": "one",
        "text": "A replay retrieves a stored record. [S1]",
        "citations": ["S1"],
    }
    with pytest.raises(ValueError, match="Factual audit"):
        validate_audit(ClaimAudit(checks=[]), {"claims": [claim]})
    with pytest.raises(ValueError, match="uncited source"):
        validate_audit(
            ClaimAudit(
                checks=[
                    {
                        "claim_id": "one",
                        "verdict": "supported",
                        "supporting_labels": ["S2"],
                        "reason": "",
                    }
                ]
            ),
            {"claims": [claim]},
        )


def test_unsupported_diagram_removal_preserves_other_sections():
    markdown = (
        "# Guide\n\n## Flow\n\n"
        '```mermaid\nflowchart TD\n    a["A"]\n    b["B"]\n    a -->|"Next"| b\n```\n\n'
        "Diagram source: [S1](sources/index.md#s1)\n\n"
        "The supported behavior remains. [S1](sources/index.md#s1)\n\n"
        "## Other flow\n\n"
        '```mermaid\nflowchart TD\n    c["C"]\n    d["D"]\n    c -->|"Next"| d\n```\n\n'
        "Diagram source: [S2](sources/index.md#s2)\n"
    )
    revised, removed = remove_section_diagrams(markdown, {"Flow"})
    assert removed == 1
    assert "a -->" not in revised
    assert "Diagram source: [S1]" not in revised
    assert "The supported behavior remains." in revised
    assert "c -->" in revised


def test_claim_audit_restarts_editorial_review_after_supported_diagram_removal(store):
    markdown = (
        '# Guide\n\n## Flow\n\n```mermaid\nflowchart TD\n    a["A"]\n'
        '    b["B"]\n    a -->|"Invented"| b\n```\n\n'
        "Diagram source: [S1](sources/index.md#s1)\n\n"
        "The documented fact remains. [S1](sources/index.md#s1)\n"
    )
    jobs = [
        {
            "claims": [
                {
                    "id": "edge",
                    "path": "index.md",
                    "section": "Flow",
                    "kind": "diagram_edge",
                    "text": "A -> B: Invented",
                    "citations": ["S1"],
                },
                {
                    "id": "prose",
                    "path": "index.md",
                    "section": "Flow",
                    "kind": "passage",
                    "text": "The documented fact remains. [S1]",
                    "citations": ["S1"],
                },
            ]
        }
    ]
    state = {
        "claim_jobs_ref": store.put(jobs, "claim-audit-jobs"),
        "claim_results_ref": store.put(
            [
                {
                    "claim_id": "edge",
                    "verdict": "unsupported",
                    "supporting_labels": [],
                    "reason": "Invented transition",
                },
                {
                    "claim_id": "prose",
                    "verdict": "supported",
                    "supporting_labels": ["S1"],
                    "reason": "",
                },
            ],
            "claim-audit-results",
        ),
        "pages_ref": store.put({"index.md": markdown}, "generation-pages"),
    }

    def read(current, key, default=None):
        return store.get(current[key]) if current.get(key) else default

    pipeline = SimpleNamespace(
        store=store,
        read=read,
        rows=lambda current, kind: [{"id": "page-1", "path": "index.md", "role": "content"}],
        gate=lambda *args: pytest.fail("Supported diagram removal must not enter review"),
    )
    result = GenerationPipeline.finalize_claim_audit(pipeline, state)
    assert result["route"] == "polish_documentation"
    assert result["claim_repair_round"] == 1
    revised = store.get(result["unpolished_pages_ref"])["index.md"]
    assert "```mermaid" not in revised
    assert "The documented fact remains." in revised
