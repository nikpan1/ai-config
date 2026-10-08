import os
import tempfile
from pathlib import Path

from langgraph.graph import END

from docgen.planning_contracts import DocumentationPlan
from docgen.planning_helpers import validate_dag
from docgen.planning_validation import validate_plan
from docgen.storage import (
    atomic_write,
    digest,
    encode,
    file_digest,
    read_json,
    write_json,
    write_jsonl,
)


def evidence_rows(pipeline, state):
    inputs = pipeline.inputs(state)
    coverage = {r["block_id"]: r for r in pipeline.store.iter_table(inputs.coverage_ref)}
    snapshot = pipeline.store.get(inputs.snapshot_ref)
    files = {r["path"]: r for r in snapshot["inventory"]}
    for obligation in pipeline.rows(state, "content-obligations"):
        for evidence in obligation["evidence"]:
            block = pipeline.store.table_rows(inputs.blocks_ref, [evidence["block_id"]])[0]
            yield {
                "id": digest([obligation["id"], evidence]),
                "obligation_id": obligation["id"],
                "record_id": obligation["record_id"],
                "block_id": block["id"],
                "excerpt": evidence["excerpt"],
                "path": block["path"],
                "snapshot_ref": files[block["path"]].get("ref"),
                "headings": block["headings"],
                "line_start": block["line_start"],
                "line_end": block["line_end"],
                "table_id": block["table_id"],
                "table_row": block["table_row"],
                "table_columns": block["table_columns"],
                "phase_1_disposition": coverage[block["id"]],
                "attribution": obligation["constraints"].get("attribution", {"kind": "source"}),
            }


def boundary_report(pipeline, state):
    lines = ["# Functional unit boundary report", ""]
    assignments = list(pipeline.rows(state, "unit-assignments"))
    for unit in pipeline.rows(state, "documentation-units"):
        lines.extend(
            [
                f"## {unit['title']} ({unit['id']})",
                "",
                f"Purpose: {unit['purpose']}",
                "",
                f"Outcome: {unit['outcome']}",
                "",
                f"Scope: {unit['scope']}",
                "",
                f"Verification: {unit['verification_status']}",
                "",
                f"Rationale: {unit['discovery_rationale']}",
                "",
                f"Alternative: {unit['alternative']}",
                "",
                "Boundaries: " + "; ".join(unit["boundaries"]),
                "",
                "Dependencies: " + "; ".join(unit["dependencies"]),
                "",
                "Evidence obligations: " + ", ".join(unit["evidence_obligation_ids"]),
                "",
                f"Owned obligations: {sum(a['owner_id'] == unit['id'] for a in assignments)}",
                "",
            ]
        )
    return "\n".join(lines)


def readable_export(pipeline, state, destination, report):
    inputs = pipeline.inputs(state)
    pages = list(pipeline.rows(state, "pages"))
    source_files = {
        row["path"]: row for row in pipeline.store.get(inputs.snapshot_ref)["inventory"]
    }
    sections = {s["id"]: s for s in pipeline.rows(state, "logical-sections")}
    page_lookup = {page["id"]: page for page in pages}
    section_pages = {section: page for page in pages for section in page["section_ids"]}
    briefs = list(pipeline.rows(state, "section-briefs"))
    lines = [
        "# Documentation plan",
        "",
        inputs.brief.purpose,
        "",
        f"Knowledge revision: `{inputs.knowledge_revision}`",
        "",
        f"Template SHA-256: `{inputs.template_hash}`",
        "",
        f"Language: {inputs.brief.language}; audience: {inputs.brief.audience}",
        "",
        f"Unit policy: {inputs.brief.unit_policy}; delivery: {inputs.brief.delivery_mode}",
        "",
        f"Product name: {inputs.brief.product_name or 'Unknown'}",
        "",
        f"Human review date: {inputs.brief.last_reviewed or 'Unknown'}",
        "",
        "Status: ready_for_generation. This is a writing plan; final prose is not generated.",
        "",
        "## Functional units",
        "",
    ]
    for unit in pipeline.rows(state, "documentation-units"):
        root = next(p for p in pages if p["owner_id"] == unit["id"] and p["role"] == "unit")
        lines.extend([f"- [{unit['title']}](page-briefs/{root['id']}.md): {unit['purpose']}"])
    lines.extend(
        [
            "",
            "[Boundary evidence and alternatives](unit-boundary-report.md)",
            "",
            "## Collection and reference pages",
            "",
            "[Complete page index and subdivision rationale](page-index.md)",
            "",
        ]
    )
    page_index = ["# Complete page index", "", "[Plan index](documentation-plan.md)", ""]
    for page in pages:
        entry = (
            f"- `{page['path']}` — [{page['title']}](page-briefs/{page['id']}.md) "
            f"({page['role']}): {page['rationale']}"
        )
        page_index.append(entry)
        if page["role"] in {"collection", "shared", "sources"}:
            lines.append(entry)
        content = [
            f"# {page['title']} — page brief",
            "",
            f"Planned path: `{page['path']}`",
            "",
            f"Owner: {page['owner_id']}; template instance: {page['template_instance_id']}",
            "",
            f"Reader task: {page['reader_task']}",
            "",
            f"Scope: {page['scope']}",
            "",
            "[Plan index](../documentation-plan.md)",
            "",
        ]
        if page["parent_id"]:
            parent = page_lookup[page["parent_id"]]
            content.extend([f"[Parent: {parent['title']}]({parent['id']}.md)", ""])
        children = [child for child in pages if child["parent_id"] == page["id"]]
        if children:
            content.extend(["## Child pages", ""])
            content.extend(
                f"- [{child['title']}]({child['id']}.md): {child['reader_task']}"
                for child in children
            )
            content.append("")
        for section_id in page["section_ids"]:
            section = sections[section_id]
            content.extend(
                [
                    f'<a id="{section_id}"></a>',
                    f"## {section['title']}",
                    "",
                    f"Reader question: {section['reader_question']}",
                    "",
                ]
            )
            for brief in (b for b in briefs if b["section_id"] == section_id):
                content.extend(
                    f"- {instruction}" for instruction in brief["content"]["instructions"]
                )
                content.extend(["", "Completion checks:", ""])
                content.extend(f"- {check}" for check in brief["content"]["completion_checks"])
                if brief["content"]["unknowns"]:
                    content.extend(["", "Unknowns:", ""])
                    content.extend(f"- {item}" for item in brief["content"]["unknowns"])
                content.extend(
                    [
                        "",
                        "Canonical obligations: " + ", ".join(brief["full_treatment_ids"]),
                        "",
                        "Qualified supporting mentions: " + ", ".join(brief["supporting_ids"]),
                        "",
                    ]
                )
                if brief["canonical_links"]:
                    content.extend(["Canonical references:", ""])
                    for target in sorted(set(brief["canonical_links"].values())):
                        target_page = section_pages[target]
                        content.append(
                            f"- [{sections[target]['title']}]({target_page['id']}.md#{target})"
                        )
                    content.append("")
                for key in brief["full_treatment_ids"] + brief["supporting_ids"]:
                    obligation = pipeline.obligations(state, [key])[0]
                    record = pipeline.store.table_rows(
                        inputs.records_ref, [obligation["record_id"]]
                    )[0]
                    content.extend(
                        [f"### Required record `{key}`", "", "```json", encode(record), "```", ""]
                    )
                for evidence in brief["evidence"]:
                    block = pipeline.store.table_rows(inputs.blocks_ref, [evidence["block_id"]])[0]
                    source_ref = source_files[block["path"]].get("ref")
                    source_link = (
                        Path(
                            os.path.relpath(
                                pipeline.store.path(source_ref), destination / "page-briefs"
                            )
                        ).as_posix()
                        if source_ref
                        else "../evidence-index.jsonl"
                    )
                    content.append(
                        f"- Source: [{block['path']}:{block['line_start']}](<{source_link}>) "
                        f"(`{block['id']}`), exact excerpt: {evidence['excerpt'].strip()}"
                    )
                content.extend(
                    [
                        "",
                        "Tables and supported diagram specifications:",
                        "",
                        "```json",
                        encode(
                            {
                                "tables": brief["content"]["tables"],
                                "diagrams": brief["content"]["diagrams"],
                            }
                        ),
                        "```",
                        "",
                    ]
                )
        atomic_write(destination / "page-briefs" / f"{page['id']}.md", "\n".join(content))
    atomic_write(destination / "page-index.md", "\n".join(page_index) + "\n")
    lines.extend(
        [
            "",
            "## Coverage and known gaps",
            "",
            f"All-inventory obligations: {report['inventory_count']}; "
            f"in-scope canonical treatments: {report['full_treatment_count']}"
            f"/{report['in_scope_count']}.",
            "",
            "Disposition counts: " + encode(report["disposition_counts"]),
            "",
            "See section briefs for attributed unknowns and local qualifications. "
            "See content-allocations.jsonl for explicit exclusions and audit-only material.",
            "",
            "Semantic checks use automated model audits; manual review has not been performed. "
            "Two-million-token end-to-end capacity remains unvalidated.",
            "",
            "## Writing order",
            "",
        ]
    )
    jobs = list(pipeline.rows(state, "writing-jobs"))
    order = validate_dag(
        [j["id"] for j in jobs], [(d, j["id"]) for j in jobs for d in j["hard_dependencies"]]
    )
    lines.append(
        "Complete canonical details, then unit overviews and summaries, then the collection guide. "
        "Contexts resolve in writing-jobs.jsonl; navigation order is independent of writing order."
    )
    atomic_write(destination / "documentation-plan.md", "\n".join(lines) + "\n")
    write_json(destination / "writing-order.json", order)


def finalize(pipeline, state):
    report = validate_plan(pipeline, state, require_audit=True)
    if report["errors"]:
        return pipeline.review_gate(
            state, "finalize_plan", "structural_integrity", "; ".join(report["errors"])
        )
    components = pipeline.components(state)
    components["validation-report"] = pipeline.store.put(report, "plan-validation")
    components["evidence-index"] = pipeline.table(evidence_rows(pipeline, state), "evidence-index")
    components["issues"] = pipeline.table(pipeline.read(state, "issues_ref", []), "issues")
    components["decisions"] = pipeline.table(pipeline.read(state, "decisions_ref", []), "decisions")
    decisions = {d["issue_id"]: d for d in pipeline.read(state, "decisions_ref", [])}
    components["issue-history"] = pipeline.table(
        (
            {**issue, "status": "resolved" if issue["id"] in decisions else issue["status"]}
            for issue in pipeline.read(state, "issue_history_ref", [])
        ),
        "issue-history",
    )
    components["phase-1-coverage"] = pipeline.inputs(state).coverage_ref
    inputs = pipeline.inputs(state)
    revision = digest([state["inputs_ref"], components])
    plan = DocumentationPlan(
        revision=revision,
        signature=state["signature"],
        inputs_ref=state["inputs_ref"],
        components=components,
        unit_policy=inputs.brief.unit_policy,
        delivery_mode=inputs.brief.delivery_mode,
        status="ready_for_generation",
        limitations=report["limitations"],
    )
    ref = pipeline.store.put(plan, "documentation-plan")
    destination = pipeline.store.path(f"runs/{state['run_id']}/documentation-plan/{digest(plan)}")
    if destination.exists():
        manifest = read_json(destination / "manifest.json")
        if manifest["plan_ref"] != ref:
            raise ValueError("Existing immutable plan export differs")
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=".export-", dir=destination.parent))
        write_json(temporary / "documentation-plan.json", plan)
        write_json(temporary / "planning-inputs.json", inputs)
        for key, component_ref in components.items():
            value = pipeline.store.get(component_ref)
            if "parts" in value and "count" in value:
                write_jsonl(temporary / f"{key}.jsonl", pipeline.store.iter_table(component_ref))
            else:
                write_json(temporary / f"{key}.json", value)
        atomic_write(
            temporary / "template.md",
            bytes.fromhex(pipeline.store.get(inputs.template_ref)["bytes_hex"]),
        )
        atomic_write(temporary / "unit-boundary-report.md", boundary_report(pipeline, state))
        atomic_write(
            temporary / "review-report.md",
            "# Planning review\n\nNo open blocking issues. "
            "Automatic structural and semantic checks completed. Manual review not performed.\n",
        )
        readable_export(pipeline, state, temporary, report)
        hashes = {
            path.relative_to(temporary).as_posix(): file_digest(path)
            for path in temporary.rglob("*")
            if path.is_file()
        }
        write_json(
            temporary / "manifest.json",
            {
                "schema_version": "1",
                "workflow": "documentation_planning",
                "plan_ref": ref,
                "revision": digest(plan),
                "planning_revision": revision,
                "status": "ready_for_generation",
                "inputs_ref": state["inputs_ref"],
                "components": components,
                "files": hashes,
            },
        )
        os.replace(temporary, destination)
    return {
        "plan_ref": ref,
        "export_path": str(destination),
        "status": "ready_for_generation",
        "components_ref": pipeline.store.put(components, "plan-components"),
        "route": END,
    }
