# Corpus pipeline improvement plan

Analyze the first full `data/` run, implement measured reliability and quality
improvements, then execute a fresh run against the same source files. Preserve
the first run as historical evidence. Do not present automated checks as domain
approval or publish customer documentation without the existing review gates.

## Work queue

- [x] Audit baseline requests, latency, usage, coverage, entity identity and conflicts.
- [x] Select and implement fixes supported by the audit, keeping evidence intact.
- [x] Add focused regression tests and run lint, types and the full offline suite.
- [x] Launch a fresh full-corpus run with bounded calls, repairs and token usage.
- [ ] Complete the fresh run to knowledge review (blocked by provider HTTP 402).
- [x] Compare both runs in `docs/`, including remaining semantic-review limits.

## Initial findings to verify

1. Extraction submits redundant source metadata and table representations.
2. The monolithic reconciliation request approaches one million input tokens;
   correcting invalid aliases forced another large request.
3. Version fields sometimes contain source-page identifiers, fragmenting identity.
4. Coverage dispositions can hide omissions inside a large source table.
5. Cumulative conservative reservations triggered a false budget stop despite much
   lower reported usage; progress and error diagnostics need to expose the distinction.

## Verification and risks

Preserve exact source snapshots and locators. Test bounded batching, reference
integrity, scope/version-safe aliases, conflict visibility, bounded repairs,
budget enforcement, resume/reset invalidation and packaged prompts. Measure
latency and actual reported tokens separately from reservations. Candidate
blocking may miss cross-topic conflicts; disclose its scope and retain unmerged
entities rather than inventing merges. A fresh run may expose model variability;
claim counts alone must not be described as semantic accuracy.

Definition of done: tested changes, a fresh completed extraction/reconciliation
run (or a precisely documented terminal failure), and a reproducible comparison
of the two runs without changing the inputs or silently approving domain facts.

## Implemented changes

- Markdown tables now have per-row evidence IDs and exact row locators; raw headers
  are retained separately with their source location and displayed in evidence views.
- Extraction requests omit redundant snapshot/parser metadata and duplicate table
  text. The complete source snapshots and parsed records remain authoritative.
- Extraction requires exactly one disposition per supplied span. Prompts distinguish
  product releases from page/feature IDs and require consistent capability typing.
- Reconciliation separates identity candidates from qualified-claim conflict checks.
  Requests are size-bounded, successful batches are recoverable, and invalid responses
  get at most two repairs. Oversized identity groups stay unmerged with explicit gaps.
- Conflict checks group related topics and explicit source conflict groups across
  sections; every claim enters the plan. Split topics and non-exhaustive cross-topic
  comparison remain disclosed limitations, not hidden truncation.
- Token budgets settle successful calls to reported input/output usage. Calls with
  unknown usage retain their full reservation. Historical reservation totals remain
  available, and legacy manifests without settled accounting remain conservative.
- CLI output reports stage/batch progress and generates a report on resume failures.
- `scripts/summarize_run.py` produces read-only, reproducible run metrics.

Local preflight: 4,702 source spans, including 2,590 individual table rows; 151
extraction batches (baseline: 182), no parser warnings. The expanded offline suite
currently passes 39 tests with one opt-in live test skipped.

The wheel resource check and desktop/mobile graph-preview browser checks also
passed. Fresh run `run-20261007-223031-d22eb286` started with `config.corpus.yaml`;
the first run remains unmodified. The fresh run has an 8-million accounted-token
limit and a 400-request cap, not an unlimited retry loop.

## Terminal outcome

The fresh run completed 87 of 151 extraction batches, then failed at the provider.
The original wrapper error lacked a saved HTTP code. Safe nested-exception status
diagnostics were added and tested. Resumption reused all 87 validated batches;
the next request and two bounded retries returned HTTP 402 / RESOURCE_EXHAUSTED.
HTTP status now takes precedence over generic provider labels, so payment-related
402 errors will not be retried. No further API calls or billing changes were made.

The run remains resumable with the existing configuration and receipts. Its local
caps were not exhausted. It has 2,547 provisional claims, 562 entities and 3,047
source dispositions; the product register has only been parsed, not extracted.
Reconciliation was not executed live, so no improved merge/conflict quality or
end-to-end savings are claimed. The [comparison](pipeline-run-comparison.md) records
both runs, exact usage, processed files and the recovery command.

Final offline suite: 41 passed, one opt-in live test skipped. All 87 batch receipts
and unchanged source hashes were verified. The complete baseline extraction also
passed the new reconciliation planner's size/claim-coverage checks without API
calls. Fixture and partial real-corpus previews passed desktop/mobile browser checks.
