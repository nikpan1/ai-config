# doc-gen

`docgen` builds source-backed Markdown documentation from a selected Markdown corpus and template. The active LangGraph package is in `src/docgen_graph/`. Each processing node has a persistent SQLite checkpoint and a numbered, readable artifact folder under its run.

## Setup

```powershell
uv sync --locked
if (-not (Test-Path -LiteralPath .env)) { Copy-Item .env.example .env }
```

Keep an existing `.env` if you already have one. Set `GEMINI_API_KEY` there. All model requests use `gemini-3.8-flash`; a different `GEMINI_MODEL` is rejected. The cumulative development budget ledger stays at `.docgen/budget.sqlite`, with pricing at `.docgen/pricing.json`. The active pipeline defaults to `.docgen/graph/`, separate from historical root checkpoints. An existing `.env` can be selected with `docgen --env-file path/to/file ...`.

Before live model calls, inspect `uv run docgen budget`. Paid development evaluations share the authorized PLN 200 ceiling, including retries. The application requires current pricing and currency conversion before reserving a request. Offline tests and model doubles make no Gemini requests.

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

The quick investment fixture and its citation cases are in `data/test_data_2_quick/` and `data/test_data_2_reference/`. The full corpus is in `data/test_data_2/`. Java and Angular files currently use generic text analysis, and ticket filtering is not implemented. The HTML mirrors verify locators only. Passing offline tests does not establish semantic completeness or browser highlighting against live Confluence.
