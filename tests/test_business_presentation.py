import json
from pathlib import Path

import pytest
from markdown_it import MarkdownIt

from docgen_graph.authoring.template import fold_plan_sections, heading_tree
from docgen_graph.contracts import SectionDraft
from docgen_graph.model import response_schema
from docgen_graph.presentation import (
    business_prose_findings,
    compact_citations,
    exact_support,
    group_repeated_list_citations,
    merge_mapping_occurrences,
    render_subprocess_catalog,
    replace_subsection,
    strip_authored_visuals,
    support_findings,
    uncited_business_passages,
    unmapped_citation_findings,
    visual_support_requirements,
)
from docgen_graph.quality import (
    compile_requirements,
    placement_records,
    position_visuals,
    render_visuals,
)
from docgen_graph.source_links import normalize_citation_syntax
from docgen_graph.storage import ArtifactStore
from docgen_graph.workflow import Pipeline


def test_identical_list_sources_are_shown_once_without_merging_distinct_excerpts():
    source = "[1](<../evidence/C1-first.md>)"
    different = "[2](<../evidence/C1-second.md>)"
    original = f"* Capability. {source}\n* Outcome. {source}"
    rendered, edits = group_repeated_list_citations(original)
    assert rendered == f"* Capability.\n* Outcome.\n\nSources: {source}"
    assert len(edits) == 2
    distinct = original.replace(f"Outcome. {source}", f"Outcome. {different}")
    assert group_repeated_list_citations(distinct) == (distinct, [])


def test_every_citation_requires_its_own_local_mapping():
    first = "A draft opens. [Code C9]"
    second = "Answers can be saved. [Code C9]"
    visual = "<table>Diagram</table>\n\n[Code C9]"
    mapping = {"obligation_id": "draft", "passage": first, "citation_ids": ["C9"]}
    markdown = "\n\n".join([first, second, visual])
    findings = unmapped_citation_findings(markdown, [mapping], [visual])
    assert len(findings) == 1
    assert "line 3" in findings[0]
    mapping["additional_passages"] = [{"passage": second, "citation_ids": ["C9"]}]
    assert not unmapped_citation_findings(markdown, [mapping], [visual])


def test_production_template_separates_instructions_from_reader_structure():
    text = Path("data/template.md").read_text("utf-8")
    contract = compile_requirements(text, "template")
    assert len(contract["headings"]) == 5
    assert not any(item["kind"] == "callout" for item in contract["requirements"])
    assert not any(
        item["kind"] == "heading" and item["text"] == "Humanizing Rules"
        for item in contract["requirements"]
    )
    assert len([item for item in contract["requirements"] if item["kind"] == "flow"]) == 1


def test_quote_schema_preserves_dynamic_citation_keys():
    schema = response_schema(SectionDraft)
    mapping = schema["properties"]["mappings"]["items"]
    assert mapping["properties"]["support_quotes"]["additionalProperties"] == {"type": "string"}


def test_precise_code_quotes_have_distinct_targets_and_real_lines():
    evidence = {
        "id": "code",
        "label": "C1",
        "file_hash": "revision",
        "path": "service.py",
        "start_line": 20,
        "text": "if not consent:\n    reject()\nif expired:\n    retain_history()",
    }
    first = exact_support(evidence, "if not consent:\n    reject()")
    second = exact_support(evidence, "if expired:\n    retain_history()")
    assert (first["start_line"], first["end_line"]) == (20, 21)
    assert (second["start_line"], second["end_line"]) == (22, 23)
    assert first["target_id"] != second["target_id"]
    with pytest.raises(ValueError):
        exact_support(evidence, "invented()")
    assert support_findings([{"citation_ids": ["C1"]}], {"C1": evidence})


def test_compact_citations_keep_changed_support_and_list_boundaries():
    source = "First. [Code C1] Second. [Code C1]\n\nThird. [Code C1]"
    assert compact_citations(source) == "First. Second. [Code C1]\n\nThird. [Code C1]"
    changed = "First. [Code C1] Second. [Legacy D2] Third. [Code C1]"
    assert compact_citations(changed) == changed


def test_technical_exclusion_requires_a_reason_without_reader_text():
    mapping = {
        "obligation_id": "fact",
        "passage": "",
        "disposition": "out_of_scope",
        "scope_reason": "Transaction annotation is an implementation mechanic.",
        "citation_ids": ["C1"],
    }
    placements, findings = placement_records("Business", "", [mapping], {"fact": {}}, {})
    assert not placements and not findings
    _, findings = placement_records(
        "Business", "", [{**mapping, "scope_reason": ""}], {"fact": {}}, {}
    )
    assert findings


def test_business_guard_rejects_implementation_but_preserves_domain_values():
    template = Path("data/template.md").read_text("utf-8")
    assert business_prose_findings("RiskProfileService calls `claimKey()`.", template)
    assert not business_prose_findings(
        "Marketing consent alone does not permit submission. "
        "The result remains valid for 365 days.",
        template,
    )


@pytest.mark.parametrize("additional", [False, True, "grouped"])
def test_shared_paragraph_exports_every_precise_code_target(tmp_path, additional):
    grouped = additional == "grouped"
    additional = additional is True
    store = ArtifactStore(tmp_path)
    pipeline = Pipeline(store, None, "precise-code")
    source = "if not consent:\n    reject()\nif expired:\n    retain_history()"
    frozen = store.put_bytes(source.encode())
    pipeline.graph.add_evidence(
        [
            {
                "id": "e",
                "kind": "code",
                "path": "profile.py",
                "file_hash": frozen,
                "start_line": 1,
                "end_line": 4,
                "text": source,
                "heading": "Profile",
                "role": "implementation",
            }
        ]
    )
    pipeline._approved_plan = lambda state: {
        "title": "Profile",
        "sections": [],
        "source_assets": [],
        "template_requirements": [],
        "template_decisions": [],
        "content_units": [],
        "asset_decisions": [],
    }
    passage = "Consent is required. Expired profiles remain in history. [Code C1]"
    if grouped:
        passage = f"* Rule: {passage}\n* Outcome: {passage}"
    mappings = [
        {
            "obligation_id": str(index),
            "passage": passage,
            "citation_ids": ["C1"],
            "support_quotes": {"C1": quote},
        }
        for index, quote in enumerate(
            ("if not consent:\n    reject()", "if expired:\n    retain_history()")
        )
    ]
    markdown = passage
    placements = [{"id": "paragraph", "passage": passage}]
    if additional:
        repeated = "Submission requires processing consent. [Code C1]"
        mappings[0]["additional_passages"] = [
            {
                "passage": repeated,
                "citation_ids": ["C1"],
                "support_quotes": {"C1": "if not consent:\n    reject()"},
            }
        ]
        markdown += "\n\n" + repeated
        placements.append({"id": "repeated", "passage": repeated})
    result = pipeline.export_candidate(
        {
            "snapshot_ref": store.put({"files": []}),
            "plan_hash": "plan",
            "graph_revision": "graph",
            "edited_ref": store.put(
                [
                    {
                        "title": "Behavior",
                        "markdown": markdown,
                        "mappings": mappings,
                        "placements": placements,
                    }
                ]
            ),
        }
    )
    directory = tmp_path / "runs/precise-code/candidates" / result["candidate_ref"]
    audit = json.loads((directory / "audit.json").read_text())
    assert len(audit["citation_occurrences"]) == (4 if grouped else 3 if additional else 2)
    assert len(audit["mappings"]) == 2
    assert audit["mappings"][0]["passage"] == audit["mappings"][1]["passage"]
    assert audit["placements"][0]["passage"] == audit["mappings"][0]["passage"]
    targets = audit["citation_occurrences"]
    assert targets[0]["local_target"] != targets[1]["local_target"]
    for target in targets:
        path = directory / "documentation" / target["local_target"]
        assert path.is_file()
        assert target["support_range"]["snapshot_hash"] == frozen
    assert targets[0]["support_range"]["start_line"] == 1
    assert targets[1]["support_range"]["start_line"] == 3
    if grouped:
        output = (directory / "documentation/index.md").read_text()
        assert output.count("Sources: ") == 1
        assert "[1]" not in audit["placements"][0]["passage"]
        assert audit["placements"][0]["passage"] in output
    with pytest.raises(ValueError, match="precise local passage support"):
        pipeline.export_candidate(
            {
                "snapshot_ref": store.put({"files": []}),
                "plan_hash": "plan",
                "graph_revision": "graph",
                "edited_ref": store.put(
                    [
                        {
                            "title": "Behavior",
                            "markdown": markdown + "\n\nUnmapped. [Code C1]",
                            "mappings": mappings,
                            "placements": placements,
                        }
                    ]
                ),
            }
        )
    if additional:
        assert targets[2]["local_target"] == targets[0]["local_target"]
        assert (
            audit["placements"][1]["passage"]
            == audit["mappings"][0]["additional_passages"][0]["passage"]
        )


def test_flat_planner_children_keep_their_ownership_and_visual_home():
    tree = heading_tree("## 5. Reference\n### 5.1 Prerequisites\n### 5.2 Views")
    sections = [
        {"title": "5. Reference", "purpose": "Details", "group_ids": []},
        {"title": "5.1 Prerequisites", "purpose": "Setup", "group_ids": ["setup"]},
        {
            "title": "5.2 Views",
            "purpose": "Views",
            "group_ids": ["views"],
            "visuals": [{"id": "screen"}],
        },
    ]
    result = fold_plan_sections(tree, sections)
    assert len(result) == 1
    assert result[0]["group_ids"] == ["setup", "views"]
    assert result[0]["visuals"][0]["subsection"] == "5.2 Views"
    assert len(result[0]["subsections"]) == 2


def test_visual_html_keeps_two_rows_and_the_correct_subsection():
    visual = {
        "id": "screen",
        "kind": "image",
        "asset_hash": "image",
        "purpose": "Result view",
        "text_alternative": "Assessment result",
        "evidence_ids": ["e"],
        "subsection": "5.2 Views",
    }
    assets = [{"hash": "image", "format": "png"}]
    evidence = [{"id": "e", "label": "D1"}]
    block = render_visuals([visual], assets, evidence)
    html = MarkdownIt("commonmark", {"html": True}).render(block)
    assert html.count("<tr>") == 2
    assert html.count("<td") == 2
    assert '<img src="assets/image.png"' in html
    assert '<td style="text-align: center;">' in html
    assert "<strong>Result view</strong>" in html
    markdown = "### 5.2 Views\n\n### 5.3 Rules\n\nA rule.\n\n" + block
    placed = position_visuals(markdown, [visual], assets, evidence)
    assert placed.index("<table>") < placed.index("### 5.3 Rules")
    assert placed.count("<table>") == 1


def test_business_checks_ignore_diagram_ids_but_check_visible_labels():
    template = "Business Behavior Contract"
    diagram = '```mermaid\nflowchart LR\nnodeCheckExisting["Review current profile"]\n```'
    assert not business_prose_findings(diagram, template)
    assert business_prose_findings(
        diagram.replace("Review current profile", "Claim Submission Key"), template
    )
    assert uncited_business_passages("The system guarantees consistency.", template)
    assert not uncited_business_passages("Consent is required. [Legacy D1]", template)
    assert business_prose_findings("Risk Profiling Service checks idempotency.", template)


def test_short_citation_normalization_preserves_code_and_existing_links():
    text = "Rule [C9]. Source [D3]. `[C9]` [C9](file.md)."
    assert normalize_citation_syntax(text) == (
        "Rule [Code C9]. Source [Legacy D3]. `[C9]` [C9](file.md)."
    )


def test_visual_support_keeps_distinct_transition_and_caption_targets():
    visual = {
        "id": "flow",
        "purpose": "Assessment process",
        "evidence_ids": ["code", "legacy"],
        "diagram": {
            "nodes": [{"id": "start", "label": "Begin", "evidence_ids": ["code"]}],
            "edges": [{"id": "submit", "label": "Consent required", "evidence_ids": ["code"]}],
        },
    }
    required = visual_support_requirements([visual])
    assert len({item["support_id"] for item in required}) == 3
    assert {item["element_id"] for item in required} == {"start", "submit", "caption"}
    assert required[-1]["evidence_id"] == "legacy"


def test_navigation_does_not_need_source_evidence():
    assert not uncited_business_passages(
        "For detailed business rules, see Section 5.3.", "Business Behavior Contract"
    )


def test_subprocess_catalog_has_source_based_identity_and_exact_row_mappings():
    record = {
        "title": "Repeat submission",
        "purpose": "Return an existing assessment.",
        "participants": "Investor",
        "result": "The same answers return the existing result.",
        "mappings": [
            {
                "obligation_id": "fact",
                "passage": "",
                "citation_ids": ["C1"],
                "support_quotes": {"C1": "return existingResult;"},
            }
        ],
    }
    table, mappings, catalog = render_subprocess_catalog([record])
    assert mappings[0]["passage"] in table
    assert mappings[0]["disposition"] == "overview"
    assert mappings[0]["support_quotes"]["C1"] == "return existingResult;"
    renamed = {**record, "title": "Identical submission"}
    assert render_subprocess_catalog([renamed])[2][0]["id"] == catalog[0]["id"]
    text = "### 4.1 Main Process Overview\n\nFlow.\n\n### 4.2 Key Subprocesses\n\nDraft text."
    rendered = replace_subsection(text, "4.2 Key Subprocesses", table)
    assert "Draft text." not in rendered
    assert "Flow." in rendered
    assert rendered.count("### 4.2") == 1


def test_every_business_table_row_needs_its_own_citation():
    table = "| Rule | Result |\n| --- | --- |\n| A | Supported [Code C1] |\n| B | Unsupported |"
    findings = uncited_business_passages(table, "Business Behavior Contract")
    assert len(findings) == 1
    assert "Unsupported" in findings[0]


def test_writer_visuals_are_discarded_before_approved_rendering():
    text = (
        "Business paragraph. [Legacy D1]\n\n"
        "<table><tr><td>\n\n![View](wrong-path)\n\n</td></tr><tr><td>Caption</td></tr></table>"
        "\n\n[Legacy D2]\n\n"
        "```mermaid\nflowchart LR\na-->b\n```\n\n[Code C1]\n\n"
        "| Rule | Effect |\n| --- | --- |\n| A | B [Legacy D3] |"
    )
    result = strip_authored_visuals(text)
    assert "wrong-path" not in result
    assert "mermaid" not in result
    assert "D2" not in result
    assert "C1" not in result
    assert "Business paragraph. [Legacy D1]" in result
    assert "| A | B [Legacy D3] |" in result


def test_required_views_keep_one_fact_and_two_validated_placements():
    primary = {
        "obligation_id": "fact",
        "passage": "Consent is required. [Code C1]",
        "citation_ids": ["C1"],
        "support_quotes": {"C1": "Consent is required."},
    }
    repeated = {**primary, "passage": "| Consent | Required [Code C1] |"}
    merged = merge_mapping_occurrences([primary], [repeated])
    assert len(merged) == 1
    markdown = primary["passage"] + "\n\n" + repeated["passage"]
    placements, findings = placement_records(
        "Rules", markdown, merged, {"fact": {"evidence_ids": ["e"]}}, {"e": {"label": "C1"}}
    )
    assert not findings
    assert len(placements) == 2
    assert all(item["obligation_ids"] == ["fact"] for item in placements)
