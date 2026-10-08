from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str = ""
    audience: str = "New customers"
    language: Literal["English"] = "English"
    style: str = "Clear connected prose, explicit prerequisites, no marketing promises"
    scope: str = "All supplied specifications describe available functionality"
    glossary: dict[str, str] = Field(default_factory=dict)
    temperature: float = Field(default=1.0, ge=0, le=2)
    max_output_tokens: int = Field(default=8192, ge=256)
    batch_chars: int = Field(default=16000, ge=1000)
    reconcile_chars: int = Field(default=48000, ge=4000)
    context_chars: int = Field(default=100000, ge=1000)
    max_calls: int = Field(default=200, ge=1)
    token_budget: int = Field(default=2000000, ge=1000)
    retries: int = Field(default=2, ge=0, le=5)
    repair_attempts: int = Field(default=2, ge=0, le=2)
    timeout_seconds: float = Field(default=120, gt=0)
    min_call_interval: float = Field(default=0, ge=0)
    customer_evidence: bool = False
    mermaid_cli: str = ""
    browser_executable: str = ""

    @classmethod
    def load(cls, path: Path | None) -> "Settings":
        return cls.model_validate(yaml.safe_load(path.read_text("utf-8")) if path else {})


STAGES: dict[str, tuple[str, ...]] = {
    "inventory": (),
    "parse": ("inventory",),
    "extract": ("parse",),
    "reconcile": ("extract",),
    "review_knowledge": ("reconcile",),
    "outline": ("review_knowledge",),
    "review_outline": ("outline",),
    "compose": ("review_outline", "review_knowledge"),
    "validate": ("compose", "review_knowledge", "parse"),
    "review_documentation": ("validate", "compose"),
    "export": ("review_documentation", "review_knowledge", "review_outline", "parse"),
}

PROMPTS = {
    "extract": ("extract_claims", "analyze_image", "repair_extraction"),
    "reconcile": ("reconcile_entities", "detect_conflicts"),
    "outline": ("plan_outline",),
    "compose": ("compose_chapter", "plan_diagram", "repair_output"),
    "validate": ("review_semantics",),
}


def stage_settings(stage: str, settings: Settings) -> dict:
    data = settings.model_dump()
    if stage in {"inventory", "parse"}:
        return {}
    if stage == "export":
        return {"customer_evidence": settings.customer_evidence}
    if stage in PROMPTS:
        if stage != "reconcile":
            data.pop("reconcile_chars")
        for field in (
            "max_calls",
            "token_budget",
            "retries",
            "timeout_seconds",
            "min_call_interval",
        ):
            data.pop(field)
        return data
    return {}
