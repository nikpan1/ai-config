import gc
import json
import sqlite3
import time
import weakref
from dataclasses import replace
from datetime import date, timedelta
from threading import Barrier, Lock
from types import SimpleNamespace

import httpx
import pytest

from docgen_graph.budget import Pricing
from docgen_graph.config import Settings
from docgen_graph.model import GeminiModel, client_for
from docgen_graph.storage import ArtifactStore


@pytest.fixture
def configured_model(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("GEMINI_API_KEY=provider-test-only\n", "utf-8")
    settings = replace(
        Settings.load(env),
        workspace=tmp_path,
        budget_ledger=tmp_path / "cost.sqlite",
        fast_mode=True,
        model_workers=4,
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
    return GeminiModel(settings, ArtifactStore(tmp_path), "parallel-test")


def response(value):
    return SimpleNamespace(
        text=json.dumps(value),
        usage_metadata=SimpleNamespace(
            prompt_token_count=100, candidates_token_count=10, thoughts_token_count=0
        ),
        candidates=[SimpleNamespace(finish_reason=SimpleNamespace(name="STOP"))],
    )


def test_concurrent_first_use_creates_one_client_and_retains_it_during_requests(
    configured_model, monkeypatch
):
    model = configured_model
    barrier = Barrier(4)
    lock = Lock()
    clients = []
    completed = []

    class FakeClient:
        def __init__(self, **kwargs):
            self.state = {"closed": False}
            with lock:
                clients.append(self.state)
            time.sleep(0.05)
            owner = weakref.ref(self)

            def generate(**request):
                barrier.wait(timeout=5)
                client_for.cache_clear()
                gc.collect()
                assert owner() is not None
                assert not owner().state["closed"]
                payload = json.loads(request["contents"])
                with lock:
                    completed.append(payload)
                return response(payload)

            self.models = SimpleNamespace(generate_content=generate)

        def __del__(self):
            self.state["closed"] = True

    monkeypatch.setattr("docgen_graph.model.genai.Client", FakeClient)
    client_for.cache_clear()
    try:
        payloads = [{"index": index} for index in range(4)]
        assert model.call_many("write_section", payloads) == payloads
        assert len(clients) == 1
        assert len(completed) == 4
    finally:
        client_for.cache_clear()


def test_concurrent_requests_keep_order_costs_events_and_independent_cache(
    configured_model, monkeypatch
):
    model = configured_model
    barrier = Barrier(4)
    lock = Lock()
    calls = []

    def generate(**kwargs):
        payload = json.loads(kwargs["contents"])
        with lock:
            calls.append(payload)
        barrier.wait(timeout=5)
        return response(payload)

    monkeypatch.setattr(
        "docgen_graph.model.client_for",
        lambda *args: SimpleNamespace(models=SimpleNamespace(generate_content=generate)),
    )
    payloads = [{"index": index} for index in range(8)]
    assert model.call_many("write_section", payloads) == payloads
    assert model.call_many("write_section", list(reversed(payloads))) == list(reversed(payloads))
    assert len(calls) == 8
    with sqlite3.connect(model.settings.budget_ledger) as connection:
        charges = connection.execute("SELECT status, charged FROM charges").fetchall()
    assert len(charges) == 8
    assert all(status == "settled" and amount > 0 for status, amount in charges)
    events = [
        json.loads(line)
        for line in (model.store.root / "runs/parallel-test/events.jsonl").read_text().splitlines()
    ]
    assert len([event for event in events if event["event"] == "request"]) == 8
    assert len([event for event in events if event["event"] == "response"]) == 8
    assert len([event for event in events if event["event"] == "cache_hit"]) == 8


def test_slow_mode_calls_in_input_order(configured_model, monkeypatch):
    model = configured_model
    model.settings = replace(model.settings, fast_mode=False)
    calls = []

    def call(stage, payload, schema):
        calls.append(payload)
        return payload

    monkeypatch.setattr(model, "call", call)
    payloads = [{"index": index} for index in range(4)]
    assert model.call_many("write_section", payloads) == payloads
    assert calls == payloads


def test_failed_request_keeps_successful_sibling_cached_and_records_uncertain_cost(
    configured_model, monkeypatch
):
    model = configured_model
    barrier = Barrier(2)

    def generate(**kwargs):
        payload = json.loads(kwargs["contents"])
        barrier.wait(timeout=5)
        if payload["index"] == 0:
            raise ConnectionError("Provider connection interrupted")
        return response(payload)

    monkeypatch.setattr(
        "docgen_graph.model.client_for",
        lambda *args: SimpleNamespace(models=SimpleNamespace(generate_content=generate)),
    )
    with pytest.raises(ConnectionError):
        model.call_many("write_section", [{"index": 0}, {"index": 1}])
    assert model.call("write_section", {"index": 1}) == {"index": 1}
    with sqlite3.connect(model.settings.budget_ledger) as connection:
        charges = connection.execute("SELECT status, charged FROM charges").fetchall()
    assert sorted(status for status, amount in charges) == ["settled", "uncertain"]
    assert all(amount > 0 for status, amount in charges)


def test_deadline_prevents_requests_and_reservations(configured_model):
    model = configured_model
    model.set_deadline(time.time() - 1)
    with pytest.raises(TimeoutError, match="runtime limit"):
        model.call_many("write_section", [{"index": index} for index in range(4)])
    with sqlite3.connect(model.settings.budget_ledger) as connection:
        assert connection.execute("SELECT COUNT(*) FROM charges").fetchone()[0] == 0


def test_request_timeout_respects_deadline_and_disables_hidden_retries(
    configured_model, monkeypatch
):
    model = configured_model
    requests = []

    def generate(**kwargs):
        requests.append(kwargs)
        return response({"ok": True})

    monkeypatch.setattr(
        "docgen_graph.model.client_for",
        lambda *args: SimpleNamespace(models=SimpleNamespace(generate_content=generate)),
    )
    model.set_deadline(time.time() + 3)
    assert model.call("write_section", {}) == {"ok": True}
    options = requests[0]["config"].http_options
    assert 0 < options.timeout <= 3000
    assert options.retry_options.attempts == 1


def test_provider_timeout_at_deadline_is_reported_as_run_timeout(configured_model, monkeypatch):
    model = configured_model
    requests = []

    def generate(**kwargs):
        requests.append(kwargs)
        model.set_deadline(time.time() - 1)
        raise httpx.ReadTimeout("Provider did not respond")

    monkeypatch.setattr(
        "docgen_graph.model.client_for",
        lambda *args: SimpleNamespace(models=SimpleNamespace(generate_content=generate)),
    )
    model.set_deadline(time.time() + 60)
    with pytest.raises(TimeoutError, match="runtime limit"):
        model.call("write_section", {})
    assert len(requests) == 1
    with sqlite3.connect(model.settings.budget_ledger) as connection:
        assert connection.execute("SELECT status FROM charges").fetchall() == [("uncertain",)]


@pytest.mark.parametrize(
    "setting,value",
    [
        ("DOCGEN_FAST_MODE", "maybe"),
        ("DOCGEN_MODEL_WORKERS", "0"),
        ("DOCGEN_MODEL_WORKERS", "33"),
        ("DOCGEN_RUN_TIMEOUT_SECONDS", "-1"),
        ("DOCGEN_MINIMUM_COVERAGE", "nan"),
        ("DOCGEN_MINIMUM_COVERAGE", "1.1"),
        ("DOCGEN_MINIMUM_COVERAGE", "0"),
    ],
)
def test_fast_configuration_rejects_invalid_values(tmp_path, monkeypatch, setting, value):
    monkeypatch.delenv(setting, raising=False)
    env = tmp_path / ".env"
    env.write_text(f"{setting}={value}\n", "utf-8")
    with pytest.raises(ValueError, match=setting):
        Settings.load(env)


def test_fast_configuration_loads_explicit_policy(tmp_path, monkeypatch):
    values = {
        "DOCGEN_FAST_MODE": "true",
        "DOCGEN_MODEL_WORKERS": "6",
        "DOCGEN_RUN_TIMEOUT_SECONDS": "1200",
        "DOCGEN_MINIMUM_COVERAGE": "0.9",
    }
    for key in values:
        monkeypatch.delenv(key, raising=False)
    env = tmp_path / ".env"
    env.write_text("\n".join(f"{key}={value}" for key, value in values.items()), "utf-8")
    settings = Settings.load(env)
    assert settings.fast_mode
    assert settings.model_workers == 6
    assert settings.run_timeout_seconds == 1200
    assert settings.minimum_coverage == 0.9


def test_multimodal_call_passes_image_parts_and_keys_cache_by_image_bytes(
    configured_model, monkeypatch
):
    model = configured_model
    calls = []

    def generate(**kwargs):
        calls.append(kwargs)
        return response({"description": "A form"})

    monkeypatch.setattr(
        "docgen_graph.model.client_for",
        lambda *args: SimpleNamespace(models=SimpleNamespace(generate_content=generate)),
    )
    first = [{"data": b"first-image", "mime_type": "image/png"}]
    second = [{"data": b"second-image", "mime_type": "image/png"}]
    model.call("describe_image", {"caption": "Form"}, images=first)
    model.call("describe_image", {"caption": "Form"}, images=first)
    model.call("describe_image", {"caption": "Form"}, images=second)
    assert len(calls) == 2
    assert calls[0]["contents"][0].parts[1].inline_data.data == b"first-image"
    assert calls[0]["contents"][0].parts[1].inline_data.mime_type == "image/png"
    with sqlite3.connect(model.settings.budget_ledger) as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM charges WHERE status='settled'").fetchone()[0]
            == 2
        )
