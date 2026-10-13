# Source-first implementation and independent comparison

## Result

The revised autopilot completes useful source-backed documentation and a navigable graph in one uninterrupted process, with bounded automatic repair and no human gate. The corrected measured run took **198.20 seconds**, used **8 Gemini requests**, and required **zero coordinator or user interventions during execution**. Its status is `complete_with_limitations`, not full semantic acceptance.

This evaluation required **two fresh full runs**. The first completed in 180.49 seconds but failed independent quality review. A corrective development round separated the runs. Neither run was resumed or edited while executing. It would be misleading to describe the entire development evaluation as a first-attempt success.

Process reliability, formatting robustness, source navigation and image provenance improved. Semantic quality is mixed: several old errors disappeared, but the model still occasionally strengthens a necessary condition into a sufficient one or assigns an unsupported scope to an ambiguous instruction. Exact quotations alone do not prove that an interpretation is correct.

## Implemented scope

- The parser preserves exact source text in size-bounded windows. Headings, tables and identifier patterns no longer determine the knowledge schema. Small corpora are supplied substantially in full; larger contexts remain bounded, with adjacent windows and explicit omission reporting.
- Gemini analyzes actual image bytes. Generated descriptions, visible text and uncertainty have explicit provider/model and image-hash provenance. Prepared Markdown receives image-title descriptions; original Markdown and image bytes remain unchanged.
- Active source-first graph generation uses concepts and natural-language relationships with source quotations and direct/inferred/uncertain status. Legacy formal condition graphs remain readable. Cross-document codes and links are interpreted semantically rather than used as identity rules.
- Bad graph interpretations are withheld individually. One invalid image relationship no longer discards an otherwise supported graph batch. Original assertions remain available even when no semantic concept claims them.
- Source-first autopilot uses persistent sequential LangGraph checkpoints, a stable run ID, bounded repairs, a total deadline and a finalization reserve. It writes from originals, with the graph serving as navigation. Recoverable uncertainty does not trigger human interruption.
- Citation-invalid paragraphs are withheld before the final document audit. The audited candidate has a content hash. If semantic quarantine changes the exported content, the report explicitly invalidates the coverage estimate for that export.
- Exact quote locations now include source line and column ranges. The viewer retains descriptions, uncertainty and source navigation. Degraded source bundles are distinguished from useful completed documentation.

## What was compared

The unchanged corpus is `data/test_data_2_quick/risk-profiling.md` plus two synthetic JPG mockups, using `data/template.md`. The Markdown contains 3,723 characters. Its SHA-256 is `b6e3143fb5ab3629346e870f65cd8cbc4eceee675fd2d614cebda5087f74cf90`. This is a small synthetic risk-profiling fixture, not a representative production corpus.

The historical graph is from `risk-fast-20261013-c`; the subsequent consumer attempt did not finish documentation. There is consequently no historical final-document quality score to compare with the new output. Historical aspect inventory coverage, new model coverage estimates, fact presence counts and semantic accuracy are different measurements.

An independent agent read the original text, inspected both image pixels, queried actual persisted graphs and compared generated artifacts. It did not assume that successful tests, matching quotes, model audit acceptance or a larger graph established semantic correctness.

## Timing and intervention record

| Measurement | Historical fast series | First source-first attempt | Corrected source-first attempt |
| --- | ---: | ---: | ---: |
| Full-process attempts | 4 related attempts | 1 fresh process | 1 fresh process, second in this evaluation |
| Elapsed measurement | 19m 37.48s calendar window | 3m 0.49s process wall time | 3m 18.20s process wall time |
| Active historical run windows | 9m 20.47s | Included above | Included above |
| Gemini requests | 42 | 8 | 8 |
| Recorded automatic repair transitions | 6 | 1 citation rewrite | 1 citation rewrite |
| Coordinator intervention | 3 code intervention rounds in the series | 0 during execution | 0 during execution |
| User intervention | 0 | 0 | 0 |
| Final documentation | Not completed | Completed, independent quality failure | Completed with explicit limitations |
| Settled run cost | See historical ledger report | PLN 0.5274 | PLN 0.5557 |

Both new process executions together took 6m 18.69s. The calendar window from the first start to the second completion was approximately 12m 54s; this includes the intervening investigation, corrections and other work. The improvement is not a controlled speed benchmark: the workflow changed and the historical series never produced the same final artifact.

Corrected-run model time: images 9.89s, extraction 30.56s, graph proposal 23.10s, plan 3.46s, writing plus one citation rewrite 96.35s, final audit 32.05s. Model response intervals occupy approximately 195.41 of 198.20 seconds. Writing and its bounded rewrite dominate; local parsing and SQLite operations are not the main delay.

## Quality findings

| Dimension | Before / first-run problem | Corrected measured result |
| --- | --- | --- |
| Formatting as knowledge | Historical graph leaked `table:11` into authored scope and conjoined independent QF08 implications under `all` | Those two defects are absent; active schema has no mandatory formal groups |
| Batch resilience | Two bad image relationship quotations erased the whole first-run semantic batch | Valid records survive independent invalid records; corrected run persists 8 concepts, 24 total semantic edges and 17 exact quotations |
| Source allocation | First new run persisted no semantic nodes or edges | 13 of 16 assertions are allocated to concepts; the remaining assertions are still retrievable. Allocation is not information recall |
| Operational facts in documentation | First export omitted idempotency key stability, duplicate-result reuse and no-provider-call behavior for incomplete drafts | All three are restored |
| Unsupported expansions | First export claimed permanent historical retention, generalized a fractional-value restriction and invented deployment prerequisites | Permanent-retention and fractional-value expansions are absent; the unsupported deployment section is withheld |
| Final-audit truthfulness | First audit reported 0.98 for a candidate different from the final export | Audit records the actual pre-semantic-quarantine candidate. Export differs afterward, so `semantic_audit_matches_exported_content=false` and `exported_coverage_estimate=null` |
| Residual graph correctness | Old rigid condition modeling produced false conjunctions | One direct relationship now incorrectly turns an incomplete-response prohibition into a sufficient acceptance condition; retry scope is also overinterpreted |
| Residual document correctness | Earlier recovery interpretation was too strong | The final body still assigns retry to failure. A limitation copied from the auditor incorrectly infers that Q2 is valid before a cutoff merely because it is prohibited afterward |

The independent 27-item authored-fact checklist found 24 present in the first narrative and 25 in the corrected narrative. The corrected narrative omits two provider-boundary facts from its business sections; they appear only in the limitation explaining the omission. These are small, unweighted presence checks, not measured percentages of retained meaning, and they do not subtract unsupported additions. They cannot justify claiming a universal preservation percentage.

The corrected model audit estimated 0.88 coverage and rejected its candidate. That estimate does not apply to the final export after an unsupported paragraph was removed. The exported result is useful but has not passed a comprehensive semantic quality gate. The run name containing `verified` denotes the corrective verification attempt, not a semantic certification.

## Robustness beyond the main fixture

The predeclared cases are in `source-first-cases.json`. Two separate live stage evaluations exercised extraction and graph proposal only; they were not full pipeline reruns.

- Initial evaluation: 8 cases/variants, 129.12s. Three library formatting variants were rejected by the legacy formal-condition contract despite preserving the intended meaning. This led to removing that contract from the active source-first model schema before the first full run.
- Final-schema evaluation: 8 cases/variants, 90.03s. All eight pass structural/source validation. The four library variants preserve both requirements and the limited staff exception. Warehouse implications remain independent; rental references connect supplied documents; contradictory 30/45-day policies coexist without invented reconciliation; matching R-17 codes do not merge unrelated sites.
- Semantic limitation: R-17's “should address” is still strengthened to “is planned to address” in one direct interpretation. The final-schema evaluation is therefore not an eight-out-of-eight semantic accuracy claim.
- Large-context boundary mechanics and image preparation have offline tests. The two real images are exercised in both main runs. No large production corpus or real oversized full run was measured here.

## Verification and artifacts

All 359 collected tests passed across the final suite and one targeted rerun: 358 passed in the full run; the remaining CSV test passed separately with a shorter temporary path. Its failed full-run check used a 266-character Windows path; the file existed under the extended path but was invisible to ordinary `Path.is_file`. Earlier sandbox and longer-path test executions are retained in logs rather than presented as application regressions. Ruff, JavaScript syntax and diff checks passed. The final inspector export has zero diagnostics.

- Implementation plan: `../.ai/plans/2026-10-13-source-first-autopilot.md`.
- Historical process: `fast-pipeline-20261013.json`; historical graph review: `fast-graph-review-20261013.json`.
- First new process: `source-first-pipeline-20261013.json`.
- Corrected process: `source-first-verified-pipeline-20261013.json`.
- Independent review, including original quotations, hashes and residual defects: `source-first-independent-review-20261013.json`.
- Corrected output: `../.docgen/source-first-verified-20261013/runs/source-first-verified-20261013/output/documentation.md`.
- Corrected graph viewer: `../.docgen/inspection-source-first/index.html#view=graph&graph=current`.

The measured gain is reliable bounded completion and better source handling. More diverse production documents, remote cross-document dependencies and semantic strengthening errors remain evaluation risks. Future quality work should target those errors with independent source-based checks, rather than add mandatory domain-specific identifiers or restore rigid topic/condition schemas.
