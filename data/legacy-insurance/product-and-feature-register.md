> Synthetic legacy documentation — test data only.
> Not legal, customer, regulatory, or production guidance.

# Northstar Benefits Platform — product and feature register

Former space: CONF-SYNTH-001. Export assembled 2025-02-18; embedded notes may predate the export.
Synthetic organisation labels: Amber Kite Workshop and Quiet Orchard Cooperative. These are invented fixture organisations; no connection to a real organisation is intended.
All issue references, dates, workflows, amounts, roles, and archived-page descriptions are invented test material. No source pages were copied.

## Product overview

Northstar Benefits Platform is the fictional workbench formerly called the benefit desk, policy hub, employer console, and occasionally pension admin. The names are retained because old index filters disagree.
The register describes supposed behaviour, not implemented capability. Status labels were copied between invented migration waves and should not be read as release evidence.
Policy and contract are sometimes used for the same object. Accounting and coverage boundaries are not reconciled.
Branch 21 and Branch 23 are catalogue labels awaiting review. Sigedis-related work is a disabled placeholder. No legal meaning is assigned here.
> Compliance note: requires Belgian-market and legal validation.

## Former space navigation

- [Feature body index](functional-specification.md#feature-index)
- [Technical entity index](integration-data-and-compliance.md#entity-index)
- [Glossary fragments](#glossary-fragments)
- [Unresolved backlog](#unresolved-backlog)

## Actors and roles

| Actor label | Approximate scope | Known ambiguity | Review owner |
| --- | --- | --- | --- |
| Employer operator | One synthetic employer | Scope inheritance missing | Operations team |
| Benefits operator | One plan revision | Old screen calls this administrator | Benefits stream |
| Claims reviewer | Assigned queue | Batch access not reconciled | TBD |
| Payment reviewer | Read-only historical view | Scope inheritance missing | Platform support |
| Report operator | One synthetic employer | Old screen calls this administrator | Reporting stream |
| Tenant administrator | One plan revision | Batch access not reconciled | Former migration team |
| Audit reader | Assigned queue | Scope inheritance missing | Operations team |
| Batch identity | Read-only historical view | Old screen calls this administrator | Benefits stream |
| Document reviewer | One synthetic employer | Batch access not reconciled | TBD |
| Support operator | One plan revision | Scope inheritance missing | Platform support |
| Configuration reviewer | Assigned queue | Old screen calls this administrator | Reporting stream |
| Migration observer | Read-only historical view | Batch access not reconciled | Former migration team |

## Product catalogue

One feature per row; the link points to the corresponding preserved feature section. Descriptions marked incomplete were never reconciled.

### Policy administration catalogue

| ID | Legacy page title | Description | Owner | Status | Priority | Related ticket | Dependencies | Source quality | Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F-001 | Policy creation | Effective date must equal the recorded approval date | Benefits stream | Copied forward | P2 | BENEFITS-142 | [Policy amendment](functional-specification.md#feature-f-002-policy-amendment) | Meeting fragment | [Policy creation](functional-specification.md#feature-f-001-policy-creation) |
| F-002 | Policy amendment | A revision may take effect before its approval date | TBD | Possibly obsolete | Unranked | BENEFITS-143 | [Policy renewal](functional-specification.md#feature-f-003-policy-renewal) | Owner missing | [Policy amendment](functional-specification.md#feature-f-002-policy-amendment) |
| F-003 | Policy renewal | Create a new coverage period without silently copying unresolved exclusions | Platform support | Disputed | P1 | BENEFITS-144 | [Policy suspension](functional-specification.md#feature-f-004-policy-suspension) | Contradicted elsewhere | [Policy renewal](functional-specification.md#feature-f-003-policy-renewal) |
| F-004 | Policy suspension | Freeze new collection instructions inside the suspension window | Reporting stream | Assumed delivered | P2 | BENEFITS-145 | [Policy cancellation](functional-specification.md#feature-f-005-policy-cancellation) | Unreviewed | [Policy suspension](functional-specification.md#feature-f-004-policy-suspension) |
| F-005 | Policy cancellation / old desk note | Require a cancellation reason before the nightly close | Former migration team | Draft | Unranked | BENEFITS-146 | [Policy reinstatement](functional-specification.md#feature-f-006-policy-reinstatement) | Meeting fragment | [Policy cancellation](functional-specification.md#feature-f-005-policy-cancellation) |
| F-006 | Policy reinstatement | Check whether the original accounting period is still open | Operations team | Copied forward | P1 | BENEFITS-147 | [Employer shell creation](functional-specification.md#feature-f-007-employer-shell-creation) | Owner missing | [Policy reinstatement](functional-specification.md#feature-f-006-policy-reinstatement) |

### Employer onboarding catalogue

| ID | Legacy page title | Description | Owner | Status | Priority | Related ticket | Dependencies | Source quality | Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F-007 | Employer shell creation | Keep a shell employer separate from an enabled sponsor | Benefits stream | Possibly obsolete | P2 | BENEFITS-148 | [Employer document intake](functional-specification.md#feature-f-008-employer-document-intake) | Contradicted elsewhere | [Employer shell creation](functional-specification.md#feature-f-007-employer-shell-creation) |
| F-008 | Employer document intake | Classify each attachment before accepting the packet | TBD | Disputed | Unranked | BENEFITS-149 | [Employer activation](functional-specification.md#feature-f-009-employer-activation) | Unreviewed | [Employer document intake](functional-specification.md#feature-f-008-employer-document-intake) |
| F-009 | Employer activation | Incomplete: reconcile the employer account with ... | Platform support | Assumed delivered | P1 | BENEFITS-150 | [Employer hierarchy change](functional-specification.md#feature-f-010-employer-hierarchy-change) | Meeting fragment | [Employer activation](functional-specification.md#feature-f-009-employer-activation) |
| F-010 | Employer hierarchy change / old desk note | Use an effective date for parent changes | Reporting stream | Draft | P2 | BENEFITS-151 | [Employer contact maintenance](functional-specification.md#feature-f-011-employer-contact-maintenance) | Owner missing | [Employer hierarchy change](functional-specification.md#feature-f-010-employer-hierarchy-change) |
| F-011 | Employer contact maintenance | Store a synthetic role mailbox label rather than a named person | Former migration team | Copied forward | Unranked | BENEFITS-152 | [Employer offboarding](functional-specification.md#feature-f-012-employer-offboarding) | Contradicted elsewhere | [Employer contact maintenance](functional-specification.md#feature-f-011-employer-contact-maintenance) |
| F-012 | Employer offboarding | Stop new enrolments after the closing date | Operations team | Possibly obsolete | P1 | BENEFITS-153 | [Employee eligibility assessment](functional-specification.md#feature-f-013-employee-eligibility-assessment) | Unreviewed | [Employer offboarding](functional-specification.md#feature-f-012-employer-offboarding) |

### Eligibility catalogue

| ID | Legacy page title | Description | Owner | Status | Priority | Related ticket | Dependencies | Source quality | Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F-013 | Employee eligibility assessment | Evaluate eligibility using the member status on the payroll period end date | Benefits stream | Disputed | P2 | BENEFITS-154 | [Waiting period evaluation](functional-specification.md#feature-f-014-waiting-period-evaluation) | Meeting fragment | [Employee eligibility assessment](functional-specification.md#feature-f-013-employee-eligibility-assessment) |
| F-014 | Waiting period evaluation | Count complete fictional plan months from the accepted start date | TBD | Assumed delivered | Unranked | BENEFITS-155 | [Employment category change](functional-specification.md#feature-f-015-employment-category-change) | Owner missing | [Waiting period evaluation](functional-specification.md#feature-f-014-waiting-period-evaluation) |
| F-015 | Employment category change / old desk note | Split coverage when a category changes during an open period | Platform support | Draft | P1 | BENEFITS-156 | [Leave and absence handling](functional-specification.md#feature-f-016-leave-and-absence-handling) | Contradicted elsewhere | [Employment category change](functional-specification.md#feature-f-015-employment-category-change) |
| F-016 | Leave and absence handling | Distinguish a missing payroll record from a declared absence | Reporting stream | Copied forward | P2 | BENEFITS-157 | [Member exit processing](functional-specification.md#feature-f-017-member-exit-processing) | Unreviewed | [Leave and absence handling](functional-specification.md#feature-f-016-leave-and-absence-handling) |
| F-017 | Member exit processing | Close future eligibility without erasing prior coverage | Former migration team | Possibly obsolete | Unranked | BENEFITS-158 | [Member re-entry](functional-specification.md#feature-f-018-member-re-entry) | Meeting fragment | [Member exit processing](functional-specification.md#feature-f-017-member-exit-processing) |
| F-018 | Member re-entry | Incomplete: reconcile the re-entry case with ... | Operations team | Disputed | P1 | BENEFITS-159 | [Contribution calculation](functional-specification.md#feature-f-019-contribution-calculation) | Owner missing | [Member re-entry](functional-specification.md#feature-f-018-member-re-entry) |

### Contributions catalogue

| ID | Legacy page title | Description | Owner | Status | Priority | Related ticket | Dependencies | Source quality | Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F-019 | Contribution calculation | Round each component before adding the period total | Benefits stream | Assumed delivered | P2 | BENEFITS-160 | [Contribution allocation](functional-specification.md#feature-f-020-contribution-allocation) | Contradicted elsewhere | [Contribution calculation](functional-specification.md#feature-f-019-contribution-calculation) |
| F-020 | Contribution allocation / old desk note | Allocate only to an open synthetic coverage account | TBD | Draft | Unranked | BENEFITS-161 | [Contribution arrears](functional-specification.md#feature-f-021-contribution-arrears) | Unreviewed | [Contribution allocation](functional-specification.md#feature-f-020-contribution-allocation) |
| F-021 | Contribution arrears | Start ageing from the synthetic due date recorded on the item | Platform support | Copied forward | P1 | BENEFITS-162 | [Payroll import](functional-specification.md#feature-f-022-payroll-import) | Meeting fragment | [Contribution arrears](functional-specification.md#feature-f-021-contribution-arrears) |
| F-022 | Payroll import | Evaluate eligibility using member status on the payroll file receipt date | Reporting stream | Possibly obsolete | P2 | BENEFITS-163 | [Contribution correction](functional-specification.md#feature-f-023-contribution-correction) | Owner missing | [Payroll import](functional-specification.md#feature-f-022-payroll-import) |
| F-023 | Contribution correction | Add unrounded components and round only the final period total | Former migration team | Disputed | Unranked | BENEFITS-164 | [Contribution refund request](functional-specification.md#feature-f-024-contribution-refund-request) | Contradicted elsewhere | [Contribution correction](functional-specification.md#feature-f-023-contribution-correction) |
| F-024 | Contribution refund request | A credit balance alone does not authorize a refund | Operations team | Assumed delivered | P1 | BENEFITS-165 | [Beneficiary designation](functional-specification.md#feature-f-025-beneficiary-designation) | Unreviewed | [Contribution refund request](functional-specification.md#feature-f-024-contribution-refund-request) |

### Beneficiaries catalogue

| ID | Legacy page title | Description | Owner | Status | Priority | Related ticket | Dependencies | Source quality | Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F-025 | Beneficiary designation / old desk note | The latest confirmed designation replaces all previous designations immediately | Benefits stream | Draft | P2 | BENEFITS-166 | [Beneficiary share validation](functional-specification.md#feature-f-026-beneficiary-share-validation) | Meeting fragment | [Beneficiary designation](functional-specification.md#feature-f-025-beneficiary-designation) |
| F-026 | Beneficiary share validation | Require the synthetic share total to equal one hundred before confirmation | TBD | Copied forward | Unranked | BENEFITS-167 | [Beneficiary evidence review](functional-specification.md#feature-f-027-beneficiary-evidence-review) | Owner missing | [Beneficiary share validation](functional-specification.md#feature-f-026-beneficiary-share-validation) |
| F-027 | Beneficiary evidence review | Incomplete: reconcile the evidence checklist with ... | Platform support | Possibly obsolete | P1 | BENEFITS-168 | [Retirement event registration](functional-specification.md#feature-f-028-retirement-event-registration) | Contradicted elsewhere | [Beneficiary evidence review](functional-specification.md#feature-f-027-beneficiary-evidence-review) |
| F-028 | Retirement event registration | Use the reported retirement date as an unvalidated event input | Reporting stream | Disputed | P2 | BENEFITS-169 | [Death event registration](functional-specification.md#feature-f-029-death-event-registration) | Unreviewed | [Retirement event registration](functional-specification.md#feature-f-028-retirement-event-registration) |
| F-029 | Death event registration | Store reported event dates without declaring legal proof | Former migration team | Assumed delivered | Unranked | BENEFITS-170 | [Disability event registration](functional-specification.md#feature-f-030-disability-event-registration) | Meeting fragment | [Death event registration](functional-specification.md#feature-f-029-death-event-registration) |
| F-030 | Disability event registration / old desk note | Keep an assessment placeholder separate from benefit authorization | Operations team | Draft | P1 | BENEFITS-171 | [Claim intake](functional-specification.md#feature-f-031-claim-intake) | Owner missing | [Disability event registration](functional-specification.md#feature-f-030-disability-event-registration) |

### Claims catalogue

| ID | Legacy page title | Description | Owner | Status | Priority | Related ticket | Dependencies | Source quality | Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F-031 | Claim intake | Allow intake even when the coverage lookup is unresolved | Benefits stream | Copied forward | P2 | BENEFITS-172 | [Claim evidence checklist](functional-specification.md#feature-f-032-claim-evidence-checklist) | Contradicted elsewhere | [Claim intake](functional-specification.md#feature-f-031-claim-intake) |
| F-032 | Claim evidence checklist | Record missing evidence as explicit checklist entries | TBD | Possibly obsolete | Unranked | BENEFITS-173 | [Death claim entitlement snapshot](functional-specification.md#feature-f-033-death-claim-entitlement-snapshot) | Unreviewed | [Claim evidence checklist](functional-specification.md#feature-f-032-claim-evidence-checklist) |
| F-033 | Death claim entitlement snapshot | Use the designation confirmed at the reported event date even if replaced later | Platform support | Disputed | P1 | BENEFITS-174 | [Disability claim assessment](functional-specification.md#feature-f-034-disability-claim-assessment) | Meeting fragment | [Death claim entitlement snapshot](functional-specification.md#feature-f-033-death-claim-entitlement-snapshot) |
| F-034 | Disability claim assessment | Require a recorded reviewer role before progressing the task | Reporting stream | Assumed delivered | P2 | BENEFITS-175 | [Retirement claim quotation](functional-specification.md#feature-f-035-retirement-claim-quotation) | Owner missing | [Disability claim assessment](functional-specification.md#feature-f-034-disability-claim-assessment) |
| F-035 | Retirement claim quotation / old desk note | Separate indicative amounts from approved settlement amounts | Former migration team | Draft | Unranked | BENEFITS-176 | [Claim appeal and reopening](functional-specification.md#feature-f-036-claim-appeal-and-reopening) | Contradicted elsewhere | [Retirement claim quotation](functional-specification.md#feature-f-035-retirement-claim-quotation) |
| F-036 | Claim appeal and reopening | Incomplete: reconcile the appeal case with ... | Operations team | Copied forward | P1 | BENEFITS-177 | [Payout authorization](functional-specification.md#feature-f-037-payout-authorization) | Unreviewed | [Claim appeal and reopening](functional-specification.md#feature-f-036-claim-appeal-and-reopening) |

### Payments catalogue

| ID | Legacy page title | Description | Owner | Status | Priority | Related ticket | Dependencies | Source quality | Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F-037 | Payout authorization | Allow one operations approver to authorize a payout | Benefits stream | Possibly obsolete | P2 | BENEFITS-178 | [Payout scheduling](functional-specification.md#feature-f-038-payout-scheduling) | Meeting fragment | [Payout authorization](functional-specification.md#feature-f-037-payout-authorization) |
| F-038 | Payout scheduling | Assign a fictional processing window rather than a bank promise | TBD | Disputed | Unranked | BENEFITS-179 | [Payout release](functional-specification.md#feature-f-039-payout-release) | Owner missing | [Payout scheduling](functional-specification.md#feature-f-038-payout-scheduling) |
| F-039 | Payout release | Require two distinct approver roles before any payout release | Platform support | Assumed delivered | P1 | BENEFITS-180 | [Payment return processing](functional-specification.md#feature-f-040-payment-return-processing) | Contradicted elsewhere | [Payout release](functional-specification.md#feature-f-039-payout-release) |
| F-040 | Payment return processing / old desk note | A return opens a reconciliation item before any retry | Reporting stream | Draft | P2 | BENEFITS-181 | [Payment reconciliation](functional-specification.md#feature-f-041-payment-reconciliation) | Unreviewed | [Payment return processing](functional-specification.md#feature-f-040-payment-return-processing) |
| F-041 | Payment reconciliation | Match both the instruction reference and synthetic amount | Former migration team | Copied forward | Unranked | BENEFITS-182 | [Payment hold removal](functional-specification.md#feature-f-042-payment-hold-removal) | Meeting fragment | [Payment reconciliation](functional-specification.md#feature-f-041-payment-reconciliation) |
| F-042 | Payment hold removal | Resolve each active hold reason separately | Operations team | Possibly obsolete | P1 | BENEFITS-183 | [Document template selection](functional-specification.md#feature-f-043-document-template-selection) | Owner missing | [Payment hold removal](functional-specification.md#feature-f-042-payment-hold-removal) |

### Documents catalogue

| ID | Legacy page title | Description | Owner | Status | Priority | Related ticket | Dependencies | Source quality | Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F-043 | Document template selection | Choose the template revision effective for the synthetic document date | Benefits stream | Disputed | P2 | BENEFITS-184 | [Statement generation](functional-specification.md#feature-f-044-statement-generation) | Contradicted elsewhere | [Document template selection](functional-specification.md#feature-f-043-document-template-selection) |
| F-044 | Statement generation | Render accepted amounts from one explicit ledger snapshot | TBD | Assumed delivered | Unranked | BENEFITS-185 | [Document retention purge](functional-specification.md#feature-f-045-document-retention-purge) | Unreviewed | [Statement generation](functional-specification.md#feature-f-044-statement-generation) |
| F-045 | Document retention purge / old desk note | Incomplete: reconcile the document retention item with ... | Platform support | Draft | P1 | BENEFITS-186 | [Document replacement](functional-specification.md#feature-f-046-document-replacement) | Meeting fragment | [Document retention purge](functional-specification.md#feature-f-045-document-retention-purge) |
| F-046 | Document replacement | Issue a replacement with a new revision reference | Reporting stream | Copied forward | P2 | BENEFITS-187 | [Document delivery receipt](functional-specification.md#feature-f-047-document-delivery-receipt) | Owner missing | [Document replacement](functional-specification.md#feature-f-046-document-replacement) |
| F-047 | Document delivery receipt | Distinguish transport acceptance from recipient acknowledgement | Former migration team | Possibly obsolete | Unranked | BENEFITS-188 | [Document language selection](functional-specification.md#feature-f-048-document-language-selection) | Contradicted elsewhere | [Document delivery receipt](functional-specification.md#feature-f-047-document-delivery-receipt) |
| F-048 | Document language selection | Use a configured language code without inferring nationality | Operations team | Disputed | P1 | BENEFITS-189 | [Notification preference update](functional-specification.md#feature-f-049-notification-preference-update) | Unreviewed | [Document language selection](functional-specification.md#feature-f-048-document-language-selection) |

### Notifications catalogue

| ID | Legacy page title | Description | Owner | Status | Priority | Related ticket | Dependencies | Source quality | Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F-049 | Notification preference update | Apply preference changes to unsent messages only | Benefits stream | Assumed delivered | P2 | BENEFITS-190 | [Eligibility notification](functional-specification.md#feature-f-050-eligibility-notification) | Meeting fragment | [Notification preference update](functional-specification.md#feature-f-049-notification-preference-update) |
| F-050 | Eligibility notification / old desk note | Reference the decision revision shown in the portal | TBD | Draft | Unranked | BENEFITS-191 | [Contribution reminder](functional-specification.md#feature-f-051-contribution-reminder) | Owner missing | [Eligibility notification](functional-specification.md#feature-f-050-eligibility-notification) |
| F-051 | Contribution reminder | Check the current dispute flag before constructing the reminder | Platform support | Copied forward | P1 | BENEFITS-192 | [Claim status notification](functional-specification.md#feature-f-052-claim-status-notification) | Contradicted elsewhere | [Contribution reminder](functional-specification.md#feature-f-051-contribution-reminder) |
| F-052 | Claim status notification | Expose only the approved display status | Reporting stream | Possibly obsolete | P2 | BENEFITS-193 | [Notification retry](functional-specification.md#feature-f-053-notification-retry) | Unreviewed | [Claim status notification](functional-specification.md#feature-f-052-claim-status-notification) |
| F-053 | Notification retry | Reuse the logical message key while creating a new attempt | Former migration team | Disputed | Unranked | BENEFITS-194 | [Notification suppression](functional-specification.md#feature-f-054-notification-suppression) | Meeting fragment | [Notification retry](functional-specification.md#feature-f-053-notification-retry) |
| F-054 | Notification suppression | Incomplete: reconcile the suppression window with ... | Operations team | Assumed delivered | P1 | BENEFITS-195 | [Employer coverage report](functional-specification.md#feature-f-055-employer-coverage-report) | Owner missing | [Notification suppression](functional-specification.md#feature-f-054-notification-suppression) |

### Reporting catalogue

| ID | Legacy page title | Description | Owner | Status | Priority | Related ticket | Dependencies | Source quality | Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F-055 | Employer coverage report / old desk note | Bind the extract to an explicit as-of date | Benefits stream | Draft | P2 | BENEFITS-196 | [Contribution exception report](functional-specification.md#feature-f-056-contribution-exception-report) | Contradicted elsewhere | [Employer coverage report](functional-specification.md#feature-f-055-employer-coverage-report) |
| F-056 | Contribution exception report | Separate rejected rows from accepted rows with warnings | TBD | Copied forward | Unranked | BENEFITS-197 | [Claim ageing report](functional-specification.md#feature-f-057-claim-ageing-report) | Unreviewed | [Contribution exception report](functional-specification.md#feature-f-056-contribution-exception-report) |
| F-057 | Claim ageing report | Measure queue duration from the latest triage start | Platform support | Possibly obsolete | P1 | BENEFITS-198 | [Branch 21 label review](functional-specification.md#feature-f-058-branch-21-label-review) | Meeting fragment | [Claim ageing report](functional-specification.md#feature-f-057-claim-ageing-report) |
| F-058 | Branch 21 label review | Treat Branch 21 as an unvalidated catalogue label only | Reporting stream | Disputed | P2 | BENEFITS-199 | [Branch 23 label review](functional-specification.md#feature-f-059-branch-23-label-review) | Owner missing | [Branch 21 label review](functional-specification.md#feature-f-058-branch-21-label-review) |
| F-059 | Branch 23 label review | Treat Branch 23 as an unvalidated catalogue label only | Former migration team | Assumed delivered | Unranked | BENEFITS-200 | [Sigedis reporting placeholder](functional-specification.md#feature-f-060-sigedis-reporting-placeholder) | Contradicted elsewhere | [Branch 23 label review](functional-specification.md#feature-f-059-branch-23-label-review) |
| F-060 | Sigedis reporting placeholder / old desk note | Disable external transmission until an approved mapping exists | Operations team | Draft | P1 | BENEFITS-201 | [User role assignment](functional-specification.md#feature-f-061-user-role-assignment) | Unreviewed | [Sigedis reporting placeholder](functional-specification.md#feature-f-060-sigedis-reporting-placeholder) |

### Administration catalogue

| ID | Legacy page title | Description | Owner | Status | Priority | Related ticket | Dependencies | Source quality | Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F-061 | User role assignment | Scope a grant to one employer or an explicit support scope | Benefits stream | Copied forward | P2 | BENEFITS-202 | [Permission override](functional-specification.md#feature-f-062-permission-override) | Meeting fragment | [User role assignment](functional-specification.md#feature-f-061-user-role-assignment) |
| F-062 | Permission override | Record a reason and expiry for the override | TBD | Possibly obsolete | Unranked | BENEFITS-203 | [Reference code maintenance](functional-specification.md#feature-f-063-reference-code-maintenance) | Owner missing | [Permission override](functional-specification.md#feature-f-062-permission-override) |
| F-063 | Reference code maintenance | Incomplete: reconcile the reference code with ... | Platform support | Disputed | P1 | BENEFITS-204 | [Plan configuration publishing](functional-specification.md#feature-f-064-plan-configuration-publishing) | Contradicted elsewhere | [Reference code maintenance](functional-specification.md#feature-f-063-reference-code-maintenance) |
| F-064 | Plan configuration publishing | Publish a complete reviewed revision as one unit | Reporting stream | Assumed delivered | P2 | BENEFITS-205 | [Operational task reassignment](functional-specification.md#feature-f-065-operational-task-reassignment) | Unreviewed | [Plan configuration publishing](functional-specification.md#feature-f-064-plan-configuration-publishing) |
| F-065 | Operational task reassignment / old desk note | Transfer ownership without resetting queue age | Former migration team | Draft | Unranked | BENEFITS-206 | [Tenant boundary review](functional-specification.md#feature-f-066-tenant-boundary-review) | Meeting fragment | [Operational task reassignment](functional-specification.md#feature-f-065-operational-task-reassignment) |
| F-066 | Tenant boundary review | Require explicit synthetic tenant context on every record lookup | Operations team | Copied forward | P1 | BENEFITS-207 | [Audit event capture](functional-specification.md#feature-f-067-audit-event-capture) | Owner missing | [Tenant boundary review](functional-specification.md#feature-f-066-tenant-boundary-review) |

### Audit catalogue

| ID | Legacy page title | Description | Owner | Status | Priority | Related ticket | Dependencies | Source quality | Link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F-067 | Audit event capture | Append a new event for a changed business decision | Benefits stream | Possibly obsolete | P2 | BENEFITS-208 | [Audit hold preservation](functional-specification.md#feature-f-068-audit-hold-preservation) | Contradicted elsewhere | [Audit event capture](functional-specification.md#feature-f-067-audit-event-capture) |
| F-068 | Audit hold preservation | Preserve document bytes while an audit hold exists even after the retention window | TBD | Disputed | Unranked | BENEFITS-209 | [Audit event search](functional-specification.md#feature-f-069-audit-event-search) | Unreviewed | [Audit hold preservation](functional-specification.md#feature-f-068-audit-hold-preservation) |
| F-069 | Audit event search | Filter by tenant scope before applying time filters | Platform support | Assumed delivered | P1 | BENEFITS-210 | [Audit export approval](functional-specification.md#feature-f-070-audit-export-approval) | Meeting fragment | [Audit event search](functional-specification.md#feature-f-069-audit-event-search) |
| F-070 | Audit export approval / old desk note | Bind approval to the selected fields and time interval | Reporting stream | Draft | P2 | BENEFITS-211 | [Historical correction trace](functional-specification.md#feature-f-071-historical-correction-trace) | Owner missing | [Audit export approval](functional-specification.md#feature-f-070-audit-export-approval) |
| F-071 | Historical correction trace | Link each adjustment to its immediate predecessor | Former migration team | Copied forward | Unranked | BENEFITS-212 | [Archive replay review](functional-specification.md#feature-f-072-archive-replay-review) | Contradicted elsewhere | [Historical correction trace](functional-specification.md#feature-f-071-historical-correction-trace) |
| F-072 | Archive replay review | Incomplete: reconcile the replay manifest with ... | Operations team | Possibly obsolete | P1 | BENEFITS-213 | [Policy creation](functional-specification.md#feature-f-001-policy-creation) | Unreviewed | [Archive replay review](functional-specification.md#feature-f-072-archive-replay-review) |

## Preserved sub-page index notes

The following stubs simulate former child pages. They repeat the catalogue in a different vocabulary because search aliases were merged without editorial review.

### CONF-SYNTH-101 — Policy creation index residue

Feature reference: [Policy creation](functional-specification.md#feature-f-001-policy-creation).
Archived label: policy administration / policy desk.
Owner recorded on 2020-02-02: Benefits stream.
Expected movement: draft → proposed.
Intended result: Effective date must equal the recorded approval date.
Unresolved exception: A proposed policy has no payable balance.
Ticket BENEFITS-501: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Policy amendment](functional-specification.md#feature-f-002-policy-amendment).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: policy, policy creation, benefits desk item 001.
Missing evidence: state transition example.
Carry-forward date: 2023-07-19; later timestamps do not imply approval.
Review question: does policy belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-102 — Policy amendment index residue

Feature reference: [Policy amendment](functional-specification.md#feature-f-002-policy-amendment).
Archived label: policy administration / policy revision desk.
Owner recorded on 2021-03-03: TBD.
Expected movement: active → revised.
Intended result: A revision may take effect before its approval date.
Unresolved exception: Preserve the preceding revision for reconciliation.
Ticket BENEFITS-502: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Policy renewal](functional-specification.md#feature-f-003-policy-renewal).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: policy revision, policy amendment, benefits desk item 002.
Missing evidence: rejection screenshot.
Carry-forward date: 2024-08-20; later timestamps do not imply approval.
Review question: does policy revision belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-103 — Policy renewal index residue

Feature reference: [Policy renewal](functional-specification.md#feature-f-003-policy-renewal).
Archived label: policy administration / renewal instruction desk.
Owner recorded on 2022-04-04: Platform support.
Expected movement: expiring → renewed.
Intended result: Create a new coverage period without silently copying unresolved exclusions.
Unresolved exception: An unapproved renewal stays in the exception queue.
Ticket BENEFITS-503: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Policy suspension](functional-specification.md#feature-f-004-policy-suspension).
Source quality: Possibly obsolete; the retired queue name still appears in filters.
Search aliases: renewal instruction, policy renewal, benefits desk item 003.
Missing evidence: batch recovery record.
Carry-forward date: 2025-09-21; later timestamps do not imply approval.
Review question: does renewal instruction belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-104 — Policy suspension index residue

Feature reference: [Policy suspension](functional-specification.md#feature-f-004-policy-suspension).
Archived label: policy administration / suspension window desk.
Owner recorded on 2023-05-05: Reporting stream.
Expected movement: active → suspended.
Intended result: Freeze new collection instructions inside the suspension window.
Unresolved exception: Already released payments are handled separately.
Ticket BENEFITS-504: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Policy cancellation](functional-specification.md#feature-f-005-policy-cancellation).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: suspension window, policy suspension, benefits desk item 004.
Missing evidence: signed-off workflow.
Carry-forward date: 2019-10-22; later timestamps do not imply approval.
Review question: does suspension window belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-105 — Policy cancellation index residue

Feature reference: [Policy cancellation](functional-specification.md#feature-f-005-policy-cancellation).
Archived label: policy administration / cancellation request desk.
Owner recorded on 2024-06-06: Former migration team.
Expected movement: active → cancelled.
Intended result: Require a cancellation reason before the nightly close.
Unresolved exception: Do not delete pending claims when coverage closes.
Ticket BENEFITS-505: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Policy reinstatement](functional-specification.md#feature-f-006-policy-reinstatement).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: cancellation request, policy cancellation, benefits desk item 005.
Missing evidence: state transition example.
Carry-forward date: 2020-11-23; later timestamps do not imply approval.
Review question: does cancellation request belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-106 — Policy reinstatement index residue

Feature reference: [Policy reinstatement](functional-specification.md#feature-f-006-policy-reinstatement).
Archived label: policy administration / reinstatement request desk.
Owner recorded on 2025-07-07: Operations team.
Expected movement: cancelled → active.
Intended result: Check whether the original accounting period is still open.
Unresolved exception: A new revision must identify the gap in coverage.
Ticket BENEFITS-506: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Employer shell creation](functional-specification.md#feature-f-007-employer-shell-creation).
Source quality: Possibly obsolete; the retired queue name still appears in filters.
Search aliases: reinstatement request, policy reinstatement, benefits desk item 006.
Missing evidence: rejection screenshot.
Carry-forward date: 2021-12-24; later timestamps do not imply approval.
Review question: does reinstatement request belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-107 — Employer shell creation index residue

Feature reference: [Employer shell creation](functional-specification.md#feature-f-007-employer-shell-creation).
Archived label: employer onboarding / employer shell desk.
Owner recorded on 2019-08-08: Benefits stream.
Expected movement: received → incomplete.
Intended result: Keep a shell employer separate from an enabled sponsor.
Unresolved exception: A missing administrative address blocks activation.
Ticket BENEFITS-507: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Employer document intake](functional-specification.md#feature-f-008-employer-document-intake).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: employer shell, employer shell creation, benefits desk item 007.
Missing evidence: batch recovery record.
Carry-forward date: 2022-01-25; later timestamps do not imply approval.
Review question: does employer shell belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-108 — Employer document intake index residue

Feature reference: [Employer document intake](functional-specification.md#feature-f-008-employer-document-intake).
Archived label: employer onboarding / intake packet desk.
Owner recorded on 2020-09-09: TBD.
Expected movement: uploaded → reviewed.
Intended result: Classify each attachment before accepting the packet.
Unresolved exception: A replacement file must retain the original intake reference.
Ticket BENEFITS-508: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Employer activation](functional-specification.md#feature-f-009-employer-activation).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: intake packet, employer document intake, benefits desk item 008.
Missing evidence: signed-off workflow.
Carry-forward date: 2023-02-26; later timestamps do not imply approval.
Review question: does intake packet belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-109 — Employer activation index residue

Feature reference: [Employer activation](functional-specification.md#feature-f-009-employer-activation).
Archived label: employer onboarding / employer account desk.
Owner recorded on 2021-10-10: Platform support.
Expected movement: reviewed → enabled.
Intended result: Require operations review and a benefit package assignment.
Unresolved exception: A disabled package cannot activate a new employer.
Ticket BENEFITS-509: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Employer hierarchy change](functional-specification.md#feature-f-010-employer-hierarchy-change).
Source quality: Possibly obsolete; the retired queue name still appears in filters.
Search aliases: employer account, employer activation, benefits desk item 009.
Missing evidence: state transition example.
Carry-forward date: 2024-03-27; later timestamps do not imply approval.
Review question: does employer account belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-110 — Employer hierarchy change index residue

Feature reference: [Employer hierarchy change](functional-specification.md#feature-f-010-employer-hierarchy-change).
Archived label: employer onboarding / employer hierarchy desk.
Owner recorded on 2022-11-11: Reporting stream.
Expected movement: flat → grouped.
Intended result: Use an effective date for parent changes.
Unresolved exception: Do not transfer historical invoices to the new parent.
Ticket BENEFITS-510: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Employer contact maintenance](functional-specification.md#feature-f-011-employer-contact-maintenance).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: employer hierarchy, employer hierarchy change, benefits desk item 010.
Missing evidence: rejection screenshot.
Carry-forward date: 2025-04-01; later timestamps do not imply approval.
Review question: does employer hierarchy belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-111 — Employer contact maintenance index residue

Feature reference: [Employer contact maintenance](functional-specification.md#feature-f-011-employer-contact-maintenance).
Archived label: employer onboarding / contact slot desk.
Owner recorded on 2023-12-12: Former migration team.
Expected movement: unassigned → routed.
Intended result: Store a synthetic role mailbox label rather than a named person.
Unresolved exception: A contact without a channel cannot receive an outbound event.
Ticket BENEFITS-511: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Employer offboarding](functional-specification.md#feature-f-012-employer-offboarding).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: contact slot, employer contact maintenance, benefits desk item 011.
Missing evidence: batch recovery record.
Carry-forward date: 2019-05-02; later timestamps do not imply approval.
Review question: does contact slot belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-112 — Employer offboarding index residue

Feature reference: [Employer offboarding](functional-specification.md#feature-f-012-employer-offboarding).
Archived label: employer onboarding / offboarding case desk.
Owner recorded on 2024-01-13: Operations team.
Expected movement: enabled → closing.
Intended result: Stop new enrolments after the closing date.
Unresolved exception: Unsettled contributions keep the shell visible.
Ticket BENEFITS-512: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Employee eligibility assessment](functional-specification.md#feature-f-013-employee-eligibility-assessment).
Source quality: Possibly obsolete; the retired queue name still appears in filters.
Search aliases: offboarding case, employer offboarding, benefits desk item 012.
Missing evidence: signed-off workflow.
Carry-forward date: 2020-06-03; later timestamps do not imply approval.
Review question: does offboarding case belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-113 — Employee eligibility assessment index residue

Feature reference: [Employee eligibility assessment](functional-specification.md#feature-f-013-employee-eligibility-assessment).
Archived label: eligibility / eligibility decision desk.
Owner recorded on 2025-02-14: Benefits stream.
Expected movement: unchecked → eligible.
Intended result: Evaluate eligibility using the member status on the payroll period end date.
Unresolved exception: An unknown class routes to manual review.
Ticket BENEFITS-513: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Waiting period evaluation](functional-specification.md#feature-f-014-waiting-period-evaluation).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: eligibility decision, employee eligibility assessment, benefits desk item 013.
Missing evidence: state transition example.
Carry-forward date: 2021-07-04; later timestamps do not imply approval.
Review question: does eligibility decision belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-114 — Waiting period evaluation index residue

Feature reference: [Waiting period evaluation](functional-specification.md#feature-f-014-waiting-period-evaluation).
Archived label: eligibility / waiting interval desk.
Owner recorded on 2019-03-15: TBD.
Expected movement: waiting → qualified.
Intended result: Count complete fictional plan months from the accepted start date.
Unresolved exception: An interrupted interval requires a new review.
Ticket BENEFITS-514: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Employment category change](functional-specification.md#feature-f-015-employment-category-change).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: waiting interval, waiting period evaluation, benefits desk item 014.
Missing evidence: rejection screenshot.
Carry-forward date: 2022-08-05; later timestamps do not imply approval.
Review question: does waiting interval belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-115 — Employment category change index residue

Feature reference: [Employment category change](functional-specification.md#feature-f-015-employment-category-change).
Archived label: eligibility / category assignment desk.
Owner recorded on 2020-04-16: Platform support.
Expected movement: class-a → class-b.
Intended result: Split coverage when a category changes during an open period.
Unresolved exception: Never infer a salary from the class label.
Ticket BENEFITS-515: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Leave and absence handling](functional-specification.md#feature-f-016-leave-and-absence-handling).
Source quality: Possibly obsolete; the retired queue name still appears in filters.
Search aliases: category assignment, employment category change, benefits desk item 015.
Missing evidence: batch recovery record.
Carry-forward date: 2023-09-06; later timestamps do not imply approval.
Review question: does category assignment belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-116 — Leave and absence handling index residue

Feature reference: [Leave and absence handling](functional-specification.md#feature-f-016-leave-and-absence-handling).
Archived label: eligibility / absence interval desk.
Owner recorded on 2021-05-17: Reporting stream.
Expected movement: working → absent.
Intended result: Distinguish a missing payroll record from a declared absence.
Unresolved exception: Overlapping intervals need an operations decision.
Ticket BENEFITS-516: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Member exit processing](functional-specification.md#feature-f-017-member-exit-processing).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: absence interval, leave and absence handling, benefits desk item 016.
Missing evidence: signed-off workflow.
Carry-forward date: 2024-10-07; later timestamps do not imply approval.
Review question: does absence interval belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-117 — Member exit processing index residue

Feature reference: [Member exit processing](functional-specification.md#feature-f-017-member-exit-processing).
Archived label: eligibility / exit instruction desk.
Owner recorded on 2022-06-18: Former migration team.
Expected movement: covered → exited.
Intended result: Close future eligibility without erasing prior coverage.
Unresolved exception: A pending death event blocks the ordinary exit path.
Ticket BENEFITS-517: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Member re-entry](functional-specification.md#feature-f-018-member-re-entry).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: exit instruction, member exit processing, benefits desk item 017.
Missing evidence: state transition example.
Carry-forward date: 2025-11-08; later timestamps do not imply approval.
Review question: does exit instruction belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-118 — Member re-entry index residue

Feature reference: [Member re-entry](functional-specification.md#feature-f-018-member-re-entry).
Archived label: eligibility / re-entry case desk.
Owner recorded on 2023-07-19: Operations team.
Expected movement: exited → candidate.
Intended result: Match the synthetic member key before creating a new membership.
Unresolved exception: Prior beneficiary choices are not automatically confirmed.
Ticket BENEFITS-518: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Contribution calculation](functional-specification.md#feature-f-019-contribution-calculation).
Source quality: Possibly obsolete; the retired queue name still appears in filters.
Search aliases: re-entry case, member re-entry, benefits desk item 018.
Missing evidence: rejection screenshot.
Carry-forward date: 2019-12-09; later timestamps do not imply approval.
Review question: does re-entry case belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-119 — Contribution calculation index residue

Feature reference: [Contribution calculation](functional-specification.md#feature-f-019-contribution-calculation).
Archived label: contributions / contribution line desk.
Owner recorded on 2024-08-20: Benefits stream.
Expected movement: rated → calculated.
Intended result: Round each component before adding the period total.
Unresolved exception: Keep the basis and rate revision alongside the result.
Ticket BENEFITS-519: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Contribution allocation](functional-specification.md#feature-f-020-contribution-allocation).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: contribution line, contribution calculation, benefits desk item 019.
Missing evidence: batch recovery record.
Carry-forward date: 2020-01-10; later timestamps do not imply approval.
Review question: does contribution line belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-120 — Contribution allocation index residue

Feature reference: [Contribution allocation](functional-specification.md#feature-f-020-contribution-allocation).
Archived label: contributions / allocation instruction desk.
Owner recorded on 2025-09-21: TBD.
Expected movement: unallocated → allocated.
Intended result: Allocate only to an open synthetic coverage account.
Unresolved exception: An unmatched remittance remains on suspense.
Ticket BENEFITS-520: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Contribution arrears](functional-specification.md#feature-f-021-contribution-arrears).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: allocation instruction, contribution allocation, benefits desk item 020.
Missing evidence: signed-off workflow.
Carry-forward date: 2021-02-11; later timestamps do not imply approval.
Review question: does allocation instruction belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-121 — Contribution arrears index residue

Feature reference: [Contribution arrears](functional-specification.md#feature-f-021-contribution-arrears).
Archived label: contributions / arrears item desk.
Owner recorded on 2019-10-22: Platform support.
Expected movement: due → overdue.
Intended result: Start ageing from the synthetic due date recorded on the item.
Unresolved exception: A disputed item remains visible in ageing.
Ticket BENEFITS-521: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Payroll import](functional-specification.md#feature-f-022-payroll-import).
Source quality: Possibly obsolete; the retired queue name still appears in filters.
Search aliases: arrears item, contribution arrears, benefits desk item 021.
Missing evidence: state transition example.
Carry-forward date: 2022-03-12; later timestamps do not imply approval.
Review question: does arrears item belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-122 — Payroll import index residue

Feature reference: [Payroll import](functional-specification.md#feature-f-022-payroll-import).
Archived label: contributions / payroll batch desk.
Owner recorded on 2020-11-23: Reporting stream.
Expected movement: staged → accepted.
Intended result: Evaluate eligibility using member status on the payroll file receipt date.
Unresolved exception: A rejected row must not silently reduce the accepted control total.
Ticket BENEFITS-522: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Contribution correction](functional-specification.md#feature-f-023-contribution-correction).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: payroll batch, payroll import, benefits desk item 022.
Missing evidence: rejection screenshot.
Carry-forward date: 2023-04-13; later timestamps do not imply approval.
Review question: does payroll batch belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-123 — Contribution correction index residue

Feature reference: [Contribution correction](functional-specification.md#feature-f-023-contribution-correction).
Archived label: contributions / correction delta desk.
Owner recorded on 2021-12-24: Former migration team.
Expected movement: posted → adjusted.
Intended result: Add unrounded components and round only the final period total.
Unresolved exception: Link every correction to a prior posted contribution.
Ticket BENEFITS-523: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Contribution refund request](functional-specification.md#feature-f-024-contribution-refund-request).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: correction delta, contribution correction, benefits desk item 023.
Missing evidence: batch recovery record.
Carry-forward date: 2024-05-14; later timestamps do not imply approval.
Review question: does correction delta belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-124 — Contribution refund request index residue

Feature reference: [Contribution refund request](functional-specification.md#feature-f-024-contribution-refund-request).
Archived label: contributions / refund case desk.
Owner recorded on 2022-01-25: Operations team.
Expected movement: credit → requested.
Intended result: A credit balance alone does not authorize a refund.
Unresolved exception: A refund must not erase the contribution that created the credit.
Ticket BENEFITS-524: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Beneficiary designation](functional-specification.md#feature-f-025-beneficiary-designation).
Source quality: Possibly obsolete; the retired queue name still appears in filters.
Search aliases: refund case, contribution refund request, benefits desk item 024.
Missing evidence: signed-off workflow.
Carry-forward date: 2025-06-15; later timestamps do not imply approval.
Review question: does refund case belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-125 — Beneficiary designation index residue

Feature reference: [Beneficiary designation](functional-specification.md#feature-f-025-beneficiary-designation).
Archived label: beneficiaries / designation set desk.
Owner recorded on 2023-02-26: Benefits stream.
Expected movement: draft → confirmed.
Intended result: The latest confirmed designation replaces all previous designations immediately.
Unresolved exception: Keep percentage totals separate from verification status.
Ticket BENEFITS-525: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Beneficiary share validation](functional-specification.md#feature-f-026-beneficiary-share-validation).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: designation set, beneficiary designation, benefits desk item 025.
Missing evidence: state transition example.
Carry-forward date: 2019-07-16; later timestamps do not imply approval.
Review question: does designation set belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-126 — Beneficiary share validation index residue

Feature reference: [Beneficiary share validation](functional-specification.md#feature-f-026-beneficiary-share-validation).
Archived label: beneficiaries / share set desk.
Owner recorded on 2024-03-27: TBD.
Expected movement: entered → balanced.
Intended result: Require the synthetic share total to equal one hundred before confirmation.
Unresolved exception: Unknown recipients keep the set in draft.
Ticket BENEFITS-526: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Beneficiary evidence review](functional-specification.md#feature-f-027-beneficiary-evidence-review).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: share set, beneficiary share validation, benefits desk item 026.
Missing evidence: rejection screenshot.
Carry-forward date: 2020-08-17; later timestamps do not imply approval.
Review question: does share set belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-127 — Beneficiary evidence review index residue

Feature reference: [Beneficiary evidence review](functional-specification.md#feature-f-027-beneficiary-evidence-review).
Archived label: beneficiaries / evidence checklist desk.
Owner recorded on 2025-04-01: Platform support.
Expected movement: missing → reviewed.
Intended result: Evidence completeness is a workflow flag only.
Unresolved exception: A reviewed attachment does not determine entitlement.
Ticket BENEFITS-527: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Retirement event registration](functional-specification.md#feature-f-028-retirement-event-registration).
Source quality: Possibly obsolete; the retired queue name still appears in filters.
Search aliases: evidence checklist, beneficiary evidence review, benefits desk item 027.
Missing evidence: batch recovery record.
Carry-forward date: 2021-09-18; later timestamps do not imply approval.
Review question: does evidence checklist belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-128 — Retirement event registration index residue

Feature reference: [Retirement event registration](functional-specification.md#feature-f-028-retirement-event-registration).
Archived label: beneficiaries / retirement event desk.
Owner recorded on 2019-05-02: Reporting stream.
Expected movement: reported → assessed.
Intended result: Use the reported retirement date as an unvalidated event input.
Unresolved exception: Do not derive statutory age rules from this fixture.
Ticket BENEFITS-528: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Death event registration](functional-specification.md#feature-f-029-death-event-registration).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: retirement event, retirement event registration, benefits desk item 028.
Missing evidence: signed-off workflow.
Carry-forward date: 2022-10-19; later timestamps do not imply approval.
Review question: does retirement event belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-129 — Death event registration index residue

Feature reference: [Death event registration](functional-specification.md#feature-f-029-death-event-registration).
Archived label: beneficiaries / death event desk.
Owner recorded on 2020-06-03: Former migration team.
Expected movement: reported → awaiting-review.
Intended result: Store reported event dates without declaring legal proof.
Unresolved exception: Conflicting event reports must remain separately traceable.
Ticket BENEFITS-529: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Disability event registration](functional-specification.md#feature-f-030-disability-event-registration).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: death event, death event registration, benefits desk item 029.
Missing evidence: state transition example.
Carry-forward date: 2023-11-20; later timestamps do not imply approval.
Review question: does death event belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-130 — Disability event registration index residue

Feature reference: [Disability event registration](functional-specification.md#feature-f-030-disability-event-registration).
Archived label: beneficiaries / disability event desk.
Owner recorded on 2021-07-04: Operations team.
Expected movement: reported → awaiting-assessment.
Intended result: Keep an assessment placeholder separate from benefit authorization.
Unresolved exception: No medical diagnosis belongs in the synthetic payload.
Ticket BENEFITS-530: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Claim intake](functional-specification.md#feature-f-031-claim-intake).
Source quality: Possibly obsolete; the retired queue name still appears in filters.
Search aliases: disability event, disability event registration, benefits desk item 030.
Missing evidence: rejection screenshot.
Carry-forward date: 2024-12-21; later timestamps do not imply approval.
Review question: does disability event belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-131 — Claim intake index residue

Feature reference: [Claim intake](functional-specification.md#feature-f-031-claim-intake).
Archived label: claims / claim shell desk.
Owner recorded on 2022-08-05: Benefits stream.
Expected movement: received → triaged.
Intended result: Allow intake even when the coverage lookup is unresolved.
Unresolved exception: A shell claim cannot generate a payment instruction.
Ticket BENEFITS-531: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Claim evidence checklist](functional-specification.md#feature-f-032-claim-evidence-checklist).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: claim shell, claim intake, benefits desk item 031.
Missing evidence: batch recovery record.
Carry-forward date: 2025-01-22; later timestamps do not imply approval.
Review question: does claim shell belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-132 — Claim evidence checklist index residue

Feature reference: [Claim evidence checklist](functional-specification.md#feature-f-032-claim-evidence-checklist).
Archived label: claims / claim checklist desk.
Owner recorded on 2023-09-06: TBD.
Expected movement: open → complete.
Intended result: Record missing evidence as explicit checklist entries.
Unresolved exception: Completeness must not imply approval.
Ticket BENEFITS-532: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Death claim entitlement snapshot](functional-specification.md#feature-f-033-death-claim-entitlement-snapshot).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: claim checklist, claim evidence checklist, benefits desk item 032.
Missing evidence: signed-off workflow.
Carry-forward date: 2019-02-23; later timestamps do not imply approval.
Review question: does claim checklist belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-133 — Death claim entitlement snapshot index residue

Feature reference: [Death claim entitlement snapshot](functional-specification.md#feature-f-033-death-claim-entitlement-snapshot).
Archived label: claims / entitlement snapshot desk.
Owner recorded on 2024-10-07: Platform support.
Expected movement: candidate → frozen.
Intended result: Use the designation confirmed at the reported event date even if replaced later.
Unresolved exception: The snapshot is a routing aid pending expert validation.
Ticket BENEFITS-533: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Disability claim assessment](functional-specification.md#feature-f-034-disability-claim-assessment).
Source quality: Possibly obsolete; the retired queue name still appears in filters.
Search aliases: entitlement snapshot, death claim entitlement snapshot, benefits desk item 033.
Missing evidence: state transition example.
Carry-forward date: 2020-03-24; later timestamps do not imply approval.
Review question: does entitlement snapshot belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-134 — Disability claim assessment index residue

Feature reference: [Disability claim assessment](functional-specification.md#feature-f-034-disability-claim-assessment).
Archived label: claims / assessment task desk.
Owner recorded on 2025-11-08: Reporting stream.
Expected movement: queued → reviewed.
Intended result: Require a recorded reviewer role before progressing the task.
Unresolved exception: An expired review reopens the checklist.
Ticket BENEFITS-534: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Retirement claim quotation](functional-specification.md#feature-f-035-retirement-claim-quotation).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: assessment task, disability claim assessment, benefits desk item 034.
Missing evidence: rejection screenshot.
Carry-forward date: 2021-04-25; later timestamps do not imply approval.
Review question: does assessment task belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-135 — Retirement claim quotation index residue

Feature reference: [Retirement claim quotation](functional-specification.md#feature-f-035-retirement-claim-quotation).
Archived label: claims / quotation draft desk.
Owner recorded on 2019-12-09: Former migration team.
Expected movement: requested → quoted.
Intended result: Separate indicative amounts from approved settlement amounts.
Unresolved exception: A recalculation invalidates the prior quote acknowledgement.
Ticket BENEFITS-535: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Claim appeal and reopening](functional-specification.md#feature-f-036-claim-appeal-and-reopening).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: quotation draft, retirement claim quotation, benefits desk item 035.
Missing evidence: batch recovery record.
Carry-forward date: 2022-05-26; later timestamps do not imply approval.
Review question: does quotation draft belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-136 — Claim appeal and reopening index residue

Feature reference: [Claim appeal and reopening](functional-specification.md#feature-f-036-claim-appeal-and-reopening).
Archived label: claims / appeal case desk.
Owner recorded on 2020-01-10: Operations team.
Expected movement: closed → reopened.
Intended result: Preserve the original decision and append the appeal reason.
Unresolved exception: Reopening does not reverse a payment automatically.
Ticket BENEFITS-536: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Payout authorization](functional-specification.md#feature-f-037-payout-authorization).
Source quality: Possibly obsolete; the retired queue name still appears in filters.
Search aliases: appeal case, claim appeal and reopening, benefits desk item 036.
Missing evidence: signed-off workflow.
Carry-forward date: 2023-06-27; later timestamps do not imply approval.
Review question: does appeal case belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-137 — Payout authorization index residue

Feature reference: [Payout authorization](functional-specification.md#feature-f-037-payout-authorization).
Archived label: payments / payout instruction desk.
Owner recorded on 2021-02-11: Benefits stream.
Expected movement: approved → authorized.
Intended result: Allow one operations approver to authorize a payout.
Unresolved exception: Authorization applies only to the recorded amount revision.
Ticket BENEFITS-537: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Payout scheduling](functional-specification.md#feature-f-038-payout-scheduling).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: payout instruction, payout authorization, benefits desk item 037.
Missing evidence: state transition example.
Carry-forward date: 2024-07-01; later timestamps do not imply approval.
Review question: does payout instruction belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-138 — Payout scheduling index residue

Feature reference: [Payout scheduling](functional-specification.md#feature-f-038-payout-scheduling).
Archived label: payments / scheduled payout desk.
Owner recorded on 2022-03-12: TBD.
Expected movement: authorized → scheduled.
Intended result: Assign a fictional processing window rather than a bank promise.
Unresolved exception: An unavailable window leaves the instruction queued.
Ticket BENEFITS-538: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Payout release](functional-specification.md#feature-f-039-payout-release).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: scheduled payout, payout scheduling, benefits desk item 038.
Missing evidence: rejection screenshot.
Carry-forward date: 2025-08-02; later timestamps do not imply approval.
Review question: does scheduled payout belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-139 — Payout release index residue

Feature reference: [Payout release](functional-specification.md#feature-f-039-payout-release).
Archived label: payments / release instruction desk.
Owner recorded on 2023-04-13: Platform support.
Expected movement: scheduled → released.
Intended result: Require two distinct approver roles before any payout release.
Unresolved exception: A changed amount cancels prior approvals.
Ticket BENEFITS-539: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Payment return processing](functional-specification.md#feature-f-040-payment-return-processing).
Source quality: Possibly obsolete; the retired queue name still appears in filters.
Search aliases: release instruction, payout release, benefits desk item 039.
Missing evidence: batch recovery record.
Carry-forward date: 2019-09-03; later timestamps do not imply approval.
Review question: does release instruction belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-140 — Payment return processing index residue

Feature reference: [Payment return processing](functional-specification.md#feature-f-040-payment-return-processing).
Archived label: payments / return notice desk.
Owner recorded on 2024-05-14: Reporting stream.
Expected movement: released → returned.
Intended result: A return opens a reconciliation item before any retry.
Unresolved exception: Never infer beneficiary identity from a return message.
Ticket BENEFITS-540: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Payment reconciliation](functional-specification.md#feature-f-041-payment-reconciliation).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: return notice, payment return processing, benefits desk item 040.
Missing evidence: signed-off workflow.
Carry-forward date: 2020-10-04; later timestamps do not imply approval.
Review question: does return notice belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-141 — Payment reconciliation index residue

Feature reference: [Payment reconciliation](functional-specification.md#feature-f-041-payment-reconciliation).
Archived label: payments / settlement match desk.
Owner recorded on 2025-06-15: Former migration team.
Expected movement: unmatched → reconciled.
Intended result: Match both the instruction reference and synthetic amount.
Unresolved exception: A many-to-one match requires an explicit grouping record.
Ticket BENEFITS-541: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Payment hold removal](functional-specification.md#feature-f-042-payment-hold-removal).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: settlement match, payment reconciliation, benefits desk item 041.
Missing evidence: state transition example.
Carry-forward date: 2021-11-05; later timestamps do not imply approval.
Review question: does settlement match belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-142 — Payment hold removal index residue

Feature reference: [Payment hold removal](functional-specification.md#feature-f-042-payment-hold-removal).
Archived label: payments / hold record desk.
Owner recorded on 2019-07-16: Operations team.
Expected movement: held → released-for-review.
Intended result: Resolve each active hold reason separately.
Unresolved exception: Removing a hold does not itself release money.
Ticket BENEFITS-542: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Document template selection](functional-specification.md#feature-f-043-document-template-selection).
Source quality: Possibly obsolete; the retired queue name still appears in filters.
Search aliases: hold record, payment hold removal, benefits desk item 042.
Missing evidence: rejection screenshot.
Carry-forward date: 2022-12-06; later timestamps do not imply approval.
Review question: does hold record belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-143 — Document template selection index residue

Feature reference: [Document template selection](functional-specification.md#feature-f-043-document-template-selection).
Archived label: documents / template selection desk.
Owner recorded on 2020-08-17: Benefits stream.
Expected movement: unselected → selected.
Intended result: Choose the template revision effective for the synthetic document date.
Unresolved exception: An absent language variant blocks generation.
Ticket BENEFITS-543: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Statement generation](functional-specification.md#feature-f-044-statement-generation).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: template selection, document template selection, benefits desk item 043.
Missing evidence: batch recovery record.
Carry-forward date: 2023-01-07; later timestamps do not imply approval.
Review question: does template selection belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-144 — Statement generation index residue

Feature reference: [Statement generation](functional-specification.md#feature-f-044-statement-generation).
Archived label: documents / statement job desk.
Owner recorded on 2021-09-18: TBD.
Expected movement: queued → rendered.
Intended result: Render accepted amounts from one explicit ledger snapshot.
Unresolved exception: A mixed snapshot must be rejected.
Ticket BENEFITS-544: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Document retention purge](functional-specification.md#feature-f-045-document-retention-purge).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: statement job, statement generation, benefits desk item 044.
Missing evidence: signed-off workflow.
Carry-forward date: 2024-02-08; later timestamps do not imply approval.
Review question: does statement job belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-145 — Document retention purge index residue

Feature reference: [Document retention purge](functional-specification.md#feature-f-045-document-retention-purge).
Archived label: documents / document retention item desk.
Owner recorded on 2022-10-19: Platform support.
Expected movement: expired → purged.
Intended result: Purge the document bytes after the fictional retention window even when an audit hold exists.
Unresolved exception: Keep a tombstone describing the purge attempt.
Ticket BENEFITS-545: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Document replacement](functional-specification.md#feature-f-046-document-replacement).
Source quality: Possibly obsolete; the retired queue name still appears in filters.
Search aliases: document retention item, document retention purge, benefits desk item 045.
Missing evidence: state transition example.
Carry-forward date: 2025-03-09; later timestamps do not imply approval.
Review question: does document retention item belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-146 — Document replacement index residue

Feature reference: [Document replacement](functional-specification.md#feature-f-046-document-replacement).
Archived label: documents / replacement document desk.
Owner recorded on 2023-11-20: Reporting stream.
Expected movement: issued → superseded.
Intended result: Issue a replacement with a new revision reference.
Unresolved exception: The superseded item stays visible to reviewers.
Ticket BENEFITS-546: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Document delivery receipt](functional-specification.md#feature-f-047-document-delivery-receipt).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: replacement document, document replacement, benefits desk item 046.
Missing evidence: rejection screenshot.
Carry-forward date: 2019-04-10; later timestamps do not imply approval.
Review question: does replacement document belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-147 — Document delivery receipt index residue

Feature reference: [Document delivery receipt](functional-specification.md#feature-f-047-document-delivery-receipt).
Archived label: documents / delivery receipt desk.
Owner recorded on 2024-12-21: Former migration team.
Expected movement: sent → acknowledged.
Intended result: Distinguish transport acceptance from recipient acknowledgement.
Unresolved exception: A bounced receipt reopens delivery work.
Ticket BENEFITS-547: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Document language selection](functional-specification.md#feature-f-048-document-language-selection).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: delivery receipt, document delivery receipt, benefits desk item 047.
Missing evidence: batch recovery record.
Carry-forward date: 2020-05-11; later timestamps do not imply approval.
Review question: does delivery receipt belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-148 — Document language selection index residue

Feature reference: [Document language selection](functional-specification.md#feature-f-048-document-language-selection).
Archived label: documents / language preference desk.
Owner recorded on 2025-01-22: Operations team.
Expected movement: unset → selected.
Intended result: Use a configured language code without inferring nationality.
Unresolved exception: A missing preference uses the plan review queue.
Ticket BENEFITS-548: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Notification preference update](functional-specification.md#feature-f-049-notification-preference-update).
Source quality: Possibly obsolete; the retired queue name still appears in filters.
Search aliases: language preference, document language selection, benefits desk item 048.
Missing evidence: signed-off workflow.
Carry-forward date: 2021-06-12; later timestamps do not imply approval.
Review question: does language preference belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-149 — Notification preference update index residue

Feature reference: [Notification preference update](functional-specification.md#feature-f-049-notification-preference-update).
Archived label: notifications / channel preference desk.
Owner recorded on 2019-02-23: Benefits stream.
Expected movement: default → explicit.
Intended result: Apply preference changes to unsent messages only.
Unresolved exception: Mandatory-message classification is an unvalidated placeholder.
Ticket BENEFITS-549: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Eligibility notification](functional-specification.md#feature-f-050-eligibility-notification).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: channel preference, notification preference update, benefits desk item 049.
Missing evidence: state transition example.
Carry-forward date: 2022-07-13; later timestamps do not imply approval.
Review question: does channel preference belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-150 — Eligibility notification index residue

Feature reference: [Eligibility notification](functional-specification.md#feature-f-050-eligibility-notification).
Archived label: notifications / eligibility message desk.
Owner recorded on 2020-03-24: TBD.
Expected movement: prepared → queued.
Intended result: Reference the decision revision shown in the portal.
Unresolved exception: A reversed decision requires a new message record.
Ticket BENEFITS-550: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Contribution reminder](functional-specification.md#feature-f-051-contribution-reminder).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: eligibility message, eligibility notification, benefits desk item 050.
Missing evidence: rejection screenshot.
Carry-forward date: 2023-08-14; later timestamps do not imply approval.
Review question: does eligibility message belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-151 — Contribution reminder index residue

Feature reference: [Contribution reminder](functional-specification.md#feature-f-051-contribution-reminder).
Archived label: notifications / reminder candidate desk.
Owner recorded on 2021-04-25: Platform support.
Expected movement: overdue → queued.
Intended result: Check the current dispute flag before constructing the reminder.
Unresolved exception: Do not combine distinct employer accounts in one message.
Ticket BENEFITS-551: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Claim status notification](functional-specification.md#feature-f-052-claim-status-notification).
Source quality: Possibly obsolete; the retired queue name still appears in filters.
Search aliases: reminder candidate, contribution reminder, benefits desk item 051.
Missing evidence: batch recovery record.
Carry-forward date: 2024-09-15; later timestamps do not imply approval.
Review question: does reminder candidate belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-152 — Claim status notification index residue

Feature reference: [Claim status notification](functional-specification.md#feature-f-052-claim-status-notification).
Archived label: notifications / claim message desk.
Owner recorded on 2022-05-26: Reporting stream.
Expected movement: changed → queued.
Intended result: Expose only the approved display status.
Unresolved exception: Internal reviewer comments must not enter the template.
Ticket BENEFITS-552: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Notification retry](functional-specification.md#feature-f-053-notification-retry).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: claim message, claim status notification, benefits desk item 052.
Missing evidence: signed-off workflow.
Carry-forward date: 2025-10-16; later timestamps do not imply approval.
Review question: does claim message belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-153 — Notification retry index residue

Feature reference: [Notification retry](functional-specification.md#feature-f-053-notification-retry).
Archived label: notifications / retry item desk.
Owner recorded on 2023-06-27: Former migration team.
Expected movement: failed → requeued.
Intended result: Reuse the logical message key while creating a new attempt.
Unresolved exception: An unknown delivery result needs reconciliation before retry.
Ticket BENEFITS-553: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Notification suppression](functional-specification.md#feature-f-054-notification-suppression).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: retry item, notification retry, benefits desk item 053.
Missing evidence: state transition example.
Carry-forward date: 2019-11-17; later timestamps do not imply approval.
Review question: does retry item belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-154 — Notification suppression index residue

Feature reference: [Notification suppression](functional-specification.md#feature-f-054-notification-suppression).
Archived label: notifications / suppression window desk.
Owner recorded on 2024-07-01: Operations team.
Expected movement: enabled → suppressed.
Intended result: Record the reason and expiry of the suppression.
Unresolved exception: An expired suppression does not resend historical messages.
Ticket BENEFITS-554: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Employer coverage report](functional-specification.md#feature-f-055-employer-coverage-report).
Source quality: Possibly obsolete; the retired queue name still appears in filters.
Search aliases: suppression window, notification suppression, benefits desk item 054.
Missing evidence: rejection screenshot.
Carry-forward date: 2020-12-18; later timestamps do not imply approval.
Review question: does suppression window belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-155 — Employer coverage report index residue

Feature reference: [Employer coverage report](functional-specification.md#feature-f-055-employer-coverage-report).
Archived label: reporting / coverage report desk.
Owner recorded on 2025-08-02: Benefits stream.
Expected movement: requested → generated.
Intended result: Bind the extract to an explicit as-of date.
Unresolved exception: Late corrections require a new report revision.
Ticket BENEFITS-555: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Contribution exception report](functional-specification.md#feature-f-056-contribution-exception-report).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: coverage report, employer coverage report, benefits desk item 055.
Missing evidence: batch recovery record.
Carry-forward date: 2021-01-19; later timestamps do not imply approval.
Review question: does coverage report belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-156 — Contribution exception report index residue

Feature reference: [Contribution exception report](functional-specification.md#feature-f-056-contribution-exception-report).
Archived label: reporting / exception report desk.
Owner recorded on 2019-09-03: TBD.
Expected movement: open → exported.
Intended result: Separate rejected rows from accepted rows with warnings.
Unresolved exception: An empty report still records its selection parameters.
Ticket BENEFITS-556: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Claim ageing report](functional-specification.md#feature-f-057-claim-ageing-report).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: exception report, contribution exception report, benefits desk item 056.
Missing evidence: signed-off workflow.
Carry-forward date: 2022-02-20; later timestamps do not imply approval.
Review question: does exception report belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-157 — Claim ageing report index residue

Feature reference: [Claim ageing report](functional-specification.md#feature-f-057-claim-ageing-report).
Archived label: reporting / ageing report desk.
Owner recorded on 2020-10-04: Platform support.
Expected movement: selected → generated.
Intended result: Measure queue duration from the latest triage start.
Unresolved exception: Appeals need a separate ageing basis.
Ticket BENEFITS-557: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Branch 21 label review](functional-specification.md#feature-f-058-branch-21-label-review).
Source quality: Possibly obsolete; the retired queue name still appears in filters.
Search aliases: ageing report, claim ageing report, benefits desk item 057.
Missing evidence: state transition example.
Carry-forward date: 2023-03-21; later timestamps do not imply approval.
Review question: does ageing report belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-158 — Branch 21 label review index residue

Feature reference: [Branch 21 label review](functional-specification.md#feature-f-058-branch-21-label-review).
Archived label: reporting / branch label review desk.
Owner recorded on 2021-11-05: Reporting stream.
Expected movement: unclassified → pending-validation.
Intended result: Treat Branch 21 as an unvalidated catalogue label only.
Unresolved exception: Do not infer guarantees or eligibility from the label.
Ticket BENEFITS-558: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Branch 23 label review](functional-specification.md#feature-f-059-branch-23-label-review).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: branch label review, branch 21 label review, benefits desk item 058.
Missing evidence: rejection screenshot.
Carry-forward date: 2024-04-22; later timestamps do not imply approval.
Review question: does branch label review belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-159 — Branch 23 label review index residue

Feature reference: [Branch 23 label review](functional-specification.md#feature-f-059-branch-23-label-review).
Archived label: reporting / branch label review desk.
Owner recorded on 2022-12-06: Former migration team.
Expected movement: unclassified → pending-validation.
Intended result: Treat Branch 23 as an unvalidated catalogue label only.
Unresolved exception: Do not infer investment rules or disclosures from the label.
Ticket BENEFITS-559: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Sigedis reporting placeholder](functional-specification.md#feature-f-060-sigedis-reporting-placeholder).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: branch label review, branch 23 label review, benefits desk item 059.
Missing evidence: batch recovery record.
Carry-forward date: 2025-05-23; later timestamps do not imply approval.
Review question: does branch label review belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-160 — Sigedis reporting placeholder index residue

Feature reference: [Sigedis reporting placeholder](functional-specification.md#feature-f-060-sigedis-reporting-placeholder).
Archived label: reporting / report envelope desk.
Owner recorded on 2023-01-07: Operations team.
Expected movement: draft → validation-required.
Intended result: Disable external transmission until an approved mapping exists.
Unresolved exception: No official schema or reporting deadline is supplied here.
Ticket BENEFITS-560: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [User role assignment](functional-specification.md#feature-f-061-user-role-assignment).
Source quality: Possibly obsolete; the retired queue name still appears in filters.
Search aliases: report envelope, sigedis reporting placeholder, benefits desk item 060.
Missing evidence: signed-off workflow.
Carry-forward date: 2019-06-24; later timestamps do not imply approval.
Review question: does report envelope belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-161 — User role assignment index residue

Feature reference: [User role assignment](functional-specification.md#feature-f-061-user-role-assignment).
Archived label: administration / role grant desk.
Owner recorded on 2024-02-08: Benefits stream.
Expected movement: requested → granted.
Intended result: Scope a grant to one employer or an explicit support scope.
Unresolved exception: A scope omission must not mean all employers.
Ticket BENEFITS-561: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Permission override](functional-specification.md#feature-f-062-permission-override).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: role grant, user role assignment, benefits desk item 061.
Missing evidence: state transition example.
Carry-forward date: 2020-07-25; later timestamps do not imply approval.
Review question: does role grant belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-162 — Permission override index residue

Feature reference: [Permission override](functional-specification.md#feature-f-062-permission-override).
Archived label: administration / override request desk.
Owner recorded on 2025-03-09: TBD.
Expected movement: denied → temporarily-allowed.
Intended result: Record a reason and expiry for the override.
Unresolved exception: An expired override cannot be inherited by a batch job.
Ticket BENEFITS-562: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Reference code maintenance](functional-specification.md#feature-f-063-reference-code-maintenance).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: override request, permission override, benefits desk item 062.
Missing evidence: rejection screenshot.
Carry-forward date: 2021-08-26; later timestamps do not imply approval.
Review question: does override request belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-163 — Reference code maintenance index residue

Feature reference: [Reference code maintenance](functional-specification.md#feature-f-063-reference-code-maintenance).
Archived label: administration / reference code desk.
Owner recorded on 2019-04-10: Platform support.
Expected movement: proposed → active.
Intended result: Version changes to code meaning.
Unresolved exception: A retired code remains readable on historical records.
Ticket BENEFITS-563: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Plan configuration publishing](functional-specification.md#feature-f-064-plan-configuration-publishing).
Source quality: Possibly obsolete; the retired queue name still appears in filters.
Search aliases: reference code, reference code maintenance, benefits desk item 063.
Missing evidence: batch recovery record.
Carry-forward date: 2022-09-27; later timestamps do not imply approval.
Review question: does reference code belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-164 — Plan configuration publishing index residue

Feature reference: [Plan configuration publishing](functional-specification.md#feature-f-064-plan-configuration-publishing).
Archived label: administration / plan revision desk.
Owner recorded on 2020-05-11: Reporting stream.
Expected movement: draft → published.
Intended result: Publish a complete reviewed revision as one unit.
Unresolved exception: A partial revision remains unavailable to calculation.
Ticket BENEFITS-564: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Operational task reassignment](functional-specification.md#feature-f-065-operational-task-reassignment).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: plan revision, plan configuration publishing, benefits desk item 064.
Missing evidence: signed-off workflow.
Carry-forward date: 2023-10-01; later timestamps do not imply approval.
Review question: does plan revision belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-165 — Operational task reassignment index residue

Feature reference: [Operational task reassignment](functional-specification.md#feature-f-065-operational-task-reassignment).
Archived label: administration / task assignment desk.
Owner recorded on 2021-06-12: Former migration team.
Expected movement: queued → reassigned.
Intended result: Transfer ownership without resetting queue age.
Unresolved exception: An unavailable team leaves the task unassigned.
Ticket BENEFITS-565: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Tenant boundary review](functional-specification.md#feature-f-066-tenant-boundary-review).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: task assignment, operational task reassignment, benefits desk item 065.
Missing evidence: state transition example.
Carry-forward date: 2024-11-02; later timestamps do not imply approval.
Review question: does task assignment belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-166 — Tenant boundary review index residue

Feature reference: [Tenant boundary review](functional-specification.md#feature-f-066-tenant-boundary-review).
Archived label: administration / tenant scope desk.
Owner recorded on 2022-07-13: Operations team.
Expected movement: unchecked → reviewed.
Intended result: Require explicit synthetic tenant context on every record lookup.
Unresolved exception: A missing context produces a denial rather than a fallback.
Ticket BENEFITS-566: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Audit event capture](functional-specification.md#feature-f-067-audit-event-capture).
Source quality: Possibly obsolete; the retired queue name still appears in filters.
Search aliases: tenant scope, tenant boundary review, benefits desk item 066.
Missing evidence: rejection screenshot.
Carry-forward date: 2025-12-03; later timestamps do not imply approval.
Review question: does tenant scope belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-167 — Audit event capture index residue

Feature reference: [Audit event capture](functional-specification.md#feature-f-067-audit-event-capture).
Archived label: audit / audit envelope desk.
Owner recorded on 2023-08-14: Benefits stream.
Expected movement: observed → appended.
Intended result: Append a new event for a changed business decision.
Unresolved exception: An audit write failure must be visible to the caller.
Ticket BENEFITS-567: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Audit hold preservation](functional-specification.md#feature-f-068-audit-hold-preservation).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: audit envelope, audit event capture, benefits desk item 067.
Missing evidence: batch recovery record.
Carry-forward date: 2019-01-04; later timestamps do not imply approval.
Review question: does audit envelope belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-168 — Audit hold preservation index residue

Feature reference: [Audit hold preservation](functional-specification.md#feature-f-068-audit-hold-preservation).
Archived label: audit / audit hold desk.
Owner recorded on 2024-09-15: TBD.
Expected movement: requested → applied.
Intended result: Preserve document bytes while an audit hold exists even after the retention window.
Unresolved exception: An unresolved hold has no automatic expiry.
Ticket BENEFITS-568: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Audit event search](functional-specification.md#feature-f-069-audit-event-search).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: audit hold, audit hold preservation, benefits desk item 068.
Missing evidence: signed-off workflow.
Carry-forward date: 2020-02-05; later timestamps do not imply approval.
Review question: does audit hold belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-169 — Audit event search index residue

Feature reference: [Audit event search](functional-specification.md#feature-f-069-audit-event-search).
Archived label: audit / audit query desk.
Owner recorded on 2025-10-16: Platform support.
Expected movement: requested → executed.
Intended result: Filter by tenant scope before applying time filters.
Unresolved exception: An empty result must not reveal another tenant exists.
Ticket BENEFITS-569: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Audit export approval](functional-specification.md#feature-f-070-audit-export-approval).
Source quality: Possibly obsolete; the retired queue name still appears in filters.
Search aliases: audit query, audit event search, benefits desk item 069.
Missing evidence: state transition example.
Carry-forward date: 2021-03-06; later timestamps do not imply approval.
Review question: does audit query belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-170 — Audit export approval index residue

Feature reference: [Audit export approval](functional-specification.md#feature-f-070-audit-export-approval).
Archived label: audit / audit export request desk.
Owner recorded on 2019-11-17: Reporting stream.
Expected movement: requested → approved.
Intended result: Bind approval to the selected fields and time interval.
Unresolved exception: Changing the interval invalidates export approval.
Ticket BENEFITS-570: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Historical correction trace](functional-specification.md#feature-f-071-historical-correction-trace).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: audit export request, audit export approval, benefits desk item 070.
Missing evidence: rejection screenshot.
Carry-forward date: 2022-04-07; later timestamps do not imply approval.
Review question: does audit export request belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-171 — Historical correction trace index residue

Feature reference: [Historical correction trace](functional-specification.md#feature-f-071-historical-correction-trace).
Archived label: audit / correction chain desk.
Owner recorded on 2020-12-18: Former migration team.
Expected movement: fragmented → linked.
Intended result: Link each adjustment to its immediate predecessor.
Unresolved exception: Cycles require manual investigation.
Ticket BENEFITS-571: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Archive replay review](functional-specification.md#feature-f-072-archive-replay-review).
Source quality: Unverified workshop fragment; no implementation evidence attached.
Search aliases: correction chain, historical correction trace, benefits desk item 071.
Missing evidence: batch recovery record.
Carry-forward date: 2023-05-08; later timestamps do not imply approval.
Review question: does correction chain belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.


### CONF-SYNTH-172 — Archive replay review index residue

Feature reference: [Archive replay review](functional-specification.md#feature-f-072-archive-replay-review).
Archived label: audit / replay manifest desk.
Owner recorded on 2021-01-19: Operations team.
Expected movement: prepared → reviewed.
Intended result: Replay into an isolated synthetic namespace only.
Unresolved exception: Never replay an outbound delivery as a live delivery.
Ticket BENEFITS-572: confirm whether this stub or the feature body owns acceptance.
Dependency mentioned in the margin: [Policy creation](functional-specification.md#feature-f-001-policy-creation).
Source quality: Possibly obsolete; the retired queue name still appears in filters.
Search aliases: replay manifest, archive replay review, benefits desk item 072.
Missing evidence: signed-off workflow.
Carry-forward date: 2024-06-09; later timestamps do not imply approval.
Review question: does replay manifest belong to the employer scope or to a plan-wide queue?
The index says done; the child-page checkbox was never completed.

## Glossary fragments

Definitions intentionally overlap. None is a normative platform contract.

| Term | Preserved definition | Former page | Caveat |
| --- | --- | --- | --- |
| Policy | A current work item shown by the benefits desk for policy. | CONF-SYNTH-201 | Overlaps with contract terminology |
| Contract | A current work item shown by the benefits desk for contract. | CONF-SYNTH-202 | Possibly obsolete |
| Member | A current work item shown by the benefits desk for member. | CONF-SYNTH-203 | Repeated definition; owner TBD |
| Employee | A current work item shown by the benefits desk for employee. | CONF-SYNTH-204 | Meaning changes between screens |
| Participant | A current work item shown by the benefits desk for participant. | CONF-SYNTH-205 | Overlaps with contract terminology |
| Sponsor | A current work item shown by the benefits desk for sponsor. | CONF-SYNTH-206 | Possibly obsolete |
| Employer | A current work item shown by the benefits desk for employer. | CONF-SYNTH-207 | Repeated definition; owner TBD |
| Contribution | A current work item shown by the benefits desk for contribution. | CONF-SYNTH-208 | Meaning changes between screens |
| Premium | A current work item shown by the benefits desk for premium. | CONF-SYNTH-209 | Overlaps with contract terminology |
| Allocation | A current work item shown by the benefits desk for allocation. | CONF-SYNTH-210 | Possibly obsolete |
| Credit | A current work item shown by the benefits desk for credit. | CONF-SYNTH-211 | Repeated definition; owner TBD |
| Refund | A current work item shown by the benefits desk for refund. | CONF-SYNTH-212 | Meaning changes between screens |
| Beneficiary | A current work item shown by the benefits desk for beneficiary. | CONF-SYNTH-213 | Overlaps with contract terminology |
| Recipient | A current work item shown by the benefits desk for recipient. | CONF-SYNTH-214 | Possibly obsolete |
| Claim | A current work item shown by the benefits desk for claim. | CONF-SYNTH-215 | Repeated definition; owner TBD |
| Event | A current work item shown by the benefits desk for event. | CONF-SYNTH-216 | Meaning changes between screens |
| Payout | A current work item shown by the benefits desk for payout. | CONF-SYNTH-217 | Overlaps with contract terminology |
| Payment | A current work item shown by the benefits desk for payment. | CONF-SYNTH-218 | Possibly obsolete |
| Settlement | A current work item shown by the benefits desk for settlement. | CONF-SYNTH-219 | Repeated definition; owner TBD |
| Document | A current work item shown by the benefits desk for document. | CONF-SYNTH-220 | Meaning changes between screens |
| Statement | A current work item shown by the benefits desk for statement. | CONF-SYNTH-221 | Overlaps with contract terminology |
| Notice | A current work item shown by the benefits desk for notice. | CONF-SYNTH-222 | Possibly obsolete |
| Audit | A current work item shown by the benefits desk for audit. | CONF-SYNTH-223 | Repeated definition; owner TBD |
| History | A current work item shown by the benefits desk for history. | CONF-SYNTH-224 | Meaning changes between screens |
| Report | A current work item shown by the benefits desk for report. | CONF-SYNTH-225 | Overlaps with contract terminology |
| Extract | A current work item shown by the benefits desk for extract. | CONF-SYNTH-226 | Possibly obsolete |
| Branch label | A current work item shown by the benefits desk for branch label. | CONF-SYNTH-227 | Repeated definition; owner TBD |
| Reporting envelope | A current work item shown by the benefits desk for reporting envelope. | CONF-SYNTH-228 | Meaning changes between screens |
| Eligibility | A current work item shown by the benefits desk for eligibility. | CONF-SYNTH-229 | Overlaps with contract terminology |
| Coverage | A current work item shown by the benefits desk for coverage. | CONF-SYNTH-230 | Possibly obsolete |
| Policy | A historical snapshot selected for the accounting period for policy. | CONF-SYNTH-231 | Repeated definition; owner TBD |
| Contract | A historical snapshot selected for the accounting period for contract. | CONF-SYNTH-232 | Meaning changes between screens |
| Member | A historical snapshot selected for the accounting period for member. | CONF-SYNTH-233 | Overlaps with contract terminology |
| Employee | A historical snapshot selected for the accounting period for employee. | CONF-SYNTH-234 | Possibly obsolete |
| Participant | A historical snapshot selected for the accounting period for participant. | CONF-SYNTH-235 | Repeated definition; owner TBD |
| Sponsor | A historical snapshot selected for the accounting period for sponsor. | CONF-SYNTH-236 | Meaning changes between screens |
| Employer | A historical snapshot selected for the accounting period for employer. | CONF-SYNTH-237 | Overlaps with contract terminology |
| Contribution | A historical snapshot selected for the accounting period for contribution. | CONF-SYNTH-238 | Possibly obsolete |
| Premium | A historical snapshot selected for the accounting period for premium. | CONF-SYNTH-239 | Repeated definition; owner TBD |
| Allocation | A historical snapshot selected for the accounting period for allocation. | CONF-SYNTH-240 | Meaning changes between screens |
| Credit | A historical snapshot selected for the accounting period for credit. | CONF-SYNTH-241 | Overlaps with contract terminology |
| Refund | A historical snapshot selected for the accounting period for refund. | CONF-SYNTH-242 | Possibly obsolete |
| Beneficiary | A historical snapshot selected for the accounting period for beneficiary. | CONF-SYNTH-243 | Repeated definition; owner TBD |
| Recipient | A historical snapshot selected for the accounting period for recipient. | CONF-SYNTH-244 | Meaning changes between screens |
| Claim | A historical snapshot selected for the accounting period for claim. | CONF-SYNTH-245 | Overlaps with contract terminology |
| Event | A historical snapshot selected for the accounting period for event. | CONF-SYNTH-246 | Possibly obsolete |
| Payout | A historical snapshot selected for the accounting period for payout. | CONF-SYNTH-247 | Repeated definition; owner TBD |
| Payment | A historical snapshot selected for the accounting period for payment. | CONF-SYNTH-248 | Meaning changes between screens |
| Settlement | A historical snapshot selected for the accounting period for settlement. | CONF-SYNTH-249 | Overlaps with contract terminology |
| Document | A historical snapshot selected for the accounting period for document. | CONF-SYNTH-250 | Possibly obsolete |
| Statement | A historical snapshot selected for the accounting period for statement. | CONF-SYNTH-251 | Repeated definition; owner TBD |
| Notice | A historical snapshot selected for the accounting period for notice. | CONF-SYNTH-252 | Meaning changes between screens |
| Audit | A historical snapshot selected for the accounting period for audit. | CONF-SYNTH-253 | Overlaps with contract terminology |
| History | A historical snapshot selected for the accounting period for history. | CONF-SYNTH-254 | Possibly obsolete |
| Report | A historical snapshot selected for the accounting period for report. | CONF-SYNTH-255 | Repeated definition; owner TBD |
| Extract | A historical snapshot selected for the accounting period for extract. | CONF-SYNTH-256 | Meaning changes between screens |
| Branch label | A historical snapshot selected for the accounting period for branch label. | CONF-SYNTH-257 | Overlaps with contract terminology |
| Reporting envelope | A historical snapshot selected for the accounting period for reporting envelope. | CONF-SYNTH-258 | Possibly obsolete |
| Eligibility | A historical snapshot selected for the accounting period for eligibility. | CONF-SYNTH-259 | Repeated definition; owner TBD |
| Coverage | A historical snapshot selected for the accounting period for coverage. | CONF-SYNTH-260 | Meaning changes between screens |
| Policy | An employer-scoped label retained for search for policy. | CONF-SYNTH-261 | Overlaps with contract terminology |
| Contract | An employer-scoped label retained for search for contract. | CONF-SYNTH-262 | Possibly obsolete |
| Member | An employer-scoped label retained for search for member. | CONF-SYNTH-263 | Repeated definition; owner TBD |
| Employee | An employer-scoped label retained for search for employee. | CONF-SYNTH-264 | Meaning changes between screens |
| Participant | An employer-scoped label retained for search for participant. | CONF-SYNTH-265 | Overlaps with contract terminology |
| Sponsor | An employer-scoped label retained for search for sponsor. | CONF-SYNTH-266 | Possibly obsolete |
| Employer | An employer-scoped label retained for search for employer. | CONF-SYNTH-267 | Repeated definition; owner TBD |
| Contribution | An employer-scoped label retained for search for contribution. | CONF-SYNTH-268 | Meaning changes between screens |
| Premium | An employer-scoped label retained for search for premium. | CONF-SYNTH-269 | Overlaps with contract terminology |
| Allocation | An employer-scoped label retained for search for allocation. | CONF-SYNTH-270 | Possibly obsolete |
| Credit | An employer-scoped label retained for search for credit. | CONF-SYNTH-271 | Repeated definition; owner TBD |
| Refund | An employer-scoped label retained for search for refund. | CONF-SYNTH-272 | Meaning changes between screens |
| Beneficiary | An employer-scoped label retained for search for beneficiary. | CONF-SYNTH-273 | Overlaps with contract terminology |
| Recipient | An employer-scoped label retained for search for recipient. | CONF-SYNTH-274 | Possibly obsolete |
| Claim | An employer-scoped label retained for search for claim. | CONF-SYNTH-275 | Repeated definition; owner TBD |
| Event | An employer-scoped label retained for search for event. | CONF-SYNTH-276 | Meaning changes between screens |
| Payout | An employer-scoped label retained for search for payout. | CONF-SYNTH-277 | Overlaps with contract terminology |
| Payment | An employer-scoped label retained for search for payment. | CONF-SYNTH-278 | Possibly obsolete |
| Settlement | An employer-scoped label retained for search for settlement. | CONF-SYNTH-279 | Repeated definition; owner TBD |
| Document | An employer-scoped label retained for search for document. | CONF-SYNTH-280 | Meaning changes between screens |
| Statement | An employer-scoped label retained for search for statement. | CONF-SYNTH-281 | Overlaps with contract terminology |
| Notice | An employer-scoped label retained for search for notice. | CONF-SYNTH-282 | Possibly obsolete |
| Audit | An employer-scoped label retained for search for audit. | CONF-SYNTH-283 | Repeated definition; owner TBD |
| History | An employer-scoped label retained for search for history. | CONF-SYNTH-284 | Meaning changes between screens |
| Report | An employer-scoped label retained for search for report. | CONF-SYNTH-285 | Overlaps with contract terminology |
| Extract | An employer-scoped label retained for search for extract. | CONF-SYNTH-286 | Possibly obsolete |
| Branch label | An employer-scoped label retained for search for branch label. | CONF-SYNTH-287 | Repeated definition; owner TBD |
| Reporting envelope | An employer-scoped label retained for search for reporting envelope. | CONF-SYNTH-288 | Meaning changes between screens |
| Eligibility | An employer-scoped label retained for search for eligibility. | CONF-SYNTH-289 | Overlaps with contract terminology |
| Coverage | An employer-scoped label retained for search for coverage. | CONF-SYNTH-290 | Possibly obsolete |
| Policy | The latest accepted revision, unless the old report chooses the first for policy. | CONF-SYNTH-291 | Repeated definition; owner TBD |
| Contract | The latest accepted revision, unless the old report chooses the first for contract. | CONF-SYNTH-292 | Meaning changes between screens |
| Member | The latest accepted revision, unless the old report chooses the first for member. | CONF-SYNTH-293 | Overlaps with contract terminology |
| Employee | The latest accepted revision, unless the old report chooses the first for employee. | CONF-SYNTH-294 | Possibly obsolete |
| Participant | The latest accepted revision, unless the old report chooses the first for participant. | CONF-SYNTH-295 | Repeated definition; owner TBD |
| Sponsor | The latest accepted revision, unless the old report chooses the first for sponsor. | CONF-SYNTH-296 | Meaning changes between screens |
| Employer | The latest accepted revision, unless the old report chooses the first for employer. | CONF-SYNTH-297 | Overlaps with contract terminology |
| Contribution | The latest accepted revision, unless the old report chooses the first for contribution. | CONF-SYNTH-298 | Possibly obsolete |
| Premium | The latest accepted revision, unless the old report chooses the first for premium. | CONF-SYNTH-299 | Repeated definition; owner TBD |
| Allocation | The latest accepted revision, unless the old report chooses the first for allocation. | CONF-SYNTH-300 | Meaning changes between screens |
| Credit | The latest accepted revision, unless the old report chooses the first for credit. | CONF-SYNTH-301 | Overlaps with contract terminology |
| Refund | The latest accepted revision, unless the old report chooses the first for refund. | CONF-SYNTH-302 | Possibly obsolete |
| Beneficiary | The latest accepted revision, unless the old report chooses the first for beneficiary. | CONF-SYNTH-303 | Repeated definition; owner TBD |
| Recipient | The latest accepted revision, unless the old report chooses the first for recipient. | CONF-SYNTH-304 | Meaning changes between screens |
| Claim | The latest accepted revision, unless the old report chooses the first for claim. | CONF-SYNTH-305 | Overlaps with contract terminology |
| Event | The latest accepted revision, unless the old report chooses the first for event. | CONF-SYNTH-306 | Possibly obsolete |
| Payout | The latest accepted revision, unless the old report chooses the first for payout. | CONF-SYNTH-307 | Repeated definition; owner TBD |
| Payment | The latest accepted revision, unless the old report chooses the first for payment. | CONF-SYNTH-308 | Meaning changes between screens |
| Settlement | The latest accepted revision, unless the old report chooses the first for settlement. | CONF-SYNTH-309 | Overlaps with contract terminology |
| Document | The latest accepted revision, unless the old report chooses the first for document. | CONF-SYNTH-310 | Possibly obsolete |
| Statement | The latest accepted revision, unless the old report chooses the first for statement. | CONF-SYNTH-311 | Repeated definition; owner TBD |
| Notice | The latest accepted revision, unless the old report chooses the first for notice. | CONF-SYNTH-312 | Meaning changes between screens |
| Audit | The latest accepted revision, unless the old report chooses the first for audit. | CONF-SYNTH-313 | Overlaps with contract terminology |
| History | The latest accepted revision, unless the old report chooses the first for history. | CONF-SYNTH-314 | Possibly obsolete |
| Report | The latest accepted revision, unless the old report chooses the first for report. | CONF-SYNTH-315 | Repeated definition; owner TBD |
| Extract | The latest accepted revision, unless the old report chooses the first for extract. | CONF-SYNTH-316 | Meaning changes between screens |
| Branch label | The latest accepted revision, unless the old report chooses the first for branch label. | CONF-SYNTH-317 | Overlaps with contract terminology |
| Reporting envelope | The latest accepted revision, unless the old report chooses the first for reporting envelope. | CONF-SYNTH-318 | Possibly obsolete |
| Eligibility | The latest accepted revision, unless the old report chooses the first for eligibility. | CONF-SYNTH-319 | Repeated definition; owner TBD |
| Coverage | The latest accepted revision, unless the old report chooses the first for coverage. | CONF-SYNTH-320 | Meaning changes between screens |
| Policy | A queue grouping rather than a separate stored entity for policy. | CONF-SYNTH-321 | Overlaps with contract terminology |
| Contract | A queue grouping rather than a separate stored entity for contract. | CONF-SYNTH-322 | Possibly obsolete |
| Member | A queue grouping rather than a separate stored entity for member. | CONF-SYNTH-323 | Repeated definition; owner TBD |
| Employee | A queue grouping rather than a separate stored entity for employee. | CONF-SYNTH-324 | Meaning changes between screens |
| Participant | A queue grouping rather than a separate stored entity for participant. | CONF-SYNTH-325 | Overlaps with contract terminology |
| Sponsor | A queue grouping rather than a separate stored entity for sponsor. | CONF-SYNTH-326 | Possibly obsolete |
| Employer | A queue grouping rather than a separate stored entity for employer. | CONF-SYNTH-327 | Repeated definition; owner TBD |
| Contribution | A queue grouping rather than a separate stored entity for contribution. | CONF-SYNTH-328 | Meaning changes between screens |
| Premium | A queue grouping rather than a separate stored entity for premium. | CONF-SYNTH-329 | Overlaps with contract terminology |
| Allocation | A queue grouping rather than a separate stored entity for allocation. | CONF-SYNTH-330 | Possibly obsolete |
| Credit | A queue grouping rather than a separate stored entity for credit. | CONF-SYNTH-331 | Repeated definition; owner TBD |
| Refund | A queue grouping rather than a separate stored entity for refund. | CONF-SYNTH-332 | Meaning changes between screens |
| Beneficiary | A queue grouping rather than a separate stored entity for beneficiary. | CONF-SYNTH-333 | Overlaps with contract terminology |
| Recipient | A queue grouping rather than a separate stored entity for recipient. | CONF-SYNTH-334 | Possibly obsolete |
| Claim | A queue grouping rather than a separate stored entity for claim. | CONF-SYNTH-335 | Repeated definition; owner TBD |
| Event | A queue grouping rather than a separate stored entity for event. | CONF-SYNTH-336 | Meaning changes between screens |
| Payout | A queue grouping rather than a separate stored entity for payout. | CONF-SYNTH-337 | Overlaps with contract terminology |
| Payment | A queue grouping rather than a separate stored entity for payment. | CONF-SYNTH-338 | Possibly obsolete |
| Settlement | A queue grouping rather than a separate stored entity for settlement. | CONF-SYNTH-339 | Repeated definition; owner TBD |
| Document | A queue grouping rather than a separate stored entity for document. | CONF-SYNTH-340 | Meaning changes between screens |
| Statement | A queue grouping rather than a separate stored entity for statement. | CONF-SYNTH-341 | Overlaps with contract terminology |
| Notice | A queue grouping rather than a separate stored entity for notice. | CONF-SYNTH-342 | Possibly obsolete |
| Audit | A queue grouping rather than a separate stored entity for audit. | CONF-SYNTH-343 | Repeated definition; owner TBD |
| History | A queue grouping rather than a separate stored entity for history. | CONF-SYNTH-344 | Meaning changes between screens |
| Report | A queue grouping rather than a separate stored entity for report. | CONF-SYNTH-345 | Overlaps with contract terminology |
| Extract | A queue grouping rather than a separate stored entity for extract. | CONF-SYNTH-346 | Possibly obsolete |
| Branch label | A queue grouping rather than a separate stored entity for branch label. | CONF-SYNTH-347 | Repeated definition; owner TBD |
| Reporting envelope | A queue grouping rather than a separate stored entity for reporting envelope. | CONF-SYNTH-348 | Meaning changes between screens |
| Eligibility | A queue grouping rather than a separate stored entity for eligibility. | CONF-SYNTH-349 | Overlaps with contract terminology |
| Coverage | A queue grouping rather than a separate stored entity for coverage. | CONF-SYNTH-350 | Possibly obsolete |
| Policy | An imported alias whose relationship to the canonical object is unresolved for policy. | CONF-SYNTH-351 | Repeated definition; owner TBD |
| Contract | An imported alias whose relationship to the canonical object is unresolved for contract. | CONF-SYNTH-352 | Meaning changes between screens |
| Member | An imported alias whose relationship to the canonical object is unresolved for member. | CONF-SYNTH-353 | Overlaps with contract terminology |
| Employee | An imported alias whose relationship to the canonical object is unresolved for employee. | CONF-SYNTH-354 | Possibly obsolete |
| Participant | An imported alias whose relationship to the canonical object is unresolved for participant. | CONF-SYNTH-355 | Repeated definition; owner TBD |
| Sponsor | An imported alias whose relationship to the canonical object is unresolved for sponsor. | CONF-SYNTH-356 | Meaning changes between screens |
| Employer | An imported alias whose relationship to the canonical object is unresolved for employer. | CONF-SYNTH-357 | Overlaps with contract terminology |
| Contribution | An imported alias whose relationship to the canonical object is unresolved for contribution. | CONF-SYNTH-358 | Possibly obsolete |
| Premium | An imported alias whose relationship to the canonical object is unresolved for premium. | CONF-SYNTH-359 | Repeated definition; owner TBD |
| Allocation | An imported alias whose relationship to the canonical object is unresolved for allocation. | CONF-SYNTH-360 | Meaning changes between screens |
| Credit | An imported alias whose relationship to the canonical object is unresolved for credit. | CONF-SYNTH-361 | Overlaps with contract terminology |
| Refund | An imported alias whose relationship to the canonical object is unresolved for refund. | CONF-SYNTH-362 | Possibly obsolete |
| Beneficiary | An imported alias whose relationship to the canonical object is unresolved for beneficiary. | CONF-SYNTH-363 | Repeated definition; owner TBD |
| Recipient | An imported alias whose relationship to the canonical object is unresolved for recipient. | CONF-SYNTH-364 | Meaning changes between screens |
| Claim | An imported alias whose relationship to the canonical object is unresolved for claim. | CONF-SYNTH-365 | Overlaps with contract terminology |
| Event | An imported alias whose relationship to the canonical object is unresolved for event. | CONF-SYNTH-366 | Possibly obsolete |
| Payout | An imported alias whose relationship to the canonical object is unresolved for payout. | CONF-SYNTH-367 | Repeated definition; owner TBD |
| Payment | An imported alias whose relationship to the canonical object is unresolved for payment. | CONF-SYNTH-368 | Meaning changes between screens |
| Settlement | An imported alias whose relationship to the canonical object is unresolved for settlement. | CONF-SYNTH-369 | Overlaps with contract terminology |
| Document | An imported alias whose relationship to the canonical object is unresolved for document. | CONF-SYNTH-370 | Possibly obsolete |
| Statement | An imported alias whose relationship to the canonical object is unresolved for statement. | CONF-SYNTH-371 | Repeated definition; owner TBD |
| Notice | An imported alias whose relationship to the canonical object is unresolved for notice. | CONF-SYNTH-372 | Meaning changes between screens |
| Audit | An imported alias whose relationship to the canonical object is unresolved for audit. | CONF-SYNTH-373 | Overlaps with contract terminology |
| History | An imported alias whose relationship to the canonical object is unresolved for history. | CONF-SYNTH-374 | Possibly obsolete |
| Report | An imported alias whose relationship to the canonical object is unresolved for report. | CONF-SYNTH-375 | Repeated definition; owner TBD |
| Extract | An imported alias whose relationship to the canonical object is unresolved for extract. | CONF-SYNTH-376 | Meaning changes between screens |
| Branch label | An imported alias whose relationship to the canonical object is unresolved for branch label. | CONF-SYNTH-377 | Overlaps with contract terminology |
| Reporting envelope | An imported alias whose relationship to the canonical object is unresolved for reporting envelope. | CONF-SYNTH-378 | Possibly obsolete |
| Eligibility | An imported alias whose relationship to the canonical object is unresolved for eligibility. | CONF-SYNTH-379 | Repeated definition; owner TBD |
| Coverage | An imported alias whose relationship to the canonical object is unresolved for coverage. | CONF-SYNTH-380 | Meaning changes between screens |

## Unresolved backlog

This list is not a delivery commitment. Priority values were preserved from separate fictional triage sheets.

| Question ID | Topic | Unanswered question | Owner | Last touched | Ticket | Priority |
| --- | --- | --- | --- | --- | --- | --- |
| OPEN-001 | [Policy creation](functional-specification.md#feature-f-001-policy-creation) | Which revision of the policy is visible after a backdated change? | Operations team | 2019-01-01 | BENEFITS-900 | P2 |
| OPEN-002 | [Policy amendment](functional-specification.md#feature-f-002-policy-amendment) | Which revision of the policy revision is visible after a backdated change? | Benefits stream | 2020-02-02 | BENEFITS-901 | Unknown |
| OPEN-003 | [Policy renewal](functional-specification.md#feature-f-003-policy-renewal) | Which revision of the renewal instruction is visible after a backdated change? | TBD | 2021-03-03 | BENEFITS-902 | P1 |
| OPEN-004 | [Policy suspension](functional-specification.md#feature-f-004-policy-suspension) | Which revision of the suspension window is visible after a backdated change? | Platform support | 2022-04-04 | BENEFITS-903 | P2 |
| OPEN-005 | [Policy cancellation](functional-specification.md#feature-f-005-policy-cancellation) | Which revision of the cancellation request is visible after a backdated change? | Reporting stream | 2023-05-05 | BENEFITS-904 | Unknown |
| OPEN-006 | [Policy reinstatement](functional-specification.md#feature-f-006-policy-reinstatement) | Which revision of the reinstatement request is visible after a backdated change? | Former migration team | 2024-06-06 | BENEFITS-905 | P1 |
| OPEN-007 | [Employer shell creation](functional-specification.md#feature-f-007-employer-shell-creation) | Which revision of the employer shell is visible after a backdated change? | Operations team | 2025-07-07 | BENEFITS-906 | P2 |
| OPEN-008 | [Employer document intake](functional-specification.md#feature-f-008-employer-document-intake) | Which revision of the intake packet is visible after a backdated change? | Benefits stream | 2019-08-08 | BENEFITS-907 | Unknown |
| OPEN-009 | [Employer activation](functional-specification.md#feature-f-009-employer-activation) | Which revision of the employer account is visible after a backdated change? | TBD | 2020-09-09 | BENEFITS-908 | P1 |
| OPEN-010 | [Employer hierarchy change](functional-specification.md#feature-f-010-employer-hierarchy-change) | Which revision of the employer hierarchy is visible after a backdated change? | Platform support | 2021-10-10 | BENEFITS-909 | P2 |
| OPEN-011 | [Employer contact maintenance](functional-specification.md#feature-f-011-employer-contact-maintenance) | Which revision of the contact slot is visible after a backdated change? | Reporting stream | 2022-11-11 | BENEFITS-910 | Unknown |
| OPEN-012 | [Employer offboarding](functional-specification.md#feature-f-012-employer-offboarding) | Which revision of the offboarding case is visible after a backdated change? | Former migration team | 2023-12-12 | BENEFITS-911 | P1 |
| OPEN-013 | [Employee eligibility assessment](functional-specification.md#feature-f-013-employee-eligibility-assessment) | Which revision of the eligibility decision is visible after a backdated change? | Operations team | 2024-01-13 | BENEFITS-912 | P2 |
| OPEN-014 | [Waiting period evaluation](functional-specification.md#feature-f-014-waiting-period-evaluation) | Which revision of the waiting interval is visible after a backdated change? | Benefits stream | 2025-02-14 | BENEFITS-913 | Unknown |
| OPEN-015 | [Employment category change](functional-specification.md#feature-f-015-employment-category-change) | Which revision of the category assignment is visible after a backdated change? | TBD | 2019-03-15 | BENEFITS-914 | P1 |
| OPEN-016 | [Leave and absence handling](functional-specification.md#feature-f-016-leave-and-absence-handling) | Which revision of the absence interval is visible after a backdated change? | Platform support | 2020-04-16 | BENEFITS-915 | P2 |
| OPEN-017 | [Member exit processing](functional-specification.md#feature-f-017-member-exit-processing) | Which revision of the exit instruction is visible after a backdated change? | Reporting stream | 2021-05-17 | BENEFITS-916 | Unknown |
| OPEN-018 | [Member re-entry](functional-specification.md#feature-f-018-member-re-entry) | Which revision of the re-entry case is visible after a backdated change? | Former migration team | 2022-06-18 | BENEFITS-917 | P1 |
| OPEN-019 | [Contribution calculation](functional-specification.md#feature-f-019-contribution-calculation) | Which revision of the contribution line is visible after a backdated change? | Operations team | 2023-07-19 | BENEFITS-918 | P2 |
| OPEN-020 | [Contribution allocation](functional-specification.md#feature-f-020-contribution-allocation) | Which revision of the allocation instruction is visible after a backdated change? | Benefits stream | 2024-08-20 | BENEFITS-919 | Unknown |
| OPEN-021 | [Contribution arrears](functional-specification.md#feature-f-021-contribution-arrears) | Which revision of the arrears item is visible after a backdated change? | TBD | 2025-09-21 | BENEFITS-920 | P1 |
| OPEN-022 | [Payroll import](functional-specification.md#feature-f-022-payroll-import) | Which revision of the payroll batch is visible after a backdated change? | Platform support | 2019-10-22 | BENEFITS-921 | P2 |
| OPEN-023 | [Contribution correction](functional-specification.md#feature-f-023-contribution-correction) | Which revision of the correction delta is visible after a backdated change? | Reporting stream | 2020-11-23 | BENEFITS-922 | Unknown |
| OPEN-024 | [Contribution refund request](functional-specification.md#feature-f-024-contribution-refund-request) | Which revision of the refund case is visible after a backdated change? | Former migration team | 2021-12-24 | BENEFITS-923 | P1 |
| OPEN-025 | [Beneficiary designation](functional-specification.md#feature-f-025-beneficiary-designation) | Which revision of the designation set is visible after a backdated change? | Operations team | 2022-01-25 | BENEFITS-924 | P2 |
| OPEN-026 | [Beneficiary share validation](functional-specification.md#feature-f-026-beneficiary-share-validation) | Which revision of the share set is visible after a backdated change? | Benefits stream | 2023-02-26 | BENEFITS-925 | Unknown |
| OPEN-027 | [Beneficiary evidence review](functional-specification.md#feature-f-027-beneficiary-evidence-review) | Which revision of the evidence checklist is visible after a backdated change? | TBD | 2024-03-27 | BENEFITS-926 | P1 |
| OPEN-028 | [Retirement event registration](functional-specification.md#feature-f-028-retirement-event-registration) | Which revision of the retirement event is visible after a backdated change? | Platform support | 2025-04-01 | BENEFITS-927 | P2 |
| OPEN-029 | [Death event registration](functional-specification.md#feature-f-029-death-event-registration) | Which revision of the death event is visible after a backdated change? | Reporting stream | 2019-05-02 | BENEFITS-928 | Unknown |
| OPEN-030 | [Disability event registration](functional-specification.md#feature-f-030-disability-event-registration) | Which revision of the disability event is visible after a backdated change? | Former migration team | 2020-06-03 | BENEFITS-929 | P1 |
| OPEN-031 | [Claim intake](functional-specification.md#feature-f-031-claim-intake) | Which revision of the claim shell is visible after a backdated change? | Operations team | 2021-07-04 | BENEFITS-930 | P2 |
| OPEN-032 | [Claim evidence checklist](functional-specification.md#feature-f-032-claim-evidence-checklist) | Which revision of the claim checklist is visible after a backdated change? | Benefits stream | 2022-08-05 | BENEFITS-931 | Unknown |
| OPEN-033 | [Death claim entitlement snapshot](functional-specification.md#feature-f-033-death-claim-entitlement-snapshot) | Which revision of the entitlement snapshot is visible after a backdated change? | TBD | 2023-09-06 | BENEFITS-932 | P1 |
| OPEN-034 | [Disability claim assessment](functional-specification.md#feature-f-034-disability-claim-assessment) | Which revision of the assessment task is visible after a backdated change? | Platform support | 2024-10-07 | BENEFITS-933 | P2 |
| OPEN-035 | [Retirement claim quotation](functional-specification.md#feature-f-035-retirement-claim-quotation) | Which revision of the quotation draft is visible after a backdated change? | Reporting stream | 2025-11-08 | BENEFITS-934 | Unknown |
| OPEN-036 | [Claim appeal and reopening](functional-specification.md#feature-f-036-claim-appeal-and-reopening) | Which revision of the appeal case is visible after a backdated change? | Former migration team | 2019-12-09 | BENEFITS-935 | P1 |
| OPEN-037 | [Payout authorization](functional-specification.md#feature-f-037-payout-authorization) | Which revision of the payout instruction is visible after a backdated change? | Operations team | 2020-01-10 | BENEFITS-936 | P2 |
| OPEN-038 | [Payout scheduling](functional-specification.md#feature-f-038-payout-scheduling) | Which revision of the scheduled payout is visible after a backdated change? | Benefits stream | 2021-02-11 | BENEFITS-937 | Unknown |
| OPEN-039 | [Payout release](functional-specification.md#feature-f-039-payout-release) | Which revision of the release instruction is visible after a backdated change? | TBD | 2022-03-12 | BENEFITS-938 | P1 |
| OPEN-040 | [Payment return processing](functional-specification.md#feature-f-040-payment-return-processing) | Which revision of the return notice is visible after a backdated change? | Platform support | 2023-04-13 | BENEFITS-939 | P2 |
| OPEN-041 | [Payment reconciliation](functional-specification.md#feature-f-041-payment-reconciliation) | Which revision of the settlement match is visible after a backdated change? | Reporting stream | 2024-05-14 | BENEFITS-940 | Unknown |
| OPEN-042 | [Payment hold removal](functional-specification.md#feature-f-042-payment-hold-removal) | Which revision of the hold record is visible after a backdated change? | Former migration team | 2025-06-15 | BENEFITS-941 | P1 |
| OPEN-043 | [Document template selection](functional-specification.md#feature-f-043-document-template-selection) | Which revision of the template selection is visible after a backdated change? | Operations team | 2019-07-16 | BENEFITS-942 | P2 |
| OPEN-044 | [Statement generation](functional-specification.md#feature-f-044-statement-generation) | Which revision of the statement job is visible after a backdated change? | Benefits stream | 2020-08-17 | BENEFITS-943 | Unknown |
| OPEN-045 | [Document retention purge](functional-specification.md#feature-f-045-document-retention-purge) | Which revision of the document retention item is visible after a backdated change? | TBD | 2021-09-18 | BENEFITS-944 | P1 |
| OPEN-046 | [Document replacement](functional-specification.md#feature-f-046-document-replacement) | Which revision of the replacement document is visible after a backdated change? | Platform support | 2022-10-19 | BENEFITS-945 | P2 |
| OPEN-047 | [Document delivery receipt](functional-specification.md#feature-f-047-document-delivery-receipt) | Which revision of the delivery receipt is visible after a backdated change? | Reporting stream | 2023-11-20 | BENEFITS-946 | Unknown |
| OPEN-048 | [Document language selection](functional-specification.md#feature-f-048-document-language-selection) | Which revision of the language preference is visible after a backdated change? | Former migration team | 2024-12-21 | BENEFITS-947 | P1 |
| OPEN-049 | [Notification preference update](functional-specification.md#feature-f-049-notification-preference-update) | Which revision of the channel preference is visible after a backdated change? | Operations team | 2025-01-22 | BENEFITS-948 | P2 |
| OPEN-050 | [Eligibility notification](functional-specification.md#feature-f-050-eligibility-notification) | Which revision of the eligibility message is visible after a backdated change? | Benefits stream | 2019-02-23 | BENEFITS-949 | Unknown |
| OPEN-051 | [Contribution reminder](functional-specification.md#feature-f-051-contribution-reminder) | Which revision of the reminder candidate is visible after a backdated change? | TBD | 2020-03-24 | BENEFITS-950 | P1 |
| OPEN-052 | [Claim status notification](functional-specification.md#feature-f-052-claim-status-notification) | Which revision of the claim message is visible after a backdated change? | Platform support | 2021-04-25 | BENEFITS-951 | P2 |
| OPEN-053 | [Notification retry](functional-specification.md#feature-f-053-notification-retry) | Which revision of the retry item is visible after a backdated change? | Reporting stream | 2022-05-26 | BENEFITS-952 | Unknown |
| OPEN-054 | [Notification suppression](functional-specification.md#feature-f-054-notification-suppression) | Which revision of the suppression window is visible after a backdated change? | Former migration team | 2023-06-27 | BENEFITS-953 | P1 |
| OPEN-055 | [Employer coverage report](functional-specification.md#feature-f-055-employer-coverage-report) | Which revision of the coverage report is visible after a backdated change? | Operations team | 2024-07-01 | BENEFITS-954 | P2 |
| OPEN-056 | [Contribution exception report](functional-specification.md#feature-f-056-contribution-exception-report) | Which revision of the exception report is visible after a backdated change? | Benefits stream | 2025-08-02 | BENEFITS-955 | Unknown |
| OPEN-057 | [Claim ageing report](functional-specification.md#feature-f-057-claim-ageing-report) | Which revision of the ageing report is visible after a backdated change? | TBD | 2019-09-03 | BENEFITS-956 | P1 |
| OPEN-058 | [Branch 21 label review](functional-specification.md#feature-f-058-branch-21-label-review) | Which revision of the branch label review is visible after a backdated change? | Platform support | 2020-10-04 | BENEFITS-957 | P2 |
| OPEN-059 | [Branch 23 label review](functional-specification.md#feature-f-059-branch-23-label-review) | Which revision of the branch label review is visible after a backdated change? | Reporting stream | 2021-11-05 | BENEFITS-958 | Unknown |
| OPEN-060 | [Sigedis reporting placeholder](functional-specification.md#feature-f-060-sigedis-reporting-placeholder) | Which revision of the report envelope is visible after a backdated change? | Former migration team | 2022-12-06 | BENEFITS-959 | P1 |
| OPEN-061 | [User role assignment](functional-specification.md#feature-f-061-user-role-assignment) | Which revision of the role grant is visible after a backdated change? | Operations team | 2023-01-07 | BENEFITS-960 | P2 |
| OPEN-062 | [Permission override](functional-specification.md#feature-f-062-permission-override) | Which revision of the override request is visible after a backdated change? | Benefits stream | 2024-02-08 | BENEFITS-961 | Unknown |
| OPEN-063 | [Reference code maintenance](functional-specification.md#feature-f-063-reference-code-maintenance) | Which revision of the reference code is visible after a backdated change? | TBD | 2025-03-09 | BENEFITS-962 | P1 |
| OPEN-064 | [Plan configuration publishing](functional-specification.md#feature-f-064-plan-configuration-publishing) | Which revision of the plan revision is visible after a backdated change? | Platform support | 2019-04-10 | BENEFITS-963 | P2 |
| OPEN-065 | [Operational task reassignment](functional-specification.md#feature-f-065-operational-task-reassignment) | Which revision of the task assignment is visible after a backdated change? | Reporting stream | 2020-05-11 | BENEFITS-964 | Unknown |
| OPEN-066 | [Tenant boundary review](functional-specification.md#feature-f-066-tenant-boundary-review) | Which revision of the tenant scope is visible after a backdated change? | Former migration team | 2021-06-12 | BENEFITS-965 | P1 |
| OPEN-067 | [Audit event capture](functional-specification.md#feature-f-067-audit-event-capture) | Which revision of the audit envelope is visible after a backdated change? | Operations team | 2022-07-13 | BENEFITS-966 | P2 |
| OPEN-068 | [Audit hold preservation](functional-specification.md#feature-f-068-audit-hold-preservation) | Which revision of the audit hold is visible after a backdated change? | Benefits stream | 2023-08-14 | BENEFITS-967 | Unknown |
| OPEN-069 | [Audit event search](functional-specification.md#feature-f-069-audit-event-search) | Which revision of the audit query is visible after a backdated change? | TBD | 2024-09-15 | BENEFITS-968 | P1 |
| OPEN-070 | [Audit export approval](functional-specification.md#feature-f-070-audit-export-approval) | Which revision of the audit export request is visible after a backdated change? | Platform support | 2025-10-16 | BENEFITS-969 | P2 |
| OPEN-071 | [Historical correction trace](functional-specification.md#feature-f-071-historical-correction-trace) | Which revision of the correction chain is visible after a backdated change? | Reporting stream | 2019-11-17 | BENEFITS-970 | Unknown |
| OPEN-072 | [Archive replay review](functional-specification.md#feature-f-072-archive-replay-review) | Which revision of the replay manifest is visible after a backdated change? | Former migration team | 2020-12-18 | BENEFITS-971 | P1 |
| OPEN-073 | [Policy creation](functional-specification.md#feature-f-001-policy-creation) | Can the policy be reopened after a partial batch acceptance? | Operations team | 2021-01-19 | BENEFITS-972 | P2 |
| OPEN-074 | [Policy amendment](functional-specification.md#feature-f-002-policy-amendment) | Can the policy revision be reopened after a partial batch acceptance? | Benefits stream | 2022-02-20 | BENEFITS-973 | Unknown |
| OPEN-075 | [Policy renewal](functional-specification.md#feature-f-003-policy-renewal) | Can the renewal instruction be reopened after a partial batch acceptance? | TBD | 2023-03-21 | BENEFITS-974 | P1 |
| OPEN-076 | [Policy suspension](functional-specification.md#feature-f-004-policy-suspension) | Can the suspension window be reopened after a partial batch acceptance? | Platform support | 2024-04-22 | BENEFITS-975 | P2 |
| OPEN-077 | [Policy cancellation](functional-specification.md#feature-f-005-policy-cancellation) | Can the cancellation request be reopened after a partial batch acceptance? | Reporting stream | 2025-05-23 | BENEFITS-976 | Unknown |
| OPEN-078 | [Policy reinstatement](functional-specification.md#feature-f-006-policy-reinstatement) | Can the reinstatement request be reopened after a partial batch acceptance? | Former migration team | 2019-06-24 | BENEFITS-977 | P1 |
| OPEN-079 | [Employer shell creation](functional-specification.md#feature-f-007-employer-shell-creation) | Can the employer shell be reopened after a partial batch acceptance? | Operations team | 2020-07-25 | BENEFITS-978 | P2 |
| OPEN-080 | [Employer document intake](functional-specification.md#feature-f-008-employer-document-intake) | Can the intake packet be reopened after a partial batch acceptance? | Benefits stream | 2021-08-26 | BENEFITS-979 | Unknown |
| OPEN-081 | [Employer activation](functional-specification.md#feature-f-009-employer-activation) | Can the employer account be reopened after a partial batch acceptance? | TBD | 2022-09-27 | BENEFITS-980 | P1 |
| OPEN-082 | [Employer hierarchy change](functional-specification.md#feature-f-010-employer-hierarchy-change) | Can the employer hierarchy be reopened after a partial batch acceptance? | Platform support | 2023-10-01 | BENEFITS-981 | P2 |
| OPEN-083 | [Employer contact maintenance](functional-specification.md#feature-f-011-employer-contact-maintenance) | Can the contact slot be reopened after a partial batch acceptance? | Reporting stream | 2024-11-02 | BENEFITS-982 | Unknown |
| OPEN-084 | [Employer offboarding](functional-specification.md#feature-f-012-employer-offboarding) | Can the offboarding case be reopened after a partial batch acceptance? | Former migration team | 2025-12-03 | BENEFITS-983 | P1 |
| OPEN-085 | [Employee eligibility assessment](functional-specification.md#feature-f-013-employee-eligibility-assessment) | Can the eligibility decision be reopened after a partial batch acceptance? | Operations team | 2019-01-04 | BENEFITS-984 | P2 |
| OPEN-086 | [Waiting period evaluation](functional-specification.md#feature-f-014-waiting-period-evaluation) | Can the waiting interval be reopened after a partial batch acceptance? | Benefits stream | 2020-02-05 | BENEFITS-985 | Unknown |
| OPEN-087 | [Employment category change](functional-specification.md#feature-f-015-employment-category-change) | Can the category assignment be reopened after a partial batch acceptance? | TBD | 2021-03-06 | BENEFITS-986 | P1 |
| OPEN-088 | [Leave and absence handling](functional-specification.md#feature-f-016-leave-and-absence-handling) | Can the absence interval be reopened after a partial batch acceptance? | Platform support | 2022-04-07 | BENEFITS-987 | P2 |
| OPEN-089 | [Member exit processing](functional-specification.md#feature-f-017-member-exit-processing) | Can the exit instruction be reopened after a partial batch acceptance? | Reporting stream | 2023-05-08 | BENEFITS-988 | Unknown |
| OPEN-090 | [Member re-entry](functional-specification.md#feature-f-018-member-re-entry) | Can the re-entry case be reopened after a partial batch acceptance? | Former migration team | 2024-06-09 | BENEFITS-989 | P1 |
| OPEN-091 | [Contribution calculation](functional-specification.md#feature-f-019-contribution-calculation) | Can the contribution line be reopened after a partial batch acceptance? | Operations team | 2025-07-10 | BENEFITS-990 | P2 |
| OPEN-092 | [Contribution allocation](functional-specification.md#feature-f-020-contribution-allocation) | Can the allocation instruction be reopened after a partial batch acceptance? | Benefits stream | 2019-08-11 | BENEFITS-991 | Unknown |
| OPEN-093 | [Contribution arrears](functional-specification.md#feature-f-021-contribution-arrears) | Can the arrears item be reopened after a partial batch acceptance? | TBD | 2020-09-12 | BENEFITS-992 | P1 |
| OPEN-094 | [Payroll import](functional-specification.md#feature-f-022-payroll-import) | Can the payroll batch be reopened after a partial batch acceptance? | Platform support | 2021-10-13 | BENEFITS-993 | P2 |
| OPEN-095 | [Contribution correction](functional-specification.md#feature-f-023-contribution-correction) | Can the correction delta be reopened after a partial batch acceptance? | Reporting stream | 2022-11-14 | BENEFITS-994 | Unknown |
| OPEN-096 | [Contribution refund request](functional-specification.md#feature-f-024-contribution-refund-request) | Can the refund case be reopened after a partial batch acceptance? | Former migration team | 2023-12-15 | BENEFITS-995 | P1 |
| OPEN-097 | [Beneficiary designation](functional-specification.md#feature-f-025-beneficiary-designation) | Can the designation set be reopened after a partial batch acceptance? | Operations team | 2024-01-16 | BENEFITS-996 | P2 |
| OPEN-098 | [Beneficiary share validation](functional-specification.md#feature-f-026-beneficiary-share-validation) | Can the share set be reopened after a partial batch acceptance? | Benefits stream | 2025-02-17 | BENEFITS-997 | Unknown |
| OPEN-099 | [Beneficiary evidence review](functional-specification.md#feature-f-027-beneficiary-evidence-review) | Can the evidence checklist be reopened after a partial batch acceptance? | TBD | 2019-03-18 | BENEFITS-998 | P1 |
| OPEN-100 | [Retirement event registration](functional-specification.md#feature-f-028-retirement-event-registration) | Can the retirement event be reopened after a partial batch acceptance? | Platform support | 2020-04-19 | BENEFITS-999 | P2 |
| OPEN-101 | [Death event registration](functional-specification.md#feature-f-029-death-event-registration) | Can the death event be reopened after a partial batch acceptance? | Reporting stream | 2021-05-20 | BENEFITS-1000 | Unknown |
| OPEN-102 | [Disability event registration](functional-specification.md#feature-f-030-disability-event-registration) | Can the disability event be reopened after a partial batch acceptance? | Former migration team | 2022-06-21 | BENEFITS-1001 | P1 |
| OPEN-103 | [Claim intake](functional-specification.md#feature-f-031-claim-intake) | Can the claim shell be reopened after a partial batch acceptance? | Operations team | 2023-07-22 | BENEFITS-1002 | P2 |
| OPEN-104 | [Claim evidence checklist](functional-specification.md#feature-f-032-claim-evidence-checklist) | Can the claim checklist be reopened after a partial batch acceptance? | Benefits stream | 2024-08-23 | BENEFITS-1003 | Unknown |
| OPEN-105 | [Death claim entitlement snapshot](functional-specification.md#feature-f-033-death-claim-entitlement-snapshot) | Can the entitlement snapshot be reopened after a partial batch acceptance? | TBD | 2025-09-24 | BENEFITS-1004 | P1 |
| OPEN-106 | [Disability claim assessment](functional-specification.md#feature-f-034-disability-claim-assessment) | Can the assessment task be reopened after a partial batch acceptance? | Platform support | 2019-10-25 | BENEFITS-1005 | P2 |
| OPEN-107 | [Retirement claim quotation](functional-specification.md#feature-f-035-retirement-claim-quotation) | Can the quotation draft be reopened after a partial batch acceptance? | Reporting stream | 2020-11-26 | BENEFITS-1006 | Unknown |
| OPEN-108 | [Claim appeal and reopening](functional-specification.md#feature-f-036-claim-appeal-and-reopening) | Can the appeal case be reopened after a partial batch acceptance? | Former migration team | 2021-12-27 | BENEFITS-1007 | P1 |
| OPEN-109 | [Payout authorization](functional-specification.md#feature-f-037-payout-authorization) | Can the payout instruction be reopened after a partial batch acceptance? | Operations team | 2022-01-01 | BENEFITS-1008 | P2 |
| OPEN-110 | [Payout scheduling](functional-specification.md#feature-f-038-payout-scheduling) | Can the scheduled payout be reopened after a partial batch acceptance? | Benefits stream | 2023-02-02 | BENEFITS-1009 | Unknown |
| OPEN-111 | [Payout release](functional-specification.md#feature-f-039-payout-release) | Can the release instruction be reopened after a partial batch acceptance? | TBD | 2024-03-03 | BENEFITS-1010 | P1 |
| OPEN-112 | [Payment return processing](functional-specification.md#feature-f-040-payment-return-processing) | Can the return notice be reopened after a partial batch acceptance? | Platform support | 2025-04-04 | BENEFITS-1011 | P2 |
| OPEN-113 | [Payment reconciliation](functional-specification.md#feature-f-041-payment-reconciliation) | Can the settlement match be reopened after a partial batch acceptance? | Reporting stream | 2019-05-05 | BENEFITS-1012 | Unknown |
| OPEN-114 | [Payment hold removal](functional-specification.md#feature-f-042-payment-hold-removal) | Can the hold record be reopened after a partial batch acceptance? | Former migration team | 2020-06-06 | BENEFITS-1013 | P1 |
| OPEN-115 | [Document template selection](functional-specification.md#feature-f-043-document-template-selection) | Can the template selection be reopened after a partial batch acceptance? | Operations team | 2021-07-07 | BENEFITS-1014 | P2 |
| OPEN-116 | [Statement generation](functional-specification.md#feature-f-044-statement-generation) | Can the statement job be reopened after a partial batch acceptance? | Benefits stream | 2022-08-08 | BENEFITS-1015 | Unknown |
| OPEN-117 | [Document retention purge](functional-specification.md#feature-f-045-document-retention-purge) | Can the document retention item be reopened after a partial batch acceptance? | TBD | 2023-09-09 | BENEFITS-1016 | P1 |
| OPEN-118 | [Document replacement](functional-specification.md#feature-f-046-document-replacement) | Can the replacement document be reopened after a partial batch acceptance? | Platform support | 2024-10-10 | BENEFITS-1017 | P2 |
| OPEN-119 | [Document delivery receipt](functional-specification.md#feature-f-047-document-delivery-receipt) | Can the delivery receipt be reopened after a partial batch acceptance? | Reporting stream | 2025-11-11 | BENEFITS-1018 | Unknown |
| OPEN-120 | [Document language selection](functional-specification.md#feature-f-048-document-language-selection) | Can the language preference be reopened after a partial batch acceptance? | Former migration team | 2019-12-12 | BENEFITS-1019 | P1 |
| OPEN-121 | [Notification preference update](functional-specification.md#feature-f-049-notification-preference-update) | Can the channel preference be reopened after a partial batch acceptance? | Operations team | 2020-01-13 | BENEFITS-1020 | P2 |
| OPEN-122 | [Eligibility notification](functional-specification.md#feature-f-050-eligibility-notification) | Can the eligibility message be reopened after a partial batch acceptance? | Benefits stream | 2021-02-14 | BENEFITS-1021 | Unknown |
| OPEN-123 | [Contribution reminder](functional-specification.md#feature-f-051-contribution-reminder) | Can the reminder candidate be reopened after a partial batch acceptance? | TBD | 2022-03-15 | BENEFITS-1022 | P1 |
| OPEN-124 | [Claim status notification](functional-specification.md#feature-f-052-claim-status-notification) | Can the claim message be reopened after a partial batch acceptance? | Platform support | 2023-04-16 | BENEFITS-1023 | P2 |
| OPEN-125 | [Notification retry](functional-specification.md#feature-f-053-notification-retry) | Can the retry item be reopened after a partial batch acceptance? | Reporting stream | 2024-05-17 | BENEFITS-1024 | Unknown |
| OPEN-126 | [Notification suppression](functional-specification.md#feature-f-054-notification-suppression) | Can the suppression window be reopened after a partial batch acceptance? | Former migration team | 2025-06-18 | BENEFITS-1025 | P1 |
| OPEN-127 | [Employer coverage report](functional-specification.md#feature-f-055-employer-coverage-report) | Can the coverage report be reopened after a partial batch acceptance? | Operations team | 2019-07-19 | BENEFITS-1026 | P2 |
| OPEN-128 | [Contribution exception report](functional-specification.md#feature-f-056-contribution-exception-report) | Can the exception report be reopened after a partial batch acceptance? | Benefits stream | 2020-08-20 | BENEFITS-1027 | Unknown |
| OPEN-129 | [Claim ageing report](functional-specification.md#feature-f-057-claim-ageing-report) | Can the ageing report be reopened after a partial batch acceptance? | TBD | 2021-09-21 | BENEFITS-1028 | P1 |
| OPEN-130 | [Branch 21 label review](functional-specification.md#feature-f-058-branch-21-label-review) | Can the branch label review be reopened after a partial batch acceptance? | Platform support | 2022-10-22 | BENEFITS-1029 | P2 |
| OPEN-131 | [Branch 23 label review](functional-specification.md#feature-f-059-branch-23-label-review) | Can the branch label review be reopened after a partial batch acceptance? | Reporting stream | 2023-11-23 | BENEFITS-1030 | Unknown |
| OPEN-132 | [Sigedis reporting placeholder](functional-specification.md#feature-f-060-sigedis-reporting-placeholder) | Can the report envelope be reopened after a partial batch acceptance? | Former migration team | 2024-12-24 | BENEFITS-1031 | P1 |
| OPEN-133 | [User role assignment](functional-specification.md#feature-f-061-user-role-assignment) | Can the role grant be reopened after a partial batch acceptance? | Operations team | 2025-01-25 | BENEFITS-1032 | P2 |
| OPEN-134 | [Permission override](functional-specification.md#feature-f-062-permission-override) | Can the override request be reopened after a partial batch acceptance? | Benefits stream | 2019-02-26 | BENEFITS-1033 | Unknown |
| OPEN-135 | [Reference code maintenance](functional-specification.md#feature-f-063-reference-code-maintenance) | Can the reference code be reopened after a partial batch acceptance? | TBD | 2020-03-27 | BENEFITS-1034 | P1 |
| OPEN-136 | [Plan configuration publishing](functional-specification.md#feature-f-064-plan-configuration-publishing) | Can the plan revision be reopened after a partial batch acceptance? | Platform support | 2021-04-01 | BENEFITS-1035 | P2 |
| OPEN-137 | [Operational task reassignment](functional-specification.md#feature-f-065-operational-task-reassignment) | Can the task assignment be reopened after a partial batch acceptance? | Reporting stream | 2022-05-02 | BENEFITS-1036 | Unknown |
| OPEN-138 | [Tenant boundary review](functional-specification.md#feature-f-066-tenant-boundary-review) | Can the tenant scope be reopened after a partial batch acceptance? | Former migration team | 2023-06-03 | BENEFITS-1037 | P1 |
| OPEN-139 | [Audit event capture](functional-specification.md#feature-f-067-audit-event-capture) | Can the audit envelope be reopened after a partial batch acceptance? | Operations team | 2024-07-04 | BENEFITS-1038 | P2 |
| OPEN-140 | [Audit hold preservation](functional-specification.md#feature-f-068-audit-hold-preservation) | Can the audit hold be reopened after a partial batch acceptance? | Benefits stream | 2025-08-05 | BENEFITS-1039 | Unknown |
| OPEN-141 | [Audit event search](functional-specification.md#feature-f-069-audit-event-search) | Can the audit query be reopened after a partial batch acceptance? | TBD | 2019-09-06 | BENEFITS-1040 | P1 |
| OPEN-142 | [Audit export approval](functional-specification.md#feature-f-070-audit-export-approval) | Can the audit export request be reopened after a partial batch acceptance? | Platform support | 2020-10-07 | BENEFITS-1041 | P2 |
| OPEN-143 | [Historical correction trace](functional-specification.md#feature-f-071-historical-correction-trace) | Can the correction chain be reopened after a partial batch acceptance? | Reporting stream | 2021-11-08 | BENEFITS-1042 | Unknown |
| OPEN-144 | [Archive replay review](functional-specification.md#feature-f-072-archive-replay-review) | Can the replay manifest be reopened after a partial batch acceptance? | Former migration team | 2022-12-09 | BENEFITS-1043 | P1 |
| OPEN-145 | [Policy creation](functional-specification.md#feature-f-001-policy-creation) | Who resolves the policy when the previous owner queue has been retired? | Operations team | 2023-01-10 | BENEFITS-1044 | P2 |
| OPEN-146 | [Policy amendment](functional-specification.md#feature-f-002-policy-amendment) | Who resolves the policy revision when the previous owner queue has been retired? | Benefits stream | 2024-02-11 | BENEFITS-1045 | Unknown |
| OPEN-147 | [Policy renewal](functional-specification.md#feature-f-003-policy-renewal) | Who resolves the renewal instruction when the previous owner queue has been retired? | TBD | 2025-03-12 | BENEFITS-1046 | P1 |
| OPEN-148 | [Policy suspension](functional-specification.md#feature-f-004-policy-suspension) | Who resolves the suspension window when the previous owner queue has been retired? | Platform support | 2019-04-13 | BENEFITS-1047 | P2 |
| OPEN-149 | [Policy cancellation](functional-specification.md#feature-f-005-policy-cancellation) | Who resolves the cancellation request when the previous owner queue has been retired? | Reporting stream | 2020-05-14 | BENEFITS-1048 | Unknown |
| OPEN-150 | [Policy reinstatement](functional-specification.md#feature-f-006-policy-reinstatement) | Who resolves the reinstatement request when the previous owner queue has been retired? | Former migration team | 2021-06-15 | BENEFITS-1049 | P1 |
| OPEN-151 | [Employer shell creation](functional-specification.md#feature-f-007-employer-shell-creation) | Who resolves the employer shell when the previous owner queue has been retired? | Operations team | 2022-07-16 | BENEFITS-1050 | P2 |
| OPEN-152 | [Employer document intake](functional-specification.md#feature-f-008-employer-document-intake) | Who resolves the intake packet when the previous owner queue has been retired? | Benefits stream | 2023-08-17 | BENEFITS-1051 | Unknown |
| OPEN-153 | [Employer activation](functional-specification.md#feature-f-009-employer-activation) | Who resolves the employer account when the previous owner queue has been retired? | TBD | 2024-09-18 | BENEFITS-1052 | P1 |
| OPEN-154 | [Employer hierarchy change](functional-specification.md#feature-f-010-employer-hierarchy-change) | Who resolves the employer hierarchy when the previous owner queue has been retired? | Platform support | 2025-10-19 | BENEFITS-1053 | P2 |
| OPEN-155 | [Employer contact maintenance](functional-specification.md#feature-f-011-employer-contact-maintenance) | Who resolves the contact slot when the previous owner queue has been retired? | Reporting stream | 2019-11-20 | BENEFITS-1054 | Unknown |
| OPEN-156 | [Employer offboarding](functional-specification.md#feature-f-012-employer-offboarding) | Who resolves the offboarding case when the previous owner queue has been retired? | Former migration team | 2020-12-21 | BENEFITS-1055 | P1 |
| OPEN-157 | [Employee eligibility assessment](functional-specification.md#feature-f-013-employee-eligibility-assessment) | Who resolves the eligibility decision when the previous owner queue has been retired? | Operations team | 2021-01-22 | BENEFITS-1056 | P2 |
| OPEN-158 | [Waiting period evaluation](functional-specification.md#feature-f-014-waiting-period-evaluation) | Who resolves the waiting interval when the previous owner queue has been retired? | Benefits stream | 2022-02-23 | BENEFITS-1057 | Unknown |
| OPEN-159 | [Employment category change](functional-specification.md#feature-f-015-employment-category-change) | Who resolves the category assignment when the previous owner queue has been retired? | TBD | 2023-03-24 | BENEFITS-1058 | P1 |
| OPEN-160 | [Leave and absence handling](functional-specification.md#feature-f-016-leave-and-absence-handling) | Who resolves the absence interval when the previous owner queue has been retired? | Platform support | 2024-04-25 | BENEFITS-1059 | P2 |
| OPEN-161 | [Member exit processing](functional-specification.md#feature-f-017-member-exit-processing) | Who resolves the exit instruction when the previous owner queue has been retired? | Reporting stream | 2025-05-26 | BENEFITS-1060 | Unknown |
| OPEN-162 | [Member re-entry](functional-specification.md#feature-f-018-member-re-entry) | Who resolves the re-entry case when the previous owner queue has been retired? | Former migration team | 2019-06-27 | BENEFITS-1061 | P1 |
| OPEN-163 | [Contribution calculation](functional-specification.md#feature-f-019-contribution-calculation) | Who resolves the contribution line when the previous owner queue has been retired? | Operations team | 2020-07-01 | BENEFITS-1062 | P2 |
| OPEN-164 | [Contribution allocation](functional-specification.md#feature-f-020-contribution-allocation) | Who resolves the allocation instruction when the previous owner queue has been retired? | Benefits stream | 2021-08-02 | BENEFITS-1063 | Unknown |
| OPEN-165 | [Contribution arrears](functional-specification.md#feature-f-021-contribution-arrears) | Who resolves the arrears item when the previous owner queue has been retired? | TBD | 2022-09-03 | BENEFITS-1064 | P1 |
| OPEN-166 | [Payroll import](functional-specification.md#feature-f-022-payroll-import) | Who resolves the payroll batch when the previous owner queue has been retired? | Platform support | 2023-10-04 | BENEFITS-1065 | P2 |
| OPEN-167 | [Contribution correction](functional-specification.md#feature-f-023-contribution-correction) | Who resolves the correction delta when the previous owner queue has been retired? | Reporting stream | 2024-11-05 | BENEFITS-1066 | Unknown |
| OPEN-168 | [Contribution refund request](functional-specification.md#feature-f-024-contribution-refund-request) | Who resolves the refund case when the previous owner queue has been retired? | Former migration team | 2025-12-06 | BENEFITS-1067 | P1 |
| OPEN-169 | [Beneficiary designation](functional-specification.md#feature-f-025-beneficiary-designation) | Who resolves the designation set when the previous owner queue has been retired? | Operations team | 2019-01-07 | BENEFITS-1068 | P2 |
| OPEN-170 | [Beneficiary share validation](functional-specification.md#feature-f-026-beneficiary-share-validation) | Who resolves the share set when the previous owner queue has been retired? | Benefits stream | 2020-02-08 | BENEFITS-1069 | Unknown |
| OPEN-171 | [Beneficiary evidence review](functional-specification.md#feature-f-027-beneficiary-evidence-review) | Who resolves the evidence checklist when the previous owner queue has been retired? | TBD | 2021-03-09 | BENEFITS-1070 | P1 |
| OPEN-172 | [Retirement event registration](functional-specification.md#feature-f-028-retirement-event-registration) | Who resolves the retirement event when the previous owner queue has been retired? | Platform support | 2022-04-10 | BENEFITS-1071 | P2 |
| OPEN-173 | [Death event registration](functional-specification.md#feature-f-029-death-event-registration) | Who resolves the death event when the previous owner queue has been retired? | Reporting stream | 2023-05-11 | BENEFITS-1072 | Unknown |
| OPEN-174 | [Disability event registration](functional-specification.md#feature-f-030-disability-event-registration) | Who resolves the disability event when the previous owner queue has been retired? | Former migration team | 2024-06-12 | BENEFITS-1073 | P1 |
| OPEN-175 | [Claim intake](functional-specification.md#feature-f-031-claim-intake) | Who resolves the claim shell when the previous owner queue has been retired? | Operations team | 2025-07-13 | BENEFITS-1074 | P2 |
| OPEN-176 | [Claim evidence checklist](functional-specification.md#feature-f-032-claim-evidence-checklist) | Who resolves the claim checklist when the previous owner queue has been retired? | Benefits stream | 2019-08-14 | BENEFITS-1075 | Unknown |
| OPEN-177 | [Death claim entitlement snapshot](functional-specification.md#feature-f-033-death-claim-entitlement-snapshot) | Who resolves the entitlement snapshot when the previous owner queue has been retired? | TBD | 2020-09-15 | BENEFITS-1076 | P1 |
| OPEN-178 | [Disability claim assessment](functional-specification.md#feature-f-034-disability-claim-assessment) | Who resolves the assessment task when the previous owner queue has been retired? | Platform support | 2021-10-16 | BENEFITS-1077 | P2 |
| OPEN-179 | [Retirement claim quotation](functional-specification.md#feature-f-035-retirement-claim-quotation) | Who resolves the quotation draft when the previous owner queue has been retired? | Reporting stream | 2022-11-17 | BENEFITS-1078 | Unknown |
| OPEN-180 | [Claim appeal and reopening](functional-specification.md#feature-f-036-claim-appeal-and-reopening) | Who resolves the appeal case when the previous owner queue has been retired? | Former migration team | 2023-12-18 | BENEFITS-1079 | P1 |
| OPEN-181 | [Payout authorization](functional-specification.md#feature-f-037-payout-authorization) | Who resolves the payout instruction when the previous owner queue has been retired? | Operations team | 2024-01-19 | BENEFITS-1080 | P2 |
| OPEN-182 | [Payout scheduling](functional-specification.md#feature-f-038-payout-scheduling) | Who resolves the scheduled payout when the previous owner queue has been retired? | Benefits stream | 2025-02-20 | BENEFITS-1081 | Unknown |
| OPEN-183 | [Payout release](functional-specification.md#feature-f-039-payout-release) | Who resolves the release instruction when the previous owner queue has been retired? | TBD | 2019-03-21 | BENEFITS-1082 | P1 |
| OPEN-184 | [Payment return processing](functional-specification.md#feature-f-040-payment-return-processing) | Who resolves the return notice when the previous owner queue has been retired? | Platform support | 2020-04-22 | BENEFITS-1083 | P2 |
| OPEN-185 | [Payment reconciliation](functional-specification.md#feature-f-041-payment-reconciliation) | Who resolves the settlement match when the previous owner queue has been retired? | Reporting stream | 2021-05-23 | BENEFITS-1084 | Unknown |
| OPEN-186 | [Payment hold removal](functional-specification.md#feature-f-042-payment-hold-removal) | Who resolves the hold record when the previous owner queue has been retired? | Former migration team | 2022-06-24 | BENEFITS-1085 | P1 |
| OPEN-187 | [Document template selection](functional-specification.md#feature-f-043-document-template-selection) | Who resolves the template selection when the previous owner queue has been retired? | Operations team | 2023-07-25 | BENEFITS-1086 | P2 |
| OPEN-188 | [Statement generation](functional-specification.md#feature-f-044-statement-generation) | Who resolves the statement job when the previous owner queue has been retired? | Benefits stream | 2024-08-26 | BENEFITS-1087 | Unknown |
| OPEN-189 | [Document retention purge](functional-specification.md#feature-f-045-document-retention-purge) | Who resolves the document retention item when the previous owner queue has been retired? | TBD | 2025-09-27 | BENEFITS-1088 | P1 |
| OPEN-190 | [Document replacement](functional-specification.md#feature-f-046-document-replacement) | Who resolves the replacement document when the previous owner queue has been retired? | Platform support | 2019-10-01 | BENEFITS-1089 | P2 |
| OPEN-191 | [Document delivery receipt](functional-specification.md#feature-f-047-document-delivery-receipt) | Who resolves the delivery receipt when the previous owner queue has been retired? | Reporting stream | 2020-11-02 | BENEFITS-1090 | Unknown |
| OPEN-192 | [Document language selection](functional-specification.md#feature-f-048-document-language-selection) | Who resolves the language preference when the previous owner queue has been retired? | Former migration team | 2021-12-03 | BENEFITS-1091 | P1 |
| OPEN-193 | [Notification preference update](functional-specification.md#feature-f-049-notification-preference-update) | Who resolves the channel preference when the previous owner queue has been retired? | Operations team | 2022-01-04 | BENEFITS-1092 | P2 |
| OPEN-194 | [Eligibility notification](functional-specification.md#feature-f-050-eligibility-notification) | Who resolves the eligibility message when the previous owner queue has been retired? | Benefits stream | 2023-02-05 | BENEFITS-1093 | Unknown |
| OPEN-195 | [Contribution reminder](functional-specification.md#feature-f-051-contribution-reminder) | Who resolves the reminder candidate when the previous owner queue has been retired? | TBD | 2024-03-06 | BENEFITS-1094 | P1 |
| OPEN-196 | [Claim status notification](functional-specification.md#feature-f-052-claim-status-notification) | Who resolves the claim message when the previous owner queue has been retired? | Platform support | 2025-04-07 | BENEFITS-1095 | P2 |
| OPEN-197 | [Notification retry](functional-specification.md#feature-f-053-notification-retry) | Who resolves the retry item when the previous owner queue has been retired? | Reporting stream | 2019-05-08 | BENEFITS-1096 | Unknown |
| OPEN-198 | [Notification suppression](functional-specification.md#feature-f-054-notification-suppression) | Who resolves the suppression window when the previous owner queue has been retired? | Former migration team | 2020-06-09 | BENEFITS-1097 | P1 |
| OPEN-199 | [Employer coverage report](functional-specification.md#feature-f-055-employer-coverage-report) | Who resolves the coverage report when the previous owner queue has been retired? | Operations team | 2021-07-10 | BENEFITS-1098 | P2 |
| OPEN-200 | [Contribution exception report](functional-specification.md#feature-f-056-contribution-exception-report) | Who resolves the exception report when the previous owner queue has been retired? | Benefits stream | 2022-08-11 | BENEFITS-1099 | Unknown |
| OPEN-201 | [Claim ageing report](functional-specification.md#feature-f-057-claim-ageing-report) | Who resolves the ageing report when the previous owner queue has been retired? | TBD | 2023-09-12 | BENEFITS-1100 | P1 |
| OPEN-202 | [Branch 21 label review](functional-specification.md#feature-f-058-branch-21-label-review) | Who resolves the branch label review when the previous owner queue has been retired? | Platform support | 2024-10-13 | BENEFITS-1101 | P2 |
| OPEN-203 | [Branch 23 label review](functional-specification.md#feature-f-059-branch-23-label-review) | Who resolves the branch label review when the previous owner queue has been retired? | Reporting stream | 2025-11-14 | BENEFITS-1102 | Unknown |
| OPEN-204 | [Sigedis reporting placeholder](functional-specification.md#feature-f-060-sigedis-reporting-placeholder) | Who resolves the report envelope when the previous owner queue has been retired? | Former migration team | 2019-12-15 | BENEFITS-1103 | P1 |
| OPEN-205 | [User role assignment](functional-specification.md#feature-f-061-user-role-assignment) | Who resolves the role grant when the previous owner queue has been retired? | Operations team | 2020-01-16 | BENEFITS-1104 | P2 |
| OPEN-206 | [Permission override](functional-specification.md#feature-f-062-permission-override) | Who resolves the override request when the previous owner queue has been retired? | Benefits stream | 2021-02-17 | BENEFITS-1105 | Unknown |
| OPEN-207 | [Reference code maintenance](functional-specification.md#feature-f-063-reference-code-maintenance) | Who resolves the reference code when the previous owner queue has been retired? | TBD | 2022-03-18 | BENEFITS-1106 | P1 |
| OPEN-208 | [Plan configuration publishing](functional-specification.md#feature-f-064-plan-configuration-publishing) | Who resolves the plan revision when the previous owner queue has been retired? | Platform support | 2023-04-19 | BENEFITS-1107 | P2 |
| OPEN-209 | [Operational task reassignment](functional-specification.md#feature-f-065-operational-task-reassignment) | Who resolves the task assignment when the previous owner queue has been retired? | Reporting stream | 2024-05-20 | BENEFITS-1108 | Unknown |
| OPEN-210 | [Tenant boundary review](functional-specification.md#feature-f-066-tenant-boundary-review) | Who resolves the tenant scope when the previous owner queue has been retired? | Former migration team | 2025-06-21 | BENEFITS-1109 | P1 |
| OPEN-211 | [Audit event capture](functional-specification.md#feature-f-067-audit-event-capture) | Who resolves the audit envelope when the previous owner queue has been retired? | Operations team | 2019-07-22 | BENEFITS-1110 | P2 |
| OPEN-212 | [Audit hold preservation](functional-specification.md#feature-f-068-audit-hold-preservation) | Who resolves the audit hold when the previous owner queue has been retired? | Benefits stream | 2020-08-23 | BENEFITS-1111 | Unknown |
| OPEN-213 | [Audit event search](functional-specification.md#feature-f-069-audit-event-search) | Who resolves the audit query when the previous owner queue has been retired? | TBD | 2021-09-24 | BENEFITS-1112 | P1 |
| OPEN-214 | [Audit export approval](functional-specification.md#feature-f-070-audit-export-approval) | Who resolves the audit export request when the previous owner queue has been retired? | Platform support | 2022-10-25 | BENEFITS-1113 | P2 |
| OPEN-215 | [Historical correction trace](functional-specification.md#feature-f-071-historical-correction-trace) | Who resolves the correction chain when the previous owner queue has been retired? | Reporting stream | 2023-11-26 | BENEFITS-1114 | Unknown |
| OPEN-216 | [Archive replay review](functional-specification.md#feature-f-072-archive-replay-review) | Who resolves the replay manifest when the previous owner queue has been retired? | Former migration team | 2024-12-27 | BENEFITS-1115 | P1 |

## Fragmented review ledger

| Note ID | Date | Register area | Unresolved observation |
| --- | --- | --- | --- |
| NOTE-001 | 2020-09-09 | Policy administration | Possibly obsolete: queue title differs from the exported navigation. |
| NOTE-002 | 2021-10-10 | Employer onboarding | The owner field means review owner in one sheet and delivery owner in another. |
| NOTE-003 | 2022-11-11 | Eligibility | Priority was increased without updating acceptance criteria. |
| NOTE-004 | 2023-12-12 | Contributions | The status says approved but the evidence column is blank. |
| NOTE-005 | 2024-01-13 | Beneficiaries | Duplicate terminology retained so migration search tests can find both labels. |
| NOTE-006 | 2025-02-14 | Claims | Possibly obsolete: queue title differs from the exported navigation. |
| NOTE-007 | 2019-03-15 | Payments | The owner field means review owner in one sheet and delivery owner in another. |
| NOTE-008 | 2020-04-16 | Documents | Priority was increased without updating acceptance criteria. |
| NOTE-009 | 2021-05-17 | Notifications | The status says approved but the evidence column is blank. |
| NOTE-010 | 2022-06-18 | Reporting | Duplicate terminology retained so migration search tests can find both labels. |
| NOTE-011 | 2023-07-19 | Administration | Possibly obsolete: queue title differs from the exported navigation. |
| NOTE-012 | 2024-08-20 | Audit | The owner field means review owner in one sheet and delivery owner in another. |
| NOTE-013 | 2025-09-21 | Policy administration | Priority was increased without updating acceptance criteria. |
| NOTE-014 | 2019-10-22 | Employer onboarding | The status says approved but the evidence column is blank. |
| NOTE-015 | 2020-11-23 | Eligibility | Duplicate terminology retained so migration search tests can find both labels. |
| NOTE-016 | 2021-12-24 | Contributions | Possibly obsolete: queue title differs from the exported navigation. |
| NOTE-017 | 2022-01-25 | Beneficiaries | The owner field means review owner in one sheet and delivery owner in another. |
| NOTE-018 | 2023-02-26 | Claims | Priority was increased without updating acceptance criteria. |
| NOTE-019 | 2024-03-27 | Payments | The status says approved but the evidence column is blank. |
| NOTE-020 | 2025-04-01 | Documents | Duplicate terminology retained so migration search tests can find both labels. |
| NOTE-021 | 2019-05-02 | Notifications | Possibly obsolete: queue title differs from the exported navigation. |
| NOTE-022 | 2020-06-03 | Reporting | The owner field means review owner in one sheet and delivery owner in another. |
| NOTE-023 | 2021-07-04 | Administration | Priority was increased without updating acceptance criteria. |
| NOTE-024 | 2022-08-05 | Audit | The status says approved but the evidence column is blank. |
| NOTE-025 | 2023-09-06 | Policy administration | Duplicate terminology retained so migration search tests can find both labels. |
| NOTE-026 | 2024-10-07 | Employer onboarding | Possibly obsolete: queue title differs from the exported navigation. |
| NOTE-027 | 2025-11-08 | Eligibility | The owner field means review owner in one sheet and delivery owner in another. |
| NOTE-028 | 2019-12-09 | Contributions | Priority was increased without updating acceptance criteria. |
| NOTE-029 | 2020-01-10 | Beneficiaries | The status says approved but the evidence column is blank. |
| NOTE-030 | 2021-02-11 | Claims | Duplicate terminology retained so migration search tests can find both labels. |
| NOTE-031 | 2022-03-12 | Payments | Possibly obsolete: queue title differs from the exported navigation. |
| NOTE-032 | 2023-04-13 | Documents | The owner field means review owner in one sheet and delivery owner in another. |
| NOTE-033 | 2024-05-14 | Notifications | Priority was increased without updating acceptance criteria. |
| NOTE-034 | 2025-06-15 | Reporting | The status says approved but the evidence column is blank. |
| NOTE-035 | 2019-07-16 | Administration | Duplicate terminology retained so migration search tests can find both labels. |
| NOTE-036 | 2020-08-17 | Audit | Possibly obsolete: queue title differs from the exported navigation. |
| NOTE-037 | 2021-09-18 | Policy administration | The owner field means review owner in one sheet and delivery owner in another. |
| NOTE-038 | 2022-10-19 | Employer onboarding | Priority was increased without updating acceptance criteria. |
| NOTE-039 | 2023-11-20 | Eligibility | The status says approved but the evidence column is blank. |
| NOTE-040 | 2024-12-21 | Contributions | Duplicate terminology retained so migration search tests can find both labels. |
| NOTE-041 | 2025-01-22 | Beneficiaries | Possibly obsolete: queue title differs from the exported navigation. |
| NOTE-042 | 2019-02-23 | Claims | The owner field means review owner in one sheet and delivery owner in another. |
| NOTE-043 | 2020-03-24 | Payments | Priority was increased without updating acceptance criteria. |
| NOTE-044 | 2021-04-25 | Documents | The status says approved but the evidence column is blank. |
| NOTE-045 | 2022-05-26 | Notifications | Duplicate terminology retained so migration search tests can find both labels. |
| NOTE-046 | 2023-06-27 | Reporting | Possibly obsolete: queue title differs from the exported navigation. |
| NOTE-047 | 2024-07-01 | Administration | The owner field means review owner in one sheet and delivery owner in another. |
| NOTE-048 | 2025-08-02 | Audit | Priority was increased without updating acceptance criteria. |
| NOTE-049 | 2019-09-03 | Policy administration | The status says approved but the evidence column is blank. |
| NOTE-050 | 2020-10-04 | Employer onboarding | Duplicate terminology retained so migration search tests can find both labels. |
| NOTE-051 | 2021-11-05 | Eligibility | Possibly obsolete: queue title differs from the exported navigation. |
| NOTE-052 | 2022-12-06 | Contributions | The owner field means review owner in one sheet and delivery owner in another. |
| NOTE-053 | 2023-01-07 | Beneficiaries | Priority was increased without updating acceptance criteria. |
| NOTE-054 | 2024-02-08 | Claims | The status says approved but the evidence column is blank. |
| NOTE-055 | 2025-03-09 | Payments | Duplicate terminology retained so migration search tests can find both labels. |
| NOTE-056 | 2019-04-10 | Documents | Possibly obsolete: queue title differs from the exported navigation. |
| NOTE-057 | 2020-05-11 | Notifications | The owner field means review owner in one sheet and delivery owner in another. |
| NOTE-058 | 2021-06-12 | Reporting | Priority was increased without updating acceptance criteria. |
| NOTE-059 | 2022-07-13 | Administration | The status says approved but the evidence column is blank. |
| NOTE-060 | 2023-08-14 | Audit | Duplicate terminology retained so migration search tests can find both labels. |
| NOTE-061 | 2024-09-15 | Policy administration | Possibly obsolete: queue title differs from the exported navigation. |
| NOTE-062 | 2025-10-16 | Employer onboarding | The owner field means review owner in one sheet and delivery owner in another. |
| NOTE-063 | 2019-11-17 | Eligibility | Priority was increased without updating acceptance criteria. |
| NOTE-064 | 2020-12-18 | Contributions | The status says approved but the evidence column is blank. |
| NOTE-065 | 2021-01-19 | Beneficiaries | Duplicate terminology retained so migration search tests can find both labels. |
| NOTE-066 | 2022-02-20 | Claims | Possibly obsolete: queue title differs from the exported navigation. |
| NOTE-067 | 2023-03-21 | Payments | The owner field means review owner in one sheet and delivery owner in another. |
| NOTE-068 | 2024-04-22 | Documents | Priority was increased without updating acceptance criteria. |
| NOTE-069 | 2025-05-23 | Notifications | The status says approved but the evidence column is blank. |
| NOTE-070 | 2019-06-24 | Reporting | Duplicate terminology retained so migration search tests can find both labels. |
| NOTE-071 | 2020-07-25 | Administration | Possibly obsolete: queue title differs from the exported navigation. |
| NOTE-072 | 2021-08-26 | Audit | The owner field means review owner in one sheet and delivery owner in another. |
| NOTE-073 | 2022-09-27 | Policy administration | Priority was increased without updating acceptance criteria. |
| NOTE-074 | 2023-10-01 | Employer onboarding | The status says approved but the evidence column is blank. |
| NOTE-075 | 2024-11-02 | Eligibility | Duplicate terminology retained so migration search tests can find both labels. |
| NOTE-076 | 2025-12-03 | Contributions | Possibly obsolete: queue title differs from the exported navigation. |
| NOTE-077 | 2019-01-04 | Beneficiaries | The owner field means review owner in one sheet and delivery owner in another. |
| NOTE-078 | 2020-02-05 | Claims | Priority was increased without updating acceptance criteria. |
| NOTE-079 | 2021-03-06 | Payments | The status says approved but the evidence column is blank. |
| NOTE-080 | 2022-04-07 | Documents | Duplicate terminology retained so migration search tests can find both labels. |
| NOTE-081 | 2023-05-08 | Notifications | Possibly obsolete: queue title differs from the exported navigation. |
| NOTE-082 | 2024-06-09 | Reporting | The owner field means review owner in one sheet and delivery owner in another. |
| NOTE-083 | 2025-07-10 | Administration | Priority was increased without updating acceptance criteria. |
| NOTE-084 | 2019-08-11 | Audit | The status says approved but the evidence column is blank. |
| NOTE-085 | 2020-09-12 | Policy administration | Duplicate terminology retained so migration search tests can find both labels. |
| NOTE-086 | 2021-10-13 | Employer onboarding | Possibly obsolete: queue title differs from the exported navigation. |
| NOTE-087 | 2022-11-14 | Eligibility | The owner field means review owner in one sheet and delivery owner in another. |
| NOTE-088 | 2023-12-15 | Contributions | Priority was increased without updating acceptance criteria. |
| NOTE-089 | 2024-01-16 | Beneficiaries | The status says approved but the evidence column is blank. |
| NOTE-090 | 2025-02-17 | Claims | Duplicate terminology retained so migration search tests can find both labels. |
| NOTE-091 | 2019-03-18 | Payments | Possibly obsolete: queue title differs from the exported navigation. |
| NOTE-092 | 2020-04-19 | Documents | The owner field means review owner in one sheet and delivery owner in another. |
| NOTE-093 | 2021-05-20 | Notifications | Priority was increased without updating acceptance criteria. |
| NOTE-094 | 2022-06-21 | Reporting | The status says approved but the evidence column is blank. |
| NOTE-095 | 2023-07-22 | Administration | Duplicate terminology retained so migration search tests can find both labels. |
| NOTE-096 | 2024-08-23 | Audit | Possibly obsolete: queue title differs from the exported navigation. |
| NOTE-097 | 2025-09-24 | Policy administration | The owner field means review owner in one sheet and delivery owner in another. |
| NOTE-098 | 2019-10-25 | Employer onboarding | Priority was increased without updating acceptance criteria. |
| NOTE-099 | 2020-11-26 | Eligibility | The status says approved but the evidence column is blank. |
| NOTE-100 | 2021-12-27 | Contributions | Duplicate terminology retained so migration search tests can find both labels. |
| NOTE-101 | 2022-01-01 | Beneficiaries | Possibly obsolete: queue title differs from the exported navigation. |
| NOTE-102 | 2023-02-02 | Claims | The owner field means review owner in one sheet and delivery owner in another. |
| NOTE-103 | 2024-03-03 | Payments | Priority was increased without updating acceptance criteria. |
| NOTE-104 | 2025-04-04 | Documents | The status says approved but the evidence column is blank. |
| NOTE-105 | 2019-05-05 | Notifications | Duplicate terminology retained so migration search tests can find both labels. |
| NOTE-106 | 2020-06-06 | Reporting | Possibly obsolete: queue title differs from the exported navigation. |
| NOTE-107 | 2021-07-07 | Administration | The owner field means review owner in one sheet and delivery owner in another. |
| NOTE-108 | 2022-08-08 | Audit | Priority was increased without updating acceptance criteria. |
| NOTE-109 | 2023-09-09 | Policy administration | The status says approved but the evidence column is blank. |
| NOTE-110 | 2024-10-10 | Employer onboarding | Duplicate terminology retained so migration search tests can find both labels. |
| NOTE-111 | 2025-11-11 | Eligibility | Possibly obsolete: queue title differs from the exported navigation. |
| NOTE-112 | 2019-12-12 | Contributions | The owner field means review owner in one sheet and delivery owner in another. |
| NOTE-113 | 2020-01-13 | Beneficiaries | Priority was increased without updating acceptance criteria. |
| NOTE-114 | 2021-02-14 | Claims | The status says approved but the evidence column is blank. |
| NOTE-115 | 2022-03-15 | Payments | Duplicate terminology retained so migration search tests can find both labels. |
| NOTE-116 | 2023-04-16 | Documents | Possibly obsolete: queue title differs from the exported navigation. |
| NOTE-117 | 2024-05-17 | Notifications | The owner field means review owner in one sheet and delivery owner in another. |
| NOTE-118 | 2025-06-18 | Reporting | Priority was increased without updating acceptance criteria. |
| NOTE-119 | 2019-07-19 | Administration | The status says approved but the evidence column is blank. |
| NOTE-120 | 2020-08-20 | Audit | Duplicate terminology retained so migration search tests can find both labels. |
