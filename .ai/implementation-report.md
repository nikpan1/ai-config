# Implementation and validation report

Validated on 2026-10-08.

## Delivered

The implementation follows `.ai/development-plan.md`; `.ai/plans/development-plan.md` does not exist.
All eight named stages are sequential LangGraph nodes with SQLite persistence, stable thread IDs, atomic versioned artifacts, review interrupts, and revision-bound decisions. The CLI supports starting, inspecting, resuming, reviewing, budget inspection, and recording verified pricing.

Source provenance, complete block accounting, bounded context, two repair attempts, truncation splitting, independent verification, conservative entity reconciliation, conflict review, and immutable final bundles are implemented. Original claims and all evidence remain available.

Template mapping and final prose generation remain later phases, as specified in the plan.

## Verification

- 23 automated tests passed, including restart and `Command(resume=...)` across separate OS processes.
- Ruff checks and formatting passed; the distribution wheel includes all versioned prompts.
- Tests exercise exact source locations, table coordinates, missing inputs, truncation, repairs, concurrent cost reservations, unknown-failure charging, stale decisions, unsupported facts, entity scope separation, conflict eligibility, and cyclic duplicate coverage.
- Full provided corpus inventory: 3 files, 4456 blocks, 846,007 bytes; no ingestion problems. All blocks were assigned once across 36 initial 8k batches.
- Scale fixture: 1,155,003 whitespace-delimited words, 35,001 blocks, 340 bounded batches, 2.53 seconds for ingestion and planning. This was a structural test, not a full live model run or a semantic completeness measurement.
- Real Gemini smoke pipeline completed: 15 claims, 4 entity entries, 11 covered blocks, and zero unresolved issues. Its synthetic source specifies a coherent archive service.

## Quality measurements

Forty passages were annotated from the supplied corpus: 30 development passages and ten held out. The user has not reviewed the reference. Autonomous evaluation therefore records exploratory measurements and does not claim acceptance. Held-out labels were withheld during implementation and tuning, then scored once after the implementation was frozen.

On all 30 development passages, Gemini's independent scoring retained 88/88 annotated facts, 23/23 qualifications and 5/5 entity distinctions. It reported 0 unsupported additions and 0 incorrect merges. The selected reference queue completed extraction and verification without code or verifier defects; source conflicts were retained as findings. Scoring uses the same model family and is not independent human proof.

The final held-out check scored 10 passages: 30/30 facts, 9/9 qualifications, 1/1 entity distinctions. Unsupported additions: 0; incorrect merges: 0. No tuning followed this check.

The size experiment used the same roughly 16k-token source sample and stopped after the first effective batch in each variant. It tested nominal 8k/16k/32k ownership limits, including splitting. It is not a complete, controlled corpus benchmark: nominal 32k did not receive 32k of source, effective batches differ, and a transient server failure affected the 16k timing.

| Nominal source budget | Initial/effective batches | Splits | First-batch claims | Facts | Qualifications | Verifier findings | Seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 8000 | 3/4 | 1 | 54 | 12/12 | 5/5 | 0 | 255.3 |
| 16000 | 2/4 | 2 | 56 | 12/12 | 5/5 | 0 | 421.77 |
| 32000 | 1/3 | 2 | 55 | 11/12 | 5/5 | 3 | 273.71 |

The 32k variant lost the instruction to preserve an attachment-list ambiguity for migration review. Reference scoring detected that omission; the independent verification pass reported three source issues but did not identify the omission. This demonstrates that model verification alone is insufficient and larger nominal batches are not automatically better. Early runs also exposed overly strict structural-header exclusions; the implementation now recognizes empty HTML anchors and table headers without excluding factual prose.

## Legacy source review

The current run `legacy-final` is `review` with 2 open issues after extraction and independent verification. CG-01 preserves the incompatible rules about effective versus approval dates. No authoritative version was invented and no final legacy bundle was produced. The saved interrupt and readable source report are the expected behavior for this unresolved corpus.

Local review report: `.docgen/runs/legacy-final/review-c909bbddcb95f27a.md`.

## Cost and retained evidence

The cumulative conservative charge is **10.4132 PLN** of 200 PLN, including retries, thinking/output usage and 30% billing headroom. Outstanding reservations: 0.0000 PLN. An API server failure with unknown usage was charged at its full reservation. The actual provider invoice may differ; the development ledger was never reset.

Verified prices: USD 0.75 per million input tokens and USD 3.75 per million output tokens through 2026-12-31, from [Google](https://ai.google.dev/gemini-api/docs/pricing). The [NBP USD rate](https://api.nbp.pl/api/exchangerates/rates/a/usd/?format=json) on 2026-10-08 was 3.9132 PLN (table 196/A/NBP/2026). The saved pricing record expires on 2026-10-15 and must be refreshed before later live calls.

Portable results are in `evaluation/results.json`; reference annotations are in `evaluation/reference.json` and `evaluation/reference-review.md`. Detailed model responses, token usage, checkpoints and source snapshots remain under ignored `.docgen/`.

## Acceptance boundaries

Implementation and automated checks are complete. Full legacy-corpus acceptance remains unestablished: the reference lacks human review, source authority conflicts remain unresolved, and the greater-than-context run was structural rather than a complete live semantic evaluation. The limited size experiments do not satisfy a full matched 8k/16k/32k corpus comparison. The benchmark and checkpoint tooling support those follow-up evaluations without resetting spending.

The candidate reconciliation policy is bounded and auditable, but relationships sharing none of its name/entity/rule/scope signals can remain undetected. Source changes after reconciliation start a new revision; extraction-stage corrections are supported directly through review. Complete source accounting is not a claim of perfect semantic preservation.
