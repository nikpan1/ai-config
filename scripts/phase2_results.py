import argparse
from collections import Counter
from pathlib import Path

from docgen.budget import BudgetLedger
from docgen.config import Settings
from docgen.storage import Artifacts, read_json, read_jsonl, write_json


def event_metrics(store, thread):
    path = store.path(f"runs/{thread}/events.jsonl")
    events = list(read_jsonl(path)) if path.exists() else []
    responses = [event for event in events if event["event"] == "response"]
    requests = [event for event in events if event["event"] == "request"]
    return {
        "api_calls": len(responses),
        "cache_hits": sum(e["event"] == "cache_hit" for e in events),
        "request_attempts": len(requests),
        "technical_failures": sum(e["event"] == "technical_failure" for e in events),
        "model_latency_seconds": sum(e["seconds"] for e in responses),
        "stage_latency_seconds": sum(
            e.get("seconds", 0) for e in events if e["event"] == "stage_complete"
        ),
        "estimated_serialized_prompt_tokens": [e["estimated_input_tokens"] for e in requests],
        "provider_prompt_tokens": sum(e["usage"].get("prompt_token_count", 0) for e in responses),
        "provider_output_tokens": sum(
            e["usage"].get("candidates_token_count", 0) for e in responses
        ),
        "conservative_response_cost_pln": sum(e.get("charged_pln") or 0 for e in responses),
    }


def checkpoint_result(store, thread):
    from docgen.cli import run_config
    from docgen.planning import PlanningPipeline
    from docgen.reconciliation import comparison_count
    from docgen.workflow import Pipeline, persistent_graph

    metadata = store.get(f"runs/{thread}/workflow.json")
    workflow = metadata.get("workflow", "knowledge")
    pipeline_type = PlanningPipeline if workflow == "documentation_planning" else Pipeline
    with persistent_graph(pipeline_type(Settings(), store, None)) as graph:
        snapshot = graph.get_state(run_config(thread))
    state = snapshot.values
    progress = {}
    for prefix in ("entity", "claim"):
        ref = state.get(f"{prefix}_plan_ref")
        if ref:
            progress[prefix] = {
                "completed": state.get(f"{prefix}_index", 0),
                "total": comparison_count(store.get(ref)),
            }
    if state.get("work_ref"):
        progress["planning_work"] = {
            "stage": state.get("work_key"),
            "completed": state.get("work_index", 0),
            "total": store.get(state["work_ref"])["count"],
        }
    return {
        "thread_id": thread,
        "workflow": workflow,
        "status": state.get("status", "incomplete"),
        "next": list(snapshot.next),
        "checkpoint_id": snapshot.config["configurable"]["checkpoint_id"],
        "signature": state.get("signature"),
        "knowledge_ref": state.get("bundle_ref"),
        "issues": store.get(state["issues_ref"]) if state.get("issues_ref") else [],
        "progress": progress,
        "acceptance": "not_established",
        "execution_stop": store.get(f"runs/{thread}/wrap-up.json")
        if store.path(f"runs/{thread}/wrap-up.json").exists()
        else None,
        **event_metrics(store, thread),
    }


def summarize(store, thread):
    prefetch_path = store.path(f"runs/{thread}/prefetch.json")
    if prefetch_path.exists():
        metadata = read_json(prefetch_path)
        results_path = store.path(f"runs/{thread}/results.json")
        results = read_json(results_path) if results_path.exists() else []
        expected = metadata["stop"] - metadata["start"]
        cached = sum(row["status"] == "cached_not_accepted" for row in results)
        return {
            "thread_id": thread,
            "workflow": "evaluation_cache_prefetch",
            "status": "cached_not_accepted" if cached == expected else "incomplete",
            "metadata": metadata,
            "cached_responses": cached,
            "expected_responses": expected,
            "acceptance": "Normal pipeline validation remains required for every response",
            "execution_stop": store.get(f"runs/{thread}/wrap-up.json")
            if store.path(f"runs/{thread}/wrap-up.json").exists()
            else None,
            **event_metrics(store, thread),
        }
    exports = sorted(store.path(f"runs/{thread}/documentation-plan").glob("*/manifest.json"))
    if not exports:
        return checkpoint_result(store, thread)
    manifest_path = exports[-1]
    manifest = read_json(manifest_path)
    plan = store.get(manifest["plan_ref"])
    components = plan["components"]
    inputs = store.get(plan["inputs_ref"])
    report = store.get(components["validation-report"])
    obligations = list(store.iter_table(components["content-obligations"]))
    units = list(store.iter_table(components["documentation-units"]))
    pages = list(store.iter_table(components["pages"]))
    audits = list(store.iter_table(components["semantic-audit"]))
    snapshot = store.get(inputs["snapshot_ref"])
    from docgen.ingestion import estimate_tokens

    return {
        "thread_id": thread,
        "status": manifest["status"],
        "plan_ref": manifest["plan_ref"],
        "manifest": str(manifest_path),
        "signature": plan["signature"],
        "knowledge_revision": inputs["knowledge_revision"],
        "template_hash": inputs["template_hash"],
        "unit_policy": plan["unit_policy"],
        "delivery_mode": plan["delivery_mode"],
        "source_estimated_tokens": sum(estimate_tokens(b["content"]) for b in snapshot["blocks"]),
        "obligation_kinds": dict(Counter(o["record_kind"] for o in obligations)),
        "coverage": report,
        "unit_boundaries": [
            {
                k: u[k]
                for k in ("id", "title", "purpose", "scope", "boundaries", "discovery_rationale")
            }
            for u in units
        ],
        "pages_by_role": dict(Counter(p["role"] for p in pages)),
        "pages": [
            {k: p[k] for k in ("id", "path", "role", "reader_task", "rationale")} for p in pages
        ],
        **event_metrics(store, thread),
        "auditor_reported_blocking_findings": sum(len(a["findings"]) for a in audits),
        "reader_task_observations": [
            {
                "brief_id": a["brief_id"],
                "section_ids": a["checked_section_ids"],
                "observations": a["reader_task_findings"],
            }
            for a in audits
        ],
        "manual_review": "not_performed",
        "held_out": False,
        "limitations": [
            "Model judgments are not proof of completeness or zero unsupported content",
            "Obligation coverage measures planning of finalized knowledge, not extraction recall",
            "The fixture and its labels are autonomous and not user-approved",
            "Two-million-token end-to-end capacity remains unvalidated",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("threads", nargs="+")
    parser.add_argument("--output", default="evaluation/phase2-results.json")
    args = parser.parse_args()
    settings = Settings()
    store = Artifacts(settings.workspace)
    output = {
        "runs": [summarize(store, thread) for thread in args.threads],
        "cumulative_budget": BudgetLedger(settings.budget_ledger).summary(),
    }
    write_json(Path(args.output), output)
    print(
        {"runs": len(output["runs"]), "output": args.output, "budget": output["cumulative_budget"]}
    )
