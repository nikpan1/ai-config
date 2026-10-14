from docgen_graph.document_preview import render_document_preview


def test_preview_has_heading_navigation_exact_evidence_and_no_executable_source_html():
    markdown = (
        '# Equipment\n\n## Eligibility\n\nAn active membership is required. [^1]\n\n'
        '<script>alert("untrusted")</script>\n\n'
        '[^1]: [Rules, L2](evidence/quote-1.md)\n'
    )
    page = render_document_preview(
        markdown,
        {'evidence/quote-1.md': '# Source excerpt\n\n> Membership is required.\n\n'
         '[Read context](source-1.md)\n'},
    )
    assert '<a class="level-h2" href="#section-1">Eligibility</a>' in page
    assert 'href="#evidence-1"' in page
    assert '<details id="evidence-1"' in page
    assert '<blockquote>\n<p>Membership is required.</p>' in page
    assert 'href="evidence/source-1.md"' in page
    assert '<script>alert("untrusted")</script>' not in page


def test_preview_preserves_visual_caption_order_and_mermaid_definition():
    markdown = (
        '# Process\n\n![Check](assets/check.png)\n\n**Figure 1. Check result**\n\n'
        '```mermaid\nflowchart LR\nA[Request] --> B[Review]\n```\n\n'
        '**Figure 2. Request review**\n'
    )
    page = render_document_preview(markdown)
    assert page.index('src="assets/check.png"') < page.index('Figure 1. Check result')
    assert '<p class="figure-caption"><strong>Figure 1.' in page
    assert '<pre class="mermaid">flowchart LR' in page
    assert page.index('<pre class="mermaid">') < page.index('Figure 2. Request review')
    assert 'securityLevel:' in page
