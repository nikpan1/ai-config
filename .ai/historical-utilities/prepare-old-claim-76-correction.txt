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
revision = "objects/claim-comparison-4f0a01ff83a9c2d1138da42f65ae1cc1d6550c8e93b3502ed1cdc86813ce539d.json"
plan_ref = "objects/claim-plan-3bc4cdd4e7d74da7d4d2600a10dc54cc9aabbda21060d17a9000b747a5d33bc9.json"

task = comparison_at(store.get(plan_ref), 76, store)
original = Comparison.model_validate(store.get(revision))
required = {tuple(sorted(pair)) for pair in task["required_pairs"]}
retained = [
    relation
    for relation in original.relations
    if tuple(sorted((relation.left, relation.right))) in required
]
removed = [relation for relation in original.relations if relation not in retained]
corrected = original.model_copy(update={"relations": retained})

expected = set(task["left"] + task["right"])
assert set(corrected.checked_ids) == expected
assert len(corrected.checked_ids) == len(expected) == 37
assert {tuple(sorted(pair)) for pair in corrected.checked_pairs} == required
assert len(corrected.checked_pairs) == len(required) == 299
assert len(removed) == 14
assert all(relation.kind == "variant" for relation in removed)
assert len(retained) == 22
assert not corrected.findings

comparison_ref = store.put(corrected, "claim-comparison-correction-proposal")
proposal = {
    "run_id": run_id,
    "task_id": task["id"],
    "original_revision": revision,
    "comparison_ref": comparison_ref,
    "removed_relations": [item.model_dump() for item in removed],
    "retained_relation_count": len(retained),
    "checked_record_count": len(corrected.checked_ids),
    "checked_pair_count": len(corrected.checked_pairs),
    "validation": "complete records and pairs; no out-of-scope relation or unresolved finding",
}
path = store.path(f"runs/{run_id}/claim-76-correction-proposal.json")
write_json(path, proposal)
print(json.dumps({"path": str(path), **proposal}, ensure_ascii=False, indent=2))
