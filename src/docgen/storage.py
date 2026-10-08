import hashlib
import json
import logging
import os
import tempfile
from contextlib import contextmanager
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
    atomic_write(path, "".join(encode(row) + "\n" for row in rows))


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
