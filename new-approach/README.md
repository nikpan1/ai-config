# New approach

This directory is reserved for an independent implementation of the [development plan](../.ai/new-approach/development-plan.md).

The intended pipeline is:

1. Snapshot legacy documentation and source code.
2. Produce concise, source-backed code analysis with a separate detail and coverage inventory.
3. Index that analysis and the legacy documentation in a persistent knowledge graph linked to original evidence.
4. Prepare a documentation page plan from the user's template and request explicit approval.
5. Retrieve graph context and original evidence to write and verify the approved documentation.

Status: planning only. There is no runnable package, CLI, dependency lockfile, or generated documentation here yet. The plan defines the implementation milestones and acceptance criteria.

Use the repository-root [data directory](../data/) for source inputs and templates shared with the old approach. Keep generated reports, indexes, checkpoints, and other runtime artifacts in this approach's own workspace; do not write them into shared input data.

Implement the new package, tests, approach-specific fixtures, configuration, and runtime state here without importing modules, prompts, schemas, or checkpoints from `../old-approach`. Shared input fixtures may live in `../data/`. The repository-wide instructions still apply. Development spending must use the same cumulative budget ledger as the old approach, through an independently implemented accounting adapter; runtime independence does not create a new budget.
