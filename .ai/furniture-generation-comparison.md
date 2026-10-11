# Comparison of Furniture Documentation Pipelines

Date: 2026-10-11. The execution protocol is `furniture-generation-protocol.md`.

## Comparable input

Both runs use the same four synthetic business Markdown pages in `data/test_data_1` and `data/template.md`. The pages contain 240 `As a ... I want the system to ...` stories in four large tables. Source front matter points to local HTML pages, which are the reader-facing targets for direct text-fragment citations. The new approach was run without `--code` as requested; any code analysis output would be outside the scope of this evaluation.

## Evaluation criteria

| Criterion | Old approach | New approach |
| --- | --- | --- |
| Source ingestion | Includes 4 Markdown pages and 4 SVG mockups; 260 source blocks in 14 batches. | Documentation-only ingestion; 256 document spans in 28 batches, no code units. |
| Durable execution | Separate checkpointed knowledge, planning, and generation workflows. | One checkpointed graph from source inventory through candidate and release. |
| Human review | Blocks unresolved evidence, source authority, planning, and final release issues. | Blocks plan approval and candidate release; may also block source issues. |
| Source traceability | Immutable source snapshot, block IDs and local audit index; direct `#:~:text=` URLs at export. | Frozen document spans, graph evidence IDs and local audit index; direct `#:~:text=` URLs at candidate export. |
| Final documentation | Pending old planning and generation. | Approved local release: one 463,272-character Markdown page with eight template sections and a separate source index. |
| Complete source coverage | Pending. | Deterministic audit maps all 457 graph claims; 240 of 240 user-story source fragments are linked. |
| Direct citation verification | Export pending; shared fragment builder was browser-tested on the HTML mirror. | 1,021 direct citation occurrences, 240 unique links; all 240 excerpts match the visible HTML source. First and last sampled fragments were also browser-tested. |
| Measured evaluation cost | Pending final ledger report. | Successful v5: 316 settled model calls, PLN 25.7086 measured and charged. Earlier development attempts are accounted for separately below. |
| Runtime | Pending. | Pending. |

## Output comparison

The new candidate `e439237ddf6192a53bd9b99b8ba14edf760d91d33351d67cf875607483c3022f` was approved and released. Its content has 17,261 whitespace-separated words; the 463,272-character size includes long URL-encoded citations. Its source index and 240 evidence records remain alongside the main page. Its title still contains the word “Plan”, inherited from the approved planning title; this is a presentation issue in the released page, not a missing source mapping.

The old output and side-by-side content assessment remain pending. Compare page count, total Markdown length, source evidence count, citations to the original HTML, retained unknowns and caveats, and sampled factual fidelity after it is released. Treat an interrupted or unapproved candidate as such; do not label it a released documentation set.
