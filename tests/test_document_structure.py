from docgen_graph.completion import (
    GroundedDocument,
    citation_excerpt_files,
    citation_findings,
    document_structure_findings,
    document_verification,
    render_grounded_document,
    visual_findings,
)
from docgen_graph.completion_repairs import preserve_planned_sections
from docgen_graph.planning import (
    SourcePlan,
    hierarchy_findings,
    normalize_plan_hierarchy,
    planned_section_findings,
    render_source_plan,
)


def source():
    return {"id": "rule", "path": "rule.md", "text": "Requests require consent.", "start_line": 1}


def citation():
    return {"evidence_id": "rule", "quote": source()["text"]}


def plan():
    return {
        "title": "Requests",
        "sections": [
            {"id": "details", "title": "5. Details", "evidence_ids": ["rule"]},
            {
                "id": "consent",
                "parent_id": "details",
                "title": "5.1 Consent",
                "evidence_ids": ["rule"],
            },
        ],
    }


def document():
    return {
        "title": "Requests",
        "sections": [
            {"id": "details", "title": "Details", "paragraphs": []},
            {
                "id": "consent",
                "parent_id": "details",
                "title": "Consent",
                "paragraphs": [{"id": "p", "text": source()["text"], "sources": [citation()]}],
            },
        ],
    }


def test_renderer_keeps_empty_parent_and_owns_consecutive_heading_numbers():
    candidate = document()
    candidate["sections"].reverse()
    rendered = render_grounded_document(candidate, [source()], {})
    assert "## 1. Details\n\n### 1.1. Consent" in rendered
    assert rendered.index("Details") < rendered.index("Consent")
    assert planned_section_findings(plan(), candidate) == []


def test_plan_normalization_preserves_parent_ids_and_approval_outline():
    normalized = normalize_plan_hierarchy(SourcePlan.model_validate(plan()).model_dump())
    assert normalized["sections"][1]["parent_id"] == "section-1"
    assert normalized["sections"][1]["title"] == "Consent"
    outline = render_source_plan(normalized)
    assert "## 1. Details" in outline
    assert "### 1.1. Consent" in outline
    assert "Sources: rule" in outline


def test_unknown_parent_and_cycles_are_reported_without_infinite_traversal():
    assert hierarchy_findings([{"id": "one", "parent_id": "missing"}])
    assert hierarchy_findings(
        [{"id": "one", "parent_id": "two"}, {"id": "two", "parent_id": "one"}]
    )
    normalized = normalize_plan_hierarchy(
        {"sections": [{"id": "one", "title": "One", "parent_id": "one"}]}
    )
    assert normalized["sections"][0]["parent_id"] == ""


def test_missing_planned_parent_is_restored_without_fabricated_paragraph():
    candidate = document()
    candidate["sections"].pop(0)
    restored, targets = preserve_planned_sections(candidate, plan(), [source()])
    parent = next(item for item in restored["sections"] if item["id"] == "details")
    assert parent["paragraphs"] == []
    assert targets == []
    assert restored["sections"][1]["parent_id"] == "details"
    restored["sections"][1]["paragraphs"] = []
    _, targets = preserve_planned_sections(restored, plan(), [source()])
    assert [target["section_id"] for target in targets] == ["consent"]


def test_body_headings_and_html_wrappers_are_structural_defects():
    candidate = document()
    candidate["sections"][1]["paragraphs"][0]["text"] = (
        "3.1 Consent: Required.\n<table>Example</table>"
    )
    findings = document_structure_findings(candidate)
    assert any("Heading embedded" in item for item in findings)
    assert any("HTML presentation" in item for item in findings)


def test_structured_image_and_diagram_have_numbered_captions_and_exact_sources():
    candidate = document()
    candidate["sections"][1]["visuals"] = [
        {
            "kind": "image",
            "image_hash": "approved",
            "caption": "Consent request",
            "alt": "Consent field",
            "sources": [citation()],
        },
        {
            "kind": "mermaid",
            "mermaid": 'flowchart LR\n A["Request"] --> B["Consent required"]',
            "caption": "Request prerequisite",
            "alt": "Consent is necessary for a request",
            "sources": [citation()],
        },
    ]
    parsed = GroundedDocument.model_validate(candidate).model_dump()
    assets = {"approved": "assets/approved.png"}
    assert visual_findings(parsed, [source()], assets) == []
    assert citation_findings(parsed, [source()]) == []
    rendered = render_grounded_document(parsed, [source()], assets)
    assert "![Consent field](assets/approved.png)\n\n**Figure 1. Consent request** [^1]" in rendered
    assert "```\n\n**Figure 2. Request prerequisite** [^1]" in rendered
    assert "<table" not in rendered
    assert len(citation_excerpt_files(parsed, [source()])) == 1
    assert len(document_verification(parsed, [source()], assets)["visuals"]) == 2


def test_unapproved_image_and_invalid_diagram_citations_are_diagnostics():
    candidate = document()
    candidate["sections"][1]["visuals"] = [
        {
            "kind": "image",
            "image_hash": "invented",
            "caption": "Consent",
            "alt": "Consent",
            "sources": [citation()],
        },
        {
            "kind": "mermaid",
            "mermaid": 'flowchart LR\n A["Request" --> B',
            "caption": "Consent",
            "alt": "Consent",
            "sources": [{"evidence_id": "rule", "quote": "Invented"}],
        },
    ]
    findings = visual_findings(candidate, [source()], {})
    assert any("Unknown visual image" in item for item in findings)
    assert any("Unbalanced Mermaid" in item for item in findings)
    assert any("Invalid exact visual citation" in item for item in findings)
    assert citation_findings(candidate, [source()])
    assert "invented" not in render_grounded_document(candidate, [source()], {})


def test_renderer_removes_model_supplied_figure_numbers_before_numbering():
    candidate = document()
    candidate["sections"][1]["visuals"] = [
        {
            "kind": "mermaid",
            "mermaid": 'flowchart LR\n A["Request"] --> B["Consent required"]',
            "caption": "Figure 12. Request prerequisite",
            "alt": "Consent is necessary for a request",
            "sources": [citation()],
        }
    ]
    rendered = render_grounded_document(candidate, [source()], {})
    assert "**Figure 1. Request prerequisite**" in rendered
    assert "Figure 12" not in rendered
