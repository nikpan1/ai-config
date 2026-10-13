import argparse
import html
import shutil
from pathlib import Path

from markdown_it import MarkdownIt

from docgen_graph.quality import section_anchor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--document", type=Path, required=True)
    parser.add_argument("--mermaid", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    assets = args.document.parent / "assets"
    if assets.exists():
        shutil.copytree(assets, args.output / "assets", dirs_exist_ok=True)
    shutil.copyfile(args.mermaid, args.output / "mermaid.min.js")
    renderer = MarkdownIt("commonmark", {"html": True}).enable("table")
    tokens = renderer.parse(args.document.read_text("utf-8"))
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            token.attrSet("id", section_anchor(tokens[index + 1].content))
    content = renderer.renderer.render(tokens, renderer.options, {})
    content = content.replace('href="../evidence/', 'href="evidence/')
    content = content.replace('href="../source-index.md"', 'href="source-index.md"')
    shutil.copyfile(
        args.document.parent.parent / "source-index.md", args.output / "source-index.md"
    )
    evidence = args.document.parent.parent / "evidence"
    if evidence.exists():
        shutil.copytree(evidence, args.output / "evidence", dirs_exist_ok=True)
    page = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Risk Profiling</title>
<style>
body { font: 16px/1.6 system-ui, sans-serif; color: #18313e; margin: 0; background: #f4f6f8; }
main { max-width: 1050px; margin: 28px auto; background: white; padding: 48px; }
h1,h2,h3 { line-height: 1.3; color: #143d52; }
h2 { margin-top: 2.8em; border-bottom: 1px solid #d8e1e7; padding-bottom: 12px; }
h3 { margin-top: 2em; }
a { color: #1467aa; text-decoration: none; }
table { width: 100%; border-collapse: collapse; margin: 24px 0; }
td,th { border: 1px solid #d8e1e7; padding: 12px; text-align: left; vertical-align: top; }
th { background: #f0f5f7; }
td img { display: block; max-width: 100%; max-height: 540px; margin: auto; }
td:has(.mermaid),td:has(img) { background: #fcfdfe; }
.mermaid { text-align: center; }
.mermaid svg { max-width: 100%; height: auto; }
code { font-size: 0.9em; }
</style></head><body><main>CONTENT</main>
<script src="mermaid.min.js"></script><script>
for (const code of document.querySelectorAll('pre > code.language-mermaid')) {
  const diagram = document.createElement('div');
  diagram.className = 'mermaid';
  diagram.textContent = code.textContent;
  code.parentElement.replaceWith(diagram);
}
mermaid.initialize({startOnLoad: true, securityLevel: 'strict', theme: 'neutral'});
</script></body></html>"""
    destination = args.output / "index.html"
    destination.write_text(page.replace("CONTENT", content), "utf-8")
    print(html.escape(str(destination.resolve())))


if __name__ == "__main__":
    main()
