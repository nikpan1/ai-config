# Editorial stage implementation

## Behavior

Generation now runs `polish_documentation` and `verify_editorial_revision` after page assembly. Each page is rewritten as a connected chapter using the original template, its compiled rules, the documentation brief and the complete evidence context for that page. Independent verification checks factual coverage, template application, readability, repetition and local citations. This replaces the previous page-review call; normal generation adds one writing call per content page. One repair is allowed.

Persistent checkpoints retain each candidate and successful page. Failures use the existing LangGraph review interrupt, with revision-bound `EditorialPage` corrections or an upstream revision request. Original pages and editorial evidence maps are immutable. Publication includes `unpolished_pages.json` and `page_reviews.json` in metadata. Source and attachment indexes are not rewritten.

Code checks preserve unique link destinations, original heading anchors and code fences. New subordinate headings with distinct anchors are allowed. Every obligation must map to text with supporting citations in the same paragraph, table row or protected Mermaid diagram's adjacent source note. Shared passages may cite multiple obligations' evidence, but must retain evidence for each mapped obligation. Semantic equivalence still requires model and human review.

## Verification

- 45 distinct focused tests passed across generation and editorial tests, including existing restart/release behavior, citation and coverage corruption, separate table source columns, diagram source notes, shared evidence, heading anchors, bounded repair, correction and checkpoint resume.
- Ruff checks passed for source and tests.
- Package build passed. The full repository suite was not repeated.

## Live editorial-only preview

The existing `phase3-archive-live-v1` fragments were reused without regenerating its 32 jobs. The source run was not changed. Two editor calls and one independent review cost approximately PLN 1.444 including configured billing headroom. The budget ledger had no remaining reservation afterward.

The old page was too large for the default 100,000-token request budget. The isolated preview used 200,000 tokens; the production default was not changed. Preflight failures made no generation calls. Production oversized pages fail explicitly instead of silently truncating evidence.

The candidate at `.docgen/runs/phase3-editorial-preview-v5/editorial-preview/a465af1e657be143c55059e0d07fc488249e27f4f9fd00903bac44d6fa35369a/index.md` is 28,003 bytes versus 87,390 bytes before editing. All unique original link destinations and 31 obligation mappings passed structural checks. This size reduction includes Markdown and citations; it is not a measure of semantic or literary quality.

Gemini's independent review passed the candidate. A subsequent agent comparison with the frozen source found unsupported scheduler technology, request-key contents, strengthened idempotency guarantees and missing local qualifications. Repetition also remains. These findings were recorded in the preview run's `source-review.md` and persisted as an actual `review_generation` interrupt. The preview has no release approval and is not a completed publication.

The final prompts were further strengthened against unsupported template filling, inferred mechanisms, guarantees, next actions and repetitive requirement paragraphs. Those final prompt refinements have not been retested with another paid generation. The live run's earlier implementation was frozen in its `implementation.json`; it used an explicit `DOCGEN_REQUEST_TOKENS=200000` override.

## Limits

The stage preserves planned page boundaries and existing heading anchors. It does not redesign an overly fragmented plan or repair protected diagrams. It edits one complete page at a time, with the page tree as navigation context; this is not a full-book structural rewrite across multiple pages. Human release review remains required, and the live false negative shows why model review alone is insufficient.
