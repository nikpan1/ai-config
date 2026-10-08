# doc-gen

A local, resumable pipeline that converts legacy Markdown into source-backed documentation. Phase 1 builds verified knowledge, phase 2 prepares a documentation plan, and phase 3 writes and checks Markdown pages for human review. A graphical interface is outside the current implementation.

The [phase 2 development plan](.ai/development-plan-phase-2.md) defines the planning contracts and acceptance criteria. See the [phase 2 implementation report](.ai/implementation-report-phase-2.md) for measured results and remaining capacity limitations. Two-million-token end-to-end capacity is not validated.

## Step by step: from sources to documentation

Run these commands in PowerShell from the repository root. Use a new thread ID for each new phase run. If a phase stops for review, resolve it using step 6 before continuing.

1. **Prepare the project and inputs.** Complete [Setup](#setup), including the API key and current pricing. Put source Markdown files in a dedicated directory and choose a template. The commands below use `data/legacy-insurance` and `data/template.md`; replace them with your own paths.

2. **Build the knowledge bundle (phase 1).**

   ```powershell
   uv run docgen run data/legacy-insurance --thread-id knowledge-001
   $knowledge = uv run docgen status --thread-id knowledge-001 | ConvertFrom-Json
   ```

   Continue only when `$knowledge.values.status` is `complete`. The next phase uses `$knowledge.values.bundle_ref`.

3. **Create the documentation plan (phase 2).**

   ```powershell
   uv run docgen plan-documentation --knowledge $knowledge.values.bundle_ref --template data/template.md --thread-id plan-001
   $plan = uv run docgen status --thread-id plan-001 | ConvertFrom-Json
   ```

   Continue only when `$plan.values.status` is `ready_for_generation`. Review `documentation-plan.md` in `$plan.values.export_path`. To set audience, scope or delivery mode, add `--brief brief.json` as described in [Documentation planning](#documentation-planning).

4. **Generate the documentation (phase 3).**

   ```powershell
   uv run docgen generate-documentation --plan $plan.values.plan_ref --thread-id documentation-001
   $generation = uv run docgen status --thread-id documentation-001 | ConvertFrom-Json
   ```

   If you already have a completed plan, start here and replace `$plan.values.plan_ref` with its immutable reference or `manifest.json` path.

5. **Read the result.** When publication succeeds, locate the main document:

   ```powershell
   Join-Path $generation.values.export_path "index.md"
   ```

   Read `sources/index.md` for source evidence. `$generation.values.manifest_path` identifies the separate reports and metadata. `ready_for_review` means the files are available for inspection; only `complete` means the release has been approved. Check the current `status` for later blocking findings.

6. **Handle pauses and approve the release.** Replace `THREAD_ID` with the ID of the paused phase:

   ```powershell
   uv run docgen status --thread-id THREAD_ID
   uv run docgen resume --thread-id THREAD_ID
   ```

   For a technical interruption, fix the reported cause and resume. For a review interrupt, inspect the issues, prepare `decisions.json` with the exact issue IDs and revisions, then submit it:

   ```powershell
   uv run docgen resume --thread-id THREAD_ID --decisions decisions.json
   ```

   Use the decision format for the relevant phase: [knowledge review](#review), [planning review](#documentation-planning), or [generation review and release approval](#phase-3-generate-markdown-documentation). Approve the final release with `approve_release` only after checking the text and resolving blocking findings. After a resume, rerun that phase's `status` assignment above to refresh its references.

Keep the same `.docgen` workspace between phases. Completed earlier phases can be reused; source, template or implementation changes require an appropriate new run instead of overwriting existing results.

## Setup

Python 3.12 or later and `uv` are required. The lockfile records the tested dependency versions.

```powershell
uv sync --python 3.13
Copy-Item .env.example .env
```

If `.env` already exists, keep it. Set `GEMINI_API_KEY` and `GEMINI_MODEL=gemini-3.8-flash`. Another model is rejected. API keys never appear in prompts, artifacts, error messages, or logs. `.env`, local checkpoints, snapshots, caches, and the development spending ledger are ignored by Git.

Before live requests, verify the current standard text prices on [Google's official pricing page](https://ai.google.dev/gemini-api/docs/pricing). Record those prices and refresh the USD/PLN rate from NBP. For example, the prices verified on 2026-10-08 were USD 0.75 input and USD 3.75 output per million tokens, including thinking output:

```powershell
uv run docgen record-pricing --input-usd 0.75 --output-usd 3.75 --valid-until 2026-10-15
uv run docgen budget
```

Pricing expires after at most seven days; the exchange observation must also be at most seven days old. Recheck prices when refreshing. No model request is sent without valid pricing and a successful cost reservation. The cumulative development ceiling is 200 PLN, including retries and repairs. Each request reserves an input byte bound, the model's full 65,536 output-token ceiling, and at least 25% billing headroom (30% by default). Recorded usage releases the unused reservation; failures with unknown usage retain the full amount. Interrupted reservations are retained across restarts. These are conservative estimates, not an invoice.

`DOCGEN_BUDGET_LEDGER` defaults to `.docgen/budget.sqlite` independently of the artifact workspace. Keep the same ledger for every development experiment. Moving or deleting it would lose cumulative accounting; do not reset it to obtain another allowance.

## Run and inspect

```powershell
uv run docgen run data/legacy-insurance --thread-id legacy-001
uv run docgen status --thread-id legacy-001
uv run docgen history --thread-id legacy-001
uv run docgen resume --thread-id legacy-001
```

Use a unique thread ID for each new input/configuration revision. `run` never silently overwrites an existing run. `resume` restores its SQLite checkpoint and immutable source snapshot. Changed code, prompts, schema, model, or generation settings require a new thread revision; old approvals are not reused. Normal source edits take effect through a new run. The supplied template is intentionally outside `data/legacy-insurance` and is not an extraction filter.

The named LangGraph nodes run sequentially:

```text
snapshot_sources → plan_batches → extract_batch → verify_batch
                                      ↑              │
                                      └── repair ────┘
                       next batch ← verified
reconcile_entities → reconcile_claims → finalize_knowledge
          any unresolved content issue → review_issues → affected stage
```

Each successful node checkpoints before the next starts. One process holds the worker lock for a run. Immutable artifacts are atomically saved before their references enter graph state. Extraction repairs are limited to two attempts. Truncated outputs are never accepted: batches are split, with source locations, headings, table headers, context bounds, and ownership preserved. Reconciliation comparisons are also partitioned, including cross-partition comparisons. Technical failures retain a resumable checkpoint and do not masquerade as content issues.

`--stop-after snapshot_sources`, `plan_batches`, `extract_batch`, or `verify_batch` creates a diagnostic checkpoint; `resume` continues it. This is useful for restart tests. Human feedback always uses LangGraph `interrupt()` and `Command(resume=...)`.

## Documentation planning

Use a completed knowledge export in its original artifact workspace. A copied manifest without its immutable objects and source snapshots is insufficient. Version 1 knowledge bundles remain supported: a missing explicit source selection is derived from the original snapshot and labeled `snapshot_derived`.

```powershell
uv run docgen plan-documentation --knowledge .docgen/runs/KNOWLEDGE_THREAD/knowledge/REVISION/manifest.json --template data/template.md --thread-id plan-001
uv run docgen status --thread-id plan-001
uv run docgen history --thread-id plan-001
uv run docgen resume --thread-id plan-001
```

The knowledge argument also accepts an immutable `objects/knowledge-HASH.json` reference in `DOCGEN_WORKSPACE`. Draft bundles, unresolved issues, modified snapshots, invalid evidence, unsupported schemas and cross-workspace imports are rejected. Phase 2 does not extract missing knowledge or choose between conflicting source authorities.

An optional `--brief brief.json` controls editorial choices. Runtime limits and API credentials stay in `.env`.

```json
{
  "schema_version": "1",
  "audience": "Operations and integration engineers",
  "purpose": "Explain the selected functionality and its operational boundaries",
  "product_name": null,
  "last_reviewed": null,
  "language": "English",
  "unit_policy": "auto",
  "delivery_mode": "auto",
  "expected_areas": [],
  "hard_scope": [],
  "include_record_ids": [],
  "exclude_record_ids": [],
  "named_boundaries": [],
  "preferences": []
}
```

`unit_policy` accepts `auto`, `single`, or `explicit`. The explicit policy requires named boundaries with `name`, `purpose`, and `scope`. Expected areas are nonbinding hints; hard scope and explicit record exclusions produce visible exclusion accounting. `delivery_mode` accepts `auto`, `single_page`, or `multi_page` independently of the number of units. With `single_page`, each unit still gets its own full template root; multiple units also get a collection guide. Missing metadata remains unknown.

`--previous-plan PATH_TO_MANIFEST` supplies a completed planning revision for identity and path reuse. It provides editorial history, never new evidence or inherited approval. Matching ownership preserves established IDs where possible; changes remain visible in navigation mappings. A new knowledge, template, brief, code, prompt, model or relevant configuration revision uses a new thread.

The sequential graph is:

```text
snapshot_planning_inputs → compile_template → inventory_content
→ discover_documentation_units → verify_documentation_units
→ plan_logical_structure → allocate_content → design_page_tree
→ write_section_briefs → plan_navigation → plan_writing_jobs
→ validate_plan → audit_plan → finalize_plan
```

Repeated work checkpoints after each bounded item. Discovery includes all inventory groups, hierarchical candidate synthesis, global reassignment against the final unit registry, and an independent boundary audit. Conditions and exceptions remain attached to the canonical treatment and every local mention. Root summaries are scheduled after detail jobs. A root page, a model work item and a storage shard are separate concepts.

Delivery mode is omitted from template interpretation, unit discovery, boundary verification, and logical-topic model inputs. It enters page design separately, allowing unchanged architectural work to use durable cached responses when comparing delivery layouts.

Issue-free runs finish automatically. Content issues use `review_plan` and LangGraph interrupts, with at most two automatic repairs. Decisions identify the exact `issue_id` and `revision`, plus `action`, `rationale`, and `reviewer`. `correct` supplies a `correction_ref` to an immutable replacement model response for the pending work item; the response is validated again. After a whole-stage audit, the reference can instead identify a `planning_component_patch` with `base_revision`, `component`, and `replacement_ref`. Supported components are `logical-sections`, `pages`, and `section-briefs`; replacement tables retain existing identities. Dependent artifacts are invalidated, rebuilt and audited again. `retain_unknown` and `inapplicable` also require an evidence-backed correction. `defer` and `request_upstream` preserve the interrupt. Decisions cannot waive coverage, references, or unsupported statements. New structures, hard scope changes and upstream knowledge corrections require new immutable revisions. Technical and budget failures retain resumable checkpoints.

The final directory is `.docgen/runs/THREAD/documentation-plan/REVISION/`. It contains the concise `documentation-plan.md`, a complete `page-index.md`, individual `page-briefs/` with parent, child and canonical links, a template snapshot and contract, unit registry and boundary report, complete obligations and allocation tables, section briefs, evidence index, navigation, writing jobs, audit results and a validation report. `manifest.json` lists component references and export hashes. The directory is published atomically and receives `ready_for_generation` only after structural and independent semantic checks pass. The resulting files are a writing specification, not generated system documentation.

## Source selection and workload inspection

The original file/directory invocation remains available. To snapshot exactly selected files, pass a manifest relative to the source root:

```json
{"schema_version": "1", "files": ["area-a.md", "subsystem/area-b.md"]}
```

```powershell
uv run docgen run data/legacy-insurance --selection selected-sources.json --thread-id selected-001
uv run docgen workload --source data/legacy-insurance --selection selected-sources.json
uv run docgen workload --knowledge objects/knowledge-HASH.json
```

Unselected linked files are reported as missing context, never silently ingested. Selection hashes travel with the knowledge bundle. The workload report performs no paid model calls; it may cache immutable snapshots and indexes. It reports heuristic source tokens, batches, available record counts, comparison tasks, largest candidate groups, remaining allowance and disk usage. Before extraction, comparison counts are unknown. Its conservative reservation bound is not a prediction of a complete pipeline's cost.

`DOCGEN_PLANNING_TOKENS` bounds owned planning material, `DOCGEN_WRITING_TOKENS` bounds resolved future writing contexts, and `DOCGEN_PAGE_SPLIT_WORDS` is an editorial review heuristic. `DOCGEN_WORKLOAD_TASKS` stops oversized queues without discarding their tail. Whole-request preflight also includes prompts, schemas and output headroom. The broad phase 1 candidate policy retains its dense worst case; some global joins and manifests still use memory proportional to their inventory.

Workflow signatures explicitly list relevant modules, Pydantic schema modules and versioned prompts in `src/docgen/signatures.py`. Old runs can still be inspected with `status` and `history`; incompatible resumes require the matching implementation or a new thread. A finalized old knowledge bundle can be imported into a new planning run without resuming phase 1. A crash after a provider request but before durable response storage can leave completion uncertain; its conservative charge is retained. Exactly-once remote execution is not promised.

## Review

An unresolved issue stops its producing stage, writes a Markdown report with exact excerpts and source locations, and returns exit code 2. The report path, issue IDs, and artifact revision appear in `status`. There is no automatic choice of conflicting authority.

Save a decision file and submit it:

```json
{
  "decisions": [
    {
      "issue_id": "issue-ID-from-status",
      "revision": "artifact-reference-from-status",
      "action": "select_authority",
      "claim_ids": ["batch-ID:c1"],
      "reviewer": "Operator name",
      "rationale": "Explain the source authority and why this version applies."
    }
  ]
}
```

```powershell
uv run docgen resume --thread-id legacy-001 --decisions decisions.json
```

Supported actions:

| Action | Effect |
| --- | --- |
| `defer` | Leaves the stage interrupted. |
| `correct` | Supplies a complete `replacement` extraction; evidence and coverage are checked, then the verification node runs again. Earlier decisions for that draft become superseded history. |
| `select_authority` | Selects `claim_ids` within a conflict; other conflicting claims remain preserved but ineligible in the bundle. |
| `keep_distinct` | Preserves ambiguous entities as separate entries. |
| `merge_entities` | Explicitly merges `entity_ids` from the reviewed issue into a register entry, retaining every member, definition, alias, and evidence passage. Incompatible type/scope/version prevents merging. |
| `acknowledge_unknown` | Records that a source question or missing dependency remains explicitly unknown. Cannot approve invented facts or resolve conflicting authority. |
| `explain_asset` | Adds an attributed `explanation` linked to the inventoried image or asset. This is reviewer evidence, not original source evidence. No images are sent to the model. |
| `exclude` | Justifies excluding unreadable input or unsupported assets. Does not discard extracted factual content. |

Ordinary approval cannot turn unsupported claims into facts. Decisions must match the exact issue and artifact revision. Partial decisions are saved, and remaining issues interrupt again. Final structural integrity failures cannot be waived. Source corrections after reconciliation require a new source revision; direct extraction corrections are supported at extraction/verification review.

If a decision file is rejected, correct it and submit the same `resume --decisions` command again. The CLI renews the failed review interrupt before accepting the replacement; the earlier checkpoint remains in history. Duplicate findings produce one review issue. Planning import rejects entity mappings that contradict inherited keep-distinct decisions.

## Artifacts and invariants

The default `.docgen/` workspace contains:

- `snapshots/`: exact, content-addressed input bytes, including original tables, examples, and procedures.
- `objects/`: immutable manifests, drafts, verification outputs, issue histories, decisions, and bundles.
- `checkpoints.sqlite`: persistent LangGraph state and history, keyed by thread ID.
- `budget.sqlite`: cumulative reservations and charges across all runs.
- `cache/`: validated model responses keyed by input, context, prompt, schema, model, code, and configuration.
- `runs/<thread-id>/events.jsonl`: stage references, timing, attempts, token usage, and sanitized failures.
- `runs/<thread-id>/review-*.md`: source-linked review reports.
- `runs/<thread-id>/knowledge/<revision>/`: frozen manifest, claims, entity entries and register, relationships, coverage, decisions, original blocks, and review report.

Blocks carry snapshot hash, relative path, heading ancestry, line and character ranges, exact content, and table coordinates. Every block has exactly one extraction owner. Reused context retains its original IDs. Coverage records distinguish represented, duplicate, excluded, and unresolved blocks. Exact evidence excerpts, ID integrity, duplicate chains, and coverage are validated in code; a separate Gemini pass checks semantic omissions and distortions. Neither block accounting nor model verification proves complete preservation of an arbitrary corpus.

Reconciliation uses bounded groups by entity names, explicit aliases, shared name words, claim entities, rule identifiers, and scope. All pairs within each candidate group are assigned to comparisons, including partition boundaries. Candidate policy and unperformed comparisons are recorded. Unrelated groups are not globally compared, so semantic relationships with no shared grouping signal remain a limitation. Original records are never discarded to fit a prompt. The register only merges entities after an explicit reviewer decision.

Candidate tasks are enumerated into immutable indexed partitions, and comparison results append linked parts instead of rewriting a growing result dictionary. Truncation splits preserve the queued tail. Each request revision binds the actual compared records, allowing an unchanged request to reuse its validated cache after another part of the corpus changes. The candidate policy remains version 1; exhaustive fixture checks verify that partitioned storage preserves the same comparisons.

## Validation and evaluation

```powershell
uv run pytest -q
uv run ruff check src tests scripts
uv run python scripts/scale_check.py
uv run python scripts/live_smoke.py
uv run python scripts/benchmark.py --sizes 8000 16000 32000 --source-tokens 32000 --score
```

The smoke test uses real Gemini calls and a small, coherent synthetic archive specification. The benchmark uses original corpus passages and the same budget ledger, reports before-verification extraction and independent verifier findings, and does not finalize unresolved knowledge. `--max-batches 1` provides a bounded exploratory run; its report explicitly marks an incomplete queue. `--source-tokens 0` selects just the annotated passages. Size values are source-token estimates, not total serialized prompt tokens; metadata, schemas, context, and outputs have separate budgets. API token preflight can split a nominally larger batch before generation.

The [reference set](evaluation/reference-review.md) contains 40 annotated passages from all three supplied files, with facts, qualifications, source hashes/lines, and entity distinctions. Thirty are development passages; ten are held out. `--include-held-out` includes the held-out labels in scoring; leave this disabled during tuning. The reference was prepared autonomously and has **not** been reviewed by the user. Automated Gemini scoring is exploratory and must not be reported as acceptance on a user-approved set. The scale check exercises ingestion/batching beyond one million words without paid model calls; it does not establish million-token semantic quality.

See [implementation and validation results](.ai/implementation-report.md) for the measured results and remaining acceptance work. Exit codes: 0 completed or diagnostically stopped, 1 invalid input/configuration, 2 content review, 3 resumable technical or budget failure.

Phase 2 results, live diagnostics and separate capacity limits are recorded in the [phase 2 implementation report](.ai/implementation-report-phase-2.md). Reproduce the structural measurements with `uv run python scripts/phase2_scale.py --tokens 100000 --full-stub`; 500000 and 2000000 exercise larger workloads and explicitly report an incomplete result when the task allowance is reached. These stub measurements do not establish semantic quality.

## Phase 3: generate Markdown documentation

Generate from a completed phase 2 manifest or immutable plan reference in the same workspace:

```powershell
uv run docgen generate-documentation --plan .docgen/runs/PLAN_THREAD/documentation-plan/REVISION/manifest.json --thread-id documentation-v1
uv run docgen status --thread-id documentation-v1
uv run docgen resume --thread-id documentation-v1
```

The workflow validates frozen knowledge, template, plan components and writing contexts. It writes jobs in dependency order, checks exact citations and table cells, and independently reviews each fragment with Gemini. Each job has a persistent checkpoint and at most two automatic repair attempts. Mermaid diagrams come from the evidence-backed plan. A separate page review checks assembled prose and qualifications. Headings, links, source locations and canonical obligation coverage are checked in code.

The user approved a simplified language policy in place of the official ASD-STE100 standard: professional, plain English with consistent terminology and preserved technical meaning. The versioned `plain-technical-english-v1` contract and source-backed terminology register are retained in metadata. Mechanical sentence and paragraph findings are review hints; independent model review checks meaning and language. No formal STE compliance or certification is claimed, and an official dictionary is not required.

The reader-facing directory is `.docgen/runs/THREAD/documentation/REVISION/` and contains only `.md` files. Start at `index.md`; use `sources/index.md` for exact source excerpts, original snapshot links and disposition accounting. Requested attachments have an index and links to immutable source snapshots. The pipeline does not copy images or create binary deliverables. Source links require the original workspace.

Workflow records, input and language revisions, evidence mappings, checks and release status are separate under `.docgen/runs/THREAD/generation-metadata/REVISION/`. Artifact references resolve in the same workspace. Directories are immutable and the final manifest is written last. A run publishes `ready_for_review` before its human release interrupt; only a revision-bound human approval changes the status to `complete`, in a new output revision.

Use `--brief generation-brief.json` for optional `quote_policy` (`exact_labeled` or `none`), `terminology`, and `assets`. This brief cannot change scope or page structure. Asset requests contain `path`, `purpose` and `disposition` (`link`, `image` or `exclude`). Image references also require a human `explanation` and `reviewer`. Absent or unexplained assets interrupt before writing. Technical terms contain `term`, `definition`, `permitted_form`, `part_of_speech`, `scope`, `authority` and optional exact `evidence`.

Inspect the pending issues with `status`. Resume with a JSON object containing `decisions`, using each issue's exact ID and revision:

```json
{
  "decisions": [{
    "issue_id": "COPY_FROM_STATUS",
    "revision": "COPY_FROM_STATUS",
    "action": "approve_release",
    "reviewer": "Your name",
    "rationale": "Reviewed the complete Markdown set against its evidence",
    "reviewed_scope": ["content_accuracy", "reader_usefulness", "language", "markdown"]
  }]
}
```

```powershell
uv run docgen resume --thread-id documentation-v1 --decisions decisions.json
```

Content corrections use `action=correct` and an immutable `correction_ref` containing a complete `WritingFragment`. Corrections re-enter verification and invalidate dependent summaries and output checks. `approve_term` and `asset_decision` require immutable typed replacement records; `request_upstream` records the need for a new plan, and `defer` retains the interrupt. Decisions cannot waive unsupported facts or missing mandatory coverage. Technical failures preserve the checkpoint without entering content review.

Generation caches are disabled by default. `--cache-mode validated` permits reuse only of fragments with successful evidence and semantic checks, keyed by frozen inputs, dependencies, language contract and implementation. The acceptance example uses no cached model responses. `--stop-after` supports each named generation node for restart inspection.

For a live example with a frozen implementation that remains resumable during development:

```powershell
uv run python scripts/phase3_live.py --thread-id phase3-example --plan objects/documentation-plan-HASH.json
uv run python scripts/phase3_live.py --thread-id phase3-example --resume
```

This helper records the source-code hashes and location in the run's `implementation.json`. Use the same helper with `--resume --decisions decisions.json` to review a frozen example after local code changes. It uses the shared model client, pricing, budget ledger, lock and SQLite checkpointer. It does not claim that fixture or model checks substitute for human acceptance.
