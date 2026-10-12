from typing import Protocol

from docgen_graph.evidence_contracts import EvidenceQuery, EvidenceResult, KnowledgeDelta
from docgen_graph.storage import digest


class EvidenceService(Protocol):
    def search_code(self, query: EvidenceQuery) -> EvidenceResult: ...
    def search_sources(self, query: EvidenceQuery) -> EvidenceResult: ...
    def search_graph(self, query: EvidenceQuery) -> EvidenceResult: ...
    def read_evidence(self, query: EvidenceQuery) -> EvidenceResult: ...
    def iter_coverage(self, query: EvidenceQuery) -> EvidenceResult: ...
    def verify_references(self, query: EvidenceQuery) -> EvidenceResult: ...
    def apply_verified_delta(self, query: EvidenceQuery, delta: KnowledgeDelta) -> EvidenceResult: ...


class FixtureEvidenceService:
    def __init__(self, packet: EvidenceResult, snapshot_id: str, revision: str, scope_id="full"):
        self.packet = packet.model_copy(deep=True)
        self.snapshot_id = snapshot_id
        self.revision = revision
        self.scope_id = scope_id

    def _check(self, query):
        if (query.snapshot_id, query.graph_revision, query.scope_id) != (
            self.snapshot_id, self.revision, self.scope_id
        ):
            raise ValueError("Evidence query does not match snapshot, revision and scope")

    def _page(self, query, field, records):
        self._check(query)
        if self.packet.status not in {"ok", "not_found"}:
            return self.packet.model_copy(deep=True)
        binding = digest(query.model_dump(exclude={"cursor", "limit"}))[:16]
        offset = 0
        if query.cursor:
            prefix, position = query.cursor.split(":", 1)
            if prefix != binding or not position.isdecimal():
                raise ValueError("Cursor belongs to a different query")
            offset = int(position)
        page = records[offset:offset + query.limit]
        more = offset + len(page) < len(records)
        result = EvidenceResult(status="ok" if records else "not_found", graph_revision=self.revision,
                                next_cursor=f"{binding}:{offset + len(page)}" if more else None,
                                truncated=more)
        setattr(result, field, page)
        if field == "facts":
            identifiers = {eid for fact in page for eid in fact.evidence_ids}
            result.evidence = [ref for ref in self.packet.evidence if ref.id in identifiers]
            fact_ids = {fact.id for fact in page}
            result.relations = [r for r in self.packet.relations
                                if r.source_id in fact_ids or r.target_id in fact_ids]
            result.conflicts = self.packet.conflicts
            provenance_ids = {pid for fact in page for pid in fact.provenance_ids}
            result.provenance = [p for p in self.packet.provenance if p.id in provenance_ids]
        return result

    def search_graph(self, query):
        text = query.query.casefold()
        facts = [fact for fact in self.packet.facts if fact.id in query.mandatory_ids
                 or not text or text in fact.model_dump_json().casefold()]
        return self._page(query, "facts", facts)

    def search_sources(self, query):
        text = query.query.casefold()
        kinds = query.filters.get("source_kinds")
        refs = [ref for ref in self.packet.evidence
                if (not kinds or ref.source_kind in kinds)
                and (ref.id in query.mandatory_ids or not text or text in ref.text.casefold())]
        return self._page(query, "evidence", refs)

    def search_code(self, query):
        return self.search_sources(query.model_copy(update={"filters": {
            **query.filters, "source_kinds": ["code", "patch"]}}))

    def read_evidence(self, query):
        refs = [ref for ref in self.packet.evidence if ref.id in query.mandatory_ids]
        result = self._page(query, "evidence", refs)
        missing = set(query.mandatory_ids) - {ref.id for ref in refs}
        if missing:
            result.status = "not_found"
            result.warnings = ["Missing evidence: " + ", ".join(sorted(missing))]
        return result

    def iter_coverage(self, query):
        return self._page(query, "coverage", self.packet.coverage)

    def verify_references(self, query):
        return self.read_evidence(query)

    def apply_verified_delta(self, query, delta):
        self._check(query)
        raise NotImplementedError("The fixture double does not publish graph revisions")
