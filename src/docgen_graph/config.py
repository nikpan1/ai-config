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
    budget_pln: float
    pricing_file: Path
    api_key: str
    model: str
    output_tokens: int
    request_tokens: int
    timeout_seconds: int
    asset_max_bytes: int = 10000000
    asset_max_pixels: int = 20000000
    source_page_map: Path | None = None
    content_repair_limit: int = 2

    @classmethod
    def load(cls, env_file: Path | None = None) -> "Settings":
        selected = (env_file or Path(__file__).resolve().parents[2] / ".env").resolve()
        values = {**dotenv_values(selected), **os.environ}

        def path(name: str, default: str) -> Path:
            return (selected.parent / str(values.get(name) or default)).resolve()

        model = str(values.get("GEMINI_MODEL") or "gemini-3.8-flash")
        if model != "gemini-3.8-flash":
            raise ValueError("GEMINI_MODEL must be gemini-3.8-flash")
        configured_budget_pln = float(values.get("DOCGEN_BUDGET_PLN") or 200)
        if configured_budget_pln <= 0:
            raise ValueError("DOCGEN_BUDGET_PLN must be positive")
        budget_pln = min(configured_budget_pln, 200.0)
        asset_max_bytes = int(values.get("DOCGEN_ASSET_MAX_BYTES") or 10000000)
        asset_max_pixels = int(values.get("DOCGEN_ASSET_MAX_PIXELS") or 20000000)
        content_repair_limit = int(values.get("DOCGEN_CONTENT_REPAIR_LIMIT", 2))
        if min(asset_max_bytes, asset_max_pixels) <= 0:
            raise ValueError("Asset byte and pixel limits must be positive")
        if content_repair_limit < 0 or content_repair_limit > 10:
            raise ValueError("DOCGEN_CONTENT_REPAIR_LIMIT must be between 0 and 10")
        return cls(
            env_file=selected,
            workspace=path("DOCGEN_WORKSPACE", ".docgen/graph"),
            shared_data=path("DOCGEN_SHARED_DATA", "data"),
            budget_ledger=path("DOCGEN_BUDGET_LEDGER", ".docgen/budget.sqlite"),
            budget_pln=budget_pln,
            pricing_file=path("DOCGEN_PRICING_FILE", ".docgen/pricing.json"),
            api_key=str(values.get("GEMINI_API_KEY") or ""),
            model=model,
            output_tokens=int(values.get("DOCGEN_OUTPUT_TOKENS") or 8192),
            request_tokens=int(values.get("DOCGEN_REQUEST_TOKENS") or 100000),
            timeout_seconds=int(values.get("DOCGEN_TIMEOUT_SECONDS") or 120),
            asset_max_bytes=asset_max_bytes,
            asset_max_pixels=asset_max_pixels,
            source_page_map=path("DOCGEN_SOURCE_PAGE_MAP", "")
            if values.get("DOCGEN_SOURCE_PAGE_MAP")
            else None,
            content_repair_limit=content_repair_limit,
        )
