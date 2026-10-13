import json
import sqlite3
from dataclasses import replace
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
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
