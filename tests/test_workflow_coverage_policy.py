from types import SimpleNamespace

from docgen_graph.storage import ArtifactStore
from docgen_graph.workflow import Pipeline


class CoverageAuditModel:
    def __init__(self, omitted=(), findings=()):
        self.settings = SimpleNamespace(minimum_coverage=0.9)
        self.omitted = set(omitted)
        self.findings = list(findings)

    def call(self, stage, payload, schema=None):
        assert stage == "audit_source_to_document"
        return {
            "decisions": [
                {
                    "aspect_id": aspect["id"],
                    "status": "unresolved" if aspect["id"] in self.omitted else "represented",
                    "fact_ids": []
                    if aspect["id"] in self.omitted
                    else [
                        fact["id"]
                        for fact in payload["facts"]
                        if aspect["evidence_id"] in fact["evidence_ids"]
                    ],
                    "reason": "Final text independently audited",
                }
                for aspect in payload["aspects"]
            ],
            "findings": self.findings,
        }


def make_pipeline(tmp_path, model, count=10, batches=None):
    store = ArtifactStore(tmp_path)
    pipeline = Pipeline(store, model, "coverage")
    spans = [{"id": f"e{index}", "text": f"Original claim {index}"} for index in range(count)]
    aspects = [
        {
            "id": f"a{index}",
            "evidence_id": span["id"],
            "kind": "obligation",
            "quote": span["text"],
        }
        for index, span in enumerate(spans)
    ]
    facts = [
        {"id": f"f{index}", "evidence_ids": [span["id"]], "statement": span["text"]}
        for index, span in enumerate(spans)
    ]
    mappings = [
        {
            "obligation_id": fact["id"],
            "passage": fact["statement"],
            "citation_ids": fact["evidence_ids"],
        }
        for fact in facts
    ]
    extracted_decisions = [
        {
            "aspect_id": aspect["id"],
            "status": "represented",
            "fact_ids": [facts[index]["id"]],
            "reason": "Complete extraction",
        }
        for index, aspect in enumerate(aspects)
    ]
    pipeline.graph = SimpleNamespace(
        evidence=lambda key: next(span for span in spans if span["id"] == key),
        conflict_candidates=lambda: [],
    )
    state = {
        "mode": "autopilot",
        "snapshot_ref": "original-snapshot",
        "graph_revision": "frozen-graph",
        "source_audit_index": 0,
        "inventory_ref": store.put(
            {
                "spans": spans,
                "document_batches": batches or [[span["id"] for span in spans]],
                "attachments": [],
            }
        ),
        "source_aspects_ref": store.put(aspects),
        "assertions_ref": store.put(facts),
        "source_decisions_ref": store.put(extracted_decisions),
        "final_source_decisions_ref": store.put([]),
        "template_ref": store.put({"text": "Describe source behavior"}),
        "edited_ref": store.put(
            [{"title": "Behavior", "markdown": "Final claims", "mappings": mappings}]
        ),
    }
    return pipeline, state


def test_final_coverage_uses_persisted_final_audit_instead_of_extraction_decisions(tmp_path):
    pipeline, state = make_pipeline(tmp_path, CoverageAuditModel(omitted=["a9"]))
    first = pipeline.audit_source_to_document(state)
    assert first["source_audit_index"] == 1
    decisions = pipeline.store.get(first["final_source_decisions_ref"])
    assert decisions[-1]["status"] == "unresolved"
    assert pipeline.store.get(state["source_decisions_ref"])[-1]["status"] == "represented"
    resumed = {**state, **first}
    final = pipeline.audit_source_to_document(resumed)
    report = pipeline.store.get(final["source_coverage_ref"])
    assert final["route"] == "export_candidate"
    assert report["accepted"] and not report["complete"]
    assert report["coverage_ratio"] == 0.9
    assert report["omitted_aspects"][0]["id"] == "a9"


def test_final_audit_semantic_findings_always_block_even_with_tolerable_omission(tmp_path):
    pipeline, state = make_pipeline(
        tmp_path,
        CoverageAuditModel(omitted=["a9"], findings=["Unsupported guarantee added to claim a0"]),
    )
    result = pipeline.audit_source_to_document(state)
    assert result["route"] == "resolve_issues_automatically"
    assert "Unsupported guarantee added to claim a0" in pipeline.store.get(result["issue_ref"])[
        "findings"
    ]
    assert "final_source_decisions_ref" not in result


def test_final_audit_batches_share_one_global_omission_budget(tmp_path):
    pipeline, state = make_pipeline(
        tmp_path,
        CoverageAuditModel(omitted=["a0", "a1"]),
        batches=[["e0"], ["e1"], [f"e{index}" for index in range(2, 10)]],
    )
    first = pipeline.audit_source_to_document(state)
    assert first["source_audit_index"] == 1
    second = pipeline.audit_source_to_document({**state, **first})
    assert second["route"] == "resolve_issues_automatically"
    assert pipeline.store.get(second["issue_ref"])["findings"] == [
        "Unresolved source aspect: a1"
    ]


def test_final_gate_keeps_original_denominator_after_graph_and_document_omissions(tmp_path):
    pipeline, state = make_pipeline(tmp_path, CoverageAuditModel(), count=100)
    facts = pipeline.store.get(state["assertions_ref"])[:90]
    sections = pipeline.store.get(state["edited_ref"])
    sections[0]["mappings"] = sections[0]["mappings"][:81]
    decisions = pipeline.store.get(state["source_decisions_ref"])
    for decision in decisions[81:]:
        decision.update(status="unresolved", fact_ids=[], reason="Original information omitted")
    state.update(
        source_audit_index=1,
        assertions_ref=pipeline.store.put(facts),
        edited_ref=pipeline.store.put(sections),
        final_source_decisions_ref=pipeline.store.put(decisions),
    )
    result = pipeline.audit_source_to_document(state)
    assert len(sections[0]["mappings"]) / len(facts) == 0.9
    assert result["route"] == "resolve_issues_automatically"
    assert "source_coverage_ref" not in result


def test_final_gate_rejects_missing_final_decisions_even_when_extraction_is_complete(tmp_path):
    pipeline, state = make_pipeline(tmp_path, CoverageAuditModel())
    state["source_audit_index"] = 1
    result = pipeline.audit_source_to_document(state)
    assert result["route"] == "resolve_issues_automatically"
    assert "source_coverage_ref" not in result
