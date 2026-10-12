import argparse
import json
import re
import shutil
import sqlite3
import sys
from collections import defaultdict
from contextlib import closing
from pathlib import Path
from time import monotonic


def summarize(store, run_id, state, ledger):
    from docgen_graph.source_links import CITATION_GROUP

    directory = store.root / "runs" / run_id
    events = [
        json.loads(line) for line in (directory / "events.jsonl").read_text("utf-8").splitlines()
    ]
    stages = defaultdict(
        lambda: {
            "paid_calls": 0,
            "cache_hits": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "response_seconds": 0.0,
            "node_seconds": 0.0,
            "retries": 0,
            "repairs": 0,
        }
    )
    for event in events:
        metrics = stages[event["stage"]]
        if event["event"] == "request":
            metrics["paid_calls"] += 1
            metrics["retries"] += int(event.get("attempt", 1) > 1)
        elif event["event"] == "response":
            metrics["response_seconds"] += event["seconds"]
            for key in ("input_tokens", "output_tokens"):
                metrics[key] += event["usage"][key]
        elif event["event"] == "completed":
            metrics["node_seconds"] += event["seconds"]
            metrics["repairs"] += int(event.get("repair", False))
        elif event["event"] == "cache_hit":
            metrics["cache_hits"] += 1
    with sqlite3.connect(ledger) as connection:
        charged, reserved = connection.execute(
            "SELECT COALESCE(SUM(charged),0), COALESCE(SUM(CASE WHEN status='reserved' "
            "THEN reserved ELSE 0 END),0) FROM charges WHERE run_id=?",
            (run_id,),
        ).fetchone()
    result = {
        "run_id": run_id,
        "status": state.get("status"),
        "stages": dict(stages),
        "paid_calls": sum(item["paid_calls"] for item in stages.values()),
        "charged_pln": charged,
        "reserved_pln": reserved,
        "active_node_seconds": sum(item["node_seconds"] for item in stages.values()),
        "human_reader_scores": "Unmeasured",
    }
    if state.get("candidate_ref"):
        candidate = directory / "candidates" / state["candidate_ref"]
        markdown = (candidate / "documentation" / "index.md").read_text("utf-8")
        text = re.sub(r"\]\((?:<[^>\n]*>|[^)\n]*)\)", "]", markdown)
        text = CITATION_GROUP.sub("", text)
        result.update(
            candidate=str(candidate),
            candidate_hash=state["candidate_ref"],
            reader_words=len(re.sub(r"[#*`>|]", " ", text).split()),
            markdown_characters=len(markdown),
            images=markdown.count("!["),
            diagrams=markdown.count("```mermaid"),
        )
        result["audit"] = json.loads((directory / "audit.json").read_text("utf-8"))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--thread-id", required=True)
    parser.add_argument("--docs", type=Path)
    parser.add_argument("--template", type=Path)
    parser.add_argument("--approve-plan", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--baseline-source", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.baseline_source:
        sys.path.insert(0, str(args.baseline_source.resolve()))
    from dataclasses import replace

    from dotenv import dotenv_values
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.types import Command

    from docgen_graph.config import Settings
    from docgen_graph.model import GeminiModel
    from docgen_graph.storage import ArtifactStore, digest
    from docgen_graph.workflow import Pipeline

    root = Path(__file__).resolve().parents[2]
    settings = Settings.load(root / "new-approach" / ".env")
    key = settings.api_key or str(dotenv_values(root / ".env").get("GEMINI_API_KEY") or "")
    settings = replace(settings, api_key=key)
    store = ArtifactStore(settings.workspace)
    with closing(
        sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)
    ) as connection:
        pipeline = Pipeline(store, GeminiModel(settings, store, args.thread_id), args.thread_id)
        graph = pipeline.build(SqliteSaver(connection))
        config = {"configurable": {"thread_id": args.thread_id}, "recursion_limit": 100000}
        state = graph.get_state(config)
        started = monotonic()
        if not args.status:
            if state.values:
                if not state.tasks or not any(task.interrupts for task in state.tasks):
                    graph.invoke(None, config)
            else:
                if not args.docs or not args.template:
                    parser.error("A new run requires --docs and --template")
                graph.invoke(
                    {
                        "run_id": args.thread_id,
                        "docs": str(args.docs.resolve()),
                        "template": str(args.template.resolve()),
                        "code": "",
                        "brief": (
                            "Produce concise source-backed documentation with canonical ownership, "
                            "explicit scoped differences, relevant source illustrations "
                            "and only supported flows."
                        ),
                        "status": "running",
                    },
                    config,
                )
            state = graph.get_state(config)
            if args.approve_plan and state.values.get("status") == "awaiting_plan_review":
                plan = store.get(state.values["plan_ref"])
                graph.invoke(
                    Command(
                        resume={
                            "action": "approve_plan",
                            "plan_hash": state.values["plan_hash"],
                            "reviewer": "Codex autonomous evaluation",
                            "rationale": (
                                "Development evaluation authorized by the user; retain all scoped "
                                "evidence and reviewed template gaps. This is not independent "
                                "human acceptance or release approval."
                            ),
                            "conflict_decisions": {
                                f"{item['code_id']}:{item['document_id']}": "present_both"
                                for item in plan["conflict_candidates"]
                            },
                            "discrepancy_decisions": {
                                digest(item)[:16]: "present_both" for item in plan["discrepancies"]
                            },
                        }
                    ),
                    config,
                )
            state = graph.get_state(config)
        result = summarize(store, args.thread_id, state.values, settings.budget_ledger)
        result["invocation_seconds"] = monotonic() - started
        result["interrupts"] = [item.value for task in state.tasks for item in task.interrupts]
        result["configuration"] = {
            "model": settings.model,
            "output_tokens": settings.output_tokens,
            "request_tokens": settings.request_tokens,
            "timeout_seconds": settings.timeout_seconds,
            "cache_mode": "durable",
            "budget_pln": settings.budget_pln,
        }
        if state.values.get("candidate_ref") and not args.baseline_source:
            from docgen_graph.assets import verify_bundle

            copied = (
                store.root / "portable-evaluation" / args.thread_id / state.values["candidate_ref"]
            )
            if not copied.exists():
                shutil.copytree(result["candidate"], copied)
            verify_bundle(
                copied, json.loads((copied / "candidate-manifest.json").read_text("utf-8"))
            )
            result["portable_copy_verified"] = True
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(
            json.dumps({key: value for key, value in result.items() if key != "stages"}, indent=2)
        )


if __name__ == "__main__":
    main()
