from collections import Counter

import pytest

from docgen_graph.ingestion import document_spans, snapshot_inputs
from docgen_graph.source_documents import document_context, extraction_packet
from docgen_graph.storage import ArtifactStore, digest


def source(text):
    return {"kind": "docs", "hash": digest(text.encode()), "path": "registration.md"}


def packets(text, **limits):
    spans = document_spans(source(text), text)
    inventory = {"spans": spans, **document_context(spans, **limits)}
    return spans, [
        extraction_packet(inventory, index) for index in range(len(inventory["document_batches"]))
    ]


def test_heading_paths_respect_levels_setext_and_fenced_code():
    text = (
        "Guide\n=====\n\n### Registration\n\nOnly adults may register.\n\n"
        "```markdown\n# Not a section\n```\n\n### Recovery\n\nUse a token.\n"
    )
    spans = document_spans(source(text), text)
    recovery = next(span for span in spans if "Use a token" in span["text"])
    assert recovery["heading"] == "Guide / Recovery"
    fence = next(span for span in spans if span["syntax_kind"] == "fence")
    assert fence["heading"] == "Guide / Registration"
    assert "# Not a section" in fence["text"]
    assert [heading["level"] for heading in recovery["heading_path"]] == [1, 3]


def test_front_matter_does_not_become_a_setext_heading():
    text = "---\nsource_url: https://example.com\n---\n\n# Registration\n\nAccept terms.\n"
    spans = document_spans(source(text), text)
    assert spans[0]["syntax_kind"] == "source_metadata"
    assert spans[0]["heading"] == ""
    assert spans[-1]["heading"] == "Registration"


def test_long_lines_preserve_unicode_crlf_and_exact_character_ranges():
    text = "# Registration\r\n\r\n" + "ż🙂 requirement " * 1300 + "\r\n"
    spans = document_spans(source(text), text)
    paragraphs = [span for span in spans if span["syntax_kind"] == "paragraph"]
    assert len(paragraphs) > 1
    assert "".join(span["text"] for span in paragraphs) == text.split("\r\n\r\n", 1)[1]
    assert len({span["id"] for span in spans}) == len(spans)
    for span in spans:
        assert len(span["text"]) <= 8000
        assert text[span["source_start_char"] : span["source_end_char"]] == span["text"]
        assert span["locator"] == {
            "kind": "characters",
            "start": span["source_start_char"],
            "end": span["source_end_char"],
        }
    assert paragraphs[1]["start_column"] > 1


@pytest.mark.parametrize(
    "body",
    [
        "Registration requires email. Registration requires consent. Minors cannot register.",
        "- Registration requires email.\n- Registration requires consent.\n"
        "- Minors cannot register.",
        "| Rule |\n| --- |\n| Registration requires email. |\n"
        "| Registration requires consent. |\n| Minors cannot register. |",
    ],
)
def test_format_variants_preserve_all_source_meaning_in_each_story_context(body):
    text = "# Registration\n\n" + body
    spans, batches = packets(text, maximum_items=1)
    statements = [
        "Registration requires email.",
        "Registration requires consent.",
        "Minors cannot register.",
    ]
    for packet in batches:
        available = packet["blocks"] + packet["context_blocks"]
        combined = "\n".join(span["text"] for span in available)
        assert all(statement in combined for statement in statements)
        assert len({span["id"] for span in available}) == len(available)
    owners = Counter(span["id"] for packet in batches for span in packet["blocks"])
    assert owners == Counter({span["id"]: 1 for span in spans})


def test_every_boundary_keeps_prerequisites_exceptions_and_ancestor_intro():
    text = (
        "# Accounts\n\nAll rules apply to customers only.\n\n## Registration\n\n"
        + "\n\n".join(f"Requirement {index} must hold." for index in range(15))
        + "\n\nIf any requirement fails, registration is denied except for invited users.\n\n"
        "## Recovery\n\nUse an independent recovery token.\n"
    )
    spans, batches = packets(text, maximum_items=3)
    registration_id = next(span["story_id"] for span in spans if "Requirement 0" in span["text"])
    for packet in batches:
        if not any(span["story_id"] == registration_id for span in packet["blocks"]):
            continue
        available = "\n".join(span["text"] for span in packet["blocks"] + packet["context_blocks"])
        assert "customers only" in available
        assert "Requirement 0" in available
        assert "Requirement 14" in available
        assert "except for invited users" in available


def test_user_story_rows_share_headers_but_do_not_require_the_whole_large_table():
    text = "# Accounts\n\n| ID | User story |\n| --- | --- |\n" + "".join(
        f"| S{index} | As a user, {'register safely ' * 200}. |\n" for index in range(25)
    )
    spans, batches = packets(text)
    assert len(text) > 48000
    rows = [span for span in spans if span["syntax_kind"] == "table_row"]
    assert len({span["story_id"] for span in rows}) == 25
    for packet in batches:
        available = packet["blocks"] + packet["context_blocks"]
        assert any(span["syntax_kind"] == "table_header" for span in available)
        assert sum(len(span["text"]) for span in available) <= 48000


def test_later_section_does_not_inherit_sibling_table_stories_as_ancestor_introduction():
    text = (
        "# Accounts\n\nRules apply to customers.\n\n| ID | User story |\n| --- | --- |\n"
        + "".join(f"| S{index} | As a user, {'register safely ' * 200}. |\n" for index in range(25))
        + "\n## Visual references\n\nThe registration form.\n"
    )
    spans, batches = packets(text, maximum_items=1)
    for packet in batches:
        if any("registration form" in span["text"] for span in packet["blocks"]):
            assert not any(span["syntax_kind"] == "table_row" for span in packet["context_blocks"])
            assert any("Rules apply" in span["text"] for span in packet["context_blocks"])


@pytest.mark.parametrize("identifier_header", ["ID", "Question ID"])
def test_large_keyed_catalog_preserves_intro_tail_headers_and_empty_cell_context(identifier_header):
    text = (
        "# Dictionary\n\nAll codes require version 3.\n\n"
        f"| {identifier_header} | Meaning | Qualification |\n| --- | --- | --- |\n"
        + "".join(
            f"| D{index} | {'A standalone dictionary value. ' * 80} | "
            f"{'Applies only to adults.' if index % 2 == 0 else ''} |\n"
            for index in range(30)
        )
        + "\nHistorical values must never be treated as current.\n"
    )
    spans, batches = packets(text, maximum_items=1)
    rows = [span for span in spans if span["syntax_kind"] == "table_row"]
    assert len({span["story_id"] for span in rows}) == 30
    for packet in batches:
        owned_rows = [span for span in packet["blocks"] if span["syntax_kind"] == "table_row"]
        if not owned_rows:
            continue
        context = "\n".join(span["text"] for span in packet["context_blocks"])
        assert "All codes require version 3." in context
        assert "Historical values must never be treated as current." in context
        assert f"| {identifier_header} | Meaning | Qualification |" in context
        if owned_rows[0]["carry_context_lines"]:
            assert "Applies only to adults." in context


def test_oversized_heading_container_partitions_child_pages_with_shared_qualifications():
    text = (
        "# Product\n\nGlobal rules remain mandatory.\n\n"
        "## Feature catalogue\n\nAll features require an active account.\n\n"
        + "\n\n".join(
            f"### Feature {index}\n\n" + "An independent feature rule. " * 100
            for index in range(25)
        )
    )
    spans, batches = packets(text)
    assert len({span["story_id"] for span in spans if "An independent" in span["text"]}) == 25
    for packet in batches:
        if not any("An independent" in span["text"] for span in packet["blocks"]):
            continue
        available = "\n".join(span["text"] for span in packet["blocks"] + packet["context_blocks"])
        assert "Global rules remain mandatory." in available
        assert "All features require an active account." in available


def test_oversized_story_context_fails_without_discarding_qualifications():
    text = "# Registration\n\n" + "Must accept terms. " * 3000 + "Except invited users."
    with pytest.raises(ValueError, match="context was not truncated"):
        packets(text)


def test_graph_only_snapshot_does_not_require_a_documentation_template(tmp_path):
    document = tmp_path / "source.md"
    document.write_text("# Registration\n\nAccept terms.", encoding="utf-8")
    store = ArtifactStore(tmp_path / "artifacts")
    snapshot = snapshot_inputs(store, document, None, None, "Build the graph")
    assert snapshot["template_path"] is None
    assert store.get_bytes(snapshot["template_hash"]) == b""
