import json
import posixpath
import re
from html.parser import HTMLParser
from importlib.metadata import version
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt
from mdit_py_plugins.footnote import footnote_plugin
from PIL import Image

from docgen.models import EvidenceRef, ImageAsset, SourceDocument, SourceSpan
from docgen.storage import digest

PARSER_VERSION = "markdown-it-py/" + version("markdown-it-py") + "/rows-v2"


def parser() -> MarkdownIt:
    return MarkdownIt("commonmark", {"html": True}).enable("table").use(footnote_plugin)


class HTMLReferences(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.images: list[tuple[str, str]] = []
        self.links: list[str] = []
        self.anchors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        anchor = values.get("id") or (values.get("name") if tag == "a" else None)
        if anchor:
            self.anchors.append(anchor)
        if tag == "img":
            self.images.append((values.get("src") or "", values.get("alt") or ""))
        if tag == "a" and values.get("href"):
            self.links.append(values["href"] or "")


def scan_document(document: SourceDocument, text: str) -> tuple[list[SourceSpan], list, list]:
    tokens = parser().parse(text)
    lines = text.splitlines(keepends=True)
    spans: list[SourceSpan] = []
    images: list[tuple[str, str, str]] = []
    links: list[tuple[str, str]] = []
    headings: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if not token.map or token.type not in {
            "heading_open",
            "paragraph_open",
            "fence",
            "code_block",
            "html_block",
            "table_open",
        }:
            index += 1
            continue
        start, end = token.map
        table: list[list[str]] = []
        selected = [token]
        if token.type == "table_open":
            finish = index + 1
            row: list[str] = []
            while finish < len(tokens) and tokens[finish].type != "table_close":
                current = tokens[finish]
                selected.append(current)
                if current.type == "tr_open":
                    row = []
                if current.type == "inline":
                    row.append(current.content)
                if current.type == "tr_close":
                    table.append(row)
                finish += 1
            index = finish
        elif token.type in {"heading_open", "paragraph_open"}:
            selected.append(tokens[index + 1])
        if token.type == "heading_open":
            level = int(token.tag[1:])
            headings = headings[: level - 1] + [selected[1].content]
        excerpt = "".join(lines[start:end])
        span = SourceSpan(
            id="s-" + digest([document.id, document.snapshot_id, start, end, PARSER_VERSION])[:20],
            snapshot_id=document.snapshot_id,
            path=document.path,
            start_line=start + 1,
            end_line=end,
            headings=list(headings),
            excerpt=excerpt,
            kind=token.type.removesuffix("_open"),
            parser_version=PARSER_VERSION,
            table=table,
        )
        row_refs = {}
        if table and len(table) > 1:
            # Give each data row its own locator and coverage disposition.
            rows = [t for t in selected if t.type == "tr_open" and t.map]
            for row_index, (row, row_token) in enumerate(zip(table[1:], rows[1:], strict=True)):
                assert row_token.map is not None
                row_start, row_end = row_token.map
                row_refs[row_start] = span.id + f"-r{row_index + 1}"
                spans.append(
                    span.model_copy(
                        update={
                            "id": span.id + f"-r{row_index + 1}",
                            "start_line": row_start + 1,
                            "end_line": row_end,
                            "excerpt": "".join(lines[row_start:row_end]),
                            "table_header_start_line": start + 1,
                            "table_header_excerpt": "".join(lines[start : start + 2]),
                            "table": [table[0], row],
                        }
                    )
                )
        else:
            spans.append(span)
        reference_id = next(iter(row_refs.values()), span.id)
        for selected_token in selected:
            if selected_token.type == "tr_open" and selected_token.map:
                reference_id = row_refs.get(selected_token.map[0], reference_id)
            for child in selected_token.children or []:
                if child.type == "text":
                    for match in re.finditer(r"!\[([^\]]*)\](?:\[([^\]]*)\])?", child.content):
                        label = match.group(2) or match.group(1)
                        images.append(
                            (f"unresolved-reference:{label}", match.group(1), reference_id)
                        )
                if child.type == "image":
                    images.append((str(child.attrGet("src") or ""), child.content, reference_id))
                if child.type == "link_open":
                    links.append((str(child.attrGet("href") or ""), reference_id))
                if child.type == "html_inline":
                    html = HTMLReferences()
                    html.feed(child.content)
                    images.extend((src, alt, reference_id) for src, alt in html.images)
                    links.extend((link, reference_id) for link in html.links)
        if token.type == "html_block":
            html = HTMLReferences()
            html.feed(excerpt)
            images.extend((src, alt, span.id) for src, alt in html.images)
            links.extend((link, span.id) for link in html.links)
            if "<table" in excerpt.lower():
                span.warnings.append("HTML table retained intact, including cell spans")
        index += 1
    return spans, images, links


def local_path(root: Path, document: Path, reference: str) -> Path:
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc:
        raise ValueError("Remote or absolute URI requires localization")
    path = (document.parent / unquote(parsed.path)).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Reference escapes the selected source root")
    return path


def snapshot(root: Path, folder: str, raw: bytes, suffix: str) -> tuple[str, str]:
    checksum = digest(raw)
    relative = f"{folder}/{checksum}{suffix}"
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != raw:
        raise ValueError("Snapshot hash collision or corrupt snapshot")
    if not path.exists():
        path.write_bytes(raw)
    return checksum, relative


def inventory(source: Path, destination: Path | None = None, exclude: Path | None = None) -> dict:
    source = source.resolve(strict=True)
    boundary = source if source.is_dir() else source.parent
    paths = sorted(source.rglob("*")) if source.is_dir() else [source]
    documents: list[SourceDocument] = []
    assets: dict[str, ImageAsset] = {}
    warnings: list[str] = []
    exclusions = [exclude.resolve(), (exclude.parent / "output").resolve()] if exclude else []
    for path in paths:
        if not path.is_file() or any(path.resolve().is_relative_to(p) for p in exclusions):
            continue
        if not path.resolve().is_relative_to(boundary):
            warnings.append(f"Outside selected root: {path.name}")
            continue
        if path.suffix.lower() not in {".md", ".markdown"}:
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                warnings.append(f"Unsupported input: {path.relative_to(boundary)}")
            continue
        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8-sig")
        except (OSError, UnicodeError) as exc:
            warnings.append(f"Unreadable input {path.name}: {type(exc).__name__}")
            continue
        checksum, relative = (
            snapshot(destination, "sources", raw, ".md") if destination else (digest(raw), "")
        )
        document = SourceDocument(
            id="d-" + digest(path.relative_to(boundary).as_posix())[:16],
            snapshot_id=checksum,
            path=path.relative_to(boundary).as_posix(),
            content_hash=checksum,
            snapshot=relative,
        )
        documents.append(document)
        _, references, _ = scan_document(document, text)
        for reference, alt, span_id in references:
            asset = ImageAsset(
                id="i-" + digest([document.id, reference])[:20],
                reference=reference,
                span_ids=[span_id],
                alt=alt,
            )
            try:
                if reference.startswith("unresolved-reference:"):
                    raise ValueError("Undefined Markdown image reference")
                image_path = local_path(boundary, path, reference)
                if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                    raise ValueError("Unsupported image format; localize as PNG, JPEG or WebP")
                image_bytes = image_path.read_bytes()
                with Image.open(image_path) as image:
                    image.verify()
                with Image.open(image_path) as image:
                    if image.format not in {"PNG", "JPEG", "WEBP"}:
                        raise ValueError("Image content has unsupported format")
                    asset.width, asset.height = image.size
                asset.content_hash = digest(image_bytes)
                asset.id = "i-" + asset.content_hash[:20]
                if destination:
                    _, asset.snapshot = snapshot(
                        destination, "assets", image_bytes, image_path.suffix.lower()
                    )
                if min(asset.width or 0, asset.height or 0) < 32:
                    raise ValueError("Low-resolution image requires review")
            except (ValueError, OSError) as exc:
                asset.status, asset.reason = "unresolved", str(exc)
                warnings.append(f"Image {reference}: {exc}")
            if asset.id in assets:
                assets[asset.id].span_ids = sorted(set(assets[asset.id].span_ids + [span_id]))
            else:
                assets[asset.id] = asset
    return {
        "documents": [d.model_dump() for d in documents],
        "images": [a.model_dump() for a in assets.values()],
        "warnings": warnings,
        "counts": {"documents": len(documents), "images": len(assets)},
    }


def parse_inventory(root: Path, data: dict) -> dict:
    spans: list[SourceSpan] = []
    links: list[tuple[str, str]] = []
    for item in data["documents"]:
        document = SourceDocument.model_validate(item)
        text = (root / document.snapshot).read_bytes().decode("utf-8-sig")
        parsed, _, references = scan_document(document, text)
        spans.extend(parsed)
        links.extend(references)
    evidence = [EvidenceRef(id=s.id, kind="text", span_id=s.id) for s in spans]
    for asset in data["images"]:
        evidence.extend(
            EvidenceRef(
                id=f"{asset['id']}-{span_id}", kind="image", span_id=span_id, asset_id=asset["id"]
            )
            for span_id in asset["span_ids"]
        )
    warnings = list(data["warnings"])
    by_id = {s.id: s for s in spans}
    anchors: dict[str, set[str]] = {}
    for span in spans:
        for token in parser().parse(span.excerpt):
            for fragment in [token, *(token.children or [])]:
                if fragment.type in {"html_inline", "html_block"}:
                    html = HTMLReferences()
                    html.feed(fragment.content)
                    anchors.setdefault(span.path, set()).update(html.anchors)
        if span.kind == "heading":
            heading = span.headings[-1].lower()
            anchor = re.sub(r"[^\w\- ]", "", heading).replace(" ", "-")
            existing = anchors.setdefault(span.path, set())
            base, number = anchor, 1
            while anchor in existing:
                anchor, number = f"{base}-{number}", number + 1
            existing.add(anchor)
    paths = {d["path"] for d in data["documents"]}
    for reference, span_id in links:
        url = urlsplit(reference)
        if url.scheme or url.netloc:
            continue
        current = by_id[span_id].path
        target = (
            posixpath.normpath((Path(current).parent / unquote(url.path)).as_posix())
            if url.path
            else current
        )
        if target not in paths or (
            url.fragment and unquote(url.fragment) not in anchors.get(target, set())
        ):
            warnings.append(f"Missing cross-reference {reference} at {span_id}")
    return {
        "spans": [s.model_dump() for s in spans],
        "evidence": [e.model_dump() for e in evidence],
        "images": data["images"],
        "documents": data["documents"],
        "warnings": warnings,
    }


def batches(spans: list[dict], limit: int) -> list[list[dict]]:
    result: list[list[dict]] = []
    current: list[dict] = []
    size = 0
    for original in spans:
        span = model_span(original)
        parts = [span]
        if len(json.dumps(span)) > limit:
            # Keep one stable locator while selecting table rows with their headers.
            if span["table"]:
                header = span["table"][0]
                parts = [
                    {**span, "excerpt": "", "table": [header, row]} for row in span["table"][1:]
                ]
            else:
                raise ValueError(
                    f"Source block {span['id']} exceeds batch_chars; increase the limit"
                )
        for part in parts:
            length = len(json.dumps(part))
            if length > limit:
                raise ValueError(f"Source block {span['id']} exceeds batch_chars")
            if current and size + length > limit:
                result.append(current)
                current, size = [], 0
            current.append(part)
            size += length
    if current:
        result.append(current)
    return result


def model_span(span: dict) -> dict:
    """Keep semantic content; snapshots and full locators remain in parse artifacts."""
    result = {k: span[k] for k in ("id", "path", "headings", "kind")}
    result["excerpt"] = "" if span["table"] else span["excerpt"]
    result["table"] = span["table"]
    return result
