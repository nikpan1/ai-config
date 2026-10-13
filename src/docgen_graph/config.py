import math
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values


@dataclass(frozen=True)
class Settings:
    env_file: Path
    workspace: Path
    shared_data: Path
    budget_ledger: Path
    budget_pln: float | None
    pricing_file: Path
    api_key: str = field(repr=False)
    model: str
    output_tokens: int
    request_tokens: int
    timeout_seconds: int
    asset_max_bytes: int = 10000000
    asset_max_pixels: int = 20000000
    source_page_map: Path | None = None
    content_repair_limit: int = 2
    code_analysis_backend: str = "gemini"
    code_analysis_model: str = "gemini-3.8-flash"
    code_analysis_timeout: int = 120
    code_analysis_turn_limit: int = 8
    code_analysis_result_limit: int = 100000
    code_scope_file: Path | None = None
    code_provider_allowance_file: Path | None = None
    auggie_api_key: str = field(default="", repr=False)
    code_analysis_api_key: str = field(default="", repr=False)
    authoring_turn_limit: int = 8
    authoring_timeout_seconds: int = 300
    authoring_result_limit: int = 60000
    thinking_level: str | None = None
    audit_thinking_level: str | None = None

    @classmethod
    def load(cls, env_file: Path | None = None) -> "Settings":
        selected = (env_file or Path(__file__).resolve().parents[2] / ".env").resolve()
        values = {**dotenv_values(selected), **os.environ}

        def path(name: str, default: str) -> Path:
            return (selected.parent / str(values.get(name) or default)).resolve()

        model = str(values.get("GEMINI_MODEL") or "gemini-3.8-flash")
        thinking_level = str(values.get("DOCGEN_THINKING_LEVEL") or "").lower() or None
        if thinking_level not in {None, "low", "medium", "high"}:
            raise ValueError("DOCGEN_THINKING_LEVEL must be low, medium or high when configured")
        audit_thinking_level = str(values.get("DOCGEN_AUDIT_THINKING_LEVEL") or "").lower() or None
        if audit_thinking_level not in {None, "low", "medium", "high"}:
            raise ValueError(
                "DOCGEN_AUDIT_THINKING_LEVEL must be low, medium or high when configured"
            )
        if model != "gemini-3.8-flash":
            raise ValueError("GEMINI_MODEL must be gemini-3.8-flash")
        configured_budget = values.get("DOCGEN_BUDGET_PLN")
        budget_pln = float(configured_budget) if configured_budget else None
        if budget_pln is not None and (not math.isfinite(budget_pln) or budget_pln <= 0):
            raise ValueError("DOCGEN_BUDGET_PLN must be positive when configured")
        asset_max_bytes = int(values.get("DOCGEN_ASSET_MAX_BYTES") or 10000000)
        asset_max_pixels = int(values.get("DOCGEN_ASSET_MAX_PIXELS") or 20000000)
        content_repair_limit = int(values.get("DOCGEN_CONTENT_REPAIR_LIMIT", 2))
        if min(asset_max_bytes, asset_max_pixels) <= 0:
            raise ValueError("Asset byte and pixel limits must be positive")
        if content_repair_limit < 0 or content_repair_limit > 10:
            raise ValueError("DOCGEN_CONTENT_REPAIR_LIMIT must be between 0 and 10")
        backend = str(values.get("DOCGEN_CODE_ANALYSIS_BACKEND") or "gemini")
        if backend not in {"gemini", "codex_sdk", "auggie_sdk"}:
            raise ValueError("Unsupported code analysis backend")
        code_model = str(
            values.get("DOCGEN_CODE_ANALYSIS_MODEL") or (model if backend == "gemini" else "")
        )
        if not code_model or (backend == "gemini" and code_model != model):
            raise ValueError("An explicit compatible code analysis model is required")
        code_timeout = int(values.get("DOCGEN_CODE_ANALYSIS_TIMEOUT") or 120)
        code_turns = int(values.get("DOCGEN_CODE_ANALYSIS_TURN_LIMIT") or 8)
        code_result = int(values.get("DOCGEN_CODE_ANALYSIS_RESULT_LIMIT") or 100000)
        if min(code_timeout, code_turns, code_result) <= 0 or code_turns > 50:
            raise ValueError("Code analysis limits must be positive and turns at most 50")
        authoring_turns = int(values.get("DOCGEN_AUTHORING_TURN_LIMIT", 8))
        authoring_timeout = int(values.get("DOCGEN_AUTHORING_TIMEOUT_SECONDS", 300))
        authoring_result = int(values.get("DOCGEN_AUTHORING_RESULT_LIMIT", 60000))
        if min(authoring_turns, authoring_timeout, authoring_result) <= 0 or authoring_turns > 50:
            raise ValueError("Authoring limits must be positive and turns at most 50")
        return cls(
            env_file=selected,
            workspace=path("DOCGEN_WORKSPACE", ".docgen/graph"),
            shared_data=path("DOCGEN_SHARED_DATA", "data"),
            budget_ledger=path("DOCGEN_BUDGET_LEDGER", ".docgen/budget.sqlite"),
            budget_pln=budget_pln,
            pricing_file=path("DOCGEN_PRICING_FILE", ".docgen/pricing.json"),
            api_key=str(values.get("GEMINI_API_KEY") or ""),
            model=model,
            thinking_level=thinking_level,
            audit_thinking_level=audit_thinking_level,
            output_tokens=int(values.get("DOCGEN_OUTPUT_TOKENS") or 8192),
            request_tokens=int(values.get("DOCGEN_REQUEST_TOKENS") or 100000),
            timeout_seconds=int(values.get("DOCGEN_TIMEOUT_SECONDS") or 120),
            asset_max_bytes=asset_max_bytes,
            asset_max_pixels=asset_max_pixels,
            source_page_map=path("DOCGEN_SOURCE_PAGE_MAP", "")
            if values.get("DOCGEN_SOURCE_PAGE_MAP")
            else None,
            content_repair_limit=content_repair_limit,
            code_analysis_backend=backend,
            code_analysis_model=code_model,
            code_analysis_timeout=code_timeout,
            code_analysis_turn_limit=code_turns,
            code_analysis_result_limit=code_result,
            code_scope_file=path("DOCGEN_CODE_SCOPE_FILE", "")
            if values.get("DOCGEN_CODE_SCOPE_FILE")
            else None,
            code_provider_allowance_file=path("DOCGEN_CODE_PROVIDER_ALLOWANCE_FILE", "")
            if values.get("DOCGEN_CODE_PROVIDER_ALLOWANCE_FILE")
            else None,
            auggie_api_key=str(values.get("AUGGIE_API_KEY") or ""),
            code_analysis_api_key=str(values.get("OPENAI_API_KEY") or ""),
            authoring_turn_limit=authoring_turns,
            authoring_timeout_seconds=authoring_timeout,
            authoring_result_limit=authoring_result,
        )
