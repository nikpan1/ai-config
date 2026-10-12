# Codex live-flow validation

Date: 2026-10-12. The requested documentation is finished. Generation run `codex-risk-live-20261012-h` produced the verified document; explicit continuation `codex-risk-live-20261012-i` repeated final checks under the corrected audit contract and exported the release. Its status is `complete_with_exclusions`: the five exclusions are frontmatter and structural Markdown headings/table syntax, not business rules.

## Finished artifacts

- [Documentation](../../.docgen/codex-live-validation/runs/codex-risk-live-20261012-i/step22/candidates/8bb760b326054ba08243726a5ff334dbc6b354c722b47e25377153c8eec079c6/documentation/index.md)
- [Coverage report](../../.docgen/codex-live-validation/runs/codex-risk-live-20261012-i/source-coverage.json)
- [Continuation lineage](../../.docgen/codex-live-validation/runs/codex-risk-live-20261012-i/continuation.json)
- [Structured results and accounting](results.json)

Candidate hash: `8bb760b326054ba08243726a5ff334dbc6b354c722b47e25377153c8eec079c6`. Final checkpoint: `1f1c67e6-9cdc-688d-800d-bddaa5f4caf6`. Release approval is explicitly attributed to **Autopilot policy v2**, not a human reviewer. The coordinator records a separate independent reader review.

The final source audit represents **36/36 source aspects**, **20/20 qualifiers**, and **35/35 facts**, and independently checks **22/22 original document blocks**. No unresolved attachment or unsupported assertion was reported. Both original illustrations, a verified Mermaid diagram, and local evidence files are included. All four numbered template sections are retained, with the title “Risk Profiling”. Bundle integrity and image-link checks passed.

Original localhost source URLs remain in some citations. The immutable bundle also contains `evidence/D3.md` through the cited document ranges and `evidence/C9.md`, so the original evidence remains available without a server. In particular, `D13.md`–`D16.md` preserve QF08–QF11, TICKET-2008/2014/2013/2020, current/planned status, uncertainties and the shared table evidence note verbatim, even where those identifiers are absent from the narrative. The code evidence is bounded to the inspected file.

## Inputs and models

- Documentation: `data/test_data_2_quick`, including its two source illustrations.
- Code: `data/investment_platform`, restricted to `backend/src/main/java/example/fixture/RiskProfileService.java`. No claim is made about inspection of other implementation files.
- Template: `evaluation/codex-live/template.md`.
- Code analysis: actual `openai-codex==0.162.1` with matching CLI runtime and explicit `gpt-6-astra`. The isolated runtime receives frozen source context, denies writes, and disables execution/discovery tools. Credentials are not copied into the workspace or report.
- Extraction, classification, planning, writing, editing and independent audits: `gemini-3.8-flash`. No model substitution or Auggie run occurred.
- Final local request allowance: 500,000 conservative UTF-8 bytes plus configured output accounting; output bound: 16,384 tokens. The provider reservation was adjusted to PLN 50 for conservative headroom and settled using actual returned usage.
- Runtime workspace: `.docgen/codex-live-validation`; shared accounting: `.docgen/budget.sqlite`. Existing ledger records were preserved.

## Attempts and corrections

| Run | Observed result |
| --- | --- |
| `a` | Source inventory rejected a quote that removed original Markdown emphasis. Added bounded exact-quote repair. |
| `b` | Codex API rejected a non-strict JSON schema before generation. Added recursive strict object schemas. |
| `probe` | Actual Codex analysis returned 13 facts and 7 relations with provider/model/session/request provenance. |
| `c` | Code verification passed; classification exceeded the original 8,192 output-token bound. |
| `d` | Code and document audits passed; evidence publication rejected model-invented document provenance. Moved document provenance assignment into the application. |
| `e` | Classification audit exposed a fact-ID schema mismatch and inconsistent interpretation of snapshot temporal status. Classification now returns metadata only; the application preserves immutable fact IDs and semantics. |
| `f` | Reached verified writing; accumulated agent evidence exceeded the original local request-size allowance before an API request. |
| `g` | The larger allowance required matching provider reservation headroom. Preflight stopped without a model call. |
| `h` | Produced all four verified and edited sections. One optional-search loop was recovered through a recorded checkpoint fork. The final batch auditor then incorrectly treated valid code/other-batch claims as unsupported because their context was omitted from its payload. |
| `i` | Explicit final-audit/export continuation: both corrected independent batch audits, deterministic final checks, export integrity and policy release passed. |

The earlier missing-ID finding was a classification schema/auditor mismatch, not proof of semantic loss. The temporal disagreement was addressed separately by defining current frozen code as `current_snapshot` and making temporal fields immutable during classification.

The final audit now receives all mappings sharing a selected paragraph, the other cited facts and original evidence supporting that paragraph, full reader text for deduplicated shared notes, and explicit non-substantive inventory candidates. Coverage decisions remain restricted to the current batch's original aspect/fact identities. Missing qualifiers, unsupported rationale and any real audit finding still block release.

Ten focused live-flow regression tests cover exact quotes, schema strictness, redaction, accounting/provenance, immutable classification, complete audit context and blocking genuine omissions. The focused suite plus restart test passed 11 tests; the coordinator verified the combined repository suite separately.

## Checkpoint continuity

Run `h` exhausted its eight-turn optional search allowance after successful evidence reads. A recorded agent review forked checkpoint `1f1c67c5-bd7c-6988-80b1-0678167cea4c` to `1f1c67c9-43f1-6a65-80b2-af0601309deb`, appending explicit readiness feedback while preserving seven already-used turns. Gemini declared readiness on the remaining eighth turn. The turn bound was not reset, and writing/evidence audits were not skipped.

The final audit fix changed runtime identity, so run `h` was not silently rewritten. [continue_final_audit.py](continue_final_audit.py) imported checkpoint `1f1c67d5-7c74-649f-80ec-5aff242ea8c0` into a new run. It verified content-addressed state artifacts, source bytes, SQLite integrity and the copied graph's logical contents. It also checked that the upstream workflow AST was unchanged outside the final-audit method and that the only source-code changes were that method and its prompt. `continuation.json` records both runtime signatures, source/target commits, imported hashes and `actor_type=agent`. Run `h` remains the artifact producer; run `i` contains final validation/export history rather than fabricated upstream stages.

## Accounting and reproduction

Usage-priced completed calls across every listed attempt total **PLN 14.264979**. This is computed from returned usage and verified pricing, not a provider invoice. Separately, **PLN 20.496862** remains conservatively marked uncertain from the original rejected Codex schema request and truncated Gemini response; these reservation amounts are not measured charges. No outstanding reservation remains, and no historical ledger row was changed.

Pricing was verified against [OpenAI model pricing](https://developers.openai.com/api/docs/models/gpt-6-astra) and [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing), with the local verified USD/PLN rate dated 2026-10-08. Refresh dated pricing before a future run.

For a new full run from the primary repository, use the existing nonsecret `.docgen/codex-live-settings/run.json` or adapt [configuration.example.json](configuration.example.json). Credentials are read from `.env`. Runtime artifacts remain in the primary repository independently of the temporary implementation checkout.

```powershell
$env:PYTHONPATH = 'src'
.venv/Scripts/python.exe evaluation/codex-live/run.py --env-file .env --configuration .docgen/codex-live-settings/run.json --thread-id codex-risk-live-new
```

Use a new thread ID after implementation, source or configuration changes. The restricted historical continuation utility deliberately rejects unrelated upstream changes; ordinary future runs should start with a new thread rather than alter old runtime signatures.
