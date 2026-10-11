from typing import Literal

from pydantic import AliasChoices, BaseModel, Field, field_validator


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

    @field_validator("conditions", "exceptions", mode="before")
    @classmethod
    def list_of_terms(cls, value):
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [value]
        return value


class CodeAnalysisDraft(VersionedRecord):
    report: str = Field(min_length=1)
    details: list[AssertionDraft]


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


class PlanSectionDraft(VersionedRecord):
    title: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    group_ids: list[str] = []
    support_group_ids: list[str] = []
    queries: list[str] = []


class PagePlanDraft(VersionedRecord):
    title: str = Field(min_length=1)
    sections: list[PlanSectionDraft] = Field(min_length=1)
    unknowns: list[str] = []
    discrepancies: list[str] = []
    exclusions: list[str] = []


class CoverageMappingDraft(VersionedRecord):
    obligation_id: str
    citation_ids: list[str] = Field(min_length=1)
    passage: str = Field(min_length=1)


class SectionDraft(VersionedRecord):
    markdown: str = Field(min_length=1)
    mappings: list[CoverageMappingDraft]


class EditDraft(VersionedRecord):
    markdown: str = Field(min_length=1)
