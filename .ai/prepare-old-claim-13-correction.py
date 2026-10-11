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
revision = "objects/claim-comparison-97d4076358d4eecde0e0c44edfe561066cc7be13ddff9009d6d830be44ded5d5.json"
plan_ref = "objects/claim-plan-6aae7e516a5c21930573a52f232a3438f330c8bd7c19ebc51fc1c82a70b92666.json"

task = comparison_at(store.get(plan_ref), 13, store)
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
assert len(corrected.checked_ids) == len(expected) == 20
assert {tuple(sorted(pair)) for pair in corrected.checked_pairs} == required
assert len(corrected.checked_pairs) == len(required) == 184
assert len(removed) == 6
assert all(relation.kind == "variant" for relation in removed)
assert len(retained) == 10
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
path = store.path(f"runs/{run_id}/claim-13-correction-proposal.json")
write_json(path, proposal)
print(json.dumps({"path": str(path), **proposal}, ensure_ascii=False, indent=2))
