import sqlite3
from datetime import date, timedelta

import pytest

from docgen_graph.budget import BudgetLedger, Pricing
from docgen_graph.config import Settings


def test_model_allowlist_and_env_relative_paths(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("DOCGEN_BUDGET_PLN", raising=False)
    env = tmp_path / ".env"
    env.write_text("GEMINI_MODEL=gemini-3.8-flash\nDOCGEN_SHARED_DATA=../data\n", encoding="utf-8")
    settings = Settings.load(env)
    assert settings.shared_data == (tmp_path / "../data").resolve()
    assert settings.budget_pln is None
    env.write_text("GEMINI_MODEL=gemini-3.8-flash\nDOCGEN_BUDGET_PLN=1000\n", encoding="utf-8")
    assert Settings.load(env).budget_pln == 1000
    env.write_text("GEMINI_MODEL=another-model\n", encoding="utf-8")
    with pytest.raises(ValueError, match="GEMINI_MODEL"):
        Settings.load(env)


def test_shared_ledger_reserves_without_resetting_existing_charges(tmp_path):
    path = tmp_path / "budget.sqlite"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE charges (id TEXT PRIMARY KEY, run_id TEXT, stage TEXT, "
            "time TEXT, reserved REAL, charged REAL, status TEXT, usage TEXT, pricing TEXT)"
        )
        connection.execute(
            "INSERT INTO charges VALUES "
            "('historical','old','write','now',0,49,'settled','{}','{}')"
        )
    today = date.today()
    pricing = Pricing(
        "gemini-3.8-flash", 1, 1, 4, today, today + timedelta(days=1), today, "official", "nbp"
    )
    ledger = BudgetLedger(path, limit=50)
    reservation = ledger.reserve("new", "analysis", 0.5, pricing)
    assert ledger.summary()["remaining_pln"] == 0.5
    with pytest.raises(ValueError, match="Budget exhausted"):
        ledger.reserve("new", "analysis", 0.6, pricing)
    ledger.settle(reservation, 0.25, {"input_tokens": 1})
    assert ledger.summary()["charged_pln"] == 49.25
    uncapped = BudgetLedger(path)
    uncapped.reserve("new", "analysis", 500, pricing)
    assert uncapped.summary()["limit_pln"] is None
    assert uncapped.summary()["remaining_pln"] is None
    assert uncapped.summary()["charged_pln"] == 49.25


def test_independent_audit_reasoning_is_explicit_and_validated(tmp_path):
    env = tmp_path / ".env"
    env.write_text("DOCGEN_THINKING_LEVEL=low\nDOCGEN_AUDIT_THINKING_LEVEL=medium\n", "utf-8")
    settings = Settings.load(env)
    assert settings.thinking_level == "low"
    assert settings.audit_thinking_level == "medium"
    env.write_text("DOCGEN_AUDIT_THINKING_LEVEL=automatic\n", "utf-8")
    with pytest.raises(ValueError, match="DOCGEN_AUDIT_THINKING_LEVEL"):
        Settings.load(env)
