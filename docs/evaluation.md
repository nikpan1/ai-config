# Evaluation baseline and release status

The implementation passes the offline suite and a live Gemini end-to-end run on
the small retry fixture. Production release approval still requires broader corpus
evaluation and a domain reviewer. The live fixture reviews were performed by Codex
and are explicitly attributed as agent test reviews, not human domain approval.

## Corpus inspection

The supplied `data/legacy-insurance/` corpus contains three UTF-8 Markdown files,
846,007 bytes and 9,305 lines. It uses large pipe tables, headings, internal links,
negation, conditional requirements and deliberately conflicting statements. No
Markdown or HTML image references were found. These are synthetic specifications,
not evidence about a real insurance product.

The parser produced 2,319 source spans, including 207 tables, and 180 extraction
batches at the default 16,000-character batch limit. Explicit HTML anchors resolve;
the supplied corpus has no missing local-link warnings after parsing.

`markdown-it-py` 4.2.0 is pinned by `uv.lock`, with tables and footnotes enabled.
Source spans preserve snapshot ID, path, line ranges, heading context, exact text
and normalized table rows with headers. HTML tables retain the complete original
markup, including row/column spans. Regression tests create valid PNG, unreadable,
missing, remote and repeated reference-style/HTML image references.

## Proposed reviewed sample

Use `tests/fixtures/retry.md` as the initial small chapter target: Notification
delivery. Expected evidence:

| Assertion | Required qualifier | Evidence |
| --- | --- | --- |
| Retry transient failures up to three times | Only while delivery remains enabled | Retry-rules table |
| Do not retry permanent failures | Zero attempts; preserve negation | Retry-rules table |
| Customer supplies sender address | Before activation; mandatory | Final prose paragraph |

This annotation is an engineering fixture, pending domain-review agreement.
The renderer/UI fixture is a separate synthetic visual test and is not an approved
documentation output.

## Automated checks

Tests cover the complete LangGraph route, persistent SQLite checkpoints, process
restart at review, failure retention, stale approvals, deleted artifacts, prompt
invalidation, root containment, table chunk context, source immutability, image
inventory, quota budgets, exact prompt snapshots, semantic repair limits,
conflict/rejection handling, portable exports and reset/purge recovery.

The graph preview is verified in Chromium at 1440x900 and 390x844: nonblank canvas,
capability filtering, search, selection, source excerpt display, reset and no page
overflow. The pinned Mermaid CLI renders the supported flowchart fixture.

## Live Gemini fixture run

On 7 October 2026, run `run-20261007-210858-33841a97` completed all eleven stages
using the configured `gemini-3.7-flash` model through LangGraph and LangChain.
Input: `tests/fixtures/retry.md`. The existing user run
`run-20261007-210536-09034619` was inspected and left at knowledge review.

- Four extracted claims retained message delivery, the three-attempt transient
  rule with its enabled-delivery condition, zero permanent retries, and the
  mandatory customer sender address before activation.
- Two chapters cover all four claims. The output explicitly identifies missing
  sender-address format/submission details instead of inventing them.
- One generated diagram has two source-backed edges. The pinned Mermaid renderer
  passed, and the rendered SVG was visually inspected in Chrome.
- Structural validation and Gemini semantic review reported no findings. All stages
  used one attempt; no repair or request retry was needed.
- Usage: 9 requests, 14,218 input tokens and 6,654 output tokens. These are actual
  provider-reported token counts, separate from the 108,113-token budget reservation.
- Resuming the completed run in a new process without a process-level API key reused
  all saved artifacts; the request count remained 9 and no duplicate export appeared.
- The customer and audit bundles were exported under
  `output/run-20261007-210858-33841a97/`. The local report is
  `runs/run-20261007-210858-33841a97/report/index.html`; raw exchanges, review decisions
  and stage timings remain in the run directory.

The SDK's automatic-function-calling advisory appeared during the run but did not
prevent structured responses or completion. This small synthetic result is not a
corpus-scale accuracy measurement, a readability score or a cost estimate.

## Outstanding release checks

- Repeat live evaluation on representative, larger specifications and informative
  images; retain prompt snapshots, raw responses, measured usage and timings.
- Review extraction support and required-claim retention on the annotated sample.
  Proposed thresholds remain 95% support and 90% retention, with no critical error.
- Have a domain reviewer score readability at least 4/5 and test customer preparation
  comprehension. Resolve the supplied corpus's intentional contradictions explicitly.
- Evaluate informative screenshots and text/image disagreements with real Gemini
  image input; generated fixture assets only verify the deterministic image path.
- Measure corpus-scale graph size, context needs and review effort. Reconciliation
  and outline calls currently require the structured graph to fit the configured
  context limit. No unbounded or silent truncation is implemented.

Source lookup integrity, model semantic assessments and human quality scores must
be reported separately. The optional M6 Streamlit interface and cross-run change
tracking are deferred as the development plan permits.
