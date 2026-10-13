import json
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from importlib.resources import files
from threading import Lock

import httpx
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

    def inventory(directory, prefix=""):
        result = {}
        for item in directory.iterdir():
            name = prefix + item.name
            if item.is_dir() and item.name != "__pycache__":
                result.update(inventory(item, name + "/"))
            elif item.name.endswith((".py", ".txt", ".json")):
                result[name] = item.read_bytes().hex()
        return result

    return digest(inventory(package))


def response_schema(schema) -> dict | None:
    if schema is None:
        return None
    original = schema.model_json_schema()
    definitions = original.get("$defs", {})

    def simplify(node):
        if "$ref" in node:
            return simplify(definitions[node["$ref"].rsplit("/", 1)[-1]])
        result = {key: node[key] for key in ("type", "enum", "minItems", "maxItems") if key in node}
        if "properties" in node:
            result["properties"] = {
                key: simplify(value)
                for key, value in node["properties"].items()
                if key != "schema_version"
            }
            result["required"] = list(result["properties"])
        if "items" in node:
            result["items"] = simplify(node["items"])
        if "additionalProperties" in node:
            additional = node["additionalProperties"]
            result["additionalProperties"] = (
                simplify(additional) if isinstance(additional, dict) else additional
            )
        if "anyOf" in node:
            result["anyOf"] = [simplify(value) for value in node["anyOf"]]
        return result

    return simplify(original)


class GeminiModel:
    provider = "gemini"

    def __init__(self, settings: Settings, store: ArtifactStore, run_id: str):
        self.settings = settings
        self.store = store
        self.run_id = run_id
        self._deadline = None
        self._event_lock = Lock()

    def set_deadline(self, epoch_seconds: float | None) -> None:
        self._deadline = epoch_seconds

    def remaining_seconds(self) -> float:
        if self._deadline is None:
            return float(self.settings.timeout_seconds)
        remaining = self._deadline - time.time()
        if remaining <= 0:
            raise TimeoutError("Pipeline runtime limit reached")
        return min(float(self.settings.timeout_seconds), remaining)

    def event(self, stage: str, event: str, **fields) -> None:
        with self._event_lock:
            self.store.event(self.run_id, stage, event, **fields)

    def call_many(self, stage: str, payloads: list[dict], schema=None) -> list[dict]:
        if not self.settings.fast_mode or len(payloads) < 2:
            return [self.call(stage, payload, schema) for payload in payloads]
        client_for(self.settings.api_key, self.settings.timeout_seconds)
        with ThreadPoolExecutor(max_workers=self.settings.model_workers) as executor:
            futures = [executor.submit(self.call, stage, payload, schema) for payload in payloads]
            try:
                return [future.result() for future in futures]
            except BaseException:
                for future in futures:
                    future.cancel()
                raise

    def tool_turn(self, payload: dict, messages: list[dict], declarations: list[dict]) -> dict:
        return self.call("authoring_action", payload, tools=declarations, messages=messages)

    def call(
        self, stage: str, payload: dict, schema=None, *, tools=None, messages=None, images=None
    ) -> dict:
        self.remaining_seconds()
        prompt = files("docgen_graph").joinpath("prompts", f"{stage}.v1.txt").read_text("utf-8")
        thinking_level = self.settings.thinking_level
        if stage.startswith(("verify_", "audit_")):
            thinking_level = self.settings.audit_thinking_level or thinking_level
        signature = digest(
            [
                self.settings.model,
                prompt,
                payload,
                self.settings.output_tokens,
                thinking_level,
                implementation_signature(),
                schema.model_json_schema() if schema else None,
                tools,
                messages,
                [
                    {"hash": digest(item["data"]), "mime_type": item["mime_type"]}
                    for item in (images or [])
                ],
            ]
        )
        cache_path = self.store.root / "cache" / f"{signature}.json"
        if cache_path.is_file():
            cached = json.loads(cache_path.read_text("utf-8"))
            if digest(cached["result"]) != cached["digest"]:
                raise ValueError("Cached model response failed integrity check")
            self.event(stage, "cache_hit", key=signature)
            return (
                schema.model_validate(cached["result"]).model_dump() if schema else cached["result"]
            )
        if not self.settings.api_key or self.settings.api_key == "replace-with-api-key":
            raise ValueError("GEMINI_API_KEY is required")
        request = json.dumps(payload, ensure_ascii=False)
        image_parts = [
            types.Part.from_bytes(data=item["data"], mime_type=item["mime_type"])
            for item in (images or [])
        ]
        contents = [types.Content(role="user", parts=[types.Part(text=request), *image_parts])]
        contents.extend(types.Content.model_validate(item) for item in (messages or []))
        context = json.dumps([payload, messages or []], ensure_ascii=False)
        image_token_reserve = 8192 * len(image_parts)
        conservative_input_allowance = len((prompt + context).encode()) + image_token_reserve
        if (
            conservative_input_allowance + self.settings.output_tokens
            > self.settings.request_tokens
        ):
            raise ValueError("Model request exceeds configured context budget (conservative bound)")
        pricing = Pricing.load(self.settings.pricing_file)
        ledger = BudgetLedger(self.settings.budget_ledger, self.settings.budget_pln)
        reserve = pricing.cost(
            conservative_input_allowance + 4096,
            self.settings.output_tokens * 2,
        )
        for attempt in range(3):
            timeout_ms = max(1, int(self.remaining_seconds() * 1000))
            reservation = ledger.reserve(self.run_id, stage, max(reserve * 1.5, 0.01), pricing)
            started = time.monotonic()
            self.event(
                stage,
                "request",
                key=signature,
                attempt=attempt + 1,
                reservation=reservation,
                conservative_input_allowance=conservative_input_allowance,
            )
            try:
                client = client_for(self.settings.api_key, self.settings.timeout_seconds)
                response = client.models.generate_content(
                    model=self.settings.model,
                    contents=contents if tools or image_parts else request,
                    config=types.GenerateContentConfig(
                        http_options=types.HttpOptions(
                            timeout=timeout_ms,
                            retry_options=types.HttpRetryOptions(attempts=1),
                        ),
                        system_instruction=prompt,
                        response_mime_type=None if tools else "application/json",
                        response_json_schema=None if tools else response_schema(schema),
                        max_output_tokens=self.settings.output_tokens,
                        thinking_config=types.ThinkingConfig(thinking_level=thinking_level.upper())
                        if thinking_level
                        else None,
                        tools=[types.Tool(function_declarations=tools)] if tools else None,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(
                            disable=True
                        ),
                    ),
                )
            except Exception as error:
                ledger.settle(reservation, None, {"error_type": type(error).__name__})
                self.event(
                    stage,
                    "provider_error",
                    error_type=type(error).__name__,
                    seconds=time.monotonic() - started,
                    attempt=attempt + 1,
                )
                if self._deadline is not None and time.time() >= self._deadline:
                    raise TimeoutError("Pipeline runtime limit reached") from error
                retryable = isinstance(error, (TimeoutError, httpx.TransportError)) or (
                    isinstance(error, errors.APIError) and error.code in {429, 500, 502, 503, 504}
                )
                if retryable and attempt < 2:
                    time.sleep(min(2**attempt, self.remaining_seconds()))
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
            if (
                (not tools and not response.text)
                or not counts
                or getattr(finish, "name", None) != "STOP"
            ):
                ledger.settle(reservation, None, {"status": "incomplete", "usage": counts})
                self.store.write(
                    f"runs/{self.run_id}/incomplete/{stage}-{signature}.json",
                    response.model_dump_json(exclude_none=True),
                )
                self.event(
                    stage,
                    "incomplete_response",
                    finish_reason=getattr(finish, "name", None),
                    usage=counts,
                )
                raise ValueError("Incomplete or truncated Gemini response")
            try:
                if tools:
                    content = response.candidates[0].content
                    calls = [
                        part.function_call.model_dump(mode="json", exclude_none=True)
                        for part in content.parts
                        if part.function_call
                    ]
                    result = {
                        "content": content.model_dump(mode="json", exclude_none=True),
                        "calls": calls,
                        "text": response.text or "",
                    }
                else:
                    result = json.loads(response.text)
            except json.JSONDecodeError:
                ledger.settle(reservation, None, {"status": "invalid_json", "usage": counts})
                raise
            if schema:
                try:
                    result = schema.model_validate(result).model_dump()
                except ValueError as error:
                    self.store.write(
                        f"runs/{self.run_id}/invalid/{stage}-{reservation}.json",
                        json.dumps({"result": result, "error": str(error), "usage": counts}),
                    )
                    ledger.settle(
                        reservation,
                        pricing.cost(counts["input_tokens"], counts["output_tokens"]),
                        {**counts, "status": "invalid_schema"},
                    )
                    self.event(
                        stage,
                        "invalid_schema",
                        reservation=reservation,
                        cost_pln=pricing.cost(counts["input_tokens"], counts["output_tokens"]),
                        attempt=attempt + 1,
                    )
                    if attempt < 2:
                        request = json.dumps(
                            {**payload, "schema_feedback": str(error)[:4000]}, ensure_ascii=False
                        )
                        contents[0] = types.Content(
                            role="user", parts=[types.Part(text=request), *image_parts]
                        )
                        size = len((prompt + request).encode()) + image_token_reserve
                        if size + self.settings.output_tokens > self.settings.request_tokens:
                            raise
                        reserve = max(
                            reserve, pricing.cost(size + 4096, self.settings.output_tokens * 2)
                        )
                        continue
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
            actual_cost = pricing.cost(counts["input_tokens"], counts["output_tokens"])
            ledger.settle(reservation, actual_cost, counts)
            self.event(
                stage,
                "response",
                key=signature,
                usage=counts,
                cost_pln=actual_cost,
                seconds=time.monotonic() - started,
                attempt=attempt + 1,
            )
            return result
        raise RuntimeError("Gemini attempts exhausted")
