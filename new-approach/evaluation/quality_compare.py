import argparse
import json
import re
from pathlib import Path

from docgen_graph.assets import verify_bundle
from docgen_graph.quality import reading_text, repetition_report


def inspect_candidate(directory: Path) -> dict:
    manifest = json.loads((directory / "candidate-manifest.json").read_text("utf-8"))
    verify_bundle(directory, manifest)
    markdown = (directory / "documentation" / "index.md").read_text("utf-8")
    audit = json.loads((directory / "audit.json").read_text("utf-8"))
    parts = re.split(r"^## (.+)\n", markdown, flags=re.M)
    sections = [
        {"title": parts[index], "markdown": parts[index + 1]}
        for index in range(1, len(parts), 2)
    ]
    placements = audit.get("placements", [])
    invalid = [
        item["id"]
        for item in placements
        if markdown[item["start"] : item["end"]] != item["passage"]
    ]
    if invalid:
        raise ValueError(f"Invalid final placement offsets: {invalid}")
    mappings = [item["obligation_id"] for item in audit["mappings"]]
    if len(set(mappings)) != len(mappings):
        raise ValueError("Duplicate obligation mappings")
    return {
        "candidate_hash": audit["candidate_hash"],
        "title": markdown.splitlines()[0].removeprefix("# "),
        "whole_page_words": len(reading_text(markdown).split()),
        "section_quality": repetition_report(sections),
        "mapped_obligations": len(mappings),
        "presentation_placements": len(placements),
        "shared_placements": sum(len(item["obligation_ids"]) > 1 for item in placements),
        "final_offsets_verified": bool(placements),
        "source_links": audit["source_links"],
        "images": markdown.count("!["),
        "diagrams": markdown.count("```mermaid"),
        "template_decisions": audit.get("template_decisions", []),
        "manifest_verified": True,
    }


def percentage_change(previous: float, current: float) -> float | None:
    return round((current / previous - 1) * 100, 2) if previous else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--revised", required=True, type=Path)
    parser.add_argument("--baseline-metrics", type=Path)
    parser.add_argument("--revised-metrics", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    baseline = inspect_candidate(args.baseline)
    revised = inspect_candidate(args.revised)
    original_links = set(baseline.pop("source_links").values())
    revised_links = set(revised.pop("source_links").values())
    result = {
        "baseline": baseline,
        "revised": revised,
        "section_word_change_percent": percentage_change(
            baseline["section_quality"]["reader_words"],
            revised["section_quality"]["reader_words"],
        ),
        "source_links": {
            "baseline": len(original_links),
            "revised": len(revised_links),
            "missing": sorted(original_links - revised_links),
            "added": sorted(revised_links - original_links),
        },
        "human_reader_scores": None,
        "factual_fidelity": "Requires annotated source review; counts alone do not establish it",
    }
    if args.baseline_metrics and args.revised_metrics:
        previous = json.loads(args.baseline_metrics.read_text("utf-8"))
        current = json.loads(args.revised_metrics.read_text("utf-8"))
        result["paid_call_change_percent"] = percentage_change(
            previous["paid_calls"], current["paid_calls"]
        )
        result["ledger_charge_change_percent"] = percentage_change(
            previous["charged_pln"], current["charged_pln"]
        )
        before = previous.get("invocation_seconds")
        after = current.get("invocation_seconds")
        result["wall_time_change_percent"] = (
            percentage_change(before, after) if before and after else None
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
