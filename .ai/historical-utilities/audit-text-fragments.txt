import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def normalized(value):
    return " ".join(value.split()).casefold()


def audit(root, markdown_paths):
    links = []
    for markdown in markdown_paths:
        content = markdown.read_text(encoding="utf-8")
        links.extend(re.findall(r"https?://127\.0\.0\.1:8765/[^>\s)]+", content))
    failures = []
    for link in sorted(set(links)):
        parsed = urlsplit(link)
        if parsed.netloc != "127.0.0.1:8765" or ":~:text=" not in parsed.fragment:
            failures.append({"url": link, "reason": "invalid local source fragment"})
            continue
        source = (root / unquote(parsed.path).lstrip("/")).resolve()
        if not source.is_relative_to(root) or not source.is_file():
            failures.append({"url": link, "reason": "source file is missing"})
            continue
        phrase = unquote(parsed.fragment.split(":~:text=", 1)[1])
        parser = VisibleText()
        parser.feed(source.read_text(encoding="utf-8"))
        if normalized(phrase) not in normalized(" ".join(parser.parts)):
            failures.append({"url": link, "reason": "text is absent from rendered source"})
    return {
        "markdown_files": len(markdown_paths),
        "direct_link_occurrences": len(links),
        "unique_direct_links": len(set(links)),
        "matched_unique_links": len(set(links)) - len(failures),
        "failures": failures,
    }


parser = argparse.ArgumentParser()
parser.add_argument("paths", nargs="+", type=Path)
args = parser.parse_args()
root = (Path(__file__).resolve().parents[1] / "data" / "test_data_1_html").resolve()
paths = [path for item in args.paths for path in (item.rglob("*.md") if item.is_dir() else [item])]
print(json.dumps(audit(root, paths), indent=2, ensure_ascii=False))
