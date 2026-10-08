import os
from pathlib import Path
from time import monotonic

from docgen.batching import plan_batches
from docgen.budget import BudgetLedger, load_pricing
from docgen.ingestion import estimate_tokens, snapshot_sources
from docgen.planning_inputs import resolve_reference, validate_knowledge
from docgen.reconciliation import comparison_tasks


def workload_report(settings, store, source=None, knowledge=None, selection=None):
    started = monotonic()
    bundle = None
    if knowledge:
        _, bundle = resolve_reference(knowledge, store, "bundle_ref", "complete")
        snapshot = validate_knowledge(bundle, store)
    elif source:
        snapshot = snapshot_sources(
            Path(source), store, min(2000, settings.batch_tokens), selection
        )
    else:
        raise ValueError("Workload report requires --source or --knowledge")
    batches = plan_batches(snapshot, settings)
    record_counts, stages, largest = {}, {}, {}
    stages["extraction_and_verification"] = 2 * len(batches)
    if bundle:
        names = {row["id"]: row["canonical_name"] for row in bundle["entities"]}
        for kind in ("entities", "claims"):
            records = bundle[kind]
            record_counts[kind] = len(records)
            comparisons = comparison_tasks(
                records, kind, settings.reconciliation_tokens, names, settings.workload_tasks
            )
            stages[f"reconcile_{kind}"] = len(comparisons["tasks"])
            largest[kind] = comparisons["largest_groups"]
    cost_bound = None
    try:
        pricing = load_pricing(settings.pricing_file)
        cost_bound = sum(stages.values()) * pricing.cost(settings.request_tokens * 3 + 4096, 65536)
        cost_bound *= settings.billing_headroom
    except (OSError, ValueError):
        pass
    disk = sum(path.stat().st_size for path in store.root.rglob("*") if path.is_file())
    return {
        "schema_version": "1",
        "source_files": len(snapshot["inventory"]),
        "source_bytes": sum(row.get("bytes", 0) for row in snapshot["inventory"]),
        "estimated_source_tokens": sum(
            estimate_tokens(row["content"]) for row in snapshot["blocks"]
        ),
        "token_estimate_method": "UTF-8 bytes divided by three; not tokenizer-counted",
        "blocks": len(snapshot["blocks"]),
        "batches": len(batches),
        "records": record_counts,
        "stage_call_estimates": stages,
        "largest_groups": largest,
        "request_tokens": settings.request_tokens,
        "planning_tokens": settings.planning_tokens,
        "output_tokens": settings.output_tokens,
        "task_allowance": settings.workload_tasks,
        "conservative_stage_reservation_bound_pln": cost_bound,
        "budget": BudgetLedger(settings.budget_ledger, settings.budget_pln).summary(),
        "workspace_bytes": disk,
        "cpu_count": os.cpu_count(),
        "elapsed_seconds": monotonic() - started,
        "limitations": [
            "Comparison counts before extraction are unknown",
            "Planning calls, retries and repairs add to these stage totals",
            "Reservation bound is not an expected invoice or a complete-run forecast",
            "Read-only with respect to runs; derived snapshots and indexes may be cached",
            "Two-million-token end-to-end capacity is unvalidated",
        ],
    }
