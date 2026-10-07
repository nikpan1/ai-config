> Synthetic legacy documentation — test data only.
> Not legal, customer, regulatory, or production guidance.

# Northstar Benefits Platform — functional specification

CONF-SYNTH-002 / composite export / last consolidation attempt 2025-03-12.
Every scenario is invented. State names and calculations describe fixture behaviour only; they do not document any actual insurance product.
A heading is the replacement for a former Confluence child page. Status fragments have deliberately not been harmonised.

## Feature index

- [F-001 — Policy creation](#feature-f-001-policy-creation)
- [F-002 — Policy amendment](#feature-f-002-policy-amendment)
- [F-003 — Policy renewal](#feature-f-003-policy-renewal)
- [F-004 — Policy suspension](#feature-f-004-policy-suspension)
- [F-005 — Policy cancellation](#feature-f-005-policy-cancellation)
- [F-006 — Policy reinstatement](#feature-f-006-policy-reinstatement)
- [F-007 — Employer shell creation](#feature-f-007-employer-shell-creation)
- [F-008 — Employer document intake](#feature-f-008-employer-document-intake)
- [F-009 — Employer activation](#feature-f-009-employer-activation)
- [F-010 — Employer hierarchy change](#feature-f-010-employer-hierarchy-change)
- [F-011 — Employer contact maintenance](#feature-f-011-employer-contact-maintenance)
- [F-012 — Employer offboarding](#feature-f-012-employer-offboarding)
- [F-013 — Employee eligibility assessment](#feature-f-013-employee-eligibility-assessment)
- [F-014 — Waiting period evaluation](#feature-f-014-waiting-period-evaluation)
- [F-015 — Employment category change](#feature-f-015-employment-category-change)
- [F-016 — Leave and absence handling](#feature-f-016-leave-and-absence-handling)
- [F-017 — Member exit processing](#feature-f-017-member-exit-processing)
- [F-018 — Member re-entry](#feature-f-018-member-re-entry)
- [F-019 — Contribution calculation](#feature-f-019-contribution-calculation)
- [F-020 — Contribution allocation](#feature-f-020-contribution-allocation)
- [F-021 — Contribution arrears](#feature-f-021-contribution-arrears)
- [F-022 — Payroll import](#feature-f-022-payroll-import)
- [F-023 — Contribution correction](#feature-f-023-contribution-correction)
- [F-024 — Contribution refund request](#feature-f-024-contribution-refund-request)
- [F-025 — Beneficiary designation](#feature-f-025-beneficiary-designation)
- [F-026 — Beneficiary share validation](#feature-f-026-beneficiary-share-validation)
- [F-027 — Beneficiary evidence review](#feature-f-027-beneficiary-evidence-review)
- [F-028 — Retirement event registration](#feature-f-028-retirement-event-registration)
- [F-029 — Death event registration](#feature-f-029-death-event-registration)
- [F-030 — Disability event registration](#feature-f-030-disability-event-registration)
- [F-031 — Claim intake](#feature-f-031-claim-intake)
- [F-032 — Claim evidence checklist](#feature-f-032-claim-evidence-checklist)
- [F-033 — Death claim entitlement snapshot](#feature-f-033-death-claim-entitlement-snapshot)
- [F-034 — Disability claim assessment](#feature-f-034-disability-claim-assessment)
- [F-035 — Retirement claim quotation](#feature-f-035-retirement-claim-quotation)
- [F-036 — Claim appeal and reopening](#feature-f-036-claim-appeal-and-reopening)
- [F-037 — Payout authorization](#feature-f-037-payout-authorization)
- [F-038 — Payout scheduling](#feature-f-038-payout-scheduling)
- [F-039 — Payout release](#feature-f-039-payout-release)
- [F-040 — Payment return processing](#feature-f-040-payment-return-processing)
- [F-041 — Payment reconciliation](#feature-f-041-payment-reconciliation)
- [F-042 — Payment hold removal](#feature-f-042-payment-hold-removal)
- [F-043 — Document template selection](#feature-f-043-document-template-selection)
- [F-044 — Statement generation](#feature-f-044-statement-generation)
- [F-045 — Document retention purge](#feature-f-045-document-retention-purge)
- [F-046 — Document replacement](#feature-f-046-document-replacement)
- [F-047 — Document delivery receipt](#feature-f-047-document-delivery-receipt)
- [F-048 — Document language selection](#feature-f-048-document-language-selection)
- [F-049 — Notification preference update](#feature-f-049-notification-preference-update)
- [F-050 — Eligibility notification](#feature-f-050-eligibility-notification)
- [F-051 — Contribution reminder](#feature-f-051-contribution-reminder)
- [F-052 — Claim status notification](#feature-f-052-claim-status-notification)
- [F-053 — Notification retry](#feature-f-053-notification-retry)
- [F-054 — Notification suppression](#feature-f-054-notification-suppression)
- [F-055 — Employer coverage report](#feature-f-055-employer-coverage-report)
- [F-056 — Contribution exception report](#feature-f-056-contribution-exception-report)
- [F-057 — Claim ageing report](#feature-f-057-claim-ageing-report)
- [F-058 — Branch 21 label review](#feature-f-058-branch-21-label-review)
- [F-059 — Branch 23 label review](#feature-f-059-branch-23-label-review)
- [F-060 — Sigedis reporting placeholder](#feature-f-060-sigedis-reporting-placeholder)
- [F-061 — User role assignment](#feature-f-061-user-role-assignment)
- [F-062 — Permission override](#feature-f-062-permission-override)
- [F-063 — Reference code maintenance](#feature-f-063-reference-code-maintenance)
- [F-064 — Plan configuration publishing](#feature-f-064-plan-configuration-publishing)
- [F-065 — Operational task reassignment](#feature-f-065-operational-task-reassignment)
- [F-066 — Tenant boundary review](#feature-f-066-tenant-boundary-review)
- [F-067 — Audit event capture](#feature-f-067-audit-event-capture)
- [F-068 — Audit hold preservation](#feature-f-068-audit-hold-preservation)
- [F-069 — Audit event search](#feature-f-069-audit-event-search)
- [F-070 — Audit export approval](#feature-f-070-audit-export-approval)
- [F-071 — Historical correction trace](#feature-f-071-historical-correction-trace)
- [F-072 — Archive replay review](#feature-f-072-archive-replay-review)

## Reading fragments

“Must” indicates a historical draft rule in this synthetic corpus. It does not indicate verified implementation.
Six conflict groups explicitly pair incompatible decisions. Other ambiguous wording is retained as ungrouped editorial debt.

<a id="feature-f-001-policy-creation"></a>

## Feature F-001 — Policy creation

Former page: CONF-SYNTH-301. Owner: Benefits stream. Last edited: 2023-05-05.
Tracking: BENEFITS-142. Status: Possibly obsolete.

The policy is described here using the policy administration vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **draft → proposed**. Effective date must equal the recorded approval date.
As an operations role, I want to review the policy in the selected employer scope so that the next queue can identify the accepted revision.

> Conflict group: CG-01

This section requires: Effective date must equal the recorded approval date.
The incompatible rule is retained in [Policy amendment](functional-specification.md#feature-f-002-policy-amendment): A revision may take effect before its approval date.
Resolution: not agreed. Both statements are fixture inputs; neither silently supersedes the other.

### F-001 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped policy reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Effective date must equal the recorded approval date | Date interpretation disputed in the old screen |
| 3 | Review result | A proposed policy has no payable balance | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-001 rules and exceptions

- RULE-001: Effective date must equal the recorded approval date.
- RULE-002: A proposed policy has no payable balance.
- RULE-003: the policy must carry a synthetic tenant scope before any lookup.
- RULE-004: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-005: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-006: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-001 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-001-A | An in-scope policy at the starting state | The normal review is accepted | Record draft → proposed with a revision reference |
| F-001-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-001-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-001-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a policy updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-001 dependencies and unanswered questions

Related workflow: [Policy amendment](functional-specification.md#feature-f-002-policy-amendment).
Technical operation: [INT-001](integration-data-and-compliance.md#int-001).
Register context: [Policy administration catalogue](product-and-feature-register.md#policy-administration-catalogue).

- Which team can reopen the policy after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1301: recover the missing example; owner Benefits stream.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-002-policy-amendment"></a>

## Feature F-002 — Policy amendment

Former page: CONF-SYNTH-302. Owner: TBD. Last edited: 2024-06-06.
Tracking: BENEFITS-143. Status: Draft with missing acceptance.

The policy revision is described here using the policy administration vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **active → revised**. A revision may take effect before its approval date.
As an operations role, I want to review the policy revision in the selected employer scope so that the next queue can identify the accepted revision.

> Conflict group: CG-01

This section requires: A revision may take effect before its approval date.
The incompatible rule is retained in [Policy creation](functional-specification.md#feature-f-001-policy-creation): Effective date must equal the recorded approval date.
Resolution: not agreed. Both statements are fixture inputs; neither silently supersedes the other.

### F-002 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped policy revision reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | A revision may take effect before its approval date | Date interpretation disputed in the old screen |
| 3 | Review result | Preserve the preceding revision for reconciliation | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-002 rules and exceptions

- RULE-007: A revision may take effect before its approval date.
- RULE-008: Preserve the preceding revision for reconciliation.
- RULE-009: the policy revision must carry a synthetic tenant scope before any lookup.
- RULE-010: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-011: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-012: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-002 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-002-A | An in-scope policy revision at the starting state | The normal review is accepted | Record active → revised with a revision reference |
| F-002-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-002-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-002-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a policy revision updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-002 dependencies and unanswered questions

Related workflow: [Policy renewal](functional-specification.md#feature-f-003-policy-renewal).
Technical operation: [INT-002](integration-data-and-compliance.md#int-002).
Register context: [Policy administration catalogue](product-and-feature-register.md#policy-administration-catalogue).

- Which team can reopen the policy revision after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1302: recover the missing example; owner TBD.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-003-policy-renewal"></a>

## Feature F-003 — Policy renewal

Former page: CONF-SYNTH-303. Owner: Platform support. Last edited: 2025-07-07.
Tracking: BENEFITS-144. Status: Assumed in release; evidence absent.

The renewal instruction is described here using the policy administration vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **expiring → renewed**. Create a new coverage period without silently copying unresolved exclusions.
As an operations role, I want to review the renewal instruction in the selected employer scope so that the next queue can identify the accepted revision.

### F-003 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped renewal instruction reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Create a new coverage period without silently copying unresolved exclusions | Date interpretation disputed in the old screen |
| 3 | Review result | An unapproved renewal stays in the exception queue | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-003 rules and exceptions

- RULE-013: Create a new coverage period without silently copying unresolved exclusions.
- RULE-014: An unapproved renewal stays in the exception queue.
- RULE-015: the renewal instruction must carry a synthetic tenant scope before any lookup.
- RULE-016: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-017: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-018: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-003 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-003-A | An in-scope renewal instruction at the starting state | The normal review is accepted | Record expiring → renewed with a revision reference |
| F-003-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-003-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-003-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a renewal instruction updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-003 archived workshop addendum

Workshop date 2021-12-24. Former migration team requested a second confirmation screen after a failed retry. No mock-up was retained.
The renewal instruction preview was described as disposable. A separate note says previews must be retained when they influenced a reviewed decision. Neither note defines “influenced”.

| Revision fragment | Comment | Disposition |
| --- | --- | --- |
| rev-a / 2022-04-04 | Use the latest available configuration when opening the screen | Possibly obsolete |
| rev-b / 2023-05-05 | Keep the configuration revision used by the originating batch | Unreviewed replacement proposal |

Recovery narrative: the first write succeeds and the acknowledgement is lost. A retry must inspect the stored logical key before creating another work item. The operator cannot decide from the red banner alone.
Partial completion narrative: the queue task exists, the audit append is pending, and the old export calls the item “complete”. Reporting must expose the mismatch, but the display wording is blank.

### F-003 dependencies and unanswered questions

Related workflow: [Policy suspension](functional-specification.md#feature-f-004-policy-suspension).
Technical operation: [INT-003](integration-data-and-compliance.md#int-003).
Register context: [Policy administration catalogue](product-and-feature-register.md#policy-administration-catalogue).

- Which team can reopen the renewal instruction after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1303: recover the missing example; owner Platform support.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-004-policy-suspension"></a>

## Feature F-004 — Policy suspension

Former page: CONF-SYNTH-304. Owner: Reporting stream. Last edited: 2019-08-08.
Tracking: BENEFITS-145. Status: Copied forward without review.

The suspension window is described here using the policy administration vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **active → suspended**. Freeze new collection instructions inside the suspension window.
As an operations role, I want to review the suspension window in the selected employer scope so that the next queue can identify the accepted revision.

### F-004 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped suspension window reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Freeze new collection instructions inside the suspension window | Date interpretation disputed in the old screen |
| 3 | Review result | Already released payments are handled separately | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-004 rules and exceptions

- RULE-019: Freeze new collection instructions inside the suspension window.
- RULE-020: Already released payments are handled separately.
- RULE-021: the suspension window must carry a synthetic tenant scope before any lookup.
- RULE-022: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-023: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-024: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-004 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-004-A | An in-scope suspension window at the starting state | The normal review is accepted | Record active → suspended with a revision reference |
| F-004-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-004-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-004-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a suspension window updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-004 dependencies and unanswered questions

Related workflow: [Policy cancellation](functional-specification.md#feature-f-005-policy-cancellation).
Technical operation: [INT-004](integration-data-and-compliance.md#int-004).
Register context: [Policy administration catalogue](product-and-feature-register.md#policy-administration-catalogue).

- Which team can reopen the suspension window after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1304: recover the missing example; owner Reporting stream.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-005-policy-cancellation"></a>

## Feature F-005 — Policy cancellation

Former page: CONF-SYNTH-305. Owner: Former migration team. Last edited: 2020-09-09.
Tracking: BENEFITS-146. Status: Possibly obsolete.

The cancellation request is described here using the policy administration vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **active → cancelled**. Require a cancellation reason before the nightly close.
As an operations role, I want to review the cancellation request in the selected employer scope so that the next queue can identify the accepted revision.

### F-005 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped cancellation request reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Require a cancellation reason before the nightly close | Date interpretation disputed in the old screen |
| 3 | Review result | Do not delete pending claims when coverage closes | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-005 rules and exceptions

- RULE-025: Require a cancellation reason before the nightly close.
- RULE-026: Do not delete pending claims when coverage closes.
- RULE-027: the cancellation request must carry a synthetic tenant scope before any lookup.
- RULE-028: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-029: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-030: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-005 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-005-A | An in-scope cancellation request at the starting state | The normal review is accepted | Record active → cancelled with a revision reference |
| F-005-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-005-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-005-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a cancellation request updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-005 dependencies and unanswered questions

Related workflow: [Policy reinstatement](functional-specification.md#feature-f-006-policy-reinstatement).
Technical operation: [INT-005](integration-data-and-compliance.md#int-005).
Register context: [Policy administration catalogue](product-and-feature-register.md#policy-administration-catalogue).

- Which team can reopen the cancellation request after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1305: recover the missing example; owner Former migration team.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-006-policy-reinstatement"></a>

## Feature F-006 — Policy reinstatement

Former page: CONF-SYNTH-306. Owner: Operations team. Last edited: 2021-10-10.
Tracking: BENEFITS-147. Status: Draft with missing acceptance.

The reinstatement request is described here using the policy administration vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **cancelled → active**. Check whether the original accounting period is still open.
As an operations role, I want to review the reinstatement request in the selected employer scope so that the next queue can identify the accepted revision.

### F-006 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped reinstatement request reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Check whether the original accounting period is still open | Date interpretation disputed in the old screen |
| 3 | Review result | A new revision must identify the gap in coverage | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-006 rules and exceptions

- RULE-031: Check whether the original accounting period is still open.
- RULE-032: A new revision must identify the gap in coverage.
- RULE-033: the reinstatement request must carry a synthetic tenant scope before any lookup.
- RULE-034: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-035: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-036: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-006 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-006-A | An in-scope reinstatement request at the starting state | The normal review is accepted | Record cancelled → active with a revision reference |
| F-006-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-006-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-006-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a reinstatement request updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-006 archived workshop addendum

Workshop date 2024-03-27. TBD requested a second confirmation screen after a failed retry. No mock-up was retained.
The reinstatement request preview was described as disposable. A separate note says previews must be retained when they influenced a reviewed decision. Neither note defines “influenced”.

| Revision fragment | Comment | Disposition |
| --- | --- | --- |
| rev-a / 2025-07-07 | Use the latest available configuration when opening the screen | Possibly obsolete |
| rev-b / 2019-08-08 | Keep the configuration revision used by the originating batch | Unreviewed replacement proposal |

Recovery narrative: the first write succeeds and the acknowledgement is lost. A retry must inspect the stored logical key before creating another work item. The operator cannot decide from the red banner alone.
Partial completion narrative: the queue task exists, the audit append is pending, and the old export calls the item “complete”. Reporting must expose the mismatch, but the display wording is blank.

### F-006 dependencies and unanswered questions

Related workflow: [Employer shell creation](functional-specification.md#feature-f-007-employer-shell-creation).
Technical operation: [INT-006](integration-data-and-compliance.md#int-006).
Register context: [Policy administration catalogue](product-and-feature-register.md#policy-administration-catalogue).

- Which team can reopen the reinstatement request after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1306: recover the missing example; owner Operations team.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-007-employer-shell-creation"></a>

## Feature F-007 — Employer shell creation

Former page: CONF-SYNTH-307. Owner: Benefits stream. Last edited: 2022-11-11.
Tracking: BENEFITS-148. Status: Assumed in release; evidence absent.

The employer shell is described here using the employer onboarding vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **received → incomplete**. Keep a shell employer separate from an enabled sponsor.
As an operations role, I want to review the employer shell in the selected employer scope so that the next queue can identify the accepted revision.

### F-007 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped employer shell reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Keep a shell employer separate from an enabled sponsor | Date interpretation disputed in the old screen |
| 3 | Review result | A missing administrative address blocks activation | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-007 rules and exceptions

- RULE-037: Keep a shell employer separate from an enabled sponsor.
- RULE-038: A missing administrative address blocks activation.
- RULE-039: the employer shell must carry a synthetic tenant scope before any lookup.
- RULE-040: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-041: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-042: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-007 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-007-A | An in-scope employer shell at the starting state | The normal review is accepted | Record received → incomplete with a revision reference |
| F-007-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-007-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-007-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a employer shell updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-007 dependencies and unanswered questions

Related workflow: [Employer document intake](functional-specification.md#feature-f-008-employer-document-intake).
Technical operation: [INT-007](integration-data-and-compliance.md#int-007).
Register context: [Employer onboarding catalogue](product-and-feature-register.md#employer-onboarding-catalogue).

- Which team can reopen the employer shell after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1307: recover the missing example; owner Benefits stream.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-008-employer-document-intake"></a>

## Feature F-008 — Employer document intake

Former page: CONF-SYNTH-308. Owner: TBD. Last edited: 2023-12-12.
Tracking: BENEFITS-149. Status: Copied forward without review.

The intake packet is described here using the employer onboarding vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **uploaded → reviewed**. Classify each attachment before accepting the packet.
As an operations role, I want to review the intake packet in the selected employer scope so that the next queue can identify the accepted revision.

### F-008 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped intake packet reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Classify each attachment before accepting the packet | Date interpretation disputed in the old screen |
| 3 | Review result | A replacement file must retain the original intake reference | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-008 rules and exceptions

- RULE-043: Classify each attachment before accepting the packet.
- RULE-044: A replacement file must retain the original intake reference.
- RULE-045: the intake packet must carry a synthetic tenant scope before any lookup.
- RULE-046: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-047: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-048: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-008 dependencies and unanswered questions

Related workflow: [Employer activation](functional-specification.md#feature-f-009-employer-activation).
Technical operation: [INT-008](integration-data-and-compliance.md#int-008).
Register context: [Employer onboarding catalogue](product-and-feature-register.md#employer-onboarding-catalogue).

- Which team can reopen the intake packet after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1308: recover the missing example; owner TBD.

Short-form page: remaining scenarios were never written. The register overstates the completeness of this feature.


<a id="feature-f-009-employer-activation"></a>

## Feature F-009 — Employer activation

Former page: CONF-SYNTH-309. Owner: Platform support. Last edited: 2024-01-13.
Tracking: BENEFITS-150. Status: Possibly obsolete.

The employer account is described here using the employer onboarding vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **reviewed → enabled**. Require operations review and a benefit package assignment.
As an operations role, I want to review the employer account in the selected employer scope so that the next queue can identify the accepted revision.

### F-009 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped employer account reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Require operations review and a benefit package assignment | Date interpretation disputed in the old screen |
| 3 | Review result | A disabled package cannot activate a new employer | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-009 rules and exceptions

- RULE-049: Require operations review and a benefit package assignment.
- RULE-050: A disabled package cannot activate a new employer.
- RULE-051: the employer account must carry a synthetic tenant scope before any lookup.
- RULE-052: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-053: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-054: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-009 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-009-A | An in-scope employer account at the starting state | The normal review is accepted | Record reviewed → enabled with a revision reference |
| F-009-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-009-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-009-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a employer account updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-009 archived workshop addendum

Workshop date 2020-06-03. Former migration team requested a second confirmation screen after a failed retry. No mock-up was retained.
The employer account preview was described as disposable. A separate note says previews must be retained when they influenced a reviewed decision. Neither note defines “influenced”.

| Revision fragment | Comment | Disposition |
| --- | --- | --- |
| rev-a / 2021-10-10 | Use the latest available configuration when opening the screen | Possibly obsolete |
| rev-b / 2022-11-11 | Keep the configuration revision used by the originating batch | Unreviewed replacement proposal |

Recovery narrative: the first write succeeds and the acknowledgement is lost. A retry must inspect the stored logical key before creating another work item. The operator cannot decide from the red banner alone.
Partial completion narrative: the queue task exists, the audit append is pending, and the old export calls the item “complete”. Reporting must expose the mismatch, but the display wording is blank.

### F-009 dependencies and unanswered questions

Related workflow: [Employer hierarchy change](functional-specification.md#feature-f-010-employer-hierarchy-change).
Technical operation: [INT-009](integration-data-and-compliance.md#int-009).
Register context: [Employer onboarding catalogue](product-and-feature-register.md#employer-onboarding-catalogue).

- Which team can reopen the employer account after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1309: recover the missing example; owner Platform support.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-010-employer-hierarchy-change"></a>

## Feature F-010 — Employer hierarchy change

Former page: CONF-SYNTH-310. Owner: Reporting stream. Last edited: 2025-02-14.
Tracking: BENEFITS-151. Status: Draft with missing acceptance.

The employer hierarchy is described here using the employer onboarding vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **flat → grouped**. Use an effective date for parent changes.
As an operations role, I want to review the employer hierarchy in the selected employer scope so that the next queue can identify the accepted revision.

### F-010 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped employer hierarchy reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Use an effective date for parent changes | Date interpretation disputed in the old screen |
| 3 | Review result | Do not transfer historical invoices to the new parent | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-010 rules and exceptions

- RULE-055: Use an effective date for parent changes.
- RULE-056: Do not transfer historical invoices to the new parent.
- RULE-057: the employer hierarchy must carry a synthetic tenant scope before any lookup.
- RULE-058: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-059: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-060: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-010 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-010-A | An in-scope employer hierarchy at the starting state | The normal review is accepted | Record flat → grouped with a revision reference |
| F-010-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-010-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-010-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a employer hierarchy updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-010 dependencies and unanswered questions

Related workflow: [Employer contact maintenance](functional-specification.md#feature-f-011-employer-contact-maintenance).
Technical operation: [INT-010](integration-data-and-compliance.md#int-010).
Register context: [Employer onboarding catalogue](product-and-feature-register.md#employer-onboarding-catalogue).

- Which team can reopen the employer hierarchy after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1310: recover the missing example; owner Reporting stream.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-011-employer-contact-maintenance"></a>

## Feature F-011 — Employer contact maintenance

Former page: CONF-SYNTH-311. Owner: Former migration team. Last edited: 2019-03-15.
Tracking: BENEFITS-152. Status: Assumed in release; evidence absent.

The contact slot is described here using the employer onboarding vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **unassigned → routed**. Store a synthetic role mailbox label rather than a named person.
As an operations role, I want to review the contact slot in the selected employer scope so that the next queue can identify the accepted revision.

### F-011 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped contact slot reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Store a synthetic role mailbox label rather than a named person | Date interpretation disputed in the old screen |
| 3 | Review result | A contact without a channel cannot receive an outbound event | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-011 rules and exceptions

- RULE-061: Store a synthetic role mailbox label rather than a named person.
- RULE-062: A contact without a channel cannot receive an outbound event.
- RULE-063: the contact slot must carry a synthetic tenant scope before any lookup.
- RULE-064: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-065: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-066: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-011 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-011-A | An in-scope contact slot at the starting state | The normal review is accepted | Record unassigned → routed with a revision reference |
| F-011-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-011-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-011-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a contact slot updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-011 dependencies and unanswered questions

Related workflow: [Employer offboarding](functional-specification.md#feature-f-012-employer-offboarding).
Technical operation: [INT-011](integration-data-and-compliance.md#int-011).
Register context: [Employer onboarding catalogue](product-and-feature-register.md#employer-onboarding-catalogue).

- Which team can reopen the contact slot after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1311: recover the missing example; owner Former migration team.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-012-employer-offboarding"></a>

## Feature F-012 — Employer offboarding

Former page: CONF-SYNTH-312. Owner: Operations team. Last edited: 2020-04-16.
Tracking: BENEFITS-153. Status: Copied forward without review.

The offboarding case is described here using the employer onboarding vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **enabled → closing**. Stop new enrolments after the closing date.
As an operations role, I want to review the offboarding case in the selected employer scope so that the next queue can identify the accepted revision.

### F-012 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped offboarding case reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Stop new enrolments after the closing date | Date interpretation disputed in the old screen |
| 3 | Review result | Unsettled contributions keep the shell visible | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-012 rules and exceptions

- RULE-067: Stop new enrolments after the closing date.
- RULE-068: Unsettled contributions keep the shell visible.
- RULE-069: the offboarding case must carry a synthetic tenant scope before any lookup.
- RULE-070: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-071: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-072: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-012 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-012-A | An in-scope offboarding case at the starting state | The normal review is accepted | Record enabled → closing with a revision reference |
| F-012-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-012-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-012-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a offboarding case updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-012 archived workshop addendum

Workshop date 2023-09-06. TBD requested a second confirmation screen after a failed retry. No mock-up was retained.
The offboarding case preview was described as disposable. A separate note says previews must be retained when they influenced a reviewed decision. Neither note defines “influenced”.

| Revision fragment | Comment | Disposition |
| --- | --- | --- |
| rev-a / 2024-01-13 | Use the latest available configuration when opening the screen | Possibly obsolete |
| rev-b / 2025-02-14 | Keep the configuration revision used by the originating batch | Unreviewed replacement proposal |

Recovery narrative: the first write succeeds and the acknowledgement is lost. A retry must inspect the stored logical key before creating another work item. The operator cannot decide from the red banner alone.
Partial completion narrative: the queue task exists, the audit append is pending, and the old export calls the item “complete”. Reporting must expose the mismatch, but the display wording is blank.

### F-012 dependencies and unanswered questions

Related workflow: [Employee eligibility assessment](functional-specification.md#feature-f-013-employee-eligibility-assessment).
Technical operation: [INT-012](integration-data-and-compliance.md#int-012).
Register context: [Employer onboarding catalogue](product-and-feature-register.md#employer-onboarding-catalogue).

- Which team can reopen the offboarding case after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1312: recover the missing example; owner Operations team.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-013-employee-eligibility-assessment"></a>

## Feature F-013 — Employee eligibility assessment

Former page: CONF-SYNTH-313. Owner: Benefits stream. Last edited: 2021-05-17.
Tracking: BENEFITS-154. Status: Possibly obsolete.

The eligibility decision is described here using the eligibility vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **unchecked → eligible**. Evaluate eligibility using the member status on the payroll period end date.
As an operations role, I want to review the eligibility decision in the selected employer scope so that the next queue can identify the accepted revision.

> Conflict group: CG-02

This section requires: Evaluate eligibility using the member status on the payroll period end date.
The incompatible rule is retained in [Payroll import](functional-specification.md#feature-f-022-payroll-import): Evaluate eligibility using member status on the payroll file receipt date.
Resolution: not agreed. Both statements are fixture inputs; neither silently supersedes the other.

### F-013 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped eligibility decision reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Evaluate eligibility using the member status on the payroll period end date | Date interpretation disputed in the old screen |
| 3 | Review result | An unknown class routes to manual review | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-013 rules and exceptions

- RULE-073: Evaluate eligibility using the member status on the payroll period end date.
- RULE-074: An unknown class routes to manual review.
- RULE-075: the eligibility decision must carry a synthetic tenant scope before any lookup.
- RULE-076: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-077: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-078: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-013 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-013-A | An in-scope eligibility decision at the starting state | The normal review is accepted | Record unchecked → eligible with a revision reference |
| F-013-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-013-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-013-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a eligibility decision updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-013 dependencies and unanswered questions

Related workflow: [Waiting period evaluation](functional-specification.md#feature-f-014-waiting-period-evaluation).
Technical operation: [INT-013](integration-data-and-compliance.md#int-013).
Register context: [Eligibility catalogue](product-and-feature-register.md#eligibility-catalogue).

- Which team can reopen the eligibility decision after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1313: recover the missing example; owner Benefits stream.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-014-waiting-period-evaluation"></a>

## Feature F-014 — Waiting period evaluation

Former page: CONF-SYNTH-314. Owner: TBD. Last edited: 2022-06-18.
Tracking: BENEFITS-155. Status: Draft with missing acceptance.

The waiting interval is described here using the eligibility vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **waiting → qualified**. Count complete fictional plan months from the accepted start date.
As an operations role, I want to review the waiting interval in the selected employer scope so that the next queue can identify the accepted revision.

> Compliance note: requires Belgian-market and legal validation.

### F-014 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped waiting interval reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Count complete fictional plan months from the accepted start date | Date interpretation disputed in the old screen |
| 3 | Review result | An interrupted interval requires a new review | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-014 rules and exceptions

- RULE-079: Count complete fictional plan months from the accepted start date.
- RULE-080: An interrupted interval requires a new review.
- RULE-081: the waiting interval must carry a synthetic tenant scope before any lookup.
- RULE-082: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-083: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-084: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-014 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-014-A | An in-scope waiting interval at the starting state | The normal review is accepted | Record waiting → qualified with a revision reference |
| F-014-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-014-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-014-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a waiting interval updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-014 dependencies and unanswered questions

Related workflow: [Employment category change](functional-specification.md#feature-f-015-employment-category-change).
Technical operation: [INT-014](integration-data-and-compliance.md#int-014).
Register context: [Eligibility catalogue](product-and-feature-register.md#eligibility-catalogue).

- Which team can reopen the waiting interval after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1314: recover the missing example; owner TBD.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-015-employment-category-change"></a>

## Feature F-015 — Employment category change

Former page: CONF-SYNTH-315. Owner: Platform support. Last edited: 2023-07-19.
Tracking: BENEFITS-156. Status: Assumed in release; evidence absent.

The category assignment is described here using the eligibility vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **class-a → class-b**. Split coverage when a category changes during an open period.
As an operations role, I want to review the category assignment in the selected employer scope so that the next queue can identify the accepted revision.

### F-015 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped category assignment reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Split coverage when a category changes during an open period | Date interpretation disputed in the old screen |
| 3 | Review result | Never infer a salary from the class label | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-015 rules and exceptions

- RULE-085: Split coverage when a category changes during an open period.
- RULE-086: Never infer a salary from the class label.
- RULE-087: the category assignment must carry a synthetic tenant scope before any lookup.
- RULE-088: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-089: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-090: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-015 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-015-A | An in-scope category assignment at the starting state | The normal review is accepted | Record class-a → class-b with a revision reference |
| F-015-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-015-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-015-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a category assignment updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-015 archived workshop addendum

Workshop date 2019-12-09. Former migration team requested a second confirmation screen after a failed retry. No mock-up was retained.
The category assignment preview was described as disposable. A separate note says previews must be retained when they influenced a reviewed decision. Neither note defines “influenced”.

| Revision fragment | Comment | Disposition |
| --- | --- | --- |
| rev-a / 2020-04-16 | Use the latest available configuration when opening the screen | Possibly obsolete |
| rev-b / 2021-05-17 | Keep the configuration revision used by the originating batch | Unreviewed replacement proposal |

Recovery narrative: the first write succeeds and the acknowledgement is lost. A retry must inspect the stored logical key before creating another work item. The operator cannot decide from the red banner alone.
Partial completion narrative: the queue task exists, the audit append is pending, and the old export calls the item “complete”. Reporting must expose the mismatch, but the display wording is blank.

### F-015 dependencies and unanswered questions

Related workflow: [Leave and absence handling](functional-specification.md#feature-f-016-leave-and-absence-handling).
Technical operation: [INT-015](integration-data-and-compliance.md#int-015).
Register context: [Eligibility catalogue](product-and-feature-register.md#eligibility-catalogue).

- Which team can reopen the category assignment after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1315: recover the missing example; owner Platform support.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-016-leave-and-absence-handling"></a>

## Feature F-016 — Leave and absence handling

Former page: CONF-SYNTH-316. Owner: Reporting stream. Last edited: 2024-08-20.
Tracking: BENEFITS-157. Status: Copied forward without review.

The absence interval is described here using the eligibility vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **working → absent**. Distinguish a missing payroll record from a declared absence.
As an operations role, I want to review the absence interval in the selected employer scope so that the next queue can identify the accepted revision.

### F-016 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped absence interval reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Distinguish a missing payroll record from a declared absence | Date interpretation disputed in the old screen |
| 3 | Review result | Overlapping intervals need an operations decision | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-016 rules and exceptions

- RULE-091: Distinguish a missing payroll record from a declared absence.
- RULE-092: Overlapping intervals need an operations decision.
- RULE-093: the absence interval must carry a synthetic tenant scope before any lookup.
- RULE-094: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-095: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-096: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-016 dependencies and unanswered questions

Related workflow: [Member exit processing](functional-specification.md#feature-f-017-member-exit-processing).
Technical operation: [INT-016](integration-data-and-compliance.md#int-016).
Register context: [Eligibility catalogue](product-and-feature-register.md#eligibility-catalogue).

- Which team can reopen the absence interval after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1316: recover the missing example; owner Reporting stream.

Short-form page: remaining scenarios were never written. The register overstates the completeness of this feature.


<a id="feature-f-017-member-exit-processing"></a>

## Feature F-017 — Member exit processing

Former page: CONF-SYNTH-317. Owner: Former migration team. Last edited: 2025-09-21.
Tracking: BENEFITS-158. Status: Possibly obsolete.

The exit instruction is described here using the eligibility vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **covered → exited**. Close future eligibility without erasing prior coverage.
As an operations role, I want to review the exit instruction in the selected employer scope so that the next queue can identify the accepted revision.

### F-017 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped exit instruction reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Close future eligibility without erasing prior coverage | Date interpretation disputed in the old screen |
| 3 | Review result | A pending death event blocks the ordinary exit path | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-017 rules and exceptions

- RULE-097: Close future eligibility without erasing prior coverage.
- RULE-098: A pending death event blocks the ordinary exit path.
- RULE-099: the exit instruction must carry a synthetic tenant scope before any lookup.
- RULE-100: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-101: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-102: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-017 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-017-A | An in-scope exit instruction at the starting state | The normal review is accepted | Record covered → exited with a revision reference |
| F-017-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-017-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-017-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a exit instruction updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-017 dependencies and unanswered questions

Related workflow: [Member re-entry](functional-specification.md#feature-f-018-member-re-entry).
Technical operation: [INT-017](integration-data-and-compliance.md#int-017).
Register context: [Eligibility catalogue](product-and-feature-register.md#eligibility-catalogue).

- Which team can reopen the exit instruction after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1317: recover the missing example; owner Former migration team.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-018-member-re-entry"></a>

## Feature F-018 — Member re-entry

Former page: CONF-SYNTH-318. Owner: Operations team. Last edited: 2019-10-22.
Tracking: BENEFITS-159. Status: Draft with missing acceptance.

The re-entry case is described here using the eligibility vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **exited → candidate**. Match the synthetic member key before creating a new membership.
As an operations role, I want to review the re-entry case in the selected employer scope so that the next queue can identify the accepted revision.

> Compliance note: requires Belgian-market and legal validation.

### F-018 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped re-entry case reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Match the synthetic member key before creating a new membership | Date interpretation disputed in the old screen |
| 3 | Review result | Prior beneficiary choices are not automatically confirmed | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-018 rules and exceptions

- RULE-103: Match the synthetic member key before creating a new membership.
- RULE-104: Prior beneficiary choices are not automatically confirmed.
- RULE-105: the re-entry case must carry a synthetic tenant scope before any lookup.
- RULE-106: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-107: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-108: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-018 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-018-A | An in-scope re-entry case at the starting state | The normal review is accepted | Record exited → candidate with a revision reference |
| F-018-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-018-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-018-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a re-entry case updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-018 archived workshop addendum

Workshop date 2022-03-12. TBD requested a second confirmation screen after a failed retry. No mock-up was retained.
The re-entry case preview was described as disposable. A separate note says previews must be retained when they influenced a reviewed decision. Neither note defines “influenced”.

| Revision fragment | Comment | Disposition |
| --- | --- | --- |
| rev-a / 2023-07-19 | Use the latest available configuration when opening the screen | Possibly obsolete |
| rev-b / 2024-08-20 | Keep the configuration revision used by the originating batch | Unreviewed replacement proposal |

Recovery narrative: the first write succeeds and the acknowledgement is lost. A retry must inspect the stored logical key before creating another work item. The operator cannot decide from the red banner alone.
Partial completion narrative: the queue task exists, the audit append is pending, and the old export calls the item “complete”. Reporting must expose the mismatch, but the display wording is blank.

### F-018 dependencies and unanswered questions

Related workflow: [Contribution calculation](functional-specification.md#feature-f-019-contribution-calculation).
Technical operation: [INT-018](integration-data-and-compliance.md#int-018).
Register context: [Eligibility catalogue](product-and-feature-register.md#eligibility-catalogue).

- Which team can reopen the re-entry case after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1318: recover the missing example; owner Operations team.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-019-contribution-calculation"></a>

## Feature F-019 — Contribution calculation

Former page: CONF-SYNTH-319. Owner: Benefits stream. Last edited: 2020-11-23.
Tracking: BENEFITS-160. Status: Assumed in release; evidence absent.

The contribution line is described here using the contributions vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **rated → calculated**. Round each component before adding the period total.
As an operations role, I want to review the contribution line in the selected employer scope so that the next queue can identify the accepted revision.

> Conflict group: CG-03

This section requires: Round each component before adding the period total.
The incompatible rule is retained in [Contribution correction](functional-specification.md#feature-f-023-contribution-correction): Add unrounded components and round only the final period total.
Resolution: not agreed. Both statements are fixture inputs; neither silently supersedes the other.

### F-019 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped contribution line reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Round each component before adding the period total | Date interpretation disputed in the old screen |
| 3 | Review result | Keep the basis and rate revision alongside the result | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-019 rules and exceptions

- RULE-109: Round each component before adding the period total.
- RULE-110: Keep the basis and rate revision alongside the result.
- RULE-111: the contribution line must carry a synthetic tenant scope before any lookup.
- RULE-112: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-113: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-114: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-019 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-019-A | An in-scope contribution line at the starting state | The normal review is accepted | Record rated → calculated with a revision reference |
| F-019-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-019-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-019-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a contribution line updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-019 dependencies and unanswered questions

Related workflow: [Contribution allocation](functional-specification.md#feature-f-020-contribution-allocation).
Technical operation: [INT-019](integration-data-and-compliance.md#int-019).
Register context: [Contributions catalogue](product-and-feature-register.md#contributions-catalogue).

- Which team can reopen the contribution line after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1319: recover the missing example; owner Benefits stream.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-020-contribution-allocation"></a>

## Feature F-020 — Contribution allocation

Former page: CONF-SYNTH-320. Owner: TBD. Last edited: 2021-12-24.
Tracking: BENEFITS-161. Status: Copied forward without review.

The allocation instruction is described here using the contributions vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **unallocated → allocated**. Allocate only to an open synthetic coverage account.
As an operations role, I want to review the allocation instruction in the selected employer scope so that the next queue can identify the accepted revision.

### F-020 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped allocation instruction reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Allocate only to an open synthetic coverage account | Date interpretation disputed in the old screen |
| 3 | Review result | An unmatched remittance remains on suspense | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-020 rules and exceptions

- RULE-115: Allocate only to an open synthetic coverage account.
- RULE-116: An unmatched remittance remains on suspense.
- RULE-117: the allocation instruction must carry a synthetic tenant scope before any lookup.
- RULE-118: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-119: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-120: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-020 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-020-A | An in-scope allocation instruction at the starting state | The normal review is accepted | Record unallocated → allocated with a revision reference |
| F-020-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-020-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-020-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a allocation instruction updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-020 dependencies and unanswered questions

Related workflow: [Contribution arrears](functional-specification.md#feature-f-021-contribution-arrears).
Technical operation: [INT-020](integration-data-and-compliance.md#int-020).
Register context: [Contributions catalogue](product-and-feature-register.md#contributions-catalogue).

- Which team can reopen the allocation instruction after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1320: recover the missing example; owner TBD.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-021-contribution-arrears"></a>

## Feature F-021 — Contribution arrears

Former page: CONF-SYNTH-321. Owner: Platform support. Last edited: 2022-01-25.
Tracking: BENEFITS-162. Status: Possibly obsolete.

The arrears item is described here using the contributions vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **due → overdue**. Start ageing from the synthetic due date recorded on the item.
As an operations role, I want to review the arrears item in the selected employer scope so that the next queue can identify the accepted revision.

### F-021 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped arrears item reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Start ageing from the synthetic due date recorded on the item | Date interpretation disputed in the old screen |
| 3 | Review result | A disputed item remains visible in ageing | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-021 rules and exceptions

- RULE-121: Start ageing from the synthetic due date recorded on the item.
- RULE-122: A disputed item remains visible in ageing.
- RULE-123: the arrears item must carry a synthetic tenant scope before any lookup.
- RULE-124: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-125: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-126: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-021 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-021-A | An in-scope arrears item at the starting state | The normal review is accepted | Record due → overdue with a revision reference |
| F-021-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-021-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-021-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a arrears item updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-021 archived workshop addendum

Workshop date 2025-06-15. Former migration team requested a second confirmation screen after a failed retry. No mock-up was retained.
The arrears item preview was described as disposable. A separate note says previews must be retained when they influenced a reviewed decision. Neither note defines “influenced”.

| Revision fragment | Comment | Disposition |
| --- | --- | --- |
| rev-a / 2019-10-22 | Use the latest available configuration when opening the screen | Possibly obsolete |
| rev-b / 2020-11-23 | Keep the configuration revision used by the originating batch | Unreviewed replacement proposal |

Recovery narrative: the first write succeeds and the acknowledgement is lost. A retry must inspect the stored logical key before creating another work item. The operator cannot decide from the red banner alone.
Partial completion narrative: the queue task exists, the audit append is pending, and the old export calls the item “complete”. Reporting must expose the mismatch, but the display wording is blank.

### F-021 dependencies and unanswered questions

Related workflow: [Payroll import](functional-specification.md#feature-f-022-payroll-import).
Technical operation: [INT-021](integration-data-and-compliance.md#int-021).
Register context: [Contributions catalogue](product-and-feature-register.md#contributions-catalogue).

- Which team can reopen the arrears item after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1321: recover the missing example; owner Platform support.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-022-payroll-import"></a>

## Feature F-022 — Payroll import

Former page: CONF-SYNTH-322. Owner: Reporting stream. Last edited: 2023-02-26.
Tracking: BENEFITS-163. Status: Draft with missing acceptance.

The payroll batch is described here using the contributions vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **staged → accepted**. Evaluate eligibility using member status on the payroll file receipt date.
As an operations role, I want to review the payroll batch in the selected employer scope so that the next queue can identify the accepted revision.

> Conflict group: CG-02

This section requires: Evaluate eligibility using member status on the payroll file receipt date.
The incompatible rule is retained in [Employee eligibility assessment](functional-specification.md#feature-f-013-employee-eligibility-assessment): Evaluate eligibility using the member status on the payroll period end date.
Resolution: not agreed. Both statements are fixture inputs; neither silently supersedes the other.

### F-022 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped payroll batch reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Evaluate eligibility using member status on the payroll file receipt date | Date interpretation disputed in the old screen |
| 3 | Review result | A rejected row must not silently reduce the accepted control total | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-022 rules and exceptions

- RULE-127: Evaluate eligibility using member status on the payroll file receipt date.
- RULE-128: A rejected row must not silently reduce the accepted control total.
- RULE-129: the payroll batch must carry a synthetic tenant scope before any lookup.
- RULE-130: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-131: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-132: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-022 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-022-A | An in-scope payroll batch at the starting state | The normal review is accepted | Record staged → accepted with a revision reference |
| F-022-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-022-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-022-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a payroll batch updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-022 dependencies and unanswered questions

Related workflow: [Contribution correction](functional-specification.md#feature-f-023-contribution-correction).
Technical operation: [INT-022](integration-data-and-compliance.md#int-022).
Register context: [Contributions catalogue](product-and-feature-register.md#contributions-catalogue).

- Which team can reopen the payroll batch after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1322: recover the missing example; owner Reporting stream.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-023-contribution-correction"></a>

## Feature F-023 — Contribution correction

Former page: CONF-SYNTH-323. Owner: Former migration team. Last edited: 2024-03-27.
Tracking: BENEFITS-164. Status: Assumed in release; evidence absent.

The correction delta is described here using the contributions vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **posted → adjusted**. Add unrounded components and round only the final period total.
As an operations role, I want to review the correction delta in the selected employer scope so that the next queue can identify the accepted revision.

> Conflict group: CG-03

This section requires: Add unrounded components and round only the final period total.
The incompatible rule is retained in [Contribution calculation](functional-specification.md#feature-f-019-contribution-calculation): Round each component before adding the period total.
Resolution: not agreed. Both statements are fixture inputs; neither silently supersedes the other.

### F-023 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped correction delta reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Add unrounded components and round only the final period total | Date interpretation disputed in the old screen |
| 3 | Review result | Link every correction to a prior posted contribution | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-023 rules and exceptions

- RULE-133: Add unrounded components and round only the final period total.
- RULE-134: Link every correction to a prior posted contribution.
- RULE-135: the correction delta must carry a synthetic tenant scope before any lookup.
- RULE-136: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-137: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-138: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-023 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-023-A | An in-scope correction delta at the starting state | The normal review is accepted | Record posted → adjusted with a revision reference |
| F-023-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-023-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-023-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a correction delta updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-023 dependencies and unanswered questions

Related workflow: [Contribution refund request](functional-specification.md#feature-f-024-contribution-refund-request).
Technical operation: [INT-023](integration-data-and-compliance.md#int-023).
Register context: [Contributions catalogue](product-and-feature-register.md#contributions-catalogue).

- Which team can reopen the correction delta after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1323: recover the missing example; owner Former migration team.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-024-contribution-refund-request"></a>

## Feature F-024 — Contribution refund request

Former page: CONF-SYNTH-324. Owner: Operations team. Last edited: 2025-04-01.
Tracking: BENEFITS-165. Status: Copied forward without review.

The refund case is described here using the contributions vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **credit → requested**. A credit balance alone does not authorize a refund.
As an operations role, I want to review the refund case in the selected employer scope so that the next queue can identify the accepted revision.

### F-024 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped refund case reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | A credit balance alone does not authorize a refund | Date interpretation disputed in the old screen |
| 3 | Review result | A refund must not erase the contribution that created the credit | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-024 rules and exceptions

- RULE-139: A credit balance alone does not authorize a refund.
- RULE-140: A refund must not erase the contribution that created the credit.
- RULE-141: the refund case must carry a synthetic tenant scope before any lookup.
- RULE-142: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-143: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-144: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-024 archived workshop addendum

Workshop date 2021-09-18. TBD requested a second confirmation screen after a failed retry. No mock-up was retained.
The refund case preview was described as disposable. A separate note says previews must be retained when they influenced a reviewed decision. Neither note defines “influenced”.

| Revision fragment | Comment | Disposition |
| --- | --- | --- |
| rev-a / 2022-01-25 | Use the latest available configuration when opening the screen | Possibly obsolete |
| rev-b / 2023-02-26 | Keep the configuration revision used by the originating batch | Unreviewed replacement proposal |

Recovery narrative: the first write succeeds and the acknowledgement is lost. A retry must inspect the stored logical key before creating another work item. The operator cannot decide from the red banner alone.
Partial completion narrative: the queue task exists, the audit append is pending, and the old export calls the item “complete”. Reporting must expose the mismatch, but the display wording is blank.

### F-024 dependencies and unanswered questions

Related workflow: [Beneficiary designation](functional-specification.md#feature-f-025-beneficiary-designation).
Technical operation: [INT-024](integration-data-and-compliance.md#int-024).
Register context: [Contributions catalogue](product-and-feature-register.md#contributions-catalogue).

- Which team can reopen the refund case after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1324: recover the missing example; owner Operations team.

Short-form page: remaining scenarios were never written. The register overstates the completeness of this feature.


<a id="feature-f-025-beneficiary-designation"></a>

## Feature F-025 — Beneficiary designation

Former page: CONF-SYNTH-325. Owner: Benefits stream. Last edited: 2019-05-02.
Tracking: BENEFITS-166. Status: Possibly obsolete.

The designation set is described here using the beneficiaries vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **draft → confirmed**. The latest confirmed designation replaces all previous designations immediately.
As an operations role, I want to review the designation set in the selected employer scope so that the next queue can identify the accepted revision.

> Conflict group: CG-04

This section requires: The latest confirmed designation replaces all previous designations immediately.
The incompatible rule is retained in [Death claim entitlement snapshot](functional-specification.md#feature-f-033-death-claim-entitlement-snapshot): Use the designation confirmed at the reported event date even if replaced later.
Resolution: not agreed. Both statements are fixture inputs; neither silently supersedes the other.

### F-025 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped designation set reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | The latest confirmed designation replaces all previous designations immediately | Date interpretation disputed in the old screen |
| 3 | Review result | Keep percentage totals separate from verification status | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-025 rules and exceptions

- RULE-145: The latest confirmed designation replaces all previous designations immediately.
- RULE-146: Keep percentage totals separate from verification status.
- RULE-147: the designation set must carry a synthetic tenant scope before any lookup.
- RULE-148: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-149: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-150: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-025 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-025-A | An in-scope designation set at the starting state | The normal review is accepted | Record draft → confirmed with a revision reference |
| F-025-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-025-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-025-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a designation set updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-025 dependencies and unanswered questions

Related workflow: [Beneficiary share validation](functional-specification.md#feature-f-026-beneficiary-share-validation).
Technical operation: [INT-025](integration-data-and-compliance.md#int-025).
Register context: [Beneficiaries catalogue](product-and-feature-register.md#beneficiaries-catalogue).

- Which team can reopen the designation set after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1325: recover the missing example; owner Benefits stream.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-026-beneficiary-share-validation"></a>

## Feature F-026 — Beneficiary share validation

Former page: CONF-SYNTH-326. Owner: TBD. Last edited: 2020-06-03.
Tracking: BENEFITS-167. Status: Draft with missing acceptance.

The share set is described here using the beneficiaries vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **entered → balanced**. Require the synthetic share total to equal one hundred before confirmation.
As an operations role, I want to review the share set in the selected employer scope so that the next queue can identify the accepted revision.

### F-026 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped share set reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Require the synthetic share total to equal one hundred before confirmation | Date interpretation disputed in the old screen |
| 3 | Review result | Unknown recipients keep the set in draft | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-026 rules and exceptions

- RULE-151: Require the synthetic share total to equal one hundred before confirmation.
- RULE-152: Unknown recipients keep the set in draft.
- RULE-153: the share set must carry a synthetic tenant scope before any lookup.
- RULE-154: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-155: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-156: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-026 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-026-A | An in-scope share set at the starting state | The normal review is accepted | Record entered → balanced with a revision reference |
| F-026-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-026-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-026-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a share set updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-026 dependencies and unanswered questions

Related workflow: [Beneficiary evidence review](functional-specification.md#feature-f-027-beneficiary-evidence-review).
Technical operation: [INT-026](integration-data-and-compliance.md#int-026).
Register context: [Beneficiaries catalogue](product-and-feature-register.md#beneficiaries-catalogue).

- Which team can reopen the share set after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1326: recover the missing example; owner TBD.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-027-beneficiary-evidence-review"></a>

## Feature F-027 — Beneficiary evidence review

Former page: CONF-SYNTH-327. Owner: Platform support. Last edited: 2021-07-04.
Tracking: BENEFITS-168. Status: Assumed in release; evidence absent.

The evidence checklist is described here using the beneficiaries vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **missing → reviewed**. Evidence completeness is a workflow flag only.
As an operations role, I want to review the evidence checklist in the selected employer scope so that the next queue can identify the accepted revision.

> Compliance note: requires Belgian-market and legal validation.

### F-027 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped evidence checklist reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Evidence completeness is a workflow flag only | Date interpretation disputed in the old screen |
| 3 | Review result | A reviewed attachment does not determine entitlement | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-027 rules and exceptions

- RULE-157: Evidence completeness is a workflow flag only.
- RULE-158: A reviewed attachment does not determine entitlement.
- RULE-159: the evidence checklist must carry a synthetic tenant scope before any lookup.
- RULE-160: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-161: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-162: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-027 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-027-A | An in-scope evidence checklist at the starting state | The normal review is accepted | Record missing → reviewed with a revision reference |
| F-027-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-027-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-027-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a evidence checklist updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-027 archived workshop addendum

Workshop date 2024-12-21. Former migration team requested a second confirmation screen after a failed retry. No mock-up was retained.
The evidence checklist preview was described as disposable. A separate note says previews must be retained when they influenced a reviewed decision. Neither note defines “influenced”.

| Revision fragment | Comment | Disposition |
| --- | --- | --- |
| rev-a / 2025-04-01 | Use the latest available configuration when opening the screen | Possibly obsolete |
| rev-b / 2019-05-02 | Keep the configuration revision used by the originating batch | Unreviewed replacement proposal |

Recovery narrative: the first write succeeds and the acknowledgement is lost. A retry must inspect the stored logical key before creating another work item. The operator cannot decide from the red banner alone.
Partial completion narrative: the queue task exists, the audit append is pending, and the old export calls the item “complete”. Reporting must expose the mismatch, but the display wording is blank.

### F-027 dependencies and unanswered questions

Related workflow: [Retirement event registration](functional-specification.md#feature-f-028-retirement-event-registration).
Technical operation: [INT-027](integration-data-and-compliance.md#int-027).
Register context: [Beneficiaries catalogue](product-and-feature-register.md#beneficiaries-catalogue).

- Which team can reopen the evidence checklist after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1327: recover the missing example; owner Platform support.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-028-retirement-event-registration"></a>

## Feature F-028 — Retirement event registration

Former page: CONF-SYNTH-328. Owner: Reporting stream. Last edited: 2022-08-05.
Tracking: BENEFITS-169. Status: Copied forward without review.

The retirement event is described here using the beneficiaries vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **reported → assessed**. Use the reported retirement date as an unvalidated event input.
As an operations role, I want to review the retirement event in the selected employer scope so that the next queue can identify the accepted revision.

> Compliance note: requires Belgian-market and legal validation.

### F-028 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped retirement event reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Use the reported retirement date as an unvalidated event input | Date interpretation disputed in the old screen |
| 3 | Review result | Do not derive statutory age rules from this fixture | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-028 rules and exceptions

- RULE-163: Use the reported retirement date as an unvalidated event input.
- RULE-164: Do not derive statutory age rules from this fixture.
- RULE-165: the retirement event must carry a synthetic tenant scope before any lookup.
- RULE-166: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-167: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-168: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-028 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-028-A | An in-scope retirement event at the starting state | The normal review is accepted | Record reported → assessed with a revision reference |
| F-028-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-028-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-028-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a retirement event updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-028 dependencies and unanswered questions

Related workflow: [Death event registration](functional-specification.md#feature-f-029-death-event-registration).
Technical operation: [INT-028](integration-data-and-compliance.md#int-028).
Register context: [Beneficiaries catalogue](product-and-feature-register.md#beneficiaries-catalogue).

- Which team can reopen the retirement event after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1328: recover the missing example; owner Reporting stream.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-029-death-event-registration"></a>

## Feature F-029 — Death event registration

Former page: CONF-SYNTH-329. Owner: Former migration team. Last edited: 2023-09-06.
Tracking: BENEFITS-170. Status: Possibly obsolete.

The death event is described here using the beneficiaries vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **reported → awaiting-review**. Store reported event dates without declaring legal proof.
As an operations role, I want to review the death event in the selected employer scope so that the next queue can identify the accepted revision.

> Compliance note: requires Belgian-market and legal validation.

### F-029 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped death event reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Store reported event dates without declaring legal proof | Date interpretation disputed in the old screen |
| 3 | Review result | Conflicting event reports must remain separately traceable | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-029 rules and exceptions

- RULE-169: Store reported event dates without declaring legal proof.
- RULE-170: Conflicting event reports must remain separately traceable.
- RULE-171: the death event must carry a synthetic tenant scope before any lookup.
- RULE-172: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-173: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-174: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-029 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-029-A | An in-scope death event at the starting state | The normal review is accepted | Record reported → awaiting-review with a revision reference |
| F-029-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-029-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-029-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a death event updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-029 dependencies and unanswered questions

Related workflow: [Disability event registration](functional-specification.md#feature-f-030-disability-event-registration).
Technical operation: [INT-029](integration-data-and-compliance.md#int-029).
Register context: [Beneficiaries catalogue](product-and-feature-register.md#beneficiaries-catalogue).

- Which team can reopen the death event after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1329: recover the missing example; owner Former migration team.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-030-disability-event-registration"></a>

## Feature F-030 — Disability event registration

Former page: CONF-SYNTH-330. Owner: Operations team. Last edited: 2024-10-07.
Tracking: BENEFITS-171. Status: Draft with missing acceptance.

The disability event is described here using the beneficiaries vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **reported → awaiting-assessment**. Keep an assessment placeholder separate from benefit authorization.
As an operations role, I want to review the disability event in the selected employer scope so that the next queue can identify the accepted revision.

> Compliance note: requires Belgian-market and legal validation.

### F-030 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped disability event reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Keep an assessment placeholder separate from benefit authorization | Date interpretation disputed in the old screen |
| 3 | Review result | No medical diagnosis belongs in the synthetic payload | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-030 rules and exceptions

- RULE-175: Keep an assessment placeholder separate from benefit authorization.
- RULE-176: No medical diagnosis belongs in the synthetic payload.
- RULE-177: the disability event must carry a synthetic tenant scope before any lookup.
- RULE-178: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-179: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-180: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-030 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-030-A | An in-scope disability event at the starting state | The normal review is accepted | Record reported → awaiting-assessment with a revision reference |
| F-030-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-030-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-030-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a disability event updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-030 archived workshop addendum

Workshop date 2020-03-24. TBD requested a second confirmation screen after a failed retry. No mock-up was retained.
The disability event preview was described as disposable. A separate note says previews must be retained when they influenced a reviewed decision. Neither note defines “influenced”.

| Revision fragment | Comment | Disposition |
| --- | --- | --- |
| rev-a / 2021-07-04 | Use the latest available configuration when opening the screen | Possibly obsolete |
| rev-b / 2022-08-05 | Keep the configuration revision used by the originating batch | Unreviewed replacement proposal |

Recovery narrative: the first write succeeds and the acknowledgement is lost. A retry must inspect the stored logical key before creating another work item. The operator cannot decide from the red banner alone.
Partial completion narrative: the queue task exists, the audit append is pending, and the old export calls the item “complete”. Reporting must expose the mismatch, but the display wording is blank.

### F-030 dependencies and unanswered questions

Related workflow: [Claim intake](functional-specification.md#feature-f-031-claim-intake).
Technical operation: [INT-030](integration-data-and-compliance.md#int-030).
Register context: [Beneficiaries catalogue](product-and-feature-register.md#beneficiaries-catalogue).

- Which team can reopen the disability event after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1330: recover the missing example; owner Operations team.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-031-claim-intake"></a>

## Feature F-031 — Claim intake

Former page: CONF-SYNTH-331. Owner: Benefits stream. Last edited: 2025-11-08.
Tracking: BENEFITS-172. Status: Assumed in release; evidence absent.

The claim shell is described here using the claims vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **received → triaged**. Allow intake even when the coverage lookup is unresolved.
As an operations role, I want to review the claim shell in the selected employer scope so that the next queue can identify the accepted revision.

### F-031 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped claim shell reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Allow intake even when the coverage lookup is unresolved | Date interpretation disputed in the old screen |
| 3 | Review result | A shell claim cannot generate a payment instruction | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-031 rules and exceptions

- RULE-181: Allow intake even when the coverage lookup is unresolved.
- RULE-182: A shell claim cannot generate a payment instruction.
- RULE-183: the claim shell must carry a synthetic tenant scope before any lookup.
- RULE-184: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-185: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-186: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-031 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-031-A | An in-scope claim shell at the starting state | The normal review is accepted | Record received → triaged with a revision reference |
| F-031-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-031-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-031-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a claim shell updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-031 dependencies and unanswered questions

Related workflow: [Claim evidence checklist](functional-specification.md#feature-f-032-claim-evidence-checklist).
Technical operation: [INT-031](integration-data-and-compliance.md#int-031).
Register context: [Claims catalogue](product-and-feature-register.md#claims-catalogue).

- Which team can reopen the claim shell after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1331: recover the missing example; owner Benefits stream.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-032-claim-evidence-checklist"></a>

## Feature F-032 — Claim evidence checklist

Former page: CONF-SYNTH-332. Owner: TBD. Last edited: 2019-12-09.
Tracking: BENEFITS-173. Status: Copied forward without review.

The claim checklist is described here using the claims vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **open → complete**. Record missing evidence as explicit checklist entries.
As an operations role, I want to review the claim checklist in the selected employer scope so that the next queue can identify the accepted revision.

### F-032 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped claim checklist reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Record missing evidence as explicit checklist entries | Date interpretation disputed in the old screen |
| 3 | Review result | Completeness must not imply approval | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-032 rules and exceptions

- RULE-187: Record missing evidence as explicit checklist entries.
- RULE-188: Completeness must not imply approval.
- RULE-189: the claim checklist must carry a synthetic tenant scope before any lookup.
- RULE-190: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-191: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-192: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-032 dependencies and unanswered questions

Related workflow: [Death claim entitlement snapshot](functional-specification.md#feature-f-033-death-claim-entitlement-snapshot).
Technical operation: [INT-032](integration-data-and-compliance.md#int-032).
Register context: [Claims catalogue](product-and-feature-register.md#claims-catalogue).

- Which team can reopen the claim checklist after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1332: recover the missing example; owner TBD.

Short-form page: remaining scenarios were never written. The register overstates the completeness of this feature.


<a id="feature-f-033-death-claim-entitlement-snapshot"></a>

## Feature F-033 — Death claim entitlement snapshot

Former page: CONF-SYNTH-333. Owner: Platform support. Last edited: 2020-01-10.
Tracking: BENEFITS-174. Status: Possibly obsolete.

The entitlement snapshot is described here using the claims vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **candidate → frozen**. Use the designation confirmed at the reported event date even if replaced later.
As an operations role, I want to review the entitlement snapshot in the selected employer scope so that the next queue can identify the accepted revision.

> Conflict group: CG-04

This section requires: Use the designation confirmed at the reported event date even if replaced later.
The incompatible rule is retained in [Beneficiary designation](functional-specification.md#feature-f-025-beneficiary-designation): The latest confirmed designation replaces all previous designations immediately.
Resolution: not agreed. Both statements are fixture inputs; neither silently supersedes the other.

> Compliance note: requires Belgian-market and legal validation.

### F-033 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped entitlement snapshot reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Use the designation confirmed at the reported event date even if replaced later | Date interpretation disputed in the old screen |
| 3 | Review result | The snapshot is a routing aid pending expert validation | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-033 rules and exceptions

- RULE-193: Use the designation confirmed at the reported event date even if replaced later.
- RULE-194: The snapshot is a routing aid pending expert validation.
- RULE-195: the entitlement snapshot must carry a synthetic tenant scope before any lookup.
- RULE-196: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-197: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-198: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-033 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-033-A | An in-scope entitlement snapshot at the starting state | The normal review is accepted | Record candidate → frozen with a revision reference |
| F-033-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-033-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-033-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a entitlement snapshot updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-033 archived workshop addendum

Workshop date 2023-06-27. Former migration team requested a second confirmation screen after a failed retry. No mock-up was retained.
The entitlement snapshot preview was described as disposable. A separate note says previews must be retained when they influenced a reviewed decision. Neither note defines “influenced”.

| Revision fragment | Comment | Disposition |
| --- | --- | --- |
| rev-a / 2024-10-07 | Use the latest available configuration when opening the screen | Possibly obsolete |
| rev-b / 2025-11-08 | Keep the configuration revision used by the originating batch | Unreviewed replacement proposal |

Recovery narrative: the first write succeeds and the acknowledgement is lost. A retry must inspect the stored logical key before creating another work item. The operator cannot decide from the red banner alone.
Partial completion narrative: the queue task exists, the audit append is pending, and the old export calls the item “complete”. Reporting must expose the mismatch, but the display wording is blank.

### F-033 dependencies and unanswered questions

Related workflow: [Disability claim assessment](functional-specification.md#feature-f-034-disability-claim-assessment).
Technical operation: [INT-033](integration-data-and-compliance.md#int-033).
Register context: [Claims catalogue](product-and-feature-register.md#claims-catalogue).

- Which team can reopen the entitlement snapshot after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1333: recover the missing example; owner Platform support.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-034-disability-claim-assessment"></a>

## Feature F-034 — Disability claim assessment

Former page: CONF-SYNTH-334. Owner: Reporting stream. Last edited: 2021-02-11.
Tracking: BENEFITS-175. Status: Draft with missing acceptance.

The assessment task is described here using the claims vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **queued → reviewed**. Require a recorded reviewer role before progressing the task.
As an operations role, I want to review the assessment task in the selected employer scope so that the next queue can identify the accepted revision.

> Compliance note: requires Belgian-market and legal validation.

### F-034 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped assessment task reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Require a recorded reviewer role before progressing the task | Date interpretation disputed in the old screen |
| 3 | Review result | An expired review reopens the checklist | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-034 rules and exceptions

- RULE-199: Require a recorded reviewer role before progressing the task.
- RULE-200: An expired review reopens the checklist.
- RULE-201: the assessment task must carry a synthetic tenant scope before any lookup.
- RULE-202: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-203: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-204: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-034 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-034-A | An in-scope assessment task at the starting state | The normal review is accepted | Record queued → reviewed with a revision reference |
| F-034-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-034-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-034-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a assessment task updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-034 dependencies and unanswered questions

Related workflow: [Retirement claim quotation](functional-specification.md#feature-f-035-retirement-claim-quotation).
Technical operation: [INT-034](integration-data-and-compliance.md#int-034).
Register context: [Claims catalogue](product-and-feature-register.md#claims-catalogue).

- Which team can reopen the assessment task after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1334: recover the missing example; owner Reporting stream.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-035-retirement-claim-quotation"></a>

## Feature F-035 — Retirement claim quotation

Former page: CONF-SYNTH-335. Owner: Former migration team. Last edited: 2022-03-12.
Tracking: BENEFITS-176. Status: Assumed in release; evidence absent.

The quotation draft is described here using the claims vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **requested → quoted**. Separate indicative amounts from approved settlement amounts.
As an operations role, I want to review the quotation draft in the selected employer scope so that the next queue can identify the accepted revision.

> Compliance note: requires Belgian-market and legal validation.

### F-035 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped quotation draft reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Separate indicative amounts from approved settlement amounts | Date interpretation disputed in the old screen |
| 3 | Review result | A recalculation invalidates the prior quote acknowledgement | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-035 rules and exceptions

- RULE-205: Separate indicative amounts from approved settlement amounts.
- RULE-206: A recalculation invalidates the prior quote acknowledgement.
- RULE-207: the quotation draft must carry a synthetic tenant scope before any lookup.
- RULE-208: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-209: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-210: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-035 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-035-A | An in-scope quotation draft at the starting state | The normal review is accepted | Record requested → quoted with a revision reference |
| F-035-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-035-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-035-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a quotation draft updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-035 dependencies and unanswered questions

Related workflow: [Claim appeal and reopening](functional-specification.md#feature-f-036-claim-appeal-and-reopening).
Technical operation: [INT-035](integration-data-and-compliance.md#int-035).
Register context: [Claims catalogue](product-and-feature-register.md#claims-catalogue).

- Which team can reopen the quotation draft after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1335: recover the missing example; owner Former migration team.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-036-claim-appeal-and-reopening"></a>

## Feature F-036 — Claim appeal and reopening

Former page: CONF-SYNTH-336. Owner: Operations team. Last edited: 2023-04-13.
Tracking: BENEFITS-177. Status: Copied forward without review.

The appeal case is described here using the claims vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **closed → reopened**. Preserve the original decision and append the appeal reason.
As an operations role, I want to review the appeal case in the selected employer scope so that the next queue can identify the accepted revision.

### F-036 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped appeal case reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Preserve the original decision and append the appeal reason | Date interpretation disputed in the old screen |
| 3 | Review result | Reopening does not reverse a payment automatically | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-036 rules and exceptions

- RULE-211: Preserve the original decision and append the appeal reason.
- RULE-212: Reopening does not reverse a payment automatically.
- RULE-213: the appeal case must carry a synthetic tenant scope before any lookup.
- RULE-214: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-215: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-216: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-036 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-036-A | An in-scope appeal case at the starting state | The normal review is accepted | Record closed → reopened with a revision reference |
| F-036-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-036-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-036-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a appeal case updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-036 archived workshop addendum

Workshop date 2019-09-03. TBD requested a second confirmation screen after a failed retry. No mock-up was retained.
The appeal case preview was described as disposable. A separate note says previews must be retained when they influenced a reviewed decision. Neither note defines “influenced”.

| Revision fragment | Comment | Disposition |
| --- | --- | --- |
| rev-a / 2020-01-10 | Use the latest available configuration when opening the screen | Possibly obsolete |
| rev-b / 2021-02-11 | Keep the configuration revision used by the originating batch | Unreviewed replacement proposal |

Recovery narrative: the first write succeeds and the acknowledgement is lost. A retry must inspect the stored logical key before creating another work item. The operator cannot decide from the red banner alone.
Partial completion narrative: the queue task exists, the audit append is pending, and the old export calls the item “complete”. Reporting must expose the mismatch, but the display wording is blank.

### F-036 dependencies and unanswered questions

Related workflow: [Payout authorization](functional-specification.md#feature-f-037-payout-authorization).
Technical operation: [INT-036](integration-data-and-compliance.md#int-036).
Register context: [Claims catalogue](product-and-feature-register.md#claims-catalogue).

- Which team can reopen the appeal case after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1336: recover the missing example; owner Operations team.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-037-payout-authorization"></a>

## Feature F-037 — Payout authorization

Former page: CONF-SYNTH-337. Owner: Benefits stream. Last edited: 2024-05-14.
Tracking: BENEFITS-178. Status: Possibly obsolete.

The payout instruction is described here using the payments vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **approved → authorized**. Allow one operations approver to authorize a payout.
As an operations role, I want to review the payout instruction in the selected employer scope so that the next queue can identify the accepted revision.

> Conflict group: CG-05

This section requires: Allow one operations approver to authorize a payout.
The incompatible rule is retained in [Payout release](functional-specification.md#feature-f-039-payout-release): Require two distinct approver roles before any payout release.
Resolution: not agreed. Both statements are fixture inputs; neither silently supersedes the other.

### F-037 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped payout instruction reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Allow one operations approver to authorize a payout | Date interpretation disputed in the old screen |
| 3 | Review result | Authorization applies only to the recorded amount revision | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-037 rules and exceptions

- RULE-217: Allow one operations approver to authorize a payout.
- RULE-218: Authorization applies only to the recorded amount revision.
- RULE-219: the payout instruction must carry a synthetic tenant scope before any lookup.
- RULE-220: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-221: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-222: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-037 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-037-A | An in-scope payout instruction at the starting state | The normal review is accepted | Record approved → authorized with a revision reference |
| F-037-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-037-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-037-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a payout instruction updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-037 dependencies and unanswered questions

Related workflow: [Payout scheduling](functional-specification.md#feature-f-038-payout-scheduling).
Technical operation: [INT-037](integration-data-and-compliance.md#int-037).
Register context: [Payments catalogue](product-and-feature-register.md#payments-catalogue).

- Which team can reopen the payout instruction after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1337: recover the missing example; owner Benefits stream.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-038-payout-scheduling"></a>

## Feature F-038 — Payout scheduling

Former page: CONF-SYNTH-338. Owner: TBD. Last edited: 2025-06-15.
Tracking: BENEFITS-179. Status: Draft with missing acceptance.

The scheduled payout is described here using the payments vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **authorized → scheduled**. Assign a fictional processing window rather than a bank promise.
As an operations role, I want to review the scheduled payout in the selected employer scope so that the next queue can identify the accepted revision.

### F-038 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped scheduled payout reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Assign a fictional processing window rather than a bank promise | Date interpretation disputed in the old screen |
| 3 | Review result | An unavailable window leaves the instruction queued | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-038 rules and exceptions

- RULE-223: Assign a fictional processing window rather than a bank promise.
- RULE-224: An unavailable window leaves the instruction queued.
- RULE-225: the scheduled payout must carry a synthetic tenant scope before any lookup.
- RULE-226: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-227: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-228: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-038 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-038-A | An in-scope scheduled payout at the starting state | The normal review is accepted | Record authorized → scheduled with a revision reference |
| F-038-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-038-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-038-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a scheduled payout updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-038 dependencies and unanswered questions

Related workflow: [Payout release](functional-specification.md#feature-f-039-payout-release).
Technical operation: [INT-038](integration-data-and-compliance.md#int-038).
Register context: [Payments catalogue](product-and-feature-register.md#payments-catalogue).

- Which team can reopen the scheduled payout after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1338: recover the missing example; owner TBD.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-039-payout-release"></a>

## Feature F-039 — Payout release

Former page: CONF-SYNTH-339. Owner: Platform support. Last edited: 2019-07-16.
Tracking: BENEFITS-180. Status: Assumed in release; evidence absent.

The release instruction is described here using the payments vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **scheduled → released**. Require two distinct approver roles before any payout release.
As an operations role, I want to review the release instruction in the selected employer scope so that the next queue can identify the accepted revision.

> Conflict group: CG-05

This section requires: Require two distinct approver roles before any payout release.
The incompatible rule is retained in [Payout authorization](functional-specification.md#feature-f-037-payout-authorization): Allow one operations approver to authorize a payout.
Resolution: not agreed. Both statements are fixture inputs; neither silently supersedes the other.

### F-039 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped release instruction reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Require two distinct approver roles before any payout release | Date interpretation disputed in the old screen |
| 3 | Review result | A changed amount cancels prior approvals | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-039 rules and exceptions

- RULE-229: Require two distinct approver roles before any payout release.
- RULE-230: A changed amount cancels prior approvals.
- RULE-231: the release instruction must carry a synthetic tenant scope before any lookup.
- RULE-232: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-233: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-234: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-039 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-039-A | An in-scope release instruction at the starting state | The normal review is accepted | Record scheduled → released with a revision reference |
| F-039-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-039-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-039-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a release instruction updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-039 archived workshop addendum

Workshop date 2022-12-06. Former migration team requested a second confirmation screen after a failed retry. No mock-up was retained.
The release instruction preview was described as disposable. A separate note says previews must be retained when they influenced a reviewed decision. Neither note defines “influenced”.

| Revision fragment | Comment | Disposition |
| --- | --- | --- |
| rev-a / 2023-04-13 | Use the latest available configuration when opening the screen | Possibly obsolete |
| rev-b / 2024-05-14 | Keep the configuration revision used by the originating batch | Unreviewed replacement proposal |

Recovery narrative: the first write succeeds and the acknowledgement is lost. A retry must inspect the stored logical key before creating another work item. The operator cannot decide from the red banner alone.
Partial completion narrative: the queue task exists, the audit append is pending, and the old export calls the item “complete”. Reporting must expose the mismatch, but the display wording is blank.

### F-039 dependencies and unanswered questions

Related workflow: [Payment return processing](functional-specification.md#feature-f-040-payment-return-processing).
Technical operation: [INT-039](integration-data-and-compliance.md#int-039).
Register context: [Payments catalogue](product-and-feature-register.md#payments-catalogue).

- Which team can reopen the release instruction after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1339: recover the missing example; owner Platform support.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-040-payment-return-processing"></a>

## Feature F-040 — Payment return processing

Former page: CONF-SYNTH-340. Owner: Reporting stream. Last edited: 2020-08-17.
Tracking: BENEFITS-181. Status: Copied forward without review.

The return notice is described here using the payments vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **released → returned**. A return opens a reconciliation item before any retry.
As an operations role, I want to review the return notice in the selected employer scope so that the next queue can identify the accepted revision.

### F-040 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped return notice reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | A return opens a reconciliation item before any retry | Date interpretation disputed in the old screen |
| 3 | Review result | Never infer beneficiary identity from a return message | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-040 rules and exceptions

- RULE-235: A return opens a reconciliation item before any retry.
- RULE-236: Never infer beneficiary identity from a return message.
- RULE-237: the return notice must carry a synthetic tenant scope before any lookup.
- RULE-238: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-239: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-240: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-040 dependencies and unanswered questions

Related workflow: [Payment reconciliation](functional-specification.md#feature-f-041-payment-reconciliation).
Technical operation: [INT-040](integration-data-and-compliance.md#int-040).
Register context: [Payments catalogue](product-and-feature-register.md#payments-catalogue).

- Which team can reopen the return notice after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1340: recover the missing example; owner Reporting stream.

Short-form page: remaining scenarios were never written. The register overstates the completeness of this feature.


<a id="feature-f-041-payment-reconciliation"></a>

## Feature F-041 — Payment reconciliation

Former page: CONF-SYNTH-341. Owner: Former migration team. Last edited: 2021-09-18.
Tracking: BENEFITS-182. Status: Possibly obsolete.

The settlement match is described here using the payments vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **unmatched → reconciled**. Match both the instruction reference and synthetic amount.
As an operations role, I want to review the settlement match in the selected employer scope so that the next queue can identify the accepted revision.

### F-041 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped settlement match reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Match both the instruction reference and synthetic amount | Date interpretation disputed in the old screen |
| 3 | Review result | A many-to-one match requires an explicit grouping record | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-041 rules and exceptions

- RULE-241: Match both the instruction reference and synthetic amount.
- RULE-242: A many-to-one match requires an explicit grouping record.
- RULE-243: the settlement match must carry a synthetic tenant scope before any lookup.
- RULE-244: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-245: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-246: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-041 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-041-A | An in-scope settlement match at the starting state | The normal review is accepted | Record unmatched → reconciled with a revision reference |
| F-041-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-041-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-041-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a settlement match updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-041 dependencies and unanswered questions

Related workflow: [Payment hold removal](functional-specification.md#feature-f-042-payment-hold-removal).
Technical operation: [INT-041](integration-data-and-compliance.md#int-041).
Register context: [Payments catalogue](product-and-feature-register.md#payments-catalogue).

- Which team can reopen the settlement match after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1341: recover the missing example; owner Former migration team.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-042-payment-hold-removal"></a>

## Feature F-042 — Payment hold removal

Former page: CONF-SYNTH-342. Owner: Operations team. Last edited: 2022-10-19.
Tracking: BENEFITS-183. Status: Draft with missing acceptance.

The hold record is described here using the payments vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **held → released-for-review**. Resolve each active hold reason separately.
As an operations role, I want to review the hold record in the selected employer scope so that the next queue can identify the accepted revision.

### F-042 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped hold record reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Resolve each active hold reason separately | Date interpretation disputed in the old screen |
| 3 | Review result | Removing a hold does not itself release money | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-042 rules and exceptions

- RULE-247: Resolve each active hold reason separately.
- RULE-248: Removing a hold does not itself release money.
- RULE-249: the hold record must carry a synthetic tenant scope before any lookup.
- RULE-250: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-251: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-252: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-042 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-042-A | An in-scope hold record at the starting state | The normal review is accepted | Record held → released-for-review with a revision reference |
| F-042-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-042-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-042-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a hold record updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-042 archived workshop addendum

Workshop date 2025-03-09. TBD requested a second confirmation screen after a failed retry. No mock-up was retained.
The hold record preview was described as disposable. A separate note says previews must be retained when they influenced a reviewed decision. Neither note defines “influenced”.

| Revision fragment | Comment | Disposition |
| --- | --- | --- |
| rev-a / 2019-07-16 | Use the latest available configuration when opening the screen | Possibly obsolete |
| rev-b / 2020-08-17 | Keep the configuration revision used by the originating batch | Unreviewed replacement proposal |

Recovery narrative: the first write succeeds and the acknowledgement is lost. A retry must inspect the stored logical key before creating another work item. The operator cannot decide from the red banner alone.
Partial completion narrative: the queue task exists, the audit append is pending, and the old export calls the item “complete”. Reporting must expose the mismatch, but the display wording is blank.

### F-042 dependencies and unanswered questions

Related workflow: [Document template selection](functional-specification.md#feature-f-043-document-template-selection).
Technical operation: [INT-042](integration-data-and-compliance.md#int-042).
Register context: [Payments catalogue](product-and-feature-register.md#payments-catalogue).

- Which team can reopen the hold record after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1342: recover the missing example; owner Operations team.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-043-document-template-selection"></a>

## Feature F-043 — Document template selection

Former page: CONF-SYNTH-343. Owner: Benefits stream. Last edited: 2023-11-20.
Tracking: BENEFITS-184. Status: Assumed in release; evidence absent.

The template selection is described here using the documents vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **unselected → selected**. Choose the template revision effective for the synthetic document date.
As an operations role, I want to review the template selection in the selected employer scope so that the next queue can identify the accepted revision.

### F-043 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped template selection reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Choose the template revision effective for the synthetic document date | Date interpretation disputed in the old screen |
| 3 | Review result | An absent language variant blocks generation | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-043 rules and exceptions

- RULE-253: Choose the template revision effective for the synthetic document date.
- RULE-254: An absent language variant blocks generation.
- RULE-255: the template selection must carry a synthetic tenant scope before any lookup.
- RULE-256: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-257: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-258: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-043 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-043-A | An in-scope template selection at the starting state | The normal review is accepted | Record unselected → selected with a revision reference |
| F-043-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-043-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-043-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a template selection updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-043 dependencies and unanswered questions

Related workflow: [Statement generation](functional-specification.md#feature-f-044-statement-generation).
Technical operation: [INT-043](integration-data-and-compliance.md#int-043).
Register context: [Documents catalogue](product-and-feature-register.md#documents-catalogue).

- Which team can reopen the template selection after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1343: recover the missing example; owner Benefits stream.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-044-statement-generation"></a>

## Feature F-044 — Statement generation

Former page: CONF-SYNTH-344. Owner: TBD. Last edited: 2024-12-21.
Tracking: BENEFITS-185. Status: Copied forward without review.

The statement job is described here using the documents vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **queued → rendered**. Render accepted amounts from one explicit ledger snapshot.
As an operations role, I want to review the statement job in the selected employer scope so that the next queue can identify the accepted revision.

### F-044 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped statement job reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Render accepted amounts from one explicit ledger snapshot | Date interpretation disputed in the old screen |
| 3 | Review result | A mixed snapshot must be rejected | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-044 rules and exceptions

- RULE-259: Render accepted amounts from one explicit ledger snapshot.
- RULE-260: A mixed snapshot must be rejected.
- RULE-261: the statement job must carry a synthetic tenant scope before any lookup.
- RULE-262: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-263: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-264: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-044 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-044-A | An in-scope statement job at the starting state | The normal review is accepted | Record queued → rendered with a revision reference |
| F-044-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-044-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-044-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a statement job updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-044 dependencies and unanswered questions

Related workflow: [Document retention purge](functional-specification.md#feature-f-045-document-retention-purge).
Technical operation: [INT-044](integration-data-and-compliance.md#int-044).
Register context: [Documents catalogue](product-and-feature-register.md#documents-catalogue).

- Which team can reopen the statement job after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1344: recover the missing example; owner TBD.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-045-document-retention-purge"></a>

## Feature F-045 — Document retention purge

Former page: CONF-SYNTH-345. Owner: Platform support. Last edited: 2025-01-22.
Tracking: BENEFITS-186. Status: Possibly obsolete.

The document retention item is described here using the documents vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **expired → purged**. Purge the document bytes after the fictional retention window even when an audit hold exists.
As an operations role, I want to review the document retention item in the selected employer scope so that the next queue can identify the accepted revision.

> Conflict group: CG-06

This section requires: Purge the document bytes after the fictional retention window even when an audit hold exists.
The incompatible rule is retained in [Audit hold preservation](functional-specification.md#feature-f-068-audit-hold-preservation): Preserve document bytes while an audit hold exists even after the retention window.
Resolution: not agreed. Both statements are fixture inputs; neither silently supersedes the other.

> Compliance note: requires Belgian-market and legal validation.

### F-045 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped document retention item reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Purge the document bytes after the fictional retention window even when an audit hold exists | Date interpretation disputed in the old screen |
| 3 | Review result | Keep a tombstone describing the purge attempt | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-045 rules and exceptions

- RULE-265: Purge the document bytes after the fictional retention window even when an audit hold exists.
- RULE-266: Keep a tombstone describing the purge attempt.
- RULE-267: the document retention item must carry a synthetic tenant scope before any lookup.
- RULE-268: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-269: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-270: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-045 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-045-A | An in-scope document retention item at the starting state | The normal review is accepted | Record expired → purged with a revision reference |
| F-045-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-045-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-045-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a document retention item updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-045 archived workshop addendum

Workshop date 2021-06-12. Former migration team requested a second confirmation screen after a failed retry. No mock-up was retained.
The document retention item preview was described as disposable. A separate note says previews must be retained when they influenced a reviewed decision. Neither note defines “influenced”.

| Revision fragment | Comment | Disposition |
| --- | --- | --- |
| rev-a / 2022-10-19 | Use the latest available configuration when opening the screen | Possibly obsolete |
| rev-b / 2023-11-20 | Keep the configuration revision used by the originating batch | Unreviewed replacement proposal |

Recovery narrative: the first write succeeds and the acknowledgement is lost. A retry must inspect the stored logical key before creating another work item. The operator cannot decide from the red banner alone.
Partial completion narrative: the queue task exists, the audit append is pending, and the old export calls the item “complete”. Reporting must expose the mismatch, but the display wording is blank.

### F-045 dependencies and unanswered questions

Related workflow: [Document replacement](functional-specification.md#feature-f-046-document-replacement).
Technical operation: [INT-045](integration-data-and-compliance.md#int-045).
Register context: [Documents catalogue](product-and-feature-register.md#documents-catalogue).

- Which team can reopen the document retention item after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1345: recover the missing example; owner Platform support.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-046-document-replacement"></a>

## Feature F-046 — Document replacement

Former page: CONF-SYNTH-346. Owner: Reporting stream. Last edited: 2019-02-23.
Tracking: BENEFITS-187. Status: Draft with missing acceptance.

The replacement document is described here using the documents vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **issued → superseded**. Issue a replacement with a new revision reference.
As an operations role, I want to review the replacement document in the selected employer scope so that the next queue can identify the accepted revision.

### F-046 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped replacement document reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Issue a replacement with a new revision reference | Date interpretation disputed in the old screen |
| 3 | Review result | The superseded item stays visible to reviewers | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-046 rules and exceptions

- RULE-271: Issue a replacement with a new revision reference.
- RULE-272: The superseded item stays visible to reviewers.
- RULE-273: the replacement document must carry a synthetic tenant scope before any lookup.
- RULE-274: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-275: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-276: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-046 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-046-A | An in-scope replacement document at the starting state | The normal review is accepted | Record issued → superseded with a revision reference |
| F-046-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-046-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-046-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a replacement document updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-046 dependencies and unanswered questions

Related workflow: [Document delivery receipt](functional-specification.md#feature-f-047-document-delivery-receipt).
Technical operation: [INT-046](integration-data-and-compliance.md#int-046).
Register context: [Documents catalogue](product-and-feature-register.md#documents-catalogue).

- Which team can reopen the replacement document after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1346: recover the missing example; owner Reporting stream.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-047-document-delivery-receipt"></a>

## Feature F-047 — Document delivery receipt

Former page: CONF-SYNTH-347. Owner: Former migration team. Last edited: 2020-03-24.
Tracking: BENEFITS-188. Status: Assumed in release; evidence absent.

The delivery receipt is described here using the documents vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **sent → acknowledged**. Distinguish transport acceptance from recipient acknowledgement.
As an operations role, I want to review the delivery receipt in the selected employer scope so that the next queue can identify the accepted revision.

### F-047 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped delivery receipt reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Distinguish transport acceptance from recipient acknowledgement | Date interpretation disputed in the old screen |
| 3 | Review result | A bounced receipt reopens delivery work | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-047 rules and exceptions

- RULE-277: Distinguish transport acceptance from recipient acknowledgement.
- RULE-278: A bounced receipt reopens delivery work.
- RULE-279: the delivery receipt must carry a synthetic tenant scope before any lookup.
- RULE-280: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-281: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-282: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-047 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-047-A | An in-scope delivery receipt at the starting state | The normal review is accepted | Record sent → acknowledged with a revision reference |
| F-047-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-047-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-047-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a delivery receipt updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-047 dependencies and unanswered questions

Related workflow: [Document language selection](functional-specification.md#feature-f-048-document-language-selection).
Technical operation: [INT-047](integration-data-and-compliance.md#int-047).
Register context: [Documents catalogue](product-and-feature-register.md#documents-catalogue).

- Which team can reopen the delivery receipt after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1347: recover the missing example; owner Former migration team.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-048-document-language-selection"></a>

## Feature F-048 — Document language selection

Former page: CONF-SYNTH-348. Owner: Operations team. Last edited: 2021-04-25.
Tracking: BENEFITS-189. Status: Copied forward without review.

The language preference is described here using the documents vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **unset → selected**. Use a configured language code without inferring nationality.
As an operations role, I want to review the language preference in the selected employer scope so that the next queue can identify the accepted revision.

### F-048 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped language preference reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Use a configured language code without inferring nationality | Date interpretation disputed in the old screen |
| 3 | Review result | A missing preference uses the plan review queue | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-048 rules and exceptions

- RULE-283: Use a configured language code without inferring nationality.
- RULE-284: A missing preference uses the plan review queue.
- RULE-285: the language preference must carry a synthetic tenant scope before any lookup.
- RULE-286: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-287: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-288: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-048 archived workshop addendum

Workshop date 2024-09-15. TBD requested a second confirmation screen after a failed retry. No mock-up was retained.
The language preference preview was described as disposable. A separate note says previews must be retained when they influenced a reviewed decision. Neither note defines “influenced”.

| Revision fragment | Comment | Disposition |
| --- | --- | --- |
| rev-a / 2025-01-22 | Use the latest available configuration when opening the screen | Possibly obsolete |
| rev-b / 2019-02-23 | Keep the configuration revision used by the originating batch | Unreviewed replacement proposal |

Recovery narrative: the first write succeeds and the acknowledgement is lost. A retry must inspect the stored logical key before creating another work item. The operator cannot decide from the red banner alone.
Partial completion narrative: the queue task exists, the audit append is pending, and the old export calls the item “complete”. Reporting must expose the mismatch, but the display wording is blank.

### F-048 dependencies and unanswered questions

Related workflow: [Notification preference update](functional-specification.md#feature-f-049-notification-preference-update).
Technical operation: [INT-048](integration-data-and-compliance.md#int-048).
Register context: [Documents catalogue](product-and-feature-register.md#documents-catalogue).

- Which team can reopen the language preference after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1348: recover the missing example; owner Operations team.

Short-form page: remaining scenarios were never written. The register overstates the completeness of this feature.


<a id="feature-f-049-notification-preference-update"></a>

## Feature F-049 — Notification preference update

Former page: CONF-SYNTH-349. Owner: Benefits stream. Last edited: 2022-05-26.
Tracking: BENEFITS-190. Status: Possibly obsolete.

The channel preference is described here using the notifications vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **default → explicit**. Apply preference changes to unsent messages only.
As an operations role, I want to review the channel preference in the selected employer scope so that the next queue can identify the accepted revision.

> Compliance note: requires Belgian-market and legal validation.

### F-049 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped channel preference reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Apply preference changes to unsent messages only | Date interpretation disputed in the old screen |
| 3 | Review result | Mandatory-message classification is an unvalidated placeholder | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-049 rules and exceptions

- RULE-289: Apply preference changes to unsent messages only.
- RULE-290: Mandatory-message classification is an unvalidated placeholder.
- RULE-291: the channel preference must carry a synthetic tenant scope before any lookup.
- RULE-292: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-293: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-294: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-049 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-049-A | An in-scope channel preference at the starting state | The normal review is accepted | Record default → explicit with a revision reference |
| F-049-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-049-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-049-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a channel preference updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-049 dependencies and unanswered questions

Related workflow: [Eligibility notification](functional-specification.md#feature-f-050-eligibility-notification).
Technical operation: [INT-049](integration-data-and-compliance.md#int-049).
Register context: [Notifications catalogue](product-and-feature-register.md#notifications-catalogue).

- Which team can reopen the channel preference after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1349: recover the missing example; owner Benefits stream.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-050-eligibility-notification"></a>

## Feature F-050 — Eligibility notification

Former page: CONF-SYNTH-350. Owner: TBD. Last edited: 2023-06-27.
Tracking: BENEFITS-191. Status: Draft with missing acceptance.

The eligibility message is described here using the notifications vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **prepared → queued**. Reference the decision revision shown in the portal.
As an operations role, I want to review the eligibility message in the selected employer scope so that the next queue can identify the accepted revision.

### F-050 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped eligibility message reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Reference the decision revision shown in the portal | Date interpretation disputed in the old screen |
| 3 | Review result | A reversed decision requires a new message record | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-050 rules and exceptions

- RULE-295: Reference the decision revision shown in the portal.
- RULE-296: A reversed decision requires a new message record.
- RULE-297: the eligibility message must carry a synthetic tenant scope before any lookup.
- RULE-298: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-299: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-300: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-050 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-050-A | An in-scope eligibility message at the starting state | The normal review is accepted | Record prepared → queued with a revision reference |
| F-050-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-050-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-050-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a eligibility message updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-050 dependencies and unanswered questions

Related workflow: [Contribution reminder](functional-specification.md#feature-f-051-contribution-reminder).
Technical operation: [INT-050](integration-data-and-compliance.md#int-050).
Register context: [Notifications catalogue](product-and-feature-register.md#notifications-catalogue).

- Which team can reopen the eligibility message after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1350: recover the missing example; owner TBD.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-051-contribution-reminder"></a>

## Feature F-051 — Contribution reminder

Former page: CONF-SYNTH-351. Owner: Platform support. Last edited: 2024-07-01.
Tracking: BENEFITS-192. Status: Assumed in release; evidence absent.

The reminder candidate is described here using the notifications vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **overdue → queued**. Check the current dispute flag before constructing the reminder.
As an operations role, I want to review the reminder candidate in the selected employer scope so that the next queue can identify the accepted revision.

### F-051 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped reminder candidate reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Check the current dispute flag before constructing the reminder | Date interpretation disputed in the old screen |
| 3 | Review result | Do not combine distinct employer accounts in one message | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-051 rules and exceptions

- RULE-301: Check the current dispute flag before constructing the reminder.
- RULE-302: Do not combine distinct employer accounts in one message.
- RULE-303: the reminder candidate must carry a synthetic tenant scope before any lookup.
- RULE-304: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-305: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-306: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-051 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-051-A | An in-scope reminder candidate at the starting state | The normal review is accepted | Record overdue → queued with a revision reference |
| F-051-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-051-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-051-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a reminder candidate updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-051 archived workshop addendum

Workshop date 2020-12-18. Former migration team requested a second confirmation screen after a failed retry. No mock-up was retained.
The reminder candidate preview was described as disposable. A separate note says previews must be retained when they influenced a reviewed decision. Neither note defines “influenced”.

| Revision fragment | Comment | Disposition |
| --- | --- | --- |
| rev-a / 2021-04-25 | Use the latest available configuration when opening the screen | Possibly obsolete |
| rev-b / 2022-05-26 | Keep the configuration revision used by the originating batch | Unreviewed replacement proposal |

Recovery narrative: the first write succeeds and the acknowledgement is lost. A retry must inspect the stored logical key before creating another work item. The operator cannot decide from the red banner alone.
Partial completion narrative: the queue task exists, the audit append is pending, and the old export calls the item “complete”. Reporting must expose the mismatch, but the display wording is blank.

### F-051 dependencies and unanswered questions

Related workflow: [Claim status notification](functional-specification.md#feature-f-052-claim-status-notification).
Technical operation: [INT-051](integration-data-and-compliance.md#int-051).
Register context: [Notifications catalogue](product-and-feature-register.md#notifications-catalogue).

- Which team can reopen the reminder candidate after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1351: recover the missing example; owner Platform support.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-052-claim-status-notification"></a>

## Feature F-052 — Claim status notification

Former page: CONF-SYNTH-352. Owner: Reporting stream. Last edited: 2025-08-02.
Tracking: BENEFITS-193. Status: Copied forward without review.

The claim message is described here using the notifications vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **changed → queued**. Expose only the approved display status.
As an operations role, I want to review the claim message in the selected employer scope so that the next queue can identify the accepted revision.

### F-052 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped claim message reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Expose only the approved display status | Date interpretation disputed in the old screen |
| 3 | Review result | Internal reviewer comments must not enter the template | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-052 rules and exceptions

- RULE-307: Expose only the approved display status.
- RULE-308: Internal reviewer comments must not enter the template.
- RULE-309: the claim message must carry a synthetic tenant scope before any lookup.
- RULE-310: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-311: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-312: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-052 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-052-A | An in-scope claim message at the starting state | The normal review is accepted | Record changed → queued with a revision reference |
| F-052-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-052-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-052-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a claim message updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-052 dependencies and unanswered questions

Related workflow: [Notification retry](functional-specification.md#feature-f-053-notification-retry).
Technical operation: [INT-052](integration-data-and-compliance.md#int-052).
Register context: [Notifications catalogue](product-and-feature-register.md#notifications-catalogue).

- Which team can reopen the claim message after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1352: recover the missing example; owner Reporting stream.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-053-notification-retry"></a>

## Feature F-053 — Notification retry

Former page: CONF-SYNTH-353. Owner: Former migration team. Last edited: 2019-09-03.
Tracking: BENEFITS-194. Status: Possibly obsolete.

The retry item is described here using the notifications vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **failed → requeued**. Reuse the logical message key while creating a new attempt.
As an operations role, I want to review the retry item in the selected employer scope so that the next queue can identify the accepted revision.

### F-053 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped retry item reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Reuse the logical message key while creating a new attempt | Date interpretation disputed in the old screen |
| 3 | Review result | An unknown delivery result needs reconciliation before retry | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-053 rules and exceptions

- RULE-313: Reuse the logical message key while creating a new attempt.
- RULE-314: An unknown delivery result needs reconciliation before retry.
- RULE-315: the retry item must carry a synthetic tenant scope before any lookup.
- RULE-316: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-317: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-318: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-053 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-053-A | An in-scope retry item at the starting state | The normal review is accepted | Record failed → requeued with a revision reference |
| F-053-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-053-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-053-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a retry item updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-053 dependencies and unanswered questions

Related workflow: [Notification suppression](functional-specification.md#feature-f-054-notification-suppression).
Technical operation: [INT-053](integration-data-and-compliance.md#int-053).
Register context: [Notifications catalogue](product-and-feature-register.md#notifications-catalogue).

- Which team can reopen the retry item after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1353: recover the missing example; owner Former migration team.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-054-notification-suppression"></a>

## Feature F-054 — Notification suppression

Former page: CONF-SYNTH-354. Owner: Operations team. Last edited: 2020-10-04.
Tracking: BENEFITS-195. Status: Draft with missing acceptance.

The suppression window is described here using the notifications vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **enabled → suppressed**. Record the reason and expiry of the suppression.
As an operations role, I want to review the suppression window in the selected employer scope so that the next queue can identify the accepted revision.

### F-054 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped suppression window reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Record the reason and expiry of the suppression | Date interpretation disputed in the old screen |
| 3 | Review result | An expired suppression does not resend historical messages | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-054 rules and exceptions

- RULE-319: Record the reason and expiry of the suppression.
- RULE-320: An expired suppression does not resend historical messages.
- RULE-321: the suppression window must carry a synthetic tenant scope before any lookup.
- RULE-322: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-323: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-324: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-054 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-054-A | An in-scope suppression window at the starting state | The normal review is accepted | Record enabled → suppressed with a revision reference |
| F-054-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-054-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-054-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a suppression window updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-054 archived workshop addendum

Workshop date 2023-03-21. TBD requested a second confirmation screen after a failed retry. No mock-up was retained.
The suppression window preview was described as disposable. A separate note says previews must be retained when they influenced a reviewed decision. Neither note defines “influenced”.

| Revision fragment | Comment | Disposition |
| --- | --- | --- |
| rev-a / 2024-07-01 | Use the latest available configuration when opening the screen | Possibly obsolete |
| rev-b / 2025-08-02 | Keep the configuration revision used by the originating batch | Unreviewed replacement proposal |

Recovery narrative: the first write succeeds and the acknowledgement is lost. A retry must inspect the stored logical key before creating another work item. The operator cannot decide from the red banner alone.
Partial completion narrative: the queue task exists, the audit append is pending, and the old export calls the item “complete”. Reporting must expose the mismatch, but the display wording is blank.

### F-054 dependencies and unanswered questions

Related workflow: [Employer coverage report](functional-specification.md#feature-f-055-employer-coverage-report).
Technical operation: [INT-054](integration-data-and-compliance.md#int-054).
Register context: [Notifications catalogue](product-and-feature-register.md#notifications-catalogue).

- Which team can reopen the suppression window after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1354: recover the missing example; owner Operations team.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-055-employer-coverage-report"></a>

## Feature F-055 — Employer coverage report

Former page: CONF-SYNTH-355. Owner: Benefits stream. Last edited: 2021-11-05.
Tracking: BENEFITS-196. Status: Assumed in release; evidence absent.

The coverage report is described here using the reporting vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **requested → generated**. Bind the extract to an explicit as-of date.
As an operations role, I want to review the coverage report in the selected employer scope so that the next queue can identify the accepted revision.

### F-055 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped coverage report reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Bind the extract to an explicit as-of date | Date interpretation disputed in the old screen |
| 3 | Review result | Late corrections require a new report revision | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-055 rules and exceptions

- RULE-325: Bind the extract to an explicit as-of date.
- RULE-326: Late corrections require a new report revision.
- RULE-327: the coverage report must carry a synthetic tenant scope before any lookup.
- RULE-328: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-329: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-330: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-055 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-055-A | An in-scope coverage report at the starting state | The normal review is accepted | Record requested → generated with a revision reference |
| F-055-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-055-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-055-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a coverage report updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-055 dependencies and unanswered questions

Related workflow: [Contribution exception report](functional-specification.md#feature-f-056-contribution-exception-report).
Technical operation: [INT-055](integration-data-and-compliance.md#int-055).
Register context: [Reporting catalogue](product-and-feature-register.md#reporting-catalogue).

- Which team can reopen the coverage report after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1355: recover the missing example; owner Benefits stream.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-056-contribution-exception-report"></a>

## Feature F-056 — Contribution exception report

Former page: CONF-SYNTH-356. Owner: TBD. Last edited: 2022-12-06.
Tracking: BENEFITS-197. Status: Copied forward without review.

The exception report is described here using the reporting vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **open → exported**. Separate rejected rows from accepted rows with warnings.
As an operations role, I want to review the exception report in the selected employer scope so that the next queue can identify the accepted revision.

### F-056 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped exception report reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Separate rejected rows from accepted rows with warnings | Date interpretation disputed in the old screen |
| 3 | Review result | An empty report still records its selection parameters | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-056 rules and exceptions

- RULE-331: Separate rejected rows from accepted rows with warnings.
- RULE-332: An empty report still records its selection parameters.
- RULE-333: the exception report must carry a synthetic tenant scope before any lookup.
- RULE-334: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-335: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-336: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-056 dependencies and unanswered questions

Related workflow: [Claim ageing report](functional-specification.md#feature-f-057-claim-ageing-report).
Technical operation: [INT-056](integration-data-and-compliance.md#int-056).
Register context: [Reporting catalogue](product-and-feature-register.md#reporting-catalogue).

- Which team can reopen the exception report after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1356: recover the missing example; owner TBD.

Short-form page: remaining scenarios were never written. The register overstates the completeness of this feature.


<a id="feature-f-057-claim-ageing-report"></a>

## Feature F-057 — Claim ageing report

Former page: CONF-SYNTH-357. Owner: Platform support. Last edited: 2023-01-07.
Tracking: BENEFITS-198. Status: Possibly obsolete.

The ageing report is described here using the reporting vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **selected → generated**. Measure queue duration from the latest triage start.
As an operations role, I want to review the ageing report in the selected employer scope so that the next queue can identify the accepted revision.

### F-057 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped ageing report reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Measure queue duration from the latest triage start | Date interpretation disputed in the old screen |
| 3 | Review result | Appeals need a separate ageing basis | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-057 rules and exceptions

- RULE-337: Measure queue duration from the latest triage start.
- RULE-338: Appeals need a separate ageing basis.
- RULE-339: the ageing report must carry a synthetic tenant scope before any lookup.
- RULE-340: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-341: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-342: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-057 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-057-A | An in-scope ageing report at the starting state | The normal review is accepted | Record selected → generated with a revision reference |
| F-057-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-057-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-057-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a ageing report updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-057 archived workshop addendum

Workshop date 2019-06-24. Former migration team requested a second confirmation screen after a failed retry. No mock-up was retained.
The ageing report preview was described as disposable. A separate note says previews must be retained when they influenced a reviewed decision. Neither note defines “influenced”.

| Revision fragment | Comment | Disposition |
| --- | --- | --- |
| rev-a / 2020-10-04 | Use the latest available configuration when opening the screen | Possibly obsolete |
| rev-b / 2021-11-05 | Keep the configuration revision used by the originating batch | Unreviewed replacement proposal |

Recovery narrative: the first write succeeds and the acknowledgement is lost. A retry must inspect the stored logical key before creating another work item. The operator cannot decide from the red banner alone.
Partial completion narrative: the queue task exists, the audit append is pending, and the old export calls the item “complete”. Reporting must expose the mismatch, but the display wording is blank.

### F-057 dependencies and unanswered questions

Related workflow: [Branch 21 label review](functional-specification.md#feature-f-058-branch-21-label-review).
Technical operation: [INT-057](integration-data-and-compliance.md#int-057).
Register context: [Reporting catalogue](product-and-feature-register.md#reporting-catalogue).

- Which team can reopen the ageing report after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1357: recover the missing example; owner Platform support.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-058-branch-21-label-review"></a>

## Feature F-058 — Branch 21 label review

Former page: CONF-SYNTH-358. Owner: Reporting stream. Last edited: 2024-02-08.
Tracking: BENEFITS-199. Status: Draft with missing acceptance.

The branch label review is described here using the reporting vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **unclassified → pending-validation**. Treat Branch 21 as an unvalidated catalogue label only.
As an operations role, I want to review the branch label review in the selected employer scope so that the next queue can identify the accepted revision.

> Compliance note: requires Belgian-market and legal validation.

Branch 21 is text for compliance review, not a promise about guarantees, investments, tax, reporting, or legal classification.

### F-058 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped branch label review reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Treat Branch 21 as an unvalidated catalogue label only | Date interpretation disputed in the old screen |
| 3 | Review result | Do not infer guarantees or eligibility from the label | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-058 rules and exceptions

- RULE-343: Treat Branch 21 as an unvalidated catalogue label only.
- RULE-344: Do not infer guarantees or eligibility from the label.
- RULE-345: the branch label review must carry a synthetic tenant scope before any lookup.
- RULE-346: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-347: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-348: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-058 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-058-A | An in-scope branch label review at the starting state | The normal review is accepted | Record unclassified → pending-validation with a revision reference |
| F-058-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-058-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-058-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a branch label review updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-058 dependencies and unanswered questions

Related workflow: [Branch 23 label review](functional-specification.md#feature-f-059-branch-23-label-review).
Technical operation: [INT-058](integration-data-and-compliance.md#int-058).
Register context: [Reporting catalogue](product-and-feature-register.md#reporting-catalogue).

- Which team can reopen the branch label review after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1358: recover the missing example; owner Reporting stream.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-059-branch-23-label-review"></a>

## Feature F-059 — Branch 23 label review

Former page: CONF-SYNTH-359. Owner: Former migration team. Last edited: 2025-03-09.
Tracking: BENEFITS-200. Status: Assumed in release; evidence absent.

The branch label review is described here using the reporting vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **unclassified → pending-validation**. Treat Branch 23 as an unvalidated catalogue label only.
As an operations role, I want to review the branch label review in the selected employer scope so that the next queue can identify the accepted revision.

> Compliance note: requires Belgian-market and legal validation.

Branch 23 is text for compliance review, not a promise about guarantees, investments, tax, reporting, or legal classification.

### F-059 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped branch label review reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Treat Branch 23 as an unvalidated catalogue label only | Date interpretation disputed in the old screen |
| 3 | Review result | Do not infer investment rules or disclosures from the label | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-059 rules and exceptions

- RULE-349: Treat Branch 23 as an unvalidated catalogue label only.
- RULE-350: Do not infer investment rules or disclosures from the label.
- RULE-351: the branch label review must carry a synthetic tenant scope before any lookup.
- RULE-352: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-353: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-354: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-059 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-059-A | An in-scope branch label review at the starting state | The normal review is accepted | Record unclassified → pending-validation with a revision reference |
| F-059-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-059-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-059-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a branch label review updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-059 dependencies and unanswered questions

Related workflow: [Sigedis reporting placeholder](functional-specification.md#feature-f-060-sigedis-reporting-placeholder).
Technical operation: [INT-059](integration-data-and-compliance.md#int-059).
Register context: [Reporting catalogue](product-and-feature-register.md#reporting-catalogue).

- Which team can reopen the branch label review after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1359: recover the missing example; owner Former migration team.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-060-sigedis-reporting-placeholder"></a>

## Feature F-060 — Sigedis reporting placeholder

Former page: CONF-SYNTH-360. Owner: Operations team. Last edited: 2019-04-10.
Tracking: BENEFITS-201. Status: Copied forward without review.

The report envelope is described here using the reporting vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **draft → validation-required**. Disable external transmission until an approved mapping exists.
As an operations role, I want to review the report envelope in the selected employer scope so that the next queue can identify the accepted revision.

> Compliance note: requires Belgian-market and legal validation.

The Sigedis-related adapter has no validated external contract, destination, schema, deadline, or accepted response vocabulary. INT-060 names only an internal simulator.

### F-060 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped report envelope reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Disable external transmission until an approved mapping exists | Date interpretation disputed in the old screen |
| 3 | Review result | No official schema or reporting deadline is supplied here | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-060 rules and exceptions

- RULE-355: Disable external transmission until an approved mapping exists.
- RULE-356: No official schema or reporting deadline is supplied here.
- RULE-357: the report envelope must carry a synthetic tenant scope before any lookup.
- RULE-358: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-359: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-360: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-060 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-060-A | An in-scope report envelope at the starting state | The normal review is accepted | Record draft → validation-required with a revision reference |
| F-060-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-060-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-060-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a report envelope updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-060 archived workshop addendum

Workshop date 2022-09-27. TBD requested a second confirmation screen after a failed retry. No mock-up was retained.
The report envelope preview was described as disposable. A separate note says previews must be retained when they influenced a reviewed decision. Neither note defines “influenced”.

| Revision fragment | Comment | Disposition |
| --- | --- | --- |
| rev-a / 2023-01-07 | Use the latest available configuration when opening the screen | Possibly obsolete |
| rev-b / 2024-02-08 | Keep the configuration revision used by the originating batch | Unreviewed replacement proposal |

Recovery narrative: the first write succeeds and the acknowledgement is lost. A retry must inspect the stored logical key before creating another work item. The operator cannot decide from the red banner alone.
Partial completion narrative: the queue task exists, the audit append is pending, and the old export calls the item “complete”. Reporting must expose the mismatch, but the display wording is blank.

### F-060 dependencies and unanswered questions

Related workflow: [User role assignment](functional-specification.md#feature-f-061-user-role-assignment).
Technical operation: [INT-060](integration-data-and-compliance.md#int-060).
Register context: [Reporting catalogue](product-and-feature-register.md#reporting-catalogue).

- Which team can reopen the report envelope after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1360: recover the missing example; owner Operations team.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-061-user-role-assignment"></a>

## Feature F-061 — User role assignment

Former page: CONF-SYNTH-361. Owner: Benefits stream. Last edited: 2020-05-11.
Tracking: BENEFITS-202. Status: Possibly obsolete.

The role grant is described here using the administration vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **requested → granted**. Scope a grant to one employer or an explicit support scope.
As an operations role, I want to review the role grant in the selected employer scope so that the next queue can identify the accepted revision.

### F-061 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped role grant reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Scope a grant to one employer or an explicit support scope | Date interpretation disputed in the old screen |
| 3 | Review result | A scope omission must not mean all employers | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-061 rules and exceptions

- RULE-361: Scope a grant to one employer or an explicit support scope.
- RULE-362: A scope omission must not mean all employers.
- RULE-363: the role grant must carry a synthetic tenant scope before any lookup.
- RULE-364: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-365: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-366: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-061 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-061-A | An in-scope role grant at the starting state | The normal review is accepted | Record requested → granted with a revision reference |
| F-061-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-061-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-061-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a role grant updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-061 dependencies and unanswered questions

Related workflow: [Permission override](functional-specification.md#feature-f-062-permission-override).
Technical operation: [INT-061](integration-data-and-compliance.md#int-061).
Register context: [Administration catalogue](product-and-feature-register.md#administration-catalogue).

- Which team can reopen the role grant after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1361: recover the missing example; owner Benefits stream.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-062-permission-override"></a>

## Feature F-062 — Permission override

Former page: CONF-SYNTH-362. Owner: TBD. Last edited: 2021-06-12.
Tracking: BENEFITS-203. Status: Draft with missing acceptance.

The override request is described here using the administration vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **denied → temporarily-allowed**. Record a reason and expiry for the override.
As an operations role, I want to review the override request in the selected employer scope so that the next queue can identify the accepted revision.

### F-062 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped override request reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Record a reason and expiry for the override | Date interpretation disputed in the old screen |
| 3 | Review result | An expired override cannot be inherited by a batch job | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-062 rules and exceptions

- RULE-367: Record a reason and expiry for the override.
- RULE-368: An expired override cannot be inherited by a batch job.
- RULE-369: the override request must carry a synthetic tenant scope before any lookup.
- RULE-370: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-371: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-372: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-062 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-062-A | An in-scope override request at the starting state | The normal review is accepted | Record denied → temporarily-allowed with a revision reference |
| F-062-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-062-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-062-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a override request updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-062 dependencies and unanswered questions

Related workflow: [Reference code maintenance](functional-specification.md#feature-f-063-reference-code-maintenance).
Technical operation: [INT-062](integration-data-and-compliance.md#int-062).
Register context: [Administration catalogue](product-and-feature-register.md#administration-catalogue).

- Which team can reopen the override request after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1362: recover the missing example; owner TBD.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-063-reference-code-maintenance"></a>

## Feature F-063 — Reference code maintenance

Former page: CONF-SYNTH-363. Owner: Platform support. Last edited: 2022-07-13.
Tracking: BENEFITS-204. Status: Assumed in release; evidence absent.

The reference code is described here using the administration vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **proposed → active**. Version changes to code meaning.
As an operations role, I want to review the reference code in the selected employer scope so that the next queue can identify the accepted revision.

### F-063 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped reference code reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Version changes to code meaning | Date interpretation disputed in the old screen |
| 3 | Review result | A retired code remains readable on historical records | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-063 rules and exceptions

- RULE-373: Version changes to code meaning.
- RULE-374: A retired code remains readable on historical records.
- RULE-375: the reference code must carry a synthetic tenant scope before any lookup.
- RULE-376: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-377: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-378: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-063 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-063-A | An in-scope reference code at the starting state | The normal review is accepted | Record proposed → active with a revision reference |
| F-063-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-063-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-063-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a reference code updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-063 archived workshop addendum

Workshop date 2025-12-03. Former migration team requested a second confirmation screen after a failed retry. No mock-up was retained.
The reference code preview was described as disposable. A separate note says previews must be retained when they influenced a reviewed decision. Neither note defines “influenced”.

| Revision fragment | Comment | Disposition |
| --- | --- | --- |
| rev-a / 2019-04-10 | Use the latest available configuration when opening the screen | Possibly obsolete |
| rev-b / 2020-05-11 | Keep the configuration revision used by the originating batch | Unreviewed replacement proposal |

Recovery narrative: the first write succeeds and the acknowledgement is lost. A retry must inspect the stored logical key before creating another work item. The operator cannot decide from the red banner alone.
Partial completion narrative: the queue task exists, the audit append is pending, and the old export calls the item “complete”. Reporting must expose the mismatch, but the display wording is blank.

### F-063 dependencies and unanswered questions

Related workflow: [Plan configuration publishing](functional-specification.md#feature-f-064-plan-configuration-publishing).
Technical operation: [INT-063](integration-data-and-compliance.md#int-063).
Register context: [Administration catalogue](product-and-feature-register.md#administration-catalogue).

- Which team can reopen the reference code after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1363: recover the missing example; owner Platform support.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-064-plan-configuration-publishing"></a>

## Feature F-064 — Plan configuration publishing

Former page: CONF-SYNTH-364. Owner: Reporting stream. Last edited: 2023-08-14.
Tracking: BENEFITS-205. Status: Copied forward without review.

The plan revision is described here using the administration vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **draft → published**. Publish a complete reviewed revision as one unit.
As an operations role, I want to review the plan revision in the selected employer scope so that the next queue can identify the accepted revision.

### F-064 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped plan revision reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Publish a complete reviewed revision as one unit | Date interpretation disputed in the old screen |
| 3 | Review result | A partial revision remains unavailable to calculation | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-064 rules and exceptions

- RULE-379: Publish a complete reviewed revision as one unit.
- RULE-380: A partial revision remains unavailable to calculation.
- RULE-381: the plan revision must carry a synthetic tenant scope before any lookup.
- RULE-382: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-383: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-384: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-064 dependencies and unanswered questions

Related workflow: [Operational task reassignment](functional-specification.md#feature-f-065-operational-task-reassignment).
Technical operation: [INT-064](integration-data-and-compliance.md#int-064).
Register context: [Administration catalogue](product-and-feature-register.md#administration-catalogue).

- Which team can reopen the plan revision after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1364: recover the missing example; owner Reporting stream.

Short-form page: remaining scenarios were never written. The register overstates the completeness of this feature.


<a id="feature-f-065-operational-task-reassignment"></a>

## Feature F-065 — Operational task reassignment

Former page: CONF-SYNTH-365. Owner: Former migration team. Last edited: 2024-09-15.
Tracking: BENEFITS-206. Status: Possibly obsolete.

The task assignment is described here using the administration vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **queued → reassigned**. Transfer ownership without resetting queue age.
As an operations role, I want to review the task assignment in the selected employer scope so that the next queue can identify the accepted revision.

### F-065 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped task assignment reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Transfer ownership without resetting queue age | Date interpretation disputed in the old screen |
| 3 | Review result | An unavailable team leaves the task unassigned | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-065 rules and exceptions

- RULE-385: Transfer ownership without resetting queue age.
- RULE-386: An unavailable team leaves the task unassigned.
- RULE-387: the task assignment must carry a synthetic tenant scope before any lookup.
- RULE-388: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-389: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-390: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-065 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-065-A | An in-scope task assignment at the starting state | The normal review is accepted | Record queued → reassigned with a revision reference |
| F-065-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-065-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-065-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a task assignment updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-065 dependencies and unanswered questions

Related workflow: [Tenant boundary review](functional-specification.md#feature-f-066-tenant-boundary-review).
Technical operation: [INT-065](integration-data-and-compliance.md#int-065).
Register context: [Administration catalogue](product-and-feature-register.md#administration-catalogue).

- Which team can reopen the task assignment after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1365: recover the missing example; owner Former migration team.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-066-tenant-boundary-review"></a>

## Feature F-066 — Tenant boundary review

Former page: CONF-SYNTH-366. Owner: Operations team. Last edited: 2025-10-16.
Tracking: BENEFITS-207. Status: Draft with missing acceptance.

The tenant scope is described here using the administration vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **unchecked → reviewed**. Require explicit synthetic tenant context on every record lookup.
As an operations role, I want to review the tenant scope in the selected employer scope so that the next queue can identify the accepted revision.

### F-066 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped tenant scope reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Require explicit synthetic tenant context on every record lookup | Date interpretation disputed in the old screen |
| 3 | Review result | A missing context produces a denial rather than a fallback | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-066 rules and exceptions

- RULE-391: Require explicit synthetic tenant context on every record lookup.
- RULE-392: A missing context produces a denial rather than a fallback.
- RULE-393: the tenant scope must carry a synthetic tenant scope before any lookup.
- RULE-394: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-395: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-396: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-066 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-066-A | An in-scope tenant scope at the starting state | The normal review is accepted | Record unchecked → reviewed with a revision reference |
| F-066-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-066-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-066-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a tenant scope updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-066 archived workshop addendum

Workshop date 2021-03-06. TBD requested a second confirmation screen after a failed retry. No mock-up was retained.
The tenant scope preview was described as disposable. A separate note says previews must be retained when they influenced a reviewed decision. Neither note defines “influenced”.

| Revision fragment | Comment | Disposition |
| --- | --- | --- |
| rev-a / 2022-07-13 | Use the latest available configuration when opening the screen | Possibly obsolete |
| rev-b / 2023-08-14 | Keep the configuration revision used by the originating batch | Unreviewed replacement proposal |

Recovery narrative: the first write succeeds and the acknowledgement is lost. A retry must inspect the stored logical key before creating another work item. The operator cannot decide from the red banner alone.
Partial completion narrative: the queue task exists, the audit append is pending, and the old export calls the item “complete”. Reporting must expose the mismatch, but the display wording is blank.

### F-066 dependencies and unanswered questions

Related workflow: [Audit event capture](functional-specification.md#feature-f-067-audit-event-capture).
Technical operation: [INT-066](integration-data-and-compliance.md#int-066).
Register context: [Administration catalogue](product-and-feature-register.md#administration-catalogue).

- Which team can reopen the tenant scope after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1366: recover the missing example; owner Operations team.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-067-audit-event-capture"></a>

## Feature F-067 — Audit event capture

Former page: CONF-SYNTH-367. Owner: Benefits stream. Last edited: 2019-11-17.
Tracking: BENEFITS-208. Status: Assumed in release; evidence absent.

The audit envelope is described here using the audit vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **observed → appended**. Append a new event for a changed business decision.
As an operations role, I want to review the audit envelope in the selected employer scope so that the next queue can identify the accepted revision.

### F-067 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped audit envelope reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Append a new event for a changed business decision | Date interpretation disputed in the old screen |
| 3 | Review result | An audit write failure must be visible to the caller | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-067 rules and exceptions

- RULE-397: Append a new event for a changed business decision.
- RULE-398: An audit write failure must be visible to the caller.
- RULE-399: the audit envelope must carry a synthetic tenant scope before any lookup.
- RULE-400: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-401: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-402: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-067 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-067-A | An in-scope audit envelope at the starting state | The normal review is accepted | Record observed → appended with a revision reference |
| F-067-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-067-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-067-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a audit envelope updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-067 dependencies and unanswered questions

Related workflow: [Audit hold preservation](functional-specification.md#feature-f-068-audit-hold-preservation).
Technical operation: [INT-067](integration-data-and-compliance.md#int-067).
Register context: [Audit catalogue](product-and-feature-register.md#audit-catalogue).

- Which team can reopen the audit envelope after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1367: recover the missing example; owner Benefits stream.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-068-audit-hold-preservation"></a>

## Feature F-068 — Audit hold preservation

Former page: CONF-SYNTH-368. Owner: TBD. Last edited: 2020-12-18.
Tracking: BENEFITS-209. Status: Copied forward without review.

The audit hold is described here using the audit vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **requested → applied**. Preserve document bytes while an audit hold exists even after the retention window.
As an operations role, I want to review the audit hold in the selected employer scope so that the next queue can identify the accepted revision.

> Conflict group: CG-06

This section requires: Preserve document bytes while an audit hold exists even after the retention window.
The incompatible rule is retained in [Document retention purge](functional-specification.md#feature-f-045-document-retention-purge): Purge the document bytes after the fictional retention window even when an audit hold exists.
Resolution: not agreed. Both statements are fixture inputs; neither silently supersedes the other.

> Compliance note: requires Belgian-market and legal validation.

### F-068 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped audit hold reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Preserve document bytes while an audit hold exists even after the retention window | Date interpretation disputed in the old screen |
| 3 | Review result | An unresolved hold has no automatic expiry | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-068 rules and exceptions

- RULE-403: Preserve document bytes while an audit hold exists even after the retention window.
- RULE-404: An unresolved hold has no automatic expiry.
- RULE-405: the audit hold must carry a synthetic tenant scope before any lookup.
- RULE-406: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-407: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-408: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-068 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-068-A | An in-scope audit hold at the starting state | The normal review is accepted | Record requested → applied with a revision reference |
| F-068-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-068-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-068-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a audit hold updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-068 dependencies and unanswered questions

Related workflow: [Audit event search](functional-specification.md#feature-f-069-audit-event-search).
Technical operation: [INT-068](integration-data-and-compliance.md#int-068).
Register context: [Audit catalogue](product-and-feature-register.md#audit-catalogue).

- Which team can reopen the audit hold after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1368: recover the missing example; owner TBD.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-069-audit-event-search"></a>

## Feature F-069 — Audit event search

Former page: CONF-SYNTH-369. Owner: Platform support. Last edited: 2021-01-19.
Tracking: BENEFITS-210. Status: Possibly obsolete.

The audit query is described here using the audit vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **requested → executed**. Filter by tenant scope before applying time filters.
As an operations role, I want to review the audit query in the selected employer scope so that the next queue can identify the accepted revision.

### F-069 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped audit query reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Filter by tenant scope before applying time filters | Date interpretation disputed in the old screen |
| 3 | Review result | An empty result must not reveal another tenant exists | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-069 rules and exceptions

- RULE-409: Filter by tenant scope before applying time filters.
- RULE-410: An empty result must not reveal another tenant exists.
- RULE-411: the audit query must carry a synthetic tenant scope before any lookup.
- RULE-412: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-413: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-414: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-069 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-069-A | An in-scope audit query at the starting state | The normal review is accepted | Record requested → executed with a revision reference |
| F-069-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-069-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-069-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a audit query updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-069 archived workshop addendum

Workshop date 2024-06-09. Former migration team requested a second confirmation screen after a failed retry. No mock-up was retained.
The audit query preview was described as disposable. A separate note says previews must be retained when they influenced a reviewed decision. Neither note defines “influenced”.

| Revision fragment | Comment | Disposition |
| --- | --- | --- |
| rev-a / 2025-10-16 | Use the latest available configuration when opening the screen | Possibly obsolete |
| rev-b / 2019-11-17 | Keep the configuration revision used by the originating batch | Unreviewed replacement proposal |

Recovery narrative: the first write succeeds and the acknowledgement is lost. A retry must inspect the stored logical key before creating another work item. The operator cannot decide from the red banner alone.
Partial completion narrative: the queue task exists, the audit append is pending, and the old export calls the item “complete”. Reporting must expose the mismatch, but the display wording is blank.

### F-069 dependencies and unanswered questions

Related workflow: [Audit export approval](functional-specification.md#feature-f-070-audit-export-approval).
Technical operation: [INT-069](integration-data-and-compliance.md#int-069).
Register context: [Audit catalogue](product-and-feature-register.md#audit-catalogue).

- Which team can reopen the audit query after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1369: recover the missing example; owner Platform support.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-070-audit-export-approval"></a>

## Feature F-070 — Audit export approval

Former page: CONF-SYNTH-370. Owner: Reporting stream. Last edited: 2022-02-20.
Tracking: BENEFITS-211. Status: Draft with missing acceptance.

The audit export request is described here using the audit vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **requested → approved**. Bind approval to the selected fields and time interval.
As an operations role, I want to review the audit export request in the selected employer scope so that the next queue can identify the accepted revision.

### F-070 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped audit export request reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Bind approval to the selected fields and time interval | Date interpretation disputed in the old screen |
| 3 | Review result | Changing the interval invalidates export approval | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-070 rules and exceptions

- RULE-415: Bind approval to the selected fields and time interval.
- RULE-416: Changing the interval invalidates export approval.
- RULE-417: the audit export request must carry a synthetic tenant scope before any lookup.
- RULE-418: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-419: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-420: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-070 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-070-A | An in-scope audit export request at the starting state | The normal review is accepted | Record requested → approved with a revision reference |
| F-070-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-070-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-070-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a audit export request updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-070 dependencies and unanswered questions

Related workflow: [Historical correction trace](functional-specification.md#feature-f-071-historical-correction-trace).
Technical operation: [INT-070](integration-data-and-compliance.md#int-070).
Register context: [Audit catalogue](product-and-feature-register.md#audit-catalogue).

- Which team can reopen the audit export request after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1370: recover the missing example; owner Reporting stream.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-071-historical-correction-trace"></a>

## Feature F-071 — Historical correction trace

Former page: CONF-SYNTH-371. Owner: Former migration team. Last edited: 2023-03-21.
Tracking: BENEFITS-212. Status: Assumed in release; evidence absent.

The correction chain is described here using the audit vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **fragmented → linked**. Link each adjustment to its immediate predecessor.
As an operations role, I want to review the correction chain in the selected employer scope so that the next queue can identify the accepted revision.

### F-071 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped correction chain reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Link each adjustment to its immediate predecessor | Date interpretation disputed in the old screen |
| 3 | Review result | Cycles require manual investigation | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-071 rules and exceptions

- RULE-421: Link each adjustment to its immediate predecessor.
- RULE-422: Cycles require manual investigation.
- RULE-423: the correction chain must carry a synthetic tenant scope before any lookup.
- RULE-424: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-425: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-426: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-071 acceptance fragments

| Scenario | Given | When | Expected draft observation |
| --- | --- | --- | --- |
| F-071-A | An in-scope correction chain at the starting state | The normal review is accepted | Record fragmented → linked with a revision reference |
| F-071-B | Two submissions with the same logical key | The second copy arrives late | Return the prior result or an explicit pending state; no second business action |
| F-071-C | The referenced period was closed after preview | The operator confirms the old preview | Recheck period state; the legacy screen may instead create a manual task |
| F-071-D | The record belongs to another synthetic employer | A saved URL is reused | Deny the lookup before returning record details |

Edge case: a correction chain updated just before the batch cut-off may be visible in a report but absent from the next work queue. No ordering contract was agreed.
Edge case: an empty attachment list means “not supplied” in the UI and “clear existing attachments” in an old import note. Preserve this ambiguity for migration review.

### F-071 dependencies and unanswered questions

Related workflow: [Archive replay review](functional-specification.md#feature-f-072-archive-replay-review).
Technical operation: [INT-071](integration-data-and-compliance.md#int-071).
Register context: [Audit catalogue](product-and-feature-register.md#audit-catalogue).

- Which team can reopen the correction chain after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1371: recover the missing example; owner Former migration team.

Possibly obsolete: the old “green means finished” acceptance note predates retry visibility.


<a id="feature-f-072-archive-replay-review"></a>

## Feature F-072 — Archive replay review

Former page: CONF-SYNTH-372. Owner: Operations team. Last edited: 2024-04-22.
Tracking: BENEFITS-213. Status: Copied forward without review.

The replay manifest is described here using the audit vocabulary. The older benefit desk may show a different name for the same queue entry.
Intended transition: **prepared → reviewed**. Replay into an isolated synthetic namespace only.
As an operations role, I want to review the replay manifest in the selected employer scope so that the next queue can identify the accepted revision.

### F-072 workflow fragments

| Step | Input or trigger | Draft behaviour | Unresolved output |
| --- | --- | --- | --- |
| 1 | Scoped replay manifest reference | Load the selected revision, not a guessed latest record | Missing scope routes to review |
| 2 | Requested effective date | Replay into an isolated synthetic namespace only | Date interpretation disputed in the old screen |
| 3 | Review result | Never replay an outbound delivery as a live delivery | Queue owner may be TBD |
| 4 | Save or batch commit | Append the decision and keep the previous revision reference | Return status naming not agreed |

### F-072 rules and exceptions

- RULE-427: Replay into an isolated synthetic namespace only.
- RULE-428: Never replay an outbound delivery as a live delivery.
- RULE-429: the replay manifest must carry a synthetic tenant scope before any lookup.
- RULE-430: an exact replay uses the original logical request key; changed content under that key goes to a discrepancy queue.
- RULE-431: preserve the input revision when the downstream task fails; whether the screen may show success is unresolved.
- RULE-432: an operator may request a rollback, but the old note does not define whether rollback means cancellation or a compensating entry.

### F-072 archived workshop addendum

Workshop date 2020-09-12. TBD requested a second confirmation screen after a failed retry. No mock-up was retained.
The replay manifest preview was described as disposable. A separate note says previews must be retained when they influenced a reviewed decision. Neither note defines “influenced”.

| Revision fragment | Comment | Disposition |
| --- | --- | --- |
| rev-a / 2021-01-19 | Use the latest available configuration when opening the screen | Possibly obsolete |
| rev-b / 2022-02-20 | Keep the configuration revision used by the originating batch | Unreviewed replacement proposal |

Recovery narrative: the first write succeeds and the acknowledgement is lost. A retry must inspect the stored logical key before creating another work item. The operator cannot decide from the red banner alone.
Partial completion narrative: the queue task exists, the audit append is pending, and the old export calls the item “complete”. Reporting must expose the mismatch, but the display wording is blank.

### F-072 dependencies and unanswered questions

Related workflow: [Policy creation](functional-specification.md#feature-f-001-policy-creation).
Technical operation: [INT-072](integration-data-and-compliance.md#int-072).
Register context: [Audit catalogue](product-and-feature-register.md#audit-catalogue).

- Which team can reopen the replay manifest after the queue has been archived?
- Does a missing value inherit the previous revision or explicitly remove it?
- Is the apparent completion date the business date, processing date, or reviewer date?
- BENEFITS-1372: recover the missing example; owner Operations team.

Short-form page: remaining scenarios were never written. The register overstates the completeness of this feature.

