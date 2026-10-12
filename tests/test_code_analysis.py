import subprocess
from types import SimpleNamespace

import pytest

from docgen_graph.code_analysis.backends import GeminiCodeBackend, SDKCodeBackend
from docgen_graph.code_analysis.history import freeze_history, parse_patch
from docgen_graph.code_analysis.inventory import CodeScope, scope_inventory, source_role
from docgen_graph.ingestion import code_spans, selected_files
from docgen_graph.knowledge import KnowledgeGraph, normalized_assertion
from docgen_graph.storage import ArtifactStore, digest


@pytest.mark.parametrize(
    "path", ["src/test/java/X.java", "tests/x.py", "a.spec.ts", "__tests__/a.ts"]
)
def test_test_roles(path):
    assert source_role(path) == "test_expectation"


def test_java_xml_patch_selected_secrets_lock_omitted(tmp_path):
    for name in [
        "Controller.java",
        "pom.xml",
        "form.html",
        "rule.diff",
        "application.properties",
        ".env",
        "package-lock.json",
    ]:
        (tmp_path / name).write_text("content")
    selected, omitted = selected_files(tmp_path, "code")
    assert {p.name for p in selected} == {
        "Controller.java",
        "pom.xml",
        "form.html",
        "rule.diff",
        "application.properties",
    }
    assert {p["path"] for p in omitted} == {".env", "package-lock.json"}


def test_entry_points_scopes_and_bounded_dependency_context():
    sources = {
        "RiskController.java": "import shared.Authorization;\n@RestController\n"
        'class RiskController {\n @PostMapping("/risk")\n'
        " void save() { if (!allowed) throw new Forbidden(); }\n}",
        "Authorization.java": "class Authorization { boolean allowed = false; }",
        "risk.component.html": '<button *ngIf="enabled" [disabled]="score > 5" '
        '(click)="submit()">Save</button>',
        "Trading.java": "class Trading { boolean sell = true; }",
    }
    spans, analysis = [], {}
    for path, text in sources.items():
        owned, meta = code_spans(
            {"kind": "code", "path": path, "hash": digest(text.encode())}, text
        )
        spans.extend(owned)
        analysis[path] = meta
    record = scope_inventory(
        {"spans": spans, "analysis": analysis},
        CodeScope(mode="feature", feature="risk", paths=["Risk*", "risk.*"]),
    )
    disposition = {f["path"]: f["disposition"] for f in record["files"]}
    assert disposition["Authorization.java"] == "supporting"
    assert disposition["Trading.java"] == "out_of_scope"
    assert {e["kind"] for e in analysis["risk.component.html"]["entry_points"]} >= {
        "visibility",
        "event",
    }
    assert analysis["RiskController.java"]["capability"] == "java_ts_text_index_v1"
    assert {u["evidence_ids"][0] for u in record["units"]} == {
        s["id"] for s in spans if s["path"] != "Trading.java"
    }


def test_sqlite_preserves_categories_provenance_and_relation(tmp_path):
    graph = KnowledgeGraph(tmp_path / "graph.sqlite")
    span = {
        "id": "e1",
        "kind": "code",
        "path": "a.java",
        "file_hash": digest(b"x"),
        "start_line": 1,
        "end_line": 1,
        "heading": "",
        "text": "x",
        "role": "implementation",
    }
    graph.add_evidence([span])
    graph.add_evidence([{**span, "id": "e2", "text": "y"}])
    first = normalized_assertion(
        {
            "statement": "Control requires flag",
            "evidence_ids": ["e1"],
            "conditions": ["flag enabled"],
            "categories": ["GUI", "PRODUCT_CONFIGURATION"],
            "provenance_ids": ["p1"],
            "temporal_status": "current_snapshot",
        },
        {"e1"},
    )
    second = normalized_assertion(
        {"statement": "Server requires role", "evidence_ids": ["e2"]}, {"e2"}
    )
    graph.add_assertions([first, second])
    relation = {
        "type": "QUALIFIES",
        "source_id": first["id"],
        "target_id": second["id"],
        "method": "verified",
        "evidence_ids": ["e1", "e2"],
    }
    graph.add_relations([relation])
    restored = KnowledgeGraph(graph.path)
    assert restored.assertion(first["id"])["categories"] == ["GUI", "PRODUCT_CONFIGURATION"]
    assert restored.assertion(first["id"])["provenance_ids"] == ["p1"]
    assert restored.relations()[0]["evidence_ids"] == ["e1", "e2"]
    assert restored.evidence("e2")["label"] == "C2"
    assert not restored.verify()


def test_patch_deleted_lines_historical_and_escape_rejected():
    patch = "--- a/Rule.java\n+++ b/Rule.java\n@@ -1 +1 @@\n-if (score > 5.1)\n+if (score > 5)"
    hunk = parse_patch(patch)[0]
    assert hunk["temporal_status"] == "historical" and "5.1" in hunk["text"]
    with pytest.raises(ValueError):
        parse_patch(patch.replace("a/Rule.java", "a/../../secret"))


def test_history_includes_deleted_and_renamed_files(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args):
        return subprocess.run(
            ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
        ).stdout.strip()

    git("init")
    git("config", "user.email", "fixture@example.invalid")
    git("config", "user.name", "Fixture")
    (repo / "Deleted.java").write_text("class Deleted {}\n")
    (repo / "Old.java").write_text("class Renamed {}\n")
    git("add", ".")
    git("commit", "-m", "base")
    base = git("rev-parse", "HEAD")
    (repo / "Deleted.java").unlink()
    (repo / "Old.java").rename(repo / "New.java")
    git("add", ".")
    git("commit", "-m", "head")
    history = freeze_history(
        ArtifactStore(tmp_path / "objects"),
        repo,
        CodeScope(base_commit=base, head_commit=git("rev-parse", "HEAD")),
        ["New.java"],
    )
    assert any(
        v["path"] == "Deleted.java" and v["side"] == "base" and v["status"] == "present"
        for v in history["versions"]
    )
    assert any(
        v["path"] == "Old.java" and v["side"] == "base" and v["status"] == "present"
        for v in history["versions"]
    )


class Transport:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, 0

    def capabilities(self):
        return {"status": "ok", "read_only": True}

    def run(self, payload):
        self.calls += 1
        if self.error:
            raise self.error
        return {"result": self.result, "session_id": "session-1", "request_id": "request-1"}

    def close(self):
        pass


class Allowance:
    def __init__(self):
        self.settlements = []

    def reserve(self, provider, model, request):
        return "reservation"

    def settle(self, reservation, usage):
        self.settlements.append((reservation, usage))


@pytest.mark.parametrize("provider", ["codex_sdk", "auggie_sdk"])
def test_sdk_contract_cache_errors_budget_and_provenance(tmp_path, provider):
    settings = SimpleNamespace(
        code_analysis_backend=provider,
        code_analysis_model="explicit-model",
        code_analysis_turn_limit=2,
        code_analysis_result_limit=10000,
    )
    store = ArtifactStore(tmp_path / provider)
    payload = {"spans": [{"id": "e1", "text": "flag"}], "scope_id": "scope"}
    raw = {
        "report": "Result",
        "details": [
            {"statement": "Flag required", "evidence_ids": ["e1"], "conditions": ["flag enabled"]}
        ],
    }
    transport, allowance = Transport(raw), Allowance()
    backend = SDKCodeBackend(
        settings, store, "run", tmp_path, transport=transport, allowance=allowance
    )
    packet = backend.analyze_unit(payload)
    assert packet.status == "ok" and packet.provenance[0].provider == provider
    assert packet.provenance[0].session_id == "session-1"
    assert packet.facts[0].conditions == ["flag enabled"]
    assert backend.analyze_unit(payload) == packet and transport.calls == 1
    blocked = SDKCodeBackend(settings, store, "run", tmp_path, transport=Transport(raw))
    assert blocked.analyze_unit({**payload, "query": "new"}).status == "budget_blocked"
    failed = SDKCodeBackend(
        settings,
        store,
        "run",
        tmp_path,
        transport=Transport(error=TimeoutError()),
        allowance=allowance,
    )
    assert failed.analyze_unit({**payload, "query": "timeout"}).status == "unavailable"
    assert allowance.settlements[-1] == ("reservation", None)
    invalid = SDKCodeBackend(
        settings, store, "run", tmp_path, transport=Transport({"bad": True}), allowance=allowance
    )
    assert invalid.analyze_unit({**payload, "query": "invalid"}).status == "unavailable"


def test_gemini_backend_keeps_same_candidate_contract():
    class Model:
        def call(self, stage, payload, schema):
            return {
                "report": "Candidate",
                "details": [{"statement": "Flag required", "evidence_ids": ["e1"]}],
            }

    result = GeminiCodeBackend(Model()).analyze_unit({"spans": [{"id": "e1"}]})
    assert result.status == "ok" and result.provenance[0].model == "gemini-3.8-flash"
    assert result.facts[0].review_status == "unreviewed"
