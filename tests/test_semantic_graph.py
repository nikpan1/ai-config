from copy import deepcopy

import pytest

from docgen_graph.knowledge import KnowledgeGraph, normalized_assertion
from docgen_graph.semantic_graph import (
    anchor_semantic_quotes,
    publish_semantic_batch,
    semantic_bundle,
    semantic_payload,
    semantic_quality_report,
    semantic_records,
    source_citation,
    topic_register,
    validate_semantic_proposal,
)
from docgen_graph.storage import digest


def registration_batch(identifier="one", scope="Customer portal"):
    text = (
        "User registration requires both a valid email and accepted terms. "
        "Invited users are exempt from accepting terms."
    )
    span = {
        "id": identifier,
        "kind": "docs",
        "path": f"{identifier}.md",
        "file_hash": digest(text),
        "start_line": 3,
        "end_line": 3,
        "heading": "Registration",
        "text": text,
        "role": "source",
    }

    def quote(phrase):
        start = text.index(phrase)
        return {
            "evidence_id": identifier,
            "start": start,
            "end": start + len(phrase),
            "text": phrase,
        }

    fact = normalized_assertion(
        {
            "statement": "Registration requires a valid email and accepted terms.",
            "subject": "User registration",
            "scope": scope,
            "modality": "necessary",
            "conditions": ["Valid email", "Accepted terms"],
            "exceptions": ["Invited users need not accept terms"],
            "evidence_ids": [identifier],
        },
        {identifier},
    )
    rule_quote = quote(text)
    draft = {
        "topics": [
            {
                "key": "registration",
                "name": "User registration",
                "scope": scope,
                "quotes": [quote("User registration")],
            }
        ],
        "rules": [
            {
                "key": "eligibility",
                "topic_key": "registration",
                "statement": fact["statement"],
                "scope": scope,
                "modality": "necessary",
                "fact_ids": [fact["id"]],
                "quotes": [rule_quote],
                "topic_quotes": [rule_quote],
                "condition_groups": [
                    {
                        "operator": "all",
                        "quotes": [rule_quote],
                        "conditions": [
                            {"statement": "Valid email", "quotes": [quote("valid email")]},
                            {"statement": "Accepted terms", "quotes": [quote("accepted terms")]},
                        ],
                    }
                ],
                "exceptions": [
                    {
                        "statement": "Invited users need not accept terms",
                        "quotes": [quote("Invited users are exempt from accepting terms.")],
                    }
                ],
            }
        ],
    }
    return semantic_payload([fact], [span]), draft


def add_batch(graph, payload, draft, batch_id):
    canonical, issues = validate_semantic_proposal(draft, payload)
    assert not issues
    graph.add_evidence(payload["sources"])
    graph.add_assertions(payload["facts"])
    publish_semantic_batch(graph, canonical, batch_id, {"provider": "offline", "model": "fixture"})
    return canonical


def test_semantic_publication_is_idempotent_and_retains_exact_quotes(tmp_path):
    graph = KnowledgeGraph(tmp_path / "graph.sqlite")
    payload, draft = registration_batch()
    canonical = add_batch(graph, payload, draft, "batch-one")
    publish_semantic_batch(graph, canonical, "batch-one")
    report = semantic_quality_report(graph)
    assert report["accepted"], report["findings"]
    assert report["counts"] == {
        "Condition": 2,
        "ConditionGroup": 1,
        "Exception": 1,
        "Rule": 1,
        "Topic": 1,
    }
    assert report["batch_count"] == 1
    topic = topic_register(graph)[0]
    bundle = semantic_bundle(graph, [topic["id"]])
    assert bundle["assertions"][0]["id"] == payload["facts"][0]["id"]
    assert len(bundle["nodes"]) == 6
    for quote in bundle["quotes"]:
        assert quote["source"]["text"][quote["start"] : quote["end"]] == quote["text"]
        assert quote["path"] == "one.md"
        assert quote["file_hash"] == payload["sources"][0]["file_hash"]
    retrieved = graph.retrieve([], [payload["facts"][0]["id"]], optional_limit=0)
    assert retrieved["semantic_graph"]["quotes"]
    assert any(node["type"] == "Exception" for node in retrieved["semantic_graph"]["nodes"])


def test_topic_and_rule_reuse_union_all_source_quotes(tmp_path):
    graph = KnowledgeGraph(tmp_path / "graph.sqlite")
    first, first_draft = registration_batch("first")
    add_batch(graph, first, first_draft, "first")
    second, second_draft = registration_batch("second")
    second["topic_register"] = topic_register(graph)
    add_batch(graph, second, second_draft, "second")
    topics = topic_register(graph)
    assert len(topics) == 1
    assert {quote["evidence_id"] for quote in topics[0]["quotes"]} == {"first", "second"}
    assert len(topics[0]["rules"]) == 1
    assert set(topics[0]["rules"][0]["fact_ids"]) == {
        first["facts"][0]["id"],
        second["facts"][0]["id"],
    }
    assert semantic_quality_report(graph)["accepted"]


def test_same_topic_name_in_distinct_scopes_remains_separate(tmp_path):
    graph = KnowledgeGraph(tmp_path / "graph.sqlite")
    first, first_draft = registration_batch("first", "Customer portal")
    second, second_draft = registration_batch("second", "Admin portal")
    add_batch(graph, first, first_draft, "first")
    second["topic_register"] = topic_register(graph)
    add_batch(graph, second, second_draft, "second")
    assert len(topic_register(graph)) == 2


@pytest.mark.parametrize(
    "corruption,expected",
    [
        ("offset", "exact source"),
        ("unknown_source", "unknown evidence"),
        ("missing_fact", "not allocated"),
        ("duplicate_fact", "more than once"),
        ("scope", "scope differ"),
        ("condition", "drops fact conditions"),
        ("exception", "drops fact exceptions"),
        ("modality", "changes fact modality"),
        ("context_only", "no owned source"),
        ("finding", "Unresolved semantic"),
    ],
)
def test_semantic_validator_rejects_unreleasable_graph(corruption, expected):
    payload, draft = registration_batch()
    rule = draft["rules"][0]
    if corruption == "offset":
        draft["topics"][0]["quotes"][0]["start"] = 1
    elif corruption == "unknown_source":
        draft["topics"][0]["quotes"][0]["evidence_id"] = "missing"
    elif corruption == "missing_fact":
        draft["rules"] = []
    elif corruption == "duplicate_fact":
        another = deepcopy(rule)
        another["key"] = "duplicate"
        draft["rules"].append(another)
    elif corruption == "scope":
        draft["topics"][0]["scope"] = "Different scope"
    elif corruption == "condition":
        rule["condition_groups"][0]["conditions"].pop()
    elif corruption == "exception":
        rule["exceptions"] = []
    elif corruption == "modality":
        rule["modality"] = "sufficient"
    elif corruption == "context_only":
        payload["context_evidence_ids"] = payload["owned_evidence_ids"]
        payload["owned_evidence_ids"] = []
    elif corruption == "finding":
        draft["findings"] = ["Unclear antecedent"]
    canonical, issues = validate_semantic_proposal(draft, payload)
    assert canonical == {}
    assert any(expected in issue for issue in issues), issues


def test_existing_topic_cannot_change_scope_through_registered_key(tmp_path):
    graph = KnowledgeGraph(tmp_path / "graph.sqlite")
    first, first_draft = registration_batch("first")
    add_batch(graph, first, first_draft, "first")
    payload, draft = registration_batch("second", "Admin portal")
    payload["topic_register"] = topic_register(graph)
    topic_id = payload["topic_register"][0]["id"]
    draft["topics"][0]["key"] = topic_id
    draft["rules"][0]["topic_key"] = topic_id
    _, issues = validate_semantic_proposal(draft, payload)
    assert any("identity or scope changed" in issue for issue in issues)


def test_publication_rejects_changed_batch_and_source_without_partial_mutation(tmp_path):
    graph = KnowledgeGraph(tmp_path / "graph.sqlite")
    payload, draft = registration_batch()
    canonical = add_batch(graph, payload, draft, "batch")
    original = semantic_records(graph)
    changed = deepcopy(canonical)
    changed["owned_evidence_ids"] = []
    with pytest.raises(ValueError, match="different content"):
        publish_semantic_batch(graph, changed, "batch")
    changed["nodes"][0]["quotes"][0]["text"] = "Invented quote"
    with pytest.raises(ValueError, match="exact source"):
        publish_semantic_batch(graph, changed, "another")
    assert semantic_records(graph) == original


def test_quality_report_flags_missing_semantic_allocations(tmp_path):
    graph = KnowledgeGraph(tmp_path / "graph.sqlite")
    payload, _ = registration_batch()
    graph.add_evidence(payload["sources"])
    graph.add_assertions(payload["facts"])
    report = semantic_quality_report(graph)
    assert not report["accepted"]
    assert report["unallocated_fact_ids"] == [payload["facts"][0]["id"]]


def test_publication_rejects_unsupported_semantic_edge(tmp_path):
    graph = KnowledgeGraph(tmp_path / "graph.sqlite")
    payload, draft = registration_batch()
    canonical, issues = validate_semantic_proposal(draft, payload)
    assert not issues
    graph.add_evidence(payload["sources"])
    graph.add_assertions(payload["facts"])
    canonical["edges"][0]["type"] = "INVENTED_RELATION"
    with pytest.raises(ValueError, match="Unsupported semantic relation"):
        publish_semantic_batch(graph, canonical, "batch")
    assert semantic_records(graph) == ([], [])


def test_citation_has_exact_absolute_location_and_preserves_span_locator(tmp_path):
    graph = KnowledgeGraph(tmp_path / "graph.sqlite")
    payload, draft = registration_batch()
    source = payload["sources"][0]
    source.update(
        {
            "source_start_char": 97,
            "start_column": 5,
            "locator": {"kind": "characters", "start": 97, "end": 97 + len(source["text"])},
        }
    )
    add_batch(graph, payload, draft, "batch")
    quotes = semantic_bundle(graph, [topic_register(graph)[0]["id"]])["quotes"]
    quote = next(item for item in quotes if item["text"] == "valid email")
    start = source["text"].index("valid email")
    assert quote["locator"] == {
        "kind": "characters",
        "start": 97 + start,
        "end": 97 + start + len("valid email"),
    }
    assert quote["source_locator"] == source["locator"]
    assert quote["start_column"] == 5 + start
    assert quote["end_column"] == quote["start_column"] + len("valid email")
    report_quote = next(
        item
        for item in semantic_quality_report(graph)["citations"]
        if item["text"] == "valid email"
    )
    assert report_quote == {key: value for key, value in quote.items() if key != "source"}


def test_citation_multiline_unicode_columns_and_attachment_locator():
    text = "ą😀 start\nsecond line\nlast"
    source = {
        "text": text,
        "start_line": 9,
        "start_column": 4,
        "path": "attachment.pdf",
        "file_hash": digest(text),
        "locator": {"kind": "page", "page": 3},
    }
    start = text.index("second")
    end = text.index("last") + len("last")
    quote = {"evidence_id": "source", "start": start, "end": end, "text": text[start:end]}
    citation = source_citation(quote, source)
    assert (citation["start_line"], citation["start_column"]) == (10, 1)
    assert (citation["end_line"], citation["end_column"]) == (11, 5)
    assert citation["locator"] == source["locator"]
    assert citation["source_locator"] == source["locator"]
    assert citation["quote_locator"] == {"kind": "characters", "start": start, "end": end}
    assert citation["quote_locator_basis"] == "evidence_text"


def test_unique_quote_anchor_repairs_offsets_without_modifying_raw_or_text():
    payload, draft = registration_batch()
    quote = draft["rules"][0]["condition_groups"][0]["conditions"][0]["quotes"][0]
    quote["start"], quote["end"] = 1, 2
    original = deepcopy(draft)
    _, issues = validate_semantic_proposal(draft, payload)
    assert any("exact source" in issue for issue in issues)
    anchored, repairs = anchor_semantic_quotes(draft, payload)
    assert draft == original
    assert len(repairs) == 1
    assert repairs[0]["path"] == "draft.rules[0].condition_groups[0].conditions[0].quotes[0]"
    assert repairs[0]["before"] == {"start": 1, "end": 2}
    assert repairs[0]["reason"] == "unique_exact_match"
    result = anchored["rules"][0]["condition_groups"][0]["conditions"][0]["quotes"][0]
    assert result["text"] == quote["text"]
    assert result["evidence_id"] == quote["evidence_id"]
    _, issues = validate_semantic_proposal(anchored, payload)
    assert not issues
    source = {**payload["sources"][0], "source_start_char": 40}
    citation = source_citation(result, source)
    assert citation["locator"]["start"] == 40 + result["start"]
    assert citation["locator"]["end"] == 40 + result["end"]


@pytest.mark.parametrize(
    "source,text,start,end",
    [
        ("repeated repeated", "repeated", 9, 17),
        ("repeated repeated", "repeated", 1, 2),
        ("banana", "ana", 0, 1),
        ("Original text", "Invented text", 0, 1),
        ("two  spaces", "two spaces", 0, 1),
        ("cafe\u0301", "café", 0, 1),
    ],
)
def test_anchoring_preserves_valid_or_unresolvable_quote(source, text, start, end):
    draft = {
        "topics": [
            {"quotes": [{"evidence_id": "source", "start": start, "end": end, "text": text}]}
        ]
    }
    anchored, repairs = anchor_semantic_quotes(
        draft, {"sources": [{"id": "source", "text": source}]}
    )
    assert anchored == draft
    assert repairs == []


@pytest.mark.parametrize(
    "text,occurrence", [("repeated", "repeated repeated"), ("Missing quote", "Original text")]
)
def test_unresolved_anchor_remains_rejected_by_strict_validator(text, occurrence):
    payload, draft = registration_batch()
    payload["sources"][0]["text"] += " " + occurrence
    draft["topics"][0]["quotes"][0].update({"text": text, "start": 1, "end": 2})
    anchored, repairs = anchor_semantic_quotes(draft, payload)
    assert repairs == []
    _, issues = validate_semantic_proposal(anchored, payload)
    assert any("exact source" in issue for issue in issues)


def test_anchor_missing_evidence_and_empty_quotes_remain_unmodified():
    draft = {
        "topics": [
            {
                "quotes": [
                    {"evidence_id": "missing", "start": 0, "end": 1, "text": "text"},
                    {"evidence_id": "source", "start": 0, "end": 1, "text": ""},
                ]
            }
        ]
    }
    anchored, repairs = anchor_semantic_quotes(
        draft, {"sources": [{"id": "source", "text": "text"}]}
    )
    assert anchored == draft
    assert repairs == []


def compound_condition_batch(identifier="one", binding="Valid email or accepted terms"):
    payload, draft = registration_batch(identifier)
    old_phrase = "both a valid email and accepted terms"
    new_phrase = "either a valid email or accepted terms"
    source = payload["sources"][0]
    source["text"] = source["text"].replace(old_phrase, new_phrase)
    source["file_hash"] = digest(source["text"])
    rule = draft["rules"][0]
    rule["statement"] = "Registration requires a valid email or accepted terms."
    for quote in rule["quotes"] + rule["topic_quotes"]:
        quote["text"] = quote["text"].replace(old_phrase, new_phrase)
    payload["facts"][0]["statement"] = rule["statement"]
    payload["facts"][0]["conditions"] = [binding]
    payload["facts"][0] = normalized_assertion(payload["facts"][0], {identifier})
    rule["fact_ids"] = [payload["facts"][0]["id"]]
    group = rule["condition_groups"][0]
    group["operator"] = "any"
    group["source_conditions"] = [binding]
    draft, _ = anchor_semantic_quotes(draft, payload)
    return payload, draft


def test_compound_condition_binding_preserves_atomic_alternatives():
    payload, draft = compound_condition_batch()
    canonical, issues = validate_semantic_proposal(draft, payload)
    assert not issues
    groups = [node for node in canonical["nodes"] if node["type"] == "ConditionGroup"]
    assert len(groups) == 1
    assert groups[0]["operator"] == "any"
    assert groups[0]["source_conditions"] == ["Valid email or accepted terms"]
    assert {node["name"] for node in canonical["nodes"] if node["type"] == "Condition"} == {
        "Valid email",
        "Accepted terms",
    }


def test_compound_condition_without_source_binding_is_rejected():
    payload, draft = compound_condition_batch()
    draft["rules"][0]["condition_groups"][0]["source_conditions"] = []
    _, issues = validate_semantic_proposal(draft, payload)
    assert any("drops fact conditions" in issue for issue in issues)


def test_invented_or_reworded_source_condition_binding_is_rejected():
    payload, draft = compound_condition_batch()
    draft["rules"][0]["condition_groups"][0]["source_conditions"].append(
        "Valid email OR accepted terms"
    )
    _, issues = validate_semantic_proposal(draft, payload)
    assert any("unknown source condition" in issue for issue in issues)


def test_compound_binding_does_not_change_identity_and_annotations_are_unioned(tmp_path):
    graph = KnowledgeGraph(tmp_path / "graph.sqlite")
    first, first_draft = compound_condition_batch("one", "Valid email or accepted terms")
    second, second_draft = compound_condition_batch("two", "Either valid email or accepted terms")
    first_canonical = add_batch(graph, first, first_draft, "one")
    second_canonical = add_batch(graph, second, second_draft, "two")
    assert {node["id"] for node in first_canonical["nodes"]} == {
        node["id"] for node in second_canonical["nodes"]
    }
    group = next(node for node in semantic_records(graph)[0] if node["type"] == "ConditionGroup")
    assert group["source_conditions"] == [
        "Either valid email or accepted terms",
        "Valid email or accepted terms",
    ]
    assert semantic_quality_report(graph)["accepted"]


def test_compound_binding_does_not_allow_dropping_exception():
    payload, draft = compound_condition_batch()
    draft["rules"][0]["exceptions"] = []
    _, issues = validate_semantic_proposal(draft, payload)
    assert any("drops fact exceptions" in issue for issue in issues)
