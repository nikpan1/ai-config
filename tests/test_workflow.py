import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import approve, complete
from filelock import FileLock

from docgen.config import Settings
from docgen.models import ReviewDecision
from docgen.storage import Store, digest, read_json
from docgen.workflow import run_pipeline


def test_complete_restart_reset_and_purge(store, model):
    result = run_pipeline(store, model)
    assert result["status"] == "waiting_for_review"
    waiting = store.active("review_knowledge")
    assert not (store.attempt_dir("review_knowledge", waiting) / "output.json").exists()
    with sqlite3.connect(store.root / "checkpoints.sqlite") as db:
        assert db.execute("SELECT count(*) FROM checkpoints").fetchone()[0] > 0
    before = list(model.calls)
    run_pipeline(Store(store.root), model)
    assert model.calls == before
    for _ in range(3):
        approve(Store(store.root), model)
    store = Store(store.root)
    assert store.manifest["status"] == "completed"
    old_export = Path(store.output("export")["path"])
    assert old_export.joinpath("audit/provenance.json").exists()
    source_hash = store.active("inventory")["output_hash"]
    outline_hash = store.active("review_outline")["output_hash"]
    old_execution = store.manifest["execution_id"]
    with store.lock():
        dry = store.reset("compose", dry_run=True)
        assert store.manifest["execution_id"] == old_execution
        assert dry["stages"] == ["compose", "validate", "review_documentation", "export"]
        store.reset("compose", purge=True)
    assert store.active("inventory")["output_hash"] == source_hash
    assert store.active("review_outline")["output_hash"] == outline_hash
    assert store.manifest["execution_id"] != old_execution
    assert old_export.exists()
    assert store.stage("compose")["attempts"][0]["status"] == "purged"
    assert not store.attempt_dir("compose", store.stage("compose")["attempts"][0]).exists()
    count = model.calls.count("compose_chapter")
    run_pipeline(store, model)
    assert model.calls.count("compose_chapter") == count + 1
    assert store.stage("review_documentation")["status"] == "waiting_for_review"
    approve(Store(store.root), model)
    store = Store(store.root)
    with store.lock():
        store.reset("extract")
    assert store.stage("parse")["status"] == "completed"
    assert store.stage("review_knowledge")["status"] == "pending"
    assert store.stage("outline")["status"] == "pending"


def test_failed_attempt_retained_and_retried(store, model):
    model.fail = "extract_claims"
    with pytest.raises(ValueError, match="Injected"):
        run_pipeline(store, model)
    failed = store.active("extract")
    directory = store.attempt_dir("extract", failed)
    assert failed["status"] == "failed"
    assert (directory / "input.json").exists() and (directory / "error.json").exists()
    assert not (directory / "output.json").exists()
    model.fail = None
    run_pipeline(Store(store.root), model)
    store = Store(store.root)
    assert store.active("extract")["id"] == 2


def test_stale_approval_and_deleted_dependency(store, model):
    run_pipeline(store, model)
    bad = ReviewDecision(revision="old", reviewer="R", action="approve", rationale="ok")
    with pytest.raises(ValueError, match="Outdated"):
        run_pipeline(store, model, bad)
    revision = digest(store.output("reconcile"))
    (store.attempt_dir("extract", store.active("extract")) / "output.json").unlink()
    with pytest.raises(ValueError, match="stale"):
        run_pipeline(store, model, bad.model_copy(update={"revision": revision}))
    store = Store(store.root)
    assert store.stage("extract")["status"] == "pending"
    assert store.stage("review_knowledge")["status"] == "pending"


def test_prompt_change_invalidates_only_consumers(store, model, monkeypatch):
    store = complete(store, model)
    from docgen import llm

    original = llm.load_prompt

    def changed(name):
        spec, checksum, raw = original(name)
        return spec, "changed" if name == "compose_chapter" else checksum, raw

    monkeypatch.setattr(llm, "load_prompt", changed)
    with store.lock():
        warnings = store.verify(Settings.model_validate(store.manifest["settings"]))
    assert "compose" in warnings[0]
    assert store.stage("review_outline")["status"] == "completed"
    assert store.stage("compose")["status"] == "pending"


def test_worker_lock(store):
    with FileLock(store.root / ".worker.lock"):
        with pytest.raises(ValueError, match="worker"):
            with store.lock():
                pass


def test_conflict_requires_resolution(store, model):
    run_pipeline(store, model)
    graph = store.output("reconcile")
    for claim in graph["claims"]:
        claim["status"] = "accepted"
    graph["conflicts"] = [
        {
            "id": "conflict-1",
            "claim_ids": [c["id"] for c in graph["claims"][:2]],
            "description": "Competing versions",
            "status": "unresolved",
            "rationale": "",
        }
    ]
    with pytest.raises(ValueError, match="conflicts"):
        approve(store, model, graph)
    graph["claims"][0]["status"] = "rejected"
    graph["conflicts"][0].update(status="resolved", rationale="Use reviewed version")
    approve(store, model, graph)
    store = Store(store.root)
    assert store.stage("outline")["status"] == "completed"
    assert (
        graph["claims"][0]["id"] not in store.output("outline")["chapters"][0]["required_claim_ids"]
    )


def test_cancel_defer_and_revision_feedback(store, model):
    run_pipeline(store, model)
    decision = ReviewDecision(
        revision=digest(store.output("reconcile")),
        reviewer="R",
        action="defer",
        rationale="Need more evidence",
    )
    run_pipeline(store, model, decision)
    assert Store(store.root).manifest["status"] == "waiting_for_review"
    run_pipeline(store, model, decision.model_copy(update={"action": "cancel"}))
    with pytest.raises(ValueError, match="cancelled"):
        run_pipeline(Store(store.root), model)
    run_pipeline(Store(store.root), model, decision.model_copy(update={"action": "revise"}))
    assert Store(store.root).manifest["feedback"]["reconcile"] == "Need more evidence"


def test_cli_reads_persisted_run_in_new_process(store, model):
    run_pipeline(store, model)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "docgen.cli",
            "review",
            store.manifest["run_id"],
            "--runs",
            str(store.root.parent),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["revision"] == digest(store.output("reconcile"))
    inspected = subprocess.run(
        [
            sys.executable,
            "-m",
            "docgen.cli",
            "show",
            store.manifest["run_id"],
            "--stage",
            "extract",
            "--attempt",
            "1",
            "--runs",
            str(store.root.parent),
        ],
        capture_output=True,
        text=True,
    )
    assert inspected.returncode == 0, inspected.stderr
    assert json.loads(inspected.stdout)["metadata"]["status"] == "completed"


def test_portable_export_and_all_checksums(store, model, tmp_path):
    store = complete(store, model)
    destination = Path(store.output("export")["path"])
    relocated = tmp_path / "moved-export"
    shutil.copytree(destination, relocated)
    checksums = read_json(relocated / "checksums.json")
    for name, checksum in checksums.items():
        assert digest((relocated / name).read_bytes()) == checksum
    from markdown_it import MarkdownIt

    for document in relocated.rglob("*.md"):
        for token in MarkdownIt().parse(document.read_text("utf-8")):
            for child in token.children or []:
                if child.type in {"link_open", "image"}:
                    target = child.attrGet("href") or child.attrGet("src")
                    assert (document.parent / target.split("#")[0]).exists(), (document, target)
