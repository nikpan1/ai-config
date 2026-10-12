import copy
import json
import sqlite3
from datetime import date
from types import SimpleNamespace

import pytest

from docgen_graph.code_analysis.allowance import ProviderAllowance
from docgen_graph.code_analysis.backends import candidate_packet
from docgen_graph.code_analysis.native_codex import (
    DISABLED_FEATURES,
    PINNED_CODEX_VERSION,
    validate_effective_config,
)


def effective_config():
    return {
        "default_permissions": "docgen-analysis",
        "permissions": {
            "docgen-analysis": {
                "filesystem": {":root": "deny", ":minimal": "read", ":workspace_roots": "read"},
                "network": {"enabled": False},
            }
        },
        "features": dict.fromkeys(DISABLED_FEATURES, False),
        "web_search": "disabled",
        "mcp_servers": {},
    }


@pytest.mark.parametrize("escape", ["shell", "network", "root", "legacy", "mcp", "version"])
def test_codex_rejects_effective_policy_broadening(escape):
    config = effective_config()
    validate_effective_config(config, PINNED_CODEX_VERSION)
    modified = copy.deepcopy(config)
    version = PINNED_CODEX_VERSION
    if escape == "shell":
        modified["features"]["shell_tool"] = True
    elif escape == "network":
        modified["permissions"]["docgen-analysis"]["network"]["enabled"] = True
    elif escape == "root":
        modified["permissions"]["docgen-analysis"]["filesystem"][":root"] = "read"
    elif escape == "legacy":
        modified["sandbox_mode"] = "read-only"
    elif escape == "mcp":
        modified["mcp_servers"] = {"external": {"command": "server"}}
    else:
        version = "0.162.0"
    with pytest.raises(ValueError):
        validate_effective_config(modified, version)


def test_codex_worker_checks_permissions_before_authentication(monkeypatch):
    import openai_codex

    from docgen_graph.code_analysis.sdk_worker import run

    authenticated = []

    class Client:
        def __init__(self, config):
            self._client = self
            self._runtime_version = PINNED_CODEX_VERSION

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def request(self, *args, **kwargs):
            return SimpleNamespace(model_dump=lambda **kw: {"config": {}})

        def login_api_key(self, key):
            authenticated.append(key)

    monkeypatch.setattr(openai_codex, "Codex", Client)
    with pytest.raises(ValueError, match="restricted profile"):
        run({"workspace": "empty", "runtime_home": "isolated", "api_key": "unused"})
    assert not authenticated


def test_provider_allowance_shares_prior_gemini_charges(tmp_path):
    ledger = tmp_path / "budget.sqlite"
    with sqlite3.connect(ledger) as connection:
        connection.execute(
            "CREATE TABLE charges (id TEXT PRIMARY KEY, run_id TEXT, stage TEXT, "
            "time TEXT, reserved REAL, charged REAL, status TEXT, usage TEXT, pricing TEXT)"
        )
        connection.execute(
            "INSERT INTO charges VALUES ('old','old','gemini','now',0,199,'settled','{}','{}')"
        )
    today = date.today().isoformat()
    path = tmp_path / "allowance.json"
    path.write_text(
        json.dumps(
            {
                "provider": "codex_sdk",
                "model": "explicit-model",
                "authorization_ref": "test-only",
                "authorized_budget_pln": 1000,
                "reservation_pln": 2,
                "pricing": {
                    "model": "explicit-model",
                    "input_usd_per_million": 1,
                    "output_usd_per_million": 1,
                    "usd_pln": 4,
                    "verified_on": today,
                    "valid_until": today,
                    "exchange_date": today,
                    "pricing_source": "test-only",
                    "exchange_source": "test-only",
                },
            }
        )
    )
    settings = SimpleNamespace(
        code_provider_allowance_file=path,
        code_analysis_backend="codex_sdk",
        code_analysis_model="explicit-model",
        code_analysis_turn_limit=2,
        budget_ledger=ledger,
        budget_pln=200,
        request_tokens=1000,
        output_tokens=1000,
    )
    allowance = ProviderAllowance(settings, "new")
    with pytest.raises(ValueError, match="Budget exhausted"):
        allowance.reserve("codex_sdk", "explicit-model", "request")
    assert allowance.ledger.summary()["charged_pln"] == 199
    assert allowance.ledger.summary()["limit_pln"] == 200


def test_code_relation_uses_context_evidence_and_validated_endpoints():
    payload = {"spans": [{"id": "e1"}], "context": [{"id": "e2"}]}
    raw = {
        "report": "Verified later",
        "details": [
            {"statement": "Flag enables control", "evidence_ids": ["e1"]},
            {"statement": "Role permits submission", "evidence_ids": ["e2"]},
        ],
        "relations": [
            {
                "type": "QUALIFIES",
                "source_fact_index": 1,
                "target_fact_index": 0,
                "method": "candidate",
                "evidence_ids": ["e2"],
            }
        ],
    }
    packet = candidate_packet(raw, payload, "codex_sdk", "explicit-model")
    assert packet.relations[0].source_id == packet.facts[1].id
    assert packet.relations[0].evidence_ids == ["e2"]
    raw["relations"][0]["target_fact_index"] = 8
    with pytest.raises(ValueError, match="unknown candidate fact"):
        candidate_packet(raw, payload, "codex_sdk", "explicit-model")
