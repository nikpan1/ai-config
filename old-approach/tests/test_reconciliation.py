from itertools import combinations

import pytest

from docgen.reconciliation import (
    comparison_at,
    comparison_count,
    comparison_tasks,
    entity_register,
    iter_comparisons,
    replace_comparison,
    split_comparison,
)
from docgen.review import validate_decisions


def entity(identifier, scope="tenant-a"):
    return {
        "id": identifier,
        "canonical_name": "Policy",
        "aliases": ["contract"],
        "kind": "object",
        "scope": scope,
        "version": None,
        "definition": "Draft boundary",
        "evidence": [{"block_id": "b1", "excerpt": "policy"}],
        "review_status": "verified",
    }


def test_partitioned_comparisons_cover_every_candidate_pair():
    records = [entity(f"e{number}") for number in range(30)]
    plan = comparison_tasks(records, "entities", 1024)
    performed = set()
    for task in plan["tasks"]:
        if task["right"]:
            performed.update(
                tuple(sorted((left, right))) for left in task["left"] for right in task["right"]
            )
        else:
            performed.update(tuple(sorted(pair)) for pair in combinations(task["left"], 2))
    expected = {
        tuple(sorted(pair)) for pair in combinations([record["id"] for record in records], 2)
    }
    assert performed == expected
    assert not plan["unperformed"]


def test_persisted_queue_matches_exhaustive_candidate_policy_and_split(store):
    records = [entity(f"e{number}") for number in range(500)]
    expected = comparison_tasks(records, "entities", 2048)
    stored = comparison_tasks(records, "entities", 2048, store=store)
    assert "tasks" not in stored
    assert len(store.get(stored["tasks_ref"])["parts"]) > 1
    assert list(iter_comparisons(stored, store)) == expected["tasks"]
    assert comparison_count(stored) == len(expected["tasks"])
    position = len(expected["tasks"]) // 2
    task = comparison_at(stored, position, store)
    children = split_comparison(task)
    assert children
    changed = replace_comparison(stored, position, children, store)
    expected["tasks"][position : position + 1] = children
    assert list(iter_comparisons(changed, store)) == expected["tasks"]
    assert comparison_count(changed) == comparison_count(stored) - 1 + len(children)


def test_register_never_merges_similar_names_without_decision():
    records = [entity("e1"), entity("e2")]
    register, mapping = entity_register(records, [])
    assert len(register) == 2
    assert mapping == {"e1": "e1", "e2": "e2"}
    decision = {"action": "merge_entities", "entity_ids": ["e1", "e2"]}
    register, mapping = entity_register(records, [decision])
    assert len(register) == 1
    assert set(register[0]["members"]) == {"e1", "e2"}
    assert mapping["e2"] == "e1"
    with pytest.raises(ValueError, match="scope"):
        entity_register([entity("e1"), entity("e2", "tenant-b")], [decision])


def test_stale_approval_and_conflicting_authority_are_not_generic_approval():
    issue = {"id": "issue1", "kind": "conflict", "record_ids": ["a:c1", "b:c1"], "revision": "r1"}
    decision = {
        "issue_id": "issue1",
        "revision": "r0",
        "action": "select_authority",
        "claim_ids": ["a:c1"],
        "reviewer": "fixture",
        "rationale": "Choose dated source",
    }
    with pytest.raises(ValueError, match="revision"):
        validate_decisions([decision], [issue], "r1")
    decision["revision"] = "r1"
    assert validate_decisions([decision], [issue], "r1")[0].claim_ids == ["a:c1"]
    decision["action"] = "acknowledge_unknown"
    with pytest.raises(ValueError, match="conflicts"):
        validate_decisions([decision], [issue], "r1")
