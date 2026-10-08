import hashlib
import json
import os
import shutil
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from filelock import FileLock, Timeout

from docgen import __version__
from docgen.config import PROMPTS, STAGES, Settings, stage_settings


def now() -> str:
    return datetime.now(UTC).isoformat()


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text("utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def fingerprint(stage: str, settings: Settings) -> str:
    from docgen.llm import load_prompt

    return digest(
        {
            "code": __version__,
            "schema": 1,
            "algorithm": {"parse": 2, "extract": 2, "reconcile": 2}.get(stage, 1),
            "settings": stage_settings(stage, settings),
            "prompts": {name: load_prompt(name)[1] for name in PROMPTS.get(stage, ())},
        }
    )


class Store:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.manifest = read_json(self.root / "manifest.json")
        self.on_event: Callable[[dict], None] | None = None

    @classmethod
    def create(cls, runs: Path, source: Path, settings: Settings) -> "Store":
        source = source.resolve(strict=True)
        run_id = "run-" + datetime.now(UTC).strftime("%Y%m%d-%H%M%S-") + uuid4().hex[:8]
        root = runs.resolve() / run_id
        root.mkdir(parents=True)
        write_json(
            root / "manifest.json",
            {
                "schema_version": 1,
                "run_id": run_id,
                "execution_id": uuid4().hex,
                "created_at": now(),
                "source": str(source),
                "settings": settings.model_dump(),
                "status": "pending",
                "stages": {
                    name: {
                        "dependencies": list(deps),
                        "status": "pending",
                        "active": None,
                        "attempts": [],
                    }
                    for name, deps in STAGES.items()
                },
                "usage": {
                    "calls": 0,
                    "reserved_tokens": 0,
                    "budget_tokens": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                },
                "exports": [],
                "cleanup": [],
                "feedback": {},
            },
        )
        return cls(root)

    def save(self) -> None:
        write_json(self.root / "manifest.json", self.manifest)

    @contextmanager
    def lock(self) -> Iterator[None]:
        lock = FileLock(self.root / ".worker.lock")
        try:
            lock.acquire(timeout=0)
        except Timeout as exc:
            raise ValueError("A worker is running; stop it before modifying this run") from exc
        try:
            self.manifest = read_json(self.root / "manifest.json")
            self.cleanup()
            yield
        finally:
            lock.release()

    def event(self, kind: str, data: dict) -> None:
        event = {"time": now(), "event": kind, **data}
        with (self.root / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event) + "\n")
        if self.on_event:
            self.on_event(event)

    def stage(self, name: str) -> dict:
        return self.manifest["stages"][name]

    def attempt_dir(self, stage: str, attempt: dict) -> Path:
        return self.root / "stages" / stage / "attempts" / str(attempt["id"])

    def active(self, stage: str) -> dict | None:
        record = self.stage(stage)
        return next((a for a in record["attempts"] if a["id"] == record["active"]), None)

    def output(self, stage: str) -> dict:
        attempt = self.active(stage)
        if not attempt or attempt["status"] != "completed":
            raise ValueError(f"Missing prerequisite: rebuild {stage}")
        return read_json(self.attempt_dir(stage, attempt) / "output.json")

    def begin(self, stage: str, settings: Settings) -> tuple[dict, Path]:
        record = self.stage(stage)
        existing = self.active(stage)
        if existing and existing["status"] == "waiting_for_review":
            return existing, self.attempt_dir(stage, existing)
        if existing:
            existing["status"] = "superseded"
        dependencies = {}
        for dep in record["dependencies"]:
            upstream = self.active(dep)
            if not upstream or upstream["status"] != "completed":
                raise ValueError(f"Missing prerequisite: rebuild {dep}")
            dependencies[dep] = {"attempt": upstream["id"], "hash": upstream["output_hash"]}
        attempt = {
            "id": len(record["attempts"]) + 1,
            "stage": stage,
            "execution_id": self.manifest["execution_id"],
            "status": "running",
            "started_at": now(),
            "ended_at": None,
            "dependencies": dependencies,
            "fingerprint": fingerprint(stage, settings),
            "code_version": __version__,
            "schema_version": 1,
            "checkpoint": self.manifest["execution_id"],
        }
        directory = self.attempt_dir(stage, attempt)
        directory.mkdir(parents=True)
        write_json(
            directory / "input.json",
            {
                "run_id": self.manifest["run_id"],
                "stage": stage,
                "configuration": settings.model_dump(),
                "dependencies": dependencies,
                "source": self.manifest["source"] if stage == "inventory" else None,
                "feedback": self.manifest["feedback"].get(stage, ""),
            },
        )
        attempt["input_hash"] = digest((directory / "input.json").read_bytes())
        record["attempts"].append(attempt)
        record.update(active=attempt["id"], status="running")
        self.persist_attempt(stage, attempt)
        return attempt, directory

    def persist_attempt(self, stage: str, attempt: dict) -> None:
        self.stage(stage)["status"] = attempt["status"]
        write_json(self.attempt_dir(stage, attempt) / "metadata.json", attempt)
        self.save()

    def commit(self, stage: str, attempt: dict, result: dict) -> None:
        directory = self.attempt_dir(stage, attempt)
        write_json(directory / "output.json", result)
        attempt.update(status="completed", ended_at=now(), output_hash=digest(result))
        attempt["files"] = {
            p.relative_to(directory).as_posix(): digest(p.read_bytes())
            for p in directory.rglob("*")
            if p.is_file() and p.name != "metadata.json"
        }
        self.persist_attempt(stage, attempt)
        if stage in {"extract", "reconcile", "review_knowledge"}:
            with sqlite3.connect(self.root / "knowledge.sqlite") as db:
                db.execute(
                    "CREATE TABLE IF NOT EXISTS revisions (hash TEXT PRIMARY KEY, data TEXT)"
                )
                db.execute(
                    "INSERT OR IGNORE INTO revisions VALUES (?, ?)",
                    (attempt["output_hash"], json.dumps(result)),
                )
        self.event("stage_completed", {"stage": stage, "attempt": attempt["id"]})

    def descendants(self, stage: str) -> list[str]:
        if stage not in self.manifest["stages"]:
            raise ValueError(f"Unknown stage: {stage}")
        affected = {stage}
        while True:
            added = {
                name
                for name, value in self.manifest["stages"].items()
                if affected.intersection(value["dependencies"])
            } - affected
            if not added:
                break
            affected.update(added)
        return [name for name in self.manifest["stages"] if name in affected]

    def reset(self, stage: str, purge: bool = False, dry_run: bool = False) -> dict:
        affected = self.descendants(stage)
        payloads = [
            str(self.attempt_dir(name, a).relative_to(self.root))
            for name in affected
            for a in self.stage(name)["attempts"]
            if a["status"] != "purged"
        ]
        report = {
            "stages": affected,
            "approvals": [s for s in affected if s.startswith("review_")],
            "payloads": payloads,
            "purge": purge,
            "cache_entries": affected,
            "retained": ["sources/", "assets/", "historical exported bundles"],
        }
        if dry_run:
            return report
        for name in affected:
            record = self.stage(name)
            for attempt in record["attempts"]:
                if attempt["status"] != "purged":
                    attempt["status"] = "purged" if purge else "invalidated"
                    attempt["invalidated_at"] = now()
            record.update(active=None, status="pending")
        for export in self.manifest["exports"]:
            export["current"] = False
        self.manifest.update(execution_id=uuid4().hex, status="pending")
        if purge:
            self.manifest["cleanup"].extend(payloads)
        self.save()
        self.cleanup()
        for name in affected:
            for attempt in self.stage(name)["attempts"]:
                directory = self.attempt_dir(name, attempt)
                if directory.exists():
                    write_json(directory / "metadata.json", attempt)
        self.event("reset", report)
        return report

    def cleanup(self) -> None:
        for relative in list(self.manifest["cleanup"]):
            parts = Path(relative).parts
            if (
                len(parts) != 4
                or parts[0] != "stages"
                or parts[1] not in STAGES
                or parts[2] != "attempts"
                or not parts[3].isdigit()
            ):
                raise ValueError("Unsafe purge path")
            path = (self.root / relative).resolve()
            if not path.is_relative_to(self.root / "stages") or path.is_symlink():
                raise ValueError("Unsafe purge path")
            if path.exists():
                shutil.rmtree(path)
            self.manifest["cleanup"].remove(relative)
            self.save()
        database = self.root / "knowledge.sqlite"
        if database.exists():
            retained = {
                a.get("output_hash")
                for stage in self.manifest["stages"].values()
                for a in stage["attempts"]
                if a["status"] != "purged"
            }
            with sqlite3.connect(database) as db:
                db.execute("PRAGMA secure_delete=ON")
                for (checksum,) in db.execute("SELECT hash FROM revisions").fetchall():
                    if checksum not in retained:
                        db.execute("DELETE FROM revisions WHERE hash = ?", (checksum,))

    def verify(self, settings: Settings) -> list[str]:
        for stage in self.manifest["stages"]:
            attempt = self.active(stage)
            if not attempt:
                continue
            reason = None
            if attempt["fingerprint"] != fingerprint(stage, settings):
                reason = "configuration or prompt changed"
            directory = self.attempt_dir(stage, attempt)
            input_path = directory / "input.json"
            if not input_path.is_file() or digest(input_path.read_bytes()) != attempt.get(
                "input_hash"
            ):
                reason = "missing or corrupt input.json"
            for relative, checksum in attempt.get("files", {}).items():
                path = directory / relative
                if not path.is_file() or digest(path.read_bytes()) != checksum:
                    reason = f"missing or corrupt {relative}"
                    break
            if stage == "inventory" and attempt["status"] == "completed" and not reason:
                inventory = self.output(stage)
                for item in inventory["documents"] + inventory["images"]:
                    if not item.get("snapshot"):
                        continue
                    path = self.root / item["snapshot"]
                    if not path.is_file() or digest(path.read_bytes()) != item["content_hash"]:
                        reason = "missing or corrupt source snapshot"
                        break
            if stage == "export" and attempt["status"] == "completed" and not reason:
                exported = self.output(stage)
                for name, checksum in exported["checksums"].items():
                    path = Path(exported["path"]) / name
                    if not path.is_file() or digest(path.read_bytes()) != checksum:
                        reason = "missing or corrupt exported bundle"
                        break
            if reason:
                self.reset(stage)
                return [f"Rebuild {stage}: {reason}"]
        return []
