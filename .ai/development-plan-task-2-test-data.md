# Development plan for investment platform test fixtures

Date: 2026-10-12

Status: ready for implementation by Agent B. This plan defines fixture generation; it does not generate the application or documents. Repository baseline: `6ec439b756ccd9dfa61333d17505412159ff2afe`.

Create a realistic synthetic investment-platform repository with Java, Angular, PostgreSQL and MongoDB, actual ticket-bearing Git history, three substantial source pages about risk profiling with HTML mirrors and JPEG mockups, and one short page for fast documentation-pipeline tests.

Work in parallel with Agent A following the [pipeline repair plan](development-plan-task-1-pipeline.md). Fixture generation must not depend on that agent's CLI or package migration.

## 1. Existing assets and scope boundaries

`data/test_data_1` is a furniture-commerce corpus with four Markdown pages, 60 scenario rows per page, HTML mirrors and SVG mockups. Measured Unicode character counts on 2026-10-12 are 77,205, 78,251, 77,467 and 82,370. Its generator already provides deterministic records, metadata and corresponding HTML; reuse the approach, not its domain prose or SVG assets. Leave that fixture unchanged because existing pipeline tests depend on it.

The new corpus must match the existing fixture's complexity per page while respecting the requested three-page structure. It should contain meaningful conditions, exceptions, versions, cross-references and irrelevant material, rather than expanding a few rules with repeated filler. The quick fixture is separately sized and isolated so a docs-only run cannot accidentally ingest the full corpus.

The application is a local synthetic test project, not a production investment service. Risk scores, thresholds, clients and external providers are invented. Do not claim regulatory approval, investment suitability or production security. All documentation, UI, ticket titles, source identifiers and tests use English.

Current pipeline capabilities are separate from fixture quality: `.java` is not selected by current ingestion, non-Python adapters provide only generic text structure, HTML is not a production source adapter, and ticket filtering is not implemented. This task prepares inputs for future code analysis; it must not claim that the present pipeline can already trace Java call graphs or limit analysis by tickets. Agent B does not modify ingestion to hide these limitations.

## 2. Ownership and deliverables

Agent B owns only the new paths below, `scripts/test_data_2/`, this plan, and its implementation report. Agent A owns production code/tests, root packaging and configuration, the root README, and integration tests. Do not share fixture-generator implementation with `docgen_graph` or require a specific location of that package.

```text
data/
  investment_platform/
    README.md
    backend/
    frontend/
    database/postgres/
    database/mongo/
    mocks/
    compose.yaml
  investment_platform_history/
    investment-platform.bundle
    manifest.json
  test_data_2/
    01-dictionaries.md
    02-external-services.md
    03-risk-profiling.md
    assets/*.jpg
  test_data_2_html/
    index.html
    01-dictionaries.html
    02-external-services.html
    03-risk-profiling.html
    attachments/*.jpg
  test_data_2_quick/
    risk-profiling.md
    assets/*.jpg
  test_data_2_quick_html/
    index.html
    risk-profiling.html
    attachments/*.jpg
  test_data_2_reference/
    README.md
    manifest.json
    citation-cases.jsonl
    expected-facts.jsonl
    discrepancies.jsonl
    ticket-map.json
    scopes/
      risk-profiling.json
      unrelated-trading.json
scripts/test_data_2/
  records/
  build_fixture.py
  build_history.py
  validate_fixture.py
  tests/
```

Keep README files, expected results, templates and manifests outside the selected Markdown source directories unless explicitly shown above. `data/test_data_2/` must contain exactly three source pages, and `data/test_data_2_quick/` exactly one; auxiliary Markdown would otherwise become unintended pipeline evidence.

Commit the inspectable source snapshot and portable history bundle, not a nested `.git` directory. Build and clone temporary repositories under an ignored, dedicated location such as `.docgen/fixtures/`. Never create application-history commits in the enclosing `doc-gen` repository. No remote publication is required.

The input contract is version 1 from [the companion plan](development-plan-task-1-pipeline.md#frozen-fixture-interface-version-1). Freeze it before implementation. Agent B publishes a tiny representative record and a citation case first; both agents can continue independently. Changes to paths/fields after that point require an explicit version change and coordination, not unilateral edits in the other agent's files.

## 3. Synthetic platform design

Use a coherent, locally runnable reference slice. Choose mutually compatible supported toolchain versions during implementation, record the exact versions, and commit wrappers/lockfiles. Avoid floating `latest` dependencies and production infrastructure requirements. Keep credentials local placeholders in `.env.example`; do not commit real secrets or customer data.

| Component | Required responsibility |
| --- | --- |
| Java backend | REST endpoints, explicit domain services, validation, persistence adapters, external-provider clients and error mapping. A conventional Spring Boot structure is suitable; keep the implementation small enough to inspect. |
| Angular frontend | A questionnaire journey, draft recovery, consent, validation, result display and profile history; small unrelated quote/trading views establish wider platform context. |
| PostgreSQL | Investor references, versioned dictionaries, profile summary/status, questionnaire-version references and any explicit idempotency/transaction records. Versioned migrations and synthetic seed data are required. |
| MongoDB | Questionnaire answer snapshots and external risk-assessment request/response audit documents with correlation and questionnaire-version fields. Include collection/index setup and realistic examples. |
| Local infrastructure | Reproducible Compose setup for databases and deterministic provider stubs. No real market, custody or risk API is called during tests. |

Avoid two stores containing contradictory authoritative copies of the same mutable field. Document which record is authoritative, how it references the other store, and what happens if the second write fails. Do not imply a distributed transaction that the fixture does not implement. Any retry/reconciliation behavior asserted in the documentation must have corresponding implementation and tests, or an explicit planned status.

### Exactly three external business services

| Fictional service | Platform use | Risk-profiling dependency |
| --- | --- | --- |
| `RiskSignal` | Evaluate a submitted questionnaire against a named scoring/rules version and return a proposed risk band and reason codes. | The only external business service called by risk profiling. |
| `MarketPulse` | Quotes, instrument reference data and market-session status for browsing/trading. | None. Its similarly named instrument-risk fields do not describe an investor's risk profile. |
| `CustodyBridge` | Cash balance, order settlement and custody status for the trading lifecycle. | None. Profile assessment does not reserve funds or place an order. |

Local databases and infrastructure are not additional external business providers. Keep provider names fictional and URLs local or clearly reserved examples. The risk workflow's integration tests must prove that `MarketPulse` and `CustodyBridge` receive no calls.

### Risk-profile feature slice

Implement a consistent core journey: start or reopen a draft, select a questionnaire version, collect answers and consent, validate completeness, submit idempotently, call `RiskSignal`, persist the assessment, display the result and its provenance, and retain prior profile history. Model timeout/unavailability, duplicate submission, validation failure, outdated questionnaires, incomplete provider responses, and expiry/reassessment as distinct supported outcomes.

Use explicit synthetic rules and boundaries for experience, horizon, loss tolerance, liquidity need and risk bands. Store thresholds in versioned configuration/dictionaries rather than scattering them across prose, SQL and UI. Explain whether an assessment replaces a previous active profile and what happens during failure; freeze one consistent policy across code and current documentation.

Include enough unrelated platform code to make later ticket selection meaningful: quote browsing, a small order lifecycle and a custody integration. These modules should share a few real DTOs/configuration files with risk profiling, so a future analyzer must distinguish ticket changes from whole-file ownership. Avoid a large unrelated application that adds setup burden without test value.

## 4. Real Git history and ticket traceability

Use an isolated application repository with a synthetic author identity, fixed time zone, deterministic timestamps, line endings, commit ordering and source records. Every commit, including the initial commit, has a subject beginning with `TICKET-XXXX`, where the suffix is four digits. No empty commits created only to increase the count.

Reserve a coherent namespace:

| Ticket family | Meaning |
| --- | --- |
| `TICKET-1000` | Platform foundation and local setup. |
| `TICKET-1001` onward | Shared dictionaries, persistence and infrastructure dependencies. |
| `TICKET-2000` | Risk-profiling epic; its stories reference this parent. |
| `TICKET-2001` through `TICKET-2024` | Risk-profiling stories, fixes and explicitly planned follow-ups. |
| `TICKET-3001` onward | Unrelated market and trading work. |

Create at least 18 meaningful commits: at least 10 for implemented risk stories/fixes and at least 4 unrelated feature commits, with foundation/shared work making up the remainder. Interleave unrelated work with risk work. At least one ticket has multiple commits, and one later risk fix changes a rule/edge case introduced earlier. A planned story has no fake implementation commit. Each completed core story has implementation and test evidence.

`ticket-map.json` maps epic/story IDs to scope, status, prerequisites, one or more actual commit SHAs, changed paths, tests, source-page sections and expected behavior. `scopes/risk-profiling.json` supplies a future ticket-selection input with `schema_version`, `fixture_revision`, `feature`, `tickets`, `dependency_tickets`, and `excluded_tickets`. Include a second selection for unrelated trading so later scope tests have a negative control. This is fixture data, not a request to add a production `--tickets` flag now.

Build each commit from meaningful incremental changes rather than recreating the same final snapshot repeatedly. Record the final branch/ref and tree hash. Export `investment-platform.bundle`; verify it, clone it into a new directory, inspect the commit subjects and compare the cloned HEAD source tree with `data/investment_platform/` using a file/hash inventory with only explicitly declared packaging exclusions.

The committed bundle and the readable source snapshot must agree. Rebuilding twice with fixed inputs should produce the same commit IDs and HEAD tree. Do not require byte-identical Git pack compression across different Git versions; verify logical history and content identity instead. Keep binaries limited to required wrapper assets, if used; do not place dependencies, build outputs or database volumes in Git history.

## 5. Three substantial source pages

Target 70,000–90,000 Unicode characters per source page, approximately 210,000–270,000 total across three pages. Use roughly 50–70 distinct dictionary/version, contract/scenario, or story/acceptance records per page. Character count is a size check, not a quality score: repetition does not count as new coverage. Report actual counts by page and substantive record type.

### Page 1: Dictionaries and shared rules

Describe general dictionaries affecting platform behavior: investor/account status, experience level, investment horizon, loss-tolerance range, liquidity need, risk band, assessment/profile status, questionnaire version, consent type, currency, instrument category and order state.

For each relevant dictionary, give stable codes, display labels, business meaning, allowed transitions or mappings, applicability, version/effective date, invalid/retired values, ownership and consumers. Include boundary examples and cross-references to the risk epic. Explicitly distinguish investor risk, instrument risk and operational risk; similar names must not become the same entity.

Include dictionaries unrelated to risk profiling to test later scope selection. Retain at least one historical version next to the current definition, visibly marked as historical. Do not put provider secrets, implied regulatory rules or undocumented scoring logic into generic descriptions.

### Page 2: External service catalog

Describe exactly `RiskSignal`, `MarketPulse` and `CustodyBridge`, covering purpose, consumers, operations, request/response fields, error conditions, timeout/retry semantics, idempotency where actually used, local configuration, correlation IDs and failure ownership.

Give the two unrelated services enough genuine detail to be plausible distractors. Make the sole risk-profiling dependency explicit in both prose and a dependency table. Include sample contracts, field-level constraints and meaningful failure scenarios. Keep examples consistent with local mocks and client implementations.

For `RiskSignal`, distinguish a provider's proposed band from the platform's accepted/persisted profile and explain versioning and failed responses. If an old timeout or field definition is retained for a discrepancy test, label it with its revision and expected applicability; do not accidentally publish two unlabelled current truths.

### Page 3: Risk epic and implementation stories

Describe `TICKET-2000`, goals, actors, scope, non-goals, dependencies, state transitions and a coherent end-to-end journey. Use story tables comparable in richness to `test_data_1`, with ticket, user story, product behavior, implementation behavior, acceptance criteria, exceptions, status/version and mockup/caption references.

Cover draft creation, questionnaire version selection, answer validation, consent, saving/reopening, submission/idempotency, provider assessment, result persistence, result explanation, history, expiry/reassessment and error recovery. Include limits and negative cases adjacent to their rules. Clearly identify current implementation, historical behavior and planned follow-ups; planned work does not acquire an implementation SHA.

Cross-link dictionary entries and the `RiskSignal` contract. Include at least one intentionally versioned code/document discrepancy for future cross-source tests, plus at least one unresolved product ambiguity requiring a recorded exclusion or review decision. Isolate these cases in the reference annotations and distinguish intentional uncertainty from a generator mistake.

## 6. HTML mirrors, JPEG mockups and citation cases

Generate Markdown and HTML from the same structured content records. Each Markdown page has `source_url`, `source_system`, `source_id`, and `source_revision`. Serve the full mirror on `127.0.0.1:8766` and the quick mirror on `127.0.0.1:8767` by default; provide builder overrides and document server commands in `test_data_2_reference/README.md`.

All delivered documentation images must be actual JPEG bytes with a `.jpg` extension: no SVG, PNG, WebP, embedded SVG, data-URI vector drawings, or renamed non-JPEG files. Existing `test_data_1` SVGs remain untouched. Inspect decoded image format and readability, not just extensions.

Produce at least six distinct application mockups: dictionary administration, integration status, questionnaire, answer validation, assessment result and profile history. At least two risk screens appear in page 3; all three source pages have appropriate visual context. Provide useful visible captions/behavior descriptions, and keep every required business rule in text rather than only inside pixels.

Prefer reproducible rendering of fixture-owned HTML/CSS screens to JPEG using an available browser renderer and a fixed viewport/font setup. These are local mockup artifacts, not a hosted website. They can be built independently of the finished Angular journey; record that they are mockups. For AI-created bitmap visuals, use the image generation skill, but AI imagery is unnecessary for deterministic application screens. Record image hashes and generation settings.

Deliberately model a Confluence-to-Markdown asset transformation: for example, HTML uses `attachments/8421/risk-questionnaire-v3.jpg`, while Markdown uses `assets/risk-questionnaire.jpg`. Bytes may be identical, but paths and image markup differ. All assets must resolve independently in their own package. The visible factual prose must still agree.

Include at least 24 annotated citation cases across the full corpus:

- At least six claims supported by a specific solution/acceptance cell rather than its generic story cell.
- Repeated story openings, repeated risk terms and identical sentences in different scopes requiring disambiguation.
- Short, unique evidence phrases and a rule shorter than 30 characters, so the previous length heuristic can fail visibly.
- Unicode names/characters, HTML entities, nonbreaking spaces, punctuation and inline formatting with preserved visible wording.
- Inline images, reference-style images, linked images and HTML `<img>` forms. Include an image-only source block that cannot support a text citation.
- A meaningful visible caption that is distinct from alternative text and attachment names.
- A deliberately absent/changed destination phrase in an isolated negative case, requiring local evidence fallback rather than a false positive.
- An exact duplicate and a scoped variant, so information accounting cannot treat the latter as redundant.

Use the version-1 case fields from the companion plan and include `forbidden_fragments` for image paths/alt text and misleading generic story locators. Add `max_encoded_fragment_bytes` only to cases with independently established short solutions. Do not make every test trivially pass by adding a unique ticket code to each factual sentence, or by repeating the production selector algorithm inside the oracle.

HTML must preserve selectable visible text, table semantics, stable element IDs and readable layout. A static DOM text check establishes correspondence, not browser text-fragment highlighting. Leave real browser navigation tests to the joint integration milestone and record their outcome separately.

## 7. One-page quick fixture

Create `data/test_data_2_quick/risk-profiling.md`, approximately 3,000–6,000 Unicode characters, with 8–12 annotated facts and one or two JPEG mockups. Its HTML mirror has the same visible facts, independent attachment paths and matching source metadata.

Keep the page self-contained: a short purpose, three or four relevant dictionary values, the sole external provider, a happy path, an explicit condition/exception, a concise failure rule, two or three ticket references and a visible uncertainty. It must not require reading the full pages, reference annotations or application source to support its claims. Any link to a full page is optional context, not an unprovided premise.

Include one repeated phrase and an image-adjacent precise rule for cheap source-link regression. Ensure there is a clear supported core so autopilot can release useful content while excluding a genuinely uncertain optional statement. Manual mode must expose that uncertainty for review. Specify expected included/excluded facts independently of whichever prose the model generates.

A quick run uses `--docs data/test_data_2_quick`, never the parent `data/`. Time/token targets should be measured during implementation; do not promise a runtime based only on character count.

## 8. Generators, oracle and independent validation

Provide fixture-local commands that work before and after Agent A's package relocation. For example, with an explicitly documented fixture runtime:

```powershell
python scripts/test_data_2/build_fixture.py
python scripts/test_data_2/build_history.py
python scripts/test_data_2/validate_fixture.py
```

Keep any extra builder dependencies inside `scripts/test_data_2/` with their own documented pinned setup; do not edit the active pipeline's dependency file. Use deterministic source records, IDs, ordering and a fixed seed only where randomness is useful. Centralize configuration and file writes. Builders must refuse to overwrite unrelated work or modify a nonempty unknown repository; write only declared output roots.

`test_data_2_reference/manifest.json` records schema/fixture revision, source page IDs and paths, source URL bases, file hashes, character/record counts, toolchain versions, build commands, Git HEAD/tree/bundle references and declared intentional defects. Rebuilds distinguish deterministic content from environment-dependent packaging metadata.

Include explicit local source-page maps for full and quick mirrors in the reference package. Their source IDs/URLs and HTML file paths let Agent A verify destination text without treating HTML as additional product evidence or depending on a running server for offline checks. Preserve the actual `source_url` values for separate browser navigation checks.

`expected-facts.jsonl` contains at least 40 selected full-corpus expectations plus all quick-fixture facts. Each expectation has a stable ID, source location/quote, conditions/exceptions, status/version, ticket/dependency references where relevant, and the expected coverage disposition. Include wrong-but-plausible alternatives in discrepancy/exclusion records. Author/review the semantic expectations separately from rendered outputs; a generator comparing its own repeated prose is not independent evidence of semantic fidelity. Mark whether human review has occurred.

Required checks, independent of production pipeline internals:

| Check | Acceptance |
| --- | --- |
| Package shape | Exactly three full source pages and one quick page; reference metadata cannot enter their ingestion roots. |
| Text complexity | Requested size bands and substantive record counts; no bulk duplication used to hit a target. |
| Markdown/HTML parity | Corresponding facts, conditions, tables, IDs and visible captions agree after formatting normalization, except declared negative cases. Images resolve despite changed paths. |
| Assets | Only decoded JPEG documentation images, correct extensions, readable screenshots, safe relative links and no SVG content. |
| Dictionary/service consistency | Stable codes/versions, exactly three external services, risk references only `RiskSignal` as an external dependency. |
| Application behavior | Backend unit/integration tests, frontend build and relevant component/service tests, PostgreSQL migrations/seeds and Mongo indexes/fixtures run successfully in the documented local setup. |
| Core scenario | A seeded investor completes a questionnaire and gets a persisted/displayed assessment; retry/idempotency and provider-failure cases exercise actual code. |
| Integration isolation | Risk scenario invokes `RiskSignal` only; unrelated provider stubs see zero calls. |
| History | Bundle verification/clone succeeds; all commit subjects match ticket format; meaningful diffs, story mappings and HEAD/source hashes agree. |
| Reproducibility | Two clean builds produce the same document/source hashes and logical Git history; any image-rendering variability is eliminated by fixed rendering inputs or explicitly recorded. |
| Reference integrity | Case IDs/paths/quotes/tickets resolve; intended uncertainty and historical discrepancies are explicit; the oracle includes negative as well as positive cases. |

Do not turn a missing Docker/Java/Node runtime into a false success. Complete source and static checks, record the unavailable execution checks, and provide exact commands for the remaining validation. A runnable application is an acceptance target until those commands actually pass.

## 9. Milestones and parallel handoffs

| Milestone | Deliverable | Agent A dependency |
| --- | --- | --- |
| B0 Contract and domain | Stable paths/metadata/case schema, provider names, ticket namespace and a few representative records. | Agent A may consume the contract immediately; no code changes in Agent A's files. |
| B1 Quick fixture | One page, HTML mirror, JPEGs and expected facts/citation cases. | First integration input for precise links and both modes; deliver before the full application. |
| B2 Code slice and history | Java/Angular/PostgreSQL/MongoDB fixture with meaningful commits and portable bundle. | No requirement for current pipeline Java/ticket support. |
| B3 Full corpus | Three substantial pages, HTML variants, six or more mockups and complete source metadata. | Larger source-link/coverage evaluation. |
| B4 Independent validation | Fixture/application/history checks, semantic reference review and reproducibility report. | A stable fixture revision that Agent A can pin in integration results. |
| B5 Joint acceptance | Resolve fixture defects in owned files and supply final README/manifest links. | Agent A owns pipeline integration tests, root README and final merged smoke run. |

The branches can merge in either order: Agent B imports no production code, while Agent A's baseline regressions use temporary standalone inputs. Agent A may run the new fixture integration suite once B1/B3 is present. A missing optional full fixture must not break unrelated pipeline tests before that merge, but the final joint acceptance cannot silently skip it.

Fixture creation and static validation should use no Gemini API calls. If live pipeline evaluation is requested during integration, Agent A coordinates it through the existing shared ledger using `gemini-3.8-flash`, verified current pricing/conversion and the single cumulative PLN 200 allowance. Agent B must not create a second budget or run an untracked generation loop.

Deliver a fixture-local README with regeneration, serving, application startup, history restoration and validation instructions, plus an implementation report listing actual counts, commits, test results, intended discrepancies and remaining gaps. Completion means the data is readable, internally consistent, testable and suitable for later ticket-scoped code analysis—not merely a directory of plausible source files.
