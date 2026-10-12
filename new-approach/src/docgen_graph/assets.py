import io
import re
import warnings
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from defusedxml import ElementTree
from markdown_it import MarkdownIt
from PIL import Image

from docgen_graph.contracts import SourceAsset
from docgen_graph.storage import digest

ASSET_SUFFIXES = {".png", ".jpg", ".jpeg", ".svg"}
SVG_TAGS = {
    "svg",
    "g",
    "defs",
    "title",
    "desc",
    "path",
    "rect",
    "circle",
    "ellipse",
    "line",
    "polyline",
    "polygon",
    "text",
    "tspan",
    "textPath",
    "clipPath",
    "mask",
    "linearGradient",
    "radialGradient",
    "stop",
    "pattern",
    "use",
    "symbol",
    "marker",
}


def image_references(text: str) -> list[dict]:
    result = []
    for token in MarkdownIt().enable("table").parse(text):
        if token.type == "html_block" and re.search(r"<(?:img|svg)\b", token.content, re.I):
            result.append(
                {
                    "target": "",
                    "alt": "",
                    "line": token.map[0] + 1,
                    "finding": "Raw HTML images are unsupported; use Markdown images",
                }
            )
        for child in token.children or []:
            if child.type == "image":
                result.append(
                    {
                        "target": child.attrGet("src") or "",
                        "alt": child.content,
                        "line": token.map[0] + 1 if token.map else 1,
                    }
                )
            elif child.type == "html_inline" and re.search(r"<(?:img|svg)\b", child.content, re.I):
                result.append(
                    {
                        "target": "",
                        "alt": "",
                        "line": token.map[0] + 1,
                        "finding": "Raw HTML images are unsupported; use Markdown images",
                    }
                )
    return result


def meaningful_alt(text: str) -> bool:
    return len(text.strip()) >= 5 and text.strip().casefold() not in {
        "image",
        "picture",
        "photo",
        "mockup",
        "screenshot",
        "diagram",
        "untitled",
    }


def validate_asset(content: bytes, suffix: str, maximum_bytes: int, maximum_pixels: int) -> dict:
    if not content or len(content) > maximum_bytes:
        raise ValueError("Asset is empty or exceeds configured byte limit")
    if suffix == ".svg":
        parser = ElementTree.iterparse(io.BytesIO(content), events=("pi",), forbid_dtd=True)
        for _ in parser:
            raise ValueError("SVG contains a processing instruction")
        root = parser.root
        if root.tag != "{http://www.w3.org/2000/svg}svg":
            raise ValueError("SVG extension does not match SVG content")
        for element in root.iter():
            tag = element.tag.removeprefix("{http://www.w3.org/2000/svg}")
            if tag not in SVG_TAGS:
                raise ValueError(f"SVG contains unsupported or active element: {tag}")
            for raw_name, value in element.attrib.items():
                name = raw_name.split("}")[-1].casefold()
                if name.startswith("on") or name in {"style", "base", "src"}:
                    raise ValueError(f"SVG contains active attribute: {name}")
                if name == "href" and not re.fullmatch(r"#[A-Za-z_][\w.-]*", value):
                    raise ValueError("SVG contains an external reference")
                if re.search(r"(?:https?:|data:|javascript:|@import|\\)", value, re.I):
                    raise ValueError("SVG contains unsafe reference content")
                for target in re.findall(r"url\((.*?)\)", value, re.I):
                    if not re.fullmatch(r"#[A-Za-z_][\w.-]*", target):
                        raise ValueError("SVG contains an external paint reference")
        dimensions = {
            key: int(root.attrib[key]) if root.attrib.get(key, "").isdigit() else None
            for key in ("width", "height")
        }
        return {"format": "svg", **dimensions}
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(content)) as image:
            expected = "JPEG" if suffix in {".jpg", ".jpeg"} else "PNG"
            if image.format != expected:
                raise ValueError("Asset extension does not match detected content")
            width, height = image.size
            if width * height > maximum_pixels:
                raise ValueError("Raster exceeds configured pixel limit")
            image.verify()
        with Image.open(io.BytesIO(content)) as image:
            image.load()
        return {"format": expected.lower(), "width": width, "height": height}


def freeze_asset(store, path: Path, relative: str, maximum_bytes: int, maximum_pixels: int) -> dict:
    record = SourceAsset(path=relative, disposition="unreferenced").model_dump()
    try:
        before = path.stat()
        record["size"] = before.st_size
        if before.st_size > maximum_bytes:
            raise ValueError("Asset exceeds configured byte limit")
        content = path.read_bytes()
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError("Asset changed during snapshot")
        record["hash"] = store.put_bytes(content)
        record.update(validate_asset(content, path.suffix.lower(), maximum_bytes, maximum_pixels))
    except (
        ValueError,
        OSError,
        SyntaxError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as error:
        record.update(disposition="rejected", findings=[str(error)])
    return record


def resolve_asset_references(
    store, files: list[dict], assets: list[dict], root: Path
) -> list[dict]:
    by_path = {item["path"]: item for item in assets}
    base = root if root.is_dir() else root.parent
    for file in files:
        if file["kind"] != "docs":
            continue
        text = store.get_bytes(file["hash"]).decode("utf-8")
        for reference in image_references(text):
            reference = {**reference, "source": file["path"]}
            target = unquote(reference["target"])
            parsed = urlsplit(target)
            relative = str(PurePosixPath(file["path"]).parent / target)
            try:
                if reference.get("finding"):
                    raise ValueError(reference["finding"])
                if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
                    raise ValueError("Image must reference a local file without query or fragment")
                if "\\" in target or target.startswith("/") or not target:
                    raise ValueError("Unsafe image path")
                path = base / PurePosixPath(relative)
                if any(part.is_symlink() for part in [path, *path.parents] if part != base.parent):
                    raise ValueError("Image path contains a symlink")
                resolved = path.resolve()
                if not resolved.is_relative_to(base):
                    raise ValueError("Image path escapes the selected root")
                relative = resolved.relative_to(base).as_posix()
                if relative not in by_path:
                    raise ValueError("Image path is missing, excluded, or unsupported")
                record = by_path[relative]
                if record["disposition"] != "rejected":
                    record["disposition"] = "referenced"
            except ValueError as error:
                record = by_path.setdefault(
                    relative,
                    SourceAsset(
                        path=relative, disposition="rejected", findings=[str(error)]
                    ).model_dump(),
                )
            record["references"].append(reference)
    return list(by_path.values())


def attach_asset_evidence(assets: list[dict], spans: list[dict]) -> list[dict]:
    for asset in assets:
        for reference in asset["references"]:
            reference["evidence_ids"] = [
                span["id"]
                for span in spans
                if span["path"] == reference["source"]
                and span["start_line"] <= reference["line"] <= span["end_line"]
            ]
    return assets


def asset_filename(asset: dict) -> str:
    suffix = "jpg" if asset["format"] == "jpeg" else asset["format"]
    return f"{asset['hash'][:32]}.{suffix}"


def verify_bundle(directory: Path, manifest: dict) -> None:
    directory = directory.resolve()
    actual = {
        path.relative_to(directory).as_posix()
        for path in directory.rglob("*")
        if path.is_file() and path.name != "candidate-manifest.json"
    }
    if actual != set(manifest):
        raise ValueError("Candidate contains missing or unmanifested files")
    for relative, checksum in manifest.items():
        path = directory / relative
        if path.is_symlink() or not path.resolve().is_relative_to(directory):
            raise ValueError("Unsafe candidate path")
        if digest(path.read_bytes()) != checksum:
            raise ValueError(f"Candidate changed after review: {relative}")
        if path.suffix == ".md":
            for reference in image_references(path.read_text("utf-8")):
                target = path.parent / unquote(reference["target"])
                if reference.get("finding") or urlsplit(reference["target"]).scheme:
                    raise ValueError("Nonportable candidate image")
                if not target.resolve().is_relative_to(directory) or not target.is_file():
                    raise ValueError("Broken candidate image link")
