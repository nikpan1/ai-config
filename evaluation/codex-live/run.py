import argparse
import json
import sqlite3
from contextlib import closing
from dataclasses import replace
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from docgen_graph.config import Settings
from docgen_graph.model import GeminiModel
from docgen_graph.storage import ArtifactStore
from docgen_graph.workflow import Pipeline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--configuration", type=Path, required=True)
    parser.add_argument("--thread-id", required=True)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    configuration = json.loads(args.configuration.read_text("utf-8"))
    overrides = configuration["settings"]
    for name in ("workspace", "code_scope_file", "code_provider_allowance_file"):
        if overrides.get(name):
            overrides[name] = Path(overrides[name]).resolve()
    settings = replace(Settings.load(args.env_file), **overrides)
    store = ArtifactStore(settings.workspace)
    with closing(
        sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)
    ) as conn:
        pipeline = Pipeline(store, GeminiModel(settings, store, args.thread_id), args.thread_id)
        graph = pipeline.build(SqliteSaver(conn))
        graph_config = {"configurable": {"thread_id": args.thread_id}, "recursion_limit": 1000}
        state = graph.get_state(graph_config)
        error = None
        if not args.status:
            inputs = (
                None
                if state.values
                else {
                    "run_id": args.thread_id,
                    "docs": configuration["docs"],
                    "code": configuration["code"],
                    "template": configuration["template"],
                    "brief": configuration["brief"],
                    "mode": "autopilot",
                    "policy_version": "v2",
                    "status": "running",
                }
            )
            try:
                for update in graph.stream(inputs, graph_config, stream_mode="updates"):
                    print(json.dumps({"completed_nodes": list(update)}), flush=True)
            except Exception as failure:
                error = {"type": type(failure).__name__, "message": str(failure)}
                for secret in (settings.api_key, settings.code_analysis_api_key):
                    if secret:
                        error["message"] = error["message"].replace(secret, "[redacted]")
        state = graph.get_state(graph_config)
        result = {
            "run_id": args.thread_id,
            "status": state.values.get("status"),
            "next": state.next,
            "error": error,
            "run_directory": str(store.root / "runs" / args.thread_id),
            "checkpoint_id": state.config.get("configurable", {}).get("checkpoint_id"),
            "state": state.values,
            "interrupts": [item.value for task in state.tasks for item in task.interrupts],
        }
        path = store.write(f"runs/{args.thread_id}/live-result.json", json.dumps(result, indent=2))
        print(json.dumps({k: v for k, v in result.items() if k != "state"}, default=str))
        print(json.dumps({"result_path": str(path)}))
        return 1 if error else 0


if __name__ == "__main__":
    raise SystemExit(main())
