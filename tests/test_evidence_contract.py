from pathlib import Path

import pytest

from docgen_graph.evidence_contracts import EvidenceQuery, EvidenceResult
from docgen_graph.evidence_service import FixtureEvidenceService
from docgen_graph.storage import digest


def test_c0_packets_roundtrip_and_locators():
    root = Path(__file__).parent / "fixtures/task3"
    for path in root.glob("*.json"):
        packet = EvidenceResult.model_validate_json(path.read_text())
        assert EvidenceResult.model_validate_json(packet.model_dump_json()) == packet
        for ref in packet.evidence:
            content = (root / ref.path).read_bytes()
            assert digest(content) == ref.content_hash
            assert "\n".join(content.decode().splitlines()[ref.locator.start - 1:ref.locator.end]) == ref.text


def test_c0_pagination_revision_and_qualifiers():
    root = Path(__file__).parent / "fixtures/task3"
    packet = EvidenceResult.model_validate_json((root / "complete.json").read_text())
    service = FixtureEvidenceService(packet, "fixture-snapshot", "r1")
    query = EvidenceQuery(snapshot_id="fixture-snapshot", graph_revision="r1", scope_id="full", limit=1)
    first = service.search_graph(query)
    assert first.facts[0].conditions == ["score exceeds 5"]
    assert first.conflicts and first.truncated
    second = service.search_graph(query.model_copy(update={"cursor": first.next_cursor}))
    assert second.facts[0].id == "f2" and not second.truncated
    with pytest.raises(ValueError):
        service.search_graph(query.model_copy(update={"graph_revision": "foreign"}))
