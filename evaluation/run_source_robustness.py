import argparse
import json
import time
from dataclasses import replace
from pathlib import Path

from docgen_graph.config import Settings
from docgen_graph.contracts import DocumentExtractionDraft
from docgen_graph.knowledge import normalized_assertion
from docgen_graph.model import GeminiModel
from docgen_graph.semantic_contracts import NavigationalGraphDraft
from docgen_graph.semantic_graph import (
    anchor_semantic_quotes,
    semantic_payload,
    validate_semantic_proposal,
)
from docgen_graph.source_documents import document_context, document_spans, extraction_packet
from docgen_graph.storage import ArtifactStore


def evaluate_case(model, store, case, sources):
    started = time.time()
    files = [
        {"kind": "docs", "path": path, "hash": store.put_bytes(text.encode())}
        for path, text in sources.items()
    ]
    spans = [span for file in files for span in document_spans(file, sources[file["path"]])]
    inventory = {"spans": spans, **document_context(spans)}
    result = {
        "case_id": case["id"],
        "expectations": case["expectations"],
        "source_files": files,
        "sources": sources,
        "semantic_review": "unreviewed",
        "batches": [],
    }
    try:
        for index in range(len(inventory["document_batches"])):
            packet = extraction_packet(inventory, index)
            batch = {"packet": packet}
            result["batches"].append(batch)
            extraction = model.call(
                "extract_document",
                {**packet, "feedback": [], "previous": None},
                DocumentExtractionDraft,
            )
            batch["extraction"] = extraction
            allowed = {span["id"] for span in packet["blocks"] + packet["context_blocks"]}
            facts = [normalized_assertion(item, allowed) for item in extraction["assertions"]]
            payload = semantic_payload(facts, packet["blocks"], packet["context_blocks"])
            draft = model.call(
                "semantic_graph",
                {**payload, "feedback": [], "previous": None},
                NavigationalGraphDraft,
            )
            batch["raw_graph"] = draft
            anchored, repairs = anchor_semantic_quotes(draft, payload)
            canonical, findings = validate_semantic_proposal(anchored, payload)
            batch.update(
                canonical_graph=canonical,
                anchored_graph=anchored,
                quote_anchoring=repairs,
                structural_findings=findings,
            )
        result["status"] = "generated_for_review"
    except Exception as error:
        result.update(status="failed", error_type=type(error).__name__)
    result["seconds"] = time.time() - started
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--seconds", type=int, default=300)
    parser.add_argument("--cases", type=Path, default=Path("evaluation/source-first-cases.json"))
    args = parser.parse_args()
    if args.seconds <= 0:
        raise ValueError("Evaluation duration must be positive")
    store = ArtifactStore(args.workspace)
    if (store.root / "runs" / args.run_id).exists():
        raise ValueError("Use a fresh evaluation run ID")
    settings = replace(Settings.load(args.env_file), workspace=store.root)
    model = GeminiModel(settings, store, args.run_id)
    started = time.time()
    model.set_deadline(started + args.seconds)
    declared = json.loads(args.cases.read_text("utf-8"))
    report = {
        "run_id": args.run_id,
        "provider": model.provider,
        "model": settings.model,
        "started_at": started,
        "time_limit_seconds": args.seconds,
        "evaluation_type": "live_stage_only_not_a_full_pipeline_run",
        "semantic_review": "Requires independent review against exact original sources",
        "cases": [],
    }
    for case in declared["cases"]:
        variants = case.get("variants", {"original": None})
        for variant, text in variants.items():
            sources = {"source.md": text} if text is not None else case.get("sources")
            if sources is None:
                report["cases"].append(
                    {"case_id": case["id"], "status": "not_run_constructed_fixture"}
                )
                continue
            if time.time() >= started + args.seconds:
                report["cases"].append(
                    {"case_id": case["id"], "variant": variant, "status": "time_limit"}
                )
                continue
            result = evaluate_case(model, store, case, sources)
            report["cases"].append({**result, "variant": variant})
            report["elapsed_seconds"] = time.time() - started
            store.write(f"runs/{args.run_id}/robustness.json", json.dumps(report, indent=2))
    report["elapsed_seconds"] = time.time() - started
    path = store.write(f"runs/{args.run_id}/robustness.json", json.dumps(report, indent=2))
    print(json.dumps({"report": str(path), "seconds": report["elapsed_seconds"]}))


if __name__ == "__main__":
    main()
