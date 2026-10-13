from collections import Counter


def graph_profile(tables):
    nodes = {row["id"]: row for row in tables.get("nodes", [])}
    edges = tables.get("edges", [])
    neighbors = {identifier: set() for identifier in nodes}
    relations = Counter()
    dangling = []
    for index, edge in enumerate(edges):
        source, target = edge["source_id"], edge["target_id"]
        if source not in nodes or target not in nodes:
            dangling.append(index)
        else:
            neighbors[source].add(target)
            neighbors[target].add(source)
        relations[
            (
                nodes.get(source, {}).get("type", "Missing endpoint"),
                edge.get("type", "Unknown"),
                nodes.get(target, {}).get("type", "Missing endpoint"),
                edge.get("method", "Not recorded"),
            )
        ] += 1
    unseen = set(nodes)
    components = []
    while unseen:
        pending = [min(unseen)]
        members = set()
        while pending:
            identifier = pending.pop()
            if identifier in members:
                continue
            members.add(identifier)
            unseen.discard(identifier)
            pending.extend(neighbors[identifier] - members)
        components.append(sorted(members))
    evidence = {row["id"] for row in tables.get("evidence", [])}
    assertions = {row["id"] for row in tables.get("assertions", [])}
    supported = {
        row["assertion_id"] for row in tables.get("support", []) if row["evidence_id"] in evidence
    }
    return {
        "node_types": dict(sorted(Counter(row["type"] for row in nodes.values()).items())),
        "relations": [
            dict(source_type=key[0], type=key[1], target_type=key[2], method=key[3], count=count)
            for key, count in sorted(relations.items(), key=lambda item: (-item[1], item[0]))
        ],
        "components": sorted(components, key=lambda group: (-len(group), group[0])),
        "isolated_ids": sorted(key for key, adjacent in neighbors.items() if not adjacent),
        "dangling_edge_indices": dangling,
        "unsupported_assertion_ids": sorted(assertions - supported),
        "supported_assertions": len(assertions & supported),
        "assertion_count": len(assertions),
        "interpretation": (
            "Topology and recorded evidence links do not establish semantic correctness "
            "or source completeness."
        ),
    }


def records(value):
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def identifiers(value):
    return {item for item in value if isinstance(item, str)} if isinstance(value, list) else set()


def referenced_values(value, artifacts, visited=None):
    visited = set() if visited is None else visited
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from referenced_values(item, artifacts, visited)
    elif isinstance(value, list):
        for item in value:
            yield from referenced_values(item, artifacts, visited)
    elif isinstance(value, str) and value in artifacts and value not in visited:
        visited.add(value)
        yield from referenced_values(artifacts[value].get("value"), artifacts, visited)


def quality_data(data):
    utilization = []
    passages = []
    for graph in data["graphs"]:
        revision = graph["id"]
        facts = {row["id"] for row in graph["tables"].get("assertions", [])}
        retrieved = set()
        assigned = set()
        retrieval_sources = []
        assignment_sources = []
        for stage in data["stages"]:
            value = stage.get("result", {}).get("value", {})
            if not isinstance(value, dict):
                continue
            inputs = value.get("inputs", {})
            outputs = value.get("outputs", {})
            if not isinstance(inputs, dict) or not isinstance(outputs, dict):
                continue
            if inputs.get("graph_revision") != revision:
                continue
            if value.get("stage") in {"retrieve_plan_evidence", "retrieve_section_evidence"}:
                retrieval_sources.append(stage["id"])
                for packet in referenced_values(outputs, data["artifacts"]):
                    for assertion in records(packet.get("assertions")):
                        if isinstance(assertion, dict) and assertion.get("id") in facts:
                            retrieved.add(assertion["id"])
            reference = outputs.get("plan_ref") or inputs.get("plan_ref")
            if not isinstance(reference, str):
                continue
            plan = data["artifacts"].get(reference, {}).get("value", {})
            if isinstance(plan, dict) and plan.get("graph_revision") == revision:
                assignment_sources.append(reference)
                for section in records(plan.get("sections")):
                    assigned.update(identifiers(section.get("obligation_ids")) & facts)
                    assigned.update(identifiers(section.get("supporting_obligation_ids")) & facts)
        utilization.append(
            {
                "graph_revision": revision,
                "denominator": len(facts),
                "denominator_source": f"graph:{revision}/assertions",
                "retrieved": sorted(retrieved) if retrieval_sources else None,
                "retrieval_sources": retrieval_sources,
                "assigned": sorted(assigned) if assignment_sources else None,
                "assignment_sources": sorted(set(assignment_sources)),
            }
        )
    for candidate in data["candidates"]:
        audit = candidate["files"].get("audit.json", {}).get("value", {})
        text = candidate["files"].get("documentation/index.md", {}).get("value")
        if not isinstance(audit, dict):
            continue
        graph = next(
            (item for item in data["graphs"] if item["id"] == audit.get("graph_revision")), None
        )
        support = graph["tables"].get("support", []) if graph else []
        for index, placement in enumerate(records(audit.get("placements"))):
            start, end = placement.get("start"), placement.get("end")
            valid = (
                isinstance(text, str)
                and type(start) is int
                and type(end) is int
                and 0 <= start <= end <= len(text)
                and text[start:end] == placement.get("passage")
            )
            ids = sorted(identifiers(placement.get("obligation_ids")))
            evidence = sorted({row["evidence_id"] for row in support if row["assertion_id"] in ids})
            passages.append(
                {
                    "candidate_id": candidate["id"],
                    "placement_index": index,
                    "graph_revision": audit.get("graph_revision"),
                    "graph_binding": "recorded" if graph else "unavailable",
                    "offset_status": "verified" if valid else "mismatch_or_unavailable",
                    "obligation_ids": ids,
                    "evidence_ids": evidence,
                    "source": f"candidate:{candidate['id']}/audit.json/placements/{index}",
                }
            )
    return {
        "utilization": utilization,
        "passages": passages,
        "interpretation": "Derived trace counts do not measure undiscovered source knowledge",
    }
