import json
import sqlite3
from contextlib import closing
from dataclasses import replace
from importlib.resources import files
from pathlib import Path

from dotenv import dotenv_values
from langgraph.checkpoint.sqlite import SqliteSaver

from docgen_graph.config import Settings
from docgen_graph.model import GeminiModel, implementation_signature
from docgen_graph.storage import ArtifactStore, digest
from docgen_graph.workflow import Pipeline


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    fixture = Path(__file__).resolve().parent / "fixtures"
    key = str(dotenv_values(root / ".env").get("GEMINI_API_KEY") or "")
    if not key:
        raise ValueError("GEMINI_API_KEY is missing from repository .env")
    settings = replace(Settings.load(), api_key=key)
    store = ArtifactStore(settings.workspace)
    prompt_hashes = {item.name: digest(item.read_bytes())
                     for item in files("docgen_graph").joinpath("prompts").iterdir()}
    fixture_hashes = {item.relative_to(fixture).as_posix(): digest(item.read_bytes())
                      for item in fixture.rglob("*") if item.is_file()}
    run_id = "new-approach-live-plan-" + digest([
        implementation_signature(), prompt_hashes, fixture_hashes,
    ])[:12]
    with closing(
        sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)
    ) as connection:
        graph = Pipeline(store, GeminiModel(settings, store, run_id), run_id).build(
            SqliteSaver(connection)
        )
        config = {"configurable": {"thread_id": run_id}, "recursion_limit": 100000}
        current = graph.get_state(config)
        if current.values:
            graph.invoke(None, config)
        else:
            graph.invoke(
                {
                    "run_id": run_id,
                    "docs": str(fixture / "docs"),
                    "code": str(fixture / "code"),
                    "template": str(fixture / "template.md"),
                    "brief": (
                        "Document the agreement and disagreement between code "
                        "and legacy policy."
                    ),
                    "status": "running",
                },
                config,
            )
        state = graph.get_state(config)
        print(
            json.dumps(
                {
                    "status": state.values.get("status"),
                    "next": state.next,
                    "plan_hash": state.values.get("plan_hash"),
                    "run_path": str(store.root / "runs" / run_id),
                },
                default=str,
            )
        )


if __name__ == "__main__":
    main()
