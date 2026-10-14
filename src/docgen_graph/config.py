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
    authoring_turn_limit: int = 8
    authoring_timeout_seconds: int = 420
    authoring_output_tokens: int = 65536
    authoring_result_limit: int = 60000
    thinking_level: str | None = None
    audit_thinking_level: str | None = None
    authoring_thinking_level: str = "high"
    editorial_review: bool = True
    editorial_round_limit: int = 3
    fast_mode: bool = False
    model_workers: int = 4
    run_timeout_seconds: int = 1200
    minimum_coverage: float = 0.9
    source_first: bool = True
    graph_assisted_retrieval: bool = False
    finalization_reserve_seconds: int = 180

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
        authoring_thinking = str(values.get("DOCGEN_AUTHORING_THINKING_LEVEL") or "high").lower()
        if authoring_thinking not in {"low", "medium", "high"}:
            raise ValueError("DOCGEN_AUTHORING_THINKING_LEVEL must be low, medium or high")
        editorial_review = str(values.get("DOCGEN_EDITORIAL_REVIEW") or "true").lower()
        if editorial_review not in {"true", "false", "1", "0"}:
            raise ValueError("DOCGEN_EDITORIAL_REVIEW must be true or false")
        editorial_rounds = int(values.get("DOCGEN_EDITORIAL_ROUND_LIMIT", 3))
        if not 1 <= editorial_rounds <= 3:
            raise ValueError("DOCGEN_EDITORIAL_ROUND_LIMIT must be between 1 and 3")
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
        authoring_turns = int(values.get("DOCGEN_AUTHORING_TURN_LIMIT", 8))
        authoring_timeout = int(values.get("DOCGEN_AUTHORING_TIMEOUT_SECONDS", 420))
        authoring_output = int(values.get("DOCGEN_AUTHORING_OUTPUT_TOKENS", 65536))
        if not 1024 <= authoring_output <= 65536:
            raise ValueError("DOCGEN_AUTHORING_OUTPUT_TOKENS must be between 1024 and 65536")
        authoring_result = int(values.get("DOCGEN_AUTHORING_RESULT_LIMIT", 60000))
        if min(authoring_turns, authoring_timeout, authoring_result) <= 0 or authoring_turns > 50:
            raise ValueError("Authoring limits must be positive and turns at most 50")
        fast_mode = str(values.get("DOCGEN_FAST_MODE") or "false").lower()
        if fast_mode not in {"true", "false", "1", "0"}:
            raise ValueError("DOCGEN_FAST_MODE must be true or false")
        model_workers = int(values.get("DOCGEN_MODEL_WORKERS") or 4)
        run_timeout = int(values.get("DOCGEN_RUN_TIMEOUT_SECONDS") or 1200)
        minimum_coverage = float(values.get("DOCGEN_MINIMUM_COVERAGE") or 0.9)
        source_first = str(values.get("DOCGEN_SOURCE_FIRST") or "true").lower()
        if source_first not in {"true", "false", "1", "0"}:
            raise ValueError("DOCGEN_SOURCE_FIRST must be true or false")
        graph_assisted = str(values.get("DOCGEN_GRAPH_ASSISTED_RETRIEVAL") or "false").lower()
        if graph_assisted not in {"true", "false", "1", "0"}:
            raise ValueError("DOCGEN_GRAPH_ASSISTED_RETRIEVAL must be true or false")
        finalization_reserve = int(values.get("DOCGEN_FINALIZATION_RESERVE_SECONDS") or 180)
        if finalization_reserve < 1:
            raise ValueError("DOCGEN_FINALIZATION_RESERVE_SECONDS must be positive")
        if not 1 <= model_workers <= 32:
            raise ValueError("DOCGEN_MODEL_WORKERS must be between 1 and 32")
        if run_timeout <= 0:
            raise ValueError("DOCGEN_RUN_TIMEOUT_SECONDS must be positive")
        if not math.isfinite(minimum_coverage) or not 0 < minimum_coverage <= 1:
            raise ValueError("DOCGEN_MINIMUM_COVERAGE must be greater than 0 and at most 1")
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
            authoring_thinking_level=authoring_thinking,
            editorial_review=editorial_review in {"true", "1"},
            editorial_round_limit=editorial_rounds,
            output_tokens=int(values.get("DOCGEN_OUTPUT_TOKENS") or 8192),
            request_tokens=int(values.get("DOCGEN_REQUEST_TOKENS") or 100000),
            timeout_seconds=int(values.get("DOCGEN_TIMEOUT_SECONDS") or 120),
            asset_max_bytes=asset_max_bytes,
            asset_max_pixels=asset_max_pixels,
            source_page_map=path("DOCGEN_SOURCE_PAGE_MAP", "")
            if values.get("DOCGEN_SOURCE_PAGE_MAP")
            else None,
            content_repair_limit=content_repair_limit,
            authoring_turn_limit=authoring_turns,
            authoring_timeout_seconds=authoring_timeout,
            authoring_output_tokens=authoring_output,
            authoring_result_limit=authoring_result,
            fast_mode=fast_mode in {"true", "1"},
            model_workers=model_workers,
            run_timeout_seconds=run_timeout,
            minimum_coverage=minimum_coverage,
            source_first=source_first in {"true", "1"},
            graph_assisted_retrieval=graph_assisted in {"true", "1"},
            finalization_reserve_seconds=finalization_reserve,
        )
