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
from docgen_graph.contracts import (
    AuditDraft,
    CodeAnalysisDraft,
    DocumentExtractionDraft,
    EditDraft,
    PagePlanDraft,
    SectionDraft,
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
from docgen_graph.source_links import (
    citation_labels,
    link_citations,
    normalize_citation_syntax,
    normalize_section_links,
    source_url_from_markdown,
    text_fragment_url,
)
from docgen_graph.storage import ArtifactStore, digest


class PipelineState(TypedDict, total=False):
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

    def read(self, state: PipelineState, key: str, default=None):
        return self.store.get(state[key]) if state.get(key) else default

    def runtime_signature(self) -> str:
        prompts = files("docgen_graph").joinpath("prompts")
        prompt_hashes = {item.name: digest(item.read_bytes()) for item in prompts.iterdir()}
        model_name = getattr(getattr(self.model, "settings", None), "model", "test-double")
        return digest([implementation_signature(), prompt_hashes, model_name, "lexical-two-hop-v1"])

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
            "route": "review_issues",
            "status": "awaiting_issue_review",
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
        snapshot["revision"] = digest([snapshot["revision"], signature])
        self.store.write(
            f"runs/{self.run_id}/run-manifest.json",
            json.dumps(snapshot, ensure_ascii=False, indent=2),
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
        return {
            "inventory_ref": self.store.put(result),
            "code_index": 0,
            "document_index": 0,
            "graph_index": 0,
            "assertions_ref": self.store.put([]),
            "exclusions_ref": self.store.put([]),
            "route": "analyze_code_unit" if result["code_units"] else "extract_document_batch",
        }

    def analyze_code_unit(self, state: PipelineState) -> dict:
        inventory_record = self.read(state, "inventory_ref")
        ids = inventory_record["code_units"][state["code_index"]]
        spans = self.spans(state)
        payload = {
            "spans": [spans[key] for key in ids],
            "analysis": {
                spans[key]["path"]: inventory_record["analysis"][spans[key]["path"]] for key in ids
            },
            "feedback": self.read(state, "feedback_ref", []),
            "previous": self.read(state, "draft_ref") if state.get("attempt") else None,
        }
        draft = self.call("analyze_code", payload, CodeAnalysisDraft)
        return {"draft_ref": self.store.put(draft)}

    def verify_code_unit(self, state: PipelineState) -> dict:
        inventory_record = self.read(state, "inventory_ref")
        ids = inventory_record["code_units"][state["code_index"]]
        spans = self.spans(state)
        draft = self.read(state, "draft_ref")
        findings = []
        try:
            records = [normalized_assertion(item, set(ids)) for item in draft["details"]]
        except (ValueError, TypeError) as error:
            records = []
            findings.append(str(error))
        missing = set(ids) - {key for record in records for key in record["evidence_ids"]}
        if missing:
            findings.append(f"Code spans lack detail records: {sorted(missing)}")
        audit = (
            self.call(
                "verify_code",
                {
                    "spans": [spans[key] for key in ids],
                    "draft": draft,
                },
                AuditDraft,
            )
            if not findings
            else {"accepted": False, "findings": findings}
        )
        findings.extend(str(item) for item in audit.get("findings", []))
        if not audit.get("accepted") or findings:
            if state.get("attempt", 0) < 2:
                return {
                    "attempt": state.get("attempt", 0) + 1,
                    "feedback_ref": self.store.put(findings),
                    "route": "analyze_code_unit",
                }
            return self.issue(state, "verify_code_unit", findings, "analyze_code_unit")
        assertions = self.assertions(state) + records
        first = spans[ids[0]]
        last = spans[ids[-1]]
        report = (
            f"## {first['path']} lines {first['start_line']}-{last['end_line']}\n\n"
            f"{draft['report']}\n"
        )
        self.store.write(f"runs/{self.run_id}/reports/code-{state['code_index']:04d}.md", report)
        next_index = state["code_index"] + 1
        return {
            "assertions_ref": self.store.put(assertions),
            "code_index": next_index,
            "attempt": 0,
            "draft_ref": "",
            "feedback_ref": "",
            "route": "analyze_code_unit"
            if next_index < len(inventory_record["code_units"])
            else "extract_document_batch",
        }

    def extract_document_batch(self, state: PipelineState) -> dict:
        inventory_record = self.read(state, "inventory_ref")
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
            records = [normalized_assertion(item, set(ids)) for item in draft["assertions"]]
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
            if state.get("attempt", 0) < 2:
                return {
                    "attempt": state.get("attempt", 0) + 1,
                    "feedback_ref": self.store.put(findings),
                    "route": "extract_document_batch",
                }
            return self.issue(state, "verify_document_batch", findings, "extract_document_batch")
        next_index = state["document_index"] + 1
        return {
            "assertions_ref": self.store.put(self.assertions(state) + records),
            "exclusions_ref": self.store.put(self.read(state, "exclusions_ref", []) + excluded),
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
        contract = compile_requirements(text, source["template_hash"])
        if not contract["headings"]:
            return self.issue(
                state,
                "compile_template",
                ["Template has no mandatory headings"],
                "compile_template",
            )
        return {"template_ref": self.store.put(contract), "route": "draft_page_plan"}

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
                visual["review_status"] = "planned"
                visual["diagram"] = diagrams.get(visual.get("diagram_id"))
                if visual.get("diagram"):
                    visual["diagram"]["source"] = diagram_source(visual["diagram"])
        plan = {
            "schema": 2,
            "title": str(draft.get("title", "Documentation")),
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
            if state.get("attempt", 0) < 2:
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
        decision = interrupt(
            {
                "kind": "plan",
                "plan_hash": state["plan_hash"],
                "plan_path": str(self.store.root / "runs" / self.run_id / "documentation-plan.md"),
                "graph_revision": state["graph_revision"],
                "source_revision": state["snapshot_ref"],
                "unknowns": plan["unknowns"],
                "discrepancies": plan["discrepancies"],
                "discrepancy_keys": [
                    {"id": digest(item)[:16], "description": item} for item in plan["discrepancies"]
                ],
                "conflict_candidates": plan["conflict_candidates"],
                "input_exclusions": plan["input_exclusions"],
                "template_decisions": plan.get("template_decisions", []),
                "asset_decisions": plan.get("asset_decisions", []),
                "visuals": [
                    visual for section in plan["sections"] for visual in section.get("visuals", [])
                ],
                "error": state.get("review_error", ""),
            }
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
            "route": "write_section",
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
                        and (
                            state["unit_index"] == 0
                            or item["kind"] in {"purpose", "conditional"}
                        )
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
            if state.get("attempt", 0) < 2:
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
            sections.append(
                {
                    "title": section["title"],
                    "markdown": "\n\n".join(item["markdown"] for item in parts),
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
            if len(mandatory) > 12 or sum(
                len(item["text"]) for item in payload["original_evidence"]
            ) > 45000:
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
            if state.get("attempt", 0) < 1:
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
        return {"route": "export_candidate"}

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
        source_urls = {
            file["path"]: source_url_from_markdown(
                self.store.get_bytes(file["hash"]).decode("utf-8")
            )
            for file in snapshot["files"]
            if file["kind"] == "docs"
        }
        direct_links = {
            item["label"]: text_fragment_url(source_urls[item["path"]], item["text"])
            for item in evidence
            if item["kind"] == "docs" and source_urls.get(item["path"])
        }
        section_targets = {
            section["title"]: f"#{section_anchor(section['title'])}" for section in sections
        }

        def render(markdown: str) -> str:
            return normalize_section_links(link_citations(markdown, direct_links), section_targets)

        rendered_sections = [
            render(_section_body(section["title"], section["markdown"])) for section in sections
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
                passage = render(placement["passage"])
                offset = rendered.find(passage)
                if offset < 0 or rendered.count(passage) != 1:
                    raise ValueError("Export changed or duplicated a factual placement")
                start = section_start + offset
                final_placements.append(
                    {**placement, "passage": passage, "start": start, "end": start + len(passage)}
                )
            final_mappings.extend(
                {**mapping, "passage": render(mapping["passage"])}
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
                f"Snapshot SHA-256: `{item['file_hash']}`\n\n{excerpt}\n"
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
                    "candidate_hash": candidate_hash,
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
        decision = interrupt(
            {
                "kind": "release",
                "candidate_hash": candidate,
                "path": str(
                    self.store.root
                    / "runs"
                    / self.run_id
                    / "candidates"
                    / candidate
                    / "documentation"
                    / "index.md"
                ),
                "error": state.get("review_error", ""),
            }
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
        directory = self.store.root / "runs" / self.run_id / "candidates" / state["candidate_ref"]
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
        return {"status": "complete"}

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
        for name in (
            "snapshot_inputs",
            "inventory_sources",
            "analyze_code_unit",
            "verify_code_unit",
            "extract_document_batch",
            "verify_document_batch",
            "link_graph_batch",
            "verify_graph_batch",
            "finalize_graph",
            "compile_template",
            "draft_page_plan",
            "retrieve_plan_evidence",
            "validate_page_plan",
            "review_plan",
            "retrieve_section_evidence",
            "write_section",
            "verify_section",
            "assemble_pages",
            "edit_page",
            "verify_edited_page",
            "audit_documentation",
            "export_candidate",
            "review_release",
            "finalize_release",
            "review_issues",
        ):
            builder.add_node(name, self.logged_node(name))
        builder.add_edge(START, "snapshot_inputs")
        builder.add_edge("snapshot_inputs", "inventory_sources")
        builder.add_edge("analyze_code_unit", "verify_code_unit")
        builder.add_edge("extract_document_batch", "verify_document_batch")
        builder.add_edge("link_graph_batch", "verify_graph_batch")
        builder.add_edge("write_section", "verify_section")
        builder.add_edge("edit_page", "verify_edited_page")
        builder.add_edge("export_candidate", "review_release")
        builder.add_edge("finalize_release", END)
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
        for name, targets in routed.items():
            builder.add_conditional_edges(name, lambda state: state["route"], targets)
        return builder.compile(checkpointer=checkpointer)

    def logged_node(self, name: str):
        function = getattr(self, name)

        def execute(state: PipelineState) -> dict:
            if name not in {"snapshot_inputs", "review_plan", "review_release", "review_issues"}:
                if state.get("runtime_signature") != self.runtime_signature():
                    raise ValueError("Runtime changed; start a new run revision")
            started = monotonic()
            update = function(state)
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
