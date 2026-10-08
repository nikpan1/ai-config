import json

import pytest
from langchain_core.messages import AIMessage

from docgen.config import PROMPTS, Settings
from docgen.llm import Gemini, error_status, load_prompt
from docgen.models import SemanticReview
from docgen.storage import Store, read_json


def test_all_prompts_load_outside_repository(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in {p for prompts in PROMPTS.values() for p in prompts}:
        spec, checksum, raw = load_prompt(name)
        assert spec["id"] == name and len(checksum) == 64 and raw
    with pytest.raises(FileNotFoundError):
        load_prompt("nonexistent")
    with pytest.raises(ValueError):
        load_prompt("../extract_claims")


def test_prompt_variable_validation(monkeypatch):
    class Resource:
        def joinpath(self, *args):
            return self

        def read_text(self, encoding):
            return (
                "id: invalid\nvariables: [context]\nmessages:\n"
                '- role: human\n  template: "{missing}"'
            )

    monkeypatch.setattr("docgen.llm.files", lambda _: Resource())
    with pytest.raises(ValueError, match="Undeclared"):
        load_prompt("invalid")


def test_model_exchange_exact_prompt_and_malformed_response(store, tmp_path):
    class Model:
        def with_structured_output(self, schema, **kwargs):
            assert kwargs["include_raw"] and kwargs["method"] == "json_schema"
            return self

        def invoke(self, messages):
            return {
                "raw": AIMessage(content="malformed"),
                "parsed": None,
                "parsing_error": ValueError("malformed"),
            }

    client = Gemini(Settings(model="test", retries=0), store)
    client.model = Model()
    with pytest.raises(ValueError, match="Model request failed"):
        client.call("review_semantics", {"source": "test"}, SemanticReview, tmp_path)
    folder = next((tmp_path / "model-calls").iterdir())
    request = read_json(folder / "request.json")
    assert request["template"] == load_prompt("review_semantics")[2]
    assert request["prompt_hash"] == load_prompt("review_semantics")[1]
    assert json.loads(request["variables"]["context"]) == {"source": "test"}
    assert read_json(folder / "response.json")["content"] == "malformed"
    assert Store(store.root).manifest["usage"]["calls"] == 1


def test_budget_prevents_request(store, tmp_path):
    client = Gemini(Settings(model="test", max_calls=1), store)
    client.model = type("Model", (), {"with_structured_output": lambda *a, **k: None})()
    store.manifest["usage"]["calls"] = 1
    with pytest.raises(ValueError, match="budget"):
        client.call("review_semantics", {}, SemanticReview, tmp_path)
    assert not (tmp_path / "model-calls").exists()


def test_rate_limit_has_one_bounded_retry_policy(store, tmp_path, monkeypatch):
    from langchain_core.exceptions import ModelRateLimitError

    class Model:
        calls = 0

        def with_structured_output(self, *args, **kwargs):
            return self

        def invoke(self, messages):
            self.calls += 1
            raise ModelRateLimitError("sensitive transport details")

    client = Gemini(Settings(model="test", retries=2), store)
    client.model = Model()
    monkeypatch.setattr("docgen.llm.time.sleep", lambda seconds: None)
    with pytest.raises(ValueError, match="Model request failed"):
        client.call("review_semantics", {}, SemanticReview, tmp_path)
    assert client.model.calls == 3
    for path in tmp_path.glob("model-calls/*/error.json"):
        assert read_json(path)["category"] == "quota"
        assert "sensitive" not in path.read_text("utf-8")


def test_budget_settles_reported_usage_not_cumulative_reservations(store, tmp_path):
    class Model:
        def with_structured_output(self, *args, **kwargs):
            return self

        def invoke(self, messages):
            return {
                "raw": AIMessage(
                    content="{}",
                    usage_metadata={"input_tokens": 20, "output_tokens": 10, "total_tokens": 30},
                ),
                "parsed": SemanticReview(findings=[]),
                "parsing_error": None,
            }

    client = Gemini(Settings(model="test", max_output_tokens=256, token_budget=6000), store)
    client.model = Model()
    for _ in range(10):
        client.call("review_semantics", {}, SemanticReview, tmp_path)
    usage = store.manifest["usage"]
    assert usage["budget_tokens"] == 300
    assert usage["reserved_tokens"] > client.settings.token_budget


def test_missing_usage_keeps_full_reservation(store, tmp_path):
    class Model:
        def with_structured_output(self, *args, **kwargs):
            return self

        def invoke(self, messages):
            return {
                "raw": AIMessage(content="{}"),
                "parsed": SemanticReview(findings=[]),
                "parsing_error": None,
            }

    client = Gemini(Settings(model="test", max_output_tokens=256), store)
    client.model = Model()
    client.call("review_semantics", {}, SemanticReview, tmp_path)
    usage = store.manifest["usage"]
    assert usage["budget_tokens"] == usage["reserved_tokens"] > 0
    client.settings.token_budget = usage["budget_tokens"] + 1
    with pytest.raises(ValueError, match="budget"):
        client.call("review_semantics", {}, SemanticReview, tmp_path)
    assert usage["calls"] == 1


def test_wrapped_provider_status_is_safe_and_retries_are_bounded(store, tmp_path, monkeypatch):
    class ProviderError(Exception):
        code = "503"
        status = "UNAVAILABLE"

    class Model:
        def with_structured_output(self, *args, **kwargs):
            return self

        def invoke(self, messages):
            cause = ProviderError("https://example.test?key=secret")
            middle = ValueError("sensitive wrapper")
            middle.__cause__ = cause
            raise RuntimeError("outer") from middle

    client = Gemini(Settings(model="test", retries=1), store)
    client.model = Model()
    monkeypatch.setattr("docgen.llm.time.sleep", lambda _: None)
    with pytest.raises(ValueError, match="Model request failed"):
        client.call("review_semantics", {}, SemanticReview, tmp_path)
    assert store.manifest["usage"]["calls"] == 2
    for path in tmp_path.glob("model-calls/*/error.json"):
        data = read_json(path)
        assert data["status_code"] == 503 and data["provider_status"] == "UNAVAILABLE"
        assert "secret" not in path.read_text("utf-8")
    assert error_status(ValueError("secret")) == (None, None)


def test_payment_resource_exhaustion_does_not_retry(store, tmp_path, monkeypatch):
    class PaymentError(Exception):
        code = 402
        status = "RESOURCE_EXHAUSTED"

    class Model:
        def with_structured_output(self, *args, **kwargs):
            return self

        def invoke(self, messages):
            raise RuntimeError("wrapper") from PaymentError("private account information")

    client = Gemini(Settings(model="test", retries=2), store)
    client.model = Model()
    monkeypatch.setattr("docgen.llm.time.sleep", lambda _: None)
    with pytest.raises(ValueError, match="status=402"):
        client.call("review_semantics", {}, SemanticReview, tmp_path)
    assert store.manifest["usage"]["calls"] == 1
    error = read_json(next(tmp_path.glob("model-calls/*/error.json")))
    assert error["category"] == "quota" and not error["transient"]
