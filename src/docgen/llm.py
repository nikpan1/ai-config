import base64
import json
import mimetypes
import os
import time
from importlib.resources import files
from pathlib import Path
from typing import Any, Protocol, TypeVar

import yaml
from langchain_core.exceptions import ModelAPIError, ModelRateLimitError
from langchain_core.messages import HumanMessage, messages_to_dict
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from docgen.config import Settings
from docgen.storage import Store, digest, now, write_json

T = TypeVar("T", bound=BaseModel)


def load_prompt(name: str) -> tuple[dict, str, str]:
    if not name.replace("_", "").isalnum():
        raise ValueError("Invalid prompt ID")
    raw = files("docgen").joinpath("prompts", f"{name}.yaml").read_text("utf-8")
    spec = yaml.safe_load(raw)
    if spec["id"] != name:
        raise ValueError("Prompt ID does not match resource")
    prompt = ChatPromptTemplate.from_messages(
        [(m["role"], m["template"]) for m in spec["messages"]]
    )
    if set(prompt.input_variables) != set(spec["variables"]):
        raise ValueError(f"Undeclared prompt variables in {name}")
    return spec, digest(raw.encode()), raw


class ModelCaller(Protocol):
    def call(
        self,
        prompt: str,
        context: dict,
        schema: type[T],
        directory: Path,
        images: list[Path] | None = None,
    ) -> T: ...


def model_factory(settings: Settings) -> ChatGoogleGenerativeAI:
    if not settings.model:
        raise ValueError("Set a Gemini model ID in your configuration before running extraction")
    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ValueError("Set GOOGLE_API_KEY or GEMINI_API_KEY before running extraction")
    return ChatGoogleGenerativeAI(
        model=settings.model,
        api_key=key,
        vertexai=False,
        temperature=settings.temperature,
        max_tokens=settings.max_output_tokens,
        timeout=settings.timeout_seconds,
        max_retries=0,
    )


class Gemini:
    def __init__(self, settings: Settings, store: Store):
        self.settings, self.store = settings, store
        self.model: Any = None
        self.last_call = 0.0

    def call(
        self,
        prompt: str,
        context: dict,
        schema: type[T],
        directory: Path,
        images: list[Path] | None = None,
    ) -> T:
        spec, checksum, raw = load_prompt(prompt)
        supplied = {"context": json.dumps(context, ensure_ascii=False)}
        if len(supplied["context"]) > self.settings.context_chars:
            raise ValueError(
                f"Context limit exceeded for {prompt}; narrow scope or increase context_chars"
            )
        template = ChatPromptTemplate.from_messages(
            [(m["role"], m["template"]) for m in spec["messages"]]
        )
        messages = template.invoke(supplied).to_messages()
        for path in images or []:
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            mime = mimetypes.guess_type(path.name)[0] or "image/png"
            messages.append(
                HumanMessage(
                    content=[
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}}
                    ]
                )
            )
        if self.model is None:
            self.model = model_factory(self.settings)
        runnable = self.model.with_structured_output(schema, method="json_schema", include_raw=True)
        for retry in range(self.settings.retries + 1):
            usage = self.store.manifest["usage"]
            reserve = (
                len(supplied["context"])
                + self.settings.max_output_tokens
                + 4096 * len(images or [])
            )
            if (
                usage["calls"] >= self.settings.max_calls
                or usage["reserved_tokens"] + reserve > self.settings.token_budget
            ):
                raise ValueError("Run budget exhausted; raise limits explicitly to continue")
            usage["calls"] += 1
            usage["reserved_tokens"] += reserve
            self.store.save()
            folder = directory / "model-calls" / f"{usage['calls']:05d}-{prompt}"
            write_json(
                folder / "request.json",
                {
                    "prompt_id": prompt,
                    "prompt_hash": checksum,
                    "template": raw,
                    "variables": supplied,
                    "messages": messages_to_dict(messages),
                    "settings": self.settings.model_dump(),
                    "schema": schema.model_json_schema(),
                    "assets": [str(p.relative_to(self.store.root)) for p in images or []],
                    "started_at": now(),
                    "retry": retry,
                },
            )
            category = "transport"
            try:
                time.sleep(
                    max(0, self.settings.min_call_interval - (time.monotonic() - self.last_call))
                )
                self.last_call = time.monotonic()
                response = runnable.invoke(messages)
                raw_response = response["raw"]
                write_json(folder / "response.json", raw_response.model_dump(mode="json"))
                metadata = raw_response.usage_metadata or {}
                usage["input_tokens"] += metadata.get("input_tokens", 0)
                usage["output_tokens"] += metadata.get("output_tokens", 0)
                self.store.save()
                finish = str(raw_response.response_metadata.get("finish_reason", ""))
                if "MAX_TOKENS" in finish:
                    category = "truncated"
                    raise ValueError("Output token limit reached")
                if raw_response.response_metadata.get("prompt_feedback", {}).get("block_reason"):
                    category = "blocked"
                    raise ValueError("Model response blocked")
                if response.get("parsing_error") or response.get("parsed") is None:
                    category = "schema" if raw_response.content else "empty"
                    raise ValueError(
                        "Malformed, blocked or truncated structured model response; "
                        "inspect response.json"
                    )
                return schema.model_validate(response["parsed"])
            except Exception as exc:
                # Transport errors may include credentials or request URLs.
                status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
                cause = exc.__cause__
                if status is None and cause is not None:
                    status = getattr(cause, "status_code", None) or getattr(cause, "code", None)
                transient = status in {429, 500, 502, 503, 504} or isinstance(
                    exc, (TimeoutError, ConnectionError, ModelAPIError, ModelRateLimitError)
                )
                if isinstance(exc, ModelRateLimitError) or status == 429:
                    category = "quota"
                write_json(
                    folder / "error.json",
                    {
                        "type": type(exc).__name__,
                        "category": category,
                        "transient": transient,
                        "time": now(),
                    },
                )
                if not transient or retry == self.settings.retries:
                    raise ValueError(
                        f"Model request failed ({type(exc).__name__}); inspect model-calls"
                    ) from None
                time.sleep(min(2**retry, 8))
        raise RuntimeError("Unreachable retry state")
