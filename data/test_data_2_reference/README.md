# Investment platform fixture

This is synthetic test material. All investors, business providers, risk bands, accounts, prices and outcomes are invented. The six JPEG screens are deterministic mockups, not screenshots of the Angular application. No regulatory approval, investment suitability or production security is implied.

## Regenerate

Use Python 3.12 or newer, Git 2.39 or newer, and the fixture-local dependency file. The builders do not import the documentation pipeline or call Gemini. The output roots are declared in the builder and unknown files cause a failure.

```powershell
python -m pip install -r scripts/test_data_2/requirements.txt
python scripts/test_data_2/build_fixture.py
python scripts/test_data_2/build_history.py
python scripts/test_data_2/validate_fixture.py
python -m unittest discover -s scripts/test_data_2/tests -v
```

`build_fixture.py --host 127.0.0.1 --full-port 8766 --quick-port 8767` controls the recorded source URLs. Rebuild both the Markdown and HTML packages after changing ports. `source-page-map-full.json` and `source-page-map-quick.json` bind source IDs and original URLs to explicit local HTML files for offline destination checks. The HTML files verify destinations only; they are not extra product evidence.

## Serve source mirrors

Run these from the repository root in separate terminals:

```powershell
python -m http.server 8766 --bind 127.0.0.1 --directory data/test_data_2_html
python -m http.server 8767 --bind 127.0.0.1 --directory data/test_data_2_quick_html
```

The full docs input is `data/test_data_2`; the fast docs-only input is `data/test_data_2_quick`. Never pass their parent `data/` as the source root for a quick run.

## Application and history

The readable source is in `data/investment_platform`. The backend needs Java 17 or newer; its wrapper pins Maven 3.9.16. The frontend lockfile targets Angular 21.2.25 with a compatible Node 24 runtime. Docker Compose starts PostgreSQL 17.7, MongoDB 8.0.17 and three local Python provider stubs. Copy the application `.env.example` only for local overrides; the checked-in values are synthetic. From `data/investment_platform`:

```powershell
docker compose up -d
cd backend
.\mvnw.cmd test
.\mvnw.cmd spring-boot:run
```

In another terminal, from `data/investment_platform/frontend`:

```powershell
npm ci
npm test
npm run build
npm start
```

Once the backend and stubs respond locally, run `python scripts/test_data_2/integration_smoke.py` from the repository root. It submits seeded investor `INV-100`, retries the accepted request, forces a RiskSignal outage, checks the prior accepted profile remains current, and inspects MarketPulse and CustodyBridge call logs for zero risk-flow calls. The local test uses the real Java HTTP API and both databases; it needs the Compose services and backend running.

Restore the isolated ticket history without creating a nested Git repository inside the readable snapshot:

```powershell
git clone data/investment_platform_history/investment-platform.bundle .docgen/fixtures/restored-investment-platform
git -C .docgen/fixtures/restored-investment-platform log --oneline
```

The bundle manifest records the `main` ref, HEAD, tree hash, commit subjects, changed paths, snapshot file hashes and bundle hash. The history builder creates temporary repositories only under ignored `.docgen/fixtures/` and compares a fresh bundle clone against the readable source.

## Oracle and known differences

`citation-cases.jsonl` is schema version 1 from the companion pipeline plan. Cases describe exact evidence, expected text fragment or local fallback, and fragments that must not be selected. `expected-facts.jsonl` contains selected full-corpus claims and every quick fact. The `human_reviewed` field is false; a person has not yet approved the semantic oracle. `discrepancies.jsonl` isolates the historical 5.1 tolerance defect, one intentionally changed HTML phrase, the unresolved expired-profile display decision, and two wrong but plausible cross-scope alternatives. Planned TICKET-2020 reconciliation has no implementation commit.

The static validator checks package shape, all table cells, selected visible notes, source metadata, image decoding and paths, reference cases, bundle clone identity and hashes. It does not prove browser text-fragment highlighting, full PostgreSQL/MongoDB behavior or a successful Docker-based application journey. Record those results after running the integration smoke command in an environment with Docker.
