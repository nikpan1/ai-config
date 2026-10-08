from collections import Counter

from docgen.planning_contracts import (
    BriefProposal,
    ContentAllocation,
    ContentObligation,
    DocumentationUnit,
    LogicalSection,
    NavigationPlan,
    PagePlan,
    SectionBrief,
    TemplateContract,
    TemplateInstance,
    UnitAssignment,
    WritingJob,
)
from docgen.planning_helpers import require_exact, validate_dag, validate_paths
from docgen.planning_inputs import validate_knowledge
from docgen.planning_layout import validate_brief
from docgen.storage import digest

TABLE_SCHEMAS = {
    "content-obligations": ContentObligation,
    "documentation-units": DocumentationUnit,
    "unit-assignments": UnitAssignment,
    "template-instances": TemplateInstance,
    "logical-sections": LogicalSection,
    "content-allocations": ContentAllocation,
    "pages": PagePlan,
    "section-briefs": SectionBrief,
    "writing-jobs": WritingJob,
}


def validate_plan(pipeline, state, require_audit=True):
    errors = []

    def check(description, action):
        try:
            action()
        except (ValueError, KeyError, TypeError, OSError) as error:
            errors.append(f"{description}: {error}")

    components = pipeline.components(state)
    inputs = pipeline.inputs(state)
    check(
        "Knowledge integrity",
        lambda: validate_knowledge(pipeline.store.get(inputs.knowledge_ref), pipeline.store),
    )
    rows = {}
    for key, schema in TABLE_SCHEMAS.items():
        rows[key] = list(pipeline.rows(state, key))
        for row in rows[key]:
            check(key, lambda row=row, schema=schema: schema.model_validate(row))
        ids = [r["id"] for r in rows[key]]
        check(key + " IDs", lambda ids=ids: require_exact(ids, set(ids), "Unique identity"))
    obligations = {r["id"]: r for r in rows["content-obligations"]}
    units = {r["id"]: r for r in rows["documentation-units"]}
    assignments = {r["obligation_id"]: r for r in rows["unit-assignments"]}
    allocations = {r["obligation_id"]: r for r in rows["content-allocations"]}
    sections = {r["id"]: r for r in rows["logical-sections"]}
    pages = {r["id"]: r for r in rows["pages"]}
    briefs = {r["id"]: r for r in rows["section-briefs"]}
    jobs = {r["id"]: r for r in rows["writing-jobs"]}
    instances = {r["unit_id"]: r for r in rows["template-instances"]}
    check(
        "Obligation inventory",
        lambda: require_exact(
            [o["record_id"] for o in obligations.values()],
            [r["id"] for r in pipeline.store.iter_table(inputs.records_ref)],
            "All original records",
        ),
    )
    check(
        "Unit ownership",
        lambda: require_exact(
            [a["obligation_id"] for a in rows["unit-assignments"]],
            obligations,
            "One owner per obligation",
        ),
    )
    check(
        "Content allocation",
        lambda: require_exact(
            [a["obligation_id"] for a in rows["content-allocations"]],
            obligations,
            "One disposition per obligation",
        ),
    )
    check(
        "Template instances",
        lambda: require_exact(
            [i["unit_id"] for i in rows["template-instances"]], units, "One instance per unit"
        ),
    )
    contract = TemplateContract.model_validate(pipeline.component(state, "template-contract"))
    template = pipeline.store.get(inputs.template_ref)
    if bytes.fromhex(template["bytes_hex"]).decode("utf-8") != template["text"]:
        errors.append("Template bytes differ from parsed text")
    if digest(bytes.fromhex(template["bytes_hex"])) != inputs.template_hash:
        errors.append("Template checksum mismatch")
    if contract.template_hash != inputs.template_hash:
        errors.append("Contract uses a different template")
    required = {r.span_id for r in contract.rules if r.required}
    spans = {s.id: s for s in contract.spans}
    treatment_counts = Counter(
        key for brief in briefs.values() for key in brief["full_treatment_ids"]
    )
    for identifier, obligation in obligations.items():
        assignment, allocation = assignments.get(identifier), allocations.get(identifier)
        if not assignment or not allocation:
            continue
        if allocation["assignment_id"] != assignment["id"]:
            errors.append(f"Allocation owner mismatch: {identifier}")
        if set(assignment["consuming_unit_ids"]) - set(units):
            errors.append(f"Missing consuming unit: {identifier}")
        record = pipeline.store.table_rows(inputs.records_ref, [obligation["record_id"]])[0][
            "record"
        ]
        expected_fields = [k for k, v in record.items() if v not in (None, [], "", {})]
        if obligation["required_fields"] != expected_fields:
            errors.append(f"Lost record fields: {identifier}")
        if assignment["disposition"] == "included":
            target = sections.get(allocation["canonical_section_id"])
            if not target or target["owner_id"] != assignment["owner_id"]:
                errors.append(
                    f"Canonical treatment missing or assigned to another owner: {identifier}"
                )
            if allocation["disposition"] != "full_treatment" or treatment_counts[identifier] != 1:
                errors.append(f"Exactly one full treatment required: {identifier}")
            if obligation["eligibility"] != "eligible":
                errors.append(f"Ineligible record included: {identifier}")
        else:
            if not assignment["reason"] or not allocation["reason"] or treatment_counts[identifier]:
                errors.append(f"Invalid non-content disposition: {identifier}")
            if allocation["canonical_section_id"] is not None:
                errors.append(f"Non-content item has a canonical section: {identifier}")
            if (
                assignment["disposition"] == "out_of_scope"
                and obligation["eligibility"] == "eligible"
                and not inputs.brief.hard_scope
            ):
                errors.append(f"Exclusion is not authorized: {identifier}")
        for mention in allocation["supporting_section_ids"]:
            if mention not in sections or not any(
                b["section_id"] == mention and identifier in b["supporting_ids"]
                for b in briefs.values()
            ):
                errors.append(f"Missing supporting mention: {identifier}")
        for consumer in assignment["consuming_unit_ids"]:
            if not any(
                sections[s]["owner_id"] == consumer for s in allocation["supporting_section_ids"]
            ):
                errors.append(f"Shared consumer has no local qualified mention: {identifier}")
    for unit in units.values():
        if unit["verification_status"] != "verified" or not unit["evidence_obligation_ids"]:
            errors.append(f"Unverified functional unit: {unit['id']}")
        if set(unit["evidence_obligation_ids"]) - set(obligations):
            errors.append(f"Missing unit boundary evidence: {unit['id']}")
    compliance = []
    for unit_id, instance in instances.items():
        bound = [s for s in sections.values() if s["template_instance_id"] == instance["id"]]
        bound_spans = {s["template_span_id"] for s in bound}
        for span_id in required:
            cursor = spans[span_id]
            while cursor.id not in bound_spans and cursor.parent_id:
                cursor = spans[cursor.parent_id]
            present = cursor.id in bound_spans
            compliance.append(
                {
                    "unit_id": unit_id,
                    "instance_id": instance["id"],
                    "span_id": span_id,
                    "status": "fulfilled" if present else "missing",
                }
            )
            if not present:
                errors.append(f"Required template obligation missing in {unit_id}: {span_id}")
        unit_roots = [p for p in pages.values() if p["owner_id"] == unit_id and p["role"] == "unit"]
        if len(unit_roots) != 1:
            errors.append(f"Unit must have one template root: {unit_id}")
        else:
            expected = [
                s["id"] for s in sorted(bound, key=lambda s: s["order"]) if s["parent_id"] is None
            ]
            actual = [s for s in unit_roots[0]["section_ids"] if sections[s]["parent_id"] is None]
            if actual != expected:
                errors.append(f"Template heading order or root placement changed: {unit_id}")
    check("Safe paths", lambda: validate_paths(pages.values()))
    check(
        "Section ownership",
        lambda: require_exact(
            [s for p in pages.values() for s in p["section_ids"]],
            sections,
            "Every section on one page",
        ),
    )
    edges = [(p["parent_id"], p["id"]) for p in pages.values() if p["parent_id"]]
    for page in pages.values():
        for identifier in page["section_ids"]:
            section = sections.get(identifier)
            if section and (
                section["owner_id"] != page["owner_id"]
                or section["template_instance_id"] != page["template_instance_id"]
            ):
                errors.append(f"Page changes section owner or template binding: {identifier}")
    check("Page hierarchy", lambda: validate_dag(pages, edges))
    if sum(p["parent_id"] is None for p in pages.values()) != 1:
        errors.append("Page hierarchy is not rooted")
    navigation = NavigationPlan.model_validate(pipeline.component(state, "navigation"))
    if navigation.root not in pages or set(navigation.anchors) != set(sections):
        errors.append("Incomplete navigation anchors or root")
    for link in navigation.links:
        if link.source not in set(pages) | set(sections) or link.target not in set(pages) | set(
            sections
        ):
            errors.append("Navigation target does not exist")
    for brief in briefs.values():
        section = sections.get(brief["section_id"])
        page = pages.get(brief["page_id"])
        if not section or not page or brief["section_id"] not in page["section_ids"]:
            errors.append(f"Brief binding invalid: {brief['id']}")
        ids = brief["full_treatment_ids"] + brief["supporting_ids"]
        check(
            "Brief identities",
            lambda ids=ids, brief=brief: require_exact(
                brief["content"]["checked_obligation_ids"], ids, "Brief owned content"
            ),
        )
        check(
            "Tables and diagrams",
            lambda brief=brief, ids=ids: validate_brief(
                BriefProposal.model_validate(brief["content"]), ids
            ),
        )
        for key in ids:
            if key not in obligations:
                errors.append(f"Brief invented obligation: {key}")
                continue
            allocation = allocations.get(key, {})
            if key in brief["full_treatment_ids"] and (
                allocation.get("canonical_section_id") != brief["section_id"]
            ):
                errors.append(f"Full treatment differs from its canonical allocation: {key}")
            if key in brief["supporting_ids"] and (
                brief["section_id"] not in allocation.get("supporting_section_ids", [])
            ):
                errors.append(f"Supporting treatment missing from allocation ledger: {key}")
            if brief["constraints"].get(key) != obligations[key]["constraints"]:
                errors.append(f"Detached or changed qualifications: {key}")
            if (
                key in brief["supporting_ids"]
                and brief["canonical_links"].get(key) != allocations[key]["canonical_section_id"]
            ):
                errors.append(f"Supporting mention lacks canonical link: {key}")
        expected_evidence = [
            e for key in ids if key in obligations for e in obligations[key]["evidence"]
        ]
        if Counter(map(digest, brief["evidence"])) != Counter(map(digest, expected_evidence)):
            errors.append(f"Brief evidence was changed: {brief['id']}")
    if {b["section_id"] for b in briefs.values()} != set(sections):
        errors.append("Some sections have no detailed brief")
    check(
        "Writing dependency graph",
        lambda: validate_dag(
            jobs, [(dep, job["id"]) for job in jobs.values() for dep in job["hard_dependencies"]]
        ),
    )
    for brief in briefs.values():
        owned_jobs = [j for j in jobs.values() if j["brief_id"] == brief["id"]]
        if not owned_jobs:
            errors.append(f"No writing job for brief {brief['id']}")
        check(
            "Fragment assembly",
            lambda owned_jobs=owned_jobs, brief=brief: require_exact(
                [key for job in owned_jobs for key in job["obligation_ids"]],
                brief["full_treatment_ids"] + brief["supporting_ids"],
                "Complete nonoverlapping fragments",
            ),
        )
    for job in jobs.values():
        if job["estimated_input_tokens"] > pipeline.settings.writing_tokens:
            errors.append(f"Unbounded writing job: {job['id']}")
        context = pipeline.store.get(job["context_ref"])
        if context["owned_obligation_ids"] != job["obligation_ids"] or context[
            "brief"
        ] != briefs.get(job["brief_id"]):
            errors.append(f"Stale or incomplete writing context: {job['id']}")
    audit_count = 0
    if require_audit:
        if "semantic-audit" not in components or "boundary-audit" not in components:
            errors.append("Required independent audits are incomplete")
        else:
            audits = list(pipeline.rows(state, "semantic-audit"))
            audit_count = len(audits)
            for brief in briefs.values():
                audited = [a for a in audits if a["brief_id"] == brief["id"]]
                if not audited or any(
                    a["brief_revision"] != digest(brief) or a["findings"] for a in audited
                ):
                    errors.append(f"Missing, stale or failed audit: {brief['id']}")
                checked = [key for a in audited for key in a["checked_obligation_ids"]]
                check(
                    "Audit obligation accounting",
                    lambda checked=checked, brief=brief: require_exact(
                        checked,
                        brief["full_treatment_ids"] + brief["supporting_ids"],
                        "Audited brief",
                    ),
                )
    if pipeline.read(state, "issues_ref", []):
        errors.append("Open planning issues remain")
    counts = Counter(a["disposition"] for a in allocations.values())
    per_unit = {}
    for owner in [*units, "shared"]:
        owned = [
            a
            for a in assignments.values()
            if a["owner_id"] == owner and a["disposition"] == "included"
        ]
        per_unit[owner] = {
            "owned_obligations": len(owned),
            "full_treatments": sum(treatment_counts[a["obligation_id"]] == 1 for a in owned),
            "consumed_shared_obligations": sum(
                owner in a["consuming_unit_ids"] for a in assignments.values()
            ),
        }
    included_count = sum(a["disposition"] == "included" for a in assignments.values())
    full_count = sum(
        treatment_counts[a["obligation_id"]] == 1
        for a in assignments.values()
        if a["disposition"] == "included"
    )
    return {
        "schema_version": "1",
        "errors": errors,
        "passed": not errors,
        "input_revision": inputs.knowledge_revision,
        "component_revision": digest(components),
        "inventory_count": len(obligations),
        "disposition_counts": dict(counts),
        "in_scope_count": included_count,
        "full_treatment_count": full_count,
        "coverage_percent": 100 * full_count / included_count if included_count else 100,
        "per_unit": per_unit,
        "template_compliance": compliance,
        "units": len(units),
        "pages": len(pages),
        "sections": len(sections),
        "writing_jobs": len(jobs),
        "completed_audit_batches": audit_count,
        "manual_review": "not_performed",
        "capacity_two_million_tokens": "unvalidated",
        "limitations": [
            "Model audits are evidence, not proof of semantic completeness",
            "Editorial grouping may vary across independent model runs",
        ],
    }
