# Legacy Docgen

Turn local Markdown specifications into evidence-backed English customer
documentation. The CLI runs all eleven development-plan stages through LangGraph,
uses Gemini through LangChain, and pauses for knowledge, outline and final review.
Inputs remain unchanged. Source excerpts and informative images are sent to Gemini.

## Install and run

Python 3.12+ and [uv](https://docs.astral.sh/uv/) are required.

```powershell
uv sync --locked
uv run docgen inspect data/legacy-insurance
```

Set `GOOGLE_API_KEY` or `GEMINI_API_KEY` in your environment. Set `model` in
`config.example.yaml` to the Gemini Developer API model you intend to evaluate.
There is intentionally no untested default model. Then start with the small fixture:

```powershell
uv run docgen run tests/fixtures/retry.md --config config.example.yaml
```

The command prints a run ID and report path. Each stage stores its effective input,
output, attempts, model exchanges and errors under `runs/<run-id>/stages/`.
The graph preview and reports are local HTML files that open directly in a browser.
No server is required. Credentials are not stored in configuration or run artifacts.

## Review

```powershell
uv run docgen review <run-id>
uv run docgen review <run-id> --write-decision decision.json
```

Edit the decision JSON with your reviewer name, rationale and action: `approve`,
`revise`, `defer` or `cancel`. Keep the displayed `revision` unchanged. Submit it:

```powershell
uv run docgen review <run-id> --decision decision.json
```

Approval without a knowledge patch accepts candidate claims. Unresolved conflicts
prevent this approval. To resolve conflicts, put the complete edited graph in
`patch`, assign every claim `accepted`, `rejected` or `unresolved`, and record a
conflict resolution rationale. Retain rejected claims and conflicts in the graph.
The decision records the full correction, including entity merges/splits.
Image-only claims receive the same explicit knowledge review.

Source evidence cannot be edited. Human factual additions use `statements`: an
array of attributed statements. A new or corrected claim in the graph patch may
reference `review:1`, `review:2`, etc. in `evidence_ids`; the application assigns
versioned evidence IDs and reviewer attribution. Do not add a coverage row for a
statement yourself. Ordinary approval never creates evidence.

Outline patches use the complete outline object. They must account for every
accepted claim, and prerequisites must precede dependent chapters. Final review
cannot patch prose: choose `revise` and describe the correction, then `resume` to
regenerate and revalidate it. `included_image_ids` explicitly selects legacy images
for the customer bundle. Every image is retained in the internal evidence bundle.

## Inspect, resume and reset

```powershell
uv run docgen stages <run-id>
uv run docgen show <run-id> --stage extract --attempt 1
uv run docgen report <run-id>
uv run docgen resume <run-id>
uv run docgen reset <run-id> --from compose --dry-run
uv run docgen reset <run-id> --from compose
uv run docgen resume <run-id>
uv run docgen reset <run-id> --from extract --purge
```

Reset invalidates the selected stage and its dependent results and approvals, then
starts a fresh execution thread. Upstream stages stay reusable. Old attempts are
retained unless `--purge` is explicit. Purge retains source snapshots, shared graph
payloads still referenced by other attempts, historical exports and manifest
tombstones. Interrupted cleanup resumes under the next run lock. Only one worker
may modify a run. Reset from `inventory` to ingest changed original files; ordinary
resume uses the retained source snapshot.

Missing/corrupt artifacts and prompt/configuration changes invalidate dependent
results before resumption. Raising operational budgets or timeouts does not erase
completed work. Repeated failures terminate with inspectable errors. Resume a
failed stage to retry; reset a cancelled run before continuing. Each retry may incur
another API charge. Before a request, the budget reserves serialized input bytes,
schema/prompt overhead, output allowance and an image estimate. A response with
complete usage metadata settles that reservation to actual input/output tokens.
Unknown usage retains its full reservation. `usage.budget_tokens` is the enforced
accounting total; `reserved_tokens` remains the historical sum of all reservations.
Legacy manifests without settled accounting retain conservative prior reservations.

Provider errors retain safe numeric/status codes, not raw transport messages.
HTTP 402 is not automatically retried, even when labelled `RESOURCE_EXHAUSTED`;
local budget increases cannot clear a provider-side refusal. Verified batches
remain resumable when the provider accepts requests again.

Extraction validates each batch before saving it. Invalid structured references get
at most `repair_attempts` corrective model calls with the original evidence.
Resuming a failed extraction reuses verified batches from the same execution and
configuration; reset or prompt changes require fresh requests. Batch progress is
recorded in `events.jsonl` and printed by the CLI with completed/total counts.

Markdown table rows have individual evidence IDs, exact row excerpts and source
locations. Table headers are retained separately and supplied to the model with
every row. Every supplied text span requires exactly one coverage disposition.

Reconciliation first checks size-bounded identity candidate groups, then qualified
claims grouped by topic and explicit source conflict markers. It retains full
claims and source evidence in the graph while omitting redundant transport fields
from model requests. `reconcile_chars` bounds each initial batch. Invalid responses
receive at most `repair_attempts` repairs, and verified batches survive a failed
stage resume. Oversized identity groups stay separate with a recorded gap;
split conflict topics explicitly disclose incomplete cross-chunk comparisons.
Candidate grouping is not an exhaustive all-pairs conflict search.

For the full supplied corpus, use the bounded evaluation configuration:

```powershell
uv run docgen run data --config config.corpus.yaml
```

This still stops at knowledge review. See the [two-run comparison](docs/pipeline-run-comparison.md)
for measured results and limitations. The comparison metrics can be reproduced
without mutating historical runs using `python scripts/summarize_run.py runs/<run-id>`.

## Diagrams and exports

Install the pinned Mermaid CLI when generating diagrams:

```powershell
pnpm install --frozen-lockfile --ignore-scripts
```

Set `browser_executable` to a local Chrome/Chromium executable, or install the
browser expected by Puppeteer. Set `mermaid_cli` to the absolute
`node_modules/@mermaid-js/mermaid-cli/src/cli.js` path when running outside this
directory. Validation checks the pinned renderer version and renders each diagram
to SVG. Missing renderer/browser or invalid syntax blocks final approval. Inspect
the SVGs during final review for visual readability.

Final approval exports automatically; `docgen export <run-id>` inspects/reuses that
approved export. `output/<run-id>/<bundle-hash>/` contains customer chapters,
preparation checklist, glossary, diagrams, selected images and a portable internal
audit bundle with excerpts, image evidence, coverage, provenance and checksums.
Customer block IDs map to `audit/provenance.json`. Both editions use the same
approved content revision. `customer_evidence: true` includes an evidence appendix.

## Verification and limits

```powershell
uv run pytest -q
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv build
```

The test model exists only under `tests/`; there is no fake production provider.
For the opt-in Gemini check, set `DOCGEN_LIVE=1` and `DOCGEN_MODEL` and run
`uv run pytest -m live -s`. It retains a real run at knowledge review, with timings
and usage in `evaluation.json`; finish human reviews through the CLI.
Browser verification uses `python tests/build_preview_fixture.py`, then
`node tests/verify-preview.cjs`; set `DOCGEN_BROWSER` for your local browser path.
See [evaluation status](docs/evaluation.md) for tested behavior and release gates.

The supplied corpus is synthetic and intentionally contradictory. Full-corpus
usage and latency are measured separately from semantic accuracy and human
readability, which still need domain evaluation. Extraction and reconciliation
are batched; outlining still requires its structured graph to fit `context_chars`.
Oversized inputs stop or receive explicit review gaps rather than silently
discarding evidence. Evaluate a small selected corpus first and set limits for your
chosen model. A domain reviewer must assess semantics and missing preparation
details. Reference integrity and model semantic review do not establish truth.

Optional Streamlit, cross-run document diffs, embeddings, multiuser review and hosted
services are outside this implementation. Application prompts are packaged YAML
resources; no direct Google SDK or Gemini HTTP calls appear in application code.
The integration follows the official [LangChain Gemini guide](https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai)
and [LangGraph interrupt contract](https://docs.langchain.com/oss/python/langgraph/interrupts).
