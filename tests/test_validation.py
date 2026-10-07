from pathlib import Path

import pytest
from conftest import approve, complete

from docgen.authoring import validate_draft
from docgen.models import Draft, Knowledge, Outline, SemanticReview
from docgen.storage import Store
from docgen.validation import check_links
from docgen.workflow import run_pipeline


def test_unsupported_blocks_and_quotation_mismatch(store, model):
    store = complete(store, model)
    graph = Knowledge.model_validate(store.output("review_knowledge")["artifact"])
    outline = Outline.model_validate(store.output("review_outline")["artifact"])
    draft = Draft.model_validate(store.output("compose"))
    parsed = store.output("parse")
    draft.chapters[0].blocks[0].claim_ids = ["invented"]
    parsed["spans"][0]["excerpt"] = "changed"
    findings = validate_draft(draft, outline, graph, parsed, store.root)
    assert any("unknown claim" in f.message for f in findings)
    assert any("quotation mismatch" in f.message for f in findings)


def test_bounded_semantic_repairs_block_export(store, model):
    original = model.call

    def call(prompt, context, schema, directory, images=None):
        if prompt == "review_semantics":
            return SemanticReview(
                findings=[
                    {"severity": "error", "artifact_id": "block-0", "message": "Dropped condition"}
                ]
            )
        return original(prompt, context, schema, directory, images)

    model.call = call
    run_pipeline(store, model)
    approve(Store(store.root), model)
    approve(Store(store.root), model)
    store = Store(store.root)
    assert len(store.stage("compose")["attempts"]) == 3
    assert store.stage("export")["status"] == "pending"
    assert not store.output("validate")["passed"]
    with pytest.raises(ValueError, match="validation errors"):
        approve(Store(store.root), model)


def test_export_links_detect_escapes_and_missing_targets(tmp_path):
    root = tmp_path / "export"
    root.mkdir()
    root.joinpath("README.md").write_text(
        "[Missing](gone.md)\n\n[Outside](../private.md)\n", "utf-8"
    )
    tmp_path.joinpath("private.md").write_text("exists outside", "utf-8")
    assert len(check_links(root)) == 2


def test_purge_recovers_and_removes_sqlite_payloads(store, model, monkeypatch):
    store = complete(store, model)
    monkeypatch.setattr(store, "cleanup", lambda: (_ for _ in ()).throw(OSError("interrupted")))
    with pytest.raises(OSError):
        store.reset("reconcile", purge=True)
    store = Store(store.root)
    assert store.manifest["cleanup"]
    assert store.active("reconcile") is None
    with store.lock():
        pass
    assert not store.manifest["cleanup"]
    import sqlite3

    with sqlite3.connect(store.root / "knowledge.sqlite") as db:
        remaining = {row[0] for row in db.execute("SELECT hash FROM revisions").fetchall()}
        assert remaining == {store.active("extract")["output_hash"]}
    assert Path(store.manifest["exports"][0]["path"]).exists()


def test_budget_change_keeps_completed_upstream(store, model):
    from docgen.config import Settings

    run_pipeline(store, model)
    original = store.active("extract")["id"]
    updated = Settings.model_validate(store.manifest["settings"]).model_copy(
        update={"max_calls": 999}
    )
    run_pipeline(store, model, settings=updated)
    assert store.active("extract")["id"] == original
