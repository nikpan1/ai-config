from pathlib import Path

import pytest


@pytest.mark.parametrize("verified_edge", [True, False])
def test_mermaid_tool_requires_own_edge_audit(verified_edge):
    from docgen_graph.authoring.tools import AuthoringTools
    from docgen_graph.evidence_contracts import EvidenceQuery, EvidenceResult
    from docgen_graph.evidence_service import FixtureEvidenceService

    packet = EvidenceResult.model_validate_json(
        (Path(__file__).parent / "fixtures/task3/complete.json").read_text()
    )
    service = FixtureEvidenceService(packet, "fixture-snapshot", "r1")

    class AuditModel:
        def call(self, stage, payload, schema):
            expected = ["risk:approval", "risk:check", "risk:transition"]
            assert payload["required_diagram_element_ids"] == expected
            return {
                "accepted": True,
                "findings": [],
                "covered_diagram_element_ids": expected if verified_edge else expected[:2],
            }

    tool = AuthoringTools(
        service,
        EvidenceQuery(snapshot_id="fixture-snapshot", graph_revision="r1", scope_id="full"),
        AuditModel(),
        [],
    )
    result = tool.execute(
        "build_mermaid",
        {
            "id": "risk",
            "kind": "flowchart",
            "question": "When is approval required?",
            "description": "A score above five requires approval.",
            "nodes": [
                {"id": "check", "label": "Check score", "evidence_ids": ["e1"]},
                {"id": "approval", "label": "Require approval", "evidence_ids": ["e1"]},
            ],
            "edges": [
                {
                    "id": "transition",
                    "source": "check",
                    "target": "approval",
                    "label": "Score exceeds five",
                    "evidence_ids": ["e1"],
                }
            ],
        },
    )
    assert result["status"] == ("ok" if verified_edge else "unresolved")
    assert result["content"].startswith("flowchart LR")
