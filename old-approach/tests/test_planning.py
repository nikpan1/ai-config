from pathlib import Path

import pytest
from langgraph.types import Command
from planning_fixtures import PlanningFixtureModel, knowledge_fixture, planning_state, run_plan

from docgen.model import ModelFailure, TruncatedOutput
from docgen.planning_contracts import AuditFinding, DocumentationBrief
from docgen.planning_helpers import validate_dag, validate_paths
from docgen.planning_inputs import resolve_reference
from docgen.planning_validation import validate_plan
from docgen.storage import digest, read_json, write_json
from docgen.workflow import persistent_graph


def test_complete_plan_preserves_template_qualifiers_and_restart(tmp_path, settings, store):
    bundle = knowledge_fixture(tmp_path, settings, store)
    state = planning_state(tmp_path, bundle)
    result, pipeline, model = run_plan(state, settings, store, stop_after="plan_navigation")
    calls = len(model.calls)
    with persistent_graph(pipeline) as graph:
        result = graph.invoke(None, {"configurable": {"thread_id": "planning"}})
    assert result["status"] == "ready_for_generation", result
    assert model.calls[calls:] == ["plan_audit"] * 11
    assert validate_plan(pipeline, result)["passed"]
    assert len(list(pipeline.rows(result, "documentation-units"))) == 1
    manifest = read_json(Path(result["export_path"]) / "manifest.json")
    for name, checksum in manifest["files"].items():
        assert digest((Path(result["export_path"]) / name).read_bytes()) == checksum
    assert store.get(bundle)["signature"] == "fixture"


@pytest.mark.parametrize("delivery", ["auto", "single_page", "multi_page"])
def test_multiple_units_independent_of_delivery_mode(tmp_path, settings, store, delivery):
    bundle = knowledge_fixture(tmp_path, settings, store, ("Issuance", "Settlement", "Claims"))
    result, pipeline, _ = run_plan(
        planning_state(tmp_path, bundle, {"delivery_mode": delivery}), settings, store
    )
    assert result["status"] == "ready_for_generation", result
    assert len(list(pipeline.rows(result, "template-instances"))) == 3
    pages = list(pipeline.rows(result, "pages"))
    assert sum(p["role"] == "collection" for p in pages) == 1
    assert sum(p["role"] == "detail" for p in pages) == (3 if delivery == "multi_page" else 0)
    assert pipeline.component(result, "validation-report")["coverage_percent"] == 100
    exported = Path(result["export_path"])
    for page in pages:
        content = (exported / "page-briefs" / f"{page['id']}.md").read_text(encoding="utf-8")
        if page["parent_id"]:
            assert f"({page['parent_id']}.md)" in content
        for child in (item for item in pages if item["parent_id"] == page["id"]):
            assert f"({child['id']}.md)" in content
        assert f"page-briefs/{page['id']}.md" in (exported / "page-index.md").read_text()


def test_scope_exclusions_are_visible_and_expectations_are_hints(tmp_path, settings, store):
    bundle = knowledge_fixture(tmp_path, settings, store, ("Issuance", "Claims"))
    record = store.get(bundle)["claims"][-1]["id"]
    state = planning_state(
        tmp_path, bundle, {"expected_areas": ["Issuance"], "exclude_record_ids": [record]}
    )
    result, pipeline, _ = run_plan(state, settings, store)
    assert result["status"] == "ready_for_generation", result
    assert len(list(pipeline.rows(result, "documentation-units"))) == 2
    assert (
        pipeline.component(result, "validation-report")["disposition_counts"]["out_of_scope"] == 1
    )


def test_single_unit_scope_mismatch_is_not_automatically_approved(tmp_path, settings, store):
    bundle = knowledge_fixture(tmp_path, settings, store, ("Issuance", "Claims"))
    result, _, _ = run_plan(
        planning_state(tmp_path, bundle, {"unit_policy": "single"}), settings, store
    )
    assert result["status"] == "review"
    assert store.get(result["issues_ref"])[0]["kind"] == "scope_mismatch"


def test_incomplete_knowledge_and_corrupt_evidence_are_rejected(tmp_path, settings, store):
    ref = knowledge_fixture(tmp_path, settings, store)
    bundle = store.get(ref)
    bundle["status"] = "draft"
    with pytest.raises(ValueError, match="status=complete"):
        run_plan(planning_state(tmp_path, store.put(bundle)), settings, store)
    bundle["status"] = "complete"
    bundle["claims"][0]["evidence"][0]["excerpt"] = "Unsupported quotation"
    with pytest.raises(ValueError, match="exact excerpt"):
        run_plan(planning_state(tmp_path, store.put(bundle), run_id="corrupt"), settings, store)


def test_manifest_cannot_import_mutable_knowledge(tmp_path, settings, store):
    ref = knowledge_fixture(tmp_path, settings, store)
    bundle = store.get(ref)
    write_json(store.path("runs/mutable-knowledge.json"), bundle)
    manifest = store.path("runs/mutable-manifest.json")
    write_json(
        manifest,
        {
            "bundle_ref": "runs/mutable-knowledge.json",
            "status": "complete",
            "revision": digest(bundle),
        },
    )
    with pytest.raises(ValueError, match="immutable"):
        resolve_reference(str(manifest), store, "bundle_ref", "complete")


def test_ineligible_claim_requires_authority_and_remains_audit_only(tmp_path, settings, store):
    ref = knowledge_fixture(tmp_path, settings, store)
    bundle = store.get(ref)
    bundle["claims"][1]["review_status"] = "ineligible"
    with pytest.raises(ValueError, match="authority decisions"):
        run_plan(planning_state(tmp_path, store.put(bundle)), settings, store)
    decision = {
        "issue_id": "authority-fixture",
        "revision": "fixture-revision",
        "action": "select_authority",
        "claim_ids": [bundle["claims"][0]["id"]],
        "rationale": "Exercise the inherited authority contract",
        "reviewer": "Synthetic fixture author",
    }
    bundle["decisions"] = [decision]
    bundle["resolved_issues"] = [
        {
            "id": decision["issue_id"],
            "revision": decision["revision"],
            "status": "resolved",
            "record_ids": [c["id"] for c in bundle["claims"]],
        }
    ]
    result, pipeline, _ = run_plan(
        planning_state(tmp_path, store.put(bundle), run_id="authority"), settings, store
    )
    rejected = next(
        o
        for o in pipeline.rows(result, "content-obligations")
        if o["record_id"] == bundle["claims"][1]["id"]
    )
    assert result["status"] == "ready_for_generation"
    assert rejected["eligibility"] == "audit_only"
    assert rejected["decision_refs"] == [decision["issue_id"]]


def test_inherited_keep_distinct_decision_cannot_be_erased(tmp_path, settings, store):
    from docgen.planning_inputs import validate_knowledge
    from docgen.reconciliation import entity_register

    bundle = store.get(knowledge_fixture(tmp_path, settings, store))
    bundle["entities"] = [
        {
            "id": key,
            "canonical_name": "Archive role",
            "aliases": [],
            "kind": "actor",
            "scope": "fixture",
            "version": "1",
            "definition": "Separate source description",
            "evidence": bundle["claims"][0]["evidence"],
            "review_status": "verified",
        }
        for key in ("e1", "e2")
    ]
    bundle["decisions"] = [
        {
            "issue_id": action,
            "revision": "fixture",
            "action": action,
            "entity_ids": ["e1", "e2"],
            "reviewer": "fixture",
            "rationale": "Deliberately contradictory identity decisions",
        }
        for action in ("keep_distinct", "merge_entities")
    ]
    bundle["resolved_issues"] = [
        {
            "id": decision["issue_id"],
            "revision": "fixture",
            "status": "resolved",
            "record_ids": ["e1", "e2"],
        }
        for decision in bundle["decisions"]
    ]
    bundle["entity_register"], bundle["canonical_entity_ids"] = entity_register(
        bundle["entities"], bundle["decisions"]
    )
    with pytest.raises(ValueError, match="keep-distinct"):
        validate_knowledge(bundle, store)


def test_bounded_context_groups_account_for_shared_source_once(store):
    from types import SimpleNamespace

    from docgen.ingestion import estimate_tokens
    from docgen.planning_helpers import bounded_context_groups, bounded_groups, evidence_context
    from docgen.storage import encode

    rows = [
        {"id": str(index), "record_id": str(index), "evidence": [{"block_id": "shared"}]}
        for index in range(30)
    ]
    inputs = SimpleNamespace(
        records_ref=store.put_table({"id": str(i), "record": "r" * 120} for i in range(30)),
        blocks_ref=store.put_table([{"id": "shared", "content": "source " * 180}]),
    )
    groups = list(bounded_context_groups(store, inputs, rows, 2048))
    naive = list(bounded_groups(rows, 2048, lambda row: evidence_context(store, inputs, [row])))
    assert len(groups) < len(naive)
    assert [row["id"] for group in groups for row in group] == [row["id"] for row in rows]
    for group in groups:
        context = evidence_context(store, inputs, group)
        assert estimate_tokens(encode(context)) <= 2048
        assert len(context["source_blocks"]) == 1


def test_lost_qualification_and_tampered_writing_context_block_finalization(
    tmp_path, settings, store
):
    bundle = knowledge_fixture(tmp_path, settings, store)
    result, pipeline, _ = run_plan(planning_state(tmp_path, bundle), settings, store)
    briefs = list(pipeline.rows(result, "section-briefs"))
    target = next(b for b in briefs if b["constraints"])
    target["constraints"] = {}
    components = pipeline.components(result)
    components["section-briefs"] = pipeline.table(briefs, "changed-briefs")
    result["components_ref"] = store.put(components)
    report = validate_plan(pipeline, result)
    assert any("qualifications" in e for e in report["errors"])
    assert any("Stale" in e or "stale" in e for e in report["errors"])


def test_brief_treatments_must_match_the_allocation_ledger(tmp_path, settings, store):
    bundle = knowledge_fixture(tmp_path, settings, store)
    result, pipeline, _ = run_plan(planning_state(tmp_path, bundle), settings, store)
    briefs = list(pipeline.rows(result, "section-briefs"))
    summary = next(b for b in briefs if b["supporting_ids"])
    key = summary["supporting_ids"][0]
    allocations = list(pipeline.rows(result, "content-allocations"))
    allocation = next(a for a in allocations if a["obligation_id"] == key)
    allocation["supporting_section_ids"].remove(summary["section_id"])
    allocation["canonical_section_id"] = summary["section_id"]
    components = pipeline.components(result)
    components["content-allocations"] = pipeline.table(allocations, "changed-allocations")
    result["components_ref"] = store.put(components)
    errors = validate_plan(pipeline, result)["errors"]
    assert any("canonical allocation" in error for error in errors)
    assert any("allocation ledger" in error for error in errors)


def test_page_cannot_move_sections_across_unit_ownership(tmp_path, settings, store):
    bundle = knowledge_fixture(tmp_path, settings, store, ("Archive", "Delivery"))
    result, pipeline, _ = run_plan(planning_state(tmp_path, bundle), settings, store)
    pages = list(pipeline.rows(result, "pages"))
    roots = [p for p in pages if p["role"] == "unit"]
    roots[0]["owner_id"] = roots[1]["owner_id"]
    components = pipeline.components(result)
    components["pages"] = pipeline.table(pages, "changed-pages")
    result["components_ref"] = store.put(components)
    assert any("Page changes section owner" in e for e in validate_plan(pipeline, result)["errors"])


def test_paid_stage_repairs_are_bounded_and_stale_review_rejected(tmp_path, settings, store):
    bundle = knowledge_fixture(tmp_path, settings, store)

    def transform(stage, payload, result):
        if stage == "plan_units":
            result.assignments = []
        return result

    result, pipeline, model = run_plan(
        planning_state(tmp_path, bundle), settings, store, PlanningFixtureModel(transform)
    )
    assert result["status"] == "review"
    assert model.calls.count("plan_units") == 3
    issue = store.get(result["issues_ref"])[0]
    decision = {
        "issue_id": issue["id"],
        "revision": "stale",
        "action": "defer",
        "reviewer": "fixture",
        "rationale": "Exercise revision binding",
    }
    with persistent_graph(pipeline) as graph:
        with pytest.raises(ValueError, match="Stale"):
            graph.invoke(
                Command(resume={"decisions": [decision]}),
                {"configurable": {"thread_id": "planning"}},
            )


def test_truncation_splits_work_and_preserves_all_obligations(tmp_path, settings, store):
    bundle = knowledge_fixture(tmp_path, settings, store, count=4)

    def transform(stage, payload, result):
        if stage == "plan_units" and len(payload["obligations"]) > 2:
            raise TruncatedOutput("Fixture split")
        return result

    result, pipeline, model = run_plan(
        planning_state(tmp_path, bundle), settings, store, PlanningFixtureModel(transform)
    )
    assert result["status"] == "ready_for_generation", result
    assert model.calls.count("plan_units") == 6
    assert len(list(pipeline.rows(result, "documentation-units"))) == 1
    assert pipeline.component(result, "validation-report")["full_treatment_count"] == 4


def test_planning_split_respects_task_admission_budget(tmp_path, settings, store):
    bundle = knowledge_fixture(tmp_path, settings, store, count=4)

    def transform(stage, payload, result):
        if stage == "plan_units":
            raise TruncatedOutput("Force a split")
        return result

    limited = settings.model_copy(update={"workload_tasks": 1})
    with pytest.raises(ModelFailure, match="Split planning queue"):
        run_plan(planning_state(tmp_path, bundle), limited, store, PlanningFixtureModel(transform))


def test_semantic_audit_repairs_upstream_stage_and_reaudits(tmp_path, settings, store):
    bundle = knowledge_fixture(tmp_path, settings, store)
    fired = []

    def transform(stage, payload, result):
        if stage == "plan_audit" and payload["obligations"] and not fired:
            fired.append(True)
            result.findings.append(
                AuditFinding(
                    kind="qualification",
                    description="Preserve approval timing locally",
                    obligation_ids=[payload["obligations"][0]["id"]],
                    section_ids=[payload["briefs"][0]["section_id"]],
                    repair_stage="write_section_briefs",
                )
            )
        return result

    result, pipeline, _ = run_plan(
        planning_state(tmp_path, bundle), settings, store, PlanningFixtureModel(transform)
    )
    assert result["status"] == "ready_for_generation", result
    assert store.get(result["repairs_ref"])["write_section_briefs"] == 1
    assert validate_plan(pipeline, result)["passed"]


@pytest.mark.parametrize(
    "path", ["../escape.md", "C:/absolute.md", "CON.md", "a\\b.md", "bad?.md", "/root.md"]
)
def test_unsafe_paths_are_rejected(path):
    with pytest.raises(ValueError):
        validate_paths([{"path": path}])


def test_case_collision_and_cycles_are_rejected():
    with pytest.raises(ValueError):
        validate_paths([{"path": "A.md"}, {"path": "a.md"}])
    with pytest.raises(ValueError, match="cycle"):
        validate_dag(["a", "b"], [("a", "b"), ("b", "a")])


def test_manifest_requires_original_workspace_objects(tmp_path, store):
    path = store.path("missing-manifest.json")
    write_json(
        path,
        {
            "status": "complete",
            "bundle_ref": "objects/missing-" + "0" * 64 + ".json",
            "revision": "unknown",
        },
    )
    with pytest.raises(ValueError, match="Missing artifact"):
        resolve_reference(str(path), store, "bundle_ref", "complete")
    outside = tmp_path / "manifest.json"
    write_json(outside, {})
    with pytest.raises(ValueError, match="Cross-workspace"):
        resolve_reference(str(outside), store, "bundle_ref", "complete")


def test_brief_forbids_unknown_fields_and_missing_explicit_boundaries():
    with pytest.raises(ValueError):
        DocumentationBrief.model_validate({"invented": True})
    with pytest.raises(ValueError):
        DocumentationBrief(unit_policy="explicit")


def test_shared_canonical_treatment_retains_every_consumer(tmp_path, settings, store):
    bundle = knowledge_fixture(tmp_path, settings, store, ("Archive", "Delivery"))

    def transform(stage, payload, result):
        if stage == "plan_units" and payload.get("mode") == "assign_to_fixed_global_units":
            result.assignments[0].owner_key = None
            result.assignments[0].consumers = [u["id"] for u in payload["fixed_units"]]
        return result

    result, pipeline, _ = run_plan(
        planning_state(tmp_path, bundle), settings, store, PlanningFixtureModel(transform)
    )
    assert result["status"] == "ready_for_generation"
    shared = next(a for a in pipeline.rows(result, "unit-assignments") if a["owner_id"] == "shared")
    assert len(shared["consuming_unit_ids"]) == 2
    allocation = next(
        a
        for a in pipeline.rows(result, "content-allocations")
        if a["obligation_id"] == shared["obligation_id"]
    )
    assert len(allocation["supporting_section_ids"]) == 3
    briefs = list(pipeline.rows(result, "section-briefs"))
    assert sum(shared["obligation_id"] in b["full_treatment_ids"] for b in briefs) == 1
    assert pipeline.component(result, "validation-report")["full_treatment_count"] == 4


def test_previous_plan_preserves_unit_identity_without_carrying_approvals(
    tmp_path, settings, store
):
    bundle = knowledge_fixture(tmp_path, settings, store, ("Archive", "Delivery"))
    first, pipeline, _ = run_plan(planning_state(tmp_path, bundle), settings, store)
    state = planning_state(tmp_path, bundle, run_id="revision-two")
    state["previous_plan"] = str(Path(first["export_path"]) / "manifest.json")
    second, revised, _ = run_plan(state, settings, store)
    assert second["status"] == "ready_for_generation"
    assert {u["id"] for u in pipeline.rows(first, "documentation-units")} == {
        u["id"] for u in revised.rows(second, "documentation-units")
    }
    assert not revised.read(second, "decisions_ref", [])
    assert revised.component(second, "navigation")["path_mappings"] == {}


def test_reviewer_unknown_retains_original_issue_and_attribution(tmp_path, settings, store):
    from conftest import FixtureModel

    from docgen.workflow import Pipeline

    source = tmp_path / "unknown.md"
    source.write_text("Archive definition [not provided](missing.md).\n", encoding="utf-8")
    config = {"configurable": {"thread_id": "unknown"}}
    with persistent_graph(Pipeline(settings, store, FixtureModel())) as graph:
        graph.invoke({"run_id": "unknown", "source": str(source), "signature": "fixture"}, config)
        issue = graph.get_state(config).interrupts[0].value["issues"][0]
        result = graph.invoke(
            Command(
                resume={
                    "decisions": [
                        {
                            "issue_id": issue["id"],
                            "revision": issue["revision"],
                            "action": "acknowledge_unknown",
                            "reviewer": "Fixture author",
                            "rationale": "Preserve the missing definition as unknown",
                        }
                    ]
                }
            ),
            config,
        )
    state = planning_state(tmp_path, result["bundle_ref"])
    planned, pipeline, _ = run_plan(
        state, settings, store, stop_after="discover_documentation_units"
    )
    obligations = list(pipeline.rows(planned, "content-obligations"))
    decision = next(o for o in obligations if o["record_kind"] == "review_decision")
    assert decision["constraints"]["review_issue"]["description"] == issue["description"]
    assert decision["constraints"]["attribution"] == {
        "kind": "reviewer",
        "reviewer": "Fixture author",
    }


def test_revision_bound_correction_revalidates_then_completes(tmp_path, settings, store):
    from docgen.planning_contracts import UnitDiscovery

    bundle = knowledge_fixture(tmp_path, settings, store)
    failures = []

    def transform(stage, payload, result):
        if stage == "plan_units" and len(failures) < 3:
            failures.append(payload)
            result.assignments = []
        return result

    state, pipeline, _ = run_plan(
        planning_state(tmp_path, bundle), settings, store, PlanningFixtureModel(transform)
    )
    issue = store.get(state["issues_ref"])[0]
    corrected = PlanningFixtureModel().call("plan_units", failures[-1], UnitDiscovery)
    decision = {
        "issue_id": issue["id"],
        "revision": issue["revision"],
        "action": "correct",
        "reviewer": "Fixture author",
        "rationale": "Restore complete owner accounting",
        "correction_ref": store.put(corrected, "review-correction"),
    }
    with persistent_graph(pipeline) as graph:
        result = graph.invoke(
            Command(resume={"decisions": [decision]}),
            {"configurable": {"thread_id": "planning"}, "recursion_limit": 10000},
        )
    assert result["status"] == "ready_for_generation"
    assert list(pipeline.rows(result, "decisions"))[0]["issue_id"] == issue["id"]
    assert list(pipeline.rows(result, "issue-history"))[0]["status"] == "resolved"


def test_exhausted_audit_accepts_component_correction_and_rebuilds_dependents(
    tmp_path, settings, store
):
    bundle = knowledge_fixture(tmp_path, settings, store)
    pending = [True]

    def transform(stage, payload, result):
        if stage == "plan_audit" and payload["obligations"] and pending[0]:
            result.findings.append(
                AuditFinding(
                    kind="qualification",
                    description="Require an explicit approval timing instruction",
                    obligation_ids=[payload["obligations"][0]["id"]],
                    section_ids=[payload["briefs"][0]["section_id"]],
                    repair_stage="write_section_briefs",
                )
            )
        return result

    state, pipeline, model = run_plan(
        planning_state(tmp_path, bundle), settings, store, PlanningFixtureModel(transform)
    )
    assert state["status"] == "review"
    calls = model.calls.count("plan_audit")
    issue = store.get(state["issues_ref"])[0]
    briefs = list(pipeline.rows(state, "section-briefs"))
    instruction = "Explain approval timing using all attached source conditions."
    for brief in briefs:
        if brief["full_treatment_ids"] or brief["supporting_ids"]:
            brief["content"]["instructions"].append(instruction)
    correction = {
        "kind": "planning_component_patch",
        "base_revision": state["review_revision"],
        "component": "section-briefs",
        "replacement_ref": pipeline.table(briefs, "corrected-briefs"),
    }
    with pytest.raises(ValueError, match="Stale component"):
        pipeline.correct_component(state, {**correction, "base_revision": "stale"})
    pending[0] = False
    with persistent_graph(pipeline) as graph:
        result = graph.invoke(
            Command(
                resume={
                    "decisions": [
                        {
                            "issue_id": issue["id"],
                            "revision": state["review_revision"],
                            "action": "correct",
                            "reviewer": "Fixture author",
                            "rationale": "Add the missing instruction and repeat dependent checks",
                            "correction_ref": store.put(correction, "component-correction"),
                        }
                    ]
                }
            ),
            {"configurable": {"thread_id": "planning"}, "recursion_limit": 10000},
        )
    assert result["status"] == "ready_for_generation"
    assert model.calls.count("plan_audit") > calls
    assert any(
        instruction in b["content"]["instructions"] for b in pipeline.rows(result, "section-briefs")
    )
    assert validate_plan(pipeline, result)["passed"]
