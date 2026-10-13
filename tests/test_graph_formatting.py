import json
from copy import deepcopy
from pathlib import Path

import pytest

from docgen_graph.ingestion import document_spans
from docgen_graph.knowledge import KnowledgeGraph, normalized_assertion
from docgen_graph.semantic_graph import (
    publish_semantic_batch,
    semantic_bundle,
    semantic_payload,
    semantic_quality_report,
    semantic_records,
    validate_semantic_proposal,
)
from docgen_graph.source_documents import document_context, extraction_packet
from docgen_graph.storage import digest

FIXTURES = Path(__file__).parent / "fixtures" / "graph_formatting"
VARIANTS = ["prose", "lists", "tables", "headings"]
SCOPE = "Customer portal"
RULES = [
    {
        "key": "registration-eligibility",
        "topic_key": "registration",
        "topic": "User registration",
        "statement": "Registration requires all the following conditions.",
        "operator": "all",
        "conditions": [
            "The user provides a valid email address.",
            "The user provides a password of at least 12 characters.",
            "The user accepts the terms of service.",
        ],
        "exceptions": [
            "Invited company users do not need to provide a password; "
            "the other registration conditions still apply."
        ],
        "qualifier": "Missing any required condition prevents registration.",
    },
    {
        "key": "registration-activation",
        "topic_key": "registration",
        "topic": "User registration",
        "statement": "Registration activation requires either of the following confirmations.",
        "operator": "any",
        "conditions": [
            "The user follows the email confirmation link.",
            "The user enters a confirmation code supplied by support.",
        ],
        "exceptions": [],
        "qualifier": "Either confirmation is enough to satisfy this confirmation requirement; "
        "it does not guarantee successful activation.",
    },
    {
        "key": "password-reset",
        "topic_key": "reset",
        "topic": "Password reset",
        "statement": "Password reset requires all the following conditions.",
        "operator": "all",
        "conditions": [
            "The account has a verified email address.",
            "The account is active.",
        ],
        "exceptions": [],
        "qualifier": "An inactive account cannot reset its password.",
    },
]


def parsed_variant(variant):
    source = (FIXTURES / f"{variant}.md").read_text(encoding="utf-8")
    file = {"kind": "docs", "path": f"{variant}.md", "hash": digest(source.encode())}
    return source, document_spans(file, source)


def exact_quote(spans, sentence):
    candidates = [span for span in spans if sentence in span["text"]]
    assert len(candidates) == 1, sentence
    span = candidates[0]
    start = span["text"].index(sentence)
    return {
        "evidence_id": span["id"],
        "start": start,
        "end": start + len(sentence),
        "text": sentence,
    }


def controlled_semantic_response(spans):
    topics = {}
    rules = []
    facts = []
    for expected in RULES:
        phrases = [
            expected["statement"],
            *expected["conditions"],
            *expected["exceptions"],
            expected["qualifier"],
        ]
        quotes = [exact_quote(spans, phrase) for phrase in phrases]
        fact = normalized_assertion(
            {
                "statement": " ".join(phrases),
                "subject": expected["topic"],
                "predicate": "requires",
                "scope": SCOPE,
                "modality": "necessary",
                "conditions": expected["conditions"],
                "exceptions": expected["exceptions"],
                "evidence_ids": sorted({quote["evidence_id"] for quote in quotes}),
            },
            {span["id"] for span in spans},
        )
        facts.append(fact)
        topics.setdefault(
            expected["topic_key"],
            {
                "key": expected["topic_key"],
                "name": expected["topic"],
                "scope": SCOPE,
                "quotes": [],
            },
        )["quotes"].append(quotes[0])
        rules.append(
            {
                "key": expected["key"],
                "topic_key": expected["topic_key"],
                "statement": fact["statement"],
                "scope": SCOPE,
                "modality": "necessary",
                "fact_ids": [fact["id"]],
                "quotes": quotes,
                "topic_quotes": [quotes[0]],
                "condition_groups": [
                    {
                        "operator": expected["operator"],
                        "quotes": [quotes[0]],
                        "conditions": [
                            {"statement": condition, "quotes": [exact_quote(spans, condition)]}
                            for condition in expected["conditions"]
                        ],
                    }
                ],
                "exceptions": [
                    {"statement": exception, "quotes": [exact_quote(spans, exception)]}
                    for exception in expected["exceptions"]
                ],
            }
        )
    return facts, {"topics": list(topics.values()), "rules": rules, "findings": []}


def controlled_meaning_signature(response):
    topics = {topic["key"]: topic for topic in response["topics"]}
    return sorted(
        (
            topics[rule["topic_key"]]["name"],
            topics[rule["topic_key"]]["scope"],
            rule["statement"],
            rule["scope"],
            rule["modality"],
            tuple(
                sorted(
                    (
                        group["operator"],
                        tuple(sorted(condition["statement"] for condition in group["conditions"])),
                    )
                    for group in rule["condition_groups"]
                )
            ),
            tuple(sorted(exception["statement"] for exception in rule["exceptions"])),
        )
        for rule in response["rules"]
    )


def publish_variant(graph, variant):
    source, spans = parsed_variant(variant)
    facts, response = controlled_semantic_response(spans)
    canonical, issues = validate_semantic_proposal(response, semantic_payload(facts, spans))
    assert issues == []
    graph.add_evidence(spans)
    graph.add_assertions(facts)
    publish_semantic_batch(
        graph,
        canonical,
        variant,
        {"provider": "test_oracle", "model": "controlled_semantic_response"},
    )
    return source, spans, facts, response


def stored_meaning_signature(graph):
    nodes, edges = semantic_records(graph)
    node_signatures = sorted(
        json.dumps(
            {key: value for key, value in node.items() if key not in {"quotes", "fact_ids"}},
            sort_keys=True,
        )
        for node in nodes
    )
    edge_signatures = []
    for edge in edges:
        if edge["type"] == "SUPPORTED_BY":
            continue
        target = edge["target_id"]
        if edge["type"] == "EXPRESSES":
            fact = graph.assertion(target)
            target = json.dumps(
                {
                    key: fact[key]
                    for key in ("statement", "scope", "modality", "conditions", "exceptions")
                },
                sort_keys=True,
            )
        edge_signatures.append((edge["source_id"], edge["type"], target))
    return node_signatures, sorted(edge_signatures)


def test_formatting_variants_have_identical_graph_meaning_with_controlled_extraction(tmp_path):
    signatures = []
    hashes = []
    for variant in VARIANTS:
        graph = KnowledgeGraph(tmp_path / f"{variant}.sqlite")
        _, spans, _, _ = publish_variant(graph, variant)
        signatures.append(stored_meaning_signature(graph))
        hashes.append(spans[0]["file_hash"])
        report = semantic_quality_report(graph)
        assert report["accepted"], report["findings"]
        assert report["counts"] == {
            "Topic": 2,
            "Rule": 3,
            "ConditionGroup": 3,
            "Condition": 7,
            "Exception": 1,
        }
        assert report["allocated_fact_count"] == report["fact_count"] == 3
    assert len(set(hashes)) == len(VARIANTS)
    assert all(signature == signatures[0] for signature in signatures[1:])


def test_repeated_topic_keeps_all_stories_and_original_variant_sources(tmp_path):
    graph = KnowledgeGraph(tmp_path / "combined.sqlite")
    for variant in VARIANTS:
        publish_variant(graph, variant)
    nodes, _ = semantic_records(graph)
    topics = [node for node in nodes if node["type"] == "Topic"]
    assert len(topics) == 2
    registration = next(node for node in topics if node["name"] == "User registration")
    bundle = semantic_bundle(graph, [registration["id"]])
    assert len([node for node in bundle["nodes"] if node["type"] == "Rule"]) == 2
    assert len(bundle["assertions"]) == 2 * len(VARIANTS)
    assert all("Password reset" not in fact["statement"] for fact in bundle["assertions"])
    assert {quote["path"] for quote in bundle["quotes"]} == {
        f"{variant}.md" for variant in VARIANTS
    }
    assert semantic_quality_report(graph)["accepted"]


@pytest.mark.parametrize("corruption", ["quote", "offset", "scope", "modality", "exception"])
def test_structural_validation_rejects_corrupted_grounding(corruption):
    _, spans = parsed_variant("tables")
    facts, response = controlled_semantic_response(spans)
    corrupted = deepcopy(response)
    rule = corrupted["rules"][0]
    if corruption == "quote":
        rule["quotes"][0]["text"] = "A fabricated claim."
    elif corruption == "offset":
        rule["quotes"][0]["start"] += 1
    elif corruption == "scope":
        rule["scope"] = "Staff portal"
    elif corruption == "modality":
        rule["modality"] = "sufficient"
    else:
        rule["exceptions"] = []
    canonical, issues = validate_semantic_proposal(corrupted, semantic_payload(facts, spans))
    assert issues
    assert canonical == {}


def test_exact_quotes_alone_do_not_certify_condition_logic():
    _, spans = parsed_variant("prose")
    facts, response = controlled_semantic_response(spans)
    corrupted = deepcopy(response)
    corrupted["rules"][0]["condition_groups"][0]["operator"] = "any"
    _, issues = validate_semantic_proposal(corrupted, semantic_payload(facts, spans))
    assert issues == []
    assert controlled_meaning_signature(response) != controlled_meaning_signature(corrupted)


@pytest.mark.parametrize("variant", VARIANTS)
def test_controlled_extraction_retains_original_source_positions(variant):
    source, spans = parsed_variant(variant)
    _, response = controlled_semantic_response(spans)
    by_id = {span["id"]: span for span in spans}
    for rule in response["rules"]:
        for quote in rule["quotes"]:
            span = by_id[quote["evidence_id"]]
            assert span["text"][quote["start"] : quote["end"]] == quote["text"]
            source_start = span["source_start_char"] + quote["start"]
            source_end = span["source_start_char"] + quote["end"]
            assert source[source_start:source_end] == quote["text"]


@pytest.mark.parametrize("variant", VARIANTS)
def test_every_owned_rule_fragment_retains_complete_story_context(variant):
    _, spans = parsed_variant(variant)
    inventory = {"spans": spans, **document_context(spans, maximum_items=2)}
    owners = [identifier for batch in inventory["document_batches"] for identifier in batch]
    assert sorted(owners) == sorted(span["id"] for span in spans)
    assert len(owners) == len(set(owners))
    for index in range(len(inventory["document_batches"])):
        packet = extraction_packet(inventory, index)
        owned_text = "\n".join(span["text"] for span in packet["blocks"])
        available_text = "\n".join(
            span["text"] for span in packet["blocks"] + packet["context_blocks"]
        )
        owned_ids = {span["id"] for span in packet["blocks"]}
        assert not owned_ids.intersection(span["id"] for span in packet["context_blocks"])
        for expected in RULES:
            phrases = [
                expected["statement"],
                *expected["conditions"],
                *expected["exceptions"],
                expected["qualifier"],
            ]
            if any(phrase in owned_text for phrase in phrases):
                assert all(phrase in available_text for phrase in phrases)


@pytest.mark.parametrize("field,value", [("scope", "Staff portal"), ("modality", "sufficient")])
def test_meaning_oracle_detects_changed_scope_and_modality(field, value):
    _, spans = parsed_variant("prose")
    _, response = controlled_semantic_response(spans)
    corrupted = deepcopy(response)
    corrupted["rules"][0][field] = value
    assert controlled_meaning_signature(response) != controlled_meaning_signature(corrupted)


def test_meaning_oracle_detects_alternative_instead_of_conjunction_and_lost_exception():
    _, spans = parsed_variant("prose")
    _, response = controlled_semantic_response(spans)
    alternatives = deepcopy(response)
    alternatives["rules"][0]["condition_groups"][0]["operator"] = "any"
    missing_exception = deepcopy(response)
    missing_exception["rules"][0]["exceptions"] = []
    assert controlled_meaning_signature(response) != controlled_meaning_signature(alternatives)
    assert controlled_meaning_signature(response) != controlled_meaning_signature(missing_exception)
