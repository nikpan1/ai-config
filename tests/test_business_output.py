from docgen_graph.completion import (
    GroundedDocument,
    SourceFinding,
    citation_excerpt_files,
    citation_target,
    document_verification,
    render_grounded_document,
)


def evidence():
    return [
        {
            "id": "policy",
            "path": "policy.md",
            "text": "The policy specifies 30 days.\nThe addendum specifies 45 days.",
            "start_line": 4,
            "start_column": 1,
            "source_start_char": 100,
        }
    ]


def document():
    return {
        "title": "Retention policy",
        "sections": [
            {
                "id": "retention",
                "title": "Retention",
                "paragraphs": [
                    {
                        "id": "retention-conflict",
                        "text": (
                            "The policy and addendum specify different periods: 30 and 45 days."
                        ),
                        "sources": [
                            {"evidence_id": "policy", "quote": "The policy specifies 30 days."},
                            {"evidence_id": "policy", "quote": "The addendum specifies 45 days."},
                        ],
                        "uncertainty": "The audit could not resolve the conflicting versions.",
                    }
                ],
                "image_hashes": [],
            }
        ],
        "limitations": ["Withheld paragraph 12.1", "AI-generated interpretation was audited"],
    }


def test_business_document_keeps_sourced_disagreement_without_pipeline_diagnostics():
    candidate = document()
    markdown = render_grounded_document(candidate, evidence(), {})
    assert candidate["sections"][0]["paragraphs"][0]["text"] in markdown
    assert "30 and 45 days" in markdown
    assert "Withheld" not in markdown
    assert "AI-generated" not in markdown
    assert "Uncertainty:" not in markdown
    assert "## Limitations" not in markdown
    assert "The audit could not" not in markdown
    verification = document_verification(candidate, evidence())
    assert verification["limitations"] == candidate["limitations"]
    assert verification["paragraphs"][0]["uncertainty"]
    assert verification["paragraphs"][0]["paragraph_id"] == "retention-conflict"


def test_renderer_preserves_business_text_instead_of_filtering_words():
    candidate = document()
    candidate["sections"][0]["paragraphs"][0]["text"] = (
        "The business workflow includes an audit and records whether content was AI-generated."
    )
    markdown = render_grounded_document(candidate, evidence(), {})
    assert candidate["sections"][0]["paragraphs"][0]["text"] in markdown


def test_citations_reuse_exact_excerpts_but_distinguish_different_quotes():
    candidate = document()
    paragraph = candidate["sections"][0]["paragraphs"][0]
    paragraph["sources"].append(dict(paragraph["sources"][0]))
    candidate["sections"][0]["paragraphs"].append({**paragraph, "id": "repeat"})
    markdown = render_grounded_document(candidate, evidence(), {})
    files = citation_excerpt_files(candidate, evidence())
    assert len(files) == 2
    assert markdown.count("[^1]:") == 1
    assert markdown.count("[^2]:") == 1
    assert "[^3]" not in markdown
    assert "[^1] [^2] [^1]" not in markdown
    for source in paragraph["sources"]:
        target = citation_target(source)
        assert f"]({target})" in markdown
        assert source["quote"] in files[target]
        assert "[Read surrounding source context](policy.md)" in files[target]
    assert "The policy specifies 30 days." not in markdown
    assert "policy.md, L4:1-L4:29" in markdown


def test_verification_preserves_image_interpretation_provenance_and_quote_locations():
    source = {
        **evidence()[0],
        "source_kind": "generated_image_description",
        "source_image_path": "screen.png",
        "source_image_hash": "image-hash",
        "provider": "gemini",
        "model": "configured-model",
        "interpretation_ref": "interpretation-hash",
    }
    result = document_verification(document(), [source])
    citation = result["paragraphs"][0]["citations"][0]
    assert citation["exact_quote_found"] is True
    assert citation["locations"][0]["source_start_char"] == 100
    assert citation["source_kind"] == "generated_image_description"
    assert citation["source_image_hash"] == "image-hash"
    assert citation["provider"] == "gemini"
    assert citation["interpretation_ref"] == "interpretation-hash"
    assert "does not establish semantic entailment" in result["citation_check"]


def test_schema_supports_stable_targets_and_source_grounded_omissions():
    parsed = GroundedDocument.model_validate(document())
    assert parsed.sections[0].id == "retention"
    assert parsed.sections[0].paragraphs[0].id == "retention-conflict"
    finding = SourceFinding.model_validate(
        {
            "section_id": "retention",
            "severity": "omission",
            "explanation": "The addendum period is absent.",
            "sources": [{"evidence_id": "policy", "quote": "The addendum specifies 45 days."}],
        }
    )
    assert finding.section_index == -1
    assert finding.paragraph_id == ""
    assert finding.sources[0].evidence_id == "policy"


def test_inline_source_image_resolves_to_exported_asset_and_is_not_repeated():
    candidate = document()
    section = candidate["sections"][0]
    section["image_hashes"] = ["image-hash"]
    section["paragraphs"][0]["text"] = (
        "<table>\n<tr><td>\n\n![Approved illustration](assets/screen.png)\n\n"
        "</td></tr>\n</table>\n\nThe policy remains applicable."
    )
    sources = [
        {
            **evidence()[0],
            "source_image_hash": "image-hash",
            "source_image_path": "assets/screen.png",
        }
    ]
    assets = {"image-hash": "assets/exported-image.png"}
    markdown = render_grounded_document(candidate, sources, assets)
    assert "![Approved illustration](assets/exported-image.png)" in markdown
    assert markdown.count("assets/exported-image.png") == 1
    assert "The policy remains applicable." in markdown
    verification = document_verification(candidate, sources, assets)
    assert verification["paragraphs"][0]["image_reference_resolutions"][0]["outcome"] == "resolved"


def test_unknown_or_ambiguous_images_preserve_caption_without_broken_resource():
    candidate = document()
    candidate["sections"][0]["paragraphs"][0]["text"] = (
        "See ![Missing example](missing.png) and ![Ambiguous example](screen.png)."
    )
    sources = [
        {**evidence()[0], "source_image_hash": "first", "source_image_path": "a/screen.png"},
        {**evidence()[0], "source_image_hash": "second", "source_image_path": "b/screen.png"},
    ]
    assets = {"first": "assets/first.png", "second": "assets/second.png"}
    markdown = render_grounded_document(candidate, sources, assets)
    assert "See Missing example and Ambiguous example." in markdown
    assert "![" not in markdown
    verification = document_verification(candidate, sources, assets)
    assert all(
        item["outcome"] == "unknown_or_ambiguous_reference"
        for item in verification["paragraphs"][0]["image_reference_resolutions"]
    )


def test_reference_images_resolve_and_image_syntax_in_code_remains_literal():
    candidate = document()
    candidate["sections"][0]["paragraphs"][0]["text"] = (
        "![Illustration][example]\n\n[example]: assets/screen.png\n\n"
        "```markdown\n![Literal example](missing.png)\n```"
    )
    sources = [
        {
            **evidence()[0],
            "source_image_hash": "image-hash",
            "source_image_path": "assets/screen.png",
        }
    ]
    markdown = render_grounded_document(candidate, sources, {"image-hash": "assets/exported.png"})
    assert "![Illustration](assets/exported.png)" in markdown
    assert "```markdown\n![Literal example](missing.png)\n```" in markdown
