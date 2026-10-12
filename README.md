# doc-gen

`docgen` builds source-backed Markdown documentation from a selected Markdown corpus and template. The active LangGraph package is in `src/docgen_graph/`. Each processing node has a persistent SQLite checkpoint and a numbered, readable artifact folder under its run.

## Setup

```powershell
uv sync --locked
if (-not (Test-Path -LiteralPath .env)) { Copy-Item .env.example .env }
```

Keep an existing `.env` if you already have one. Set `GEMINI_API_KEY` there. All model requests use `gemini-3.8-flash`; a different `GEMINI_MODEL` is rejected. The cumulative development budget ledger stays at `.docgen/budget.sqlite`, with pricing at `.docgen/pricing.json`. The active pipeline defaults to `.docgen/graph/`, separate from historical root checkpoints. An existing `.env` can be selected with `docgen --env-file path/to/file ...`.

Inspect `uv run docgen budget` for cumulative usage and charges. Accounting uses current pricing and currency conversion. `DOCGEN_BUDGET_PLN` is optional: leave it blank for uncapped accounting, or configure a positive runtime limit. Offline tests and model doubles make no provider requests.

## Run

```powershell
uv run docgen run --mode manual --docs data/test_data_2_quick --template data/template.md --thread-id risk-manual-001
uv run docgen run --mode autopilot --docs data/test_data_2_quick --template data/template.md --thread-id risk-auto-001
uv run docgen resume --thread-id risk-manual-001
uv run docgen status --thread-id risk-manual-001 --json
```

`run` defaults to `manual`; explicit modes make automation safer to audit. `manual` pauses after each executed stage artifact, then at the plan and release gates. The CLI prompts for an action, reviewer and rationale, binding decisions to the exact artifact revision. EOF or a noninteractive terminal leaves a checkpointed pending review. `resume --decisions decision.json` accepts one structured decision for automation or testing. `autopilot` uses attributed policy decisions at plan and release, bounded repairs, and explicit content exclusions when it can continue safely. If essential content cannot be verified, it ends `incomplete` with its artifacts preserved.

Runs, including repeated item revisions, are under `.docgen/graph/runs/<thread-id>/step1/` through `step27/`. `run-manifest.json` maps node names to step folders. `step22/candidates/<hash>/` is a portable candidate bundle with relative evidence and asset links. `exclusions.md` and `exclusions.json` account for omitted content. Exit codes are 0 for a completed release, 10 for pending manual review, 11 for technical or configuration blocking, 12 for rejection, and 13 for incomplete content.

Use `uv run docgen history --thread-id ID`, `uv run docgen inspect-evidence --thread-id ID --citation D1`, and `uv run docgen budget` for inspection. Resume always uses the stored mode. Changing inputs, policy or runtime implementation requires a new thread ID; incompatible checkpoints are not silently resumed.

## Source links

Each citation is checked against its frozen Markdown source and, when configured, a supplied local HTML export. Set `DOCGEN_SOURCE_PAGE_MAP` in `.env` to a JSON file mapping source IDs or original URLs to local HTML paths relative to the map file. Those HTML bytes are frozen for navigation verification only; they are never ingested as product facts. Without a map, the citation audit reports `markdown_projection_only`. If a reliable selector cannot be made, the reader links to a portable local evidence record and shows the original page separately. Production Confluence highlighting remains unverified unless a browser can open the authenticated original page.

## Repository layout

The repository root is the only application project. Run installation, CLI commands, tests, and builds here; neither an `old-approach/` nor a `new-approach/` application directory is needed.

| Path | Contents |
| --- | --- |
| `src/docgen_graph/` | Active pipeline and versioned prompts. |
| `tests/` and `evaluation/` | Tests, fixtures, and evaluation tools. |
| `pyproject.toml` and `uv.lock` | Shared package configuration and pinned dependencies. |
| `.env` and `.venv/` | Ignored local configuration and the root Python environment. |
| `data/` | Source inputs and templates. |
| `.docgen/graph/` | Active run artifacts and checkpoints. |
| `.docgen/graph/imported-legacy/` | Preserved historical output from the former nested project. |

The former `new-approach/.docgen/` contents have been copied into `.docgen/graph/imported-legacy/` and verified before removing the nested directory. The former nested `.env` is preserved at `.docgen/root-consolidation/new-approach.env`; it is an archival copy with historical relative paths, not the active configuration. Root `.env`, budget accounting, and existing checkpoints remain intact. Migration manifests are under `.docgen/root-consolidation/`.

## Importing another historical workspace

To import output from a separate historical checkout, inspect and verify its workspace before copying:

```powershell
uv run docgen migrate --from-workspace path/to/historical-workspace
uv run docgen migrate --from-workspace path/to/historical-workspace --copy
```

The first command is a dry run. Both commands verify content object hashes and candidate manifests; copy refuses different files already at the destination. Copies go to `.docgen/graph/imported-legacy/`, preserving the active checkpoint database separately. Historical checkpoints remain inspectable, but their old graph schema and runtime signature are incompatible with the root pipeline. Start a new thread from selected inputs for new execution. Neither command changes `.env` or the shared budget ledger.

The former `old-approach` executable, `docgen-graph` command, and phase-specific scripts are retired. Historical evaluation results are kept in `.ai/legacy-evaluation/`; historical utilities are non-executable records in `.ai/historical-utilities/`. Repository history retains the old source.

Historical plans and reports may retain their original command names and paths. They describe earlier runs; the root project and commands above are the current entry points.

## Development checks

```powershell
uv run pytest tests
uv run ruff check src tests evaluation
```

The quick investment fixture and its citation cases are in `data/test_data_2_quick/` and `data/test_data_2_reference/`. The full corpus is in `data/test_data_2/`. Java and Angular use a bounded text index with entry-point discovery; feature and ticket scopes require explicit path mappings. The HTML mirrors verify locators only. Passing offline tests does not establish semantic completeness or browser highlighting against live Confluence.

## Evidence authoring and code analysis

Code analysis can use `gemini`, `codex_sdk`, or `auggie_sdk` through
`DOCGEN_CODE_ANALYSIS_BACKEND` and `DOCGEN_CODE_ANALYSIS_MODEL` in `.env`.
The CLI also accepts global `--code-backend` and `--code-model` options:

```powershell
uv run docgen --code-backend gemini --code-model gemini-3.8-flash run --docs data/docs --code data/code --thread-id example
```

Use the same effective configuration when resuming a thread. Changing the model,
tool limits, source revision, prompts, or implementation invalidates runtime
compatibility and requires a new run. Documentation extraction, planning,
authoring, editing, and independent audits always use `gemini-3.8-flash`.
The SDK exception is restricted to read-only code analysis. Native Codex uses
the verified isolation boundary; Auggie reports `unsupported` where its host
cannot establish equivalent isolation. Neither backend silently falls back.
Provider execution also requires an authorized shared accounting allowance.

The authoring workflow checkpoints each model action, tool execution, result
verification, new-fact audit, and graph revision publication separately. Tools
search frozen original sources, the revision-bound knowledge graph, and code;
read exact evidence and attachments; build restricted Mermaid diagrams; and
independently check proposed content. Gemini automatic function execution is
disabled. Full serialized protocol messages, including opaque thinking
signatures, are retained for restart. Tool turns, elapsed time and result bytes
are bounded by `DOCGEN_AUTHORING_TURN_LIMIT`,
`DOCGEN_AUTHORING_TIMEOUT_SECONDS`, and `DOCGEN_AUTHORING_RESULT_LIMIT`.

Completeness is checked independently at source inventory, source-aspect
discovery, and final reader passages. Using every graph fact does not establish
complete extraction. Missing qualifiers or unresolved required attachments stop
autopilot with `incomplete`; manual mode requests LangGraph review. Failed
extraction is never automatically relabeled as harmless boilerplate. Inspect
`source-coverage.json`, `unresolved.json`, graph revisions, and stage artifacts
alongside the final candidate audit.

Place explicitly supplied local TXT/MD, text PDF, DOCX, CSV, or XLSX attachments
under the selected documentation directory. Their frozen hashes, parser
versions, native page/paragraph/table/cell coordinates, formulas, available
cached values, and extraction limitations enter the source register. Published
evidence pages retain native locators and link to deduplicated frozen files.
Scans, image-only knowledge, encrypted or corrupt documents, and unfaithfully
readable complex content remain unresolved. No OCR, image interpretation,
macro execution, or arbitrary URL fetching is performed. For required image or
unsupported attachment knowledge, supply a source-attributed transcription
identifying the original attachment and reviewer, then start a new snapshot/run;
approving an issue alone does not create missing evidence.

Template headings are parsed as Markdown, preserving fixed wording and numbers.
Generated headings inherit numbering, dynamic heading slots have stable IDs,
and renumbered local links follow their headings. Fixed numbers are never
silently shifted; conflicts are rejected. Editing retains exact fact mappings
and source quotes, audits changes to qualifiers and causal explanations, and
checks candidate repetition in prose and tables before removing it.

The implementation was initially exercised with offline fixtures. Live
SDK/Gemini compatibility and human readability acceptance remain separate
acceptance steps. Usage accounting persists across offline and live evaluations.
