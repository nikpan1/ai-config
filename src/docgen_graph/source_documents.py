from bisect import bisect_right

from markdown_it import MarkdownIt

from docgen_graph.storage import digest

PARSER_VERSION = "markdown-it-context-v2"
MAXIMUM_SPAN_CHARACTERS = 8000
MAXIMUM_CONTEXT_CHARACTERS = 48000


def _mapped_blocks(text: str) -> list[dict]:
    lines = text.splitlines(keepends=True)
    blocks = []
    parsed_text = text
    if lines and lines[0].strip() == "---":
        boundary = next(
            (index for index, line in enumerate(lines[1:], 1) if line.strip() in {"---", "..."}),
            None,
        )
        if boundary is not None:
            blocks.append({"start": 0, "end": boundary + 1, "syntax_kind": "source_metadata"})
            parsed_text = "\n" * (boundary + 1) + "".join(lines[boundary + 1 :])
    tokens = MarkdownIt("commonmark").enable("table").parse(parsed_text)
    for index, token in enumerate(tokens):
        if token.level or token.map is None or token.nesting == -1:
            continue
        start, end = token.map
        kind = token.type.removesuffix("_open").removesuffix("_block")
        block = {"start": start, "end": end, "syntax_kind": kind}
        if kind == "heading":
            block.update(level=int(token.tag[1:]), title=tokens[index + 1].content)
        if kind != "table":
            blocks.append(block)
            continue
        columns = []
        for child in tokens[index + 1 :]:
            if child.type == "thead_close":
                break
            if child.type == "inline":
                columns.append(child.content)
        table_id = f"table:{start}"
        rows = {}
        for child in tokens[index + 1 :]:
            if child.type == "table_close":
                break
            if child.type == "inline" and child.map and child.map[0] >= start + 2:
                rows.setdefault(child.map[0], []).append(child.content)
        keys = [cells[0] for cells in rows.values() if cells]
        key_label = columns[0].casefold()
        keyed_records = (
            sum(len(line) for line in lines[start:end]) > MAXIMUM_CONTEXT_CHARACTERS
            and (
                key_label in {"id", "identifier", "code", "key"}
                or key_label.endswith((" id", " identifier", " code", " key"))
            )
            and all(keys)
            and len(set(keys)) == len(keys)
        )
        preceding_values = {}
        for line in range(start, end):
            cells = rows.get(line, [])
            carry_lines = set()
            for column, cell in enumerate(cells):
                if cell.strip():
                    preceding_values[column] = line
                elif column in preceding_values:
                    carry_lines.add(preceding_values[column])
            blocks.append(
                {
                    "start": line,
                    "end": line + 1,
                    "syntax_kind": "table_header" if line < start + 2 else "table_row",
                    "table_columns": columns,
                    "table_id": table_id,
                    "carry_context_lines": sorted(carry_lines),
                    "story_boundary": "keyed_table_record" if keyed_records else "source_structure",
                    "row_story": line >= start + 2
                    and (
                        keyed_records
                        or any(column.casefold() in {"story", "user story"} for column in columns)
                    ),
                }
            )
    covered = {line for block in blocks for line in range(block["start"], block["end"])}
    for line, content in enumerate(lines):
        if line not in covered and content.strip():
            blocks.append({"start": line, "end": line + 1, "syntax_kind": "source_metadata"})
    return sorted(blocks, key=lambda block: block["start"])


def _story_level(blocks: list[dict]) -> int:
    levels = [block["level"] for block in blocks if block["syntax_kind"] == "heading"]
    if not levels:
        return 1
    minimum = min(levels)
    if levels.count(minimum) == 1 and levels[0] == minimum:
        deeper = [level for level in levels if level > minimum]
        if deeper:
            return min(deeper)
    return minimum


def _source_parts(text: str, start: int, end: int):
    while start < end:
        stop = min(start + MAXIMUM_SPAN_CHARACTERS, end)
        if stop < end:
            boundary = text.rfind("\n", start, stop)
            if boundary >= start:
                stop = boundary + 1
        yield start, stop
        start = stop


def document_spans(file: dict, text: str) -> list[dict]:
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    blocks = _mapped_blocks(text)
    story_level = _story_level(blocks)
    headings = []
    root_story = digest([file["hash"], file["path"], "root-story"])[:20]
    story_id = root_story
    spans = []
    for block in blocks:
        if block["syntax_kind"] == "heading":
            while headings and headings[-1]["level"] >= block["level"]:
                headings.pop()
            headings.append(
                {"level": block["level"], "title": block["title"], "line": block["start"] + 1}
            )
            if block["level"] <= story_level or (
                len(headings) == 2 and headings[0]["level"] < story_level
            ):
                story_id = digest([file["hash"], file["path"], block["start"], "story"])[:20]
        block_story = story_id
        if block.get("row_story"):
            block_story = digest([file["hash"], file["path"], block["start"], "row-story"])[:20]
        start, end = offsets[block["start"]], offsets[block["end"]]
        for first, last in _source_parts(text, start, end):
            first_line = bisect_right(offsets, first) - 1
            last_line = bisect_right(offsets, last - 1) - 1
            span = {
                "id": digest([file["kind"], file["hash"], file["path"], first, last])[:20],
                "kind": file["kind"],
                "path": file["path"],
                "file_hash": file["hash"],
                "start_line": first_line + 1,
                "end_line": last_line + 1,
                "start_column": first - offsets[first_line] + 1,
                "end_column": last - offsets[last_line] + 1,
                "source_start_char": first,
                "source_end_char": last,
                "locator": {"kind": "characters", "start": first, "end": last},
                "heading": " / ".join(heading["title"] for heading in headings),
                "heading_path": [dict(heading) for heading in headings],
                "text": text[first:last],
                "role": "legacy_document",
                "syntax_kind": block["syntax_kind"],
                "story_id": block_story,
                "parent_story_id": story_id if block_story != story_id else None,
                "parser_version": PARSER_VERSION,
            }
            for field in ("table_columns", "table_id", "carry_context_lines", "story_boundary"):
                if field in block:
                    span[field] = block[field]
            spans.append(span)
    return _partition_heading_stories(spans)


def _partition_heading_stories(spans: list[dict]) -> list[dict]:
    stories = {}
    for span in spans:
        stories.setdefault(span["story_id"], []).append(span)
    for identifier, owned in stories.items():
        if sum(len(span["text"]) for span in owned) <= MAXIMUM_CONTEXT_CHARACTERS:
            continue
        prefix = owned[0]["heading_path"]
        for span in owned:
            path = span["heading_path"]
            if len(path) > len(prefix):
                span["story_id"] = digest([identifier, path, "heading-partition"])[:20]
                span["story_boundary"] = "oversized_heading_section"
    return spans


def document_context(
    spans: list[dict],
    maximum_chars: int = 12000,
    maximum_items: int = 12,
    maximum_context_chars: int = MAXIMUM_CONTEXT_CHARACTERS,
) -> dict:
    documents = [span for span in spans if span["kind"] == "docs"]
    stories = {}
    by_id = {span["id"]: span for span in documents}
    for span in documents:
        identifier = span.get("story_id") or digest([span["path"], span["file_hash"], "story"])[:20]
        span["story_id"] = identifier
        story = stories.setdefault(
            identifier,
            {
                "id": identifier,
                "path": span["path"],
                "file_hash": span["file_hash"],
                "heading": span["heading"],
                "block_ids": [],
                "context_block_ids": [],
                "context_policy": "complete_story_and_ancestor_introductions",
                "story_boundary": span.get("story_boundary", "source_structure"),
            },
        )
        story["block_ids"].append(span["id"])
    for story in stories.values():
        owned = [by_id[identifier] for identifier in story["block_ids"]]
        first = owned[0]
        ancestor_lines = {heading["line"] for heading in first.get("heading_path", [])}
        prefix = first.get("heading_path", [])
        context = []
        carry_lines = {line + 1 for span in owned for line in span.get("carry_context_lines", [])}
        for span in documents:
            if span["path"] != story["path"] or span["file_hash"] != story["file_hash"]:
                continue
            if span["id"] in story["block_ids"]:
                continue
            path = span.get("heading_path", [])
            is_ancestor = (
                len(path) < len(prefix)
                and path == prefix[: len(path)]
                and not (span.get("parent_story_id") and span.get("syntax_kind") == "table_row")
            )
            same_parent = first.get("parent_story_id") == span["story_id"]
            is_heading = (
                span.get("syntax_kind") == "heading" and span["start_line"] in ancestor_lines
            )
            carry_context = (
                span.get("table_id") == first.get("table_id") and span["start_line"] in carry_lines
            )
            if is_ancestor or same_parent or is_heading or carry_context:
                context.append(span["id"])
        story["context_block_ids"] = context
        size = sum(len(by_id[identifier]["text"]) for identifier in story["block_ids"] + context)
        story["context_characters"] = size
        if size > maximum_context_chars:
            raise ValueError(
                f"Complete story context exceeds {maximum_context_chars} characters: "
                f"{story['path']} / {story['heading']} ({size} characters). "
                "Split the story explicitly or increase the context budget; "
                "context was not truncated."
            )
    batches = []
    contexts = []
    for story in stories.values():
        current = []
        size = 0
        for identifier in story["block_ids"]:
            length = len(by_id[identifier]["text"])
            if length > maximum_chars:
                raise ValueError(f"Source span {identifier} exceeds the configured batch size")
            if current and (size + length > maximum_chars or len(current) >= maximum_items):
                batches.append(current)
                contexts.append(_context_batch(story, current))
                current, size = [], 0
            current.append(identifier)
            size += length
        if current:
            batches.append(current)
            contexts.append(_context_batch(story, current))
    batches, contexts = _combine_batches(
        batches, contexts, by_id, maximum_chars, maximum_items, maximum_context_chars
    )
    return {
        "stories": list(stories.values()),
        "document_batches": batches,
        "document_context_batches": contexts,
        "parser_version": PARSER_VERSION,
    }


def _combine_batches(batches, contexts, by_id, maximum_chars, maximum_items, maximum_context_chars):
    combined = []
    records = []
    for owned, context in zip(batches, contexts, strict=True):
        if combined:
            previous = combined[-1]
            merged = previous + owned
            contextual = list(
                dict.fromkeys(records[-1]["context_block_ids"] + context["context_block_ids"])
            )
            contextual = [identifier for identifier in contextual if identifier not in merged]
            size = sum(len(by_id[identifier]["text"]) for identifier in merged)
            total = size + sum(len(by_id[identifier]["text"]) for identifier in contextual)
            if (
                size <= maximum_chars
                and len(merged) <= maximum_items
                and total <= maximum_context_chars
            ):
                combined[-1] = merged
                records[-1]["context_block_ids"] = contextual
                records[-1]["story_ids"] = list(
                    dict.fromkeys(records[-1]["story_ids"] + context["story_ids"])
                )
                continue
        combined.append(owned)
        records.append(context)
    return combined, records


def _context_batch(story: dict, owned: list[str]) -> dict:
    return {
        "story_ids": [story["id"]],
        "context_block_ids": [
            identifier
            for identifier in story["block_ids"] + story["context_block_ids"]
            if identifier not in owned
        ],
        "context_policy": story["context_policy"],
    }


def extraction_packet(inventory: dict, index: int) -> dict:
    by_id = {span["id"]: span for span in inventory["spans"]}
    owned = inventory["document_batches"][index]
    records = inventory.get("document_context_batches", [])
    record = records[index] if records else {}
    contexts = record.get("context_block_ids", [])
    return {
        "blocks": [by_id[identifier] for identifier in owned],
        "context_blocks": [by_id[identifier] for identifier in contexts],
        "stories": [
            story
            for story in inventory.get("stories", [])
            if story["id"] in record.get("story_ids", [])
        ],
        "context_policy": record.get("context_policy", "legacy_owned_blocks_only"),
    }
