import base64
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

import pytest

from docgen_graph.inspection import export_run
from docgen_graph.inspection.quality import quality_data
from docgen_graph.inspection.reader import RunReader, redact, safe_sql_value
from docgen_graph.stages import StageArtifacts
from docgen_graph.storage import ArtifactStore, digest


@pytest.fixture
def recorded(tmp_path):
    workspace = tmp_path / "workspace with spaces ł"
    store = ArtifactStore(workspace)
    run = workspace / "runs" / "example"
    run.mkdir(parents=True)
    db = sqlite3.connect(run / "graph.sqlite")
    db.executescript(
        "CREATE TABLE nodes(id TEXT,type TEXT,name TEXT,scope TEXT);"
        "CREATE TABLE edges(source_id TEXT,target_id TEXT,type TEXT,method TEXT,evidence_id TEXT);"
        "CREATE TABLE evidence(id TEXT,path TEXT,text TEXT,label TEXT);"
        "CREATE TABLE assertions(id TEXT,statement TEXT);"
        "CREATE TABLE support(assertion_id TEXT,evidence_id TEXT);"
        "CREATE TABLE verified_relations(id TEXT,payload TEXT);"
    )
    db.executemany(
        "INSERT INTO nodes VALUES (?,?,?,?)",
        [(f"node-{i:04}", "Assertion", f"Fact {i}", "test") for i in range(203)],
    )
    db.executemany(
        "INSERT INTO edges VALUES (?,?,?,?,?)",
        [
            ("node-0000", "node-0202", "RELATED", "exact-subject", "e1"),
            ("node-0000", "node-0202", "RELATED", "verified-code", "e2"),
            ("node-0001", "node-0001", "SELF", "recorded", None),
            ("node-0001", "missing", "RELATED", "recorded", None),
        ],
    )
    db.execute("INSERT INTO evidence VALUES (?,?,?,?)", ("e1", "source.json", '{"x":1}', "D1"))
    db.execute("INSERT INTO assertions VALUES (?,?)", ("node-0000", '["literal statement"]'))
    db.execute("INSERT INTO support VALUES (?,?)", ("node-0000", "e1"))
    db.execute(
        "INSERT INTO verified_relations VALUES (?,?)",
        (
            "rel",
            json.dumps(
                {"source_id": "node-0000", "target_id": "node-0202", "evidence_ids": ["e1", "e2"]}
            ),
        ),
    )
    db.commit()
    db.close()
    stages = StageArtifacts(store, "example")
    stages.initialize("autopilot", "test", "test")
    text_ref = store.put({"markdown": "The why and what </script><script>evil()</script>"})
    stages.record("write_section", {"section_index": 0}, {"written_ref": text_ref})
    stages.record(
        "write_section", {"section_index": 0}, {"written_ref": text_ref, "status": "repair"}
    )
    stages.pending(
        "review_stage", {"stage": "write_section", "item": "0000", "hash": "x", "path": "none"}
    )
    stages.skip("analyze_code_unit", "No code in this run")
    store.event("example", "write_section", "model_request", api_key="secret-sentinel")
    with (run / "events.jsonl").open("ab") as output:
        output.write(b"{broken}\n")
    store.event("example", "write_section", "model_response", message="Bearer ABCDEFGHIJKL")
    db = sqlite3.connect(workspace / "checkpoints.sqlite")
    db.executescript(
        "CREATE TABLE checkpoints(thread_id TEXT,checkpoint_id TEXT,parent_checkpoint_id TEXT,"
        "checkpoint_ns TEXT,type TEXT,checkpoint BLOB,metadata TEXT);"
        "CREATE TABLE writes(thread_id TEXT,checkpoint_id TEXT,task_id TEXT,"
        "channel TEXT,value BLOB);"
    )
    db.execute(
        "INSERT INTO checkpoints VALUES (?,?,?,?,?,?,?)",
        ("example", "c2", "c1", "", "msgpack", b"\x80\x04UNSAFE_PICKLE", '{"step":2}'),
    )
    db.execute(
        "INSERT INTO checkpoints VALUES (?,?,?,?,?,?,?)",
        ("other", "private", "", "", "json", b"{}", "{}"),
    )
    db.execute(
        "INSERT INTO writes VALUES (?,?,?,?,?)",
        ("example", "c2", "task", "__interrupt__", b"\x00opaque"),
    )
    db.commit()
    db.close()
    return workspace, text_ref


def file_state(root):
    return {
        str(path.relative_to(root)): (digest(path.read_bytes()), path.stat().st_mtime_ns)
        for path in root.rglob("*")
        if path.is_file()
    }


def test_full_graph_all_revisions_and_read_only_inputs(recorded, tmp_path):
    workspace, _ = recorded
    before = file_state(workspace)
    result = export_run(workspace, "example", tmp_path / "export")
    data = json.loads(Path(result["json"]).read_text("utf-8"))
    assert file_state(workspace) == before
    graph = data["graphs"][0]
    assert {node["id"] for node in graph["tables"]["nodes"]} == {f"node-{i:04}" for i in range(203)}
    assert len(graph["tables"]["edges"]) == 4
    assert graph["tables"]["evidence"][0]["text"] == '{"x":1}'
    assert graph["tables"]["assertions"][0]["statement"] == '["literal statement"]'
    assert graph["tables"]["verified_relations"][0]["payload"]["evidence_ids"] == ["e1", "e2"]
    assert len([stage for stage in data["stages"] if stage.get("result")]) == 2
    statuses = {stage["manifest"]["value"].get("status") for stage in data["stages"]}
    assert {"pending", "skipped"} <= statuses
    assert [event["line"] for event in data["events"]] == [1, 3]
    assert any(item["source"] == "events.jsonl:2" for item in data["diagnostics"])
    assert data["checkpoints"]["checkpoints"][0]["checkpoint"]["encoding"] == "opaque"
    assert len(data["checkpoints"]["checkpoints"]) == 1
    assert data["checkpoints"]["writes"][0]["channel"] == "__interrupt__"


def test_standalone_html_payload_and_csp(recorded, tmp_path):
    workspace, _ = recorded
    result = export_run(workspace, "example", tmp_path / "export")
    html = Path(result["html"]).read_text("utf-8")
    assert "secret-sentinel" not in Path(result["json"]).read_text("utf-8")
    assert "ABCDEFGHIJKL" not in Path(result["json"]).read_text("utf-8")
    assert "<script>evil()" not in html
    payload = re.search(r'<div id="dataset" hidden>([^<]+)</div>', html)[1]
    assert json.loads(base64.b64decode(payload))["run_id"] == "example"
    scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
    assert len(scripts) == 1
    expected = base64.b64encode(hashlib.sha256(scripts[0].encode()).digest()).decode()
    assert f"script-src 'sha256-{expected}'" in html
    assert "connect-src 'none'" in html
    assert "fetch(" not in scripts[0]
    assert "innerHTML" not in scripts[0]
    assert "eval(" not in scripts[0]
    assert scripts[0].isascii()
    style = re.search(r"<style>(.*?)</style>", html, re.S)[1]
    style_hash = base64.b64encode(hashlib.sha256(style.encode()).digest()).decode()
    assert f"style-src 'sha256-{style_hash}'" in html


def test_missing_corrupt_and_unsafe_references(recorded, tmp_path):
    workspace, existing = recorded
    store = ArtifactStore(workspace)
    corrupt_path = workspace / "objects" / existing[:2] / existing
    corrupt_path.write_text('{"content":"changed"}', "utf-8")
    StageArtifacts(store, "example").record(
        "edit_page", {}, {"missing_ref": "a" * 64, "bad_ref": "../../.env"}
    )
    candidate = workspace / "runs" / "example" / "candidates" / "candidate"
    candidate.mkdir(parents=True)
    (workspace / "runs" / "example" / "AUTH.JSON").write_text("TOP_SECRET", "utf-8")
    (candidate / "candidate-manifest.json").write_text(
        json.dumps({"../../AUTH.JSON": "b" * 64}), "utf-8"
    )
    data = RunReader(workspace, "example").read()
    assert data["artifacts"][existing]["status"] == "corrupt"
    assert data["artifacts"]["a" * 64]["status"] == "unavailable"
    assert data["candidates"][0]["files"]["../../AUTH.JSON"]["status"] == "unavailable"
    assert "TOP_SECRET" not in json.dumps(data)
    assert any("not followed" in item["message"] for item in data["diagnostics"])


@pytest.mark.parametrize("run_id", ["../other", "a/b", "..", "a\\b"])
def test_invalid_run_identifier(recorded, run_id):
    workspace, _ = recorded
    with pytest.raises(ValueError):
        RunReader(workspace, run_id)


def test_unsafe_output_and_missing_inputs_create_nothing(recorded, tmp_path):
    workspace, _ = recorded
    before = file_state(workspace)
    for output in [workspace, workspace / "runs" / "example" / "debug", workspace / "objects"]:
        with pytest.raises(ValueError):
            export_run(workspace, "example", output)
    with pytest.raises(ValueError):
        export_run(workspace, "missing", tmp_path / "not-created")
    assert not (tmp_path / "not-created").exists()
    assert file_state(workspace) == before


def test_cli_never_loads_settings_or_constructs_paid_clients(recorded, tmp_path, monkeypatch):
    from docgen_graph import cli

    workspace, _ = recorded

    def forbidden(*args, **kwargs):
        raise AssertionError("Inspection must not initialize pipeline or models")

    monkeypatch.setattr(cli.Settings, "load", forbidden)
    monkeypatch.setattr(cli, "GeminiModel", forbidden)
    monkeypatch.setattr(cli, "Pipeline", forbidden)
    monkeypatch.setattr(cli, "ArtifactStore", forbidden)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docgen",
            "inspect-run",
            "--workspace",
            str(workspace),
            "--thread-id",
            "example",
            "--output",
            str(tmp_path / "export"),
        ],
    )
    assert cli.main() == 0


def test_ledger_scoped_to_run_and_safe_checkpoint_json(recorded, tmp_path):
    workspace, _ = recorded
    ledger = tmp_path / "ledger.sqlite"
    db = sqlite3.connect(ledger)
    db.execute(
        "CREATE TABLE charges(id TEXT,run_id TEXT,status TEXT,charged REAL,"
        "reserved REAL,usage TEXT,pricing TEXT)"
    )
    db.executemany(
        "INSERT INTO charges VALUES (?,?,?,?,?,?,?)",
        [
            ("1", "example", "settled", 2, 3, '{"input_tokens":12}', "{}"),
            ("2", "example", "uncertain", 4, 4, "{}", "{}"),
            ("3", "example", "reserved", 0, 5, "{}", "{}"),
            ("4", "other", "settled", 100, 100, "{}", "{}"),
        ],
    )
    db.commit()
    db.close()
    data = RunReader(workspace, "example", ledger).read()
    assert len(data["costs"]["charges"]) == 3
    assert {row["status"] for row in data["costs"]["charges"]} == {
        "settled",
        "uncertain",
        "reserved",
    }
    assert safe_sql_value(b'{"safe":true}')["value"] == {"safe": True}


def test_early_partial_run_is_usable(tmp_path):
    workspace = tmp_path / "workspace"
    (workspace / "runs" / "early").mkdir(parents=True)
    result = export_run(workspace, "early", tmp_path / "export")
    data = json.loads(Path(result["json"]).read_text("utf-8"))
    assert not data["graphs"][0]["tables"]
    assert data["diagnostics"]
    assert "not available" in json.dumps(data["diagnostics"])


def test_quality_denominators_and_passage_trace_use_recorded_revision():
    data = {
        "graphs": [
            {
                "id": "revision",
                "tables": {
                    "assertions": [{"id": "f1"}, {"id": "f2"}],
                    "support": [{"assertion_id": "f1", "evidence_id": "original"}],
                },
            }
        ],
        "artifacts": {
            "packet": {"value": {"assertions": [{"id": "f1"}]}},
            "plan": {
                "value": {
                    "graph_revision": "revision",
                    "sections": [{"obligation_ids": ["f1"], "supporting_obligation_ids": ["f2"]}],
                }
            },
        },
        "stages": [
            {
                "id": "stage/r1",
                "result": {
                    "value": {
                        "stage": "retrieve_section_evidence",
                        "inputs": {"graph_revision": "revision", "plan_ref": "plan"},
                        "outputs": {"packet_ref": "packet"},
                    }
                },
            }
        ],
        "candidates": [
            {
                "id": "c1",
                "files": {
                    "documentation/index.md": {"value": "😀 Valid fact."},
                    "audit.json": {
                        "value": {
                            "graph_revision": "revision",
                            "placements": [
                                {
                                    "start": 2,
                                    "end": 13,
                                    "passage": "Valid fact.",
                                    "obligation_ids": ["f1"],
                                },
                                {
                                    "start": 3,
                                    "end": 13,
                                    "passage": "Valid fact.",
                                    "obligation_ids": ["f1"],
                                },
                            ],
                        }
                    },
                },
            }
        ],
    }
    quality = quality_data(data)
    metric = quality["utilization"][0]
    assert metric["denominator"] == 2
    assert metric["retrieved"] == ["f1"]
    assert metric["assigned"] == ["f1", "f2"]
    assert quality["passages"][0]["offset_status"] == "verified"
    assert quality["passages"][0]["evidence_ids"] == ["original"]
    assert quality["passages"][1]["offset_status"] == "mismatch_or_unavailable"
    data["graphs"][0]["id"] = "unrelated"
    quality = quality_data(data)
    assert quality["utilization"][0]["retrieved"] is None
    assert quality["passages"][0]["graph_binding"] == "unavailable"
    assert quality["passages"][0]["evidence_ids"] == []


def test_wal_snapshot_preserves_uncheckpointed_rows_and_inputs(tmp_path):
    workspace = tmp_path / "workspace"
    run = workspace / "runs" / "wal-run"
    run.mkdir(parents=True)
    connection = sqlite3.connect(run / "graph.sqlite")
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE nodes(id TEXT, type TEXT, name TEXT, scope TEXT)")
        connection.execute("INSERT INTO nodes VALUES ('fresh','Assertion','Uncheckpointed','')")
        connection.commit()
        before = file_state(workspace)
        data = RunReader(workspace, "wal-run").read()
        assert data["graphs"][0]["tables"]["nodes"][0]["id"] == "fresh"
        assert file_state(workspace) == before
    finally:
        connection.close()


def test_symlink_escape_is_not_followed(recorded, tmp_path):
    workspace, _ = recorded
    external = tmp_path / "external"
    external.mkdir()
    (external / "candidate-manifest.json").write_text('{"private.txt":"hash"}', "utf-8")
    (external / "private.txt").write_text("UNRELATED_SECRET", "utf-8")
    candidate = workspace / "runs" / "example" / "candidates" / "escape"
    candidate.parent.mkdir()
    try:
        candidate.symlink_to(external, target_is_directory=True)
    except OSError:
        pytest.skip("Creating symlinks is unavailable on this Windows account")
    data = RunReader(workspace, "example").read()
    assert "UNRELATED_SECRET" not in json.dumps(data)
    assert any("Unsafe candidate" in item["message"] for item in data["diagnostics"])


def test_quoted_secret_and_source_script_remain_inert(recorded):
    workspace, _ = recorded
    ArtifactStore(workspace).event(
        "example", "test", "message", text="api_key='QUOTED_SECRET' javascript:evil() </script>"
    )
    data = RunReader(workspace, "example").read()
    assert "QUOTED_SECRET" not in json.dumps(data)
    assert "javascript:evil()" in json.dumps(data)
    assert data["capture"]["redactions"]["strings"] >= 2


def test_candidate_reference_is_not_a_missing_object(recorded):
    workspace, _ = recorded
    reader = RunReader(workspace, "example")
    reader.references({"candidate_ref": "c" * 64}, "stage")
    assert not reader.artifacts
    assert reader.trace_links[0]["kind"] == "candidate_reference"


def test_malformed_candidate_shape_preserved_with_diagnostic(recorded):
    workspace, _ = recorded
    store = ArtifactStore(workspace)
    base = "runs/example/candidates/malformed"
    content = json.dumps({"placements": "invalid", "mappings": {"incorrect": "shape"}})
    store.write(f"{base}/audit.json", content)
    store.write(
        f"{base}/candidate-manifest.json", json.dumps({"audit.json": digest(content.encode())})
    )
    data = RunReader(workspace, "example").read()
    assert data["candidates"][0]["files"]["audit.json"]["value"]["placements"] == "invalid"
    assert not data["quality"]["passages"]
    assert any("malformed rows" in item["message"] for item in data["diagnostics"])


def test_redaction_preserves_risk_run_identity_and_removes_standalone_key():
    value = "codex-risk-live-20261012-d /run/risk-source-20261012 sk-live12345678901234567890"
    counts = {"fields": 0, "strings": 0}
    assert redact(value, counts) == (
        "codex-risk-live-20261012-d /run/risk-source-20261012 [REDACTED]"
    )
    assert counts["strings"] == 1


def test_live_result_failure_is_visible_redacted_and_follows_declared_state_refs(recorded):
    workspace, _ = recorded
    store = ArtifactStore(workspace)
    reference = store.put({"issue": "Provenance mismatch in persisted state"})
    result = {
        "run_id": "example",
        "status": "graph_ready",
        "next": ["execute_authoring_tool"],
        "error": {"type": "ValueError", "message": "Unknown provenance", "api_key": "SENSITIVE"},
        "interrupts": [{"kind": "review"}],
        "state": {"issue_ref": reference},
    }
    store.write("runs/example/live-result.json", json.dumps(result))
    store.write("runs/example/unrelated.json", '{"private":"UNRELATED_SENTINEL"}')
    before = file_state(workspace)
    data = RunReader(workspace, "example").read()
    exported = data["run_files"]["live-result.json"]["value"]
    assert exported["error"] == {
        "type": "ValueError",
        "message": "Unknown provenance",
        "api_key": "[REDACTED]",
    }
    assert exported["status"] == "graph_ready"
    assert exported["next"] == ["execute_authoring_tool"]
    assert exported["interrupts"] == [{"kind": "review"}]
    assert reference in data["artifacts"]
    assert "UNRELATED_SENTINEL" not in json.dumps(data)
    assert file_state(workspace) == before
