import json
import re
import sqlite3
from collections import deque
from contextlib import contextmanager
from pathlib import Path

from docgen_graph.evidence_contracts import FactRecord
from docgen_graph.storage import digest

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY, kind TEXT NOT NULL, path TEXT NOT NULL, file_hash TEXT NOT NULL,
    start_line INTEGER NOT NULL, end_line INTEGER NOT NULL, heading TEXT NOT NULL,
    text TEXT NOT NULL, role TEXT NOT NULL, label TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY, type TEXT NOT NULL, name TEXT NOT NULL, scope TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS assertions (
    id TEXT PRIMARY KEY REFERENCES nodes(id), statement TEXT NOT NULL,
    subject TEXT NOT NULL, predicate TEXT NOT NULL, scope TEXT NOT NULL,
    modality TEXT NOT NULL, conditions TEXT NOT NULL, exceptions TEXT NOT NULL,
    source_role TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS support (
    assertion_id TEXT NOT NULL REFERENCES assertions(id),
    evidence_id TEXT NOT NULL REFERENCES evidence(id),
    PRIMARY KEY(assertion_id, evidence_id)
);
CREATE TABLE IF NOT EXISTS edges (
    source_id TEXT NOT NULL REFERENCES nodes(id), target_id TEXT NOT NULL REFERENCES nodes(id),
    type TEXT NOT NULL, method TEXT NOT NULL, evidence_id TEXT REFERENCES evidence(id),
    PRIMARY KEY(source_id, target_id, type, method)
);
CREATE VIRTUAL TABLE IF NOT EXISTS search USING fts5(id UNINDEXED, text);
CREATE TABLE IF NOT EXISTS indexed_search (id TEXT PRIMARY KEY);
"""


def normalized_assertion(raw: dict, allowed: set[str]) -> dict:
    statement = str(raw.get("statement", "")).strip()
    evidence_ids = [str(value) for value in raw.get("evidence_ids", [])]
    if not statement or not evidence_ids or any(value not in allowed for value in evidence_ids):
        raise ValueError("Assertion has missing statement or invalid evidence")

    def terms(value) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        return [str(value)] if value else []

    record = {
        "statement": statement,
        "evidence_ids": sorted(set(evidence_ids)),
        "subject": str(raw.get("subject") or "unspecified"),
        "predicate": str(raw.get("predicate") or "describes"),
        "scope": str(raw.get("scope") or "selected sources"),
        "modality": str(raw.get("modality") or "descriptive"),
        "conditions": terms(raw.get("conditions")),
        "exceptions": terms(raw.get("exceptions")),
        "source_role": str(raw.get("source_role") or "source"),
    }
    enriched = FactRecord.model_validate({**raw, **record, "id": "pending"}).model_dump()
    record.update(
        {key: value for key, value in enriched.items() if key not in {"id", "schema_version"}}
    )
    record["id"] = digest(record)[:24]
    return record


class KnowledgeGraph:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def add_evidence(self, spans: list[dict]) -> None:
        with self.connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS evidence_metadata "
                "(id TEXT PRIMARY KEY REFERENCES evidence(id), payload TEXT NOT NULL)"
            )
            code = connection.execute("SELECT COUNT(*) FROM evidence WHERE kind='code'").fetchone()[
                0
            ]
            docs = connection.execute(
                "SELECT COUNT(*) FROM evidence WHERE kind!='code'"
            ).fetchone()[0]
            for span in spans:
                if connection.execute(
                    "SELECT 1 FROM evidence WHERE id=?", (span["id"],)
                ).fetchone():
                    continue
                if span["kind"] == "code":
                    code += 1
                    label = f"C{code}"
                else:
                    docs += 1
                    label = f"D{docs}"
                connection.execute(
                    "INSERT OR IGNORE INTO evidence VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        span["id"],
                        span["kind"],
                        span["path"],
                        span["file_hash"],
                        span["start_line"],
                        span["end_line"],
                        span["heading"],
                        span["text"],
                        span["role"],
                        label,
                    ),
                )
                self._search(connection, span["id"], span["text"])
                connection.execute(
                    "INSERT OR IGNORE INTO evidence_metadata VALUES (?,?)",
                    (span["id"], json.dumps(span, ensure_ascii=False)),
                )
                connection.execute(
                    "INSERT OR IGNORE INTO nodes VALUES (?,?,?,?)",
                    (span["id"], "SourceSpan", span["path"], ""),
                )

    def add_structure(self, inventory: dict) -> None:
        spans_by_path = {}
        for span in inventory["spans"]:
            if span["kind"] == "code":
                spans_by_path.setdefault(span["path"], []).append(span)
        with self.connect() as connection:
            for path, metadata in inventory["analysis"].items():
                component_id = digest(["component", path])[:24]
                connection.execute(
                    "INSERT OR IGNORE INTO nodes VALUES (?,?,?,?)",
                    (component_id, "Component", path, path),
                )
                for span in spans_by_path.get(path, []):
                    connection.execute(
                        "INSERT OR IGNORE INTO edges VALUES (?,?,?,?,?)",
                        (component_id, span["id"], "CONTAINS", "inventory", span["id"]),
                    )
                for symbol in metadata["symbols"]:
                    symbol_id = digest(["symbol", path, symbol["name"], symbol["line"]])[:24]
                    connection.execute(
                        "INSERT OR IGNORE INTO nodes VALUES (?,?,?,?)",
                        (symbol_id, "Symbol", symbol["name"], path),
                    )
                    owner = next(
                        (
                            span
                            for span in spans_by_path.get(path, [])
                            if span["start_line"] <= symbol["line"] <= span["end_line"]
                        ),
                        None,
                    )
                    if owner:
                        connection.execute(
                            "INSERT OR IGNORE INTO edges VALUES (?,?,?,?,?)",
                            (component_id, symbol_id, "DEFINES", "python_ast", owner["id"]),
                        )
                        connection.execute(
                            "INSERT OR IGNORE INTO edges VALUES (?,?,?,?,?)",
                            (symbol_id, owner["id"], "SUPPORTED_BY", "python_ast", owner["id"]),
                        )
                for imported in metadata["imports"]:
                    target_id = digest(["import", imported["name"]])[:24]
                    connection.execute(
                        "INSERT OR IGNORE INTO nodes VALUES (?,?,?,?)",
                        (target_id, "Component", imported["name"], "imported name only"),
                    )
                    owner = next(
                        (
                            span
                            for span in spans_by_path.get(path, [])
                            if span["start_line"] <= imported["line"] <= span["end_line"]
                        ),
                        None,
                    )
                    connection.execute(
                        "INSERT OR IGNORE INTO edges VALUES (?,?,?,?,?)",
                        (
                            component_id,
                            target_id,
                            "IMPORTS",
                            "python_ast",
                            owner["id"] if owner else None,
                        ),
                    )

    @staticmethod
    def _search(connection, identifier: str, content: str) -> None:
        if connection.execute("SELECT 1 FROM indexed_search WHERE id=?", (identifier,)).fetchone():
            return
        connection.execute("INSERT INTO search (id,text) VALUES (?,?)", (identifier, content))
        connection.execute("INSERT INTO indexed_search VALUES (?)", (identifier,))

    def add_assertions(self, assertions: list[dict]) -> None:
        with self.connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS assertion_metadata "
                "(id TEXT PRIMARY KEY REFERENCES assertions(id), payload TEXT NOT NULL)"
            )
            for item in assertions:
                connection.execute(
                    "INSERT OR IGNORE INTO nodes VALUES (?,?,?,?)",
                    (item["id"], "Assertion", item["subject"], item["scope"]),
                )
                connection.execute(
                    "INSERT OR IGNORE INTO assertions VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        item["id"],
                        item["statement"],
                        item["subject"],
                        item["predicate"],
                        item["scope"],
                        item["modality"],
                        json.dumps(item["conditions"], ensure_ascii=False),
                        json.dumps(item["exceptions"], ensure_ascii=False),
                        item["source_role"],
                    ),
                )
                self._search(
                    connection,
                    item["id"],
                    " ".join(
                        [
                            item["subject"],
                            item["predicate"],
                            item["statement"],
                            " ".join(item["conditions"]),
                            " ".join(item["exceptions"]),
                        ]
                    ),
                )
                metadata = FactRecord.model_validate(item).model_dump()
                connection.execute(
                    "INSERT OR IGNORE INTO assertion_metadata VALUES (?,?)",
                    (item["id"], json.dumps(metadata, ensure_ascii=False)),
                )
                for evidence_id in item["evidence_ids"]:
                    connection.execute(
                        "INSERT OR IGNORE INTO support VALUES (?,?)", (item["id"], evidence_id)
                    )
                    connection.execute(
                        "INSERT OR IGNORE INTO edges VALUES (?,?,?,?,?)",
                        (item["id"], evidence_id, "SUPPORTED_BY", "extracted", evidence_id),
                    )
            subjects = {}
            for row in connection.execute("SELECT id,subject,scope FROM assertions"):
                key = (row["subject"].casefold(), row["scope"].casefold())
                subjects.setdefault(key, []).append(row["id"])
            for matches in subjects.values():
                for first, second in zip(matches, matches[1:], strict=False):
                    connection.execute(
                        "INSERT OR IGNORE INTO edges VALUES (?,?,?,?,NULL)",
                        (first, second, "DESCRIBES", "exact_subject_scope"),
                    )

    def verify(self) -> list[str]:
        with self.connect() as connection:
            issues = [
                f"Foreign key violation: {tuple(row)}"
                for row in connection.execute("PRAGMA foreign_key_check")
            ]
            for row in connection.execute(
                "SELECT a.id FROM assertions a LEFT JOIN support s ON s.assertion_id=a.id "
                "WHERE s.assertion_id IS NULL"
            ):
                issues.append(f"Assertion lacks original evidence: {row['id']}")
            for row in connection.execute(
                "SELECT e.source_id,e.target_id,e.type FROM edges e "
                "LEFT JOIN evidence v ON v.id=e.evidence_id "
                "WHERE e.evidence_id IS NOT NULL AND v.id IS NULL"
            ):
                issues.append(f"Edge lacks evidence: {tuple(row)}")
        return issues

    def conflict_candidates(self) -> list[dict]:
        candidates = []
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT a.id,a.subject,a.predicate,a.scope,a.statement,e.kind "
                "FROM assertions a JOIN support s ON s.assertion_id=a.id "
                "JOIN evidence e ON e.id=s.evidence_id"
            ).fetchall()
        groups = {}
        for row in rows:
            key = (row["subject"].casefold(), row["predicate"].casefold(), row["scope"].casefold())
            groups.setdefault(key, {}).setdefault(row["kind"], []).append(dict(row))
        for key, roles in groups.items():
            if "code" not in roles or "docs" not in roles:
                continue
            for code in roles["code"][:10]:
                for doc in roles["docs"][:10]:
                    if code["statement"].casefold() != doc["statement"].casefold():
                        candidates.append(
                            {
                                "subject": key[0],
                                "predicate": key[1],
                                "scope": key[2],
                                "code_id": code["id"],
                                "document_id": doc["id"],
                                "status": "candidate",
                            }
                        )
        return candidates

    def evidence(self, identifier: str) -> dict | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM evidence WHERE id=? OR label=?", (identifier, identifier)
            ).fetchone()
            if not row:
                return None
            item = dict(row)
            if connection.execute(
                "SELECT 1 FROM sqlite_master WHERE name='evidence_metadata'"
            ).fetchone():
                metadata = connection.execute(
                    "SELECT payload FROM evidence_metadata WHERE id=?", (item["id"],)
                ).fetchone()
                if metadata:
                    item.update(json.loads(metadata[0]))
            return item

    def assertion(self, identifier: str) -> dict | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM assertions WHERE id=?", (identifier,)
            ).fetchone()
            if not row:
                return None
            item = dict(row)
            item["conditions"] = json.loads(item["conditions"])
            item["exceptions"] = json.loads(item["exceptions"])
            item["evidence_ids"] = [
                record[0]
                for record in connection.execute(
                    "SELECT evidence_id FROM support WHERE assertion_id=?", (identifier,)
                )
            ]
            has_metadata = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE name='assertion_metadata'"
            ).fetchone()
            if has_metadata:
                extra = connection.execute(
                    "SELECT payload FROM assertion_metadata WHERE id=?", (identifier,)
                ).fetchone()
                if extra:
                    item.update(json.loads(extra[0]))
            item = FactRecord.model_validate(item).model_dump()
            return item

    def retrieve(
        self, queries: list[str], mandatory: list[str], hops: int = 2, optional_limit: int = 40
    ) -> dict:
        seeds = []
        with self.connect() as connection:
            for query in queries:
                terms = re.findall(r"[\w-]{3,}", query.lower())[:8]
                if not terms:
                    continue
                expression = " OR ".join('"' + term.replace('"', "") + '"' for term in terms)
                try:
                    seeds.extend(
                        row[0]
                        for row in connection.execute(
                            "SELECT id FROM search WHERE search MATCH ? ORDER BY rank LIMIT 12",
                            (expression,),
                        )
                    )
                except sqlite3.OperationalError:
                    continue
            selected = set(mandatory)
            seen = set(seeds) | selected
            queue = deque((seed, 0) for seed in seen)
            traversed = []
            while queue and len(seen) < optional_limit + len(mandatory):
                node, depth = queue.popleft()
                if depth >= hops:
                    continue
                for row in connection.execute(
                    "SELECT target_id,type FROM edges WHERE source_id=? "
                    "UNION SELECT source_id,type FROM edges WHERE target_id=?",
                    (node, node),
                ):
                    target = row[0]
                    traversed.append({"from": node, "to": target, "type": row[1]})
                    if target not in seen:
                        seen.add(target)
                        queue.append((target, depth + 1))
            closure = set(mandatory)
            required = deque(mandatory)
            while required:
                node = required.popleft()
                for row in connection.execute(
                    "SELECT target_id FROM edges WHERE source_id=? "
                    "AND type IN ('DESCRIBES','QUALIFIES','CONTRADICTS') "
                    "UNION SELECT source_id FROM edges WHERE target_id=? "
                    "AND type IN ('DESCRIBES','QUALIFIES','CONTRADICTS')",
                    (node, node),
                ):
                    target = row[0]
                    if target not in closure:
                        closure.add(target)
                        required.append(target)
            selected.update(identifier for identifier in seen if self.assertion(identifier))
            selected.update(closure)
            assertions = [self.assertion(identifier) for identifier in sorted(selected)]
            assertions = [item for item in assertions if item]
            evidence_ids = {eid for item in assertions for eid in item["evidence_ids"]}
            evidence = (
                [
                    dict(row)
                    for row in connection.execute(
                        "SELECT * FROM evidence WHERE id IN ("
                        + ",".join("?" for _ in evidence_ids)
                        + ")",
                        tuple(evidence_ids),
                    )
                ]
                if evidence_ids
                else []
            )
        return {
            "queries": queries,
            "mandatory": mandatory,
            "seed_matches": sorted(set(seeds)),
            "traversed_edges": traversed,
            "assertions": assertions,
            "evidence": evidence,
            "limits_reached": bool(queue),
            "mandatory_closure": sorted(closure),
            "context_characters": sum(len(item["text"]) for item in evidence),
            "policy": "lexical-two-hop-v1",
        }
