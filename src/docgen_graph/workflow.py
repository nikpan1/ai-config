import json
import os
import re
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from difflib import SequenceMatcher
from importlib.resources import files
from pathlib import Path
from time import monotonic
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from docgen_graph.assets import asset_filename, validate_asset, verify_bundle
from docgen_graph.authoring.template import (
    bind_plan_sections,
    document_title,
    number_generated_headings,
)
from docgen_graph.authoring.tools import AuthoringTools, declarations
from docgen_graph.code_analysis import stages as code_stages
from docgen_graph.contracts import (
    AuditDraft,
    DocumentExtractionDraft,
    EditDraft,
    PagePlanDraft,
    SectionDraft,
)
from docgen_graph.documentation_contracts import AspectInventory, SourceAudit
from docgen_graph.evidence_contracts import (
    DeltaVerification,
    EvidenceLocator,
    EvidenceQuery,
    KnowledgeDelta,
    SourceCoverageItem,
)
from docgen_graph.ingestion import inventory, snapshot_inputs
from docgen_graph.knowledge import KnowledgeGraph, normalized_assertion
from docgen_graph.model import implementation_signature
from docgen_graph.quality import (
    compile_requirements,
    content_groups,
    content_units,
    diagram_element_ids,
    diagram_source,
    duplicate_risks,
    placement_records,
    render_visuals,
    repetition_report,
    section_anchor,
    validate_quality_plan,
    validate_template_output,
    validate_visual_output,
    visual_evidence_ids,
)
from docgen_graph.source_coverage import (
    audit_decisions,
    coverage_report,
    editorial_findings,
    validate_aspect_inventory,
)
from docgen_graph.source_links import (
    CITATION_GROUP,
    citation_labels,
    normalize_citation_syntax,
    normalize_section_links,
    select_text_fragment,
    source_url_from_markdown,
    text_fragment_url,
    visible_html_text,
)
from docgen_graph.stages import STEPS, StageArtifacts
from docgen_graph.storage import ArtifactStore, digest


class PipelineState(TypedDict, total=False):
    source_aspects_ref: str
    source_decisions_ref: str
    source_non_substantive_ref: str
    source_aspect_index: int
    source_audit_index: int
    pending_document_ref: str
    source_coverage_ref: str
    authoring_ref: str
    authoring_result_ref: str
    authoring_context_ref: str
    evidence_revision: str
    authoring_return: str
    knowledge_delta_ref: str
    knowledge_revision_ref: str
    unresolved_ref: str
    code_scope_ref: str
    code_history_ref: str
    code_provenance_ref: str
    code_candidate_ref: str
    verified_code_ref: str
    classified_code_ref: str
    code_classification_verified_ref: str
    code_relations_ref: str
    mode: str
    policy_version: str
    stage_record: dict
    automatic_issue_attempts: int
    completion_status: str
    run_id: str
    docs: str
    code: str
    template: str
    brief: str
    snapshot_ref: str
    runtime_signature: str
    inventory_ref: str
    code_index: int
    document_index: int
    graph_index: int
    section_index: int
    unit_index: int
    edit_index: int
    attempt: int
    draft_ref: str
    feedback_ref: str
    assertions_ref: str
    exclusions_ref: str
    graph_revision: str
    template_ref: str
    plan_ref: str
    plan_hash: str
    plan_feedback: str
    plan_packets_ref: str
    plan_packet_index: int
    approval_ref: str
    packet_ref: str
    written_ref: str
    assembled_ref: str
    edited_ref: str
    edit_queue_ref: str
    audit_attempt: int
    candidate_ref: str
    candidate_manifest_hash: str
    release_ref: str
    release_feedback: str
    review_error: str
    issue_ref: str
    issue_return: str
    route: str
    status: str


def _sections(template: str) -> list[str]:
    return [
        match.group(1).strip()
        for line in template.splitlines()
        if (match := re.match(r"^##\s+(.+)$", line)) and "[" not in match.group(1)
    ]


def _chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _markdown_changes(original: str, edited: str) -> tuple[str, str]:
    before, after = original.splitlines(), edited.splitlines()
    original_parts, edited_parts = [], []
    for group in SequenceMatcher(None, before, after, autojunk=False).get_grouped_opcodes(2):
        changed_lines = [
            line
            for tag, start, end, new_start, new_end in group
            if tag != "equal"
            for line in before[start:end] + after[new_start:new_end]
        ]
        if not any(line.strip() for line in changed_lines):
            continue
        original_parts.append("\n".join(before[group[0][1] : group[-1][2]]))
        edited_parts.append("\n".join(after[group[0][3] : group[-1][4]]))
    return "\n\n".join(original_parts), "\n\n".join(edited_parts)


def _needs_source_context(text: str) -> bool:
    return bool(
        re.search(
            r"^\s*(?:(?:[-*+>]|\d+[.)]|#{1,6})\s+)?"
            r"(?:both|these|those|the same|it|they|this|that|above|following)\b"
            r"|\bas (?:described|defined|noted) above\b"
            r"|\bthe (?:previous|preceding) (?:section|rule|paragraph)\b",
            text,
            re.I,
        )
    )


def _section_body(title: str, markdown: str) -> str:
    lines = []
    fenced = False
    for line in markdown.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        match = None if fenced else re.match(r"^#{1,2}\s+(.+)$", line)
        if match and match.group(1).strip().casefold() == title.casefold():
            continue
        lines.append(f"### {match.group(1)}" if match else line)
    return "\n".join(lines).strip()


def _bounded_evidence_packet(packet: dict, limit: int = 45000) -> dict:
    assertions = {item["id"]: item for item in packet["assertions"]}
    evidence = {item["id"]: item for item in packet["evidence"]}
    required = set(packet["mandatory_closure"])
    selected = [item for item in packet["assertions"] if item["id"] in required]
    evidence_ids = {key for item in selected for key in item["evidence_ids"]}
    size = sum(len(evidence[key]["text"]) for key in evidence_ids)
    optional = [identifier for identifier in packet["seed_matches"] if identifier in assertions]
    optional.extend(sorted(set(assertions) - set(optional) - required))
    for identifier in optional:
        if identifier in required:
            continue
        item = assertions[identifier]
        extra = set(item["evidence_ids"]) - evidence_ids
        extra_size = sum(len(evidence[key]["text"]) for key in extra)
        if size + extra_size > limit:
            continue
        selected.append(item)
        evidence_ids.update(extra)
        size += extra_size
    return {
        **packet,
        "assertions": selected,
        "evidence": [item for item in packet["evidence"] if item["id"] in evidence_ids],
        "context_characters": size,
    }


def _normalized_section_draft(draft: dict, packet: dict) -> dict:
    labels = {item["id"]: item["label"] for item in packet["evidence"]}
    draft["markdown"] = normalize_citation_syntax(draft["markdown"])
    for mapping in draft["mappings"]:
        mapping["passage"] = normalize_citation_syntax(mapping["passage"])
        normalized = []
        for key in mapping["citation_ids"]:
            label = labels.get(key, key)
            match = re.fullmatch(r"\[?(?:Legacy|Code)\s+([CD]\d+)\]?", label)
            normalized.append(match.group(1) if match else label)
        mapping["citation_ids"] = normalized
    return draft


class Pipeline:
    def __init__(self, store: ArtifactStore, model, run_id: str):
        self.store = store
        self.model = model
        self.run_id = run_id
        self.graph = KnowledgeGraph(store.root / "runs" / run_id / "graph.sqlite")
        self.stages = StageArtifacts(store, run_id)

    def read(self, state: PipelineState, key: str, default=None):
        return self.store.get(state[key]) if state.get(key) else default

    def repair_limit(self) -> int:
        return getattr(getattr(self.model, "settings", None), "content_repair_limit", 2)

    def runtime_signature(self) -> str:
        prompts = files("docgen_graph").joinpath("prompts")
        prompt_hashes = {item.name: digest(item.read_bytes()) for item in prompts.iterdir()}
        model_name = getattr(getattr(self.model, "settings", None), "model", "test-double")
        settings = getattr(self.model, "settings", None)
        configuration = {
            key: getattr(settings, key, None)
            for key in (
                "output_tokens",
                "request_tokens",
                "timeout_seconds",
                "authoring_turn_limit",
                "authoring_timeout_seconds",
                "authoring_result_limit",
                "code_analysis_backend",
                "code_analysis_model",
                "code_analysis_timeout",
                "code_analysis_turn_limit",
                "code_analysis_result_limit",
            )
        }
        scope_file = getattr(settings, "code_scope_file", None)
        configuration["code_scope_hash"] = digest(scope_file.read_bytes()) if scope_file else None
        return digest(
            [
                implementation_signature(),
                prompt_hashes,
                model_name,
                self.repair_limit(),
                configuration,
                "pipeline-schema-v3",
            ]
        )

    def call(self, stage: str, payload: dict, schema) -> dict:
        return schema.model_validate(self.model.call(stage, payload, schema)).model_dump()

    def spans(self, state: PipelineState) -> dict[str, dict]:
        return {item["id"]: item for item in self.read(state, "inventory_ref")["spans"]}

    def assertions(self, state: PipelineState) -> list[dict]:
        return self.read(state, "assertions_ref", [])

    def issue(self, state: PipelineState, stage: str, findings: list[str], retry: str) -> dict:
        issue = {
            "stage": stage,
            "findings": findings,
            "revision": digest(
                [stage, findings, state.get("snapshot_ref"), state.get("plan_hash")]
            ),
        }
        ref = self.store.put(issue)
        self.store.write(
            f"runs/{self.run_id}/review-issue-{ref[:12]}.json", json.dumps(issue, indent=2)
        )
        return {
            "issue_ref": ref,
            "issue_return": retry,
            "route": "resolve_issues_automatically"
            if state.get("mode") == "autopilot"
            else "review_issues",
            "status": "resolving_issue"
            if state.get("mode") == "autopilot"
            else "awaiting_issue_review",
        }

    def snapshot_inputs(self, state: PipelineState) -> dict:
        settings = getattr(self.model, "settings", None)
        snapshot = snapshot_inputs(
            self.store,
            Path(state["docs"]),
            Path(state["code"]) if state.get("code") else None,
            Path(state["template"]),
            state.get("brief", ""),
            getattr(settings, "asset_max_bytes", 10000000),
            getattr(settings, "asset_max_pixels", 20000000),
        )
        signature = self.runtime_signature()
        snapshot["runtime_signature"] = signature
        snapshot["content_repair_limit"] = self.repair_limit()
        mapping_path = getattr(settings, "source_page_map", None)
        if mapping_path:
            mapping = json.loads(mapping_path.read_text("utf-8"))
            sources = mapping.get("pages", mapping.get("sources", mapping))
            frozen = {}
            for key, entry in sources.items():
                relative = Path(entry["html_path"] if isinstance(entry, dict) else entry)
                candidates = (
                    [relative]
                    if relative.is_absolute()
                    else [mapping_path.parent / relative, settings.env_file.parent / relative]
                )
                selected = next((path.resolve() for path in candidates if path.is_file()), None)
                if selected is None:
                    raise ValueError(f"Declared source page is missing: {relative}")
                frozen[key] = self.store.put_bytes(selected.read_bytes())
            snapshot["source_pages"] = frozen
        else:
            snapshot["source_pages"] = {}
        snapshot["revision"] = digest([snapshot["revision"], signature])
        self.stages.initialize(
            state.get("mode", "manual"),
            state.get("policy_version", "v2"),
            signature,
            self.repair_limit(),
        )
        sources = ["# Sources", ""]
        sources.extend(f"- `{item['path']}` SHA-256 `{item['hash']}`" for item in snapshot["files"])
        self.store.write(
            str(self.stages.step("snapshot_inputs") / "sources.md"), "\n".join(sources) + "\n"
        )
        return {
            "snapshot_ref": self.store.put(snapshot),
            "runtime_signature": signature,
            "status": "running",
        }

    def inventory_sources(self, state: PipelineState) -> dict:
        source = self.read(state, "snapshot_ref")
        result = inventory(self.store, source)
        self.graph.add_evidence(result["spans"])
        self.graph.add_structure(result)
        if not result["code_units"]:
            self.stages.skip("analyze_code_unit", "No code input was selected")
            self.stages.skip("verify_code_unit", "No code input was selected")
        return {
            "inventory_ref": self.store.put(result),
            "code_index": 0,
            "document_index": 0,
            "graph_index": 0,
            "assertions_ref": self.store.put([]),
            "exclusions_ref": self.store.put([]),
            "source_aspect_index": 0,
            "source_aspects_ref": self.store.put([]),
            "source_decisions_ref": self.store.put([]),
            "source_non_substantive_ref": self.store.put([]),
            "route": "inventory_code_scope",
        }

    def inventory_source_aspects(self, state: PipelineState) -> dict:
        inventory_record = self.read(state, "inventory_ref")
        index = state.get("source_aspect_index", 0)
        batches = inventory_record["document_batches"]
        if index >= len(batches):
            return {
                "route": "analyze_code_unit"
                if inventory_record["code_units"]
                else "extract_document_batch"
            }
        spans = self.spans(state)
        blocks = [spans[key] for key in batches[index]]
        draft = self.call("inventory_aspects", {"blocks": blocks}, AspectInventory)
        aspects, findings = validate_aspect_inventory(draft["aspects"], spans)
        covered = {item["evidence_id"] for item in aspects} | set(draft["non_substantive"])
        if covered != set(batches[index]):
            findings.append("Independent aspect inventory does not account for every source block")
        if findings:
            return self.issue(
                state, "inventory_source_aspects", findings, "inventory_source_aspects"
            )
        return {
            "source_aspects_ref": self.store.put(
                self.read(state, "source_aspects_ref", []) + aspects
            ),
            "source_aspect_index": index + 1,
            "source_non_substantive_ref": self.store.put(
                self.read(state, "source_non_substantive_ref", [])
                + [
                    {
                        "evidence_id": key,
                        "decision": "Inventory candidate; independently checked against source",
                    }
                    for key in draft["non_substantive"]
                ]
            ),
            "route": "inventory_source_aspects",
        }

    def extract_document_batch(self, state: PipelineState) -> dict:
        inventory_record = self.read(state, "inventory_ref")
        if not inventory_record["document_batches"]:
            return self.issue(
                state,
                "extract_document_batch",
                [
                    "Selected documents have no readable content; "
                    "attachment interpretation is required"
                ],
                "inventory_sources",
            )
        ids = inventory_record["document_batches"][state["document_index"]]
        spans = self.spans(state)
        draft = self.call(
            "extract_document",
            {
                "blocks": [spans[key] for key in ids],
                "feedback": self.read(state, "feedback_ref", []),
                "previous": self.read(state, "draft_ref") if state.get("attempt") else None,
            },
            DocumentExtractionDraft,
        )
        return {"draft_ref": self.store.put(draft)}

    def verify_document_batch(self, state: PipelineState) -> dict:
        inventory_record = self.read(state, "inventory_ref")
        ids = inventory_record["document_batches"][state["document_index"]]
        spans = self.spans(state)
        draft = self.read(state, "draft_ref")
        findings = []
        try:
            records = [
                normalized_assertion({**item, "review_status": "verified"}, set(ids))
                for item in draft["assertions"]
            ]
        except (ValueError, TypeError) as error:
            records = []
            findings.append(str(error))
        excluded = draft.get("excluded", [])
        if not isinstance(excluded, list) or any(
            not isinstance(item, dict)
            or item.get("evidence_id") not in ids
            or not item.get("reason")
            for item in excluded
        ):
            excluded = []
            findings.append("Invalid exclusion record")
        covered = {key for record in records for key in record["evidence_ids"]}
        covered.update(item["evidence_id"] for item in excluded)
        missing = set(ids) - covered
        if missing:
            findings.append(f"Document blocks lack coverage: {sorted(missing)}")
        audit = (
            self.call(
                "verify_document",
                {
                    "blocks": [spans[key] for key in ids],
                    "draft": draft,
                },
                AuditDraft,
            )
            if not findings
            else {"accepted": False, "findings": findings}
        )
        findings.extend(str(item) for item in audit.get("findings", []))
        if not audit.get("accepted") or findings:
            if state.get("attempt", 0) < self.repair_limit():
                return {
                    "attempt": state.get("attempt", 0) + 1,
                    "feedback_ref": self.store.put(findings),
                    "route": "extract_document_batch",
                }
            return self.issue(state, "verify_document_batch", findings, "extract_document_batch")
        return {
            "pending_document_ref": self.store.put({"records": records, "excluded": excluded}),
            "route": "audit_source_coverage",
        }

    def audit_source_coverage(self, state: PipelineState) -> dict:
        inventory_record = self.read(state, "inventory_ref")
        ids = inventory_record["document_batches"][state["document_index"]]
        spans = self.spans(state)
        pending = self.read(state, "pending_document_ref")
        aspects = [
            item
            for item in self.read(state, "source_aspects_ref", [])
            if item["evidence_id"] in ids
        ]
        audit = self.call(
            "audit_source_coverage",
            {
                "blocks": [spans[key] for key in ids],
                "aspects": aspects,
                "facts": pending["records"],
                "non_substantive_candidates": [
                    item
                    for item in self.read(state, "source_non_substantive_ref", [])
                    if item["evidence_id"] in ids
                ],
            },
            SourceAudit,
        )
        findings = audit["findings"] + audit_decisions(
            aspects, audit["decisions"], pending["records"]
        )
        if findings:
            if state.get("attempt", 0) < self.repair_limit():
                return {
                    "attempt": state.get("attempt", 0) + 1,
                    "feedback_ref": self.store.put(findings),
                    "route": "extract_document_batch",
                }
            return self.issue(state, "audit_source_coverage", findings, "extract_document_batch")
        next_index = state["document_index"] + 1
        return {
            "assertions_ref": self.store.put(self.assertions(state) + pending["records"]),
            "exclusions_ref": self.store.put(
                self.read(state, "exclusions_ref", []) + pending["excluded"]
            ),
            "source_decisions_ref": self.store.put(
                self.read(state, "source_decisions_ref", []) + audit["decisions"]
            ),
            "document_index": next_index,
            "attempt": 0,
            "draft_ref": "",
            "feedback_ref": "",
            "route": "extract_document_batch"
            if next_index < len(inventory_record["document_batches"])
            else "link_graph_batch",
        }

    def link_graph_batch(self, state: PipelineState) -> dict:
        batch = _chunks(self.assertions(state), 50)[state["graph_index"]]
        self.graph.add_assertions(batch)
        return {"route": "verify_graph_batch"}

    def verify_graph_batch(self, state: PipelineState) -> dict:
        findings = self.graph.verify()
        if findings:
            return self.issue(state, "verify_graph_batch", findings, "link_graph_batch")
        next_index = state["graph_index"] + 1
        return {
            "graph_index": next_index,
            "route": "link_graph_batch"
            if next_index < len(_chunks(self.assertions(state), 50))
            else "finalize_graph",
        }

    def finalize_graph(self, state: PipelineState) -> dict:
        spans = self.spans(state)
        assertions = self.assertions(state)
        exclusions = self.read(state, "exclusions_ref", [])
        if self.read(state, "code_relations_ref", []):
            self.graph.add_relations(self.read(state, "code_relations_ref", []))
        covered = {key for item in assertions for key in item["evidence_ids"]}
        covered.update(item["evidence_id"] for item in exclusions)
        missing = set(spans) - covered
        if missing:
            return self.issue(
                state,
                "finalize_graph",
                [f"Unresolved source spans: {sorted(missing)}"],
                "finalize_graph",
            )
        findings = self.graph.verify()
        if findings:
            return self.issue(state, "finalize_graph", findings, "finalize_graph")
        revision = digest([state["snapshot_ref"], state["inventory_ref"], assertions, exclusions])
        inventory_record = self.read(state, "inventory_ref")
        non_substantive = [
            {"path": path, **range_record}
            for path, metadata in inventory_record["analysis"].items()
            for range_record in metadata["non_substantive"]
        ]
        manifest = {
            "schema": 1,
            "revision": revision,
            "source_revision": state["snapshot_ref"],
            "data_hash": digest([assertions, exclusions]),
            "model": getattr(getattr(self.model, "settings", None), "model", "test-double"),
            "parser_capabilities": sorted(
                {metadata["capability"] for metadata in inventory_record["analysis"].values()}
            ),
            "assertion_count": len(assertions),
            "evidence_count": len(spans),
            "excluded": exclusions,
            "input_exclusions": self.read(state, "snapshot_ref")["exclusions"],
            "conflict_candidates": self.graph.conflict_candidates(),
            "policy": "lexical-two-hop-v1",
        }
        self.store.write(f"runs/{self.run_id}/graph-manifest.json", json.dumps(manifest, indent=2))
        frozen = self.store.root / "graphs" / revision / "graph.sqlite"
        if not frozen.exists():
            frozen.parent.mkdir(parents=True, exist_ok=True)
            temporary = frozen.with_suffix(".building")
            with self.graph.connect() as source, closing(sqlite3.connect(temporary)) as target:
                source.backup(target)
            os.replace(temporary, frozen)
        self.store.write(f"graphs/{revision}/manifest.json", json.dumps(manifest, indent=2))
        report_lines = ["# Code analysis", ""]
        for index in range(state.get("code_index", 0)):
            report_lines.append(f"- [Unit {index + 1}](reports/code-{index:04d}.md)")
        self.store.write(f"runs/{self.run_id}/code-analysis.md", "\n".join(report_lines) + "\n")
        self.store.write(
            f"runs/{self.run_id}/code-analysis.jsonl",
            "\n".join(
                json.dumps(item, ensure_ascii=False)
                for item in assertions
                if any(spans[key]["kind"] == "code" for key in item["evidence_ids"])
            )
            + "\n",
        )
        self.store.write(
            f"runs/{self.run_id}/coverage.json",
            json.dumps(
                {
                    "represented": sorted(
                        {key for item in assertions for key in item["evidence_ids"]}
                    ),
                    "excluded_with_reason": exclusions + non_substantive,
                    "unresolved": [],
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
        return {"graph_revision": revision, "status": "graph_ready", "route": "compile_template"}

    def compile_template(self, state: PipelineState) -> dict:
        source = self.read(state, "snapshot_ref")
        text = self.store.get_bytes(source["template_hash"]).decode("utf-8")
        try:
            contract = compile_requirements(text, source["template_hash"])
        except ValueError as error:
            return self.issue(state, "compile_template", [str(error)], "compile_template")
        if not contract["headings"]:
            return self.issue(
                state,
                "compile_template",
                ["Template has no mandatory headings"],
                "compile_template",
            )
        return {
            "template_ref": self.store.put(contract),
            "authoring_ref": "",
            "authoring_return": "draft_page_plan",
            "route": "plan_authoring_action",
        }

    def _groups(self, state: PipelineState) -> list[dict]:
        return content_groups(self.assertions(state), self.spans(state))

    def draft_page_plan(self, state: PipelineState) -> dict:
        groups = self._groups(state)
        contract = self.read(state, "template_ref")
        draft = self.call(
            "draft_plan",
            {
                "brief": self.read(state, "snapshot_ref")["brief"],
                "template_headings": contract["headings"],
                "template_requirements": contract["requirements"],
                "source_assets": self.read(state, "inventory_ref").get("assets", []),
                "groups": [
                    {key: group[key] for key in ("id", "topic", "facts")}
                    | {"obligation_count": len(group["obligation_ids"])}
                    for group in groups
                ],
                "feedback": state.get("plan_feedback", ""),
                "previous_allocations": [
                    {key: section[key] for key in ("title", "group_ids", "support_group_ids")}
                    for section in self.read(state, "plan_ref", {}).get("sections", [])
                ]
                if state.get("attempt")
                else [],
                "conflict_candidates": self.graph.conflict_candidates(),
            },
            PagePlanDraft,
        )
        group_map = {group["id"]: group for group in groups}
        try:
            omitted = {
                item["requirement_id"]
                for item in draft.get("template_decisions", [])
                if item["disposition"] == "inapplicable"
            }
            draft["sections"] = bind_plan_sections(
                contract["heading_tree"],
                draft["sections"],
                [item["text"] for item in contract["requirements"] if item["id"] in omitted],
            )
        except ValueError as error:
            return self.issue(state, "draft_page_plan", [str(error)], "draft_page_plan")
        diagrams = {item["id"]: item for item in draft.get("diagrams", [])}
        sections = []
        for raw in draft["sections"]:
            ids = raw.get("group_ids", [])
            support_ids = raw.get("support_group_ids", [])
            if not isinstance(ids, list):
                ids = []
            obligations = [
                identifier
                for group_id in ids
                if group_id in group_map
                for identifier in group_map[group_id]["obligation_ids"]
            ]
            supporting = [
                identifier
                for group_id in support_ids
                if group_id in group_map
                for identifier in group_map[group_id]["obligation_ids"][:1]
            ]
            sections.append(
                {
                    "title": str(raw.get("title", "")).strip(),
                    "section_id": raw["section_id"],
                    "purpose": str(raw.get("purpose", "")).strip(),
                    "group_ids": ids,
                    "support_group_ids": support_ids,
                    "obligation_ids": obligations,
                    "supporting_obligation_ids": list(dict.fromkeys(supporting))[:8],
                    "unit_obligations": [
                        group_map[key]["obligation_ids"] for key in ids if key in group_map
                    ],
                    "queries": [str(query) for query in raw.get("queries", [])],
                    "visuals": raw.get("visuals", []),
                }
            )
        units = content_units(groups, sections)
        section_ids = {section["title"]: section["section_id"] for section in sections}
        for unit in units:
            unit["canonical_section_id"] = section_ids.get(unit["canonical_section"], "")
        for section in sections:
            section["content_unit_ids"] = [
                unit["id"] for unit in units if unit["canonical_section"] == section["title"]
            ]
            section["overview_links"] = [
                {"topic": unit["topic"], "section": unit["canonical_section"]}
                for unit in units
                if unit["id"] in section["support_group_ids"]
                and unit["canonical_section"] != section["title"]
            ]
            for visual in section["visuals"]:
                visual["section_id"] = section["section_id"]
                visual["section"] = section["title"]
                visual["review_status"] = "planned"
                visual["diagram"] = diagrams.get(visual.get("diagram_id"))
                if visual.get("diagram"):
                    visual["diagram"]["source"] = diagram_source(visual["diagram"])
        plan = {
            "schema": 2,
            "title": document_title(
                str(draft.get("title", "Documentation")),
                contract["text"],
                self.read(state, "snapshot_ref")["brief"],
            ),
            "sections": sections,
            "groups": groups,
            "content_units": units,
            "duplicate_risks": duplicate_risks(units),
            "template_requirements": contract["requirements"],
            "template_decisions": draft.get("template_decisions", []),
            "asset_decisions": draft.get("asset_decisions", []),
            "source_assets": self.read(state, "inventory_ref").get("assets", []),
            "unknowns": draft.get("unknowns", []),
            "discrepancies": draft.get("discrepancies", []),
            "conflict_candidates": self.graph.conflict_candidates(),
            "input_exclusions": self.read(state, "snapshot_ref")["exclusions"],
            "exclusions": draft.get("exclusions", []),
            "source_revision": state["snapshot_ref"],
            "graph_revision": state["graph_revision"],
            "template_hash": contract["hash"],
            "brief": self.read(state, "snapshot_ref")["brief"],
        }
        return {
            "plan_ref": self.store.put(plan),
            "plan_packet_index": 0,
            "plan_packets_ref": self.store.put([]),
            "route": "retrieve_plan_evidence",
        }

    def retrieve_plan_evidence(self, state: PipelineState) -> dict:
        plan = self.read(state, "plan_ref")
        index = state["plan_packet_index"]
        section = plan["sections"][index]
        packet = self.graph.retrieve(
            section["queries"] or [section["title"]],
            section["obligation_ids"] + section["supporting_obligation_ids"],
        )
        packets = self.read(state, "plan_packets_ref", []) + [self.store.put(packet)]
        index += 1
        return {
            "plan_packets_ref": self.store.put(packets),
            "plan_packet_index": index,
            "route": "retrieve_plan_evidence"
            if index < len(plan["sections"])
            else "validate_page_plan",
        }

    def validate_page_plan(self, state: PipelineState) -> dict:
        plan = self.read(state, "plan_ref")
        contract = self.read(state, "template_ref")
        all_ids = [item["id"] for item in self.assertions(state)]
        allocated = [
            identifier for section in plan["sections"] for identifier in section["obligation_ids"]
        ]
        findings = []
        findings.extend(
            validate_quality_plan(
                plan,
                contract,
                self.read(state, "inventory_ref").get("assets", []),
                self.spans(state),
            )
        )
        if len(allocated) != len(set(allocated)) or set(allocated) != set(all_ids):
            assigned = [key for section in plan["sections"] for key in section["group_ids"]]
            missing = [group["id"] for group in plan["groups"] if group["id"] not in assigned]
            repeated = sorted({key for key in assigned if assigned.count(key) > 1})
            findings.append(
                "Plan must allocate every obligation exactly once; "
                f"missing group_ids: {missing}; repeated group_ids: {repeated}"
            )
        group_ids = {group["id"] for group in plan["groups"]}
        for section in plan["sections"]:
            if not section["obligation_ids"] and not section["supporting_obligation_ids"]:
                findings.append(f"Section has no source evidence: {section['title']}")
            if not set(section["group_ids"] + section["support_group_ids"]).issubset(group_ids):
                findings.append(f"Section references an unknown source group: {section['title']}")
            try:
                self._units(section)
            except ValueError as error:
                findings.append(str(error))
        if any(not section["title"] or not section["purpose"] for section in plan["sections"]):
            findings.append("A section lacks title or purpose")
        if not plan["sections"]:
            findings.append("Plan has no sections")
        if not findings:
            audit = self.call(
                "verify_plan",
                {
                    "template_headings": contract["headings"],
                    "template_requirements": contract["requirements"],
                    "template_decisions": plan["template_decisions"],
                    "content_units": [
                        {
                            key: unit[key]
                            for key in ("id", "topic", "canonical_section", "scoped_variants")
                        }
                        for unit in plan["content_units"]
                    ],
                    "duplicate_risks": plan["duplicate_risks"],
                    "visuals": [
                        visual for section in plan["sections"] for visual in section["visuals"]
                    ],
                    "visual_evidence": [
                        self.spans(state)[key]
                        for key in sorted(
                            visual_evidence_ids(
                                [
                                    visual
                                    for section in plan["sections"]
                                    for visual in section["visuals"]
                                ]
                            )
                        )
                        if key in self.spans(state)
                    ],
                    "groups": [
                        {
                            "id": group["id"],
                            "topic": group["topic"],
                            "count": len(group["obligation_ids"]),
                        }
                        for group in plan["groups"]
                    ],
                    "sections": [
                        {
                            "title": section["title"],
                            "purpose": section["purpose"],
                            "group_ids": section["group_ids"],
                            "support_group_ids": section["support_group_ids"],
                        }
                        for section in plan["sections"]
                    ],
                },
                AuditDraft,
            )
            if not audit.get("accepted"):
                findings.extend(str(item) for item in audit.get("findings", []))
                if not findings:
                    findings.append("Independent plan audit rejected the plan")
            required_elements = diagram_element_ids(
                [visual for section in plan["sections"] for visual in section["visuals"]]
            )
            if not required_elements.issubset(audit.get("covered_diagram_element_ids", [])):
                findings.append("Plan audit did not support every diagram node and transition")
        if findings:
            if state.get("attempt", 0) < self.repair_limit():
                return {
                    "attempt": state.get("attempt", 0) + 1,
                    "plan_feedback": "\n".join(findings),
                    "route": "draft_page_plan",
                }
            return self.issue(state, "validate_page_plan", findings, "draft_page_plan")
        plan_hash = digest(plan)
        lines = [
            f"# {plan['title']}",
            "",
            f"Plan hash: `{plan_hash}`",
            "",
            f"Graph revision: `{plan['graph_revision']}`",
            "",
            f"Template hash: `{plan['template_hash']}`",
            "",
        ]
        for section in plan["sections"]:
            lines.extend(
                [
                    f"## {section['title']}",
                    "",
                    section["purpose"],
                    "",
                    f"Allocated obligations: {len(section['obligation_ids'])}",
                    f"Supporting obligations: {len(section['supporting_obligation_ids'])}",
                    "",
                ]
            )
            preview_ids = section["obligation_ids"][:5] or section["supporting_obligation_ids"][:5]
            for identifier in preview_ids:
                assertion = self.graph.assertion(identifier)
                lines.append(f"- {assertion['statement']} ({', '.join(assertion['evidence_ids'])})")
            lines.append("")
        for key in (
            "unknowns",
            "discrepancies",
            "conflict_candidates",
            "input_exclusions",
            "exclusions",
            "content_units",
            "template_requirements",
            "template_decisions",
            "source_assets",
            "asset_decisions",
            "duplicate_risks",
        ):
            lines.extend(
                [f"## {key.title()}", "", json.dumps(plan[key], ensure_ascii=False, indent=2), ""]
            )
        self.store.write(f"runs/{self.run_id}/documentation-plan.md", "\n".join(lines))
        self.store.write(
            f"runs/{self.run_id}/visual-plan.json",
            json.dumps(
                [visual for section in plan["sections"] for visual in section["visuals"]], indent=2
            ),
        )
        preview_lines = ["# Source previews", ""]
        spans = self.spans(state)
        for kind in ("code", "docs"):
            selected = [span for span in spans.values() if span["kind"] == kind]
            for span in selected[:3]:
                preview_lines.extend(
                    [
                        f"## {kind}: {span['path']}:{span['start_line']}-{span['end_line']}",
                        "",
                        "    " + span["text"].replace("\n", "\n    "),
                        "",
                    ]
                )
        self.store.write(f"runs/{self.run_id}/source-previews.md", "\n".join(preview_lines))
        for index, section in enumerate(plan["sections"]):
            brief = [
                f"# {section['title']}",
                "",
                section["purpose"],
                "",
                f"Allocated obligations: {len(section['obligation_ids'])}",
                "",
            ]
            for identifier in section["obligation_ids"] or section["supporting_obligation_ids"]:
                assertion = self.graph.assertion(identifier)
                brief.append(f"- {assertion['statement']}")
            self.store.write(
                f"runs/{self.run_id}/page-briefs/{index:03d}.md", "\n".join(brief) + "\n"
            )
        self.store.write(
            f"runs/{self.run_id}/template-mapping.json",
            json.dumps(
                {
                    "template_headings": contract["headings"],
                    "plan_headings": [section["title"] for section in plan["sections"]],
                    "exclusions": plan["input_exclusions"] + plan["exclusions"],
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
        return {
            "plan_hash": plan_hash,
            "attempt": 0,
            "status": "awaiting_plan_review",
            "route": "review_plan",
        }

    def review_plan(self, state: PipelineState) -> dict:
        if state.get("runtime_signature") != self.runtime_signature():
            return {"status": "stale", "route": END}
        plan = self.read(state, "plan_ref")
        decision = (
            {
                "action": "approve_plan",
                "plan_hash": state["plan_hash"],
                "reviewer": "Autopilot policy v2",
                "actor_type": "policy",
                "rationale": (
                    "Plan passed deterministic validation; "
                    "unresolved applicability is presented explicitly"
                ),
                "conflict_decisions": {
                    f"{item['code_id']}:{item['document_id']}": "present_both"
                    for item in plan["conflict_candidates"]
                },
                "discrepancy_decisions": {
                    digest(item)[:16]: "present_both" for item in plan["discrepancies"]
                },
            }
            if state.get("mode") == "autopilot"
            else interrupt(
                {
                    "kind": "plan",
                    "plan_hash": state["plan_hash"],
                    "plan_path": str(
                        self.store.root / "runs" / self.run_id / "documentation-plan.md"
                    ),
                    "graph_revision": state["graph_revision"],
                    "source_revision": state["snapshot_ref"],
                    "unknowns": plan["unknowns"],
                    "discrepancies": plan["discrepancies"],
                    "discrepancy_keys": [
                        {"id": digest(item)[:16], "description": item}
                        for item in plan["discrepancies"]
                    ],
                    "conflict_candidates": plan["conflict_candidates"],
                    "input_exclusions": plan["input_exclusions"],
                    "template_decisions": plan.get("template_decisions", []),
                    "asset_decisions": plan.get("asset_decisions", []),
                    "visuals": [
                        visual
                        for section in plan["sections"]
                        for visual in section.get("visuals", [])
                    ],
                    "error": state.get("review_error", ""),
                }
            )
        )
        if not isinstance(decision, dict) or decision.get("plan_hash") != state["plan_hash"]:
            return {"route": "review_plan", "review_error": "Decision has a stale plan hash"}
        if not decision.get("reviewer") or not decision.get("rationale"):
            return {"route": "review_plan", "review_error": "Reviewer and rationale are required"}
        candidates = {
            f"{item['code_id']}:{item['document_id']}" for item in plan["conflict_candidates"]
        }
        resolutions = decision.get("conflict_decisions", {})
        valid_resolutions = {"present_both", "code_applies", "docs_apply", "not_conflict"}
        if not isinstance(resolutions, dict) or any(
            key not in candidates or value not in valid_resolutions
            for key, value in resolutions.items()
        ):
            return {"route": "review_plan", "review_error": "Invalid conflict decision"}
        if decision.get("action") == "approve_plan" and candidates - set(resolutions):
            return {
                "route": "review_plan",
                "review_error": (
                    "Every cross-source conflict candidate needs an applicability decision"
                ),
            }
        discrepancy_keys = {digest(item)[:16] for item in plan["discrepancies"]}
        discrepancy_decisions = decision.get("discrepancy_decisions", {})
        if not isinstance(discrepancy_decisions, dict) or any(
            key not in discrepancy_keys or value not in valid_resolutions
            for key, value in discrepancy_decisions.items()
        ):
            return {"route": "review_plan", "review_error": "Invalid discrepancy decision"}
        if decision.get("action") == "approve_plan" and discrepancy_keys - set(
            discrepancy_decisions
        ):
            return {
                "route": "review_plan",
                "review_error": "Every discrepancy needs an applicability decision",
            }
        action = decision.get("action")
        record = {
            **decision,
            "graph_revision": state["graph_revision"],
            "source_revision": state["snapshot_ref"],
            "template_hash": plan["template_hash"],
            "timestamp": datetime.now(UTC).isoformat(),
        }
        ref = self.store.put(record)
        self.store.write(
            f"runs/{self.run_id}/reviews/plan-{ref}.json",
            json.dumps(record, ensure_ascii=False, indent=2),
        )
        if action == "approve_plan":
            return {
                "approval_ref": ref,
                "section_index": 0,
                "unit_index": 0,
                "written_ref": self.store.put([]),
                "status": "plan_approved",
                "route": "retrieve_section_evidence",
                "review_error": "",
            }
        if action == "request_changes":
            return {
                "plan_feedback": str(decision.get("rationale")),
                "attempt": 0,
                "route": "draft_page_plan",
                "status": "planning",
            }
        if action == "reject_plan":
            return {"status": "rejected", "route": END}
        return {"route": "review_plan", "review_error": "Unsupported plan review action"}

    def _approved_plan(self, state: PipelineState) -> dict:
        if state.get("runtime_signature") != self.runtime_signature():
            raise ValueError("Runtime changed after plan approval; start a new run revision")
        approval = self.read(state, "approval_ref")
        plan = self.read(state, "plan_ref")
        if (
            not approval
            or approval.get("action") != "approve_plan"
            or approval.get("plan_hash") != digest(plan)
        ):
            raise ValueError("Valid exact plan approval is required before writing")
        if (
            approval["graph_revision"] != state["graph_revision"]
            or approval["source_revision"] != state["snapshot_ref"]
        ):
            raise ValueError("Plan approval is stale")
        return plan

    def _units(self, section: dict) -> list[list[str]]:
        units = []
        current = []
        evidence_ids = set()
        groups = section.get("unit_obligations") or [section["supporting_obligation_ids"]]
        for identifiers in groups:
            required = {
                key
                for identifier in identifiers
                for key in self.graph.assertion(identifier)["evidence_ids"]
            }
            cost = sum(len(self.graph.evidence(key)["text"]) for key in required)
            if cost > 18000:
                raise ValueError("Content unit needs a smaller scoped boundary before approval")
            combined = evidence_ids | required
            size = sum(len(self.graph.evidence(key)["text"]) for key in combined)
            if current and (len(current) + len(identifiers) > 12 or size > 18000):
                units.append(current)
                current, evidence_ids = [], set()
            current.extend(identifiers)
            evidence_ids.update(required)
        if current:
            units.append(current)
        return units or [[]]

    def retrieve_section_evidence(self, state: PipelineState) -> dict:
        plan = self._approved_plan(state)
        section = plan["sections"][state["section_index"]]
        ids = self._units(section)[state["unit_index"]]
        required = ids + (section["supporting_obligation_ids"] if state["unit_index"] == 0 else [])
        packet = _bounded_evidence_packet(
            self.graph.retrieve([], required, hops=0, optional_limit=0)
        )
        visuals = section.get("visuals", []) if state["unit_index"] == 0 else []
        known = {item["id"] for item in packet["evidence"]}
        packet["evidence"].extend(
            self.graph.evidence(key) for key in sorted(visual_evidence_ids(visuals) - known)
        )
        contextual = set()
        spans = list(self.spans(state).values())
        for evidence in list(packet["evidence"]):
            if evidence["kind"] != "docs" or not _needs_source_context(evidence["text"]):
                continue
            nearby = sorted(
                (
                    span
                    for span in spans
                    if span["path"] == evidence["path"] and span["kind"] == "docs"
                ),
                key=lambda span: span["start_line"],
            )
            index = next(i for i, span in enumerate(nearby) if span["id"] == evidence["id"])
            contextual.update(span["id"] for span in nearby[max(0, index - 2) : index])
        known = {item["id"] for item in packet["evidence"]}
        packet["evidence"].extend(self.graph.evidence(key) for key in sorted(contextual - known))
        packet["contextual_evidence_ids"] = sorted(contextual)
        packet["context_characters"] = sum(len(item["text"]) for item in packet["evidence"])
        packet["visuals"] = visuals
        present = {item["id"] for item in packet["assertions"]}
        if not set(ids).issubset(present):
            return self.issue(
                state,
                "retrieve_section_evidence",
                ["Mandatory evidence missing"],
                "retrieve_section_evidence",
            )
        if packet["context_characters"] > 45000:
            return self.issue(
                state,
                "retrieve_section_evidence",
                ["Required evidence closure exceeds the section request limit"],
                "retrieve_section_evidence",
            )
        return {
            "packet_ref": self.store.put(packet),
            "status": "generating",
            "authoring_ref": "",
            "authoring_context_ref": "",
            "authoring_return": "write_section",
            "route": "plan_authoring_action",
        }

    def _writing_context(self, state: PipelineState) -> dict:
        preceding = [
            item
            for item in self.read(state, "written_ref", [])
            if item["section_index"] == state["section_index"]
        ]
        blocks = []
        size = 0
        if preceding:
            for block in reversed(preceding[-1]["markdown"].split("\n\n")):
                if size + len(block) > 18000:
                    break
                blocks.append(block)
                size += len(block)
        return {
            "existing_headings": [
                line
                for item in preceding
                for line in item["markdown"].splitlines()
                if re.match(r"^#{3,6}\s", line)
            ],
            "preceding_passages": list(reversed(blocks)),
            "purpose": "Writing continuity only; original_evidence remains the factual authority",
        }

    def authoring_tools(self, state: PipelineState):
        from docgen_graph.evidence_service import RevisionEvidenceService

        service = getattr(self, "evidence_service", None)
        scope_id = self.read(state, "code_scope_ref", {}).get("scope_id", "full")
        decisions = {
            item["aspect_id"]: item for item in self.read(state, "source_decisions_ref", [])
        }
        spans = self.spans(state)
        coverage = [
            SourceCoverageItem(
                id=aspect["id"],
                evidence_ids=[aspect["evidence_id"]],
                unit_locator=EvidenceLocator.model_validate(
                    spans[aspect["evidence_id"]].get("locator")
                    or {
                        "kind": "lines",
                        "start": spans[aspect["evidence_id"]]["start_line"],
                        "end": spans[aspect["evidence_id"]]["end_line"],
                    }
                ),
                aspect=aspect["description"],
                disposition="represented"
                if decisions.get(aspect["id"], {}).get("fact_ids")
                else "unresolved",
                fact_ids=decisions.get(aspect["id"], {}).get("fact_ids", []),
                reason=decisions.get(aspect["id"], {}).get("reason", "Not audited"),
            )
            for aspect in self.read(state, "source_aspects_ref", [])
        ]
        if service is None:
            service = (
                RevisionEvidenceService(self.store, state["evidence_revision"])
                if state.get("evidence_revision")
                else RevisionEvidenceService.from_graph(
                    self.store,
                    self.graph,
                    state["snapshot_ref"],
                    scope_id,
                    coverage=coverage,
                    provenance=self.read(state, "code_provenance_ref", []),
                )
            )
        query = EvidenceQuery(
            snapshot_id=state["snapshot_ref"], graph_revision=service.revision, scope_id=scope_id
        )
        limit = getattr(getattr(self.model, "settings", None), "authoring_result_limit", 60000)
        return AuthoringTools(
            service,
            query,
            self.model,
            self.read(state, "inventory_ref").get("attachments", []),
            limit,
        ), service.revision

    def plan_authoring_action(self, state: PipelineState) -> dict:
        session = self.read(
            state,
            "authoring_ref",
            {"messages": [], "turns": 0, "queries": [], "started": datetime.now(UTC).timestamp()},
        )
        settings = getattr(self.model, "settings", None)
        limit = getattr(settings, "authoring_turn_limit", 8)
        seconds = getattr(settings, "authoring_timeout_seconds", 300)
        if (
            session["turns"] >= limit
            or datetime.now(UTC).timestamp() - session["started"] > seconds
        ):
            return self.issue(
                state,
                "plan_authoring_action",
                ["Authoring tool limit exhausted with unresolved readiness"],
                "retrieve_section_evidence",
            )
        target = state.get("authoring_return", "write_section")
        packet = (
            self.read(state, "packet_ref", {})
            if target == "write_section"
            else {"groups": self._groups(state), "template": self.read(state, "template_ref")}
        )
        section = (
            self._approved_plan(state)["sections"][state["section_index"]]
            if target == "write_section"
            else {"purpose": "Plan document content without losing source information"}
        )
        payload = {
            "section": section,
            "required_evidence": packet,
            "objective": "Resolve missing context and prepare faithful, readable documentation",
        }
        response = self.model.tool_turn(payload, session["messages"], declarations())
        calls = response.get("calls", [])
        if len(calls) > 1:
            return self.issue(
                state,
                "plan_authoring_action",
                ["Parallel tool calls exceed the sequential checkpoint protocol"],
                "retrieve_section_evidence",
            )
        session = {
            **session,
            "turns": session["turns"] + 1,
            "messages": session["messages"] + [response["content"]],
            "call": calls[0] if calls else None,
        }
        if calls:
            fingerprint = digest([calls[0]["name"], calls[0].get("args", {})])
            if fingerprint in session["queries"]:
                return self.issue(
                    state,
                    "plan_authoring_action",
                    ["Repeated authoring query gained no new knowledge"],
                    "retrieve_section_evidence",
                )
            session["queries"] = session["queries"] + [fingerprint]
        return {
            "authoring_ref": self.store.put(session),
            "route": "execute_authoring_tool" if calls else target,
        }

    def execute_authoring_tool(self, state: PipelineState) -> dict:
        session = self.read(state, "authoring_ref")
        tools, revision = self.authoring_tools(state)
        call = session["call"]
        try:
            result = tools.execute(call["name"], call.get("args", {}))
        except (ValueError, TypeError, KeyError) as error:
            result = {
                "status": "unresolved",
                "warnings": [f"Invalid tool request: {type(error).__name__}"],
            }
        return {
            "authoring_result_ref": self.store.put(result),
            "evidence_revision": revision,
            "route": "verify_tool_result",
        }

    def verify_tool_result(self, state: PipelineState) -> dict:
        session = self.read(state, "authoring_ref")
        result = self.read(state, "authoring_result_ref")
        call = session["call"]
        if result.get("status") == "ok" and result.get("evidence"):
            tools, _ = self.authoring_tools(state)
            identifiers = [item["id"] for item in result["evidence"]]
            verified = tools.service.verify_references(
                tools.query.model_copy(update={"mandatory_ids": identifiers, "limit": 1000})
            )
            if (
                verified.status != "ok"
                or verified.truncated
                or {item.id for item in verified.evidence} != set(identifiers)
            ):
                return self.issue(
                    state,
                    "verify_tool_result",
                    ["Tool evidence references did not verify against the frozen snapshot"],
                    "retrieve_section_evidence",
                )
        known = {item["id"] for item in self.assertions(state)}
        new_facts = [item for item in result.get("facts", []) if item["id"] not in known]
        if new_facts:
            return {
                "knowledge_delta_ref": self.store.put(
                    {
                        "facts": new_facts,
                        "evidence": result.get("evidence", []),
                        "relations": result.get("relations", []),
                        "conflicts": result.get("conflicts", []),
                        "coverage": result.get("coverage", []),
                        "provenance": result.get("provenance", []),
                    }
                ),
                "route": "verify_knowledge_delta",
            }
        content = {
            "role": "user",
            "parts": [
                {
                    "function_response": {
                        "name": call["name"],
                        "response": result,
                        **({"id": call["id"]} if call.get("id") else {}),
                    }
                }
            ],
        }
        session = {**session, "messages": session["messages"] + [content]}
        context = self.read(state, "authoring_context_ref", []) + [
            {"tool": call["name"], "result_ref": state["authoring_result_ref"]}
        ]
        return {
            "authoring_ref": self.store.put(session),
            "authoring_context_ref": self.store.put(context),
            "route": "plan_authoring_action",
        }

    def verify_knowledge_delta(self, state: PipelineState) -> dict:
        candidate = self.read(state, "knowledge_delta_ref")
        audit = self.call(
            "verify_tool_content",
            {
                "new_facts": candidate["facts"],
                "original_evidence": candidate["evidence"],
                "relations": candidate["relations"],
            },
            AuditDraft,
        )
        if not audit["accepted"] or audit["findings"]:
            return self.issue(
                state,
                "verify_knowledge_delta",
                audit["findings"] or ["New knowledge is not independently supported"],
                "retrieve_section_evidence",
            )
        delta = KnowledgeDelta(
            base_revision=state["evidence_revision"],
            **candidate,
            verification=DeltaVerification(
                accepted=True, verifier="gemini-3.8-flash", input_hash=""
            ),
        )
        delta.verification.input_hash = digest(delta.verification_payload())
        return {
            "knowledge_delta_ref": self.store.put(delta.model_dump(mode="json")),
            "route": "commit_knowledge_revision",
        }

    def commit_knowledge_revision(self, state: PipelineState) -> dict:
        tools, _ = self.authoring_tools(state)
        delta = KnowledgeDelta.model_validate(self.read(state, "knowledge_delta_ref"))
        result = tools.service.apply_verified_delta(tools.query, delta)
        if result.status != "ok" or not result.graph_revision:
            return self.issue(
                state,
                "commit_knowledge_revision",
                ["Verified knowledge revision could not be committed"],
                "retrieve_section_evidence",
            )
        from docgen_graph.evidence_service import RevisionEvidenceService

        published = RevisionEvidenceService(self.store, result.graph_revision)
        published.sync_graph(self.graph)
        inventory_record = self.read(state, "inventory_ref")
        existing = {item["id"] for item in inventory_record["spans"]}
        inventory_record["spans"].extend(
            self.graph.evidence(ref.id) for ref in delta.evidence if ref.id not in existing
        )
        return {
            "assertions_ref": self.store.put(
                [item.model_dump(mode="json") for item in published.packet.facts]
            ),
            "inventory_ref": self.store.put(inventory_record),
            "code_provenance_ref": self.store.put(
                [item.model_dump(mode="json") for item in published.packet.provenance]
            ),
            "evidence_revision": result.graph_revision,
            "plan_ref": "",
            "plan_hash": "",
            "approval_ref": "",
            "release_ref": "",
            "candidate_ref": "",
            "written_ref": "",
            "edited_ref": "",
            "authoring_ref": "",
            "authoring_context_ref": "",
            "route": "finalize_graph",
        }

    def write_section(self, state: PipelineState) -> dict:
        plan = self._approved_plan(state)
        section = plan["sections"][state["section_index"]]
        packet = self.read(state, "packet_ref")
        writing_ids = self._units(section)[state["unit_index"]]
        canonical = writing_ids if section["obligation_ids"] else []
        if not writing_ids:
            draft = {
                "markdown": ("No source-backed statement was approved for this section."),
                "mappings": [],
            }
        else:
            draft = self.call(
                "write_section",
                {
                    "section": {"title": section["title"], "purpose": section["purpose"]},
                    "content_units": [
                        unit
                        for unit in plan["content_units"]
                        if set(unit["obligation_ids"]) & set(canonical)
                    ],
                    "overview_links": section.get("overview_links", []),
                    "writing_context": self._writing_context(state),
                    "template_requirements": [
                        item
                        for item in plan["template_requirements"]
                        if item["section"] == section["title"]
                        and (state["unit_index"] == 0 or item["kind"] in {"purpose", "conditional"})
                    ],
                    "document_instructions": [
                        item["text"]
                        for item in plan["template_requirements"]
                        if item["section"] == "__document__" and item["kind"] != "metadata"
                    ],
                    "template_decisions": plan["template_decisions"],
                    "unit_index": state["unit_index"],
                    "unit_count": len(self._units(section)),
                    "approved_visuals": packet.get("visuals", []),
                    "mandatory_obligation_ids": canonical,
                    "assertions": [
                        item for item in packet["assertions"] if item["id"] in canonical
                    ],
                    "supporting_assertions": [
                        item
                        for item in packet["assertions"]
                        if item["id"] in writing_ids and item["id"] not in canonical
                    ],
                    "related_assertions": [
                        item for item in packet["assertions"] if item["id"] not in writing_ids
                    ],
                    "original_evidence": packet["evidence"],
                    "authoring_context": [
                        self.store.get(item["result_ref"])
                        for item in self.read(state, "authoring_context_ref", [])
                    ],
                    "conflict_decisions": self.read(state, "approval_ref").get(
                        "conflict_decisions", {}
                    ),
                    "discrepancy_decisions": self.read(state, "approval_ref").get(
                        "discrepancy_decisions", {}
                    ),
                    "feedback": self.read(state, "feedback_ref", []),
                    "previous": self.read(state, "draft_ref") if state.get("attempt") else None,
                },
                SectionDraft,
            )
        draft = _normalized_section_draft(SectionDraft.model_validate(draft).model_dump(), packet)
        visuals = render_visuals(
            packet.get("visuals", []), plan["source_assets"], packet["evidence"]
        )
        if visuals:
            draft["markdown"] += "\n\n" + visuals
        return {"draft_ref": self.store.put(draft)}

    def verify_section(self, state: PipelineState) -> dict:
        plan = self._approved_plan(state)
        section = plan["sections"][state["section_index"]]
        writing_ids = self._units(section)[state["unit_index"]]
        canonical = writing_ids if section["obligation_ids"] else []
        packet = self.read(state, "packet_ref")
        draft = self.read(state, "draft_ref")
        evidence = {item["label"]: item for item in packet["evidence"]}
        assertions = {item["id"]: item for item in packet["assertions"]}
        mapped = set()
        findings = []
        placements, placement_findings = placement_records(
            section["title"],
            draft["markdown"],
            draft["mappings"],
            assertions,
            {item["id"]: item for item in packet["evidence"]},
        )
        findings.extend(placement_findings)
        findings.extend(
            validate_visual_output(
                draft["markdown"],
                packet.get("visuals", []),
                plan["source_assets"],
                packet["evidence"],
            )
        )
        for mapping in draft["mappings"]:
            identifier = mapping.get("obligation_id")
            labels = mapping.get("citation_ids", [])
            if identifier not in canonical or not labels:
                findings.append("Invalid obligation mapping")
                continue
            supported = {
                self.graph.evidence(key)["label"] for key in assertions[identifier]["evidence_ids"]
            }
            if not set(labels).issubset(supported):
                findings.append(f"Mapping cites unsupported evidence for {identifier}")
            if mapping.get("passage") not in draft["markdown"]:
                findings.append(f"Mapped passage is absent from prose for {identifier}")
            mapped.add(identifier)
        if set(canonical) != mapped:
            findings.append("Section misses approved obligations")
        cited = set(citation_labels(draft["markdown"]))
        if any(label not in evidence for label in cited):
            findings.append("Section contains an unknown citation")
        for mapping in draft["mappings"]:
            if any(label not in cited for label in mapping.get("citation_ids", [])):
                findings.append("Mapped citation is absent from prose")
        if not findings and writing_ids:
            audit = self.call(
                "verify_section",
                {
                    "section": section["title"],
                    "markdown": draft["markdown"],
                    "mappings": draft["mappings"],
                    "placements": placements,
                    "visuals": packet.get("visuals", []),
                    "mandatory_obligation_ids": canonical,
                    "supporting_obligation_ids": [
                        identifier for identifier in writing_ids if identifier not in canonical
                    ],
                    "assertions": [assertions[key] for key in writing_ids],
                    "original_evidence": packet["evidence"],
                },
                AuditDraft,
            )
            if not audit.get("accepted") or not set(canonical).issubset(
                audit.get("covered_obligation_ids", [])
            ):
                findings.extend(str(item) for item in audit.get("findings", []))
                if not findings:
                    findings.append("Independent source audit did not cover all obligations")
            if not diagram_element_ids(packet.get("visuals", [])).issubset(
                audit.get("covered_diagram_element_ids", [])
            ):
                findings.append("Independent source audit did not support every diagram element")
        if findings:
            if state.get("attempt", 0) < self.repair_limit():
                return {
                    "attempt": state.get("attempt", 0) + 1,
                    "feedback_ref": self.store.put(findings),
                    "route": "write_section",
                }
            return self.issue(state, "verify_section", findings, "write_section")
        written = self.read(state, "written_ref", [])
        written.append(
            {
                "section_index": state["section_index"],
                "unit_index": state["unit_index"],
                "markdown": draft["markdown"],
                "mappings": draft["mappings"],
                "placements": placements,
                "visuals": packet.get("visuals", []),
                "context_evidence_ids": [item["id"] for item in packet["evidence"]],
            }
        )
        next_unit = state["unit_index"] + 1
        next_section = state["section_index"]
        if next_unit >= len(self._units(section)):
            next_section += 1
            next_unit = 0
        route = (
            "assemble_pages"
            if next_section >= len(plan["sections"])
            else "retrieve_section_evidence"
        )
        return {
            "written_ref": self.store.put(written),
            "section_index": next_section,
            "unit_index": next_unit,
            "attempt": 0,
            "draft_ref": "",
            "feedback_ref": "",
            "route": route,
        }

    def assemble_pages(self, state: PipelineState) -> dict:
        plan = self._approved_plan(state)
        written = self.read(state, "written_ref", [])
        sections = []
        for index, section in enumerate(plan["sections"]):
            parts = [item for item in written if item["section_index"] == index]
            if len(parts) != len(self._units(section)):
                return self.issue(
                    state,
                    "assemble_pages",
                    [f"Incomplete section: {section['title']}"],
                    "assemble_pages",
                )
            markdown = "\n\n".join(item["markdown"] for item in parts)
            title_number = re.match(r"^(\d+(?:\.\d+)*)\.?\s", section["title"])
            if title_number:
                fixed = [
                    item["text"]
                    for item in plan["template_requirements"]
                    if item["section"] == section["title"]
                    and item["kind"] == "heading"
                    and item["text"] != section["title"]
                ]
                markdown = number_generated_headings(markdown, title_number[1], fixed)
            sections.append(
                {
                    "title": section["title"],
                    "section_id": section.get("section_id", section["title"]),
                    "markdown": markdown,
                    "mappings": [mapping for item in parts for mapping in item["mappings"]],
                    "supporting_obligation_ids": section["supporting_obligation_ids"],
                    "visuals": section.get("visuals", []),
                    "context_evidence_ids": sorted(
                        {key for item in parts for key in item.get("context_evidence_ids", [])}
                    ),
                }
            )
        return {
            "assembled_ref": self.store.put(sections),
            "edited_ref": self.store.put([]),
            "edit_index": 0,
            "edit_queue_ref": self.store.put(list(range(len(sections)))),
            "route": "edit_page",
        }

    def _editing_section(self, state: PipelineState) -> dict:
        edited = self.read(state, "edited_ref", [])
        index = state["edit_index"]
        return edited[index] if index < len(edited) else self.read(state, "assembled_ref")[index]

    def edit_page(self, state: PipelineState) -> dict:
        plan = self._approved_plan(state)
        section = self._editing_section(state)
        if not section["mappings"] and not citation_labels(section["markdown"]):
            draft = {"markdown": section["markdown"]}
        else:
            draft = self.call(
                "edit_page",
                {
                    "title": section["title"],
                    "markdown": section["markdown"],
                    "mappings": section["mappings"],
                    "visuals": section.get("visuals", []),
                    "template_requirements": [
                        item
                        for item in plan["template_requirements"]
                        if item["section"] == section["title"]
                    ],
                    "template_decisions": plan["template_decisions"],
                    "canonical_ownership": [
                        {"topic": unit["topic"], "section": unit["canonical_section"]}
                        for unit in plan["content_units"]
                    ],
                    "adjacent_section_summaries": [
                        {"title": item["title"], "purpose": item["purpose"]}
                        for item in plan["sections"]
                        if item["title"] != section["title"]
                    ],
                    "feedback": self.read(state, "feedback_ref", [])
                    or state.get("release_feedback", ""),
                },
                EditDraft,
            )
        draft = EditDraft.model_validate(draft).model_dump()
        draft["markdown"] = normalize_citation_syntax(draft["markdown"])
        for mapping in draft["mappings"]:
            mapping["passage"] = normalize_citation_syntax(mapping["passage"])
        return {"draft_ref": self.store.put(draft)}

    def _editorial_evidence(
        self, section: dict, markdown: str, mappings: list, placements: list, evidence: list
    ) -> dict:
        original = {item["obligation_id"]: item for item in section["mappings"]}
        changed = [item for item in mappings if item != original.get(item["obligation_id"])]
        mandatory = {item["obligation_id"] for item in changed}
        before, after = _markdown_changes(section["markdown"], markdown)
        labels = set(citation_labels(before + "\n" + after))
        assertions = [self.graph.assertion(key) for key in sorted(mandatory)]
        evidence_ids = {key for item in assertions for key in item["evidence_ids"]}
        evidence_ids.update(item["id"] for item in evidence if item["label"] in labels)
        evidence_ids.update(visual_evidence_ids(section.get("visuals", [])))
        contextual = set()
        for item in evidence:
            if (
                item["id"] not in evidence_ids
                or item["kind"] != "docs"
                or not _needs_source_context(item["text"])
            ):
                continue
            preceding = sorted(
                (
                    other
                    for other in evidence
                    if other["path"] == item["path"] and other["start_line"] < item["start_line"]
                ),
                key=lambda other: other["start_line"],
            )
            contextual.update(other["id"] for other in preceding[-2:])
        evidence_ids.update(contextual)
        return {
            "original_markdown": before,
            "edited_markdown": after,
            "qualifier_and_causality_risks": editorial_findings(before, after),
            "comparison_scope": (
                "Changed line ranges with nearby context; unchanged text was verified"
            ),
            "mandatory_obligation_ids": sorted(mandatory),
            "supporting_obligation_ids": [],
            "obligations": assertions,
            "original_evidence": [item for item in evidence if item["id"] in evidence_ids],
            "mappings": changed,
            "placements": [item for item in placements if mandatory & set(item["obligation_ids"])],
            "visuals": section.get("visuals", []),
        }

    def verify_edited_page(self, state: PipelineState) -> dict:
        plan = self._approved_plan(state)
        sections = self.read(state, "assembled_ref")
        section = self._editing_section(state)
        draft = self.read(state, "draft_ref")
        markdown = draft["markdown"]
        replacements = {item["obligation_id"]: item for item in draft.get("mappings", [])}
        original_ids = {item["obligation_id"] for item in section["mappings"]}
        mappings = [replacements.get(item["obligation_id"], item) for item in section["mappings"]]
        mappings.extend(
            item for item in draft.get("mappings", []) if item["obligation_id"] not in original_ids
        )
        old_citations = set(citation_labels(section["markdown"]))
        new_citations = set(citation_labels(markdown))
        findings = []
        if len(replacements) != len(draft.get("mappings", [])):
            findings.append("Editorial revision returned duplicate obligation mappings")
        if old_citations != new_citations:
            findings.append("Editorial revision changed citation coverage")
        ids = sorted(
            {item["obligation_id"] for item in section["mappings"]}
            | set(section["supporting_obligation_ids"])
        )
        evidence_ids = {
            key for identifier in ids for key in self.graph.assertion(identifier)["evidence_ids"]
        }
        evidence_ids.update(visual_evidence_ids(section.get("visuals", [])))
        evidence_ids.update(section.get("context_evidence_ids", []))
        evidence = [self.graph.evidence(key) for key in sorted(evidence_ids)]
        placements, placement_findings = placement_records(
            section["title"],
            markdown,
            mappings,
            {key: self.graph.assertion(key) for key in ids},
            {item["id"]: item for item in evidence},
        )
        findings.extend(placement_findings)
        if {item["obligation_id"] for item in mappings} != {
            item["obligation_id"] for item in section["mappings"]
        }:
            findings.append("Editorial revision lost final obligation placements")
        findings.extend(
            validate_visual_output(
                markdown, section.get("visuals", []), plan["source_assets"], evidence
            )
        )
        contract = self.read(state, "template_ref")
        local_contract = {
            **contract,
            "requirements": [
                item for item in contract["requirements"] if item["section"] == section["title"]
            ],
        }
        findings.extend(
            validate_template_output(
                [
                    {
                        "title": section["title"],
                        "markdown": _section_body(section["title"], markdown),
                    }
                ],
                local_contract,
                plan["template_decisions"],
            )
        )
        if not findings and ids and markdown != section["markdown"]:
            payload = self._editorial_evidence(section, markdown, mappings, placements, evidence)
            mandatory = set(payload["mandatory_obligation_ids"])
            if (
                len(mandatory) > 12
                or sum(len(item["text"]) for item in payload["original_evidence"]) > 45000
            ):
                findings.append(
                    "Editorial changes exceed the bounded audit: change fewer passages and keep "
                    "all other passages verbatim; at most 12 changed obligations and 45000 "
                    "source characters are permitted"
                )
                audit = {"accepted": False}
            else:
                audit = self.call(
                    "verify_page",
                    {
                        **payload,
                        "template_requirements": local_contract["requirements"],
                        "template_decisions": plan["template_decisions"],
                    },
                    AuditDraft,
                )
            if (
                not audit.get("accepted")
                or not mandatory.issubset(audit.get("covered_obligation_ids", []))
                or not diagram_element_ids(section.get("visuals", [])).issubset(
                    audit.get("covered_diagram_element_ids", [])
                )
            ):
                findings.extend(str(item) for item in audit.get("findings", []))
                if not findings:
                    findings.append("Edited text failed independent source audit")
        if findings:
            if state.get("attempt", 0) < self.repair_limit():
                return {
                    "attempt": state.get("attempt", 0) + 1,
                    "feedback_ref": self.store.put(findings),
                    "route": "edit_page",
                }
            return self.issue(state, "verify_edited_page", findings, "edit_page")
        edited = self.read(state, "edited_ref", [])
        replacement = {
            "title": section["title"],
            "markdown": markdown,
            "mappings": mappings,
            "placements": placements,
            "visuals": section.get("visuals", []),
            "context_evidence_ids": section.get("context_evidence_ids", []),
            "supporting_obligation_ids": section["supporting_obligation_ids"],
        }
        if state["edit_index"] < len(edited):
            edited[state["edit_index"]] = replacement
        else:
            edited.append(replacement)
        pending = self.read(
            state, "edit_queue_ref", list(range(state["edit_index"], len(sections)))
        )[1:]
        return {
            "edited_ref": self.store.put(edited),
            "edit_index": pending[0] if pending else len(sections),
            "edit_queue_ref": self.store.put(pending),
            "attempt": 0,
            "feedback_ref": "",
            "route": "edit_page" if pending else "audit_documentation",
        }

    def audit_documentation(self, state: PipelineState) -> dict:
        plan = self._approved_plan(state)
        sections = self.read(state, "edited_ref")
        expected = {item["id"] for item in self.assertions(state)}
        actual = [
            mapping["obligation_id"] for section in sections for mapping in section["mappings"]
        ]
        findings = []
        findings.extend(
            validate_template_output(
                [
                    {**section, "markdown": _section_body(section["title"], section["markdown"])}
                    for section in sections
                ],
                self.read(state, "template_ref"),
                plan["template_decisions"],
            )
        )
        repetition = repetition_report(sections)
        if repetition["semantic_candidates"]:
            semantic_audit = self.call(
                "audit_repetition",
                {"candidates": repetition["semantic_candidates"], "facts": self.assertions(state)},
                AuditDraft,
            )
            if not semantic_audit["accepted"] or semantic_audit["findings"]:
                if state.get("audit_attempt", 0) < 1:
                    return {
                        "edit_index": 0,
                        "edit_queue_ref": self.store.put(list(range(len(sections)))),
                        "audit_attempt": state.get("audit_attempt", 0) + 1,
                        "route": "edit_page",
                        "feedback_ref": self.store.put(
                            semantic_audit["findings"]
                            or ["Remove independently verified repetition; preserve all qualifiers"]
                        ),
                    }
                findings.extend(semantic_audit["findings"] or ["Unresolved semantic repetition"])
        if set(actual) != expected or len(actual) != len(set(actual)):
            findings.append("Final output does not map every obligation exactly once")
        if len(sections) != len(plan["sections"]):
            findings.append("Final section count differs from approved plan")
        for section, approved in zip(sections, plan["sections"], strict=False):
            if section["title"] != approved["title"]:
                findings.append("Edited section title differs from approved plan")
            for mapping in section["mappings"]:
                for label in mapping["citation_ids"]:
                    if not self.graph.evidence(label):
                        findings.append(f"Citation does not resolve: {label}")
            for label in citation_labels(section["markdown"]):
                if not self.graph.evidence(label):
                    findings.append(f"Citation does not resolve: {label}")
            assertions = {key: self.graph.assertion(key) for key in approved["obligation_ids"]}
            evidence_ids = {key for item in assertions.values() for key in item["evidence_ids"]}
            evidence_ids.update(visual_evidence_ids(approved.get("visuals", [])))
            evidence = {key: self.graph.evidence(key) for key in evidence_ids}
            _, placement_findings = placement_records(
                section["title"], section["markdown"], section["mappings"], assertions, evidence
            )
            findings.extend(placement_findings)
            findings.extend(
                validate_visual_output(
                    section["markdown"],
                    approved.get("visuals", []),
                    plan["source_assets"],
                    list(evidence.values()),
                )
            )
        if (
            repetition["duplicate_paragraphs"]
            and not findings
            and state.get("audit_attempt", 0) < 1
        ):
            affected_titles = {
                title for item in repetition["duplicate_paragraphs"] for title in item["sections"]
            }
            affected = [
                index
                for index, section in enumerate(sections)
                if section["title"] in affected_titles
            ]
            return {
                "edit_index": affected[0],
                "edit_queue_ref": self.store.put(affected),
                "audit_attempt": state.get("audit_attempt", 0) + 1,
                "route": "edit_page",
                "feedback_ref": self.store.put(
                    [
                        "Remove repeated full paragraphs. Retain detailed facts in their canonical "
                        "owner and use brief cited navigation elsewhere. Preserve every mapping.",
                        *repetition["duplicate_paragraphs"],
                    ]
                ),
            }
        if repetition["duplicate_paragraphs"]:
            findings.append("Final output contains duplicated full paragraphs")
        if findings:
            return self.issue(state, "audit_documentation", findings, "assemble_pages")
        audit = {
            "plan_hash": state["plan_hash"],
            "graph_revision": state["graph_revision"],
            "obligation_count": len(expected),
            "mapped_count": len(actual),
            "section_count": len(sections),
            "findings": [],
            "quality": repetition,
            "template_decisions": plan["template_decisions"],
            "visual_count": sum(len(section.get("visuals", [])) for section in sections),
        }
        self.store.write(f"runs/{self.run_id}/audit.json", json.dumps(audit, indent=2))
        return {"source_audit_index": 0, "route": "audit_source_to_document"}

    def audit_source_to_document(self, state: PipelineState) -> dict:
        inventory_record = self.read(state, "inventory_ref")
        batches = inventory_record["document_batches"]
        index = state.get("source_audit_index", 0)
        sections = self.read(state, "edited_ref")
        mapped = {item["obligation_id"] for section in sections for item in section["mappings"]}
        aspects = self.read(state, "source_aspects_ref", [])
        if index < len(batches):
            ids = set(batches[index])
            packet_aspects = [item for item in aspects if item["evidence_id"] in ids]
            facts = [item for item in self.assertions(state) if ids & set(item["evidence_ids"])]
            fact_ids = {item["id"] for item in facts}
            passages = [
                {
                    "section_id": section.get("section_id", section["title"]),
                    "mappings": [
                        item for item in section["mappings"] if item["obligation_id"] in fact_ids
                    ],
                }
                for section in sections
            ]
            audit = self.call(
                "audit_source_to_document",
                {
                    "blocks": [self.spans(state)[key] for key in ids],
                    "aspects": packet_aspects,
                    "facts": facts,
                    "final_passages": passages,
                },
                SourceAudit,
            )
            findings = audit["findings"] + audit_decisions(
                packet_aspects, audit["decisions"], facts
            )
            if findings:
                return self.issue(state, "audit_source_to_document", findings, "assemble_pages")
            return {"source_audit_index": index + 1, "route": "audit_source_to_document"}
        report = coverage_report(
            aspects,
            self.read(state, "source_decisions_ref", []),
            mapped,
            state["snapshot_ref"],
            state["graph_revision"],
            inventory_record.get("attachments", []),
        )
        report["blocks"] = {
            "total": sum(len(batch) for batch in batches),
            "independently_audited": sum(len(batch) for batch in batches),
        }
        report["facts_in_text"] = {"total": len(self.assertions(state)), "mapped": len(mapped)}
        report["non_substantive_candidates"] = self.read(state, "source_non_substantive_ref", [])
        report["exclusions"] = self.read(state, "exclusions_ref", [])
        report["conflict_candidates"] = len(self.graph.conflict_candidates())
        report["unsupported_assertions"] = 0
        if not report["complete"]:
            return self.issue(
                state,
                "audit_source_to_document",
                ["Source aspect or attachment coverage is incomplete"],
                "assemble_pages",
            )
        self.store.write(f"runs/{self.run_id}/source-coverage.json", json.dumps(report, indent=2))
        return {"source_coverage_ref": self.store.put(report), "route": "export_candidate"}

    def export_candidate(self, state: PipelineState) -> dict:
        plan = self._approved_plan(state)
        sections = self.read(state, "edited_ref")
        citations = sorted(
            {
                label
                for section in sections
                for mapping in section["mappings"]
                for label in mapping["citation_ids"]
            }
            | {label for section in sections for label in citation_labels(section["markdown"])}
        )
        evidence = [self.graph.evidence(label) for label in citations]
        snapshot = self.read(state, "snapshot_ref")
        source_text = {
            file["path"]: self.store.get_bytes(file["hash"]).decode("utf-8")
            for file in snapshot["files"]
            if file["kind"] == "docs"
        }
        source_urls = {
            path: source_url_from_markdown(markdown) for path, markdown in source_text.items()
        }
        source_ids = {
            path: next(
                (
                    line.partition(":")[2].strip().strip("\"'")
                    for line in markdown.splitlines()
                    if line.startswith("source_id:")
                ),
                None,
            )
            for path, markdown in source_text.items()
        }
        source_pages = snapshot.get("source_pages", {})
        destinations = {}
        for path, url in source_urls.items():
            page_hash = source_pages.get(source_ids[path]) or source_pages.get(url)
            if page_hash:
                destinations[path] = (
                    visible_html_text(self.store.get_bytes(page_hash).decode("utf-8")),
                    page_hash,
                )
        by_label = {item["label"]: item for item in evidence}
        selection_cache = {}

        def select(label: str, quote: str | None = None, claim: str | None = None) -> dict:
            key = (label, quote, claim)
            if key in selection_cache:
                return selection_cache[key]
            item = by_label.get(label)
            if not item or item["kind"] != "docs" or not source_urls.get(item["path"]):
                result = {"status": "fallback", "reason": "No original page URL", "url": None}
            else:
                destination = destinations.get(item["path"])
                result = select_text_fragment(
                    item["text"],
                    source_text[item["path"]],
                    quote,
                    destination[0] if destination else None,
                    claim,
                )
                result["url"] = (
                    text_fragment_url(
                        source_urls[item["path"]],
                        item["text"],
                        source_text[item["path"]],
                        quote,
                        destination[0] if destination else None,
                        claim,
                    )
                    if result["status"] != "fallback"
                    else None
                )
                result["source_url"] = source_urls[item["path"]]
                result["source_hash"] = item["file_hash"]
                result["destination_hash"] = destination[1] if destination else None
                support = quote or result.get("phrase")
                if support:
                    line_start = sum(
                        len(line) + 1
                        for line in source_text[item["path"]].splitlines()[: item["start_line"] - 1]
                    )
                    line_end = sum(
                        len(line) + 1
                        for line in source_text[item["path"]].splitlines()[: item["end_line"]]
                    )
                    offset = source_text[item["path"]].find(support, line_start, line_end)
                    if offset >= 0:
                        support_range = {
                            "snapshot_hash": item["file_hash"],
                            "source_path": item["path"],
                            "source_id": source_ids[item["path"]],
                            "evidence_id": item["id"],
                            "exact_quote": support,
                            "start_line": item["start_line"],
                            "end_line": item["end_line"],
                            "start_char": offset,
                            "end_char": offset + len(support),
                        }
                        row_text = source_text[item["path"]].splitlines()[item["start_line"] - 1]
                        row_cells = [
                            cell.strip() for cell in row_text.strip().strip("|").split("|")
                        ]
                        cell_index = next(
                            (index for index, cell in enumerate(row_cells) if support in cell), None
                        )
                        if cell_index is not None and row_text.lstrip().startswith("|"):
                            previous_rows = source_text[item["path"]].splitlines()[
                                : item["start_line"] - 1
                            ]
                            header = next(
                                (
                                    previous_rows[index - 1]
                                    for index in range(len(previous_rows) - 1, 0, -1)
                                    if re.match(r"^\s*\|[\s:|-]+\|\s*$", previous_rows[index])
                                ),
                                "",
                            )
                            columns = (
                                [cell.strip() for cell in header.strip().strip("|").split("|")]
                                if header
                                else []
                            )
                            support_range["table_row_line"] = item["start_line"]
                            support_range["table_cell_index"] = cell_index
                            support_range["table_column"] = (
                                columns[cell_index] if cell_index < len(columns) else None
                            )
                        result["support_range"] = support_range
                    else:
                        result.update(
                            {
                                "status": "fallback",
                                "reason": "Support quote lacks an exact source character range",
                                "url": None,
                            }
                        )
            selection_cache[key] = result
            return result

        direct_links = {item["label"]: select(item["label"])["url"] for item in evidence}
        section_targets = {
            section["title"]: f"#{section_anchor(section['title'])}" for section in sections
        }
        citation_occurrences = []

        def render(
            markdown: str,
            mappings: list[dict] | None = None,
            section: str = "",
            audit: bool = False,
        ) -> str:
            scoped = []
            for mapping in mappings or []:
                passage = mapping["passage"]
                location = markdown.find(passage)
                if location >= 0:
                    scoped.append((location, location + len(passage), mapping))

            def replace(match: re.Match) -> str:
                if markdown[match.end() :].startswith("("):
                    return match.group()
                kind = match.group(1)
                labels = re.findall(r"[CD]\d+", match.group())
                links = []
                for label in labels:
                    mapping = next(
                        (
                            item
                            for start, end, item in scoped
                            if start <= match.start() < end
                            and label in item.get("citation_ids", [])
                        ),
                        None,
                    )
                    quote = mapping.get("support_quotes", {}).get(label) if mapping else None
                    selection = select(label, quote, mapping["passage"] if mapping else None)
                    href = selection.get("url") or f"../evidence/{label}.md"
                    links.append(f"[{kind} {label}](<{href}>)")
                    if audit:
                        citation_occurrences.append(
                            {
                                "id": digest(
                                    [
                                        section,
                                        match.start(),
                                        label,
                                        mapping.get("obligation_id") if mapping else None,
                                    ]
                                )[:20],
                                "section": section,
                                "label": label,
                                "support_quote": quote,
                                **selection,
                            }
                        )
                return " ".join(links)

            return normalize_section_links(CITATION_GROUP.sub(replace, markdown), section_targets)

        rendered_sections = [
            render(
                _section_body(section["title"], section["markdown"]),
                section["mappings"],
                section["title"],
                True,
            )
            for section in sections
        ]
        chosen_hashes = {
            visual["asset_hash"]
            for section in plan["sections"]
            for visual in section["visuals"]
            if visual["kind"] == "image"
        }
        chosen_assets = {
            asset["hash"]: asset
            for asset in plan["source_assets"]
            if asset["hash"] in chosen_hashes
        }
        if len({asset_filename(asset) for asset in chosen_assets.values()}) != len(chosen_assets):
            raise ValueError("Exported asset filenames collide")
        candidate_hash = digest([state["plan_hash"], rendered_sections, evidence, chosen_assets])
        base = f"runs/{self.run_id}/candidates/{candidate_hash}"
        lines = [f"# {plan['title']}", "", "[Source index](../source-index.md)", ""]
        metadata = [item for item in plan["template_requirements"] if item["kind"] == "metadata"]
        for requirement in metadata:
            columns = requirement["columns"]
            lines.extend(
                [
                    "| " + " | ".join(columns) + " |",
                    "| " + " | ".join("---" for _ in columns) + " |",
                ]
            )
            values = {
                "Scope": "Selected source documentation",
                "Audience": "Readers familiar with the business domain",
                "Knowledge revision": f"`{state['graph_revision']}`",
                "Last reviewed": "Candidate awaiting final release review",
                "Source set": "[Source index](../source-index.md)",
            }
            for key in requirement.get("rows") or values:
                value = values.get(key, "Not recorded")
                cells = [key, value] + ["Not recorded"] * max(0, len(columns) - 2)
                lines.append("| " + " | ".join(cells[: len(columns)]) + " |")
            lines.append("")
        lines.extend(
            [
                " · ".join(
                    f"[{section['title']}](#{section_anchor(section['title'])})"
                    for section in sections
                ),
                "",
            ]
        )
        for section, markdown in zip(sections, rendered_sections, strict=True):
            lines.extend([f"## {section['title']}", "", markdown, ""])
        final_markdown = "\n".join(lines)
        self.store.write(f"{base}/documentation/index.md", final_markdown)
        for asset in chosen_assets.values():
            content = self.store.get_bytes(asset["hash"])
            suffix = ".jpg" if asset["format"] == "jpeg" else "." + asset["format"]
            validate_asset(content, suffix, **snapshot["asset_limits"])
            self.store.write(f"{base}/documentation/assets/{asset_filename(asset)}", content)
        for attachment in snapshot.get("attachments", []):
            if attachment.get("hash"):
                suffix = Path(attachment["path"]).suffix.lower()
                self.store.write(
                    f"{base}/attachments/{attachment['hash']}{suffix}",
                    self.store.get_bytes(attachment["hash"]),
                )
        self.store.write(
            f"{base}/attachments.json",
            json.dumps(snapshot.get("attachments", []), ensure_ascii=False, indent=2),
        )
        asset_index = ["# Source assets", ""]
        for asset in plan["source_assets"]:
            asset_index.extend(
                [
                    f"## {asset['path']}",
                    "",
                    f"SHA-256: `{asset['hash'] or 'Not frozen'}`",
                    f"Disposition: {asset['disposition']}",
                    "Reader placement: "
                    + ("included" if asset["hash"] in chosen_hashes else "not placed"),
                    "",
                    json.dumps(
                        {"references": asset["references"], "findings": asset["findings"]},
                        ensure_ascii=False,
                        indent=2,
                    ),
                    "",
                ]
            )
        self.store.write(f"{base}/source-assets.md", "\n".join(asset_index))
        final_mappings = []
        final_placements = []
        for section, rendered in zip(sections, rendered_sections, strict=True):
            section_start = final_markdown.index(f"## {section['title']}\n\n")
            section_start += len(f"## {section['title']}\n\n")
            for placement in section["placements"]:
                passage = render(placement["passage"], section["mappings"])
                offset = rendered.find(passage)
                if offset < 0 or rendered.count(passage) != 1:
                    raise ValueError("Export changed or duplicated a factual placement")
                start = section_start + offset
                final_placements.append(
                    {**placement, "passage": passage, "start": start, "end": start + len(passage)}
                )
            final_mappings.extend(
                {**mapping, "passage": render(mapping["passage"], [mapping])}
                for mapping in section["mappings"]
            )
        index = ["# Source index", ""]
        for item in evidence:
            label = item["label"]
            href = direct_links.get(label) or f"evidence/{label}.md"
            index.append(
                f"- [{label}](<{href}>): {item['path']} lines "
                f"{item['start_line']}-{item['end_line']}"
            )
            excerpt = "\n".join("    " + line for line in item["text"].splitlines())
            content = (
                f"# {label}\n\nSource: `{item['path']}` lines "
                f"{item['start_line']}-{item['end_line']}\n\n"
                f"Snapshot SHA-256: `{item['file_hash']}`\n\n"
                + (
                    f"Original page: {source_urls.get(item['path'])}\n\n"
                    if item["kind"] == "docs" and source_urls.get(item["path"])
                    else ""
                )
                + f"{excerpt}\n"
            )
            if item.get("source_kind") == "attachment":
                suffix = Path(item["path"]).suffix.lower()
                locator = json.dumps(item["locator"], ensure_ascii=False, sort_keys=True)
                content += (
                    f"\nNative locator: `{locator}`\n\n"
                    f"[Frozen attachment](../attachments/{item['file_hash']}{suffix})\n"
                )
            self.store.write(f"{base}/evidence/{label}.md", content)
        self.store.write(f"{base}/source-index.md", "\n".join(index) + "\n")
        self.store.write(
            f"{base}/audit.json",
            json.dumps(
                {
                    "plan_hash": state["plan_hash"],
                    "graph_revision": state["graph_revision"],
                    "mappings": final_mappings,
                    "placements": final_placements,
                    "content_units": plan["content_units"],
                    "template_requirements": plan["template_requirements"],
                    "template_decisions": plan["template_decisions"],
                    "source_assets": plan["source_assets"],
                    "asset_decisions": plan["asset_decisions"],
                    "visuals": [
                        {**visual, "review_status": "approved"}
                        for section in plan["sections"]
                        for visual in section["visuals"]
                    ],
                    "quality": repetition_report(sections),
                    "citations": citations,
                    "source_links": direct_links,
                    "citation_occurrences": citation_occurrences,
                    "candidate_hash": candidate_hash,
                    "source_coverage": self.read(state, "source_coverage_ref"),
                    "attachments": snapshot.get("attachments", []),
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
        directory = self.store.root / base
        manifest = {
            path.relative_to(directory).as_posix(): digest(path.read_bytes())
            for path in directory.rglob("*")
            if path.is_file()
        }
        self.store.write(
            f"{base}/candidate-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2)
        )
        verify_bundle(directory, manifest)
        self.stages.mirror_candidate(candidate_hash, directory)
        return {
            "candidate_ref": candidate_hash,
            "candidate_manifest_hash": digest(manifest),
            "status": "ready_for_review",
            "route": "review_release",
        }

    def review_release(self, state: PipelineState) -> dict:
        if state.get("runtime_signature") != self.runtime_signature():
            return {"status": "stale", "route": END}
        candidate = state["candidate_ref"]
        decision = (
            {
                "action": "approve_release",
                "candidate_hash": candidate,
                "reviewer": "Autopilot policy v2",
                "actor_type": "policy",
                "rationale": "Candidate passed the final audit and bundle integrity checks",
            }
            if state.get("mode") == "autopilot"
            else interrupt(
                {
                    "kind": "release",
                    "candidate_hash": candidate,
                    "path": str(
                        self.store.root
                        / "runs"
                        / self.run_id
                        / "step22"
                        / "candidates"
                        / candidate
                        / "documentation"
                        / "index.md"
                    ),
                    "error": state.get("review_error", ""),
                }
            )
        )
        if not isinstance(decision, dict) or decision.get("candidate_hash") != candidate:
            return {
                "route": "review_release",
                "review_error": "Decision has a stale candidate hash",
            }
        if not decision.get("reviewer") or not decision.get("rationale"):
            return {
                "route": "review_release",
                "review_error": "Reviewer and rationale are required",
            }
        action = decision.get("action")
        record = {
            **decision,
            "plan_hash": state["plan_hash"],
            "timestamp": datetime.now(UTC).isoformat(),
        }
        ref = self.store.put(record)
        self.store.write(
            f"runs/{self.run_id}/reviews/release-{ref}.json",
            json.dumps(record, ensure_ascii=False, indent=2),
        )
        if action == "approve_release":
            return {"release_ref": ref, "route": "finalize_release", "review_error": ""}
        if action == "request_changes":
            return {
                "release_feedback": str(decision["rationale"]),
                "edit_index": 0,
                "edited_ref": self.store.put([]),
                "edit_queue_ref": self.store.put(
                    list(range(len(self.read(state, "assembled_ref"))))
                ),
                "route": "edit_page",
            }
        if action == "reject_release":
            return {"status": "rejected", "route": END}
        return {"route": "review_release", "review_error": "Unsupported release review action"}

    def finalize_release(self, state: PipelineState) -> dict:
        decision = self.read(state, "release_ref")
        if decision.get("candidate_hash") != state["candidate_ref"]:
            raise ValueError("Release approval is stale")
        directory = (
            self.store.root
            / self.stages.step("export_candidate")
            / "candidates"
            / state["candidate_ref"]
        )
        expected = json.loads((directory / "candidate-manifest.json").read_text("utf-8"))
        if digest(expected) != state["candidate_manifest_hash"]:
            raise ValueError("Candidate manifest changed after review")
        verify_bundle(directory, expected)
        manifest = {
            "candidate_hash": state["candidate_ref"],
            "plan_hash": state["plan_hash"],
            "graph_revision": state["graph_revision"],
            "review": state["release_ref"],
            "completed_at": datetime.now(UTC).isoformat(),
        }
        self.store.write(
            f"runs/{self.run_id}/releases/{state['candidate_ref']}.json",
            json.dumps(manifest, indent=2),
        )
        self.store.write(
            str(self.stages.step("finalize_release") / "release.json"),
            json.dumps(manifest, indent=2),
        )
        completion = (
            "complete_with_exclusions" if self.read(state, "exclusions_ref", []) else "complete"
        )
        return {
            "completion_status": completion,
            "status": "awaiting_final_receipt_review"
            if state.get("mode") == "manual"
            else completion,
        }

    def review_issues(self, state: PipelineState) -> dict:
        if state.get("runtime_signature") != self.runtime_signature():
            return {"status": "stale", "route": END}
        issue = self.read(state, "issue_ref")
        decision = interrupt(
            {"kind": "issue", "issue": issue, "error": state.get("review_error", "")}
        )
        if not isinstance(decision, dict) or decision.get("revision") != issue["revision"]:
            return {"route": "review_issues", "review_error": "Issue review revision mismatch"}
        if not decision.get("reviewer") or not decision.get("rationale"):
            return {"route": "review_issues", "review_error": "Reviewer and rationale are required"}
        if decision.get("action") not in {"retry", "reject"}:
            return {"route": "review_issues", "review_error": "Unsupported issue review action"}
        self.store.write(
            f"runs/{self.run_id}/reviews/issue-{issue['revision']}.json",
            json.dumps(decision, ensure_ascii=False, indent=2),
        )
        if decision.get("action") == "retry":
            return {
                "route": state["issue_return"],
                "attempt": 0,
                "feedback_ref": self.store.put(issue["findings"]),
                "status": "running",
                "review_error": "",
            }
        if decision.get("action") == "reject":
            return {"route": END, "status": "rejected"}

    def build(self, checkpointer):
        builder = StateGraph(PipelineState)
        for name in STEPS[:25]:
            builder.add_node(name, self.logged_node(name))
        for name in STEPS[27:]:
            builder.add_node(name, self.logged_node(name))
        builder.add_node("review_stage", self.review_stage)
        builder.add_node("resolve_issues_automatically", self.resolve_issues_automatically)
        builder.add_edge(START, "snapshot_inputs")
        fixed = {
            "snapshot_inputs": "inventory_sources",
            "analyze_code_unit": "verify_code_unit",
            "extract_document_batch": "verify_document_batch",
            "link_graph_batch": "verify_graph_batch",
            "write_section": "verify_section",
            "edit_page": "verify_edited_page",
            "export_candidate": "review_release",
            "finalize_release": END,
        }
        routed = {
            "inventory_sources": ["analyze_code_unit", "extract_document_batch"],
            "verify_code_unit": ["analyze_code_unit", "extract_document_batch", "review_issues"],
            "verify_document_batch": [
                "extract_document_batch",
                "link_graph_batch",
                "review_issues",
            ],
            "verify_graph_batch": ["link_graph_batch", "finalize_graph", "review_issues"],
            "finalize_graph": ["compile_template", "review_issues"],
            "compile_template": ["draft_page_plan", "review_issues"],
            "draft_page_plan": ["retrieve_plan_evidence"],
            "retrieve_plan_evidence": ["retrieve_plan_evidence", "validate_page_plan"],
            "validate_page_plan": ["draft_page_plan", "review_plan", "review_issues"],
            "review_plan": ["retrieve_section_evidence", "draft_page_plan", "review_plan", END],
            "retrieve_section_evidence": ["write_section", "review_issues"],
            "verify_section": [
                "write_section",
                "retrieve_section_evidence",
                "assemble_pages",
                "review_issues",
            ],
            "assemble_pages": ["edit_page", "review_issues"],
            "verify_edited_page": ["edit_page", "audit_documentation", "review_issues"],
            "audit_documentation": ["export_candidate", "edit_page", "review_issues"],
            "review_release": ["finalize_release", "edit_page", "review_release", END],
            "review_issues": [
                "analyze_code_unit",
                "extract_document_batch",
                "link_graph_batch",
                "finalize_graph",
                "compile_template",
                "draft_page_plan",
                "retrieve_section_evidence",
                "write_section",
                "assemble_pages",
                "edit_page",
                "review_issues",
                END,
            ],
        }
        for name in STEPS[:25]:
            if name in {"review_plan", "review_release", "review_issues"}:
                builder.add_conditional_edges(
                    name, lambda state: state["route"], list(STEPS) + [END]
                )
            else:
                builder.add_edge(name, "review_stage")
        for name in STEPS[27:]:
            builder.add_edge(name, "review_stage")
        targets = sorted(
            set(fixed.values())
            | {target for values in routed.values() for target in values}
            | {"review_stage", "resolve_issues_automatically"}
            | set(STEPS[27:])
        )
        builder.add_conditional_edges("review_stage", lambda state: state["route"], targets)
        builder.add_conditional_edges(
            "resolve_issues_automatically",
            lambda state: state["route"],
            [
                END,
                "verify_document_batch",
                "extract_document_batch",
                "link_graph_batch",
                "finalize_graph",
                "analyze_code_unit",
            ],
        )
        return builder.compile(checkpointer=checkpointer)

    def logged_node(self, name: str):
        function = (
            (lambda state: getattr(code_stages, name)(self, state))
            if name in code_stages.CODE_STAGE_NAMES
            else getattr(self, name)
        )

        def execute(state: PipelineState) -> dict:
            if name not in {"snapshot_inputs", "review_plan", "review_release", "review_issues"}:
                if state.get("runtime_signature") != self.runtime_signature():
                    raise ValueError("Runtime changed; start a new run revision")
            started = monotonic()
            event_path = self.store.root / "runs" / self.run_id / "events.jsonl"
            event_offset = event_path.stat().st_size if event_path.exists() else 0
            update = function(state)
            if name == "inventory_code_scope" and update.get("route") not in {
                "review_issues",
                "resolve_issues_automatically",
            }:
                update["route"] = "inventory_source_aspects"
            cost_pln = 0.0
            if event_path.exists():
                with event_path.open("rb") as events:
                    events.seek(event_offset)
                    for line in events:
                        event = json.loads(line)
                        if event.get("event") == "response":
                            cost_pln += float(event.get("cost_pln", 0.0))
            if name not in {"review_plan", "review_release", "review_issues"}:
                if name == "snapshot_inputs":
                    self.stages.initialize(
                        state.get("mode", "manual"),
                        state.get("policy_version", "v2"),
                        update["runtime_signature"],
                        self.repair_limit(),
                    )
                default_routes = {
                    "snapshot_inputs": "inventory_sources",
                    "analyze_code_unit": "verify_code_unit",
                    "extract_document_batch": "verify_document_batch",
                    "link_graph_batch": "verify_graph_batch",
                    "write_section": "verify_section",
                    "edit_page": "verify_edited_page",
                    "export_candidate": "review_release",
                    "finalize_release": END,
                }
                update.setdefault("route", default_routes.get(name, END))
                update["stage_record"] = self.stages.record(name, state, update, cost_pln)
                if update["route"] in {
                    "review_plan",
                    "review_release",
                    "review_issues",
                    "review_stage",
                }:
                    self.stages.pending(update["route"], update["stage_record"])
            else:
                self.stages.record(name, state, update, cost_pln)
            self.store.event(
                self.run_id,
                name,
                "completed",
                seconds=monotonic() - started,
                route=update.get("route"),
                status=update.get("status"),
                attempt=state.get("attempt", 0),
                repair=bool(update.get("attempt", 0) > state.get("attempt", 0)),
            )
            return update

        return execute

    def review_stage(self, state: PipelineState) -> dict:
        record = state["stage_record"]
        destination = state["route"]
        if state.get("mode") != "manual" or destination in {
            "review_issues",
            "resolve_issues_automatically",
        }:
            if state.get("mode") != "manual":
                self.stages.skip(
                    "review_stage", "Autopilot advances through validated stage outputs"
                )
            return {"route": destination}
        decision = interrupt(
            {
                "kind": "stage",
                **record,
                "next": destination,
                "actions": ["approve", "request_correction", "reject"],
            }
        )
        if (
            not isinstance(decision, dict)
            or decision.get("hash") != record["hash"]
            or decision.get("stage") != record["stage"]
            or decision.get("item") != record["item"]
        ):
            return {
                "route": "review_stage",
                "review_error": "Decision does not match the current artifact",
            }
        if not decision.get("reviewer") or not decision.get("rationale"):
            return {"route": "review_stage", "review_error": "Reviewer and rationale are required"}
        action = decision.get("action")
        decision_ref = self.store.put(
            {**decision, "actor_type": "human", "artifact_hash": record["hash"]}
        )
        self.store.write(
            f"runs/{self.run_id}/reviews/stage-{decision_ref}.json",
            json.dumps(self.store.get(decision_ref), indent=2),
        )
        if action == "approve":
            self.stages.record(
                "review_stage", state, {"route": destination, "decision_ref": decision_ref}
            )
            update = {"route": destination, "review_error": ""}
            if record["stage"] == "finalize_release":
                update["status"] = state["completion_status"]
            return update
        if action == "reject":
            self.stages.record(
                "review_stage",
                state,
                {"route": END, "decision_ref": decision_ref, "status": "rejected"},
            )
            return {"route": END, "status": "rejected"}
        repair_targets = {
            "verify_code_unit": "analyze_code_unit",
            "verify_document_batch": "extract_document_batch",
            "validate_page_plan": "draft_page_plan",
            "verify_section": "write_section",
            "verify_edited_page": "edit_page",
        }
        target = repair_targets.get(record["stage"], record["stage"])
        if action == "request_correction" and target in {
            "analyze_code_unit",
            "extract_document_batch",
            "draft_page_plan",
            "write_section",
            "edit_page",
        }:
            update = {
                "route": target,
                "feedback_ref": self.store.put([decision["rationale"]]),
                "attempt": state.get("attempt", 0) + 1,
                "release_ref": "",
            }
            if target == "draft_page_plan":
                update["approval_ref"] = ""
            self.stages.record("review_stage", state, {"decision_ref": decision_ref, **update})
            return update
        return {
            "route": "review_stage",
            "review_error": "This stage cannot be corrected in place; create a new run revision",
        }

    def resolve_issues_automatically(self, state: PipelineState) -> dict:
        issue = self.read(state, "issue_ref")
        unresolved = {
            "actor_type": "policy",
            "stage": issue["stage"],
            "findings": issue["findings"],
            "source_revision": state.get("snapshot_ref"),
            "reason": "Relevant unresolved information cannot be excluded to obtain completeness",
        }
        ref = self.store.put(unresolved)
        spans = self.spans(state) if state.get("inventory_ref") else {}
        records = [
            {
                "source_id": key,
                "path": span["path"],
                "start_line": span["start_line"],
                "end_line": span["end_line"],
                "reason": unresolved["reason"],
                "decision_ref": ref,
            }
            for key, span in spans.items()
        ]
        self.store.write(f"runs/{self.run_id}/unresolved.json", json.dumps(unresolved, indent=2))
        result = {
            "status": "incomplete",
            "route": END,
            "source_coverage_ref": ref,
            "unresolved_ref": self.store.put(records),
        }
        self.stages.record("resolve_issues_automatically", state, result)
        return result
