# Codex live-flow validation

Date: 2026-10-12. The requested Codex integration was exercised against real model endpoints. No documentation release was produced: the final run ended `incomplete` at the independent code-classification audit. All attempts, successful analysis, failures, graph artifacts and checkpoints remain available for inspection.

## Inputs and configuration

- Documentation: `data/test_data_2_quick`, including its two source illustrations.
- Code: `data/investment_platform`, restricted to `backend/src/main/java/example/fixture/RiskProfileService.java`. Other implementation files were not analyzed.
- Template: `evaluation/codex-live/template.md`, with four numbered sections.
- Code analysis: `openai-codex==0.162.1` and its matching CLI runtime, explicitly configured `gpt-6-astra` using the existing API credential. The runtime used an isolated home, empty workspace, frozen source context, denied writes and disabled execution/discovery tools. No desktop authentication files were copied.
- Extraction, classification, independent audits and authoring: `gemini-3.8-flash`.
- Gemini output was increased from 8,192 to 16,384 tokens after an observed classification truncation. New immutable run revisions were used when implementation or configuration changed.
- Runtime workspace: `.docgen/codex-live-validation`; shared accounting: `.docgen/budget.sqlite`. Existing ledger rows were preserved. No Auggie run was attempted.

## Observed outcomes

| Run | Outcome |
| --- | --- |
| `codex-risk-live-20261012-a` | Source inventory rejected a quote that omitted the original Markdown emphasis markers. This exposed missing bounded repair in that stage. |
| `codex-risk-live-20261012-b` | Codex reached the API; HTTP 400 rejected the raw Pydantic output schema because strict objects require `additionalProperties: false`. |
| `codex-risk-probe-20261012` | Actual Codex analysis succeeded after schema correction: 13 candidate facts, 7 evidence-backed relations, retained SDK/model/session/request provenance. |
| `codex-risk-live-20261012-c` | Actual Codex analysis produced 12 facts and 8 relations; independent Gemini code verification passed. Gemini classification then exhausted its configured output token bound. |
| `codex-risk-live-20261012-d` | Reused the validated Codex cache. All code stages and document-source audits passed, including one repair of a missing table qualifier. Built a graph containing 35 assertions and 35 source aspects. The first authoring tool exposed document extraction provenance invented by the model; immutable evidence publication correctly rejected those unknown IDs. |
| `codex-risk-live-20261012-e` | Actual Codex analysis produced 12 facts and 6 relations and passed independent code verification. Classification completed within the larger output bound. Its independent audit rejected changed temporal status and missing original fact identities; autopilot ended `incomplete` without bypassing the gate. |

The final audit reported that facts labeled `historical` by the code producer were changed to `current_snapshot`, and that classification omitted original fact IDs. The latter also exposes a contract mismatch: the classification draft schema does not retain an `id` field, while the auditor expected it. The ID finding is an audit/schema mismatch and does not by itself establish semantic information loss. The temporal interpretation of an ordinary frozen current-code snapshot also needs clarification between the producer and classifier. These are recorded follow-up findings, not accepted documentation content.

The deepest completed graph is run `d`. The latest run with the provenance correction is `e`. Successful stages across different runs must not be combined into a claim of a successful end-to-end release. Human readability review and final source-to-document acceptance were not reached.

## Corrections implemented and verified

- Strict Codex output schemas recursively prohibit additional object properties and require declared fields, including nested fact and relation definitions.
- SDK request, response and cache events retain provider/model identity, elapsed time, usage, actual session/request IDs and accounting references. Diagnostics redact the configured credential.
- Source inventory can repair invalid quotes with the original blocks, the rejected draft and concrete validation feedback, within the existing repair bound. Exact original-text matching remains mandatory.
- Document analysis provenance is assigned by the application from the actual producer, prompt version and input hash. Model-supplied provenance IDs and review claims are replaced before verification; accepted provenance survives downstream evidence publication.
- A reusable live runner and repository-relative nonsecret configuration were saved alongside this report.

Six focused regressions cover exact-quote repair and exhaustion, strict nested SDK schemas, secret redaction, usage/cache events and invented document provenance. The related restart/integration subset passed 11 tests. The coordinator performs the combined repository validation.

## Accounting

Usage-priced completed requests total **PLN 5.615624** for this validation. This is a calculation from returned token usage and the verified pricing configuration, not an invoice.

A separate **PLN 20.496862** remains conservatively recorded as uncertain: PLN 20 for the rejected Codex schema request and PLN 0.496862 for the truncated Gemini classification. These reserved amounts are not measured provider charges. No outstanding reservation remains for these evaluation run IDs, and no historical ledger row was edited to make the totals look smaller.

Current pricing was checked against [OpenAI model pricing](https://developers.openai.com/api/docs/models/gpt-6-astra) and [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing). The local verified USD/PLN rate was dated 2026-10-08. Structured run totals and exact audit findings are in [results.json](results.json).

## Inspection and reproduction

Each run directory under `.docgen/codex-live-validation/runs/<run-id>` contains `live-result.json`, events and stage artifacts. The shared workspace contains content-addressed source bytes and `checkpoints.sqlite`; exact checkpoint IDs are retained in each `live-result.json` and in `results.json`. The runtime files remain at the primary repository root, independently of the temporary implementation worktree.

From the repository root, use the existing nonsecret `.docgen/codex-live-settings/run.json` or adapt [configuration.example.json](configuration.example.json). Its paths now target the primary repository. The scope and provider-pricing files are stored under `.docgen/codex-live-settings`; refresh their dated pricing before a future run. Credentials are read from the repository `.env` and are not included in these artifacts.

```powershell
$env:PYTHONPATH = 'src'
.venv/Scripts/python.exe evaluation/codex-live/run.py --env-file .env --configuration .docgen/codex-live-settings/run.json --thread-id codex-risk-live-new
```

Use a new thread ID after a source, implementation or configuration change. Existing interrupted checkpoints belong to their recorded runtime signature and remain available for historical inspection.
