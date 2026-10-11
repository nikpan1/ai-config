import time
from functools import lru_cache
from importlib.resources import files

from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from docgen.budget import BudgetLedger, load_pricing
from docgen.config import Settings
from docgen.ingestion import estimate_tokens
from docgen.storage import Artifacts, digest, encode, read_json, write_json


class TruncatedOutput(RuntimeError):
    pass


class ModelFailure(RuntimeError):
    pass


class RequestTooLarge(RuntimeError):
    pass


@lru_cache(maxsize=4)
def client_for(key: str, timeout_seconds: int):
    return genai.Client(
        api_key=key,
        http_options=types.HttpOptions(
            timeout=timeout_seconds * 1000, retry_options=types.HttpRetryOptions(attempts=1)
        ),
    )


def prompt_text(stage: str) -> str:
    return files("docgen").joinpath("prompts", f"{stage}.v1.txt").read_text(encoding="utf-8")


def implementation_signature() -> str:
    root = files("docgen")
    names = sorted(p.name for p in root.iterdir() if p.name.endswith(".py"))
    return digest({name: root.joinpath(name).read_text(encoding="utf-8") for name in names})


class GeminiModel:
    def __init__(self, settings: Settings, store: Artifacts, run_id: str):
        self.settings = settings
        self.store = store
        self.run_id = run_id
        self.ledger = BudgetLedger(settings.budget_ledger, settings.budget_pln)

    def call(self, stage: str, payload: dict, schema: type[BaseModel]):
        from docgen.signatures import workflow_manifest

        instruction = prompt_text(stage)
        generation = stage.startswith("gen_")
        output_tokens = (
            min(
                payload.get("generation_output_limit", self.settings.output_tokens),
                self.settings.output_tokens,
            )
            if generation
            else self.settings.output_tokens
        )
        request = encode(payload)
        schema_json = schema.model_json_schema()
        signature = digest(
            [
                instruction,
                payload,
                schema_json,
                self.settings.signature(),
                workflow_manifest(
                    "documentation_generation"
                    if generation
                    else "documentation_planning"
                    if stage.startswith("plan_")
                    else "knowledge"
                ),
            ]
        )
        cache_path = self.store.path(f"cache/{signature}.json")
        if not generation and cache_path.exists():
            cached = read_json(cache_path)
            if digest(cached["result"]) != cached["checksum"]:
                raise ValueError("Model cache integrity check failed")
            self.store.event(self.run_id, stage=stage, event="cache_hit", key=signature)
            return schema.model_validate(cached["result"])
        material = instruction + request + encode(schema_json)
        estimated = estimate_tokens(material)
        if estimated + output_tokens > self.settings.request_tokens:
            raise RequestTooLarge("Serialized request exceeds configured context budget")
        key = self.settings.gemini_api_key.get_secret_value()
        if not key:
            raise ValueError("GEMINI_API_KEY is required for live execution")
        pricing = load_pricing(self.settings.pricing_file)
        reservation = pricing.cost(len(material.encode("utf-8")) + 4096, 65536)
        reservation *= self.settings.billing_headroom
        client = client_for(key, self.settings.timeout_seconds)
        try:
            counted = client.models.count_tokens(
                model=self.settings.gemini_model,
                contents=instruction + "\n\n" + request,
            ).total_tokens
        except Exception as error:
            raise ModelFailure(f"Token preflight failed ({type(error).__name__})") from None
        input_bound = (
            (counted or len(material.encode("utf-8")))
            + len(encode(schema_json).encode("utf-8"))
            + 4096
        )
        if input_bound + output_tokens > self.settings.request_tokens:
            raise RequestTooLarge("Counted request plus schema and output headroom exceeds budget")
        for attempt in range(self.settings.technical_retries + 1):
            charge = self.ledger.reserve(self.run_id, stage, reservation, pricing)
            started = time.monotonic()
            self.store.event(
                self.run_id,
                stage=stage,
                event="request",
                key=signature,
                attempt=attempt + 1,
                reserved_pln=reservation,
                estimated_input_tokens=estimated,
            )
            try:
                response = client.models.generate_content(
                    model=self.settings.gemini_model,
                    contents=request,
                    config=types.GenerateContentConfig(
                        system_instruction=instruction,
                        response_mime_type="application/json",
                        response_json_schema=schema_json,
                        max_output_tokens=output_tokens,
                        thinking_config=types.ThinkingConfig(
                            thinking_level=self.settings.thinking_level
                        ),
                    ),
                )
            except Exception as error:
                self.ledger.settle(charge, None, {"error_type": type(error).__name__})
                self.store.event(
                    self.run_id,
                    stage=stage,
                    event="technical_failure",
                    error_type=type(error).__name__,
                    seconds=time.monotonic() - started,
                )
                retryable = isinstance(error, errors.APIError) and error.code in {
                    429,
                    500,
                    502,
                    503,
                    504,
                }
                if retryable and attempt < self.settings.technical_retries:
                    time.sleep(min(2**attempt, 8))
                    continue
                raise ModelFailure(
                    f"Gemini request failed ({type(error).__name__}); checkpoint retained"
                ) from None
            usage = response.usage_metadata
            counts = usage.model_dump(mode="json") if usage else {}
            input_count = (usage.prompt_token_count or 0) if usage else 0
            output_count = (
                ((usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0))
                if usage
                else 0
            )
            if usage and usage.total_token_count:
                output_count = max(output_count, usage.total_token_count - input_count)
            actual = (
                pricing.cost(input_count, output_count) * self.settings.billing_headroom
                if usage
                else None
            )
            self.ledger.settle(charge, actual, counts)
            raw_ref = self.store.put(response.model_dump(mode="json"), "response")
            self.store.event(
                self.run_id,
                stage=stage,
                event="response",
                key=signature,
                usage=counts,
                charged_pln=actual,
                seconds=time.monotonic() - started,
                response_ref=raw_ref,
            )
            candidates = response.candidates or []
            reason = str(candidates[0].finish_reason) if candidates else "EMPTY"
            if "MAX_TOKENS" in reason:
                raise TruncatedOutput("Gemini output truncated; split the batch")
            if "STOP" not in reason or not response.text:
                raise ModelFailure("Gemini returned no complete candidate; checkpoint retained")
            result = schema.model_validate_json(response.text)
            value = result.model_dump(mode="json")
            if not generation:
                write_json(
                    cache_path,
                    {"result": value, "checksum": digest(value), "response_ref": raw_ref},
                )
            return result
        raise ModelFailure("Retry limit reached")
