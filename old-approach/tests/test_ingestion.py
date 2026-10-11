from docgen.batching import plan_batches, split_batch
from docgen.contracts import Block
from docgen.ingestion import estimate_tokens, parse_markdown, snapshot_sources


def test_exact_locations_tables_and_links(tmp_path, store, settings):
    text = (
        "# Scope\r\n\r\nA condition with [details](#details).\r\n\r\n"
        "| Field | Meaning |\r\n| --- | --- |\r\n| x | unknown |\r\n\r\n"
        "## Details\r\n\r\n- First\r\n- Second\r\n"
    )
    source = tmp_path / "source"
    source.mkdir()
    (source / "doc.md").write_bytes(text.encode())
    snapshot = snapshot_sources(source, store)
    assert not snapshot["problems"]
    blocks = [Block.model_validate(item) for item in snapshot["blocks"]]
    for block in blocks:
        assert text[block.char_start : block.char_end] == block.content
    assert [block.table_row for block in blocks if block.table_id] == [0, 1, 2]
    assert all(block.table_columns == ["Field", "Meaning"] for block in blocks if block.table_id)
    covered = {index for block in blocks for index in range(block.char_start, block.char_end)}
    assert all(char.isspace() or index in covered for index, char in enumerate(text))
    batches = plan_batches(snapshot, settings)
    assert sorted(key for batch in batches for key in batch.owned) == sorted(
        block.id for block in blocks
    )
    assert snapshot_sources(source, store) == snapshot


def test_oversized_unicode_and_code_remain_bounded():
    text = "# Long\n\n" + "żółć" * 8000 + "\n\n```python\nprint('x')\n```\n"
    blocks = parse_markdown(text, "long.md", "snapshot", 256)
    assert all(estimate_tokens(block.content) <= 256 for block in blocks)
    for block in blocks:
        assert text[block.char_start : block.char_end] == block.content
    covered = {index for block in blocks for index in range(block.char_start, block.char_end)}
    assert all(char.isspace() or index in covered for index, char in enumerate(text))


def test_unreadable_missing_links_assets_are_visible(tmp_path, store):
    source = tmp_path / "source"
    source.mkdir()
    (source / "bad.md").write_bytes(b"\xff")
    (source / "image.png").write_bytes(b"not-an-image")
    (source / "doc.md").write_text(
        "![diagram](image.png)\n\n[missing](missing.md)\n", encoding="utf-8"
    )
    snapshot = snapshot_sources(source, store)
    assert {issue["kind"] for issue in snapshot["problems"]} == {
        "asset",
        "missing_link",
        "unreadable",
    }
    assert len(snapshot["inventory"]) == 3


def test_split_ownership_preserves_context(tmp_path, store, settings):
    source = tmp_path / "doc.md"
    source.write_text("# Title\n\nFirst rule.\n\nSecond rule.\n", encoding="utf-8")
    snapshot = snapshot_sources(source, store)
    blocks = {item["id"]: Block.model_validate(item) for item in snapshot["blocks"]}
    batch = plan_batches(snapshot, settings)[0]
    children = split_batch(batch, blocks)
    assert [key for child in children for key in child.owned] == batch.owned
    assert all(set(batch.context) <= set(child.context) for child in children)
    assert set(children[1].context) & set(children[0].owned)
