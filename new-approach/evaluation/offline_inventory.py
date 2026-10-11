import argparse
import json
import time
import tracemalloc
from pathlib import Path

from docgen_graph.ingestion import inventory, snapshot_inputs
from docgen_graph.storage import ArtifactStore


def main() -> None:
    command = argparse.ArgumentParser()
    command.add_argument("--docs", type=Path, required=True)
    command.add_argument("--code", type=Path, required=True)
    command.add_argument("--template", type=Path, required=True)
    command.add_argument("--workspace", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    args = command.parse_args()
    started = time.monotonic()
    tracemalloc.start()
    store = ArtifactStore(args.workspace)
    snapshot = snapshot_inputs(store, args.docs, args.code, args.template, "offline evaluation")
    result = inventory(store, snapshot)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    summary = {
        "status": "inventory_only",
        "selected_files": len(snapshot["files"]),
        "selected_bytes": sum(item["size"] for item in snapshot["files"]),
        "excluded_inputs": len(snapshot["exclusions"]),
        "source_spans": len(result["spans"]),
        "code_units": len(result["code_units"]),
        "document_batches": len(result["document_batches"]),
        "parser_capabilities": sorted(
            {metadata["capability"] for metadata in result["analysis"].values()}
        ),
        "seconds": round(time.monotonic() - started, 3),
        "python_peak_allocated_bytes": peak,
        "source_revision": snapshot["revision"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
