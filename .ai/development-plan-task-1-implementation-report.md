# Task 1 pipeline implementation report

Date: 2026-10-12

## Delivered

| Milestone | Result |
| --- | --- |
| A0 baseline | The existing active `new-approach` package had persistent LangGraph checkpoints, Gemini budget accounting, source provenance, candidate manifests, and manual plan/release gates. Its old citation selector was broad and its stages lacked numbered user-facing artifacts. The baseline offline suite passed 79 tests after using a workspace-local pytest temporary directory. |
| A1 evidence and links | Citation selection now projects visible Markdown text, excludes image tokens and hidden HTML text, searches the destination page for unique evidence-bearing phrases, supports prefix/suffix disambiguation, and scopes repeated table facts to the declared source row. Every citation occurrence may select its own URL and records exact source character offsets, source snapshot hash, claim, support quote, verification status, and local fallback reason. Original URL query and anchor components remain present. An optional explicitly configured HTML page map is frozen at input snapshot. |
| A2 step outputs | The 25 existing nodes have stable `step1`–`step25` folders; manual review and automatic issue resolution use `step26` and `step27`. Executed nodes write JSON, a readable Markdown summary, a revision manifest, and linked object projections. Repeated items use immutable revisions; replay checks persisted hashes. Skipped nodes state why. Candidate bundles are mirrored under `step22/candidates/<hash>`. |
| A3 modes | One CLI supports `manual` and `autopilot`. Manual execution interrupts at each produced artifact and binds approval, correction, or rejection to the exact stage/item/hash. The final receipt has its own gate. Autopilot records attributed policy decisions for plan/release and bounded document-coverage resolution or explicit exclusion. It can finish `complete`, `complete_with_exclusions`, or `incomplete`. |
| A4 consolidation | `src/docgen_graph`, tests, evaluation files, `pyproject.toml`, lockfile, and `.env.example` moved to the repository root. The console command is `docgen`. Obsolete `old-approach` executable code and legacy Python utilities were retired; historical evaluation results and local runtime state were preserved. Root `.env` and `.docgen/budget.sqlite` were not overwritten. |
| A5 integration | The version-1 investment fixture is consumed by the offline citation evaluator and tests. The final reference package has 72 citation cases and 65 expected facts. The structural citation evaluation reports 72/72 expected behaviors and zero forbidden-fragment matches. A model-double pipeline reached release in autopilot mode, and a manual CLI run stopped at a checkpointed first-stage review. |

## Commands and measured results

| Command or check | Result |
| --- | --- |
| `uv sync --locked --no-dev` and `uv sync --locked --group dev` | Succeeded in a clean root virtual environment. |
| `uv run --locked --no-dev docgen --help` | Root command loaded successfully. |
| `python -m evaluation.citation_cases` | 72 cases; 72 expected behaviors; zero forbidden fragments. |
| `python -m pytest tests -q --basetemp=.docgen/pytest-task1-complete -o cache_dir=.docgen/pytest-cache` | 89 passed in 134.13 seconds. |
| `python -m ruff check src tests evaluation` | Passed. |
| `python -m ruff format --check src tests evaluation` | Passed. |
| `docgen migrate --from-workspace new-approach/.docgen` | Dry-run verified 8,484 files, content object hashes, and candidate manifests; zero collisions in the separate import destination. No copy was performed. |
| `docgen budget` | Authorized limit PLN 200; historical charged PLN 445.4719064244 and reserved PLN 1.62453494619; remaining PLN -247.09644137059. No live Gemini request was made for this task. |

For the 72-case fixture, the generated selector is 19 encoded bytes at the median, 91 at p95, and 102 at maximum. The old broad-selector approximation is 260, 438, and 438 bytes respectively. The comparison includes cases with a text-fragment outcome; exclusions and local-evidence fallbacks do not have a selector length. The old baseline value is a reimplementation of the prior `As a ...` or long-cell heuristic applied to the same evidence lines, not a browser measurement.

## Inspectable examples

- Manual stage artifact: `.docgen/graph/runs/task1-artifact-sample/step1/revisions/r0001/result.md`. Its JSON and manifest are alongside it. The run is intentionally paused at `review_stage`; no Gemini request occurred.
- Candidate bundle shape is tested under `step22/candidates/<candidate_hash>/`, including evidence, image assets, source index, audit, and manifest.
- Automatic exclusion example in `tests/test_modes_and_artifacts.py`: an uncovered `rules.md` line is first accounted for in a corrected extraction draft, then, after independent verification remains unresolved, receives a source range, reason, and decision reference in `exclusions.json` and `exclusions.md`. This is a model-double test, not an actual decision to omit fixture content.
- Historical artifacts remain in `new-approach/.docgen/`; `docgen migrate` can copy them to `.docgen/graph/imported-legacy/` after verification. Existing historical checkpoints are inspectable but incompatible with the new graph signature and cannot be resumed as current runs.

## Verification limits

- Browser highlighting over HTTP remains unverified. A local server was started, but the available in-app browser returned a connection timeout. The citation checks prove deterministic source and supplied-HTML text matching, not browser selection or authenticated Confluence rendering.
- The current selector supports exact text, bounded prefix/suffix context, and a `start,end` range for a unique long support quote. It does not prove global minimality with an independent exhaustive oracle. Shortest length is measured over candidates supported by this implementation.
- No live quick or full documentation run was made because the historical ledger exceeds the authorized ceiling. Structural fixture results do not establish full information coverage, reader quality, or semantic correctness of the authored expected-fact oracle; that oracle is marked as not human reviewed.
- Automatic issue resolution is implemented for document coverage repair/exclusion. Other unresolved validation issues end `incomplete`. It does not yet provide general Gemini-guided, dependency-minimal repairs for every content issue. A failed document batch can exclude the batch rather than the smallest possible unsupported proposition.
- Tests cover restart at representative manual, autopilot, receipt, and exclusion points; they do not exercise every stage interruption or a crash in the interval between artifact write and checkpoint commit.
