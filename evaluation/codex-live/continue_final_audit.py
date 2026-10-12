import argparse
import ast
import json
import sqlite3
import subprocess
from contextlib import closing
from dataclasses import replace
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from docgen_graph.config import Settings
from docgen_graph.model import GeminiModel
from docgen_graph.storage import ArtifactStore, digest
from docgen_graph.workflow import Pipeline


def without_final_audit(source):
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Pipeline":
            node.body = [
                item
                for item in node.body
                if getattr(item, "name", "") != "audit_source_to_document"
            ]
    return ast.dump(tree)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--configuration", type=Path, required=True)
    parser.add_argument("--source-run", required=True)
    parser.add_argument("--target-run", required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[2]
    workflow = "src/docgen_graph/workflow.py"
    prompt = "src/docgen_graph/prompts/audit_source_to_document.v1.txt"

    def git(*parts):
        return subprocess.check_output(["git", "-C", str(repository), *parts])

    changed = set(git("diff", "--name-only", args.source_commit, "--", "src").decode().splitlines())
    if changed != {workflow, prompt}:
        raise ValueError(
            "Continuation permits only the reviewed final-audit implementation and prompt change"
        )
    old_workflow = git("show", f"{args.source_commit}:{workflow}").decode("utf-8")
    if without_final_audit(old_workflow) != without_final_audit(
        (repository / workflow).read_text("utf-8")
    ):
        raise ValueError("An upstream workflow stage changed")
    configuration = json.loads(args.configuration.read_text("utf-8"))
    overrides = configuration["settings"]
    for name in ("workspace", "code_scope_file", "code_provider_allowance_file"):
        overrides[name] = Path(overrides[name]).resolve()
    settings = replace(Settings.load(args.env_file), **overrides)
    store = ArtifactStore(settings.workspace)
    target = store.root / "runs" / args.target_run
    if target.exists():
        raise ValueError("Continuation target already exists")
    with closing(
        sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)
    ) as connection:
        saver = SqliteSaver(connection)
        source_pipeline = Pipeline(
            store, GeminiModel(settings, store, args.source_run), args.source_run
        )
        source_graph = source_pipeline.build(saver)
        source_config = {"configurable": {"thread_id": args.source_run}}
        checkpoint = next(
            item
            for item in source_graph.get_state_history(source_config)
            if item.next == ("audit_source_to_document",)
            and item.values.get("source_audit_index") == 0
        )
        state = dict(checkpoint.values)
        source_manifest = json.loads(
            (store.root / "runs" / args.source_run / "run-manifest.json").read_text("utf-8")
        )
        if state["runtime_signature"] != source_manifest["runtime_signature"]:
            raise ValueError("Source runtime identity is inconsistent")
        verified = {}
        for key, value in state.items():
            if key.endswith("_ref") and isinstance(value, str) and len(value) == 64:
                store.get_bytes(value)
                verified[key] = value
        snapshot = store.get(state["snapshot_ref"])
        for item in snapshot["files"] + snapshot.get("assets", []):
            if item.get("hash"):
                store.get_bytes(item["hash"])
        source_database = store.root / "runs" / args.source_run / "graph.sqlite"
        target.mkdir(parents=True)
        with (
            closing(sqlite3.connect(source_database)) as source,
            closing(sqlite3.connect(target / "graph.sqlite")) as copied,
        ):
            if source.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Source graph integrity failed")
            source.backup(copied)
            if copied.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Copied graph integrity failed")
            original_dump = "\n".join(source.iterdump())
            if original_dump != "\n".join(copied.iterdump()):
                raise ValueError("Imported graph differs from its producer")
        pipeline = Pipeline(store, GeminiModel(settings, store, args.target_run), args.target_run)
        graph = pipeline.build(saver)
        signature = pipeline.runtime_signature()
        lineage = {
            "actor_type": "agent",
            "kind": "final_audit_export_continuation",
            "source_run": args.source_run,
            "source_checkpoint": checkpoint.config["configurable"]["checkpoint_id"],
            "source_commit": args.source_commit,
            "source_runtime_signature": state["runtime_signature"],
            "target_run": args.target_run,
            "target_commit": git("rev-parse", "HEAD").decode().strip(),
            "target_runtime_signature": signature,
            "reviewed_change_ref": store.put_bytes(git("diff", args.source_commit, "--", "src")),
            "imported_refs": verified,
            "graph_logical_hash": digest(original_dump),
            "revalidated_upstream_workflow_ast": True,
            "resume_at": "audit_documentation",
            "rationale": (
                "Correct final audit batch context; preserve verified source, writing and editing "
                "artifacts and repeat final mapping, coverage, independent source audits "
                "and bundle checks."
            ),
        }
        pipeline.stages.initialize(
            state.get("mode", "autopilot"),
            state.get("policy_version", "v2"),
            signature,
            pipeline.repair_limit(),
        )
        store.write(f"runs/{args.target_run}/continuation.json", json.dumps(lineage, indent=2))
        store.write(
            f"runs/{args.target_run}/README.md",
            (
                f"# Final-audit continuation {args.target_run}\n\n"
                f"Generation and editing artifacts: ../{args.source_run}/\n\n"
                "See continuation.json for verified import lineage. "
                "This run repeats final audits and exports the imported document.\n"
            ),
        )
        state.update(
            run_id=args.target_run,
            runtime_signature=signature,
            route="audit_documentation",
            status="auditing",
            source_audit_index=0,
            candidate_ref="",
            candidate_manifest_hash="",
            release_ref="",
            issue_ref="",
            unresolved_ref="",
        )
        state.pop("stage_record", None)
        config = {"configurable": {"thread_id": args.target_run}}
        imported = graph.update_state(config, state, as_node="review_stage")
        store.event(
            args.target_run,
            "continuation_import",
            "completed",
            actor_type="agent",
            source_run=args.source_run,
            source_checkpoint=lineage["source_checkpoint"],
            checkpoint_id=imported["configurable"]["checkpoint_id"],
            imported_refs=verified,
            route="audit_documentation",
        )
        print(
            json.dumps(
                {
                    "target_run": args.target_run,
                    "next": graph.get_state(config).next,
                    "lineage": str(target / "continuation.json"),
                }
            )
        )


if __name__ == "__main__":
    main()
