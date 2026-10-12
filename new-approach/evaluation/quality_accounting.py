import argparse
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

from docgen_graph.config import Settings


def aggregate(rows: list[dict]) -> dict:
    statuses = defaultdict(int)
    input_tokens = output_tokens = missing_usage = 0
    for row in rows:
        statuses[row["status"]] += 1
        usage = json.loads(row["usage"])
        usage = usage.get("usage", usage) or {}
        if "input_tokens" in usage and "output_tokens" in usage:
            input_tokens += usage["input_tokens"]
            output_tokens += usage["output_tokens"]
        else:
            missing_usage += 1
    return {
        "requests": len(rows),
        "statuses": dict(statuses),
        "charged_pln": sum(row["charged"] for row in rows),
        "reserved_pln": sum(row["reserved"] for row in rows if row["status"] == "reserved"),
        "known_input_tokens": input_tokens,
        "known_output_tokens": output_tokens,
        "requests_without_token_usage": missing_usage,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-prefix", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with sqlite3.connect(Settings.load().budget_ledger) as connection:
        connection.row_factory = sqlite3.Row
        all_rows = [dict(row) for row in connection.execute("SELECT * FROM charges")]
    rows = [
        row for row in all_rows if any(row["run_id"].startswith(p) for p in args.run_prefix)
    ]
    by_run = defaultdict(list)
    for row in rows:
        by_run[row["run_id"]].append(row)
    runs = {}
    for run_id, charges in sorted(by_run.items()):
        stages = defaultdict(list)
        for row in charges:
            stages[row["stage"]].append(row)
        runs[run_id] = {
            **aggregate(charges),
            "stages": {stage: aggregate(items) for stage, items in sorted(stages.items())},
        }
    result = {
        "method": (
            "Read-only shared-ledger accounting, including failed and interrupted requests. "
            "Uncertain charges retain their full reservation; known tokens are a lower bound "
            "when requests_without_token_usage is nonzero."
        ),
        "selected_prefixes": args.run_prefix,
        "total": aggregate(rows),
        "runs": runs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["total"], indent=2))


if __name__ == "__main__":
    main()
