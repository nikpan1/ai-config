from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceDocument(Record):
    id: str
    snapshot_id: str
    path: str
    content_hash: str
    snapshot: str
    format: Literal["markdown"] = "markdown"
    version: str | None = None


class SourceSpan(Record):
    id: str
    snapshot_id: str
    path: str
    start_line: int
    end_line: int
    headings: list[str]
    excerpt: str
    kind: str
    parser_version: str
    table: list[list[str]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ImageAsset(Record):
    id: str
    content_hash: str | None = None
    snapshot: str | None = None
    reference: str
    span_ids: list[str]
    alt: str = ""
    status: Literal["pending", "unresolved", "analyzed", "excluded"] = "pending"
    reason: str = ""
    width: int | None = None
    height: int | None = None


class EvidenceRef(Record):
    id: str
    kind: Literal["text", "image", "reviewer"]
    span_id: str | None = None
    asset_id: str | None = None
    statement: str | None = None
    reviewer: str | None = None
    timestamp: str | None = None
    region: list[float] | None = None


EntityType = Literal[
    "capability",
    "business_scenario",
    "actor",
    "process",
    "customer_input",
    "prerequisite",
    "integration",
    "configuration",
    "constraint",
]


class Entity(Record):
    id: str
    type: EntityType
    name: str
    aliases: list[str] = Field(default_factory=list)
    scope: str = ""
    version: str = ""
    evidence_ids: list[str]


class Obligation(Record):
    supplied: str
    by: str | None = None
    format: str | None = None
    stage: str | None = None
    requirement: Literal["mandatory", "optional", "conditional", "unknown"]


class Claim(Record):
    id: str
    assertion: str
    entity_ids: list[str]
    conditions: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)
    scope: str = ""
    version: str = ""
    evidence_ids: list[str]
    obligation: Obligation | None = None
    status: Literal["candidate", "accepted", "rejected", "unresolved"] = "candidate"


class Relationship(Record):
    id: str
    subject: str
    object: str
    type: Literal[
        "enables",
        "requires",
        "provided_by",
        "integrates_with",
        "depends_on",
        "produces",
        "precedes",
    ]
    claim_ids: list[str]
    direction: Literal["directed", "undirected"] = "directed"


class Conflict(Record):
    id: str
    claim_ids: list[str]
    description: str
    status: Literal["unresolved", "resolved"] = "unresolved"
    rationale: str = ""


class Coverage(Record):
    evidence_id: str
    disposition: Literal["covered", "excluded", "unresolved"]
    claim_ids: list[str] = Field(default_factory=list)
    reason: str = ""


class Extraction(Record):
    entities: list[Entity]
    claims: list[Claim]
    relationships: list[Relationship]
    coverage: list[Coverage]


class ImageAnalysis(Extraction):
    classification: Literal["decorative", "illustrative", "informative", "unreadable"]
    reason: str


class Resolution(Record):
    aliases: dict[str, str] = Field(default_factory=dict)
    conflicts: list[Conflict] = Field(default_factory=list)


class Knowledge(Extraction):
    schema_version: int = 1
    evidence: list[EvidenceRef]
    conflicts: list[Conflict] = Field(default_factory=list)
    aliases: dict[str, str] = Field(default_factory=dict)
    gaps: list[str] = Field(default_factory=list)


class ChapterPlan(Record):
    id: str
    title: str
    reader_question: str
    prerequisites: list[str]
    learning_outcome: str
    required_claim_ids: list[str]
    uncovered_topics: list[str]


class Outline(Record):
    chapters: list[ChapterPlan]
    excluded_claims: dict[str, str] = Field(default_factory=dict)


class GeneratedBlock(Record):
    id: str
    content: str
    claim_ids: list[str]
    evidence_ids: list[str]
    type: Literal["explanation", "step", "caution", "example", "summary"]


class DiagramEdge(Record):
    subject: str
    object: str
    label: str
    relationship_id: str
    claim_ids: list[str]


class DiagramSpec(Record):
    id: str
    type: Literal["flowchart"] = "flowchart"
    nodes: dict[str, str]
    edges: list[DiagramEdge]


class Diagrams(Record):
    diagrams: list[DiagramSpec]


class Chapter(Record):
    id: str
    title: str
    blocks: list[GeneratedBlock]
    gaps: list[str] = Field(default_factory=list)
    diagrams: list[DiagramSpec] = Field(default_factory=list)


class Draft(Record):
    chapters: list[Chapter]


class Finding(Record):
    severity: Literal["error", "warning"]
    artifact_id: str
    message: str


class SemanticReview(Record):
    findings: list[Finding]


class ReviewDecision(Record):
    revision: str
    reviewer: str = Field(min_length=1)
    action: Literal["approve", "revise", "defer", "cancel"]
    rationale: str = Field(min_length=1)
    patch: dict | None = None
    statements: list[str] = Field(default_factory=list)
    included_image_ids: list[str] = Field(default_factory=list)
