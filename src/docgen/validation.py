import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

from docgen.authoring import mermaid
from docgen.config import Settings
from docgen.models import Draft, Finding
from docgen.storage import write_json

MERMAID_VERSION = "11.12.0"


def render_diagrams(draft: Draft, directory: Path, settings: Settings) -> list[Finding]:
    diagrams = [(chapter.id, diagram) for chapter in draft.chapters for diagram in chapter.diagrams]
    if not diagrams:
        return []
    node = shutil.which("node")
    cli = Path(settings.mermaid_cli or "node_modules/@mermaid-js/mermaid-cli/src/cli.js").resolve()
    if not node or not cli.is_file():
        return [
            Finding(
                severity="error",
                artifact_id="diagrams",
                message="Install pinned Mermaid CLI and Node, or configure mermaid_cli",
            )
        ]
    try:
        version = subprocess.run(
            [node, str(cli), "--version"], capture_output=True, text=True, timeout=30, check=True
        )
        if version.stdout.strip() != MERMAID_VERSION:
            raise ValueError("Mermaid CLI version does not match the pinned renderer")
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return [Finding(severity="error", artifact_id="diagrams", message=str(exc))]
    directory.mkdir(parents=True, exist_ok=True)
    puppeteer = directory / "puppeteer.json"
    write_json(
        puppeteer,
        {"executablePath": settings.browser_executable} if settings.browser_executable else {},
    )
    findings = []
    for chapter_id, diagram in diagrams:
        name = f"{chapter_id}-{diagram.id}"
        source, output = directory / f"{name}.mmd", directory / f"{name}.svg"
        source.write_text(mermaid(diagram.model_dump()), "utf-8")
        try:
            result = subprocess.run(
                [node, str(cli), "-i", str(source), "-o", str(output), "-p", str(puppeteer)],
                capture_output=True,
                text=True,
                timeout=120,
                check=True,
            )
            write_json(
                directory / f"{name}-renderer.json",
                {"stdout": result.stdout, "stderr": result.stderr},
            )
        except (OSError, subprocess.SubprocessError) as exc:
            findings.append(
                Finding(
                    severity="error",
                    artifact_id=name,
                    message=f"Mermaid rendering failed: {type(exc).__name__}",
                )
            )
    return findings


def check_links(root: Path) -> list[str]:
    problems = []
    parser = MarkdownIt("commonmark")
    for document in root.rglob("*.md"):
        for token in parser.parse(document.read_text("utf-8")):
            for child in token.children or []:
                if child.type not in {"link_open", "image"}:
                    continue
                target = str(child.attrGet("href") or child.attrGet("src") or "")
                url = urlsplit(target)
                if url.scheme or url.netloc:
                    problems.append(f"Unexpected external export link: {target}")
                    continue
                path = (document.parent / unquote(url.path)).resolve() if url.path else document
                if not path.is_relative_to(root.resolve()) or not path.is_file():
                    problems.append(f"Missing export link in {document.name}: {target}")
                elif url.fragment:
                    text = path.read_text("utf-8")
                    anchors = set(re.findall(r'<a id="([^"]+)"', text))
                    if unquote(url.fragment) not in anchors:
                        problems.append(f"Missing export anchor: {target}")
    return problems
