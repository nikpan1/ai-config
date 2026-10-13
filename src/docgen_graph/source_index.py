import re
from pathlib import PurePosixPath

from docgen_graph.storage import digest


def source_role(path: str) -> str:
    name = PurePosixPath(path).name.lower()
    parts = {part.lower() for part in PurePosixPath(path).parts}
    if (
        parts & {"test", "tests", "__tests__"}
        or name.startswith("test_")
        or re.search(r"\.(test|spec)\.", name)
    ):
        return "test_expectation"
    if name.endswith((".diff", ".patch")):
        return "change_history"
    if name.endswith((".yaml", ".yml", ".toml", ".json", ".xml", ".properties")):
        return "configuration_declaration"
    return "implementation"


def structural_index(path: str, text: str) -> dict:
    suffix = PurePosixPath(path).suffix.lower()
    kinds = {
        "controller": r"@(?:RestController|Controller|(?:Get|Post|Put|Delete|Request)Mapping)\b",
        "service": r"@Service\b|@Injectable\b",
        "dto": r"\b(?:record|class)\s+\w*(?:Dto|DTO|Request|Response)\b",
        "component": r"@Component\b|templateUrl\s*:",
        "route": r"\bpath\s*:|routerLink|RouterModule",
        "visibility": r"\*ngIf|@if\s*\(|\[hidden\]|\[disabled\]",
        "validation": r"@(?:NotNull|NotBlank|Min|Max|Valid)\b|Validators\.|\bthrow\b",
        "event": r"\([a-zA-Z]+\)\s*=|onClick|onSubmit",
        "configuration_use": r"@Value\b|@ConfigurationProperties\b|environment\.|featureFlag",
    }
    entries, symbols, imports = [], [], []
    for number, line in enumerate(text.splitlines(), 1):
        for kind, pattern in kinds.items():
            if re.search(pattern, line):
                entries.append({"kind": kind, "line": number, "text": line.strip()})
        symbol = re.search(r"\b(?:class|interface|record|enum|function)\s+(\w+)", line)
        if symbol:
            symbols.append({"name": symbol.group(1), "line": number, "end_line": number})
        imported = re.search(
            r"(?:\bimport\s+(?:static\s+)?([\w.*]+)|\bfrom\s+['\"]([^'\"]+))", line
        )
        if imported:
            imports.append({"name": imported.group(1) or imported.group(2), "line": number})
    return {
        "capability": "java_ts_text_index_v1"
        if suffix in {".java", ".ts", ".tsx", ".html"}
        else "generic_text_index_v1",
        "symbols": symbols,
        "imports": imports,
        "calls": [],
        "entry_points": entries,
        "non_substantive": [],
    }


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


