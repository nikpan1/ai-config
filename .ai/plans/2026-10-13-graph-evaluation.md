# Graph construction evaluation — 2026-10-13

The final live experiment completed all four formatting variants. Inspection of the published graphs found the same business meaning and elementary condition structure: **2 topics, 3 necessary rules, 3 condition groups, 7 conditions and 1 exception** per variant. This is evidence for the small registration fixture, not a guarantee for arbitrary documents.

## Scope and observed meaning

The English fixture appears as paragraphs, bullet lists, tables and mixed heading levels. It contains two registration stories and a separate password-reset story. All final graphs preserve:

- One registration topic containing eligibility and activation; password reset remains separate. All rules retain the `Customer portal` scope.
- Registration requires ALL three prerequisites: a valid email, a password of at least 12 characters and accepted terms. Missing a required condition prevents registration.
- The invited-company-user exception waives only the password requirement; the remaining prerequisites still apply.
- Activation requires ANY of two elementary confirmation conditions: the email link or a support-provided code. Meeting this requirement does not guarantee successful activation.
- Password reset requires BOTH a verified email and an active account; inactive accounts cannot reset passwords.

Compound input qualifiers are retained in condition-group `source_conditions` metadata, with separate elementary condition nodes. They no longer force duplicate compound nodes. Topic labels vary slightly, such as `User registration` versus `Customer portal registration`; their rule membership and scope agree. Consequently this comparison establishes meaning preservation, not identical labels, node IDs or graph hashes.

## Live iterations

| Version | Complete graphs | Concurrent event window | Ledger charge | Settled | Uncertain estimate | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| v1 | 0/4 | 491.7 s | PLN 5.207104 | PLN 1.914683 | PLN 3.292421 | Semantic requests exceeded output limits; an early proposal also split registration into phase topics. |
| v2 | 3/4 | 171.4 s | PLN 1.922867 | PLN 1.922867 | PLN 0 | Main topics improved, but strict compound-condition retention conflicted with elementary decomposition. |
| v3 | 4/4 | 239.4 s | PLN 1.834833 | PLN 1.834833 | PLN 0 | All four released graphs preserve the tested meaning and elementary structure. |
| v4 | 1/1 prose | 87.5 s | PLN 0.261157 | PLN 0.261157 | PLN 0 | Revalidated corrected source-coverage binding to the frozen graph for the final inspector. |

Timing is the last recorded event minus the first recorded event; process startup is excluded. Concurrent windows are not the sum of individual run times. Total ledger charge across all 13 runs is **PLN 9.225961**, comprising **PLN 5.933540 settled** and **PLN 3.292421 uncertain estimates**. No reservations remain. The existing shared ledger was retained.

The v2 list run correctly stopped: a structural check demanded the original compound OR phrase, while the independent audit rejected adding that phrase as a redundant condition group. Binding the original qualifier to the decomposed group resolved this conflict in v3.

## Final variant results

| Variant | Time | Settled cost | Semantic edges | Exact source quotations | Model repair cycles | Recorded quote-offset corrections |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Prose | 85.6 s | PLN 0.269713 | 33 | 17 | 0 | 15 |
| Lists | 88.8 s | PLN 0.277306 | 34 | 24 | 0 | 13 |
| Tables | 165.9 s | PLN 0.550210 | 41 | 24 | 0 | 11 |
| Headings | 238.9 s | PLN 0.737604 | 40 | 20 | 1 | 0 |

The single model repair occurred during the headings source-coverage audit. All final semantic proposals passed without a semantic retry. The 39 offset corrections were deterministic anchoring of unique exact quotations; they did not modify original source text. Different edge and quotation counts reflect formatting-specific evidence fragments. All **85 final quotations** were independently checked against their original fixture character ranges, with zero mismatches. All four source-coverage reports are complete and all facts have semantic rules.

After v3, inspector export exposed a metadata mismatch: source coverage named the semantic-content hash instead of the frozen graph revision. The binding was corrected without changing graph semantics. The additional prose v4 run retained the same 2/3/3/7/1 structure, completed without model repairs and passed all 19 original-source quotation checks. Its coverage revision matches the existing frozen SQLite graph. The [final interactive inspector](../../.docgen/inspection-semantic-graph/index.html) exported with zero diagnostics.

## Provenance and reproducibility

The actual published batch provenance records provider `gemini`, model `gemini-3.8-flash`, SDK version, prompt version, original proposal, anchored proposal, anchoring changes and independent audit references. Source files and runtime signatures are frozen. Full SHA-256 source hashes are:

| Fixture | SHA-256 |
| --- | --- |
| prose.md | `703ec7e4a05bb19f4e844483bef2fe2af637714e5b38cc334f5c2ddf13ad8b8b` |
| lists.md | `33c431243eea69daeafc463a4153e62d50b9583c0d7d11304814c1d4ffead87c` |
| tables.md | `a7b8ebd3cea10b59fcd3c12ecefc59908d3df850bb35f07639e595bcc37c0eb1` |
| headings.md | `0b7438ba221dbfac6129f6a3f9b6807924f7da2ec2c121a06b97aa4ee3ec0caa` |

[Detailed evaluation JSON](../../.docgen/semantic-live-20261013/evaluation-summary.json) contains all run IDs, costs, repairs, source coverage, provenance references, graph hashes and actual published rule structures. Comparison artifacts are under `.docgen/semantic-live-20261013/runs/semantic-{variant}-v3`; the final inspector uses `semantic-prose-v4`. The shared ledger is `.docgen/budget.sqlite`. Pricing and exchange-rate metadata used for accounting are included in the JSON.

## Limits

The final focused offline suite passed **82 distinct tests**, covering graph construction, contracts, formatting, provenance, context, rejection and persistent restarts; the graph-pipeline subset was rerun after the metadata correction. Ruff, JavaScript syntax and diff-whitespace checks also passed. Controlled-model tests do not prove model quality.

This was one live v3 run per format, plus earlier iterations and the prose v4 confirmation, not a statistical robustness study. The production document corpus was not subjected to a new full model audit. Documentation planning, writing, editing and delivery were not exercised. Password-specific exception attachment remains explicit in the exception text, rather than a dedicated edge targeting the password condition.
