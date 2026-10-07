import html
import json
import shutil
from importlib.resources import files
from pathlib import Path

from docgen.models import Knowledge
from docgen.storage import Store


def graph_preview(destination: Path, graph: Knowledge, parsed: dict, root: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    assets = []
    for asset in parsed["images"]:
        local = None
        if asset["snapshot"]:
            name = Path(asset["snapshot"]).name
            (destination / "assets").mkdir(exist_ok=True)
            shutil.copyfile(root / asset["snapshot"], destination / "assets" / name)
            local = f"assets/{name}"
        assets.append({**asset, "local": local})
    data = json.dumps(
        {"graph": graph.model_dump(), "spans": parsed["spans"], "assets": assets}, ensure_ascii=True
    ).replace("<", "\\u003c")
    template = files("docgen").joinpath("static", "graph.html").read_text("utf-8")
    (destination / "index.html").write_text(template.replace("__GRAPH_DATA__", data), "utf-8")
    for name in ("graph.js", "graph.css", "vis-network.min.js", "vis-network.LICENSE"):
        source = files("docgen").joinpath("static", name)
        (destination / name).write_bytes(source.read_bytes())
    return destination / "index.html"


def run_report(store: Store) -> Path:
    destination = store.root / "report"
    destination.mkdir(exist_ok=True)
    sections = []
    for stage, record in store.manifest["stages"].items():
        attempts = []
        for attempt in record["attempts"]:
            directory = store.attempt_dir(stage, attempt)
            links = []
            if directory.exists():
                for path in sorted(directory.rglob("*")):
                    if path.is_file():
                        relative = "../" + path.relative_to(store.root).as_posix()
                        links.append(
                            f'<li><a href="{html.escape(relative, quote=True)}">'
                            f"{html.escape(path.relative_to(directory).as_posix())}</a></li>"
                        )
            attempts.append(
                f"<details><summary>Attempt {attempt['id']}: "
                f"{html.escape(attempt['status'])}</summary><ul>{''.join(links)}</ul></details>"
            )
        sections.append(
            f"<section><h2>{html.escape(stage)}: {html.escape(record['status'])}</h2>"
            + "".join(attempts)
            + "</section>"
        )
    content = (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Documentation run report</title><style>"
        "body{font:16px system-ui;max-width:1000px;margin:32px auto;padding:16px;color:#222}"
        "section{border-top:1px solid #ddd;padding:12px 0}h2{font-size:18px}"
        "a{color:#08675d}summary{cursor:pointer;padding:8px}li{margin:6px 0}"
        "</style><h1>Documentation run report</h1><p>"
        + html.escape(store.manifest["run_id"] + ": " + store.manifest["status"])
        + '</p><p><a href="../manifest.json">Run manifest</a></p>'
        + "".join(sections)
        + "</html>"
    )
    path = destination / "index.html"
    path.write_text(content, "utf-8")
    return path
