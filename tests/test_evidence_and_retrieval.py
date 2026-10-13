import sqlite3

from docgen_graph.ingestion import inventory, snapshot_inputs
from docgen_graph.knowledge import KnowledgeGraph, normalized_assertion
from docgen_graph.storage import ArtifactStore
from docgen_graph.workflow import Pipeline, _bounded_evidence_packet, _normalized_section_draft


def test_snapshot_preserves_bytes_and_excludes_secrets(tmp_path):
    docs = tmp_path / "docs"
    code = tmp_path / "code"
    docs.mkdir()
    code.mkdir()
    (docs / "guide.md").write_text(
        "# Rules\n\n| Mode | Result |\n| --- | --- |\n| strict | Reject |\n", encoding="utf-8"
    )
    (code / "app.py").write_text(
        "import os\n\ndef process(value):\n"
        "    if value:\n        return value\n    raise ValueError()\n",
        encoding="utf-8",
    )
    (code / ".env.local").write_text("SECRET=hidden", encoding="utf-8")
    template = tmp_path / "template.md"
    template.write_text("## Rules\n", encoding="utf-8")
    store = ArtifactStore(tmp_path / "runtime")
    snapshot = snapshot_inputs(store, docs, code, template, "")
    result = inventory(store, snapshot)
    assert len(snapshot["files"]) == 2
    assert any(item["path"] == ".env.local" for item in snapshot["exclusions"])
    for item in result["spans"]:
        original = store.get_bytes(item["file_hash"]).decode()
        if item.get("locator", {}).get("kind") == "characters":
            assert item["text"] == original[item["locator"]["start"] : item["locator"]["end"]]
        else:
            assert item["text"] == "\n".join(
                original.splitlines()[item["start_line"] - 1 : item["end_line"]]
            )
    assert result["analysis"]["app.py"]["capability"] == "python_ast"
    assert any(symbol["name"] == "process" for symbol in result["analysis"]["app.py"]["symbols"])
    assert any(span["heading"] == "process" and span["start_line"] == 3 for span in result["spans"])
    assert any("| Mode | Result |" in span["text"] for span in result["spans"])


def test_graph_traversal_recovers_related_qualification(tmp_path):
    graph = KnowledgeGraph(tmp_path / "graph.sqlite")
    spans = [
        {
            "id": "source-a",
            "kind": "docs",
            "path": "guide.md",
            "file_hash": "hash-a",
            "start_line": 1,
            "end_line": 1,
            "heading": "Rule",
            "text": "entrypoint accepts requests",
            "role": "legacy_document",
        },
        {
            "id": "source-b",
            "kind": "code",
            "path": "app.py",
            "file_hash": "hash-b",
            "start_line": 5,
            "end_line": 5,
            "heading": "",
            "text": "requires an enabled flag",
            "role": "code",
        },
    ]
    graph.add_evidence(spans)
    first = normalized_assertion(
        {
            "statement": "The entrypoint accepts requests.",
            "subject": "entrypoint",
            "predicate": "accepts",
            "evidence_ids": ["source-a"],
        },
        {"source-a"},
    )
    second = normalized_assertion(
        {
            "statement": "Only when the flag is enabled.",
            "subject": "entrypoint",
            "predicate": "accepts",
            "conditions": "enabled flag",
            "evidence_ids": ["source-b"],
        },
        {"source-b"},
    )
    graph.add_assertions([first, second])
    packet = graph.retrieve(["entrypoint requests"], [])
    assert {first["id"], second["id"]}.issubset({item["id"] for item in packet["assertions"]})
    assert {"source-a", "source-b"}.issubset({item["id"] for item in packet["evidence"]})
    closure = graph.retrieve([], [first["id"]], optional_limit=0)
    assert second["id"] in closure["mandatory_closure"]
    assert not graph.verify()
    with sqlite3.connect(graph.path) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_section_packet_keeps_required_closure_within_limit():
    packet = {
        "mandatory_closure": ["required", "qualified"],
        "seed_matches": ["optional"],
        "assertions": [
            {"id": "required", "evidence_ids": ["source-a"]},
            {"id": "qualified", "evidence_ids": ["source-b"]},
            {"id": "optional", "evidence_ids": ["source-c"]},
        ],
        "evidence": [
            {"id": "source-a", "text": "a" * 8},
            {"id": "source-b", "text": "b" * 8},
            {"id": "source-c", "text": "c" * 8},
        ],
    }
    bounded = _bounded_evidence_packet(packet, limit=16)
    assert {item["id"] for item in bounded["assertions"]} == {"required", "qualified"}
    assert {item["id"] for item in bounded["evidence"]} == {"source-a", "source-b"}
    assert bounded["context_characters"] == 16
    assert _bounded_evidence_packet(packet, limit=8)["context_characters"] == 16


def test_section_mapping_normalizes_evidence_ids_to_citation_labels():
    draft = {
        "markdown": "A supported statement [Legacy D7].",
        "mappings": [
            {
                "obligation_id": "required",
                "citation_ids": ["evidence-id", "Legacy D8", "[Code C2]"],
                "passage": "A supported statement [Legacy D7].",
            }
        ],
    }
    packet = {"evidence": [{"id": "evidence-id", "label": "D7"}]}
    normalized = _normalized_section_draft(draft, packet)
    assert normalized["mappings"][0]["citation_ids"] == ["D7", "D8", "C2"]


def test_supporting_summary_rejects_unmapped_citations(tmp_path):
    store = ArtifactStore(tmp_path / "runtime")
    pipeline = Pipeline(store, None, "summary-audit")
    section = {"title": "Executive Summary", "obligation_ids": []}
    pipeline._approved_plan = lambda state: {"sections": [section], "source_assets": []}
    pipeline._units = lambda section: [["support-a", "support-b"]]
    observed = {}

    def audit(stage, payload, schema):
        observed.update(payload)
        return {"accepted": True, "findings": [], "covered_obligation_ids": ["support-a"]}

    pipeline.call = audit
    state = {
        "template_ref": store.put({"text": "## Executive Summary"}),
        "section_index": 0,
        "unit_index": 0,
        "packet_ref": store.put(
            {
                "assertions": [{"id": "support-a"}, {"id": "support-b"}],
                "evidence": [{"id": "e1", "label": "D1"}],
            }
        ),
        "draft_ref": store.put({"markdown": "A cited summary [Legacy D1].", "mappings": []}),
        "written_ref": store.put([]),
    }
    result = pipeline.verify_section(state)
    assert result["route"] == "write_section"
    assert "Section misses approved obligations" in store.get(result["feedback_ref"])
    assert not observed
