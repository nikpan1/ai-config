import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from docgen.budget import BudgetLedger
from docgen.config import Settings
from docgen.storage import Artifacts, read_jsonl, write_json


def run_metrics(store, run_id):
    events_path = store.path(f"runs/{run_id}/events.jsonl")
    if not events_path.exists():
        raise ValueError(f"No event log for run {run_id}")
    events = list(read_jsonl(events_path))
    if not events:
        raise ValueError(f"Empty event log for run {run_id}")
    stages = defaultdict(lambda: defaultdict(float))
    questions = set()
    review_started = None
    review_wait = 0.0
    operator_actions = 0
    for event in events:
        stage = stages[event["stage"]]
        kind = event["event"]
        if kind == "request":
            stage["paid_requests"] += 1
            stage["retries"] += event.get("attempt", 1) > 1
            stage["estimated_input_tokens"] += event.get("estimated_input_tokens", 0)
        elif kind == "response":
            usage = event.get("usage", {})
            stage["model_seconds"] += event.get("seconds", 0)
            stage["charged_pln"] += event.get("charged_pln") or 0
            stage["input_tokens"] += usage.get("prompt_token_count") or 0
            stage["output_tokens"] += (usage.get("candidates_token_count") or 0) + (
                usage.get("thoughts_token_count") or 0
            )
        elif kind == "stage_complete":
            stage["completed_nodes"] += 1
            stage["node_seconds"] += event.get("seconds", 0)
            outputs = event.get("outputs", {})
            if outputs.get("route") in {"review_issues", "review_plan", "review_generation"}:
                review_started = datetime.fromisoformat(event["time"])
                if outputs.get("issues_ref"):
                    questions.update(issue["id"] for issue in store.get(outputs["issues_ref"]))
            if event["stage"] in {"review_issues", "review_plan", "review_generation"}:
                operator_actions += 1
                if review_started:
                    review_wait += (
                        datetime.fromisoformat(event["time"]) - review_started
                    ).total_seconds()
                    review_started = None
        elif kind in {"cache_hit", "token_preflight_cache_hit"}:
            stage[kind] += 1
        elif kind == "token_preflight":
            stage["preflight_seconds"] += event.get("seconds", 0)
        elif kind == "technical_failure":
            stage["technical_failures"] += 1
    first = datetime.fromisoformat(events[0]["time"])
    last = datetime.fromisoformat(events[-1]["time"])
    active = sum(stage["node_seconds"] for stage in stages.values())
    run_root = store.path(f"runs/{run_id}")
    return {
        "run_id": run_id,
        "status": next(
            (
                event.get("outputs", {}).get("status")
                for event in reversed(events)
                if event["event"] == "stage_complete" and event.get("outputs", {}).get("status")
            ),
            "unknown",
        ),
        "wall_seconds": (last - first).total_seconds(),
        "active_node_seconds": active,
        "measured_review_wait_seconds": review_wait,
        "review_sessions": operator_actions,
        "unique_questions": len(questions),
        "artifact_bytes": sum(
            path.stat().st_size for path in run_root.rglob("*") if path.is_file()
        ),
        "stages": {key: dict(value) for key, value in sorted(stages.items())},
        "limitations": [
            "Node time includes model latency and file I/O; subtotals are not additive",
            "Older runs did not record token preflight latency",
            "Review waiting is measured only for completed review sessions",
            "Peak memory and semantic quality require separate evaluation",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_ids", nargs="+")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    settings = Settings()
    store = Artifacts(settings.workspace)
    report = {
        "schema_version": "1",
        "runs": [run_metrics(store, run_id) for run_id in args.run_ids],
        "shared_budget": BudgetLedger(settings.budget_ledger, settings.budget_pln).summary(),
    }
    if args.output:
        write_json(args.output, report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
