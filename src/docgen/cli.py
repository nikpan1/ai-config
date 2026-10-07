import json
import sys
from pathlib import Path
from typing import Annotated

import typer

from docgen.config import STAGES, Settings
from docgen.ingestion import inventory
from docgen.models import ReviewDecision
from docgen.preview import run_report
from docgen.storage import Store, read_json, write_json
from docgen.workflow import run_pipeline

app = typer.Typer(no_args_is_help=True, help="Evidence-backed documentation from legacy Markdown.")
Runs = Annotated[Path, typer.Option(help="Run storage directory")]


def emit(value: object) -> None:
    typer.echo(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def find_run(run_id: str, runs: Path) -> Store:
    path = (runs / run_id).resolve()
    if not path.is_relative_to(runs.resolve()) or path == runs.resolve():
        raise ValueError("Run ID must identify a directory inside run storage")
    return Store(path)


@app.command()
def inspect(path: Path, runs: Runs = Path("runs")) -> None:
    """Inventory Markdown and image gaps without calling a model."""
    emit(inventory(path, exclude=runs))


@app.command()
def run(path: Path, config: Path | None = None, runs: Runs = Path("runs")) -> None:
    """Start a run; source excerpts and informative images will be sent to Gemini."""
    store = Store.create(runs, path, Settings.load(config))
    typer.echo(f"Run: {store.manifest['run_id']}")
    try:
        emit(run_pipeline(store))
    finally:
        typer.echo(f"Report: {run_report(store)}")


@app.command()
def resume(run_id: str, config: Path | None = None, runs: Runs = Path("runs")) -> None:
    """Resume from retained valid artifacts and persistent checkpoints."""
    store = find_run(run_id, runs)
    emit(run_pipeline(store, settings=Settings.load(config) if config else None))


@app.command()
def stages(run_id: str, runs: Runs = Path("runs")) -> None:
    """Show active stages, history and integrity warnings."""
    store = find_run(run_id, runs)
    with store.lock():
        warnings = store.verify(Settings.model_validate(store.manifest["settings"]))
        emit(
            {
                "run_id": run_id,
                "status": store.manifest["status"],
                "warnings": warnings,
                "stages": store.manifest["stages"],
                "usage": store.manifest["usage"],
            }
        )


@app.command()
def show(
    run_id: str,
    stage: Annotated[str, typer.Option("--stage")],
    attempt: int | None = None,
    runs: Runs = Path("runs"),
) -> None:
    """Print one attempt's inputs, output, review, failure and exchange paths."""
    store = find_run(run_id, runs)
    if stage not in STAGES:
        raise ValueError(f"Unknown stage: {stage}")
    selected = (
        next((a for a in store.stage(stage)["attempts"] if a["id"] == attempt), None)
        if attempt
        else store.active(stage)
    )
    if not selected:
        raise ValueError("No matching attempt")
    directory = store.attempt_dir(stage, selected)
    emit(
        {
            "metadata": selected,
            "files": {
                p.relative_to(directory).as_posix(): read_json(p)
                for p in sorted(directory.glob("*.json"))
            },
            "model_exchanges": [str(p) for p in directory.glob("model-calls/*")],
        }
    )


@app.command()
def report(run_id: str, runs: Runs = Path("runs")) -> None:
    """Generate a local report, including failed and historical attempts."""
    store = find_run(run_id, runs)
    with store.lock():
        store.verify(Settings.model_validate(store.manifest["settings"]))
        typer.echo(str(run_report(store)))


@app.command()
def reset(
    run_id: str,
    from_stage: Annotated[str, typer.Option("--from")],
    purge: bool = False,
    dry_run: bool = False,
    runs: Runs = Path("runs"),
) -> None:
    """Invalidate a stage and its dependents; optionally purge generated payloads."""
    store = find_run(run_id, runs)
    with store.lock():
        emit(store.reset(from_stage, purge=purge, dry_run=dry_run))


@app.command()
def review(
    run_id: str,
    decision: Path | None = None,
    write_decision: Path | None = None,
    runs: Runs = Path("runs"),
) -> None:
    """Inspect the pending request, create a decision template or submit a JSON decision."""
    store = find_run(run_id, runs)
    if decision:
        emit(run_pipeline(store, decision=ReviewDecision.model_validate(read_json(decision))))
        return
    with store.lock():
        store.verify(Settings.model_validate(store.manifest["settings"]))
        stage = next((s for s in STAGES if store.stage(s)["status"] == "waiting_for_review"), None)
        if not stage:
            raise ValueError("No pending review")
        attempt = store.active(stage)
        assert attempt is not None
        request = read_json(store.attempt_dir(stage, attempt) / "review-request.json")
        if write_decision:
            if write_decision.exists():
                raise ValueError("Decision file already exists")
            write_json(
                write_decision,
                {
                    "revision": request["revision"],
                    "reviewer": "",
                    "action": "defer",
                    "rationale": "",
                    "patch": None,
                    "statements": [],
                    "included_image_ids": [],
                },
            )
            typer.echo(str(write_decision.resolve()))
        else:
            emit(request)


@app.command()
def export(run_id: str, runs: Runs = Path("runs")) -> None:
    """Export only an approved and validated documentation revision."""
    store = find_run(run_id, runs)
    with store.lock():
        store.verify(Settings.model_validate(store.manifest["settings"]))
        if store.stage("review_documentation")["status"] != "completed":
            raise ValueError("Final documentation approval is required")
    run_pipeline(store)
    emit(store.output("export"))


def main() -> None:
    try:
        app()
    except (ValueError, OSError) as exc:
        typer.echo(str(exc), err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
