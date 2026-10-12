# Task III Development Plan for Code Analysis

Plan for agent III. Agent IV works on [documentation generation](development-plan-task-4-documentation.md) in parallel. Task III delivers verifiable information about application behavior, its classification, and interchangeable Codex SDK and Auggie SDK integrations. Documentation uses a single evidence contract regardless of the analysis provider.

Baseline inspected on 2026-10-12: the active `src/docgen_graph` package, HEAD `7a7dd7c1b2d6f759fe13c0de4eb00924d752aa3b`, including current working changes. This is an implementation plan, not a report of completed changes. Before implementation, check for differences from this baseline again; do not rebuild solutions that have since been implemented.

## 1. Existing capabilities and confirmed gaps

| Area | State in the active code | Implication for this task |
| --- | --- | --- |
| Source snapshots | `ingestion.snapshot_inputs` stores bytes, hashes, paths, and the code commit and dirty flag. | Extend the existing mechanism with analysis scope and change history. Do not create a second source store. |
| Code analysis and verification | `workflow.analyze_code_unit` and `verify_code_unit` call Gemini, validate evidence IDs, and perform a separate semantic audit. | Retain the independent audit and replace candidate discovery with an interchangeable backend. |
| Languages | `code_spans` uses an AST for Python and text partitioning for other selected files. `CODE_SUFFIXES` **contains neither `.java` nor `.xml`**. | Java is omitted during file selection. The README claim about generic Java analysis does not match this filter. Add a file-selection regression test, not just a better prompt. |
| Views and rules | The prompt requires behavior, conditions, exceptions, and configuration. Structural view–action–API–rule links and dependency discovery across units are missing. | Introduce an entry-point inventory and trace evidence across files. |
| Provenance | The graph stores `kind`, `source_role`, line ranges, evidence IDs, and file hashes. | Extend existing provenance; there is currently no explicit taxonomy for GUI and product features. |
| Classification and information value | `AssertionDraft` and `normalized_assertion` have no categories or relevance assessment. The normalizer copies a fixed set of fields. | Merely adding fields to the model response would lose them before graph storage. Change the contract, normalization, storage, and retrieval together. |
| Patches and tickets | Recording the current commit is not diff analysis. The pipeline has no ticket-based selection. The fixture includes history and a ticket map. | Current-tree analysis is the baseline; explicitly selected history provides an additional evidence type. |
| Providers | `GeminiModel.call` is the only model integration. There are no Codex/Auggie adapters or contracts for their results. | Add two actual SDK adapters alongside the existing Gemini backend. |
| Completeness | Missing spans are detected, but one assertion from a large passage can satisfy the ID check. | Also measure behavior discovery and qualifier preservation; task IV provides a semantic source-coverage audit. |

Basis: [ingestion.py](../src/docgen_graph/ingestion.py), [contracts.py](../src/docgen_graph/contracts.py), [knowledge.py](../src/docgen_graph/knowledge.py), [workflow.py](../src/docgen_graph/workflow.py), [model.py](../src/docgen_graph/model.py), [README](../README.md). Treat the user's observations as hypotheses to verify, not as proof of a defect in a particular run.

## 2. Task outcome and limits of interpretation

Analysis must identify important views, user actions, control visibility and availability, validations, conditions and exceptions, product settings, feature flags, data flows, error handling, integrations, and the effects of specified changes. Every result must lead to a frozen implementation passage or another explicitly identified source.

In this plan, “patches” means Git changes or supplied diff/patch files. It does not mean modifying the repository being analyzed. Missing history does not block current-tree analysis; it blocks claims that require comparing versions.

Static analysis does not establish deployment, active environment configuration, or feature availability for a particular customer. A test describes an expectation, a comment or ticket may describe intent, and a deleted diff line describes historical state. Conflicts between documentation and implementation remain visible; there is no automatic “code always wins” rule.

Information value determines work priority and prominence in documentation. It must not remove a potentially relevant fact from mandatory coverage.

## 3. Model and cost policy

In response to a clarification question, the user chose to propose an exception for code analysis through Codex/Auggie while keeping everything else on Gemini. Proposed wording for `AGENTS.md`, to be implemented by agent III as part of this task:

> Use the Gemini API with gemini-3.8-flash for document extraction, documentation planning, writing, editing, and evidence audits. Codex SDK and Auggie SDK may use explicitly configured provider models solely for read-only code discovery and analysis. Preserve the actual provider and model in provenance. Reject a different GEMINI_MODEL value; never silently substitute a provider or model.

The exception also covers the `search_code` tool invoked by the generator when its sole purpose is code analysis. It does not cover documentation writing, publication audits, or automatic conflict resolution. An SDK result is a candidate; evidence acceptance still requires the shared validators and a Gemini audit.

The current [Codex SDK documentation](https://learn.chatgpt.com/docs/codex-sdk) describes official Python and TypeScript libraries and read-only mode. Prefer Python in this repository; do not assume a Node bridge is necessary. The [Auggie Python SDK](https://docs.augmentcode.com/cli/sdk-python) provides workspace, model, and limit configuration, structured results, and events. Before implementation, pin verified SDK and CLI versions and check model availability and permissions for the actual account. Do not assume either SDK is merely a free search interface.

Reading the shared ledger during planning showed PLN 445.4719064244 charged and PLN 1.62453494619 reserved against a PLN 200 limit. There is currently no available budget for new paid Gemini trials. Do not reset the ledger or restore the historical PLN 1000 limit from older reports. Continue implementation and offline tests; paid tests require new budget authorization. Account for Codex/Auggie costs explicitly according to the actual subscription or allowance; the model exception grants no new budget. Do not route calls to another provider to bypass the Gemini limit.

## 4. Division of work between agents

This table defines shared ownership for both plans. A file's owner also makes small changes needed by the other agent. The other agent supplies the requirement and contract test case instead of editing the same file.

| Owner | Existing files and proposed modules | Responsibility |
| --- | --- | --- |
| III | `ingestion.py`, `knowledge.py`, `contracts.py`, `config.py`, `budget.py`, `storage.py` | Shared contracts, normalization, graph storage/retrieval, snapshots, configuration, and accounting. |
| III | `code_analysis/`, `evidence_contracts.py`, `evidence_service.py`, `analyze_code*` and `verify_code*` prompts | Adapters, code classification, change history, and evidence service. |
| III | `pyproject.toml`, `uv.lock`, `.env.example`, `AGENTS.md` | Sole author of dependency and configuration changes, including those needed by task IV. |
| III | `tests/test_code_analysis*.py`, `tests/test_evidence_contract*.py`, `tests/test_configuration_and_budget.py`, `tests/test_evidence_and_retrieval.py`, `evaluation/task3/`, `tests/fixtures/task3/` | Evidence-producer contracts and regression tests. |
| IV | `workflow.py`, `stages.py`, `cli.py`, `model.py`, `quality.py`, `source_links.py`, `assets.py`, `README.md` | Integration of the entire pipeline, the Gemini model, generation, export, and user interaction. |
| IV | `authoring/`, `source_coverage.py`, `attachments.py`, `documentation_contracts.py`, remaining prompts | Semantic source coverage, authoring tools, templates, editing, and attachments. |
| IV | Remaining existing tests, new `tests/test_authoring*.py`, `tests/test_source_coverage*.py`, `tests/test_template_numbering.py`, `tests/test_attachments.py`, `tests/test_task34_integration.py`, `evaluation/task4/` | Consumer regression tests and shared integration. |
| Unchanged in both tasks | Published fixtures `data/test_data_2*`, `data/investment_platform*`, their generators, and historical evaluation results | Use as inputs and an oracle. Add new cases separately; do not adjust existing expectations to match implementation output. |

Agent III prepares stage functions in `code_analysis/stages.py` and their registration specification. Agent IV connects each stage as a separate LangGraph node and is the sole editor of `workflow.py` and `stages.py`. Do not run all analysis and verification in one function that loses intermediate checkpoints.

Shared starting point C0: agent III publishes a small commit with the contracts, a compatible `EvidenceService` test double, and serialization examples. Agent IV can immediately work on the template, editing, and tests against the current graph, then connect the test double after C0. III then develops the producer while IV develops the consumer in parallel. Integration does not wait for access to paid SDKs.

Work in separate branches/worktrees from a shared, agreed working state; preserve the user's existing changes. Use separate `thread_id` values, run directories, and test graph databases. There must still be a single shared cost ledger across both worktrees; pass its canonical path through `.env`.

## 5. C0 contract delivered to agent IV

This section contains the normative contract referenced by plan IV. Agent III implements it in Pydantic and JSON fixtures. New fields must survive normalization and SQLite retrieval. New contract records have their own `schema_version`; do not globally change all historical v1 records.

### 5.1 Records

| Record | Required field semantics |
| --- | --- |
| `EvidenceRef` | `id`, `source_kind` (`code`, `document`, `attachment`, `patch`, `reviewer`), `snapshot_id`, `path`, `content_hash`, `locator`, `source_role`. The locator is typed: lines/characters, page, table/cell, sheet/range, or diff hunk. |
| `AnalysisProvenance` | `provider`, `model`, `sdk_version`, `session_id`, `request_id`, `prompt_version`, `input_hash`, `scope_id`, optional `commit`, `base_commit`, `head_commit`; also record the deterministic method when no model was used. |
| `FactRecord` | Existing statement, subject, predicate, scope, modality, conditions, exceptions, and evidence IDs; additionally `categories`, `classification_reason`, `relevance`, `relevance_reason`, `support_status`, `temporal_status`, `provenance_ids`, `review_status`. |
| `SourceCoverageItem` | `id`, `evidence_ids`, `unit_locator`, `aspect`, `disposition`, `fact_ids`, `duplicate_of`, `reason`, `decision_ref`. One block may contain multiple aspects and qualifiers. |
| `EvidenceQuery` | `snapshot_id`, `graph_revision`, `scope_id`, `query`, `mandatory_ids`, `filters`, `cursor`, `limit`. Revisions are binding; no result does not prove that a feature does not exist. |
| `EvidenceResult` | `status` (`ok`, `not_found`, `unavailable`, `unsupported`, `budget_blocked`), `facts`, `evidence`, `relations`, `conflicts`, `provenance`, `next_cursor`, `truncated`, `warnings`, `usage_ref`. An error is not an empty success. |
| `KnowledgeDelta` | New or changed facts, evidence, conflicts, and coverage with `base_revision`, provenance, and a verification result. Acceptance creates a new graph revision; it never modifies the old one in place. |

`categories` is a nonempty list drawn from `GUI`, `PRODUCT_CONFIGURATION`, `PRODUCT_FEATURE`, `IMPLEMENTATION_FEATURE`, `UNKNOWN`. Categories may overlap. For example, a button visible only when a flag is enabled requires both `GUI` and `PRODUCT_CONFIGURATION`. Do not equate category with source type: a document can also describe GUI behavior.

`relevance`: `essential`, `supporting`, `context`, `unknown`; the assessment requires a reason and an audience scope. `support_status`: `direct`, `inferred`, `unresolved`. `temporal_status`: `current_snapshot`, `historical`, `planned`, `unknown`. These are independent dimensions: important information may be unconfirmed, while a directly supported detail may have little relevance to the main narrative. Do not use an arbitrary confidence percentage as permission to publish.

Each `relation` has a type, source and target IDs, a method, and its own evidence IDs. The presence of two endpoints does not prove a transition between them. Comments, tests, configuration declarations, and implementation retain distinct `source_role` values.

`SourceCoverageItem.disposition`: `represented`, `duplicate`, `excluded_non_substantive`, `unresolved`. Do not relabel a substantive omission as boilerplate. Excluding material from the document's scope requires a separate, versioned decision and remains visible in the report.

### 5.2 Operations and compatibility rules

`EvidenceService` exposes `search_code`, `search_sources`, `search_graph`, `read_evidence`, `iter_coverage`, `verify_references`, and `apply_verified_delta`. Search operates on an explicit revision; `iter_coverage` traverses the complete inventory with a cursor. Search limits do not restrict mandatory information. Split large complete sets into packets with visible continuation state.

`search_code` may use the selected adapter and return candidates; it does not store them as accepted facts. `apply_verified_delta` accepts only the output of a separate verification stage and is idempotent. Task IV supplies document extraction, coverage auditing, and attachment reading logic; agent III stores their outputs using the same contract.

C0 must include four packets: no code, a complete result with a qualifier and a conflict, a paginated result, and an unavailable backend. The test double uses real fixture files and verifiable locators. A shared test requires records to round-trip without metadata loss.

Old graphs remain readable. On import, a missing category means `UNKNOWN`, and a missing coverage audit means `unresolved`, not full compliance. New schemas, the adapter, model, selected scope, prompts, and parser versions contribute to hashes and the runtime signature. Changing providers requires a new revision/run, not an implicit resume of an old checkpoint.

## 6. Implementation stages for agent III

### III0 Establish the baseline and deliver C0

- Confirm active files, working changes, environment versions, and available budget. Do not rely solely on historical reports.
- Deliver C0 contracts, a test double, and a serialization test. Include the hooks needed by agent IV and proposed configuration parameters.
- Assign one owner to each missing dependency. The current quality and retrieval test attempt stopped at the `PIL` and `defusedxml` imports; first restore the environment from the lockfile. Do not declare a passing baseline based on the earlier 91 tests.

Acceptance: IV can implement a contract consumer without importing a specific SDK.

### III1 Complete inventory and controlled code scope

- Add support for `.java`, `.xml`, and `.patch`/`.diff`; distinguish configuration and resources from executable implementation. Do not send lockfiles, dependencies, or secrets merely because their extensions are supported.
- Record every selected and omitted file with a reason. Exclusions must not conceal important code. Fix test-role detection for structures such as `tests/`, `src/test/java/`, and `*.spec.ts`.
- For Java/Spring and Angular/TypeScript, build an explicit entry-point index: controllers, services, DTOs, components, templates, routing, visibility conditions, and validations. Use parsers where they provide the required structure; a text fallback must declare its lower analysis capability rather than claim a full AST.
- Link definitions to usages and configuration in bounded context packets. Split long symbols while preserving declarations, enclosing conditions, and dependencies. Do not remove context needed to interpret branches.
- Scope may select an entire snapshot, feature, paths, or tickets. Include dependencies as `supporting` and identify unrelated features as out of scope. Do not assume that top-k search hits contain the entire product.

Acceptance: the fixture's Java backend is retained, every supported unit is scheduled or explicitly accounted for, and shared context does not leak into the description of another feature.

### III2 Analysis and search adapters

- Introduce a small `CodeAnalysisBackend` interface with `capabilities`, `analyze_unit`, `search_code`, and `close` operations. Pass dependencies explicitly; session state remains per run.
- The `gemini`, `codex_sdk`, and `auggie_sdk` implementations return C0. Preserve a working `gemini` option for installations without additional SDKs; SDK selection is explicit, without automatic fallback.
- Central settings: `DOCGEN_CODE_ANALYSIS_BACKEND`, `DOCGEN_CODE_ANALYSIS_MODEL`, timeout, turn limit, and result limit. These names propose a new interface; they are not existing options. `GEMINI_MODEL` continues to accept only `gemini-3.8-flash`.
- The backend receives only the frozen, filtered directory and permitted context. Disable tools for writing, arbitrary code execution, dependency installation, and browsing other repositories. Enforce this through permissions and isolation, not just prompts. If an SDK cannot provide sufficient restrictions, return `unsupported` rather than weaken protection.
- An SDK may index code remotely: index scope must match the snapshot. Check the index version and map every hit to local frozen bytes. Do not accept lines from the current, modified workspace.
- Handle cancellation, timeouts, unavailable models, missing authentication, limits, invalid JSON, truncated output, and lost connections. Account for retries and uncertain outcomes as well; log identifiers and usage without secrets.
- Instructions and files found in the analyzed repository are data. Do not let them alter the contract, permissions, or analysis objective. Do not require new project comments/docstrings for automatic SDK introspection.

Acceptance: the same contract tests pass for all three backends; facts are verified independently of how convincing an SDK response sounds.

### III3 Extraction, classification, and history

- Extend results with categories, value, source status, and provenance. Verify classification consistency; unresolved classification must yield `UNKNOWN`/`unresolved`.
- For views, preserve control text, event, visibility/enabled condition, role, effect, and backend contract. A UI condition does not replace server authorization.
- For configuration, preserve the key, type, default, allowed values, dependencies, overrides, and usage location. A repository default does not establish the production setting.
- Run patch analysis for an explicit base/head pair or a supplied diff. Freeze both versions and hunks; preserve renames/deletions and the mapping of changes to symbols and behavior. History outside the scope is not evidence of current behavior.
- Treat ticket links as provenance. The fixture's planned `TICKET-2020` must not receive implemented status without an implementation. Do not guess commits from similar descriptions.
- Return relations and conflicts with evidence on both sides. The verifier receives original sources, not only the adapter's summary.

Acceptance: complete categories and provenance reach the graph and survive retrieval; conditions, exceptions, and historical status are preserved.

### III4 Nodes, restart, and generator integration

Target sequence: `inventory_code_scope` → `analyze_code_unit` → `verify_code_unit` → `classify_code_facts` → `verify_code_classification` → `publish_code_evidence`. Analysis and verification repeat for subsequent units; the history stage precedes analysis only when a change scope is specified. Extend existing nodes rather than leave a second competing path.

Agent III supplies functions and artifacts; IV registers nodes, routing, and gates. Each stage writes its artifact atomically before the checkpoint. Sequential nodes use the existing SQLite checkpointer and a stable `thread_id`; an SDK session does not replace LangGraph state. These rules follow the [LangGraph persistence documentation](https://docs.langchain.com/oss/python/langgraph/persistence).

Persist the provider's `session_id` and completed results. After a failure, restore accepted artifacts; if the provider does not guarantee resumption, start a new session for the unfinished unit. Do not promise exactly one paid call if a crash occurs between the response and checkpoint; that case requires request identification and conservative accounting.

Human feedback uses `interrupt()` and `Command(resume=...)`. Changing a fact or evidence invalidates dependent mappings and approvals. `manual` retains stage reviews; in `autopilot`, reaching the repair limit does not permit incomplete material to be labeled complete.

## 7. Tests and acceptance criteria

| Suite | Cases and expected result |
| --- | --- |
| Source selection | Java, XML, TS, HTML, SQL, YAML, test files, and diffs are classified correctly; secrets, symlinks, and files outside the root do not reach the provider. Omissions are explicit. |
| Actual behavior | A small Java/Spring + Angular example contains a view, flag, boundary condition, exception, and server check. All annotated facts and qualifiers are discovered; no transitions are invented. |
| Contract | SQLite round-tripping preserves all fields. A category/provenance change changes the revision. Incorrect hashes, foreign revisions, and invented lines are rejected. |
| Backend | Shared tests for both SDKs with recorded or synthetic responses: success, timeout, missing authentication, truncation, invalid results, resumption, and backend changes. No exception triggers a silent fallback. |
| History | The fixture's 5.1 change does not become the current rule after the fix; deleted code remains historical; a planned ticket does not become implemented. |
| Scope | `risk-profiling.json` retains required shared dependencies without adding trading rules. The oracle and ticket map are evaluator inputs, not hidden hints for the analyzer being evaluated. |
| Restart | Failures after saving an SDK result, before a checkpoint, after verification, and during review do not lose results or mix snapshots. |
| Integration with IV | `search_code` supplies support or an explicit absence of support; a new fact is verified and creates a new revision before entering the document. |

Acceptance requires 100% of information and qualifiers on the frozen annotated set, correct locators, no unsupported assertions, and no incorrect conflict resolutions. Every source unit has a disposition. A sample result does not provide a mathematical guarantee of completeness for an arbitrary repository.

Unit and contract tests run offline. Controlled live trials of both SDKs are a separate condition for full integration acceptance, after checking permissions, versions, and funding. If this condition is unmet, report “adapter implemented and tested offline; live behavior unverified” rather than mark the entire task complete.

## 8. Handoff and shared integration

1. C0: contracts, test double, examples, and file ownership; agent IV begins consuming the contract.
2. C1: a frozen producer fixture and working `EvidenceService` reads; IV replaces the test double with the real service.
3. C2: III hands over stage functions, backends, and configuration metadata; IV connects them to a single workflow and CLI.
4. C3: IV runs the integration of both tasks; III fixes producer issues in its owned code. Jointly verify that artifact numbers do not collide and that evidence changes invalidate approval.
5. Deliver the task III report with a backend matrix, test results, limitations, and spending. Do not require working live access before giving agent IV a functioning offline contract.

## 9. Sources and revalidation

- [Baseline provenance and full-coverage rules](development-plan.md).
- [Current pipeline report](development-plan-task-1-implementation-report.md) and [application and history fixture](../data/test_data_2_reference/README.md).
- [Official Codex SDK](https://learn.chatgpt.com/docs/codex-sdk), OpenAI, accessed 2026-10-12.
- [Auggie Python SDK](https://docs.augmentcode.com/cli/sdk-python), Augment, accessed 2026-10-12.
- [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence), LangChain, accessed 2026-10-12.

No paid model calls were made while preparing this plan. The code, reports, and fixtures were inspected, and the ledger was read. The attempt to run `test_documentation_quality.py` and `test_evidence_and_retrieval.py` ended with two collection errors caused by missing dependencies; this is not a confirmed regression in application logic.
