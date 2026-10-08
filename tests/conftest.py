from copy import deepcopy

import pytest

from docgen.config import Settings
from docgen.contracts import Comparison, Extraction, Verification
from docgen.storage import Artifacts


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None,
        gemini_api_key="test-key",
        DOCGEN_WORKSPACE=tmp_path / "workspace",
        DOCGEN_BUDGET_LEDGER=tmp_path / "workspace/budget.sqlite",
    )


@pytest.fixture
def store(settings):
    return Artifacts(settings.workspace)


def extraction_for(payload):
    claims, coverage = [], []
    for index, block in enumerate(payload["owned"]):
        identifier = f"c{index}"
        claims.append(
            {
                "id": identifier,
                "statement": block["content"],
                "entities": [],
                "conditions": [],
                "exceptions": [],
                "frequency_time": None,
                "scope": None,
                "version": None,
                "modality": "unknown",
                "source_status": None,
                "rule_keys": [],
                "evidence": [{"block_id": block["id"], "excerpt": block["content"]}],
            }
        )
        coverage.append(
            {
                "block_id": block["id"],
                "disposition": "represented",
                "claim_ids": [identifier],
                "explanation": "All source text preserved in the fixture claim",
            }
        )
    return Extraction.model_validate(
        {"claims": claims, "entities": [], "coverage": coverage, "findings": []}
    )


class FixtureModel:
    def __init__(self, transform=None):
        self.calls = []
        self.transform = transform

    def call(self, stage, payload, schema):
        self.calls.append(stage)
        if stage == "extract":
            result = extraction_for(payload)
        elif stage == "verify":
            result = Verification(
                findings=[], checked_block_ids=[block["id"] for block in payload["owned"]]
            )
        else:
            result = Comparison(
                relations=[],
                findings=[],
                checked_ids=[record["id"] for record in payload["left"] + payload["right"]],
            )
        return self.transform(stage, deepcopy(payload), result) if self.transform else result
