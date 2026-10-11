import pytest
from conftest import FixtureModel

from docgen.ingestion import snapshot_sources
from docgen.model import ModelFailure, TruncatedOutput
from docgen.reconciliation import comparison_tasks
from docgen.storage import read_jsonl, write_json, write_jsonl
from docgen.workflow import Pipeline, persistent_graph


def test_reconciliation_resolves_full_blocks_beyond_short_excerpts(tmp_path, settings, store):
    source = tmp_path / "source.md"
    source.write_text("Record A requires approval.\n\nRecord B preserves revisions.\n")
    observed = []

    def transform(stage, payload, result):
        if stage == "extract":
            for claim in result.claims:
                claim.evidence[0].excerpt = "Record"
        if stage == "claims":
            observed.append(payload)
        return result

    with persistent_graph(Pipeline(settings, store, FixtureModel(transform))) as graph:
        result = graph.invoke(
            {"run_id": "full-context", "source": str(source), "signature": "fixture"},
            {"configurable": {"thread_id": "full-context"}},
        )
    assert result["status"] == "complete"
    assert observed
    for payload in observed:
        records = payload["left"] + payload["right"]
        blocks = {b["id"]: b for b in payload["source_blocks"]}
        assert set(blocks) == {e["block_id"] for r in records for e in r["evidence"]}
        assert all(
            r["statement"] == blocks[r["evidence"][0]["block_id"]]["content"] for r in records
        )


def test_reconciliation_split_respects_task_admission_budget(tmp_path, settings, store):
    source = tmp_path / "source.md"
    source.write_text("\n\n".join(f"Record {i} requires scoped approval." for i in range(4)))

    def transform(stage, payload, result):
        if stage == "claims":
            raise TruncatedOutput("Force a split")
        return result

    limited = settings.model_copy(update={"workload_tasks": 1})
    with persistent_graph(Pipeline(limited, store, FixtureModel(transform))) as graph:
        with pytest.raises(ModelFailure, match="Split reconciliation queue"):
            graph.invoke(
                {"run_id": "split-budget", "source": str(source), "signature": "fixture"},
                {"configurable": {"thread_id": "split-budget"}},
            )


def test_split_reconciliation_results_survive_restart_without_dictionary_rewrites(
    tmp_path, settings, store
):
    source = tmp_path / "source.md"
    source.write_text("\n\n".join(f"Record {i} requires scoped approval." for i in range(4)))

    def transform(stage, payload, result):
        if stage == "claims" and len(payload["left"] + payload["right"]) > 2:
            raise TruncatedOutput("Force bounded comparison partitions")
        return result

    model = FixtureModel(transform)
    pipeline = Pipeline(settings, store, model)
    config = {"configurable": {"thread_id": "split-restart"}, "recursion_limit": 1000}
    with persistent_graph(pipeline, "reconcile_claims") as graph:
        graph.invoke(
            {"run_id": "split-restart", "source": str(source), "signature": "fixture"}, config
        )
        while not graph.get_state(config).values.get("claim_results_ref"):
            graph.invoke(None, config)
        state = graph.get_state(config).values
        first = state["claim_results_ref"]
        assert len(store.get(first)["rows"]) == 1
    with persistent_graph(pipeline) as graph:
        result = graph.invoke(None, config)
    assert result["status"] == "complete"
    results = list(pipeline.comparison_results(result, "claim"))
    assert len(results) == 6
    assert len({key for key, _ in results}) == 6
    assert len(store.get(first)["rows"]) == 1
    assert len(store.get(result["claim_results_ref"])["rows"]) == 1
    assert len(store.get(result["bundle_ref"])["claim_comparisons"]) == 6


def test_explicit_selection_does_not_follow_unselected_links(tmp_path, store):
    root = tmp_path / "sources"
    root.mkdir()
    (root / "chosen.md").write_text("A [related file](unselected.md).\n", encoding="utf-8")
    (root / "unselected.md").write_text("Must not enter the snapshot.\n", encoding="utf-8")
    manifest = tmp_path / "selection.json"
    write_json(manifest, {"schema_version": "1", "files": ["chosen.md"]})
    snapshot = snapshot_sources(root, store, selection=manifest)
    assert [row["path"] for row in snapshot["inventory"]] == ["chosen.md"]
    assert snapshot["selection"]["origin"] == "explicit"
    assert any(p["kind"] == "missing_link" for p in snapshot["problems"])
    write_json(manifest, {"schema_version": "1", "files": ["missing.md"]})
    with pytest.raises(ValueError, match="missing"):
        snapshot_sources(root, store, selection=manifest)
    write_json(manifest, {"schema_version": "1", "files": ["../selection.json"]})
    with pytest.raises(ValueError, match="leaves"):
        snapshot_sources(root, store, selection=manifest)


def test_indexed_immutable_shards_resolve_exact_rows_and_detect_corruption(store):
    ref = store.put_table(
        ({"id": str(i), "value": "x" * 100} for i in range(100)), shard_bytes=1000
    )
    assert len(store.get(ref)["parts"]) > 1
    assert [r["id"] for r in store.table_rows(ref, ["99", "1", "50"])] == ["99", "1", "50"]
    with pytest.raises(ValueError, match="Missing indexed"):
        store.table_rows(ref, ["missing"])
    part = store.get(ref)["parts"][0]
    store.path(part).write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="integrity"):
        store.table_rows(ref, ["1"])


def test_jsonl_export_streams_generator(tmp_path):
    path = tmp_path / "rows.jsonl"
    write_jsonl(path, ({"id": i} for i in range(1000)))
    assert sum(1 for _ in read_jsonl(path)) == 1000


def test_table_rejects_mutable_manifest_and_shard_references(store):
    write_json(store.path("runs/mutable.json"), [{"id": "one"}])
    manifest = store.put({"parts": ["runs/mutable.json"], "count": 1, "schema_version": "1"})
    with pytest.raises(ValueError, match="immutable"):
        list(store.iter_table(manifest))
    with pytest.raises(ValueError, match="immutable"):
        store.table_rows(manifest, ["one"])
    with pytest.raises(ValueError, match="immutable"):
        list(store.iter_table("runs/mutable.json"))


def test_workload_limit_does_not_silently_drop_candidate_pairs():
    rows = [
        {"id": str(i), "canonical_name": "Shared", "aliases": [], "padding": "x" * 300}
        for i in range(100)
    ]
    with pytest.raises(ModelFailure, match="no candidate tail"):
        comparison_tasks(rows, "entities", 1024, task_limit=2)
