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


class SemanticGraphDraft(SemanticRecord):
    topics: list[SemanticTopic]
    rules: list[SemanticRule]
    findings: list[str] = []
