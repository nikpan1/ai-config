import json
import time
from functools import lru_cache
from importlib.resources import files

from google import genai
from google.genai import errors, types

from docgen_graph.budget import BudgetLedger, Pricing
from docgen_graph.config import Settings
from docgen_graph.storage import ArtifactStore, digest


@lru_cache(maxsize=4)
def client_for(api_key: str, timeout_seconds: int):
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=timeout_seconds * 1000),
    )


@lru_cache(maxsize=1)
def implementation_signature() -> str:
    package = files("docgen_graph")
    return digest(
        {
            item.name: item.read_bytes().hex()
            for item in package.iterdir()
            if item.name.endswith(".py")
        }
    )


def response_schema(schema) -> dict | None:
    if schema is None:
        return None
    original = schema.model_json_schema()
    definitions = original.get("$defs", {})

    def simplify(node):
        if "$ref" in node:
            return simplify(definitions[node["$ref"].rsplit("/", 1)[-1]])
        result = {key: node[key] for key in ("type", "enum") if key in node}
        if "properties" in node:
            result["properties"] = {
                key: simplify(value)
                for key, value in node["properties"].items()
                if key != "schema_version"
            }
            result["required"] = list(result["properties"])
        if "items" in node:
            result["items"] = simplify(node["items"])
        if "anyOf" in node:
            result["anyOf"] = [simplify(value) for value in node["anyOf"]]
        return result

    return simplify(original)


class GeminiModel:
    def __init__(self, settings: Settings, store: ArtifactStore, run_id: str):
        self.settings = settings
        self.store = store
        self.run_id = run_id

    def call(self, stage: str, payload: dict, schema=None) -> dict:
        prompt = files("docgen_graph").joinpath("prompts", f"{stage}.v1.txt").read_text("utf-8")
        signature = digest(
            [
                self.settings.model,
                prompt,
                payload,
                self.settings.output_tokens,
                implementation_signature(),
                schema.model_json_schema() if schema else None,
            ]
        )
        cache_path = self.store.root / "cache" / f"{signature}.json"
        if cache_path.is_file():
            cached = json.loads(cache_path.read_text("utf-8"))
            if digest(cached["result"]) != cached["digest"]:
                raise ValueError("Cached model response failed integrity check")
            self.store.event(self.run_id, stage, "cache_hit", key=signature)
            return (
                schema.model_validate(cached["result"]).model_dump() if schema else cached["result"]
            )
        if not self.settings.api_key or self.settings.api_key == "replace-with-api-key":
            raise ValueError("GEMINI_API_KEY is required")
        request = json.dumps(payload, ensure_ascii=False)
        if (
            len((prompt + request).encode()) + self.settings.output_tokens
            > self.settings.request_tokens
        ):
            raise ValueError("Model request exceeds configured context budget")
        pricing = Pricing.load(self.settings.pricing_file)
        ledger = BudgetLedger(self.settings.budget_ledger, self.settings.budget_pln)
        reserve = pricing.cost(
            len((prompt + request).encode()) + 4096, self.settings.output_tokens * 2
        )
        for attempt in range(3):
            reservation = ledger.reserve(self.run_id, stage, max(reserve * 1.5, 0.01), pricing)
            started = time.monotonic()
            self.store.event(
                self.run_id,
                stage,
                "request",
                key=signature,
                attempt=attempt + 1,
                reservation=reservation,
            )
            try:
                response = client_for(
                    self.settings.api_key, self.settings.timeout_seconds
                ).models.generate_content(
                    model=self.settings.model,
                    contents=request,
                    config=types.GenerateContentConfig(
                        system_instruction=prompt,
                        response_mime_type="application/json",
                        response_json_schema=response_schema(schema),
                        max_output_tokens=self.settings.output_tokens,
                    ),
                )
            except Exception as error:
                ledger.settle(reservation, None, {"error_type": type(error).__name__})
                self.store.event(
                    self.run_id,
                    stage,
                    "provider_error",
                    error_type=type(error).__name__,
                    seconds=time.monotonic() - started,
                    attempt=attempt + 1,
                )
                retryable = isinstance(error, errors.APIError) and error.code in {
                    429,
                    500,
                    502,
                    503,
                    504,
                }
                if retryable and attempt < 2:
                    time.sleep(2**attempt)
                    continue
                raise
            usage = response.usage_metadata
            finish = response.candidates[0].finish_reason if response.candidates else None
            counts = (
                {
                    "input_tokens": usage.prompt_token_count or 0,
                    "output_tokens": (usage.candidates_token_count or 0)
                    + (usage.thoughts_token_count or 0),
                }
                if usage
                else {}
            )
            if not response.text or not counts or getattr(finish, "name", None) != "STOP":
                ledger.settle(reservation, None, {"status": "incomplete", "usage": counts})
                raise ValueError("Incomplete or truncated Gemini response")
            try:
                result = json.loads(response.text)
            except json.JSONDecodeError:
                ledger.settle(reservation, None, {"status": "invalid_json", "usage": counts})
                raise
            if schema:
                try:
                    result = schema.model_validate(result).model_dump()
                except ValueError:
                    ledger.settle(
                        reservation,
                        pricing.cost(counts["input_tokens"], counts["output_tokens"]),
                        {**counts, "status": "invalid_schema"},
                    )
                    raise
            self.store.write(
                f"cache/{signature}.json",
                json.dumps(
                    {
                        "result": result,
                        "digest": digest(result),
                        "usage": counts,
                        "stage": stage,
                        "completed_at": time.time(),
                    },
                    ensure_ascii=False,
                ),
            )
            ledger.settle(
                reservation, pricing.cost(counts["input_tokens"], counts["output_tokens"]), counts
            )
            self.store.event(
                self.run_id,
                stage,
                "response",
                key=signature,
                usage=counts,
                seconds=time.monotonic() - started,
                attempt=attempt + 1,
            )
            return result
        raise RuntimeError("Gemini attempts exhausted")
