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
        "template_ref": store.put({"text": "## Rules"}),
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
