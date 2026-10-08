# Phase 3 implementation and validation

Date: 2026-10-08. Specification: [development-plan-phase-3.md](development-plan-phase-3.md).

## Authorized language-policy change

During implementation, the user explicitly replaced the requirement for a local official ASD-STE100 Issue 9 reference with a manually authored, substantially simplified policy: professional but simple English. The implementation therefore uses `plain-technical-english-v1`. It pins the policy hash and terminology revision, preserves quotation and identifier handling, and performs mechanical and independent model review. It does not require the official dictionary, redistribute the standard, or claim formal STE compliance. This is an authorized change to the original phase 3 plan.

## Implemented workflow

`docgen generate-documentation` accepts an immutable completed plan or its export manifest. It validates schemas, component revisions, exact frozen knowledge and source snapshots, template hashes, eligible evidence, current structural/audit checks, writing contexts, dependency order and canonical fragment ownership. Schema-version-1 plans from the earlier completed implementation remain usable: absent optional `knowledge` and `planning_inputs` back-references are resolved from the plan itself, while inherited references that are present must match. This supports the completed ArchiveService plan without re-running its earlier phases.

All named phase 3 stages are sequential LangGraph nodes using the existing SQLite checkpointer, synchronous durability, stable thread IDs, artifact store, worker lock, logging, Gemini client and cumulative cost ledger. Each writing job and verification step creates a checkpoint. Large records remain in immutable artifacts. The model is still restricted to `gemini-3.8-flash`.

Writing produces typed passages and table cells with obligation IDs and exact source excerpts. Deterministic checks reject unsupported references, missing canonical coverage, missing citations, altered quotes, unplanned table rows or columns, injected HTML and arbitrary links. An independent Gemini request checks facts, local conditions, exceptions, timing, scope, version, modality, entities, uncertainty, table cells, diagrams and language. There are at most two automatic fragment repairs. Plan-specified diagrams are emitted as Mermaid fences, with evidence mappings, text descriptions and visible unknown transitions.

Assembly follows the planned page/section tree and fragment order. It adds stable heading links where unambiguous, canonical links, navigation, citations, a source index and disposition accounting. Existing attachments require explicit link, image or exclusion decisions; image explanations must identify a reviewer. Source assets are linked to immutable snapshots, never copied into the documentation directory or interpreted through vision.

Global checks revalidate inputs and fragment revisions, account for every canonical obligation, and check Markdown structure and local links. Each non-source page receives a separate bounded model audit against its complete allocated evidence. A page that exceeds the configured request bound fails visibly; it is not silently truncated. A final presentation report identifies representative long, table, Mermaid and unknown-bearing pages. Source quotes and literal code remain distinct from authored English. Escaped HTML in an exact source quotation is allowed as literal text; raw HTML output is rejected.

Publication creates immutable reader-facing `.md` directories and separate generation metadata, writing the final manifest last. Repeated publication checks existing hashes instead of overwriting files. The initial release is `ready_for_review` and enters a LangGraph human-release interrupt. `complete` requires an explicit revision-bound review of content accuracy, reader usefulness, language and Markdown. Corrections return to verification and invalidate dependent writing jobs; original output revisions remain inspectable. Content review cannot waive unsupported facts, broken provenance or missing mandatory coverage.

Generation model-response caches are off by default. The optional validated cache is written only after successful structural and independent semantic checks. Keys include frozen plan, source, brief, language, dependency and code revisions. Budget/technical errors retain their checkpoint. All live requests use the existing conservative reservation and usage-accounting path.

## Validation

The complete existing and new suite passed 86 tests in 120.06 seconds. Six additional focused checks passed after that run: four factual-table corruption cases, source-asset integrity, and literal escaped source markup. The original raw-HTML/heading/link regression was rerun with the last change. Ruff checks and package build passed. No large stress suite or second complete live corpus was run, respecting the user's request to minimize long tests.

Generation tests exercise two units, immutable publication, human release, restart after each of the ten processing stages, bounded repairs, interrupted corrections, rejection of stale decisions, corrupted input artifacts, stale plan revisions, missing coverage, false excerpts, absent assets, changed assets, unauthorized paths/links, raw HTML, heading hierarchy, table cells/rows and Mermaid escaping. The deterministic model is a structural fixture, not semantic acceptance evidence.

## Live example and acceptance scope

The live example uses the completed `phase2-smoke-v8` ArchiveService plan, with 32 writing jobs and two planned pages. It does not repeat extraction or planning. `scripts/phase3_live.py` freezes the implementation and records its hashes so the run remains resumable during local development. `scripts/phase3_results.py` reports cost, runtime, token usage, checkpoint count, validation and human-review status separately. Its output is retained in `evaluation/phase3-results.json` and in the run directory.

The small live example is not evidence of medium multi-unit or large-corpus semantic readiness. Medium orchestration is covered only by deterministic fixtures. No human content acceptance or external language certification is claimed. The implementation preserves the original phase 2 plan structure, including its verbosity and repeated supporting treatments; phase 3 does not silently redesign that structure.

### Recorded live outcome

Thread: `phase3-archive-live-v1`. All 32 writing jobs completed, with 31/31 canonical obligation allocations and 621 checked Markdown links. The run produced two `.md` pages, including two Mermaid blocks. It made 72 paid requests with response-cache reuse disabled, charged PLN 8.0086 including conservative billing headroom, and left no reservation outstanding. Model response time was 738.21 seconds; time between the first and last generation events was 906.98 seconds (15.12 minutes), including interrupted correction handling. The final checkpoint count after source review is 95.

The example is available at [the generated index](../.docgen/runs/phase3-archive-live-v1/documentation/13ad662b5672261673339ff85ece0ecca2d8fb703e0744a6572776eaa1d03cc3/index.md). Two corrections were submitted through revision-bound `Command(resume=...)` decisions, attributed to automated Codex source/editorial correction, not human acceptance. They repaired a blanket unknown statement and attached the right source to a local information gap. Both returned through independent verification.

The assembled-page model audit returned no findings. A subsequent direct source review found two blocking inconsistencies: the retry table says eligibility criteria are unspecified despite ARCH-1 defining them, and an inherited diagram calls hold=true handling unknown despite ARCH-2 defining it. The operator section also uses an overly broad unknown-schedule statement. Internal planning jargon and repetition remain editorial weaknesses of the frozen example.

These findings are recorded in [the source-review notes](../.docgen/runs/phase3-archive-live-v1/review-notes/733a68e036669d10aa3d4bd98c2afd15ece8eb6f887b0229b88d96c24aae5406.md) and were registered as blocking issues through the persisted `review_generation` node. The current run status is `awaiting_review`, while the previously published candidate remains immutable with its original `ready_for_review` manifest. No `complete` release exists. Ordinary release approval cannot waive the source findings. A new upstream plan revision or an authorized evidence-backed alternative is needed for the defective inherited diagram.

The live run deliberately preserves its actual output instead of silently replacing it with manually edited files. It is a reviewable example, not a successful semantic acceptance result. This distinguishes passing allocation/link checks and a clean model audit from source correctness. A second long live corpus was not run.

After observing the example, the current writer prompt was strengthened to suppress planning jargon, the page-audit prompt was strengthened to cross-check all unknown claims against all supplied blocks, and citation errors now identify the affected passage or table cell. Escaped source markup was also corrected in the Markdown checker. These changes have focused deterministic regression coverage, but their semantic effect has not been claimed as validated by another paid run. The frozen example's implementation and these subsequent improvements are explicitly distinct.

A further focused test confirms that a blocking page-level semantic finding prevents publication and enters `review_generation`; it passed in a 3.19-second test run. There are 93 distinct passing tests across the initial full suite and the seven added targeted cases. Ruff and the final package build also passed after the changes.
