from typing import Literal

from pydantic import Field

from docgen.contracts import Evidence, Record


class TechnicalTerm(Record):
    term: str = Field(min_length=1)
    definition: str = Field(min_length=1)
    permitted_form: str = Field(min_length=1)
    part_of_speech: Literal["noun", "verb", "name", "identifier"]
    scope: str = Field(min_length=1)
    authority: str = Field(min_length=1)
    evidence: list[Evidence] = Field(default_factory=list)


class AssetRequest(Record):
    path: str
    purpose: str = Field(min_length=1)
    disposition: Literal["link", "image", "exclude"]
    explanation: str | None = None
    reviewer: str | None = None


class GenerationBrief(Record):
    schema_version: Literal["1"] = "1"
    quote_policy: Literal["exact_labeled", "none"] = "exact_labeled"
    terminology: list[TechnicalTerm] = Field(default_factory=list)
    assets: list[AssetRequest] = Field(default_factory=list)
    markdown_convention: Literal["commonmark_gfm"] = "commonmark_gfm"


class Passage(Record):
    text: str = Field(min_length=1)
    kind: Literal[
        "explanation",
        "requirement",
        "proposal",
        "observed",
        "example",
        "unknown",
        "quote",
        "editorial",
    ]
    obligation_ids: list[str]
    evidence: list[Evidence]


class TableCell(Record):
    text: str = Field(min_length=1)
    obligation_ids: list[str]
    evidence: list[Evidence]


class TableRow(Record):
    id: str
    cells: list[TableCell]


class GeneratedTable(Record):
    index: int = Field(ge=0)
    rows: list[TableRow]


class WritingFragment(Record):
    job_id: str
    section_id: str
    passages: list[Passage]
    tables: list[GeneratedTable]
    covered_obligation_ids: list[str]


class GenerationFinding(Record):
    kind: Literal[
        "unsupported",
        "omission",
        "qualification",
        "modality",
        "identity",
        "table",
        "diagram",
        "language",
        "terminology",
        "presentation",
    ]
    description: str
    obligation_ids: list[str]
    blocking: bool = True


class WritingVerification(Record):
    checked_obligation_ids: list[str]
    checked_table_rows: list[str]
    checked_diagram_ids: list[str]
    findings: list[GenerationFinding]
    language_review_scope: str


class GenerationDecision(Record):
    issue_id: str
    revision: str
    action: Literal[
        "correct", "approve_term", "asset_decision", "request_upstream", "defer", "approve_release"
    ]
    reviewer: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    correction_ref: str | None = None
    reviewed_scope: list[str] = Field(default_factory=list)


class PageVerification(Record):
    checked_section_ids: list[str]
    findings: list[GenerationFinding]
    readability: str
