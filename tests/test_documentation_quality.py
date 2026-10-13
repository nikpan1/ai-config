import io
import json
import shutil
import sqlite3
from contextlib import closing
from copy import deepcopy

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from PIL import Image
from test_pipeline_restart import FixtureModel

from docgen_graph.assets import image_references, validate_asset, verify_bundle
from docgen_graph.contracts import DiagramSpec, PagePlanDraft
from docgen_graph.ingestion import inventory, snapshot_inputs
from docgen_graph.knowledge import normalized_assertion
from docgen_graph.model import response_schema
from docgen_graph.quality import (
    compile_requirements,
    content_groups,
    content_units,
    diagram_element_ids,
    diagram_source,
    placement_records,
    reading_text,
    render_visuals,
    repetition_report,
    validate_diagram,
    validate_quality_plan,
    validate_template_output,
    validate_visual_output,
)
from docgen_graph.storage import ArtifactStore, digest
from docgen_graph.workflow import Pipeline, _markdown_changes

SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8">'
    b'<rect width="8" height="8"/></svg>'
)


def test_reading_metrics_preserve_claims_between_citations():
    paragraph = (
        "First scoped claim [Legacy D1](<https://example.com/first>). "
        "Second distinct claim [Legacy D2](<https://example.com/second>). "
        "Unlinked third claim [Legacy D3, Legacy D4]."
    )
    value = reading_text(paragraph)
    assert "First scoped claim" in value
    assert "Second distinct claim" in value
    assert "Unlinked third claim" in value
    assert "Legacy" not in value and "example.com" not in value


def test_editorial_diff_excludes_blank_line_cleanup_but_keeps_changed_claims():
    rows = [f"| Rule {index} | Scoped fact [Legacy D{index}] |" for index in range(30)]
    retained = "\n\n".join(f"Unchanged context {index}." for index in range(5))
    original = "\n\n".join(rows) + "\n\n" + retained + "\n\nA scoped claim [Legacy D40]."
    edited = "\n".join(rows) + "\n\n" + retained + "\n\nA changed claim [Legacy D40]."
    before, after = _markdown_changes(original, edited)
    assert "A scoped claim" in before and "A changed claim" in after
    assert "Scoped fact" not in before + after
    assert _markdown_changes("\n\n".join(rows), "\n".join(rows)) == ("", "")


def raster(kind="PNG", size=(3, 2)):
    output = io.BytesIO()
    Image.new("RGB", size).save(output, format=kind)
    return output.getvalue()


@pytest.mark.parametrize(
    "suffix,content",
    [
        (".png", raster()),
        (".jpg", raster("JPEG")),
        (".jpeg", raster("JPEG")),
        (".svg", SVG),
    ],
)
def test_assets_validate_detected_format_and_dimensions(suffix, content):
    record = validate_asset(content, suffix, 10000, 100)
    assert record["width"] and record["height"]


@pytest.mark.parametrize(
    "content",
    [
        b"not xml",
        b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        SVG.replace(b"<rect", b'<rect onclick="alert(1)"'),
        SVG.replace(b"<rect", b'<rect style="fill: url(https://bad.test/x)"'),
        SVG.replace(b"<rect", b'<use href="https://bad.test/x"/><rect'),
        b'<!DOCTYPE svg [<!ENTITY x "bad">]>' + SVG,
        SVG.replace(b"<rect", b"<foreignObject/><rect"),
        SVG.replace(b"<rect", b'<rect fill="url(data:bad)"'),
    ],
)
def test_unsafe_and_malformed_svg_is_rejected(content):
    with pytest.raises((ValueError, SyntaxError)):
        validate_asset(content, ".svg", 10000, 100)


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "utf-16-be", "utf-16-le"])
@pytest.mark.parametrize(
    "prefix,suffix",
    [
        ('<?xml-stylesheet href="https://example.invalid/style.css"?>', ""),
        ("", '<?xml-stylesheet href="https://example.invalid/style.css"?>'),
        ("<!DOCTYPE svg>", ""),
    ],
)
def test_svg_xml_safety_is_independent_of_encoding(encoding, prefix, suffix):
    content = (prefix + SVG.decode("utf-8") + suffix).encode(encoding)
    with pytest.raises(ValueError):
        validate_asset(content, ".svg", 10000, 100)


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "utf-16-be", "utf-16-le"])
def test_inert_svg_accepts_supported_xml_encodings(encoding):
    content = SVG.decode("utf-8").encode(encoding)
    assert validate_asset(content, ".svg", 10000, 100) == {
        "format": "svg",
        "width": 8,
        "height": 8,
    }


def test_raster_limits_and_extension_mismatch():
    with pytest.raises(ValueError, match="pixel"):
        validate_asset(raster(size=(11, 10)), ".png", 10000, 100)
    with pytest.raises(ValueError, match="byte"):
        validate_asset(raster(), ".png", 10, 100)
    with pytest.raises(ValueError, match="extension"):
        validate_asset(raster(), ".jpg", 10000, 100)
    with pytest.raises(OSError):
        validate_asset(b"broken image", ".png", 10000, 100)


def test_asset_snapshot_deduplicates_references_and_accounts_for_invalid_paths(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "one.svg").write_bytes(SVG)
    (docs / "copy.svg").write_bytes(SVG)
    (docs / "unused.svg").write_bytes(SVG.replace(b'width="8"', b'width="9"', 1))
    (docs / "source.md").write_text(
        "# Flow\n\n![Approval process](one.svg)\n\n![Approval process again][ref]\n\n"
        "[ref]: copy.svg\n\n![Missing illustration](missing.png)\n\n"
        "![Outside illustration](../outside.png)\n\n![Remote](https://example.com/a.png)\n",
        encoding="utf-8",
    )
    template = tmp_path / "template.md"
    template.write_text("## Flow\n", encoding="utf-8")
    store = ArtifactStore(tmp_path / "runtime")
    snapshot = snapshot_inputs(store, docs, None, template, "")
    result = inventory(store, snapshot)
    assets = {item["path"]: item for item in result["assets"]}
    assert assets["one.svg"]["hash"] == assets["copy.svg"]["hash"]
    assert assets["one.svg"]["references"][0]["evidence_ids"]
    assert assets["unused.svg"]["disposition"] == "unreferenced"
    assert sum(item["disposition"] == "rejected" for item in assets.values()) == 3
    (docs / "one.svg").write_bytes(b"changed")
    assert store.get_bytes(assets["one.svg"]["hash"]) == SVG


def test_markdown_reference_images_in_tables_and_code():
    text = (
        "| A | Image |\n| --- | --- |\n| Rule | ![Review panel](a.svg) |\n\n"
        "```\n![Not an image](none.svg)\n```\n"
    )
    references = image_references(text)
    assert len(references) == 1
    assert references[0]["line"] == 3


def test_template_inventory_retains_purpose_tables_callouts_flow_and_optional_sections():
    source = (
        "# [Product]\n\n| Detail | Value |\n| --- | --- |\n| Scope | [Scope] |\n\n"
        "## Overview\n\n[Explain the outcome.]\n\n> **At a glance**\n\n"
        "| Role | Limit |\n| --- | --- |\n| Sample | 999 |\n\n"
        "## Flow\n\n```mermaid\nflowchart LR\nA --> B\n```\n\n"
        "### Secondary flow: [Optional flow]\n\n| Step | Result |\n| --- | --- |\n"
    )
    contract = compile_requirements(source, digest(source))
    assert contract["headings"] == ["Overview", "Flow"]
    assert {item["kind"] for item in contract["requirements"]} >= {
        "purpose",
        "table",
        "metadata",
        "flow",
        "callout",
        "conditional",
    }
    assert all("999" not in item["text"] for item in contract["requirements"])
    optional_table = next(
        item for item in contract["requirements"] if item["columns"] == ["Step", "Result"]
    )
    assert optional_table["required"] is False
    sections = [
        {"title": "Overview", "markdown": "A summary."},
        {"title": "Flow", "markdown": "Unknown."},
    ]
    assert len(validate_template_output(sections, contract, [])) == 3
    decisions = [
        {"requirement_id": item["id"], "disposition": "inapplicable"}
        for item in contract["requirements"]
        if item["kind"] == "flow"
    ]
    assert len(validate_template_output(sections, contract, decisions)) == 2


def test_content_units_preserve_identical_words_with_different_scopes_and_exceptions():
    facts = [
        {
            "id": str(index),
            "subject": "Approval",
            "predicate": "limits",
            "statement": "The limit is 500.",
            "scope": scope,
            "modality": "required",
            "conditions": ["Active account"],
            "exceptions": exceptions,
            "evidence_ids": ["e"],
        }
        for index, (scope, exceptions) in enumerate(
            [
                ("shopper", []),
                ("merchant", []),
                ("shopper", ["Manual review"]),
                ("shopper", []),
            ]
        )
    ]
    spans = {"e": {"kind": "docs", "path": "rules.md", "heading": "Rules", "text": "Limits"}}
    groups = content_groups(facts, spans)
    units = content_units(groups, [{"title": "Rules", "group_ids": [g["id"] for g in groups]}])
    assert len(units) == 1
    assert len(units[0]["scoped_variants"]) == 4
    assert len(units[0]["common_facts"]) == 1
    assert units[0]["common_facts"][0]["obligation_ids"] == ["0", "3"]
    assert units[0]["exceptions"] == ["Manual review"]


def test_template_callout_fields_and_export_metadata_have_distinct_placement():
    instruction = "> **Document purpose:** Replace every bracketed prompt with supported content."
    header = "| Document detail | Value |"
    template = (
        instruction
        + "\n\n"
        + header
        + "\n| --- | --- |\n| Scope | [Scope] |\n\n## Summary\n\n"
        + "> **At a glance**\n> - **Primary users:** [Roles]\n> - **Open question:** [Unknown]\n"
    )
    contract = compile_requirements(template, digest(template))
    labels = {item["text"] for item in contract["requirements"] if item["kind"] == "callout"}
    assert labels == {"At a glance", "Primary users", "Open question"}
    incomplete = [
        {"title": "Summary", "markdown": "> **At a glance**\n\n" + instruction + "\n" + header}
    ]
    findings = validate_template_output(incomplete, contract, [])
    assert any("Primary users" in item for item in findings)
    assert any("Open question" in item for item in findings)
    assert any("metadata belongs" in item for item in findings)
    assert any("Copied template instructions" in item for item in findings)
    complete = [
        {
            "title": "Summary",
            "markdown": (
                "> **At a glance**\n> - **Primary users:** Shoppers\n"
                "> - **Open question:** Retention duration is unspecified.\n"
            ),
        }
    ]
    assert validate_template_output(complete, contract, []) == []


def test_content_groups_split_scoped_variants_by_complete_evidence_size():
    facts = [
        {
            "id": str(index),
            "subject": "Handoff",
            "predicate": "retains decision details",
            "statement": "The handoff retains date, conditions and open questions.",
            "scope": scope,
            "modality": "required",
            "conditions": [],
            "exceptions": [f"Scoped exception {index}"],
            "evidence_ids": [str(index)],
        }
        for index, scope in enumerate(["Checkout", "Operations", "Discovery"])
    ]
    spans = {
        str(index): {"kind": "docs", "path": f"{index}.md", "heading": "Rules", "text": "x" * 11000}
        for index in range(3)
    }
    groups = content_groups(facts, spans)
    assert [group["obligation_ids"] for group in groups] == [["0"], ["1"], ["2"]]
    assert [group["facts"][0] for group in groups] == [
        {key: value for key, value in fact.items() if key not in {"subject", "predicate"}}
        for fact in facts
    ]


def test_shared_placement_requires_exact_passage_and_all_local_support():
    passage = "Shoppers and merchants have a limit of 500. [Legacy D1] [Legacy D2]"
    assertions = {"a": {"evidence_ids": ["e1"]}, "b": {"evidence_ids": ["e2"]}}
    evidence = {"e1": {"label": "D1"}, "e2": {"label": "D2"}}
    mappings = [
        {"obligation_id": key, "passage": passage, "citation_ids": [label]}
        for key, label in [("a", "D1"), ("b", "D2")]
    ]
    records, findings = placement_records("Rules", passage, mappings, assertions, evidence)
    assert not findings and len(records) == 1
    assert records[0]["obligation_ids"] == ["a", "b"]
    assert placement_records("Rules", passage, mappings[:1], assertions, evidence)[1]
    assert placement_records("Rules", "Changed text", mappings, assertions, evidence)[1]
    broken = deepcopy(mappings)
    broken[0]["citation_ids"] = ["D2"]
    assert placement_records("Rules", passage, broken, assertions, evidence)[1]


def diagram(kind="flowchart"):
    return DiagramSpec(
        id="approval",
        kind=kind,
        question="What happens after review?",
        description="Valid requests are approved; invalid requests need correction.",
        nodes=[
            {"id": name, "label": label, "evidence_ids": ["e"]}
            for name, label in [
                ("Review", "Review request"),
                ("Approved", "Approved"),
                ("Correction", "Correction"),
            ]
        ],
        edges=[
            {
                "id": name,
                "source": "Review",
                "target": target,
                "label": label,
                "evidence_ids": ["e"],
            }
            for name, target, label in [
                ("Accept", "Approved", "Valid"),
                ("Reject", "Correction", "Invalid"),
            ]
        ],
    ).model_dump()


@pytest.mark.parametrize("kind", ["flowchart", "stateDiagram-v2", "sequenceDiagram"])
def test_diagram_grammar_and_evidence_are_bounded(kind):
    spec = diagram(kind)
    spec["source"] = diagram_source(spec)
    assert not validate_diagram(spec, {"e"})
    spec["edges"][0]["evidence_ids"] = ["invented"]
    assert validate_diagram(spec, {"e"})
    spec = diagram(kind)
    spec["source"] = diagram_source(spec) + "\nReview --> GuaranteedSuccess"
    assert validate_diagram(spec, {"e"})
    spec = diagram(kind)
    spec["nodes"][0]["label"] = "<script>alert(1)</script>"
    assert validate_diagram(spec, {"e"})


def test_unapproved_diagram_and_missing_alt_cannot_be_published():
    visual = {"id": "flow", "kind": "diagram", "diagram": diagram(), "evidence_ids": []}
    markdown = render_visuals([visual], [], [{"id": "e", "label": "D1"}])
    assert not validate_visual_output(markdown, [visual], [], [{"id": "e", "label": "D1"}])
    assert validate_visual_output(markdown, [], [], [])
    contract = compile_requirements("## Flow", "t")
    asset = {
        "hash": "asset",
        "path": "a.svg",
        "disposition": "referenced",
        "references": [{"alt": "", "evidence_ids": ["e"]}],
    }
    image = {
        "id": "image",
        "kind": "image",
        "section": "Flow",
        "purpose": "Clarify review",
        "asset_hash": "asset",
        "text_alternative": "Inferred from pixels",
        "evidence_ids": ["e"],
    }
    plan = {"title": "Approvals", "sections": [{"title": "Flow", "visuals": [image]}]}
    assert any(
        "source-provided" in finding
        for finding in validate_quality_plan(
            plan, contract, [asset], {"e": {"text": "Source evidence"}}
        )
    )


def test_provider_schema_expands_references_and_preserves_array_limits():
    schema = response_schema(PagePlanDraft)
    serialized = json.dumps(schema)
    assert "$ref" not in serialized and "schema_version" not in serialized
    assert schema["properties"]["sections"]["minItems"] == 1
    assert schema["properties"]["diagrams"]["items"]["properties"]["nodes"]["maxItems"] == 16
    assert "maxItems" in json.dumps(PagePlanDraft.model_json_schema())
    assert schema["required"] == list(schema["properties"])


def test_optional_and_reviewed_inapplicable_template_sections():
    contract = compile_requirements("## Rules\n\n## Optional recovery\n", "template")
    plan = {"title": "Orders", "sections": [{"title": "Rules", "visuals": []}]}
    assert not validate_quality_plan(plan, contract, [], {})
    mandatory = compile_requirements("## Rules\n\n## Recovery\n", "template")
    assert validate_quality_plan(plan, mandatory, [], {})
    requirement = next(item for item in mandatory["requirements"] if item["text"] == "Recovery")
    plan["template_decisions"] = [
        {
            "requirement_id": requirement["id"],
            "disposition": "inapplicable",
            "reason": "No recovery documented",
            "evidence_ids": [],
        }
    ]
    assert not validate_quality_plan(plan, mandatory, [], {})


def test_visual_change_invalidates_exact_plan_approval(tmp_path):
    store = ArtifactStore(tmp_path)
    pipeline = Pipeline(store, None, "approval")
    plan = {"title": "Review", "sections": [], "source_assets": [], "template_hash": "t"}
    state = {
        "runtime_signature": pipeline.runtime_signature(),
        "plan_ref": store.put(plan),
        "graph_revision": "g",
        "snapshot_ref": "s",
        "approval_ref": store.put(
            {
                "action": "approve_plan",
                "plan_hash": digest(plan),
                "graph_revision": "g",
                "source_revision": "s",
            }
        ),
    }
    assert pipeline._approved_plan(state) == plan
    state["plan_ref"] = store.put({**plan, "source_assets": [{"hash": "changed"}]})
    with pytest.raises(ValueError, match="exact plan approval"):
        pipeline._approved_plan(state)


def test_selected_asset_symlink_is_not_frozen(tmp_path, monkeypatch):
    docs = tmp_path / "docs"
    docs.mkdir()
    image = docs / "link.svg"
    image.write_bytes(SVG)
    (docs / "guide.md").write_text("![Review panel](link.svg)", encoding="utf-8")
    template = tmp_path / "template.md"
    template.write_text("## Review", encoding="utf-8")
    path_type = type(image)
    real_is_symlink = path_type.is_symlink
    monkeypatch.setattr(
        path_type, "is_symlink", lambda path: path == image or real_is_symlink(path)
    )
    snapshot = snapshot_inputs(ArtifactStore(tmp_path / "runtime"), docs, None, template, "")
    asset = snapshot["assets"][0]
    assert asset["disposition"] == "rejected" and not asset["hash"]
    assert "symlink" in asset["findings"][0]


def test_nearby_role_antecedents_remain_in_section_evidence(tmp_path):
    store = ArtifactStore(tmp_path)
    pipeline = Pipeline(store, None, "context")
    spans = [
        {
            "id": f"e{index}",
            "kind": "docs",
            "path": "roles.md",
            "heading": "Roles",
            "file_hash": "f",
            "start_line": index,
            "end_line": index,
            "role": "legacy_document",
            "text": text,
        }
        for index, text in enumerate(
            [
                "Shoppers use the review panel.",
                "Merchants use the same review panel.",
                "Both roles can save drafts for 30 days.",
            ],
            1,
        )
    ]
    pipeline.graph.add_evidence(spans)
    assertion = normalized_assertion(
        {"statement": spans[-1]["text"], "evidence_ids": ["e3"]}, {"e3"}
    )
    pipeline.graph.add_assertions([assertion])
    section = {
        "title": "Drafts",
        "obligation_ids": [assertion["id"]],
        "supporting_obligation_ids": [],
        "unit_obligations": [[assertion["id"]]],
        "queries": [],
        "visuals": [],
    }
    pipeline._approved_plan = lambda state: {"sections": [section]}
    result = pipeline.retrieve_section_evidence(
        {"section_index": 0, "unit_index": 0, "inventory_ref": store.put({"spans": spans})}
    )
    packet = store.get(result["packet_ref"])
    assert packet["contextual_evidence_ids"] == ["e1", "e2"]
    assert {item["id"] for item in packet["evidence"]} == {"e1", "e2", "e3"}
    assert [item["id"] for item in packet["assertions"]] == [assertion["id"]]


def test_self_contained_rows_do_not_pull_unrelated_neighbor_stories(tmp_path):
    store = ArtifactStore(tmp_path)
    pipeline = Pipeline(store, None, "independent-stories")
    spans = [
        {
            "id": f"e{index}",
            "kind": "docs",
            "path": "stories.md",
            "heading": "Stories",
            "file_hash": "f",
            "start_line": index,
            "end_line": index,
            "role": "legacy_document",
            "text": f"| Story {index} | A shopper saves a quote and reviews it. " + "detail " * 550,
        }
        for index in range(1, 17)
    ]
    pipeline.graph.add_evidence(spans)
    required = [spans[index] for index in (3, 7, 11, 15)]
    assertions = [
        normalized_assertion(
            {"statement": f"Story {span['id']} retains its quote.", "evidence_ids": [span["id"]]},
            {span["id"]},
        )
        for span in required
    ]
    pipeline.graph.add_assertions(assertions)
    identifiers = [item["id"] for item in assertions]
    section = {
        "title": "Quotes",
        "obligation_ids": identifiers,
        "supporting_obligation_ids": [],
        "unit_obligations": [identifiers],
        "visuals": [],
    }
    pipeline._approved_plan = lambda state: {"sections": [section]}
    result = pipeline.retrieve_section_evidence(
        {"section_index": 0, "unit_index": 0, "inventory_ref": store.put({"spans": spans})}
    )
    packet = store.get(result["packet_ref"])
    assert packet["contextual_evidence_ids"] == []
    assert {item["id"] for item in packet["evidence"]} == {item["id"] for item in required}
    assert {item["id"] for item in packet["assertions"]} == set(identifiers)


def test_later_writing_unit_continues_prior_content_and_normalizes_citations(tmp_path):
    store = ArtifactStore(tmp_path)
    pipeline = Pipeline(store, None, "writing-continuity")
    section = {
        "title": "Capabilities",
        "purpose": "Explain scoped capabilities",
        "obligation_ids": ["first", "second"],
        "supporting_obligation_ids": [],
    }
    plan = {
        "sections": [section],
        "content_units": [],
        "source_assets": [],
        "template_decisions": [],
        "template_requirements": [
            {"section": "Capabilities", "kind": "table", "text": "Capability overview"},
            {"section": "Capabilities", "kind": "callout", "text": "Important distinction"},
            {"section": "Capabilities", "kind": "purpose", "text": "Keep role differences"},
        ],
    }
    pipeline._approved_plan = lambda state: plan
    pipeline._units = lambda section: [["first"], ["second"]]
    captured = {}

    def write(stage, payload, schema):
        captured.update(payload)
        return {
            "markdown": "Merchants retain the same search filters. Legacy D2",
            "mappings": [
                {
                    "obligation_id": "second",
                    "passage": "Merchants retain the same search filters. Legacy D2",
                    "citation_ids": ["D2"],
                }
            ],
        }

    pipeline.call = write
    prior = "### Guided search\n\nShoppers retain the search filters. [Legacy D1]"
    state = {
        "template_ref": store.put({"text": "## Capabilities"}),
        "section_index": 0,
        "unit_index": 1,
        "packet_ref": store.put(
            {"evidence": [{"id": "e2", "label": "D2"}], "assertions": [{"id": "second"}]}
        ),
        "approval_ref": store.put({}),
        "written_ref": store.put([{"section_index": 0, "unit_index": 0, "markdown": prior}]),
    }
    result = pipeline.write_section(state)
    draft = store.get(result["draft_ref"])
    assert captured["writing_context"]["existing_headings"] == ["### Guided search"]
    assert "\n\n".join(captured["writing_context"]["preceding_passages"]) == prior
    assert [item["kind"] for item in captured["template_requirements"]] == ["purpose"]
    assert captured["mandatory_obligation_ids"] == ["second"]
    assert draft["markdown"] == draft["mappings"][0]["passage"]
    assert draft["markdown"].endswith("[Legacy D2]")


def test_a_clean_model_audit_cannot_omit_diagram_element_support(tmp_path):
    store = ArtifactStore(tmp_path)
    pipeline = Pipeline(store, None, "diagram-audit")
    visual = {"id": "flow", "kind": "diagram", "diagram": diagram(), "evidence_ids": []}
    evidence = [
        {
            "id": "e",
            "label": "D1",
            "kind": "docs",
            "path": "rules.md",
            "file_hash": "snapshot",
            "start_line": 1,
            "end_line": 1,
            "text": "A reviewer approves before release.",
            "heading": "Process",
            "role": "legacy_document",
        }
    ]
    pipeline.graph.add_evidence(evidence)
    passage = "A reviewer approves before release. [Legacy D1]"
    section = {"title": "Process", "obligation_ids": [], "visuals": [visual]}
    pipeline._approved_plan = lambda state: {"sections": [section], "source_assets": []}
    pipeline._units = lambda section: [["support"]]
    pipeline.call = lambda stage, payload, schema: {
        "accepted": True,
        "findings": [],
        "covered_diagram_element_ids": ["flow:Review"],
    }
    state = {
        "section_index": 0,
        "unit_index": 0,
        "template_ref": store.put({"text": "## Process"}),
        "written_ref": store.put([]),
        "packet_ref": store.put(
            {
                "assertions": [{"id": "support", "evidence_ids": ["e"]}],
                "evidence": evidence,
                "visuals": [visual],
            }
        ),
        "draft_ref": store.put(
            {
                "markdown": passage + "\n\n" + render_visuals([visual], [], evidence),
                "mappings": [
                    {
                        "obligation_id": "support",
                        "passage": passage,
                        "citation_ids": ["D1"],
                        "support_quotes": {"D1": evidence[0]["text"]},
                    }
                ],
            }
        ),
    }
    result = pipeline.verify_section(state)
    assert result["route"] == "write_section"
    assert any("diagram element" in item for item in store.get(result["feedback_ref"]))


def test_inert_svg_xml_declaration_is_supported():
    assert (
        validate_asset(b'<?xml version="1.0" encoding="UTF-8"?>' + SVG, ".svg", 10000, 100)[
            "format"
        ]
        == "svg"
    )


def test_repetition_ignores_url_length_and_finds_summary_detail_overlap():
    paragraph = (
        "The shopper can request a review when the account is active and the order is "
        "complete, except when manual approval is required. [Legacy D1](https://example.test/long)"
    )
    report = repetition_report(
        [{"title": title, "markdown": paragraph} for title in ("Summary", "Detail")]
    )
    assert len(report["duplicate_paragraphs"]) == 1
    assert report["reader_words"] < len(paragraph.split()) * 2


class VisualModel(FixtureModel):
    def call(self, stage, payload, schema=None):
        response = super().call(stage, payload, schema)
        if stage == "draft_plan":
            asset = payload["source_assets"][0]
            reference = asset["references"][0]
            response["sections"][0]["visuals"] = [
                {
                    "id": "review_image",
                    "kind": "image",
                    "section": payload["template_headings"][0],
                    "purpose": "Locate the review panel",
                    "asset_hash": asset["hash"],
                    "evidence_ids": reference["evidence_ids"],
                    "text_alternative": reference["alt"],
                }
            ]
        if stage in {"verify_plan", "verify_section", "verify_page"}:
            response["covered_diagram_element_ids"] = sorted(
                diagram_element_ids(payload.get("visuals", []))
            )
        return response


class EditingModel(FixtureModel):
    def __init__(self, stale):
        super().__init__()
        self.stale = stale

    def call(self, stage, payload, schema=None):
        if stage == "edit_page":
            markdown = payload["markdown"].replace(
                "An active account is required.", "The account must be active."
            )
            mappings = deepcopy(payload["mappings"])
            if not self.stale:
                for mapping in mappings:
                    mapping["passage"] = mapping["passage"].replace(
                        "An active account is required.", "The account must be active."
                    )
            return {"markdown": markdown, "mappings": mappings}
        if stage == "verify_page":
            return {
                "accepted": True,
                "findings": [],
                "covered_obligation_ids": payload["mandatory_obligation_ids"],
            }
        return super().call(stage, payload, schema)


class RelativeHeadingModel(FixtureModel):
    def __init__(self, include_heading):
        super().__init__()
        self.include_heading = include_heading

    def call(self, stage, payload, schema=None):
        result = super().call(stage, payload, schema)
        if stage == "write_section" and self.include_heading:
            result["markdown"] = "# Rules\n\n## Key data\n\n" + result["markdown"]
        return result


@pytest.mark.parametrize("include_heading", [True, False])
def test_template_checks_use_exported_heading_levels(tmp_path, include_heading):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "rules.md").write_text("An active account is required.\n", encoding="utf-8")
    template = tmp_path / "template.md"
    template.write_text("## Rules\n\n### Key data\n", encoding="utf-8")
    store = ArtifactStore(tmp_path / "runtime")
    model = RelativeHeadingModel(include_heading)
    config = {"configurable": {"thread_id": "headings"}, "recursion_limit": 1000}
    with closing(
        sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)
    ) as connection:
        graph = Pipeline(store, model, "headings").build(SqliteSaver(connection))
        graph.invoke({"run_id": "headings", "docs": str(docs), "template": str(template)}, config)
        state = graph.get_state(config).values
        graph.invoke(
            Command(
                resume={
                    "action": "approve_plan",
                    "plan_hash": state["plan_hash"],
                    "reviewer": "test",
                    "rationale": "Check template headings after export normalization",
                }
            ),
            config,
        )
        state = graph.get_state(config).values
    if not include_heading:
        assert state["status"] == "awaiting_issue_review"
        assert "Missing template heading" in store.get(state["issue_ref"])["findings"][0]
        return
    assert state["status"] == "ready_for_review"
    assert model.calls.count("edit_page") == 1
    candidate = store.root / "runs" / "headings" / "candidates" / state["candidate_ref"]
    markdown = (candidate / "documentation" / "index.md").read_text("utf-8")
    assert markdown.count("\n## Rules\n") == 1
    assert markdown.count("\n### Key data\n") == 1
    audit = json.loads((candidate / "audit.json").read_text("utf-8"))
    for placement in audit["placements"]:
        assert markdown[placement["start"] : placement["end"]] == placement["passage"]


class GroupedCitationModel(FixtureModel):
    def __init__(self, edit_group):
        super().__init__()
        self.edit_group = edit_group

    def call(self, stage, payload, schema=None):
        result = super().call(stage, payload, schema)
        if stage == "write_section":
            labels = [item["citation_ids"][0] for item in result["mappings"]]
            prose = " ".join(item["statement"] for item in payload["assertions"])
            passage = prose + " [Legacy " + ", ".join(labels) + "]"
            for mapping in result["mappings"]:
                mapping["passage"] = passage
            result["markdown"] = passage
        elif stage == "edit_page" and self.edit_group:
            markdown = payload["markdown"].replace("[Legacy D1, D2]", "[Legacy D1] [Legacy D2]")
            result = {
                "markdown": markdown,
                "mappings": [{**item, "passage": markdown} for item in payload["mappings"]],
            }
        elif stage == "verify_page":
            result["covered_obligation_ids"] = payload["mandatory_obligation_ids"]
        return result


@pytest.mark.parametrize("edit_group", [False, True])
def test_grouped_citations_survive_writing_editing_and_export(tmp_path, edit_group):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "rules.md").write_text(
        "An active account is required.\n", encoding="utf-8"
    )
    (docs / "retention.md").write_text("Drafts remain for 30 days.\n", encoding="utf-8")
    template = tmp_path / "template.md"
    template.write_text("## Rules\n", encoding="utf-8")
    store = ArtifactStore(tmp_path / "runtime")
    model = GroupedCitationModel(edit_group)
    config = {"configurable": {"thread_id": "grouped"}, "recursion_limit": 1000}
    with closing(
        sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)
    ) as connection:
        graph = Pipeline(store, model, "grouped").build(SqliteSaver(connection))
        graph.invoke({"run_id": "grouped", "docs": str(docs), "template": str(template)}, config)
        state = graph.get_state(config).values
        graph.invoke(
            Command(
                resume={
                    "action": "approve_plan",
                    "plan_hash": state["plan_hash"],
                    "reviewer": "test",
                    "rationale": "Check shared citations",
                }
            ),
            config,
        )
        state = graph.get_state(config).values
    assert state["status"] == "ready_for_review"
    assert model.calls.count("write_section") == 1
    candidate = store.root / "runs" / "grouped" / "candidates" / state["candidate_ref"]
    audit = json.loads((candidate / "audit.json").read_text("utf-8"))
    assert len(audit["mappings"]) == 2
    assert len(audit["placements"]) == 1
    assert set(audit["placements"][0]["citation_ids"]) == {"D1", "D2"}


@pytest.mark.parametrize("unmapped", [False, True])
def test_editorial_audit_checks_changes_with_bounded_source_context(tmp_path, unmapped):
    pipeline = Pipeline(ArtifactStore(tmp_path), None, "editorial-scope")
    evidence = [
        {
            "id": f"e{index}",
            "label": f"D{index}",
            "kind": "docs",
            "path": "rules.md",
            "start_line": index,
            "text": "Source text " * 450,
        }
        for index in range(100)
    ]
    mappings = [
        {
            "obligation_id": f"a{index}",
            "citation_ids": [f"D{index}"],
            "passage": f"Rule {index} requires review. [Legacy D{index}]",
        }
        for index in range(100)
    ]
    original = "\n\n".join(item["passage"] for item in mappings)
    section = {"markdown": original, "mappings": deepcopy(mappings), "visuals": []}
    pipeline.graph.assertion = lambda key: {"id": key, "evidence_ids": [key.replace("a", "e")]}
    if unmapped:
        markdown = original + "\n\nA new guarantee is claimed. [Legacy D90]"
    else:
        mappings[50]["passage"] = "Review is required for rule 50. [Legacy D50]"
        markdown = "\n\n".join(item["passage"] for item in mappings)
    payload = pipeline._editorial_evidence(section, markdown, mappings, [], evidence)
    assert len(payload["original_evidence"]) < 10
    assert sum(len(item["text"]) for item in payload["original_evidence"]) < 45000
    if unmapped:
        assert "A new guarantee" in payload["edited_markdown"]
        assert "D90" in {item["label"] for item in payload["original_evidence"]}
        assert payload["mandatory_obligation_ids"] == []
    else:
        assert payload["mandatory_obligation_ids"] == ["a50"]
        assert payload["mappings"] == [mappings[50]]
        assert "Rule 0 requires" not in payload["original_markdown"]


@pytest.mark.parametrize("stale", [True, False])
def test_changed_editor_passages_require_final_mappings(tmp_path, stale):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "rule.md").write_text("An active account is required.\n", encoding="utf-8")
    template = tmp_path / "template.md"
    template.write_text("## Rules\n", encoding="utf-8")
    store = ArtifactStore(tmp_path / "runtime")
    with closing(
        sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)
    ) as connection:
        graph = Pipeline(store, EditingModel(stale), "edited").build(SqliteSaver(connection))
        config = {"configurable": {"thread_id": "edited"}}
        graph.invoke({"docs": str(docs), "template": str(template), "run_id": "edited"}, config)
        state = graph.get_state(config).values
        graph.invoke(
            Command(
                resume={
                    "action": "approve_plan",
                    "plan_hash": state["plan_hash"],
                    "reviewer": "Test",
                    "rationale": "Fixture",
                }
            ),
            config,
        )
        state = graph.get_state(config).values
        assert state["status"] == ("awaiting_issue_review" if stale else "ready_for_review")
        if stale:
            assert any("absent" in finding for finding in store.get(state["issue_ref"])["findings"])
        else:
            edited = store.get(state["edited_ref"])[0]
            assert edited["mappings"][0]["passage"].startswith("The account must be active.")


@pytest.mark.parametrize(
    "failure_stage", ["review_plan", "assemble_pages", "export_candidate", "review_release"]
)
def test_visual_pipeline_restarts_at_checkpoint_and_exports_portably(tmp_path, failure_stage):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "panel.svg").write_bytes(SVG)
    (docs / "guide.md").write_text(
        "# Review\n\nValid requests are approved.\n\n![Review panel](panel.svg)\n", encoding="utf-8"
    )
    template = tmp_path / "template.md"
    template.write_text("## Review\n", encoding="utf-8")
    store = ArtifactStore(tmp_path / "runtime")
    model = VisualModel()
    config = {"configurable": {"thread_id": "visual"}}

    def open_graph(fail=False):
        connection = sqlite3.connect(store.root / "checkpoints.sqlite", check_same_thread=False)
        pipeline = Pipeline(store, model, "visual")
        if fail:

            def crash(state):
                raise RuntimeError("Injected restart")

            setattr(pipeline, failure_stage, crash)
        return connection, pipeline.build(SqliteSaver(connection))

    inputs = {"docs": str(docs), "template": str(template), "run_id": "visual", "brief": ""}
    connection, graph = open_graph(True)
    with closing(connection):
        if failure_stage == "review_plan":
            with pytest.raises(RuntimeError, match="Injected"):
                graph.invoke(inputs, config)
        else:
            graph.invoke(inputs, config)
            state = graph.get_state(config).values
            with pytest.raises(RuntimeError, match="Injected"):
                graph.invoke(
                    Command(
                        resume={
                            "action": "approve_plan",
                            "plan_hash": state["plan_hash"],
                            "reviewer": "Test",
                            "rationale": "Fixture",
                        }
                    ),
                    config,
                )
    calls = list(model.calls)
    connection, graph = open_graph()
    with closing(connection):
        graph.invoke(None, config)
        state = graph.get_state(config).values
        if state["status"] == "awaiting_plan_review":
            assert model.calls == calls
            graph.invoke(
                Command(
                    resume={
                        "action": "approve_plan",
                        "plan_hash": state["plan_hash"],
                        "reviewer": "Test",
                        "rationale": "Fixture",
                    }
                ),
                config,
            )
        state = graph.get_state(config).values
        assert state["status"] == "ready_for_review"
        if failure_stage == "review_release":
            assert model.calls == calls
        candidate = store.root / "runs" / "visual" / "candidates" / state["candidate_ref"]
        copied = tmp_path / "moved" / "bundle"
        shutil.copytree(candidate, copied)
        manifest = json.loads((copied / "candidate-manifest.json").read_text("utf-8"))
        verify_bundle(copied, manifest)
        assert len(list((copied / "documentation" / "assets").iterdir())) == 1
        audit = json.loads((copied / "audit.json").read_text("utf-8"))
        markdown = (copied / "documentation" / "index.md").read_text("utf-8")
        assert all(
            markdown[item["start"] : item["end"]] == item["passage"] for item in audit["placements"]
        )
        image = next((copied / "documentation" / "assets").iterdir())
        image.write_bytes(b"tampered")
        with pytest.raises(ValueError, match="changed"):
            verify_bundle(copied, manifest)
