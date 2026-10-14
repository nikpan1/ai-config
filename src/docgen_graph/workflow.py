import json
import os
import re
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from difflib import SequenceMatcher
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path
from time import monotonic
from typing import TypedDict

import httpx
from google.genai.errors import APIError
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import ValidationError

from docgen_graph.assets import asset_filename, validate_asset, verify_bundle
from docgen_graph.authoring.template import (
    bind_plan_sections,
    document_title,
    fold_plan_sections,
    number_generated_headings,
)
from docgen_graph.authoring.tools import AuthoringTools, declarations
from docgen_graph.completion import (
    GroundedDocument,
    SourceDocumentAudit,
    SourcePlan,
    citation_excerpt_files,
    citation_findings,
    document_content_hash,
    document_structure_findings,
    document_verification,
    render_grounded_document,
    visual_findings,
)
from docgen_graph.completion_repairs import (
    DocumentRepairs,
    apply_repairs,
    assign_document_ids,
    audit_targets,
    citation_targets,
    preserve_planned_sections,
)
from docgen_graph.contracts import (
    AuditDraft,
    DocumentExtractionDraft,
    EditDraft,
    PagePlanDraft,
    SectionDraft,
    VisualEvidenceDraft,
)
from docgen_graph.document_preview import render_document_preview
from docgen_graph.document_repairs import repair_document_draft, unique_visual_quote
from docgen_graph.documentation_contracts import AspectInventory, SourceAudit
from docgen_graph.editorial import (
    DocumentRevision,
    EditorialReview,
    RevisionVerification,
    apply_editorial_revision,
    merge_editorial_findings,
    outstanding_audit_findings,
    revision_accepted,
    revision_findings,
    unchanged_audit_targets,
)
from docgen_graph.evidence_contracts import (
    AnalysisProvenance,
    DeltaVerification,
    EvidenceLocator,
    EvidenceQuery,
    KnowledgeDelta,
    SourceCoverageItem,
)
from docgen_graph.ingestion import extraction_packet, inventory, snapshot_inputs
from docgen_graph.knowledge import KnowledgeGraph, normalized_assertion
from docgen_graph.model import implementation_signature
from docgen_graph.planning import (
    bounded_source_overview,
    normalize_plan_hierarchy,
    plan_findings,
    render_source_plan,
    section_evidence_ids,
    section_queries,
)
from docgen_graph.presentation import (
    business_prose_findings,
    compact_citations,
    exact_support,
    group_repeated_list_citations,
    mapping_occurrences,
    merge_mapping_occurrences,
    render_subprocess_catalog,
    replace_subsection,
    strip_authored_visuals,
    support_findings,
    uncited_business_passages,
    unmapped_citation_findings,
    visual_support_requirements,
)
from docgen_graph.quality import (
    compile_requirements,
    content_groups,
    content_units,
    diagram_element_ids,
    diagram_source,
    duplicate_risks,
    placement_records,
    position_visuals,
    render_visuals,
    repetition_report,
    section_anchor,
    validate_quality_plan,
    validate_template_output,
    validate_visual_output,
    visual_evidence_ids,
)
from docgen_graph.quality_policy import evaluate_coverage
from docgen_graph.semantic_contracts import NavigationalGraphDraft, SemanticGraphDraft
from docgen_graph.semantic_graph import (
    anchor_semantic_quotes,
    publish_semantic_batch,
    salvage_semantic_proposal,
    semantic_payload,
    semantic_quality_report,
    semantic_records,
    topic_register,
    validate_semantic_proposal,
)
from docgen_graph.source_coverage import (
    coverage_report,
    editorial_findings,
    source_audit_findings,
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
    editorial_review_ref: str
    editorial_candidate_ref: str
    editorial_history_ref: str
    editorial_round: int
    completion_context_ref: str
    completion_plan_ref: str
    completion_plan_path: str
    completion_draft_ref: str
    completion_audit_ref: str
    completion_findings_ref: str
    completion_attempt: int
    completion_repair_phase: str
    completion_repair_counts: dict
    completion_repair_records_ref: str
    completion_audit_diagnostics_ref: str
    completion_audit_count: int
    completion_packet_index: int
    completion_sections_ref: str
    completion_path: str
    limitations_ref: str
    recovery_counts: dict
    deadline: float
    prefetched_aspects_ref: str
    prefetched_extractions_ref: str
    final_source_decisions_ref: str
    graph_only: bool
    fact_batches_ref: str
    semantic_index: int
    semantic_payload_ref: str
    semantic_draft_ref: str
    semantic_raw_draft_ref: str
    semantic_anchoring_ref: str
    semantic_canonical_ref: str
    semantic_audit_ref: str
    graph_quality_ref: str
    visual_attempt: int
    visual_feedback_ref: str
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
    tool_provenance_ref: str
    document_provenance_ref: str
    document_candidate_provenance_ref: str
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
    draft["markdown"] = compact_citations(normalize_citation_syntax(draft["markdown"]))
    for mapping in draft["mappings"]:
        for occurrence in [mapping] + mapping.get("additional_passages", []):
            occurrence["passage"] = compact_citations(
                normalize_citation_syntax(occurrence["passage"])
            )
            normalized = []
            for key in occurrence["citation_ids"]:
                label = labels.get(key, key)
                match = re.fullmatch(r"\[?(?:Legacy|Code)\s+([CD]\d+)\]?", label)
                normalized.append(match.group(1) if match else label)
            occurrence["citation_ids"] = normalized
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

    def fast_mode(self) -> bool:
        return getattr(getattr(self.model, "settings", None), "fast_mode", False)

    def minimum_coverage(self) -> float:
        return getattr(getattr(self.model, "settings", None), "minimum_coverage", 1.0)

    def source_first(self, state: PipelineState) -> bool:
        return state.get("mode") in {"autopilot", "manual"} and getattr(
            getattr(self.model, "settings", None), "source_first", False
        )

    def limitations(self, state: PipelineState, findings: list[str]) -> str:
        return self.store.put(
            list(dict.fromkeys(self.read(state, "limitations_ref", []) + findings))
        )

    def call_many(self, stage: str, payloads: list[dict], schema) -> list[dict]:
        if hasattr(self.model, "call_many"):
            return [
                schema.model_validate(item).model_dump()
                for item in self.model.call_many(stage, payloads, schema)
            ]
        return [self.call(stage, payload, schema) for payload in payloads]

    def runtime_signature(self) -> str:
        prompts = files("docgen_graph").joinpath("prompts")
        prompt_hashes = {item.name: digest(item.read_bytes()) for item in prompts.iterdir()}
        model_name = getattr(getattr(self.model, "settings", None), "model", "test-double")
        settings = getattr(self.model, "settings", None)
        configuration = {
            key: getattr(settings, key, None)
            for key in (
                "output_tokens",
                "authoring_output_tokens",
                "thinking_level",
                "audit_thinking_level",
                "authoring_thinking_level",
                "editorial_review",
                "editorial_round_limit",
                "request_tokens",
                "timeout_seconds",
                "authoring_turn_limit",
                "authoring_timeout_seconds",
                "authoring_result_limit",
                "fast_mode",
                "model_workers",
                "minimum_coverage",
                "run_timeout_seconds",
                "source_first",
                "graph_assisted_retrieval",
                "finalization_reserve_seconds",
            )
        }
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
            if state.get("mode") == "autopilot" or self.source_first(state)
            else "review_issues",
            "status": "resolving_issue"
            if state.get("mode") == "autopilot" or self.source_first(state)
            else "awaiting_issue_review",
        }

    def snapshot_inputs(self, state: PipelineState) -> dict:
        if state.get("code"):
            raise ValueError("Code inputs are no longer supported; start a documentation-only run")
        settings = getattr(self.model, "settings", None)
        snapshot = snapshot_inputs(
            self.store,
            Path(state["docs"]),
            None,
            None if state.get("graph_only") else Path(state["template"]),
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
            "deadline": state.get("deadline", 0),
            "status": "running",
        }

    def inventory_sources(self, state: PipelineState) -> dict:
        source = self.read(state, "snapshot_ref")
        try:
            result = inventory(self.store, source)
        except ValueError as error:
            return self.issue(state, "inventory_sources", [str(error)], "inventory_sources")
        self.graph.add_evidence(result["spans"])
        self.graph.add_structure(result)
        return {
            "inventory_ref": self.store.put(result),
            "document_index": 0,
            "graph_index": 0,
            "semantic_index": 0,
            "fact_batches_ref": self.store.put([]),
            "assertions_ref": self.store.put([]),
            "exclusions_ref": self.store.put([]),
            "source_aspect_index": 0,
            "source_aspects_ref": self.store.put([]),
            "source_decisions_ref": self.store.put([]),
            "source_non_substantive_ref": self.store.put([]),
            "route": "prepare_source_images",
        }

    def prepare_source_images(self, state: PipelineState) -> dict:
        from docgen_graph.image_preparation import prepare_image_context

        prepared = prepare_image_context(
            self.model,
            self.store,
            self.read(state, "snapshot_ref"),
            self.read(state, "inventory_ref"),
        )
        self.graph.add_evidence(prepared["spans"])
        return {
            "inventory_ref": self.store.put(prepared),
            "limitations_ref": self.limitations(
                state,
                [
                    f"Image interpretation unavailable: {item['path']}"
                    for item in prepared.get("image_analyses", [])
                    if item.get("status") == "unavailable"
                ],
            ),
            "route": "extract_document_batch"
            if self.source_first(state)
            else "inventory_source_aspects",
        }

    def inventory_source_aspects(self, state: PipelineState) -> dict:
        inventory_record = self.read(state, "inventory_ref")
        index = state.get("source_aspect_index", 0)
        batches = inventory_record["document_batches"]
        if index >= len(batches):
            return {"route": "extract_document_batch"}
        if self.fast_mode() and not state.get("prefetched_aspects_ref"):
            drafts = self.call_many(
                "inventory_aspects",
                [
                    {**extraction_packet(inventory_record, batch), "feedback": [], "previous": None}
                    for batch in range(len(batches))
                ],
                AspectInventory,
            )
            return {
                "prefetched_aspects_ref": self.store.put(drafts),
                "route": "inventory_source_aspects",
            }
        spans = self.spans(state)
        draft = (
            self.read(state, "prefetched_aspects_ref")[index]
            if (self.fast_mode() and not state.get("attempt"))
            else self.call(
                "inventory_aspects",
                {
                    **extraction_packet(inventory_record, index),
                    "feedback": self.read(state, "feedback_ref", []),
                    "previous": self.read(state, "draft_ref") if state.get("attempt") else None,
                },
                AspectInventory,
            )
        )
        aspects, findings = validate_aspect_inventory(draft["aspects"], spans)
        covered = {item["evidence_id"] for item in aspects} | set(draft["non_substantive"])
        if covered != set(batches[index]):
            findings.append("Independent aspect inventory does not account for every source block")
        if findings:
            if state.get("attempt", 0) < self.repair_limit():
                return {
                    "attempt": state.get("attempt", 0) + 1,
                    "feedback_ref": self.store.put(findings),
                    "draft_ref": self.store.put(draft),
                    "route": "inventory_source_aspects",
                }
            return self.issue(
                state, "inventory_source_aspects", findings, "inventory_source_aspects"
            )
        return {
            "attempt": 0,
            "feedback_ref": "",
            "draft_ref": "",
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
        if self.fast_mode() and not state.get("prefetched_extractions_ref"):
            drafts = self.call_many(
                "extract_document",
                [
                    {**extraction_packet(inventory_record, batch), "feedback": [], "previous": None}
                    for batch in range(len(inventory_record["document_batches"]))
                ],
                DocumentExtractionDraft,
            )
            return {
                "prefetched_extractions_ref": self.store.put(drafts),
                "route": "extract_document_batch",
            }
        payload = {
            **extraction_packet(inventory_record, state["document_index"]),
            "feedback": self.read(state, "feedback_ref", []),
            "previous": self.read(state, "draft_ref") if state.get("attempt") else None,
        }
        draft = (
            self.read(state, "prefetched_extractions_ref")[state["document_index"]]
            if (self.fast_mode() and not state.get("attempt"))
            else self.call("extract_document", payload, DocumentExtractionDraft)
        )
        model_name = getattr(getattr(self.model, "settings", None), "model", "test-double")
        provenance = AnalysisProvenance(
            id=digest([model_name, "extract_document.v1", payload, draft]),
            provider="gemini" if model_name == "gemini-3.8-flash" else "test-double",
            model=model_name,
            sdk_version=version("google-genai"),
            prompt_version="extract_document.v1",
            input_hash=digest(payload),
            scope_id="full",
        )
        for assertion in draft["assertions"]:
            assertion["provenance_ids"] = [provenance.id]
            assertion["review_status"] = "unreviewed"
        return {
            "draft_ref": self.store.put(draft),
            "document_candidate_provenance_ref": self.store.put(provenance.model_dump()),
        }

    def verify_document_batch(self, state: PipelineState) -> dict:
        inventory_record = self.read(state, "inventory_ref")
        ids = inventory_record["document_batches"][state["document_index"]]
        draft = self.read(state, "draft_ref")
        findings = []
        packet = extraction_packet(inventory_record, state["document_index"])
        allowed = {item["id"] for item in packet["blocks"] + packet["context_blocks"]}
        try:
            records = [
                normalized_assertion({**item, "review_status": "verified"}, allowed)
                for item in draft["assertions"]
            ]
            if any(not set(record["evidence_ids"]).intersection(ids) for record in records):
                findings.append("Every extracted fact must cite at least one owned source block")
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
        if self.source_first(state):
            valid_records = []
            for item in draft["assertions"]:
                try:
                    valid_records.append(
                        normalized_assertion({**item, "review_status": "unreviewed"}, allowed)
                    )
                except (ValueError, TypeError) as error:
                    findings.append(str(error))
            next_index = state["document_index"] + 1
            return {
                "assertions_ref": self.store.put(self.assertions(state) + valid_records),
                "fact_batches_ref": self.store.put(
                    self.read(state, "fact_batches_ref", [])
                    + [[item["id"] for item in valid_records]]
                ),
                "document_provenance_ref": self.store.put(
                    self.read(state, "document_provenance_ref", [])
                    + [self.read(state, "document_candidate_provenance_ref")]
                ),
                "exclusions_ref": self.store.put(self.read(state, "exclusions_ref", []) + excluded),
                "limitations_ref": self.limitations(state, findings),
                "document_index": next_index,
                "attempt": 0,
                "draft_ref": "",
                "feedback_ref": "",
                "route": "extract_document_batch"
                if next_index < len(inventory_record["document_batches"])
                else "link_graph_batch",
            }
        if missing and self.minimum_coverage() == 1.0:
            findings.append(f"Document blocks lack coverage: {sorted(missing)}")
        audit = (
            self.call(
                "verify_document",
                {
                    **packet,
                    "draft": draft,
                    "coverage_audited_separately": self.minimum_coverage() < 1.0,
                },
                AuditDraft,
            )
            if not findings
            else {"accepted": False, "findings": []}
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
        pending = self.read(state, "pending_document_ref")
        aspects = [
            item
            for item in self.read(state, "source_aspects_ref", [])
            if item["evidence_id"] in ids
        ]
        audit = self.call(
            "audit_source_coverage",
            {
                **extraction_packet(inventory_record, state["document_index"]),
                "aspects": aspects,
                "minimum_coverage": self.minimum_coverage(),
                "facts": pending["records"],
                "non_substantive_candidates": [
                    item
                    for item in self.read(state, "source_non_substantive_ref", [])
                    if item["evidence_id"] in ids
                ],
            },
            SourceAudit,
        )
        findings = audit["findings"] + source_audit_findings(
            aspects,
            audit["decisions"],
            pending["records"],
            all_aspects=self.read(state, "source_aspects_ref", []),
            prior_decisions=self.read(state, "source_decisions_ref", []),
            minimum_coverage=self.minimum_coverage(),
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
            "fact_batches_ref": self.store.put(
                self.read(state, "fact_batches_ref", [])
                + [[record["id"] for record in pending["records"]]]
            ),
            "document_provenance_ref": self.store.put(
                self.read(state, "document_provenance_ref", [])
                + [self.read(state, "document_candidate_provenance_ref")]
            ),
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
        if not self.assertions(state):
            return {"route": "propose_semantic_graph"}
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
            else "propose_semantic_graph",
        }

    def propose_semantic_graph(self, state: PipelineState) -> dict:
        index = state.get("semantic_index", 0)
        batches = self.read(state, "fact_batches_ref", [])
        if index >= len(batches):
            return {"route": "finalize_graph"}
        if not batches[index]:
            return {"semantic_index": index + 1, "route": "propose_semantic_graph"}
        packet = extraction_packet(self.read(state, "inventory_ref"), index)
        fact_ids = set(batches[index])
        payload = semantic_payload(
            [fact for fact in self.assertions(state) if fact["id"] in fact_ids],
            packet["blocks"],
            packet["context_blocks"],
            topic_register(self.graph),
        )
        payload.update({"stories": packet["stories"], "context_policy": packet["context_policy"]})
        raw_draft = self.call(
            "semantic_graph",
            {
                **payload,
                "feedback": self.read(state, "feedback_ref", []),
                "previous": self.read(state, "semantic_draft_ref")
                if state.get("attempt")
                else None,
            },
            NavigationalGraphDraft if self.source_first(state) else SemanticGraphDraft,
        )
        draft, anchoring = anchor_semantic_quotes(raw_draft, payload)
        return {
            "semantic_payload_ref": self.store.put(payload),
            "semantic_raw_draft_ref": self.store.put(raw_draft),
            "semantic_anchoring_ref": self.store.put(anchoring),
            "semantic_draft_ref": self.store.put(draft),
            "route": "audit_semantic_graph",
        }

    def audit_semantic_graph(self, state: PipelineState) -> dict:
        payload = self.read(state, "semantic_payload_ref")
        draft = self.read(state, "semantic_draft_ref")
        canonical, findings = validate_semantic_proposal(draft, payload)
        if self.source_first(state):
            if findings:
                canonical, findings = salvage_semantic_proposal(draft, payload)
            limitations = draft.get("findings", []) + [
                "Graph interpretation withheld: " + item for item in findings
            ]
            if not canonical:
                return {
                    "semantic_index": state.get("semantic_index", 0) + 1,
                    "limitations_ref": self.limitations(state, limitations),
                    "route": "propose_semantic_graph",
                }
            return {
                "semantic_canonical_ref": self.store.put(canonical),
                "semantic_audit_ref": self.store.put(
                    {
                        "accepted": None,
                        "status": "source_links_validated_semantics_unreviewed",
                        "findings": draft.get("findings", []) + findings,
                    }
                ),
                "limitations_ref": self.limitations(state, limitations),
                "route": "publish_semantic_graph",
            }
        audit = {"accepted": False, "findings": findings}
        if not findings:
            audit = self.call("audit_semantic_graph", {**payload, "draft": draft}, AuditDraft)
            findings.extend(audit.get("findings", []))
            if not audit["accepted"]:
                findings.append("Independent semantic audit rejected the proposed graph")
            if set(audit.get("covered_obligation_ids", [])) != {
                fact["id"] for fact in payload["facts"]
            }:
                findings.append("Semantic audit must account for every verified fact")
            if audit.get("missing_evidence_ids"):
                findings.append("Semantic audit reported missing evidence")
        if findings:
            if state.get("attempt", 0) < self.repair_limit():
                return {
                    "attempt": state.get("attempt", 0) + 1,
                    "feedback_ref": self.store.put(findings),
                    "semantic_audit_ref": self.store.put(audit),
                    "route": "propose_semantic_graph",
                }
            return self.issue(state, "audit_semantic_graph", findings, "propose_semantic_graph")
        return {
            "semantic_canonical_ref": self.store.put(canonical),
            "semantic_audit_ref": self.store.put(audit),
            "route": "publish_semantic_graph",
        }

    def publish_semantic_graph(self, state: PipelineState) -> dict:
        model_name = getattr(getattr(self.model, "settings", None), "model", "test-double")
        publish_semantic_batch(
            self.graph,
            self.read(state, "semantic_canonical_ref"),
            f"{self.run_id}:{state['semantic_index']}",
            {
                "provider": "gemini" if model_name == "gemini-3.8-flash" else "test-double",
                "model": model_name,
                "sdk_version": version("google-genai"),
                "prompt_version": "semantic_graph.v1",
                "payload_ref": state["semantic_payload_ref"],
                "draft_ref": state["semantic_draft_ref"],
                "raw_draft_ref": state["semantic_raw_draft_ref"],
                "anchoring_ref": state["semantic_anchoring_ref"],
                "audit_ref": state["semantic_audit_ref"],
            },
        )
        return {
            "semantic_index": state["semantic_index"] + 1,
            "attempt": 0,
            "feedback_ref": "",
            "route": "propose_semantic_graph",
        }

    def finalize_graph(self, state: PipelineState) -> dict:
        spans = self.spans(state)
        assertions = self.assertions(state)
        exclusions = self.read(state, "exclusions_ref", [])
        covered = {key for item in assertions for key in item["evidence_ids"]}
        covered.update(item["evidence_id"] for item in exclusions)
        missing = set(spans) - covered
        if missing and self.minimum_coverage() == 1.0 and not self.source_first(state):
            return self.issue(
                state,
                "finalize_graph",
                [f"Unresolved source spans: {sorted(missing)}"],
                "finalize_graph",
            )
        findings = self.graph.verify()
        if findings:
            return self.issue(state, "finalize_graph", findings, "finalize_graph")
        quality = semantic_quality_report(self.graph)
        semantic = semantic_records(self.graph)
        revision = digest(
            [state["snapshot_ref"], state["inventory_ref"], assertions, exclusions, semantic]
        )
        quality["source_coverage"] = coverage_report(
            self.read(state, "source_aspects_ref", []),
            self.read(state, "source_decisions_ref", []),
            {fact["id"] for fact in assertions},
            state["snapshot_ref"],
            revision,
            self.read(state, "snapshot_ref").get("attachments", []),
            minimum_coverage=self.minimum_coverage(),
        )
        if self.source_first(state):
            quality["source_coverage"].update(
                {
                    "coverage_ratio": None,
                    "complete": None,
                    "accepted": None,
                    "status": "not_independently_measured",
                    "reason": "Source-first mode uses original context and a final document audit; "
                    "no separate source-aspect inventory was audited",
                }
            )
            quality["source_coverage"]["qualifiers"]["coverage_ratio"] = None
        elif not quality["source_coverage"]["accepted"]:
            quality["accepted"] = False
            quality["findings"].append("Source aspect or attachment coverage is incomplete")
        if not quality["accepted"] and not self.source_first(state):
            self.store.write(
                f"runs/{self.run_id}/graph-quality.json",
                json.dumps(quality, ensure_ascii=False, indent=2),
            )
            return self.issue(state, "finalize_graph", quality["findings"], "finalize_graph")
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
            "data_hash": digest([assertions, exclusions, semantic]),
            "semantic_schema": 1,
            "graph_quality": quality,
            "model": getattr(getattr(self.model, "settings", None), "model", "test-double"),
            "parser_capabilities": sorted(
                {metadata["capability"] for metadata in inventory_record["analysis"].values()}
                | {inventory_record.get("parser_version", "legacy-document-parser")}
            ),
            "story_count": len(inventory_record.get("stories", [])),
            "assertion_count": len(assertions),
            "evidence_count": len(spans),
            "excluded": exclusions,
            "input_exclusions": self.read(state, "snapshot_ref")["exclusions"],
            "conflict_candidates": self.graph.conflict_candidates(),
            "policy": "source-first-context-v1"
            if self.source_first(state)
            else "lexical-two-hop-v1",
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
        self.store.write(
            f"runs/{self.run_id}/coverage.json",
            json.dumps(
                {
                    "represented": sorted(
                        {key for item in assertions for key in item["evidence_ids"]}
                    ),
                    "excluded_with_reason": exclusions + non_substantive,
                    "unresolved": sorted(missing),
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
        self.store.write(
            f"runs/{self.run_id}/graph-quality.json",
            json.dumps(quality, ensure_ascii=False, indent=2),
        )
        return {
            "graph_revision": revision,
            "graph_quality_ref": self.store.put(quality),
            "status": (
                "awaiting_manual_review" if state.get("mode") == "manual" else "graph_complete"
            )
            if state.get("graph_only")
            else "graph_ready",
            "route": END
            if state.get("graph_only")
            else ("plan_source_document" if self.source_first(state) else "compile_template"),
        }

    def completion_context(
        self,
        state: PipelineState,
        queries: list[str] | None = None,
        mandatory_evidence_ids: list[str] | None = None,
    ) -> dict:
        settings = getattr(self.model, "settings", None)
        capacity = max(
            2000,
            min(
                120000,
                int(getattr(settings, "request_tokens", 100000))
                - int(
                    getattr(
                        settings,
                        "authoring_output_tokens",
                        getattr(settings, "output_tokens", 8192),
                    )
                )
                - 16000,
            ),
        )
        return self.graph.source_context(
            queries=queries or [],
            mandatory_evidence_ids=mandatory_evidence_ids,
            max_characters=capacity,
            graph_assisted=getattr(settings, "graph_assisted_retrieval", False),
        )

    def plan_source_document(self, state: PipelineState) -> dict:
        context = self.completion_context(state, [state.get("brief", "")])
        snapshot = self.read(state, "snapshot_ref")
        overview = []
        overview_incomplete = False
        if context.get("omitted_evidence_ids") or context.get("excerpted_evidence_ids"):
            overview, overview_incomplete = bounded_source_overview(
                list(self.spans(state).values()), self.assertions(state)
            )
        plan = self.call(
            "source_plan",
            {
                "brief": state.get("brief", ""),
                "template": self.store.get_bytes(snapshot["template_hash"]).decode("utf-8"),
                "sources": context,
                "corpus_overview": overview,
                "feedback": self.read(state, "feedback_ref", []),
                "overview_may_be_incomplete": overview_incomplete,
            },
            SourcePlan,
        )
        plan = SourcePlan.model_validate(plan).model_dump()
        binding_findings = plan_findings(plan, list(self.spans(state).values()))
        plan = normalize_plan_hierarchy(plan)
        available = set(self.spans(state))
        context_bindings = []
        for section in plan["sections"]:
            section["evidence_ids"] = [key for key in section["evidence_ids"] if key in available]
            if not section["evidence_ids"]:
                section["evidence_ids"] = [item["id"] for item in context["evidence"]]
                context_bindings.append(section["id"])
        self.store.write(f"runs/{self.run_id}/plan.md", render_source_plan(plan))
        self.store.write(
            f"runs/{self.run_id}/source-plan-review.json",
            json.dumps(
                {
                    "findings": binding_findings,
                    "context_bound_sections": context_bindings,
                    "binding_kind": "source_navigation_not_semantic_coverage",
                },
                indent=2,
            ),
        )
        return {
            "completion_plan_ref": self.store.put(plan),
            "completion_plan_path": str(self.store.root / "runs" / self.run_id / "plan.md"),
            "completion_context_ref": self.store.put(context),
            "completion_packet_index": 0,
            "completion_attempt": 0,
            "editorial_round": 0,
            "editorial_review_ref": "",
            "editorial_candidate_ref": "",
            "editorial_history_ref": self.store.put([]),
            "completion_sections_ref": self.store.put([]),
            "route": "write_source_document",
        }

    def write_source_document(self, state: PipelineState) -> dict:
        plan = self.read(
            state,
            "completion_plan_ref",
            {"title": "Documentation", "sections": ["Source-backed behavior"], "questions": []},
        )
        context = self.read(state, "completion_context_ref") or self.completion_context(state)
        packet_index = state.get("completion_packet_index", 0)
        split = bool(context.get("omitted_evidence_ids") or context.get("excerpted_evidence_ids"))
        selected_plan = plan
        if split:
            section = plan["sections"][packet_index]
            selected_plan = {**plan, "sections": [section]}
            context = self.completion_context(
                state,
                section_queries(section) + [state.get("brief", "")],
                section_evidence_ids(section),
            )
        snapshot = self.read(state, "snapshot_ref")
        draft = self.call(
            "source_document",
            {
                "brief": state.get("brief", ""),
                "plan": selected_plan,
                "feedback": self.read(state, "feedback_ref", []),
                "template": self.store.get_bytes(snapshot["template_hash"]).decode("utf-8"),
                "sources": context,
                "images": [
                    {key: asset.get(key) for key in ("hash", "path", "format")}
                    for asset in self.read(state, "inventory_ref").get("assets", [])
                    if asset.get("disposition") != "rejected"
                ],
                "limitations": self.read(state, "limitations_ref", []),
            },
            GroundedDocument,
        )
        findings = citation_findings(draft, context["evidence"])
        if split:
            sections = self.read(state, "completion_sections_ref", []) + draft["sections"]
            if packet_index + 1 < len(plan["sections"]):
                return {
                    "completion_sections_ref": self.store.put(sections),
                    "completion_draft_ref": "",
                    "completion_packet_index": packet_index + 1,
                    "completion_attempt": 0,
                    "completion_findings_ref": self.store.put([]),
                    "limitations_ref": self.limitations(state, findings + draft["limitations"]),
                    "route": "write_source_document",
                }
            draft["sections"] = sections
        planned = {
            section["id"]: section for section in plan["sections"] if isinstance(section, dict)
        }
        for section in draft["sections"]:
            approved = planned.get(section.get("id")) or next(
                (item for item in planned.values() if item["title"] == section["title"]), None
            )
            if approved:
                section.update({key: approved.get(key, "") for key in ("id", "title", "parent_id")})
        return {
            "completion_draft_ref": self.store.put(assign_document_ids(draft)),
            "completion_sections_ref": self.store.put([]),
            "completion_findings_ref": self.store.put(findings),
            "completion_repair_phase": "citations",
            "route": "repair_source_document",
        }

    def repair_source_document(self, state: PipelineState) -> dict:
        evidence = self.completion_evidence(state)
        draft = assign_document_ids(self.read(state, "completion_draft_ref"))
        phase = state.get("completion_repair_phase", "citations")
        diagnostics = self.read(state, "completion_audit_diagnostics_ref", [])
        if phase == "citations":
            draft, missing_sections = preserve_planned_sections(
                draft, self.read(state, "completion_plan_ref", {}), evidence
            )
            targets = citation_targets(draft, evidence) + missing_sections
        else:
            targets, invalid = audit_targets(
                draft, self.read(state, "completion_audit_ref", {}), evidence
            )
            diagnostics += invalid
        counts = dict(state.get("completion_repair_counts", {}))
        response, failure = {}, None
        if targets and counts.get(phase, 0) == 0:
            counts[phase] = 1
            mandatory_ids = list(
                dict.fromkeys(
                    source["evidence_id"] for target in targets for source in target["sources"]
                )
            )
            queries = [
                section["title"]
                for section in draft["sections"]
                if section["id"] in {target["section_id"] for target in targets}
            ]
            try:
                response = self.call(
                    "source_document_repair",
                    {
                        "title": draft["title"],
                        "targets": targets,
                        "sources": self.completion_context(state, queries, mandatory_ids),
                        "sections": [
                            {"id": section["id"], "title": section["title"]}
                            for section in draft["sections"]
                        ],
                    },
                    DocumentRepairs,
                )
            except (
                TimeoutError,
                ValidationError,
                ValueError,
                RuntimeError,
                httpx.TransportError,
                APIError,
            ) as error:
                failure = f"{type(error).__name__}: {error}"
        repaired, records = apply_repairs(draft, targets, response, evidence)
        for record in records:
            record["phase"] = phase
            if failure:
                record["failure"] = failure
        return {
            "completion_draft_ref": self.store.put(repaired),
            "completion_repair_counts": counts,
            "completion_repair_records_ref": self.store.put(
                self.read(state, "completion_repair_records_ref", []) + records
            ),
            "completion_audit_diagnostics_ref": self.store.put(diagnostics),
            "route": "audit_source_document",
        }

    def completion_evidence(self, state: PipelineState) -> list[dict]:
        evidence = list(self.spans(state).values()) if state.get("inventory_ref") else []
        for span in evidence:
            if span.get("interpretation_ref"):
                interpretation = self.store.get(span["interpretation_ref"])
                description = interpretation.get("description", "")
                if description and description in span["text"]:
                    span["fallback_text"] = description
        return evidence

    def audit_source_document(self, state: PipelineState) -> dict:
        draft = self.read(state, "completion_draft_ref")
        audit_metadata = {
            "document_content_hash": document_content_hash(draft),
        }
        candidate_update = {
            "completion_draft_ref": self.store.put(draft),
        }
        evidence_ids = list(
            dict.fromkeys(
                source["evidence_id"]
                for section in draft["sections"]
                for passage in section["paragraphs"] + section.get("visuals", [])
                for source in passage.get("sources", [])
            )
        )
        context = self.completion_context(state)
        known = {item["id"] for item in context["evidence"]}
        missing = set(evidence_ids) - known
        if missing or context.get("excerpted_evidence_ids") or context.get("omitted_evidence_ids"):
            return {
                **candidate_update,
                "limitations_ref": self.limitations(
                    state,
                    [
                        "Final semantic audit context is incomplete; "
                        "some source passages require separate review"
                    ],
                ),
                "completion_audit_ref": self.store.put(
                    {
                        **audit_metadata,
                        "accepted": False,
                        "findings": [],
                        "coverage_estimate": None,
                        "coverage_explanation": "Draft exceeds the bounded final audit context",
                    }
                ),
                "route": self.editorial_destination(),
            }
        audit = self.call(
            "audit_source_document",
            {"document": draft, "sources": context, "minimum_coverage": self.minimum_coverage()},
            SourceDocumentAudit,
        )
        return {
            **candidate_update,
            "completion_audit_ref": self.store.put({**audit, **audit_metadata}),
            "completion_audit_count": state.get("completion_audit_count", 0) + 1,
            "completion_repair_phase": "semantic",
            "route": "repair_source_document"
            if audit_targets(draft, audit, list(self.spans(state).values()))[0]
            and not state.get("completion_repair_counts", {}).get("semantic")
            else self.editorial_destination(),
        }

    def editorial_destination(self) -> str:
        return (
            "review_source_editorial"
            if getattr(getattr(self.model, "settings", None), "editorial_review", False)
            else "finalize_source_document"
        )

    def editorial_context(self, state: PipelineState, document: dict) -> dict:
        evidence_ids = list(
            dict.fromkeys(
                source["evidence_id"]
                for section in document["sections"]
                for passage in section.get("paragraphs", []) + section.get("visuals", [])
                for source in passage.get("sources", [])
            )
        )
        return self.completion_context(
            state, [section["title"] for section in document["sections"]], evidence_ids
        )

    def review_source_editorial(self, state: PipelineState) -> dict:
        document = self.read(state, "completion_draft_ref")
        context = self.editorial_context(state, document)
        if context.get("omitted_evidence_ids") or context.get("excerpted_evidence_ids"):
            return {
                "limitations_ref": self.limitations(
                    state,
                    [
                        "Whole-document editorial verification exceeded its context budget; "
                        "the source-backed draft was retained without an unverified rewrite"
                    ],
                ),
                "route": "finalize_source_document",
            }
        outstanding, diagnostics = outstanding_audit_findings(
            document, self.read(state, "completion_audit_ref"), self.completion_evidence(state)
        )
        review = self.call(
            "source_editorial",
            {
                "document": document,
                "plan": self.read(state, "completion_plan_ref", {}),
                "sources": context,
                "previous_rounds": self.read(state, "editorial_history_ref", []),
                "outstanding_factual_findings": outstanding,
                "presentation_findings": document_structure_findings(document)
                + visual_findings(
                    document, self.completion_evidence(state), self.editorial_image_paths(state)
                ),
            },
            EditorialReview,
        )
        review = merge_editorial_findings(review, outstanding)
        for section in document["sections"]:
            section_visual_findings = visual_findings(
                {"sections": [section]},
                self.completion_evidence(state),
                self.editorial_image_paths(state),
            )
            if section_visual_findings and not any(
                item["section_id"] == section["id"] and item["category"] == "visual"
                for item in review["findings"]
            ):
                review["findings"].append(
                    {
                        "section_id": section["id"],
                        "paragraph_id": "",
                        "category": "visual",
                        "explanation": "; ".join(section_visual_findings),
                        "requested_change": (
                            "Correct visual representation and exact citations "
                            "while preserving supported meaning."
                        ),
                        "sources": [],
                    }
                )
            for paragraph in section["paragraphs"]:
                issues = document_structure_findings(
                    {"sections": [{**section, "parent_id": "", "paragraphs": [paragraph]}]}
                )
                if issues and not any(
                    item.get("paragraph_id") == paragraph["id"] for item in review["findings"]
                ):
                    review["findings"].append(
                        {
                            "section_id": section["id"],
                            "paragraph_id": paragraph["id"],
                            "category": "clarity",
                            "explanation": "; ".join(issues),
                            "requested_change": (
                                "Use plain business prose under approved headings; "
                                "preserve all supported information."
                            ),
                            "sources": paragraph["sources"],
                        }
                    )
        return {
            "editorial_review_ref": self.store.put(review),
            "completion_audit_diagnostics_ref": self.store.put(
                self.read(state, "completion_audit_diagnostics_ref", []) + diagnostics
            ),
            "route": "revise_source_document" if review["findings"] else "finalize_source_document",
        }

    def editorial_image_paths(self, state: PipelineState) -> dict[str, str]:
        return {
            asset["hash"]: f"assets/{asset['hash']}.{asset['format']}"
            for asset in self.read(state, "inventory_ref", {}).get("assets", [])
            if asset.get("hash") and asset.get("disposition") != "rejected"
        }

    def revise_source_document(self, state: PipelineState) -> dict:
        document = self.read(state, "completion_draft_ref")
        review = self.read(state, "editorial_review_ref")
        number = state.get("editorial_round", 0) + 1
        limit = getattr(getattr(self.model, "settings", None), "editorial_round_limit", 3)
        if number > limit:
            return {"route": "finalize_source_document"}
        response = self.call(
            "source_revision",
            {
                "document": document,
                "plan": self.read(state, "completion_plan_ref", {}),
                "review": review,
                "sources": self.editorial_context(state, document),
            },
            DocumentRevision,
        )
        try:
            candidate = apply_editorial_revision(document, response, review)
            findings = revision_findings(
                document,
                candidate,
                self.completion_evidence(state),
                self.editorial_image_paths(state),
            )
        except ValueError as error:
            candidate, findings = document, [str(error)]
        record = {
            "round": number,
            "baseline_ref": state["completion_draft_ref"],
            "baseline_hash": document_content_hash(document),
            "candidate_ref": self.store.put(candidate),
            "candidate_hash": document_content_hash(candidate),
            "revision_ref": self.store.put(response),
            "review_ref": state["editorial_review_ref"],
            "structural_findings": findings,
            "outcome": "rejected_structure" if findings else "pending_semantic_verification",
        }
        history = self.read(state, "editorial_history_ref", []) + [record]
        unchanged = record["candidate_hash"] == record["baseline_hash"]
        if unchanged and not findings:
            record["outcome"] = "retained_unchanged"
        update = {
            "editorial_round": number,
            "editorial_history_ref": self.store.put(history),
            "editorial_candidate_ref": record["candidate_ref"] if not findings else "",
            "route": "finalize_source_document"
            if findings or unchanged
            else "verify_source_revision",
        }
        if findings:
            update["limitations_ref"] = self.limitations(
                state,
                [
                    "An editorial revision failed structural or exact-source validation; "
                    "the previous version was retained"
                ],
            )
        elif unchanged:
            update["limitations_ref"] = self.limitations(
                state, ["Editorial review requested improvements but the model proposed no changes"]
            )
        return update

    def verify_source_revision(self, state: PipelineState) -> dict:
        baseline = self.read(state, "completion_draft_ref")
        candidate = self.read(state, "editorial_candidate_ref")
        context = self.editorial_context(state, candidate)
        if context.get("omitted_evidence_ids") or context.get("excerpted_evidence_ids"):
            history = self.read(state, "editorial_history_ref", [])
            history[-1] = {**history[-1], "outcome": "rejected_incomplete_source_context"}
            return {
                "editorial_history_ref": self.store.put(history),
                "editorial_candidate_ref": "",
                "limitations_ref": self.limitations(
                    state,
                    [
                        "Editorial candidate could not be verified within its context budget; "
                        "the previous version was retained"
                    ],
                ),
                "route": "finalize_source_document",
            }
        verification = self.call(
            "verify_source_revision",
            {
                "previous_document": baseline,
                "candidate": candidate,
                "requested_changes": self.read(state, "editorial_review_ref"),
                "outstanding_factual_findings": outstanding_audit_findings(
                    baseline,
                    self.read(state, "completion_audit_ref"),
                    self.completion_evidence(state),
                )[0],
                "plan": self.read(state, "completion_plan_ref", {}),
                "sources": context,
                "minimum_coverage": self.minimum_coverage(),
            },
            RevisionVerification,
        )
        unchanged = unchanged_audit_targets(
            baseline,
            candidate,
            outstanding_audit_findings(
                baseline, self.read(state, "completion_audit_ref"), self.completion_evidence(state)
            )[0],
        )
        accepted = revision_accepted(verification) and not unchanged
        history = self.read(state, "editorial_history_ref", [])
        history[-1] = {
            **history[-1],
            "verification_ref": self.store.put(verification),
            "outcome": "accepted"
            if accepted
            else "rejected_unresolved_factual_targets"
            if unchanged
            else "rejected_semantic_regression",
            "unchanged_factual_targets": unchanged,
        }
        update = {
            "editorial_history_ref": self.store.put(history),
            "editorial_candidate_ref": "",
            "route": "finalize_source_document",
        }
        if not accepted:
            update["limitations_ref"] = self.limitations(
                state,
                [
                    "An editorial revision did not pass semantic preservation checks; "
                    "the previous version was retained"
                ],
            )
            return update
        update["completion_draft_ref"] = state["editorial_candidate_ref"]
        update["completion_audit_ref"] = self.store.put(
            {**verification["audit"], "document_content_hash": document_content_hash(candidate)}
        )
        remaining = verification["remaining_editorial_findings"]
        limit = getattr(getattr(self.model, "settings", None), "editorial_round_limit", 3)
        if remaining and state.get("editorial_round", 0) < limit:
            update["editorial_review_ref"] = self.store.put(
                {"findings": remaining, "summary": verification["explanation"]}
            )
            update["route"] = "revise_source_document"
        elif remaining:
            update["limitations_ref"] = self.limitations(
                state, ["The editorial correction limit was reached with remaining review findings"]
            )
        return update

    def finalize_source_document(self, state: PipelineState) -> dict:
        evidence = self.completion_evidence(state)
        draft = self.read(state, "completion_draft_ref")
        audit = self.read(state, "completion_audit_ref")
        limitations = self.read(state, "limitations_ref", [])
        completed_sections = self.read(state, "completion_sections_ref", [])
        if draft and completed_sections:
            draft = {**draft, "sections": completed_sections + draft["sections"]}
        if not draft:
            sections = completed_sections
            draft = {"title": "Documentation", "sections": sections, "limitations": []}
            if not sections:
                draft["sections"] = [
                    {
                        "title": "Preserved source extracts",
                        "paragraphs": [
                            {
                                "text": span["text"],
                                "sources": [{"evidence_id": span["id"], "quote": span["text"]}],
                                "uncertainty": "Original extract; synthesis was not completed",
                            }
                            for span in evidence
                            if span.get("role") != "generated_image_description"
                        ],
                        "image_hashes": [],
                    }
                ]
                limitations.append(
                    "Synthesis was unavailable. This is a source extract bundle, "
                    "not completed documentation."
                )
        draft = assign_document_ids(draft)
        draft, missing_sections = preserve_planned_sections(
            draft, self.read(state, "completion_plan_ref", {}), evidence
        )
        targets = citation_targets(draft, evidence) + missing_sections
        diagnostics = self.read(state, "completion_audit_diagnostics_ref", [])
        if audit and audit.get("document_content_hash") == document_content_hash(draft):
            remaining, invalid = audit_targets(draft, audit, evidence)
            targets += [
                item
                for item in remaining
                if item["target_id"] not in {target["target_id"] for target in targets}
            ]
            diagnostics += invalid
        cleaned, final_repairs = apply_repairs(draft, targets, {}, evidence)
        structure_issues = document_structure_findings(cleaned)
        visual_issues = visual_findings(cleaned, evidence, self.editorial_image_paths(state))
        if structure_issues:
            limitations.append("Document presentation still has structural issues requiring review")
        if visual_issues:
            limitations.append(
                "Some visuals failed validation and are retained in verification evidence "
                "but excluded from the business rendering"
            )
        repair_records = self.read(state, "completion_repair_records_ref", []) + final_repairs
        if any(item["outcome"] != "repaired" for item in repair_records):
            limitations.append("Some passages use original source extracts after bounded repair")
        if diagnostics:
            limitations.append("Some audit findings could not be verified against document targets")
        if not audit:
            limitations.append("Final semantic audit was not completed")
        elif not audit.get("accepted") and not audit.get("findings"):
            limitations.append("Final semantic audit did not accept the document")
        context = self.read(state, "completion_context_ref", {})
        if context.get("omitted_evidence_ids") or context.get("excerpted_evidence_ids"):
            limitations.append(
                f"Initial bounded context omitted {len(context.get('omitted_evidence_ids', []))} "
                f"and excerpted {len(context.get('excerpted_evidence_ids', []))} "
                "source fragments; coverage is not fully measured"
            )
        cleaned["limitations"] = list(dict.fromkeys(cleaned.get("limitations", []) + limitations))
        generated = bool(
            state.get("completion_draft_ref")
            or state.get("completion_sections_ref")
            and self.read(state, "completion_sections_ref")
        )
        paragraph_outcomes = {
            identifier: record["outcome"]
            for record in repair_records
            for identifier in record["replacement_ids"]
        }
        fallback_ids = {
            identifier
            for identifier, outcome in paragraph_outcomes.items()
            if outcome != "repaired"
        }
        if generated and all(
            paragraph["id"] in fallback_ids
            for section in cleaned["sections"]
            for paragraph in section["paragraphs"]
        ):
            generated = False
        usable = any(section["paragraphs"] for section in cleaned["sections"])
        if not usable and evidence:
            cleaned["sections"] = [
                {
                    "title": "Preserved source extracts",
                    "paragraphs": [
                        {
                            "text": span["text"],
                            "sources": [{"evidence_id": span["id"], "quote": span["text"]}],
                            "uncertainty": "Original extract; generated synthesis was withheld",
                        }
                        for span in evidence
                        if span.get("role") != "generated_image_description"
                    ],
                    "image_hashes": [],
                }
            ]
            cleaned["limitations"].append(
                "Generated synthesis was withheld. This is a source extract bundle, "
                "not completed documentation."
            )
        accepted = bool(
            audit
            and audit.get("accepted")
            and not final_repairs
            and not context.get("omitted_evidence_ids")
            and not context.get("excerpted_evidence_ids")
            and not cleaned["limitations"]
            and audit.get("coverage_estimate", 0) >= self.minimum_coverage()
            and audit.get("document_content_hash") == document_content_hash(cleaned)
        )
        status = (
            "complete"
            if accepted and generated and usable
            else "complete_with_limitations"
            if generated and usable
            else "degraded_source_bundle"
        )
        if any(
            paragraph_outcomes.get(paragraph["id"]) == "unresolved_no_authored_source"
            for section in cleaned["sections"]
            for paragraph in section["paragraphs"]
        ):
            status = "degraded_source_bundle"
        directory = f"runs/{self.run_id}/output"
        for span in evidence:
            provenance = (
                "AI-generated image interpretation"
                if span.get("role") == "generated_image_description"
                else "Original source fragment"
            )
            origin = (
                f"Source image: [{span['source_image_path']}]"
                f"(../originals/{span['source_image_path']}). "
                f"Provider: {span.get('provider', 'unknown')}; "
                f"model: {span.get('model', 'unknown')}. "
                f"Image SHA-256: `{span.get('source_image_hash', '')}`.\n\n"
                if span.get("source_image_path")
                else f"[Original document](../originals/{span['path']})\n\n"
            )
            self.store.write(
                f"{directory}/evidence/{span['id']}.md",
                f"# {span['path']}\n\n{provenance}. "
                f"Lines {span['start_line']}-{span['end_line']}.\n\n"
                f"{origin}SHA-256: `{span['file_hash']}`\n\n{span['text']}\n",
            )
        image_paths = {}
        inventory_record = self.read(state, "inventory_ref", {})
        snapshot = self.read(state, "snapshot_ref", {})
        for original in snapshot.get("files", []):
            self.store.write(
                f"{directory}/originals/{original['path']}",
                self.store.get_bytes(original["hash"]),
            )
        for derivative in inventory_record.get("enriched_documents", []):
            self.store.write(
                f"{directory}/prepared/{derivative['path']}",
                self.store.get_bytes(derivative["prepared_hash"]),
            )
        for asset in inventory_record.get("assets", []):
            if asset.get("hash") and asset.get("disposition") != "rejected":
                for folder in ("originals", "prepared"):
                    self.store.write(
                        f"{directory}/{folder}/{asset['path']}",
                        self.store.get_bytes(asset["hash"]),
                    )
        selected_hashes = {
            value for section in cleaned["sections"] for value in section.get("image_hashes", [])
        }
        selected_hashes.update(
            visual["image_hash"]
            for section in cleaned["sections"]
            for visual in section.get("visuals", [])
            if visual.get("kind") == "image" and visual.get("image_hash")
        )
        known_hashes = {asset.get("hash") for asset in inventory_record.get("assets", [])}
        if selected_hashes - known_hashes:
            cleaned["limitations"].append("Unrecognized image references were omitted")
            if status == "complete":
                status = "complete_with_limitations"
        for asset in inventory_record.get("assets", []):
            if asset.get("hash") in selected_hashes and asset.get("disposition") != "rejected":
                filename = f"assets/{asset['hash']}.{asset['format']}"
                self.store.write(f"{directory}/{filename}", self.store.get_bytes(asset["hash"]))
                image_paths[asset["hash"]] = filename
        markdown = render_grounded_document(cleaned, evidence, image_paths)
        excerpts = citation_excerpt_files(cleaned, evidence)
        output = self.store.write(f"{directory}/documentation.md", markdown)
        self.store.write(
            f"{directory}/documentation.html", render_document_preview(markdown, excerpts)
        )
        for path, content in excerpts.items():
            self.store.write(f"{directory}/{path}", content)
        self.store.write(
            f"{directory}/verification.json",
            json.dumps(
                document_verification(cleaned, evidence, image_paths), ensure_ascii=False, indent=2
            ),
        )
        report = {
            "status": status,
            "semantic_audit": audit,
            "semantic_audit_matches_exported_content": bool(
                audit and audit.get("document_content_hash") == document_content_hash(cleaned)
            ),
            "exported_content_hash": document_content_hash(cleaned),
            "exported_coverage_estimate": (
                audit.get("coverage_estimate")
                if audit and audit.get("document_content_hash") == document_content_hash(cleaned)
                else None
            ),
            "exact_citations_valid": not citation_findings(cleaned, evidence),
            "structure_findings": structure_issues,
            "visual_findings": visual_issues,
            "limitations": cleaned["limitations"],
            "source_revision": state.get("snapshot_ref"),
            "graph_revision": state.get("graph_revision"),
            "coverage_kind": "model_estimate_not_measured_information_recall",
            "coordinator_interventions": "Measure externally; not observable inside pipeline",
            "automatic_recovery_counts": state.get("recovery_counts", {}),
            "citation_repair_attempts_current_packet": state.get("completion_attempt", 0),
            "withheld_paragraphs": [],
            "targeted_repair_counts": state.get("completion_repair_counts", {}),
            "paragraph_repairs": repair_records,
            "audit_target_diagnostics": diagnostics,
            "editorial_rounds": state.get("editorial_round", 0),
            "editorial_revisions": self.read(state, "editorial_history_ref", []),
            "editorial_review": self.read(state, "editorial_review_ref", None),
        }
        self.store.write(
            f"{directory}/report.json", json.dumps(report, ensure_ascii=False, indent=2)
        )
        return {
            "completion_path": str(output),
            "completion_status": status,
            "status": status,
            "route": END,
            "candidate_ref": self.store.put(cleaned),
            "source_coverage_ref": self.store.put(report),
        }

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
                "template_text": contract["text"],
                "template_headings": contract["headings"],
                "template_requirements": contract["requirements"],
                "source_assets": self.read(state, "inventory_ref").get("assets", []),
                "visual_source_excerpts": [
                    span
                    for span in self.spans(state).values()
                    if span["id"]
                    in {
                        key
                        for group in groups
                        for fact in group["facts"]
                        for key in fact["evidence_ids"]
                    }
                ]
                if sum(len(span["text"]) for span in self.spans(state).values()) <= 45000
                else [],
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
                fold_plan_sections(contract["heading_tree"], draft["sections"]),
                [item["text"] for item in contract["requirements"] if item["id"] in omitted],
            )
        except ValueError as error:
            if state.get("attempt", 0) < self.repair_limit():
                return {
                    "attempt": state.get("attempt", 0) + 1,
                    "plan_feedback": str(error),
                    "route": "draft_page_plan",
                }
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
                    "subsections": [
                        {
                            "title": child["title"],
                            "purpose": child["purpose"],
                            "obligation_ids": [
                                identifier
                                for key in child.get("group_ids", [])
                                if key in group_map
                                for identifier in group_map[key]["obligation_ids"]
                            ],
                        }
                        for child in raw.get("subsections", [])
                    ],
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
                if visual.get("section") != section["title"]:
                    visual.setdefault("subsection", visual["section"])
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
            "visual_attempt": 0,
            "visual_feedback_ref": "",
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
            else "locate_visual_evidence",
        }

    def locate_visual_evidence(self, state: PipelineState) -> dict:
        plan = self.read(state, "plan_ref")
        visuals = [visual for section in plan["sections"] for visual in section["visuals"]]
        required = visual_support_requirements(visuals)
        if not required:
            return {"route": "validate_page_plan"}
        spans = self.spans(state)
        identifiers = {item["evidence_id"] for item in required}
        if sum(len(spans[key]["text"]) for key in identifiers if key in spans) > 45000:
            return self.issue(
                state,
                "locate_visual_evidence",
                ["Visual evidence exceeds the bounded packet; split the planned visuals"],
                "draft_page_plan",
            )
        draft = self.call(
            "locate_visual_evidence",
            {
                "visuals": visuals,
                "required_support": required,
                "original_evidence": [spans[key] for key in sorted(identifiers) if key in spans],
                "feedback": self.read(state, "visual_feedback_ref", []),
            },
            VisualEvidenceDraft,
        )
        actual = {item["support_id"]: item for item in draft["locations"]}
        findings = []
        if len(actual) != len(draft["locations"]) or set(actual) != {
            item["support_id"] for item in required
        }:
            findings.append("Every visual element needs exactly one original support quote")
        locations = []
        for item in required:
            key = item["evidence_id"]
            if item["support_id"] not in actual or key not in spans:
                continue
            quote = actual[item["support_id"]]["quote"]
            expanded_quote = unique_visual_quote(spans[key]["text"], quote)
            if expanded_quote != quote:
                self.store.event(
                    self.run_id,
                    "locate_visual_evidence",
                    "local_repair",
                    support_id=item["support_id"],
                    before=quote,
                    after=expanded_quote,
                )
                quote = expanded_quote
            try:
                support = exact_support({**spans[key], "label": key}, quote)
                locations.append({**item, "quote": quote, "support_range": support})
            except ValueError as error:
                findings.append(str(error))
        if findings:
            if state.get("visual_attempt", 0) < self.repair_limit():
                return {
                    "visual_attempt": state.get("visual_attempt", 0) + 1,
                    "visual_feedback_ref": self.store.put(findings),
                    "route": "locate_visual_evidence",
                }
            return self.issue(state, "locate_visual_evidence", findings, "draft_page_plan")
        for visual in visuals:
            visual["support_quotes"] = {}
            visual["support_locations"] = [
                item for item in locations if item["visual_id"] == visual["id"]
            ]
        return {"plan_ref": self.store.put(plan), "route": "validate_page_plan"}

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
                    "template_text": contract["text"],
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
                    "required_diagram_element_ids": sorted(
                        diagram_element_ids(
                            [
                                visual
                                for section in plan["sections"]
                                for visual in section["visuals"]
                            ]
                        )
                    ),
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
                            "subsections": section.get("subsections", []),
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
                    "template_text": contract["text"],
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
        scope_id = "full"
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
                    provenance=self.read(state, "tool_provenance_ref", [])
                    + self.read(state, "document_provenance_ref", []),
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
        if self.fast_mode():
            return {
                "route": state.get("authoring_return", "write_section"),
                "authoring_ref": "",
                "authoring_context_ref": "",
            }
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
            "tool_provenance_ref": self.store.put(
                [item.model_dump(mode="json") for item in published.packet.provenance]
            ),
            "document_provenance_ref": "",
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
                    "template_text": self.read(state, "template_ref")["text"],
                    "section": {"title": section["title"], "purpose": section["purpose"]},
                    "planned_subsections": section.get("subsections", []),
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
                    "mandatory_obligation_ids": writing_ids,
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
        draft = SectionDraft.model_validate(draft).model_dump()
        draft["markdown"] = strip_authored_visuals(draft["markdown"])
        if draft["subprocesses"]:
            table, mappings, records = render_subprocess_catalog(draft["subprocesses"])
            draft["markdown"] = replace_subsection(draft["markdown"], "4.2 Key Subprocesses", table)
            draft["mappings"] = merge_mapping_occurrences(draft["mappings"], mappings)
            draft["subprocess_records"] = records
        draft = _normalized_section_draft(draft, packet)
        for mapping in draft["mappings"]:
            if (
                mapping["obligation_id"] not in canonical
                and mapping.get("disposition") != "out_of_scope"
            ):
                mapping["disposition"] = "overview"
        visuals = render_visuals(
            packet.get("visuals", []), plan["source_assets"], packet["evidence"]
        )
        if visuals:
            draft["markdown"] += "\n\n" + visuals
            draft["markdown"] = position_visuals(
                draft["markdown"],
                packet.get("visuals", []),
                plan["source_assets"],
                packet["evidence"],
            )
        draft, repairs = repair_document_draft(
            draft,
            evidence=packet["evidence"],
            assertions=packet["assertions"],
            fixed_headings=[
                item["text"]
                for item in plan["template_requirements"]
                if item["section"] == section["title"] and item["kind"] == "heading"
            ],
            visuals=packet.get("visuals", []),
            assets=plan["source_assets"],
            subprocess_records=draft.get("subprocess_records", []),
        )
        if repairs:
            draft["automatic_repairs"] = repairs
            self.store.event(self.run_id, "write_section", "local_repair", repairs=repairs)
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
        if (
            "Python-owned catalog" in self.read(state, "template_ref")["text"]
            and any(
                child["title"] == "4.2 Key Subprocesses" for child in section.get("subsections", [])
            )
            and state["unit_index"] == 0
            and not draft.get("subprocess_records")
        ):
            findings.append(
                "Section 4.2 requires structured source-backed subprocesses for Python rendering"
            )
        placements, placement_findings = placement_records(
            section["title"],
            draft["markdown"],
            draft["mappings"],
            assertions,
            {item["id"]: item for item in packet["evidence"]},
        )
        findings.extend(placement_findings)
        findings.extend(support_findings(draft["mappings"], evidence))
        findings.extend(
            unmapped_citation_findings(
                draft["markdown"],
                draft["mappings"],
                [
                    render_visuals([visual], plan["source_assets"], packet["evidence"])
                    for visual in packet.get("visuals", [])
                ],
            )
        )
        findings.extend(
            business_prose_findings(draft["markdown"], self.read(state, "template_ref")["text"])
        )
        findings.extend(
            uncited_business_passages(draft["markdown"], self.read(state, "template_ref")["text"])
        )
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
            if identifier not in writing_ids or not labels:
                findings.append("Invalid obligation mapping")
                continue
            supported = {
                self.graph.evidence(key)["label"] for key in assertions[identifier]["evidence_ids"]
            }
            if not set(labels).issubset(supported):
                findings.append(f"Mapping {identifier} may cite only {sorted(supported)}")
            if mapping.get("passage") not in draft["markdown"]:
                findings.append(f"Mapped passage is absent from prose for {identifier}")
            mapped.add(identifier)
        if set(writing_ids) != mapped:
            prior_written = self.read(state, "written_ref", [])
            prior_expected = {
                key
                for item in prior_written
                for key in self._units(plan["sections"][item["section_index"]])[item["unit_index"]]
            }
            prior_mapped = {
                mapping["obligation_id"] for item in prior_written for mapping in item["mappings"]
            }
            missing = (set(writing_ids) - mapped) | (prior_expected - prior_mapped)
            expected = {fact["id"] for fact in self.assertions(state)}
            if (
                self.minimum_coverage() == 1.0
                or not evaluate_coverage(
                    expected | missing, expected - missing, self.minimum_coverage()
                )["accepted"]
            ):
                findings.append("Section misses approved obligations")
        cited = set(citation_labels(draft["markdown"]))
        if any(label not in evidence for label in cited):
            findings.append("Section contains an unknown citation")
        for mapping in draft["mappings"]:
            if mapping.get("disposition") != "out_of_scope" and any(
                label not in cited for label in mapping.get("citation_ids", [])
            ):
                findings.append("Mapped citation is absent from prose")
        if not findings and writing_ids:
            audit = self.call(
                "verify_section",
                {
                    "template_text": self.read(state, "template_ref")["text"],
                    "section": section["title"],
                    "markdown": draft["markdown"],
                    "mappings": draft["mappings"],
                    "placements": placements,
                    "visuals": packet.get("visuals", []),
                    "mandatory_obligation_ids": sorted(mapped),
                    "required_diagram_element_ids": sorted(
                        diagram_element_ids(packet.get("visuals", []))
                    ),
                    "supporting_obligation_ids": [
                        identifier for identifier in writing_ids if identifier not in canonical
                    ],
                    "assertions": [assertions[key] for key in sorted(mapped)],
                    "original_evidence": packet["evidence"],
                },
                AuditDraft,
            )
            if (
                audit.get("findings")
                or not audit.get("accepted")
                or not mapped.issubset(audit.get("covered_obligation_ids", []))
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
                "subprocess_records": draft.get("subprocess_records", []),
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
            visual_ids = visual_evidence_ids(section.get("visuals", []))
            markdown = position_visuals(
                markdown,
                section.get("visuals", []),
                plan["source_assets"],
                [self.graph.evidence(key) for key in sorted(visual_ids)],
            )
            mappings = [mapping for item in parts for mapping in item["mappings"]]
            assertions = {
                item["obligation_id"]: self.graph.assertion(item["obligation_id"])
                for item in mappings
            }
            evidence = {
                key: self.graph.evidence(key)
                for assertion in assertions.values()
                for key in assertion["evidence_ids"]
            }
            placements, findings = placement_records(
                section["title"], markdown, mappings, assertions, evidence
            )
            if findings:
                return self.issue(state, "assemble_pages", findings, "assemble_pages")
            sections.append(
                {
                    "title": section["title"],
                    "section_id": section.get("section_id", section["title"]),
                    "markdown": markdown,
                    "mappings": mappings,
                    "placements": placements,
                    "supporting_obligation_ids": section["supporting_obligation_ids"],
                    "visuals": section.get("visuals", []),
                    "context_evidence_ids": sorted(
                        {key for item in parts for key in item.get("context_evidence_ids", [])}
                    ),
                    "subprocess_records": [
                        record for item in parts for record in item.get("subprocess_records", [])
                    ],
                }
            )
        return {
            "assembled_ref": self.store.put(sections),
            "edited_ref": self.store.put(sections if self.fast_mode() else []),
            "edit_index": 0,
            "edit_queue_ref": self.store.put(list(range(len(sections)))),
            "route": "audit_documentation" if self.fast_mode() else "edit_page",
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
                    "template_text": self.read(state, "template_ref")["text"],
                    "title": section["title"],
                    "markdown": section["markdown"],
                    "mappings": section["mappings"],
                    "original_evidence": [
                        self.graph.evidence(key)
                        for key in sorted(
                            {
                                key
                                for mapping in section["mappings"]
                                for key in self.graph.assertion(mapping["obligation_id"])[
                                    "evidence_ids"
                                ]
                            }
                        )
                    ],
                    "subprocess_records": section.get("subprocess_records", []),
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
                    "previous": self.read(state, "draft_ref") if state.get("attempt") else None,
                    "repair_attempt": state.get("attempt", 0),
                },
                EditDraft,
            )
        draft = EditDraft.model_validate(draft).model_dump()
        draft["markdown"] = compact_citations(normalize_citation_syntax(draft["markdown"]))
        for mapping in draft["mappings"]:
            for occurrence in [mapping] + mapping.get("additional_passages", []):
                occurrence["passage"] = compact_citations(
                    normalize_citation_syntax(occurrence["passage"])
                )
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
            "required_diagram_element_ids": sorted(diagram_element_ids(section.get("visuals", []))),
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
        overview_ids = {
            item["obligation_id"]
            for item in section["mappings"]
            if item.get("disposition") == "overview"
        }
        for item in mappings:
            if item["obligation_id"] in overview_ids:
                item["disposition"] = "overview"
        old_citations = set(citation_labels(section["markdown"]))
        new_citations = set(citation_labels(markdown))
        findings = []
        if len(replacements) != len(draft.get("mappings", [])):
            findings.append("Editorial revision returned duplicate obligation mappings")
        if section.get("subprocess_records"):
            table, _, _ = render_subprocess_catalog(section["subprocess_records"])
            if table not in markdown:
                findings.append("Preserve the Python-rendered subprocess catalog verbatim")
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
        findings.extend(support_findings(mappings, {item["label"]: item for item in evidence}))
        findings.extend(
            unmapped_citation_findings(
                markdown,
                mappings,
                [
                    render_visuals([visual], plan["source_assets"], evidence)
                    for visual in section.get("visuals", [])
                ],
            )
        )
        findings.extend(business_prose_findings(markdown, self.read(state, "template_ref")["text"]))
        findings.extend(
            uncited_business_passages(markdown, self.read(state, "template_ref")["text"])
        )
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
                        "template_text": contract["text"],
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
            "subprocess_records": section.get("subprocess_records", []),
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
            mapping["obligation_id"]
            for section in sections
            for mapping in section["mappings"]
            if mapping.get("disposition") != "overview"
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
        if repetition["semantic_candidates"] and not self.fast_mode():
            semantic_audit = self.call(
                "audit_repetition",
                {
                    "candidates": repetition["semantic_candidates"],
                    "facts": self.assertions(state),
                    "template_text": self.read(state, "template_ref")["text"],
                },
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
        coverage = evaluate_coverage(expected, actual, self.minimum_coverage())
        if not coverage["accepted"] or len(actual) != len(set(actual)):
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
            assertions = {
                key: self.graph.assertion(key)
                for key in approved["obligation_ids"] + approved["supporting_obligation_ids"]
            }
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
            and not self.fast_mode()
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
        if repetition["duplicate_paragraphs"] and not self.fast_mode():
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
            "coverage": coverage,
            "repetition_is_advisory": self.fast_mode(),
            "template_decisions": plan["template_decisions"],
            "visual_count": sum(len(section.get("visuals", [])) for section in sections),
        }
        self.store.write(f"runs/{self.run_id}/audit.json", json.dumps(audit, indent=2))
        return {
            "source_audit_index": 0,
            "final_source_decisions_ref": self.store.put([]),
            "route": "audit_source_to_document",
        }

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
            passages = []
            for section in sections:
                selected = {
                    item["passage"]
                    for item in section["mappings"]
                    if item["obligation_id"] in fact_ids
                }
                passages.append(
                    {
                        "section_id": section.get("section_id", section["title"]),
                        "mappings": [
                            item for item in section["mappings"] if item["passage"] in selected
                        ],
                    }
                )
            supporting_ids = {
                item["obligation_id"] for section in passages for item in section["mappings"]
            } - fact_ids
            citation_ids = {
                citation
                for section in passages
                for item in section["mappings"]
                for citation in item["citation_ids"]
            }
            supporting_blocks = {
                block["id"]: block
                for citation in sorted(citation_ids)
                if (block := self.graph.evidence(citation))["id"] not in ids
            }
            audit = self.call(
                "audit_source_to_document",
                {
                    "template_text": self.read(state, "template_ref")["text"],
                    "blocks": [self.spans(state)[key] for key in ids],
                    "aspects": packet_aspects,
                    "minimum_coverage": self.minimum_coverage(),
                    "facts": facts,
                    "final_passages": passages,
                    "document_context": [
                        {"title": section["title"], "markdown": section["markdown"]}
                        for section in sections
                    ],
                    "supporting_facts": [
                        item for item in self.assertions(state) if item["id"] in supporting_ids
                    ],
                    "supporting_blocks": list(supporting_blocks.values()),
                    "non_substantive_candidates": [
                        item
                        for item in self.read(state, "source_non_substantive_ref", [])
                        if item["evidence_id"] in ids
                    ],
                },
                SourceAudit,
            )
            findings = audit["findings"] + source_audit_findings(
                packet_aspects,
                audit["decisions"],
                facts,
                all_aspects=aspects,
                prior_decisions=self.read(state, "final_source_decisions_ref", []),
                minimum_coverage=self.minimum_coverage(),
            )
            if findings:
                return self.issue(state, "audit_source_to_document", findings, "assemble_pages")
            return {
                "source_audit_index": index + 1,
                "route": "audit_source_to_document",
                "final_source_decisions_ref": self.store.put(
                    self.read(state, "final_source_decisions_ref", []) + audit["decisions"]
                ),
            }
        report = coverage_report(
            aspects,
            self.read(state, "final_source_decisions_ref", []),
            mapped,
            state["snapshot_ref"],
            state["graph_revision"],
            inventory_record.get("attachments", []),
            minimum_coverage=self.minimum_coverage(),
        )
        report["blocks"] = {
            "total": sum(len(batch) for batch in batches),
            "independently_audited": sum(len(batch) for batch in batches),
        }
        excluded = [
            item
            for section in sections
            for item in section["mappings"]
            if item.get("disposition") == "out_of_scope"
        ]
        report["facts_in_text"] = {
            "total": len(self.assertions(state)),
            "mapped": len(mapped) - len(excluded),
        }
        report["scope_exclusions"] = excluded
        report["non_substantive_candidates"] = self.read(state, "source_non_substantive_ref", [])
        report["exclusions"] = self.read(state, "exclusions_ref", [])
        report["conflict_candidates"] = len(self.graph.conflict_candidates())
        report["unsupported_assertions"] = 0
        self.store.write(f"runs/{self.run_id}/source-coverage.json", json.dumps(report, indent=2))
        if not report["accepted"]:
            return self.issue(
                state,
                "audit_source_to_document",
                ["Source aspect or attachment coverage is incomplete"],
                "assemble_pages",
            )
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
        excerpt_targets = {}
        diagram_targets = {}

        def render(
            markdown: str,
            mappings: list[dict] | None = None,
            section: str = "",
            audit: bool = False,
        ) -> str:
            scoped = []
            for mapping in mapping_occurrences(mappings or []):
                passage = mapping["passage"]
                location = markdown.find(passage)
                if passage and location >= 0:
                    scoped.append((location, location + len(passage), mapping))
            visual_ranges = []
            rendered_diagrams = set()
            for planned in plan["sections"]:
                for visual in planned.get("visuals", []):
                    block = render_visuals([visual], plan["source_assets"], evidence)
                    location = markdown.find(block)
                    if location >= 0:
                        visual_ranges.append((location, location + len(block), visual))

            def replace(match: re.Match) -> str:
                if markdown[match.end() :].startswith("("):
                    return match.group()
                labels = re.findall(r"[CD]\d+", match.group())
                links = []
                diagram = next(
                    (
                        visual
                        for start, end, visual in visual_ranges
                        if start <= match.start() < end and visual["kind"] != "image"
                    ),
                    None,
                )
                for label in labels:
                    related = [
                        item
                        for start, end, item in scoped
                        if start <= match.start() < end and label in item.get("citation_ids", [])
                    ]
                    quotes = list(
                        dict.fromkeys(
                            item.get("support_quotes", {}).get(label, "") for item in related
                        )
                    )
                    if not quotes:
                        quotes = list(
                            dict.fromkeys(
                                visual.get("support_quotes", {}).get(by_label[label]["id"], "")
                                for start, end, visual in visual_ranges
                                if start <= match.start() < end
                                if by_label[label]["id"] in visual_evidence_ids([visual])
                            )
                        )
                        quotes = [quote for quote in quotes if quote]
                    if not quotes:
                        quotes = list(
                            dict.fromkeys(
                                location["quote"]
                                for start, end, visual in visual_ranges
                                if start <= match.start() < end
                                for location in visual.get("support_locations", [])
                                if location["evidence_id"] == by_label[label]["id"]
                            )
                        )
                    if not quotes:
                        raise ValueError(f"Citation lacks precise local passage support: {label}")
                    for quote in quotes:
                        support = exact_support(by_label[label], quote)
                        target_id = support["target_id"]
                        excerpt_targets[target_id] = {"label": label, **support}
                        selection = select(label, quote, related[0]["passage"] if related else None)
                        selection["support_range"] = support
                        href = f"../evidence/{label}-{target_id}.md"
                        number = list(excerpt_targets).index(target_id) + 1
                        links.append(f"[{number}](<{href}>)")
                        if audit:
                            citation_occurrences.append(
                                {
                                    "id": digest([section, match.start(), target_id])[:20],
                                    "section": section,
                                    "label": label,
                                    "reference_number": number,
                                    "support_quote": quote,
                                    "obligation_ids": [item["obligation_id"] for item in related],
                                    **selection,
                                    "local_target": href,
                                }
                            )
                if diagram:
                    key = digest(diagram)[:20]
                    diagram_targets[key] = diagram
                    if key in rendered_diagrams:
                        return ""
                    rendered_diagrams.add(key)
                    return f"[Diagram sources](../evidence/visual-{key}.md)"
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
        grouped_sections = [group_repeated_list_citations(text) for text in rendered_sections]
        rendered_sections = [text for text, _ in grouped_sections]
        citation_group_edits = {
            section["title"]: replacements
            for section, (_, replacements) in zip(sections, grouped_sections, strict=True)
        }

        def reader_passage(passage: str, section: dict) -> str:
            rendered = render(passage, section["mappings"])
            for original, replacement in citation_group_edits[section["title"]]:
                rendered = rendered.replace(original, replacement)
            return rendered

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
                passage = reader_passage(placement["passage"], section)
                offset = rendered.find(passage)
                if offset < 0 or rendered.count(passage) != 1:
                    raise ValueError("Export changed or duplicated a factual placement")
                start = section_start + offset
                final_placements.append(
                    {**placement, "passage": passage, "start": start, "end": start + len(passage)}
                )
            final_mappings.extend(
                {
                    **mapping,
                    "passage": reader_passage(mapping["passage"], section),
                    "additional_passages": [
                        {**extra, "passage": reader_passage(extra["passage"], section)}
                        for extra in mapping.get("additional_passages", [])
                    ],
                }
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
        for target_id, target in excerpt_targets.items():
            label = target["label"]
            excerpt = "\n".join("    " + line for line in target["exact_quote"].splitlines())
            original = select(label, target["exact_quote"]).get("url")
            content = (
                f"# Evidence {list(excerpt_targets).index(target_id) + 1}\n\n"
                f"Source: `{target['source_path']}` lines "
                f"{target['start_line']}-{target['end_line']}\n\n"
                f"Frozen revision: `{target['snapshot_hash']}`\n\n"
                f"{excerpt}\n\n[Full frozen context]({label}.md)\n"
            )
            if original:
                content += f"\n[Original source excerpt](<{original}>)\n"
            self.store.write(f"{base}/evidence/{label}-{target_id}.md", content)
        for key, visual in diagram_targets.items():
            requirements = {
                item["support_id"]: item for item in visual_support_requirements([visual])
            }
            content = ["# Diagram sources", "", visual["diagram"]["description"], ""]
            for location in visual.get("support_locations", []):
                item = self.graph.evidence(location["evidence_id"])
                support = exact_support(item, location["quote"])
                requirement = requirements.get(location.get("support_id"), {})
                content.extend(
                    [
                        f"## {requirement.get('label', location['element_id'])}",
                        "",
                        f"Source: `{item['path']}` lines "
                        f"{support['start_line']}-{support['end_line']}",
                        "",
                        "\n".join("    " + line for line in location["quote"].splitlines()),
                        "",
                        f"[Frozen excerpt]({item['label']}-{support['target_id']}.md)",
                        "",
                    ]
                )
            self.store.write(f"{base}/evidence/visual-{key}.md", "\n".join(content))
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
                    "subprocess_catalog": [
                        record
                        for section in sections
                        for record in section.get("subprocess_records", [])
                    ],
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
        if not self.read(state, "source_coverage_ref", {}).get("complete", True):
            completion = "complete_with_omissions"
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
        control_nodes = {"review_stage", "resolve_issues_automatically"}
        review_nodes = {"review_plan", "review_release", "review_issues"}
        for name in STEPS:
            function = getattr(self, name) if name in control_nodes else self.logged_node(name)
            builder.add_node(name, function)
        builder.add_edge(START, "snapshot_inputs")
        for name in STEPS:
            if name in control_nodes | review_nodes:
                builder.add_conditional_edges(
                    name, lambda state: state["route"], list(STEPS) + [END]
                )
            else:
                builder.add_edge(name, "review_stage")
        return builder.compile(checkpointer=checkpointer)

    def logged_node(self, name: str):
        function = getattr(self, name)

        def execute(state: PipelineState) -> dict:
            if name not in {"snapshot_inputs", "review_plan", "review_release", "review_issues"}:
                if state.get("runtime_signature") != self.runtime_signature():
                    raise ValueError("Runtime changed; start a new run revision")
            started = monotonic()
            event_path = self.store.root / "runs" / self.run_id / "events.jsonl"
            event_offset = event_path.stat().st_size if event_path.exists() else 0
            try:
                deadline = state.get("deadline", 0)
                now = datetime.now(UTC).timestamp()
                completion_nodes = {
                    "plan_source_document",
                    "write_source_document",
                    "repair_source_document",
                    "audit_source_document",
                    "finalize_source_document",
                    "review_source_editorial",
                    "revise_source_document",
                    "verify_source_revision",
                }
                reserve = getattr(
                    getattr(self.model, "settings", None), "finalization_reserve_seconds", 180
                )
                if (
                    self.source_first(state)
                    and state.get("inventory_ref")
                    and deadline
                    and name not in completion_nodes
                    and now >= deadline - reserve
                ):
                    update = {
                        "limitations_ref": self.limitations(
                            state,
                            [
                                f"Preparation stopped at {name} "
                                "to reserve time for document completion"
                            ],
                        ),
                        "route": "write_source_document",
                    }
                elif self.source_first(state) and name == "finalize_source_document":
                    update = function(state)
                elif deadline and now >= deadline:
                    raise TimeoutError("Pipeline runtime limit reached")
                else:
                    if hasattr(self.model, "set_deadline"):
                        retained = (
                            20
                            if name == "audit_source_document"
                            else 60
                            if name in completion_nodes
                            else reserve
                        )
                        model_deadline = (
                            max(now, deadline - retained)
                            if deadline and self.source_first(state)
                            else deadline
                        )
                        self.model.set_deadline(model_deadline or None)
                    update = function(state)
            except TimeoutError as error:
                if self.source_first(state) and state.get("inventory_ref"):
                    update = {
                        "limitations_ref": self.limitations(
                            state, [f"Time budget reached during {name}: {error}"]
                        ),
                        "route": "finalize_source_document"
                        if name
                        in {
                            "write_source_document",
                            "repair_source_document",
                            "audit_source_document",
                            "finalize_source_document",
                            "review_source_editorial",
                            "revise_source_document",
                            "verify_source_revision",
                        }
                        else "write_source_document",
                    }
                else:
                    update = {"status": "timed_out", "route": END}
                self.store.write(
                    f"runs/{self.run_id}/runtime-limit.json",
                    json.dumps(
                        {
                            "stage": name,
                            "deadline": state.get("deadline"),
                            "reason": str(error),
                            "completed": False,
                        },
                        indent=2,
                    ),
                )
            except ValidationError as error:
                update = self.issue(
                    state, name, [f"Model response failed structural validation: {error}"], name
                )
            except (ValueError, RuntimeError, httpx.TransportError, APIError) as error:
                if not self.source_first(state) or name == "finalize_source_document":
                    raise
                update = self.issue(
                    state, name, [f"Recoverable {type(error).__name__}: {error}"], name
                )
            cost_pln = 0.0
            if event_path.exists():
                with event_path.open("rb") as events:
                    events.seek(event_offset)
                    for line in events:
                        event = json.loads(line)
                        if event.get("event") in {"response", "invalid_schema"}:
                            cost_pln += float(event.get("cost_pln", 0.0))
            if name not in {"review_plan", "review_release", "review_issues"}:
                if name == "snapshot_inputs" and update.get("runtime_signature"):
                    self.stages.initialize(
                        state.get("mode", "manual"),
                        state.get("policy_version", "v2"),
                        update["runtime_signature"],
                        self.repair_limit(),
                    )
                default_routes = {
                    "snapshot_inputs": "inventory_sources",
                    "extract_document_batch": "verify_document_batch",
                    "link_graph_batch": "verify_graph_batch",
                    "write_section": "verify_section",
                    "edit_page": "verify_edited_page",
                    "export_candidate": "review_release",
                    "finalize_release": END,
                }
                update.setdefault("route", default_routes.get(name, END))
                if (
                    self.source_first(state)
                    and state.get("mode") == "manual"
                    and name in {"plan_source_document", "finalize_source_document"}
                ):
                    update["status"] = "awaiting_manual_review"
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
        if self.source_first(state) and destination == "review_stage":
            destination = {
                "plan_source_document": "write_source_document",
                "finalize_source_document": END,
            }.get(record["stage"], destination)
        if (
            self.source_first(state)
            and record["stage"] not in {"plan_source_document", "finalize_source_document"}
            and not (record["stage"] == "finalize_graph" and state.get("graph_only"))
        ):
            return {"route": destination}
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
                "readable_document": state.get("completion_plan_path", "")
                if record["stage"] == "plan_source_document"
                else state.get("completion_path", "")
                if record["stage"] == "finalize_source_document"
                else "",
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
            if record["stage"] in {"finalize_release", "finalize_source_document"}:
                update["status"] = state["completion_status"]
            if record["stage"] == "finalize_graph" and state.get("graph_only"):
                update["status"] = "graph_complete"
            return update
        if action == "reject":
            self.stages.record(
                "review_stage",
                state,
                {"route": END, "decision_ref": decision_ref, "status": "rejected"},
            )
            return {"route": END, "status": "rejected"}
        if (
            action == "request_correction"
            and self.source_first(state)
            and record["stage"] in {"plan_source_document", "finalize_source_document"}
        ):
            update = {
                "route": "plan_source_document"
                if record["stage"] == "plan_source_document"
                else "write_source_document",
                "feedback_ref": self.store.put([decision["rationale"]]),
                "completion_packet_index": 0,
                "completion_attempt": 0,
                "completion_repair_counts": {},
                "completion_repair_records_ref": "",
                "completion_audit_diagnostics_ref": "",
                "completion_sections_ref": "",
                "completion_draft_ref": "",
                "completion_audit_ref": "",
                "completion_audit_count": 0,
                "editorial_round": 0,
                "editorial_review_ref": "",
                "editorial_candidate_ref": "",
                "editorial_history_ref": "",
                "review_error": "",
                "status": "running",
            }
            self.stages.record("review_stage", state, {"decision_ref": decision_ref, **update})
            return update
        repair_targets = {
            "audit_semantic_graph": "propose_semantic_graph",
            "verify_document_batch": "extract_document_batch",
            "validate_page_plan": "draft_page_plan",
            "verify_section": "write_section",
            "verify_edited_page": "edit_page",
        }
        target = repair_targets.get(record["stage"], record["stage"])
        if action == "request_correction" and target in {
            "propose_semantic_graph",
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
        if self.source_first(state) and state.get("inventory_ref"):
            counts = dict(state.get("recovery_counts", {}))
            stage = issue["stage"]
            counts[stage] = counts.get(stage, 0) + 1
            target = state.get("issue_return", stage)
            if counts[stage] > 1:
                target = {
                    "prepare_source_images": "extract_document_batch",
                    "plan_source_document": "write_source_document",
                    "write_source_document": "finalize_source_document",
                    "repair_source_document": "finalize_source_document",
                    "audit_source_document": "finalize_source_document",
                    "review_source_editorial": "finalize_source_document",
                    "revise_source_document": "finalize_source_document",
                    "verify_source_revision": "finalize_source_document",
                }.get(stage, "plan_source_document")
            result = {
                "route": target,
                "status": "running_with_limitations",
                "recovery_counts": counts,
                "limitations_ref": self.limitations(
                    state, [f"{stage}: {finding}" for finding in issue["findings"]]
                ),
            }
            self.stages.record("resolve_issues_automatically", state, result)
            return result
        unresolved = {
            "actor_type": "policy",
            "stage": issue["stage"],
            "findings": issue["findings"],
            "source_revision": state.get("snapshot_ref"),
            "reason": "Unresolved integrity failure or coverage below the configured threshold",
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
