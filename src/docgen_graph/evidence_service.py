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
    def apply_verified_delta(
        self, query: EvidenceQuery, delta: KnowledgeDelta
    ) -> EvidenceResult: ...


class FixtureEvidenceService:
    def __init__(self, packet: EvidenceResult, snapshot_id: str, revision: str, scope_id="full"):
        self.packet = packet.model_copy(deep=True)
        self.snapshot_id = snapshot_id
        self.revision = revision
        self.scope_id = scope_id

    def _check(self, query):
        if (query.snapshot_id, query.graph_revision, query.scope_id) != (
            self.snapshot_id,
            self.revision,
            self.scope_id,
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
        page = records[offset : offset + query.limit]
        more = offset + len(page) < len(records)
        result = EvidenceResult(
            status="ok" if records else "not_found",
            graph_revision=self.revision,
            next_cursor=f"{binding}:{offset + len(page)}" if more else None,
            truncated=more,
        )
        setattr(result, field, page)
        if field == "facts":
            identifiers = {eid for fact in page for eid in fact.evidence_ids}
            result.evidence = [ref for ref in self.packet.evidence if ref.id in identifiers]
            fact_ids = {fact.id for fact in page}
            result.relations = [
                r
                for r in self.packet.relations
                if r.source_id in fact_ids or r.target_id in fact_ids
            ]
            result.conflicts = self.packet.conflicts
            provenance_ids = {pid for fact in page for pid in fact.provenance_ids}
            result.provenance = [p for p in self.packet.provenance if p.id in provenance_ids]
        return result

    def search_graph(self, query):
        text = query.query.casefold()
        mandatory = set(query.mandatory_ids)
        while True:
            added = {
                endpoint
                for relation in self.packet.relations
                if relation.type in {"QUALIFIES", "CONTRADICTS"}
                and ({relation.source_id, relation.target_id} & mandatory)
                for endpoint in (relation.source_id, relation.target_id)
            } - mandatory
            if not added:
                break
            mandatory |= added
        supported_filters = {"categories", "relevance", "temporal_status", "source_kinds"}
        if query.filters.keys() - supported_filters:
            raise ValueError("Unsupported evidence query filter")

        def matches(fact):
            for key in ("categories", "relevance", "temporal_status"):
                values = query.filters.get(key)
                if values:
                    actual = getattr(fact, key)
                    if not (set(actual if isinstance(actual, list) else [actual]) & set(values)):
                        return False
            return not text or text in fact.model_dump_json().casefold()

        facts = [fact for fact in self.packet.facts if fact.id in mandatory or matches(fact)]
        result = self._page(query, "facts", facts)
        missing = set(query.mandatory_ids) - {fact.id for fact in self.packet.facts}
        if missing:
            result.status = "not_found"
            result.warnings.append("Missing mandatory facts: " + ", ".join(sorted(missing)))
        return result

    def search_sources(self, query):
        text = query.query.casefold()
        kinds = query.filters.get("source_kinds")
        refs = [
            ref
            for ref in self.packet.evidence
            if (not kinds or ref.source_kind in kinds)
            and (ref.id in query.mandatory_ids or not text or text in ref.text.casefold())
        ]
        result = self._page(query, "evidence", refs)
        missing = set(query.mandatory_ids) - {ref.id for ref in refs}
        if missing:
            result.status = "not_found"
            result.warnings = ["Missing mandatory evidence: " + ", ".join(sorted(missing))]
        return result

    def search_code(self, query):
        return self.search_sources(
            query.model_copy(
                update={"filters": {**query.filters, "source_kinds": ["code", "patch"]}}
            )
        )

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


class RevisionEvidenceService(FixtureEvidenceService):
    def __init__(self, store, revision: str):
        record = store.get(revision)
        super().__init__(
            EvidenceResult.model_validate(record["packet"]),
            record["snapshot_id"],
            revision,
            record["scope_id"],
        )
        self.store = store

    def sync_graph(self, graph):
        spans = []
        for ref in self.packet.evidence:
            spans.append(
                {
                    "id": ref.id,
                    "kind": "code" if ref.source_kind in {"code", "patch"} else "docs",
                    "path": ref.path,
                    "file_hash": ref.content_hash,
                    "start_line": ref.locator.start or 1,
                    "end_line": ref.locator.end or 1,
                    "heading": "",
                    "text": ref.text,
                    "role": ref.source_role,
                    "source_kind": ref.source_kind,
                    "locator": ref.locator.model_dump(),
                    "snapshot_id": ref.snapshot_id,
                    "parent_ids": ref.parent_ids,
                }
            )
        graph.add_evidence(spans)
        graph.add_assertions([fact.model_dump() for fact in self.packet.facts])
        graph.add_relations([relation.model_dump() for relation in self.packet.relations])
        with graph.connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS evidence_service_state "
                "(name TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            import json

            for name, records in (
                ("coverage", self.packet.coverage),
                ("provenance", self.packet.provenance),
            ):
                connection.execute(
                    "INSERT OR REPLACE INTO evidence_service_state VALUES (?,?)",
                    (name, json.dumps([record.model_dump() for record in records])),
                )

    @classmethod
    def publish(cls, store, packet, snapshot_id, scope_id="full"):
        cls._validate_packet(store, packet, snapshot_id)
        revision = store.put(
            {
                "schema_version": 1,
                "snapshot_id": snapshot_id,
                "scope_id": scope_id,
                "packet": packet.model_dump(),
            }
        )
        return cls(store, revision)

    @classmethod
    def from_graph(cls, store, graph, snapshot_id, scope_id="full", coverage=None, provenance=None):
        from docgen_graph.evidence_contracts import (
            EvidenceLocator,
            EvidenceRef,
            FactRecord,
            SourceCoverageItem,
        )

        with graph.connect() as connection:
            refs = [
                graph.evidence(row[0])
                for row in connection.execute("SELECT id FROM evidence ORDER BY id")
            ]
            ids = [row[0] for row in connection.execute("SELECT id FROM assertions ORDER BY id")]
            if connection.execute(
                "SELECT 1 FROM sqlite_master WHERE name='evidence_service_state'"
            ).fetchone():
                import json

                saved = {
                    row[0]: json.loads(row[1])
                    for row in connection.execute("SELECT name,payload FROM evidence_service_state")
                }
                coverage = coverage if coverage is not None else saved.get("coverage", [])
                provenance = provenance if provenance is not None else saved.get("provenance", [])
        snapshot = store.get(snapshot_id)
        scope = snapshot.get("code_scope")
        if scope:
            allowed_paths = {
                f["path"] for f in scope["files"] if f["disposition"] != "out_of_scope"
            }
            refs = [
                ref
                for ref in refs
                if ref["kind"] != "code"
                or ref["path"] in allowed_paths
                or ref["path"].startswith("__history__/")
            ]
        evidence = [
            EvidenceRef(
                id=ref["id"],
                source_kind=ref.get("source_kind")
                or ("code" if ref["kind"] == "code" else "document"),
                snapshot_id=snapshot_id,
                path=ref["path"],
                content_hash=ref["file_hash"],
                source_role=ref["role"],
                locator=EvidenceLocator.model_validate(
                    ref.get("locator")
                    or {"kind": "lines", "start": ref["start_line"], "end": ref["end_line"]}
                ),
                text=ref["text"],
            )
            for ref in refs
        ]
        if coverage is None:
            coverage = [
                SourceCoverageItem(
                    id=digest(["unverified", ref.id]),
                    evidence_ids=[ref.id],
                    unit_locator=ref.locator,
                    aspect="Source coverage not audited",
                    disposition="unresolved",
                    reason="Legacy graph has no source aspect audit",
                )
                for ref in evidence
            ]
        packet = EvidenceResult(
            status="ok",
            evidence=evidence,
            facts=[FactRecord.model_validate(graph.assertion(i)) for i in ids],
            relations=graph.relations(),
            conflicts=graph.conflict_candidates(),
            coverage=coverage or [],
            provenance=provenance or [],
        )
        return cls.publish(store, packet, snapshot_id, scope_id)

    @staticmethod
    def _validate_packet(store, packet, snapshot_id):
        snapshot = store.get(snapshot_id)
        manifest = {
            (item["path"], item["hash"])
            for item in snapshot.get("files", []) + snapshot.get("attachments", [])
        }
        evidence = {ref.id: ref for ref in packet.evidence}
        facts = {fact.id: fact for fact in packet.facts}
        provenance = {p.id for p in packet.provenance}
        if len(evidence) != len(packet.evidence) or len(facts) != len(packet.facts):
            raise ValueError("Duplicate evidence or fact identities")
        for ref in evidence.values():
            if ref.snapshot_id != snapshot_id:
                raise ValueError("Evidence belongs to a foreign snapshot")
            if (ref.path, ref.content_hash) not in manifest:
                raise ValueError("Evidence path and hash are not in the frozen snapshot")
            content = store.get_bytes(ref.content_hash)
            locator = ref.locator
            if ref.source_kind == "attachment":
                from docgen_graph.attachments import extract_attachment

                parsed = extract_attachment(ref.path, content)
                if not any(
                    span["text"] == ref.text
                    and all(locator.model_dump().get(k) == v for k, v in span["locator"].items())
                    for span in parsed.get("spans", [])
                ):
                    raise ValueError("Attachment locator differs from frozen source")
            elif locator.kind == "lines":
                lines = content.decode("utf-8").splitlines()
                if locator.end > len(lines):
                    raise ValueError("Evidence line exceeds frozen source")
                if "\n".join(lines[locator.start - 1 : locator.end]) != ref.text:
                    raise ValueError("Evidence text differs from frozen source")
            elif locator.kind == "characters":
                text = content.decode("utf-8")
                if locator.end > len(text) or text[locator.start : locator.end] != ref.text:
                    raise ValueError("Evidence character range differs from frozen source")
            elif locator.kind == "diff_hunk":
                from docgen_graph.code_analysis.history import parse_patch

                hunks = parse_patch(content.decode("utf-8"))
                if not any(h["header"] == locator.hunk and h["text"] == ref.text for h in hunks):
                    raise ValueError("Diff hunk not found in frozen patch")
            else:
                raise ValueError("Unsupported locator for this source kind")
        for fact in facts.values():
            if set(fact.evidence_ids) - evidence.keys() or set(fact.provenance_ids) - provenance:
                raise ValueError("Fact references unknown evidence or provenance")
        for relation in packet.relations:
            if relation.source_id not in facts or relation.target_id not in facts:
                raise ValueError("Relation references unknown facts")
            if set(relation.evidence_ids) - evidence.keys():
                raise ValueError("Relation lacks its own evidence")
        coverage_ids = {item.id for item in packet.coverage}
        for item in packet.coverage:
            if set(item.evidence_ids) - evidence.keys() or set(item.fact_ids) - facts.keys():
                raise ValueError("Coverage references unknown records")
            if item.disposition == "represented" and not item.fact_ids:
                raise ValueError("Represented coverage requires facts")
            if item.disposition == "duplicate" and item.duplicate_of not in coverage_ids:
                raise ValueError("Duplicate coverage requires a known original aspect")
            if item.disposition == "excluded_non_substantive" and not item.decision_ref:
                raise ValueError("Coverage exclusion requires a versioned decision")
        for conflict in packet.conflicts:
            identifiers = [
                conflict[key]
                for key in ("source_id", "target_id", "code_id", "document_id")
                if key in conflict
            ]
            if any(identifier not in facts for identifier in identifiers):
                raise ValueError("Conflict references unknown facts")
            if set(conflict.get("evidence_ids", [])) - evidence.keys():
                raise ValueError("Conflict references unknown evidence")

    def verify_references(self, query):
        self._check(query)
        self._validate_packet(self.store, self.packet, self.snapshot_id)
        return self.read_evidence(query)

    def apply_verified_delta(self, query, delta):
        self._check(query)
        verification = delta.verification
        if delta.base_revision != self.revision:
            raise ValueError("Delta uses a foreign base revision")
        if (
            not verification.accepted
            or verification.findings
            or verification.verifier != "gemini-3.8-flash"
            or verification.input_hash != digest(delta.verification_payload())
        ):
            raise ValueError("Delta requires a separate accepted Gemini audit of these exact bytes")
        packet = self.packet.model_copy(deep=True)
        for field in ("facts", "evidence", "coverage", "provenance"):
            records = {record.id: record for record in getattr(packet, field)}
            for record in getattr(delta, field):
                if (
                    field in {"evidence", "provenance"}
                    and record.id in records
                    and records[record.id] != record
                ):
                    raise ValueError("Immutable evidence/provenance ID was reused")
                records[record.id] = record
            setattr(packet, field, [records[key] for key in sorted(records)])
        packet.relations = list(
            {digest(r.model_dump()): r for r in packet.relations + delta.relations}.values()
        )
        packet.conflicts = list({digest(c): c for c in packet.conflicts + delta.conflicts}.values())
        self._validate_packet(self.store, packet, self.snapshot_id)
        revision = self.store.put(
            {
                "schema_version": 1,
                "snapshot_id": self.snapshot_id,
                "scope_id": self.scope_id,
                "base_revision": self.revision,
                "delta": delta.model_dump(),
                "packet": packet.model_dump(),
            }
        )
        return EvidenceResult(
            status="ok",
            graph_revision=revision,
            facts=delta.facts,
            evidence=delta.evidence,
            coverage=delta.coverage,
        )
