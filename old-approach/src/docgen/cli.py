import argparse
import json
import re
import sys
from contextlib import nullcontext
from datetime import date, timedelta
from pathlib import Path

import httpx
from langgraph.types import Command
from pydantic import ValidationError

from docgen.budget import BudgetExceeded, BudgetLedger, Pricing
from docgen.config import Settings
from docgen.generation import STAGES as GENERATION_STAGES
from docgen.generation import GenerationPipeline
from docgen.model import GeminiModel, ModelFailure, RequestTooLarge, TruncatedOutput
from docgen.planning import STAGES, PlanningPipeline
from docgen.signatures import runtime_signature
from docgen.storage import Artifacts, configure_logging, read_json, run_lock, write_json
from docgen.workflow import Pipeline, persistent_graph


def run_config(run_id):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", run_id):
        raise ValueError("Thread ID must be 1-100 safe filename characters")
    return {"configurable": {"thread_id": run_id}, "recursion_limit": 100000}


def status_payload(snapshot):
    return {
        "values": snapshot.values,
        "next": list(snapshot.next),
        "interrupts": [item.value for item in snapshot.interrupts],
        "checkpoint_id": snapshot.config.get("configurable", {}).get("checkpoint_id"),
    }


def selected_decisions(args, snapshot, workflow):
    choices = args.select_authority or []
    distinct = args.keep_distinct or []
    unknowns = args.retain_unknown or []
    excluded = args.exclude or []
    explanations = args.explain_asset or []
    approve = args.approve_release
    if not any((choices, distinct, unknowns, excluded, explanations, approve)):
        return None
    if not snapshot.interrupts:
        raise ValueError("There is no pending review interrupt")
    if not args.reviewer:
        raise ValueError("--reviewer is required for a selected decision")
    issues = {issue["id"]: issue for issue in snapshot.interrupts[0].value["issues"]}
    decisions = []
    for value in choices:
        issue_id, separator, claims = value.partition("=")
        if not separator or issue_id not in issues or not claims:
            raise ValueError("Use --select-authority ISSUE=CLAIM[,CLAIM]")
        decisions.append(
            {
                "issue_id": issue_id,
                "revision": issues[issue_id]["revision"],
                "action": "select_authority",
                "claim_ids": claims.split(","),
                "reviewer": args.reviewer,
                "rationale": args.rationale or "Selected source authority after review",
            }
        )
    for issue_id in distinct:
        if issue_id not in issues:
            raise ValueError("Unknown review issue: " + issue_id)
        decisions.append(
            {
                "issue_id": issue_id,
                "revision": issues[issue_id]["revision"],
                "action": "keep_distinct",
                "reviewer": args.reviewer,
                "rationale": args.rationale or "Reviewed distinct entity meanings",
            }
        )
    for issue_id in unknowns:
        if issue_id not in issues:
            raise ValueError("Unknown review issue: " + issue_id)
        if workflow == "documentation_planning":
            raise ValueError("Planning unknowns require an evidence-backed correction reference")
        decisions.append(
            {
                "issue_id": issue_id,
                "revision": issues[issue_id]["revision"],
                "action": "acknowledge_unknown",
                "reviewer": args.reviewer,
                "rationale": args.rationale or "Reviewed the documented information gap",
            }
        )
    for issue_id in excluded:
        if issue_id not in issues:
            raise ValueError("Unknown review issue: " + issue_id)
        decisions.append(
            {
                "issue_id": issue_id,
                "revision": issues[issue_id]["revision"],
                "action": "exclude",
                "reviewer": args.reviewer,
                "rationale": args.rationale or "Reviewed exclusion from this source revision",
            }
        )
    for value in explanations:
        issue_id, separator, explanation = value.partition("=")
        if not separator or issue_id not in issues or not explanation:
            raise ValueError("Use --explain-asset ISSUE=EXPLANATION")
        decisions.append(
            {
                "issue_id": issue_id,
                "revision": issues[issue_id]["revision"],
                "action": "explain_asset",
                "reviewer": args.reviewer,
                "rationale": args.rationale or "Reviewed source asset",
                "explanation": explanation,
            }
        )
    if approve:
        if workflow != "documentation_generation" or any(
            issue["kind"] != "release" for issue in issues.values()
        ):
            raise ValueError("Release approval is available only at the final generation review")
        decisions.extend(
            {
                "issue_id": issue_id,
                "revision": issues[issue_id]["revision"],
                "action": "approve_release",
                "reviewer": args.reviewer,
                "rationale": args.rationale or "Reviewed the release candidate",
                "reviewed_scope": [
                    "content_accuracy",
                    "reader_usefulness",
                    "language",
                    "markdown",
                ],
            }
            for issue_id in issues
        )
    if len({decision["issue_id"] for decision in decisions}) != len(decisions):
        raise ValueError("Only one selected decision per issue is allowed")
    return {"decisions": decisions}


def execute(args, settings: Settings):
    store = Artifacts(settings.workspace)
    if args.command == "workload":
        from docgen.workload import workload_report

        return workload_report(settings, store, args.source, args.knowledge, args.selection)
    if args.command == "budget":
        return BudgetLedger(settings.budget_ledger, settings.budget_pln).summary()
    if args.command == "record-pricing":
        exchange_url = "https://api.nbp.pl/api/exchangerates/rates/a/usd/?format=json"
        response = httpx.get(exchange_url, timeout=30)
        response.raise_for_status()
        exchange = response.json()["rates"][-1]
        pricing = Pricing(
            model=settings.gemini_model,
            input_usd_per_million=args.input_usd,
            output_usd_per_million=args.output_usd,
            usd_pln=exchange["mid"],
            exchange_date=exchange["effectiveDate"],
            verified_on=date.today(),
            valid_until=min(date.fromisoformat(args.valid_until), date.today() + timedelta(days=7)),
            pricing_source="https://ai.google.dev/gemini-api/docs/pricing",
            exchange_source=exchange_url,
        )
        pricing.validate_current()
        write_json(settings.pricing_file, pricing)
        return pricing.model_dump(mode="json")
    config = run_config(args.thread_id)
    model = GeminiModel(settings, store, args.thread_id)
    metadata_path = store.path(f"runs/{args.thread_id}/workflow.json")
    metadata = read_json(metadata_path) if metadata_path.exists() else {}
    workflow = (
        "documentation_generation"
        if args.command == "generate-documentation"
        else "documentation_planning"
        if args.command == "plan-documentation"
        else metadata.get("workflow", "knowledge")
    )
    if args.command == "run" and workflow != "knowledge":
        raise ValueError("Thread belongs to another workflow; choose a new thread ID")
    if metadata and workflow != metadata["workflow"]:
        raise ValueError("Thread belongs to another workflow; choose a new thread ID")
    pipeline = (
        GenerationPipeline(settings, store, model)
        if workflow == "documentation_generation"
        else PlanningPipeline(settings, store, model)
        if workflow == "documentation_planning"
        else Pipeline(settings, store, model)
    )
    with (
        nullcontext() if args.command in {"status", "history"} else run_lock(store, args.thread_id),
        persistent_graph(pipeline, getattr(args, "stop_after", None)) as graph,
    ):
        current = graph.get_state(config)
        if args.command == "status":
            if not current.values:
                raise ValueError("Thread does not exist")
            return status_payload(current)
        if args.command == "history":
            return [
                {
                    "checkpoint_id": state.config["configurable"]["checkpoint_id"],
                    "created_at": state.created_at,
                    "next": list(state.next),
                    "status": state.values.get("status"),
                }
                for state in graph.get_state_history(config, limit=args.limit)
            ]
        signature = runtime_signature(settings, workflow)
        if current.values and current.values.get("signature") != signature:
            raise ValueError(
                "Code, prompts, schema, model or configuration changed; start a new thread revision"
            )
        if args.command in {"run", "plan-documentation", "generate-documentation"}:
            if current.values:
                raise ValueError("Thread already exists; use resume or choose a new thread ID")
            payload = {
                "run_id": args.thread_id,
                "workflow": workflow,
                "signature": signature,
                "status": "running",
            }
            if args.command == "run":
                payload.update(
                    source=str(Path(args.source).resolve()),
                    selection=str(Path(args.selection).resolve()) if args.selection else "",
                )
            elif args.command == "generate-documentation":
                payload.update(
                    plan=args.plan,
                    brief=str(Path(args.brief).resolve()) if args.brief else "",
                    cache_mode=args.cache_mode,
                )
            else:
                payload.update(
                    knowledge=args.knowledge,
                    template=str(Path(args.template).resolve()),
                    brief=str(Path(args.brief).resolve()) if args.brief else "",
                    previous_plan=args.previous_plan or "",
                )
            write_json(metadata_path, {"workflow": workflow, "signature": signature})
        else:
            if not current.values:
                raise ValueError("Thread does not exist")
            choice_payload = (
                selected_decisions(args, current, workflow) if args.command == "resume" else None
            )
            if choice_payload and args.decisions:
                raise ValueError("Use selected decisions or --decisions, not both")
            if (
                args.decisions
                and any(task.error for task in current.tasks)
                and current.next in {("review_issues",), ("review_plan",), ("review_generation",)}
            ):
                graph.update_state(
                    config,
                    {"route": current.next[0]},
                    as_node=current.values["review_stage"],
                )
                graph.invoke(None, config, durability="sync")
                current = graph.get_state(config)
            if current.interrupts:
                if not args.decisions and not choice_payload:
                    return status_payload(current)
                payload = Command(
                    resume=choice_payload if choice_payload else read_json(Path(args.decisions))
                )
            else:
                if args.decisions or choice_payload:
                    raise ValueError("There is no pending review interrupt")
                payload = None
        try:
            graph.invoke(payload, config, durability="sync")
        except (BudgetExceeded, ModelFailure, RequestTooLarge, TruncatedOutput) as error:
            snapshot = status_payload(graph.get_state(config))
            return {**snapshot, "technical_failure": str(error), "resumable": True}
        return status_payload(graph.get_state(config))


def parser():
    root = argparse.ArgumentParser(prog="docgen")
    root.add_argument("--env-file", default=".env")
    commands = root.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="Start a new immutable source revision")
    run.add_argument("source")
    run.add_argument("--thread-id", required=True)
    run.add_argument("--selection", help="Exact file-list JSON relative to the source root")
    run.add_argument(
        "--stop-after",
        choices=["snapshot_sources", "plan_batches", "extract_batch", "verify_batch"],
    )
    resume = commands.add_parser("resume", help="Resume a checkpoint or submit review decisions")
    resume.add_argument("--thread-id", required=True)
    resume.add_argument("--decisions")
    resume.add_argument("--select-authority", action="append", metavar="ISSUE=CLAIM[,CLAIM]")
    resume.add_argument("--keep-distinct", action="append", metavar="ISSUE")
    resume.add_argument("--retain-unknown", action="append", metavar="ISSUE")
    resume.add_argument("--exclude", action="append", metavar="ISSUE")
    resume.add_argument("--explain-asset", action="append", metavar="ISSUE=EXPLANATION")
    resume.add_argument("--approve-release", action="store_true")
    resume.add_argument("--reviewer")
    resume.add_argument("--rationale")
    resume.add_argument(
        "--stop-after",
        choices=[
            "snapshot_sources",
            "plan_batches",
            "extract_batch",
            "verify_batch",
            *STAGES,
            *GENERATION_STAGES,
        ],
    )
    plan = commands.add_parser(
        "plan-documentation", help="Plan documentation from completed knowledge"
    )
    plan.add_argument("--knowledge", required=True)
    plan.add_argument("--template", required=True)
    plan.add_argument("--thread-id", required=True)
    plan.add_argument("--brief")
    plan.add_argument("--previous-plan")
    plan.add_argument("--stop-after", choices=STAGES)
    generation = commands.add_parser(
        "generate-documentation", help="Generate evidence-backed Markdown from a completed plan"
    )
    generation.add_argument("--plan", required=True)
    generation.add_argument("--thread-id", required=True)
    generation.add_argument("--brief")
    generation.add_argument("--cache-mode", choices=["off", "validated"], default="validated")
    generation.add_argument("--stop-after", choices=GENERATION_STAGES)
    for name in ("status", "history"):
        command = commands.add_parser(name)
        command.add_argument("--thread-id", required=True)
        if name == "history":
            command.add_argument("--limit", type=int, default=20)
    commands.add_parser("budget")
    workload = commands.add_parser("workload", help="Report workload without paid model calls")
    workload.add_argument("--source")
    workload.add_argument("--knowledge")
    workload.add_argument("--selection")
    pricing = commands.add_parser(
        "record-pricing", help="Record verified official prices and refresh NBP FX"
    )
    pricing.add_argument("--input-usd", type=float, required=True)
    pricing.add_argument("--output-usd", type=float, required=True)
    pricing.add_argument("--valid-until", required=True)
    return root


def main():
    arguments = parser().parse_args()
    configure_logging()
    try:
        settings = Settings(_env_file=arguments.env_file)
        result = execute(arguments, settings)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        if isinstance(result, dict) and "technical_failure" in result:
            return 3
        if isinstance(result, dict) and result.get("interrupts"):
            return 2
        return 0
    except ValidationError:
        print(
            "Configuration or decision schema is invalid; verify field names and required model",
            file=sys.stderr,
        )
        return 1
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
