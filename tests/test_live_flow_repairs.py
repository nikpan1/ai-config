from types import SimpleNamespace

from docgen_graph.storage import ArtifactStore
from docgen_graph.workflow import Pipeline


class InventoryModel:
    settings = SimpleNamespace(content_repair_limit=1)

    def __init__(self, repaired):
        self.repaired = repaired
        self.requests = []

    def call(self, stage, payload, schema):
        assert stage == "inventory_aspects"
        self.requests.append(payload)
        quote = (
            "**No call** occurs." if self.repaired and len(self.requests) > 1 else "No call occurs."
        )
        return {
            "aspects": [
                {
                    "id": "candidate",
                    "evidence_id": "e1",
                    "quote": quote,
                    "kind": "condition",
                    "description": "No provider call occurs.",
                }
            ],
            "non_substantive": [],
        }


def inventory_pipeline(tmp_path, repaired):
    store = ArtifactStore(tmp_path)
    model = InventoryModel(repaired)
    pipeline = Pipeline(store, model, "quote-repair")
    state = {
        "mode": "autopilot",
        "inventory_ref": store.put(
            {
                "document_batches": [["e1"]],
                "code_units": [],
                "spans": [{"id": "e1", "text": "**No call** occurs."}],
            }
        ),
    }
    return pipeline, model, state


def test_inventory_repairs_rendered_quote_from_original_source(tmp_path):
    pipeline, model, state = inventory_pipeline(tmp_path, True)
    first = pipeline.inventory_source_aspects(state)
    assert first["route"] == "inventory_source_aspects"
    second = pipeline.inventory_source_aspects({**state, **first})
    assert "Aspect quote does not resolve: e1" in model.requests[1]["feedback"]
    assert model.requests[1]["previous"]["aspects"][0]["quote"] == "No call occurs."
    assert second["source_aspect_index"] == 1
    assert second["attempt"] == 0 and second["feedback_ref"] == ""
    aspect = pipeline.store.get(second["source_aspects_ref"])[0]
    assert aspect["quote"] == "**No call** occurs."
    assert aspect["start"] == 0 and aspect["end"] == 19


def test_inventory_still_rejects_invalid_quote_after_bounded_repair(tmp_path):
    pipeline, model, state = inventory_pipeline(tmp_path, False)
    first = pipeline.inventory_source_aspects(state)
    second = pipeline.inventory_source_aspects({**state, **first})
    assert second["route"] == "resolve_issues_automatically"
    assert len(model.requests) == 2
    assert "source_aspects_ref" not in second


def test_codex_schema_meets_strict_object_contract():
    from docgen_graph.code_analysis.sdk_worker import output_schema

    schema = output_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"schema_version", "report", "details", "relations"}
    fact = schema["$defs"]["AssertionDraft"]
    assert fact["additionalProperties"] is False
    assert set(fact["required"]) == set(fact["properties"])
    assert "default" not in fact["properties"]["conditions"]
    relation = schema["$defs"]["CodeRelationDraft"]
    assert relation["additionalProperties"] is False
    assert set(relation["required"]) == set(relation["properties"])


def test_sdk_worker_redacts_key_from_provider_diagnostics(monkeypatch, capsys):
    import io
    import json

    from docgen_graph.code_analysis import sdk_worker

    def rejected(request):
        raise ValueError("Rejected token " + request["api_key"])

    monkeypatch.setattr(sdk_worker, "run", rejected)
    monkeypatch.setattr(sdk_worker.sys, "stdin", io.StringIO('{"api_key":"sensitive-key"}'))
    sdk_worker.main()
    output = capsys.readouterr().out
    assert "sensitive-key" not in output
    assert json.loads(output)["error_message"] == "Rejected token [redacted]"


def test_codex_usage_events_distinguish_request_response_and_cache(tmp_path):
    import json

    from test_code_analysis import Allowance, Transport

    from docgen_graph.code_analysis.backends import SDKCodeBackend

    class MeteredTransport(Transport):
        def run(self, payload):
            return {**super().run(payload), "usage": {"input_tokens": 10, "output_tokens": 20}}

    class MeteredAllowance(Allowance):
        def settle(self, reservation, usage):
            super().settle(reservation, usage)
            return 1.25

    settings = SimpleNamespace(
        code_analysis_backend="codex_sdk",
        code_analysis_model="explicit-model",
        code_analysis_turn_limit=1,
        code_analysis_result_limit=10000,
        code_analysis_timeout=60,
        request_tokens=10000,
    )
    store = ArtifactStore(tmp_path)
    transport = MeteredTransport(
        {
            "report": "result",
            "details": [
                {
                    "statement": "Consent is required.",
                    "evidence_ids": ["e1"],
                }
            ],
        }
    )
    allowance = MeteredAllowance()
    backend = SDKCodeBackend(settings, store, "usage", tmp_path, transport, allowance)
    payload = {"spans": [{"id": "e1", "text": "require consent"}]}
    assert backend.analyze_unit(payload).status == "ok"
    assert backend.analyze_unit(payload).status == "ok"
    events = [
        json.loads(line) for line in (tmp_path / "runs/usage/events.jsonl").read_text().splitlines()
    ]
    assert [item["event"] for item in events] == ["request", "response", "cache_hit"]
    assert all(item["provider"] == "codex_sdk" for item in events)
    assert all(item["model"] == "explicit-model" for item in events)
    assert events[1]["usage"] == {"input_tokens": 10, "output_tokens": 20}
    assert events[1]["cost_pln"] == 1.25
    assert len(allowance.settlements) == transport.calls == 1


def test_document_provenance_is_assigned_by_the_actual_producer(tmp_path):
    from test_pipeline_restart import FixtureModel

    from docgen_graph.evidence_service import RevisionEvidenceService
    from docgen_graph.ingestion import inventory, snapshot_inputs

    class InventedProvenance(FixtureModel):
        settings = SimpleNamespace(model="gemini-3.8-flash")

        def call(self, stage, payload, schema=None):
            result = super().call(stage, payload, schema)
            if stage == "extract_document":
                for fact in result["assertions"]:
                    fact["provenance_ids"] = [fact["evidence_ids"][0], "invented-producer"]
                    fact["review_status"] = "verified"
            return result

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "rules.md").write_text("Customer acceptance is required before substitution.\n")
    template = tmp_path / "template.md"
    template.write_text("## Rules\n")
    store = ArtifactStore(tmp_path / "runtime")
    model = InventedProvenance()
    pipeline = Pipeline(store, model, "provenance")
    snapshot = snapshot_inputs(store, docs, None, template, "")
    source_inventory = inventory(store, snapshot)
    state = {
        "snapshot_ref": store.put(snapshot),
        "inventory_ref": store.put(source_inventory),
        "document_index": 0,
    }
    output = pipeline.extract_document_batch(state)
    draft = store.get(output["draft_ref"])
    provenance = store.get(output["document_candidate_provenance_ref"])
    assert provenance["provider"] == "gemini"
    assert provenance["model"] == "gemini-3.8-flash"
    assert provenance["prompt_version"] == "extract_document.v1"
    assert all(f["provenance_ids"] == [provenance["id"]] for f in draft["assertions"])
    assert all(f["review_status"] == "unreviewed" for f in draft["assertions"])
    pipeline.graph.add_evidence(source_inventory["spans"])
    from docgen_graph.knowledge import normalized_assertion

    allowed = {s["id"] for s in source_inventory["spans"]}
    pipeline.graph.add_assertions([normalized_assertion(f, allowed) for f in draft["assertions"]])
    service = RevisionEvidenceService.from_graph(
        store,
        pipeline.graph,
        state["snapshot_ref"],
        provenance=[provenance],
    )
    assert service.packet.facts[0].provenance_ids == [provenance["id"]]


def test_classification_cannot_return_semantic_or_temporal_edits():
    import pytest
    from pydantic import ValidationError

    from docgen_graph.contracts import CodeFactClassification

    metadata = {
        "id": "fact-1",
        "categories": ["PRODUCT_FEATURE"],
        "classification_reason": "Visible action",
        "relevance": "essential",
        "relevance_reason": "Required behavior",
        "audience_scope": "product readers",
        "support_status": "direct",
    }
    for field, value in [("statement", "Changed meaning"), ("temporal_status", "current_snapshot")]:
        with pytest.raises(ValidationError, match="Extra inputs"):
            CodeFactClassification.model_validate({**metadata, field: value})


def test_classification_keeps_original_identity_and_temporal_status(tmp_path):
    from test_code_analysis_stages import OfflineModel, StagePipeline

    from docgen_graph.code_analysis import stages
    from docgen_graph.ingestion import inventory
    from docgen_graph.knowledge import normalized_assertion

    pipeline = StagePipeline(tmp_path, OfflineModel())
    file_hash = pipeline.store.put_bytes(b"if (enabled) approve();\n")
    snapshot = {
        "files": [{"kind": "code", "path": "Rule.java", "hash": file_hash}],
        "revision": "fixture",
    }
    source_inventory = inventory(pipeline.store, snapshot)
    state = {
        "snapshot_ref": pipeline.store.put(snapshot),
        "inventory_ref": pipeline.store.put(source_inventory),
    }
    state.update(stages.inventory_code_scope(pipeline, state))
    span_id = source_inventory["spans"][0]["id"]
    original = normalized_assertion(
        {
            "statement": "Approve only when enabled.",
            "conditions": ["enabled"],
            "exceptions": ["disabled"],
            "evidence_ids": [span_id],
            "temporal_status": "historical",
        },
        {span_id},
    )
    state["verified_code_ref"] = pipeline.store.put([original])
    update = stages.classify_code_facts(pipeline, state)
    classified = pipeline.store.get(update["classified_code_ref"])["details"][0]
    for name in ["id", "statement", "conditions", "exceptions", "evidence_ids", "temporal_status"]:
        assert classified[name] == original[name]


class FinalAuditModel:
    def __init__(self, findings=None):
        self.payload = None
        self.findings = findings or []

    def call(self, stage, payload, schema):
        assert stage == "audit_source_to_document"
        self.payload = payload
        return {
            "decisions": [
                {
                    "aspect_id": "a1",
                    "fact_ids": ["f1"],
                    "status": "represented",
                    "reason": "Preserved",
                }
            ],
            "findings": self.findings,
        }


def final_audit_fixture(tmp_path, model):
    store = ArtifactStore(tmp_path)
    pipeline = Pipeline(store, model, "final-audit")
    blocks = {
        "D1": {"id": "e1", "text": "Consent is required."},
        "D2": {"id": "e2", "text": "Both systems share a correlation ID."},
        "C1": {"id": "e3", "text": "checkConsent();"},
    }
    pipeline.graph = SimpleNamespace(evidence=lambda key: blocks[key])
    passage = (
        "Consent is required [Legacy D1]; code checks it [Code C1]. "
        "Systems share an ID [Legacy D2]."
    )
    mappings = [
        {"obligation_id": key, "passage": passage, "citation_ids": [citation]}
        for key, citation in [("f1", "D1"), ("f2", "D2"), ("f3", "C1")]
    ]
    mappings.append({"obligation_id": "f4", "passage": "Other paragraph", "citation_ids": ["D4"]})
    facts = [{"id": f"f{i}", "evidence_ids": [f"e{i}"]} for i in range(1, 5)]
    state = {
        "inventory_ref": store.put(
            {
                "document_batches": [["e1", "meta"]],
                "spans": list(blocks.values()) + [{"id": "meta", "text": "source_id: sample"}],
            }
        ),
        "assertions_ref": store.put(facts),
        "source_aspects_ref": store.put([{"id": "a1", "evidence_id": "e1"}]),
        "source_non_substantive_ref": store.put([{"evidence_id": "meta", "reason": "Metadata"}]),
        "edited_ref": store.put(
            [{"title": "Rules", "markdown": "Shared source note.", "mappings": mappings}]
        ),
        "snapshot_ref": "snapshot",
        "plan_hash": "plan",
        "mode": "autopilot",
    }
    return pipeline, state


def test_final_source_audit_includes_shared_paragraph_support(tmp_path):
    model = FinalAuditModel()
    pipeline, state = final_audit_fixture(tmp_path, model)
    result = pipeline.audit_source_to_document(state)
    assert result["source_audit_index"] == 1
    assert model.payload["aspects"] == [{"id": "a1", "evidence_id": "e1"}]
    assert model.payload["document_context"] == [
        {"title": "Rules", "markdown": "Shared source note."}
    ]
    assert {item["text"] for item in model.payload["blocks"]} == {
        "Consent is required.",
        "source_id: sample",
    }
    assert {item["id"] for item in model.payload["facts"]} == {"f1"}
    assert {item["id"] for item in model.payload["supporting_facts"]} == {"f2", "f3"}
    assert {item["id"] for item in model.payload["supporting_blocks"]} == {"e2", "e3"}
    assert len(model.payload["final_passages"][0]["mappings"]) == 3
    assert model.payload["non_substantive_candidates"] == [
        {"evidence_id": "meta", "reason": "Metadata"}
    ]


def test_final_source_audit_still_blocks_real_omissions(tmp_path):
    model = FinalAuditModel(["Mandatory consent qualifier is missing"])
    pipeline, state = final_audit_fixture(tmp_path, model)
    result = pipeline.audit_source_to_document(state)
    assert result["route"] == "resolve_issues_automatically"
    assert pipeline.store.get(result["issue_ref"])["findings"] == model.findings
