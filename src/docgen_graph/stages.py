import json
from pathlib import Path

from docgen_graph.storage import ArtifactStore, digest

STEPS = (
    "snapshot_inputs",
    "inventory_sources",
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
    "review_stage",
    "resolve_issues_automatically",
    "inventory_source_aspects",
    "audit_source_coverage",
    "plan_authoring_action",
    "execute_authoring_tool",
    "verify_tool_result",
    "audit_source_to_document",
    "verify_knowledge_delta",
    "commit_knowledge_revision",
    "locate_visual_evidence",
    "propose_semantic_graph",
    "audit_semantic_graph",
    "publish_semantic_graph",
    "prepare_source_images",
    "plan_source_document",
    "write_source_document",
    "audit_source_document",
    "finalize_source_document",
    "repair_source_document",
)
STEP_NUMBERS = {
    "snapshot_inputs": 1,
    "inventory_sources": 2,
    "extract_document_batch": 5,
    "verify_document_batch": 6,
    "link_graph_batch": 7,
    "verify_graph_batch": 8,
    "finalize_graph": 9,
    "compile_template": 10,
    "draft_page_plan": 11,
    "retrieve_plan_evidence": 12,
    "validate_page_plan": 13,
    "review_plan": 14,
    "retrieve_section_evidence": 15,
    "write_section": 16,
    "verify_section": 17,
    "assemble_pages": 18,
    "edit_page": 19,
    "verify_edited_page": 20,
    "audit_documentation": 21,
    "export_candidate": 22,
    "review_release": 23,
    "finalize_release": 24,
    "review_issues": 25,
    "review_stage": 26,
    "resolve_issues_automatically": 27,
    "inventory_source_aspects": 28,
    "audit_source_coverage": 29,
    "plan_authoring_action": 30,
    "execute_authoring_tool": 31,
    "verify_tool_result": 32,
    "audit_source_to_document": 33,
    "verify_knowledge_delta": 34,
    "commit_knowledge_revision": 35,
    "locate_visual_evidence": 40,
    "propose_semantic_graph": 41,
    "audit_semantic_graph": 42,
    "publish_semantic_graph": 43,
    "prepare_source_images": 44,
    "plan_source_document": 45,
    "write_source_document": 46,
    "audit_source_document": 47,
    "finalize_source_document": 48,
    "repair_source_document": 49,
}
REPEATED = {
    "propose_semantic_graph": "semantic_index",
    "audit_semantic_graph": "semantic_index",
    "publish_semantic_graph": "semantic_index",
    "inventory_source_aspects": "source_aspect_index",
    "audit_source_coverage": "document_index",
    "audit_source_to_document": "source_audit_index",
    "plan_authoring_action": "section_index",
    "execute_authoring_tool": "section_index",
    "verify_tool_result": "section_index",
    "extract_document_batch": "document_index",
    "verify_document_batch": "document_index",
    "link_graph_batch": "graph_index",
    "verify_graph_batch": "graph_index",
    "retrieve_plan_evidence": "plan_packet_index",
    "retrieve_section_evidence": "section_index",
    "write_section": "section_index",
    "verify_section": "section_index",
    "edit_page": "edit_index",
    "verify_edited_page": "edit_index",
}


class StageArtifacts:
    def __init__(self, store: ArtifactStore, run_id: str):
        self.store = store
        self.run_id = run_id
        self.run = Path("runs") / run_id

    def initialize(
        self, mode: str, policy_version: str, signature: str, content_repair_limit: int = 2
    ) -> None:
        path = self.store.root / self.run / "run-manifest.json"
        manifest = {
            "schema_version": 2,
            "mode": mode,
            "policy_version": policy_version,
            "runtime_signature": signature,
            "content_repair_limit": content_repair_limit,
            "steps": {name: f"step{number}" for name, number in STEP_NUMBERS.items()},
        }
        if path.exists():
            if json.loads(path.read_text("utf-8")) != manifest:
                raise ValueError("Run manifest is incompatible with the current pipeline revision")
            return
        self.store.write(str(self.run / "run-manifest.json"), json.dumps(manifest, indent=2))
        self.store.write(
            str(self.run / "README.md"),
            f"# Run {self.run_id}\n\nMode: {mode}\n\nSee `run-manifest.json` for the step map.\n",
        )
        self.store.write(str(self.run / "decisions.md"), "# Decisions\n\n")
        self.store.write(str(self.run / "exclusions.md"), "# Exclusions\n\n")

    def step(self, name: str) -> Path:
        return self.run / f"step{STEP_NUMBERS[name]}"

    def record(self, name: str, state: dict, update: dict, cost_pln: float = 0.0) -> dict:
        base = self.step(name)
        item_key = REPEATED.get(name)
        item = f"{state.get(item_key, 0):04d}" if item_key else "run"
        root = base / "items" / item if item_key else base
        content = {"stage": name, "item": item, "inputs": state, "outputs": update}
        content_hash = digest(content)
        directory = self.store.root / root / "revisions"
        prior = sorted(directory.glob("r*/manifest.json")) if directory.exists() else []
        for manifest_path in prior:
            manifest = json.loads(manifest_path.read_text("utf-8"))
            if manifest["hash"] == content_hash:
                if (
                    digest((manifest_path.parent / "result.json").read_bytes())
                    != manifest["result_hash"]
                ):
                    raise ValueError("Stage artifact changed after checkpoint")
                return {
                    "stage": name,
                    "item": item,
                    "hash": content_hash,
                    "path": str(manifest_path.parent / "result.md"),
                }
        revision = len(prior) + 1
        destination = root / "revisions" / f"r{revision:04d}"
        result = json.dumps(
            {**content, "cost_pln": cost_pln}, ensure_ascii=False, indent=2, default=str
        )
        result_path = self.store.write(str(destination / "result.json"), result)
        links = []
        for key, value in update.items():
            if key.endswith("_ref") and isinstance(value, str):
                try:
                    projection = json.dumps(self.store.get(value), ensure_ascii=False, indent=2)
                except (OSError, ValueError):
                    continue
                filename = f"{key}.json"
                self.store.write(str(destination / filename), projection)
                links.append(f"- {key}: [{filename}]({filename})")
        lines = [
            f"# {name}",
            "",
            f"Item: `{item}`",
            f"Revision: `r{revision:04d}`",
            f"Hash: `{content_hash}`",
            "",
            "## Inputs",
            "",
            "| Field | Value |",
            "| --- | --- |",
        ]
        lines.extend(
            f"| {key} | `{str(value)[:160]}` |"
            for key, value in sorted(state.items())
            if key not in {"stage_record"}
        )
        lines.extend(["", "## Outputs", "", "| Field | Value |", "| --- | --- |"])
        lines.extend(f"| {key} | `{str(value)[:160]}` |" for key, value in sorted(update.items()))
        findings = [
            f"- {key}: `{str(update[key])[:300]}`"
            for key in ("status", "issue", "coverage_status", "audit_status")
            if key in update
        ]
        decisions = [
            f"- {key}: `{str(update[key])[:300]}`"
            for key in ("decision_ref", "review_ref", "exclusions_ref")
            if key in update
        ]
        lines.extend(
            [
                "",
                "## Findings",
                "",
                *(findings or ["No separate findings recorded."]),
                "",
                "## Decisions",
                "",
                *(decisions or ["No decision was made in this step."]),
                "",
                "## Cost",
                "",
                f"Gemini cost incurred in this execution: PLN {cost_pln:.6f}.",
                "",
                "## Readable artifacts",
                "",
                *(links or ["No object references."]),
                "",
                f"Next action: `{update.get('route', 'continue')}`",
                "",
            ]
        )
        self.store.write(str(destination / "result.md"), "\n".join(lines))
        self.store.write(
            str(destination / "manifest.json"),
            json.dumps(
                {
                    "stage": name,
                    "item": item,
                    "revision": revision,
                    "hash": content_hash,
                    "result_hash": digest(result_path.read_bytes()),
                },
                indent=2,
            ),
        )
        if item_key:
            self.store.write(
                str(root / "README.md"),
                f"# {name} {item}\n\n"
                f"Current: [r{revision:04d}](revisions/r{revision:04d}/result.md)\n\n"
                f"Previous revisions: {revision - 1}\n",
            )
        current_link = (
            f"items/{item}/README.md" if item_key else f"revisions/r{revision:04d}/result.md"
        )
        self.store.write(
            str(base / "README.md"),
            f"# Step {STEP_NUMBERS[name]}: {name}\n\nCurrent: [{item}]({current_link})\n",
        )
        self.store.write(
            str(base / "manifest.json"),
            json.dumps(
                {
                    "step": STEP_NUMBERS[name],
                    "stage": name,
                    "current_item": item,
                    "current_revision": revision,
                },
                indent=2,
            ),
        )
        return {
            "stage": name,
            "item": item,
            "hash": content_hash,
            "path": str(self.store.root / destination / "result.md"),
        }

    def skip(self, name: str, reason: str) -> None:
        base = self.step(name)
        self.store.write(
            str(base / "README.md"), f"# Step {STEP_NUMBERS[name]}: {name}\n\nSkipped: {reason}\n"
        )
        self.store.write(
            str(base / "manifest.json"),
            json.dumps(
                {"step": STEP_NUMBERS[name], "stage": name, "status": "skipped", "reason": reason},
                indent=2,
            ),
        )

    def pending(self, name: str, producer: dict) -> None:
        base = self.step(name)
        self.store.write(
            str(base / "README.md"),
            f"# Step {STEP_NUMBERS[name]}: {name}\n\n"
            f"Pending review of `{producer['stage']}` item `{producer['item']}` "
            f"hash `{producer['hash']}`.\n\nArtifact: {producer['path']}\n",
        )
        self.store.write(
            str(base / "manifest.json"),
            json.dumps(
                {
                    "step": STEP_NUMBERS[name],
                    "stage": name,
                    "status": "pending",
                    "producer": producer,
                },
                indent=2,
            ),
        )

    def mirror_candidate(self, candidate_hash: str, original: Path) -> Path:
        target = self.store.root / self.step("export_candidate") / "candidates" / candidate_hash
        for source in original.rglob("*"):
            if source.is_file():
                relative = source.relative_to(original)
                destination = target / relative
                if destination.exists() and digest(destination.read_bytes()) != digest(
                    source.read_bytes()
                ):
                    raise ValueError("Candidate copy differs from the reviewed artifact")
                if not destination.exists():
                    self.store.write(
                        str(destination.relative_to(self.store.root)), source.read_bytes()
                    )
        return target
