# Investment platform fixture implementation report

Date: 2026-10-12

Fixture revision: `investment-fixture-v1`

## Delivered

The fixture includes a readable Java/Angular/PostgreSQL/MongoDB application snapshot under `data/investment_platform`, a portable ticket-bearing Git bundle under `data/investment_platform_history`, three full source pages and one isolated quick page, HTML mirrors with transformed attachment paths, six distinct JPEG mockups, and a separate reference package. The fixture builders and validator live under `scripts/test_data_2`. No production pipeline package, root packaging or existing `test_data_1` file was changed by this workstream.

| Page | Unicode characters | Substantive records |
| --- | ---: | ---: |
| Dictionaries | 77,051 | 60 code/version records |
| External services | 70,837 | 60 field/contract records plus 28 operational cases |
| Risk profiling | 81,144 | 60 story/acceptance variants |
| Quick risk profiling | 3,723 | 11 annotated facts |

The reference package contains 72 citation cases and 65 expected facts: 54 selected full-corpus expectations in a separately authored oracle plus all 11 quick facts. The oracle records whether human review occurred; its current value is `false`. Six distinct screens produce 16 decoded JPEG files across Markdown and HTML packages. Image generation uses Pillow 12.3.0, Arial from the recorded font path and hash, fixed 1100 × 650 pixels, quality 90 and no progressive encoding. The output was visually inspected for legible text and decoded as JPEG.

The application bundle has 21 nonempty commits: 13 risk-ticket commits, four unrelated trading commits and four foundation/shared commits. Every commit subject begins with a `TICKET-XXXX` code; TICKET-2007 has two commits. The pre-fix profile repository accepted free-text `5.1` as a tolerance input, and TICKET-2019 removed that acceptance. Planned TICKET-2018, TICKET-2020 and TICKET-2021 through TICKET-2024 have no fabricated implementation commit. The final branch is `refs/heads/main`, HEAD is `32aa15ad06c7af25a90fd7d119cbc56d74c89518`, and tree is `f8e5ad148043aaa1505cbfb812f7be5f657bed11`.

## Checks run

| Check | Result |
| --- | --- |
| Fixture static validation | Passed: source shape, size bands, Markdown/HTML table parity, selected notes, source metadata, decoded JPEGs, citation cases, facts, scopes, bundle clone and snapshot hashes. |
| Reproducibility | Two sequential rebuilds produced the same fixture manifest hash, HEAD and tree. |
| Java backend | `mvn test` passed 10 tests with Java 21.0.11 targeting Java 17. |
| Angular frontend | `npm run build` passed; `npm test` passed two component/service tests with Node 24.21.0. |
| Provider stubs | One local HTTP contract test passed, including same-key reuse, changed-body conflict and zero unrelated provider calls. |
| Maven wrapper | `mvnw.cmd -v` ran pinned Maven 3.9.16. |

The static validator used Python 3.12.14, Git 2.39.1 for the bundle check and Pillow 12.3.0. Source content and logical history were deterministic on a second run. No Gemini API call was made and no budget was spent.

## Deliberate discrepancies and open checks

`D-01` is the versioned pre-fix tolerance acceptance in application history. `D-02` changes one HTML destination phrase from the Markdown evidence to require a local-evidence fallback. `D-03` leaves the expired-profile trading-confirmation question unresolved and excluded. `D-04` and `D-05` exclude plausible but false instrument-risk and custody-dependency claims. Automatic orphan-audit reconciliation and a live integration-status UI are explicitly planned; they are not claimed as implemented.

Docker, Podman, PostgreSQL and MongoDB executables were unavailable on this host. Consequently the actual database migrations, Mongo indexes, Java HTTP journey, provider-failure recovery across both stores and zero-call isolation against the running application have not been executed. Run `docker compose up -d`, start the backend, then run `python scripts/test_data_2/integration_smoke.py` as described in `data/test_data_2_reference/README.md`. The separate stub test proves only its local contract. Real browser text-fragment highlighting over HTTP also remains unverified; static DOM membership is not a substitute. No human semantic review of the expected-fact oracle has occurred.
