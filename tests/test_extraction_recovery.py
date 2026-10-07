import pytest

from docgen.storage import Store, read_json
from docgen.workflow import run_pipeline


def test_invalid_coverage_is_repaired_without_loosening_validation(store, model):
    original = model.call
    repairs = []

    def call(prompt, context, schema, directory, images=None):
        if prompt == "repair_extraction":
            repairs.append(context["validation_error"])
            return original("extract_claims", context, schema, directory, images)
        result = original(prompt, context, schema, directory, images)
        if prompt == "extract_claims":
            row = next(r for r in result.coverage if r.claim_ids)
            row.evidence_id = context["spans"][0]["id"]
        return result

    model.call = call
    run_pipeline(store, model)
    assert repairs == ["Coverage claim does not reference its evidence"]
    assert store.stage("review_knowledge")["status"] == "waiting_for_review"
    directory = store.attempt_dir("extract", store.active("extract"))
    assert (directory / "batch-drafts/0-0-error.json").exists()
    assert (directory / "batch-drafts/0-1.json").exists()


def test_failed_extraction_reuses_batches_but_explicit_reset_does_not(store, model, monkeypatch):
    monkeypatch.setattr("docgen.workflow.batches", lambda spans, limit: [[s] for s in spans])
    original = model.call
    requests = []
    fail = True

    def call(prompt, context, schema, directory, images=None):
        if prompt == "extract_claims":
            requests.append(context["spans"][0]["id"])
            if fail and len(requests) == 3:
                raise ValueError("Injected transient failure")
        return original(prompt, context, schema, directory, images)

    model.call = call
    with pytest.raises(ValueError, match="Injected"):
        run_pipeline(store, model)
    fail = False
    first_two = requests[:2]
    run_pipeline(store, model)
    assert all(requests.count(span_id) == 1 for span_id in first_two)
    directory = store.attempt_dir("extract", store.active("extract"))
    assert read_json(directory / "batches/0.receipt.json")["reused_from"] == 1
    with store.lock():
        store.reset("extract")
    run_pipeline(store, model)
    assert all(requests.count(span_id) == 2 for span_id in first_two)


def test_repair_exhaustion_is_bounded_and_does_not_commit(store, model):
    original = model.call
    repairs = []

    def call(prompt, context, schema, directory, images=None):
        if prompt == "repair_extraction":
            repairs.append(prompt)
        result = original(
            "extract_claims" if prompt == "repair_extraction" else prompt,
            context,
            schema,
            directory,
            images,
        )
        if prompt in {"extract_claims", "repair_extraction"}:
            next(r for r in result.coverage if r.claim_ids).evidence_id = context["spans"][0]["id"]
        return result

    model.call = call
    with pytest.raises(ValueError, match="Coverage claim"):
        run_pipeline(store, model)
    assert len(repairs) == 2
    store = Store(store.root)
    assert store.stage("extract")["status"] == "failed"
    assert not (store.attempt_dir("extract", store.active("extract")) / "output.json").exists()
