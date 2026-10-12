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
