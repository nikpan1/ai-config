# Development plan for pipeline repairs and a unified CLI

Date: 2026-10-12

Status: ready for implementation by Agent A. This plan changes no runtime behavior. The repository inspection used commit `6ec439b756ccd9dfa61333d17505412159ff2afe`. Recheck the working tree before implementing each milestone; some requested repairs already exist in part.

Deliver precise citations to original text, readable artifacts for every pipeline step, and one CLI with explicit `manual` and `autopilot` modes. Continue the implemented `docgen_graph` pipeline and retire the runnable `old-approach` implementation after migration checks pass.

The parallel workstream is [test data and the investment platform](development-plan-task-2-test-data.md). The two agents can start independently using the ownership and input contract below.

## 1. Current behavior and actual gaps

| Area | Verified repository evidence | Implementation consequence |
| --- | --- | --- |
| Active implementation | `new-approach/src/docgen_graph/` contains the complete graph from snapshots to release; its README describes it. The root README incorrectly calls it a planning scaffold. | Extend the active implementation. Correct the root instructions rather than building another pipeline. |
| Original source navigation | `source_links.py` reads `source_url` from frozen Markdown metadata and exports `:~:text=` links. Local evidence files and a source index also exist. | Preserve this provenance chain and fallback; replace the imprecise fragment selection. |
| Evidence precision | `visible_phrase()` prefers an entire `As a ...` story in a table. Export passes the complete evidence block, not the supporting portion for a particular claim. Citation links are keyed by evidence label. | Add a claim-specific original-text selection. Two claims citing the same row may need different destinations. |
| Image exclusion | Inline `![...](...)` syntax is removed in one branch, but reference images and HTML `<img>` markup survive. Local probes reproduced both cases. | Parse text and asset nodes explicitly; do not expand the current regex into another incomplete image filter. |
| Link length | Ordinary phrases require at least 30 characters and may be truncated to 180; the preferred story branch returns the full story. There is no page-wide uniqueness or minimum-length search. | Replace fixed length heuristics with bounded, deterministic selection of the shortest valid locator. |
| Artifact storage | Content-addressed objects, a graph database, Markdown reports, plans, reviews and portable candidate bundles exist. Outputs are spread across the run root, `reports/`, `reviews/`, `candidates/`, and `releases/`. | Keep integrity protections while adding the required `stepX/` layout and readable projections. |
| CLI and reviews | `docgen-graph` already supports `run`, `resume`, `status`, `history`, `inspect-evidence`, and `budget`. Production review nodes cover plan, release and blocking issues. | Add modes and a single interactive execution loop. Manual currently does not review every step; the development evaluator's `--approve-plan` is not autopilot. |
| Restart safety | SQLite checkpoints, stable thread IDs, revision-bound decisions, runtime signatures and manifest checks exist. | Preserve these safeguards and define migration behavior for older runs. |
| Future code fixture | Code ingestion has Python AST support and generic text support for selected formats. `.java` is absent from `CODE_SUFFIXES`. Ticket filtering is absent. | Record this limitation. Full Java/Angular analysis and ticket selection belong to later work, not this repair task. |

Planning verification: eight existing source-link and pipeline-restart tests passed offline. The initial attempt could not create pytest's default temporary directory; rerunning with a fresh directory under `.docgen/` passed. No paid model calls or browser-navigation verification were performed. Passing these tests does not establish that current links highlight the correct fact in Confluence.

## 2. Ownership and parallel implementation contract

| Owner | Writable scope |
| --- | --- |
| Agent A | Active pipeline code, prompts, tests and evaluation tools; root packaging, lockfile, `.env.example`, `.gitignore`, and README; retirement of `old-approach`; this plan and its implementation report. |
| Agent B | New investment-platform source/history fixtures; `data/test_data_2*`; `scripts/test_data_2/`; this plan's companion and Agent B's implementation report. |
| Preserved inputs | Existing `data/test_data_1`, `data/test_data_1_html`, `data/legacy-insurance`, `data/template.md`, and their existing generator. Neither agent rewrites them for convenience. |

Agent A must not edit Agent B's fixtures or helper scripts. Agent B must not import production pipeline internals, change its dependencies, or modify the root README/configuration. Agent A owns pipeline integration tests and final root documentation links. Fixture failures are reported to Agent B instead of patched by Agent A.

Use separate branches/worktrees when available: `codex/pipeline-repairs` and `codex/investment-fixtures`. In a shared checkout, stage only owned files and do not run destructive repository-wide cleanup. Neither branch requires the other's commits to pass its own tests. Agent A uses small inline temporary fixtures until Agent B publishes the agreed contract; integration is the final milestone.

### Frozen fixture interface version 1

Agent B provides these paths, independent of package relocation:

| Path | Contract |
| --- | --- |
| `data/test_data_2/` | Exactly three source Markdown pages: `01-dictionaries.md`, `02-external-services.md`, `03-risk-profiling.md`; local `.jpg` assets. |
| `data/test_data_2_html/` | Three corresponding HTML pages, a navigation index, and JPEG attachments with deliberately different paths/names from Markdown assets. |
| `data/test_data_2_quick/` | Exactly one source page, `risk-profiling.md`, and a small JPEG asset set. |
| `data/test_data_2_quick_html/` | The corresponding quick HTML page and attachments. |
| `data/test_data_2_reference/` | Fixture manifest, citation cases, expected facts, discrepancies, exclusions and ticket mappings. These are evaluation inputs, never documentation source inputs. |
| `data/investment_platform/` | Inspectable Java/Angular/PostgreSQL/MongoDB application source without an embedded `.git` directory. |
| `data/investment_platform_history/` | A portable Git bundle and manifest, allowing an independent repository with real ticket-bearing history to be restored. |

Each Markdown page retains existing metadata names: `source_url`, `source_system`, `source_id`, `source_revision`. The default full mirror uses port `8766`; the quick mirror uses `8767`, leaving `test_data_1` on `8765`. Host/port are fixture-builder options, not assumptions embedded in production code. A rebuild records the chosen URL base and revision.

Each reference citation case has `case_id`, `source_id`, `markdown_path`, `html_path`, `claim`, `evidence_quote`, `target_text`, `expected_behavior`, and `reason`; optional `forbidden_fragments` and `max_encoded_fragment_bytes` describe negative/length cases. Paths are repository-relative with `/`. Expected behaviors are `text_fragment`, `local_evidence`, or `excluded`. Offsets, if recorded, use Unicode code points and reference a named hashed text projection. Agent B owns the JSON schema and case data. Agent A consumes the records without fixing a particular phrase-selection implementation in the fixture.

## 3. Exact evidence and short text-only links

### Supporting evidence and navigation are separate records

Extend assertion-to-passage mappings so each factual citation occurrence can identify the supporting source range: snapshot hash, source path/ID, evidence ID, exact quote, line range, and character range; preserve table row/column identity where available. Keep enclosing conditions, exceptions and scope as supporting context. A short navigation fragment must never replace the full evidential excerpt.

Where the model proposes a quote, validate it against the immutable source and the parsed visible-text projection. Reject invented or ambiguous offsets. One citation can need several supporting ranges; show several citations when a single location cannot support the claim. Do not link to a generic story cell when the factual proof is in a different cell of that row.

Use citation occurrence IDs, or an equivalent scoped mapping, so reusing `D1` in two output passages does not force both passages to use the same URL. Preserve evidence-label lookup for `inspect-evidence`. Editorial repairs must regenerate affected support ranges, links, final character offsets, candidate hashes and approvals together.

### Text projection and candidate selection

1. Build a deterministic plain-text view from parsed Markdown blocks and inline tokens. Keep visible prose, table cell boundaries, link labels, inline code, headings and captions. Decode entities and normalize whitespace without joining unrelated cells into fabricated sentences. Retain a mapping to source ranges.
2. Exclude images in every supported form: inline, reference-style, linked images and HTML image nodes. Exclude image alternative text, title attributes, attachment names/paths, raw tags, front matter and hidden markup from locator candidates. A caption may be cited only when it is an actual visible text node supporting the fact. Inventory/export of images remains supported independently.
3. Start inside the exact support range for the claim. Enumerate contiguous, word-boundary candidates; require a meaningful evidence-bearing match and uniqueness on the destination text model, not merely uniqueness inside one row. An unrelated ticket ID alone is insufficient proof.
4. Among valid locators, minimize the percent-encoded directive byte length, including any needed context. Prefer a plain exact phrase when equally short. Use the smallest prefix/suffix only when it disambiguates repeated evidence; allow a bounded start/end range for a necessary longer passage. Never cut at an arbitrary character limit into the middle of a word or semantic condition.
5. Preserve required original page query parameters, such as a Confluence page ID. The user's short-query requirement applies to the generated text selector, not removal of routing parameters from the original URL.
6. If no reliable text locator exists, link to the exact local evidence record and expose the original page separately. Record why highlighting is unavailable. Do not quietly substitute a broad page link and label it precise evidence, or manufacture a link from an image.

Text directives use `#:~:text=[prefix-,]start[,end][,-suffix]`; text components must encode delimiter characters. Prefix/suffix context disambiguates a match without becoming the highlighted text. These behaviors and the preference for exact matching with context only when necessary are described in the [WICG text fragment specification](https://wicg.github.io/scroll-to-text-fragment/). It is a community-group specification; browser support and navigation behavior need separate verification.

Minimization is over the declared valid candidates and supported grammar, with correctness preceding length. On tiny fixtures, compare with an exhaustive independent oracle; on large pages, measure bounded search effort and deterministic tie-breaking. Report median, p95 and maximum encoded selector length against the current implementation without accepting a shorter but weaker target.

### Source visibility and verification limits

Production currently receives Markdown, not the original rendered Confluence DOM. Distinguish `verified_html`, `markdown_projection_only`, and `fallback` link checks in the citation audit. Local fixture mirrors give exact destination-text verification; they must not become a production dependency or a source of product facts. A URL alone does not prove that authenticated Confluence still contains the same rendered words. Do not add unrestricted web fetching to citation export as part of this task.

Allow an optional explicit local source-page map, configured through `.env`, for destination verification. It maps declared source IDs/URLs to supplied HTML exports; freeze their bytes and record the verification revision. Use their visible text only to verify/disambiguate navigation, never as additional product evidence. Without that map, report the weaker Markdown-only check. Do not discover sibling fixture directories implicitly. Unit tests can inject the same verifier interface; integration runs use the explicit map, so a deliberately absent HTML phrase can produce a tested local-evidence fallback. This is a locator-verification input, not a general HTML ingestion adapter.

Verify representative generated links in a supporting browser over HTTP, including a repeated phrase, a table-cell claim, and changed image paths. Record the browser and what was actually observed; string membership and successful page loading alone do not prove correct highlighting. If the environment blocks this check, report it as unverified rather than passing it.

## 4. Step artifact layout

Give every existing logical processing node a stable step number. Keep nodes sequential and checkpointed; do not combine extraction and verification merely to simplify directories.

| Folder | Existing node |
| --- | --- |
| `step1/` | `snapshot_inputs` |
| `step2/` | `inventory_sources` |
| `step3/` | `analyze_code_unit` |
| `step4/` | `verify_code_unit` |
| `step5/` | `extract_document_batch` |
| `step6/` | `verify_document_batch` |
| `step7/` | `link_graph_batch` |
| `step8/` | `verify_graph_batch` |
| `step9/` | `finalize_graph` |
| `step10/` | `compile_template` |
| `step11/` | `draft_page_plan` |
| `step12/` | `retrieve_plan_evidence` |
| `step13/` | `validate_page_plan` |
| `step14/` | `review_plan` |
| `step15/` | `retrieve_section_evidence` |
| `step16/` | `write_section` |
| `step17/` | `verify_section` |
| `step18/` | `assemble_pages` |
| `step19/` | `edit_page` |
| `step20/` | `verify_edited_page` |
| `step21/` | `audit_documentation` |
| `step22/` | `export_candidate` |
| `step23/` | `review_release` |
| `step24/` | `finalize_release` |
| `step25/` | `review_issues` |

New generic manual-review and automatic issue-resolution nodes receive `step26/` and `step27/`; append future numbers without renumbering existing steps. A versioned run manifest is the source of the node-to-folder mapping. Control nodes link back to the exact producing step and item revision.

Required shape under the configured runtime workspace:

```text
runs/<thread_id>/
  README.md
  run-manifest.json
  decisions.md
  exclusions.md
  step1/
    README.md
    manifest.json
    sources.md
  step5/
    README.md
    manifest.json
    items/batch-0001/revisions/r0001/
      result.md
      result.json
      manifest.json
  step22/
    README.md
    candidates/<candidate_hash>/
      documentation/index.md
      documentation/assets/
      evidence/
      source-index.md
      audit.json
      candidate-manifest.json
  step24/
    README.md
    release.json
```

Every executed step writes a readable Markdown summary with its inputs, outputs, findings, decisions, costs where applicable, and next action. Structured data remains pretty-printed JSON/JSONL or SQLite as appropriate, accompanied by usable tables/reports. Do not require the operator to decode content-addressed objects to inspect a result.

Repeated nodes use stable item IDs and immutable attempt/revision subdirectories; a repair must not overwrite reviewed content. Summaries link to current and previous revisions. Skipped steps, including code analysis in a docs-only run, have a visible `skipped` reason and require no fictitious review. Root reports aggregate step records; they do not become independent sources of truth.

Keep content-addressed objects, checkpoint databases and shared caches as internal storage. User-facing stage artifacts must live under their step folders even if the same bytes are also in the object store. Centralize paths, atomic writes, manifests and report rendering in shared storage code. Do not scatter folder names through node implementations. Raw model artifacts and per-stage logs, when exposed, belong under that stage's diagnostics directory.

Artifact writes happen atomically before checkpoint references are committed. Replay detects an already-persisted revision, verifies its hash and avoids duplicating it. Candidate bundles remain portable when copied without the run workspace; all relative evidence and image links must continue to work.

## 5. One CLI and two execution modes

### Public entry point

Consolidate the active package at repository root: `src/docgen_graph/`, `tests/`, `evaluation/`, root `pyproject.toml`, `uv.lock`, and placeholder-only `.env.example`. Keep the internal package name to reduce unnecessary changes; publish one console command, `docgen`. Move supported active evaluation assets together and update their paths.

After initial environment configuration, these are the planned commands from repository root:

```powershell
uv run docgen run --mode autopilot --docs data/test_data_2_quick --template data/template.md --thread-id risk-auto-001
uv run docgen run --mode manual --docs data/test_data_2_quick --template data/template.md --thread-id risk-manual-001
uv run docgen resume --thread-id risk-manual-001
uv run docgen status --thread-id risk-manual-001
```

Retain `history`, `inspect-evidence`, and `budget` behind the same command. `run` defaults to `manual`; documentation shows explicit modes. Persist mode and policy version in the run manifest and checkpoints. Resume uses the stored mode; an attempted implicit mode change is rejected. Technical retries reuse the same thread; a changed input/policy creates an explicit new revision.

The CLI starts and drives the entire process, including plan and final release, without phase-specific scripts or hand-authored decision JSON for normal interactive use. Retain `--decisions` as an automation/testing interface. Human prompts contain the relevant report paths, exact revision, available actions and a concise change summary.

### Manual mode

After every executed artifact-producing node/item, require human review of its output before advancing. This includes extraction versus verification, each repeated batch/section, and changed results after repair; do not treat approval of a whole extraction queue as approval of unseen items. Existing plan, issue and release reviews serve their own stage gates without a duplicate approval of the same artifact.

Use a separate LangGraph review node with `interrupt()` after the producing node's checkpoint. The CLI gathers a structured decision and resumes via `Command(resume=...)`. No model request or non-idempotent write may occur before the interrupt in that review node. Never implement an independent pause file or in-memory review loop that loses checkpoint state.

Supported decisions are approval, requested correction, and rejection, bound to the exact stage/item/artifact hash and reviewer. Corrections create a new revision, rerun affected validators and invalidate dependent approvals. The user can inspect the finalization receipt as the final manual stage; mark the run complete only after its required gate. Cancellation/EOF leaves a resumable pending interrupt and does not imply consent. In a noninteractive terminal, pending manual review produces a documented status/exit code rather than auto-approving.

### Autopilot mode

Resolve content issues using deterministic checks first and bounded Gemini reasoning only where useful. Automatic decisions have `actor_type=ai` or `actor_type=policy`, rationale, evidence references, attempts, policy version, and artifact revision. They are never recorded as human approvals. Plan/release gates still validate the exact hashes and receive attributed automatic decisions through the supported graph decision flow.

| Situation | Required behavior |
| --- | --- |
| Evidence supports an unambiguous repair | Apply it, rerun affected stages and validations, and record the change. |
| Conflicting assertions with documented applicability | Apply the supported scope/version distinction, keeping both original assertions and the rationale. |
| Conflict without sufficient authority | Present both as a documented discrepancy when useful, or exclude the uncertain conclusion and its dependent content. Do not choose whichever source sounds more confident. |
| Exhausted bounded content repair | Exclude the smallest coherent unsupported unit and record why; rebuild dependent allocations and check remaining passages. Never drop a qualifier while retaining an unconditional version of its claim. |
| Essential feature cannot be documented coherently | End as `incomplete` with a readable explanation and preserved artifacts, rather than releasing a misleading page. |
| Corrupt artifacts, stale approval, missing credentials/pricing, or insufficient budget | Block further execution with a technical/configuration status. These failures are not content exclusions and cannot be waived by AI. |

Use a configurable, persisted attempt limit with a default of two content repair attempts per item. Reuse existing validation nodes; do not add an AI call after every successful stage. A decision to reject an uncertain item must recompute all downstream coverage and plan obligations.

The run-level `exclusions.md` and machine-readable equivalent list source IDs, exact ranges, the rejected proposition, reason, dependent items, stage and decision reference. Every selected input remains accounted for as included, duplicate, excluded with justification, or unresolved. Autopilot's explicit exclusions satisfy accounting, not complete semantic preservation. A release with substantive uncertainty exclusions is `complete_with_exclusions` and visibly reports them; unresolved mandatory items block release. The command prints both the output location and the exclusions report.

Document stable exit behavior for automation: successful releases, including visibly reported exclusions, return success; waiting for manual input, technical/budget blocking, rejection and incomplete content have distinct non-success codes. Preserve a machine-readable status option alongside the normal readable CLI output.

This mode policy supersedes older plans' unconditional human-only content decisions when autopilot is selected. It does not weaken source evidence, deterministic integrity checks, or the current spending ceiling.

## 6. Migration and removal of legacy execution

1. Inventory executable commands, package imports, helper scripts, checkpoints, environment path defaults and ledgers. Record the baseline revision. Historical `.ai/` reports remain historical evidence and are not competing supported entry points.
2. Move the active package and tests to the canonical root layout. Update package resources, implementation-signature inputs, evaluation paths, CLI help and root README. Agent B's fixture paths do not move.
3. Preserve the cumulative root `.docgen/budget.sqlite` ledger and pricing records at their existing paths. Use a distinct active-pipeline workspace such as `.docgen/graph/`; do not merge its checkpoints into the legacy root checkpoint database.
4. Provide a documented dry-run and copy-first migration path for `new-approach/.docgen/` artifacts. Verify manifests and object hashes before adopting copied data. Do not overwrite `.env`; describe changed defaults and allow `--env-file` for an existing file.
5. Explicitly version the changed state/graph schema and runtime signature. Existing runs must remain inspectable. Resume only demonstrably compatible checkpoints; otherwise return an actionable incompatible-revision message and create a new run from frozen inputs with provenance links. Never bypass the existing signature check to make old checkpoints appear compatible, and never force automatic paid reruns.
6. Remove `old-approach` source, entry points, obsolete dependency lockfile and runnable legacy-specific helper scripts once replacement tests pass. Audit root and `.ai/` Python utilities for legacy imports/commands; remove obsolete executable utilities or retain their useful results as non-executable historical reports. Do not delete historical runtime outputs, ledgers or user secrets. Preserve any unique evaluation evidence before removing its containing directory.
7. Remove the now-empty active-package wrapper directory only after its ignored local state has an explicit disposition. Document unsupported historical commands and the current command in the README; do not maintain a second runnable pipeline or silent legacy fallback.

Repository history is the source for old implementation code. No archive copy of legacy source should remain executable inside the current checkout. A clean environment must install and run the active package without `old-approach` or its environment.

## 7. Milestones and acceptance

| Milestone | Work | Acceptance evidence |
| --- | --- | --- |
| A0 Baseline | Recheck observations, run relevant existing tests, freeze fixture contract and ownership. | Each concern marked existing, partial, reproduced, or still unverified; no duplicate implementation of already-correct behavior. |
| A1 Evidence and links | Add exact support ranges, text projection, per-occurrence locators, shortest valid selection and fallbacks. | Correct cell/sentence targets, image-free locators, original provenance and unchanged mandatory URL parameters. |
| A2 Step outputs | Centralize path mapping, readable reports, revision manifests and replay-safe stage exports. | Every node output is reachable through `stepX/`; repeated work and skipped stages are understandable without reading raw object storage. |
| A3 Modes | Implement mode state, manual stage gates, attributed automatic decisions and exclusion reporting. | Manual gates every stage/item; autopilot finishes or reports a justified terminal/blocking state without waiting for content approval. |
| A4 Consolidation | Move active package, migrate configuration/state conservatively and retire legacy execution. | Root command works in a clean environment; prior spending and evidence are preserved; incompatible historical runs fail explicitly. |
| A5 Integration | Consume Agent B's version-1 quick/full reference cases and assess the reader output. | Reproducible citation, mode, artifact and portability results; external-browser and paid-evaluation gaps reported separately. |

Required regression coverage:

- Exact factual evidence from a non-story table cell; multiple distinct citations into one row; same phrase in different rows; a short source rule under the old 30-character threshold; Unicode, entities, nonbreaking spaces, punctuation and emphasis.
- Inline, reference-style, linked and HTML images, including image-only evidence. Renaming every JPEG between Markdown and HTML must not change a text locator. Pixel content, alt text and attachment URLs cannot become supporting evidence.
- Independent minimality checks for short cases, page-wide ambiguity, preservation of original query/anchor components, missing `source_url`, source text absent from the HTML mirror, and reliable local-evidence fallback.
- Final citation/support offsets after editorial changes and shortened link rendering; copy-only candidate portability and manifest tampering detection.
- Restart while awaiting every kind of manual review; at least one repeated extraction item and writing item; immediately after artifact write and before checkpoint commit; after an automatic exclusion. Verify no duplicate paid call or decision and no approval of a changed revision.
- Autopilot ambiguity, dependency-aware exclusion, exhausted retries, all-essential-content rejection, and budget/configuration blocking. Human approval and AI approval must remain distinguishable in final manifests.
- Clean-install CLI run, status/resume/history, no import of legacy code, configuration path continuity, and rejection of incompatible old checkpoints.

Fast CI/regression coverage uses deterministic model doubles and Agent B's quick fixture. The full corpus provides coverage and size evaluation, not a mandatory paid invocation on every test run. A passing structural fixture cannot establish universal semantic fidelity or production Confluence compatibility.

Follow [AGENTS.md](../AGENTS.md) and the provenance rules in [the original development plan](development-plan.md). Use the LangGraph fundamentals and persistence skills when implementing graph changes. Keep identifiers, prompts, software UI and tests in English, with no explanatory code comments/docstrings.

All model calls use `gemini-3.8-flash`. Inspect current pricing and exchange rates and preserve cumulative accounting, including uncertain charges and reservations. Agent A owns paid pipeline evaluation; Agent B's fixture construction should need no Gemini requests. Do not reset accounting.

Deliver an implementation report with completed milestones, actual commands/results, selector-length comparison, migration disposition, sample artifact paths, exclusion examples and remaining verification gaps. Completion requires working behavior and checks, not merely new CLI flags or renamed folders.
