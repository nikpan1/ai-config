# doc-gen

A local, resumable pipeline that converts legacy Markdown into an evidence-backed knowledge bundle. The implemented scope is [the development plan](.ai/development-plan.md): ingestion, extraction, independent verification, reconciliation, review, and knowledge finalization. Document generation from `data/template.md`, publishing, and a graphical interface are later phases.

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
