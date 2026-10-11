from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from docgen_graph.ingestion import document_spans, inventory, snapshot_inputs
from docgen_graph.source_links import source_url_from_markdown, text_fragment_url
from docgen_graph.storage import ArtifactStore
from docgen_graph.workflow import Pipeline


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def test_every_synthetic_story_has_a_matching_html_text_fragment():
    root = Path(__file__).resolve().parents[2] / "data"
    markdown_files = sorted((root / "test_data_1").glob("*.md"))
    assert len(markdown_files) == 4
    for path in markdown_files:
        markdown = path.read_text(encoding="utf-8")
        url = source_url_from_markdown(markdown)
        assert url
        assert 70_000 <= len(markdown) <= 90_000
        assert (root / "test_data_1" / "assets" / f"{path.stem}.svg").is_file()
        assert (root / "test_data_1_html" / "assets" / f"{path.stem}.svg").is_file()
        parser = VisibleText()
        parser.feed((root / "test_data_1_html" / f"{path.stem}.html").read_text("utf-8"))
        visible = " ".join(" ".join(parser.parts).split())
        rows = [line for line in markdown.splitlines() if line.startswith("| ")][2:]
        assert len(rows) == 60
        for row in rows:
            href = text_fragment_url(url, row)
            assert href and ":~:text=" in href
            phrase = unquote(urlsplit(href).fragment.split(":~:text=", 1)[1])
            assert visible.count(phrase) == 1


def test_document_spans_keep_table_rows_separate():
    file = {"kind": "docs", "hash": "a" * 64, "path": "source.md"}
    spans = document_spans(
        file, "# Source\n\n| ID | Story |\n| --- | --- |\n| A | As a shopper, I want a table. |\n"
    )
    row = next(item for item in spans if "As a shopper" in item["text"])
    assert row["start_line"] == row["end_line"] == 5
    assert row["table_columns"] == ["ID", "Story"]


def test_fragment_url_preserves_query_and_encodes_directive_delimiters():
    url = "https://example.atlassian.net/wiki/page?id=9#section"
    result = text_fragment_url(url, "A made-to-order cabinet, size A & B is available.")
    assert result.startswith(url + ":~:text=")
    assert "%2D" in result and "%2C" in result and "%26" in result


def test_candidate_export_links_legacy_evidence_to_original_html(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[2] / "data"
    source = (root / "test_data_1" / "kitchen-3d-planning.md").read_text("utf-8")
    story_row = next(line for line in source.splitlines() if "KITCHEN3DPLANNING-01-1" in line)
    store = ArtifactStore(tmp_path)
    source_hash = store.put_bytes(source.encode())
    snapshot_ref = store.put(
        {"files": [{"kind": "docs", "path": "kitchen-3d-planning.md", "hash": source_hash}]}
    )
    pipeline = Pipeline(store, None, "citation-check")
    pipeline.graph.add_evidence(
        [
            {
                "id": "row-1",
                "kind": "docs",
                "path": "kitchen-3d-planning.md",
                "file_hash": source_hash,
                "start_line": 12,
                "end_line": 12,
                "heading": "Kitchen 3D planning",
                "text": story_row,
                "role": "legacy_document",
            },
            {
                "id": "row-2",
                "kind": "docs",
                "path": "kitchen-3d-planning.md",
                "file_hash": source_hash,
                "start_line": 13,
                "end_line": 13,
                "heading": "Kitchen 3D planning",
                "text": story_row,
                "role": "legacy_document",
            },
        ]
    )
    monkeypatch.setattr(pipeline, "_approved_plan", lambda state: {"title": "Kitchen guidance"})
    edited_ref = store.put(
        [
            {
                "title": "Room setup",
                "markdown": "## Room setup\n\nA room starts with measurements. [Legacy D1, D2]",
                "mappings": [{"citation_ids": ["D1", "D2"]}],
            }
        ]
    )
    result = pipeline.export_candidate(
        {
            "snapshot_ref": snapshot_ref,
            "edited_ref": edited_ref,
            "plan_hash": "plan",
            "graph_revision": "graph",
        }
    )
    candidate = tmp_path / "runs" / "citation-check" / "candidates" / result["candidate_ref"]
    markdown = (candidate / "documentation" / "index.md").read_text("utf-8")
    assert markdown.count("http://127.0.0.1:8765/kitchen-3d-planning.html#:~:text=") == 2
    assert "[Legacy D1, D2]" not in markdown
    assert markdown.count("## Room setup") == 1
    assert (candidate / "evidence" / "D1.md").exists()
    assert (candidate / "evidence" / "D2.md").exists()


def test_docs_only_snapshot_has_no_code_units(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "source.md").write_text("# Product\n\nA documented rule.\n", encoding="utf-8")
    template = tmp_path / "template.md"
    template.write_text("# Documentation\n\n## Rules\n", encoding="utf-8")
    store = ArtifactStore(tmp_path / "artifacts")
    snapshot = snapshot_inputs(store, docs, None, template, "Document-only evaluation")
    assert snapshot["roots"]["code"] is None
    assert snapshot["code_revision"] is None
    result = inventory(store, snapshot)
    assert result["code_units"] == []
    assert result["document_batches"]
