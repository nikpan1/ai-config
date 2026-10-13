import ast
import os
import subprocess
from pathlib import Path

from docgen_graph.assets import (
    ASSET_SUFFIXES,
    attach_asset_evidence,
    freeze_asset,
    resolve_asset_references,
)
from docgen_graph.source_documents import (
    document_context,
)
from docgen_graph.source_documents import (
    document_spans as document_spans,
)
from docgen_graph.source_documents import (
    extraction_packet as extraction_packet,
)
from docgen_graph.source_index import source_role, structural_index
from docgen_graph.storage import ArtifactStore, digest

SKIP_NAMES = {
    ".git",
    ".venv",
    ".docgen",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".pytest_cache",
    ".ruff_cache",
    "vendor",
}
CODE_SUFFIXES = {
    ".java",
    ".xml",
    ".patch",
    ".diff",
    ".properties",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".sql",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".html",
    ".css",
    ".sh",
}
SECRET_NAMES = {".env", "id_rsa", "credentials.json", "secrets.json"}
LOCK_NAMES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "uv.lock",
    "composer.lock",
}
ATTACHMENT_SUFFIXES = {".txt", ".pdf", ".docx", ".csv", ".xlsx"}


def selected_files(root: Path, kind: str) -> tuple[list[Path], list[dict]]:
    if root.is_symlink():
        raise ValueError("Selected root cannot be a symlink")
    root = root.resolve()
    if not root.exists():
        raise ValueError(f"Input does not exist: {root}")
    candidates = []
    selected = []
    excluded = []
    if root.is_file():
        candidates.append(root)
    else:
        for directory, names, files in os.walk(root, followlinks=False):
            base = Path(directory)
            retained = []
            for name in names:
                candidate = base / name
                if name in SKIP_NAMES or candidate.is_symlink():
                    excluded.append(
                        {
                            "path": candidate.relative_to(root).as_posix(),
                            "reason": "excluded directory or symlink",
                        }
                    )
                else:
                    retained.append(name)
            names[:] = retained
            candidates.extend(base / name for name in files)
        candidates.sort()
    for path in candidates:
        relative = path.relative_to(root) if root.is_dir() else Path(path.name)
        if path.is_symlink():
            excluded.append({"path": str(relative), "reason": "symlink"})
            continue
        if not path.is_file():
            continue
        secret = (
            path.name in SECRET_NAMES
            or path.name.startswith(".env.")
            or path.suffix.lower() in {".pem", ".key", ".p12"}
        )
        if any(part in SKIP_NAMES for part in relative.parts) or secret or path.name in LOCK_NAMES:
            excluded.append({"path": str(relative), "reason": "excluded directory or secret"})
            continue
        if kind == "docs" and path.suffix.lower() not in {
            ".md",
            *ASSET_SUFFIXES,
            *ATTACHMENT_SUFFIXES,
        }:
            excluded.append({"path": str(relative), "reason": "unsupported document or asset"})
            continue
        if kind == "code" and path.suffix.lower() not in CODE_SUFFIXES:
            excluded.append({"path": str(relative), "reason": "unsupported code or binary"})
            continue
        selected.append(path)
    if not selected:
        raise ValueError(f"No supported {kind} files selected from {root}")
    return selected, excluded


def git_revision(root: Path) -> dict:
    directory = root if root.is_dir() else root.parent
    try:
        commit = subprocess.run(
            ["git", "-C", str(directory), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "-C", str(directory), "status", "--porcelain", "--", str(root)],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            ).stdout.strip()
        )
        return {"commit": commit, "dirty": dirty}
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "dirty": None}


def snapshot_inputs(
    store: ArtifactStore,
    docs: Path,
    code: Path | None,
    template: Path | None,
    brief: str,
    asset_max_bytes: int = 10000000,
    asset_max_pixels: int = 20000000,
) -> dict:
    files = []
    assets = []
    attachments = []
    exclusions = []
    sources = (("docs", docs), ("code", code)) if code else (("docs", docs),)
    for kind, root in sources:
        if root.is_symlink():
            raise ValueError("Selected root cannot be a symlink")
        root = root.resolve()
        selected, skipped = selected_files(root, kind)
        exclusions.extend({"kind": kind, **item} for item in skipped)
        for path in selected:
            relative = path.relative_to(root) if root.is_dir() else Path(path.name)
            if kind == "docs" and path.suffix.lower() in ASSET_SUFFIXES:
                assets.append(
                    freeze_asset(
                        store, path, relative.as_posix(), asset_max_bytes, asset_max_pixels
                    )
                )
                continue
            before = path.stat()
            content = path.read_bytes()
            after = path.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ValueError(f"Source changed during snapshot: {path}")
            if kind == "docs" and path.suffix.lower() in ATTACHMENT_SUFFIXES:
                from docgen_graph.attachments import extract_attachment

                parsed = extract_attachment(relative.as_posix(), content)
                attachments.append(
                    {
                        "path": relative.as_posix(),
                        "hash": store.put_bytes(content),
                        "size": len(content),
                        **parsed,
                    }
                )
                continue
            try:
                content.decode("utf-8")
            except UnicodeDecodeError:
                exclusions.append({"kind": kind, "path": str(relative), "reason": "invalid UTF-8"})
                continue
            if not content:
                exclusions.append(
                    {"kind": kind, "path": relative.as_posix(), "reason": "empty file"}
                )
                continue
            files.append(
                {
                    "kind": kind,
                    "path": relative.as_posix(),
                    "original_path": str(path.resolve()),
                    "hash": store.put_bytes(content),
                    "size": len(content),
                }
            )
    if not any(item["kind"] == "docs" for item in files) and not attachments:
        raise ValueError("No readable Markdown documentation remains after selection")
    if code and not any(item["kind"] == "code" for item in files):
        raise ValueError("No readable code remains after selection")
    template_bytes = template.resolve().read_bytes() if template else b""
    template_bytes.decode("utf-8")
    assets = resolve_asset_references(store, files, assets, docs.resolve())
    return {
        "schema": 1,
        "files": files,
        "assets": assets,
        "attachments": attachments,
        "asset_limits": {"maximum_bytes": asset_max_bytes, "maximum_pixels": asset_max_pixels},
        "exclusions": exclusions,
        "roots": {"docs": str(docs.resolve()), "code": str(code.resolve()) if code else None},
        "code_revision": git_revision(code) if code else None,
        "template_hash": store.put_bytes(template_bytes),
        "template_path": str(template.resolve()) if template else None,
        "brief": brief,
        "revision": digest(
            [files, assets, attachments, exclusions, store.put_bytes(template_bytes), brief]
        ),
    }


def _span(file: dict, start: int, end: int, heading: str, text: str, role: str) -> dict:
    identifier = digest([file["kind"], file["hash"], file["path"], start, end])[:20]
    return {
        "id": identifier,
        "kind": file["kind"],
        "path": file["path"],
        "file_hash": file["hash"],
        "start_line": start,
        "end_line": end,
        "heading": heading,
        "text": text,
        "role": role,
    }


def code_spans(file: dict, text: str) -> tuple[list[dict], dict]:
    lines = text.splitlines()
    symbols = []
    imports = []
    calls = []
    capability = "generic_text"
    semantic_ranges = []
    if file["path"].endswith(".py"):
        try:
            tree = ast.parse(text)
            capability = "python_ast"
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    start = min([node.lineno] + [item.lineno for item in node.decorator_list])
                    semantic_ranges.append((start, node.end_lineno, node.name))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    symbols.append(
                        {"name": node.name, "line": node.lineno, "end_line": node.end_lineno}
                    )
                elif isinstance(node, ast.Import):
                    imports.extend(
                        {"name": alias.name, "line": node.lineno} for alias in node.names
                    )
                elif isinstance(node, ast.ImportFrom):
                    imports.append({"name": node.module or "", "line": node.lineno})
                elif isinstance(node, ast.Call):
                    target = node.func
                    if isinstance(target, ast.Name):
                        calls.append({"name": target.id, "line": node.lineno})
                    elif isinstance(target, ast.Attribute):
                        calls.append({"name": target.attr, "line": node.lineno})
        except SyntaxError:
            capability = "python_syntax_error"
    spans = []
    intervals = []
    cursor = 1
    for start, end, name in sorted(semantic_ranges):
        if cursor < start:
            intervals.append((cursor, start - 1, "module"))
        intervals.append((start, end, name))
        cursor = end + 1
    if cursor <= len(lines):
        intervals.append((cursor, len(lines), "module"))
    if not intervals and lines:
        intervals.append((1, len(lines), "module"))
    role = source_role(file["path"])
    non_substantive = []
    for start, last, name in intervals:
        if not any(line.strip() for line in lines[start - 1 : last]):
            non_substantive.append({"start_line": start, "end_line": last, "reason": "whitespace"})
            continue
        offset = start - 1
        while offset < last:
            end = offset
            length = 0
            while end < last and end - offset < 200 and length + len(lines[end]) < 10000:
                length += len(lines[end]) + 1
                end += 1
            if end == offset:
                raise ValueError(
                    f"Code line exceeds source span limit: {file['path']}:{offset + 1}"
                )
            chunk = lines[offset:end]
            spans.append(_span(file, offset + 1, end, name, "\n".join(chunk), role))
            offset = end
    metadata = {
        "capability": capability,
        "symbols": symbols,
        "imports": sorted(imports, key=lambda item: (item["name"], item["line"])),
        "calls": calls,
        "non_substantive": non_substantive,
    }
    if capability == "generic_text":
        metadata = structural_index(file["path"], text)
    return spans, metadata


def batches(
    items: list[dict], maximum_chars: int = 12000, maximum_items: int = 12
) -> list[list[str]]:
    result = []
    current = []
    size = 0
    for item in items:
        length = len(item["text"])
        if length > maximum_chars:
            raise ValueError(f"Source span {item['id']} exceeds the configured batch size")
        if current and (size + length > maximum_chars or len(current) >= maximum_items):
            result.append(current)
            current, size = [], 0
        current.append(item["id"])
        size += length
    if current:
        result.append(current)
    return result


def inventory(store: ArtifactStore, snapshot: dict) -> dict:
    spans = []
    analysis = {}
    for file in snapshot["files"]:
        text = store.get_bytes(file["hash"]).decode("utf-8")
        if file["kind"] == "docs":
            spans.extend(document_spans(file, text))
        else:
            owned, metadata = code_spans(file, text)
            spans.extend(owned)
            analysis[file["path"]] = metadata
    for attachment in snapshot.get("attachments", []):
        for position, segment in enumerate(attachment.get("spans", []), 1):
            file = {"kind": "docs", "path": attachment["path"], "hash": attachment["hash"]}
            span = _span(
                file, position, position, attachment["path"], segment["text"], "attachment"
            )
            span.update(
                {
                    "source_kind": "attachment",
                    "locator": segment["locator"],
                    "parser_version": attachment["parser_version"],
                }
            )
            spans.append(span)
    code_units = batches([span for span in spans if span["kind"] == "code"], 12000, 1)
    context = document_context(spans)
    return {
        "schema": 1,
        "spans": spans,
        "analysis": analysis,
        "code_units": code_units,
        **context,
        "assets": attach_asset_evidence(snapshot.get("assets", []), spans),
        "attachments": snapshot.get("attachments", []),
        "revision": digest([snapshot["revision"], [s["id"] for s in spans], analysis, context]),
    }
