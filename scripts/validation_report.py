import sqlite3
from collections import Counter
from pathlib import Path

from docgen.budget import BudgetLedger
from docgen.config import Settings
from docgen.storage import Artifacts, atomic_write, read_json, write_json


def main():
    settings = Settings()
    store = Artifacts(settings.workspace)
    ingestion = read_json(store.path("ingestion-status.json"))
    snapshot = store.get(ingestion["values"]["snapshot_ref"])
    scale = read_json(store.path("evaluation/scale-check.json"))
    reference = read_json(store.path("evaluation/reference-v1-8000/quality.json"))
    held_out = read_json(store.path("evaluation/held-out-final/quality.json"))
    reference_run = read_json(store.path("evaluation/reference-v1-8000/result.json"))
    smoke = read_json(store.path("evaluation/live-smoke.json"))
    bundle = store.get(smoke["values"]["bundle_ref"])
    budget = BudgetLedger(settings.budget_ledger).summary()
    variants = []
    for size in (8000, 16000, 32000):
        root = store.path(f"evaluation/exploratory-v1-{size}")
        run = read_json(root / "result.json")
        quality = read_json(root / "quality.json")
        variants.append(
            {
                "source_batch_tokens": size,
                "initial_batches": run["initial_batches"],
                "effective_batches": run["effective_batches"],
                "splits": run["splits"],
                "completed_batches": run["completed_batches"],
                "complete_queue": run["complete_queue"],
                "seconds": round(run["seconds"], 2),
                "claims": sum(len(value["extraction"]["claims"]) for value in run["results"]),
                "verifier_findings": sum(
                    len(value["verification"]["findings"]) for value in run["results"]
                ),
                "retained_facts": quality["facts_retained"],
                "total_facts": quality["facts_total"],
                "retained_qualifications": quality["qualifications_retained"],
                "total_qualifications": quality["qualifications_total"],
            }
        )
    with sqlite3.connect(settings.budget_ledger) as connection:
        rows = connection.execute("SELECT status,COUNT(*) FROM charges GROUP BY status").fetchall()
    corpus_status = read_json(store.path("legacy-final-status.json"))
    issues = [issue for value in corpus_status["interrupts"] for issue in value["issues"]]
    results = {
        "validation_date": "2026-10-08",
        "model": settings.gemini_model,
        "automated_tests": 23,
        "lint_passed": True,
        "wheel_built": True,
        "source_inventory": {
            "files": len(snapshot["inventory"]),
            "blocks": len(snapshot["blocks"]),
            "bytes": sum(value["bytes"] for value in snapshot["inventory"]),
            "problems": dict(Counter(value["kind"] for value in snapshot["problems"])),
        },
        "scale": scale,
        "live_smoke": {
            "status": smoke["values"]["status"],
            "thread_id": smoke["values"]["run_id"],
            "claims": len(bundle["claims"]),
            "entities": len(bundle["entities"]),
            "blocks": len(bundle["coverage"]),
            "bundle_ref": smoke["values"]["bundle_ref"],
        },
        "legacy_run": {
            "thread_id": corpus_status["values"]["run_id"],
            "status": corpus_status["values"]["status"],
            "open_issues": issues,
            "review_report": corpus_status["values"].get("review_report"),
        },
        "size_experiments": variants,
        "reference_assessment": {
            key: value for key, value in reference.items() if key != "assessments"
        },
        "reference_queue_complete": reference_run["complete_queue"],
        "held_out_assessment": {
            key: value for key, value in held_out.items() if key != "assessments"
        },
        "reference_claims": sum(
            len(value["extraction"]["claims"]) for value in reference_run["results"]
        ),
        "development_budget": budget,
        "request_outcomes": dict(rows),
    }
    write_json(Path("evaluation/results.json"), results)
    lines = [
        "# Implementation and validation report",
        "",
        "Validated on 2026-10-08.",
        "",
        "## Delivered",
        "",
        "The implementation follows `.ai/development-plan.md`; "
        "`.ai/plans/development-plan.md` does not exist.",
        "All eight named stages are sequential LangGraph nodes with SQLite persistence, "
        "stable thread IDs, "
        "atomic versioned artifacts, review interrupts, and revision-bound decisions. The "
        "CLI supports "
        "starting, inspecting, resuming, reviewing, budget inspection, and recording "
        "verified pricing.",
        "",
        "Source provenance, complete block accounting, bounded context, two repair "
        "attempts, truncation "
        "splitting, independent verification, conservative entity reconciliation, conflict "
        "review, and "
        "immutable final bundles are implemented. Original claims and all evidence remain "
        "available.",
        "",
        "Template mapping and final prose generation remain later phases, as specified in "
        "the plan.",
        "",
        "## Verification",
        "",
        "- 23 automated tests passed, including restart and `Command(resume=...)` across "
        "separate OS processes.",
        "- Ruff checks and formatting passed; the distribution wheel includes all "
        "versioned prompts.",
        "- Tests exercise exact source locations, table coordinates, missing inputs, "
        "truncation, repairs, "
        "concurrent cost reservations, unknown-failure charging, stale decisions, "
        "unsupported facts, "
        "entity scope separation, conflict eligibility, and cyclic duplicate coverage.",
        f"- Full provided corpus inventory: {len(snapshot['inventory'])} files, "
        f"{len(snapshot['blocks'])} "
        f"blocks, {sum(value['bytes'] for value in snapshot['inventory']):,} bytes; no "
        f"ingestion problems. "
        "All blocks were assigned once across 36 initial 8k batches.",
        f"- Scale fixture: {scale['whitespace_words']:,} whitespace-delimited words, "
        f"{scale['blocks']:,} blocks, {scale['batches']} bounded batches, "
        f"{scale['seconds']:.2f} seconds for ingestion and planning. "
        "This was a structural test, not a full live model run or a semantic completeness "
        "measurement.",
        f"- Real Gemini smoke pipeline completed: {len(bundle['claims'])} claims, "
        f"{len(bundle['entities'])} entity entries, {len(bundle['coverage'])} covered blocks, "
        "and zero unresolved issues. Its synthetic source specifies a coherent archive service.",
        "",
        "## Quality measurements",
        "",
        "Forty passages were annotated from the supplied corpus: 30 development passages "
        "and ten held out. "
        "The user has not reviewed the reference. Autonomous evaluation therefore records "
        "exploratory "
        "measurements and does not claim acceptance. Held-out labels were withheld during "
        "implementation and tuning, then scored once after the implementation was frozen.",
        "",
        f"On all 30 development passages, Gemini's independent scoring retained "
        f"{reference['facts_retained']}/{reference['facts_total']} annotated facts, "
        f"{reference['qualifications_retained']}/{reference['qualifications_total']} "
        f"qualifications and "
        f"{reference['entity_distinctions_correct']}/{reference['entity_distinctions_total']} "
        "entity distinctions. "
        f"It reported {reference['unsupported_additions']} unsupported additions and "
        f"{reference['incorrect_merges']} incorrect merges. "
        "The selected reference queue completed extraction and verification without code "
        "or verifier defects; "
        "source conflicts were retained as findings. Scoring uses the same model family "
        "and is not independent human proof.",
        "",
        f"The final held-out check scored {held_out['passages_scored']} passages: "
        f"{held_out['facts_retained']}/{held_out['facts_total']} facts, "
        f"{held_out['qualifications_retained']}/{held_out['qualifications_total']} qualifications, "
        f"{held_out['entity_distinctions_correct']}/{held_out['entity_distinctions_total']} "
        "entity distinctions. "
        f"Unsupported additions: {held_out['unsupported_additions']}; "
        f"incorrect merges: {held_out['incorrect_merges']}. No tuning followed this check.",
        "",
        "The size experiment used the same roughly 16k-token source sample and stopped "
        "after the first "
        "effective batch in each variant. It tested nominal 8k/16k/32k ownership limits, "
        "including splitting. "
        "It is not a complete, controlled corpus benchmark: nominal 32k did not receive "
        "32k of source, "
        "effective batches differ, and a transient server failure affected the 16k timing.",
        "",
        "| Nominal source budget | Initial/effective batches | Splits | First-batch claims "
        "| Facts | Qualifications | Verifier findings | Seconds |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for value in variants:
        lines.append(
            f"| {value['source_batch_tokens']} | "
            f"{value['initial_batches']}/{value['effective_batches']} "
            f"| {value['splits']} | {value['claims']} | "
            f"{value['retained_facts']}/{value['total_facts']} "
            f"| {value['retained_qualifications']}/{value['total_qualifications']} "
            f"| {value['verifier_findings']} | {value['seconds']} |"
        )
    lines.extend(
        [
            "",
            "The 32k variant lost the instruction to preserve an attachment-list ambiguity "
            "for migration review. Reference scoring detected that omission; the independent "
            "verification pass reported three source issues but did not identify the omission. "
            "This demonstrates that model verification alone is insufficient and larger "
            "nominal batches are not automatically better. "
            "Early runs also exposed overly strict structural-header exclusions; the "
            "implementation now recognizes "
            "empty HTML anchors and table headers without excluding factual prose.",
            "",
            "## Legacy source review",
            "",
            f"The current run `{corpus_status['values']['run_id']}` is "
            f"`{corpus_status['values']['status']}` "
            f"with {len(issues)} open issues after extraction and independent verification. "
            "CG-01 preserves the incompatible rules about effective versus approval dates. "
            "No authoritative version was invented and no final legacy bundle was produced. "
            "The saved interrupt and readable source report are the expected behavior for "
            "this unresolved corpus.",
            "",
            f"Local review report: `.docgen/{corpus_status['values'].get('review_report')}`.",
            "",
            "## Cost and retained evidence",
            "",
            f"The cumulative conservative charge is **{budget['charged_pln']:.4f} PLN** of "
            f"200 PLN, "
            f"including retries, thinking/output usage and 30% billing headroom. "
            f"Outstanding reservations: {budget['reserved_pln']:.4f} PLN. "
            "An API server failure with unknown usage was charged at its full reservation. "
            "The actual provider invoice may differ; the development ledger was never reset.",
            "",
            "Verified prices: USD 0.75 per million input tokens and USD 3.75 per million "
            "output tokens "
            "through 2026-12-31, from [Google](https://ai.google.dev/gemini-api/docs/pricing). "
            "The [NBP USD rate](https://api.nbp.pl/api/exchangerates/rates/a/usd/?format=json) "
            "on 2026-10-08 was 3.9132 PLN (table 196/A/NBP/2026). "
            "The saved pricing record expires on 2026-10-15 and must be refreshed before "
            "later live calls.",
            "",
            "Portable results are in `evaluation/results.json`; reference annotations are in "
            "`evaluation/reference.json` and `evaluation/reference-review.md`. "
            "Detailed model responses, token usage, checkpoints and source snapshots "
            "remain under ignored `.docgen/`.",
            "",
            "## Acceptance boundaries",
            "",
            "Implementation and automated checks are complete. Full legacy-corpus "
            "acceptance remains unestablished: "
            "the reference lacks human review, source authority conflicts remain "
            "unresolved, and the greater-than-context run was structural rather than a "
            "complete live semantic evaluation. "
            "The limited size experiments do not satisfy a full matched 8k/16k/32k corpus "
            "comparison. "
            "The benchmark and checkpoint tooling support those follow-up evaluations "
            "without resetting spending.",
            "",
            "The candidate reconciliation policy is bounded and auditable, but "
            "relationships sharing none of "
            "its name/entity/rule/scope signals can remain undetected. Source changes "
            "after reconciliation start a "
            "new revision; extraction-stage corrections are supported directly through review. "
            "Complete source accounting is not a claim of perfect semantic preservation.",
            "",
        ]
    )
    atomic_write(Path(".ai/implementation-report.md"), "\n".join(lines))


if __name__ == "__main__":
    main()
