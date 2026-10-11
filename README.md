# doc-gen

This repository contains two independent approaches to generating documentation.

| Directory | Purpose |
| --- | --- |
| [old-approach](old-approach/README.md) | The existing three-phase implementation, its tests, evaluation results, scripts, and dependency lockfile. |
| [new-approach](new-approach/README.md) | The new implementation location. Currently a planning scaffold; no new pipeline has been implemented. |
| [data](data/) | Shared source inputs and templates used by both approaches. |
| [.ai/new-approach](.ai/new-approach/development-plan.md) | The independent development plan: code analysis and legacy documentation, graph retrieval, template-based planning, explicit plan approval, and source-backed writing. |

Historical plans and implementation reports remain in `.ai/`; research remains in `research/`. The existing revitalization proposal is separate from the new approach.

## Running the existing implementation

Run from the repository root so the existing `.env`, `.docgen` workspace, checkpoints, pricing, and cumulative spending ledger keep their original paths:

```powershell
uv sync --project old-approach --python 3.13
uv run --project old-approach docgen status --thread-id THREAD_ID
uv run --project old-approach docgen run data/legacy-insurance --thread-id NEW_THREAD_ID
```

Follow [the existing implementation guide](old-approach/README.md) for configuration, review, and generation. Keep an existing root `.env`; for first-time setup only, copy `old-approach/.env.example` to `.env`. The root `.venv` is a retained local environment from before the move; `uv` manages the relocated project's environment separately.

Both approaches read inputs and templates from the repository-root `data/` directory. Keep generated artifacts and runtime state separate from these shared inputs.

Local runtime artifacts remain at the root to preserve historical references. No checkpoints or spending records were migrated or reset. Both approaches must respect the same cumulative PLN 200 Gemini development allowance; the new approach does not receive another allowance.
