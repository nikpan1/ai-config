import json
import statistics
from pathlib import Path
from urllib.parse import quote

from docgen_graph.source_links import select_text_fragment, visible_html_text


def percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]


def baseline_length(excerpt: str) -> int:
    cells = [item.strip() for item in excerpt.strip().strip("|").split("|")]
    phrase = next((item for item in cells if item.startswith(("As a ", "As an "))), "")
    if not phrase:
        phrase = next((item for item in cells if len(item) >= 35), "")
    return len(quote(phrase, safe="").replace("-", "%2D"))


def evaluate(root: Path) -> dict:
    records = [
        json.loads(line)
        for line in (root / "data/test_data_2_reference/citation-cases.jsonl")
        .read_text("utf-8")
        .splitlines()
    ]
    results = []
    lengths = []
    old_lengths = []
    for case in records:
        if case["expected_behavior"] == "excluded":
            results.append(
                {"case_id": case["case_id"], "expected": "excluded", "actual": "excluded"}
            )
            continue
        markdown = (root / case["markdown_path"]).read_text("utf-8")
        html_text = visible_html_text((root / case["html_path"]).read_text("utf-8"))
        excerpt = next(
            (line for line in markdown.splitlines() if case["evidence_quote"] in line),
            case["evidence_quote"],
        )
        selection = select_text_fragment(
            excerpt, markdown, case["evidence_quote"], html_text, case["claim"]
        )
        actual = "local_evidence" if selection["status"] == "fallback" else "text_fragment"
        entry = {
            "case_id": case["case_id"],
            "expected": case["expected_behavior"],
            "actual": actual,
            "selection": selection,
        }
        if actual == "text_fragment":
            entry["encoded_bytes"] = len(selection["directive"].encode("ascii"))
            entry["baseline_bytes"] = baseline_length(excerpt)
            lengths.append(entry["encoded_bytes"])
            old_lengths.append(entry["baseline_bytes"])
            entry["forbidden_hits"] = [
                fragment
                for fragment in case.get("forbidden_fragments", [])
                if fragment in selection["directive"]
            ]
        results.append(entry)
    summary = {
        "cases": len(records),
        "correct_behaviors": sum(item["expected"] == item["actual"] for item in results),
        "selector_bytes": {
            "median": statistics.median(lengths) if lengths else None,
            "p95": percentile(lengths, 0.95) if lengths else None,
            "max": max(lengths) if lengths else None,
        },
        "baseline_bytes": {
            "median": statistics.median(old_lengths) if old_lengths else None,
            "p95": percentile(old_lengths, 0.95) if old_lengths else None,
            "max": max(old_lengths) if old_lengths else None,
        },
        "results": results,
    }
    return summary


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    report = evaluate(root)
    output = root / ".docgen" / "citation-cases-report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "results"}, indent=2))
