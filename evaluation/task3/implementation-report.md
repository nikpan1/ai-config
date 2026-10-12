# Task III implementation report

The producer now preserves classified facts, qualifiers, source roles, actual model provenance, evidence-backed relations and explicit coverage state. Documentation consumes a revision-bound evidence service. Source bytes and locators are checked against the immutable snapshot manifest, and accepted deltas create new content-addressed revisions rather than modifying existing revisions.

## Delivered behavior

- Java, XML, properties and patch files are selected; tests, configuration declarations and implementation have distinct roles. Secrets and dependency lockfiles are omitted. Java/Spring and Angular entry points use an explicitly named text index, not a claimed compiler AST.
- Full, path, feature and ticket scopes select primary and supporting files. Restricted feature/ticket scopes require explicit path mappings; an unmapped ticket cannot establish implementation. Import dependencies are bounded context, and omitted context IDs remain visible. Every selected source unit is scheduled independently.
- Explicit Git base/head selection freezes both versions and the patch, including deleted and renamed files. Historical units remain historical. Supplied patches reject paths outside the selected repository and symlinks.
- Analysis, independent evidence verification, classification, independent classification verification and publication are separate stage functions. The documentation agent registers them in the existing persistent LangGraph. A restart regression closes and reopens SQLite between verification attempts and proves completed model stages are not repeated.
- Categories and relevance survive normalization and SQLite reads. Relevance does not remove coverage obligations. Unknown categories remain unresolved. Historical evidence cannot become current implementation through classification.
- The evidence service validates snapshot/revision/scope bindings, supports explicit pagination, preserves mandatory qualifier/conflict closure and reports missing mandatory IDs. It validates frozen source hashes and exact locators before publishing. Old graphs receive UNKNOWN categories and unresolved source coverage.
- Task IV attachment parsing is integrated into source freezing and inventory. Original bytes, typed locators and parser limitations survive evidence normalization.

## Provider matrix

| Provider | Implementation | Offline validation | Live status |
| --- | --- | --- | --- |
| Gemini | Existing `gemini-3.8-flash` calls behind the common backend; all evidence audits and documentation remain Gemini | Candidate contract and complete six-stage restart verified with synthetic responses | No new paid calls |
| Codex SDK | `openai-codex==0.162.1`, with its pinned `openai-codex-cli-bin==0.162.1`; isolated subprocess, empty runtime workspace, frozen context supplied in the request, explicit model and API key, restrictive permission profile, disabled tools and inherited skills | Actual pinned runtime initialization and effective configuration read verified without a model call; synthetic success/error/budget/cache/relation tests pass | Adapter implemented and tested offline; model/account behavior unverified |
| Auggie SDK | `auggie-sdk==0.2.2` real transport, injectable verified external isolation; explicit model, bounded retries and tool permissions | Shared synthetic backend contract tests pass; installed SDK source inspected | Native mode returns `unsupported`; safe host isolation and a funded live trial remain required |

The published Auggie CLI was `@augmentcode/auggie@0.36.0` when checked on 2026-10-12. It is not installed or implicitly updated by this application. The inspected SDK's ACP permission handler automatically approves requests, including indexing, and its actual constructor lacks the documentation's `allow_indexing` parameter. Exact tool removal flags do not establish a complete deny-all policy for dynamic tools. Native execution therefore fails closed rather than presenting a permissive process as isolated. An external transport must establish its own pinned CLI, denied writes/commands/outside reads and bounded execution before reporting capability `ok`.

## Configuration

`DOCGEN_CODE_ANALYSIS_BACKEND` accepts `gemini`, `codex_sdk`, or `auggie_sdk`; there is no fallback. Non-Gemini selections require `DOCGEN_CODE_ANALYSIS_MODEL`. `.env.example` includes timeout, turn and output limits, `OPENAI_API_KEY`, `AUGGIE_API_KEY`, a scope file and a provider allowance file. Secret fields do not appear in settings representations.

A scope file can contain:

```json
{
  "mode": "feature",
  "feature": "risk-profiling",
  "paths": ["backend/**/risk/**", "frontend/**/risk/**"],
  "supporting_paths": ["backend/**/authorization/**"],
  "excluded_paths": ["**/trading/**"],
  "context_chars": 24000
}
```

Ticket scopes use `tickets`, `dependency_tickets` and `ticket_paths` containing user-supplied path mappings. Evaluator expected behavior and status are not model inputs. A provider allowance must identify the provider, model, authorization reference, currently verified pricing and exchange rate, and a conservative reservation. It uses the existing shared ledger; runtime limits are optional configuration.

## Verification and limits

The producer/configuration/retrieval/adapter/restart suites plus coordinator transport review tests passed offline: 40 tests after the final supporting-context regression. Ruff passed for the owned implementation and tests. The coordinator runs the combined full suite after merging task IV.

Final integrated validation passed 143/143 tests at the repository root. Two subsequently added Mermaid-tool regressions also pass, bringing the verified distinct cases to 145; all 12 coordinator review tests passed after that correction. Ruff passed across the implementation and tests, and the final wheel built successfully. Candidate provenance now binds current/base/head commit identifiers when available, while snapshots without Git metadata remain supported.

No paid Gemini, Codex or Auggie analysis call was made. The existing accounting ledger was preserved. Live provider trials and semantic acceptance against the full frozen human-reviewed reference set are not claimed. The Java/TypeScript text index and explicit import matching are bounded static discovery mechanisms; unresolved dynamic behavior remains a coverage issue for the independent audit.

## Revalidated primary references

- [Codex SDK](https://learn.chatgpt.com/docs/codex-sdk), including the installed Python SDK source and package metadata.
- [Codex permissions](https://learn.chatgpt.com/docs/permissions) and [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).
- [Auggie Python SDK](https://docs.augmentcode.com/cli/sdk-python), [tool permissions](https://docs.augmentcode.com/cli/permissions), and [CLI flags](https://docs.augmentcode.com/cli/reference). Installed SDK behavior takes precedence over stale examples.
