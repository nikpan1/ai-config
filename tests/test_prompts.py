import json

import pytest
from langchain_core.messages import AIMessage

from docgen.config import PROMPTS, Settings
from docgen.llm import Gemini, load_prompt
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
