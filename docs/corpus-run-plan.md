# Full corpus run

Run all three Markdown files under `data/` through extraction and reconciliation,
then stop at knowledge review. Do not approve the domain graph automatically.

- [x] Inventory inputs and start a bounded Gemini run with corpus-sized limits.
- [x] Repair the extraction coverage-reference failure without relaxing provenance.
- [x] Verify bounded extraction repair, reuse after failure and fresh work after reset.
- [x] Resume the corpus run and retain all stage/model artifacts.
- [x] Report the review location, actual usage and any unresolved processing failure.

The first live attempt stopped on batch 3 with a coverage reference mismatch. Add
bounded repair and verified per-batch recovery before continuing the long run.
Prompt/config changes and explicit reset must still invalidate old results. Keep
request and token budgets finite; preserve unresolved facts for review.

The updated suite passes 29 tests, with the opt-in live fixture test skipped.
Run `run-20261007-211927-87e3d586` resumed in extraction attempt 2. The added repair
prompt invalidated attempt 1; it remains inspectable. The new attempt writes
per-batch receipts and progress events. Reuse requires matching inputs, prompt and
configuration fingerprints, dependency revisions, execution ID and output hash.
Explicit resets and prompt changes do not reuse those batches.

All 182 extraction batches completed, producing 2,634 candidate claims from 2,319
evidence spans across all three files. Reconciliation initially exceeded the
conservative reservation limit by 26,133, so the cap was raised to 12.5 million.
Its response then proposed 38 cross-type aliases and was correctly rejected.
Make the existing type-matching and no-alias-chain validation rules explicit in
the reconciliation prompt. Allow one fresh reconciliation request with a
15-million reservation cap; retain the completed extraction unchanged.

## Result

Run `run-20261007-211927-87e3d586` reached `waiting_for_review` at the knowledge
gate. Reconciliation attempt 3 passed structural/provenance validation; no domain
approval was submitted. All three source files were included. The graph contains
1,608 entities, 2,634 candidate claims, 578 relationships and 14 aliases. Eight
conflicts remain unresolved. Of 2,319 evidence spans, 1,572 are covered, 744 have
exclusion dispositions and three are unresolved. These dispositions and the
semantic accuracy of the claims still require review.

The run used 200 model requests, including failed attempts and repairs. Reported
usage is 2,950,442 input tokens and 1,021,518 output tokens; the conservative
reservation total is 14,472,003. Reservation counts are not billed token counts.
The final regression run passed 29 tests with one opt-in live test skipped.

- Report: `runs/run-20261007-211927-87e3d586/report/index.html`
- Graph: `runs/run-20261007-211927-87e3d586/stages/reconcile/attempts/3/graph-preview/index.html`
- Review: `uv run docgen review run-20261007-211927-87e3d586`

No customer documentation or final export has been produced for this run.
