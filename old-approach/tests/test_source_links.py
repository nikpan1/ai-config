from pathlib import Path

from docgen.generation_export import citations, evidence_id
from docgen.generation_validation import markdown_report
from docgen.source_links import source_url_from_markdown, text_fragment_url
from docgen.storage import Artifacts


def test_citation_uses_declared_source_url_and_retains_local_fallback():
    source = (
        "---\nsource_url: https://example.atlassian.net/wiki/page?id=4\n---\n"
        "| A | As a shopper, I want the system to compare cabinet sizes. |"
    )
    url = source_url_from_markdown(source)
    evidence = {
        "block_id": "b-1",
        "excerpt": "As a shopper, I want the system to compare cabinet sizes.",
    }
    key = evidence_id(evidence)
    direct = text_fragment_url(url, source.splitlines()[-1])
    assert direct in citations([evidence], "index.md", {key: "S1"}, {key: direct})
    assert "[S1](sources/index.md#s1)" == citations([evidence], "index.md", {key: "S1"})


def test_markdown_validation_allows_only_declared_source_pages(tmp_path: Path):
    store = Artifacts(tmp_path / "store")
    url = "https://example.atlassian.net/wiki/page?id=4"
    pages = {"index.md": f"# Example\n\n[Source](<{url}#:~:text=cabinet>)\n"}
    assert markdown_report(pages, tmp_path, store, [], {url})["passed"]
    assert not markdown_report(pages, tmp_path, store, [], set())["passed"]
