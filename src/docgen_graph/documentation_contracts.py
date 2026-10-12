from typing import Literal

from pydantic import BaseModel, Field


class SourceAspect(BaseModel):
    id: str = ""
    evidence_id: str
    quote: str = Field(min_length=1)
    kind: Literal[
        "obligation",
        "condition",
        "exception",
        "boundary",
        "role",
        "order",
        "effect",
        "relationship",
        "unknown",
        "example",
    ]
    description: str


class AspectInventory(BaseModel):
    aspects: list[SourceAspect]
    non_substantive: list[str] = []


class AspectDecision(BaseModel):
    aspect_id: str
    fact_ids: list[str] = []
    status: Literal["represented", "duplicate", "unresolved"]
    reason: str


class SourceAudit(BaseModel):
    decisions: list[AspectDecision]
    findings: list[str] = []


class HeadingNode(BaseModel):
    section_id: str
    parent_id: str = ""
    level: int
    title: str
    number: str = ""
    placeholder: bool = False
    required: bool = True
    order: int
    minimum: int = 1
    maximum: int = 1


class ToolOutcome(BaseModel):
    status: Literal["ok", "not_found", "unavailable", "unsupported", "budget_blocked", "unresolved"]
    data: dict = {}
    findings: list[str] = []
    truncated: bool = False
    next_cursor: str | None = None
