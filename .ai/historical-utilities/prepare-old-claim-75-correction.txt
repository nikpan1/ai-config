import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "old-approach" / "src"))

from docgen.contracts import Comparison
from docgen.reconciliation import comparison_at
from docgen.storage import Artifacts, write_json

workspace = Path(__file__).resolve().parents[1]
store = Artifacts(workspace / ".docgen")
run_id = "furniture-old-knowledge-v2"
revision = "objects/claim-comparison-e8270bf5a3f768e9edd20c2b270d7d51c5b94b46e892e79c78c547b256046b77.json"
plan_ref = "objects/claim-plan-3bc4cdd4e7d74da7d4d2600a10dc54cc9aabbda21060d17a9000b747a5d33bc9.json"

task = comparison_at(store.get(plan_ref), 75, store)
original = Comparison.model_validate(store.get(revision))
required = {tuple(sorted(pair)) for pair in task["required_pairs"]}
observed = {tuple(sorted(pair)) for pair in original.checked_pairs}
missing = sorted(required - observed)
extra = sorted(observed - required)
assert missing == [
    ("batch-7ad1c2b6931af00e:c13", "batch-ded65bf5276b5c9a:c20"),
    ("batch-7ad1c2b6931af00e:c15", "batch-ded65bf5276b5c9a:c17"),
]
assert extra == [
    ("batch-7ad1c2b6931af00e:c17", "batch-ded65bf5276b5c9a:c17"),
]

correction = original.model_copy(update={"checked_pairs": task["required_pairs"]})
expected = set(task["left"] + task["right"])
assert set(correction.checked_ids) == expected
assert len(correction.checked_ids) == len(expected) == 36
assert {tuple(sorted(pair)) for pair in correction.checked_pairs} == required
assert len(correction.checked_pairs) == len(required) == 301
assert not correction.relations
assert not correction.findings

comparison_ref = store.put(correction, "claim-comparison-correction-proposal")
proposal = {
    "run_id": run_id,
    "task_id": task["id"],
    "original_revision": revision,
    "comparison_ref": comparison_ref,
    "added_checked_pairs": [
        {
            "ids": list(missing[0]),
            "review": "Front and handle first-purchase summary is a specific choice; the design-template mockup describes immediate summary updates. Both claims remain separate, with no identity or contradiction asserted.",
        },
        {
            "ids": list(missing[1]),
            "review": "Returning front-and-handle and budget-tracking journeys both show changes to saved choices, but concern different choices and remain separate requirements. No identity or contradiction is asserted.",
        },
    ],
    "removed_checked_pairs": [list(extra[0])],
    "retained_relation_count": len(correction.relations),
    "checked_record_count": len(correction.checked_ids),
    "checked_pair_count": len(correction.checked_pairs),
    "validation": "All 36 records and 301 required pairs are covered; no extra pair, relation, or unresolved finding",
}
path = store.path(f"runs/{run_id}/claim-75-correction-proposal.json")
write_json(path, proposal)
print(json.dumps({"path": str(path), **proposal}, ensure_ascii=False, indent=2))
