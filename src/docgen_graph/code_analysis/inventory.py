import re
from fnmatch import fnmatch
from pathlib import PurePosixPath

from pydantic import BaseModel, Field

from docgen_graph.storage import digest


class CodeScope(BaseModel):
    mode: str = "full"
    feature: str = ""
    paths: list[str] = []
    supporting_paths: list[str] = []
    excluded_paths: list[str] = []
    tickets: list[str] = []
    dependency_tickets: list[str] = []
    ticket_paths: dict[str, list[str]] = {}
    base_commit: str | None = None
    head_commit: str | None = None
    patch_paths: list[str] = []
    context_chars: int = Field(default=24000, ge=1000, le=100000)

    @property
    def id(self):
        return digest(self.model_dump())


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


def scope_inventory(inventory: dict, scope: CodeScope) -> dict:
    paths = sorted(inventory["analysis"])
    primary = list(scope.paths)
    support = list(scope.supporting_paths)
    for ticket in scope.tickets:
        primary.extend(scope.ticket_paths.get(ticket, []))
    for ticket in scope.dependency_tickets:
        support.extend(scope.ticket_paths.get(ticket, []))
    if scope.mode != "full" and not primary:
        raise ValueError("A restricted code scope requires explicit paths or ticket path mappings")
    selected = {p for p in paths if scope.mode == "full" or any(fnmatch(p, q) for q in primary)}
    supporting = {p for p in paths if any(fnmatch(p, q) for q in support)} - selected
    excluded = {p for p in paths if any(fnmatch(p, q) for q in scope.excluded_paths)}
    selected -= excluded
    supporting -= excluded
    symbols = {
        symbol["name"]: path
        for path, meta in inventory["analysis"].items()
        for symbol in meta.get("symbols", [])
    }
    while True:
        dependencies = {
            symbols[name.split(".")[-1]]
            for path in selected | supporting
            for imp in inventory["analysis"][path].get("imports", [])
            for name in [imp["name"]]
            if name.split(".")[-1] in symbols
        }
        added = dependencies - selected - supporting - excluded
        if not added:
            break
        supporting |= added
    dispositions = [
        {
            "path": path,
            "disposition": "selected"
            if path in selected
            else "supporting"
            if path in supporting
            else "out_of_scope",
            "reason": "explicit scope" if path not in supporting else "dependency context",
        }
        for path in paths
    ]
    spans = [
        s for s in inventory["spans"] if s["kind"] == "code" and s["path"] in selected | supporting
    ]
    units = []
    for span in spans:
        metadata = inventory["analysis"].get(span["path"], {})
        declarations = [
            entry for entry in metadata.get("symbols", []) if entry["line"] <= span["start_line"]
        ]
        context, size = [], len(span["text"])
        omitted = []
        for candidate in spans:
            if candidate["id"] == span["id"]:
                continue
            if candidate["path"] == span["path"] or candidate["path"] in supporting:
                if size + len(candidate["text"]) > scope.context_chars:
                    omitted.append(candidate["id"])
                else:
                    context.append(candidate["id"])
                    size += len(candidate["text"])
        units.append(
            {
                "id": digest([scope.id, span["id"]]),
                "evidence_ids": [span["id"]],
                "context_ids": context,
                "omitted_context_ids": omitted,
                "declarations": declarations,
                "context_truncated": bool(omitted),
                "scope_role": "supporting" if span["path"] in supporting else "primary",
            }
        )
    return {
        "schema_version": 1,
        "scope_id": scope.id,
        "scope": scope.model_dump(),
        "files": dispositions,
        "units": units,
        "unmapped_tickets": [t for t in scope.tickets if not scope.ticket_paths.get(t)],
    }
