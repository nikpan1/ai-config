import json
from pathlib import Path

from docgen_graph.assets import verify_bundle
from docgen_graph.storage import ArtifactStore, digest


def inspect_legacy_workspace(source: Path, target: Path, copy: bool = False) -> dict:
    source = source.resolve()
    target = target.resolve()
    if not source.is_dir() or source == target or target.is_relative_to(source):
        raise ValueError("Choose a separate existing source workspace and destination")
    files = [path for path in source.rglob("*") if path.is_file()]
    for path in files:
        relative = path.relative_to(source)
        if (
            relative.parts[:1] == ("objects",)
            and len(relative.parts) == 3
            and len(relative.name) == 64
        ):
            if digest(path.read_bytes()) != relative.name:
                raise ValueError(f"Corrupt content object: {relative}")
        if path.name == "candidate-manifest.json":
            verify_bundle(path.parent, json.loads(path.read_text("utf-8")))
    collisions = []
    for path in files:
        destination = target / path.relative_to(source)
        if destination.exists() and digest(destination.read_bytes()) != digest(path.read_bytes()):
            collisions.append(path.relative_to(source).as_posix())
    if collisions and copy:
        raise ValueError(f"Destination has different files: {collisions[:10]}")
    if copy:
        store = ArtifactStore(target)
        for path in files:
            relative = path.relative_to(source)
            if not (target / relative).exists():
                store.write(relative.as_posix(), path.read_bytes())
    return {
        "source": str(source),
        "target": str(target),
        "files_verified": len(files),
        "copied": copy,
        "collisions": collisions,
        "checkpoint_compatibility": (
            "Historical checkpoints remain inspectable; "
            "resume requires the current runtime signature"
        ),
    }
