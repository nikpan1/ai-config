import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

from docgen.cli import run_config, status_payload
from docgen.config import Settings
from docgen.generation import GenerationPipeline
from docgen.storage import Artifacts, read_json, read_jsonl, write_json
from docgen.workflow import persistent_graph


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--thread-id", required=True)
    parser.add_argument("--output", default="evaluation/phase3-results.json")
    args = parser.parse_args()
    settings = Settings()
    store = Artifacts(settings.workspace)
    with persistent_graph(GenerationPipeline(settings, store, None)) as graph:
        snapshot = graph.get_state(run_config(args.thread_id))
        state = snapshot.values
        history = sum(1 for _ in graph.get_state_history(run_config(args.thread_id)))
    events = list(read_jsonl(store.path(f"runs/{args.thread_id}/events.jsonl")))
    responses = [e for e in events if e.get("event") == "response"]
    with sqlite3.connect(settings.budget_ledger) as connection:
        charged, reserved = connection.execute(
            "SELECT COALESCE(SUM(charged),0), "
            "COALESCE(SUM(CASE WHEN status='reserved' THEN reserved ELSE 0 END),0) "
            "FROM charges WHERE run_id=?",
            (args.thread_id,),
        ).fetchone()
    result = {
        "thread_id": args.thread_id,
        "status": state.get("status"),
        "cache_mode": state.get("cache_mode"),
        "completed_writing_jobs": state.get("job_index", 0),
        "checkpoint_count": history,
        "paid_responses": len(responses),
        "charged_pln_with_headroom": charged,
        "reserved_pln": reserved,
        "model_seconds": sum(e["seconds"] for e in responses),
        "elapsed_event_seconds": (
            datetime.fromisoformat(events[-1]["time"]) - datetime.fromisoformat(events[0]["time"])
        ).total_seconds(),
        "input_tokens": sum(e["usage"].get("prompt_token_count", 0) or 0 for e in responses),
        "output_tokens": sum(
            (e["usage"].get("candidates_token_count", 0) or 0)
            + (e["usage"].get("thoughts_token_count", 0) or 0)
            for e in responses
        ),
        "human_acceptance": "recorded" if state.get("release_approval_ref") else "not_performed",
        "open_issues": store.get_object(state["issues_ref"]) if state.get("issues_ref") else [],
        "formal_ste_compliance": "not_claimed; user-authorized plain technical English",
        "live_medium_multi_unit_acceptance": "not_run",
        "large_corpus_acceptance": "not_run",
        "snapshot": status_payload(snapshot),
    }
    result["semantic_acceptance"] = (
        "needs_correction"
        if state.get("status") == "awaiting_review"
        else "human_accepted"
        if state.get("status") == "complete"
        else "not_accepted"
    )
    if state.get("manifest_path"):
        result["manifest"] = read_json(Path(state["manifest_path"]))
    for key in ("validation_ref", "presentation_ref"):
        if state.get(key):
            result[key.removesuffix("_ref")] = store.get_object(state[key])
    write_json(Path(args.output), result)
    write_json(store.path(f"runs/{args.thread_id}/generation-metrics.json"), result)
    print(
        {
            key: value
            for key, value in result.items()
            if key not in {"snapshot", "manifest", "validation", "presentation", "open_issues"}
        }
    )


if __name__ == "__main__":
    main()
