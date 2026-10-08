import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--implementation", required=True)
    parser.add_argument("--thread-id", required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--stop", type=int, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(args.implementation).resolve()))

    from docgen.budget import BudgetExceeded
    from docgen.cli import run_config, runtime_signature
    from docgen.config import Settings
    from docgen.contracts import Comparison
    from docgen.model import GeminiModel
    from docgen.reconciliation import comparison_at, comparison_count
    from docgen.storage import Artifacts, configure_logging, digest, write_json
    from docgen.workflow import Pipeline, persistent_graph

    settings = Settings()
    store = Artifacts(settings.workspace)
    with persistent_graph(Pipeline(settings, store, None)) as graph:
        snapshot = graph.get_state(run_config(args.thread_id))
    state = snapshot.values
    if Path(state["source"]).resolve() != Path(".docgen/phase2-medium-source").resolve():
        raise ValueError("Prefetch applies only to the authored evaluation fixture")
    if state["signature"] != runtime_signature(settings):
        raise ValueError("Use the matching immutable implementation")
    plan = store.get(state["claim_plan_ref"])
    if not state.get("claim_index", 0) + 30 <= args.start < args.stop <= comparison_count(plan):
        raise ValueError("Prefetch must target a bounded future range with a 30-task lead")
    run_id = f"{args.thread_id}-prefetch-{args.start}-{args.stop}"
    store.path(f"runs/{run_id}").mkdir(parents=True, exist_ok=False)
    write_json(
        store.path(f"runs/{run_id}/prefetch.json"),
        {
            "parent_thread": args.thread_id,
            "checkpoint": snapshot.config["configurable"]["checkpoint_id"],
            "plan_ref": state["claim_plan_ref"],
            "signature": state["signature"],
            "start": args.start,
            "stop": args.stop,
            "concurrency": 3,
            "acceptance": "Responses require the normal sequential pipeline validation",
        },
    )
    configure_logging()

    def prepare(index):
        task = comparison_at(plan, index, store)
        lookup = {
            row["id"]: row
            for row in store.table_rows(state["records_ref"], task["left"] + task["right"])
        }
        payload = {
            "group": task["group"],
            "revision": digest(lookup),
            "left": [lookup[key] for key in task["left"]],
            "right": [lookup[key] for key in task["right"]],
            "source_blocks": store.table_rows(
                state["blocks_ref"],
                sorted({e["block_id"] for row in lookup.values() for e in row["evidence"]}),
            ),
        }
        GeminiModel(settings, store, run_id).call("claims", payload, Comparison)
        return {"index": index, "task_id": task["id"], "status": "cached_not_accepted"}

    results = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(prepare, index): index for index in range(args.start, args.stop)}
        for future in as_completed(futures):
            try:
                result = future.result()
            except BudgetExceeded:
                for pending in futures:
                    pending.cancel()
                raise
            except Exception as error:
                result = {
                    "index": futures[future],
                    "status": "pipeline_retry_required",
                    "error_type": type(error).__name__,
                }
            results.append(result)
            write_json(store.path(f"runs/{run_id}/results.json"), results)
            print(result, flush=True)


if __name__ == "__main__":
    main()
