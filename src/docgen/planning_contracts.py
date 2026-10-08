from typing import Any, Literal

from pydantic import Field, model_validator

from docgen.contracts import Evidence, Record


class PlanRecord(Record):
    schema_version: Literal["1"] = "1"


class NamedBoundary(Record):
    name: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    scope: str = Field(min_length=1)


class DocumentationBrief(PlanRecord):
    audience: str = "Readers familiar with the domain but new to this implementation"
    purpose: str = "Explain the selected system knowledge without losing qualifications"
    product_name: str | None = None
    last_reviewed: str | None = None
    language: str = "English"
    hard_scope: list[str] = Field(default_factory=list)
    include_record_ids: list[str] = Field(default_factory=list)
    exclude_record_ids: list[str] = Field(default_factory=list)
    expected_areas: list[str] = Field(default_factory=list)
    unit_policy: Literal["auto", "single", "explicit"] = "auto"
    delivery_mode: Literal["auto", "single_page", "multi_page"] = "auto"
    named_boundaries: list[NamedBoundary] = Field(default_factory=list)
    preferences: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def explicit_boundaries(self):
        if self.unit_policy == "explicit" and not self.named_boundaries:
            raise ValueError("Explicit unit policy requires named boundaries")
        if set(self.include_record_ids) & set(self.exclude_record_ids):
            raise ValueError("A record cannot be both included and excluded")
        return self


class PlanningInputs(PlanRecord):
    workflow: Literal["documentation_planning"] = "documentation_planning"
    signature: str
    knowledge_ref: str
    knowledge_revision: str
    knowledge_signature: str
    snapshot_ref: str
    selection_ref: str
    records_ref: str
    blocks_ref: str
    coverage_ref: str
    template_ref: str
    template_hash: str
    brief: DocumentationBrief
    origins: dict[str, str]
    previous_plan_ref: str | None = None


class TemplateSpan(Record):
    id: str
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    heading: str
    level: int
    parent_id: str | None
    text: str


class TemplateRule(Record):
    span_id: str
    role: Literal[
        "metadata",
        "summary",
        "capabilities",
        "process",
        "reference",
        "integrations",
        "access",
        "limitations",
        "sources",
        "other",
    ]
    required: bool
    repeatable: bool
    example: bool
    requirements: list[str]
    forms: list[str]
    rationale: str


class TemplateInterpretation(Record):
    rules: list[TemplateRule]
    application_scope: Literal["functional_unit", "collection"]
    allows_extensions: bool
    citation_rule: str
    audience: str | None
    conflicts: list[str]


class TemplateContract(PlanRecord):
    template_ref: str
    template_hash: str
    spans: list[TemplateSpan]
    rules: list[TemplateRule]
    application_scope: Literal["functional_unit", "collection"]
    allows_extensions: bool
    citation_rule: str
    page_profiles: list[str]
    audience: str | None


class ContentObligation(PlanRecord):
    id: str
    record_id: str
    record_kind: str
    facet: str
    record_ref: str
    required_fields: list[str]
    evidence: list[Evidence]
    constraints: dict[str, Any]
    eligibility: Literal["eligible", "audit_only", "out_of_scope"]
    decision_refs: list[str]
    reason: str | None = None


class UnitProposal(Record):
    key: str
    title: str
    purpose: str
    outcome: str
    scope: str
    evidence_obligation_ids: list[str] = Field(min_length=1)
    boundaries: list[str]
    dependencies: list[str]
    rationale: str
    alternative: str
    source_epic_id: str | None = None


class OwnershipProposal(Record):
    obligation_id: str
    owner_key: str | None
    disposition: Literal["included", "out_of_scope", "audit_only"]
    consumers: list[str]
    reason: str


class UnitDiscovery(Record):
    units: list[UnitProposal]
    assignments: list[OwnershipProposal]


class UnitMerge(Record):
    candidate_keys: list[str] = Field(min_length=1)
    unit: UnitProposal


class UnitSynthesis(Record):
    groups: list[UnitMerge]


class DocumentationUnit(PlanRecord):
    id: str
    title: str
    purpose: str
    outcome: str
    audience: str
    scope: str
    source_epic_id: str | None
    evidence_obligation_ids: list[str]
    boundaries: list[str]
    dependencies: list[str]
    discovery_rationale: str
    alternative: str
    verification_status: Literal["proposed", "verified"]


class UnitAssignment(PlanRecord):
    id: str
    obligation_id: str
    owner_id: str | None
    disposition: Literal["included", "out_of_scope", "audit_only"]
    consuming_unit_ids: list[str]
    dependencies: list[str]
    boundary_evidence: list[str]
    decision_refs: list[str]
    reason: str


class TemplateInstance(PlanRecord):
    id: str
    unit_id: str
    contract_ref: str
    metadata: dict[str, str | None]
    obligation_ids: list[str]
    exceptions: list[str]
    compliance: dict[str, str]


class TopicProposal(Record):
    key: str
    title: str
    template_span_id: str
    reader_question: str
    learning_outcome: str
    form: Literal[
        "explanation",
        "steps",
        "decision_table",
        "data_table",
        "comparison",
        "diagram",
        "warning",
        "reference_list",
    ]
    obligation_ids: list[str] = Field(min_length=1)
    explanation_order: list[str]
    supporting_span_ids: list[str] = Field(default_factory=list)


class LogicalProposal(Record):
    topics: list[TopicProposal]


class LogicalSection(PlanRecord):
    id: str
    topic_id: str
    owner_id: str
    template_instance_id: str | None
    template_span_id: str | None
    parent_id: str | None
    title: str
    reader_question: str
    purpose: str
    order: int
    scope: str
    form: str
    role: str
    editorial: bool = True
    explanation_order: list[str] = Field(default_factory=list)


class ContentAllocation(PlanRecord):
    id: str
    obligation_id: str
    assignment_id: str
    disposition: Literal["full_treatment", "out_of_scope", "audit_only", "unassigned"]
    canonical_section_id: str | None
    supporting_section_ids: list[str]
    reason: str
    decision_refs: list[str]


class PageChoice(Record):
    section_id: str
    detail: bool
    profile: Literal["capability", "process", "reference", "limitations"]
    reader_task: str
    estimated_words: int = Field(ge=0)
    rationale: str
    alternatives: str


class Subdivision(Record):
    choices: list[PageChoice]


class PagePlan(PlanRecord):
    id: str
    owner_id: str
    role: Literal["unit", "detail", "collection", "shared", "sources"]
    template_instance_id: str | None
    path: str
    parent_id: str | None
    profile: str
    title: str
    purpose: str
    audience: str
    reader_task: str
    scope: str
    section_ids: list[str]
    estimated_words: int
    expected_length: list[int]
    rationale: str
    alternatives: str
    dependencies: list[str]
    completion_checks: list[str]


class EvidenceElement(Record):
    id: str
    label: str
    obligation_ids: list[str]
    editorial: bool = False


class DiagramEdge(Record):
    source: str
    target: str
    label: str
    obligation_ids: list[str] = Field(min_length=1)


class DiagramSpec(Record):
    nodes: list[EvidenceElement]
    edges: list[DiagramEdge]
    unknown_transitions: list[str]


class TableSpec(Record):
    columns: list[str]
    rows: list[EvidenceElement]


class BriefProposal(Record):
    reader_question: str
    learning_outcome: str
    instructions: list[str]
    explanation_order: list[str]
    tables: list[TableSpec]
    diagrams: list[DiagramSpec]
    unknowns: list[str]
    boundaries: list[str]
    completion_checks: list[str]
    checked_obligation_ids: list[str]


class SectionBrief(PlanRecord):
    id: str
    section_id: str
    page_id: str
    part: int
    form: str
    template_span_id: str | None
    full_treatment_ids: list[str]
    supporting_ids: list[str]
    record_ids: list[str]
    evidence: list[Evidence]
    constraints: dict[str, dict[str, Any]]
    canonical_links: dict[str, str]
    content: BriefProposal


class NavigationLink(Record):
    source: str
    target: str
    kind: Literal["parent", "root", "detail", "canonical", "related", "reader_entry"]
    reason: str


class NavigationPlan(PlanRecord):
    root: str
    tree_edges: list[list[str]]
    anchors: dict[str, str]
    links: list[NavigationLink]
    path_mappings: dict[str, str]
    changes: list[dict[str, Any]]


class WritingJob(PlanRecord):
    id: str
    section_id: str
    page_id: str
    brief_id: str
    fragment: int
    assembly_order: int
    obligation_ids: list[str]
    context_ref: str
    hard_dependencies: list[str]
    estimated_input_tokens: int
    max_output_tokens: int
    output_contract: dict[str, Any]
    completion_checks: list[str]


class AuditFinding(Record):
    kind: Literal[
        "boundary",
        "scope",
        "omission",
        "unsupported",
        "qualification",
        "identity",
        "navigation",
        "template",
        "upstream_knowledge_gap",
    ]
    description: str
    obligation_ids: list[str]
    section_ids: list[str]
    repair_stage: Literal[
        "compile_template",
        "discover_documentation_units",
        "plan_logical_structure",
        "design_page_tree",
        "write_section_briefs",
    ]


class SemanticAudit(Record):
    checked_obligation_ids: list[str]
    checked_section_ids: list[str]
    findings: list[AuditFinding]
    reader_task_findings: list[str]


class PlanIssue(PlanRecord):
    id: str
    revision: str
    stage: str
    kind: str
    severity: Literal["blocking", "warning"]
    description: str
    obligation_ids: list[str]
    section_ids: list[str]
    repair_stage: str
    status: Literal["open", "resolved"] = "open"


class PlanDecision(PlanRecord):
    issue_id: str
    revision: str
    action: Literal["correct", "retain_unknown", "inapplicable", "request_upstream", "defer"]
    rationale: str = Field(min_length=1)
    reviewer: str = Field(min_length=1)
    origin: Literal["reviewer", "automatic_policy"] = "reviewer"
    correction_ref: str | None = None


class DocumentationPlan(PlanRecord):
    workflow: Literal["documentation_planning"] = "documentation_planning"
    revision: str
    signature: str
    inputs_ref: str
    components: dict[str, str]
    unit_policy: str
    delivery_mode: str
    status: Literal["ready_for_generation"]
    limitations: list[str]


class PlanComponentCorrection(PlanRecord):
    kind: Literal["planning_component_patch"]
    base_revision: str
    component: Literal["logical-sections", "pages", "section-briefs"]
    replacement_ref: str
