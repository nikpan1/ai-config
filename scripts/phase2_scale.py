import argparse
import ctypes
import sys
from pathlib import Path
from time import monotonic
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from conftest import FixtureModel
from planning_fixtures import PlanningFixtureModel, planning_state, run_plan

from docgen.batching import plan_batches
from docgen.config import Settings
from docgen.ingestion import estimate_tokens, snapshot_sources
from docgen.model import ModelFailure, prompt_text
from docgen.reconciliation import comparison_tasks
from docgen.storage import Artifacts, atomic_write, encode, write_json
from docgen.workflow import Pipeline, persistent_graph


class MeasuredFixtureModel:
    def __init__(self, delegate, settings):
        self.delegate = delegate
        self.settings = settings
        self.calls = delegate.calls
        self.max_input_tokens = 0
        self.oversized_requests = 0

    def call(self, stage, payload, schema):
        tokens = estimate_tokens(
            prompt_text(stage) + encode(payload) + encode(schema.model_json_schema())
        )
        self.max_input_tokens = max(self.max_input_tokens, tokens)
        if tokens + self.settings.output_tokens > self.settings.request_tokens:
            self.oversized_requests += 1
        return self.delegate.call(stage, payload, schema)


def peak_memory_bytes():
    if sys.platform != "win32":
        import resource

        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024

    class MemoryCounters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("faults", ctypes.c_ulong)] + [
            (name, ctypes.c_size_t)
            for name in (
                "peak_working_set",
                "working_set",
                "peak_paged_pool",
                "paged_pool",
                "peak_nonpaged_pool",
                "nonpaged_pool",
                "pagefile",
                "peak_pagefile",
            )
        ]

    counters = MemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.windll.kernel32
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    read = ctypes.windll.psapi.GetProcessMemoryInfo
    read.argtypes = [ctypes.c_void_p, ctypes.POINTER(MemoryCounters), ctypes.c_ulong]
    if not read(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise OSError("Process memory observation failed")
    return counters.peak_working_set


def source_text(target):
    chunks, estimated, index = [], 0, 0
    while estimated < target:
        area = "Archive" if index % 2 == 0 else "Delivery"
        number = index // 2
        text = (
            f"{area} profile P-{index:06} in tenant T-{number % 17}, version {1 + number % 3}, "
            f"requires rule R-{index:06}. The action requires approval "
            f"after {number % 31 + 1} days, "
            f"unless legal hold H-{number % 13} applies. Preserve the original request key and "
            f"revision V-{number:06} after failure. Customer C-{number % 101} and the shared audit "
            f"service are context, not permission to merge tenant or version scopes. "
            f"The related rule R-{max(0, index - 100):06} is an explicit distant dependency. "
            f"The retry limit is {number % 5 + 1}; the time is {number % 24:02}:00 UTC. "
            f"The role Role-{number % 7} may inspect only this profile, and the returned status "
            f"is State-{number % 11}. Missing downstream recovery behavior remains unknown.\n\n"
        )
        chunks.append(text)
        estimated += estimate_tokens(text)
        index += 1
    return "".join(chunks)


def run(target, full):
    root = Path(f".docgen/phase2-scale-{target}") / uuid4().hex[:12]
    root.mkdir(parents=True, exist_ok=True)
    source = root / "source.md"
    text = source_text(target)
    atomic_write(source, text)
    store = Artifacts(root / "artifacts")
    settings = Settings(
        _env_file=None,
        DOCGEN_WORKSPACE=store.root,
        DOCGEN_BUDGET_LEDGER=Path(".docgen/budget.sqlite"),
    )
    started = monotonic()
    snapshot = snapshot_sources(source, store)
    batches = plan_batches(snapshot, settings)
    records = [
        {
            "id": f"c-{index}",
            "statement": block["content"],
            "entities": ["shared-hub"],
            "scope": "shared-scope",
            "rule_keys": [f"r-{index % 17}"],
        }
        for index, block in enumerate(snapshot["blocks"])
    ]
    report = {
        "target": target,
        "actual_source_estimate": estimate_tokens(text),
        "token_method": "UTF-8 byte heuristic",
        "blocks": len(snapshot["blocks"]),
        "batches": len(batches),
        "resource_budgets": {
            "max_tasks": settings.workload_tasks,
            "peak_rss_bytes": 1_500_000_000,
            "artifact_bytes": 10_000_000_000,
        },
        "semantic_validation": "not_performed",
        "model": "deterministic_structural_stub",
        "full_orchestration_requested": full,
    }
    try:
        plan = comparison_tasks(
            records, "claims", settings.reconciliation_tokens, task_limit=settings.workload_tasks
        )
        report.update(comparison_tasks=len(plan["tasks"]), largest_groups=plan["largest_groups"])
    except ModelFailure as error:
        report.update(workload_incomplete=True, stop_reason=str(error))
    if full and not report.get("workload_incomplete"):
        model = MeasuredFixtureModel(FixtureModel(), settings)
        with persistent_graph(Pipeline(settings, store, model)) as graph:
            config = {"configurable": {"thread_id": "knowledge"}, "recursion_limit": 100000}
            try:
                result = graph.invoke(
                    {
                        "run_id": "knowledge",
                        "source": str(source.resolve()),
                        "signature": "structural-stub",
                    },
                    config,
                )
            except ModelFailure as error:
                snapshot = graph.get_state(config)
                result = snapshot.values
                report.update(
                    workload_incomplete=True,
                    stop_reason=str(error),
                    pending_stages=list(snapshot.next),
                    checkpoint_id=snapshot.config["configurable"]["checkpoint_id"],
                )
        report["knowledge_status"] = result.get("status", "incomplete")
        report["knowledge_calls"] = len(model.calls)
        report["knowledge_max_serialized_input_tokens"] = model.max_input_tokens
        report["oversized_requests"] = model.oversized_requests
        if result.get("status") == "complete":
            planning_model = MeasuredFixtureModel(PlanningFixtureModel(), settings)
            result, pipeline, planning_model = run_plan(
                planning_state(root, result["bundle_ref"]), settings, store, planning_model
            )
            report["planning_status"] = result["status"]
            report["planning_calls"] = len(planning_model.calls)
            report["planning_max_serialized_input_tokens"] = planning_model.max_input_tokens
            report["oversized_requests"] += planning_model.oversized_requests
            if result["status"] == "ready_for_generation":
                report["validation"] = pipeline.component(result, "validation-report")
    report["elapsed_seconds"] = monotonic() - started
    report["peak_rss_bytes"] = peak_memory_bytes()
    report["artifact_bytes"] = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
    report["resource_checks"] = {
        key: report[key] <= report["resource_budgets"][key]
        for key in ("peak_rss_bytes", "artifact_bytes")
    }
    if not all(report["resource_checks"].values()) or report.get("oversized_requests", 0):
        report["workload_incomplete"] = True
        report["stop_reason"] = "Measured resources exceed the predeclared acceptance budget"
    report["capacity_claim"] = "Unvalidated; structural workload and stub measurements only"
    write_json(Path(f"evaluation/phase2-scale-{target}.json"), report)
    print({k: v for k, v in report.items() if k not in {"validation", "largest_groups"}})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tokens", type=int, required=True)
    parser.add_argument("--full-stub", action="store_true")
    args = parser.parse_args()
    run(args.tokens, args.full_stub)
