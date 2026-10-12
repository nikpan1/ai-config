import argparse
import json
import re
import sqlite3
import sys
from contextlib import closing
from dataclasses import replace
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from docgen_graph.budget import BudgetLedger
from docgen_graph.config import Settings
from docgen_graph.knowledge import KnowledgeGraph
from docgen_graph.migration import inspect_legacy_workspace
from docgen_graph.model import GeminiModel
from docgen_graph.storage import ArtifactStore
from docgen_graph.workflow import Pipeline


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(prog="docgen")
    command.add_argument("--env-file", type=Path)
    command.add_argument("--code-backend", choices=("gemini", "codex_sdk", "auggie_sdk"))
    command.add_argument("--code-model")
    subcommands = command.add_subparsers(dest="command", required=True)
    run = subcommands.add_parser("run")
    run.add_argument("--docs", type=Path, required=True)
    run.add_argument("--code", type=Path)
    run.add_argument("--template", type=Path)
    run.add_argument("--brief", default="")
    run.add_argument("--mode", choices=("manual", "autopilot"), default="manual")
    run.add_argument("--thread-id", required=True)
    run.add_argument("--decisions", type=Path)
    for name in ("status", "history", "resume", "inspect-evidence"):
        subcommands.add_parser(name).add_argument("--thread-id", required=True)
    subcommands.choices["resume"].add_argument("--decisions", type=Path)
    subcommands.choices["status"].add_argument("--json", action="store_true")
    subcommands.choices["inspect-evidence"].add_argument("--citation", required=True)
    subcommands.add_parser("budget")
    migrate = subcommands.add_parser("migrate")
    migrate.add_argument("--from-workspace", type=Path, required=True)
    migrate.add_argument("--copy", action="store_true")
    return command


def _pending(state) -> list[dict]:
    return [item.value for task in state.tasks for item in task.interrupts]


def _choice(prompt: str, choices: dict[str, str]) -> str | None:
    print(prompt)
    for key, label in choices.items():
        print(f"  {key}: {label}")
    while True:
        try:
            answer = input("Choice: ").strip().lower()
        except EOFError:
            return None
        if answer in choices:
            return answer
        print("Choose one of the listed actions.")


def _input(prompt: str) -> str | None:
    try:
        return input(prompt).strip()
    except EOFError:
        return None


def _decision(request: dict) -> dict | None:
    kind = request["kind"]
    print(f"\nReview: {kind}")
    artifact = request.get("path") or request.get("plan_path")
    artifact = artifact or request.get("issue", {}).get("stage")
    revision = request.get("hash") or request.get("plan_hash")
    revision = revision or request.get("candidate_hash")
    revision = revision or request.get("issue", {}).get("revision")
    print(f"Artifact: {artifact}")
    print(f"Revision: {revision}")
    if kind == "stage":
        selected = _choice(
            "Review this step output", {"a": "Approve", "c": "Request correction", "r": "Reject"}
        )
        action = {"a": "approve", "c": "request_correction", "r": "reject"}.get(selected)
        binding = {key: request[key] for key in ("stage", "item", "hash")}
    elif kind == "plan":
        selected = _choice(
            "Review the plan", {"a": "Approve", "c": "Request changes", "r": "Reject"}
        )
        action = {"a": "approve_plan", "c": "request_changes", "r": "reject_plan"}.get(selected)
        binding = {"plan_hash": request["plan_hash"]}
        if action == "approve_plan":
            binding["conflict_decisions"] = {}
            for item in request.get("conflict_candidates", []):
                key = f"{item['code_id']}:{item['document_id']}"
                resolution = _choice(
                    f"Conflict {key}",
                    {
                        "b": "Present both",
                        "c": "Code applies",
                        "d": "Docs apply",
                        "n": "Not a conflict",
                    },
                )
                if resolution is None:
                    return None
                binding["conflict_decisions"][key] = {
                    "b": "present_both",
                    "c": "code_applies",
                    "d": "docs_apply",
                    "n": "not_conflict",
                }[resolution]
            binding["discrepancy_decisions"] = {}
            for item in request.get("discrepancy_keys", []):
                resolution = _choice(
                    f"Discrepancy {item['description']}",
                    {
                        "b": "Present both",
                        "c": "Code applies",
                        "d": "Docs apply",
                        "n": "Not a conflict",
                    },
                )
                if resolution is None:
                    return None
                binding["discrepancy_decisions"][item["id"]] = {
                    "b": "present_both",
                    "c": "code_applies",
                    "d": "docs_apply",
                    "n": "not_conflict",
                }[resolution]
    elif kind == "release":
        selected = _choice(
            "Review the candidate", {"a": "Approve release", "c": "Request changes", "r": "Reject"}
        )
        action = {"a": "approve_release", "c": "request_changes", "r": "reject_release"}.get(
            selected
        )
        binding = {"candidate_hash": request["candidate_hash"]}
    else:
        selected = _choice("Review the issue", {"t": "Retry", "r": "Reject"})
        action = {"t": "retry", "r": "reject"}.get(selected)
        binding = {"revision": request["issue"]["revision"]}
    if action is None:
        return None
    reviewer = _input("Reviewer: ")
    rationale = _input("Rationale: ")
    if not reviewer or not rationale:
        return None
    return {"action": action, "reviewer": reviewer, "rationale": rationale, **binding}


def _drive(graph, config: dict, initial, decision: dict | None, interactive: bool) -> dict:
    graph.invoke(initial, config)
    while True:
        state = graph.get_state(config)
        pending = _pending(state)
        if not pending:
            return {"status": state.values.get("status"), "next": state.next, "interrupts": []}
        if decision is None:
            if not interactive:
                return {
                    "status": "awaiting_manual_review",
                    "next": state.next,
                    "interrupts": pending,
                }
            decision = _decision(pending[0])
            if decision is None:
                return {
                    "status": "awaiting_manual_review",
                    "next": state.next,
                    "interrupts": pending,
                }
        graph.invoke(Command(resume=decision), config)
        decision = None


def _main() -> int:
    args = parser().parse_args()
    settings = Settings.load(args.env_file)
    if args.code_backend or args.code_model:
        backend = args.code_backend or settings.code_analysis_backend
        model = args.code_model or (settings.model if backend == "gemini" else "")
        if not model or (backend == "gemini" and model != settings.model):
            raise ValueError(
                "Specify an explicit provider code model; Gemini remains gemini-3.8-flash"
            )
        settings = replace(settings, code_analysis_backend=backend, code_analysis_model=model)
    if args.command == "budget":
        print(
            json.dumps(
                {
                    "ledger": str(settings.budget_ledger),
                    **BudgetLedger(settings.budget_ledger, settings.budget_pln).summary(),
                },
                indent=2,
            )
        )
        return 0
    if args.command == "migrate":
        print(
            json.dumps(
                inspect_legacy_workspace(
                    args.from_workspace, settings.workspace / "imported-legacy", args.copy
                ),
                indent=2,
            )
        )
        return 0
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,100}", args.thread_id):
        raise ValueError(
            "thread-id must contain only letters, digits, periods, underscores, and dashes"
        )
    store = ArtifactStore(settings.workspace)
    if args.command == "inspect-evidence":
        graph = KnowledgeGraph(store.root / "runs" / args.thread_id / "graph.sqlite")
        evidence = graph.evidence(args.citation)
        if not evidence:
            raise ValueError(f"Citation not found: {args.citation}")
        print(json.dumps(evidence, ensure_ascii=False, indent=2))
        return 0
    checkpoint_path = store.root / "checkpoints.sqlite"
    with closing(sqlite3.connect(checkpoint_path, check_same_thread=False)) as connection:
        pipeline = Pipeline(store, GeminiModel(settings, store, args.thread_id), args.thread_id)
        graph = pipeline.build(SqliteSaver(connection))
        config = {"configurable": {"thread_id": args.thread_id}, "recursion_limit": 100000}
        state = graph.get_state(config)
        if args.command == "run":
            if state.values:
                raise ValueError("Thread already exists; use resume or choose a new thread-id")
            inputs = {
                "run_id": args.thread_id,
                "docs": str(args.docs.resolve()),
                "code": str(args.code.resolve()) if args.code else "",
                "template": str((args.template or settings.shared_data / "template.md").resolve()),
                "brief": args.brief,
                "mode": args.mode,
                "policy_version": "v2",
                "status": "running",
            }
            decision = json.loads(args.decisions.read_text("utf-8")) if args.decisions else None
            result = _drive(graph, config, inputs, decision, sys.stdin.isatty())
        elif args.command == "resume":
            if not state.values:
                raise ValueError("Thread does not exist")
            if state.values.get("runtime_signature") != pipeline.runtime_signature():
                raise ValueError(
                    "Run uses an incompatible graph revision; inspect its artifacts "
                    "and start a new thread from frozen inputs"
                )
            decision = json.loads(args.decisions.read_text("utf-8")) if args.decisions else None
            result = _drive(
                graph,
                config,
                Command(resume=decision) if decision is not None else None,
                None,
                sys.stdin.isatty(),
            )
        elif args.command == "status":
            result = {"state": state.values, "next": state.next, "interrupts": _pending(state)}
        else:
            result = [
                {
                    "next": snapshot.next,
                    "status": snapshot.values.get("status"),
                    "checkpoint": snapshot.config.get("configurable", {}).get("checkpoint_id"),
                }
                for snapshot in graph.get_state_history(config)
            ]
        if args.command in {"run", "resume"}:
            result["run_path"] = str(store.root / "runs" / args.thread_id)
            if result["status"] in {"complete", "complete_with_exclusions"}:
                result["exclusions"] = str(store.root / "runs" / args.thread_id / "exclusions.md")
        if args.command == "status" and not args.json:
            print(f"Status: {result['state'].get('status', 'not started')}")
            print(f"Next nodes: {', '.join(result['next']) or 'none'}")
            for pending in result["interrupts"]:
                print(f"Pending review: {pending.get('kind')} {pending.get('path', '')}")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return (
            {
                "complete": 0,
                "complete_with_exclusions": 0,
                "awaiting_manual_review": 10,
                "rejected": 12,
                "incomplete": 13,
            }.get(result.get("status"), 11)
            if isinstance(result, dict) and args.command in {"run", "resume"}
            else 0
        )


def main() -> int:
    try:
        return _main()
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as error:
        print(f"docgen: {error}", file=sys.stderr)
        return 11


if __name__ == "__main__":
    raise SystemExit(main())
