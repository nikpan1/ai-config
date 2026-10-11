import json
import os
import re
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from time import monotonic
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

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
from docgen_graph.source_links import (
    citation_labels,
    link_citations,
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
    for mapping in draft["mappings"]:
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
        snapshot = snapshot_inputs(
            self.store,
            Path(state["docs"]),
            Path(state["code"]) if state.get("code") else None,
            Path(state["template"]),
            state.get("brief", ""),
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
        contract = {"hash": source["template_hash"], "headings": _sections(text), "text": text}
        if not contract["headings"]:
            return self.issue(
                state,
                "compile_template",
                ["Template has no mandatory headings"],
                "compile_template",
            )
        return {"template_ref": self.store.put(contract), "route": "draft_page_plan"}

    def _groups(self, state: PipelineState) -> list[dict]:
        spans = self.spans(state)
        groups = {}
        for item in self.assertions(state):
            span = spans[item["evidence_ids"][0]]
            heading = span["heading"]
            topic = " / ".join(heading.split(" / ")[:2]) if heading else span["path"]
            key = (span["kind"], span["path"], topic)
            group = groups.setdefault(
                key,
                {
                    "source": span["path"],
                    "topic": topic,
                    "kind": span["kind"],
                    "obligation_ids": [],
                    "examples": [],
                },
            )
            group["obligation_ids"].append(item["id"])
            if len(group["examples"]) < 2:
                group["examples"].append(item["statement"])
        result = []
        for key, group in groups.items():
            for index, ids in enumerate(_chunks(group["obligation_ids"], 30)):
                result.append({**group, "id": digest([key, index])[:16], "obligation_ids": ids})
        return result

    def draft_page_plan(self, state: PipelineState) -> dict:
        groups = self._groups(state)
        contract = self.read(state, "template_ref")
        draft = self.call(
            "draft_plan",
            {
                "brief": self.read(state, "snapshot_ref")["brief"],
                "template_headings": contract["headings"],
                "groups": [
                    {key: value for key, value in group.items() if key != "obligation_ids"}
                    | {"obligation_count": len(group["obligation_ids"])}
                    for group in groups
                ],
                "feedback": state.get("plan_feedback", ""),
                "conflict_candidates": self.graph.conflict_candidates(),
            },
            PagePlanDraft,
        )
        group_map = {group["id"]: group for group in groups}
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
                for identifier in group_map[group_id]["obligation_ids"][:3]
            ]
            sections.append(
                {
                    "title": str(raw.get("title", "")).strip(),
                    "purpose": str(raw.get("purpose", "")).strip(),
                    "group_ids": ids,
                    "support_group_ids": support_ids,
                    "obligation_ids": obligations,
                    "supporting_obligation_ids": sorted(set(supporting)),
                    "queries": [str(query) for query in raw.get("queries", [])],
                }
            )
        plan = {
            "schema": 1,
            "title": str(draft.get("title", "Documentation")),
            "sections": sections,
            "groups": groups,
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
        if len(allocated) != len(set(allocated)) or set(allocated) != set(all_ids):
            findings.append("Plan must allocate every obligation exactly once")
        group_ids = {group["id"] for group in plan["groups"]}
        for section in plan["sections"]:
            if not section["obligation_ids"] and not section["supporting_obligation_ids"]:
                findings.append(f"Section has no source evidence: {section['title']}")
            if not set(section["group_ids"] + section["support_group_ids"]).issubset(group_ids):
                findings.append(f"Section references an unknown source group: {section['title']}")
        titles = {section["title"].casefold() for section in plan["sections"]}
        for heading in contract["headings"]:
            if heading.casefold() not in titles:
                findings.append(f"Missing required template heading: {heading}")
        if any(not section["title"] or not section["purpose"] for section in plan["sections"]):
            findings.append("A section lacks title or purpose")
        if not plan["sections"]:
            findings.append("Plan has no sections")
        if not findings:
            audit = self.call(
                "verify_plan",
                {
                    "template_headings": contract["headings"],
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
        ):
            lines.extend(
                [f"## {key.title()}", "", json.dumps(plan[key], ensure_ascii=False, indent=2), ""]
            )
        self.store.write(f"runs/{self.run_id}/documentation-plan.md", "\n".join(lines))
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
        size = 0
        for identifier in section["obligation_ids"] or section["supporting_obligation_ids"]:
            assertion = self.graph.assertion(identifier)
            cost = sum(len(self.graph.evidence(key)["text"]) for key in assertion["evidence_ids"])
            if cost > 18000:
                raise ValueError(f"Obligation source context is too large: {identifier}")
            if current and (len(current) >= 6 or size + cost > 18000):
                units.append(current)
                current, size = [], 0
            current.append(identifier)
            size += cost
        if current:
            units.append(current)
        return units or [[]]

    def retrieve_section_evidence(self, state: PipelineState) -> dict:
        plan = self._approved_plan(state)
        section = plan["sections"][state["section_index"]]
        ids = self._units(section)[state["unit_index"]]
        required = ids + (section["supporting_obligation_ids"] if state["unit_index"] == 0 else [])
        packet = _bounded_evidence_packet(
            self.graph.retrieve(section["queries"] or [section["title"]], required)
        )
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
        cited = set(re.findall(r"\[(?:Code|Legacy) ([CD]\d+)\]", draft["markdown"]))
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
                }
            )
        return {
            "assembled_ref": self.store.put(sections),
            "edited_ref": self.store.put([]),
            "edit_index": 0,
            "route": "edit_page",
        }

    def edit_page(self, state: PipelineState) -> dict:
        sections = self.read(state, "assembled_ref")
        section = sections[state["edit_index"]]
        if not section["mappings"] and not re.search(
            r"\[(?:Code|Legacy) [CD]\d+\]", section["markdown"]
        ):
            draft = {"markdown": section["markdown"]}
        else:
            draft = self.call(
                "edit_page",
                {
                    "title": section["title"],
                    "markdown": section["markdown"],
                    "mappings": section["mappings"],
                    "feedback": self.read(state, "feedback_ref", [])
                    or state.get("release_feedback", ""),
                },
                EditDraft,
            )
        draft = EditDraft.model_validate(draft).model_dump()
        return {"draft_ref": self.store.put(draft)}

    def verify_edited_page(self, state: PipelineState) -> dict:
        sections = self.read(state, "assembled_ref")
        section = sections[state["edit_index"]]
        markdown = self.read(state, "draft_ref")["markdown"]
        old_citations = set(re.findall(r"\[(?:Code|Legacy) ([CD]\d+)\]", section["markdown"]))
        new_citations = set(re.findall(r"\[(?:Code|Legacy) ([CD]\d+)\]", markdown))
        findings = []
        if old_citations != new_citations:
            findings.append("Editorial revision changed citation coverage")
        ids = sorted(
            {item["obligation_id"] for item in section["mappings"]}
            | set(section["supporting_obligation_ids"])
        )
        if not findings and ids:
            evidence_ids = {
                key
                for identifier in ids
                for key in self.graph.assertion(identifier)["evidence_ids"]
            }
            audit = self.call(
                "verify_page",
                {
                    "original_markdown": section["markdown"],
                    "edited_markdown": markdown,
                    "mandatory_obligation_ids": sorted(
                        {item["obligation_id"] for item in section["mappings"]}
                    ),
                    "supporting_obligation_ids": section["supporting_obligation_ids"],
                    "obligations": [self.graph.assertion(identifier) for identifier in ids],
                    "original_evidence": [self.graph.evidence(key) for key in evidence_ids],
                },
                AuditDraft,
            )
            if not audit.get("accepted"):
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
        edited.append(
            {
                "title": section["title"],
                "markdown": markdown,
                "mappings": section["mappings"],
                "supporting_obligation_ids": section["supporting_obligation_ids"],
            }
        )
        next_index = state["edit_index"] + 1
        return {
            "edited_ref": self.store.put(edited),
            "edit_index": next_index,
            "attempt": 0,
            "feedback_ref": "",
            "route": "edit_page" if next_index < len(sections) else "audit_documentation",
        }

    def audit_documentation(self, state: PipelineState) -> dict:
        plan = self._approved_plan(state)
        sections = self.read(state, "edited_ref")
        expected = {item["id"] for item in self.assertions(state)}
        actual = [
            mapping["obligation_id"] for section in sections for mapping in section["mappings"]
        ]
        findings = []
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
        if findings:
            return self.issue(state, "audit_documentation", findings, "assemble_pages")
        audit = {
            "plan_hash": state["plan_hash"],
            "graph_revision": state["graph_revision"],
            "obligation_count": len(expected),
            "mapped_count": len(actual),
            "section_count": len(sections),
            "findings": [],
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
        rendered_sections = [
            link_citations(_section_body(section["title"], section["markdown"]), direct_links)
            for section in sections
        ]
        candidate_hash = digest([state["plan_hash"], rendered_sections, evidence])
        base = f"runs/{self.run_id}/candidates/{candidate_hash}"
        lines = [f"# {plan['title']}", "", "[Source index](../source-index.md)", ""]
        for section, markdown in zip(sections, rendered_sections, strict=True):
            lines.extend([f"## {section['title']}", "", markdown, ""])
        self.store.write(f"{base}/documentation/index.md", "\n".join(lines))
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
                    "mappings": [
                        mapping for section in sections for mapping in section["mappings"]
                    ],
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
        for relative, checksum in expected.items():
            path = (directory / relative).resolve()
            if not path.is_relative_to(directory) or digest(path.read_bytes()) != checksum:
                raise ValueError(f"Candidate changed after review: {relative}")
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
            "audit_documentation": ["export_candidate", "review_issues"],
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
            )
            return update

        return execute
