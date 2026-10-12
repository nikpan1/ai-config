from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvidenceRecord(BaseModel):
    schema_version: Literal[1] = 1


class EvidenceLocator(EvidenceRecord):
    model_config = ConfigDict(extra="forbid")
    kind: Literal[
        "lines", "characters", "page", "paragraph", "table_cell", "sheet_range", "diff_hunk"
    ]
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=0)
    page: int | None = Field(default=None, ge=1)
    table: str | int | None = None
    cell: str | None = None
    row: int | None = Field(default=None, ge=1)
    column: int | None = Field(default=None, ge=1)
    paragraph: int | None = Field(default=None, ge=1)
    sheet: str | None = None
    range: str | None = None
    hunk: str | None = None
    side: Literal["base", "head"] | None = None

    @model_validator(mode="after")
    def valid_location(self):
        if self.kind in {"lines", "characters"}:
            minimum = 1 if self.kind == "lines" else 0
            if (
                self.start is None
                or self.end is None
                or self.start < minimum
                or self.end < self.start
            ):
                raise ValueError("Invalid source range")
        required = {
            "page": self.page,
            "paragraph": self.paragraph,
            "table_cell": self.cell or (self.row and self.column),
            "sheet_range": self.range,
            "diff_hunk": self.hunk,
        }
        if self.kind in required and not required[self.kind]:
            raise ValueError("Locator lacks its typed position")
        if self.kind == "sheet_range" and not self.sheet:
            raise ValueError("Sheet locator requires a sheet name")
        if self.kind == "table_cell" and not self.table:
            raise ValueError("Cell locator requires a table identifier")
        if self.kind == "diff_hunk" and not self.side:
            raise ValueError("Diff locator requires a base or head side")
        return self


class EvidenceRef(EvidenceRecord):
    id: str = Field(min_length=1)
    source_kind: Literal["code", "document", "attachment", "patch", "reviewer"]
    snapshot_id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    locator: EvidenceLocator
    source_role: str
    text: str = ""
    parent_ids: list[str] = []
    parser_version: str | None = None
    commit: str | None = None
    temporal_status: Literal["current_snapshot", "historical", "planned", "unknown"] = "unknown"

    @model_validator(mode="after")
    def relative_path(self):
        path = PurePosixPath(self.path.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts or ":" in self.path:
            raise ValueError("Evidence path must be relative to its frozen snapshot")
        return self


class AnalysisProvenance(EvidenceRecord):
    id: str
    provider: str
    model: str
    sdk_version: str = ""
    session_id: str = ""
    request_id: str = ""
    prompt_version: str = ""
    input_hash: str
    scope_id: str
    commit: str | None = None
    base_commit: str | None = None
    head_commit: str | None = None
    deterministic_method: str | None = None


Category = Literal[
    "GUI", "PRODUCT_CONFIGURATION", "PRODUCT_FEATURE", "IMPLEMENTATION_FEATURE", "UNKNOWN"
]


class FactRecord(EvidenceRecord):
    id: str
    statement: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    subject: str = "unspecified"
    predicate: str = "describes"
    scope: str = "selected sources"
    modality: str = "descriptive"
    conditions: list[str] = []
    exceptions: list[str] = []
    source_role: str = "source"
    categories: list[Category] = Field(default=["UNKNOWN"], min_length=1)
    classification_reason: str = "Not classified"
    relevance: Literal["essential", "supporting", "context", "unknown"] = "unknown"
    relevance_reason: str = "Not assessed"
    audience_scope: str = "selected audience"
    support_status: Literal["direct", "inferred", "unresolved"] = "unresolved"
    temporal_status: Literal["current_snapshot", "historical", "planned", "unknown"] = "unknown"
    provenance_ids: list[str] = []
    review_status: Literal["unreviewed", "verified", "rejected"] = "unreviewed"


class EvidenceRelation(EvidenceRecord):
    type: str
    source_id: str
    target_id: str
    method: str
    evidence_ids: list[str] = Field(min_length=1)


class SourceCoverageItem(EvidenceRecord):
    id: str
    evidence_ids: list[str] = Field(min_length=1)
    unit_locator: EvidenceLocator
    aspect: str
    disposition: Literal["represented", "duplicate", "excluded_non_substantive", "unresolved"] = (
        "unresolved"
    )
    fact_ids: list[str] = []
    duplicate_of: str | None = None
    reason: str = ""
    decision_ref: str | None = None


class EvidenceQuery(EvidenceRecord):
    snapshot_id: str
    graph_revision: str
    scope_id: str
    query: str = ""
    mandatory_ids: list[str] = []
    filters: dict = {}
    cursor: str | None = None
    limit: int = Field(default=40, ge=1, le=1000)


class EvidenceResult(EvidenceRecord):
    status: Literal["ok", "not_found", "unavailable", "unsupported", "budget_blocked"]
    facts: list[FactRecord] = []
    evidence: list[EvidenceRef] = []
    relations: list[EvidenceRelation] = []
    conflicts: list[dict] = []
    provenance: list[AnalysisProvenance] = []
    coverage: list[SourceCoverageItem] = []
    next_cursor: str | None = None
    truncated: bool = False
    warnings: list[str] = []
    usage_ref: str | None = None
    graph_revision: str | None = None


class DeltaVerification(EvidenceRecord):
    accepted: bool
    verifier: str
    input_hash: str
    findings: list[str] = []


class KnowledgeDelta(EvidenceRecord):
    base_revision: str
    facts: list[FactRecord] = []
    evidence: list[EvidenceRef] = []
    relations: list[EvidenceRelation] = []
    conflicts: list[dict] = []
    coverage: list[SourceCoverageItem] = []
    provenance: list[AnalysisProvenance] = []
    verification: DeltaVerification

    def verification_payload(self) -> dict:
        return self.model_dump(exclude={"verification"})
