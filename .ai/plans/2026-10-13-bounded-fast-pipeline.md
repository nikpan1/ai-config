# Bounded autonomous pipeline

## Goal

Complete a documentation-only end-to-end run on the risk profiling corpus within a 1,200-second processing budget, with persistent checkpoints, original-source citations and explicitly measured omissions.

## Implementation

1. Add an opt-in fast mode using concurrent ordinary Gemini requests for independent document batches. Preserve response caching, individual usage records and uncertain-outcome accounting. Keep publication and dependent LangGraph stages sequential.
2. Replace model readiness conversations with prepared evidence packets in fast mode. Retain mandatory evidence closure checks.
3. Repair citation presentation, fixed heading numbering and approved visual placement deterministically. Do not manufacture support or change business meaning.
4. Skip the optional stylistic rewrite in fast mode. Verify written claims against their sources and perform one final source-to-document coverage audit. Treat repetition as advisory in fast mode instead of rewriting every section.
5. Accept at least 90% source-aspect coverage, explicitly listing omitted aspects. Retain hard failures for invalid provenance, invented claims and contradictory meanings. Use the original aspect inventory as the final denominator so losses at successive stages cannot compound unnoticed.
6. Persist final audit decisions and a run deadline. Stop with a truthful incomplete result when the time budget is exhausted; do not restart the full pipeline automatically.
7. Test policy boundaries, deterministic repairs, ordered concurrency, checkpoint compatibility and an offline full fast-mode run. Then freeze code and launch a fresh complete live run with fast mode enabled, four workers and the 20-minute budget.

## Evaluation

Record wall time, model calls, automatic repairs, external interventions, source coverage, graph size, completion status and shared-ledger cost. Compare mechanism and observed full-run duration with the historical 19-attempt series; do not compare a full run with the historical 77-second resumed tail as if they were equivalent.

## Implementation verification

The full offline suite initially reported 305 passing tests and three regressions. All three were repaired and their focused reruns passed: incomplete test evidence is not a repair source; strict coverage still rejects missing summary mappings; the standalone inspector script retains its ASCII contract. Additional tests cover the full fast pipeline, persistent deadlines, the global source-aspect denominator, concurrency, ledger accounting and deterministic repairs.

The live evaluation exposed two pre-existing integration assumptions that focused offline fixtures did not cover. Concurrent first use could construct and close overlapping SDK clients; the client is now initialized before workers and retained throughout each request. A regression test checks one construction and lifetime during cache eviction. Separately, requiring topic scope to equal every rule scope conflicted with the instruction to group one business capability. Topics can now encompass narrower independently audited rules; each rule still preserves its verified fact scope and exact source-backed topic relationship. The audit also now explicitly permits empty decomposition bindings when atomic conditions already preserve the original fact verbatim.

The evaluation retains its original 20-minute deadline across attempts. Reusing verified extraction must create a separate run revision and a provenance receipt; previous runs, source snapshots and ledger entries must remain untouched.

## Live result

The four related attempts `risk-fast-20261013-a` through `d` occupied 19 minutes 37.48 seconds from the first to the last recorded event. Their run windows totaled 9 minutes 20.47 seconds; the remaining intervals included diagnosis and implementation changes and are not a measured labor duration. There were 42 model requests, 40 responses, two initial client-lifecycle errors, six automatic repair transitions and three coordinator code interventions. No user intervention was required. The shared ledger retains PLN 2.833449 settled usage and PLN 3.030378 uncertain estimates.

The result is **incomplete**, not a successful full-pipeline speed benchmark. Graph construction and planning completed; four of six writing packets were verified. The last writing failure prevented assembly, final source-to-document audit and export. The graph has one main topic, 20 rules and 62 exact quotations, with measured source-aspect coverage of 37/38. This ratio does not prove equivalent retention of all source meaning.

After the live window, offline replay identified and repaired two mechanical mapping failures: shared-paragraph citations were incorrectly assigned to every fact instead of their grounded owners, and bare repeated citation tokens were used as passage locators. The repairs preserve prose, original quotes and every occurrence. Replay reduced the corresponding validation findings from four and two to zero. These final repairs have not been validated in another paid end-to-end run.

Machine-readable timing, costs, interventions and per-run detail are in `evaluation/fast-pipeline-20261013.json`. Independent graph review is in `evaluation/fast-graph-review-20261013.json`: parser metadata leaked into a rule's table name, and one condition group may conjoin separate implications. These remain quality limitations of the evaluated graph despite its automated audit acceptance. The interactive capture is `.docgen/inspection-fast-pipeline/index.html` and accurately retains the historical incomplete status.
