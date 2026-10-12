# Northstar Investment synthetic platform

This repository is a local documentation test fixture. Investor references, scoring bands, provider responses and account data are fictional. No regulatory approval, investment suitability or production security is claimed.

The backend is a Spring Boot 3.5.16 Java 17 service. The frontend targets Angular 21.2.25 and Node 24.21.0. PostgreSQL 17.7 stores investor status, versioned dictionary codes, drafts, idempotency keys and accepted profile summaries. MongoDB 8.0 stores immutable answer snapshots and provider request/response audits. The accepted PostgreSQL summary is authoritative for the current profile; Mongo documents are associated through `draft_id` and never treated as a second mutable profile state.

Submission writes Mongo evidence before accepting the PostgreSQL summary. A Mongo failure blocks acceptance. A later PostgreSQL failure can leave an orphan Mongo audit; automated reconciliation is planned under TICKET-2020 and is not implemented. Failed reassessment leaves the previous unexpired profile active. New accepted results supersede the previous active row.

Exactly three fictional external business providers exist. Risk profiling calls only RiskSignal. MarketPulse supplies quote and instrument context. CustodyBridge supplies reservation and settlement context for orders. All three are deterministic local stubs in `mocks/`.

Run `docker compose up -d`, then `cd backend && .\mvnw.cmd test && .\mvnw.cmd spring-boot:run` on Windows, and in another terminal `cd frontend && npm ci && npm test && npm run build && npm start`. On Unix use `./mvnw`. The databases are exposed locally on ports 5434 and 27018. Copy `.env.example` to `.env` at the application root for local settings; Spring imports that file when the backend starts from `backend/`. No real provider or customer credential is stored here.

The core demo uses seeded investor `INV-100`, questionnaire `Q3`, rules `RS-2026-09` and processing consent `CP-3`. POST `/api/profile/drafts` with `{"investorRef":"INV-100"}`, PATCH `/api/profile/drafts/{draftId}` with Q3 answer codes, then POST `/api/profile/drafts/{draftId}/submit` with an idempotency key. GET `/api/profile/investors/INV-100/history` shows prior accepted results.
