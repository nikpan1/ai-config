from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from test_budget import pricing

from docgen.budget import BudgetLedger
from docgen.config import Settings
from docgen.contracts import Extraction
from docgen.model import GeminiModel, ModelFailure, TruncatedOutput
from docgen.storage import write_json


def test_wrong_model_is_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, gemini_model="gemini-2.5-flash")


def test_paid_invalid_output_is_charged_and_truncation_not_cached(settings, store, monkeypatch):
    settings = settings.model_copy(update={"pricing_file": store.path("pricing.json")})
    write_json(settings.pricing_file, pricing())

    class Response:
        usage_metadata = SimpleNamespace(
            prompt_token_count=100,
            candidates_token_count=200,
            thoughts_token_count=50,
            total_token_count=350,
            model_dump=lambda **kwargs: {"total_token_count": 350},
        )
        candidates = [SimpleNamespace(finish_reason="MAX_TOKENS")]
        text = "partial output"

        def model_dump(self, **kwargs):
            return {"finish_reason": "MAX_TOKENS", "text": self.text}

    models = SimpleNamespace(
        generate_content=lambda **kwargs: Response(),
        count_tokens=lambda **kwargs: SimpleNamespace(total_tokens=100),
    )
    monkeypatch.setattr("docgen.model.client_for", lambda *args: SimpleNamespace(models=models))
    model = GeminiModel(settings, store, "test")
    with pytest.raises(TruncatedOutput):
        model.call("extract", {"source": "fixture"}, Extraction)
    assert model.ledger.summary()["charged_pln"] > 0
    assert model.ledger.summary()["reserved_pln"] == 0
    assert not list(store.path("cache").glob("*.json"))


def test_failed_request_keeps_reservation_as_charge(settings, store, monkeypatch):
    settings = settings.model_copy(update={"pricing_file": store.path("pricing.json")})
    write_json(settings.pricing_file, pricing())

    def fail(**kwargs):
        raise RuntimeError("secret-api-key-must-not-appear")

    models = SimpleNamespace(
        generate_content=fail, count_tokens=lambda **kwargs: SimpleNamespace(total_tokens=100)
    )
    monkeypatch.setattr("docgen.model.client_for", lambda *args: SimpleNamespace(models=models))
    model = GeminiModel(settings, store, "test")
    with pytest.raises(ModelFailure) as error:
        model.call("extract", {"source": "fixture"}, Extraction)
    assert "secret-api-key" not in str(error.value)
    assert BudgetLedger(store.path("budget.sqlite")).summary()["charged_pln"] > 0
    assert "secret-api-key" not in store.path("runs/test/events.jsonl").read_text()
