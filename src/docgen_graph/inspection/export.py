import base64
import hashlib
import json
from importlib.resources import files
from pathlib import Path

from docgen_graph.inspection.reader import RunReader
from docgen_graph.storage import atomic_write


def export_run(workspace: Path, run_id: str, output: Path, ledger: Path | None = None) -> dict:
    reader = RunReader(workspace, run_id, ledger)
    output = output.resolve()
    protected = [reader.workspace / name for name in ("runs", "objects", "graphs")]
    protected.extend([reader.workspace / "checkpoints.sqlite"])
    if ledger:
        protected.append(ledger.resolve())
    if any(
        output.is_relative_to(path.resolve()) or path.resolve().is_relative_to(output)
        for path in protected
    ):
        raise ValueError("Output must not overlap input runs, objects, graphs, or databases")
    for name in ("index.html", "inspection.json"):
        if (output / name).is_symlink():
            raise ValueError("Output files cannot be symbolic links")
    data = reader.read()
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    resources = files("docgen_graph.inspection")
    script = resources.joinpath("viewer.js").read_text("utf-8")
    style = resources.joinpath("viewer.css").read_text("utf-8")
    hashes = [
        base64.b64encode(hashlib.sha256(value.encode()).digest()).decode()
        for value in (script, style)
    ]
    html = resources.joinpath("viewer.html").read_text("utf-8")
    html = html.replace("__SCRIPT_HASH__", hashes[0]).replace("__STYLE_HASH__", hashes[1])
    html = html.replace("__DATA__", base64.b64encode(encoded).decode())
    html = html.replace("__STYLE__", style).replace("__SCRIPT__", script)
    atomic_write(output / "inspection.json", encoded)
    atomic_write(output / "index.html", html.encode("utf-8"))
    return {
        "html": str(output / "index.html"),
        "json": str(output / "inspection.json"),
        "diagnostics": len(data["diagnostics"]),
        "capture": data["capture"],
    }
