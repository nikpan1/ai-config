import json
from dataclasses import replace
from pathlib import Path

from dotenv import dotenv_values

from docgen_graph.config import Settings
from docgen_graph.contracts import CodeAnalysisDraft
from docgen_graph.model import GeminiModel
from docgen_graph.storage import ArtifactStore


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    key = str(dotenv_values(root / ".env").get("GEMINI_API_KEY") or "")
    settings = replace(Settings.load(), api_key=key)
    if not key:
        raise ValueError("GEMINI_API_KEY is missing from repository .env")
    model = GeminiModel(settings, ArtifactStore(settings.workspace), "docgen-live-smoke")
    response = model.call(
        "analyze_code",
        {
            "spans": [
                {
                    "id": "smoke-code-1",
                    "kind": "code",
                    "path": "example.py",
                    "start_line": 1,
                    "end_line": 3,
                    "text": "def choose(value):\n    if value is None:\n        raise ValueError()",
                }
            ],
            "analysis": {"example.py": {"capability": "python_ast", "symbols": ["choose"]}},
            "feedback": [],
            "previous": None,
        },
        CodeAnalysisDraft,
    )
    result = {
        "schema_valid": True,
        "detail_count": len(response["details"]),
        "evidence_ids": sorted(
            {key for item in response["details"] for key in item["evidence_ids"]}
        ),
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
