from typing import Literal

from pydantic import AliasChoices, BaseModel, Field, field_validator

from docgen_graph.evidence_contracts import Category


class VersionedRecord(BaseModel):
    schema_version: Literal[1] = 1


class AssertionDraft(VersionedRecord):
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

    @field_validator("conditions", "exceptions", mode="before")
    @classmethod
    def list_of_terms(cls, value):
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [value]
        return value


class ExclusionDraft(VersionedRecord):
    evidence_id: str = Field(validation_alias=AliasChoices("evidence_id", "id"))
    reason: str = Field(min_length=1)


class DocumentExtractionDraft(VersionedRecord):
    assertions: list[AssertionDraft]
    excluded: list[ExclusionDraft] = []


class AuditDraft(VersionedRecord):
    accepted: bool
    findings: list[str] = []
    missing_evidence_ids: list[str] = []
    covered_obligation_ids: list[str] = []
    covered_diagram_element_ids: list[str] = []


class TemplateRequirement(VersionedRecord):
    id: str
    kind: Literal[
        "heading", "purpose", "table", "callout", "flow", "conditional", "style", "metadata"
    ]
    section: str
    text: str
    order: int
    required: bool = True
    columns: list[str] = []
    rows: list[str] = []


class TemplateDecision(VersionedRecord):
    requirement_id: str
    disposition: Literal["applicable", "inapplicable"]
    reason: str = ""
    evidence_ids: list[str] = []


class ContentUnit(VersionedRecord):
    id: str
    topic: str
    canonical_section: str
    obligation_ids: list[str]
    common_facts: list[dict] = []
    scoped_variants: list[dict] = []
    conditions: list[str] = []
    exceptions: list[str] = []
    evidence_ids: list[str] = []


class SourceAsset(VersionedRecord):
    path: str
    hash: str = ""
    format: str = ""
    size: int = 0
    width: int | None = None
    height: int | None = None
    references: list[dict] = []
    disposition: Literal["referenced", "unreferenced", "rejected"]
    findings: list[str] = []
    transformation: str | None = None


class DiagramNode(VersionedRecord):
    id: str
    label: str
    evidence_ids: list[str] = Field(min_length=1)


class DiagramEdge(VersionedRecord):
    id: str
    source: str
    target: str
    label: str
    evidence_ids: list[str] = Field(min_length=1)


class DiagramSpec(VersionedRecord):
    id: str
    kind: Literal["flowchart", "stateDiagram-v2", "sequenceDiagram"]
    question: str
    description: str
    nodes: list[DiagramNode] = Field(min_length=2, max_length=16)
    edges: list[DiagramEdge] = Field(min_length=1, max_length=24)
    source: str = ""


class VisualChoice(VersionedRecord):
    id: str
    kind: Literal["image", "diagram"]
    section: str
    purpose: str
    asset_hash: str = ""
    evidence_ids: list[str] = []
    text_alternative: str = ""
    support_quotes: dict[str, str] = {}
    diagram_id: str = ""
    review_status: Literal["planned", "approved"] = "planned"


class VisualPlacement(VisualChoice):
    diagram: DiagramSpec | None = None


class AssetDecision(VersionedRecord):
    path: str
    reason: str = Field(min_length=1)


class PlanSubsectionDraft(VersionedRecord):
    title: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    group_ids: list[str] = []


class PlanSectionDraft(VersionedRecord):
    title: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    group_ids: list[str] = []
    support_group_ids: list[str] = []
    queries: list[str] = []
    visuals: list[VisualChoice] = []
    subsections: list[PlanSubsectionDraft] = []


class PagePlanDraft(VersionedRecord):
    title: str = Field(min_length=1)
    sections: list[PlanSectionDraft] = Field(min_length=1)
    unknowns: list[str] = []
    discrepancies: list[str] = []
    exclusions: list[str] = []
    template_decisions: list[TemplateDecision] = []
    asset_decisions: list[AssetDecision] = []
    diagrams: list[DiagramSpec] = []


class EvidencePassage(VersionedRecord):
    citation_ids: list[str] = Field(min_length=1)
    passage: str
    support_quotes: dict[str, str] = {}


class CoverageMappingDraft(EvidencePassage):
    obligation_id: str
    disposition: Literal["documented", "out_of_scope", "overview"] = "documented"
    scope_reason: str = ""
    additional_passages: list[EvidencePassage] = []


class VisualSupportQuote(VersionedRecord):
    support_id: str
    quote: str = Field(min_length=1)


class VisualEvidenceDraft(VersionedRecord):
    locations: list[VisualSupportQuote]


class PresentationPlacement(VersionedRecord):
    id: str
    kind: Literal["paragraph", "list_item", "table_row", "image", "diagram"] = "paragraph"
    section: str
    passage: str = Field(min_length=1)
    obligation_ids: list[str] = Field(min_length=1)
    citation_ids: list[str] = Field(min_length=1)
    start: int
    end: int


class SubprocessDraft(VersionedRecord):
    title: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    participants: str = Field(min_length=1)
    result: str = Field(min_length=1)
    mappings: list[CoverageMappingDraft] = Field(min_length=1)


class SectionDraft(VersionedRecord):
    markdown: str
    mappings: list[CoverageMappingDraft]
    subprocesses: list[SubprocessDraft] = []


class EditDraft(VersionedRecord):
    markdown: str = Field(min_length=1)
    mappings: list[CoverageMappingDraft] = []
