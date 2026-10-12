import json
import sys
from importlib.resources import files

from docgen_graph.code_analysis.native_codex import restricted_config, validate_effective_config
from docgen_graph.contracts import CodeAnalysisDraft


def run(request):
    from openai_codex import ApprovalMode, Codex
    from openai_codex.generated.v2_all import ConfigReadResponse

    config = restricted_config(request["workspace"], request["runtime_home"])
    with Codex(config) as client:
        response = client._client.request(
            "config/read", {"cwd": request["workspace"]}, response_model=ConfigReadResponse
        )
        validate_effective_config(
            response.model_dump(mode="json", by_alias=True)["config"],
            client._client._runtime_version,
        )
        client.login_api_key(request["api_key"])
        prompt = files("docgen_graph").joinpath("prompts", "analyze_code.v1.txt").read_text("utf-8")
        thread = client.thread_start(
            model=request["model"],
            cwd=request["workspace"],
            approval_mode=ApprovalMode.deny_all,
            ephemeral=True,
            developer_instructions=prompt,
        )
        result = thread.run(
            json.dumps(request["payload"], ensure_ascii=False),
            output_schema=CodeAnalysisDraft.model_json_schema(),
        )
        if result.status.value != "completed" or not result.final_response:
            raise ValueError("Codex analysis did not complete")
        if len(result.final_response.encode()) > request["result_limit"]:
            raise ValueError("Codex analysis result exceeds its limit")
        usage = result.usage.last if result.usage else None
        return {
            "status": "ok",
            "result": json.loads(result.final_response),
            "session_id": thread.id,
            "request_id": result.id,
            "usage": {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens}
            if usage
            else None,
        }


def main():
    try:
        result = run(json.load(sys.stdin))
    except Exception as error:
        result = {"status": "unavailable", "error_type": type(error).__name__}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
