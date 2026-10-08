import re
from pathlib import Path

from docgen.generation_contracts import GenerationBrief
from docgen.planning import PlanningPipeline
from docgen.planning_contracts import DocumentationPlan
from docgen.planning_helpers import evidence_context, require_exact, validate_paths
from docgen.planning_inputs import resolve_reference
from docgen.planning_validation import validate_plan
from docgen.storage import digest, file_digest, read_json


def load_plan(settings, store, value):
    ref, raw = resolve_reference(value, store, "plan_ref", "ready_for_generation")
    plan = DocumentationPlan.model_validate(raw)
    if not re.fullmatch(r"[a-f0-9]{64}", plan.signature):
        raise ValueError("Unsupported planning workflow signature")
    if plan.revision != digest([plan.inputs_ref, plan.components]):
        raise ValueError("Plan component revision mismatch")
    adapter = PlanningPipeline(settings, store, None)
    state = {
        "inputs_ref": plan.inputs_ref,
        "components_ref": store.put(plan.components, "plan-components"),
    }
    issues = list(store.iter_table(plan.components["issues"]))
    if any(i["status"] == "open" and i["severity"] == "blocking" for i in issues):
        raise ValueError("Unresolved blocking plan issue")
    report = validate_plan(adapter, state)
    if report["errors"]:
        raise ValueError("Invalid generation plan: " + "; ".join(report["errors"]))
    inputs = adapter.inputs(state)
    if inputs.signature != plan.signature:
        raise ValueError("Plan and frozen input signatures differ")
    if digest(store.get_object(inputs.knowledge_ref)) != inputs.knowledge_revision:
        raise ValueError("Stale knowledge revision")
    knowledge = store.get_object(inputs.knowledge_ref)
    if knowledge["signature"] != inputs.knowledge_signature:
        raise ValueError("Stale knowledge signature")
    if knowledge["snapshot_ref"] != inputs.snapshot_ref:
        raise ValueError("Plan does not use its frozen knowledge snapshot")
    store.get_object(inputs.selection_ref)
    if (
        digest(bytes.fromhex(store.get_object(inputs.template_ref)["bytes_hex"]))
        != inputs.template_hash
    ):
        raise ValueError("Stale template revision")
    pages = list(adapter.rows(state, "pages"))
    validate_paths(pages)
    jobs = list(adapter.rows(state, "writing-jobs"))
    for job in jobs:
        context = store.get_object(job["context_ref"])
        expected = evidence_context(
            store, inputs, adapter.obligations(state, job["obligation_ids"])
        )
        if context["originals"] != expected:
            raise ValueError("Writing context differs from exact eligible evidence")
        if context["knowledge_revision"] != inputs.knowledge_revision:
            raise ValueError("Stale writing job knowledge revision")
        inherited = context["inherited_references"]
        if inherited.get("planning_inputs", plan.inputs_ref) != plan.inputs_ref:
            raise ValueError("Writing job references another planning revision")
        expected_refs = {
            "knowledge": inputs.knowledge_ref,
            "selection": inputs.selection_ref,
            "source_blocks": inputs.blocks_ref,
            "phase_1_coverage": inputs.coverage_ref,
            "template": inputs.template_ref,
            **plan.components,
        }
        for key, reference in inherited.items():
            if key != "planning_inputs" and reference != expected_refs.get(key):
                raise ValueError("Writing job inherits a stale component reference")
        if context["metadata"] != inputs.brief.model_dump():
            raise ValueError("Writing job changes the frozen documentation brief")
    if not value.startswith("objects/"):
        manifest_path = Path(value).resolve()
        manifest = read_json(manifest_path)
        for name, checksum in manifest["files"].items():
            path = (manifest_path.parent / name).resolve()
            if not path.is_relative_to(manifest_path.parent) or file_digest(path) != checksum:
                raise ValueError("Corrupted or unsafe plan export")
    return ref, raw, inputs, report


def writing_order(jobs):
    remaining = {job["id"]: job for job in jobs}
    completed, ordered = set(), []
    while remaining:
        ready = sorted(
            (j for j in remaining.values() if set(j["hard_dependencies"]) <= completed),
            key=lambda j: (j["assembly_order"], j["id"]),
        )
        if not ready:
            raise ValueError("Writing dependency cycle or missing dependency")
        job = ready[0]
        completed.add(job["id"])
        ordered.append(job["id"])
        del remaining[job["id"]]
    return ordered


def freeze_inputs(pipeline, state):
    ref, plan, inputs, report = load_plan(pipeline.settings, pipeline.store, state["plan"])
    brief = GenerationBrief.model_validate(
        read_json(Path(state["brief"])) if state.get("brief") else {}
    )
    jobs = list(pipeline.store.iter_table(plan["components"]["writing-jobs"]))
    canonical = [key for job in jobs for key in job["output_contract"]["full_treatment_ids"]]
    expected = [
        a["obligation_id"]
        for a in pipeline.store.iter_table(plan["components"]["content-allocations"])
        if a["disposition"] == "full_treatment"
    ]
    require_exact(canonical, expected, "Canonical fragment ownership")
    return pipeline.store.put(
        {
            "plan_ref": ref,
            "plan_revision": digest(plan),
            "planning_inputs_ref": plan["inputs_ref"],
            "knowledge_revision": inputs.knowledge_revision,
            "template_hash": inputs.template_hash,
            "generation_brief": brief,
            "writing_order": writing_order(jobs),
            "validation": report,
            "signature": state["signature"],
            "preview": state.get("preview", False),
            "cache_mode": state.get("cache_mode", "off"),
        },
        "generation-inputs",
    )
