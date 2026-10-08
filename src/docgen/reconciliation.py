"""Bounded identity candidates and topic-based conflict review."""

import json
import re
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from docgen.knowledge import apply_resolution
from docgen.models import Claim, Knowledge, Resolution
from docgen.storage import digest, write_json


def size(value: object) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def qualified_claim(claim: Claim) -> dict:
    return claim.model_dump(exclude={"status", "evidence_ids"}, exclude_defaults=True)


def names(entity: dict) -> set[str]:
    result = set()
    for name in [entity["name"], *entity.get("aliases", [])]:
        result.add(" ".join(re.findall(r"\w+", name.casefold())))
        result.update(re.findall(r"\b[A-Z]{1,12}-\d+\b", name))
    return result - {""}


def identity_batches(graph: Knowledge, limit: int) -> tuple[list[dict], list[str]]:
    entities = {e.id: e.model_dump(exclude_defaults=True) for e in graph.entities}
    parents = {key: key for key in entities}

    def root(key: str) -> str:
        while parents[key] != key:
            parents[key] = parents[parents[key]]
            key = parents[key]
        return key

    seen: dict[tuple, str] = {}
    for entity in graph.entities:
        for name in sorted(names(entities[entity.id])):
            key = (entity.type, entity.scope, entity.version, name)
            if key in seen:
                parents[root(entity.id)] = root(seen[key])
            seen[key] = entity.id
    groups: dict[str, list[str]] = defaultdict(list)
    for entity_id in entities:
        groups[root(entity_id)].append(entity_id)
    claims: dict[str, list[Claim]] = defaultdict(list)
    for claim in graph.claims:
        for entity_id in claim.entity_ids:
            claims[entity_id].append(claim)
    batches, gaps = [], []
    current: list[dict] = []
    for members in groups.values():
        if len(members) < 2:
            continue
        sample = {c.id: qualified_claim(c) for e in members for c in claims[e][:3]}
        group = {
            "entities": [entities[e] for e in members],
            "claims": list(sample.values()),
            "claim_sample_limit_per_entity": 3,
        }
        if size({"groups": [group]}) > limit:
            gaps.append(f"Identity group exceeds reconciliation limit; left unmerged: {members}")
            continue
        if current and size({"groups": [*current, group]}) > limit:
            batches.append({"groups": current})
            current = []
        current.append(group)
    if current:
        batches.append({"groups": current})
    return batches, gaps


def conflict_batches(graph: Knowledge, parsed: dict, limit: int) -> tuple[list[dict], list[str]]:
    spans = {s["id"]: s for s in parsed["spans"]}
    evidence = {e.id: e for e in graph.evidence}
    entities = {e.id: e for e in graph.entities}
    markers = {}
    for span in spans.values():
        match = re.search(r"\bconflict\s+group:\s*([A-Za-z0-9_-]+)", span["excerpt"], re.I)
        if match and match[1].lower() not in {"none", "unknown", "n", "na"}:
            markers[(span["path"], tuple(span["headings"]))] = match[1]
    groups: dict[str, list[dict]] = defaultdict(list)
    priority = {"capability": 0, "process": 1, "integration": 2, "configuration": 3}
    for claim in graph.claims:
        topics = set()
        for eid in claim.evidence_ids:
            span = spans.get(evidence[eid].span_id)
            if span:
                for depth in range(1, len(span["headings"]) + 1):
                    marker = markers.get((span["path"], tuple(span["headings"][:depth])))
                    if marker:
                        topics.add("source-conflict-group:" + marker)
        candidates = sorted(
            (entities[e] for e in claim.entity_ids),
            key=lambda e: (priority.get(e.type, 4), e.name.casefold(), e.id),
        )
        if candidates:
            entity = candidates[0]
            # Scope/version stay in the claims: different versions may explain a discrepancy.
            topics.add("topic:" + " ".join(re.findall(r"\w+", entity.name.casefold())))
        if not topics:
            topics.add("unclassified")
        row = qualified_claim(claim)
        row["entity_names"] = {e: entities[e].name for e in claim.entity_ids}
        for topic in sorted(topics):
            groups[topic].append(row)
    result, gaps = [], []
    current: list[dict] = []
    for topic, claims in sorted(groups.items()):
        chunk: list[dict] = []
        for claim_row in claims:
            if size({"groups": [{"topic": topic, "claims": [claim_row]}]}) > limit:
                raise ValueError(f"Claim {claim_row['id']} exceeds reconcile_chars")
            if (
                chunk
                and size({"groups": [{"topic": topic, "claims": [*chunk, claim_row]}]}) > limit
            ):
                group = {"topic": topic, "claims": chunk}
                if current:
                    result.append({"groups": current})
                    current = []
                result.append({"groups": [group]})
                gaps.append(
                    "Conflict topic split; comparisons across all chunks "
                    f"are not exhaustive: {topic}"
                )
                chunk = []
            chunk.append(claim_row)
        group = {"topic": topic, "claims": chunk}
        if current and size({"groups": [*current, group]}) > limit:
            result.append({"groups": current})
            current = []
        current.append(group)
    if current:
        result.append({"groups": current})
    gaps.append(
        "Conflict review is topic- and explicit-conflict-group-based, "
        "not an exhaustive all-pairs audit."
    )
    return result, sorted(set(gaps))


def validate_resolution(
    result: Resolution, context: dict, graph: Knowledge, identity: bool
) -> None:
    if identity:
        if result.conflicts:
            raise ValueError("Identity batches must not return conflicts")
        membership = {
            e["id"]: i for i, group in enumerate(context["groups"]) for e in group["entities"]
        }
        for source, target in result.aliases.items():
            if (
                source not in membership
                or target not in membership
                or membership[source] != membership[target]
            ):
                raise ValueError(f"Alias outside supplied identity group: {source} -> {target}")
        apply_resolution(graph, result)
    else:
        if result.aliases:
            raise ValueError("Conflict batches must not return aliases")
        allowed = {c["id"] for group in context["groups"] for c in group["claims"]}
        for conflict in result.conflicts:
            if not set(conflict.claim_ids) <= allowed:
                raise ValueError(f"Conflict {conflict.id} cites a claim outside this batch")
        apply_resolution(graph, result)


def reconcile(
    graph: Knowledge,
    parsed: dict,
    limit: int,
    directory: Path,
    resolve: Callable[[str, dict, Knowledge, bool, int], Resolution],
    event: Callable[[str, dict], None],
) -> Knowledge:
    identity, gaps = identity_batches(graph, limit)
    write_json(directory / "identity-plan.json", {"batches": identity, "gaps": gaps})
    aliases = {}
    for i, context in enumerate(identity):
        result = resolve("reconcile_entities", context, graph, True, i)
        aliases.update(result.aliases)
        event(
            "reconciliation_batch",
            {"phase": "identity", "completed": i + 1, "total": len(identity)},
        )
    graph = apply_resolution(graph, Resolution(aliases=aliases))
    conflicts, conflict_gaps = conflict_batches(graph, parsed, limit)
    write_json(directory / "conflict-plan.json", {"batches": conflicts, "gaps": conflict_gaps})
    found = {}
    for i, context in enumerate(conflicts):
        result = resolve("detect_conflicts", context, graph, False, i)
        for conflict in result.conflicts:
            key = tuple(sorted(set(conflict.claim_ids)))
            conflict.id = "conflict-" + digest(key)[:16]
            found[key] = conflict
        event(
            "reconciliation_batch",
            {"phase": "conflicts", "completed": i + 1, "total": len(conflicts)},
        )
    graph = apply_resolution(graph, Resolution(conflicts=list(found.values())))
    graph.gaps.extend(gaps + conflict_gaps)
    return graph
