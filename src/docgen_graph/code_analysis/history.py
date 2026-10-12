import re
import subprocess
from pathlib import Path, PurePosixPath

from docgen_graph.storage import digest


def parse_patch(text: str) -> list[dict]:
    hunks = []
    base_path, head_path, current = "", "", None
    for line in text.splitlines():
        if line.startswith("diff --git ") or line.startswith("--- "):
            if current:
                hunks.append(current)
                current = None
        if line.startswith("--- "):
            base_path = line[4:].split("\t")[0].removeprefix("a/")
        elif line.startswith("+++ "):
            head_path = line[4:].split("\t")[0].removeprefix("b/")
        elif match := re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line):
            if current:
                hunks.append(current)
            current = {
                "header": line,
                "base_path": base_path,
                "head_path": head_path,
                "base_start": int(match[1]),
                "head_start": int(match[3]),
                "base_count": int(match[2] or 1),
                "head_count": int(match[4] or 1),
                "text": line,
                "temporal_status": "historical",
            }
        elif current is not None:
            current["text"] += "\n" + line
    if current:
        hunks.append(current)
    for hunk in hunks:
        for path in (hunk["base_path"], hunk["head_path"]):
            if path == "/dev/null":
                continue
            selected = PurePosixPath(path)
            if selected.is_absolute() or ".." in selected.parts or ":" in path:
                raise ValueError("Patch path leaves the selected repository")
        hunk["id"] = digest(hunk)
    return hunks


def _git(root, *arguments):
    result = subprocess.run(
        ["git", "-C", str(root), *arguments], capture_output=True, check=True, timeout=30
    )
    return result.stdout


def freeze_history(store, root: Path, scope, selected_paths: list[str]) -> dict:
    if bool(scope.base_commit) != bool(scope.head_commit):
        raise ValueError("History requires both base and head commits")
    versions, patches = [], []
    base, head = None, None
    if scope.base_commit:
        base = (
            _git(root, "rev-parse", "--verify", "--end-of-options", scope.base_commit + "^{commit}")
            .decode()
            .strip()
        )
        head = (
            _git(root, "rev-parse", "--verify", "--end-of-options", scope.head_commit + "^{commit}")
            .decode()
            .strip()
        )
        if not selected_paths:
            raise ValueError("History requires explicitly selected code paths")
        for commit, side in ((base, "base"), (head, "head")):
            for path in selected_paths:
                candidate = PurePosixPath(path)
                if candidate.is_absolute() or ".." in candidate.parts or ":" in path:
                    raise ValueError("History path leaves repository")
                try:
                    content = _git(root, "show", f"{commit}:{path}")
                except subprocess.CalledProcessError:
                    versions.append(
                        {"path": path, "side": side, "commit": commit, "status": "absent"}
                    )
                    continue
                versions.append(
                    {
                        "path": path,
                        "side": side,
                        "commit": commit,
                        "hash": store.put_bytes(content),
                        "status": "present",
                    }
                )
        patch = _git(
            root,
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--find-renames",
            base,
            head,
            "--",
            *selected_paths,
        )
        patches.append(
            {
                "path": "selected-history.diff",
                "hash": store.put_bytes(patch),
                "hunks": parse_patch(patch.decode("utf-8")),
            }
        )
    for relative in scope.patch_paths:
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()) or path.is_symlink():
            raise ValueError("Patch must be a regular file inside the selected root")
        content = path.read_bytes()
        patches.append(
            {
                "path": relative,
                "hash": store.put_bytes(content),
                "hunks": parse_patch(content.decode("utf-8")),
            }
        )
    return {
        "schema_version": 1,
        "base_commit": base,
        "head_commit": head,
        "versions": versions,
        "patches": patches,
        "scope_id": scope.id,
    }
