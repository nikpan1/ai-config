from pathlib import Path
from types import SimpleNamespace

from docgen_graph.storage import ArtifactStore
from docgen_graph.workflow import Pipeline
from evaluation.citation_cases import evaluate


def test_investment_fixture_citation_cases():
    root = Path(__file__).resolve().parents[1]
    report = evaluate(root)
    assert report["cases"] >= 69
    assert report["correct_behaviors"] == report["cases"]
    assert not [item for item in report["results"] if item.get("forbidden_hits")]


def test_explicit_quick_source_page_map_is_frozen(tmp_path):
    root = Path(__file__).resolve().parents[1]
    settings = SimpleNamespace(
        env_file=root / ".env",
        source_page_map=root / "data/test_data_2_reference/source-page-map-quick.json",
        model="gemini-3.8-flash",
        content_repair_limit=2,
    )
    pipeline = Pipeline(ArtifactStore(tmp_path), SimpleNamespace(settings=settings), "map-check")
    update = pipeline.snapshot_inputs(
        {
            "docs": str(root / "data/test_data_2_quick"),
            "code": "",
            "template": str(root / "data/template.md"),
            "mode": "manual",
        }
    )
    snapshot = pipeline.store.get(update["snapshot_ref"])
    page_hash = snapshot["source_pages"]["investment-platform/quick-risk-profiling"]
    expected = (root / "data/test_data_2_quick_html/risk-profiling.html").read_bytes()
    assert pipeline.store.get_bytes(page_hash) == expected
