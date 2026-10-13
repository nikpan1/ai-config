import argparse
import json
import re
import sqlite3
import time
from contextlib import closing
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from docgen_graph.config import Settings
from docgen_graph.model import GeminiModel
from docgen_graph.semantic_graph import semantic_quality_report
from docgen_graph.storage import ArtifactStore, digest
from docgen_graph.workflow import Pipeline


def verify_source_graph(path, assertions):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as connection:
        findings = list(connection.execute("PRAGMA foreign_key_check"))
        findings.extend(
            connection.execute(
                "SELECT a.id FROM assertions a LEFT JOIN support s ON s.assertion_id=a.id "
                "WHERE s.assertion_id IS NULL"
            )
        )
        findings.extend(
            connection.execute(
                "SELECT e.source_id,e.target_id FROM edges e "
                "LEFT JOIN evidence v ON v.id=e.evidence_id "
                "WHERE e.evidence_id IS NOT NULL AND v.id IS NULL"
            )
        )
        existing = {row[0] for row in connection.execute("SELECT id FROM assertions")}
    if findings or existing != {item["id"] for item in assertions}:
        raise ValueError(
            "Source graph failed evidence integrity or assertion identity verification"
        )


def prepare_reuse(store, checkpointer, settings, from_run, thread_id, model=None):
    for value in (from_run, thread_id):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,100}", value):
            raise ValueError(
                "Run identifiers must contain only letters, digits, dots, underscores or dashes"
            )
    target_config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 100000}
    if (store.root / "runs" / thread_id).exists() or checkpointer.get_tuple(target_config):
        raise ValueError("Target run already exists")
    source_checkpoint = checkpointer.get_tuple({"configurable": {"thread_id": from_run}})
    if source_checkpoint is None:
        raise ValueError("Source run does not exist")
    source = source_checkpoint.checkpoint["channel_values"]
    if source.get("status") != "incomplete":
        raise ValueError("Only an incomplete verified run can be reused")
    issue = store.get(source["issue_ref"])
    if issue["stage"] not in {"audit_semantic_graph", "locate_visual_evidence"}:
        raise ValueError("Source run did not stop at a supported verified stage")
    reuse_semantics = issue["stage"] == "locate_visual_evidence"
    route = "locate_visual_evidence" if reuse_semantics else "propose_semantic_graph"
    seed_node = "retrieve_plan_evidence" if reuse_semantics else "verify_graph_batch"
    if source.get("deadline", 0) <= time.time():
        raise TimeoutError("Original run deadline has expired")
    assertions = store.get(source["assertions_ref"])
    inventory = store.get(source["inventory_ref"])
    verify_source_graph(store.root / "runs" / from_run / "graph.sqlite", assertions)
    fact_batches = store.get(source["fact_batches_ref"])
    if {identifier for batch in fact_batches for identifier in batch} != {
        item["id"] for item in assertions
    }:
        raise ValueError("Verified assertion batches do not cover the preserved assertions")
    preserved_keys = {
        "snapshot_ref",
        "inventory_ref",
        "assertions_ref",
        "exclusions_ref",
        "fact_batches_ref",
        "source_aspects_ref",
        "source_decisions_ref",
        "source_non_substantive_ref",
        "document_provenance_ref",
        "document_index",
        "source_aspect_index",
        "source_audit_index",
        "docs",
        "template",
        "brief",
        "mode",
        "policy_version",
        "graph_only",
        "deadline",
    }
    if reuse_semantics:
        preserved_keys.update(
            {
                "plan_ref",
                "template_ref",
                "graph_revision",
                "graph_quality_ref",
                "plan_packets_ref",
                "plan_packet_index",
                "plan_hash",
                "source_coverage_ref",
                "semantic_index",
                "semantic_audit_ref",
                "semantic_canonical_ref",
            }
        )
        manifest = json.loads(
            (store.root / "runs" / from_run / "graph-manifest.json").read_text("utf-8")
        )
        if manifest["revision"] != source["graph_revision"]:
            raise ValueError("Frozen graph revision does not match the source checkpoint")
        if manifest["source_revision"] != source["snapshot_ref"]:
            raise ValueError("Frozen graph source snapshot does not match the checkpoint")
        if not store.get(source["graph_quality_ref"])["accepted"]:
            raise ValueError("Source semantic graph quality was not accepted")
    state = {key: source[key] for key in preserved_keys if key in source}
    for key, value in state.items():
        if key.endswith("_ref") and value:
            store.get(value)
    pipeline = Pipeline(store, model or GeminiModel(settings, store, thread_id), thread_id)
    if reuse_semantics:
        source_path = store.root / "runs" / from_run / "graph.sqlite"
        with closing(sqlite3.connect(source_path.as_uri() + "?mode=ro", uri=True)) as origin:
            with closing(sqlite3.connect(pipeline.graph.path)) as destination:
                origin.backup(destination)
        if not semantic_quality_report(pipeline.graph)["accepted"]:
            raise ValueError("Copied semantic graph did not pass independent structural validation")
        for filename in ("graph-manifest.json", "graph-quality.json", "coverage.json"):
            store.write(
                f"runs/{thread_id}/{filename}",
                (store.root / "runs" / from_run / filename).read_bytes(),
            )
    else:
        pipeline.graph.add_evidence(inventory["spans"])
        pipeline.graph.add_structure(inventory)
        pipeline.graph.add_assertions(assertions)
    findings = pipeline.graph.verify()
    if findings:
        raise ValueError(f"Rebuilt graph failed integrity verification: {findings}")
    state.update(
        {
            "run_id": thread_id,
            "runtime_signature": pipeline.runtime_signature(),
            "status": "running",
            "mode": "autopilot",
            "graph_index": (len(assertions) + 49) // 50,
            "semantic_index": source.get("semantic_index", 0) if reuse_semantics else 0,
            "attempt": 0,
            "automatic_issue_attempts": 0,
            "feedback_ref": "",
            "visual_attempt": 0,
            "visual_feedback_ref": "",
            "route": route,
        }
    )
    pipeline.stages.initialize(
        state["mode"],
        state.get("policy_version", "v2"),
        state["runtime_signature"],
        pipeline.repair_limit(),
    )
    provenance = {
        "source_run": from_run,
        "target_run": thread_id,
        "source_checkpoint": source_checkpoint.config,
        "source_runtime_signature": source["runtime_signature"],
        "target_runtime_signature": state["runtime_signature"],
        "source_issue_ref": source["issue_ref"],
        "preserved_references": {
            key: value for key, value in state.items() if key.endswith("_ref") and value
        },
        "assertions_digest": digest(assertions),
        "assertion_count": len(assertions),
        "source_span_count": len(inventory["spans"]),
        "source_graph_verified": True,
        "deadline": state["deadline"],
        "resumed_stage": route,
        "preserved_semantic_graph": reuse_semantics,
        "reason": "Preserve verified work and resume the failed stage under corrected runtime",
    }
    store.write(f"runs/{thread_id}/reuse-provenance.json", json.dumps(provenance, indent=2))
    state["stage_record"] = pipeline.stages.record(
        seed_node, state, {"route": route, "reused_from": from_run}
    )
    graph = pipeline.build(checkpointer)
    graph.update_state(target_config, state, as_node=seed_node)
    return graph, target_config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-run", required=True)
    parser.add_argument("--thread-id", required=True)
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    settings = Settings.load(args.env_file)
    store = ArtifactStore(settings.workspace)
    with closing(
        sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)
    ) as connection:
        graph, config = prepare_reuse(
            store, SqliteSaver(connection), settings, args.from_run, args.thread_id
        )
        result = graph.invoke(None, config)
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "run_id": args.thread_id,
                    "reused_from": args.from_run,
                    "deadline": result["deadline"],
                    "candidate_ref": result.get("candidate_ref"),
                },
                indent=2,
            )
        )
        return (
            0
            if result["status"]
            in {"complete", "complete_with_omissions", "complete_with_exclusions", "graph_complete"}
            else 13
        )


if __name__ == "__main__":
    raise SystemExit(main())
