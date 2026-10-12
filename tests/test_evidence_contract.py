from pathlib import Path

import pytest

from docgen_graph.evidence_contracts import (
    DeltaVerification,
    EvidenceQuery,
    EvidenceResult,
    KnowledgeDelta,
)
from docgen_graph.evidence_service import FixtureEvidenceService, RevisionEvidenceService
from docgen_graph.storage import ArtifactStore, digest


def test_c0_packets_roundtrip_and_locators():
    root = Path(__file__).parent / "fixtures/task3"
    for path in root.glob("*.json"):
        packet = EvidenceResult.model_validate_json(path.read_text())
        assert EvidenceResult.model_validate_json(packet.model_dump_json()) == packet
        for ref in packet.evidence:
            content = (root / ref.path).read_bytes()
            assert digest(content) == ref.content_hash
            assert (
                "\n".join(content.decode().splitlines()[ref.locator.start - 1 : ref.locator.end])
                == ref.text
            )


def test_c0_pagination_revision_and_qualifiers():
    root = Path(__file__).parent / "fixtures/task3"
    packet = EvidenceResult.model_validate_json((root / "complete.json").read_text())
    service = FixtureEvidenceService(packet, "fixture-snapshot", "r1")
    query = EvidenceQuery(
        snapshot_id="fixture-snapshot", graph_revision="r1", scope_id="full", limit=1
    )
    first = service.search_graph(query)
    assert first.facts[0].conditions == ["score exceeds 5"]
    assert first.conflicts and first.truncated
    second = service.search_graph(query.model_copy(update={"cursor": first.next_cursor}))
    assert second.facts[0].id == "f2" and not second.truncated
    with pytest.raises(ValueError):
        service.search_graph(query.model_copy(update={"graph_revision": "foreign"}))


def test_revision_service_rejects_foreign_bytes_and_publishes_idempotent_delta(tmp_path):
    root = Path(__file__).parent / "fixtures/task3"
    packet = EvidenceResult.model_validate_json((root / "complete.json").read_text())
    store = ArtifactStore(tmp_path)
    key = store.put_bytes((root / "source.txt").read_bytes())
    snapshot = store.put({"files": [{"path": "source.txt", "hash": key}]})
    for ref in packet.evidence:
        ref.snapshot_id = snapshot
    service = RevisionEvidenceService.publish(store, packet, snapshot)
    original = store.get_bytes(service.revision)
    query = EvidenceQuery(snapshot_id=snapshot, graph_revision=service.revision, scope_id="full")
    delta = KnowledgeDelta(
        base_revision=service.revision,
        facts=[packet.facts[0].model_copy(update={"categories": ["GUI"]})],
        verification=DeltaVerification(
            accepted=True, verifier="gemini-3.8-flash", input_hash="pending"
        ),
    )
    delta.verification.input_hash = digest(delta.verification_payload())
    result = service.apply_verified_delta(query, delta)
    assert result.graph_revision != service.revision
    assert service.apply_verified_delta(query, delta).graph_revision == result.graph_revision
    assert store.get_bytes(service.revision) == original
    foreign = packet.model_copy(deep=True)
    foreign.evidence[0].path = "other.txt"
    with pytest.raises(ValueError, match="frozen snapshot"):
        RevisionEvidenceService.publish(store, foreign, snapshot)
    delta.facts[0].statement = "Forged after audit"
    with pytest.raises(ValueError, match="exact bytes"):
        service.apply_verified_delta(query, delta)
