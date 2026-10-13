from copy import deepcopy

import pytest

from docgen_graph.knowledge import KnowledgeGraph, normalized_assertion
from docgen_graph.quality import content_groups
from docgen_graph.semantic_graph import (
    publish_semantic_batch,
    salvage_semantic_proposal,
    semantic_bundle,
    semantic_payload,
    semantic_quality_report,
    validate_semantic_proposal,
)


def source(identifier, text, **metadata):
    return {
        "id": identifier,
        "kind": "docs",
        "path": f"{identifier}.md",
        "file_hash": identifier,
        "start_line": 1,
        "end_line": 1,
        "heading": "",
        "text": text,
        "role": "source",
        **metadata,
    }


def quote(span):
    return {"evidence_id": span["id"], "start": 0, "end": len(span["text"]), "text": span["text"]}


def test_uncertain_cross_document_reference_is_preserved_without_identity_merge(tmp_path):
    first = source("policy", "Permit K-8 expires in 30 days. See the renewal memo.")
    second = source("memo", "Permit K-8 expires in 90 days. Version applicability is unknown.")
    draft = {
        "concepts": [
            {
                "key": "renewal",
                "name": "Permit renewal",
                "kind": "Question",
                "description": "The two expiry periods may concern different versions.",
                "quotes": [quote(first), quote(second)],
                "status": "uncertain",
            }
        ],
        "relationships": [
            {
                "source_key": "policy",
                "target_key": "memo",
                "description": "The memo may expand the policy, but expiry differs.",
                "label": "Possibly expands",
                "status": "uncertain",
                "quotes": [quote(first), quote(second)],
            }
        ],
        "findings": ["The applicable version is not established."],
    }
    payload = semantic_payload([], [first, second])
    canonical, issues = validate_semantic_proposal(draft, payload)
    assert not issues
    graph = KnowledgeGraph(tmp_path / "graph.sqlite")
    graph.add_evidence([first, second])
    publish_semantic_batch(graph, canonical, "references")
    report = semantic_quality_report(graph)
    assert report["accepted"]
    assert report["uncertainties"] == draft["findings"]
    bundle = semantic_bundle(graph, ["policy"])
    related = [edge for edge in bundle["edges"] if edge["type"] == "RELATED"]
    assert related[0]["description"] == draft["relationships"][0]["description"]
    assert related[0]["status"] == "uncertain"
    assert {item["id"] for item in graph.source_context()["evidence"]} == {"policy", "memo"}


@pytest.mark.parametrize(
    "first,second",
    [
        ("If pressure rises, open the valve.", "If temperature falls, start the heater."),
        ("Missing consent blocks submission.", "An expired card requires renewal."),
        ("Late payment triggers a reminder.", "A disputed invoice pauses collection."),
    ],
)
def test_independent_outcomes_need_no_conjunctive_group(first, second):
    span = source("procedure", f"{first} {second}")
    draft = {
        "concepts": [
            {
                "key": "procedure",
                "name": "Operational responses",
                "description": f"{first} Separately, {second}",
                "quotes": [quote(span)],
            }
        ],
        "relationships": [],
    }
    canonical, issues = validate_semantic_proposal(draft, semantic_payload([], [span]))
    assert not issues
    assert len(canonical["nodes"]) == 1
    assert canonical["nodes"][0]["description"] == draft["concepts"][0]["description"]
    assert not any(node["type"] == "ConditionGroup" for node in canonical["nodes"])


def test_flexible_map_can_leave_facts_in_source_without_semantic_allocation(tmp_path):
    span = source("manual", "Store sealed containers below 8 degrees.")
    fact = normalized_assertion(
        {"statement": span["text"], "evidence_ids": [span["id"]]}, {span["id"]}
    )
    graph = KnowledgeGraph(tmp_path / "graph.sqlite")
    graph.add_evidence([span])
    graph.add_assertions([fact])
    canonical, issues = validate_semantic_proposal(
        {"concepts": [], "relationships": [], "findings": ["Topic grouping deferred."]},
        semantic_payload([fact], [span]),
    )
    assert not issues
    publish_semantic_batch(graph, canonical, "partial-map")
    report = semantic_quality_report(graph)
    assert report["accepted"]
    assert report["unallocated_fact_ids"] == [fact["id"]]
    assert graph.retrieve([], [fact["id"]])["assertions"][0]["statement"] == span["text"]


def test_uncertainty_does_not_permit_fabricated_quotes_or_endpoints():
    span = source("notice", "The applicable revision is unknown.")
    draft = {
        "relationships": [
            {
                "source_key": "notice",
                "target_key": "missing",
                "description": "This might amend another notice.",
                "status": "uncertain",
                "quotes": [quote(span)],
            }
        ]
    }
    canonical, issues = validate_semantic_proposal(draft, semantic_payload([], [span]))
    assert not canonical
    assert any("unknown endpoint" in issue for issue in issues)
    draft["relationships"][0]["target_key"] = "notice"
    draft["relationships"][0]["quotes"][0]["text"] = "Invented"
    assert any(
        "exact source" in issue
        for issue in validate_semantic_proposal(draft, semantic_payload([], [span]))[1]
    )


def test_image_interpretation_keeps_generated_provenance_and_can_have_narrative_relation(tmp_path):
    original = source("instructions", "Complete the request form.")
    image = source(
        "image-analysis",
        "Generated description: the screenshot shows an email field.",
        generated=True,
        image_asset_id="asset-one",
        model="fixture",
    )
    draft = {
        "concepts": [
            {
                "key": "screen",
                "name": "Request screen",
                "kind": "Image observation",
                "description": "A visible email field; mandatory status is unknown.",
                "status": "inferred",
                "quotes": [quote(image)],
            }
        ],
        "relationships": [
            {
                "source_key": "screen",
                "target_key": "instructions",
                "label": "Illustrates",
                "description": "The image may illustrate the request form.",
                "status": "uncertain",
                "quotes": [quote(image), quote(original)],
            }
        ],
    }
    canonical, issues = validate_semantic_proposal(draft, semantic_payload([], [image, original]))
    assert not issues
    graph = KnowledgeGraph(tmp_path / "graph.sqlite")
    graph.add_evidence([original, image])
    publish_semantic_batch(graph, canonical, "image-map")
    assert graph.evidence("image-analysis")["generated"] is True
    assert canonical["nodes"][0]["concept_kind"] == "Image observation"


def test_small_context_reads_all_sources_even_without_facts_or_graph(tmp_path):
    graph = KnowledgeGraph(tmp_path / "graph.sqlite")
    graph.add_evidence(
        [
            source("one", "An obscure synonym refers to the process."),
            source("two", "The exception is described elsewhere."),
        ]
    )
    result = graph.retrieve(["not-matching-any-text"], [])
    assert len(result["evidence"]) == 2
    assert result["policy"] == "whole-source-context"


def test_large_context_is_bounded_and_exact_without_hiding_omissions(tmp_path):
    graph = KnowledgeGraph(tmp_path / "graph.sqlite")
    span = source("large", "a" * 300 + "needle" + "b" * 300)
    graph.add_evidence([span, source("other", "unrelated" * 100)])
    result = graph.source_context(["needle"], max_characters=100)
    assert result["context_characters"] <= 100
    excerpt = result["evidence"][0]
    assert "needle" in excerpt["text"]
    assert (
        excerpt["text"]
        == span["text"][excerpt["context_excerpt_start"] : excerpt["context_excerpt_end"]]
    )
    assert result["omitted_evidence_ids"] == ["other"]
    assert result["excerpted_evidence_ids"] == ["large"]


def test_planning_group_does_not_derive_business_subject_from_heading_or_table_locator():
    span = source(
        "rule", "Renewal requires approval.", heading="Invented heading", table_id="table:11"
    )
    fact = normalized_assertion(
        {"statement": span["text"], "evidence_ids": [span["id"]]}, {span["id"]}
    )
    before = content_groups([fact], {span["id"]: span})
    variant = deepcopy(span)
    variant.update(heading="Unrelated layout", table_id="table:999")
    after = content_groups([fact], {span["id"]: variant})
    assert before == after
    assert "heading" not in before[0]["topic"]


def test_salvage_withholds_bad_relationship_without_discarding_grounded_map(tmp_path):
    first = source("policy", "Containers must remain sealed.")
    second = source("diagram", "Generated observation: a closed container is visible.")
    draft = {
        "concepts": [
            {
                "key": "storage",
                "name": "Storage",
                "description": first["text"],
                "quotes": [quote(first)],
            },
            {
                "key": "image",
                "name": "Diagram",
                "description": second["text"],
                "status": "inferred",
                "quotes": [quote(second)],
            },
        ],
        "relationships": [
            {
                "source_key": "storage",
                "target_key": "policy",
                "description": "Explained by the policy.",
                "quotes": [quote(first)],
            },
            {
                "source_key": "image",
                "target_key": "storage",
                "description": "May illustrate closure.",
                "status": "uncertain",
                "quotes": [quote(first), {**quote(second), "text": "Invented text"}],
            },
        ],
    }
    payload = semantic_payload([], [first, second])
    assert validate_semantic_proposal(draft, payload)[1]
    canonical, limitations = salvage_semantic_proposal(draft, payload)
    assert len(canonical["nodes"]) == 2
    assert len([edge for edge in canonical["edges"] if edge["type"] == "RELATED"]) == 1
    assert len(limitations) == 1
    assert canonical["withheld_records"][0]["kind"] == "relationship"
    graph = KnowledgeGraph(tmp_path / "graph.sqlite")
    graph.add_evidence([first, second])
    publish_semantic_batch(graph, canonical, "salvaged")
    assert semantic_quality_report(graph)["accepted"]
    assert semantic_quality_report(graph)["uncertainties"] == limitations
    assert draft["relationships"][1]["quotes"][1]["text"] == "Invented text"


def test_salvage_withholds_invalid_concept_and_dependent_relationship():
    span = source("policy", "Approval is necessary.")
    draft = {
        "concepts": [
            {
                "key": "valid",
                "name": "Approval",
                "description": span["text"],
                "quotes": [quote(span)],
            },
            {
                "key": "invalid",
                "name": "Certificate",
                "description": "An invented requirement.",
                "quotes": [{**quote(span), "text": "Certificate is necessary."}],
            },
        ],
        "relationships": [
            {
                "source_key": "valid",
                "target_key": "invalid",
                "description": "Proposed connection",
                "quotes": [quote(span)],
            }
        ],
    }
    canonical, limitations = salvage_semantic_proposal(draft, semantic_payload([], [span]))
    assert len(canonical["nodes"]) == 1
    assert len(limitations) == 2
    assert not any(edge["type"] == "RELATED" for edge in canonical["edges"])
