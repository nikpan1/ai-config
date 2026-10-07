from pathlib import Path

import pytest

from docgen.config import Settings
from docgen.models import ReviewDecision
from docgen.storage import Store, digest
from docgen.workflow import REVIEW_SOURCES, run_pipeline


class FixtureModel:
    """Deterministic test double; never available as a production CLI provider."""

    def __init__(self):
        self.calls = []
        self.fail = None

    def call(self, prompt, context, schema, directory, images=None):
        self.calls.append(prompt)
        if self.fail == prompt:
            raise ValueError("Injected model failure")
        if prompt == "extract_claims":
            spans = context["spans"]
            entities, claims, coverage = [], [], []
            for i, span in enumerate(spans):
                if span["kind"] == "heading":
                    coverage.append(
                        {
                            "evidence_id": span["id"],
                            "disposition": "excluded",
                            "reason": "Section heading",
                        }
                    )
                    continue
                entity_id, claim_id = f"e{i}", f"c{i}"
                entities.append(
                    {
                        "id": entity_id,
                        "type": "capability",
                        "name": "Notification delivery",
                        "evidence_ids": [span["id"]],
                    }
                )
                claims.append(
                    {
                        "id": claim_id,
                        "assertion": span["excerpt"].strip(),
                        "entity_ids": [entity_id],
                        "evidence_ids": [span["id"]],
                    }
                )
                coverage.append(
                    {"evidence_id": span["id"], "disposition": "covered", "claim_ids": [claim_id]}
                )
            value = {
                "entities": entities,
                "claims": claims,
                "relationships": [],
                "coverage": coverage,
            }
        elif prompt == "analyze_image":
            value = {
                "entities": [],
                "claims": [],
                "relationships": [],
                "coverage": [
                    {"evidence_id": e["id"], "disposition": "excluded", "reason": "Fixture image"}
                    for e in context["evidence"]
                ],
                "classification": "decorative",
                "reason": "Fixture",
            }
        elif prompt == "reconcile_entities":
            value = {"aliases": {}, "conflicts": []}
        elif prompt == "plan_outline":
            value = {
                "chapters": [
                    {
                        "id": "notification-delivery",
                        "title": "Notification delivery",
                        "reader_question": "How are messages delivered?",
                        "learning_outcome": "Prepare delivery",
                        "prerequisites": [],
                        "required_claim_ids": [
                            c["id"]
                            for c in context["knowledge"]["claims"]
                            if c["status"] == "accepted"
                        ],
                        "uncovered_topics": [],
                    }
                ]
            }
        elif prompt in {"compose_chapter", "repair_output"}:
            value = {
                "id": context["plan"]["id"],
                "title": context["plan"]["title"],
                "blocks": [
                    {
                        "id": f"block-{i}",
                        "content": " ".join(c["assertion"].replace("|", " ").split()),
                        "claim_ids": [c["id"]],
                        "evidence_ids": c["evidence_ids"],
                        "type": "explanation",
                    }
                    for i, c in enumerate(context["evidence"]["claims"])
                ],
                "diagrams": [],
            }
            for block in value["blocks"]:
                if "[" in block["content"]:
                    block["content"] = "See the retry rules."
        elif prompt == "plan_diagram":
            value = {"diagrams": []}
        elif prompt == "review_semantics":
            value = {"findings": []}
        else:
            raise AssertionError(prompt)
        return schema.model_validate(value)


@pytest.fixture
def model():
    return FixtureModel()


@pytest.fixture
def store(tmp_path):
    source = tmp_path / "input"
    source.mkdir()
    source.joinpath("retry.md").write_bytes(Path("tests/fixtures/retry.md").read_bytes())
    return Store.create(tmp_path / "runs", source, Settings(model="test-gemini"))


def approve(store, model, patch=None):
    stage = next(s for s in REVIEW_SOURCES if store.stage(s)["status"] == "waiting_for_review")
    decision = ReviewDecision(
        revision=digest(store.output(REVIEW_SOURCES[stage])),
        reviewer="Test reviewer",
        action="approve",
        rationale="Fixture approval",
        patch=patch,
    )
    return run_pipeline(Store(store.root), model, decision)


def complete(store, model):
    run_pipeline(store, model)
    for _ in range(3):
        approve(Store(store.root), model)
    return Store(store.root)
