import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from docgen.config import Settings
from docgen.storage import Artifacts, digest, read_json, write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--thread-id", required=True)
    parser.add_argument("--plan")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--decisions")
    args = parser.parse_args()
    from docgen.cli import run_config

    run_config(args.thread_id)
    store = Artifacts(Settings().workspace)
    record = store.path(f"runs/{args.thread_id}/implementation.json")
    if args.resume:
        implementation = Path(read_json(record)["path"])
    else:
        if not args.plan or record.exists():
            raise ValueError("A new thread ID and completed plan are required")
        source = Path(__file__).resolve().parents[1] / "src/docgen"
        hashes = {
            p.relative_to(source).as_posix(): digest(p.read_bytes())
            for p in source.rglob("*")
            if p.suffix in {".py", ".txt"}
        }
        implementation = store.path(f"implementations/generation-{digest(hashes)}")
        if not implementation.exists():
            shutil.copytree(
                source, implementation / "docgen", ignore=shutil.ignore_patterns("__pycache__")
            )
        write_json(record, {"path": str(implementation), "files": hashes})
    metadata = read_json(record)
    for name, checksum in metadata["files"].items():
        if digest((implementation / "docgen" / name).read_bytes()) != checksum:
            raise ValueError("Frozen generation implementation changed")
    environment = {**os.environ, "PYTHONPATH": str(implementation)}
    command = [sys.executable, "-m", "docgen.cli"]
    if args.resume:
        command += ["resume", "--thread-id", args.thread_id]
        if args.decisions:
            command += ["--decisions", args.decisions]
    else:
        command += [
            "generate-documentation",
            "--plan",
            args.plan,
            "--thread-id",
            args.thread_id,
            "--cache-mode",
            "off",
        ]
    return subprocess.call(command, env=environment)


if __name__ == "__main__":
    raise SystemExit(main())
