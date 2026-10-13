from copy import deepcopy

import pytest

from docgen_graph.document_repairs import (
    repair_document_draft,
    restore_verified_editorial_section,
    unique_visual_quote,
)
from docgen_graph.quality import render_visuals, validate_visual_output


def test_repeated_visual_quote_preserves_all_occurrences_in_minimal_source_window():
    source_text = "Prefix. Żółć → accepted. Different context. Żółć → accepted. Suffix."
    assert unique_visual_quote(source_text, "Żółć → accepted.") == (
        "Żółć → accepted. Different context. Żółć → accepted."
    )


@pytest.mark.parametrize("quote", ["Missing", "two  spaces", "", "unique"])
def test_visual_quote_does_not_normalize_or_invent_missing_text(quote):
    assert unique_visual_quote("One unique phrase with two spaces.", quote) == quote


def test_overlapping_visual_quote_occurrences_are_all_preserved():
    assert unique_visual_quote("prefix aaaa suffix", "aaa") == "aaaa"


def source(label="D1", identifier="e1"):
    return {
        "id": identifier,
        "label": label,
        "text": "Only verified users can register.",
        "file_hash": "source-hash",
        "path": "registration.md",
        "start_line": 7,
    }


def mapping(passage="Only verified users can register."):
    return {
        "obligation_id": "rule1",
        "passage": passage,
        "citation_ids": ["D1"],
        "support_quotes": {"D1": "Only verified users can register."},
    }


def repair(draft, **kwargs):
    return repair_document_draft(
        draft,
        evidence=[source()],
        assertions=[{"id": "rule1", "evidence_ids": ["e1"]}],
        **kwargs,
    )


@pytest.mark.parametrize("mapped_citation", ["", " [Legacy D1]"])
def test_missing_local_citation_is_restored_without_changing_source_or_claim(mapped_citation):
    draft = {
        "markdown": "Only verified users can register.",
        "mappings": [mapping("Only verified users can register." + mapped_citation)],
    }
    original = deepcopy(draft)
    restored, records = repair(draft)
    assert restored["markdown"] == "Only verified users can register. [Legacy D1]"
    assert restored["mappings"][0]["passage"] == restored["markdown"]
    assert restored["mappings"][0]["support_quotes"] == original["mappings"][0]["support_quotes"]
    assert records[0]["kind"] == "local_citation"
    assert draft == original
    again, records = repair(restored)
    assert again == restored
    assert records == []


@pytest.mark.parametrize("fault", ["ambiguous", "changed_meaning", "bad_quote", "wrong_evidence"])
def test_untrusted_or_ambiguous_content_is_left_for_validation(fault):
    draft = {"markdown": "Only verified users can register.", "mappings": [mapping()]}
    if fault == "ambiguous":
        draft["markdown"] += "\n\n" + draft["markdown"]
    elif fault == "changed_meaning":
        draft["markdown"] = "All users can register."
    elif fault == "bad_quote":
        draft["mappings"][0]["support_quotes"]["D1"] = "All users can register."
    else:
        draft["mappings"][0]["obligation_id"] = "unknown-rule"
    restored, records = repair(draft)
    assert restored == draft
    assert records == []


def test_table_citation_is_inside_the_cell_and_all_shared_mappings_are_updated():
    row = "| Registration | Only verified users can register. |"
    first, second = mapping(row), mapping(row)
    second["obligation_id"] = "rule2"
    draft, records = repair_document_draft(
        {"markdown": row, "mappings": [first, second]},
        evidence=[source()],
        assertions=[{"id": key, "evidence_ids": ["e1"]} for key in ["rule1", "rule2"]],
    )
    assert draft["markdown"].endswith("[Legacy D1] |")
    assert all(item["passage"] == draft["markdown"] for item in draft["mappings"])
    assert len(records) == 1


def test_fixed_heading_number_and_case_are_restored_without_relabeling_other_topics():
    text = "### 9. registration\n\nContent\n\n### Sign up\n\n```md\n### Registration\n```"
    draft, records = repair({"markdown": text, "mappings": []}, fixed_headings=["4.1 Registration"])
    assert draft["markdown"].startswith("### 4.1 Registration")
    assert "### Sign up" in draft["markdown"]
    assert "```md\n### Registration\n```" in draft["markdown"]
    assert records == [
        {"kind": "fixed_heading", "before": "9. registration", "after": "4.1 Registration"}
    ]


def test_missing_heading_is_not_guessed_from_unrelated_prose():
    draft = {"markdown": "### Other topic\n\nOnly verified users can register.", "mappings": []}
    assert repair(draft, fixed_headings=["4.1 Registration"])[0] == draft


def test_duplicate_heading_candidates_are_not_merged_or_renamed():
    draft = {"markdown": "### Registration\n\nA\n\n### 9. Registration\n\nB", "mappings": []}
    assert repair(draft, fixed_headings=["4.1 Registration"]) == (draft, [])


def test_shared_passages_with_different_missing_citations_are_restored_together():
    first = mapping("Only verified users can register. [Legacy D1]")
    second = mapping("Only verified users can register. [Legacy D2]")
    second.update(
        obligation_id="rule2",
        citation_ids=["D2"],
        support_quotes={"D2": "Only verified users can register."},
    )
    draft, _ = repair_document_draft(
        {"markdown": "Only verified users can register.", "mappings": [first, second]},
        evidence=[source(), source("D2", "e2")],
        assertions=[
            {"id": "rule1", "evidence_ids": ["e1"]},
            {"id": "rule2", "evidence_ids": ["e2"]},
        ],
    )
    assert draft["markdown"] == "Only verified users can register. [Legacy D1] [Legacy D2]"
    assert all(item["passage"] == draft["markdown"] for item in draft["mappings"])


def test_approved_visual_is_rebuilt_and_moved_to_its_owned_subsection():
    visual = {
        "id": "v1",
        "kind": "image",
        "asset_hash": "asset-hash",
        "text_alternative": "Registration screen",
        "purpose": "Registration",
        "subsection": "4.1 Registration",
        "evidence_ids": ["e1"],
    }
    assets = [{"hash": "asset-hash", "format": "png"}]
    draft, records = repair(
        {
            "markdown": "### 4.1 Registration\n\n![Wrong](wrong.png)\n\n### Other\n\nText",
            "mappings": [],
        },
        visuals=[visual],
        assets=assets,
    )
    rendered = render_visuals([visual], assets, [source()])
    assert rendered in draft["markdown"]
    assert draft["markdown"].index(rendered) < draft["markdown"].index("### Other")
    assert "wrong.png" not in draft["markdown"]
    assert validate_visual_output(draft["markdown"], [visual], assets, [source()]) == []
    assert records[-1]["kind"] == "approved_visuals"
    assert repair(draft, visuals=[visual], assets=assets) == (draft, [])


def test_failed_optional_edit_can_restore_verified_section_with_audit_trail():
    section = {"markdown": "Only verified users can register. [Legacy D1]", "mappings": [mapping()]}
    draft, records = restore_verified_editorial_section(
        section, ["Editor broadened user eligibility"]
    )
    assert draft == section
    draft["mappings"][0]["support_quotes"] = {}
    assert section["mappings"][0]["support_quotes"]
    assert records[0]["findings"] == ["Editor broadened user eligibility"]


def test_changed_mermaid_is_replaced_with_approved_elements_verbatim():
    visual = {
        "id": "flow",
        "kind": "diagram",
        "evidence_ids": ["e1"],
        "diagram": {
            "kind": "flowchart",
            "direction": "TD",
            "description": "Verified user registration",
            "nodes": [
                {"id": "User", "label": "Verified user", "evidence_ids": ["e1"]},
                {"id": "Register", "label": "Registration", "evidence_ids": ["e1"]},
            ],
            "edges": [
                {
                    "id": "eligible",
                    "source": "User",
                    "target": "Register",
                    "label": "Can register",
                    "evidence_ids": ["e1"],
                }
            ],
        },
    }
    draft, records = repair(
        {"markdown": "```mermaid\nflowchart TD\nAnyone --> Register\n```", "mappings": []},
        visuals=[visual],
    )
    assert draft["markdown"] == render_visuals([visual], [], [source()])
    assert "Anyone" not in draft["markdown"]
    assert records == [{"kind": "approved_visuals", "visual_ids": ["flow"]}]


def test_shared_paragraph_ownership_preserves_prose_and_all_source_quotes():
    passage = "First fact. Second fact. [Legacy D1] [Legacy D2]"
    first, second = mapping(passage), mapping(passage)
    first["citation_ids"] = ["D1", "D2"]
    second.update(
        obligation_id="rule2",
        citation_ids=["D1", "D2"],
        support_quotes={"D2": "Only verified users can register."},
    )
    draft = {"markdown": passage, "mappings": [first, second]}
    result, repairs = repair_document_draft(
        draft,
        evidence=[source(), source("D2", "e2")],
        assertions=[
            {"id": "rule1", "evidence_ids": ["e1"]},
            {"id": "rule2", "evidence_ids": ["e2"]},
        ],
    )
    assert result["markdown"] == passage
    assert [item["citation_ids"] for item in result["mappings"]] == [["D1"], ["D2"]]
    assert [item["support_quotes"] for item in result["mappings"]] == [
        item["support_quotes"] for item in draft["mappings"]
    ]
    assert len(repairs) == 2


def test_shared_paragraph_does_not_drop_a_citation_without_another_grounded_owner():
    passage = "First fact. Second fact. [Legacy D1] [Legacy D2]"
    first, second = mapping(passage), mapping(passage)
    first["citation_ids"] = ["D1", "D2"]
    second["citation_ids"] = ["D1", "D2"]
    draft = {"markdown": passage, "mappings": [first, second]}
    assert repair(draft) == (draft, [])


def test_owned_source_with_missing_quote_is_not_dropped_to_make_mapping_pass():
    passage = "First fact. Second fact. [Legacy D1] [Legacy D2]"
    first, second = mapping(passage), mapping(passage)
    first["citation_ids"] = ["D1", "D2"]
    second.update(
        obligation_id="rule2",
        citation_ids=["D2"],
        support_quotes={"D2": "Only verified users can register."},
    )
    draft = {"markdown": passage, "mappings": [first, second]}
    result, repairs = repair_document_draft(
        draft,
        evidence=[source(), source("D2", "e2")],
        assertions=[
            {"id": "rule1", "evidence_ids": ["e1", "e2"]},
            {"id": "rule2", "evidence_ids": ["e2"]},
        ],
    )
    assert result == draft
    assert repairs == []


def test_repeated_citation_locator_keeps_all_occurrences_and_deduplicates_primary():
    passage = "Only verified users can register. [Legacy D1]"
    first = mapping(passage)
    first["additional_passages"] = [
        {key: value for key, value in mapping("[Legacy D1]").items() if key != "obligation_id"}
    ]
    markdown = passage + "\n\nImage caption.\n\n[Legacy D1]"
    draft, repairs = repair({"markdown": markdown, "mappings": [first]})
    assert draft["markdown"] == markdown
    assert draft["mappings"][0]["passage"] == passage
    extra = draft["mappings"][0]["additional_passages"]
    assert len(extra) == 1
    assert extra[0]["passage"] == "Image caption.\n\n[Legacy D1]"
    assert markdown.count(extra[0]["passage"]) == 1
    assert repairs[0]["kind"] == "all_passage_occurrences"
    assert repair(draft) == (draft, [])
