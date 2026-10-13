from bisect import bisect_right

from docgen_graph.storage import digest

PARSER_VERSION = "source-windows-v3"
MAXIMUM_SPAN_CHARACTERS = 8000
MAXIMUM_CONTEXT_CHARACTERS = 48000


def document_spans(file: dict, text: str) -> list[dict]:
    if not text.strip():
        return []
    offsets = [0]
    for line in text.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    spans = []
    for first in range(0, len(text), MAXIMUM_SPAN_CHARACTERS):
        last = min(first + MAXIMUM_SPAN_CHARACTERS, len(text))
        first_line = bisect_right(offsets, first) - 1
        last_line = bisect_right(offsets, last - 1) - 1
        spans.append(
            {
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
                "heading": "",
                "text": text[first:last],
                "role": "legacy_document",
                "syntax_kind": "source_window",
                "parser_version": PARSER_VERSION,
            }
        )
    return spans


def document_context(
    spans: list[dict],
    maximum_chars: int = MAXIMUM_CONTEXT_CHARACTERS,
    maximum_items: int = 12,
    maximum_context_chars: int = MAXIMUM_CONTEXT_CHARACTERS,
) -> dict:
    if min(maximum_chars, maximum_items, maximum_context_chars) <= 0:
        raise ValueError("Source context limits must be positive")
    documents = [span for span in spans if span["kind"] == "docs"]
    ownership_limit = min(maximum_chars, maximum_context_chars)
    if sum(len(span["text"]) for span in documents) > maximum_context_chars:
        ownership_limit = min(ownership_limit, maximum_context_chars // 2)
    batches = []
    current = []
    size = 0
    for span in documents:
        length = len(span["text"])
        if length > ownership_limit:
            raise ValueError(f"Source span {span['id']} exceeds the configured batch size")
        if current and (size + length > ownership_limit or len(current) >= maximum_items):
            batches.append(current)
            current, size = [], 0
        current.append(span["id"])
        size += length
    if current:
        batches.append(current)
    positions = {span["id"]: index for index, span in enumerate(documents)}
    contexts = []
    for batch in batches:
        owned = set(batch)
        owned_positions = [positions[identifier] for identifier in batch]
        paths = {documents[index]["path"] for index in owned_positions}
        candidates = sorted(
            (index for index, span in enumerate(documents) if span["id"] not in owned),
            key=lambda index: (
                documents[index]["path"] not in paths,
                min(abs(index - position) for position in owned_positions),
                index,
            ),
        )
        size = sum(len(documents[index]["text"]) for index in owned_positions)
        contextual = []
        for index in candidates:
            span = documents[index]
            if size + len(span["text"]) <= maximum_context_chars:
                contextual.append(index)
                size += len(span["text"])
        contexts.append(
            {
                "context_block_ids": [documents[index]["id"] for index in sorted(contextual)],
                "context_policy": "source_windows_with_overlap",
                "context_characters": size,
                "available_source_characters": sum(len(span["text"]) for span in documents),
            }
        )
    return {
        "stories": [],
        "document_batches": batches,
        "document_context_batches": contexts,
        "parser_version": PARSER_VERSION,
    }


def extraction_packet(inventory: dict, index: int) -> dict:
    by_id = {span["id"]: span for span in inventory["spans"]}
    owned = inventory["document_batches"][index]
    records = inventory.get("document_context_batches", [])
    record = records[index] if records else {}
    return {
        "blocks": [by_id[identifier] for identifier in owned],
        "context_blocks": [by_id[identifier] for identifier in record.get("context_block_ids", [])],
        "stories": [],
        "context_policy": record.get("context_policy", "legacy_owned_blocks_only"),
        "context_is_complete": record.get("context_characters")
        == record.get("available_source_characters"),
        "interpretation_policy": (
            "Read original text across adjacent windows. Formatting and window boundaries are "
            "not business boundaries. Preserve uncertainty when required context is unavailable. "
            "Generated image descriptions are model interpretations, not authored source text."
        ),
    }
