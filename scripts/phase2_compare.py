import argparse
from collections import Counter
from pathlib import Path

from phase2_results import summarize

from docgen.config import Settings
from docgen.storage import Artifacts, read_json, write_json


def architecture(store, result):
    plan = store.get(result["plan_ref"])
    components = plan["components"]
    return {
        key: list(store.iter_table(components[key]))
        for key in (
            "documentation-units",
            "unit-assignments",
            "content-obligations",
            "content-allocations",
            "logical-sections",
            "pages",
        )
    }


def compare(store, automatic, single, reference=None):
    summaries = [summarize(store, thread) for thread in (automatic, single)]
    if any(result["status"] != "ready_for_generation" for result in summaries):
        raise ValueError("Both delivery modes require completed planning exports")
    first, second = summaries
    if first["knowledge_revision"] != second["knowledge_revision"]:
        raise ValueError("Delivery comparison requires the same knowledge revision")
    if (first["delivery_mode"], second["delivery_mode"]) != ("auto", "single_page"):
        raise ValueError("Supply auto and single_page runs in that order")
    if first["unit_policy"] != second["unit_policy"]:
        raise ValueError("Delivery comparison requires the same unit policy")
    architectures = [architecture(store, result) for result in summaries]
    result = {
        "knowledge_revision": first["knowledge_revision"],
        "unit_policy": first["unit_policy"],
        "same_units": architectures[0]["documentation-units"]
        == architectures[1]["documentation-units"],
        "same_ownership": architectures[0]["unit-assignments"]
        == architectures[1]["unit-assignments"],
        "same_logical_sections": architectures[0]["logical-sections"]
        == architectures[1]["logical-sections"],
        "runs": [],
        "reader_questions": read_json(Path(reference))["reader_questions"] if reference else [],
        "reference": reference,
        "reader_question_scoring": "Requires separate inspection; allocation alone is not "
        "evidence of answer quality or reader success",
        "held_out": False,
        "manual_review": "not_performed",
    }
    for summary, structure in zip(summaries, architectures, strict=True):
        section_pages = {
            section: page["id"] for page in structure["pages"] for section in page["section_ids"]
        }
        counts = Counter(
            section_pages[row["canonical_section_id"]]
            for row in structure["content-allocations"]
            if row["disposition"] == "full_treatment"
        )
        result["runs"].append(
            {
                key: summary[key]
                for key in (
                    "thread_id",
                    "plan_ref",
                    "delivery_mode",
                    "coverage",
                    "unit_boundaries",
                    "api_calls",
                    "cache_hits",
                    "model_latency_seconds",
                    "conservative_response_cost_pln",
                    "auditor_reported_blocking_findings",
                )
            }
            | {
                "pages": [
                    {
                        "id": page["id"],
                        "path": page["path"],
                        "role": page["role"],
                        "reader_task": page["reader_task"],
                        "subdivision_rationale": page["rationale"],
                        "canonical_obligations": counts[page["id"]],
                    }
                    for page in structure["pages"]
                ]
            }
        )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", required=True)
    parser.add_argument("--single-page", required=True)
    parser.add_argument("--reference")
    parser.add_argument("--output", default="evaluation/phase2-delivery-comparison.json")
    args = parser.parse_args()
    result = compare(Artifacts(Settings().workspace), args.auto, args.single_page, args.reference)
    write_json(Path(args.output), result)
    print({key: result[key] for key in ("same_units", "same_ownership", "same_logical_sections")})
