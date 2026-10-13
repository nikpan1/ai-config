import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from docgen_graph.knowledge import KnowledgeGraph
from docgen_graph.semantic_graph import SEMANTIC_SCHEMA
from docgen_graph.storage import atomic_write

CASES = [
    {
        "name": "library_cross_document_exception",
        "query": "Borrowing",
        "texts": [
            "Borrowing requires active membership.",
            "Borrowing statistics are refreshed every evening.",
            "Invited readers do not need membership.",
        ],
        "required": ["s0", "s2"],
        "target": 2,
    },
    {
        "name": "warehouse_independent_outcomes",
        "query": "Shipment",
        "texts": [
            "Shipment is blocked when the address is incomplete.",
            "Shipment notifications are translated into French.",
            "Missing customs data retains draft status; it does not imply an address fault.",
        ],
        "required": ["s0", "s2"],
        "target": 2,
    },
    {
        "name": "conflicting_retention_versions",
        "query": "Retention",
        "texts": [
            "Retention policy alpha says 30 days.",
            "Retention dashboard refreshes hourly.",
            "Policy beta says 45 days. Neither policy supersedes the other explicitly.",
        ],
        "required": ["s0", "s2"],
        "target": 2,
    },
    {
        "name": "incorrect_but_quoted_edge_can_hurt",
        "query": "Rental",
        "texts": [
            "Rental requires a deposit.",
            "Rental deposit is waived for annual subscribers.",
            "Office stationery requests are reviewed weekly.",
        ],
        "required": ["s0", "s1"],
        "target": 2,
    },
    {
        "name": "invalid_quote_falls_back",
        "query": "Warranty",
        "texts": [
            "Warranty lasts two years.",
            "Warranty does not cover water damage.",
            "Contact details are listed in the appendix.",
        ],
        "required": ["s0", "s1"],
        "target": 2,
        "invalid_quote": True,
    },
    {
        "name": "small_corpus_unchanged",
        "query": "Access",
        "texts": [
            "Access requires approval.",
            "Guests follow a separate approval procedure.",
            "Emergency responders are exempt.",
        ],
        "required": ["s0", "s1", "s2"],
        "target": 2,
        "budget": 600,
    },
]


def run_case(directory: Path, case: dict) -> dict:
    graph = KnowledgeGraph(directory / f"{case['name']}.sqlite")
    spans = [
        {
            "id": f"s{index}",
            "kind": "docs",
            "path": f"document-{index}.md",
            "file_hash": f"hash-{index}",
            "start_line": 1,
            "end_line": 1,
            "heading": "",
            "text": text.ljust(200),
            "role": "legacy_document",
        }
        for index, text in enumerate(case["texts"])
    ]
    graph.add_evidence(spans)
    with graph.connect() as connection:
        connection.executescript(SEMANTIC_SCHEMA)
        for index in (0, case["target"]):
            node = {
                "id": f"n{index}",
                "quotes": [{"evidence_id": f"s{index}", "text": case["texts"][index]}],
            }
            connection.execute(
                "INSERT INTO nodes VALUES (?,?,?,?)",
                (node["id"], "Concept", "Navigation concept", "fixture"),
            )
            connection.execute(
                "INSERT INTO semantic_nodes VALUES (?,?)", (node["id"], json.dumps(node))
            )
        edge = {
            "id": "edge",
            "source_id": "n0",
            "target_id": f"n{case['target']}",
            "type": "RELATED",
            "status": "uncertain",
            "quotes": [
                {
                    "evidence_id": "s0",
                    "text": "Invented evidence" if case.get("invalid_quote") else case["texts"][0],
                }
            ],
        }
        connection.execute(
            "INSERT INTO semantic_edges VALUES (?,?,?,?,?)",
            ("edge", edge["source_id"], edge["target_id"], "RELATED", json.dumps(edge)),
        )
    result = {"case": case, "source_only": {}, "graph_assisted": {}}
    for assisted, name in ((False, "source_only"), (True, "graph_assisted")):
        context = graph.source_context(
            [case["query"]],
            max_characters=case.get("budget", 400),
            graph_assisted=assisted,
        )
        selected = {source["id"] for source in context["evidence"]}
        required = set(case["required"])
        result[name] = {
            "selected_evidence_ids": sorted(selected),
            "required_evidence_recall": len(selected & required) / len(required),
            "complete_required_context": required <= selected,
            "characters": context["context_characters"],
        }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, default=Path(".docgen"))
    arguments = parser.parse_args()
    arguments.workspace.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="navigation-ab-", dir=arguments.workspace) as directory:
        cases = [run_case(Path(directory), case) for case in CASES]
    report = {
        "evaluation_type": "controlled_deterministic_source_selection",
        "limitations": [
            "Synthetic fixtures and hand-constructed edges are not held-out real-world data.",
            "Measures source retrieval only, not generated content quality or semantic entailment.",
            "An anchored but semantically wrong edge can displace a relevant original source.",
            "Small corpora use the same complete original context in both variants.",
        ],
        "cases": cases,
    }
    atomic_write(arguments.output, json.dumps(report, indent=2).encode())
    print(json.dumps({"output": str(arguments.output), "cases": len(cases)}))


if __name__ == "__main__":
    main()
