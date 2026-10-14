import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


def inspect_document(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    headings = []
    pseudo_headings = []
    fence = None
    visual_lines = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        marker = re.match(r"^(`{3,}|~{3,})(.*)$", stripped)
        if marker:
            if fence is None:
                fence = marker.group(1)[0]
                if marker.group(2).strip().lower() == "mermaid":
                    visual_lines.append((index, "diagram"))
            elif marker.group(1)[0] == fence:
                fence = None
            continue
        if fence is not None:
            continue
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*#*$", line)
        if heading:
            numbering = re.match(r"^(\d+(?:\.\d+)*)(?:\.|\s)\s*(.*)$", heading.group(2))
            headings.append(
                {
                    "line": index + 1,
                    "level": len(heading.group(1)),
                    "title": heading.group(2),
                    "number": numbering.group(1) if numbering else None,
                }
            )
        elif re.match(r"^\s*(?:\*\*)?\d+\.\d+(?:\.\d+)*\s+\S", line):
            pseudo_headings.append({"line": index + 1, "text": line[:160]})
        if re.search(r"!\[[^\]]*\]\([^)]+\)", line):
            visual_lines.append((index, "image"))
    numbers = {item["number"] for item in headings if item["number"]}
    orphans = [
        item
        for item in headings
        if item["number"]
        and "." in item["number"]
        and item["number"].rsplit(".", 1)[0] not in numbers
    ]
    level_jumps = [
        {"previous": previous, "next": following}
        for previous, following in zip(headings, headings[1:], strict=False)
        if following["level"] > previous["level"] + 1
    ]
    local_links = []
    for match in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", text):
        target = match.group(1).strip().split(' "', 1)[0].strip("<>")
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        destination = path.parent / unquote(parsed.path)
        local_links.append({"target": target, "exists": destination.exists()})
    captions = []
    for index, kind in visual_lines:
        search_start = index + 1
        if kind == "diagram":
            while search_start < len(lines) and not re.match(
                r"^\s*(?:`{3,}|~{3,})\s*$", lines[search_start]
            ):
                search_start += 1
            search_start += 1
        next_nonempty = next((line.strip() for line in lines[search_start:] if line.strip()), "")
        captions.append(
            {
                "visual_line": index + 1,
                "kind": kind,
                "immediate_caption": bool(
                    re.match(
                        r"^(?:\*{1,2})?(?:Figure|Diagram|Image|Illustration|Rysunek|Schemat)\s+\d+\b",
                        next_nonempty,
                        re.I,
                    )
                ),
                "next_nonempty_line": next_nonempty[:180],
            }
        )
    body = text.split("\n[^", 1)[0]
    blocks = [
        block.strip()
        for block in re.split(r"\n\s*\n", body)
        if block.strip() and not block.lstrip().startswith(("#", "```", "~~~", "<", "![", "|"))
    ]
    word_counts = [len(re.findall(r"\b[\w'-]+\b", block)) for block in blocks]
    citation_refs = re.findall(r"\[\^([^\]]+)\](?!:)", text)
    definitions = re.findall(r"^\[\^([^\]]+)\]:", text, re.M)
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "headings": headings,
        "orphan_numbered_headings": orphans,
        "heading_level_jumps": level_jumps,
        "numbered_pseudo_headings": pseudo_headings,
        "html_table_count": len(re.findall(r"<table\b", text, re.I)),
        "visuals": captions,
        "missing_immediate_visual_captions": sum(
            not item["immediate_caption"] for item in captions
        ),
        "local_links": len(local_links),
        "broken_local_links": [item["target"] for item in local_links if not item["exists"]],
        "citation_uses": len(citation_refs),
        "citation_definitions": len(definitions),
        "unresolved_footnote_references": sorted(set(citation_refs) - set(definitions)),
        "body_words": len(re.findall(r"\b[\w'-]+\b", body)),
        "body_blocks_over_120_words": sum(count > 120 for count in word_counts),
        "longest_body_block_words": max(word_counts, default=0),
        "qualification": (
            "Mechanical presentation checks only. Heading patterns do not prove content hierarchy, "
            "exact citations do not prove entailment, block lengths do not establish readability, "
            "and rendered appearance requires separate inspection."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("documents", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = {
        "method": "Read-only Markdown inspection, no model calls or document mutations",
        "documents": [inspect_document(path) for path in args.documents],
    }
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
