import json
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Protocol

from docgen_graph.contracts import CodeAnalysisDraft
from docgen_graph.evidence_contracts import (
    AnalysisProvenance,
    EvidenceRelation,
    EvidenceResult,
    FactRecord,
)
from docgen_graph.knowledge import normalized_assertion
from docgen_graph.storage import digest

SDK_VERSIONS = {"codex_sdk": "0.162.1", "auggie_sdk": "0.2.2"}


class CodeAnalysisBackend(Protocol):
    def capabilities(self) -> dict: ...
    def analyze_unit(self, payload: dict) -> EvidenceResult: ...
    def search_code(self, payload: dict) -> EvidenceResult: ...
    def close(self) -> None: ...


def candidate_packet(raw, payload, provider, model, sdk_version="", session_id="", request_id=""):
    draft = CodeAnalysisDraft.model_validate(raw)
    provenance = AnalysisProvenance(
        id=digest([provider, model, sdk_version, payload, request_id]),
        provider=provider,
        model=model,
        sdk_version=sdk_version,
        session_id=session_id,
        request_id=request_id,
        prompt_version="analyze_code.v1",
        input_hash=digest(payload),
        scope_id=payload.get("scope_id", "full"),
        commit=payload.get("code_revision", {}).get("commit"),
        base_commit=payload.get("history", {}).get("base_commit"),
        head_commit=payload.get("history", {}).get("head_commit"),
    )
    allowed = {span["id"] for span in payload["spans"] + payload.get("context", [])}
    facts = [
        FactRecord.model_validate(
            normalized_assertion(
                {
                    **item.model_dump(),
                    "provenance_ids": [provenance.id],
                    "review_status": "unreviewed",
                },
                allowed,
            )
        )
        for item in draft.details
    ]
    relations = []
    for relation in getattr(draft, "relations", []):
        indexes = (relation.source_fact_index, relation.target_fact_index)
        if any(index < 0 or index >= len(facts) for index in indexes):
            raise ValueError("Code relation refers to an unknown candidate fact")
        if not relation.evidence_ids or set(relation.evidence_ids) - allowed:
            raise ValueError("Code relation lacks its own source evidence")
        relations.append(
            EvidenceRelation(
                type=relation.type,
                source_id=facts[indexes[0]].id,
                target_id=facts[indexes[1]].id,
                method=relation.method,
                evidence_ids=relation.evidence_ids,
            )
        )
    return EvidenceResult(
        status="ok",
        facts=facts,
        relations=relations,
        provenance=[provenance],
        warnings=["Candidate facts require an independent Gemini audit"],
    )


class GeminiCodeBackend:
    def __init__(self, model):
        self.model = model

    def capabilities(self):
        return {
            "status": "ok",
            "provider": "gemini",
            "read_only": True,
            "filesystem_tools": False,
            "method": "frozen_context",
        }

    def analyze_unit(self, payload):
        raw = self.model.call("analyze_code", payload, CodeAnalysisDraft)
        return candidate_packet(raw, payload, "gemini", "gemini-3.8-flash")

    def search_code(self, payload):
        return self.analyze_unit(payload)

    def close(self):
        pass


class SDKCodeBackend:
    def __init__(self, settings, store, run_id, frozen_root, transport=None, allowance=None):
        self.settings = settings
        self.store = store
        self.run_id = run_id
        self.frozen_root = Path(frozen_root).resolve()
        self.provider = settings.code_analysis_backend
        self.model = settings.code_analysis_model
        if transport is None and self.provider == "codex_sdk":
            from docgen_graph.code_analysis.native_codex import NativeCodexTransport

            transport = NativeCodexTransport(settings, self.frozen_root)
        self.transport = transport or NativeSDKTransport(self.provider, settings, self.frozen_root)
        self.allowance = allowance
        self.allowance_error = ""
        if self.allowance is None and getattr(settings, "code_provider_allowance_file", None):
            from docgen_graph.code_analysis.allowance import ProviderAllowance

            try:
                self.allowance = ProviderAllowance(settings, run_id)
            except (OSError, ValueError, KeyError, TypeError):
                self.allowance_error = "Provider allowance is missing, stale, or incompatible"

    def capabilities(self):
        return self.transport.capabilities()

    def analyze_unit(self, payload):
        from docgen_graph.model import implementation_signature

        capability = self.capabilities()
        if capability["status"] != "ok":
            return EvidenceResult(status=capability["status"], warnings=[capability["reason"]])
        key = digest(
            [
                self.provider,
                self.model,
                SDK_VERSIONS[self.provider],
                payload,
                self.settings.code_analysis_turn_limit,
                self.settings.code_analysis_result_limit,
                self.settings.code_analysis_timeout,
                implementation_signature(),
            ]
        )
        cache = self.store.root / "code-cache" / f"{key}.json"
        if cache.is_file():
            stored = json.loads(cache.read_text("utf-8"))
            packet = self.store.get(stored["result_ref"])
            return EvidenceResult.model_validate(packet)
        if self.allowance is None:
            return EvidenceResult(
                status="budget_blocked",
                warnings=[
                    self.allowance_error
                    or "Provider calls require a funded allowance and shared-ledger reservation"
                ],
            )
        if len(json.dumps(payload).encode()) > self.settings.request_tokens:
            return EvidenceResult(
                status="unsupported", warnings=["Code context exceeds request limit"]
            )
        try:
            reservation = self.allowance.reserve(self.provider, self.model, key)
        except ValueError:
            return EvidenceResult(
                status="budget_blocked", warnings=["Shared provider budget is exhausted"]
            )
        try:
            response = self.transport.run(payload)
            if len(json.dumps(response).encode()) > self.settings.code_analysis_result_limit:
                raise ValueError("SDK output exceeds the configured result limit")
            packet = candidate_packet(
                response["result"],
                payload,
                self.provider,
                self.model,
                SDK_VERSIONS[self.provider],
                response.get("session_id", ""),
                response.get("request_id", ""),
            )
            packet.usage_ref = reservation
            self.allowance.settle(reservation, response.get("usage"))
            self.store.write(
                f"code-cache/{key}.json",
                json.dumps({"result_ref": self.store.put(packet.model_dump())}),
            )
            return packet
        except Exception as error:
            self.allowance.settle(reservation, None)
            self.transport.close()
            self.store.event(
                self.run_id,
                "analyze_code",
                "provider_failure",
                provider=self.provider,
                request_id=key,
                error_type=type(error).__name__,
            )
            return EvidenceResult(
                status="unavailable",
                warnings=[f"{self.provider} failed: {type(error).__name__}; reservation charged"],
                usage_ref=reservation,
            )

    def search_code(self, payload):
        return self.analyze_unit(payload)

    def close(self):
        self.transport.close()


class NativeSDKTransport:
    def __init__(self, provider, settings, frozen_root):
        self.provider, self.settings, self.frozen_root = provider, settings, frozen_root
        self.client = None

    def capabilities(self):
        package = "openai-codex" if self.provider == "codex_sdk" else "auggie-sdk"
        try:
            installed = version(package)
        except PackageNotFoundError:
            return {"status": "unavailable", "reason": f"Install optional {package} integration"}
        if installed != SDK_VERSIONS[self.provider]:
            return {"status": "unsupported", "reason": "SDK version differs from the verified pin"}
        return {
            "status": "unsupported",
            "provider": self.provider,
            "sdk_version": installed,
            "reason": "Native SDK tool isolation cannot yet be proven for this host; "
            "a verified isolated transport is required before model execution",
        }

    def run(self, payload):
        raise ValueError(self.capabilities()["reason"])

    def close(self):
        if self.client:
            self.client.close()


class AuggieIsolatedTransport:
    def __init__(self, settings, frozen_root, isolation):
        self.settings, self.frozen_root, self.isolation = settings, frozen_root, isolation
        self.client = None

    def capabilities(self):
        return self.isolation.verify(self.frozen_root, "auggie_sdk", SDK_VERSIONS["auggie_sdk"])

    def run(self, payload):
        if self.capabilities()["status"] != "ok":
            raise ValueError("Auggie isolation is unavailable")
        from auggie_sdk import Auggie

        cli_args = ["--max-turns", str(self.settings.code_analysis_turn_limit)]
        for tool in ("terminal", "launch-process", "edit", "write", "web-fetch", "web-search"):
            cli_args.extend(["--permission", tool + ":deny"])
        self.client = Auggie(
            workspace_root=self.frozen_root,
            model=self.settings.code_analysis_model,
            timeout=self.settings.code_analysis_timeout,
            api_key=self.settings.auggie_api_key or None,
            cli_args=cli_args,
        )
        result = self.client.run(
            json.dumps(payload),
            return_type=dict,
            timeout=self.settings.code_analysis_timeout,
            max_retries=0,
            max_verification_rounds=0,
        )
        return {"result": result, "session_id": self.client.session_id or ""}

    def close(self):
        if self.client:
            self.client.close()


class CodexIsolatedTransport:
    def __init__(self, settings, frozen_root, isolation):
        self.settings, self.frozen_root, self.isolation = settings, frozen_root, isolation
        self.client = None

    def capabilities(self):
        return self.isolation.verify(self.frozen_root, "codex_sdk", SDK_VERSIONS["codex_sdk"])

    def run(self, payload):
        if self.capabilities()["status"] != "ok":
            raise ValueError("Codex isolation is unavailable")
        from openai_codex import ApprovalMode, Codex

        self.client = Codex(config=self.isolation.codex_config(self.frozen_root))
        thread = self.client.thread_start(
            model=self.settings.code_analysis_model,
            cwd=str(self.frozen_root),
            approval_mode=ApprovalMode.deny_all,
        )
        result = self.isolation.run_bounded(
            thread,
            json.dumps(payload),
            CodeAnalysisDraft.model_json_schema(),
            self.settings.code_analysis_timeout,
            self.settings.code_analysis_turn_limit,
        )
        return {
            "result": json.loads(result.final_response),
            "session_id": thread.id,
            "request_id": getattr(result, "id", ""),
        }

    def close(self):
        if self.client:
            self.client.close()


def backend_for(model, store, run_id, frozen_root):
    settings = getattr(model, "settings", None)
    if getattr(settings, "code_analysis_backend", "gemini") == "gemini":
        return GeminiCodeBackend(model)
    return SDKCodeBackend(settings, store, run_id, frozen_root)
