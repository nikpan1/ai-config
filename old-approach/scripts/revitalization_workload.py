import argparse
from pathlib import Path
from time import monotonic

from docgen.contracts import Comparison
from docgen.ingestion import estimate_tokens
from docgen.model import prompt_text
from docgen.reconciliation import comparison_record, comparison_tasks, iter_comparisons
from docgen.storage import Artifacts, encode, write_json


def measure(bundle_path: Path, output: Path, token_budget: int):
    source_store = Artifacts(bundle_path.parents[1])
    task_store = Artifacts(Path(".docgen/revitalization-workload"))
    bundle = source_store.get(f"objects/{bundle_path.name}")
    snapshot = source_store.get(bundle["snapshot_ref"])
    claims = bundle["claims"]
    lookup = {record["id"]: record for record in claims}
    blocks = {block["id"]: block for block in snapshot["blocks"]}
    started = monotonic()
    plan = comparison_tasks(
        claims,
        "claims",
        token_budget,
        task_limit=20000,
        store=task_store,
        policy="exact",
    )
    largest_request = 0
    largest_pairs = 0
    total_pairs = 0
    prompt = prompt_text("claims")
    schema = encode(Comparison.model_json_schema())
    for task in iter_comparisons(plan, task_store):
        records = [lookup[key] for key in task["left"] + task["right"]]
        payload = {
            "group": task["group"],
            "left": [comparison_record(lookup[key]) for key in task["left"]],
            "right": [comparison_record(lookup[key]) for key in task["right"]],
            "source_blocks": [
                blocks[key]
                for key in sorted(
                    {entry["block_id"] for record in records for entry in record["evidence"]}
                )
            ],
            "required_pairs": task["required_pairs"],
            "shared_contexts": task["shared_contexts"],
            "pair_contexts": task["pair_contexts"],
        }
        largest_request = max(largest_request, estimate_tokens(prompt + encode(payload) + schema))
        largest_pairs = max(largest_pairs, len(task["required_pairs"]))
        total_pairs += len(task["required_pairs"])
    result = {
        "fixture": str(bundle_path),
        "claim_records": len(claims),
        "comparison_policy": "exact",
        "token_budget": token_budget,
        "comparison_tasks": plan["task_count"],
        "required_relationships": plan["required_relationships"],
        "checked_relationships_in_queue": total_pairs,
        "exact_pairs_discharged": plan["exact_pairs_discharged"],
        "unperformed": len(plan["unperformed"]),
        "largest_task_pairs": largest_pairs,
        "largest_request_estimated_tokens": largest_request,
        "largest_request_with_reserved_output": largest_request + 24000,
        "elapsed_seconds": monotonic() - started,
        "semantic_validation": "not_performed",
    }
    write_json(output, result)
    print(encode(result))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--token-budget", type=int, default=48000)
    args = parser.parse_args()
    measure(args.bundle, args.output, args.token_budget)


if __name__ == "__main__":
    main()
