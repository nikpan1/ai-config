import json
from collections import Counter
from pathlib import Path

import pytest

from docgen_graph.ingestion import document_spans, snapshot_inputs
from docgen_graph.source_documents import document_context, extraction_packet
from docgen_graph.storage import ArtifactStore, digest


def source(text, path="registration.md"):
    return {"kind": "docs", "hash": digest(text.encode()), "path": path}


def packets(text, **limits):
    spans = document_spans(source(text), text)
    inventory = {"spans": spans, **document_context(spans, **limits)}
    return spans, [
        extraction_packet(inventory, index) for index in range(len(inventory["document_batches"]))
    ]


def test_small_document_keeps_whole_source_without_inferred_business_boundaries():
    text = (
        "---\nsource_url: https://example.com\n---\n# Guide\n\n## Registration\n"
        "Only adults may register.\n\n| ID | Rule |\n| --- | --- |\n"
        "| X | Accept terms. |\n\n## Recovery\nUse a token.\n"
    )
    spans, batches = packets(text)
    assert len(spans) == len(batches) == 1
    assert spans[0]["text"] == text
    assert spans[0]["heading"] == ""
    assert not {"story_id", "table_id", "table_columns", "heading_path"} & spans[0].keys()
    assert batches[0]["context_is_complete"]


def test_long_lines_preserve_unicode_crlf_and_exact_character_ranges():
    text = "# Registration\r\n\r\n" + "ż🙂 requirement " * 6000 + "\r\n"
    spans, batches = packets(text)
    assert len(spans) > 1
    assert "".join(span["text"] for span in spans) == text
    assert len({span["id"] for span in spans}) == len(spans)
    for span in spans:
        assert len(span["text"]) <= 8000
        assert text[span["source_start_char"] : span["source_end_char"]] == span["text"]
        assert span["locator"] == {
            "kind": "characters",
            "start": span["source_start_char"],
            "end": span["source_end_char"],
        }
    assert spans[1]["start_column"] > 1
    assert all(not batch["context_is_complete"] for batch in batches)


@pytest.mark.parametrize("variant", ["prose", "headings", "list", "table"])
def test_predeclared_library_variants_keep_complete_source_context(variant):
    cases = json.loads(
        (Path(__file__).parents[1] / "evaluation/source-first-cases.json").read_text("utf-8")
    )["cases"]
    case = next(item for item in cases if item["id"] == "formatting-equivalence")
    text = case["variants"][variant]
    spans, batches = packets(text)
    assert batches[0]["blocks"][0]["text"] == text
    assert batches[0]["context_is_complete"]
    assert not any("story_id" in span or "table_id" in span for span in spans)


def test_adjacent_exception_remains_available_across_size_boundary():
    text = "Neutral background. " * 3500
    boundary = 24000
    rule = "Borrowing requires active membership. "
    exception = "Invited readers are exempt from membership. "
    text = text[: boundary - len(rule)] + rule + exception + text[boundary:]
    spans, batches = packets(text)
    matching = [packet for packet in batches if any(rule in s["text"] for s in packet["blocks"])]
    assert matching
    for packet in matching:
        context = "".join(s["text"] for s in packet["blocks"] + packet["context_blocks"])
        assert exception in context
        assert len(context) <= 48000
    owners = Counter(span["id"] for packet in batches for span in packet["blocks"])
    assert owners == Counter({span["id"]: 1 for span in spans})


def test_small_cross_document_corpus_is_available_together():
    texts = {
        "rental.md": "Collection requires the check in [eligibility](eligibility.md).",
        "eligibility.md": "The check requires an unexpired identity document.",
        "note.md": "R-17 may refer to either site's independently defined requirement.",
    }
    spans = [
        span for path, text in texts.items() for span in document_spans(source(text, path), text)
    ]
    inventory = {"spans": spans, **document_context(spans)}
    assert len(inventory["document_batches"]) == 1
    packet = extraction_packet(inventory, 0)
    assert {span["path"] for span in packet["blocks"]} == set(texts)
    assert packet["stories"] == []


def test_oversized_unformatted_document_remains_bounded_without_failure():
    text = "Must accept terms. " * 9000 + "Except invited users."
    spans, batches = packets(text)
    assert "".join(span["text"] for span in spans) == text
    assert all(
        sum(len(span["text"]) for span in batch["blocks"] + batch["context_blocks"]) <= 48000
        for batch in batches
    )
    assert any(batch["context_blocks"] for batch in batches)


def test_graph_only_snapshot_does_not_require_a_documentation_template(tmp_path):
    document = tmp_path / "source.md"
    document.write_text("# Registration\n\nAccept terms.", encoding="utf-8")
    store = ArtifactStore(tmp_path / "artifacts")
    snapshot = snapshot_inputs(store, document, None, None, "Build the graph")
    assert snapshot["template_path"] is None
    assert store.get_bytes(snapshot["template_hash"]) == b""


def test_large_plain_text_attachment_has_bounded_windows_and_original_locator(tmp_path):
    from docgen_graph.ingestion import inventory

    document = tmp_path / "source.txt"
    document.write_bytes(("No formatting is needed. " * 4000).encode())
    store = ArtifactStore(tmp_path / "artifacts")
    snapshot = snapshot_inputs(store, document, None, None, "Read the plain text")
    result = inventory(store, snapshot)
    assert result["spans"]
    assert all(len(span["text"]) <= 8000 for span in result["spans"])
    assert all(span["source_kind"] == "attachment" for span in result["spans"])
    assert all("text_start" in span["locator"] for span in result["spans"])
    assert "".join(span["text"] for span in result["spans"]) == document.read_text("utf-8")
