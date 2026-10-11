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
revision = "objects/entity-comparison-64d3794784191b23dc48793c8e82fd7cb8e7fd17e1395d21e2aef8daefb1c22e.json"
plan_ref = "objects/entity-plan-796c6fc4a8df187091c3ed83acaa298e0fae1c871d843ae1f24e7f31b160cdb9.json"

task = comparison_at(store.get(plan_ref), 114, store)
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
assert len(corrected.checked_ids) == len(expected) == 24
assert {tuple(sorted(pair)) for pair in corrected.checked_pairs} == required
assert len(corrected.checked_pairs) == len(required) == 261
assert len(removed) == 4
assert all(relation.kind == "same_entity" for relation in removed)
assert len(retained) == 27
assert not corrected.findings

comparison_ref = store.put(corrected, "entity-comparison-correction-proposal")
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
path = store.path(f"runs/{run_id}/entity-114-correction-proposal.json")
write_json(path, proposal)
print(json.dumps({"path": str(path), **proposal}, ensure_ascii=False, indent=2))
