import hashlib
import json
import os
import time
from pathlib import Path
from tempfile import NamedTemporaryFile


def encode(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(value: object) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else encode(value)).hexdigest()


def windows_extended_path(path: Path) -> str:
    value = str(path)
    if value.startswith("\\\\?\\"):
        return value
    if value.startswith("\\\\"):
        return "\\\\?\\UNC\\" + value[2:]
    return "\\\\?\\" + value


def within_directory(path: Path, root: Path) -> bool:
    if os.name == "nt":
        return Path(windows_extended_path(path)).is_relative_to(Path(windows_extended_path(root)))
    return path.is_relative_to(root)


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
        temporary.write(content)
        temporary.flush()
        os.fsync(temporary.fileno())
        name = temporary.name
    source = Path(name).resolve()
    target = path.resolve()
    if os.name == "nt":
        os.replace(windows_extended_path(source), windows_extended_path(target))
    else:
        os.replace(source, target)


class ArtifactStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def put_bytes(self, content: bytes) -> str:
        key = digest(content)
        path = self.root / "objects" / key[:2] / key
        if not path.exists():
            atomic_write(path, content)
        return key

    def get_bytes(self, key: str) -> bytes:
        content = (self.root / "objects" / key[:2] / key).read_bytes()
        if digest(content) != key:
            raise ValueError("Artifact digest mismatch")
        return content

    def put(self, value: object) -> str:
        return self.put_bytes(encode(value))

    def get(self, key: str):
        return json.loads(self.get_bytes(key))

    def write(self, relative: str, content: str | bytes) -> Path:
        path = (self.root / relative).resolve()
        if not within_directory(path, self.root):
            raise ValueError("Artifact path leaves workspace")
        atomic_write(path, content.encode() if isinstance(content, str) else content)
        return path

    def event(self, run_id: str, stage: str, event: str, **fields) -> None:
        path = (self.root / "runs" / run_id / "events.jsonl").resolve()
        if not within_directory(path, self.root):
            raise ValueError("Event path leaves workspace")
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {"time": time.time(), "stage": stage, "event": event, **fields}
        with path.open("ab") as output:
            output.write(encode(entry) + b"\n")
            output.flush()
            os.fsync(output.fileno())
