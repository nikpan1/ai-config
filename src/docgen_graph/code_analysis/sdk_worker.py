import json
import sys
from importlib.resources import files

from docgen_graph.code_analysis.native_codex import restricted_config, validate_effective_config
from docgen_graph.contracts import CodeAnalysisDraft


def output_schema():
    def strict(node):
        if isinstance(node, list):
            return [strict(value) for value in node]
        if not isinstance(node, dict):
            return node
        result = {key: strict(value) for key, value in node.items() if key != "default"}
        if result.get("type") == "object":
            result["additionalProperties"] = False
            result["required"] = list(result.get("properties", {}))
        return result

    return strict(CodeAnalysisDraft.model_json_schema())


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
            output_schema=output_schema(),
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
    request = {}
    try:
        request = json.load(sys.stdin)
        result = run(request)
    except Exception as error:
        message = str(error)
        if request.get("api_key"):
            message = message.replace(request["api_key"], "[redacted]")
        result = {
            "status": "unavailable",
            "error_type": type(error).__name__,
            "error_message": message[:2000],
        }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
