from types import SimpleNamespace

from docgen_graph.knowledge import KnowledgeGraph
from docgen_graph.semantic_contracts import NavigationalGraphDraft, SemanticGraphDraft
from docgen_graph.semantic_graph import semantic_payload
from docgen_graph.source_documents import document_spans
from docgen_graph.storage import ArtifactStore, digest
from docgen_graph.workflow import Pipeline


def test_authoring_context_retains_adjacent_exception_before_unrelated_keyword_hit(tmp_path):
    graph = KnowledgeGraph(tmp_path / "graph.sqlite")
    phrases = [
        "Borrowing requires active membership.",
        "Invited readers are exempt from membership.",
        "Borrowing unrelated procedure.",
    ]
    spans = [
        {
            "id": str(index),
            "kind": "docs",
            "path": "library.md" if index < 2 else "other.md",
            "file_hash": "library" if index < 2 else "other",
            "start_line": index + 1,
            "end_line": index + 1,
            "heading": "",
            "text": phrase + " neutral" * 400,
            "role": "legacy_document",
        }
        for index, phrase in enumerate(phrases)
    ]
    graph.add_evidence(spans)
    budget = sum(len(span["text"]) for span in spans[:2])
    context = graph.source_context(["Borrowing"], max_characters=budget)
    assert {span["id"] for span in context["evidence"]} == {"0", "1"}
    assert context["context_characters"] <= budget
    assert context["omitted_evidence_ids"] == ["2"]


def test_adjacent_context_does_not_displace_mandatory_source(tmp_path):
    graph = KnowledgeGraph(tmp_path / "graph.sqlite")
    graph.add_evidence(
        [
            {
                "id": str(index),
                "kind": "docs",
                "path": "source.md",
                "file_hash": "source",
                "start_line": index + 1,
                "end_line": index + 1,
                "heading": "",
                "text": f"Rule {index}. " * 20,
                "role": "legacy_document",
            }
            for index in range(4)
        ]
    )
    context = graph.source_context(["Rule"], ["3"], max_characters=200)
    assert context["evidence"][0]["id"] == "3"
    assert "3" not in context["omitted_evidence_ids"]


def test_long_unformatted_source_remains_in_character_order(tmp_path):
    text = "first " * 1800 + "middle " * 1800 + "last " * 1800
    spans = document_spans(
        {"path": "plain.md", "kind": "docs", "hash": digest(text.encode())}, text
    )
    assert len(spans) > 2
    assert {span["start_line"] for span in spans} == {1}
    graph = KnowledgeGraph(tmp_path / "graph.sqlite")
    graph.add_evidence(list(reversed(spans)))
    context = graph.source_context(max_characters=len(text))
    assert "".join(span["text"] for span in context["evidence"]) == text


def test_active_navigation_contract_excludes_legacy_formalization():
    schema = NavigationalGraphDraft.model_json_schema()
    assert set(schema["properties"]) == {"concepts", "relationships", "findings"}
    assert "SemanticConditionGroup" not in schema["$defs"]
    legacy = SemanticGraphDraft.model_validate({"concepts": [], "relationships": []})
    assert legacy.topics == []
    assert legacy.rules == []


def test_autopilot_publishes_valid_map_despite_one_unsupported_relationship(tmp_path):
    store = ArtifactStore(tmp_path)
    pipeline = Pipeline(store, SimpleNamespace(settings=SimpleNamespace(source_first=True)), "run")
    text = "Approval is required."
    source = {"id": "source", "text": text}
    quote = {"evidence_id": "source", "text": text, "start": 0, "end": len(text)}
    state = {
        "mode": "autopilot",
        "semantic_payload_ref": store.put(semantic_payload([], [source])),
        "semantic_draft_ref": store.put(
            {
                "concepts": [
                    {"key": "approval", "name": "Approval", "description": text, "quotes": [quote]}
                ],
                "relationships": [
                    {
                        "source_key": "approval",
                        "target_key": "source",
                        "description": "Unsupported extension",
                        "quotes": [{**quote, "text": "Approval is never required."}],
                    }
                ],
            }
        ),
    }
    result = pipeline.audit_semantic_graph(state)
    assert result["route"] == "publish_semantic_graph"
    canonical = store.get(result["semantic_canonical_ref"])
    assert len(canonical["nodes"]) == 1
    assert not any(edge["type"] == "RELATED" for edge in canonical["edges"])
    assert len(store.get(result["limitations_ref"])) == 1
    assert store.get(result["semantic_audit_ref"])["accepted"] is None
