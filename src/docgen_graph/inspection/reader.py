import json
import re
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from docgen_graph.storage import digest

GRAPH_TABLES = (
    "nodes",
    "edges",
    "assertions",
    "support",
    "evidence",
    "assertion_metadata",
    "evidence_metadata",
    "verified_relations",
    "graph_metadata",
    "analysis_provenance",
    "evidence_service_state",
)
HASH = re.compile(r"[a-f0-9]{64}")
SECRET_KEY = re.compile(
    r"(?:api[_-]?key|access[_-]?token|refresh[_-]?token|authorization|password|"
    r"client[_-]?secret|private[_-]?key|credential|cookie|secret)",
    re.I,
)
SECRET_TEXT = re.compile(
    r"(?i)(?:bearer\s+[a-z0-9._~+/=-]+|sk-[a-z0-9_-]{12,}|"
    r"AIza[a-z0-9_-]{25,}|(?:api[_-]?key|password|access[_-]?token|"
    r"client[_-]?secret)\s*[:=]\s*[\"']?[^\s,;\"']+|"
    r"gh[pousr]_[a-z0-9]{20,}|github_pat_[a-z0-9_]{20,}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----)"
)
FORBIDDEN = {".env", "auth.json", "credentials.json", "config.toml"}


def timestamp() -> str:
    return datetime.now(UTC).isoformat()


def safe_path(root: Path, relative: str | Path) -> Path:
    candidate = root / relative
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("Path leaves the approved input root")
    if any(
        part.casefold() in FORBIDDEN or part.casefold().startswith(".env.")
        for part in candidate.parts
    ):
        raise ValueError("Credential or runtime configuration files cannot be exported")
    return resolved


def redact(value, counts: dict):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if SECRET_KEY.search(key) and item:
                result[key] = "[REDACTED]"
                counts["fields"] += 1
            else:
                result[key] = redact(item, counts)
        return result
    if isinstance(value, list):
        return [redact(item, counts) for item in value]
    if isinstance(value, str):
        result, number = SECRET_TEXT.subn("[REDACTED]", value)
        counts["strings"] += number
        return result
    return value


def safe_sql_value(value, column=""):
    if isinstance(value, bytes):
        try:
            decoded = json.loads(value)
            return {"encoding": "json", "size": len(value), "value": decoded}
        except (ValueError, UnicodeError):
            return {
                "encoding": "opaque",
                "size": len(value),
                "sha256": digest(value),
                "reason": "Binary payload is not deserialized or executed",
            }
    if column in {"payload", "metadata", "usage", "pricing"} and isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            pass
    return value


class RunReader:
    def __init__(self, workspace: Path, run_id: str, ledger: Path | None = None):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,100}", run_id):
            raise ValueError("Invalid run identifier")
        self.workspace = workspace.resolve()
        if not self.workspace.is_dir():
            raise ValueError("Artifact workspace does not exist or cannot be read")
        self.run = safe_path(self.workspace, Path("runs") / run_id)
        if not self.run.is_dir():
            raise ValueError("Requested run does not exist")
        self.run_id = run_id
        self.ledger = ledger.resolve() if ledger else None
        self.diagnostics = []
        self.artifacts = {}
        self.graph_revisions = set()
        self.trace_links = []

    def warn(self, source, message, severity="warning", affected_ids=None):
        self.diagnostics.append(
            {
                "severity": severity,
                "source": str(source),
                "message": message,
                "affected_ids": affected_ids or [],
                "recovery": "Inspect the recorded input; re-export after repair",
            }
        )

    def read_file(self, root: Path, relative: str | Path, expected=None):
        source = str(relative)
        try:
            path = safe_path(root, relative)
            content = path.read_bytes()
        except (OSError, ValueError) as error:
            self.warn(source, f"Unavailable file: {type(error).__name__}")
            return {"path": source, "status": "unavailable"}
        actual = digest(content)
        status = "verified" if expected == actual else "read"
        if expected and expected != actual:
            status = "corrupt"
            self.warn(source, "Recorded SHA-256 does not match file bytes", "error")
        record = {"path": source, "status": status, "sha256": actual, "size": len(content)}
        try:
            text = content.decode("utf-8")
            if "\x00" in text:
                raise UnicodeError()
            try:
                record.update(format="json", value=json.loads(text))
            except ValueError:
                record.update(format="text", value=text)
        except UnicodeError:
            record.update(format="binary", preview="Unavailable; original bytes are not embedded")
        return record

    def database(self, path: Path, tables: tuple, selected_run=False) -> dict:
        result = {}
        if not path.is_file():
            self.warn(path.name, "Database is not available")
            return result
        try:
            with TemporaryDirectory(prefix="docgen-inspection-") as temporary:
                copied = Path(temporary) / "snapshot.sqlite"
                signatures = {}
                for suffix in ("", "-wal", "-shm"):
                    source = safe_path(path.parent, path.name + suffix)
                    if source.is_file():
                        content = source.read_bytes()
                        signatures[suffix] = digest(content)
                        Path(str(copied) + suffix).write_bytes(content)
                for suffix, signature in signatures.items():
                    source = safe_path(path.parent, path.name + suffix)
                    if digest(source.read_bytes()) != signature:
                        self.warn(path.name, "Database changed during snapshot capture", "error")
                        return {}
                with closing(sqlite3.connect(copied.as_uri() + "?mode=ro", uri=True)) as db:
                    db.row_factory = sqlite3.Row
                    db.execute("PRAGMA query_only=ON")
                    db.execute("BEGIN")
                    available = {
                        row[0]
                        for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    }
                    for table in tables:
                        if table not in available:
                            continue
                        columns = {row[1] for row in db.execute(f'PRAGMA table_info("{table}")')}
                        where = ""
                        parameters = ()
                        if selected_run:
                            column = "run_id" if "run_id" in columns else "thread_id"
                            if column not in columns:
                                self.warn(table, "Cannot bind table rows to selected run")
                                continue
                            where = f' WHERE "{column}"=?'
                            parameters = (self.run_id,)
                        rows = [
                            dict(row)
                            for row in db.execute(f'SELECT * FROM "{table}"{where}', parameters)
                        ]
                        converted = [
                            {key: safe_sql_value(value, key) for key, value in row.items()}
                            for row in rows
                        ]
                        result[table] = sorted(
                            converted,
                            key=lambda row: json.dumps(row, sort_keys=True, ensure_ascii=False),
                        )
        except (OSError, ValueError, sqlite3.Error) as error:
            self.warn(path.name, f"Unreadable database: {type(error).__name__}", "error")
        return result

    def graph(self, identifier: str, path: Path, manifest=None) -> dict:
        tables = self.database(path, GRAPH_TABLES)
        ids = {row["id"] for row in tables.get("nodes", [])}
        for edge in tables.get("edges", []):
            missing = [edge[key] for key in ("source_id", "target_id") if edge[key] not in ids]
            if missing:
                self.warn(identifier, "Stored edge has missing endpoints", affected_ids=missing)
        enriched = {}
        for base_name, meta_name in (
            ("assertions", "assertion_metadata"),
            ("evidence", "evidence_metadata"),
        ):
            metadata = {row["id"]: row.get("payload", {}) for row in tables.get(meta_name, [])}
            enriched[base_name] = []
            for row in tables.get(base_name, []):
                extra = metadata.get(row["id"], {})
                if not isinstance(extra, dict):
                    self.warn(identifier, "Invalid metadata payload", affected_ids=[row["id"]])
                    extra = {}
                comparable = dict(row)
                for key in ("conditions", "exceptions"):
                    if isinstance(comparable.get(key), str):
                        try:
                            comparable[key] = json.loads(comparable[key])
                        except ValueError:
                            pass
                conflicts = {
                    key: [value, extra[key]]
                    for key, value in comparable.items()
                    if key in extra and extra[key] != value
                }
                if conflicts:
                    self.warn(
                        identifier, "Base and metadata fields differ", affected_ids=[row["id"]]
                    )
                enriched[base_name].append(
                    {**extra, **comparable, "metadata": extra, "metadata_conflicts": conflicts}
                )
        return {
            "id": identifier,
            "kind": "current" if identifier == "current" else "frozen",
            "manifest": manifest,
            "tables": tables,
            "enriched": enriched,
            "missing_tables": [name for name in GRAPH_TABLES if name not in tables],
        }

    def references(self, value, origin: str, key=""):
        if isinstance(value, dict):
            for name, item in value.items():
                self.references(item, origin, name)
        elif isinstance(value, list):
            for item in value:
                self.references(item, origin, key)
        elif isinstance(value, str):
            if key == "candidate_ref" and HASH.fullmatch(value):
                self.trace_links.append(
                    {"origin": origin, "field": key, "target": value, "kind": "candidate_reference"}
                )
                return
            if key in ("graph_revision", "graph_version") and HASH.fullmatch(value):
                self.graph_revisions.add(value)
            if HASH.fullmatch(value):
                path = Path("objects") / value[:2] / value
                try:
                    exists = safe_path(self.workspace, path).is_file()
                except ValueError:
                    self.warn(origin, "Unsafe object reference was not followed", "error")
                    return
                if key.endswith("_ref") or exists:
                    self.trace_links.append(
                        {
                            "origin": origin,
                            "field": key,
                            "target": value,
                            "kind": "artifact_reference",
                        }
                    )
                    if value not in self.artifacts:
                        record = self.read_file(self.workspace, path, value)
                        self.artifacts[value] = record
                        if record.get("format") == "json":
                            self.references(record["value"], value)
            elif key.endswith("_ref") and value:
                self.warn(origin, f"Non-content-addressed reference in {key}; not followed")

    def stages(self) -> list:
        records = []
        directories = [
            path for path in self.run.glob("step*") if re.fullmatch(r"step\d+", path.name)
        ]
        for directory in sorted(directories, key=lambda path: int(path.name[4:])):
            if not re.fullmatch(r"step\d+", directory.name):
                continue
            try:
                safe_path(self.run, directory.relative_to(self.run))
            except ValueError:
                self.warn(directory.name, "Unsafe stage directory")
                continue
            if (directory / "manifest.json").is_file():
                manifest = self.read_file(
                    self.run, directory.relative_to(self.run) / "manifest.json"
                )
                records.append(
                    {
                        "id": directory.name,
                        "step": directory.name,
                        "manifest": manifest,
                        "kind": "stage_inventory",
                    }
                )
            for pattern in ("revisions/*/manifest.json", "items/*/revisions/*/manifest.json"):
                for path in sorted(directory.glob(pattern)):
                    relative = path.relative_to(self.run)
                    manifest = self.read_file(self.run, relative)
                    data = manifest.get("value", {})
                    if not isinstance(data, dict):
                        data = {}
                    result = self.read_file(
                        self.run, relative.parent / "result.json", data.get("result_hash")
                    )
                    value = result.get("value", {})
                    if isinstance(value, dict) and data.get("hash"):
                        content = {
                            key: value.get(key) for key in ("stage", "item", "inputs", "outputs")
                        }
                        if digest(content) != data["hash"]:
                            result["status"] = "corrupt"
                            self.warn(relative, "Stage logical content hash mismatch", "error")
                    identifier = relative.parent.as_posix()
                    record = {
                        "id": identifier,
                        "step": directory.name,
                        "manifest": manifest,
                        "result": result,
                    }
                    records.append(record)
                    self.references(result.get("value"), identifier)
        return records

    def events(self) -> list:
        path = safe_path(self.run, "events.jsonl")
        if not path.is_file():
            self.warn("events.jsonl", "Event history is not available")
            return []
        events = []
        for line_number, line in enumerate(path.read_bytes().splitlines(), 1):
            try:
                value = json.loads(line)
            except (ValueError, UnicodeError):
                self.warn(f"events.jsonl:{line_number}", "Malformed or partial JSONL record")
                continue
            events.append({"line": line_number, "record": value})
            self.references(value, f"event:{line_number}")
        return events

    def candidates(self) -> list:
        candidates = []
        for manifest_path in sorted(self.run.glob("candidates/*/candidate-manifest.json")):
            relative = manifest_path.relative_to(self.run)
            manifest = self.read_file(self.run, relative)
            files = {}
            values = manifest.get("value", {})
            if isinstance(values, dict):
                try:
                    candidate_root = safe_path(self.run, relative.parent)
                except ValueError:
                    self.warn(relative, "Unsafe candidate directory was not followed", "error")
                    continue
                for filename, expected in sorted(values.items()):
                    files[filename] = self.read_file(candidate_root, filename, expected)
                    self.references(files[filename].get("value"), relative.parent.as_posix())
            candidates.append(
                {"id": manifest_path.parent.name, "manifest": manifest, "files": files}
            )
        return candidates

    def read(self) -> dict:
        started = timestamp()
        manifest = self.read_file(self.run, "run-manifest.json")
        stages = self.stages()
        events = self.events()
        candidates = self.candidates()
        run_files = {}
        for name in (
            "graph-manifest.json",
            "coverage.json",
            "source-coverage.json",
            "audit.json",
            "release.json",
            "decisions.md",
            "exclusions.md",
        ):
            if safe_path(self.run, name).is_file():
                run_files[name] = self.read_file(self.run, name)
                value = run_files[name].get("value", {})
                self.references(value, name)
                if name == "graph-manifest.json" and isinstance(value, dict):
                    revision = value.get("revision", "")
                    if HASH.fullmatch(revision):
                        self.graph_revisions.add(revision)
        for path in sorted(self.run.glob("releases/*.json")):
            name = path.relative_to(self.run).as_posix()
            run_files[name] = self.read_file(self.run, name)
            self.references(run_files[name].get("value"), name)
        graphs = [
            self.graph(
                "current", safe_path(self.run, "graph.sqlite"), run_files.get("graph-manifest.json")
            )
        ]
        for revision in sorted(self.graph_revisions):
            directory = safe_path(self.workspace, Path("graphs") / revision)
            graphs.append(
                self.graph(
                    revision,
                    safe_path(directory, "graph.sqlite"),
                    self.read_file(directory, "manifest.json"),
                )
            )
        for graph in graphs:
            self.references(graph["tables"], f"graph:{graph['id']}")
        checkpoints = self.database(
            safe_path(self.workspace, "checkpoints.sqlite"),
            ("checkpoints", "writes"),
            selected_run=True,
        )
        costs = self.database(self.ledger, ("charges",), selected_run=True) if self.ledger else {}
        if not self.ledger:
            self.warn("costs", "No ledger supplied; cost data is not available")
        result = {
            "schema_version": 1,
            "capture": {
                "started": started,
                "finished": timestamp(),
                "mode": "offline read-only export",
                "refresh": "Re-export to refresh",
            },
            "run_id": self.run_id,
            "run_manifest": manifest,
            "graphs": graphs,
            "stages": stages,
            "events": events,
            "checkpoints": checkpoints,
            "artifacts": self.artifacts,
            "candidates": candidates,
            "run_files": run_files,
            "costs": costs,
            "trace_links": self.trace_links,
            "diagnostics": self.diagnostics,
        }
        counts = {"fields": 0, "strings": 0}
        result = redact(result, counts)
        result["capture"]["redactions"] = counts
        return result
