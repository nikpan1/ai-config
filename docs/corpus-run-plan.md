# Full corpus run

Run all three Markdown files under `data/` through extraction and reconciliation,
then stop at knowledge review. Do not approve the domain graph automatically.

- [x] Inventory inputs and start a bounded Gemini run with corpus-sized limits.
- [x] Repair the extraction coverage-reference failure without relaxing provenance.
- [x] Verify bounded extraction repair, reuse after failure and fresh work after reset.
- [ ] Resume the corpus run and retain all stage/model artifacts.
- [ ] Report the review location, actual usage and any unresolved processing failure.

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
