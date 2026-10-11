from time import monotonic

from docgen.batching import plan_batches
from docgen.config import Settings
from docgen.ingestion import snapshot_sources
from docgen.storage import Artifacts, atomic_write, encode, write_json


def main():
    settings = Settings()
    store = Artifacts(settings.workspace)
    source = store.path("scale-source/corpus.md")
    paragraph = (
        "Each synthetic archive operation must retain the original request revision and "
        "tenant scope before lookup, except when an explicitly recorded hold prevents "
        "the daily operation. The fixture supplies no execution hour or timezone.\n\n"
    )
    repetitions = 35000
    content = "# Scale fixture\n\n" + paragraph * repetitions
    atomic_write(source, content)
    started = monotonic()
    snapshot = snapshot_sources(source, store)
    batches = plan_batches(snapshot, settings)
    ids = [key for batch in batches for key in batch.owned]
    assert len(ids) == len(set(ids)) == len(snapshot["blocks"])
    assert all(batch.source_tokens <= settings.batch_tokens for batch in batches)
    result = {
        "source_bytes": len(content.encode()),
        "whitespace_words": len(content.split()),
        "model_context_limit": 1048576,
        "blocks": len(ids),
        "batches": len(batches),
        "source_token_estimate": sum(batch.source_tokens for batch in batches),
        "seconds": monotonic() - started,
        "ownership_complete": True,
        "live_model_used": False,
        "limitation": (
            "Structural scale test only; no semantic or whole-corpus live-model acceptance."
        ),
    }
    assert result["whitespace_words"] > result["model_context_limit"]
    write_json(store.path("evaluation/scale-check.json"), result)
    print(encode(result))


if __name__ == "__main__":
    main()
