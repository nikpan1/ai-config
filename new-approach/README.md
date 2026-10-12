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

For a legacy-document-only run, omit `--code`:

```powershell
uv run --project new-approach docgen-graph run --docs data/test_data_1 --template data/template.md --thread-id furniture-docs-v1
```

The resulting graph contains documentation evidence only. It does not make claims about a software implementation.

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

## Documentation quality

The plan records canonical content units, scoped variants, overview links, template requirements,
visual choices, and explicit inapplicability decisions. Approving its exact hash approves these
choices together. A changed owner, image, diagram, or template exception requires another plan
revision. Model-facing schemas are simplified for Gemini; complete local Pydantic and source
validation still apply.

Every obligation has an exact final passage. Several obligations can share a paragraph or table
row when its mappings collectively support every fact and citation. Editing must return updated
passages; missing, ambiguous, unsupported, or stale mappings block export. The audit includes
character offsets into the exported reader page, content ownership, template decisions, visual
provenance, and repetition findings. Repetition repairs revisit affected sections only.
Editorial source audits include changed passages, nearby context and newly added claims. Each
editorial response may change at most 12 obligation mappings; unchanged passages keep their
verified mappings. Content units split at scoped fact boundaries when their complete evidence
would exceed the writing context limit.

Markdown sources can reference local PNG, JPG/JPEG, or inert SVG files inside the selected document
root. Both referenced and unreferenced assets are inventoried and frozen by content hash. Configure
`DOCGEN_ASSET_MAX_BYTES` and `DOCGEN_ASSET_MAX_PIXELS` in `.env`. Broken or escaping paths, symlinks,
format mismatches, malformed images, and active or externally linked SVG content remain visible as
rejected assets. Including an image requires meaningful source-provided alternative text. The
pipeline does not interpret image pixels. Identical bytes have one exported file and at most one
reader placement; unplaced assets remain in `source-assets.md` and the audit inventory.

Approved process, state, and handoff diagrams use a bounded Mermaid subset: at most 16 nodes and
24 transitions, one primary diagram per section. Every node, transition, condition, and description
is checked against original text. Missing relationship evidence is a gap for plan review, never a
reason to invent a path. Generation and checking use existing planning and section calls.

Copy the entire candidate directory to move an export. Images use relative `documentation/assets/`
links. `candidate-manifest.json` covers all reader, evidence, audit, and image files; release checks
reject modified, missing, or additional files. Preserve the manifest alongside the bundle.

## Evaluation

Run offline checks with `uv run --project new-approach pytest new-approach/tests`. The annotated
document-only fixture and reader rubric are in `evaluation/quality/`. For a development evaluation:

```powershell
uv run --project new-approach python new-approach/evaluation/quality_run.py --thread-id quality-example --docs new-approach/evaluation/quality/docs --template new-approach/evaluation/quality/template.md --approve-plan --output new-approach/evaluation/quality/example.json
```

`--approve-plan` records an explicitly attributed automated development decision through the normal
LangGraph interrupt. It does not establish independent human acceptance and stops at final release
review. Without that flag, the evaluator stops for normal plan review too. `--status` inspects a run
without making calls. Metrics include paid calls, token usage, response and active node time,
retries, repairs, ledger charges, reader length excluding citation URLs, and portable-copy checks.
Report human reader scores and unmeasured timing targets separately from structural test passes.

Use `evaluation/quality_compare.py --baseline <candidate-directory> --revised <candidate-directory>
--output <comparison.json>` to verify both manifests, compare reading length and original source
links, and check revised passage offsets. Optional `--baseline-metrics` and `--revised-metrics`
add call, charge and timing comparisons from evaluation JSON files. Source fidelity and human
reading scores still require the annotated review.

Use `evaluation/quality_accounting.py --run-prefix <prefix> --output <accounting.json>` for
read-only cost and token accounting across development revisions. It includes failed and
interrupted requests, separates conservative uncertain charges from settled charges, and reports
missing token usage explicitly. Prefixes can be repeated to include several experiment families.

The code adapter uses Python AST for `.py` files and reports structural limitations for other selected text formats. Source text and template examples are treated as data. Source coverage, assertions, citations, graph paths, and final mappings are inspectable in the run artifacts. Production commands retain both plan and final release review.
