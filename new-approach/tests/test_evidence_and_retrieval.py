import sqlite3

from docgen_graph.ingestion import inventory, snapshot_inputs
from docgen_graph.knowledge import KnowledgeGraph, normalized_assertion
from docgen_graph.storage import ArtifactStore


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
    assert all(
        item["text"]
        == "\n".join(
            store.get_bytes(item["file_hash"])
            .decode()
            .splitlines()[item["start_line"] - 1 : item["end_line"]]
        )
        for item in result["spans"]
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
