import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from docgen_graph.storage import ArtifactStore, atomic_write


def read_database(path):
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)


def graph_records(path):
    with read_database(path) as connection:
        connection.row_factory = sqlite3.Row
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master")}
        result = {
            "node_types": dict(
                connection.execute("SELECT type, COUNT(*) FROM nodes GROUP BY type")
            ),
            "edge_types": dict(
                connection.execute("SELECT type, COUNT(*) FROM edges GROUP BY type")
            ),
            "assertions": [dict(row) for row in connection.execute("SELECT * FROM assertions")],
            "source_count": connection.execute("SELECT COUNT(*) FROM evidence").fetchone()[0],
        }
        for table in ("semantic_nodes", "semantic_edges"):
            result[table] = (
                [json.loads(row[0]) for row in connection.execute(f"SELECT payload FROM {table}")]
                if table in tables
                else []
            )
    return result


def inspect_run(workspace, run_id, ledger):
    store = ArtifactStore(workspace)
    root = workspace / "runs" / run_id
    events = [json.loads(line) for line in (root / "events.jsonl").read_text("utf-8").splitlines()]
    counts = Counter(event["event"] for event in events)
    stages = defaultdict(lambda: {"requests": 0, "responses": 0, "response_seconds_sum": 0.0})
    intervals = []
    for event in events:
        stage = stages[event["stage"]]
        if event["event"] == "request":
            stage["requests"] += 1
        if event["event"] == "response":
            stage["responses"] += 1
            seconds = event.get("seconds", 0.0)
            stage["response_seconds_sum"] += seconds
            intervals.append((event["time"] - seconds, event["time"]))
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start, end])
    with read_database(workspace / "checkpoints.sqlite") as connection:
        checkpoint = SqliteSaver(connection).get_tuple({"configurable": {"thread_id": run_id}})
        state = checkpoint.checkpoint["channel_values"]
    with read_database(ledger) as connection:
        charges = [
            {"status": status, "entries": entries, "charged_pln": charged}
            for status, entries, charged in connection.execute(
                "SELECT status,COUNT(*),SUM(charged) FROM charges WHERE run_id=? GROUP BY status",
                (run_id,),
            )
        ]
    artifacts = {}
    for key, value in state.items():
        if key.endswith("_ref") and isinstance(value, str) and len(value) == 64:
            try:
                record = store.get(value)
            except (OSError, ValueError):
                continue
            if any(
                term in key
                for term in ("audit", "quality", "coverage", "limitation", "source_first")
            ):
                artifacts[key] = record
    return {
        "schema_version": 1,
        "run_id": run_id,
        "workspace": str(workspace.resolve()),
        "status": state.get("status"),
        "state_references": {key: value for key, value in state.items() if key.endswith("_ref")},
        "recorded_event_window_seconds": events[-1]["time"] - events[0]["time"],
        "model_response_wall_union_seconds": sum(end - start for start, end in merged),
        "event_counts": dict(counts),
        "stage_metrics": dict(stages),
        "quality_artifacts": artifacts,
        "ledger": charges,
        "graph": graph_records(root / "graph.sqlite"),
        "limitations": [
            "Node counts and successful audits are not semantic accuracy measurements.",
            "The recorded event window excludes process startup and shutdown.",
            "Model response sums can include concurrent requests.",
            "Coordinator interventions must be supplied from the execution record, not inferred.",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = inspect_run(args.workspace, args.run_id, args.ledger)
    atomic_write(args.output, json.dumps(report, indent=2, ensure_ascii=False).encode())
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "run_id",
                    "status",
                    "recorded_event_window_seconds",
                    "event_counts",
                    "ledger",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
