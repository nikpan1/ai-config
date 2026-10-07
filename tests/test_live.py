import os
import time
from pathlib import Path

import pytest

from docgen.config import Settings
from docgen.models import Knowledge
from docgen.storage import Store, write_json
from docgen.workflow import run_pipeline


@pytest.mark.live
@pytest.mark.skipif(os.environ.get("DOCGEN_LIVE") != "1", reason="Opt-in Gemini evaluation")
def test_live_gemini_to_knowledge_review():
    model = os.environ.get("DOCGEN_MODEL")
    if not model:
        pytest.fail("Set DOCGEN_MODEL for live evaluation")
    store = Store.create(
        Path("runs"), Path("tests/fixtures/retry.md"), Settings(model=model, max_calls=12)
    )
    started = time.monotonic()
    result = run_pipeline(store)
    graph = Knowledge.model_validate(store.output("reconcile"))
    assert result["status"] == "waiting_for_review"
    assert graph.claims
    write_json(
        store.root / "evaluation.json",
        {
            "run_id": store.manifest["run_id"],
            "seconds_to_review": time.monotonic() - started,
            "usage": store.manifest["usage"],
            "claims": len(graph.claims),
            "semantic_support": "Awaiting independent human evaluation",
            "required_claim_recall": "Awaiting independent human evaluation",
        },
    )
    print(f"Live evaluation awaits domain review: {store.root}")
