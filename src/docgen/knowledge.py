from collections import defaultdict

from docgen.models import Claim, Entity, Extraction, Knowledge, Outline, Resolution


def unique(items: list, name: str) -> set[str]:
    ids = [item.id for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate {name} IDs")
    return set(ids)


def validate_extraction(batch: Extraction, supplied: set[str], complete: bool = False) -> None:
    entities = unique(batch.entities, "entity")
    claims = unique(batch.claims, "claim")
    unique(batch.relationships, "relationship")
    items: list[Entity | Claim] = [*batch.entities, *batch.claims]
    for item in items:
        if not item.evidence_ids or not set(item.evidence_ids) <= supplied:
            raise ValueError(f"Invalid evidence on {item.id}")
    for claim in batch.claims:
        if not set(claim.entity_ids) <= entities:
            raise ValueError(f"Unknown entity on {claim.id}")
    for edge in batch.relationships:
        if edge.subject not in entities or edge.object not in entities:
            raise ValueError(f"Unknown endpoint on {edge.id}")
        if not edge.claim_ids or not set(edge.claim_ids) <= claims:
            raise ValueError(f"Unsupported relationship {edge.id}")
    for row in batch.coverage:
        if row.evidence_id not in supplied or not set(row.claim_ids) <= claims:
            raise ValueError("Invalid coverage reference")
        if row.disposition == "excluded" and not row.reason.strip():
            raise ValueError("Excluded evidence requires a reason")
        if row.disposition == "covered" and not row.claim_ids:
            raise ValueError("Covered evidence requires claims")
        for claim_id in row.claim_ids:
            claim = next(c for c in batch.claims if c.id == claim_id)
            if row.evidence_id not in claim.evidence_ids:
                raise ValueError("Coverage claim does not reference its evidence")
    if complete:
        covered = [row.evidence_id for row in batch.coverage]
        if set(covered) != supplied or len(covered) != len(supplied):
            raise ValueError("Every supplied span requires exactly one coverage disposition")


def namespace(batch: Extraction, prefix: str) -> Extraction:
    result = batch.model_copy(deep=True)
    entities = {e.id: f"{prefix}-{e.id}" for e in result.entities}
    claims = {c.id: f"{prefix}-{c.id}" for c in result.claims}
    for entity in result.entities:
        entity.id = entities[entity.id]
    for claim in result.claims:
        claim.id = claims[claim.id]
        claim.entity_ids = [entities[e] for e in claim.entity_ids]
        claim.status = "candidate"
    for edge in result.relationships:
        edge.id = f"{prefix}-{edge.id}"
        edge.subject, edge.object = entities[edge.subject], entities[edge.object]
        edge.claim_ids = [claims[c] for c in edge.claim_ids]
    for row in result.coverage:
        row.claim_ids = [claims[c] for c in row.claim_ids]
    return result


def apply_resolution(graph: Knowledge, resolution: Resolution) -> Knowledge:
    graph = graph.model_copy(deep=True)
    entities = {e.id: e for e in graph.entities}
    for source, target in resolution.aliases.items():
        if source not in entities or target not in entities or source == target:
            raise ValueError("Invalid alias mapping")
        if target in resolution.aliases:
            raise ValueError(f"Alias chain or cycle: {source} -> {target}")
        old, retained = entities[source], entities[target]
        if (old.scope, old.version, old.type) != (retained.scope, retained.version, retained.type):
            raise ValueError(
                f"Incompatible alias {source} -> {target}: type, scope or version differs"
            )
        retained.aliases = sorted(set(retained.aliases + old.aliases + [old.name]))
        retained.evidence_ids = sorted(set(retained.evidence_ids + old.evidence_ids))
    graph.entities = [e for e in graph.entities if e.id not in resolution.aliases]
    for claim in graph.claims:
        claim.entity_ids = sorted({resolution.aliases.get(e, e) for e in claim.entity_ids})
    for edge in graph.relationships:
        edge.subject = resolution.aliases.get(edge.subject, edge.subject)
        edge.object = resolution.aliases.get(edge.object, edge.object)
    graph.aliases.update(resolution.aliases)
    graph.conflicts = resolution.conflicts
    for conflict in graph.conflicts:
        conflict.status = "unresolved"
    validate_knowledge(graph)
    return graph


def consolidate_coverage(graph: Knowledge) -> None:
    groups: dict[str, list] = defaultdict(list)
    for row in graph.coverage:
        groups[row.evidence_id].append(row)
    from docgen.models import Coverage

    ledger = []
    for evidence in graph.evidence:
        rows = groups[evidence.id]
        claims = sorted({c for row in rows for c in row.claim_ids})
        if claims:
            ledger.append(
                Coverage(evidence_id=evidence.id, disposition="covered", claim_ids=claims)
            )
        elif rows and all(row.disposition == "excluded" for row in rows):
            ledger.append(
                Coverage(
                    evidence_id=evidence.id,
                    disposition="excluded",
                    reason="; ".join(sorted({row.reason for row in rows})),
                )
            )
        else:
            ledger.append(
                Coverage(
                    evidence_id=evidence.id,
                    disposition="unresolved",
                    reason="Extraction did not establish a disposition",
                )
            )
    graph.coverage = ledger


def validate_knowledge(graph: Knowledge, approved: bool = False) -> None:
    evidence = unique(graph.evidence, "evidence")
    validate_extraction(graph, evidence)
    claims = {c.id: c for c in graph.claims}
    unique(graph.conflicts, "conflict")
    if {r.evidence_id for r in graph.coverage} != evidence:
        raise ValueError("Every evidence record needs a coverage disposition")
    if len(graph.coverage) != len(evidence):
        raise ValueError("Duplicate coverage dispositions")
    for conflict in graph.conflicts:
        if len(set(conflict.claim_ids)) < 2 or not set(conflict.claim_ids) <= claims.keys():
            raise ValueError("Invalid competing claims")
        if conflict.status == "resolved" and not conflict.rationale.strip():
            raise ValueError("Conflict resolution requires a rationale")
        if approved and any(claims[c].status == "accepted" for c in conflict.claim_ids):
            if conflict.status != "resolved":
                raise ValueError(
                    "Resolve conflicts or leave all competing claims unresolved/rejected"
                )
            if sum(claims[c].status == "accepted" for c in conflict.claim_ids) > 1:
                raise ValueError("Competing claims cannot both be approved as settled facts")
    if approved and any(c.status == "candidate" for c in graph.claims):
        raise ValueError("Assign accepted, rejected or unresolved status to every claim")


def validate_outline(outline: Outline, graph: Knowledge) -> None:
    import re

    accepted = {c.id for c in graph.claims if c.status == "accepted"}
    if not outline.chapters:
        raise ValueError("Outline must contain at least one chapter")
    chapter_ids = unique(outline.chapters, "chapter")
    covered: set[str] = set()
    seen: set[str] = set()
    for chapter in outline.chapters:
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,79}", chapter.id):
            raise ValueError("Chapter IDs must be safe lowercase slugs")
        if not chapter.required_claim_ids or not set(chapter.required_claim_ids) <= accepted:
            raise ValueError("Outline may only use accepted claims")
        if not set(chapter.prerequisites) <= seen:
            raise ValueError("Chapter prerequisites must reference earlier chapter IDs")
        seen.add(chapter.id)
        covered.update(chapter.required_claim_ids)
    if set(outline.excluded_claims) - accepted or any(
        not r.strip() for r in outline.excluded_claims.values()
    ):
        raise ValueError("Excluded outline claims require valid IDs and reasons")
    if covered | set(outline.excluded_claims) != accepted:
        raise ValueError("Outline omits accepted claims without an explicit exclusion")
    if covered & set(outline.excluded_claims) or len(chapter_ids) != len(outline.chapters):
        raise ValueError("Conflicting outline dispositions")
