import pytest
from PIL import Image

from docgen.ingestion import batches, inventory, local_path, parse_inventory


def test_images_tables_html_and_snapshots(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    image = source / "diagram.png"
    Image.new("RGB", (100, 80), "white").save(image)
    source.joinpath("bad.png").write_text("not an image", "utf-8")
    text = (
        "# Test\n\n| Value | Units |\n| --- | --- |\n| 3 | attempts |\n\n"
        "![Diagram](diagram.png)\n\n![Same][image]\n\n[image]: diagram.png\n\n"
        '<img src="diagram.png" alt="HTML image">\n\n'
        "![Missing](missing.png)\n\n![Bad](bad.png)\n\n"
        "![Remote](https://example.com/image.png)\n\n"
        '<table><tr><td colspan="2">Preserve span</td></tr></table>\n'
    )
    source.joinpath("test.md").write_text(text, "utf-8")
    destination = tmp_path / "run"
    data = inventory(source, destination)
    assert data["counts"] == {"documents": 1, "images": 4}
    local = next(a for a in data["images"] if a["status"] == "pending")
    assert len(local["span_ids"]) == 3
    parsed = parse_inventory(destination, data)
    table = next(s for s in parsed["spans"] if s["kind"] == "table")
    assert table["table"] == [["Value", "Units"], ["3", "attempts"]]
    assert "| Value | Units |" in table["excerpt"]
    assert any("colspan" in s["excerpt"] for s in parsed["spans"])
    source.joinpath("test.md").write_text("changed", "utf-8")
    assert parse_inventory(destination, data) == parsed
    assert len([e for e in parsed["evidence"] if e["kind"] == "image"]) == 6


def test_root_escape_remote_and_missing_links(tmp_path):
    path = tmp_path / "document.md"
    with pytest.raises(ValueError, match="escapes"):
        local_path(tmp_path, path, "../outside.png")
    with pytest.raises(ValueError, match="localization"):
        local_path(tmp_path, path, "https://example.com/a.png")
    path.write_text("# Heading\n\n[Missing](missing.md#absent)\n", "utf-8")
    result = inventory(path, tmp_path / "run")
    assert any(
        "Missing cross-reference" in w
        for w in parse_inventory(tmp_path / "run", result)["warnings"]
    )


def test_large_tables_retain_header_in_every_batch(tmp_path):
    path = tmp_path / "table.md"
    path.write_text("| Value | Unit |\n| --- | --- |\n" + "| 3 | attempts |\n" * 200, "utf-8")
    data = parse_inventory(tmp_path / "run", inventory(path, tmp_path / "run"))
    chunked = batches(data["spans"], 1200)
    assert len(chunked) > 1
    assert all(s["table"][0] == ["Value", "Unit"] for batch in chunked for s in batch)


def test_empty_unsupported_and_output_exclusion(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    source.joinpath("notes.docx").write_bytes(b"unsupported")
    output = source / "runs"
    output.mkdir()
    output.joinpath("generated.md").write_text("ignored", "utf-8")
    result = inventory(source, exclude=output)
    assert result["counts"]["documents"] == 0
    assert "Unsupported" in result["warnings"][0]


def test_identical_documents_have_distinct_locations(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    for name in ("one.md", "two.md"):
        source.joinpath(name).write_text("# Same\n\nSame content.\n", "utf-8")
    parsed = parse_inventory(tmp_path / "run", inventory(source, tmp_path / "run"))
    ids = [s["id"] for s in parsed["spans"]]
    assert len(ids) == len(set(ids))


def test_undefined_image_reference_is_visible(tmp_path):
    path = tmp_path / "broken.md"
    path.write_text("# Missing image\n\n![Important diagram][undefined]\n", "utf-8")
    result = inventory(path, tmp_path / "run")
    assert result["images"][0]["status"] == "unresolved"
    assert "Undefined" in result["images"][0]["reason"]


def test_supplied_corpus_parses_without_lost_table_context(tmp_path):
    from pathlib import Path

    result = inventory(Path("data/legacy-insurance"), tmp_path)
    parsed = parse_inventory(tmp_path, result)
    assert len(parsed["documents"]) == 3
    assert not parsed["images"]
    assert not any("feature-f-001-policy-creation" in w for w in parsed["warnings"])
    assert len({s["id"] for s in parsed["spans"]}) == len(parsed["spans"])
    chunked = batches(parsed["spans"], 16000)
    assert {s["id"] for batch in chunked for s in batch} == {s["id"] for s in parsed["spans"]}
    print(
        {
            "spans": len(parsed["spans"]),
            "batches": len(chunked),
            "tables": sum(bool(s["table"]) for s in parsed["spans"]),
            "warnings": len(parsed["warnings"]),
        }
    )
