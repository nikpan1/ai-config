# Phase 2 implementation and validation

Date: 2026-10-08. Specification: [development-plan-phase-2.md](development-plan-phase-2.md).

## Final handoff status

Implementation is delivered with 69 passing tests, passing Ruff checks and a successful wheel/source distribution build. M1–M5 are implemented. M6 remains partially validated; M0S is partial and M7 is unvalidated. The user requested that the work be brought to a close, so all live processes were stopped with their checkpoints and immutable artifacts preserved. No API process remains running.

The cumulative shared ledger is PLN 104.2898 charged, zero reserved, and PLN 95.7102 remaining out of PLN 200. Charges include earlier development runs, retries and interrupted calls. Calls interrupted at handoff were conservatively charged at their full reservation because final provider usage was unavailable. This is a conservative development ledger, not an invoice reconciliation.

The latest completed live planning example is `phase2-smoke-v8`. Final-code experiments `phase2-smoke-v14-auto` and `phase2-smoke-v14-single` passed structural checks but were still rebuilding sections and briefs after semantic/template audit findings when stopped. They are not completed plans and do not establish the paired delivery-mode acceptance criterion. Concurrent repair requests can produce different model proposals; no invariant architecture result is claimed from those unfinished runs.

The medium live thread `phase2-medium-knowledge-v14` completed verification of 14 curated extraction batches: 667 claims, 184 entity descriptions and 224 source blocks. It completed 70/70 entity comparisons and 155/392 claim comparisons before the requested stop. Its knowledge is not finalized, and medium phase 2 planning was not started. Curation includes scope/version and requirement modality, exact evidence additions, scoped actor descriptions and locally attached legal-hold conditions; all curated batches were reverified through Gemini. This is not an untouched extraction-quality pass.

A bounded evaluation-only [prefetch helper](../scripts/phase2_prefetch.py) prepared some later comparison responses with three concurrent API calls through the same budget ledger. These are cached responses, not accepted comparisons. They require the unchanged sequential LangGraph validation and review gates. Its separate metrics and stopped status are included in [phase2-results.json](../evaluation/phase2-results.json).

The local preview package is `.docgen/delivery/phase-2-preview.zip`, with `.docgen/delivery/phase-2-preview/INDEX.md` as its browsing entry. It includes the completed small plan, 14 readable medium extraction batches and their complete JSON companions, source snapshots, validation results and the installable package. It labels the larger extraction as incomplete at corpus level. It contains neither API credentials nor generated phase 3 documentation prose.

## Implemented behavior

`docgen plan-documentation` consumes a completed phase 1 artifact or its export manifest, the Markdown template, an optional documentation brief, and an optional previous plan. It validates source snapshots, exact excerpts, extraction coverage, effective authority decisions, entity identity, and the inherited file selection before planning. Existing version 1 selections are explicitly labeled `snapshot_derived`.

The sequential LangGraph has all fifteen specified stages, including a separate review node. Bounded work items persist their immutable queue, result references and cursor through SQLite checkpoints. Functional unit discovery, hierarchical candidate synthesis, reassignment against the final global unit registry, and independent boundary verification precede template instantiation and page subdivision. Unit policy and delivery mode are independent.

The inventory retains complete records, qualifications, table and procedural context, reviewer attribution, unknowns, and audit-only dispositions. Each included obligation receives one canonical section. Supporting summaries and shared consumers retain local qualifications and links to that canonical treatment. Briefs contain exact source context, table and diagram specifications, unknowns, and completion checks. Writing jobs have bounded resolved contexts, nonoverlapping assembly, and an acyclic dependency graph that schedules details before summaries.

Finalization rechecks the current structural and semantic results before atomically publishing the plan, page briefs, source links, JSON/JSONL component exports and a hashed manifest. `ready_for_generation` describes readiness to write documentation; it is neither generated prose nor a claim that requirements have been implemented.

The CLI also supports exact source selection and a no-model `workload` report. Explicit workflow code/prompt manifests prevent incompatible checkpoint resumes. Old artifacts and checkpoints remain readable; continuing an old implementation requires its matching code. Development runs use immutable code copies under the ignored `.docgen/implementations/` directory for that reason.

## Verification

Regression coverage includes existing phase 1 behavior, three interleaved units under each delivery policy, shared canonical rules, scope accounting, corrupt inputs, safe paths, lost qualifications, stale audits, revision-bound correction, truncation splitting, two-repair limits, previous-plan identities, and a separate OS process restart after each meaningful planning stage. Checks also reject brief treatments that disagree with the allocation ledger and ineligible claims without an effective authority decision.

The regression suite includes 69 tests. The package build includes all planning modules and eight planning prompt files. Ruff and the regression suite are run against `src`, `tests`, and `scripts`; bundled skill files are not reformatted.

Additional checks exercise replacement of an invalid review response after a process restart, duplicate finding removal, inherited keep-distinct decisions, immutable import/shard references, and exact equivalence between the original exhaustive candidate policy and the indexed comparison queue. A split comparison run resumes with append-only result parts and completes all six required pairs without rewriting its first result. Invalid comparison IDs receive at most two repairs, then a blocking interrupt. Shared source blocks are counted once per bounded discovery context, with complete record participation. Readable exports link parent/child pages and canonical sections, with a separate complete page index.

## Live evidence

All development requests use Gemini `gemini-3.8-flash` and the existing shared PLN 200 ledger, including failed and truncated responses. No ledger reset, allowance increase, or source-authority shortcut is used. Machine-readable results are in [phase2-results.json](../evaluation/phase2-results.json).

The initial completed run, `phase2-smoke-v2`, plans the real finalized ArchiveService knowledge bundle: 15 claims, 4 entities and 12 relationships become 31 canonical obligations with 100% structural coverage. It produced one unit, four pages, 20 logical sections, 21 writing jobs and 21 completed semantic audit batches. This is a small integration test, not medium-size acceptance. Its two short detail pages motivated later subdivision prompt changes that include actual source statement volume.

Subsequent live experiments exercised failures as well as successful paths. Unit discovery initially separated hold controls from their archival journey; global reassignment and clearer boundary criteria corrected that behavior. Semantic audits exposed missing process context and confusion between root-template requirements and child patterns. Explicit supporting section references now carry cross-cutting process evidence. A bounded topic response also contained one out-of-batch ID; a revision-bound autonomous correction removed that assignment without modifying source facts. Diagnostics and failed revisions remain available.

`phase2-smoke-v4` also completed with 31/31 canonical obligations, one unit root and a source-index page, 22 sections and 32 bounded writing jobs. It includes the attributed autonomous correction described above and two automatic brief repairs. `phase2-smoke-v5` completed without a review interrupt: 31/31 obligations, one unit root and a source-index page, 23 sections and 31 writing jobs. Its 78 paid responses cost approximately PLN 3.0424 under the conservative ledger. Source statement volume now keeps this small functionality on its unit root rather than creating short detail pages.

The dedicated medium fixture contains approximately 42.9k estimated source tokens across two interleaved files, 48 scoped profiles, independently useful archive and delivery outcomes, shared audit requirements, recovery flows, explicit unknowns, and 14 reader questions. It is generated by [phase2_fixture.py](../scripts/phase2_fixture.py); [phase2-reference.json](../evaluation/phase2-reference.json) records its expectations. The fixture and its labels were authored autonomously and have not received user or held-out review. Medium live extraction and planning results are recorded separately when completed; the fixture's existence alone is not a passed evaluation.

`phase2-smoke-v8` completed without a review interrupt: 31/31 canonical obligations, one unit root plus the source index, 22 sections, 32 writing jobs and 32 completed semantic audit batches. Its 79 paid responses cost PLN 2.9687. Earlier failed revisions remain diagnostics, rather than being included in the success count.

The medium test exposed an upstream context bug: reconciliation received short record excerpts but not their complete original blocks, so it rejected details that the original block actually supported. Reconciliation now resolves the exact blocks through the existing index. A regression test covers short excerpts with complete source context.

The first medium extraction completed all 13 split batches. Later comparison found incomplete profile scope/version metadata that the batch verifier had missed. The evaluation-only [revision utility](../scripts/phase2_reconcile_revision.py) creates an explicitly linked new thread, preserves the old one, and supports curated metadata drafts derived from exact source scope declarations. All curated drafts must pass the normal Gemini verification nodes again before reconciliation. Changes, original signatures, parent checkpoints and reused references are recorded under the new run; no old checkpoint is silently reinterpreted and no corrected draft is promoted directly to complete knowledge. This is autonomous fixture curation, not acceptance of untouched extraction quality. The [live fixture driver](../scripts/phase2_live.py) is restricted to this authored source directory and records every review decision through LangGraph.

The supplied legacy corpus remains interrupted at a real conflict: CG-01 has mutually incompatible effective-date rules marked unresolved in the source. A second issue concerns missing attachment and rollback semantics. These are not converted into accepted behavior to obtain a successful phase 2 demonstration.

## Capacity measurements

Source sizes are UTF-8 byte heuristic estimates, not provider tokenizer counts. Deterministic stub results establish orchestration properties only, not semantic recall or correctness.

| Workload | Observed result |
| --- | --- |
| Approximately 100k source tokens | Complete phase 1 and phase 2 stub orchestration; 524 blocks and obligations, 100% canonical accounting, two units. Full measurements are in [phase2-scale-100000.json](../evaluation/phase2-scale-100000.json). |
| Approximately 500k source tokens | Complete phase 1 and phase 2 stub orchestration with an explicitly increased 40,000-task experiment allowance: 2,619/2,619 obligations, two units, four pages. The default 20,000-task admission failure is retained separately in [phase2-scale-500000-admission.json](../evaluation/phase2-scale-500000-admission.json). |
| Approximately 2m source tokens | Workload projection reaches the predeclared 20,000 comparison-task allowance and stops as incomplete. No candidate tail is discarded. No end-to-end claim. |

The latest 100k run used 96.26 seconds, 172,802,048 bytes peak resident memory and 45,203,779 bytes of artifacts. It made 1,016 knowledge and 806 planning stub calls; the largest serialized input estimates were 37,160 and 14,112 tokens, with zero oversized requests. The same fixture previously wrote 104,058,409 bytes before comparison results became append-only.

The completed 500k run used 1,197.60 seconds, 456,531,968 bytes peak resident memory and 396,375,814 bytes of artifacts. It made 24,218 knowledge calls, including 24,090 full-record comparisons, and 3,835 planning calls. Maximum serialized inputs were 37,214 and 14,125 estimated tokens, with zero oversized requests. The compact pre-extraction proxy had projected only 5,508 comparisons, demonstrating why actual record volumes must be measured. The process-only 40,000-task setting did not change `.env`, the default 20,000-task setting, or the API allowance. The initial admission-limited attempt remains recorded with its resumable checkpoint.

At approximately 5 times the source volume, observed elapsed time grew 12.44 times, memory 2.64 times, artifact bytes 8.77 times, knowledge calls 23.84 times, and planning calls 4.76 times. These are development-machine observations with concurrent work, not isolated throughput guarantees.

The scale runner declares resource acceptance bounds of 1.5 GB peak working set and 10 GB artifact growth. The comparison task bound is enforced before execution and after splits; memory and disk measurements flag an over-budget result after the run. These are experiment acceptance bounds, not an operating-system memory quota. Patterned profiles exercise wide groups and distant references but do not replace a representative labeled evaluation of diverse large tables and procedures.

M0S remains partial and M7 remains unvalidated. Indexed immutable tables, lazy comparison enumeration, streaming JSONL export, bounded model requests, linked result parts, and task admission checks improve resource behavior. The candidate policy is unchanged and checked against exhaustive fixtures; it still has a dense all-pairs worst case. Some global joins remain materialized in memory, and source knowledge bundles remain monolithic. A large nonreducing functional-unit registry stops with a visible technical error. These limits must be addressed and measured before claiming full two-million-token throughput. The 2m fixture has not completed full local orchestration; neither large fixture has completed a full live run.

## Remaining acceptance limits

Model audits are independent calls but are not proof of semantic completeness or zero unsupported content. Coverage percentages measure allocation of the completed knowledge bundle, not extraction recall against arbitrary source text. Multi-unit discovery and editorial grouping can vary between independent model runs.

Planning review accepts a replacement response for a pending bounded work item or a revision-bound replacement table for existing logical sections, pages or section briefs after a whole-stage audit. Component corrections invalidate and rebuild downstream outputs, including writing contexts and semantic audits. Replacement tables preserve identities; new structures and scope/input changes require a new immutable revision. Unknown or inapplicability labels cannot waive evidence or coverage checks.

Previous-plan reuse conservatively preserves IDs when obligation ownership overlaps and retains stable paths when safe. It does not perform semantic identity matching across changed source-record IDs and does not carry approvals forward.

M1–M5 have executable implementations and deterministic checks. M6 requires completed, reported smoke and medium live runs, including the `auto` versus `single_page` comparison; any incomplete experiment must remain identified as an acceptance limitation. See the machine-readable live results for the actual completion status.
