import re
from bisect import bisect_right
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

from docgen.contracts import Block, Link
from docgen.storage import Artifacts, atomic_write, digest


def estimate_tokens(text: str) -> int:
    return (len(text.encode("utf-8")) + 2) // 3


def slug(text: str) -> str:
    return re.sub(r"[^\w\- ]", "", text.lower()).replace(" ", "-")


def parse_markdown(text: str, path: str, snapshot: str, max_tokens=2000) -> list[Block]:
    parser = MarkdownIt("commonmark").enable("table")
    environment = {}
    tokens = parser.parse(text, environment)
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    spans = []
    headings = []
    for token in tokens:
        if token.level != 0 or token.map is None:
            continue
        start, end = token.map
        if spans and start < spans[-1][1]:
            continue
        if token.type == "heading_open":
            depth = int(token.tag[1:])
            name = re.sub(r"^#+\s*|\s*#+\s*$", "", lines[start].strip())
            headings = headings[: depth - 1] + [name]
        spans.append((start, end, token.type.removesuffix("_open"), list(headings)))
    covered = set()
    blocks = []
    for start, end, kind, heading_path in spans:
        covered.update(range(start, end))
        ranges = [(start, end, None, None, [])]
        if kind == "table":
            table_id = "t-" + digest([snapshot, path, start])[:16]
            columns = []
            for cell in parser.parse("".join(lines[start:end])):
                if cell.type == "thead_close":
                    break
                if cell.type == "inline":
                    columns.append(cell.content)
            ranges = [(row, row + 1, table_id, row - start, columns) for row in range(start, end)]
        for first, last, table_id, row, columns in ranges:
            beginning, ending = offsets[first], offsets[last]
            cursor = beginning
            while cursor < ending:
                limit = min(ending, cursor + max_tokens * 2)
                if limit < ending:
                    newline = text.rfind("\n", cursor + 1, limit)
                    if newline > cursor:
                        limit = newline + 1
                while estimate_tokens(text[cursor:limit]) > max_tokens:
                    limit = cursor + max(1, (limit - cursor) // 2)
                content = text[cursor:limit]
                links = []
                for inline in parser.parse(content, environment):
                    for child in inline.children or []:
                        if child.type == "image":
                            links.append(Link(target=child.attrGet("src") or "", kind="image"))
                        elif child.type == "link_open":
                            links.append(Link(target=child.attrGet("href") or "", kind="link"))
                for target in re.findall(r"<img\b[^>]*\bsrc=[\"\']([^\"\']+)", content, re.I):
                    links.append(Link(target=target, kind="image"))
                blocks.append(
                    Block(
                        id="b-" + digest([snapshot, path, cursor, limit])[:20],
                        snapshot=snapshot,
                        path=path,
                        headings=heading_path,
                        line_start=bisect_right(offsets, cursor),
                        line_end=bisect_right(offsets, max(cursor, limit - 1)),
                        char_start=cursor,
                        char_end=limit,
                        kind=kind,
                        content=content,
                        table_id=table_id,
                        table_row=row,
                        table_columns=columns,
                        links=links,
                    )
                )
                cursor = limit
    for number, line in enumerate(lines):
        if number not in covered and line.strip():
            blocks.extend(parse_markdown_fragment(line, path, snapshot, number, offsets[number]))
    return sorted(blocks, key=lambda block: block.char_start)


def parse_markdown_fragment(content, path, snapshot, number, offset):
    return [
        Block(
            id="b-" + digest([snapshot, path, offset, offset + len(content)])[:20],
            snapshot=snapshot,
            path=path,
            headings=[],
            line_start=number + 1,
            line_end=number + 1,
            char_start=offset,
            char_end=offset + len(content),
            kind="raw",
            content=content,
        )
    ]


def snapshot_sources(source: Path, store: Artifacts, max_tokens=2000) -> dict:
    source = source.resolve()
    if not source.exists():
        raise ValueError("Source path does not exist")
    root = source if source.is_dir() else source.parent
    files = sorted(source.rglob("*")) if source.is_dir() else [source]
    inventory, blocks, problems = [], [], []
    for file in files:
        if file.is_dir():
            continue
        relative = file.relative_to(root).as_posix()
        if file.is_symlink() or not file.resolve().is_relative_to(root):
            inventory.append({"path": relative, "status": "unsupported_symlink"})
            problems.append(
                {
                    "kind": "unreadable",
                    "path": relative,
                    "description": "Symbolic links are not followed",
                }
            )
            continue
        try:
            raw = file.read_bytes()
        except OSError:
            inventory.append({"path": relative, "status": "unreadable"})
            problems.append(
                {"kind": "unreadable", "path": relative, "description": "Source cannot be read"}
            )
            continue
        checksum = digest(raw)
        ref = f"snapshots/{checksum}/{relative}"
        saved = store.path(ref)
        if saved.exists() and saved.read_bytes() != raw:
            raise ValueError("Immutable source snapshot was modified")
        if not saved.exists():
            atomic_write(saved, raw)
        entry = {"path": relative, "snapshot": checksum, "ref": ref, "bytes": len(raw)}
        if file.suffix.lower() not in {".md", ".markdown"}:
            entry["status"] = "asset"
            problems.append(
                {
                    "kind": "asset",
                    "path": relative,
                    "description": "Unsupported asset requires an attributed explanation",
                }
            )
        else:
            try:
                text = raw.decode("utf-8")
                parsed = parse_markdown(text, relative, checksum, max_tokens)
                blocks.extend(parsed)
                entry.update(status="parsed", blocks=len(parsed))
            except UnicodeError:
                entry["status"] = "unreadable"
                problems.append(
                    {
                        "kind": "unreadable",
                        "path": relative,
                        "description": "Source is not valid UTF-8",
                    }
                )
        inventory.append(entry)
    if not inventory:
        problems.append({"kind": "empty_source", "description": "No source files found"})
    link_targets, link_problems = resolve_links(blocks, inventory)
    problems.extend(link_problems)
    return {
        "inventory": inventory,
        "blocks": [b.model_dump() for b in blocks],
        "links": link_targets,
        "problems": problems,
    }


def resolve_links(blocks: list[Block], inventory: list[dict]):
    files = {entry["path"]: entry for entry in inventory}
    anchors = {}
    first_blocks = {}
    for block in blocks:
        first_blocks.setdefault(block.path, block.id)
        if block.kind == "heading":
            base = slug(block.headings[-1])
            key = base
            suffix = 0
            while (block.path, key) in anchors:
                suffix += 1
                key = f"{base}-{suffix}"
            anchors[block.path, key] = block.id
        for anchor in re.findall(r"\bid=[\"\']([^\"\']+)", block.content):
            anchors[block.path, anchor] = block.id
    targets, problems = {}, []
    for block in blocks:
        targets[block.id] = []
        for link in block.links:
            url = urlsplit(link.target)
            if link.kind == "image":
                problems.append(
                    {
                        "kind": "asset",
                        "block_ids": [block.id],
                        "description": f"Image requires explanation: {link.target}",
                    }
                )
            if url.scheme or url.netloc:
                targets[block.id].append({"target": link.target, "status": "external"})
                continue
            path = (
                str(PurePosixPath(block.path).parent / unquote(url.path))
                if url.path
                else block.path
            )
            parts = []
            for part in PurePosixPath(path).parts:
                if part == ".." and parts:
                    parts.pop()
                elif part != ".":
                    parts.append(part)
            path = "/".join(parts)
            target = (
                anchors.get((path, unquote(url.fragment)))
                if url.fragment
                else first_blocks.get(path)
            )
            status = (
                "resolved"
                if target
                else "asset"
                if path in files and not url.fragment
                else "missing"
            )
            targets[block.id].append({"target": link.target, "status": status, "block_id": target})
            if status == "missing":
                problems.append(
                    {
                        "kind": "missing_link",
                        "block_ids": [block.id],
                        "description": f"Missing local link target: {link.target}",
                    }
                )
    return targets, problems
