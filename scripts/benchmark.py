import argparse
from pathlib import Path

from docgen.config import Settings
from docgen.evaluation import assess_variant, load_reference, run_variant, selected_snapshot
from docgen.ingestion import snapshot_sources
from docgen.storage import Artifacts, configure_logging, encode, run_lock, write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", nargs="+", type=int, default=[8000, 16000, 32000])
    parser.add_argument("--source-tokens", type=int, default=32000)
    parser.add_argument("--max-batches", type=int)
    parser.add_argument("--run-prefix", default="benchmark")
    parser.add_argument("--score", action="store_true")
    parser.add_argument("--include-held-out", action="store_true")
    args = parser.parse_args()
    settings = Settings()
    store = Artifacts(settings.workspace)
    reference = load_reference()
    configure_logging()
    snapshot = snapshot_sources(Path("data/legacy-insurance"), store)
    selected = selected_snapshot(snapshot, reference, args.source_tokens)
    write_json(store.path(f"evaluation/{args.run_prefix}/selected.json"), selected)
    for size in args.sizes:
        run_id = f"{args.run_prefix}-{size}"
        with run_lock(store, run_id):
            variant = run_variant(settings, store, selected, size, run_id, args.max_batches)
            print(
                encode({key: value for key, value in variant.items() if key != "results"}),
                flush=True,
            )
            if args.score:
                quality = assess_variant(
                    settings, store, variant, reference, selected, run_id, args.include_held_out
                )
                print(
                    encode({key: value for key, value in quality.items() if key != "assessments"}),
                    flush=True,
                )


if __name__ == "__main__":
    main()
