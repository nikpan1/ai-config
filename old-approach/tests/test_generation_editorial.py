from copy import deepcopy

import pytest
from langgraph.types import Command
from test_generation import generation

from docgen.generation_contracts import EditorialPage
from docgen.generation_editorial import validate_editorial_page
from docgen.generation_export import evidence_id
from docgen.storage import read_json
from docgen.workflow import persistent_graph

__all__ = ["generation"]


@pytest.fixture
def editorial_example():
    evidence = {"block_id": "b1", "excerpt": "Archive approved revisions daily at 02:00 UTC."}
    key = evidence_id(evidence)
    sentence = evidence["excerpt"]
    markdown = f"# Archive\n\n## Daily run\n\n{sentence} [Rule](sources/index.md#source-{key})\n"
    return (
        EditorialPage(
            page_id="p1",
            markdown=markdown,
            coverage=[{"obligation_id": "o1", "excerpt": sentence, "evidence_ids": [key]}],
            changes=["Clarified daily run"],
        ),
        {
            "page": {"id": "p1"},
            "markdown": markdown,
            "originals": {"obligations": [{"id": "o1", "evidence": [evidence]}]},
        },
    )


@pytest.mark.parametrize(
    "defect",
    [
        "lost_source",
        "invented_source",
        "lost_fact",
        "detached_citation",
        "false_excerpt",
        "unrelated_evidence",
        "heading",
        "code",
    ],
)
def test_editorial_rejects_provenance_and_coverage_damage(editorial_example, defect):
    result, payload = deepcopy(editorial_example)
    if defect == "lost_source":
        result.markdown = result.markdown.split(" [Rule]")[0]
    elif defect == "invented_source":
        result.markdown += "\n[Invented](sources/index.md#source-other)\n"
    elif defect == "lost_fact":
        result.coverage.clear()
    elif defect == "detached_citation":
        result.markdown = result.markdown.replace(" [Rule]", "\n\n[Rule]")
    elif defect == "false_excerpt":
        result.coverage[0].excerpt = "A sentence absent from the page"
    elif defect == "unrelated_evidence":
        result.coverage[0].evidence_ids = ["unrelated"]
    elif defect == "heading":
        result.markdown = result.markdown.replace("Daily run", "Other heading")
    else:
        result.markdown += '\n```mermaid\nflowchart TD\n    n0["Invented"]\n```\n'
    with pytest.raises(ValueError):
        validate_editorial_page(result, payload)


def test_editorial_allows_grouped_repeated_citations(editorial_example):
    result, payload = editorial_example
    payload["markdown"] += payload["markdown"].split("## Daily run\n\n")[1]
    validate_editorial_page(result, payload)


def test_editorial_allows_new_subheadings_but_preserves_existing_anchor_identity(editorial_example):
    result, payload = editorial_example
    result.markdown = result.markdown.replace("## Daily run\n", "## Daily run\n\n### Eligibility\n")
    validate_editorial_page(result, payload)
    result.markdown += "\n### Daily run\n"
    with pytest.raises(ValueError, match="headings or anchors"):
        validate_editorial_page(result, payload)


def test_editorial_diagram_coverage_requires_its_adjacent_source_note(editorial_example):
    result, payload = editorial_example
    key = result.coverage[0].evidence_ids[0]
    result.markdown = (
        '# Archive\n\n## Daily run\n\n```mermaid\nflowchart TD\n    n0["Daily retry"]\n```\n\n'
        f"Diagram source: [Rule](sources/index.md#source-{key})\n"
    )
    payload["markdown"] = result.markdown
    result.coverage[0].excerpt = "Daily retry"
    validate_editorial_page(result, payload)
    result.markdown = result.markdown.replace(
        "Diagram source:", "An unrelated paragraph.\n\nDiagram source:"
    )
    with pytest.raises(ValueError, match="adjacent source"):
        validate_editorial_page(result, payload)


def test_editorial_combined_passage_can_cite_two_facts_but_not_substitute_evidence(
    editorial_example,
):
    result, payload = editorial_example
    other = {"block_id": "b2", "excerpt": "Leave held revisions unchanged."}
    other_id = evidence_id(other)
    payload["originals"]["obligations"].append({"id": "o2", "evidence": [other]})
    result.markdown = (
        result.markdown.rstrip()
        + f" {other['excerpt']} [Hold](sources/index.md#source-{other_id})\n"
    )
    payload["markdown"] = result.markdown
    result.coverage[0].evidence_ids.append(other_id)
    result.coverage.append(
        result.coverage[0].model_copy(update={"obligation_id": "o2", "excerpt": other["excerpt"]})
    )
    validate_editorial_page(result, payload)
    result.coverage[0].evidence_ids = [other_id]
    with pytest.raises(ValueError, match="unrelated evidence"):
        validate_editorial_page(result, payload)


def test_editorial_allows_source_column_but_not_another_rows_citation(editorial_example):
    result, payload = editorial_example
    key = result.coverage[0].evidence_ids[0]
    result.markdown = (
        "# Archive\n\n## Daily run\n\n| Rule | Source |\n| --- | --- |\n"
        f"| {result.coverage[0].excerpt} | [Rule](sources/index.md#source-{key}) |\n"
    )
    validate_editorial_page(result, payload)
    result.markdown = result.markdown.replace(
        " | [Rule]", " | No source |\n| Unrelated row | [Rule]"
    )
    with pytest.raises(ValueError, match="adjacent source"):
        validate_editorial_page(result, payload)


@pytest.mark.parametrize(
    "flag",
    ["narrative_flows", "repetition_controlled", "source_links_readable", "template", "accounting"],
)
def test_editorial_quality_failure_is_bounded_and_reviewable(generation, flag):
    pipeline, model, initial, config = generation
    original = model.call

    def reject(stage, payload, schema):
        result = original(stage, payload, schema)
        if stage == "gen_page_review":
            if flag == "template":
                result.template_assessments[0].satisfied = False
            elif flag == "accounting":
                result.checked_obligation_ids.append("invented")
            else:
                setattr(result, flag, False)
        return result

    model.call = reject
    with persistent_graph(pipeline) as graph:
        result = graph.invoke(initial, config)
    assert result["status"] == "awaiting_review"
    assert result["review_stage"] == "verify_editorial_revision"
    assert model.calls.count("gen_polish") == 2
    assert not result.get("export_path")
    assert result["pages_ref"] == result["unpolished_pages_ref"]
    decisions = [
        {
            "issue_id": issue["id"],
            "revision": issue["revision"],
            "action": "correct",
            "reviewer": "Fixture reviewer",
            "rationale": "Corrected editorial page",
            "correction_ref": result["editorial_draft_ref"],
        }
        for issue in pipeline.read(result, "issues_ref")
    ]
    model.call = original
    writing_calls = model.calls.count("gen_write")
    with persistent_graph(pipeline) as graph:
        final = graph.invoke(Command(resume={"decisions": decisions}), config)
    assert final["status"] == "ready_for_review", final
    assert model.calls.count("gen_write") == writing_calls


def test_editorial_preserves_originals_and_resumes_without_rewriting(generation):
    pipeline, model, initial, config = generation
    with persistent_graph(pipeline, "verify_editorial_revision") as graph:
        stopped = graph.invoke(initial, config)
    count = model.calls.count("gen_polish")
    assert count == 1
    assert stopped["editorial_index"] == 1
    assert stopped["pages_ref"] != stopped["unpolished_pages_ref"]
    with persistent_graph(pipeline) as graph:
        final = graph.invoke(None, config)
    assert final["status"] == "ready_for_review"
    assert final["unpolished_pages_ref"] == stopped["unpolished_pages_ref"]
    reviews = pipeline.read(final, "page_reviews_ref")
    assert model.calls.count("gen_polish") == len(reviews)
    assert {r["page_id"] for r in reviews} >= {
        r["page_id"] for r in pipeline.read(stopped, "page_reviews_ref")
    }
    from pathlib import Path

    metadata = Path(final["manifest_path"]).parent
    assert read_json(metadata / "unpolished_pages.json") == pipeline.read(
        stopped, "unpolished_pages_ref"
    )
    assert read_json(metadata / "page_reviews.json") == reviews
