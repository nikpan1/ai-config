import hashlib
import json
import logging
import os
import re
import sqlite3
import tempfile
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path

from filelock import FileLock, Timeout
from pydantic import BaseModel


def serializable(value):
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Path):
        return str(value)
    raise TypeError(type(value).__name__)


def encode(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=serializable)


def digest(value) -> str:
    raw = value if isinstance(value, bytes) else encode(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def now() -> str:
    return datetime.now(UTC).isoformat()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def file_digest(path: Path):
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def atomic_write(path: Path, content: str | bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = content.encode("utf-8") if isinstance(content, str) else content
    descriptor, name = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def write_json(path: Path, value):
    atomic_write(path, encode(value) + "\n")


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            for row in rows:
                stream.write(encode(row) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


class Artifacts:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, value, kind="artifact") -> str:
        ref = f"objects/{kind}-{digest(value)}.json"
        path = self.path(ref)
        if not path.exists():
            write_json(path, value)
        elif read_json(path) != json.loads(encode(value)):
            raise ValueError("Immutable artifact was modified")
        return ref

    def path(self, ref: str) -> Path:
        path = (self.root / ref).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Artifact reference leaves workspace")
        return path

    def get(self, ref: str):
        value = read_json(self.path(ref))
        if ref.startswith("objects/") and not ref.endswith(f"-{digest(value)}.json"):
            raise ValueError("Artifact integrity check failed")
        return value

    def get_object(self, ref: str):
        if not isinstance(ref, str) or not re.fullmatch(r"objects/[^/\\]+-[a-f0-9]{64}\.json", ref):
            raise ValueError("An immutable content-addressed object reference is required")
        return self.get(ref)

    def put_table(self, rows, kind="records", shard_bytes=128_000):
        parts, chunk, size, count = [], [], 0, 0
        for row in rows:
            value = json.loads(encode(row))
            cost = len(encode(value).encode("utf-8"))
            if chunk and size + cost > shard_bytes:
                parts.append(self.put(chunk, f"{kind}-part"))
                chunk, size = [], 0
            chunk.append(value)
            size += cost
            count += 1
        if chunk:
            parts.append(self.put(chunk, f"{kind}-part"))
        return self.put({"schema_version": "1", "parts": parts, "count": count}, kind)

    def iter_table(self, ref):
        for part in self.get_object(ref)["parts"]:
            yield from self.get_object(part)

    def table_rows(self, ref, ids):
        parts = set(self.get_object(ref)["parts"])
        index = self.path(f"indexes/{digest(ref)}.sqlite")
        if not index.exists():
            index.parent.mkdir(parents=True, exist_ok=True)
            descriptor, name = tempfile.mkstemp(dir=index.parent, suffix=".sqlite")
            os.close(descriptor)
            try:
                with closing(sqlite3.connect(name)) as connection, connection:
                    connection.execute("CREATE TABLE records (id TEXT PRIMARY KEY, part TEXT)")
                    for part in self.get_object(ref)["parts"]:
                        connection.executemany(
                            "INSERT INTO records VALUES (?,?)",
                            ((row["id"], part) for row in self.get_object(part)),
                        )
                os.replace(name, index)
            finally:
                Path(name).unlink(missing_ok=True)
        result, cache = [], {}
        with closing(sqlite3.connect(index)) as connection:
            for identifier in ids:
                row = connection.execute(
                    "SELECT part FROM records WHERE id=?", (identifier,)
                ).fetchone()
                if row is None:
                    raise ValueError(f"Missing indexed record: {identifier}")
                if row[0] not in parts:
                    raise ValueError("Derived index references a shard outside its immutable table")
                if row[0] not in cache:
                    if len(cache) >= 8:
                        del cache[next(iter(cache))]
                    cache[row[0]] = {item["id"]: item for item in self.get_object(row[0])}
                item = cache[row[0]].get(identifier)
                if item is None:
                    raise ValueError("Derived index does not match immutable artifact")
                result.append(item)
        return result

    def append_part(self, previous, rows, kind):
        return self.put({"previous": previous, "rows": rows}, f"{kind}-link")

    def iter_parts(self, ref):
        chain = []
        while ref:
            chain.append(ref)
            ref = self.get(ref)["previous"]
        for ref in reversed(chain):
            yield from self.get(ref)["rows"]

    def event(self, run_id: str, **fields):
        path = self.path(f"runs/{run_id}/events.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(encode({"time": now(), **fields}) + "\n")
            stream.flush()
        logging.getLogger("docgen").info("%s", encode(fields))


@contextmanager
def run_lock(store: Artifacts, run_id: str):
    path = store.path(f"runs/{run_id}/worker.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with FileLock(path, timeout=0):
            yield
    except Timeout as error:
        raise ValueError("Another worker holds this run") from error


def configure_logging():
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    logging.getLogger("docgen").setLevel(logging.INFO)
