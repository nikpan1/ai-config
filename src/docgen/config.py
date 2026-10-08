from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", frozen=True)

    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: Literal["gemini-3.8-flash"] = "gemini-3.8-flash"
    workspace: Path = Field(Path(".docgen"), validation_alias="DOCGEN_WORKSPACE")
    budget_ledger: Path = Field(
        Path(".docgen/budget.sqlite"), validation_alias="DOCGEN_BUDGET_LEDGER"
    )
    batch_tokens: int = Field(8000, ge=256, validation_alias="DOCGEN_BATCH_TOKENS")
    context_tokens: int = Field(4000, ge=0, validation_alias="DOCGEN_CONTEXT_TOKENS")
    output_tokens: int = Field(24000, ge=1024, le=65536, validation_alias="DOCGEN_OUTPUT_TOKENS")
    request_tokens: int = Field(
        100000, ge=4096, le=1048576, validation_alias="DOCGEN_REQUEST_TOKENS"
    )
    reconciliation_tokens: int = Field(
        12000, ge=1024, validation_alias="DOCGEN_RECONCILIATION_TOKENS"
    )
    timeout_seconds: int = Field(180, ge=1, validation_alias="DOCGEN_TIMEOUT_SECONDS")
    technical_retries: int = Field(2, ge=0, le=5, validation_alias="DOCGEN_TECHNICAL_RETRIES")
    thinking_level: Literal["low", "medium", "high"] = Field(
        "low", validation_alias="DOCGEN_THINKING_LEVEL"
    )
    budget_pln: float = Field(200, gt=0, le=200, validation_alias="DOCGEN_BUDGET_PLN")
    billing_headroom: float = Field(1.3, ge=1.25, validation_alias="DOCGEN_BILLING_HEADROOM")
    pricing_file: Path = Field(Path(".docgen/pricing.json"), validation_alias="DOCGEN_PRICING_FILE")

    @model_validator(mode="after")
    def check_budgets(self):
        if (
            self.batch_tokens + self.context_tokens + self.output_tokens + 8000
            > self.request_tokens
        ):
            raise ValueError("Source, context, instructions and output exceed request token budget")
        return self

    def signature(self) -> dict:
        return self.model_dump(
            mode="json",
            exclude={
                "gemini_api_key",
                "workspace",
                "budget_ledger",
                "pricing_file",
                "budget_pln",
                "billing_headroom",
                "timeout_seconds",
                "technical_retries",
            },
        )
