import argparse
import json
import sqlite3
from contextlib import closing
from dataclasses import replace
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from docgen_graph.config import Settings
from docgen_graph.model import GeminiModel
from docgen_graph.storage import ArtifactStore, digest
from docgen_graph.workflow import Pipeline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-run", required=True)
    parser.add_argument("--thread-id", required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--reuse-plan", action="store_true")
    restart = parser.add_mutually_exclusive_group()
    restart.add_argument("--restart-section", type=int)
    restart.add_argument("--restart-edit", type=int)
    restart.add_argument("--edit-sections", type=int, nargs="+")
    parser.add_argument("--review-feedback", type=Path)
    parser.add_argument("--thinking-level", choices=("low", "medium", "high"), default="medium")
    args = parser.parse_args()
    if args.edit_sections:
        args.edit_sections = sorted(set(args.edit_sections))
        args.restart_edit = args.edit_sections[0]
    if (args.restart_section is not None or args.restart_edit is not None) and not args.reuse_plan:
        parser.error("Restarting authoring requires --reuse-plan")
    feedback = json.loads(args.review_feedback.read_text()) if args.review_feedback else []
    if not isinstance(feedback, list) or any(not isinstance(item, str) for item in feedback):
        parser.error("Review feedback must be a JSON list of strings")
    settings = replace(
        Settings.load(),
        workspace=args.workspace.resolve(),
        output_tokens=32768,
        request_tokens=500000,
        timeout_seconds=240,
        content_repair_limit=5,
        thinking_level=args.thinking_level,
        audit_thinking_level="medium",
    )
    store = ArtifactStore(settings.workspace)
    config = {"configurable": {"thread_id": args.thread_id}, "recursion_limit": 1000}
    with closing(
        sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)
    ) as connection:
        saver = SqliteSaver(connection)
        target = store.root / "runs" / args.thread_id
        fresh = not target.exists()
        if fresh:
            source = Pipeline(store, GeminiModel(settings, store, args.source_run), args.source_run)
            source_graph = source.build(saver)
            checkpoint = source_graph.get_state({"configurable": {"thread_id": args.source_run}})
            if not args.reuse_plan and checkpoint.values.get("status") not in {
                "completed",
                "complete",
                "complete_with_exclusions",
            }:
                raise ValueError("Reauthoring requires a completed verified source run")
            old = checkpoint.values
            if args.reuse_plan:
                approved = store.get(old["approval_ref"])
                source_plan = store.get(old["plan_ref"])
                if (
                    approved["action"] != "approve_plan"
                    or approved["plan_hash"] != digest(source_plan)
                    or approved["source_revision"] != old["snapshot_ref"]
                    or source_plan["template_hash"] != digest(args.template.read_bytes())
                ):
                    raise ValueError("Plan reuse requires the exact approved source and template")
            target.mkdir(parents=True)
            with (
                closing(
                    sqlite3.connect(store.root / "runs" / args.source_run / "graph.sqlite")
                ) as original,
                closing(sqlite3.connect(target / "graph.sqlite")) as copied,
            ):
                original.backup(copied)
                if copied.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("Imported graph failed integrity verification")
            snapshot = dict(store.get(old["snapshot_ref"]))
            for file in snapshot["files"]:
                store.get_bytes(file["hash"])
            snapshot["template_hash"] = store.put_bytes(args.template.read_bytes())
            snapshot["template_path"] = str(args.template.resolve())
            snapshot["brief"] = (
                "Risk Profiling. Create the complete single-page business documentation using "
                "the production template. Preserve all business conditions, boundaries and "
                "uncertainties. Retain technical findings only in audit scope decisions. "
                "Use precise compact evidence references and the required visual tables."
            )
            if not args.reuse_plan:
                snapshot["revision"] = digest(snapshot)
            retained = (
                "inventory_ref",
                "assertions_ref",
                "exclusions_ref",
                "graph_revision",
                "source_aspects_ref",
                "source_decisions_ref",
                "source_non_substantive_ref",
                "code_provenance_ref",
                "document_provenance_ref",
                "code_scope_ref",
                "code_history_ref",
            )
            state = {key: old[key] for key in retained if key in old}
            if args.reuse_plan:
                snapshot = store.get(old["snapshot_ref"])
                state.update(
                    {
                        key: old[key]
                        for key in (
                            "template_ref",
                            "plan_ref",
                            "plan_packets_ref",
                            "plan_packet_index",
                        )
                    }
                )
            state.update(
                run_id=args.thread_id,
                snapshot_ref=store.put(snapshot),
                mode="autopilot",
                policy_version="v2",
                status="running",
                route="validate_page_plan" if args.reuse_plan else "compile_template",
                attempt=0,
                source_audit_index=0,
            )
        pipeline = Pipeline(store, GeminiModel(settings, store, args.thread_id), args.thread_id)
        graph = pipeline.build(saver)
        if fresh:
            state["runtime_signature"] = pipeline.runtime_signature()
            pipeline.stages.initialize(
                "autopilot", "v2", state["runtime_signature"], settings.content_repair_limit
            )
            store.write(
                f"runs/{args.thread_id}/source-reuse.json",
                json.dumps(
                    {
                        "source_run": args.source_run,
                        "source_checkpoint": checkpoint.config["configurable"]["checkpoint_id"],
                        "source_runtime_signature": old["runtime_signature"],
                        "source_snapshot": old["snapshot_ref"],
                        "target_snapshot": state["snapshot_ref"],
                        "retained_refs": {key: state[key] for key in retained if key in state},
                        "repeated_stages": (
                            "Plan verification, writing, editing, all final audits"
                            if args.reuse_plan
                            else "Template compilation, planning, writing, editing and final audits"
                        ),
                        "reused_plan": old.get("plan_ref") if args.reuse_plan else None,
                        "reused_written_ref": old.get("written_ref")
                        if args.restart_section is not None or args.restart_edit is not None
                        else None,
                        "restart_section": args.restart_section,
                        "restart_edit": args.restart_edit,
                        "edit_sections": args.edit_sections,
                        "reused_assembled_ref": old.get("assembled_ref")
                        if args.restart_edit is not None
                        else None,
                        "reused_edited_ref": old.get("edited_ref")
                        if args.restart_edit is not None
                        else None,
                        "agent_review_feedback": feedback,
                        "provider_provenance": (
                            "Preserved from original source extraction and code analysis"
                        ),
                    },
                    indent=2,
                ),
            )
            graph.update_state(config, state, as_node="review_stage")
        elif graph.get_state(config).values["runtime_signature"] != pipeline.runtime_signature():
            raise ValueError("Implementation changed; use a fresh thread for reauthoring")
        try:
            if fresh and (args.restart_section is not None or args.restart_edit is not None):
                for update in graph.stream(
                    None, config, stream_mode="updates", interrupt_after=["review_plan"]
                ):
                    print(json.dumps({"completed_nodes": list(update)}), flush=True)
                reviewed = graph.get_state(config).values
                if reviewed.get("status") != "plan_approved":
                    raise ValueError("Reused authoring requires a newly verified and approved plan")
            if fresh and args.restart_edit is not None:
                assembled = store.get(old["assembled_ref"])
                edited = store.get(old["edited_ref"])
                if not 0 <= args.restart_edit <= len(assembled):
                    raise ValueError("Restart edit is outside the assembled sections")
                if len(edited) < args.restart_edit:
                    raise ValueError("Only previously verified edited sections can be reused")
                queue = args.edit_sections or list(range(args.restart_edit, len(assembled)))
                if any(index < 0 or index >= len(assembled) for index in queue):
                    raise ValueError("Edit section is outside the assembled sections")
                if args.edit_sections and len(edited) != len(assembled):
                    raise ValueError("Selective editing requires all sections previously verified")
                graph.update_state(
                    config,
                    {
                        "written_ref": old["written_ref"],
                        "assembled_ref": old["assembled_ref"],
                        "edited_ref": store.put(
                            edited if args.edit_sections else edited[: args.restart_edit]
                        ),
                        "edit_index": args.restart_edit,
                        "edit_queue_ref": store.put(queue),
                        "attempt": 0,
                        "draft_ref": "",
                        "feedback_ref": store.put(feedback),
                        "release_feedback": "\n".join(feedback),
                        "route": "edit_page" if queue else "audit_documentation",
                    },
                    as_node="review_stage",
                )
            if fresh and args.restart_section is not None:
                prefix = [
                    item
                    for item in store.get(old["written_ref"])
                    if item["section_index"] < args.restart_section
                ]
                plan = store.get(reviewed["plan_ref"])
                if not 0 <= args.restart_section < len(plan["sections"]):
                    raise ValueError("Restart section is outside the approved plan")
                for index in range(args.restart_section):
                    if len([item for item in prefix if item["section_index"] == index]) != len(
                        pipeline._units(plan["sections"][index])
                    ):
                        raise ValueError("Only complete previously verified sections can be reused")
                graph.update_state(
                    config,
                    {
                        "written_ref": store.put(prefix),
                        "section_index": args.restart_section,
                        "unit_index": 0,
                        "attempt": 0,
                        "draft_ref": "",
                        "feedback_ref": "",
                        "route": "retrieve_section_evidence",
                    },
                    as_node="review_stage",
                )
            for update in graph.stream(None, config, stream_mode="updates"):
                print(json.dumps({"completed_nodes": list(update)}), flush=True)
        finally:
            result = graph.get_state(config)
            store.write(
                f"runs/{args.thread_id}/live-result.json",
                json.dumps(
                    {
                        "state": result.values,
                        "next": result.next,
                    },
                    indent=2,
                ),
            )
            print(json.dumps({"status": result.values.get("status"), "next": result.next}))


if __name__ == "__main__":
    main()
