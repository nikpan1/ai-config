# Development Plan: Faster Processing and Reader-Friendly Documentation

Date: 2026-10-11

Status: proposed implementation plan. No runtime behavior has been changed and no new live acceptance result is claimed.

## 1. Objective

Revitalize the existing three-phase pipeline so that large source collections require substantially less elapsed time and operator effort, while the generated documentation becomes coherent, approachable, and visually organized.

The intended experience is to start a run, let it complete all work that does not require a source-authority decision, and review a polished candidate with one concise decision package. The reader should encounter an explanation of the system, rather than the pipeline's internal obligation ledger rendered as prose.

This is a cross-phase change: extraction and reconciliation determine throughput; planning determines the document's structure; writing, editing, and rendering determine readability. Adding another polishing prompt alone will not meet the objective.

### Relationship to existing plans

This plan builds on [phase 1](development-plan.md), [phase 2](development-plan-phase-2.md), [phase 3](development-plan-phase-3.md), and [AGENTS.md](../AGENTS.md). It proposes replacing the earlier policy that every unresolved issue immediately pauses its producing stage with dependency-aware, consolidated review. It also proposes bounded concurrent preparation of independent work while retaining one coordinator and sequential durable stage acceptance.

The following requirements remain binding:

- Preserve source snapshots, exact provenance, all substantive information, conditions, exceptions, modality, scope, and version distinctions. Extraction must not be filtered by the output template.
- Keep logical stages as LangGraph nodes, persistent checkpoints, stable `thread_id` values, immutable artifacts, and revision-bound decisions. Human interaction uses `interrupt()` and `Command(resume=...)`.
- Use only Gemini `gemini-3.8-flash` for model calls and reject another configured model. Centralize configuration, model access, logging, and file I/O.
- Read runtime settings from `.env`, maintain placeholder-only `.env.example`, and preserve the shared cumulative PLN 200 development budget, including retries and repairs.
- Never invent missing behavior, choose conflicting source authority automatically, silently drop comparison work, or treat model approval as proof of correctness.
- Keep the deliverable as portable Markdown with source indexes, tables, blockquotes, and evidence-backed Mermaid. A website, graphical editor, generated artwork, and a new export format are outside this increment.
- Use the already implemented professional, simple English policy. Do not reintroduce the superseded requirement for formal ASD-STE100 certification.

## 2. Findings from the current implementation

The measurements below are historical evidence from repository reports, not newly reproduced benchmarks or current budget balances.

| Finding | Evidence | Consequence |
| --- | --- | --- |
| Reconciliation has a dense all-pairs worst case. Shared entities, rules, and scopes produce large groups and cross-partition comparisons. | `comparison_tasks` and `iter_comparison_tasks` in [reconciliation.py](../old-approach/src/docgen/reconciliation.py). | More workers alone will not fix the growth in total work. |
| A fivefold source increase caused almost 24 times as many knowledge calls in the recorded stub experiment. | [Phase 2 report](implementation-report-phase-2.md): approximately 100k tokens used 1,016 knowledge calls; approximately 500k used 24,218, including 24,090 comparisons. Elapsed times were 96.26 and 1,197.60 seconds. | Optimize comparison volume before presenting concurrency as a scale solution. Stub timings do not predict live API throughput. |
| Planning and writing are overfragmented for small documents. | The completed small planning example used 79 paid responses for 31 obligations and 32 writing jobs; the phase 3 example used 72 paid requests and about 15.12 minutes. See the phase 2 and [phase 3 reports](implementation-report-phase-3.md). | Combine compatible tasks and write coherent sections instead of many isolated fragments. |
| Review gates stop progress at individual findings. | [workflow.py](../old-approach/src/docgen/workflow.py), [planning.py](../old-approach/src/docgen/planning.py), and [generation.py](../old-approach/src/docgen/generation.py). | Routine repairs and repeated findings consume disproportionate operator attention. |
| Final polishing already exists, but inherits rigid structure and can exceed the request bound. | [Editorial report](implementation-report-editorial.md) and [generation_editorial.py](../old-approach/src/docgen/generation_editorial.py). The preview needed a 200k request override; production defaults stayed unchanged. | Fix structure before writing and partition editorial context without truncating evidence. |
| Shorter output and a clean model audit did not establish factual quality. | The editorial preview fell from 87,390 to 28,003 bytes but subsequent source review found unsupported mechanisms, stronger guarantees, and lost qualifications. | Evaluate semantic fidelity and reader usefulness separately from length and structural coverage. |
| Citations and metadata dominate parts of the reader experience. | [generation_export.py](../old-approach/src/docgen/generation_export.py) renders `Source <hash>` labels; the retained editorial preview repeats scope, requirement labels, and internal metadata. | Keep precise traceability while simplifying visible citation labels and moving implementation metadata to audit artifacts. |
| Every uncached model request performs remote token preflight; generation caching is optional and limited to validated fragments. | [model.py](../old-approach/src/docgen/model.py) and [generation.py](../old-approach/src/docgen/generation.py). | Measure preflight latency and enable safe reuse at more stages before increasing request volume. |

Two-million-token end-to-end capacity remains unvalidated. Some global joins and final bundles still materialize large collections. The existing indexed storage, append-only comparison results, worker lock, conservative budget ledger, and resumable stages are foundations to retain.

## 3. Target operating policy: unattended work, consolidated decisions

Introduce a versioned review policy, persisted in the run signature. Make `consolidated` the default for new runs after validation; retain `strict` for diagnosis and compatibility. Policy selection must not weaken factual or coverage requirements.

| Issue category | Automatic handling | Human involvement |
| --- | --- | --- |
| Schema, formatting, citation placement, broken generated links, or bounded-context errors | Deterministic repair where possible; otherwise evidence-backed model repair and normal revalidation. Split oversized work instead of truncating it. | No routine question. Exhausted repair becomes a technical or content blocker, according to its cause. |
| Duplicate findings or equivalent editorial suggestions | Group by underlying cause and affected revision; apply one repair to all affected dependents. | Include only unresolved, actionable findings in the decision package. |
| Unsupported generated statement or omitted qualification | Correct from exact evidence, then independently verify. | Block acceptance of the affected output if correction fails; ordinary approval cannot waive it. |
| Conflicting authority, ambiguous identity affecting meaning, or missing indispensable evidence | Preserve competing evidence and isolate affected dependencies. Continue unrelated work. | Ask once at the next necessary dependency barrier, grouping all currently known decisions. |
| A source explicitly leaves a detail unspecified | Preserve a concise, locally qualified unknown; verify it against the complete relevant source context. | No mandatory question merely because a documented unknown exists. |
| Optional asset or presentation preference | Apply the frozen default inclusion/style policy and record the disposition. | Ask only when the asset contains necessary information that cannot otherwise be preserved. Keep the existing human-explanation rule for images. |
| API failure, rate limit, budget exhaustion, or corrupt artifact | Bounded retry/backoff or resumable technical stop with a precise diagnostic. | Do not turn technical failures into requests to adjudicate content. Never exceed the spending allowance. |
| Finished candidate | Run all acceptance checks and prepare a focused review package. | One final release review by default. |

### Review mechanics

1. Store findings in a shared revision-aware issue register with category, severity, evidence, affected work, repair history, and resolution provenance. Keep automated corrections distinct from human decisions.
2. Maintain dependency-level blocked status. A blocked batch or section cannot contribute accepted facts to downstream outputs, but unrelated batches and sections may continue. Draft artifacts remain explicitly incomplete.
3. Collect decisions when dependent progress would otherwise stop, after independent work has drained. Do not pause once per finding or call the reviewer again for an unchanged issue.
4. Present one readable Markdown report with grouped questions, exact source passages, affected pages, and concrete permitted decisions. Retain JSON as an interchange format; the CLI should allow selecting decisions without manually authoring replacement JSON records for ordinary cases.
5. Validate decisions through the existing LangGraph interrupt/resume path. Changed evidence invalidates affected decisions; cosmetic presentation changes alone should not invalidate unrelated source-authority decisions.
6. Keep `ready_for_review` separate from human-approved `complete`. A clean run should reach the former without intermediate human interaction. A conflict-bearing run may require additional dependency-barrier sessions; never promise a hard cap that forces silent acceptance.

A documented unknown is not the same as unresolved contradictory knowledge. Mandatory coverage and unresolved authority must still prevent a completed knowledge bundle or final release. Exporting partial drafts must never relabel them as complete.

## 4. Performance workstreams

### A. Establish a reproducible baseline

Extend existing workload and benchmark tooling instead of adding a separate monitoring system. Record, per phase and logical work item:

- Wall time, active processing time, human waiting time, model latency, token-preflight latency, retry/backoff time, and checkpoint/file I/O time.
- Paid request count, input/output usage, repeated context volume, truncations, repairs, cache hits, and conservative PLN charges.
- Source blocks, obligations, candidate relationships, actual comparisons, writing tasks, largest groups, queue depth, and unperformed work.
- Peak resident memory, artifact growth, review sessions, unique questions, operator actions, and measured review time.

Freeze source fixtures, templates, settings, implementation signatures, and the original outputs. Separate cold-cache, warm-cache, deterministic-stub, and live-model results. Report failures and partial runs alongside successful ones. Do not reuse the old report's remaining budget as the current allowance; read the actual shared ledger before any experiment.

### B. Reduce reconciliation work without losing coverage

Implement safe reductions first:

1. Use normalized typed identity, rule, scope, version, and explicit dependency indexes to explain why records require comparison. Broad shared words or scope alone should be identified as sources of candidate expansion.
2. Deduplicate required pair coverage across overlapping groups, not only identical task payloads. Persist a compact comparison-coverage ledger that records which input revisions and contexts discharged each required relationship. Reuse must preserve any group context relevant to the decision.
3. Collapse byte-equivalent, identically qualified records into comparison representatives while retaining all original records, evidence, and coverage mappings. This is computational deduplication, not an automatic semantic entity merge.
4. Pack remaining required comparisons into bounded tasks with explicit checked relationships. A set of checked record IDs alone does not prove all required pairs were checked.
5. Cache successful validated comparisons by record, source-context, policy, prompt, schema, model, and validator revisions. A changed record invalidates its relevant comparisons and dependents, not every unaffected result.

Only then evaluate a new candidate policy that separates demonstrably unrelated records and makes cross-scope dependencies explicit. Compare it with exhaustive small fixtures, known distant conflicts, ambiguous names, missing scope, cross-version contradictions, and unclassified records. Unknown compatibility must take the broader fallback path. Semantic summaries or top-k retrieval cannot replace complete source accounting or justify discarded comparisons.

Candidate pruning is an acceptance-gated optimization, not an assumed equivalence. Record retained, safely discharged, and unresolved relationship work with reasons. If quality or relationship recall regresses, keep the original candidate policy and ship the safe reductions independently. Dense legitimate groups can still be expensive; publish their workload and preserve visible admission limits.

### C. Increase useful work per model request

- Combine small section-brief and writing tasks when they share a page, compatible evidence, and dependency level. Keep each obligation's canonical ownership explicit inside the combined result.
- Design extraction batches from measured input/output density, table and procedure boundaries, and truncation history. Compare existing 8k/16k/32k options within the available test budget; do not enlarge every request indiscriminately.
- Resolve shared evidence once per payload and reference it by stable IDs within the request. Retain full relevant source blocks, qualifications, and table headers; do not substitute lossy summaries for evidence.
- Cache exact token-count preflight results by the full counted input and model revision. Keep conservative schema/output bounds and the existing reservation safety margin. Changing reservation assumptions requires separately verified provider limits and pricing.
- Avoid verifying substantially identical unmodified text multiple times. Every newly authored or materially rewritten unit still receives deterministic checks and an independent semantic check. A final audit should focus on cross-unit consistency and complete accounting rather than blindly repeat every local check.

### D. Add bounded concurrent preparation with durable acceptance

Retain one active coordinator, one graph-state writer, and the existing run lock. Introduce a small configurable in-flight window for independent model requests, initially evaluated at 1, 2, and 3. These are runtime requests, not multiple agents or concurrent coordinators for the same thread.

- Dispatch only tasks whose accepted dependencies are immutable. Summary writing waits for its detail sections; verification waits for its draft; finalization waits for all required accepted results.
- Persist each completed response atomically by work key before ordered stage acceptance. Worker responses are candidates until the appropriate LangGraph validation node accepts them.
- Keep each logical draft, verification, reconciliation, and assembly stage as a node. Commit accepted progress sequentially, with a checkpoint after each accepted work item/stage boundary. Prefetch is an optimization around those boundaries, not a replacement pipeline hidden inside one long node.
- On restart, consume durable completed responses and redispatch only unfinished work. Account for the crash window where the provider completed a request but no response was persisted; do not claim exactly-once API execution.
- Use bounded queues, rate-limit backoff, conservative reservations for every in-flight request, and a lower effective window when remaining allowance cannot fund the configured window. Preserve uncertain charges after crashes.
- Verify SDK client/thread behavior against the installed version before choosing threads or asynchronous calls. Serialize graph mutations, event writes where required, and cache publication; test budget reservation races and independent-run contention.

Start with independent reconciliation tasks and sibling writing tasks. Expand only after crash recovery, deterministic acceptance order, and shared-ledger tests pass.

### E. Reuse work and bound storage

Extend validated artifact caching to plans, editorial units, and semantic checks with explicit dependency keys and validator versions. Reusing a raw response must never skip acceptance checks. Separate operational settings such as concurrency from content-affecting signatures so scheduling changes do not invalidate unchanged content.

Track dirty dependencies from changed source blocks through claims, comparisons, plans, writing units, and citations. A source change can alter global identity or architecture, so conservatively expand invalidation when needed. Start with exact-revision reuse; cross-revision incremental reuse comes after dependency correctness is established.

Replace repeated whole-table scans and monolithic intermediate copies with indexed reads and streamed exports where profiling identifies growth. Keep a manifest over immutable partitions while maintaining compatibility for existing bundles. Avoid building an in-memory quadratic pair set merely to save API calls.

## 5. Documentation quality and presentation

### Plan for a reader before planning model jobs

Create a versioned editorial contract from the existing documentation brief and template. Defaults: a domain-aware reader new to this system, professional plain English, concise connected prose, restrained visual emphasis, and compact local citations. Apply defaults without a questionnaire for every run.

Separate mandatory template requirements from illustrative headings and example rows. Never turn template placeholders into product facts. Group content by reader questions, capabilities, and user journeys; use obligation IDs for coverage behind the scenes. Several obligations can support one paragraph, table row, or explanation.

Use a coherent progression: purpose and boundaries, a short overview, normal operation, important rules and exceptions, integrations where relevant, and genuine open questions. Choose page boundaries from reader navigation and bounded evidence size. Avoid numerous tiny sections and a single oversized chapter.

Before freezing the new plan, run a structural editorial pass that merges repetition, assigns canonical explanations, and checks necessary local qualifications. Existing frozen plans remain immutable; structural redesign creates a new linked plan revision. Do not ask the final editor to repair structure while requiring it to preserve every obsolete heading.

### Write coherent units, then edit gently

- Write a complete coherent section or bounded chapter segment in one task where practical, with all its allocated evidence and required qualifications.
- Use the final editorial pass for flow, transitions, concise phrasing, and consistency. Avoid rewriting already verified facts unnecessarily. Preserve exact quotations and normative force.
- Keep requirements understandable through verbs such as `must` and `may`; avoid prefixing every paragraph with `Requirement`. Establish scope once, then repeat it locally wherever omission would mislead.
- Remove duplicated explanations, not unique information. Summaries may omit detail only when they remain accurate and link to a complete canonical treatment.
- Remove implementation hashes, object paths, allocation terminology, and audit counters from the reading path. Retain readable document version/source information and keep technical metadata in the manifest and audit reports.
- Partition oversized editorial work along semantic boundaries. Every obligation and all its evidence must enter a bounded verification unit; retain shared context and perform a cross-unit consistency check. Neither evidence truncation nor raising the request limit indefinitely is acceptable.

### Add useful visual structure

Use visual elements to help readers answer questions, not to decorate every section:

| Element | Intended use | Guardrail |
| --- | --- | --- |
| Short opening summary and optional “At a glance” block | Orient the reader quickly. | Do not repeat the whole chapter or fill unknown slots with guesses. |
| Numbered steps | Explain an evidenced sequence or procedure. | Preserve branches, eligibility conditions, and failure paths. |
| Compact tables | Compare conditions, decisions, actors, or outcomes. | Avoid one-row tables and wide prose-heavy matrices unless the template requires them. Keep row-level sources. |
| Labeled blockquotes | Highlight a consequential constraint, exception, or distinction. | Use sparingly; do not exaggerate the source's warning or requirement. |
| Mermaid flow or state diagram | Explain a process whose relationships are evidenced. | Verify every edge and condition, provide a textual explanation, and test rendering in the selected viewer. |
| Descriptive links and contents/navigation | Help the reader move between canonical explanations. | No raw hashes in labels, broken anchors, or repetitive “see also” chains. |

Correct defective diagram specifications through a new plan revision before rendering. If an optional diagram cannot be supported, replace it with a complete evidence-backed explanation. Do not preserve a known false diagram merely to maintain its original fence.

### Make sources precise but unobtrusive

Render compact stable labels such as `[S1]` as ordinary Markdown links to the source index. Assign labels deterministically for a frozen release and retain immutable evidence IDs internally. The source index resolves each label to path, heading, line range, exact excerpt, and any reviewer attribution.

Place references beside the supported paragraph, table row, or diagram note. Group identical supporting citations within that unit; do not detach all evidence into a bibliography. Keep a machine-readable passage-to-obligation-to-evidence map so presentation changes cannot hide missing support. If a paragraph contains separately qualified claims, split it or provide suitably local reference groups.

Illustrative style target, subject to verification against the selected source revision:

> The service runs daily at 02:00 UTC. A revision is eligible for archiving only when its status is approved and its archive hold is false. [S1]

The improvement is a connected explanation with a readable source marker. It must not add a scheduler technology, stronger idempotency guarantee, or implied next action.

### Verify facts and reader usefulness separately

Retain complete structural coverage checks and independent semantic review. Add targeted checks based on actual prior failures: false unknowns, unsupported technology names, inferred request contents, strengthened guarantees, conditions lost in summaries, and contradictions between diagrams and prose.

Use a separate editorial rubric for coherence, ability to locate answers, repetition, plain language, and visual hierarchy. Mechanical metrics are diagnostics, not proof of good writing. Include a blinded before/after assessment in the consolidated release review; do not introduce a new human approval gate for every page.

Inspect representative rendered pages during development, including a long chapter, dense rules, a table, a Mermaid flow, and unknown/conflicting-source cases. Rendering is a QA activity; the shipped artifact remains Markdown. Ensure the text remains understandable in viewers without Mermaid support.

## 6. Workflow and implementation map

Preserve phase boundaries and their immutable handoffs. Within each phase, use the same operational cycle: plan bounded work, prepare eligible requests, validate results, accept durable progress, register findings, and continue independent work. Enter the existing review node only at a necessary dependency barrier or final release.

The generation path should become: validate inputs → prepare editorial and asset contracts → draft coherent unit → verify unit → assemble pages → polish bounded editorial unit → verify revision → validate full document and presentation → publish review candidate → consolidated release review. Loops and repairs retain their own checkpoints. Source-authority decisions return through affected upstream stages and invalidate dependent output.

| Area | Primary implementation locations |
| --- | --- |
| Review policy, issue aggregation, decisions | `review.py`, `contracts.py`, `workflow.py`, `planning.py`, `generation.py`, phase-specific contracts, `cli.py` |
| Comparison reduction and workload projection | `reconciliation.py`, `workload.py`, `batching.py`, `validation.py` |
| Bounded requests, reuse, rate control, reservations | `model.py`, `budget.py`, `config.py`, `storage.py`, `signatures.py` |
| Reader-oriented structure and larger writing units | `planning.py`, `planning_layout.py`, `planning_helpers.py`, `planning_contracts.py`, planning prompts |
| Gentle editing, evidence maps, targeted audits | `generation.py`, `generation_editorial.py`, `generation_contracts.py`, `generation_validation.py`, generation prompts |
| Source labels, navigation, tables, presentation | `generation_export.py`, `planning_export.py`, `generation_assets.py`, `data/template.md` |
| Measurements and regression evidence | Existing `scripts/benchmark.py`, `scripts/scale_check.py`, `scripts/phase2_scale.py`, phase result scripts, `evaluation/`, and `tests/` |

Prefer small shared modules for issue policy and scheduling only when responsibilities warrant them. Avoid a framework rewrite, a second mutable run-state store, or separate pause machinery.

## 7. Delivery sequence

| Milestone | Deliverables | Exit evidence |
| --- | --- | --- |
| M0 — Baseline and fixtures | Frozen original outputs; reproducible cold/warm measurements; regression cases from existing source-review failures; measured current allowance. | Phase cost/time/call breakdown and review-effort baseline, with incomplete runs labeled. |
| M1 — Consolidated review | Versioned issue policy, dependency blocking, grouped CLI decisions, bounded automatic repairs. | Clean fixture reaches final review without intermediate prompts; authority conflicts remain unresolved until valid decisions; restart preserves the queue. |
| M2 — Safe work reduction | Pair coverage deduplication, exact representative reuse, compatible task packing, validated caches, token-count reuse. | Required comparison work is accounted for; coverage and semantic regressions pass; cold and warm savings reported separately. |
| M3 — Reader-oriented planning and output | New plan revisions with coherent sections; concise citation labels; bounded gentle editing; useful tables, callouts, and diagrams. | Side-by-side rendered samples show clearer structure and retain every annotated qualification; prior factual failures are caught. |
| M4 — Bounded concurrent execution | Small prefetch window, atomic response persistence, ordered acceptance, backoff, shared-ledger tests. | Restart and concurrency tests pass; serial/concurrent runs accept equivalent required work; no lost reservation or accepted duplicate. |
| M5 — Scale and release validation | Resource fixes from profiling; evaluation-gated candidate policy if justified; large local orchestration and affordable live comparison; migration documentation. | Acceptance matrix and remaining limitations published, including any unvalidated large live workload. |

Deliver M1–M3 before depending on concurrency for user-visible improvement. Candidate-policy pruning and cross-revision reuse must not delay shipping validated simpler reductions. Each milestone should leave a usable pipeline, with independently reversible configuration where feasible.

## 8. Acceptance criteria and evaluation budget

These are implementation targets, not measured promises. Compare the same corpus, scope, template requirements, model, and hardware. Register the baseline and evaluation protocol before optimizing.

| Dimension | Target and measurement |
| --- | --- |
| End-to-end speed | At least 2× lower active elapsed time on the medium benchmark, and at least 40% fewer paid generation requests on the small reference case. Measure human waiting separately. Confirm on affordable paired runs; otherwise mark the live target unvalidated. |
| Reconciliation work | At least 70% fewer model comparison tasks on the existing dense 500k fixture, without missing any required annotated or exhaustively checked relationship. Report both tasks and checked relationships so task packing cannot disguise lost work. |
| Human effort | Zero intermediate prompts on a clean run, one final release session, and at least 80% fewer operator actions on the repeatable repairable-issue fixture. Track sessions, questions, and review minutes separately; real authority conflicts remain an explicit exception. |
| Information preservation | Every source block has a valid disposition and every included obligation has a canonical treatment. Preserve 100% of annotated facts, conditions, exceptions, modality, and scope; zero unsupported additions or incorrect entity merges on the labeled set. Sample acceptance is not a corpus-wide semantic guarantee. |
| Editorial quality | At least 4/5 for coherence, findability, plain language, repetition control, and visual organization in the final human rubric; no dimension below baseline. Answer at least 90% of predefined reader questions correctly from the documentation, preserving all critical-answer qualifications. |
| Presentation and provenance | All local links and evidence mappings resolve; no placeholders or internal workflow jargon in reader prose; representative tables and diagrams render correctly; each substantive unit remains locally traceable. |
| Resume and reuse | Fault injection after request persistence and after each acceptance boundary resumes without losing completed validated work. Changed evidence invalidates affected checks/decisions; unchanged accepted work is reused. Unknown provider completion remains conservatively charged. |
| Local scale | Complete 100k, 500k, then 2m source-token deterministic orchestration within the existing 1.5 GB peak-memory and 10 GB artifact acceptance bounds. Report queue growth and limits; no silent task-tail discard. This does not certify large-corpus live semantics or throughput. |
| Development spending | Charged plus reserved spending stays within the same cumulative PLN 200 ledger. Never reset the ledger or increase the ceiling to finish evaluation. |

Use existing test suites as the base. Add focused behavioral tests for issue aggregation, authority boundaries, pair/context coverage, concurrent reservation races, crash recovery, dirty-dependency invalidation, citation remapping, semantic-boundary splitting, and the observed editorial errors. Avoid tests that only mirror implementation details.

Run deterministic and local performance checks before paid experiments. Verify current official model pricing and currency conversion before live calls. Reserve funds for the whole planned paired experiment, including conservative retry/repair headroom, while still reserving each request through the shared ledger. Prefer one small and one medium paired live comparison over repeated unbounded smoke runs. If the remaining allowance is insufficient, complete local validation and explicitly leave live targets open; do not switch models or claim simulated results as live evidence.

## 9. Compatibility, rollout, and completion

Version the review policy, comparison policy, editorial contract, citation scheme, and affected schemas. Preserve old artifacts and the implementation signatures required to read or resume them. New behavior starts in a new run or an explicit derived revision; never reinterpret an old checkpoint silently.

Keep old plan and generation imports available. A legacy plan can use improved citation rendering and gentle editing where compatible, but a structural improvement requires a new derived plan with revalidated allocation, anchors, diagrams, and navigation. Existing source-authority decisions may transfer only when their exact evidence and decision scope remain valid; final release approval never transfers to changed prose automatically.

Initially enable consolidated review and new presentation on selected fixtures, with concurrency at one. Promote them after M1–M3 checks, then enable the measured bounded request window. Retain strict review and serial execution as troubleshooting options. Disable a failing optimization without rolling back valid content or hiding its audit history.

Update the README and placeholder configuration examples with the new default experience, review commands, status meanings, tuning options, and resume behavior. Publish an implementation report with before/after outputs, measured time/cost/review changes, source-fidelity results, and remaining limitations.

The increment is complete when users receive a substantially faster, resumable process and a clearly improved reading experience, with normal human effort concentrated in one final review. Passing link counts, shortening Markdown, or reducing prompts alone is insufficient.
