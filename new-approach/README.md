# Documentation graph pipeline

This package implements an independent pipeline for source-backed Markdown documentation. Shared input files live in the repository-root `data/` directory. Checkpoints, snapshots, graph indexes, reviews, and exports live under `new-approach/.docgen/`.

## Setup

```powershell
uv sync --project new-approach --group dev
Copy-Item new-approach/.env.example new-approach/.env
```

Set `GEMINI_API_KEY` in `new-approach/.env`. Live calls require the shared budget ledger and a current pricing file. The configured model must be `gemini-3.8-flash`.

## Run

```powershell
uv run --project new-approach docgen-graph run --docs data/legacy-insurance --code path/to/source --template data/template.md --thread-id insurance-v1
uv run --project new-approach docgen-graph status --thread-id insurance-v1
```

The first run stops at `review_plan`. Read `new-approach/.docgen/runs/insurance-v1/documentation-plan.md`, then supply a decision file:

```json
{"action":"approve_plan","plan_hash":"exact hash from status","reviewer":"name","rationale":"Reviewed allocations and source previews"}
```

```powershell
uv run --project new-approach docgen-graph resume --thread-id insurance-v1 --decisions plan-decision.json
```

The candidate stops at `review_release`. Its decision uses `approve_release`, `request_changes`, or `reject_release` and the exact `candidate_hash`. Plan decisions also support `request_changes` and `reject_plan`. Blocking issues accept `retry` or `reject` with their exact issue revision. Every decision requires reviewer and rationale. `resume` without a decision resumes only technical interruptions.

When plan review reports cross-source candidates or discrepancies, an approval also needs `conflict_decisions` and `discrepancy_decisions` maps keyed by the IDs in `status`. Values are `present_both`, `code_applies`, `docs_apply`, or `not_conflict`. The chosen applicability remains reviewer input and does not replace the original evidence.

Other commands are `history`, `inspect-evidence --citation C1`, and `budget`.

The code adapter uses Python AST for `.py` files and reports structural limitations for other selected text formats. Source text and template examples are treated as data. Source coverage, assertions, citations, graph paths, and final mappings are inspectable in the run artifacts. Automated checks never bypass either human review.
