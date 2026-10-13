from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SemanticRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceQuote(SemanticRecord):
    evidence_id: str = Field(min_length=1)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str = Field(min_length=1)


class SemanticTopic(SemanticRecord):
    key: str = Field(min_length=1)
    name: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    quotes: list[EvidenceQuote] = Field(min_length=1)


class SemanticQualifier(SemanticRecord):
    statement: str = Field(min_length=1)
    quotes: list[EvidenceQuote] = Field(min_length=1)


class SemanticConditionGroup(SemanticRecord):
    operator: Literal["all", "any", "unspecified"]
    source_conditions: list[str] = []
    quotes: list[EvidenceQuote] = Field(min_length=1)
    conditions: list[SemanticQualifier] = Field(min_length=1)


class SemanticRule(SemanticRecord):
    key: str = Field(min_length=1)
    topic_key: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    modality: Literal[
        "necessary", "sufficient", "necessary_and_sufficient", "descriptive", "prohibited"
    ]
    fact_ids: list[str] = Field(min_length=1)
    quotes: list[EvidenceQuote] = Field(min_length=1)
    topic_quotes: list[EvidenceQuote] = Field(min_length=1)
    condition_groups: list[SemanticConditionGroup] = []
    exceptions: list[SemanticQualifier] = []
    preserved_conditions: list[str] = []
    preserved_exceptions: list[str] = []


class SemanticConcept(SemanticRecord):
    key: str = Field(min_length=1)
    name: str = Field(min_length=1)
    kind: str = Field(default="Concept", min_length=1)
    scope: str = Field(default="Selected sources", min_length=1)
    description: str = Field(min_length=1)
    fact_ids: list[str] = []
    quotes: list[EvidenceQuote] = Field(min_length=1)
    status: Literal["direct", "inferred", "uncertain"] = "direct"


class SemanticRelationship(SemanticRecord):
    source_key: str = Field(min_length=1)
    target_key: str = Field(min_length=1)
    description: str = Field(min_length=1)
    label: str = Field(default="Related", min_length=1)
    status: Literal["direct", "inferred", "uncertain"] = "direct"
    quotes: list[EvidenceQuote] = Field(min_length=1)


class NavigationalGraphDraft(SemanticRecord):
    concepts: list[SemanticConcept] = []
    relationships: list[SemanticRelationship] = []
    findings: list[str] = []


class SemanticGraphDraft(NavigationalGraphDraft):
    topics: list[SemanticTopic] = []
    rules: list[SemanticRule] = []
