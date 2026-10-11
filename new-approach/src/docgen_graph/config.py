import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


@dataclass(frozen=True)
class Settings:
    env_file: Path
    workspace: Path
    shared_data: Path
    budget_ledger: Path
    pricing_file: Path
    api_key: str
    model: str
    output_tokens: int
    request_tokens: int
    timeout_seconds: int

    @classmethod
    def load(cls, env_file: Path | None = None) -> "Settings":
        selected = (env_file or Path(__file__).resolve().parents[2] / ".env").resolve()
        values = {**dotenv_values(selected), **os.environ}

        def path(name: str, default: str) -> Path:
            return (selected.parent / str(values.get(name) or default)).resolve()

        model = str(values.get("GEMINI_MODEL") or "gemini-3.8-flash")
        if model != "gemini-3.8-flash":
            raise ValueError("GEMINI_MODEL must be gemini-3.8-flash")
        return cls(
            env_file=selected,
            workspace=path("DOCGEN_WORKSPACE", ".docgen"),
            shared_data=path("DOCGEN_SHARED_DATA", "../data"),
            budget_ledger=path("DOCGEN_BUDGET_LEDGER", "../.docgen/budget.sqlite"),
            pricing_file=path("DOCGEN_PRICING_FILE", "../.docgen/pricing.json"),
            api_key=str(values.get("GEMINI_API_KEY") or ""),
            model=model,
            output_tokens=int(values.get("DOCGEN_OUTPUT_TOKENS") or 8192),
            request_tokens=int(values.get("DOCGEN_REQUEST_TOKENS") or 100000),
            timeout_seconds=int(values.get("DOCGEN_TIMEOUT_SECONDS") or 120),
        )
