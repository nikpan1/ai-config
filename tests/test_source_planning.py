import json

import pytest

from docgen_graph.config import Settings
from docgen_graph.knowledge import KnowledgeGraph
from docgen_graph.planning import (
    SourcePlan,
    bounded_source_overview,
    plan_findings,
    planned_section_findings,
    section_evidence_ids,
    section_queries,
)
from docgen_graph.semantic_graph import SEMANTIC_SCHEMA


def test_graph_assistance_requires_explicit_valid_configuration(tmp_path, monkeypatch):
    monkeypatch.delenv("DOCGEN_GRAPH_ASSISTED_RETRIEVAL", raising=False)
    assert not Settings.load(tmp_path / ".env").graph_assisted_retrieval
    monkeypatch.setenv("DOCGEN_GRAPH_ASSISTED_RETRIEVAL", "true")
    assert Settings.load(tmp_path / ".env").graph_assisted_retrieval
    monkeypatch.setenv("DOCGEN_GRAPH_ASSISTED_RETRIEVAL", "sometimes")
    with pytest.raises(ValueError, match="DOCGEN_GRAPH_ASSISTED_RETRIEVAL"):
        Settings.load(tmp_path / ".env")


def sources():
    return [
        {
            "id": identifier,
            "kind": "docs",
            "path": path,
            "file_hash": identifier,
            "start_line": 1,
            "end_line": 1,
            "heading": "",
            "text": text.ljust(200),
            "role": "legacy_document",
        }
        for identifier, path, text in (
            ("rule", "a.md", "Access requires registration."),
            ("noise", "b.md", "Access analytics are stored separately."),
            ("exception", "z.md", "Invited guests are exempt from registration."),
        )
    ]


def graph_with_relation(tmp_path, status="uncertain", valid=True):
    graph = KnowledgeGraph(tmp_path / "graph.sqlite")
    spans = sources()
    graph.add_evidence(spans)
    with graph.connect() as connection:
        connection.executescript(SEMANTIC_SCHEMA)
        for identifier in ("rule", "exception"):
            source = next(source for source in spans if source["id"] == identifier)
            connection.execute(
                "INSERT INTO semantic_nodes VALUES (?,?)",
                (
                    identifier,
                    json.dumps(
                        {
                            "id": identifier,
                            "quotes": [{"evidence_id": identifier, "text": source["text"].strip()}],
                        }
                    ),
                ),
            )
        edge = {
            "id": "relation",
            "source_id": "rule",
            "target_id": "exception",
            "type": "RELATED",
            "status": status,
            "description": "Model interpretation must never become authoritative source text.",
            "quotes": [
                {"evidence_id": "rule", "text": spans[0]["text"].strip() if valid else "Invented"}
            ],
        }
        connection.execute(
            "INSERT INTO semantic_edges VALUES (?,?,?,?,?)",
            ("relation", "rule", "exception", "RELATED", json.dumps(edge)),
        )
    return graph


def test_graph_navigation_recovers_cross_file_exception_as_original_context(tmp_path):
    graph = graph_with_relation(tmp_path)
    baseline = graph.source_context(["Access"], max_characters=400)
    assisted = graph.source_context(["Access"], max_characters=400, graph_assisted=True)
    assert [source["id"] for source in baseline["evidence"]] == ["rule", "noise"]
    assert [source["id"] for source in assisted["evidence"]] == ["rule", "exception"]
    assert assisted["context_characters"] == 400
    assert assisted["navigation_hints"][0]["status"] == "uncertain"
    assert assisted["navigation_hints"][0]["authority"] == "navigation_only"
    assert "Model interpretation" not in json.dumps(assisted)


def test_invalid_graph_quote_falls_back_to_source_ranking(tmp_path):
    graph = graph_with_relation(tmp_path, valid=False)
    result = graph.source_context(["Access"], max_characters=400, graph_assisted=True)
    assert [source["id"] for source in result["evidence"]] == ["rule", "noise"]
    assert result["navigation_hints"] == []


def test_graph_navigation_cannot_displace_required_source(tmp_path):
    graph = graph_with_relation(tmp_path)
    result = graph.source_context(["Access"], ["noise"], 200, graph_assisted=True)
    assert [source["id"] for source in result["evidence"]] == ["noise"]
    assert result["missing_mandatory_evidence_ids"] == []


def test_small_source_context_is_identical_with_graph_navigation(tmp_path):
    graph = graph_with_relation(tmp_path)
    assert graph.source_context(["Access"]) == graph.source_context(["Access"], graph_assisted=True)


def test_plan_legacy_normalization_and_source_binding():
    legacy = SourcePlan.model_validate({"title": "Guide", "sections": ["Access"]}).model_dump()
    assert legacy["sections"][0]["id"] == "section-1"
    assert plan_findings(legacy, sources()) == [
        "Planned section has no source references: section-1"
    ]
    section = {
        "id": "access",
        "title": "Access",
        "purpose": "Registration and guest exemptions",
        "evidence_ids": ["rule", "exception"],
    }
    plan = {"title": "Guide", "sections": [section]}
    assert plan_findings(plan, sources()) == []
    assert section_queries(section) == ["Access", "Registration and guest exemptions"]
    assert section_evidence_ids(section) == ["rule", "exception"]
    assert planned_section_findings(plan, {"sections": []}) == [
        "Missing planned section: access: Access"
    ]


def test_plan_checks_do_not_mistake_source_id_presence_for_semantic_coverage():
    plan = {
        "title": "Guide",
        "sections": [{"id": "access", "title": "Access", "evidence_ids": ["rule"]}],
    }
    document = {"sections": [{"id": "access", "paragraphs": [{"text": "Incomplete account"}]}]}
    assert planned_section_findings(plan, document) == []
    assert "coverage" not in SourcePlan.model_fields


def test_unknown_source_and_duplicate_section_are_reported():
    section = {"id": "access", "title": "Access", "evidence_ids": ["missing"]}
    issues = plan_findings({"title": "Guide", "sections": [section, section]}, sources())
    assert "Unknown planned source reference: access: missing" in issues
    assert "Duplicate planned section ID: access" in issues


def test_overview_budget_counts_many_evidence_ids_and_reports_truncation():
    many = [
        {"id": f"evidence-{index:06d}", "path": "many-windows.md"} for index in range(1000)
    ]
    small = {"id": "small", "path": "short.md"}
    facts = [{"evidence_ids": ["small"], "statement": "Short source."}]
    overview, incomplete = bounded_source_overview([*many, small], facts, 300)
    assert len(json.dumps(overview, ensure_ascii=False)) <= 300
    assert incomplete
    assert overview == [
        {"path": "short.md", "navigation_summary": "Short source.", "evidence_ids": ["small"]}
    ]
    assert bounded_source_overview(list(reversed([*many, small])), facts, 300) == (
        overview,
        incomplete,
    )
    assert bounded_source_overview([small], facts, 300) == (overview, False)
    _, summary_incomplete = bounded_source_overview(
        [small], [{"evidence_ids": ["small"], "statement": "Long summary " * 100}], 12000
    )
    assert summary_incomplete
