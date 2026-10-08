from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Link(Record):
    target: str
    kind: Literal["link", "image"]


class Block(Record):
    id: str
    snapshot: str
    path: str
    headings: list[str]
    line_start: int
    line_end: int
    char_start: int
    char_end: int
    kind: str
    content: str
    table_id: str | None = None
    table_row: int | None = None
    table_columns: list[str] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)


class Batch(Record):
    id: str
    owned: list[str]
    context: list[str]
    dependencies: list[str]
    omitted_context: list[str]
    source_tokens: int
    context_tokens: int
    instruction_tokens: int = 8000
    output_tokens: int
    status: str = "pending"
    attempts: int = 0
    split_from: str | None = None


class Evidence(Record):
    block_id: str
    excerpt: str = Field(min_length=1)


class Claim(Record):
    id: str
    statement: str = Field(min_length=1)
    entities: list[str]
    conditions: list[str]
    exceptions: list[str]
    frequency_time: str | None
    scope: str | None
    version: str | None
    modality: Literal["requirement", "implemented", "proposal", "example", "unknown"]
    source_status: str | None
    rule_keys: list[str]
    evidence: list[Evidence] = Field(min_length=1)
    review_status: Literal["draft", "verified", "reviewed", "ineligible"] = "draft"


class Entity(Record):
    id: str
    canonical_name: str
    aliases: list[str]
    kind: Literal["term", "actor", "service", "object", "feature"]
    definition: str | None
    scope: str | None
    version: str | None
    evidence: list[Evidence] = Field(min_length=1)
    review_status: Literal["draft", "verified", "reviewed"] = "draft"


class Coverage(Record):
    block_id: str
    disposition: Literal["represented", "duplicate", "excluded", "unresolved"]
    claim_ids: list[str]
    duplicate_of: str | None = None
    explanation: str = Field(min_length=1)


class Finding(Record):
    kind: Literal[
        "omission",
        "distortion",
        "unsupported",
        "conflict",
        "missing_context",
        "ambiguous_entity",
        "source_issue",
    ]
    description: str
    block_ids: list[str]
    record_ids: list[str]


class Extraction(Record):
    claims: list[Claim]
    entities: list[Entity]
    coverage: list[Coverage]
    findings: list[Finding]


class Verification(Record):
    findings: list[Finding]
    checked_block_ids: list[str]


class Relation(Record):
    kind: Literal[
        "duplicate",
        "variant",
        "conflict",
        "same_entity",
        "distinct_entity",
        "dependency",
        "missing_dependency",
    ]
    left: str
    right: str
    explanation: str


class Comparison(Record):
    relations: list[Relation]
    findings: list[Finding]
    checked_ids: list[str]


class Issue(Record):
    id: str
    stage: str
    kind: str
    description: str
    block_ids: list[str] = Field(default_factory=list)
    record_ids: list[str] = Field(default_factory=list)
    revision: str
    source_path: str | None = None
    status: Literal["open", "resolved"] = "open"


class Decision(Record):
    issue_id: str
    revision: str
    action: Literal[
        "defer",
        "correct",
        "exclude",
        "select_authority",
        "keep_distinct",
        "merge_entities",
        "explain_asset",
        "acknowledge_unknown",
    ]
    rationale: str = Field(min_length=1)
    reviewer: str = Field(min_length=1)
    claim_ids: list[str] = Field(default_factory=list)
    entity_ids: list[str] = Field(default_factory=list)
    replacement: Extraction | None = None
    explanation: str | None = None
