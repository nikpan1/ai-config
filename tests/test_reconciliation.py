import pytest

from docgen.models import Claim, Coverage, Entity, EvidenceRef, Knowledge, Resolution
from docgen.reconciliation import conflict_batches, identity_batches, size, validate_resolution
from docgen.storage import Store, read_json
from docgen.workflow import run_pipeline


def graph_fixture():
    return Knowledge(
        entities=[
            Entity(id=f"e{i}", type="capability", name="Retry", evidence_ids=[f"s{i}"])
            for i in range(3)
        ],
        claims=[
            Claim(
                id=f"c{i}",
                assertion=f"Retry limit is {i}.",
                entity_ids=[f"e{i}"],
                evidence_ids=[f"s{i}"],
            )
            for i in range(3)
        ],
        relationships=[],
        coverage=[
            Coverage(evidence_id=f"s{i}", disposition="covered", claim_ids=[f"c{i}"])
            for i in range(3)
        ],
        evidence=[EvidenceRef(id=f"s{i}", kind="text", span_id=f"s{i}") for i in range(3)],
    )


def test_identity_groups_respect_type_scope_version_and_limit():
    graph = graph_fixture()
    batches, gaps = identity_batches(graph, 5000)
    assert not gaps and len(batches) == 1 and size(batches[0]) <= 5000
    graph.entities[2].version = "v2"
    graph.entities[1].type = "process"
    assert identity_batches(graph, 5000) == ([], [])
    batches, gaps = identity_batches(graph_fixture(), 100)
    assert not batches and "left unmerged" in gaps[0]


def test_conflict_batches_include_every_claim_and_explicit_cross_topic_groups():
    graph = graph_fixture()
    for i, entity in enumerate(graph.entities):
        entity.name = f"Different feature {i}"
    parsed = {
        "spans": [
            {
                "id": f"s{i}",
                "path": "source.md",
                "headings": [f"Feature {i}"],
                "excerpt": "Conflict group: GROUP-1",
            }
            for i in range(3)
        ]
    }
    batches, _ = conflict_batches(graph, parsed, 4000)
    assert all(size(batch) <= 4000 for batch in batches)
    groups = [g for batch in batches for g in batch["groups"]]
    assert {c["id"] for g in groups for c in g["claims"]} == {"c0", "c1", "c2"}
    assert len(next(g for g in groups if g["topic"].startswith("source-conflict"))["claims"]) == 3
    graph.claims[0].assertion = "x" * 5000
    with pytest.raises(ValueError, match="exceeds"):
        conflict_batches(graph, parsed, 4000)


def test_resolution_rejects_cross_batch_aliases_and_duplicate_claim_conflicts():
    graph = graph_fixture()
    context = {"groups": [{"entities": [graph.entities[0].model_dump()]}]}
    with pytest.raises(ValueError, match="outside"):
        validate_resolution(Resolution(aliases={"e0": "e1"}), context, graph, True)
    context = {"groups": [{"claims": [{"id": "c0"}]}]}
    result = Resolution(conflicts=[{"id": "bad", "claim_ids": ["c0", "c0"], "description": "bad"}])
    with pytest.raises(ValueError, match="competing"):
        validate_resolution(result, context, graph, False)


def test_invalid_resolution_is_repaired_and_saved(store, model):
    original = model.call
    calls = []

    def call(prompt, context, schema, directory, images=None):
        if prompt == "reconcile_entities":
            calls.append(context)
            if len(calls) == 1:
                return Resolution(aliases={"unknown": "also-unknown"})
        return original(prompt, context, schema, directory, images)

    model.call = call
    run_pipeline(store, model)
    assert len(calls) == 2 and "validation_error" in calls[1]
    assert store.stage("review_knowledge")["status"] == "waiting_for_review"


def test_reconciliation_resume_reuses_verified_batches_but_reset_does_not(store, model):
    original = model.call
    fail = True

    def call(prompt, context, schema, directory, images=None):
        if fail and prompt == "detect_conflicts":
            raise ValueError("Injected conflict failure")
        return original(prompt, context, schema, directory, images)

    model.call = call
    with pytest.raises(ValueError, match="Injected"):
        run_pipeline(store, model)
    fail = False
    initial = model.calls.count("reconcile_entities")
    run_pipeline(store, model)
    assert model.calls.count("reconcile_entities") == initial
    directory = store.attempt_dir("reconcile", store.active("reconcile"))
    assert read_json(directory / "batches/reconcile_entities-0.receipt.json")["reused_from"] == 1
    with store.lock():
        store.reset("reconcile")
    run_pipeline(Store(store.root), model)
    assert model.calls.count("reconcile_entities") == initial + 1


def test_reconciliation_repair_is_bounded(store, model):
    original = model.call
    requests = []

    def call(prompt, context, schema, directory, images=None):
        if prompt == "reconcile_entities":
            requests.append(prompt)
            return Resolution(aliases={"unknown": "unknown"})
        return original(prompt, context, schema, directory, images)

    model.call = call
    with pytest.raises(ValueError, match="outside"):
        run_pipeline(store, model)
    assert len(requests) == 3
    assert store.stage("reconcile")["status"] == "failed"
