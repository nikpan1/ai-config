import json
from collections import Counter
from copy import deepcopy

from pydantic import ValidationError

from docgen_graph.knowledge import KnowledgeGraph
from docgen_graph.semantic_contracts import SemanticGraphDraft
from docgen_graph.storage import digest

SEMANTIC_SCHEMA = """
CREATE TABLE IF NOT EXISTS semantic_nodes (
    id TEXT PRIMARY KEY REFERENCES nodes(id), payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS semantic_edges (
    id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES nodes(id),
    target_id TEXT NOT NULL REFERENCES nodes(id), type TEXT NOT NULL, payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS semantic_quotes (
    id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, owner_kind TEXT NOT NULL,
    evidence_id TEXT NOT NULL REFERENCES evidence(id), payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS semantic_batches (
    id TEXT PRIMARY KEY, content_hash TEXT NOT NULL, payload TEXT NOT NULL,
    provenance TEXT NOT NULL
);
"""


def anchor_semantic_quotes(raw: dict, payload: dict) -> tuple[dict, list[dict]]:
    anchored = deepcopy(raw)
    sources = {item["id"]: item["text"] for item in payload["sources"]}
    repairs = []

    def anchor(quote, path):
        if not isinstance(quote, dict):
            return
        text = quote.get("text")
        source = sources.get(quote.get("evidence_id"))
        if source is None or not isinstance(text, str) or not text:
            return
        start, end = quote.get("start"), quote.get("end")
        if (
            isinstance(start, int)
            and isinstance(end, int)
            and 0 <= start < end <= len(source)
            and source[start:end] == text
        ):
            return
        found = source.find(text)
        if found < 0 or source.find(text, found + 1) >= 0:
            return
        quote["start"], quote["end"] = found, found + len(text)
        repairs.append(
            {
                "path": path,
                "evidence_id": quote["evidence_id"],
                "before": {"start": start, "end": end},
                "after": {"start": quote["start"], "end": quote["end"]},
                "reason": "unique_exact_match",
            }
        )

    def visit(value, path):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {"quotes", "topic_quotes"} and isinstance(child, list):
                    for index, quote in enumerate(child):
                        anchor(quote, f"{path}.{key}[{index}]")
                else:
                    visit(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")

    visit(anchored, "draft")
    return anchored, repairs


def normalized_term(value: str) -> str:
    return " ".join(value.split()).casefold()


def semantic_id(kind: str, content) -> str:
    return f"semantic:{kind.lower()}:{digest(content)[:24]}"


def semantic_payload(
    facts: list[dict],
    owned_spans: list[dict],
    context_spans: list[dict] | None = None,
    topics: list[dict] | None = None,
) -> dict:
    sources = {span["id"]: span for span in context_spans or []}
    sources.update({span["id"]: span for span in owned_spans})
    return {
        "schema_version": 1,
        "facts": facts,
        "owned_evidence_ids": sorted({span["id"] for span in owned_spans}),
        "context_evidence_ids": sorted(set(sources) - {span["id"] for span in owned_spans}),
        "sources": [sources[key] for key in sorted(sources)],
        "topic_register": topics or [],
        "quote_offsets": "Zero-based Python character offsets, end exclusive, in source.text",
    }


def unique_quotes(quotes: list[dict]) -> list[dict]:
    return [item for _, item in sorted({digest(item): item for item in quotes}.items())]


def quote_issues(quotes: list[dict], sources: dict[str, dict], owner: str) -> list[str]:
    issues = []
    for quote in quotes:
        source = sources.get(quote["evidence_id"])
        if source is None:
            issues.append(f"{owner}: quote references unknown evidence {quote['evidence_id']}")
            continue
        text = source["text"]
        start, end = quote["start"], quote["end"]
        if not 0 <= start < end <= len(text) or text[start:end] != quote["text"]:
            issues.append(f"{owner}: quote does not match exact source characters")
    return issues


def all_quoted_records(draft: dict):
    for topic in draft["topics"]:
        yield topic["key"], topic["quotes"]
    for rule in draft["rules"]:
        yield rule["key"], rule["quotes"]
        yield f"{rule['key']} topic relation", rule["topic_quotes"]
        for group in rule["condition_groups"]:
            yield f"{rule['key']} condition group", group["quotes"]
            for condition in group["conditions"]:
                yield condition["statement"], condition["quotes"]
        for exception in rule["exceptions"]:
            yield exception["statement"], exception["quotes"]


def validate_semantic_proposal(raw: dict, payload: dict) -> tuple[dict, list[str]]:
    try:
        draft = SemanticGraphDraft.model_validate(raw).model_dump()
    except ValidationError as error:
        return {}, [f"Invalid semantic graph contract: {error}"]
    sources = {span["id"]: span for span in payload["sources"]}
    facts = {fact["id"]: fact for fact in payload["facts"]}
    owned = set(payload["owned_evidence_ids"])
    topics = {topic["key"]: topic for topic in draft["topics"]}
    issues = [f"Unresolved semantic finding: {finding}" for finding in draft["findings"]]
    for kind in ("topics", "rules"):
        counts = Counter(item["key"] for item in draft[kind])
        issues.extend(f"Duplicate {kind} key: {key}" for key, count in counts.items() if count > 1)
    for owner, quotes in all_quoted_records(draft):
        issues.extend(quote_issues(quotes, sources, owner))
    assigned = Counter(fid for rule in draft["rules"] for fid in rule["fact_ids"])
    issues.extend(f"Fact not allocated to a rule: {fid}" for fid in facts if not assigned[fid])
    issues.extend(f"Fact allocated more than once: {fid}" for fid, n in assigned.items() if n > 1)
    issues.extend(f"Rule references unknown fact: {fid}" for fid in assigned if fid not in facts)
    for fact in facts.values():
        if not owned.intersection(fact["evidence_ids"]):
            issues.append(f"Fact has no owned source: {fact['id']}")
        if not set(fact["evidence_ids"]).issubset(sources):
            issues.append(f"Fact source missing from semantic context: {fact['id']}")
    topic_keys = {rule["topic_key"] for rule in draft["rules"]}
    issues.extend(f"Topic has no rules: {key}" for key in topics if key not in topic_keys)
    for rule in draft["rules"]:
        topic = topics.get(rule["topic_key"])
        if topic is None:
            issues.append(f"Rule references unknown topic: {rule['key']}")
        elif normalized_term(topic["scope"]) != normalized_term(rule["scope"]):
            issues.append(f"Topic and rule scope differ: {rule['key']}")
        conditions = {
            normalized_term(item["statement"])
            for group in rule["condition_groups"]
            for item in group["conditions"]
        }
        verified_conditions = {
            condition
            for fid in rule["fact_ids"]
            if fid in facts
            for condition in facts[fid].get("conditions", [])
        }
        source_conditions = {
            condition
            for group in rule["condition_groups"]
            for condition in group["source_conditions"]
        }
        for condition in sorted(source_conditions - verified_conditions):
            issues.append(f"Group references unknown source condition: {rule['key']}: {condition}")
        conditions.update(normalized_term(condition) for condition in source_conditions)
        exceptions = {normalized_term(item["statement"]) for item in rule["exceptions"]}
        rule_sources = {quote["evidence_id"] for quote in rule["quotes"]}
        for fid in rule["fact_ids"]:
            if fid not in facts:
                continue
            fact = facts[fid]
            if normalized_term(fact["scope"]) != normalized_term(rule["scope"]):
                issues.append(f"Rule changes fact scope: {fid}")
            if not rule_sources.intersection(fact["evidence_ids"]):
                issues.append(f"Rule has no quotation from assigned fact evidence: {fid}")
            for field, actual in (("conditions", conditions), ("exceptions", exceptions)):
                missing = {normalized_term(item) for item in fact.get(field, [])} - actual
                if missing:
                    issues.append(f"Rule drops fact {field}: {fid}: {sorted(missing)}")
            modality = fact.get("modality", "descriptive")
            if modality in {"necessary", "sufficient", "necessary_and_sufficient", "prohibited"}:
                if modality != rule["modality"]:
                    issues.append(f"Rule changes fact modality: {fid}")
    register = {topic["id"]: topic for topic in payload.get("topic_register", [])}
    for topic in draft["topics"]:
        identifier = topic_identifier(topic)
        if topic["key"] in register and topic["key"] != identifier:
            issues.append(f"Existing topic identity or scope changed: {topic['key']}")
    if issues:
        return {}, sorted(set(issues))
    return canonical_graph(draft, payload), []


def topic_identifier(topic: dict) -> str:
    return semantic_id("Topic", [normalized_term(topic["name"]), normalized_term(topic["scope"])])


def canonical_graph(draft: dict, payload: dict) -> dict:
    nodes = {}
    edges = {}

    def add_node(kind, identity, name, scope, quotes, **attributes):
        identifier = semantic_id(kind, identity)
        record = {
            "id": identifier,
            "type": kind,
            "name": name,
            "scope": scope,
            "quotes": unique_quotes(quotes),
            **attributes,
        }
        if identifier in nodes:
            record["quotes"] = unique_quotes(nodes[identifier]["quotes"] + record["quotes"])
            record["fact_ids"] = sorted(
                set(nodes[identifier].get("fact_ids", [])) | set(record.get("fact_ids", []))
            )
            if "source_conditions" in record:
                record["source_conditions"] = sorted(
                    set(nodes[identifier].get("source_conditions", []))
                    | set(record["source_conditions"])
                )
        nodes[identifier] = record
        return identifier

    def add_edge(source, target, relation, quotes):
        identifier = semantic_id("Edge", [source, target, relation])
        record = {
            "id": identifier,
            "source_id": source,
            "target_id": target,
            "type": relation,
            "quotes": unique_quotes(quotes),
        }
        if identifier in edges:
            record["quotes"] = unique_quotes(edges[identifier]["quotes"] + record["quotes"])
        edges[identifier] = record

    topic_ids = {}
    for topic in draft["topics"]:
        topic_ids[topic["key"]] = add_node(
            "Topic",
            [normalized_term(topic["name"]), normalized_term(topic["scope"])],
            topic["name"],
            topic["scope"],
            topic["quotes"],
        )
    facts = {fact["id"]: fact for fact in payload["facts"]}
    for rule in draft["rules"]:
        groups = sorted(
            [
                group["operator"],
                sorted(normalized_term(c["statement"]) for c in group["conditions"]),
            ]
            for group in rule["condition_groups"]
        )
        identity = [
            normalized_term(rule["statement"]),
            normalized_term(rule["scope"]),
            rule["modality"],
            groups,
            sorted(normalized_term(e["statement"]) for e in rule["exceptions"]),
        ]
        rid = add_node(
            "Rule",
            identity,
            rule["statement"],
            rule["scope"],
            rule["quotes"],
            modality=rule["modality"],
            fact_ids=sorted(rule["fact_ids"]),
        )
        add_edge(topic_ids[rule["topic_key"]], rid, "HAS_RULE", rule["topic_quotes"])
        for fid in rule["fact_ids"]:
            quotes = [q for q in rule["quotes"] if q["evidence_id"] in facts[fid]["evidence_ids"]]
            add_edge(rid, fid, "EXPRESSES", quotes)
        for group in rule["condition_groups"]:
            gid = add_node(
                "ConditionGroup",
                [
                    rid,
                    group["operator"],
                    sorted(normalized_term(c["statement"]) for c in group["conditions"]),
                ],
                group["operator"],
                rule["scope"],
                group["quotes"],
                operator=group["operator"],
                source_conditions=sorted(set(group["source_conditions"])),
            )
            add_edge(rid, gid, "HAS_CONDITION_GROUP", group["quotes"])
            for condition in group["conditions"]:
                cid = add_node(
                    "Condition",
                    [rid, normalized_term(condition["statement"])],
                    condition["statement"],
                    rule["scope"],
                    condition["quotes"],
                )
                add_edge(gid, cid, "HAS_CONDITION", condition["quotes"])
        for exception in rule["exceptions"]:
            eid = add_node(
                "Exception",
                [rid, normalized_term(exception["statement"])],
                exception["statement"],
                rule["scope"],
                exception["quotes"],
            )
            add_edge(rid, eid, "HAS_EXCEPTION", exception["quotes"])
    for node in nodes.values():
        for evidence_id in sorted({quote["evidence_id"] for quote in node["quotes"]}):
            add_edge(
                node["id"],
                evidence_id,
                "SUPPORTED_BY",
                [quote for quote in node["quotes"] if quote["evidence_id"] == evidence_id],
            )
    return {
        "schema_version": 1,
        "nodes": sorted(nodes.values(), key=lambda item: item["id"]),
        "edges": sorted(edges.values(), key=lambda item: item["id"]),
        "fact_ids": sorted(facts),
        "owned_evidence_ids": payload["owned_evidence_ids"],
        "context_evidence_ids": payload["context_evidence_ids"],
        "findings": [],
    }


def has_semantic_tables(connection) -> bool:
    return bool(
        connection.execute("SELECT 1 FROM sqlite_master WHERE name='semantic_nodes'").fetchone()
    )


def merge_record(previous: dict, current: dict) -> dict:
    merged = {**previous, **current}
    merged["quotes"] = unique_quotes(previous.get("quotes", []) + current["quotes"])
    if "fact_ids" in previous or "fact_ids" in current:
        merged["fact_ids"] = sorted(
            set(previous.get("fact_ids", [])) | set(current.get("fact_ids", []))
        )
    if "source_conditions" in previous or "source_conditions" in current:
        merged["source_conditions"] = sorted(
            set(previous.get("source_conditions", [])) | set(current.get("source_conditions", []))
        )
    return merged


def semantic_structure_issues(
    nodes: list[dict], edges: list[dict], types: dict[str, str]
) -> list[str]:
    allowed = {
        "HAS_RULE": ("Topic", "Rule"),
        "HAS_CONDITION_GROUP": ("Rule", "ConditionGroup"),
        "HAS_CONDITION": ("ConditionGroup", "Condition"),
        "HAS_EXCEPTION": ("Rule", "Exception"),
        "EXPRESSES": ("Rule", "Assertion"),
    }
    semantic_types = {"Topic", "Rule", "ConditionGroup", "Condition", "Exception"}
    issues = []
    for node in nodes:
        if node["type"] not in semantic_types:
            issues.append(f"Unsupported semantic node type: {node['id']}")
        if node["type"] == "ConditionGroup" and node.get("operator") not in {
            "all",
            "any",
            "unspecified",
        }:
            issues.append(f"Invalid condition group operator: {node['id']}")
    for edge in edges:
        endpoints = (types.get(edge["source_id"]), types.get(edge["target_id"]))
        if edge["type"] == "SUPPORTED_BY":
            valid = endpoints[0] in semantic_types and endpoints[1] == "SourceSpan"
        else:
            valid = edge["type"] in allowed and endpoints == allowed[edge["type"]]
        if not valid:
            issues.append(f"Unsupported semantic relation or endpoint types: {edge['id']}")
    return issues


def publish_semantic_batch(
    graph: KnowledgeGraph, canonical: dict, batch_id: str, provenance: dict | None = None
) -> None:
    if canonical.get("findings"):
        raise ValueError("Cannot publish unresolved semantic findings")
    sources = {
        quote["evidence_id"]: graph.evidence(quote["evidence_id"])
        for record in canonical["nodes"] + canonical["edges"]
        for quote in record["quotes"]
    }
    sources = {key: value for key, value in sources.items() if value}
    issues = []
    with graph.connect() as connection:
        types = dict(connection.execute("SELECT id,type FROM nodes"))
    types.update({node["id"]: node["type"] for node in canonical["nodes"]})
    issues.extend(semantic_structure_issues(canonical["nodes"], canonical["edges"], types))
    for record in canonical["nodes"] + canonical["edges"]:
        if not record["quotes"]:
            issues.append(f"Semantic record has no source quotes: {record['id']}")
        issues.extend(quote_issues(record["quotes"], sources, record["id"]))
    if any(not graph.assertion(fid) for fid in canonical["fact_ids"]):
        issues.append("Semantic batch references facts missing from graph")
    if issues:
        raise ValueError("; ".join(issues))
    content_hash = digest(canonical)
    with graph.connect() as connection:
        connection.executescript(SEMANTIC_SCHEMA)
        existing = connection.execute(
            "SELECT content_hash FROM semantic_batches WHERE id=?", (batch_id,)
        ).fetchone()
        if existing:
            if existing[0] != content_hash:
                raise ValueError("Semantic batch identity reused with different content")
            return
        for node in canonical["nodes"]:
            connection.execute(
                "INSERT OR IGNORE INTO nodes VALUES (?,?,?,?)",
                (node["id"], node["type"], node["name"], node["scope"]),
            )
            graph._search(connection, node["id"], node["name"])
            previous = connection.execute(
                "SELECT payload FROM semantic_nodes WHERE id=?", (node["id"],)
            ).fetchone()
            record = merge_record(json.loads(previous[0]), node) if previous else node
            connection.execute(
                "INSERT OR REPLACE INTO semantic_nodes VALUES (?,?)",
                (node["id"], json.dumps(record, ensure_ascii=False)),
            )
        for edge in canonical["edges"]:
            previous = connection.execute(
                "SELECT payload FROM semantic_edges WHERE id=?", (edge["id"],)
            ).fetchone()
            record = merge_record(json.loads(previous[0]), edge) if previous else edge
            connection.execute(
                "INSERT OR REPLACE INTO semantic_edges VALUES (?,?,?,?,?)",
                (
                    edge["id"],
                    edge["source_id"],
                    edge["target_id"],
                    edge["type"],
                    json.dumps(record, ensure_ascii=False),
                ),
            )
            connection.execute(
                "INSERT OR IGNORE INTO edges VALUES (?,?,?,?,?)",
                (
                    edge["source_id"],
                    edge["target_id"],
                    edge["type"],
                    "verified_semantics",
                    edge["quotes"][0]["evidence_id"],
                ),
            )
        for kind, records in (("node", canonical["nodes"]), ("edge", canonical["edges"])):
            for record in records:
                for quote in record["quotes"]:
                    identifier = digest([kind, record["id"], quote])
                    connection.execute(
                        "INSERT OR IGNORE INTO semantic_quotes VALUES (?,?,?,?,?)",
                        (
                            identifier,
                            record["id"],
                            kind,
                            quote["evidence_id"],
                            json.dumps(quote, ensure_ascii=False),
                        ),
                    )
        connection.execute(
            "INSERT INTO semantic_batches VALUES (?,?,?,?)",
            (
                batch_id,
                content_hash,
                json.dumps(canonical, ensure_ascii=False),
                json.dumps(provenance or {}, ensure_ascii=False),
            ),
        )


def semantic_records(graph: KnowledgeGraph) -> tuple[list[dict], list[dict]]:
    with graph.connect() as connection:
        if not has_semantic_tables(connection):
            return [], []
        return tuple(
            [
                json.loads(row[0])
                for row in connection.execute(f"SELECT payload FROM {table} ORDER BY id")
            ]
            for table in ("semantic_nodes", "semantic_edges")
        )


def topic_register(graph: KnowledgeGraph) -> list[dict]:
    nodes, edges = semantic_records(graph)
    rules = {node["id"]: node for node in nodes if node["type"] == "Rule"}
    topics = []
    for node in nodes:
        if node["type"] == "Topic":
            topics.append(
                {
                    **node,
                    "rules": [
                        rules[edge["target_id"]]
                        for edge in edges
                        if edge["source_id"] == node["id"] and edge["type"] == "HAS_RULE"
                    ],
                }
            )
    return topics


def source_citation(quote: dict, source: dict) -> dict:
    def position(offset: int) -> tuple[int, int]:
        prefix = source["text"][:offset]
        line = source["start_line"] + prefix.count("\n")
        previous_newline = prefix.rfind("\n")
        column = (
            offset - previous_newline
            if previous_newline >= 0
            else source.get("start_column", 1) + offset
        )
        return line, column

    start_line, start_column = position(quote["start"])
    end_line, end_column = position(quote["end"])
    source_locator = source.get("locator")
    absolute_start = source.get("source_start_char")
    locator = source_locator
    if absolute_start is not None:
        locator = {
            "kind": "characters",
            "start": absolute_start + quote["start"],
            "end": absolute_start + quote["end"],
        }
    return {
        **quote,
        "path": source["path"],
        "file_hash": source["file_hash"],
        "start_line": start_line,
        "start_column": start_column,
        "end_line": end_line,
        "end_column": end_column,
        "locator": locator,
        "source_locator": source_locator,
        "quote_locator": {"kind": "characters", "start": quote["start"], "end": quote["end"]},
        "quote_locator_basis": "evidence_text",
    }


def semantic_bundle(graph: KnowledgeGraph, node_ids: list[str]) -> dict:
    nodes, edges = semantic_records(graph)
    selected = set(node_ids)
    structural = {"HAS_RULE", "HAS_CONDITION_GROUP", "HAS_CONDITION", "HAS_EXCEPTION", "EXPRESSES"}
    while True:
        expanded = selected | {
            edge["target_id"]
            for edge in edges
            if edge["source_id"] in selected and edge["type"] in structural
        }
        expanded |= {
            edge["source_id"]
            for edge in edges
            if edge["target_id"] in selected and edge["type"] == "EXPRESSES"
        }
        if expanded == selected:
            break
        selected = expanded
    selected_nodes = [node for node in nodes if node["id"] in selected]
    selected_edges = [
        edge
        for edge in edges
        if edge["source_id"] in selected
        and (edge["target_id"] in selected or edge["type"] == "SUPPORTED_BY")
    ]
    quotes = unique_quotes(
        [quote for record in selected_nodes + selected_edges for quote in record["quotes"]]
    )
    evidence = {quote["evidence_id"]: graph.evidence(quote["evidence_id"]) for quote in quotes}
    resolved = []
    for quote in quotes:
        source = evidence[quote["evidence_id"]]
        resolved.append({**source_citation(quote, source), "source": source})
    facts = [fact for identifier in sorted(selected) if (fact := graph.assertion(identifier))]
    return {
        "nodes": selected_nodes,
        "edges": selected_edges,
        "assertions": facts,
        "quotes": resolved,
        "evidence": [evidence[key] for key in sorted(evidence)],
    }


def semantic_quality_report(graph: KnowledgeGraph) -> dict:
    nodes, edges = semantic_records(graph)
    issues = graph.verify()
    with graph.connect() as connection:
        facts = {row[0] for row in connection.execute("SELECT id FROM assertions")}
        known = {row[0] for row in connection.execute("SELECT id FROM nodes")}
        types = dict(connection.execute("SELECT id,type FROM nodes"))
        source_ids = {row[0] for row in connection.execute("SELECT id FROM evidence")}
        batches = []
        if has_semantic_tables(connection):
            batches = [
                json.loads(row[0])
                for row in connection.execute("SELECT payload FROM semantic_batches ORDER BY id")
            ]
    allocated = {edge["target_id"] for edge in edges if edge["type"] == "EXPRESSES"}
    issues.extend(semantic_structure_issues(nodes, edges, types))
    allocations = Counter(edge["target_id"] for edge in edges if edge["type"] == "EXPRESSES")
    issues.extend(
        f"Fact has multiple semantic rules: {fid}"
        for fid, count in allocations.items()
        if count > 1
    )
    missing = sorted(facts - allocated)
    issues.extend(f"Fact has no semantic rule: {identifier}" for identifier in missing)
    sources = {}
    for record in nodes + edges:
        if not record.get("quotes"):
            issues.append(f"Semantic record has no exact quotation: {record['id']}")
        for quote in record["quotes"]:
            if quote["evidence_id"] not in sources:
                source = graph.evidence(quote["evidence_id"])
                if source:
                    sources[quote["evidence_id"]] = source
        issues.extend(quote_issues(record["quotes"], sources, record["id"]))
    for edge in edges:
        if edge["source_id"] not in known or edge["target_id"] not in known:
            issues.append(f"Semantic relation has missing endpoint: {edge['id']}")
    ownership = Counter(eid for batch in batches for eid in batch["owned_evidence_ids"])
    issues.extend(
        f"Source has multiple semantic batch owners: {eid}"
        for eid, count in ownership.items()
        if count > 1
    )
    counts = Counter(node["type"] for node in nodes)
    return {
        "schema_version": 1,
        "graph_hash": digest({"nodes": nodes, "edges": edges}),
        "accepted": not issues,
        "counts": dict(counts),
        "semantic_edges": len(edges),
        "fact_count": len(facts),
        "allocated_fact_count": len(allocated),
        "unallocated_fact_ids": missing,
        "source_count": len(source_ids),
        "quoted_source_count": len(sources),
        "owned_source_count": len(ownership),
        "batch_count": len(batches),
        "quote_count": len(unique_quotes([q for r in nodes + edges for q in r["quotes"]])),
        "findings": sorted(set(issues)),
        "citations": [
            source_citation(quote, sources[quote["evidence_id"]])
            for quote in unique_quotes([q for record in nodes + edges for q in record["quotes"]])
            if quote["evidence_id"] in sources
        ],
        "verification": (
            "Exact provenance and structure; semantic correctness requires independent model audit"
        ),
    }
