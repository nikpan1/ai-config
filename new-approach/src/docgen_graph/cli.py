import argparse
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from docgen_graph.budget import BudgetLedger
from docgen_graph.config import Settings
from docgen_graph.knowledge import KnowledgeGraph
from docgen_graph.model import GeminiModel
from docgen_graph.storage import ArtifactStore
from docgen_graph.workflow import Pipeline


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(prog="docgen-graph")
    command.add_argument("--env-file", type=Path)
    subcommands = command.add_subparsers(dest="command", required=True)
    run = subcommands.add_parser("run")
    run.add_argument("--docs", type=Path, required=True)
    run.add_argument("--code", type=Path, required=True)
    run.add_argument("--template", type=Path)
    run.add_argument("--brief", default="")
    run.add_argument("--thread-id", required=True)
    for name in ("status", "history", "resume", "inspect-evidence"):
        subcommands.add_parser(name).add_argument("--thread-id", required=True)
    subcommands.choices["resume"].add_argument("--decisions", type=Path)
    subcommands.choices["inspect-evidence"].add_argument("--citation", required=True)
    subcommands.add_parser("budget")
    return command


def main() -> None:
    args = parser().parse_args()
    settings = Settings.load(args.env_file)
    if args.command == "budget":
        print(
            json.dumps(
                {
                    "ledger": str(settings.budget_ledger),
                    **BudgetLedger(settings.budget_ledger).summary(),
                },
                indent=2,
            )
        )
        return
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
        return
    checkpoint_path = store.root / "checkpoints.sqlite"
    with closing(sqlite3.connect(checkpoint_path, check_same_thread=False)) as connection:
        saver = SqliteSaver(connection)
        model = GeminiModel(settings, store, args.thread_id)
        graph = Pipeline(store, model, args.thread_id).build(saver)
        config = {"configurable": {"thread_id": args.thread_id}, "recursion_limit": 100000}
        if args.command == "run":
            if graph.get_state(config).values:
                raise ValueError("Thread already exists; use resume or choose a new thread-id")
            inputs = {
                "run_id": args.thread_id,
                "docs": str(args.docs.resolve()),
                "code": str(args.code.resolve()),
                "template": str((args.template or settings.shared_data / "template.md").resolve()),
                "brief": args.brief,
                "status": "running",
            }
            graph.invoke(inputs, config)
        elif args.command == "resume":
            decision = json.loads(args.decisions.read_text("utf-8")) if args.decisions else None
            graph.invoke(Command(resume=decision) if decision is not None else None, config)
        elif args.command == "status":
            state = graph.get_state(config)
            result = {
                "state": state.values,
                "next": state.next,
                "interrupts": [item.value for task in state.tasks for item in task.interrupts],
            }
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
            state = graph.get_state(config)
            result = {
                "status": state.values.get("status"),
                "next": state.next,
                "interrupts": [item.value for task in state.tasks for item in task.interrupts],
                "run_path": str(store.root / "runs" / args.thread_id),
            }
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
