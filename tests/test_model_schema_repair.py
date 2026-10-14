import json
import sqlite3
import time
from dataclasses import replace
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from google.genai.errors import APIError
from pydantic import BaseModel, Field, ValidationError

from docgen_graph.budget import Pricing
from docgen_graph.config import Settings
from docgen_graph.model import GeminiModel, response_schema
from docgen_graph.storage import ArtifactStore


class BoundedResponse(BaseModel):
    values: list[str] = Field(min_length=1, max_length=2)


@pytest.mark.parametrize("succeeds", [True, False])
def test_schema_failures_are_bounded_recorded_and_charged(tmp_path, monkeypatch, succeeds):
    env = tmp_path / ".env"
    env.write_text("GEMINI_API_KEY=provider-test-only\n", "utf-8")
    settings = replace(
        Settings.load(env), workspace=tmp_path, budget_ledger=tmp_path / "cost.sqlite"
    )
    with sqlite3.connect(settings.budget_ledger) as connection:
        connection.execute(
            "CREATE TABLE charges (id TEXT PRIMARY KEY, run_id TEXT, stage TEXT, "
            "time TEXT, reserved REAL, charged REAL, status TEXT, usage TEXT, pricing TEXT)"
        )
    today = date.today()
    pricing = Pricing(
        "gemini-3.8-flash", 1, 1, 4, today, today + timedelta(days=1), today, "test", "test"
    )
    monkeypatch.setattr(Pricing, "load", lambda path: pricing)
    requests = []

    def generate(**kwargs):
        requests.append(kwargs)
        return SimpleNamespace(
            text=json.dumps({"values": ["supported"] if succeeds and len(requests) == 2 else []}),
            usage_metadata=SimpleNamespace(
                prompt_token_count=100, candidates_token_count=10, thoughts_token_count=0
            ),
            candidates=[SimpleNamespace(finish_reason=SimpleNamespace(name="STOP"))],
        )

    monkeypatch.setattr(
        "docgen_graph.model.client_for",
        lambda *args: SimpleNamespace(models=SimpleNamespace(generate_content=generate)),
    )
    model = GeminiModel(settings, ArtifactStore(tmp_path), "schema-repair")
    if succeeds:
        assert model.call("write_section", {"task": "test"}, BoundedResponse)["values"] == [
            "supported"
        ]
        assert "schema_feedback" in requests[1]["contents"]
    else:
        with pytest.raises(ValidationError):
            model.call("write_section", {"task": "test"}, BoundedResponse)
    assert len(requests) == (2 if succeeds else 3)
    with sqlite3.connect(settings.budget_ledger) as connection:
        charges = connection.execute("SELECT status, charged FROM charges").fetchall()
    assert len(charges) == len(requests)
    assert all(status == "settled" and amount > 0 for status, amount in charges)
    assert len(list((tmp_path / "runs/schema-repair/invalid").glob("*.json"))) == (
        1 if succeeds else 3
    )
    schema = response_schema(BoundedResponse)["properties"]["values"]
    assert schema["minItems"] == 1
    assert schema["maxItems"] == 2


@pytest.mark.parametrize(
    "stage,output,timeout,thinking",
    [
        ("source_document", 65536, 420, "HIGH"),
        ("extract_document", 8192, 120, "LOW"),
    ],
)
def test_authoring_uses_separate_allowance_and_honors_run_deadline(
    tmp_path, monkeypatch, stage, output, timeout, thinking
):
    env = tmp_path / ".env"
    env.write_text("GEMINI_API_KEY=provider-test-only\n", "utf-8")
    settings = replace(
        Settings.load(env),
        workspace=tmp_path,
        budget_ledger=tmp_path / "cost.sqlite",
        thinking_level="low",
        output_tokens=8192,
        timeout_seconds=120,
        authoring_output_tokens=65536,
        authoring_timeout_seconds=420,
    )
    with sqlite3.connect(settings.budget_ledger) as connection:
        connection.execute(
            "CREATE TABLE charges (id TEXT PRIMARY KEY, run_id TEXT, stage TEXT, "
            "time TEXT, reserved REAL, charged REAL, status TEXT, usage TEXT, pricing TEXT)"
        )
    today = date.today()
    pricing = Pricing(
        "gemini-3.8-flash", 1, 1, 4, today, today + timedelta(days=1), today, "test", "test"
    )
    monkeypatch.setattr(Pricing, "load", lambda path: pricing)
    requests, clients = [], []

    def generate(**kwargs):
        requests.append(kwargs)
        return SimpleNamespace(
            text=json.dumps({"values": ["supported"]}),
            usage_metadata=SimpleNamespace(
                prompt_token_count=100, candidates_token_count=10, thoughts_token_count=20
            ),
            candidates=[SimpleNamespace(finish_reason=SimpleNamespace(name="STOP"))],
        )

    def client(key, seconds):
        clients.append(seconds)
        return SimpleNamespace(models=SimpleNamespace(generate_content=generate))

    monkeypatch.setattr("docgen_graph.model.client_for", client)
    model = GeminiModel(settings, ArtifactStore(tmp_path), "authoring-budget")
    model.set_deadline(time.time() + 25)
    assert model.call(stage, {"task": "test"}, BoundedResponse)["values"] == ["supported"]
    config = requests[0]["config"]
    assert config.max_output_tokens == output
    assert config.thinking_config.thinking_level == thinking
    assert clients == [timeout]
    assert 0 < config.http_options.timeout <= 25000
    with sqlite3.connect(settings.budget_ledger) as connection:
        usage, status = connection.execute("SELECT usage, status FROM charges").fetchone()
    assert status == "settled"
    assert json.loads(usage)["output_tokens"] == 30
    model.settings = replace(settings, request_tokens=output)
    with pytest.raises(ValueError, match="context budget"):
        model.call(stage, {"task": "different request"}, BoundedResponse)


@pytest.mark.parametrize(
    "remaining,expected_delays,expected_calls",
    [
        (None, [10, 30], 3),
        (12, [10, 2], 2),
    ],
)
def test_provider_overload_backoff_is_bounded_and_respects_deadline(
    tmp_path, monkeypatch, remaining, expected_delays, expected_calls
):
    settings = replace(Settings.load(tmp_path / ".env"), api_key="test-only")
    clock, delays, requests, settlements = [1000.0], [], [], []
    monkeypatch.setattr("docgen_graph.model.time.time", lambda: clock[0])

    def sleep(seconds):
        delays.append(seconds)
        clock[0] += seconds

    def generate(**kwargs):
        requests.append(kwargs)
        raise APIError(503, {"error": {"message": "High demand", "status": "UNAVAILABLE"}})

    monkeypatch.setattr("docgen_graph.model.time.sleep", sleep)
    monkeypatch.setattr(
        "docgen_graph.model.Pricing.load", lambda path: SimpleNamespace(cost=lambda *args: 1.0)
    )
    monkeypatch.setattr(
        "docgen_graph.model.BudgetLedger",
        lambda *args: SimpleNamespace(
            reserve=lambda *args: "reservation", settle=lambda *args: settlements.append(args)
        ),
    )
    monkeypatch.setattr(
        "docgen_graph.model.client_for",
        lambda *args: SimpleNamespace(models=SimpleNamespace(generate_content=generate)),
    )
    model = GeminiModel(settings, ArtifactStore(tmp_path), "overload")
    model.set_deadline(clock[0] + remaining if remaining else None)
    with pytest.raises(TimeoutError if remaining else APIError):
        model.call("source_plan", {"task": "test overload"}, BoundedResponse)
    assert delays == expected_delays
    assert len(requests) == expected_calls
    assert len(settlements) == expected_calls
    assert all(item[1] is None for item in settlements)
