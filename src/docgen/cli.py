import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx
from langgraph.types import Command
from pydantic import ValidationError

from docgen.budget import BudgetExceeded, BudgetLedger, Pricing
from docgen.config import Settings
from docgen.model import GeminiModel, ModelFailure, implementation_signature, prompt_text
from docgen.storage import Artifacts, configure_logging, digest, read_json, run_lock, write_json
from docgen.workflow import Pipeline, persistent_graph


def runtime_signature(settings: Settings):
    return digest(
        [
            settings.signature(),
            implementation_signature(),
            {name: prompt_text(name) for name in ("extract", "verify", "entities", "claims")},
        ]
    )


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


def execute(args, settings: Settings):
    store = Artifacts(settings.workspace)
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
    pipeline = Pipeline(settings, store, model)
    with (
        run_lock(store, args.thread_id),
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
        signature = runtime_signature(settings)
        if current.values and current.values.get("signature") != signature:
            raise ValueError(
                "Code, prompts, schema, model or configuration changed; start a new thread revision"
            )
        if args.command == "run":
            if current.values:
                raise ValueError("Thread already exists; use resume or choose a new thread ID")
            payload = {
                "run_id": args.thread_id,
                "source": str(Path(args.source).resolve()),
                "signature": signature,
                "status": "running",
            }
        else:
            if not current.values:
                raise ValueError("Thread does not exist")
            if current.interrupts:
                if not args.decisions:
                    return status_payload(current)
                payload = Command(resume=read_json(Path(args.decisions)))
            else:
                if args.decisions:
                    raise ValueError("There is no pending review interrupt")
                payload = None
        try:
            graph.invoke(payload, config, durability="sync")
        except (BudgetExceeded, ModelFailure) as error:
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
    run.add_argument(
        "--stop-after",
        choices=["snapshot_sources", "plan_batches", "extract_batch", "verify_batch"],
    )
    resume = commands.add_parser("resume", help="Resume a checkpoint or submit review decisions")
    resume.add_argument("--thread-id", required=True)
    resume.add_argument("--decisions")
    resume.add_argument(
        "--stop-after",
        choices=["snapshot_sources", "plan_batches", "extract_batch", "verify_batch"],
    )
    for name in ("status", "history"):
        command = commands.add_parser(name)
        command.add_argument("--thread-id", required=True)
        if name == "history":
            command.add_argument("--limit", type=int, default=20)
    commands.add_parser("budget")
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
        if "technical_failure" in result:
            return 3
        if result.get("interrupts"):
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
