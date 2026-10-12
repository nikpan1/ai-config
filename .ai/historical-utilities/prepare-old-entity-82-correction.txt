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
revision = "objects/entity-comparison-ab4f5d0346a8bce25d56d8c36736ef48cfdb2e9040da3266ccaab521c3a2e7b1.json"
plan_ref = "objects/entity-plan-796c6fc4a8df187091c3ed83acaa298e0fae1c871d843ae1f24e7f31b160cdb9.json"
plan = store.get(plan_ref)
task = comparison_at(plan, 82, store)
original = Comparison.model_validate(store.get(revision))
removed = [relation for relation in original.relations if relation.kind == "same_entity"]
corrected = original.model_copy(
    update={"relations": [relation for relation in original.relations if relation.kind != "same_entity"]}
)
required = {tuple(sorted(pair)) for pair in task["required_pairs"]}
checked = [tuple(sorted(pair)) for pair in corrected.checked_pairs]
expected = set(task["left"] + task["right"])
assert set(corrected.checked_ids) == expected
assert len(corrected.checked_ids) == len(expected)
assert set(checked) == required
assert len(checked) == len(required)
assert not corrected.findings
assert all(tuple(sorted((item.left, item.right))) in required for item in corrected.relations)
assert len(removed) == 4
assert len(corrected.relations) == 7
comparison_ref = store.put(corrected, "entity-comparison-correction-proposal")
proposal = {
    "run_id": run_id,
    "task_id": task["id"],
    "original_revision": revision,
    "comparison_ref": comparison_ref,
    "removed_relations": [item.model_dump() for item in removed],
    "retained_relation_count": len(corrected.relations),
    "checked_record_count": len(corrected.checked_ids),
    "checked_pair_count": len(corrected.checked_pairs),
    "validation": "complete records and pairs; no out-of-scope relation or unresolved finding",
}
path = store.path(f"runs/{run_id}/entity-82-correction-proposal.json")
write_json(path, proposal)
print(json.dumps({"path": str(path), **proposal}, ensure_ascii=False, indent=2))
