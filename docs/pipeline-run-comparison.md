# Full-corpus pipeline comparison

The fixes are implemented and tested, but the fresh live run could not finish:
the provider returned HTTP **402 / RESOURCE_EXHAUSTED** after 87 of 151 extraction
batches. Its verified results are retained for resumption. The first run reached
knowledge review; the second did not reach reconciliation. Neither run constitutes
domain approval or a customer export. There is no basis yet for claiming end-to-end
cost savings, better conflict detection or better entity merging from the rerun.

Both runs selected the same three Markdown files under `data/`. All three current
files and both runs' immutable snapshots have identical SHA-256 hashes, verified
after the rerun stopped. The final status was recorded on 8 October 2026 (local time).

## Baseline findings and implemented fixes

| Finding in the first run | Implemented correction |
| --- | --- |
| 13 extraction repair calls; coverage references could disagree | Explicit coverage-reference instructions and exactly one disposition per supplied span, with bounded repair |
| 207 entire tables shared one disposition per table | Individual evidence IDs for all 2,590 table rows, exact row excerpts, separately retained raw headers |
| Redundant parser metadata and duplicate table representations in requests | Compact model-facing spans; complete immutable sources and locators retained locally |
| Two reconciliation calls consumed 1,823,933 input tokens; largest context 2,413,102 characters | Separate bounded identity and conflict batches, recoverable receipts and local bounded repair |
| 38 incompatible aliases caused an initial reconciliation failure | Candidate identity groups partitioned by exact type, scope and version; the same strict validation remains enforced |
| Only 14 final merges; 828 excess exact-name occurrences | Focused identity candidate review with sampled qualified claims; no automatic name-only merging |
| 13 entity versions looked like page or feature IDs | Extraction prompts distinguish explicit product releases from page, issue and feature identifiers |
| Cumulative reservations caused a budget stop despite lower reported usage | Settle known responses to actual token usage; keep full reservations for unknown usage and preserve historical totals |
| Progress required inspecting files | CLI stage/batch progress and reports on both run and resume |
| Rerun transport failure lacked a useful provider code | Safe HTTP/status-code diagnostics across nested exceptions, without raw transport messages |
| HTTP 402 with RESOURCE_EXHAUSTED was initially classified as retryable | Explicit HTTP failures take precedence over generic status labels; 402 now fails without retries |

The first run's artifacts are preserved. These findings are based on
[baseline metrics](run-comparison/baseline.json), the saved model exchanges and
stage failures. [Rerun metrics](run-comparison/rerun.json) include the partial
extraction, failed provider calls and exact processed source counts. The implementation checklist is in
[the improvement plan](pipeline-improvement-plan.md).

## Runs

- Baseline: `run-20261007-211927-87e3d586`, `gemini-3.7-flash`, full `data/` root.
- Rerun: `run-20261007-223031-d22eb286`, same model and root, `config.corpus.yaml`.
- Both use LangGraph nodes and LangChain structured Gemini calls.
- Baseline consumed 200 requests, 2,950,442 input tokens and 1,021,518 output tokens,
  including unsuccessful attempts and repairs. No currency cost is inferred.
- Baseline extraction completed 182 batches and retained 2,634 candidate claims,
  1,608 entities, 578 relationships, 8 unresolved conflicts and 2,319 evidence spans.
- Baseline dispositions: 1,572 covered, 744 excluded, 3 unresolved. Of the excluded
  spans, 579 were headings and 165 paragraphs. These were model dispositions, not
  independently reviewed exclusions.

### Measured outcome

| Metric | Baseline (complete to knowledge review) | Rerun (partial, provider blocked) |
| --- | --- | --- |
| Status | `waiting_for_review` | `failed` during extraction |
| Completed extraction batches | 182 / 182 | 87 / 151 |
| Model requests, including failures/repairs | 200 | 93 |
| Reported input tokens | 2,950,442 | 388,024 |
| Reported output tokens | 1,021,518 | 796,197 |
| Reported total tokens | 3,971,960 | 1,184,221 |
| Extraction repair calls | 13 | 2 |
| Active processing across attempts | 48 min 19 s | 29 min 40 s, incomplete |
| Wall time to knowledge review | 55 min 50 s | Not reached |
| Claims | 2,634 reconciled candidates | 2,547 extraction candidates, provisional |
| Entities | 1,608 after reconciliation | 562 before reconciliation, provisional |
| Final aliases / conflicts | 14 / 8 | Not run |
| Parsed source spans | 2,319 | 4,702 |
| Spans with extraction dispositions | 2,319 | 3,047 |
| Covered / excluded / unresolved dispositions | 1,572 / 744 / 3 | 2,489 / 558 / 0 among processed spans |
| Page/feature-ID-like entity versions (heuristic) | 13 | 0 among partial entities |

The rerun processed all 2,274 new spans in `functional-specification.md` and 773
of 1,651 in `integration-data-and-compliance.md`. `product-and-feature-register.md`
was snapshotted and parsed (777 spans), but **was not sent through extraction**
before the provider failure. The remaining 1,655 parsed spans have no completed
extraction disposition; zero unresolved dispositions must not be read as zero gaps.

Both extractions retained claim references for all 12 explicitly paired requirement
paragraphs in the functional specification. An agent spot-check confirmed that
the sampled assertions retained the opposed effective-date, eligibility-date,
rounding, beneficiary, approver-count and audit-hold rules. This is a limited
engineering check, not a statistically valid support/recall score. The baseline
linked all six seeded groups across their source sections; the rerun has not yet
performed conflict detection, so its recall is **not measured**.

### Provider stop and recovery

Request 90 failed without a retained numeric provider code. Safe diagnostics were
added, then the run was resumed. All 87 verified batches were reused with no model
requests for those batches. Requests 91-93 returned HTTP 402 and
`RESOURCE_EXHAUSTED`; the then-current label-based policy made two bounded retries.
That policy was corrected and tested: HTTP 402 is now terminal, even when wrapped
with that generic resource-exhaustion label. No further live request was made.

This is a provider-side quota/payment block, not exhaustion of the configured
8-million local token budget or 400-call cap. The account's precise billing or
quota condition was not inspected and no billing settings, credentials or models
were changed. The pipeline accounts for 1,399,381 tokens: 1,184,221 reported plus
215,160 retained reservations for four calls with no usage response. Its historical
reservation sum is 5,040,886; that sum is no longer the enforced budget balance.

When the provider accepts requests again, the saved run is resumable with:

```powershell
uv run docgen resume run-20261007-223031-d22eb286
```

No reset is needed. The verified 87 receipts and their hashes remain intact;
resetting extraction would deliberately discard their eligibility for reuse.
No unattended retries or scheduled jobs remain running.

## Offline Scale Check

The new planner was exercised locally against all 2,634 claims from the baseline
extraction, without model calls or changes to that run. It produced 12 identity
batches (maximum 47,921 characters) and 27 conflict batches (maximum 47,893), all
within the 48,000-character planning limit. Every claim appeared in the conflict
plan. One oversized identity group was explicitly left unmerged; no conflict topic
needed splitting in this check. These are **planning results**, not live-model
reconciliation results or measured token savings.

## Comparison cautions

Row-level evidence changes the denominator from 2,319 to 4,702 spans. Raw coverage
percentages between runs are therefore not directly comparable. More claims or
conflicts do not prove greater accuracy. The six explicitly seeded conflict groups
can be checked for linked source sections, but this is a structural recovery check,
not a complete semantic recall benchmark or an evaluation of unlabelled conflicts.

Identity candidates use exact normalized names/aliases and explicit identifier
hints within matching type/scope/version. Ambiguous candidates stay separate.
Oversized groups are reported as gaps. Conflict review covers every claim through
topic groups and explicit source conflict markers, but does not compare every
claim pair across unrelated topics or all split-topic chunks. These limits are
retained in the graph's gaps and batch-plan artifacts.

No API pricing, production-domain correctness, human readability score or full
customer-documentation acceptance is established by these runs. Downstream outline,
composition and publication gates remain unchanged.

## Verification

Before the rerun: 39 offline tests passed and one opt-in live test was skipped;
lint and type checks passed. The wheel built offline and packaged resources loaded
outside the repository. Chromium checks passed at 1440x900 and 390x844, including
canvas pixels, selection, table-header display and overflow checks.

After the provider-stop diagnostic/retry fixes, the full suite passed **41 tests**
with one opt-in live test skipped. All 87 saved batch hashes and complete per-batch
evidence dispositions were checked. The partial real-corpus preview also passed
desktop/mobile canvas, evidence-header and horizontal-overflow checks; it is
clearly labelled as incomplete and not reconciled. Live verification of the new
reconciliation stage remains blocked by the provider response.

`scripts/summarize_run.py` reads historical artifacts without calling Gemini or
invalidating old runs. Token totals include repairs and failed attempts when the
provider returned usage. Unknown usage keeps its conservative budget reservation.

## Local evidence

- [Baseline report](../runs/run-20261007-211927-87e3d586/report/index.html)
- [Baseline graph](../runs/run-20261007-211927-87e3d586/stages/reconcile/attempts/3/graph-preview/index.html)
- [Rerun manifest](../runs/run-20261007-223031-d22eb286/manifest.json)
- [Rerun report](../runs/run-20261007-223031-d22eb286/report/index.html)
- [Partial rerun graph, not reconciled](../runs/run-20261007-223031-d22eb286/analysis/partial-graph-preview/index.html)
- [Rerun configuration](../config.corpus.yaml)

The source files are synthetic fixtures. All conclusions above refer to local
artifacts and source code, not external product or insurance-law claims.
