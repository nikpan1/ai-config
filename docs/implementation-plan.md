# Implementation work plan

Implement the first-release workflow described in `development-plan.md` with a
local Python package and terminal interface. Optional Streamlit work is deferred.

## Scope and checkpoints

- [x] Inspect the supplied corpus; add small annotated regression fixtures.
- [x] Package configuration, typed records, external prompts and Gemini integration.
- [x] Implement immutable ingestion, source locations and image inventory.
- [x] Implement persistent stage attempts, dependency invalidation, reset and purge.
- [x] Wire LangGraph extraction, reconciliation, reviews, outline, authoring,
  validation and export with SQLite checkpoints.
- [x] Add a local interactive graph preview and inspectable run reports.
- [x] Verify offline workflows, restart, provenance, review invalidation and packaging.
- [x] Document operation and identify unverified live-model/reviewer acceptance checks.

## Risks and definition of done

The supplied corpus is synthetic and intentionally contradictory. Preserve its
qualifiers and disagreements; do not treat automated reference checks as proof of
semantic correctness. Model credentials and a domain reviewer may be unavailable.
Record live evaluation as unverified unless actually performed. No production
release claim is justified by offline test doubles.

Done for implementation means a usable installed CLI, all explicit stages with
inspectable history, restartable review gates, safe reset/purge, evidence-linked
drafts and portable exports, passing formatting/lint/type and focused acceptance
tests. The release additionally needs real Gemini evaluation and human approval.

## Verification outcome

Initial verification: 26 offline tests passed; the opt-in Gemini evaluation was
skipped because no API key was configured at that time. Ruff lint/format and mypy pass.
The installed CLI and built wheel
work, including prompt and frontend resources loaded outside the repository.
Desktop/mobile graph interactions and canvas pixels pass browser checks, and the
pinned Mermaid renderer produces the flowchart fixture. Corpus parsing covers all
three supplied documents with 2,319 spans, 207 tables and no missing-link warnings.

Subsequent live verification on 7 October 2026 completed all eleven stages using
Gemini on the retry fixture: four claims, two chapters, one diagram, nine model
requests and no validation findings. See `evaluation.md` for the saved run and
usage. Agent fixture review does not replace outstanding human domain acceptance.
