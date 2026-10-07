> Synthetic legacy documentation — test data only.
> Not legal, customer, regulatory, or production guidance.

# Northstar Benefits Platform — integration, data and compliance fragments

CONF-SYNTH-003. Composite technical notebook; extracts dated 2019–2025 were never fully reconciled.
All schemas, field names, identifiers, endpoints, error semantics, report names, and schedules below are invented fixture contracts. No endpoint is deployed.
No credentials, personal identities, bank accounts, real policy identifiers, or external destinations are included. Example tokens such as SYNTH-EMPTY are inert sentinel strings.

## Entity index

- [policy](#entity-policy)
- [contract](#entity-contract)
- [employer](#entity-employer)
- [member](#entity-member)
- [contribution](#entity-contribution)
- [beneficiary](#entity-beneficiary)
- [claim](#entity-claim)
- [payment](#entity-payment)
- [document](#entity-document)
- [audit event](#entity-audit-event)
- [report](#entity-report)
- [integration envelope](#entity-integration-envelope)

## Storage conventions still under discussion

Dates are text in the staging tables and calendar dates in the proposed canonical model. Time zone ownership is not settled.
Amounts are synthetic decimal values. Scale decisions in the functional pages intentionally disagree.
Null, omitted, and empty string remain distinct in the canonical proposal; old CSV import logic sometimes merges them.
No national identifier format is modeled. Member identifiers are opaque fixture keys with no real-world identity semantics.

## Entity policy

DATASET-001. Owner: Operations team. Last mapping discussion: 2023-05-05.
The policy record is a fictional persistence boundary. Its older export counterpart is called contract. The rename was not propagated to reports.
Primary workflow context: [Policy creation](functional-specification.md#feature-f-001-policy-creation). Relationships are represented by opaque synthetic keys; referential enforcement on legacy staging rows is TBD.
Possibly obsolete: the migration sheet describes policy as mutable in place. The feature pages usually assume revisions.
Canonical proposal: one tenant scope and one fixture key identify a revision chain, but exported snapshots may repeat the key.

| Data ID | Field | Draft type | Presence | Meaning or mapping note | Source quality |
| --- | --- | --- | --- | --- | --- |
| DATA-001 | fixture_key | opaque text | Required | Synthetic record reference; never a policy number or real identity | Possibly obsolete |
| DATA-002 | tenant_scope | opaque text | Required | Partition boundary used before any business lookup | Duplicate alias |
| DATA-003 | revision_no | integer | Required | Monotonic within this fixture object, not across entities | Unreviewed |
| DATA-004 | state_code | enum text | Required | Draft state vocabulary depends on the owning feature | Draft |
| DATA-005 | effective_on | date text | Conditional | Business effective date; missing date interpretation unresolved | Possibly obsolete |
| DATA-006 | recorded_at | timestamp text | Required | Processing timestamp; source zone missing in old import | Duplicate alias |
| DATA-007 | source_ref | opaque text | Optional | Reference to the internal staging envelope | Unreviewed |
| DATA-008 | previous_ref | opaque text | Optional | Predecessor revision; must not form a cycle | Draft |
| DATA-009 | owner_queue | enum text | Optional | Queue label rather than a named individual | Possibly obsolete |
| DATA-010 | review_status | enum text | Required | Review completeness is separate from business approval | Duplicate alias |
| DATA-011 | reason_code | enum text | Conditional | Code values differ between the old desk and the new queue | Unreviewed |
| DATA-012 | display_label | text | Optional | Synthetic label; no real person or organisation name | Draft |
| DATA-013 | import_batch_ref | opaque text | Optional | Batch provenance; blank in interactive records | Possibly obsolete |
| DATA-014 | control_total | decimal text | Conditional | Synthetic aggregate; scale must be explicitly supplied | Duplicate alias |
| DATA-015 | is_deleted | boolean text | Optional | Historical soft-delete flag; conflicts with state semantics | Unreviewed |
| DATA-016 | hold_ref | opaque text | Optional | Current hold link; multiple holds were not modeled here | Draft |
| DATA-017 | configuration_ref | opaque text | Required | Versioned rule configuration used at processing time | Possibly obsolete |
| DATA-018 | correlation_ref | opaque text | Required | End-to-end trace marker without identifying content | Duplicate alias |
| DATA-019 | legacy_status | text | Optional | Untranslated historical status retained for reconciliation | Unreviewed |
| DATA-020 | notes_state | enum text | Optional | Indicates notes existence without including free-form personal data | Draft |
| DATA-021 | coverage_start | unresolved scalar | Required | coverage start for the policy; keep source text until reviewed | Possibly obsolete |
| DATA-022 | coverage_end | unresolved scalar | Conditional | coverage end for the policy; reference target not agreed | Duplicate alias |
| DATA-023 | renewal_basis | unresolved scalar | Conditional | renewal basis for the policy; blank differs from omitted | Unreviewed |
| DATA-024 | suspension_start | unresolved scalar | Required | suspension start for the policy; version must match the originating task | Draft |
| DATA-025 | suspension_end | unresolved scalar | Conditional | suspension end for the policy; keep source text until reviewed | Possibly obsolete |
| DATA-026 | cancellation_reason | unresolved scalar | Conditional | cancellation reason for the policy; reference target not agreed | Duplicate alias |
| DATA-027 | branch_label | unresolved scalar | Required | branch label for the policy; blank differs from omitted | Unreviewed |
| DATA-028 | plan_ref | unresolved scalar | Conditional | plan ref for the policy; version must match the originating task | Draft |
| DATA-029 | amendment_ref | unresolved scalar | Conditional | amendment ref for the policy; keep source text until reviewed | Possibly obsolete |
| DATA-030 | coverage_state | unresolved scalar | Required | coverage state for the policy; reference target not agreed | Duplicate alias |
| DATA-031 | proposal_ref | unresolved scalar | Conditional | proposal ref for the policy; blank differs from omitted | Unreviewed |
| DATA-032 | renewal_ref | unresolved scalar | Conditional | renewal ref for the policy; version must match the originating task | Draft |

### policy field mapping residue

| Mapping ID | Source column | Target field | Transform | Rejection or ambiguity |
| --- | --- | --- | --- | --- |
| MAP-001 | old_fixture_key | policy.fixture_key | Preserve source text | Empty input is not defaulted |
| MAP-002 | old_tenant_scope | policy.tenant_scope | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-003 | old_revision_no | policy.revision_no | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-004 | old_state_code | policy.state_code | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-005 | old_effective_on | policy.effective_on | Preserve source text | Empty input is not defaulted |
| MAP-006 | old_recorded_at | policy.recorded_at | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-007 | old_source_ref | policy.source_ref | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-008 | old_previous_ref | policy.previous_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-009 | old_owner_queue | policy.owner_queue | Preserve source text | Empty input is not defaulted |
| MAP-010 | old_review_status | policy.review_status | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-011 | old_reason_code | policy.reason_code | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-012 | old_display_label | policy.display_label | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-013 | old_import_batch_ref | policy.import_batch_ref | Preserve source text | Empty input is not defaulted |
| MAP-014 | old_control_total | policy.control_total | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-015 | old_is_deleted | policy.is_deleted | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-016 | old_hold_ref | policy.hold_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-017 | old_configuration_ref | policy.configuration_ref | Preserve source text | Empty input is not defaulted |
| MAP-018 | old_correlation_ref | policy.correlation_ref | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-019 | old_legacy_status | policy.legacy_status | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-020 | old_notes_state | policy.notes_state | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-021 | old_coverage_start | policy.coverage_start | Preserve source text | Empty input is not defaulted |
| MAP-022 | old_coverage_end | policy.coverage_end | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-023 | old_renewal_basis | policy.renewal_basis | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-024 | old_suspension_start | policy.suspension_start | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-025 | old_suspension_end | policy.suspension_end | Preserve source text | Empty input is not defaulted |
| MAP-026 | old_cancellation_reason | policy.cancellation_reason | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-027 | old_branch_label | policy.branch_label | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-028 | old_plan_ref | policy.plan_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-029 | old_amendment_ref | policy.amendment_ref | Preserve source text | Empty input is not defaulted |
| MAP-030 | old_coverage_state | policy.coverage_state | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-031 | old_proposal_ref | policy.proposal_ref | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-032 | old_renewal_ref | policy.renewal_ref | Pass through when explicitly present | Case sensitivity remains unresolved |

Relationship fragment: the policy export includes a parent reference, but the parent may belong to a different historical revision. Reject cross-tenant references; do not silently adopt the parent scope.
Deletion fragment: an inactive policy may still be needed for replay comparison. Retention periods are invented scenario parameters, not legal schedules.

> Compliance note: requires Belgian-market and legal validation.


## Entity contract

DATASET-002. Owner: Benefits stream. Last mapping discussion: 2024-06-06.
The contract record is a fictional persistence boundary. Its older export counterpart is called contract master. The rename was not propagated to reports.
Primary workflow context: [Employer shell creation](functional-specification.md#feature-f-007-employer-shell-creation). Relationships are represented by opaque synthetic keys; referential enforcement on legacy staging rows is TBD.
Possibly obsolete: the migration sheet describes contract as mutable in place. The feature pages usually assume revisions.
Canonical proposal: one tenant scope and one fixture key identify a revision chain, but exported snapshots may repeat the key.

| Data ID | Field | Draft type | Presence | Meaning or mapping note | Source quality |
| --- | --- | --- | --- | --- | --- |
| DATA-033 | fixture_key | opaque text | Required | Synthetic record reference; never a policy number or real identity | Possibly obsolete |
| DATA-034 | tenant_scope | opaque text | Required | Partition boundary used before any business lookup | Duplicate alias |
| DATA-035 | revision_no | integer | Required | Monotonic within this fixture object, not across entities | Unreviewed |
| DATA-036 | state_code | enum text | Required | Draft state vocabulary depends on the owning feature | Draft |
| DATA-037 | effective_on | date text | Conditional | Business effective date; missing date interpretation unresolved | Possibly obsolete |
| DATA-038 | recorded_at | timestamp text | Required | Processing timestamp; source zone missing in old import | Duplicate alias |
| DATA-039 | source_ref | opaque text | Optional | Reference to the internal staging envelope | Unreviewed |
| DATA-040 | previous_ref | opaque text | Optional | Predecessor revision; must not form a cycle | Draft |
| DATA-041 | owner_queue | enum text | Optional | Queue label rather than a named individual | Possibly obsolete |
| DATA-042 | review_status | enum text | Required | Review completeness is separate from business approval | Duplicate alias |
| DATA-043 | reason_code | enum text | Conditional | Code values differ between the old desk and the new queue | Unreviewed |
| DATA-044 | display_label | text | Optional | Synthetic label; no real person or organisation name | Draft |
| DATA-045 | import_batch_ref | opaque text | Optional | Batch provenance; blank in interactive records | Possibly obsolete |
| DATA-046 | control_total | decimal text | Conditional | Synthetic aggregate; scale must be explicitly supplied | Duplicate alias |
| DATA-047 | is_deleted | boolean text | Optional | Historical soft-delete flag; conflicts with state semantics | Unreviewed |
| DATA-048 | hold_ref | opaque text | Optional | Current hold link; multiple holds were not modeled here | Draft |
| DATA-049 | configuration_ref | opaque text | Required | Versioned rule configuration used at processing time | Possibly obsolete |
| DATA-050 | correlation_ref | opaque text | Required | End-to-end trace marker without identifying content | Duplicate alias |
| DATA-051 | legacy_status | text | Optional | Untranslated historical status retained for reconciliation | Unreviewed |
| DATA-052 | notes_state | enum text | Optional | Indicates notes existence without including free-form personal data | Draft |
| DATA-053 | policy_ref | unresolved scalar | Required | policy ref for the contract; keep source text until reviewed | Possibly obsolete |
| DATA-054 | employer_ref | unresolved scalar | Conditional | employer ref for the contract; reference target not agreed | Duplicate alias |
| DATA-055 | agreement_state | unresolved scalar | Conditional | agreement state for the contract; blank differs from omitted | Unreviewed |
| DATA-056 | signature_placeholder | unresolved scalar | Required | signature placeholder for the contract; version must match the originating task | Draft |
| DATA-057 | schedule_ref | unresolved scalar | Conditional | schedule ref for the contract; keep source text until reviewed | Possibly obsolete |
| DATA-058 | billing_scope | unresolved scalar | Conditional | billing scope for the contract; reference target not agreed | Duplicate alias |
| DATA-059 | contract_start | unresolved scalar | Required | contract start for the contract; blank differs from omitted | Unreviewed |
| DATA-060 | contract_end | unresolved scalar | Conditional | contract end for the contract; version must match the originating task | Draft |
| DATA-061 | amendment_count | integer | Conditional | amendment count for the contract; keep source text until reviewed | Possibly obsolete |
| DATA-062 | governing_text_ref | unresolved scalar | Required | governing text ref for the contract; reference target not agreed | Duplicate alias |
| DATA-063 | plan_ref | unresolved scalar | Conditional | plan ref for the contract; blank differs from omitted | Unreviewed |
| DATA-064 | closure_reason | unresolved scalar | Conditional | closure reason for the contract; version must match the originating task | Draft |

### contract field mapping residue

| Mapping ID | Source column | Target field | Transform | Rejection or ambiguity |
| --- | --- | --- | --- | --- |
| MAP-033 | old_fixture_key | contract.fixture_key | Preserve source text | Empty input is not defaulted |
| MAP-034 | old_tenant_scope | contract.tenant_scope | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-035 | old_revision_no | contract.revision_no | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-036 | old_state_code | contract.state_code | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-037 | old_effective_on | contract.effective_on | Preserve source text | Empty input is not defaulted |
| MAP-038 | old_recorded_at | contract.recorded_at | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-039 | old_source_ref | contract.source_ref | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-040 | old_previous_ref | contract.previous_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-041 | old_owner_queue | contract.owner_queue | Preserve source text | Empty input is not defaulted |
| MAP-042 | old_review_status | contract.review_status | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-043 | old_reason_code | contract.reason_code | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-044 | old_display_label | contract.display_label | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-045 | old_import_batch_ref | contract.import_batch_ref | Preserve source text | Empty input is not defaulted |
| MAP-046 | old_control_total | contract.control_total | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-047 | old_is_deleted | contract.is_deleted | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-048 | old_hold_ref | contract.hold_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-049 | old_configuration_ref | contract.configuration_ref | Preserve source text | Empty input is not defaulted |
| MAP-050 | old_correlation_ref | contract.correlation_ref | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-051 | old_legacy_status | contract.legacy_status | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-052 | old_notes_state | contract.notes_state | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-053 | old_policy_ref | contract.policy_ref | Preserve source text | Empty input is not defaulted |
| MAP-054 | old_employer_ref | contract.employer_ref | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-055 | old_agreement_state | contract.agreement_state | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-056 | old_signature_placeholder | contract.signature_placeholder | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-057 | old_schedule_ref | contract.schedule_ref | Preserve source text | Empty input is not defaulted |
| MAP-058 | old_billing_scope | contract.billing_scope | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-059 | old_contract_start | contract.contract_start | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-060 | old_contract_end | contract.contract_end | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-061 | old_amendment_count | contract.amendment_count | Preserve source text | Empty input is not defaulted |
| MAP-062 | old_governing_text_ref | contract.governing_text_ref | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-063 | old_plan_ref | contract.plan_ref | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-064 | old_closure_reason | contract.closure_reason | Pass through when explicitly present | Case sensitivity remains unresolved |

Relationship fragment: the contract export includes a parent reference, but the parent may belong to a different historical revision. Reject cross-tenant references; do not silently adopt the parent scope.
Deletion fragment: an inactive contract may still be needed for replay comparison. Retention periods are invented scenario parameters, not legal schedules.

> Compliance note: requires Belgian-market and legal validation.


## Entity employer

DATASET-003. Owner: TBD. Last mapping discussion: 2025-07-07.
The employer record is a fictional persistence boundary. Its older export counterpart is called employer master. The rename was not propagated to reports.
Primary workflow context: [Employee eligibility assessment](functional-specification.md#feature-f-013-employee-eligibility-assessment). Relationships are represented by opaque synthetic keys; referential enforcement on legacy staging rows is TBD.
Possibly obsolete: the migration sheet describes employer as mutable in place. The feature pages usually assume revisions.
Canonical proposal: one tenant scope and one fixture key identify a revision chain, but exported snapshots may repeat the key.

| Data ID | Field | Draft type | Presence | Meaning or mapping note | Source quality |
| --- | --- | --- | --- | --- | --- |
| DATA-065 | fixture_key | opaque text | Required | Synthetic record reference; never a policy number or real identity | Possibly obsolete |
| DATA-066 | tenant_scope | opaque text | Required | Partition boundary used before any business lookup | Duplicate alias |
| DATA-067 | revision_no | integer | Required | Monotonic within this fixture object, not across entities | Unreviewed |
| DATA-068 | state_code | enum text | Required | Draft state vocabulary depends on the owning feature | Draft |
| DATA-069 | effective_on | date text | Conditional | Business effective date; missing date interpretation unresolved | Possibly obsolete |
| DATA-070 | recorded_at | timestamp text | Required | Processing timestamp; source zone missing in old import | Duplicate alias |
| DATA-071 | source_ref | opaque text | Optional | Reference to the internal staging envelope | Unreviewed |
| DATA-072 | previous_ref | opaque text | Optional | Predecessor revision; must not form a cycle | Draft |
| DATA-073 | owner_queue | enum text | Optional | Queue label rather than a named individual | Possibly obsolete |
| DATA-074 | review_status | enum text | Required | Review completeness is separate from business approval | Duplicate alias |
| DATA-075 | reason_code | enum text | Conditional | Code values differ between the old desk and the new queue | Unreviewed |
| DATA-076 | display_label | text | Optional | Synthetic label; no real person or organisation name | Draft |
| DATA-077 | import_batch_ref | opaque text | Optional | Batch provenance; blank in interactive records | Possibly obsolete |
| DATA-078 | control_total | decimal text | Conditional | Synthetic aggregate; scale must be explicitly supplied | Duplicate alias |
| DATA-079 | is_deleted | boolean text | Optional | Historical soft-delete flag; conflicts with state semantics | Unreviewed |
| DATA-080 | hold_ref | opaque text | Optional | Current hold link; multiple holds were not modeled here | Draft |
| DATA-081 | configuration_ref | opaque text | Required | Versioned rule configuration used at processing time | Possibly obsolete |
| DATA-082 | correlation_ref | opaque text | Required | End-to-end trace marker without identifying content | Duplicate alias |
| DATA-083 | legacy_status | text | Optional | Untranslated historical status retained for reconciliation | Unreviewed |
| DATA-084 | notes_state | enum text | Optional | Indicates notes existence without including free-form personal data | Draft |
| DATA-085 | parent_ref | unresolved scalar | Required | parent ref for the employer; keep source text until reviewed | Possibly obsolete |
| DATA-086 | onboarding_state | unresolved scalar | Conditional | onboarding state for the employer; reference target not agreed | Duplicate alias |
| DATA-087 | package_ref | unresolved scalar | Conditional | package ref for the employer; blank differs from omitted | Unreviewed |
| DATA-088 | contact_role_label | unresolved scalar | Required | contact role label for the employer; version must match the originating task | Draft |
| DATA-089 | routing_channel | unresolved scalar | Conditional | routing channel for the employer; keep source text until reviewed | Possibly obsolete |
| DATA-090 | activation_date | unresolved scalar | Conditional | activation date for the employer; reference target not agreed | Duplicate alias |
| DATA-091 | closure_date | unresolved scalar | Required | closure date for the employer; blank differs from omitted | Unreviewed |
| DATA-092 | hierarchy_revision | unresolved scalar | Conditional | hierarchy revision for the employer; version must match the originating task | Draft |
| DATA-093 | intake_packet_ref | unresolved scalar | Conditional | intake packet ref for the employer; keep source text until reviewed | Possibly obsolete |
| DATA-094 | payroll_source_ref | unresolved scalar | Required | payroll source ref for the employer; reference target not agreed | Duplicate alias |
| DATA-095 | billing_group | unresolved scalar | Conditional | billing group for the employer; blank differs from omitted | Unreviewed |
| DATA-096 | offboarding_ref | unresolved scalar | Conditional | offboarding ref for the employer; version must match the originating task | Draft |

### employer field mapping residue

| Mapping ID | Source column | Target field | Transform | Rejection or ambiguity |
| --- | --- | --- | --- | --- |
| MAP-065 | old_fixture_key | employer.fixture_key | Preserve source text | Empty input is not defaulted |
| MAP-066 | old_tenant_scope | employer.tenant_scope | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-067 | old_revision_no | employer.revision_no | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-068 | old_state_code | employer.state_code | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-069 | old_effective_on | employer.effective_on | Preserve source text | Empty input is not defaulted |
| MAP-070 | old_recorded_at | employer.recorded_at | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-071 | old_source_ref | employer.source_ref | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-072 | old_previous_ref | employer.previous_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-073 | old_owner_queue | employer.owner_queue | Preserve source text | Empty input is not defaulted |
| MAP-074 | old_review_status | employer.review_status | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-075 | old_reason_code | employer.reason_code | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-076 | old_display_label | employer.display_label | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-077 | old_import_batch_ref | employer.import_batch_ref | Preserve source text | Empty input is not defaulted |
| MAP-078 | old_control_total | employer.control_total | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-079 | old_is_deleted | employer.is_deleted | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-080 | old_hold_ref | employer.hold_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-081 | old_configuration_ref | employer.configuration_ref | Preserve source text | Empty input is not defaulted |
| MAP-082 | old_correlation_ref | employer.correlation_ref | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-083 | old_legacy_status | employer.legacy_status | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-084 | old_notes_state | employer.notes_state | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-085 | old_parent_ref | employer.parent_ref | Preserve source text | Empty input is not defaulted |
| MAP-086 | old_onboarding_state | employer.onboarding_state | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-087 | old_package_ref | employer.package_ref | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-088 | old_contact_role_label | employer.contact_role_label | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-089 | old_routing_channel | employer.routing_channel | Preserve source text | Empty input is not defaulted |
| MAP-090 | old_activation_date | employer.activation_date | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-091 | old_closure_date | employer.closure_date | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-092 | old_hierarchy_revision | employer.hierarchy_revision | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-093 | old_intake_packet_ref | employer.intake_packet_ref | Preserve source text | Empty input is not defaulted |
| MAP-094 | old_payroll_source_ref | employer.payroll_source_ref | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-095 | old_billing_group | employer.billing_group | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-096 | old_offboarding_ref | employer.offboarding_ref | Pass through when explicitly present | Case sensitivity remains unresolved |

Relationship fragment: the employer export includes a parent reference, but the parent may belong to a different historical revision. Reject cross-tenant references; do not silently adopt the parent scope.
Deletion fragment: an inactive employer may still be needed for replay comparison. Retention periods are invented scenario parameters, not legal schedules.

> Compliance note: requires Belgian-market and legal validation.


## Entity member

DATASET-004. Owner: Platform support. Last mapping discussion: 2019-08-08.
The member record is a fictional persistence boundary. Its older export counterpart is called employee. The rename was not propagated to reports.
Primary workflow context: [Contribution calculation](functional-specification.md#feature-f-019-contribution-calculation). Relationships are represented by opaque synthetic keys; referential enforcement on legacy staging rows is TBD.
Possibly obsolete: the migration sheet describes member as mutable in place. The feature pages usually assume revisions.
Canonical proposal: one tenant scope and one fixture key identify a revision chain, but exported snapshots may repeat the key.

| Data ID | Field | Draft type | Presence | Meaning or mapping note | Source quality |
| --- | --- | --- | --- | --- | --- |
| DATA-097 | fixture_key | opaque text | Required | Synthetic record reference; never a policy number or real identity | Possibly obsolete |
| DATA-098 | tenant_scope | opaque text | Required | Partition boundary used before any business lookup | Duplicate alias |
| DATA-099 | revision_no | integer | Required | Monotonic within this fixture object, not across entities | Unreviewed |
| DATA-100 | state_code | enum text | Required | Draft state vocabulary depends on the owning feature | Draft |
| DATA-101 | effective_on | date text | Conditional | Business effective date; missing date interpretation unresolved | Possibly obsolete |
| DATA-102 | recorded_at | timestamp text | Required | Processing timestamp; source zone missing in old import | Duplicate alias |
| DATA-103 | source_ref | opaque text | Optional | Reference to the internal staging envelope | Unreviewed |
| DATA-104 | previous_ref | opaque text | Optional | Predecessor revision; must not form a cycle | Draft |
| DATA-105 | owner_queue | enum text | Optional | Queue label rather than a named individual | Possibly obsolete |
| DATA-106 | review_status | enum text | Required | Review completeness is separate from business approval | Duplicate alias |
| DATA-107 | reason_code | enum text | Conditional | Code values differ between the old desk and the new queue | Unreviewed |
| DATA-108 | display_label | text | Optional | Synthetic label; no real person or organisation name | Draft |
| DATA-109 | import_batch_ref | opaque text | Optional | Batch provenance; blank in interactive records | Possibly obsolete |
| DATA-110 | control_total | decimal text | Conditional | Synthetic aggregate; scale must be explicitly supplied | Duplicate alias |
| DATA-111 | is_deleted | boolean text | Optional | Historical soft-delete flag; conflicts with state semantics | Unreviewed |
| DATA-112 | hold_ref | opaque text | Optional | Current hold link; multiple holds were not modeled here | Draft |
| DATA-113 | configuration_ref | opaque text | Required | Versioned rule configuration used at processing time | Possibly obsolete |
| DATA-114 | correlation_ref | opaque text | Required | End-to-end trace marker without identifying content | Duplicate alias |
| DATA-115 | legacy_status | text | Optional | Untranslated historical status retained for reconciliation | Unreviewed |
| DATA-116 | notes_state | enum text | Optional | Indicates notes existence without including free-form personal data | Draft |
| DATA-117 | employer_ref | unresolved scalar | Required | employer ref for the member; keep source text until reviewed | Possibly obsolete |
| DATA-118 | membership_start | unresolved scalar | Conditional | membership start for the member; reference target not agreed | Duplicate alias |
| DATA-119 | membership_end | unresolved scalar | Conditional | membership end for the member; blank differs from omitted | Unreviewed |
| DATA-120 | category_code | unresolved scalar | Required | category code for the member; version must match the originating task | Draft |
| DATA-121 | eligibility_state | unresolved scalar | Conditional | eligibility state for the member; keep source text until reviewed | Possibly obsolete |
| DATA-122 | waiting_start | unresolved scalar | Conditional | waiting start for the member; reference target not agreed | Duplicate alias |
| DATA-123 | waiting_end | unresolved scalar | Required | waiting end for the member; blank differs from omitted | Unreviewed |
| DATA-124 | absence_ref | unresolved scalar | Conditional | absence ref for the member; version must match the originating task | Draft |
| DATA-125 | exit_ref | unresolved scalar | Conditional | exit ref for the member; keep source text until reviewed | Possibly obsolete |
| DATA-126 | reentry_ref | unresolved scalar | Required | reentry ref for the member; reference target not agreed | Duplicate alias |
| DATA-127 | language_code | unresolved scalar | Conditional | language code for the member; blank differs from omitted | Unreviewed |
| DATA-128 | coverage_ref | unresolved scalar | Conditional | coverage ref for the member; version must match the originating task | Draft |

### member field mapping residue

| Mapping ID | Source column | Target field | Transform | Rejection or ambiguity |
| --- | --- | --- | --- | --- |
| MAP-097 | old_fixture_key | member.fixture_key | Preserve source text | Empty input is not defaulted |
| MAP-098 | old_tenant_scope | member.tenant_scope | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-099 | old_revision_no | member.revision_no | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-100 | old_state_code | member.state_code | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-101 | old_effective_on | member.effective_on | Preserve source text | Empty input is not defaulted |
| MAP-102 | old_recorded_at | member.recorded_at | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-103 | old_source_ref | member.source_ref | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-104 | old_previous_ref | member.previous_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-105 | old_owner_queue | member.owner_queue | Preserve source text | Empty input is not defaulted |
| MAP-106 | old_review_status | member.review_status | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-107 | old_reason_code | member.reason_code | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-108 | old_display_label | member.display_label | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-109 | old_import_batch_ref | member.import_batch_ref | Preserve source text | Empty input is not defaulted |
| MAP-110 | old_control_total | member.control_total | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-111 | old_is_deleted | member.is_deleted | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-112 | old_hold_ref | member.hold_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-113 | old_configuration_ref | member.configuration_ref | Preserve source text | Empty input is not defaulted |
| MAP-114 | old_correlation_ref | member.correlation_ref | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-115 | old_legacy_status | member.legacy_status | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-116 | old_notes_state | member.notes_state | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-117 | old_employer_ref | member.employer_ref | Preserve source text | Empty input is not defaulted |
| MAP-118 | old_membership_start | member.membership_start | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-119 | old_membership_end | member.membership_end | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-120 | old_category_code | member.category_code | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-121 | old_eligibility_state | member.eligibility_state | Preserve source text | Empty input is not defaulted |
| MAP-122 | old_waiting_start | member.waiting_start | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-123 | old_waiting_end | member.waiting_end | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-124 | old_absence_ref | member.absence_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-125 | old_exit_ref | member.exit_ref | Preserve source text | Empty input is not defaulted |
| MAP-126 | old_reentry_ref | member.reentry_ref | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-127 | old_language_code | member.language_code | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-128 | old_coverage_ref | member.coverage_ref | Pass through when explicitly present | Case sensitivity remains unresolved |

Relationship fragment: the member export includes a parent reference, but the parent may belong to a different historical revision. Reject cross-tenant references; do not silently adopt the parent scope.
Deletion fragment: an inactive member may still be needed for replay comparison. Retention periods are invented scenario parameters, not legal schedules.

> Compliance note: requires Belgian-market and legal validation.


## Entity contribution

DATASET-005. Owner: Reporting stream. Last mapping discussion: 2020-09-09.
The contribution record is a fictional persistence boundary. Its older export counterpart is called contribution master. The rename was not propagated to reports.
Primary workflow context: [Beneficiary designation](functional-specification.md#feature-f-025-beneficiary-designation). Relationships are represented by opaque synthetic keys; referential enforcement on legacy staging rows is TBD.
Possibly obsolete: the migration sheet describes contribution as mutable in place. The feature pages usually assume revisions.
Canonical proposal: one tenant scope and one fixture key identify a revision chain, but exported snapshots may repeat the key.

| Data ID | Field | Draft type | Presence | Meaning or mapping note | Source quality |
| --- | --- | --- | --- | --- | --- |
| DATA-129 | fixture_key | opaque text | Required | Synthetic record reference; never a policy number or real identity | Possibly obsolete |
| DATA-130 | tenant_scope | opaque text | Required | Partition boundary used before any business lookup | Duplicate alias |
| DATA-131 | revision_no | integer | Required | Monotonic within this fixture object, not across entities | Unreviewed |
| DATA-132 | state_code | enum text | Required | Draft state vocabulary depends on the owning feature | Draft |
| DATA-133 | effective_on | date text | Conditional | Business effective date; missing date interpretation unresolved | Possibly obsolete |
| DATA-134 | recorded_at | timestamp text | Required | Processing timestamp; source zone missing in old import | Duplicate alias |
| DATA-135 | source_ref | opaque text | Optional | Reference to the internal staging envelope | Unreviewed |
| DATA-136 | previous_ref | opaque text | Optional | Predecessor revision; must not form a cycle | Draft |
| DATA-137 | owner_queue | enum text | Optional | Queue label rather than a named individual | Possibly obsolete |
| DATA-138 | review_status | enum text | Required | Review completeness is separate from business approval | Duplicate alias |
| DATA-139 | reason_code | enum text | Conditional | Code values differ between the old desk and the new queue | Unreviewed |
| DATA-140 | display_label | text | Optional | Synthetic label; no real person or organisation name | Draft |
| DATA-141 | import_batch_ref | opaque text | Optional | Batch provenance; blank in interactive records | Possibly obsolete |
| DATA-142 | control_total | decimal text | Conditional | Synthetic aggregate; scale must be explicitly supplied | Duplicate alias |
| DATA-143 | is_deleted | boolean text | Optional | Historical soft-delete flag; conflicts with state semantics | Unreviewed |
| DATA-144 | hold_ref | opaque text | Optional | Current hold link; multiple holds were not modeled here | Draft |
| DATA-145 | configuration_ref | opaque text | Required | Versioned rule configuration used at processing time | Possibly obsolete |
| DATA-146 | correlation_ref | opaque text | Required | End-to-end trace marker without identifying content | Duplicate alias |
| DATA-147 | legacy_status | text | Optional | Untranslated historical status retained for reconciliation | Unreviewed |
| DATA-148 | notes_state | enum text | Optional | Indicates notes existence without including free-form personal data | Draft |
| DATA-149 | member_ref | unresolved scalar | Required | member ref for the contribution; keep source text until reviewed | Possibly obsolete |
| DATA-150 | period_start | unresolved scalar | Conditional | period start for the contribution; reference target not agreed | Duplicate alias |
| DATA-151 | period_end | unresolved scalar | Conditional | period end for the contribution; blank differs from omitted | Unreviewed |
| DATA-152 | basis_amount | decimal text | Required | basis amount for the contribution; version must match the originating task | Draft |
| DATA-153 | rate_ref | unresolved scalar | Conditional | rate ref for the contribution; keep source text until reviewed | Possibly obsolete |
| DATA-154 | component_amount | decimal text | Conditional | component amount for the contribution; reference target not agreed | Duplicate alias |
| DATA-155 | rounded_amount | decimal text | Required | rounded amount for the contribution; blank differs from omitted | Unreviewed |
| DATA-156 | allocation_ref | unresolved scalar | Conditional | allocation ref for the contribution; version must match the originating task | Draft |
| DATA-157 | correction_of | unresolved scalar | Conditional | correction of for the contribution; keep source text until reviewed | Possibly obsolete |
| DATA-158 | arrears_state | unresolved scalar | Required | arrears state for the contribution; reference target not agreed | Duplicate alias |
| DATA-159 | credit_amount | decimal text | Conditional | credit amount for the contribution; blank differs from omitted | Unreviewed |
| DATA-160 | refund_ref | unresolved scalar | Conditional | refund ref for the contribution; version must match the originating task | Draft |

### contribution field mapping residue

| Mapping ID | Source column | Target field | Transform | Rejection or ambiguity |
| --- | --- | --- | --- | --- |
| MAP-129 | old_fixture_key | contribution.fixture_key | Preserve source text | Empty input is not defaulted |
| MAP-130 | old_tenant_scope | contribution.tenant_scope | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-131 | old_revision_no | contribution.revision_no | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-132 | old_state_code | contribution.state_code | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-133 | old_effective_on | contribution.effective_on | Preserve source text | Empty input is not defaulted |
| MAP-134 | old_recorded_at | contribution.recorded_at | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-135 | old_source_ref | contribution.source_ref | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-136 | old_previous_ref | contribution.previous_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-137 | old_owner_queue | contribution.owner_queue | Preserve source text | Empty input is not defaulted |
| MAP-138 | old_review_status | contribution.review_status | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-139 | old_reason_code | contribution.reason_code | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-140 | old_display_label | contribution.display_label | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-141 | old_import_batch_ref | contribution.import_batch_ref | Preserve source text | Empty input is not defaulted |
| MAP-142 | old_control_total | contribution.control_total | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-143 | old_is_deleted | contribution.is_deleted | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-144 | old_hold_ref | contribution.hold_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-145 | old_configuration_ref | contribution.configuration_ref | Preserve source text | Empty input is not defaulted |
| MAP-146 | old_correlation_ref | contribution.correlation_ref | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-147 | old_legacy_status | contribution.legacy_status | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-148 | old_notes_state | contribution.notes_state | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-149 | old_member_ref | contribution.member_ref | Preserve source text | Empty input is not defaulted |
| MAP-150 | old_period_start | contribution.period_start | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-151 | old_period_end | contribution.period_end | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-152 | old_basis_amount | contribution.basis_amount | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-153 | old_rate_ref | contribution.rate_ref | Preserve source text | Empty input is not defaulted |
| MAP-154 | old_component_amount | contribution.component_amount | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-155 | old_rounded_amount | contribution.rounded_amount | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-156 | old_allocation_ref | contribution.allocation_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-157 | old_correction_of | contribution.correction_of | Preserve source text | Empty input is not defaulted |
| MAP-158 | old_arrears_state | contribution.arrears_state | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-159 | old_credit_amount | contribution.credit_amount | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-160 | old_refund_ref | contribution.refund_ref | Pass through when explicitly present | Case sensitivity remains unresolved |

Relationship fragment: the contribution export includes a parent reference, but the parent may belong to a different historical revision. Reject cross-tenant references; do not silently adopt the parent scope.
Deletion fragment: an inactive contribution may still be needed for replay comparison. Retention periods are invented scenario parameters, not legal schedules.

> Compliance note: requires Belgian-market and legal validation.


## Entity beneficiary

DATASET-006. Owner: Former migration team. Last mapping discussion: 2021-10-10.
The beneficiary record is a fictional persistence boundary. Its older export counterpart is called beneficiary master. The rename was not propagated to reports.
Primary workflow context: [Claim intake](functional-specification.md#feature-f-031-claim-intake). Relationships are represented by opaque synthetic keys; referential enforcement on legacy staging rows is TBD.
Possibly obsolete: the migration sheet describes beneficiary as mutable in place. The feature pages usually assume revisions.
Canonical proposal: one tenant scope and one fixture key identify a revision chain, but exported snapshots may repeat the key.

| Data ID | Field | Draft type | Presence | Meaning or mapping note | Source quality |
| --- | --- | --- | --- | --- | --- |
| DATA-161 | fixture_key | opaque text | Required | Synthetic record reference; never a policy number or real identity | Possibly obsolete |
| DATA-162 | tenant_scope | opaque text | Required | Partition boundary used before any business lookup | Duplicate alias |
| DATA-163 | revision_no | integer | Required | Monotonic within this fixture object, not across entities | Unreviewed |
| DATA-164 | state_code | enum text | Required | Draft state vocabulary depends on the owning feature | Draft |
| DATA-165 | effective_on | date text | Conditional | Business effective date; missing date interpretation unresolved | Possibly obsolete |
| DATA-166 | recorded_at | timestamp text | Required | Processing timestamp; source zone missing in old import | Duplicate alias |
| DATA-167 | source_ref | opaque text | Optional | Reference to the internal staging envelope | Unreviewed |
| DATA-168 | previous_ref | opaque text | Optional | Predecessor revision; must not form a cycle | Draft |
| DATA-169 | owner_queue | enum text | Optional | Queue label rather than a named individual | Possibly obsolete |
| DATA-170 | review_status | enum text | Required | Review completeness is separate from business approval | Duplicate alias |
| DATA-171 | reason_code | enum text | Conditional | Code values differ between the old desk and the new queue | Unreviewed |
| DATA-172 | display_label | text | Optional | Synthetic label; no real person or organisation name | Draft |
| DATA-173 | import_batch_ref | opaque text | Optional | Batch provenance; blank in interactive records | Possibly obsolete |
| DATA-174 | control_total | decimal text | Conditional | Synthetic aggregate; scale must be explicitly supplied | Duplicate alias |
| DATA-175 | is_deleted | boolean text | Optional | Historical soft-delete flag; conflicts with state semantics | Unreviewed |
| DATA-176 | hold_ref | opaque text | Optional | Current hold link; multiple holds were not modeled here | Draft |
| DATA-177 | configuration_ref | opaque text | Required | Versioned rule configuration used at processing time | Possibly obsolete |
| DATA-178 | correlation_ref | opaque text | Required | End-to-end trace marker without identifying content | Duplicate alias |
| DATA-179 | legacy_status | text | Optional | Untranslated historical status retained for reconciliation | Unreviewed |
| DATA-180 | notes_state | enum text | Optional | Indicates notes existence without including free-form personal data | Draft |
| DATA-181 | designation_ref | unresolved scalar | Required | designation ref for the beneficiary; keep source text until reviewed | Possibly obsolete |
| DATA-182 | member_ref | unresolved scalar | Conditional | member ref for the beneficiary; reference target not agreed | Duplicate alias |
| DATA-183 | recipient_fixture_ref | unresolved scalar | Conditional | recipient fixture ref for the beneficiary; blank differs from omitted | Unreviewed |
| DATA-184 | share_percent | decimal text | Required | share percent for the beneficiary; version must match the originating task | Draft |
| DATA-185 | priority_rank | integer | Conditional | priority rank for the beneficiary; keep source text until reviewed | Possibly obsolete |
| DATA-186 | verification_state | unresolved scalar | Conditional | verification state for the beneficiary; reference target not agreed | Duplicate alias |
| DATA-187 | confirmed_on | unresolved scalar | Required | confirmed on for the beneficiary; blank differs from omitted | Unreviewed |
| DATA-188 | replaced_on | unresolved scalar | Conditional | replaced on for the beneficiary; version must match the originating task | Draft |
| DATA-189 | evidence_ref | unresolved scalar | Conditional | evidence ref for the beneficiary; keep source text until reviewed | Possibly obsolete |
| DATA-190 | event_snapshot_ref | unresolved scalar | Required | event snapshot ref for the beneficiary; reference target not agreed | Duplicate alias |
| DATA-191 | relationship_label | unresolved scalar | Conditional | relationship label for the beneficiary; blank differs from omitted | Unreviewed |
| DATA-192 | allocation_state | unresolved scalar | Conditional | allocation state for the beneficiary; version must match the originating task | Draft |

### beneficiary field mapping residue

| Mapping ID | Source column | Target field | Transform | Rejection or ambiguity |
| --- | --- | --- | --- | --- |
| MAP-161 | old_fixture_key | beneficiary.fixture_key | Preserve source text | Empty input is not defaulted |
| MAP-162 | old_tenant_scope | beneficiary.tenant_scope | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-163 | old_revision_no | beneficiary.revision_no | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-164 | old_state_code | beneficiary.state_code | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-165 | old_effective_on | beneficiary.effective_on | Preserve source text | Empty input is not defaulted |
| MAP-166 | old_recorded_at | beneficiary.recorded_at | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-167 | old_source_ref | beneficiary.source_ref | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-168 | old_previous_ref | beneficiary.previous_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-169 | old_owner_queue | beneficiary.owner_queue | Preserve source text | Empty input is not defaulted |
| MAP-170 | old_review_status | beneficiary.review_status | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-171 | old_reason_code | beneficiary.reason_code | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-172 | old_display_label | beneficiary.display_label | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-173 | old_import_batch_ref | beneficiary.import_batch_ref | Preserve source text | Empty input is not defaulted |
| MAP-174 | old_control_total | beneficiary.control_total | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-175 | old_is_deleted | beneficiary.is_deleted | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-176 | old_hold_ref | beneficiary.hold_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-177 | old_configuration_ref | beneficiary.configuration_ref | Preserve source text | Empty input is not defaulted |
| MAP-178 | old_correlation_ref | beneficiary.correlation_ref | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-179 | old_legacy_status | beneficiary.legacy_status | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-180 | old_notes_state | beneficiary.notes_state | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-181 | old_designation_ref | beneficiary.designation_ref | Preserve source text | Empty input is not defaulted |
| MAP-182 | old_member_ref | beneficiary.member_ref | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-183 | old_recipient_fixture_ref | beneficiary.recipient_fixture_ref | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-184 | old_share_percent | beneficiary.share_percent | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-185 | old_priority_rank | beneficiary.priority_rank | Preserve source text | Empty input is not defaulted |
| MAP-186 | old_verification_state | beneficiary.verification_state | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-187 | old_confirmed_on | beneficiary.confirmed_on | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-188 | old_replaced_on | beneficiary.replaced_on | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-189 | old_evidence_ref | beneficiary.evidence_ref | Preserve source text | Empty input is not defaulted |
| MAP-190 | old_event_snapshot_ref | beneficiary.event_snapshot_ref | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-191 | old_relationship_label | beneficiary.relationship_label | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-192 | old_allocation_state | beneficiary.allocation_state | Pass through when explicitly present | Case sensitivity remains unresolved |

Relationship fragment: the beneficiary export includes a parent reference, but the parent may belong to a different historical revision. Reject cross-tenant references; do not silently adopt the parent scope.
Deletion fragment: an inactive beneficiary may still be needed for replay comparison. Retention periods are invented scenario parameters, not legal schedules.

> Compliance note: requires Belgian-market and legal validation.


## Entity claim

DATASET-007. Owner: Operations team. Last mapping discussion: 2022-11-11.
The claim record is a fictional persistence boundary. Its older export counterpart is called claim master. The rename was not propagated to reports.
Primary workflow context: [Payout authorization](functional-specification.md#feature-f-037-payout-authorization). Relationships are represented by opaque synthetic keys; referential enforcement on legacy staging rows is TBD.
Possibly obsolete: the migration sheet describes claim as mutable in place. The feature pages usually assume revisions.
Canonical proposal: one tenant scope and one fixture key identify a revision chain, but exported snapshots may repeat the key.

| Data ID | Field | Draft type | Presence | Meaning or mapping note | Source quality |
| --- | --- | --- | --- | --- | --- |
| DATA-193 | fixture_key | opaque text | Required | Synthetic record reference; never a policy number or real identity | Possibly obsolete |
| DATA-194 | tenant_scope | opaque text | Required | Partition boundary used before any business lookup | Duplicate alias |
| DATA-195 | revision_no | integer | Required | Monotonic within this fixture object, not across entities | Unreviewed |
| DATA-196 | state_code | enum text | Required | Draft state vocabulary depends on the owning feature | Draft |
| DATA-197 | effective_on | date text | Conditional | Business effective date; missing date interpretation unresolved | Possibly obsolete |
| DATA-198 | recorded_at | timestamp text | Required | Processing timestamp; source zone missing in old import | Duplicate alias |
| DATA-199 | source_ref | opaque text | Optional | Reference to the internal staging envelope | Unreviewed |
| DATA-200 | previous_ref | opaque text | Optional | Predecessor revision; must not form a cycle | Draft |
| DATA-201 | owner_queue | enum text | Optional | Queue label rather than a named individual | Possibly obsolete |
| DATA-202 | review_status | enum text | Required | Review completeness is separate from business approval | Duplicate alias |
| DATA-203 | reason_code | enum text | Conditional | Code values differ between the old desk and the new queue | Unreviewed |
| DATA-204 | display_label | text | Optional | Synthetic label; no real person or organisation name | Draft |
| DATA-205 | import_batch_ref | opaque text | Optional | Batch provenance; blank in interactive records | Possibly obsolete |
| DATA-206 | control_total | decimal text | Conditional | Synthetic aggregate; scale must be explicitly supplied | Duplicate alias |
| DATA-207 | is_deleted | boolean text | Optional | Historical soft-delete flag; conflicts with state semantics | Unreviewed |
| DATA-208 | hold_ref | opaque text | Optional | Current hold link; multiple holds were not modeled here | Draft |
| DATA-209 | configuration_ref | opaque text | Required | Versioned rule configuration used at processing time | Possibly obsolete |
| DATA-210 | correlation_ref | opaque text | Required | End-to-end trace marker without identifying content | Duplicate alias |
| DATA-211 | legacy_status | text | Optional | Untranslated historical status retained for reconciliation | Unreviewed |
| DATA-212 | notes_state | enum text | Optional | Indicates notes existence without including free-form personal data | Draft |
| DATA-213 | member_ref | unresolved scalar | Required | member ref for the claim; keep source text until reviewed | Possibly obsolete |
| DATA-214 | event_ref | unresolved scalar | Conditional | event ref for the claim; reference target not agreed | Duplicate alias |
| DATA-215 | event_type | unresolved scalar | Conditional | event type for the claim; blank differs from omitted | Unreviewed |
| DATA-216 | reported_on | unresolved scalar | Required | reported on for the claim; version must match the originating task | Draft |
| DATA-217 | intake_state | unresolved scalar | Conditional | intake state for the claim; keep source text until reviewed | Possibly obsolete |
| DATA-218 | checklist_ref | unresolved scalar | Conditional | checklist ref for the claim; reference target not agreed | Duplicate alias |
| DATA-219 | assessment_ref | unresolved scalar | Required | assessment ref for the claim; blank differs from omitted | Unreviewed |
| DATA-220 | decision_ref | unresolved scalar | Conditional | decision ref for the claim; version must match the originating task | Draft |
| DATA-221 | quote_amount | decimal text | Conditional | quote amount for the claim; keep source text until reviewed | Possibly obsolete |
| DATA-222 | appeal_ref | unresolved scalar | Required | appeal ref for the claim; reference target not agreed | Duplicate alias |
| DATA-223 | reopened_on | unresolved scalar | Conditional | reopened on for the claim; blank differs from omitted | Unreviewed |
| DATA-224 | entitlement_ref | unresolved scalar | Conditional | entitlement ref for the claim; version must match the originating task | Draft |

### claim field mapping residue

| Mapping ID | Source column | Target field | Transform | Rejection or ambiguity |
| --- | --- | --- | --- | --- |
| MAP-193 | old_fixture_key | claim.fixture_key | Preserve source text | Empty input is not defaulted |
| MAP-194 | old_tenant_scope | claim.tenant_scope | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-195 | old_revision_no | claim.revision_no | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-196 | old_state_code | claim.state_code | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-197 | old_effective_on | claim.effective_on | Preserve source text | Empty input is not defaulted |
| MAP-198 | old_recorded_at | claim.recorded_at | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-199 | old_source_ref | claim.source_ref | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-200 | old_previous_ref | claim.previous_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-201 | old_owner_queue | claim.owner_queue | Preserve source text | Empty input is not defaulted |
| MAP-202 | old_review_status | claim.review_status | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-203 | old_reason_code | claim.reason_code | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-204 | old_display_label | claim.display_label | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-205 | old_import_batch_ref | claim.import_batch_ref | Preserve source text | Empty input is not defaulted |
| MAP-206 | old_control_total | claim.control_total | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-207 | old_is_deleted | claim.is_deleted | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-208 | old_hold_ref | claim.hold_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-209 | old_configuration_ref | claim.configuration_ref | Preserve source text | Empty input is not defaulted |
| MAP-210 | old_correlation_ref | claim.correlation_ref | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-211 | old_legacy_status | claim.legacy_status | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-212 | old_notes_state | claim.notes_state | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-213 | old_member_ref | claim.member_ref | Preserve source text | Empty input is not defaulted |
| MAP-214 | old_event_ref | claim.event_ref | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-215 | old_event_type | claim.event_type | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-216 | old_reported_on | claim.reported_on | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-217 | old_intake_state | claim.intake_state | Preserve source text | Empty input is not defaulted |
| MAP-218 | old_checklist_ref | claim.checklist_ref | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-219 | old_assessment_ref | claim.assessment_ref | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-220 | old_decision_ref | claim.decision_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-221 | old_quote_amount | claim.quote_amount | Preserve source text | Empty input is not defaulted |
| MAP-222 | old_appeal_ref | claim.appeal_ref | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-223 | old_reopened_on | claim.reopened_on | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-224 | old_entitlement_ref | claim.entitlement_ref | Pass through when explicitly present | Case sensitivity remains unresolved |

Relationship fragment: the claim export includes a parent reference, but the parent may belong to a different historical revision. Reject cross-tenant references; do not silently adopt the parent scope.
Deletion fragment: an inactive claim may still be needed for replay comparison. Retention periods are invented scenario parameters, not legal schedules.

> Compliance note: requires Belgian-market and legal validation.


## Entity payment

DATASET-008. Owner: Benefits stream. Last mapping discussion: 2023-12-12.
The payment record is a fictional persistence boundary. Its older export counterpart is called payment master. The rename was not propagated to reports.
Primary workflow context: [Document template selection](functional-specification.md#feature-f-043-document-template-selection). Relationships are represented by opaque synthetic keys; referential enforcement on legacy staging rows is TBD.
Possibly obsolete: the migration sheet describes payment as mutable in place. The feature pages usually assume revisions.
Canonical proposal: one tenant scope and one fixture key identify a revision chain, but exported snapshots may repeat the key.

| Data ID | Field | Draft type | Presence | Meaning or mapping note | Source quality |
| --- | --- | --- | --- | --- | --- |
| DATA-225 | fixture_key | opaque text | Required | Synthetic record reference; never a policy number or real identity | Possibly obsolete |
| DATA-226 | tenant_scope | opaque text | Required | Partition boundary used before any business lookup | Duplicate alias |
| DATA-227 | revision_no | integer | Required | Monotonic within this fixture object, not across entities | Unreviewed |
| DATA-228 | state_code | enum text | Required | Draft state vocabulary depends on the owning feature | Draft |
| DATA-229 | effective_on | date text | Conditional | Business effective date; missing date interpretation unresolved | Possibly obsolete |
| DATA-230 | recorded_at | timestamp text | Required | Processing timestamp; source zone missing in old import | Duplicate alias |
| DATA-231 | source_ref | opaque text | Optional | Reference to the internal staging envelope | Unreviewed |
| DATA-232 | previous_ref | opaque text | Optional | Predecessor revision; must not form a cycle | Draft |
| DATA-233 | owner_queue | enum text | Optional | Queue label rather than a named individual | Possibly obsolete |
| DATA-234 | review_status | enum text | Required | Review completeness is separate from business approval | Duplicate alias |
| DATA-235 | reason_code | enum text | Conditional | Code values differ between the old desk and the new queue | Unreviewed |
| DATA-236 | display_label | text | Optional | Synthetic label; no real person or organisation name | Draft |
| DATA-237 | import_batch_ref | opaque text | Optional | Batch provenance; blank in interactive records | Possibly obsolete |
| DATA-238 | control_total | decimal text | Conditional | Synthetic aggregate; scale must be explicitly supplied | Duplicate alias |
| DATA-239 | is_deleted | boolean text | Optional | Historical soft-delete flag; conflicts with state semantics | Unreviewed |
| DATA-240 | hold_ref | opaque text | Optional | Current hold link; multiple holds were not modeled here | Draft |
| DATA-241 | configuration_ref | opaque text | Required | Versioned rule configuration used at processing time | Possibly obsolete |
| DATA-242 | correlation_ref | opaque text | Required | End-to-end trace marker without identifying content | Duplicate alias |
| DATA-243 | legacy_status | text | Optional | Untranslated historical status retained for reconciliation | Unreviewed |
| DATA-244 | notes_state | enum text | Optional | Indicates notes existence without including free-form personal data | Draft |
| DATA-245 | claim_ref | unresolved scalar | Required | claim ref for the payment; keep source text until reviewed | Possibly obsolete |
| DATA-246 | instruction_ref | unresolved scalar | Conditional | instruction ref for the payment; reference target not agreed | Duplicate alias |
| DATA-247 | amount | decimal text | Conditional | amount for the payment; blank differs from omitted | Unreviewed |
| DATA-248 | currency_label | unresolved scalar | Required | currency label for the payment; version must match the originating task | Draft |
| DATA-249 | approval_one_ref | unresolved scalar | Conditional | approval one ref for the payment; keep source text until reviewed | Possibly obsolete |
| DATA-250 | approval_two_ref | unresolved scalar | Conditional | approval two ref for the payment; reference target not agreed | Duplicate alias |
| DATA-251 | window_ref | unresolved scalar | Required | window ref for the payment; blank differs from omitted | Unreviewed |
| DATA-252 | release_state | unresolved scalar | Conditional | release state for the payment; version must match the originating task | Draft |
| DATA-253 | return_ref | unresolved scalar | Conditional | return ref for the payment; keep source text until reviewed | Possibly obsolete |
| DATA-254 | settlement_ref | unresolved scalar | Required | settlement ref for the payment; reference target not agreed | Duplicate alias |
| DATA-255 | hold_reason | unresolved scalar | Conditional | hold reason for the payment; blank differs from omitted | Unreviewed |
| DATA-256 | retry_count | integer | Conditional | retry count for the payment; version must match the originating task | Draft |

### payment field mapping residue

| Mapping ID | Source column | Target field | Transform | Rejection or ambiguity |
| --- | --- | --- | --- | --- |
| MAP-225 | old_fixture_key | payment.fixture_key | Preserve source text | Empty input is not defaulted |
| MAP-226 | old_tenant_scope | payment.tenant_scope | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-227 | old_revision_no | payment.revision_no | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-228 | old_state_code | payment.state_code | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-229 | old_effective_on | payment.effective_on | Preserve source text | Empty input is not defaulted |
| MAP-230 | old_recorded_at | payment.recorded_at | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-231 | old_source_ref | payment.source_ref | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-232 | old_previous_ref | payment.previous_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-233 | old_owner_queue | payment.owner_queue | Preserve source text | Empty input is not defaulted |
| MAP-234 | old_review_status | payment.review_status | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-235 | old_reason_code | payment.reason_code | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-236 | old_display_label | payment.display_label | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-237 | old_import_batch_ref | payment.import_batch_ref | Preserve source text | Empty input is not defaulted |
| MAP-238 | old_control_total | payment.control_total | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-239 | old_is_deleted | payment.is_deleted | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-240 | old_hold_ref | payment.hold_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-241 | old_configuration_ref | payment.configuration_ref | Preserve source text | Empty input is not defaulted |
| MAP-242 | old_correlation_ref | payment.correlation_ref | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-243 | old_legacy_status | payment.legacy_status | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-244 | old_notes_state | payment.notes_state | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-245 | old_claim_ref | payment.claim_ref | Preserve source text | Empty input is not defaulted |
| MAP-246 | old_instruction_ref | payment.instruction_ref | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-247 | old_amount | payment.amount | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-248 | old_currency_label | payment.currency_label | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-249 | old_approval_one_ref | payment.approval_one_ref | Preserve source text | Empty input is not defaulted |
| MAP-250 | old_approval_two_ref | payment.approval_two_ref | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-251 | old_window_ref | payment.window_ref | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-252 | old_release_state | payment.release_state | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-253 | old_return_ref | payment.return_ref | Preserve source text | Empty input is not defaulted |
| MAP-254 | old_settlement_ref | payment.settlement_ref | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-255 | old_hold_reason | payment.hold_reason | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-256 | old_retry_count | payment.retry_count | Pass through when explicitly present | Case sensitivity remains unresolved |

Relationship fragment: the payment export includes a parent reference, but the parent may belong to a different historical revision. Reject cross-tenant references; do not silently adopt the parent scope.
Deletion fragment: an inactive payment may still be needed for replay comparison. Retention periods are invented scenario parameters, not legal schedules.

> Compliance note: requires Belgian-market and legal validation.


## Entity document

DATASET-009. Owner: TBD. Last mapping discussion: 2024-01-13.
The document record is a fictional persistence boundary. Its older export counterpart is called document master. The rename was not propagated to reports.
Primary workflow context: [Notification preference update](functional-specification.md#feature-f-049-notification-preference-update). Relationships are represented by opaque synthetic keys; referential enforcement on legacy staging rows is TBD.
Possibly obsolete: the migration sheet describes document as mutable in place. The feature pages usually assume revisions.
Canonical proposal: one tenant scope and one fixture key identify a revision chain, but exported snapshots may repeat the key.

| Data ID | Field | Draft type | Presence | Meaning or mapping note | Source quality |
| --- | --- | --- | --- | --- | --- |
| DATA-257 | fixture_key | opaque text | Required | Synthetic record reference; never a policy number or real identity | Possibly obsolete |
| DATA-258 | tenant_scope | opaque text | Required | Partition boundary used before any business lookup | Duplicate alias |
| DATA-259 | revision_no | integer | Required | Monotonic within this fixture object, not across entities | Unreviewed |
| DATA-260 | state_code | enum text | Required | Draft state vocabulary depends on the owning feature | Draft |
| DATA-261 | effective_on | date text | Conditional | Business effective date; missing date interpretation unresolved | Possibly obsolete |
| DATA-262 | recorded_at | timestamp text | Required | Processing timestamp; source zone missing in old import | Duplicate alias |
| DATA-263 | source_ref | opaque text | Optional | Reference to the internal staging envelope | Unreviewed |
| DATA-264 | previous_ref | opaque text | Optional | Predecessor revision; must not form a cycle | Draft |
| DATA-265 | owner_queue | enum text | Optional | Queue label rather than a named individual | Possibly obsolete |
| DATA-266 | review_status | enum text | Required | Review completeness is separate from business approval | Duplicate alias |
| DATA-267 | reason_code | enum text | Conditional | Code values differ between the old desk and the new queue | Unreviewed |
| DATA-268 | display_label | text | Optional | Synthetic label; no real person or organisation name | Draft |
| DATA-269 | import_batch_ref | opaque text | Optional | Batch provenance; blank in interactive records | Possibly obsolete |
| DATA-270 | control_total | decimal text | Conditional | Synthetic aggregate; scale must be explicitly supplied | Duplicate alias |
| DATA-271 | is_deleted | boolean text | Optional | Historical soft-delete flag; conflicts with state semantics | Unreviewed |
| DATA-272 | hold_ref | opaque text | Optional | Current hold link; multiple holds were not modeled here | Draft |
| DATA-273 | configuration_ref | opaque text | Required | Versioned rule configuration used at processing time | Possibly obsolete |
| DATA-274 | correlation_ref | opaque text | Required | End-to-end trace marker without identifying content | Duplicate alias |
| DATA-275 | legacy_status | text | Optional | Untranslated historical status retained for reconciliation | Unreviewed |
| DATA-276 | notes_state | enum text | Optional | Indicates notes existence without including free-form personal data | Draft |
| DATA-277 | template_ref | unresolved scalar | Required | template ref for the document; keep source text until reviewed | Possibly obsolete |
| DATA-278 | template_revision | unresolved scalar | Conditional | template revision for the document; reference target not agreed | Duplicate alias |
| DATA-279 | language_code | unresolved scalar | Conditional | language code for the document; blank differs from omitted | Unreviewed |
| DATA-280 | snapshot_ref | unresolved scalar | Required | snapshot ref for the document; version must match the originating task | Draft |
| DATA-281 | content_placeholder | unresolved scalar | Conditional | content placeholder for the document; keep source text until reviewed | Possibly obsolete |
| DATA-282 | render_state | unresolved scalar | Conditional | render state for the document; reference target not agreed | Duplicate alias |
| DATA-283 | issued_on | unresolved scalar | Required | issued on for the document; blank differs from omitted | Unreviewed |
| DATA-284 | superseded_by | unresolved scalar | Conditional | superseded by for the document; version must match the originating task | Draft |
| DATA-285 | delivery_ref | unresolved scalar | Conditional | delivery ref for the document; keep source text until reviewed | Possibly obsolete |
| DATA-286 | retention_until | unresolved scalar | Required | retention until for the document; reference target not agreed | Duplicate alias |
| DATA-287 | purge_state | unresolved scalar | Conditional | purge state for the document; blank differs from omitted | Unreviewed |
| DATA-288 | tombstone_ref | unresolved scalar | Conditional | tombstone ref for the document; version must match the originating task | Draft |

### document field mapping residue

| Mapping ID | Source column | Target field | Transform | Rejection or ambiguity |
| --- | --- | --- | --- | --- |
| MAP-257 | old_fixture_key | document.fixture_key | Preserve source text | Empty input is not defaulted |
| MAP-258 | old_tenant_scope | document.tenant_scope | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-259 | old_revision_no | document.revision_no | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-260 | old_state_code | document.state_code | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-261 | old_effective_on | document.effective_on | Preserve source text | Empty input is not defaulted |
| MAP-262 | old_recorded_at | document.recorded_at | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-263 | old_source_ref | document.source_ref | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-264 | old_previous_ref | document.previous_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-265 | old_owner_queue | document.owner_queue | Preserve source text | Empty input is not defaulted |
| MAP-266 | old_review_status | document.review_status | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-267 | old_reason_code | document.reason_code | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-268 | old_display_label | document.display_label | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-269 | old_import_batch_ref | document.import_batch_ref | Preserve source text | Empty input is not defaulted |
| MAP-270 | old_control_total | document.control_total | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-271 | old_is_deleted | document.is_deleted | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-272 | old_hold_ref | document.hold_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-273 | old_configuration_ref | document.configuration_ref | Preserve source text | Empty input is not defaulted |
| MAP-274 | old_correlation_ref | document.correlation_ref | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-275 | old_legacy_status | document.legacy_status | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-276 | old_notes_state | document.notes_state | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-277 | old_template_ref | document.template_ref | Preserve source text | Empty input is not defaulted |
| MAP-278 | old_template_revision | document.template_revision | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-279 | old_language_code | document.language_code | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-280 | old_snapshot_ref | document.snapshot_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-281 | old_content_placeholder | document.content_placeholder | Preserve source text | Empty input is not defaulted |
| MAP-282 | old_render_state | document.render_state | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-283 | old_issued_on | document.issued_on | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-284 | old_superseded_by | document.superseded_by | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-285 | old_delivery_ref | document.delivery_ref | Preserve source text | Empty input is not defaulted |
| MAP-286 | old_retention_until | document.retention_until | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-287 | old_purge_state | document.purge_state | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-288 | old_tombstone_ref | document.tombstone_ref | Pass through when explicitly present | Case sensitivity remains unresolved |

Relationship fragment: the document export includes a parent reference, but the parent may belong to a different historical revision. Reject cross-tenant references; do not silently adopt the parent scope.
Deletion fragment: an inactive document may still be needed for replay comparison. Retention periods are invented scenario parameters, not legal schedules.

> Compliance note: requires Belgian-market and legal validation.


## Entity audit event

DATASET-010. Owner: Platform support. Last mapping discussion: 2025-02-14.
The audit event record is a fictional persistence boundary. Its older export counterpart is called audit event master. The rename was not propagated to reports.
Primary workflow context: [Employer coverage report](functional-specification.md#feature-f-055-employer-coverage-report). Relationships are represented by opaque synthetic keys; referential enforcement on legacy staging rows is TBD.
Possibly obsolete: the migration sheet describes audit event as mutable in place. The feature pages usually assume revisions.
Canonical proposal: one tenant scope and one fixture key identify a revision chain, but exported snapshots may repeat the key.

| Data ID | Field | Draft type | Presence | Meaning or mapping note | Source quality |
| --- | --- | --- | --- | --- | --- |
| DATA-289 | fixture_key | opaque text | Required | Synthetic record reference; never a policy number or real identity | Possibly obsolete |
| DATA-290 | tenant_scope | opaque text | Required | Partition boundary used before any business lookup | Duplicate alias |
| DATA-291 | revision_no | integer | Required | Monotonic within this fixture object, not across entities | Unreviewed |
| DATA-292 | state_code | enum text | Required | Draft state vocabulary depends on the owning feature | Draft |
| DATA-293 | effective_on | date text | Conditional | Business effective date; missing date interpretation unresolved | Possibly obsolete |
| DATA-294 | recorded_at | timestamp text | Required | Processing timestamp; source zone missing in old import | Duplicate alias |
| DATA-295 | source_ref | opaque text | Optional | Reference to the internal staging envelope | Unreviewed |
| DATA-296 | previous_ref | opaque text | Optional | Predecessor revision; must not form a cycle | Draft |
| DATA-297 | owner_queue | enum text | Optional | Queue label rather than a named individual | Possibly obsolete |
| DATA-298 | review_status | enum text | Required | Review completeness is separate from business approval | Duplicate alias |
| DATA-299 | reason_code | enum text | Conditional | Code values differ between the old desk and the new queue | Unreviewed |
| DATA-300 | display_label | text | Optional | Synthetic label; no real person or organisation name | Draft |
| DATA-301 | import_batch_ref | opaque text | Optional | Batch provenance; blank in interactive records | Possibly obsolete |
| DATA-302 | control_total | decimal text | Conditional | Synthetic aggregate; scale must be explicitly supplied | Duplicate alias |
| DATA-303 | is_deleted | boolean text | Optional | Historical soft-delete flag; conflicts with state semantics | Unreviewed |
| DATA-304 | hold_ref | opaque text | Optional | Current hold link; multiple holds were not modeled here | Draft |
| DATA-305 | configuration_ref | opaque text | Required | Versioned rule configuration used at processing time | Possibly obsolete |
| DATA-306 | correlation_ref | opaque text | Required | End-to-end trace marker without identifying content | Duplicate alias |
| DATA-307 | legacy_status | text | Optional | Untranslated historical status retained for reconciliation | Unreviewed |
| DATA-308 | notes_state | enum text | Optional | Indicates notes existence without including free-form personal data | Draft |
| DATA-309 | subject_ref | unresolved scalar | Required | subject ref for the audit event; keep source text until reviewed | Possibly obsolete |
| DATA-310 | action_code | unresolved scalar | Conditional | action code for the audit event; reference target not agreed | Duplicate alias |
| DATA-311 | actor_role_label | unresolved scalar | Conditional | actor role label for the audit event; blank differs from omitted | Unreviewed |
| DATA-312 | occurred_at | unresolved scalar | Required | occurred at for the audit event; version must match the originating task | Draft |
| DATA-313 | before_revision | unresolved scalar | Conditional | before revision for the audit event; keep source text until reviewed | Possibly obsolete |
| DATA-314 | after_revision | unresolved scalar | Conditional | after revision for the audit event; reference target not agreed | Duplicate alias |
| DATA-315 | outcome_code | unresolved scalar | Required | outcome code for the audit event; blank differs from omitted | Unreviewed |
| DATA-316 | hold_ref_list | unresolved scalar | Conditional | hold ref list for the audit event; version must match the originating task | Draft |
| DATA-317 | export_ref | unresolved scalar | Conditional | export ref for the audit event; keep source text until reviewed | Possibly obsolete |
| DATA-318 | event_sequence | unresolved scalar | Required | event sequence for the audit event; reference target not agreed | Duplicate alias |
| DATA-319 | replay_ref | unresolved scalar | Conditional | replay ref for the audit event; blank differs from omitted | Unreviewed |
| DATA-320 | payload_digest_placeholder | unresolved scalar | Conditional | payload digest placeholder for the audit event; version must match the originating task | Draft |

### audit event field mapping residue

| Mapping ID | Source column | Target field | Transform | Rejection or ambiguity |
| --- | --- | --- | --- | --- |
| MAP-289 | old_fixture_key | audit_event.fixture_key | Preserve source text | Empty input is not defaulted |
| MAP-290 | old_tenant_scope | audit_event.tenant_scope | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-291 | old_revision_no | audit_event.revision_no | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-292 | old_state_code | audit_event.state_code | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-293 | old_effective_on | audit_event.effective_on | Preserve source text | Empty input is not defaulted |
| MAP-294 | old_recorded_at | audit_event.recorded_at | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-295 | old_source_ref | audit_event.source_ref | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-296 | old_previous_ref | audit_event.previous_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-297 | old_owner_queue | audit_event.owner_queue | Preserve source text | Empty input is not defaulted |
| MAP-298 | old_review_status | audit_event.review_status | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-299 | old_reason_code | audit_event.reason_code | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-300 | old_display_label | audit_event.display_label | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-301 | old_import_batch_ref | audit_event.import_batch_ref | Preserve source text | Empty input is not defaulted |
| MAP-302 | old_control_total | audit_event.control_total | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-303 | old_is_deleted | audit_event.is_deleted | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-304 | old_hold_ref | audit_event.hold_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-305 | old_configuration_ref | audit_event.configuration_ref | Preserve source text | Empty input is not defaulted |
| MAP-306 | old_correlation_ref | audit_event.correlation_ref | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-307 | old_legacy_status | audit_event.legacy_status | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-308 | old_notes_state | audit_event.notes_state | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-309 | old_subject_ref | audit_event.subject_ref | Preserve source text | Empty input is not defaulted |
| MAP-310 | old_action_code | audit_event.action_code | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-311 | old_actor_role_label | audit_event.actor_role_label | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-312 | old_occurred_at | audit_event.occurred_at | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-313 | old_before_revision | audit_event.before_revision | Preserve source text | Empty input is not defaulted |
| MAP-314 | old_after_revision | audit_event.after_revision | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-315 | old_outcome_code | audit_event.outcome_code | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-316 | old_hold_ref_list | audit_event.hold_ref_list | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-317 | old_export_ref | audit_event.export_ref | Preserve source text | Empty input is not defaulted |
| MAP-318 | old_event_sequence | audit_event.event_sequence | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-319 | old_replay_ref | audit_event.replay_ref | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-320 | old_payload_digest_placeholder | audit_event.payload_digest_placeholder | Pass through when explicitly present | Case sensitivity remains unresolved |

Relationship fragment: the audit event export includes a parent reference, but the parent may belong to a different historical revision. Reject cross-tenant references; do not silently adopt the parent scope.
Deletion fragment: an inactive audit event may still be needed for replay comparison. Retention periods are invented scenario parameters, not legal schedules.

> Compliance note: requires Belgian-market and legal validation.


## Entity report

DATASET-011. Owner: Reporting stream. Last mapping discussion: 2019-03-15.
The report record is a fictional persistence boundary. Its older export counterpart is called report master. The rename was not propagated to reports.
Primary workflow context: [User role assignment](functional-specification.md#feature-f-061-user-role-assignment). Relationships are represented by opaque synthetic keys; referential enforcement on legacy staging rows is TBD.
Possibly obsolete: the migration sheet describes report as mutable in place. The feature pages usually assume revisions.
Canonical proposal: one tenant scope and one fixture key identify a revision chain, but exported snapshots may repeat the key.

| Data ID | Field | Draft type | Presence | Meaning or mapping note | Source quality |
| --- | --- | --- | --- | --- | --- |
| DATA-321 | fixture_key | opaque text | Required | Synthetic record reference; never a policy number or real identity | Possibly obsolete |
| DATA-322 | tenant_scope | opaque text | Required | Partition boundary used before any business lookup | Duplicate alias |
| DATA-323 | revision_no | integer | Required | Monotonic within this fixture object, not across entities | Unreviewed |
| DATA-324 | state_code | enum text | Required | Draft state vocabulary depends on the owning feature | Draft |
| DATA-325 | effective_on | date text | Conditional | Business effective date; missing date interpretation unresolved | Possibly obsolete |
| DATA-326 | recorded_at | timestamp text | Required | Processing timestamp; source zone missing in old import | Duplicate alias |
| DATA-327 | source_ref | opaque text | Optional | Reference to the internal staging envelope | Unreviewed |
| DATA-328 | previous_ref | opaque text | Optional | Predecessor revision; must not form a cycle | Draft |
| DATA-329 | owner_queue | enum text | Optional | Queue label rather than a named individual | Possibly obsolete |
| DATA-330 | review_status | enum text | Required | Review completeness is separate from business approval | Duplicate alias |
| DATA-331 | reason_code | enum text | Conditional | Code values differ between the old desk and the new queue | Unreviewed |
| DATA-332 | display_label | text | Optional | Synthetic label; no real person or organisation name | Draft |
| DATA-333 | import_batch_ref | opaque text | Optional | Batch provenance; blank in interactive records | Possibly obsolete |
| DATA-334 | control_total | decimal text | Conditional | Synthetic aggregate; scale must be explicitly supplied | Duplicate alias |
| DATA-335 | is_deleted | boolean text | Optional | Historical soft-delete flag; conflicts with state semantics | Unreviewed |
| DATA-336 | hold_ref | opaque text | Optional | Current hold link; multiple holds were not modeled here | Draft |
| DATA-337 | configuration_ref | opaque text | Required | Versioned rule configuration used at processing time | Possibly obsolete |
| DATA-338 | correlation_ref | opaque text | Required | End-to-end trace marker without identifying content | Duplicate alias |
| DATA-339 | legacy_status | text | Optional | Untranslated historical status retained for reconciliation | Unreviewed |
| DATA-340 | notes_state | enum text | Optional | Indicates notes existence without including free-form personal data | Draft |
| DATA-341 | report_type | unresolved scalar | Required | report type for the report; keep source text until reviewed | Possibly obsolete |
| DATA-342 | as_of_date | unresolved scalar | Conditional | as of date for the report; reference target not agreed | Duplicate alias |
| DATA-343 | selection_ref | unresolved scalar | Conditional | selection ref for the report; blank differs from omitted | Unreviewed |
| DATA-344 | snapshot_ref | unresolved scalar | Required | snapshot ref for the report; version must match the originating task | Draft |
| DATA-345 | row_count | integer | Conditional | row count for the report; keep source text until reviewed | Possibly obsolete |
| DATA-346 | warning_count | integer | Conditional | warning count for the report; reference target not agreed | Duplicate alias |
| DATA-347 | control_amount | decimal text | Required | control amount for the report; blank differs from omitted | Unreviewed |
| DATA-348 | generation_state | unresolved scalar | Conditional | generation state for the report; version must match the originating task | Draft |
| DATA-349 | supersedes_ref | unresolved scalar | Conditional | supersedes ref for the report; keep source text until reviewed | Possibly obsolete |
| DATA-350 | delivery_state | unresolved scalar | Required | delivery state for the report; reference target not agreed | Duplicate alias |
| DATA-351 | branch_review_ref | unresolved scalar | Conditional | branch review ref for the report; blank differs from omitted | Unreviewed |
| DATA-352 | external_validation_state | unresolved scalar | Conditional | external validation state for the report; version must match the originating task | Draft |

### report field mapping residue

| Mapping ID | Source column | Target field | Transform | Rejection or ambiguity |
| --- | --- | --- | --- | --- |
| MAP-321 | old_fixture_key | report.fixture_key | Preserve source text | Empty input is not defaulted |
| MAP-322 | old_tenant_scope | report.tenant_scope | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-323 | old_revision_no | report.revision_no | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-324 | old_state_code | report.state_code | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-325 | old_effective_on | report.effective_on | Preserve source text | Empty input is not defaulted |
| MAP-326 | old_recorded_at | report.recorded_at | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-327 | old_source_ref | report.source_ref | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-328 | old_previous_ref | report.previous_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-329 | old_owner_queue | report.owner_queue | Preserve source text | Empty input is not defaulted |
| MAP-330 | old_review_status | report.review_status | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-331 | old_reason_code | report.reason_code | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-332 | old_display_label | report.display_label | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-333 | old_import_batch_ref | report.import_batch_ref | Preserve source text | Empty input is not defaulted |
| MAP-334 | old_control_total | report.control_total | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-335 | old_is_deleted | report.is_deleted | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-336 | old_hold_ref | report.hold_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-337 | old_configuration_ref | report.configuration_ref | Preserve source text | Empty input is not defaulted |
| MAP-338 | old_correlation_ref | report.correlation_ref | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-339 | old_legacy_status | report.legacy_status | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-340 | old_notes_state | report.notes_state | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-341 | old_report_type | report.report_type | Preserve source text | Empty input is not defaulted |
| MAP-342 | old_as_of_date | report.as_of_date | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-343 | old_selection_ref | report.selection_ref | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-344 | old_snapshot_ref | report.snapshot_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-345 | old_row_count | report.row_count | Preserve source text | Empty input is not defaulted |
| MAP-346 | old_warning_count | report.warning_count | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-347 | old_control_amount | report.control_amount | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-348 | old_generation_state | report.generation_state | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-349 | old_supersedes_ref | report.supersedes_ref | Preserve source text | Empty input is not defaulted |
| MAP-350 | old_delivery_state | report.delivery_state | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-351 | old_branch_review_ref | report.branch_review_ref | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-352 | old_external_validation_state | report.external_validation_state | Pass through when explicitly present | Case sensitivity remains unresolved |

Relationship fragment: the report export includes a parent reference, but the parent may belong to a different historical revision. Reject cross-tenant references; do not silently adopt the parent scope.
Deletion fragment: an inactive report may still be needed for replay comparison. Retention periods are invented scenario parameters, not legal schedules.

> Compliance note: requires Belgian-market and legal validation.


## Entity integration envelope

DATASET-012. Owner: Former migration team. Last mapping discussion: 2020-04-16.
The integration envelope record is a fictional persistence boundary. Its older export counterpart is called integration envelope master. The rename was not propagated to reports.
Primary workflow context: [Audit event capture](functional-specification.md#feature-f-067-audit-event-capture). Relationships are represented by opaque synthetic keys; referential enforcement on legacy staging rows is TBD.
Possibly obsolete: the migration sheet describes integration envelope as mutable in place. The feature pages usually assume revisions.
Canonical proposal: one tenant scope and one fixture key identify a revision chain, but exported snapshots may repeat the key.

| Data ID | Field | Draft type | Presence | Meaning or mapping note | Source quality |
| --- | --- | --- | --- | --- | --- |
| DATA-353 | fixture_key | opaque text | Required | Synthetic record reference; never a policy number or real identity | Possibly obsolete |
| DATA-354 | tenant_scope | opaque text | Required | Partition boundary used before any business lookup | Duplicate alias |
| DATA-355 | revision_no | integer | Required | Monotonic within this fixture object, not across entities | Unreviewed |
| DATA-356 | state_code | enum text | Required | Draft state vocabulary depends on the owning feature | Draft |
| DATA-357 | effective_on | date text | Conditional | Business effective date; missing date interpretation unresolved | Possibly obsolete |
| DATA-358 | recorded_at | timestamp text | Required | Processing timestamp; source zone missing in old import | Duplicate alias |
| DATA-359 | source_ref | opaque text | Optional | Reference to the internal staging envelope | Unreviewed |
| DATA-360 | previous_ref | opaque text | Optional | Predecessor revision; must not form a cycle | Draft |
| DATA-361 | owner_queue | enum text | Optional | Queue label rather than a named individual | Possibly obsolete |
| DATA-362 | review_status | enum text | Required | Review completeness is separate from business approval | Duplicate alias |
| DATA-363 | reason_code | enum text | Conditional | Code values differ between the old desk and the new queue | Unreviewed |
| DATA-364 | display_label | text | Optional | Synthetic label; no real person or organisation name | Draft |
| DATA-365 | import_batch_ref | opaque text | Optional | Batch provenance; blank in interactive records | Possibly obsolete |
| DATA-366 | control_total | decimal text | Conditional | Synthetic aggregate; scale must be explicitly supplied | Duplicate alias |
| DATA-367 | is_deleted | boolean text | Optional | Historical soft-delete flag; conflicts with state semantics | Unreviewed |
| DATA-368 | hold_ref | opaque text | Optional | Current hold link; multiple holds were not modeled here | Draft |
| DATA-369 | configuration_ref | opaque text | Required | Versioned rule configuration used at processing time | Possibly obsolete |
| DATA-370 | correlation_ref | opaque text | Required | End-to-end trace marker without identifying content | Duplicate alias |
| DATA-371 | legacy_status | text | Optional | Untranslated historical status retained for reconciliation | Unreviewed |
| DATA-372 | notes_state | enum text | Optional | Indicates notes existence without including free-form personal data | Draft |
| DATA-373 | operation_ref | unresolved scalar | Required | operation ref for the integration envelope; keep source text until reviewed | Possibly obsolete |
| DATA-374 | logical_key | unresolved scalar | Conditional | logical key for the integration envelope; reference target not agreed | Duplicate alias |
| DATA-375 | request_revision | unresolved scalar | Conditional | request revision for the integration envelope; blank differs from omitted | Unreviewed |
| DATA-376 | payload_version | unresolved scalar | Required | payload version for the integration envelope; version must match the originating task | Draft |
| DATA-377 | received_at | unresolved scalar | Conditional | received at for the integration envelope; keep source text until reviewed | Possibly obsolete |
| DATA-378 | processed_at | unresolved scalar | Conditional | processed at for the integration envelope; reference target not agreed | Duplicate alias |
| DATA-379 | attempt_count | integer | Required | attempt count for the integration envelope; blank differs from omitted | Unreviewed |
| DATA-380 | response_code | unresolved scalar | Conditional | response code for the integration envelope; version must match the originating task | Draft |
| DATA-381 | rejection_ref | unresolved scalar | Conditional | rejection ref for the integration envelope; keep source text until reviewed | Possibly obsolete |
| DATA-382 | accepted_count | integer | Required | accepted count for the integration envelope; reference target not agreed | Duplicate alias |
| DATA-383 | rejected_count | integer | Conditional | rejected count for the integration envelope; blank differs from omitted | Unreviewed |
| DATA-384 | simulation_mode | unresolved scalar | Conditional | simulation mode for the integration envelope; version must match the originating task | Draft |

### integration envelope field mapping residue

| Mapping ID | Source column | Target field | Transform | Rejection or ambiguity |
| --- | --- | --- | --- | --- |
| MAP-353 | old_fixture_key | integration_envelope.fixture_key | Preserve source text | Empty input is not defaulted |
| MAP-354 | old_tenant_scope | integration_envelope.tenant_scope | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-355 | old_revision_no | integration_envelope.revision_no | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-356 | old_state_code | integration_envelope.state_code | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-357 | old_effective_on | integration_envelope.effective_on | Preserve source text | Empty input is not defaulted |
| MAP-358 | old_recorded_at | integration_envelope.recorded_at | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-359 | old_source_ref | integration_envelope.source_ref | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-360 | old_previous_ref | integration_envelope.previous_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-361 | old_owner_queue | integration_envelope.owner_queue | Preserve source text | Empty input is not defaulted |
| MAP-362 | old_review_status | integration_envelope.review_status | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-363 | old_reason_code | integration_envelope.reason_code | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-364 | old_display_label | integration_envelope.display_label | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-365 | old_import_batch_ref | integration_envelope.import_batch_ref | Preserve source text | Empty input is not defaulted |
| MAP-366 | old_control_total | integration_envelope.control_total | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-367 | old_is_deleted | integration_envelope.is_deleted | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-368 | old_hold_ref | integration_envelope.hold_ref | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-369 | old_configuration_ref | integration_envelope.configuration_ref | Preserve source text | Empty input is not defaulted |
| MAP-370 | old_correlation_ref | integration_envelope.correlation_ref | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-371 | old_legacy_status | integration_envelope.legacy_status | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-372 | old_notes_state | integration_envelope.notes_state | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-373 | old_operation_ref | integration_envelope.operation_ref | Preserve source text | Empty input is not defaulted |
| MAP-374 | old_logical_key | integration_envelope.logical_key | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-375 | old_request_revision | integration_envelope.request_revision | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-376 | old_payload_version | integration_envelope.payload_version | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-377 | old_received_at | integration_envelope.received_at | Preserve source text | Empty input is not defaulted |
| MAP-378 | old_processed_at | integration_envelope.processed_at | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-379 | old_attempt_count | integration_envelope.attempt_count | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-380 | old_response_code | integration_envelope.response_code | Pass through when explicitly present | Case sensitivity remains unresolved |
| MAP-381 | old_rejection_ref | integration_envelope.rejection_ref | Preserve source text | Empty input is not defaulted |
| MAP-382 | old_accepted_count | integration_envelope.accepted_count | Trim outer whitespace only | Unrecognized value enters review queue |
| MAP-383 | old_rejected_count | integration_envelope.rejected_count | Lookup a versioned alias; table missing | Prior import silently dropped this value |
| MAP-384 | old_simulation_mode | integration_envelope.simulation_mode | Pass through when explicitly present | Case sensitivity remains unresolved |

Relationship fragment: the integration envelope export includes a parent reference, but the parent may belong to a different historical revision. Reject cross-tenant references; do not silently adopt the parent scope.
Deletion fragment: an inactive integration envelope may still be needed for replay comparison. Retention periods are invented scenario parameters, not legal schedules.

> Compliance note: requires Belgian-market and legal validation.

## API-like operation notebook

These are relative routes for a nonexistent local simulator. No host, secret, authentication token, real account, or production protocol is specified.
The status codes below are proposed fixture responses. Names do not assert interoperability with any external service.

## INT-001

Operation title: Policy creation. Feature contract: [Policy creation](functional-specification.md#feature-f-001-policy-creation).
Draft route: `POST /synthetic/v0/policy-administration/policy-creation`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the policy at the start of draft → proposed.
Proposed action: Effective date must equal the recorded approval date.
Guard: A proposed policy has no payable balance.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Benefits stream owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1601: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2020-02-02 adapter note omitted expected_revision.


## INT-002

Operation title: Policy amendment. Feature contract: [Policy amendment](functional-specification.md#feature-f-002-policy-amendment).
Draft route: `POST /synthetic/v0/policy-administration/policy-amendment`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the policy revision at the start of active → revised.
Proposed action: A revision may take effect before its approval date.
Guard: Preserve the preceding revision for reconciliation.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: TBD owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1602: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2021-03-03 adapter note omitted expected_revision.


## INT-003

Operation title: Policy renewal. Feature contract: [Policy renewal](functional-specification.md#feature-f-003-policy-renewal).
Draft route: `POST /synthetic/v0/policy-administration/policy-renewal`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the renewal instruction at the start of expiring → renewed.
Proposed action: Create a new coverage period without silently copying unresolved exclusions.
Guard: An unapproved renewal stays in the exception queue.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Platform support owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1603: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2022-04-04 adapter note omitted expected_revision.


## INT-004

Operation title: Policy suspension. Feature contract: [Policy suspension](functional-specification.md#feature-f-004-policy-suspension).
Draft route: `POST /synthetic/v0/policy-administration/policy-suspension`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the suspension window at the start of active → suspended.
Proposed action: Freeze new collection instructions inside the suspension window.
Guard: Already released payments are handled separately.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Reporting stream owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1604: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2023-05-05 adapter note omitted expected_revision.


## INT-005

Operation title: Policy cancellation. Feature contract: [Policy cancellation](functional-specification.md#feature-f-005-policy-cancellation).
Draft route: `POST /synthetic/v0/policy-administration/policy-cancellation`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the cancellation request at the start of active → cancelled.
Proposed action: Require a cancellation reason before the nightly close.
Guard: Do not delete pending claims when coverage closes.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Former migration team owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1605: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2024-06-06 adapter note omitted expected_revision.


## INT-006

Operation title: Policy reinstatement. Feature contract: [Policy reinstatement](functional-specification.md#feature-f-006-policy-reinstatement).
Draft route: `POST /synthetic/v0/policy-administration/policy-reinstatement`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the reinstatement request at the start of cancelled → active.
Proposed action: Check whether the original accounting period is still open.
Guard: A new revision must identify the gap in coverage.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Operations team owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1606: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2025-07-07 adapter note omitted expected_revision.


## INT-007

Operation title: Employer shell creation. Feature contract: [Employer shell creation](functional-specification.md#feature-f-007-employer-shell-creation).
Draft route: `POST /synthetic/v0/employer-onboarding/employer-shell-creation`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the employer shell at the start of received → incomplete.
Proposed action: Keep a shell employer separate from an enabled sponsor.
Guard: A missing administrative address blocks activation.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Benefits stream owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1607: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2019-08-08 adapter note omitted expected_revision.


## INT-008

Operation title: Employer document intake. Feature contract: [Employer document intake](functional-specification.md#feature-f-008-employer-document-intake).
Draft route: `POST /synthetic/v0/employer-onboarding/employer-document-intake`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the intake packet at the start of uploaded → reviewed.
Proposed action: Classify each attachment before accepting the packet.
Guard: A replacement file must retain the original intake reference.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: TBD owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1608: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2020-09-09 adapter note omitted expected_revision.


## INT-009

Operation title: Employer activation. Feature contract: [Employer activation](functional-specification.md#feature-f-009-employer-activation).
Draft route: `POST /synthetic/v0/employer-onboarding/employer-activation`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the employer account at the start of reviewed → enabled.
Proposed action: Require operations review and a benefit package assignment.
Guard: A disabled package cannot activate a new employer.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Platform support owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1609: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2021-10-10 adapter note omitted expected_revision.


## INT-010

Operation title: Employer hierarchy change. Feature contract: [Employer hierarchy change](functional-specification.md#feature-f-010-employer-hierarchy-change).
Draft route: `POST /synthetic/v0/employer-onboarding/employer-hierarchy-change`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the employer hierarchy at the start of flat → grouped.
Proposed action: Use an effective date for parent changes.
Guard: Do not transfer historical invoices to the new parent.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Reporting stream owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1610: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2022-11-11 adapter note omitted expected_revision.


## INT-011

Operation title: Employer contact maintenance. Feature contract: [Employer contact maintenance](functional-specification.md#feature-f-011-employer-contact-maintenance).
Draft route: `POST /synthetic/v0/employer-onboarding/employer-contact-maintenance`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the contact slot at the start of unassigned → routed.
Proposed action: Store a synthetic role mailbox label rather than a named person.
Guard: A contact without a channel cannot receive an outbound event.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Former migration team owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1611: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2023-12-12 adapter note omitted expected_revision.


## INT-012

Operation title: Employer offboarding. Feature contract: [Employer offboarding](functional-specification.md#feature-f-012-employer-offboarding).
Draft route: `POST /synthetic/v0/employer-onboarding/employer-offboarding`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the offboarding case at the start of enabled → closing.
Proposed action: Stop new enrolments after the closing date.
Guard: Unsettled contributions keep the shell visible.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Operations team owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1612: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2024-01-13 adapter note omitted expected_revision.


## INT-013

Operation title: Employee eligibility assessment. Feature contract: [Employee eligibility assessment](functional-specification.md#feature-f-013-employee-eligibility-assessment).
Draft route: `POST /synthetic/v0/eligibility/employee-eligibility-assessment`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the eligibility decision at the start of unchecked → eligible.
Proposed action: Evaluate eligibility using the member status on the payroll period end date.
Guard: An unknown class routes to manual review.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Benefits stream owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1613: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2025-02-14 adapter note omitted expected_revision.


## INT-014

Operation title: Waiting period evaluation. Feature contract: [Waiting period evaluation](functional-specification.md#feature-f-014-waiting-period-evaluation).
Draft route: `POST /synthetic/v0/eligibility/waiting-period-evaluation`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the waiting interval at the start of waiting → qualified.
Proposed action: Count complete fictional plan months from the accepted start date.
Guard: An interrupted interval requires a new review.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: TBD owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1614: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2019-03-15 adapter note omitted expected_revision.


## INT-015

Operation title: Employment category change. Feature contract: [Employment category change](functional-specification.md#feature-f-015-employment-category-change).
Draft route: `POST /synthetic/v0/eligibility/employment-category-change`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the category assignment at the start of class-a → class-b.
Proposed action: Split coverage when a category changes during an open period.
Guard: Never infer a salary from the class label.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Platform support owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1615: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2020-04-16 adapter note omitted expected_revision.


## INT-016

Operation title: Leave and absence handling. Feature contract: [Leave and absence handling](functional-specification.md#feature-f-016-leave-and-absence-handling).
Draft route: `POST /synthetic/v0/eligibility/leave-and-absence-handling`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the absence interval at the start of working → absent.
Proposed action: Distinguish a missing payroll record from a declared absence.
Guard: Overlapping intervals need an operations decision.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Reporting stream owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1616: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2021-05-17 adapter note omitted expected_revision.


## INT-017

Operation title: Member exit processing. Feature contract: [Member exit processing](functional-specification.md#feature-f-017-member-exit-processing).
Draft route: `POST /synthetic/v0/eligibility/member-exit-processing`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the exit instruction at the start of covered → exited.
Proposed action: Close future eligibility without erasing prior coverage.
Guard: A pending death event blocks the ordinary exit path.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Former migration team owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1617: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2022-06-18 adapter note omitted expected_revision.


## INT-018

Operation title: Member re-entry. Feature contract: [Member re-entry](functional-specification.md#feature-f-018-member-re-entry).
Draft route: `POST /synthetic/v0/eligibility/member-re-entry`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the re-entry case at the start of exited → candidate.
Proposed action: Match the synthetic member key before creating a new membership.
Guard: Prior beneficiary choices are not automatically confirmed.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Operations team owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1618: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2023-07-19 adapter note omitted expected_revision.


## INT-019

Operation title: Contribution calculation. Feature contract: [Contribution calculation](functional-specification.md#feature-f-019-contribution-calculation).
Draft route: `POST /synthetic/v0/contributions/contribution-calculation`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the contribution line at the start of rated → calculated.
Proposed action: Round each component before adding the period total.
Guard: Keep the basis and rate revision alongside the result.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Benefits stream owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1619: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2024-08-20 adapter note omitted expected_revision.


## INT-020

Operation title: Contribution allocation. Feature contract: [Contribution allocation](functional-specification.md#feature-f-020-contribution-allocation).
Draft route: `POST /synthetic/v0/contributions/contribution-allocation`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the allocation instruction at the start of unallocated → allocated.
Proposed action: Allocate only to an open synthetic coverage account.
Guard: An unmatched remittance remains on suspense.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: TBD owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1620: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2025-09-21 adapter note omitted expected_revision.


## INT-021

Operation title: Contribution arrears. Feature contract: [Contribution arrears](functional-specification.md#feature-f-021-contribution-arrears).
Draft route: `POST /synthetic/v0/contributions/contribution-arrears`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the arrears item at the start of due → overdue.
Proposed action: Start ageing from the synthetic due date recorded on the item.
Guard: A disputed item remains visible in ageing.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Platform support owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1621: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2019-10-22 adapter note omitted expected_revision.


## INT-022

Operation title: Payroll import. Feature contract: [Payroll import](functional-specification.md#feature-f-022-payroll-import).
Draft route: `POST /synthetic/v0/contributions/payroll-import`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the payroll batch at the start of staged → accepted.
Proposed action: Evaluate eligibility using member status on the payroll file receipt date.
Guard: A rejected row must not silently reduce the accepted control total.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Reporting stream owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1622: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2020-11-23 adapter note omitted expected_revision.


## INT-023

Operation title: Contribution correction. Feature contract: [Contribution correction](functional-specification.md#feature-f-023-contribution-correction).
Draft route: `POST /synthetic/v0/contributions/contribution-correction`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the correction delta at the start of posted → adjusted.
Proposed action: Add unrounded components and round only the final period total.
Guard: Link every correction to a prior posted contribution.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Former migration team owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1623: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2021-12-24 adapter note omitted expected_revision.


## INT-024

Operation title: Contribution refund request. Feature contract: [Contribution refund request](functional-specification.md#feature-f-024-contribution-refund-request).
Draft route: `POST /synthetic/v0/contributions/contribution-refund-request`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the refund case at the start of credit → requested.
Proposed action: A credit balance alone does not authorize a refund.
Guard: A refund must not erase the contribution that created the credit.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Operations team owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1624: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2022-01-25 adapter note omitted expected_revision.


## INT-025

Operation title: Beneficiary designation. Feature contract: [Beneficiary designation](functional-specification.md#feature-f-025-beneficiary-designation).
Draft route: `POST /synthetic/v0/beneficiaries/beneficiary-designation`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the designation set at the start of draft → confirmed.
Proposed action: The latest confirmed designation replaces all previous designations immediately.
Guard: Keep percentage totals separate from verification status.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Benefits stream owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1625: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2023-02-26 adapter note omitted expected_revision.


## INT-026

Operation title: Beneficiary share validation. Feature contract: [Beneficiary share validation](functional-specification.md#feature-f-026-beneficiary-share-validation).
Draft route: `POST /synthetic/v0/beneficiaries/beneficiary-share-validation`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the share set at the start of entered → balanced.
Proposed action: Require the synthetic share total to equal one hundred before confirmation.
Guard: Unknown recipients keep the set in draft.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: TBD owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1626: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2024-03-27 adapter note omitted expected_revision.


## INT-027

Operation title: Beneficiary evidence review. Feature contract: [Beneficiary evidence review](functional-specification.md#feature-f-027-beneficiary-evidence-review).
Draft route: `POST /synthetic/v0/beneficiaries/beneficiary-evidence-review`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the evidence checklist at the start of missing → reviewed.
Proposed action: Evidence completeness is a workflow flag only.
Guard: A reviewed attachment does not determine entitlement.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Platform support owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1627: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2025-04-01 adapter note omitted expected_revision.


## INT-028

Operation title: Retirement event registration. Feature contract: [Retirement event registration](functional-specification.md#feature-f-028-retirement-event-registration).
Draft route: `POST /synthetic/v0/beneficiaries/retirement-event-registration`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the retirement event at the start of reported → assessed.
Proposed action: Use the reported retirement date as an unvalidated event input.
Guard: Do not derive statutory age rules from this fixture.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Reporting stream owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1628: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2019-05-02 adapter note omitted expected_revision.


## INT-029

Operation title: Death event registration. Feature contract: [Death event registration](functional-specification.md#feature-f-029-death-event-registration).
Draft route: `POST /synthetic/v0/beneficiaries/death-event-registration`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the death event at the start of reported → awaiting-review.
Proposed action: Store reported event dates without declaring legal proof.
Guard: Conflicting event reports must remain separately traceable.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Former migration team owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1629: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2020-06-03 adapter note omitted expected_revision.


## INT-030

Operation title: Disability event registration. Feature contract: [Disability event registration](functional-specification.md#feature-f-030-disability-event-registration).
Draft route: `POST /synthetic/v0/beneficiaries/disability-event-registration`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the disability event at the start of reported → awaiting-assessment.
Proposed action: Keep an assessment placeholder separate from benefit authorization.
Guard: No medical diagnosis belongs in the synthetic payload.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Operations team owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1630: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2021-07-04 adapter note omitted expected_revision.


## INT-031

Operation title: Claim intake. Feature contract: [Claim intake](functional-specification.md#feature-f-031-claim-intake).
Draft route: `POST /synthetic/v0/claims/claim-intake`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the claim shell at the start of received → triaged.
Proposed action: Allow intake even when the coverage lookup is unresolved.
Guard: A shell claim cannot generate a payment instruction.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Benefits stream owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1631: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2022-08-05 adapter note omitted expected_revision.


## INT-032

Operation title: Claim evidence checklist. Feature contract: [Claim evidence checklist](functional-specification.md#feature-f-032-claim-evidence-checklist).
Draft route: `POST /synthetic/v0/claims/claim-evidence-checklist`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the claim checklist at the start of open → complete.
Proposed action: Record missing evidence as explicit checklist entries.
Guard: Completeness must not imply approval.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: TBD owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1632: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2023-09-06 adapter note omitted expected_revision.


## INT-033

Operation title: Death claim entitlement snapshot. Feature contract: [Death claim entitlement snapshot](functional-specification.md#feature-f-033-death-claim-entitlement-snapshot).
Draft route: `POST /synthetic/v0/claims/death-claim-entitlement-snapshot`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the entitlement snapshot at the start of candidate → frozen.
Proposed action: Use the designation confirmed at the reported event date even if replaced later.
Guard: The snapshot is a routing aid pending expert validation.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Platform support owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1633: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2024-10-07 adapter note omitted expected_revision.


## INT-034

Operation title: Disability claim assessment. Feature contract: [Disability claim assessment](functional-specification.md#feature-f-034-disability-claim-assessment).
Draft route: `POST /synthetic/v0/claims/disability-claim-assessment`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the assessment task at the start of queued → reviewed.
Proposed action: Require a recorded reviewer role before progressing the task.
Guard: An expired review reopens the checklist.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Reporting stream owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1634: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2025-11-08 adapter note omitted expected_revision.


## INT-035

Operation title: Retirement claim quotation. Feature contract: [Retirement claim quotation](functional-specification.md#feature-f-035-retirement-claim-quotation).
Draft route: `POST /synthetic/v0/claims/retirement-claim-quotation`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the quotation draft at the start of requested → quoted.
Proposed action: Separate indicative amounts from approved settlement amounts.
Guard: A recalculation invalidates the prior quote acknowledgement.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Former migration team owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1635: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2019-12-09 adapter note omitted expected_revision.


## INT-036

Operation title: Claim appeal and reopening. Feature contract: [Claim appeal and reopening](functional-specification.md#feature-f-036-claim-appeal-and-reopening).
Draft route: `POST /synthetic/v0/claims/claim-appeal-and-reopening`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the appeal case at the start of closed → reopened.
Proposed action: Preserve the original decision and append the appeal reason.
Guard: Reopening does not reverse a payment automatically.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Operations team owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1636: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2020-01-10 adapter note omitted expected_revision.


## INT-037

Operation title: Payout authorization. Feature contract: [Payout authorization](functional-specification.md#feature-f-037-payout-authorization).
Draft route: `POST /synthetic/v0/payments/payout-authorization`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the payout instruction at the start of approved → authorized.
Proposed action: Allow one operations approver to authorize a payout.
Guard: Authorization applies only to the recorded amount revision.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Benefits stream owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1637: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2021-02-11 adapter note omitted expected_revision.


## INT-038

Operation title: Payout scheduling. Feature contract: [Payout scheduling](functional-specification.md#feature-f-038-payout-scheduling).
Draft route: `POST /synthetic/v0/payments/payout-scheduling`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the scheduled payout at the start of authorized → scheduled.
Proposed action: Assign a fictional processing window rather than a bank promise.
Guard: An unavailable window leaves the instruction queued.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: TBD owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1638: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2022-03-12 adapter note omitted expected_revision.


## INT-039

Operation title: Payout release. Feature contract: [Payout release](functional-specification.md#feature-f-039-payout-release).
Draft route: `POST /synthetic/v0/payments/payout-release`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the release instruction at the start of scheduled → released.
Proposed action: Require two distinct approver roles before any payout release.
Guard: A changed amount cancels prior approvals.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Platform support owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1639: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2023-04-13 adapter note omitted expected_revision.


## INT-040

Operation title: Payment return processing. Feature contract: [Payment return processing](functional-specification.md#feature-f-040-payment-return-processing).
Draft route: `POST /synthetic/v0/payments/payment-return-processing`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the return notice at the start of released → returned.
Proposed action: A return opens a reconciliation item before any retry.
Guard: Never infer beneficiary identity from a return message.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Reporting stream owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1640: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2024-05-14 adapter note omitted expected_revision.


## INT-041

Operation title: Payment reconciliation. Feature contract: [Payment reconciliation](functional-specification.md#feature-f-041-payment-reconciliation).
Draft route: `POST /synthetic/v0/payments/payment-reconciliation`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the settlement match at the start of unmatched → reconciled.
Proposed action: Match both the instruction reference and synthetic amount.
Guard: A many-to-one match requires an explicit grouping record.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Former migration team owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1641: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2025-06-15 adapter note omitted expected_revision.


## INT-042

Operation title: Payment hold removal. Feature contract: [Payment hold removal](functional-specification.md#feature-f-042-payment-hold-removal).
Draft route: `POST /synthetic/v0/payments/payment-hold-removal`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the hold record at the start of held → released-for-review.
Proposed action: Resolve each active hold reason separately.
Guard: Removing a hold does not itself release money.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Operations team owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1642: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2019-07-16 adapter note omitted expected_revision.


## INT-043

Operation title: Document template selection. Feature contract: [Document template selection](functional-specification.md#feature-f-043-document-template-selection).
Draft route: `POST /synthetic/v0/documents/document-template-selection`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the template selection at the start of unselected → selected.
Proposed action: Choose the template revision effective for the synthetic document date.
Guard: An absent language variant blocks generation.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Benefits stream owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1643: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2020-08-17 adapter note omitted expected_revision.


## INT-044

Operation title: Statement generation. Feature contract: [Statement generation](functional-specification.md#feature-f-044-statement-generation).
Draft route: `POST /synthetic/v0/documents/statement-generation`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the statement job at the start of queued → rendered.
Proposed action: Render accepted amounts from one explicit ledger snapshot.
Guard: A mixed snapshot must be rejected.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: TBD owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1644: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2021-09-18 adapter note omitted expected_revision.


## INT-045

Operation title: Document retention purge. Feature contract: [Document retention purge](functional-specification.md#feature-f-045-document-retention-purge).
Draft route: `POST /synthetic/v0/documents/document-retention-purge`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the document retention item at the start of expired → purged.
Proposed action: Purge the document bytes after the fictional retention window even when an audit hold exists.
Guard: Keep a tombstone describing the purge attempt.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Platform support owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1645: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2022-10-19 adapter note omitted expected_revision.


## INT-046

Operation title: Document replacement. Feature contract: [Document replacement](functional-specification.md#feature-f-046-document-replacement).
Draft route: `POST /synthetic/v0/documents/document-replacement`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the replacement document at the start of issued → superseded.
Proposed action: Issue a replacement with a new revision reference.
Guard: The superseded item stays visible to reviewers.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Reporting stream owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1646: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2023-11-20 adapter note omitted expected_revision.


## INT-047

Operation title: Document delivery receipt. Feature contract: [Document delivery receipt](functional-specification.md#feature-f-047-document-delivery-receipt).
Draft route: `POST /synthetic/v0/documents/document-delivery-receipt`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the delivery receipt at the start of sent → acknowledged.
Proposed action: Distinguish transport acceptance from recipient acknowledgement.
Guard: A bounced receipt reopens delivery work.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Former migration team owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1647: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2024-12-21 adapter note omitted expected_revision.


## INT-048

Operation title: Document language selection. Feature contract: [Document language selection](functional-specification.md#feature-f-048-document-language-selection).
Draft route: `POST /synthetic/v0/documents/document-language-selection`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the language preference at the start of unset → selected.
Proposed action: Use a configured language code without inferring nationality.
Guard: A missing preference uses the plan review queue.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Operations team owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1648: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2025-01-22 adapter note omitted expected_revision.


## INT-049

Operation title: Notification preference update. Feature contract: [Notification preference update](functional-specification.md#feature-f-049-notification-preference-update).
Draft route: `POST /synthetic/v0/notifications/notification-preference-update`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the channel preference at the start of default → explicit.
Proposed action: Apply preference changes to unsent messages only.
Guard: Mandatory-message classification is an unvalidated placeholder.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Benefits stream owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1649: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2019-02-23 adapter note omitted expected_revision.


## INT-050

Operation title: Eligibility notification. Feature contract: [Eligibility notification](functional-specification.md#feature-f-050-eligibility-notification).
Draft route: `POST /synthetic/v0/notifications/eligibility-notification`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the eligibility message at the start of prepared → queued.
Proposed action: Reference the decision revision shown in the portal.
Guard: A reversed decision requires a new message record.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: TBD owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1650: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2020-03-24 adapter note omitted expected_revision.


## INT-051

Operation title: Contribution reminder. Feature contract: [Contribution reminder](functional-specification.md#feature-f-051-contribution-reminder).
Draft route: `POST /synthetic/v0/notifications/contribution-reminder`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the reminder candidate at the start of overdue → queued.
Proposed action: Check the current dispute flag before constructing the reminder.
Guard: Do not combine distinct employer accounts in one message.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Platform support owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1651: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2021-04-25 adapter note omitted expected_revision.


## INT-052

Operation title: Claim status notification. Feature contract: [Claim status notification](functional-specification.md#feature-f-052-claim-status-notification).
Draft route: `POST /synthetic/v0/notifications/claim-status-notification`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the claim message at the start of changed → queued.
Proposed action: Expose only the approved display status.
Guard: Internal reviewer comments must not enter the template.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Reporting stream owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1652: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2022-05-26 adapter note omitted expected_revision.


## INT-053

Operation title: Notification retry. Feature contract: [Notification retry](functional-specification.md#feature-f-053-notification-retry).
Draft route: `POST /synthetic/v0/notifications/notification-retry`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the retry item at the start of failed → requeued.
Proposed action: Reuse the logical message key while creating a new attempt.
Guard: An unknown delivery result needs reconciliation before retry.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Former migration team owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1653: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2023-06-27 adapter note omitted expected_revision.


## INT-054

Operation title: Notification suppression. Feature contract: [Notification suppression](functional-specification.md#feature-f-054-notification-suppression).
Draft route: `POST /synthetic/v0/notifications/notification-suppression`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the suppression window at the start of enabled → suppressed.
Proposed action: Record the reason and expiry of the suppression.
Guard: An expired suppression does not resend historical messages.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Operations team owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1654: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2024-07-01 adapter note omitted expected_revision.


## INT-055

Operation title: Employer coverage report. Feature contract: [Employer coverage report](functional-specification.md#feature-f-055-employer-coverage-report).
Draft route: `POST /synthetic/v0/reporting/employer-coverage-report`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the coverage report at the start of requested → generated.
Proposed action: Bind the extract to an explicit as-of date.
Guard: Late corrections require a new report revision.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Benefits stream owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1655: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2025-08-02 adapter note omitted expected_revision.


## INT-056

Operation title: Contribution exception report. Feature contract: [Contribution exception report](functional-specification.md#feature-f-056-contribution-exception-report).
Draft route: `POST /synthetic/v0/reporting/contribution-exception-report`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the exception report at the start of open → exported.
Proposed action: Separate rejected rows from accepted rows with warnings.
Guard: An empty report still records its selection parameters.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: TBD owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1656: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2019-09-03 adapter note omitted expected_revision.


## INT-057

Operation title: Claim ageing report. Feature contract: [Claim ageing report](functional-specification.md#feature-f-057-claim-ageing-report).
Draft route: `POST /synthetic/v0/reporting/claim-ageing-report`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the ageing report at the start of selected → generated.
Proposed action: Measure queue duration from the latest triage start.
Guard: Appeals need a separate ageing basis.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Platform support owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1657: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2020-10-04 adapter note omitted expected_revision.


## INT-058

Operation title: Branch 21 label review. Feature contract: [Branch 21 label review](functional-specification.md#feature-f-058-branch-21-label-review).
Draft route: `POST /synthetic/v0/reporting/branch-21-label-review`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the branch label review at the start of unclassified → pending-validation.
Proposed action: Treat Branch 21 as an unvalidated catalogue label only.
Guard: Do not infer guarantees or eligibility from the label.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Reporting stream owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1658: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2021-11-05 adapter note omitted expected_revision.


## INT-059

Operation title: Branch 23 label review. Feature contract: [Branch 23 label review](functional-specification.md#feature-f-059-branch-23-label-review).
Draft route: `POST /synthetic/v0/reporting/branch-23-label-review`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the branch label review at the start of unclassified → pending-validation.
Proposed action: Treat Branch 23 as an unvalidated catalogue label only.
Guard: Do not infer investment rules or disclosures from the label.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Former migration team owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1659: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2022-12-06 adapter note omitted expected_revision.


## INT-060

Operation title: Sigedis reporting placeholder. Feature contract: [Sigedis reporting placeholder](functional-specification.md#feature-f-060-sigedis-reporting-placeholder).
Draft route: `POST /synthetic/v0/reporting/sigedis-reporting-placeholder`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the report envelope at the start of draft → validation-required.
Proposed action: Disable external transmission until an approved mapping exists.
Guard: No official schema or reporting deadline is supplied here.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Operations team owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1660: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2023-01-07 adapter note omitted expected_revision.


## INT-061

Operation title: User role assignment. Feature contract: [User role assignment](functional-specification.md#feature-f-061-user-role-assignment).
Draft route: `POST /synthetic/v0/administration/user-role-assignment`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the role grant at the start of requested → granted.
Proposed action: Scope a grant to one employer or an explicit support scope.
Guard: A scope omission must not mean all employers.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Benefits stream owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1661: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2024-02-08 adapter note omitted expected_revision.


## INT-062

Operation title: Permission override. Feature contract: [Permission override](functional-specification.md#feature-f-062-permission-override).
Draft route: `POST /synthetic/v0/administration/permission-override`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the override request at the start of denied → temporarily-allowed.
Proposed action: Record a reason and expiry for the override.
Guard: An expired override cannot be inherited by a batch job.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: TBD owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1662: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2025-03-09 adapter note omitted expected_revision.


## INT-063

Operation title: Reference code maintenance. Feature contract: [Reference code maintenance](functional-specification.md#feature-f-063-reference-code-maintenance).
Draft route: `POST /synthetic/v0/administration/reference-code-maintenance`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the reference code at the start of proposed → active.
Proposed action: Version changes to code meaning.
Guard: A retired code remains readable on historical records.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Platform support owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1663: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2019-04-10 adapter note omitted expected_revision.


## INT-064

Operation title: Plan configuration publishing. Feature contract: [Plan configuration publishing](functional-specification.md#feature-f-064-plan-configuration-publishing).
Draft route: `POST /synthetic/v0/administration/plan-configuration-publishing`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the plan revision at the start of draft → published.
Proposed action: Publish a complete reviewed revision as one unit.
Guard: A partial revision remains unavailable to calculation.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Reporting stream owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1664: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2020-05-11 adapter note omitted expected_revision.


## INT-065

Operation title: Operational task reassignment. Feature contract: [Operational task reassignment](functional-specification.md#feature-f-065-operational-task-reassignment).
Draft route: `POST /synthetic/v0/administration/operational-task-reassignment`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the task assignment at the start of queued → reassigned.
Proposed action: Transfer ownership without resetting queue age.
Guard: An unavailable team leaves the task unassigned.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Former migration team owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1665: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2021-06-12 adapter note omitted expected_revision.


## INT-066

Operation title: Tenant boundary review. Feature contract: [Tenant boundary review](functional-specification.md#feature-f-066-tenant-boundary-review).
Draft route: `POST /synthetic/v0/administration/tenant-boundary-review`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the tenant scope at the start of unchecked → reviewed.
Proposed action: Require explicit synthetic tenant context on every record lookup.
Guard: A missing context produces a denial rather than a fallback.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Operations team owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1666: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2022-07-13 adapter note omitted expected_revision.


## INT-067

Operation title: Audit event capture. Feature contract: [Audit event capture](functional-specification.md#feature-f-067-audit-event-capture).
Draft route: `POST /synthetic/v0/audit/audit-event-capture`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the audit envelope at the start of observed → appended.
Proposed action: Append a new event for a changed business decision.
Guard: An audit write failure must be visible to the caller.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Benefits stream owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1667: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2023-08-14 adapter note omitted expected_revision.


## INT-068

Operation title: Audit hold preservation. Feature contract: [Audit hold preservation](functional-specification.md#feature-f-068-audit-hold-preservation).
Draft route: `POST /synthetic/v0/audit/audit-hold-preservation`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the audit hold at the start of requested → applied.
Proposed action: Preserve document bytes while an audit hold exists even after the retention window.
Guard: An unresolved hold has no automatic expiry.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: TBD owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1668: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2024-09-15 adapter note omitted expected_revision.


## INT-069

Operation title: Audit event search. Feature contract: [Audit event search](functional-specification.md#feature-f-069-audit-event-search).
Draft route: `POST /synthetic/v0/audit/audit-event-search`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the audit query at the start of requested → executed.
Proposed action: Filter by tenant scope before applying time filters.
Guard: An empty result must not reveal another tenant exists.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Platform support owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1669: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2025-10-16 adapter note omitted expected_revision.


## INT-070

Operation title: Audit export approval. Feature contract: [Audit export approval](functional-specification.md#feature-f-070-audit-export-approval).
Draft route: `POST /synthetic/v0/audit/audit-export-approval`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the audit export request at the start of requested → approved.
Proposed action: Bind approval to the selected fields and time interval.
Guard: Changing the interval invalidates export approval.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Reporting stream owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1670: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2019-11-17 adapter note omitted expected_revision.


## INT-071

Operation title: Historical correction trace. Feature contract: [Historical correction trace](functional-specification.md#feature-f-071-historical-correction-trace).
Draft route: `POST /synthetic/v0/audit/historical-correction-trace`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the correction chain at the start of fragmented → linked.
Proposed action: Link each adjustment to its immediate predecessor.
Guard: Cycles require manual investigation.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Former migration team owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1671: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2020-12-18 adapter note omitted expected_revision.


## INT-072

Operation title: Archive replay review. Feature contract: [Archive replay review](functional-specification.md#feature-f-072-archive-replay-review).
Draft route: `POST /synthetic/v0/audit/archive-replay-review`.
Request envelope: `tenant_scope`, `fixture_key`, `logical_key`, `expected_revision`, `effective_on`, and a feature-specific payload placeholder.
Business input: the replay manifest at the start of prepared → reviewed.
Proposed action: Replay into an isolated synthetic namespace only.
Guard: Never replay an outbound delivery as a live delivery.
Success fragment: return 202 with an internal task reference; the retired interface returned 200 before the audit append completed.
Failure fragment: 409 for a known revision mismatch; 422 for a known input rejection; an unknown timeout remains pending until reconciled.
Replay fragment: identical logical key and payload returns the stored outcome; differing payload under the same key enters discrepancy handling.
Permission fragment: Operations team owns the review queue, but that ownership is not an access grant.
Open question BENEFITS-1672: should this operation wait for the queue write, the ledger write, or the audit append?
Possibly obsolete: the 2021-01-19 adapter note omitted expected_revision.

## Batch jobs and file-import scraps

No actual files are supplied. All named formats below are invented and suitable only for fixture parsing experiments.
A file can be accepted as an envelope while individual rows remain rejected; the retired monitor used one status for both levels.

| Job ID | Input label | Draft schedule | Work | Recovery gap | Feature |
| --- | --- | --- | --- | --- | --- |
| JOB-001 | SYNTH_F_001_staging.csv | Nightly after fictional close | Stage policy; effective date must equal the recorded approval date | Checkpoint excludes rejected rows | [Policy creation](functional-specification.md#feature-f-001-policy-creation) |
| JOB-002 | SYNTH_F_002_staging.csv | On demand | Stage policy revision; a revision may take effect before its approval date | Envelope count and row count disagree | [Policy amendment](functional-specification.md#feature-f-002-policy-amendment) |
| JOB-003 | SYNTH_F_003_staging.csv | Retry window unspecified | Stage renewal instruction; create a new coverage period without silently copying unresolved exclusions | Retry does not define config version | [Policy renewal](functional-specification.md#feature-f-003-policy-renewal) |
| JOB-004 | SYNTH_F_004_staging.csv | Second workday of fictional period | Stage suspension window; freeze new collection instructions inside the suspension window | Missing trailer leaves job pending | [Policy suspension](functional-specification.md#feature-f-004-policy-suspension) |
| JOB-005 | SYNTH_F_005_staging.csv | Nightly after fictional close | Stage cancellation request; require a cancellation reason before the nightly close | Checkpoint excludes rejected rows | [Policy cancellation](functional-specification.md#feature-f-005-policy-cancellation) |
| JOB-006 | SYNTH_F_006_staging.csv | On demand | Stage reinstatement request; check whether the original accounting period is still open | Envelope count and row count disagree | [Policy reinstatement](functional-specification.md#feature-f-006-policy-reinstatement) |
| JOB-007 | SYNTH_F_007_staging.csv | Retry window unspecified | Stage employer shell; keep a shell employer separate from an enabled sponsor | Retry does not define config version | [Employer shell creation](functional-specification.md#feature-f-007-employer-shell-creation) |
| JOB-008 | SYNTH_F_008_staging.csv | Second workday of fictional period | Stage intake packet; classify each attachment before accepting the packet | Missing trailer leaves job pending | [Employer document intake](functional-specification.md#feature-f-008-employer-document-intake) |
| JOB-009 | SYNTH_F_009_staging.csv | Nightly after fictional close | Stage employer account; require operations review and a benefit package assignment | Checkpoint excludes rejected rows | [Employer activation](functional-specification.md#feature-f-009-employer-activation) |
| JOB-010 | SYNTH_F_010_staging.csv | On demand | Stage employer hierarchy; use an effective date for parent changes | Envelope count and row count disagree | [Employer hierarchy change](functional-specification.md#feature-f-010-employer-hierarchy-change) |
| JOB-011 | SYNTH_F_011_staging.csv | Retry window unspecified | Stage contact slot; store a synthetic role mailbox label rather than a named person | Retry does not define config version | [Employer contact maintenance](functional-specification.md#feature-f-011-employer-contact-maintenance) |
| JOB-012 | SYNTH_F_012_staging.csv | Second workday of fictional period | Stage offboarding case; stop new enrolments after the closing date | Missing trailer leaves job pending | [Employer offboarding](functional-specification.md#feature-f-012-employer-offboarding) |
| JOB-013 | SYNTH_F_013_staging.csv | Nightly after fictional close | Stage eligibility decision; evaluate eligibility using the member status on the payroll period end date | Checkpoint excludes rejected rows | [Employee eligibility assessment](functional-specification.md#feature-f-013-employee-eligibility-assessment) |
| JOB-014 | SYNTH_F_014_staging.csv | On demand | Stage waiting interval; count complete fictional plan months from the accepted start date | Envelope count and row count disagree | [Waiting period evaluation](functional-specification.md#feature-f-014-waiting-period-evaluation) |
| JOB-015 | SYNTH_F_015_staging.csv | Retry window unspecified | Stage category assignment; split coverage when a category changes during an open period | Retry does not define config version | [Employment category change](functional-specification.md#feature-f-015-employment-category-change) |
| JOB-016 | SYNTH_F_016_staging.csv | Second workday of fictional period | Stage absence interval; distinguish a missing payroll record from a declared absence | Missing trailer leaves job pending | [Leave and absence handling](functional-specification.md#feature-f-016-leave-and-absence-handling) |
| JOB-017 | SYNTH_F_017_staging.csv | Nightly after fictional close | Stage exit instruction; close future eligibility without erasing prior coverage | Checkpoint excludes rejected rows | [Member exit processing](functional-specification.md#feature-f-017-member-exit-processing) |
| JOB-018 | SYNTH_F_018_staging.csv | On demand | Stage re-entry case; match the synthetic member key before creating a new membership | Envelope count and row count disagree | [Member re-entry](functional-specification.md#feature-f-018-member-re-entry) |
| JOB-019 | SYNTH_F_019_staging.csv | Retry window unspecified | Stage contribution line; round each component before adding the period total | Retry does not define config version | [Contribution calculation](functional-specification.md#feature-f-019-contribution-calculation) |
| JOB-020 | SYNTH_F_020_staging.csv | Second workday of fictional period | Stage allocation instruction; allocate only to an open synthetic coverage account | Missing trailer leaves job pending | [Contribution allocation](functional-specification.md#feature-f-020-contribution-allocation) |
| JOB-021 | SYNTH_F_021_staging.csv | Nightly after fictional close | Stage arrears item; start ageing from the synthetic due date recorded on the item | Checkpoint excludes rejected rows | [Contribution arrears](functional-specification.md#feature-f-021-contribution-arrears) |
| JOB-022 | SYNTH_F_022_staging.csv | On demand | Stage payroll batch; evaluate eligibility using member status on the payroll file receipt date | Envelope count and row count disagree | [Payroll import](functional-specification.md#feature-f-022-payroll-import) |
| JOB-023 | SYNTH_F_023_staging.csv | Retry window unspecified | Stage correction delta; add unrounded components and round only the final period total | Retry does not define config version | [Contribution correction](functional-specification.md#feature-f-023-contribution-correction) |
| JOB-024 | SYNTH_F_024_staging.csv | Second workday of fictional period | Stage refund case; a credit balance alone does not authorize a refund | Missing trailer leaves job pending | [Contribution refund request](functional-specification.md#feature-f-024-contribution-refund-request) |
| JOB-025 | SYNTH_F_025_staging.csv | Nightly after fictional close | Stage designation set; the latest confirmed designation replaces all previous designations immediately | Checkpoint excludes rejected rows | [Beneficiary designation](functional-specification.md#feature-f-025-beneficiary-designation) |
| JOB-026 | SYNTH_F_026_staging.csv | On demand | Stage share set; require the synthetic share total to equal one hundred before confirmation | Envelope count and row count disagree | [Beneficiary share validation](functional-specification.md#feature-f-026-beneficiary-share-validation) |
| JOB-027 | SYNTH_F_027_staging.csv | Retry window unspecified | Stage evidence checklist; evidence completeness is a workflow flag only | Retry does not define config version | [Beneficiary evidence review](functional-specification.md#feature-f-027-beneficiary-evidence-review) |
| JOB-028 | SYNTH_F_028_staging.csv | Second workday of fictional period | Stage retirement event; use the reported retirement date as an unvalidated event input | Missing trailer leaves job pending | [Retirement event registration](functional-specification.md#feature-f-028-retirement-event-registration) |
| JOB-029 | SYNTH_F_029_staging.csv | Nightly after fictional close | Stage death event; store reported event dates without declaring legal proof | Checkpoint excludes rejected rows | [Death event registration](functional-specification.md#feature-f-029-death-event-registration) |
| JOB-030 | SYNTH_F_030_staging.csv | On demand | Stage disability event; keep an assessment placeholder separate from benefit authorization | Envelope count and row count disagree | [Disability event registration](functional-specification.md#feature-f-030-disability-event-registration) |
| JOB-031 | SYNTH_F_031_staging.csv | Retry window unspecified | Stage claim shell; allow intake even when the coverage lookup is unresolved | Retry does not define config version | [Claim intake](functional-specification.md#feature-f-031-claim-intake) |
| JOB-032 | SYNTH_F_032_staging.csv | Second workday of fictional period | Stage claim checklist; record missing evidence as explicit checklist entries | Missing trailer leaves job pending | [Claim evidence checklist](functional-specification.md#feature-f-032-claim-evidence-checklist) |
| JOB-033 | SYNTH_F_033_staging.csv | Nightly after fictional close | Stage entitlement snapshot; use the designation confirmed at the reported event date even if replaced later | Checkpoint excludes rejected rows | [Death claim entitlement snapshot](functional-specification.md#feature-f-033-death-claim-entitlement-snapshot) |
| JOB-034 | SYNTH_F_034_staging.csv | On demand | Stage assessment task; require a recorded reviewer role before progressing the task | Envelope count and row count disagree | [Disability claim assessment](functional-specification.md#feature-f-034-disability-claim-assessment) |
| JOB-035 | SYNTH_F_035_staging.csv | Retry window unspecified | Stage quotation draft; separate indicative amounts from approved settlement amounts | Retry does not define config version | [Retirement claim quotation](functional-specification.md#feature-f-035-retirement-claim-quotation) |
| JOB-036 | SYNTH_F_036_staging.csv | Second workday of fictional period | Stage appeal case; preserve the original decision and append the appeal reason | Missing trailer leaves job pending | [Claim appeal and reopening](functional-specification.md#feature-f-036-claim-appeal-and-reopening) |
| JOB-037 | SYNTH_F_037_staging.csv | Nightly after fictional close | Stage payout instruction; allow one operations approver to authorize a payout | Checkpoint excludes rejected rows | [Payout authorization](functional-specification.md#feature-f-037-payout-authorization) |
| JOB-038 | SYNTH_F_038_staging.csv | On demand | Stage scheduled payout; assign a fictional processing window rather than a bank promise | Envelope count and row count disagree | [Payout scheduling](functional-specification.md#feature-f-038-payout-scheduling) |
| JOB-039 | SYNTH_F_039_staging.csv | Retry window unspecified | Stage release instruction; require two distinct approver roles before any payout release | Retry does not define config version | [Payout release](functional-specification.md#feature-f-039-payout-release) |
| JOB-040 | SYNTH_F_040_staging.csv | Second workday of fictional period | Stage return notice; a return opens a reconciliation item before any retry | Missing trailer leaves job pending | [Payment return processing](functional-specification.md#feature-f-040-payment-return-processing) |
| JOB-041 | SYNTH_F_041_staging.csv | Nightly after fictional close | Stage settlement match; match both the instruction reference and synthetic amount | Checkpoint excludes rejected rows | [Payment reconciliation](functional-specification.md#feature-f-041-payment-reconciliation) |
| JOB-042 | SYNTH_F_042_staging.csv | On demand | Stage hold record; resolve each active hold reason separately | Envelope count and row count disagree | [Payment hold removal](functional-specification.md#feature-f-042-payment-hold-removal) |
| JOB-043 | SYNTH_F_043_staging.csv | Retry window unspecified | Stage template selection; choose the template revision effective for the synthetic document date | Retry does not define config version | [Document template selection](functional-specification.md#feature-f-043-document-template-selection) |
| JOB-044 | SYNTH_F_044_staging.csv | Second workday of fictional period | Stage statement job; render accepted amounts from one explicit ledger snapshot | Missing trailer leaves job pending | [Statement generation](functional-specification.md#feature-f-044-statement-generation) |
| JOB-045 | SYNTH_F_045_staging.csv | Nightly after fictional close | Stage document retention item; purge the document bytes after the fictional retention window even when an audit hold exists | Checkpoint excludes rejected rows | [Document retention purge](functional-specification.md#feature-f-045-document-retention-purge) |
| JOB-046 | SYNTH_F_046_staging.csv | On demand | Stage replacement document; issue a replacement with a new revision reference | Envelope count and row count disagree | [Document replacement](functional-specification.md#feature-f-046-document-replacement) |
| JOB-047 | SYNTH_F_047_staging.csv | Retry window unspecified | Stage delivery receipt; distinguish transport acceptance from recipient acknowledgement | Retry does not define config version | [Document delivery receipt](functional-specification.md#feature-f-047-document-delivery-receipt) |
| JOB-048 | SYNTH_F_048_staging.csv | Second workday of fictional period | Stage language preference; use a configured language code without inferring nationality | Missing trailer leaves job pending | [Document language selection](functional-specification.md#feature-f-048-document-language-selection) |
| JOB-049 | SYNTH_F_049_staging.csv | Nightly after fictional close | Stage channel preference; apply preference changes to unsent messages only | Checkpoint excludes rejected rows | [Notification preference update](functional-specification.md#feature-f-049-notification-preference-update) |
| JOB-050 | SYNTH_F_050_staging.csv | On demand | Stage eligibility message; reference the decision revision shown in the portal | Envelope count and row count disagree | [Eligibility notification](functional-specification.md#feature-f-050-eligibility-notification) |
| JOB-051 | SYNTH_F_051_staging.csv | Retry window unspecified | Stage reminder candidate; check the current dispute flag before constructing the reminder | Retry does not define config version | [Contribution reminder](functional-specification.md#feature-f-051-contribution-reminder) |
| JOB-052 | SYNTH_F_052_staging.csv | Second workday of fictional period | Stage claim message; expose only the approved display status | Missing trailer leaves job pending | [Claim status notification](functional-specification.md#feature-f-052-claim-status-notification) |
| JOB-053 | SYNTH_F_053_staging.csv | Nightly after fictional close | Stage retry item; reuse the logical message key while creating a new attempt | Checkpoint excludes rejected rows | [Notification retry](functional-specification.md#feature-f-053-notification-retry) |
| JOB-054 | SYNTH_F_054_staging.csv | On demand | Stage suppression window; record the reason and expiry of the suppression | Envelope count and row count disagree | [Notification suppression](functional-specification.md#feature-f-054-notification-suppression) |
| JOB-055 | SYNTH_F_055_staging.csv | Retry window unspecified | Stage coverage report; bind the extract to an explicit as-of date | Retry does not define config version | [Employer coverage report](functional-specification.md#feature-f-055-employer-coverage-report) |
| JOB-056 | SYNTH_F_056_staging.csv | Second workday of fictional period | Stage exception report; separate rejected rows from accepted rows with warnings | Missing trailer leaves job pending | [Contribution exception report](functional-specification.md#feature-f-056-contribution-exception-report) |
| JOB-057 | SYNTH_F_057_staging.csv | Nightly after fictional close | Stage ageing report; measure queue duration from the latest triage start | Checkpoint excludes rejected rows | [Claim ageing report](functional-specification.md#feature-f-057-claim-ageing-report) |
| JOB-058 | SYNTH_F_058_staging.csv | On demand | Stage branch label review; treat branch 21 as an unvalidated catalogue label only | Envelope count and row count disagree | [Branch 21 label review](functional-specification.md#feature-f-058-branch-21-label-review) |
| JOB-059 | SYNTH_F_059_staging.csv | Retry window unspecified | Stage branch label review; treat branch 23 as an unvalidated catalogue label only | Retry does not define config version | [Branch 23 label review](functional-specification.md#feature-f-059-branch-23-label-review) |
| JOB-060 | SYNTH_F_060_staging.csv | Second workday of fictional period | Stage report envelope; disable external transmission until an approved mapping exists | Missing trailer leaves job pending | [Sigedis reporting placeholder](functional-specification.md#feature-f-060-sigedis-reporting-placeholder) |
| JOB-061 | SYNTH_F_061_staging.csv | Nightly after fictional close | Stage role grant; scope a grant to one employer or an explicit support scope | Checkpoint excludes rejected rows | [User role assignment](functional-specification.md#feature-f-061-user-role-assignment) |
| JOB-062 | SYNTH_F_062_staging.csv | On demand | Stage override request; record a reason and expiry for the override | Envelope count and row count disagree | [Permission override](functional-specification.md#feature-f-062-permission-override) |
| JOB-063 | SYNTH_F_063_staging.csv | Retry window unspecified | Stage reference code; version changes to code meaning | Retry does not define config version | [Reference code maintenance](functional-specification.md#feature-f-063-reference-code-maintenance) |
| JOB-064 | SYNTH_F_064_staging.csv | Second workday of fictional period | Stage plan revision; publish a complete reviewed revision as one unit | Missing trailer leaves job pending | [Plan configuration publishing](functional-specification.md#feature-f-064-plan-configuration-publishing) |
| JOB-065 | SYNTH_F_065_staging.csv | Nightly after fictional close | Stage task assignment; transfer ownership without resetting queue age | Checkpoint excludes rejected rows | [Operational task reassignment](functional-specification.md#feature-f-065-operational-task-reassignment) |
| JOB-066 | SYNTH_F_066_staging.csv | On demand | Stage tenant scope; require explicit synthetic tenant context on every record lookup | Envelope count and row count disagree | [Tenant boundary review](functional-specification.md#feature-f-066-tenant-boundary-review) |
| JOB-067 | SYNTH_F_067_staging.csv | Retry window unspecified | Stage audit envelope; append a new event for a changed business decision | Retry does not define config version | [Audit event capture](functional-specification.md#feature-f-067-audit-event-capture) |
| JOB-068 | SYNTH_F_068_staging.csv | Second workday of fictional period | Stage audit hold; preserve document bytes while an audit hold exists even after the retention window | Missing trailer leaves job pending | [Audit hold preservation](functional-specification.md#feature-f-068-audit-hold-preservation) |
| JOB-069 | SYNTH_F_069_staging.csv | Nightly after fictional close | Stage audit query; filter by tenant scope before applying time filters | Checkpoint excludes rejected rows | [Audit event search](functional-specification.md#feature-f-069-audit-event-search) |
| JOB-070 | SYNTH_F_070_staging.csv | On demand | Stage audit export request; bind approval to the selected fields and time interval | Envelope count and row count disagree | [Audit export approval](functional-specification.md#feature-f-070-audit-export-approval) |
| JOB-071 | SYNTH_F_071_staging.csv | Retry window unspecified | Stage correction chain; link each adjustment to its immediate predecessor | Retry does not define config version | [Historical correction trace](functional-specification.md#feature-f-071-historical-correction-trace) |
| JOB-072 | SYNTH_F_072_staging.csv | Second workday of fictional period | Stage replay manifest; replay into an isolated synthetic namespace only | Missing trailer leaves job pending | [Archive replay review](functional-specification.md#feature-f-072-archive-replay-review) |

### Payroll file layout fragments

| Position | Field | Draft validation | Legacy uncertainty |
| --- | --- | --- | --- |
| 1 | fixture_key | Preserve a quoted empty string | Header spelling differs by export revision |
| 2 | tenant_scope | Reject mismatched tenant scope | Possibly obsolete |
| 3 | revision_no | Require explicit decimal scale | Column may have moved after the trailer redesign |
| 4 | state_code | Do not guess the business period | Header spelling differs by export revision |
| 5 | effective_on | Preserve a quoted empty string | Possibly obsolete |
| 6 | recorded_at | Reject mismatched tenant scope | Column may have moved after the trailer redesign |
| 7 | source_ref | Require explicit decimal scale | Header spelling differs by export revision |
| 8 | previous_ref | Do not guess the business period | Possibly obsolete |
| 9 | owner_queue | Preserve a quoted empty string | Column may have moved after the trailer redesign |
| 10 | review_status | Reject mismatched tenant scope | Header spelling differs by export revision |
| 11 | reason_code | Require explicit decimal scale | Possibly obsolete |
| 12 | display_label | Do not guess the business period | Column may have moved after the trailer redesign |
| 13 | import_batch_ref | Preserve a quoted empty string | Header spelling differs by export revision |
| 14 | control_total | Reject mismatched tenant scope | Possibly obsolete |
| 15 | is_deleted | Require explicit decimal scale | Column may have moved after the trailer redesign |
| 16 | hold_ref | Do not guess the business period | Header spelling differs by export revision |
| 17 | configuration_ref | Preserve a quoted empty string | Possibly obsolete |
| 18 | correlation_ref | Reject mismatched tenant scope | Column may have moved after the trailer redesign |
| 19 | legacy_status | Require explicit decimal scale | Header spelling differs by export revision |
| 20 | notes_state | Do not guess the business period | Possibly obsolete |
| 21 | member_ref | Preserve a quoted empty string | Column may have moved after the trailer redesign |
| 22 | period_start | Reject mismatched tenant scope | Header spelling differs by export revision |
| 23 | period_end | Require explicit decimal scale | Possibly obsolete |
| 24 | basis_amount | Do not guess the business period | Column may have moved after the trailer redesign |
| 25 | rate_ref | Preserve a quoted empty string | Header spelling differs by export revision |
| 26 | component_amount | Reject mismatched tenant scope | Possibly obsolete |
| 27 | rounded_amount | Require explicit decimal scale | Column may have moved after the trailer redesign |
| 28 | allocation_ref | Do not guess the business period | Header spelling differs by export revision |
| 29 | correction_of | Preserve a quoted empty string | Possibly obsolete |
| 30 | arrears_state | Reject mismatched tenant scope | Column may have moved after the trailer redesign |
| 31 | credit_amount | Require explicit decimal scale | Header spelling differs by export revision |
| 32 | refund_ref | Do not guess the business period | Possibly obsolete |
| 33 | supplemental_fixture_key | Preserve a quoted empty string | Column may have moved after the trailer redesign |
| 34 | supplemental_tenant_scope | Reject mismatched tenant scope | Header spelling differs by export revision |
| 35 | supplemental_revision_no | Require explicit decimal scale | Possibly obsolete |
| 36 | supplemental_state_code | Do not guess the business period | Column may have moved after the trailer redesign |
| 37 | supplemental_effective_on | Preserve a quoted empty string | Header spelling differs by export revision |
| 38 | supplemental_recorded_at | Reject mismatched tenant scope | Possibly obsolete |
| 39 | supplemental_source_ref | Require explicit decimal scale | Column may have moved after the trailer redesign |
| 40 | supplemental_previous_ref | Do not guess the business period | Header spelling differs by export revision |
| 41 | supplemental_owner_queue | Preserve a quoted empty string | Possibly obsolete |
| 42 | supplemental_review_status | Reject mismatched tenant scope | Column may have moved after the trailer redesign |
| 43 | supplemental_reason_code | Require explicit decimal scale | Header spelling differs by export revision |
| 44 | supplemental_display_label | Do not guess the business period | Possibly obsolete |
| 45 | supplemental_import_batch_ref | Preserve a quoted empty string | Column may have moved after the trailer redesign |
| 46 | supplemental_control_total | Reject mismatched tenant scope | Header spelling differs by export revision |
| 47 | supplemental_is_deleted | Require explicit decimal scale | Possibly obsolete |
| 48 | supplemental_hold_ref | Do not guess the business period | Column may have moved after the trailer redesign |

### Import transaction diary

| Fragment | Stage | Preserved note |
| --- | --- | --- |
| BATCH-NOTE-001 | Received | Do not post any rows before the envelope control count is checked. |
| BATCH-NOTE-002 | Parsed | Old implementation note says valid rows may post before the trailer arrives. |
| BATCH-NOTE-003 | Validated | A rejected row remains addressable by its ordinal and envelope reference. |
| BATCH-NOTE-004 | Posted | A corrected file needs a new envelope key while retaining the replaced-envelope reference. |
| BATCH-NOTE-005 | Acknowledged | The report consumer may see partial posting; watermark semantics are missing. |
| BATCH-NOTE-006 | Received | Possibly obsolete: recovery was described as deleting the staging batch and starting again. |
| BATCH-NOTE-007 | Parsed | Do not post any rows before the envelope control count is checked. |
| BATCH-NOTE-008 | Validated | Old implementation note says valid rows may post before the trailer arrives. |
| BATCH-NOTE-009 | Posted | A rejected row remains addressable by its ordinal and envelope reference. |
| BATCH-NOTE-010 | Acknowledged | A corrected file needs a new envelope key while retaining the replaced-envelope reference. |
| BATCH-NOTE-011 | Received | The report consumer may see partial posting; watermark semantics are missing. |
| BATCH-NOTE-012 | Parsed | Possibly obsolete: recovery was described as deleting the staging batch and starting again. |
| BATCH-NOTE-013 | Validated | Do not post any rows before the envelope control count is checked. |
| BATCH-NOTE-014 | Posted | Old implementation note says valid rows may post before the trailer arrives. |
| BATCH-NOTE-015 | Acknowledged | A rejected row remains addressable by its ordinal and envelope reference. |
| BATCH-NOTE-016 | Received | A corrected file needs a new envelope key while retaining the replaced-envelope reference. |
| BATCH-NOTE-017 | Parsed | The report consumer may see partial posting; watermark semantics are missing. |
| BATCH-NOTE-018 | Validated | Possibly obsolete: recovery was described as deleting the staging batch and starting again. |
| BATCH-NOTE-019 | Posted | Do not post any rows before the envelope control count is checked. |
| BATCH-NOTE-020 | Acknowledged | Old implementation note says valid rows may post before the trailer arrives. |
| BATCH-NOTE-021 | Received | A rejected row remains addressable by its ordinal and envelope reference. |
| BATCH-NOTE-022 | Parsed | A corrected file needs a new envelope key while retaining the replaced-envelope reference. |
| BATCH-NOTE-023 | Validated | The report consumer may see partial posting; watermark semantics are missing. |
| BATCH-NOTE-024 | Posted | Possibly obsolete: recovery was described as deleting the staging batch and starting again. |
| BATCH-NOTE-025 | Acknowledged | Do not post any rows before the envelope control count is checked. |
| BATCH-NOTE-026 | Received | Old implementation note says valid rows may post before the trailer arrives. |
| BATCH-NOTE-027 | Parsed | A rejected row remains addressable by its ordinal and envelope reference. |
| BATCH-NOTE-028 | Validated | A corrected file needs a new envelope key while retaining the replaced-envelope reference. |
| BATCH-NOTE-029 | Posted | The report consumer may see partial posting; watermark semantics are missing. |
| BATCH-NOTE-030 | Acknowledged | Possibly obsolete: recovery was described as deleting the staging batch and starting again. |
| BATCH-NOTE-031 | Received | Do not post any rows before the envelope control count is checked. |
| BATCH-NOTE-032 | Parsed | Old implementation note says valid rows may post before the trailer arrives. |
| BATCH-NOTE-033 | Validated | A rejected row remains addressable by its ordinal and envelope reference. |
| BATCH-NOTE-034 | Posted | A corrected file needs a new envelope key while retaining the replaced-envelope reference. |
| BATCH-NOTE-035 | Acknowledged | The report consumer may see partial posting; watermark semantics are missing. |
| BATCH-NOTE-036 | Received | Possibly obsolete: recovery was described as deleting the staging batch and starting again. |
| BATCH-NOTE-037 | Parsed | Do not post any rows before the envelope control count is checked. |
| BATCH-NOTE-038 | Validated | Old implementation note says valid rows may post before the trailer arrives. |
| BATCH-NOTE-039 | Posted | A rejected row remains addressable by its ordinal and envelope reference. |
| BATCH-NOTE-040 | Acknowledged | A corrected file needs a new envelope key while retaining the replaced-envelope reference. |
| BATCH-NOTE-041 | Received | The report consumer may see partial posting; watermark semantics are missing. |
| BATCH-NOTE-042 | Parsed | Possibly obsolete: recovery was described as deleting the staging batch and starting again. |
| BATCH-NOTE-043 | Validated | Do not post any rows before the envelope control count is checked. |
| BATCH-NOTE-044 | Posted | Old implementation note says valid rows may post before the trailer arrives. |
| BATCH-NOTE-045 | Acknowledged | A rejected row remains addressable by its ordinal and envelope reference. |
| BATCH-NOTE-046 | Received | A corrected file needs a new envelope key while retaining the replaced-envelope reference. |
| BATCH-NOTE-047 | Parsed | The report consumer may see partial posting; watermark semantics are missing. |
| BATCH-NOTE-048 | Validated | Possibly obsolete: recovery was described as deleting the staging batch and starting again. |
| BATCH-NOTE-049 | Posted | Do not post any rows before the envelope control count is checked. |
| BATCH-NOTE-050 | Acknowledged | Old implementation note says valid rows may post before the trailer arrives. |
| BATCH-NOTE-051 | Received | A rejected row remains addressable by its ordinal and envelope reference. |
| BATCH-NOTE-052 | Parsed | A corrected file needs a new envelope key while retaining the replaced-envelope reference. |
| BATCH-NOTE-053 | Validated | The report consumer may see partial posting; watermark semantics are missing. |
| BATCH-NOTE-054 | Posted | Possibly obsolete: recovery was described as deleting the staging batch and starting again. |
| BATCH-NOTE-055 | Acknowledged | Do not post any rows before the envelope control count is checked. |
| BATCH-NOTE-056 | Received | Old implementation note says valid rows may post before the trailer arrives. |
| BATCH-NOTE-057 | Parsed | A rejected row remains addressable by its ordinal and envelope reference. |
| BATCH-NOTE-058 | Validated | A corrected file needs a new envelope key while retaining the replaced-envelope reference. |
| BATCH-NOTE-059 | Posted | The report consumer may see partial posting; watermark semantics are missing. |
| BATCH-NOTE-060 | Acknowledged | Possibly obsolete: recovery was described as deleting the staging batch and starting again. |

## Error-code notebook

Each error family has intentionally inconsistent retry advice. No production compatibility is implied.

| Error ID | Feature context | Condition | Draft response | Retry fragment | Owner |
| --- | --- | --- | --- | --- | --- |
| ERR-001 | [Policy creation](functional-specification.md#feature-f-001-policy-creation) | Input revision no longer matches the policy | 409 / review required | Never blind-retry | Operations team |
| ERR-002 | [Policy amendment](functional-specification.md#feature-f-002-policy-amendment) | Input revision no longer matches the policy revision | 409 / review required | Old note says retry three times | Benefits stream |
| ERR-003 | [Policy renewal](functional-specification.md#feature-f-003-policy-renewal) | Input revision no longer matches the renewal instruction | 409 / review required | Only replay the same logical key | TBD |
| ERR-004 | [Policy suspension](functional-specification.md#feature-f-004-policy-suspension) | Input revision no longer matches the suspension window | 409 / review required | TBD after reconciliation | Platform support |
| ERR-005 | [Policy cancellation](functional-specification.md#feature-f-005-policy-cancellation) | Input revision no longer matches the cancellation request | 409 / review required | Never blind-retry | Reporting stream |
| ERR-006 | [Policy reinstatement](functional-specification.md#feature-f-006-policy-reinstatement) | Input revision no longer matches the reinstatement request | 409 / review required | Old note says retry three times | Former migration team |
| ERR-007 | [Employer shell creation](functional-specification.md#feature-f-007-employer-shell-creation) | Input revision no longer matches the employer shell | 409 / review required | Only replay the same logical key | Operations team |
| ERR-008 | [Employer document intake](functional-specification.md#feature-f-008-employer-document-intake) | Input revision no longer matches the intake packet | 409 / review required | TBD after reconciliation | Benefits stream |
| ERR-009 | [Employer activation](functional-specification.md#feature-f-009-employer-activation) | Input revision no longer matches the employer account | 409 / review required | Never blind-retry | TBD |
| ERR-010 | [Employer hierarchy change](functional-specification.md#feature-f-010-employer-hierarchy-change) | Input revision no longer matches the employer hierarchy | 409 / review required | Old note says retry three times | Platform support |
| ERR-011 | [Employer contact maintenance](functional-specification.md#feature-f-011-employer-contact-maintenance) | Input revision no longer matches the contact slot | 409 / review required | Only replay the same logical key | Reporting stream |
| ERR-012 | [Employer offboarding](functional-specification.md#feature-f-012-employer-offboarding) | Input revision no longer matches the offboarding case | 409 / review required | TBD after reconciliation | Former migration team |
| ERR-013 | [Employee eligibility assessment](functional-specification.md#feature-f-013-employee-eligibility-assessment) | Input revision no longer matches the eligibility decision | 409 / review required | Never blind-retry | Operations team |
| ERR-014 | [Waiting period evaluation](functional-specification.md#feature-f-014-waiting-period-evaluation) | Input revision no longer matches the waiting interval | 409 / review required | Old note says retry three times | Benefits stream |
| ERR-015 | [Employment category change](functional-specification.md#feature-f-015-employment-category-change) | Input revision no longer matches the category assignment | 409 / review required | Only replay the same logical key | TBD |
| ERR-016 | [Leave and absence handling](functional-specification.md#feature-f-016-leave-and-absence-handling) | Input revision no longer matches the absence interval | 409 / review required | TBD after reconciliation | Platform support |
| ERR-017 | [Member exit processing](functional-specification.md#feature-f-017-member-exit-processing) | Input revision no longer matches the exit instruction | 409 / review required | Never blind-retry | Reporting stream |
| ERR-018 | [Member re-entry](functional-specification.md#feature-f-018-member-re-entry) | Input revision no longer matches the re-entry case | 409 / review required | Old note says retry three times | Former migration team |
| ERR-019 | [Contribution calculation](functional-specification.md#feature-f-019-contribution-calculation) | Input revision no longer matches the contribution line | 409 / review required | Only replay the same logical key | Operations team |
| ERR-020 | [Contribution allocation](functional-specification.md#feature-f-020-contribution-allocation) | Input revision no longer matches the allocation instruction | 409 / review required | TBD after reconciliation | Benefits stream |
| ERR-021 | [Contribution arrears](functional-specification.md#feature-f-021-contribution-arrears) | Input revision no longer matches the arrears item | 409 / review required | Never blind-retry | TBD |
| ERR-022 | [Payroll import](functional-specification.md#feature-f-022-payroll-import) | Input revision no longer matches the payroll batch | 409 / review required | Old note says retry three times | Platform support |
| ERR-023 | [Contribution correction](functional-specification.md#feature-f-023-contribution-correction) | Input revision no longer matches the correction delta | 409 / review required | Only replay the same logical key | Reporting stream |
| ERR-024 | [Contribution refund request](functional-specification.md#feature-f-024-contribution-refund-request) | Input revision no longer matches the refund case | 409 / review required | TBD after reconciliation | Former migration team |
| ERR-025 | [Beneficiary designation](functional-specification.md#feature-f-025-beneficiary-designation) | Input revision no longer matches the designation set | 409 / review required | Never blind-retry | Operations team |
| ERR-026 | [Beneficiary share validation](functional-specification.md#feature-f-026-beneficiary-share-validation) | Input revision no longer matches the share set | 409 / review required | Old note says retry three times | Benefits stream |
| ERR-027 | [Beneficiary evidence review](functional-specification.md#feature-f-027-beneficiary-evidence-review) | Input revision no longer matches the evidence checklist | 409 / review required | Only replay the same logical key | TBD |
| ERR-028 | [Retirement event registration](functional-specification.md#feature-f-028-retirement-event-registration) | Input revision no longer matches the retirement event | 409 / review required | TBD after reconciliation | Platform support |
| ERR-029 | [Death event registration](functional-specification.md#feature-f-029-death-event-registration) | Input revision no longer matches the death event | 409 / review required | Never blind-retry | Reporting stream |
| ERR-030 | [Disability event registration](functional-specification.md#feature-f-030-disability-event-registration) | Input revision no longer matches the disability event | 409 / review required | Old note says retry three times | Former migration team |
| ERR-031 | [Claim intake](functional-specification.md#feature-f-031-claim-intake) | Input revision no longer matches the claim shell | 409 / review required | Only replay the same logical key | Operations team |
| ERR-032 | [Claim evidence checklist](functional-specification.md#feature-f-032-claim-evidence-checklist) | Input revision no longer matches the claim checklist | 409 / review required | TBD after reconciliation | Benefits stream |
| ERR-033 | [Death claim entitlement snapshot](functional-specification.md#feature-f-033-death-claim-entitlement-snapshot) | Input revision no longer matches the entitlement snapshot | 409 / review required | Never blind-retry | TBD |
| ERR-034 | [Disability claim assessment](functional-specification.md#feature-f-034-disability-claim-assessment) | Input revision no longer matches the assessment task | 409 / review required | Old note says retry three times | Platform support |
| ERR-035 | [Retirement claim quotation](functional-specification.md#feature-f-035-retirement-claim-quotation) | Input revision no longer matches the quotation draft | 409 / review required | Only replay the same logical key | Reporting stream |
| ERR-036 | [Claim appeal and reopening](functional-specification.md#feature-f-036-claim-appeal-and-reopening) | Input revision no longer matches the appeal case | 409 / review required | TBD after reconciliation | Former migration team |
| ERR-037 | [Payout authorization](functional-specification.md#feature-f-037-payout-authorization) | Input revision no longer matches the payout instruction | 409 / review required | Never blind-retry | Operations team |
| ERR-038 | [Payout scheduling](functional-specification.md#feature-f-038-payout-scheduling) | Input revision no longer matches the scheduled payout | 409 / review required | Old note says retry three times | Benefits stream |
| ERR-039 | [Payout release](functional-specification.md#feature-f-039-payout-release) | Input revision no longer matches the release instruction | 409 / review required | Only replay the same logical key | TBD |
| ERR-040 | [Payment return processing](functional-specification.md#feature-f-040-payment-return-processing) | Input revision no longer matches the return notice | 409 / review required | TBD after reconciliation | Platform support |
| ERR-041 | [Payment reconciliation](functional-specification.md#feature-f-041-payment-reconciliation) | Input revision no longer matches the settlement match | 409 / review required | Never blind-retry | Reporting stream |
| ERR-042 | [Payment hold removal](functional-specification.md#feature-f-042-payment-hold-removal) | Input revision no longer matches the hold record | 409 / review required | Old note says retry three times | Former migration team |
| ERR-043 | [Document template selection](functional-specification.md#feature-f-043-document-template-selection) | Input revision no longer matches the template selection | 409 / review required | Only replay the same logical key | Operations team |
| ERR-044 | [Statement generation](functional-specification.md#feature-f-044-statement-generation) | Input revision no longer matches the statement job | 409 / review required | TBD after reconciliation | Benefits stream |
| ERR-045 | [Document retention purge](functional-specification.md#feature-f-045-document-retention-purge) | Input revision no longer matches the document retention item | 409 / review required | Never blind-retry | TBD |
| ERR-046 | [Document replacement](functional-specification.md#feature-f-046-document-replacement) | Input revision no longer matches the replacement document | 409 / review required | Old note says retry three times | Platform support |
| ERR-047 | [Document delivery receipt](functional-specification.md#feature-f-047-document-delivery-receipt) | Input revision no longer matches the delivery receipt | 409 / review required | Only replay the same logical key | Reporting stream |
| ERR-048 | [Document language selection](functional-specification.md#feature-f-048-document-language-selection) | Input revision no longer matches the language preference | 409 / review required | TBD after reconciliation | Former migration team |
| ERR-049 | [Notification preference update](functional-specification.md#feature-f-049-notification-preference-update) | Input revision no longer matches the channel preference | 409 / review required | Never blind-retry | Operations team |
| ERR-050 | [Eligibility notification](functional-specification.md#feature-f-050-eligibility-notification) | Input revision no longer matches the eligibility message | 409 / review required | Old note says retry three times | Benefits stream |
| ERR-051 | [Contribution reminder](functional-specification.md#feature-f-051-contribution-reminder) | Input revision no longer matches the reminder candidate | 409 / review required | Only replay the same logical key | TBD |
| ERR-052 | [Claim status notification](functional-specification.md#feature-f-052-claim-status-notification) | Input revision no longer matches the claim message | 409 / review required | TBD after reconciliation | Platform support |
| ERR-053 | [Notification retry](functional-specification.md#feature-f-053-notification-retry) | Input revision no longer matches the retry item | 409 / review required | Never blind-retry | Reporting stream |
| ERR-054 | [Notification suppression](functional-specification.md#feature-f-054-notification-suppression) | Input revision no longer matches the suppression window | 409 / review required | Old note says retry three times | Former migration team |
| ERR-055 | [Employer coverage report](functional-specification.md#feature-f-055-employer-coverage-report) | Input revision no longer matches the coverage report | 409 / review required | Only replay the same logical key | Operations team |
| ERR-056 | [Contribution exception report](functional-specification.md#feature-f-056-contribution-exception-report) | Input revision no longer matches the exception report | 409 / review required | TBD after reconciliation | Benefits stream |
| ERR-057 | [Claim ageing report](functional-specification.md#feature-f-057-claim-ageing-report) | Input revision no longer matches the ageing report | 409 / review required | Never blind-retry | TBD |
| ERR-058 | [Branch 21 label review](functional-specification.md#feature-f-058-branch-21-label-review) | Input revision no longer matches the branch label review | 409 / review required | Old note says retry three times | Platform support |
| ERR-059 | [Branch 23 label review](functional-specification.md#feature-f-059-branch-23-label-review) | Input revision no longer matches the branch label review | 409 / review required | Only replay the same logical key | Reporting stream |
| ERR-060 | [Sigedis reporting placeholder](functional-specification.md#feature-f-060-sigedis-reporting-placeholder) | Input revision no longer matches the report envelope | 409 / review required | TBD after reconciliation | Former migration team |
| ERR-061 | [User role assignment](functional-specification.md#feature-f-061-user-role-assignment) | Input revision no longer matches the role grant | 409 / review required | Never blind-retry | Operations team |
| ERR-062 | [Permission override](functional-specification.md#feature-f-062-permission-override) | Input revision no longer matches the override request | 409 / review required | Old note says retry three times | Benefits stream |
| ERR-063 | [Reference code maintenance](functional-specification.md#feature-f-063-reference-code-maintenance) | Input revision no longer matches the reference code | 409 / review required | Only replay the same logical key | TBD |
| ERR-064 | [Plan configuration publishing](functional-specification.md#feature-f-064-plan-configuration-publishing) | Input revision no longer matches the plan revision | 409 / review required | TBD after reconciliation | Platform support |
| ERR-065 | [Operational task reassignment](functional-specification.md#feature-f-065-operational-task-reassignment) | Input revision no longer matches the task assignment | 409 / review required | Never blind-retry | Reporting stream |
| ERR-066 | [Tenant boundary review](functional-specification.md#feature-f-066-tenant-boundary-review) | Input revision no longer matches the tenant scope | 409 / review required | Old note says retry three times | Former migration team |
| ERR-067 | [Audit event capture](functional-specification.md#feature-f-067-audit-event-capture) | Input revision no longer matches the audit envelope | 409 / review required | Only replay the same logical key | Operations team |
| ERR-068 | [Audit hold preservation](functional-specification.md#feature-f-068-audit-hold-preservation) | Input revision no longer matches the audit hold | 409 / review required | TBD after reconciliation | Benefits stream |
| ERR-069 | [Audit event search](functional-specification.md#feature-f-069-audit-event-search) | Input revision no longer matches the audit query | 409 / review required | Never blind-retry | TBD |
| ERR-070 | [Audit export approval](functional-specification.md#feature-f-070-audit-export-approval) | Input revision no longer matches the audit export request | 409 / review required | Old note says retry three times | Platform support |
| ERR-071 | [Historical correction trace](functional-specification.md#feature-f-071-historical-correction-trace) | Input revision no longer matches the correction chain | 409 / review required | Only replay the same logical key | Reporting stream |
| ERR-072 | [Archive replay review](functional-specification.md#feature-f-072-archive-replay-review) | Input revision no longer matches the replay manifest | 409 / review required | TBD after reconciliation | Former migration team |
| ERR-073 | [Policy creation](functional-specification.md#feature-f-001-policy-creation) | Acknowledgement missing after accepting the policy | 202 / reconciliation pending | Never blind-retry | Operations team |
| ERR-074 | [Policy amendment](functional-specification.md#feature-f-002-policy-amendment) | Acknowledgement missing after accepting the policy revision | 202 / reconciliation pending | Old note says retry three times | Benefits stream |
| ERR-075 | [Policy renewal](functional-specification.md#feature-f-003-policy-renewal) | Acknowledgement missing after accepting the renewal instruction | 202 / reconciliation pending | Only replay the same logical key | TBD |
| ERR-076 | [Policy suspension](functional-specification.md#feature-f-004-policy-suspension) | Acknowledgement missing after accepting the suspension window | 202 / reconciliation pending | TBD after reconciliation | Platform support |
| ERR-077 | [Policy cancellation](functional-specification.md#feature-f-005-policy-cancellation) | Acknowledgement missing after accepting the cancellation request | 202 / reconciliation pending | Never blind-retry | Reporting stream |
| ERR-078 | [Policy reinstatement](functional-specification.md#feature-f-006-policy-reinstatement) | Acknowledgement missing after accepting the reinstatement request | 202 / reconciliation pending | Old note says retry three times | Former migration team |
| ERR-079 | [Employer shell creation](functional-specification.md#feature-f-007-employer-shell-creation) | Acknowledgement missing after accepting the employer shell | 202 / reconciliation pending | Only replay the same logical key | Operations team |
| ERR-080 | [Employer document intake](functional-specification.md#feature-f-008-employer-document-intake) | Acknowledgement missing after accepting the intake packet | 202 / reconciliation pending | TBD after reconciliation | Benefits stream |
| ERR-081 | [Employer activation](functional-specification.md#feature-f-009-employer-activation) | Acknowledgement missing after accepting the employer account | 202 / reconciliation pending | Never blind-retry | TBD |
| ERR-082 | [Employer hierarchy change](functional-specification.md#feature-f-010-employer-hierarchy-change) | Acknowledgement missing after accepting the employer hierarchy | 202 / reconciliation pending | Old note says retry three times | Platform support |
| ERR-083 | [Employer contact maintenance](functional-specification.md#feature-f-011-employer-contact-maintenance) | Acknowledgement missing after accepting the contact slot | 202 / reconciliation pending | Only replay the same logical key | Reporting stream |
| ERR-084 | [Employer offboarding](functional-specification.md#feature-f-012-employer-offboarding) | Acknowledgement missing after accepting the offboarding case | 202 / reconciliation pending | TBD after reconciliation | Former migration team |
| ERR-085 | [Employee eligibility assessment](functional-specification.md#feature-f-013-employee-eligibility-assessment) | Acknowledgement missing after accepting the eligibility decision | 202 / reconciliation pending | Never blind-retry | Operations team |
| ERR-086 | [Waiting period evaluation](functional-specification.md#feature-f-014-waiting-period-evaluation) | Acknowledgement missing after accepting the waiting interval | 202 / reconciliation pending | Old note says retry three times | Benefits stream |
| ERR-087 | [Employment category change](functional-specification.md#feature-f-015-employment-category-change) | Acknowledgement missing after accepting the category assignment | 202 / reconciliation pending | Only replay the same logical key | TBD |
| ERR-088 | [Leave and absence handling](functional-specification.md#feature-f-016-leave-and-absence-handling) | Acknowledgement missing after accepting the absence interval | 202 / reconciliation pending | TBD after reconciliation | Platform support |
| ERR-089 | [Member exit processing](functional-specification.md#feature-f-017-member-exit-processing) | Acknowledgement missing after accepting the exit instruction | 202 / reconciliation pending | Never blind-retry | Reporting stream |
| ERR-090 | [Member re-entry](functional-specification.md#feature-f-018-member-re-entry) | Acknowledgement missing after accepting the re-entry case | 202 / reconciliation pending | Old note says retry three times | Former migration team |
| ERR-091 | [Contribution calculation](functional-specification.md#feature-f-019-contribution-calculation) | Acknowledgement missing after accepting the contribution line | 202 / reconciliation pending | Only replay the same logical key | Operations team |
| ERR-092 | [Contribution allocation](functional-specification.md#feature-f-020-contribution-allocation) | Acknowledgement missing after accepting the allocation instruction | 202 / reconciliation pending | TBD after reconciliation | Benefits stream |
| ERR-093 | [Contribution arrears](functional-specification.md#feature-f-021-contribution-arrears) | Acknowledgement missing after accepting the arrears item | 202 / reconciliation pending | Never blind-retry | TBD |
| ERR-094 | [Payroll import](functional-specification.md#feature-f-022-payroll-import) | Acknowledgement missing after accepting the payroll batch | 202 / reconciliation pending | Old note says retry three times | Platform support |
| ERR-095 | [Contribution correction](functional-specification.md#feature-f-023-contribution-correction) | Acknowledgement missing after accepting the correction delta | 202 / reconciliation pending | Only replay the same logical key | Reporting stream |
| ERR-096 | [Contribution refund request](functional-specification.md#feature-f-024-contribution-refund-request) | Acknowledgement missing after accepting the refund case | 202 / reconciliation pending | TBD after reconciliation | Former migration team |
| ERR-097 | [Beneficiary designation](functional-specification.md#feature-f-025-beneficiary-designation) | Acknowledgement missing after accepting the designation set | 202 / reconciliation pending | Never blind-retry | Operations team |
| ERR-098 | [Beneficiary share validation](functional-specification.md#feature-f-026-beneficiary-share-validation) | Acknowledgement missing after accepting the share set | 202 / reconciliation pending | Old note says retry three times | Benefits stream |
| ERR-099 | [Beneficiary evidence review](functional-specification.md#feature-f-027-beneficiary-evidence-review) | Acknowledgement missing after accepting the evidence checklist | 202 / reconciliation pending | Only replay the same logical key | TBD |
| ERR-100 | [Retirement event registration](functional-specification.md#feature-f-028-retirement-event-registration) | Acknowledgement missing after accepting the retirement event | 202 / reconciliation pending | TBD after reconciliation | Platform support |
| ERR-101 | [Death event registration](functional-specification.md#feature-f-029-death-event-registration) | Acknowledgement missing after accepting the death event | 202 / reconciliation pending | Never blind-retry | Reporting stream |
| ERR-102 | [Disability event registration](functional-specification.md#feature-f-030-disability-event-registration) | Acknowledgement missing after accepting the disability event | 202 / reconciliation pending | Old note says retry three times | Former migration team |
| ERR-103 | [Claim intake](functional-specification.md#feature-f-031-claim-intake) | Acknowledgement missing after accepting the claim shell | 202 / reconciliation pending | Only replay the same logical key | Operations team |
| ERR-104 | [Claim evidence checklist](functional-specification.md#feature-f-032-claim-evidence-checklist) | Acknowledgement missing after accepting the claim checklist | 202 / reconciliation pending | TBD after reconciliation | Benefits stream |
| ERR-105 | [Death claim entitlement snapshot](functional-specification.md#feature-f-033-death-claim-entitlement-snapshot) | Acknowledgement missing after accepting the entitlement snapshot | 202 / reconciliation pending | Never blind-retry | TBD |
| ERR-106 | [Disability claim assessment](functional-specification.md#feature-f-034-disability-claim-assessment) | Acknowledgement missing after accepting the assessment task | 202 / reconciliation pending | Old note says retry three times | Platform support |
| ERR-107 | [Retirement claim quotation](functional-specification.md#feature-f-035-retirement-claim-quotation) | Acknowledgement missing after accepting the quotation draft | 202 / reconciliation pending | Only replay the same logical key | Reporting stream |
| ERR-108 | [Claim appeal and reopening](functional-specification.md#feature-f-036-claim-appeal-and-reopening) | Acknowledgement missing after accepting the appeal case | 202 / reconciliation pending | TBD after reconciliation | Former migration team |
| ERR-109 | [Payout authorization](functional-specification.md#feature-f-037-payout-authorization) | Acknowledgement missing after accepting the payout instruction | 202 / reconciliation pending | Never blind-retry | Operations team |
| ERR-110 | [Payout scheduling](functional-specification.md#feature-f-038-payout-scheduling) | Acknowledgement missing after accepting the scheduled payout | 202 / reconciliation pending | Old note says retry three times | Benefits stream |
| ERR-111 | [Payout release](functional-specification.md#feature-f-039-payout-release) | Acknowledgement missing after accepting the release instruction | 202 / reconciliation pending | Only replay the same logical key | TBD |
| ERR-112 | [Payment return processing](functional-specification.md#feature-f-040-payment-return-processing) | Acknowledgement missing after accepting the return notice | 202 / reconciliation pending | TBD after reconciliation | Platform support |
| ERR-113 | [Payment reconciliation](functional-specification.md#feature-f-041-payment-reconciliation) | Acknowledgement missing after accepting the settlement match | 202 / reconciliation pending | Never blind-retry | Reporting stream |
| ERR-114 | [Payment hold removal](functional-specification.md#feature-f-042-payment-hold-removal) | Acknowledgement missing after accepting the hold record | 202 / reconciliation pending | Old note says retry three times | Former migration team |
| ERR-115 | [Document template selection](functional-specification.md#feature-f-043-document-template-selection) | Acknowledgement missing after accepting the template selection | 202 / reconciliation pending | Only replay the same logical key | Operations team |
| ERR-116 | [Statement generation](functional-specification.md#feature-f-044-statement-generation) | Acknowledgement missing after accepting the statement job | 202 / reconciliation pending | TBD after reconciliation | Benefits stream |
| ERR-117 | [Document retention purge](functional-specification.md#feature-f-045-document-retention-purge) | Acknowledgement missing after accepting the document retention item | 202 / reconciliation pending | Never blind-retry | TBD |
| ERR-118 | [Document replacement](functional-specification.md#feature-f-046-document-replacement) | Acknowledgement missing after accepting the replacement document | 202 / reconciliation pending | Old note says retry three times | Platform support |
| ERR-119 | [Document delivery receipt](functional-specification.md#feature-f-047-document-delivery-receipt) | Acknowledgement missing after accepting the delivery receipt | 202 / reconciliation pending | Only replay the same logical key | Reporting stream |
| ERR-120 | [Document language selection](functional-specification.md#feature-f-048-document-language-selection) | Acknowledgement missing after accepting the language preference | 202 / reconciliation pending | TBD after reconciliation | Former migration team |
| ERR-121 | [Notification preference update](functional-specification.md#feature-f-049-notification-preference-update) | Acknowledgement missing after accepting the channel preference | 202 / reconciliation pending | Never blind-retry | Operations team |
| ERR-122 | [Eligibility notification](functional-specification.md#feature-f-050-eligibility-notification) | Acknowledgement missing after accepting the eligibility message | 202 / reconciliation pending | Old note says retry three times | Benefits stream |
| ERR-123 | [Contribution reminder](functional-specification.md#feature-f-051-contribution-reminder) | Acknowledgement missing after accepting the reminder candidate | 202 / reconciliation pending | Only replay the same logical key | TBD |
| ERR-124 | [Claim status notification](functional-specification.md#feature-f-052-claim-status-notification) | Acknowledgement missing after accepting the claim message | 202 / reconciliation pending | TBD after reconciliation | Platform support |
| ERR-125 | [Notification retry](functional-specification.md#feature-f-053-notification-retry) | Acknowledgement missing after accepting the retry item | 202 / reconciliation pending | Never blind-retry | Reporting stream |
| ERR-126 | [Notification suppression](functional-specification.md#feature-f-054-notification-suppression) | Acknowledgement missing after accepting the suppression window | 202 / reconciliation pending | Old note says retry three times | Former migration team |
| ERR-127 | [Employer coverage report](functional-specification.md#feature-f-055-employer-coverage-report) | Acknowledgement missing after accepting the coverage report | 202 / reconciliation pending | Only replay the same logical key | Operations team |
| ERR-128 | [Contribution exception report](functional-specification.md#feature-f-056-contribution-exception-report) | Acknowledgement missing after accepting the exception report | 202 / reconciliation pending | TBD after reconciliation | Benefits stream |
| ERR-129 | [Claim ageing report](functional-specification.md#feature-f-057-claim-ageing-report) | Acknowledgement missing after accepting the ageing report | 202 / reconciliation pending | Never blind-retry | TBD |
| ERR-130 | [Branch 21 label review](functional-specification.md#feature-f-058-branch-21-label-review) | Acknowledgement missing after accepting the branch label review | 202 / reconciliation pending | Old note says retry three times | Platform support |
| ERR-131 | [Branch 23 label review](functional-specification.md#feature-f-059-branch-23-label-review) | Acknowledgement missing after accepting the branch label review | 202 / reconciliation pending | Only replay the same logical key | Reporting stream |
| ERR-132 | [Sigedis reporting placeholder](functional-specification.md#feature-f-060-sigedis-reporting-placeholder) | Acknowledgement missing after accepting the report envelope | 202 / reconciliation pending | TBD after reconciliation | Former migration team |
| ERR-133 | [User role assignment](functional-specification.md#feature-f-061-user-role-assignment) | Acknowledgement missing after accepting the role grant | 202 / reconciliation pending | Never blind-retry | Operations team |
| ERR-134 | [Permission override](functional-specification.md#feature-f-062-permission-override) | Acknowledgement missing after accepting the override request | 202 / reconciliation pending | Old note says retry three times | Benefits stream |
| ERR-135 | [Reference code maintenance](functional-specification.md#feature-f-063-reference-code-maintenance) | Acknowledgement missing after accepting the reference code | 202 / reconciliation pending | Only replay the same logical key | TBD |
| ERR-136 | [Plan configuration publishing](functional-specification.md#feature-f-064-plan-configuration-publishing) | Acknowledgement missing after accepting the plan revision | 202 / reconciliation pending | TBD after reconciliation | Platform support |
| ERR-137 | [Operational task reassignment](functional-specification.md#feature-f-065-operational-task-reassignment) | Acknowledgement missing after accepting the task assignment | 202 / reconciliation pending | Never blind-retry | Reporting stream |
| ERR-138 | [Tenant boundary review](functional-specification.md#feature-f-066-tenant-boundary-review) | Acknowledgement missing after accepting the tenant scope | 202 / reconciliation pending | Old note says retry three times | Former migration team |
| ERR-139 | [Audit event capture](functional-specification.md#feature-f-067-audit-event-capture) | Acknowledgement missing after accepting the audit envelope | 202 / reconciliation pending | Only replay the same logical key | Operations team |
| ERR-140 | [Audit hold preservation](functional-specification.md#feature-f-068-audit-hold-preservation) | Acknowledgement missing after accepting the audit hold | 202 / reconciliation pending | TBD after reconciliation | Benefits stream |
| ERR-141 | [Audit event search](functional-specification.md#feature-f-069-audit-event-search) | Acknowledgement missing after accepting the audit query | 202 / reconciliation pending | Never blind-retry | TBD |
| ERR-142 | [Audit export approval](functional-specification.md#feature-f-070-audit-export-approval) | Acknowledgement missing after accepting the audit export request | 202 / reconciliation pending | Old note says retry three times | Platform support |
| ERR-143 | [Historical correction trace](functional-specification.md#feature-f-071-historical-correction-trace) | Acknowledgement missing after accepting the correction chain | 202 / reconciliation pending | Only replay the same logical key | Reporting stream |
| ERR-144 | [Archive replay review](functional-specification.md#feature-f-072-archive-replay-review) | Acknowledgement missing after accepting the replay manifest | 202 / reconciliation pending | TBD after reconciliation | Former migration team |

## Reporting catalogue

| Report ID | Name | Selection basis | Fields or totals | Unresolved definition | Feature |
| --- | --- | --- | --- | --- | --- |
| RPT-001 | Policy creation queue extract | As-of business date | fixture_key, state_code, revision_no, warning_count | Cancelled rows included in old total | [Policy creation](functional-specification.md#feature-f-001-policy-creation) |
| RPT-002 | Policy amendment queue extract | Processed-before watermark | fixture_key, state_code, revision_no, warning_count | Missing owners grouped as blank | [Policy amendment](functional-specification.md#feature-f-002-policy-amendment) |
| RPT-003 | Policy renewal queue extract | Current queue state | fixture_key, state_code, revision_no, warning_count | Late corrections may move between periods | [Policy renewal](functional-specification.md#feature-f-003-policy-renewal) |
| RPT-004 | Policy suspension queue extract | Latest reviewed revision | fixture_key, state_code, revision_no, warning_count | Empty export versus failed export unclear | [Policy suspension](functional-specification.md#feature-f-004-policy-suspension) |
| RPT-005 | Policy cancellation queue extract | As-of business date | fixture_key, state_code, revision_no, warning_count | Cancelled rows included in old total | [Policy cancellation](functional-specification.md#feature-f-005-policy-cancellation) |
| RPT-006 | Policy reinstatement queue extract | Processed-before watermark | fixture_key, state_code, revision_no, warning_count | Missing owners grouped as blank | [Policy reinstatement](functional-specification.md#feature-f-006-policy-reinstatement) |
| RPT-007 | Employer shell creation queue extract | Current queue state | fixture_key, state_code, revision_no, warning_count | Late corrections may move between periods | [Employer shell creation](functional-specification.md#feature-f-007-employer-shell-creation) |
| RPT-008 | Employer document intake queue extract | Latest reviewed revision | fixture_key, state_code, revision_no, warning_count | Empty export versus failed export unclear | [Employer document intake](functional-specification.md#feature-f-008-employer-document-intake) |
| RPT-009 | Employer activation queue extract | As-of business date | fixture_key, state_code, revision_no, warning_count | Cancelled rows included in old total | [Employer activation](functional-specification.md#feature-f-009-employer-activation) |
| RPT-010 | Employer hierarchy change queue extract | Processed-before watermark | fixture_key, state_code, revision_no, warning_count | Missing owners grouped as blank | [Employer hierarchy change](functional-specification.md#feature-f-010-employer-hierarchy-change) |
| RPT-011 | Employer contact maintenance queue extract | Current queue state | fixture_key, state_code, revision_no, warning_count | Late corrections may move between periods | [Employer contact maintenance](functional-specification.md#feature-f-011-employer-contact-maintenance) |
| RPT-012 | Employer offboarding queue extract | Latest reviewed revision | fixture_key, state_code, revision_no, warning_count | Empty export versus failed export unclear | [Employer offboarding](functional-specification.md#feature-f-012-employer-offboarding) |
| RPT-013 | Employee eligibility assessment queue extract | As-of business date | fixture_key, state_code, revision_no, warning_count | Cancelled rows included in old total | [Employee eligibility assessment](functional-specification.md#feature-f-013-employee-eligibility-assessment) |
| RPT-014 | Waiting period evaluation queue extract | Processed-before watermark | fixture_key, state_code, revision_no, warning_count | Missing owners grouped as blank | [Waiting period evaluation](functional-specification.md#feature-f-014-waiting-period-evaluation) |
| RPT-015 | Employment category change queue extract | Current queue state | fixture_key, state_code, revision_no, warning_count | Late corrections may move between periods | [Employment category change](functional-specification.md#feature-f-015-employment-category-change) |
| RPT-016 | Leave and absence handling queue extract | Latest reviewed revision | fixture_key, state_code, revision_no, warning_count | Empty export versus failed export unclear | [Leave and absence handling](functional-specification.md#feature-f-016-leave-and-absence-handling) |
| RPT-017 | Member exit processing queue extract | As-of business date | fixture_key, state_code, revision_no, warning_count | Cancelled rows included in old total | [Member exit processing](functional-specification.md#feature-f-017-member-exit-processing) |
| RPT-018 | Member re-entry queue extract | Processed-before watermark | fixture_key, state_code, revision_no, warning_count | Missing owners grouped as blank | [Member re-entry](functional-specification.md#feature-f-018-member-re-entry) |
| RPT-019 | Contribution calculation queue extract | Current queue state | fixture_key, state_code, revision_no, warning_count | Late corrections may move between periods | [Contribution calculation](functional-specification.md#feature-f-019-contribution-calculation) |
| RPT-020 | Contribution allocation queue extract | Latest reviewed revision | fixture_key, state_code, revision_no, warning_count | Empty export versus failed export unclear | [Contribution allocation](functional-specification.md#feature-f-020-contribution-allocation) |
| RPT-021 | Contribution arrears queue extract | As-of business date | fixture_key, state_code, revision_no, warning_count | Cancelled rows included in old total | [Contribution arrears](functional-specification.md#feature-f-021-contribution-arrears) |
| RPT-022 | Payroll import queue extract | Processed-before watermark | fixture_key, state_code, revision_no, warning_count | Missing owners grouped as blank | [Payroll import](functional-specification.md#feature-f-022-payroll-import) |
| RPT-023 | Contribution correction queue extract | Current queue state | fixture_key, state_code, revision_no, warning_count | Late corrections may move between periods | [Contribution correction](functional-specification.md#feature-f-023-contribution-correction) |
| RPT-024 | Contribution refund request queue extract | Latest reviewed revision | fixture_key, state_code, revision_no, warning_count | Empty export versus failed export unclear | [Contribution refund request](functional-specification.md#feature-f-024-contribution-refund-request) |
| RPT-025 | Beneficiary designation queue extract | As-of business date | fixture_key, state_code, revision_no, warning_count | Cancelled rows included in old total | [Beneficiary designation](functional-specification.md#feature-f-025-beneficiary-designation) |
| RPT-026 | Beneficiary share validation queue extract | Processed-before watermark | fixture_key, state_code, revision_no, warning_count | Missing owners grouped as blank | [Beneficiary share validation](functional-specification.md#feature-f-026-beneficiary-share-validation) |
| RPT-027 | Beneficiary evidence review queue extract | Current queue state | fixture_key, state_code, revision_no, warning_count | Late corrections may move between periods | [Beneficiary evidence review](functional-specification.md#feature-f-027-beneficiary-evidence-review) |
| RPT-028 | Retirement event registration queue extract | Latest reviewed revision | fixture_key, state_code, revision_no, warning_count | Empty export versus failed export unclear | [Retirement event registration](functional-specification.md#feature-f-028-retirement-event-registration) |
| RPT-029 | Death event registration queue extract | As-of business date | fixture_key, state_code, revision_no, warning_count | Cancelled rows included in old total | [Death event registration](functional-specification.md#feature-f-029-death-event-registration) |
| RPT-030 | Disability event registration queue extract | Processed-before watermark | fixture_key, state_code, revision_no, warning_count | Missing owners grouped as blank | [Disability event registration](functional-specification.md#feature-f-030-disability-event-registration) |
| RPT-031 | Claim intake queue extract | Current queue state | fixture_key, state_code, revision_no, warning_count | Late corrections may move between periods | [Claim intake](functional-specification.md#feature-f-031-claim-intake) |
| RPT-032 | Claim evidence checklist queue extract | Latest reviewed revision | fixture_key, state_code, revision_no, warning_count | Empty export versus failed export unclear | [Claim evidence checklist](functional-specification.md#feature-f-032-claim-evidence-checklist) |
| RPT-033 | Death claim entitlement snapshot queue extract | As-of business date | fixture_key, state_code, revision_no, warning_count | Cancelled rows included in old total | [Death claim entitlement snapshot](functional-specification.md#feature-f-033-death-claim-entitlement-snapshot) |
| RPT-034 | Disability claim assessment queue extract | Processed-before watermark | fixture_key, state_code, revision_no, warning_count | Missing owners grouped as blank | [Disability claim assessment](functional-specification.md#feature-f-034-disability-claim-assessment) |
| RPT-035 | Retirement claim quotation queue extract | Current queue state | fixture_key, state_code, revision_no, warning_count | Late corrections may move between periods | [Retirement claim quotation](functional-specification.md#feature-f-035-retirement-claim-quotation) |
| RPT-036 | Claim appeal and reopening queue extract | Latest reviewed revision | fixture_key, state_code, revision_no, warning_count | Empty export versus failed export unclear | [Claim appeal and reopening](functional-specification.md#feature-f-036-claim-appeal-and-reopening) |
| RPT-037 | Payout authorization queue extract | As-of business date | fixture_key, state_code, revision_no, warning_count | Cancelled rows included in old total | [Payout authorization](functional-specification.md#feature-f-037-payout-authorization) |
| RPT-038 | Payout scheduling queue extract | Processed-before watermark | fixture_key, state_code, revision_no, warning_count | Missing owners grouped as blank | [Payout scheduling](functional-specification.md#feature-f-038-payout-scheduling) |
| RPT-039 | Payout release queue extract | Current queue state | fixture_key, state_code, revision_no, warning_count | Late corrections may move between periods | [Payout release](functional-specification.md#feature-f-039-payout-release) |
| RPT-040 | Payment return processing queue extract | Latest reviewed revision | fixture_key, state_code, revision_no, warning_count | Empty export versus failed export unclear | [Payment return processing](functional-specification.md#feature-f-040-payment-return-processing) |
| RPT-041 | Payment reconciliation queue extract | As-of business date | fixture_key, state_code, revision_no, warning_count | Cancelled rows included in old total | [Payment reconciliation](functional-specification.md#feature-f-041-payment-reconciliation) |
| RPT-042 | Payment hold removal queue extract | Processed-before watermark | fixture_key, state_code, revision_no, warning_count | Missing owners grouped as blank | [Payment hold removal](functional-specification.md#feature-f-042-payment-hold-removal) |
| RPT-043 | Document template selection queue extract | Current queue state | fixture_key, state_code, revision_no, warning_count | Late corrections may move between periods | [Document template selection](functional-specification.md#feature-f-043-document-template-selection) |
| RPT-044 | Statement generation queue extract | Latest reviewed revision | fixture_key, state_code, revision_no, warning_count | Empty export versus failed export unclear | [Statement generation](functional-specification.md#feature-f-044-statement-generation) |
| RPT-045 | Document retention purge queue extract | As-of business date | fixture_key, state_code, revision_no, warning_count | Cancelled rows included in old total | [Document retention purge](functional-specification.md#feature-f-045-document-retention-purge) |
| RPT-046 | Document replacement queue extract | Processed-before watermark | fixture_key, state_code, revision_no, warning_count | Missing owners grouped as blank | [Document replacement](functional-specification.md#feature-f-046-document-replacement) |
| RPT-047 | Document delivery receipt queue extract | Current queue state | fixture_key, state_code, revision_no, warning_count | Late corrections may move between periods | [Document delivery receipt](functional-specification.md#feature-f-047-document-delivery-receipt) |
| RPT-048 | Document language selection queue extract | Latest reviewed revision | fixture_key, state_code, revision_no, warning_count | Empty export versus failed export unclear | [Document language selection](functional-specification.md#feature-f-048-document-language-selection) |
| RPT-049 | Notification preference update queue extract | As-of business date | fixture_key, state_code, revision_no, warning_count | Cancelled rows included in old total | [Notification preference update](functional-specification.md#feature-f-049-notification-preference-update) |
| RPT-050 | Eligibility notification queue extract | Processed-before watermark | fixture_key, state_code, revision_no, warning_count | Missing owners grouped as blank | [Eligibility notification](functional-specification.md#feature-f-050-eligibility-notification) |
| RPT-051 | Contribution reminder queue extract | Current queue state | fixture_key, state_code, revision_no, warning_count | Late corrections may move between periods | [Contribution reminder](functional-specification.md#feature-f-051-contribution-reminder) |
| RPT-052 | Claim status notification queue extract | Latest reviewed revision | fixture_key, state_code, revision_no, warning_count | Empty export versus failed export unclear | [Claim status notification](functional-specification.md#feature-f-052-claim-status-notification) |
| RPT-053 | Notification retry queue extract | As-of business date | fixture_key, state_code, revision_no, warning_count | Cancelled rows included in old total | [Notification retry](functional-specification.md#feature-f-053-notification-retry) |
| RPT-054 | Notification suppression queue extract | Processed-before watermark | fixture_key, state_code, revision_no, warning_count | Missing owners grouped as blank | [Notification suppression](functional-specification.md#feature-f-054-notification-suppression) |
| RPT-055 | Employer coverage report queue extract | Current queue state | fixture_key, state_code, revision_no, warning_count | Late corrections may move between periods | [Employer coverage report](functional-specification.md#feature-f-055-employer-coverage-report) |
| RPT-056 | Contribution exception report queue extract | Latest reviewed revision | fixture_key, state_code, revision_no, warning_count | Empty export versus failed export unclear | [Contribution exception report](functional-specification.md#feature-f-056-contribution-exception-report) |
| RPT-057 | Claim ageing report queue extract | As-of business date | fixture_key, state_code, revision_no, warning_count | Cancelled rows included in old total | [Claim ageing report](functional-specification.md#feature-f-057-claim-ageing-report) |
| RPT-058 | Branch 21 label review queue extract | Processed-before watermark | fixture_key, state_code, revision_no, warning_count | Missing owners grouped as blank | [Branch 21 label review](functional-specification.md#feature-f-058-branch-21-label-review) |
| RPT-059 | Branch 23 label review queue extract | Current queue state | fixture_key, state_code, revision_no, warning_count | Late corrections may move between periods | [Branch 23 label review](functional-specification.md#feature-f-059-branch-23-label-review) |
| RPT-060 | Sigedis reporting placeholder queue extract | Latest reviewed revision | fixture_key, state_code, revision_no, warning_count | Empty export versus failed export unclear | [Sigedis reporting placeholder](functional-specification.md#feature-f-060-sigedis-reporting-placeholder) |
| RPT-061 | User role assignment queue extract | As-of business date | fixture_key, state_code, revision_no, warning_count | Cancelled rows included in old total | [User role assignment](functional-specification.md#feature-f-061-user-role-assignment) |
| RPT-062 | Permission override queue extract | Processed-before watermark | fixture_key, state_code, revision_no, warning_count | Missing owners grouped as blank | [Permission override](functional-specification.md#feature-f-062-permission-override) |
| RPT-063 | Reference code maintenance queue extract | Current queue state | fixture_key, state_code, revision_no, warning_count | Late corrections may move between periods | [Reference code maintenance](functional-specification.md#feature-f-063-reference-code-maintenance) |
| RPT-064 | Plan configuration publishing queue extract | Latest reviewed revision | fixture_key, state_code, revision_no, warning_count | Empty export versus failed export unclear | [Plan configuration publishing](functional-specification.md#feature-f-064-plan-configuration-publishing) |
| RPT-065 | Operational task reassignment queue extract | As-of business date | fixture_key, state_code, revision_no, warning_count | Cancelled rows included in old total | [Operational task reassignment](functional-specification.md#feature-f-065-operational-task-reassignment) |
| RPT-066 | Tenant boundary review queue extract | Processed-before watermark | fixture_key, state_code, revision_no, warning_count | Missing owners grouped as blank | [Tenant boundary review](functional-specification.md#feature-f-066-tenant-boundary-review) |
| RPT-067 | Audit event capture queue extract | Current queue state | fixture_key, state_code, revision_no, warning_count | Late corrections may move between periods | [Audit event capture](functional-specification.md#feature-f-067-audit-event-capture) |
| RPT-068 | Audit hold preservation queue extract | Latest reviewed revision | fixture_key, state_code, revision_no, warning_count | Empty export versus failed export unclear | [Audit hold preservation](functional-specification.md#feature-f-068-audit-hold-preservation) |
| RPT-069 | Audit event search queue extract | As-of business date | fixture_key, state_code, revision_no, warning_count | Cancelled rows included in old total | [Audit event search](functional-specification.md#feature-f-069-audit-event-search) |
| RPT-070 | Audit export approval queue extract | Processed-before watermark | fixture_key, state_code, revision_no, warning_count | Missing owners grouped as blank | [Audit export approval](functional-specification.md#feature-f-070-audit-export-approval) |
| RPT-071 | Historical correction trace queue extract | Current queue state | fixture_key, state_code, revision_no, warning_count | Late corrections may move between periods | [Historical correction trace](functional-specification.md#feature-f-071-historical-correction-trace) |
| RPT-072 | Archive replay review queue extract | Latest reviewed revision | fixture_key, state_code, revision_no, warning_count | Empty export versus failed export unclear | [Archive replay review](functional-specification.md#feature-f-072-archive-replay-review) |
| RPT-073 | Policy creation revision comparison | As-of business date | fixture_key, state_code, revision_no, warning_count | Cancelled rows included in old total | [Policy creation](functional-specification.md#feature-f-001-policy-creation) |
| RPT-074 | Policy amendment revision comparison | Processed-before watermark | fixture_key, state_code, revision_no, warning_count | Missing owners grouped as blank | [Policy amendment](functional-specification.md#feature-f-002-policy-amendment) |
| RPT-075 | Policy renewal revision comparison | Current queue state | fixture_key, state_code, revision_no, warning_count | Late corrections may move between periods | [Policy renewal](functional-specification.md#feature-f-003-policy-renewal) |
| RPT-076 | Policy suspension revision comparison | Latest reviewed revision | fixture_key, state_code, revision_no, warning_count | Empty export versus failed export unclear | [Policy suspension](functional-specification.md#feature-f-004-policy-suspension) |
| RPT-077 | Policy cancellation revision comparison | As-of business date | fixture_key, state_code, revision_no, warning_count | Cancelled rows included in old total | [Policy cancellation](functional-specification.md#feature-f-005-policy-cancellation) |
| RPT-078 | Policy reinstatement revision comparison | Processed-before watermark | fixture_key, state_code, revision_no, warning_count | Missing owners grouped as blank | [Policy reinstatement](functional-specification.md#feature-f-006-policy-reinstatement) |
| RPT-079 | Employer shell creation revision comparison | Current queue state | fixture_key, state_code, revision_no, warning_count | Late corrections may move between periods | [Employer shell creation](functional-specification.md#feature-f-007-employer-shell-creation) |
| RPT-080 | Employer document intake revision comparison | Latest reviewed revision | fixture_key, state_code, revision_no, warning_count | Empty export versus failed export unclear | [Employer document intake](functional-specification.md#feature-f-008-employer-document-intake) |
| RPT-081 | Employer activation revision comparison | As-of business date | fixture_key, state_code, revision_no, warning_count | Cancelled rows included in old total | [Employer activation](functional-specification.md#feature-f-009-employer-activation) |
| RPT-082 | Employer hierarchy change revision comparison | Processed-before watermark | fixture_key, state_code, revision_no, warning_count | Missing owners grouped as blank | [Employer hierarchy change](functional-specification.md#feature-f-010-employer-hierarchy-change) |
| RPT-083 | Employer contact maintenance revision comparison | Current queue state | fixture_key, state_code, revision_no, warning_count | Late corrections may move between periods | [Employer contact maintenance](functional-specification.md#feature-f-011-employer-contact-maintenance) |
| RPT-084 | Employer offboarding revision comparison | Latest reviewed revision | fixture_key, state_code, revision_no, warning_count | Empty export versus failed export unclear | [Employer offboarding](functional-specification.md#feature-f-012-employer-offboarding) |
| RPT-085 | Employee eligibility assessment revision comparison | As-of business date | fixture_key, state_code, revision_no, warning_count | Cancelled rows included in old total | [Employee eligibility assessment](functional-specification.md#feature-f-013-employee-eligibility-assessment) |
| RPT-086 | Waiting period evaluation revision comparison | Processed-before watermark | fixture_key, state_code, revision_no, warning_count | Missing owners grouped as blank | [Waiting period evaluation](functional-specification.md#feature-f-014-waiting-period-evaluation) |
| RPT-087 | Employment category change revision comparison | Current queue state | fixture_key, state_code, revision_no, warning_count | Late corrections may move between periods | [Employment category change](functional-specification.md#feature-f-015-employment-category-change) |
| RPT-088 | Leave and absence handling revision comparison | Latest reviewed revision | fixture_key, state_code, revision_no, warning_count | Empty export versus failed export unclear | [Leave and absence handling](functional-specification.md#feature-f-016-leave-and-absence-handling) |
| RPT-089 | Member exit processing revision comparison | As-of business date | fixture_key, state_code, revision_no, warning_count | Cancelled rows included in old total | [Member exit processing](functional-specification.md#feature-f-017-member-exit-processing) |
| RPT-090 | Member re-entry revision comparison | Processed-before watermark | fixture_key, state_code, revision_no, warning_count | Missing owners grouped as blank | [Member re-entry](functional-specification.md#feature-f-018-member-re-entry) |
| RPT-091 | Contribution calculation revision comparison | Current queue state | fixture_key, state_code, revision_no, warning_count | Late corrections may move between periods | [Contribution calculation](functional-specification.md#feature-f-019-contribution-calculation) |
| RPT-092 | Contribution allocation revision comparison | Latest reviewed revision | fixture_key, state_code, revision_no, warning_count | Empty export versus failed export unclear | [Contribution allocation](functional-specification.md#feature-f-020-contribution-allocation) |
| RPT-093 | Contribution arrears revision comparison | As-of business date | fixture_key, state_code, revision_no, warning_count | Cancelled rows included in old total | [Contribution arrears](functional-specification.md#feature-f-021-contribution-arrears) |
| RPT-094 | Payroll import revision comparison | Processed-before watermark | fixture_key, state_code, revision_no, warning_count | Missing owners grouped as blank | [Payroll import](functional-specification.md#feature-f-022-payroll-import) |
| RPT-095 | Contribution correction revision comparison | Current queue state | fixture_key, state_code, revision_no, warning_count | Late corrections may move between periods | [Contribution correction](functional-specification.md#feature-f-023-contribution-correction) |
| RPT-096 | Contribution refund request revision comparison | Latest reviewed revision | fixture_key, state_code, revision_no, warning_count | Empty export versus failed export unclear | [Contribution refund request](functional-specification.md#feature-f-024-contribution-refund-request) |

### Report reconciliation notes

| Control ID | Scope | Proposed invariant | Known gap |
| --- | --- | --- | --- |
| CONTROL-001 | [Policy creation](functional-specification.md#feature-f-001-policy-creation) | Accepted count plus rejected count equals received count for one envelope revision | Duplicate rows counted twice in the old monitor |
| CONTROL-002 | [Policy amendment](functional-specification.md#feature-f-002-policy-amendment) | Accepted count plus rejected count equals received count for one envelope revision | Warnings overlap accepted rows; do not add them again |
| CONTROL-003 | [Policy renewal](functional-specification.md#feature-f-003-policy-renewal) | Accepted count plus rejected count equals received count for one envelope revision | Superseded rows need a separate measure |
| CONTROL-004 | [Policy suspension](functional-specification.md#feature-f-004-policy-suspension) | Accepted count plus rejected count equals received count for one envelope revision | Possibly obsolete: trailer count included the header |
| CONTROL-005 | [Policy cancellation](functional-specification.md#feature-f-005-policy-cancellation) | Accepted count plus rejected count equals received count for one envelope revision | Duplicate rows counted twice in the old monitor |
| CONTROL-006 | [Policy reinstatement](functional-specification.md#feature-f-006-policy-reinstatement) | Accepted count plus rejected count equals received count for one envelope revision | Warnings overlap accepted rows; do not add them again |
| CONTROL-007 | [Employer shell creation](functional-specification.md#feature-f-007-employer-shell-creation) | Accepted count plus rejected count equals received count for one envelope revision | Superseded rows need a separate measure |
| CONTROL-008 | [Employer document intake](functional-specification.md#feature-f-008-employer-document-intake) | Accepted count plus rejected count equals received count for one envelope revision | Possibly obsolete: trailer count included the header |
| CONTROL-009 | [Employer activation](functional-specification.md#feature-f-009-employer-activation) | Accepted count plus rejected count equals received count for one envelope revision | Duplicate rows counted twice in the old monitor |
| CONTROL-010 | [Employer hierarchy change](functional-specification.md#feature-f-010-employer-hierarchy-change) | Accepted count plus rejected count equals received count for one envelope revision | Warnings overlap accepted rows; do not add them again |
| CONTROL-011 | [Employer contact maintenance](functional-specification.md#feature-f-011-employer-contact-maintenance) | Accepted count plus rejected count equals received count for one envelope revision | Superseded rows need a separate measure |
| CONTROL-012 | [Employer offboarding](functional-specification.md#feature-f-012-employer-offboarding) | Accepted count plus rejected count equals received count for one envelope revision | Possibly obsolete: trailer count included the header |
| CONTROL-013 | [Employee eligibility assessment](functional-specification.md#feature-f-013-employee-eligibility-assessment) | Accepted count plus rejected count equals received count for one envelope revision | Duplicate rows counted twice in the old monitor |
| CONTROL-014 | [Waiting period evaluation](functional-specification.md#feature-f-014-waiting-period-evaluation) | Accepted count plus rejected count equals received count for one envelope revision | Warnings overlap accepted rows; do not add them again |
| CONTROL-015 | [Employment category change](functional-specification.md#feature-f-015-employment-category-change) | Accepted count plus rejected count equals received count for one envelope revision | Superseded rows need a separate measure |
| CONTROL-016 | [Leave and absence handling](functional-specification.md#feature-f-016-leave-and-absence-handling) | Accepted count plus rejected count equals received count for one envelope revision | Possibly obsolete: trailer count included the header |
| CONTROL-017 | [Member exit processing](functional-specification.md#feature-f-017-member-exit-processing) | Accepted count plus rejected count equals received count for one envelope revision | Duplicate rows counted twice in the old monitor |
| CONTROL-018 | [Member re-entry](functional-specification.md#feature-f-018-member-re-entry) | Accepted count plus rejected count equals received count for one envelope revision | Warnings overlap accepted rows; do not add them again |
| CONTROL-019 | [Contribution calculation](functional-specification.md#feature-f-019-contribution-calculation) | Accepted count plus rejected count equals received count for one envelope revision | Superseded rows need a separate measure |
| CONTROL-020 | [Contribution allocation](functional-specification.md#feature-f-020-contribution-allocation) | Accepted count plus rejected count equals received count for one envelope revision | Possibly obsolete: trailer count included the header |
| CONTROL-021 | [Contribution arrears](functional-specification.md#feature-f-021-contribution-arrears) | Accepted count plus rejected count equals received count for one envelope revision | Duplicate rows counted twice in the old monitor |
| CONTROL-022 | [Payroll import](functional-specification.md#feature-f-022-payroll-import) | Accepted count plus rejected count equals received count for one envelope revision | Warnings overlap accepted rows; do not add them again |
| CONTROL-023 | [Contribution correction](functional-specification.md#feature-f-023-contribution-correction) | Accepted count plus rejected count equals received count for one envelope revision | Superseded rows need a separate measure |
| CONTROL-024 | [Contribution refund request](functional-specification.md#feature-f-024-contribution-refund-request) | Accepted count plus rejected count equals received count for one envelope revision | Possibly obsolete: trailer count included the header |
| CONTROL-025 | [Beneficiary designation](functional-specification.md#feature-f-025-beneficiary-designation) | Accepted count plus rejected count equals received count for one envelope revision | Duplicate rows counted twice in the old monitor |
| CONTROL-026 | [Beneficiary share validation](functional-specification.md#feature-f-026-beneficiary-share-validation) | Accepted count plus rejected count equals received count for one envelope revision | Warnings overlap accepted rows; do not add them again |
| CONTROL-027 | [Beneficiary evidence review](functional-specification.md#feature-f-027-beneficiary-evidence-review) | Accepted count plus rejected count equals received count for one envelope revision | Superseded rows need a separate measure |
| CONTROL-028 | [Retirement event registration](functional-specification.md#feature-f-028-retirement-event-registration) | Accepted count plus rejected count equals received count for one envelope revision | Possibly obsolete: trailer count included the header |
| CONTROL-029 | [Death event registration](functional-specification.md#feature-f-029-death-event-registration) | Accepted count plus rejected count equals received count for one envelope revision | Duplicate rows counted twice in the old monitor |
| CONTROL-030 | [Disability event registration](functional-specification.md#feature-f-030-disability-event-registration) | Accepted count plus rejected count equals received count for one envelope revision | Warnings overlap accepted rows; do not add them again |
| CONTROL-031 | [Claim intake](functional-specification.md#feature-f-031-claim-intake) | Accepted count plus rejected count equals received count for one envelope revision | Superseded rows need a separate measure |
| CONTROL-032 | [Claim evidence checklist](functional-specification.md#feature-f-032-claim-evidence-checklist) | Accepted count plus rejected count equals received count for one envelope revision | Possibly obsolete: trailer count included the header |
| CONTROL-033 | [Death claim entitlement snapshot](functional-specification.md#feature-f-033-death-claim-entitlement-snapshot) | Accepted count plus rejected count equals received count for one envelope revision | Duplicate rows counted twice in the old monitor |
| CONTROL-034 | [Disability claim assessment](functional-specification.md#feature-f-034-disability-claim-assessment) | Accepted count plus rejected count equals received count for one envelope revision | Warnings overlap accepted rows; do not add them again |
| CONTROL-035 | [Retirement claim quotation](functional-specification.md#feature-f-035-retirement-claim-quotation) | Accepted count plus rejected count equals received count for one envelope revision | Superseded rows need a separate measure |
| CONTROL-036 | [Claim appeal and reopening](functional-specification.md#feature-f-036-claim-appeal-and-reopening) | Accepted count plus rejected count equals received count for one envelope revision | Possibly obsolete: trailer count included the header |
| CONTROL-037 | [Payout authorization](functional-specification.md#feature-f-037-payout-authorization) | Accepted count plus rejected count equals received count for one envelope revision | Duplicate rows counted twice in the old monitor |
| CONTROL-038 | [Payout scheduling](functional-specification.md#feature-f-038-payout-scheduling) | Accepted count plus rejected count equals received count for one envelope revision | Warnings overlap accepted rows; do not add them again |
| CONTROL-039 | [Payout release](functional-specification.md#feature-f-039-payout-release) | Accepted count plus rejected count equals received count for one envelope revision | Superseded rows need a separate measure |
| CONTROL-040 | [Payment return processing](functional-specification.md#feature-f-040-payment-return-processing) | Accepted count plus rejected count equals received count for one envelope revision | Possibly obsolete: trailer count included the header |
| CONTROL-041 | [Payment reconciliation](functional-specification.md#feature-f-041-payment-reconciliation) | Accepted count plus rejected count equals received count for one envelope revision | Duplicate rows counted twice in the old monitor |
| CONTROL-042 | [Payment hold removal](functional-specification.md#feature-f-042-payment-hold-removal) | Accepted count plus rejected count equals received count for one envelope revision | Warnings overlap accepted rows; do not add them again |
| CONTROL-043 | [Document template selection](functional-specification.md#feature-f-043-document-template-selection) | Accepted count plus rejected count equals received count for one envelope revision | Superseded rows need a separate measure |
| CONTROL-044 | [Statement generation](functional-specification.md#feature-f-044-statement-generation) | Accepted count plus rejected count equals received count for one envelope revision | Possibly obsolete: trailer count included the header |
| CONTROL-045 | [Document retention purge](functional-specification.md#feature-f-045-document-retention-purge) | Accepted count plus rejected count equals received count for one envelope revision | Duplicate rows counted twice in the old monitor |
| CONTROL-046 | [Document replacement](functional-specification.md#feature-f-046-document-replacement) | Accepted count plus rejected count equals received count for one envelope revision | Warnings overlap accepted rows; do not add them again |
| CONTROL-047 | [Document delivery receipt](functional-specification.md#feature-f-047-document-delivery-receipt) | Accepted count plus rejected count equals received count for one envelope revision | Superseded rows need a separate measure |
| CONTROL-048 | [Document language selection](functional-specification.md#feature-f-048-document-language-selection) | Accepted count plus rejected count equals received count for one envelope revision | Possibly obsolete: trailer count included the header |
| CONTROL-049 | [Notification preference update](functional-specification.md#feature-f-049-notification-preference-update) | Accepted count plus rejected count equals received count for one envelope revision | Duplicate rows counted twice in the old monitor |
| CONTROL-050 | [Eligibility notification](functional-specification.md#feature-f-050-eligibility-notification) | Accepted count plus rejected count equals received count for one envelope revision | Warnings overlap accepted rows; do not add them again |
| CONTROL-051 | [Contribution reminder](functional-specification.md#feature-f-051-contribution-reminder) | Accepted count plus rejected count equals received count for one envelope revision | Superseded rows need a separate measure |
| CONTROL-052 | [Claim status notification](functional-specification.md#feature-f-052-claim-status-notification) | Accepted count plus rejected count equals received count for one envelope revision | Possibly obsolete: trailer count included the header |
| CONTROL-053 | [Notification retry](functional-specification.md#feature-f-053-notification-retry) | Accepted count plus rejected count equals received count for one envelope revision | Duplicate rows counted twice in the old monitor |
| CONTROL-054 | [Notification suppression](functional-specification.md#feature-f-054-notification-suppression) | Accepted count plus rejected count equals received count for one envelope revision | Warnings overlap accepted rows; do not add them again |
| CONTROL-055 | [Employer coverage report](functional-specification.md#feature-f-055-employer-coverage-report) | Accepted count plus rejected count equals received count for one envelope revision | Superseded rows need a separate measure |
| CONTROL-056 | [Contribution exception report](functional-specification.md#feature-f-056-contribution-exception-report) | Accepted count plus rejected count equals received count for one envelope revision | Possibly obsolete: trailer count included the header |
| CONTROL-057 | [Claim ageing report](functional-specification.md#feature-f-057-claim-ageing-report) | Accepted count plus rejected count equals received count for one envelope revision | Duplicate rows counted twice in the old monitor |
| CONTROL-058 | [Branch 21 label review](functional-specification.md#feature-f-058-branch-21-label-review) | Accepted count plus rejected count equals received count for one envelope revision | Warnings overlap accepted rows; do not add them again |
| CONTROL-059 | [Branch 23 label review](functional-specification.md#feature-f-059-branch-23-label-review) | Accepted count plus rejected count equals received count for one envelope revision | Superseded rows need a separate measure |
| CONTROL-060 | [Sigedis reporting placeholder](functional-specification.md#feature-f-060-sigedis-reporting-placeholder) | Accepted count plus rejected count equals received count for one envelope revision | Possibly obsolete: trailer count included the header |
| CONTROL-061 | [User role assignment](functional-specification.md#feature-f-061-user-role-assignment) | Accepted count plus rejected count equals received count for one envelope revision | Duplicate rows counted twice in the old monitor |
| CONTROL-062 | [Permission override](functional-specification.md#feature-f-062-permission-override) | Accepted count plus rejected count equals received count for one envelope revision | Warnings overlap accepted rows; do not add them again |
| CONTROL-063 | [Reference code maintenance](functional-specification.md#feature-f-063-reference-code-maintenance) | Accepted count plus rejected count equals received count for one envelope revision | Superseded rows need a separate measure |
| CONTROL-064 | [Plan configuration publishing](functional-specification.md#feature-f-064-plan-configuration-publishing) | Accepted count plus rejected count equals received count for one envelope revision | Possibly obsolete: trailer count included the header |
| CONTROL-065 | [Operational task reassignment](functional-specification.md#feature-f-065-operational-task-reassignment) | Accepted count plus rejected count equals received count for one envelope revision | Duplicate rows counted twice in the old monitor |
| CONTROL-066 | [Tenant boundary review](functional-specification.md#feature-f-066-tenant-boundary-review) | Accepted count plus rejected count equals received count for one envelope revision | Warnings overlap accepted rows; do not add them again |
| CONTROL-067 | [Audit event capture](functional-specification.md#feature-f-067-audit-event-capture) | Accepted count plus rejected count equals received count for one envelope revision | Superseded rows need a separate measure |
| CONTROL-068 | [Audit hold preservation](functional-specification.md#feature-f-068-audit-hold-preservation) | Accepted count plus rejected count equals received count for one envelope revision | Possibly obsolete: trailer count included the header |
| CONTROL-069 | [Audit event search](functional-specification.md#feature-f-069-audit-event-search) | Accepted count plus rejected count equals received count for one envelope revision | Duplicate rows counted twice in the old monitor |
| CONTROL-070 | [Audit export approval](functional-specification.md#feature-f-070-audit-export-approval) | Accepted count plus rejected count equals received count for one envelope revision | Warnings overlap accepted rows; do not add them again |
| CONTROL-071 | [Historical correction trace](functional-specification.md#feature-f-071-historical-correction-trace) | Accepted count plus rejected count equals received count for one envelope revision | Superseded rows need a separate measure |
| CONTROL-072 | [Archive replay review](functional-specification.md#feature-f-072-archive-replay-review) | Accepted count plus rejected count equals received count for one envelope revision | Possibly obsolete: trailer count included the header |

## Regulatory-reference placeholders

> Regulatory reference only. Validation by Belgian compliance and legal experts is required before external use.

> Compliance note: requires Belgian-market and legal validation.

### Branch 21 reference fragment

Branch 21 is retained only as a label in the synthetic catalogue. This fixture makes no statement about product characteristics, guarantees, accounting treatment, tax, distribution, or applicable obligations.
Review entry: [Branch 21 label review](functional-specification.md#feature-f-058-branch-21-label-review). No authoritative source is attached; no external material was copied.
Open review: determine whether the label is appropriate for the fictional product design before deriving any field, document, or rule from it.
Possibly obsolete: an invented 2020-04-09 workshop note assumed the label could select a template. That assumption is unvalidated.

> Regulatory reference only. Validation by Belgian compliance and legal experts is required before external use.

> Compliance note: requires Belgian-market and legal validation.

### Branch 23 reference fragment

Branch 23 is another unvalidated catalogue label. The technical model deliberately supplies no fund catalogue, valuation schedule, risk disclosure, or entitlement rule.
Review entry: [Branch 23 label review](functional-specification.md#feature-f-059-branch-23-label-review). Mapping a label to a workflow is blocked pending expert validation.
The old routing sheet suggests sharing the Branch 21 template selector. A later note says separate selectors are required. Neither statement is approved.

> Regulatory reference only. Validation by Belgian compliance and legal experts is required before external use.

> Compliance note: requires Belgian-market and legal validation.

### Sigedis-related reporting placeholder

Sigedis is named solely to identify a future validation topic. INT-060 describes a fictional internal envelope simulator; it is not an official or working integration.
Review entry: [Sigedis reporting placeholder](functional-specification.md#feature-f-060-sigedis-reporting-placeholder). Transmission mode remains disabled.
No endpoint, official schema, authentication mechanism, statutory deadline, reporting population, retention rule, or acceptance criteria is claimed.
The internal report envelope uses invented fields solely to exercise validation and error handling in tests.
A hypothetical acknowledgement called SIMULATED-RECEIPT must never be interpreted as an external acceptance.

> Regulatory reference only. Validation by Belgian compliance and legal experts is required before external use.

> Compliance note: requires Belgian-market and legal validation.

### Validation backlog for placeholder references

| Review ID | Topic | Question for future validation | Owner | Stale note date |
| --- | --- | --- | --- | --- |
| LEGAL-REVIEW-001 | Branch 21 | Is the fictional scope sufficiently defined to determine which obligations would need review? | Operations team | 2024-06-06 |
| LEGAL-REVIEW-002 | Branch 23 | Is the fictional scope sufficiently defined to determine which obligations would need review? | Benefits stream | 2025-07-07 |
| LEGAL-REVIEW-003 | Sigedis-related placeholder | Is the fictional scope sufficiently defined to determine which obligations would need review? | TBD | 2019-08-08 |
| LEGAL-REVIEW-004 | Branch 21 | Is the fictional scope sufficiently defined to determine which obligations would need review? | Platform support | 2020-09-09 |
| LEGAL-REVIEW-005 | Branch 23 | Is the fictional scope sufficiently defined to determine which obligations would need review? | Reporting stream | 2021-10-10 |
| LEGAL-REVIEW-006 | Sigedis-related placeholder | Is the fictional scope sufficiently defined to determine which obligations would need review? | Former migration team | 2022-11-11 |
| LEGAL-REVIEW-007 | Branch 21 | Which invented fields must be replaced after an authoritative schema is selected? | Operations team | 2023-12-12 |
| LEGAL-REVIEW-008 | Branch 23 | Which invented fields must be replaced after an authoritative schema is selected? | Benefits stream | 2024-01-13 |
| LEGAL-REVIEW-009 | Sigedis-related placeholder | Which invented fields must be replaced after an authoritative schema is selected? | TBD | 2025-02-14 |
| LEGAL-REVIEW-010 | Branch 21 | Which invented fields must be replaced after an authoritative schema is selected? | Platform support | 2019-03-15 |
| LEGAL-REVIEW-011 | Branch 23 | Which invented fields must be replaced after an authoritative schema is selected? | Reporting stream | 2020-04-16 |
| LEGAL-REVIEW-012 | Sigedis-related placeholder | Which invented fields must be replaced after an authoritative schema is selected? | Former migration team | 2021-05-17 |
| LEGAL-REVIEW-013 | Branch 21 | Who approves the distinction between internal completion and external acceptance? | Operations team | 2022-06-18 |
| LEGAL-REVIEW-014 | Branch 23 | Who approves the distinction between internal completion and external acceptance? | Benefits stream | 2023-07-19 |
| LEGAL-REVIEW-015 | Sigedis-related placeholder | Who approves the distinction between internal completion and external acceptance? | TBD | 2024-08-20 |
| LEGAL-REVIEW-016 | Branch 21 | Who approves the distinction between internal completion and external acceptance? | Platform support | 2025-09-21 |
| LEGAL-REVIEW-017 | Branch 23 | Who approves the distinction between internal completion and external acceptance? | Reporting stream | 2019-10-22 |
| LEGAL-REVIEW-018 | Sigedis-related placeholder | Who approves the distinction between internal completion and external acceptance? | Former migration team | 2020-11-23 |
| LEGAL-REVIEW-019 | Branch 21 | Does any proposed retention behaviour require a separately validated policy? | Operations team | 2021-12-24 |
| LEGAL-REVIEW-020 | Branch 23 | Does any proposed retention behaviour require a separately validated policy? | Benefits stream | 2022-01-25 |
| LEGAL-REVIEW-021 | Sigedis-related placeholder | Does any proposed retention behaviour require a separately validated policy? | TBD | 2023-02-26 |
| LEGAL-REVIEW-022 | Branch 21 | Does any proposed retention behaviour require a separately validated policy? | Platform support | 2024-03-27 |
| LEGAL-REVIEW-023 | Branch 23 | Does any proposed retention behaviour require a separately validated policy? | Reporting stream | 2025-04-01 |
| LEGAL-REVIEW-024 | Sigedis-related placeholder | Does any proposed retention behaviour require a separately validated policy? | Former migration team | 2019-05-02 |
| LEGAL-REVIEW-025 | Branch 21 | Which draft labels could mislead a downstream document consumer? | Operations team | 2020-06-03 |
| LEGAL-REVIEW-026 | Branch 23 | Which draft labels could mislead a downstream document consumer? | Benefits stream | 2021-07-04 |
| LEGAL-REVIEW-027 | Sigedis-related placeholder | Which draft labels could mislead a downstream document consumer? | TBD | 2022-08-05 |
| LEGAL-REVIEW-028 | Branch 21 | Which draft labels could mislead a downstream document consumer? | Platform support | 2023-09-06 |
| LEGAL-REVIEW-029 | Branch 23 | Which draft labels could mislead a downstream document consumer? | Reporting stream | 2024-10-07 |
| LEGAL-REVIEW-030 | Sigedis-related placeholder | Which draft labels could mislead a downstream document consumer? | Former migration team | 2025-11-08 |
| LEGAL-REVIEW-031 | Branch 21 | What evidence would be needed before enabling any external use? | Operations team | 2019-12-09 |
| LEGAL-REVIEW-032 | Branch 23 | What evidence would be needed before enabling any external use? | Benefits stream | 2020-01-10 |
| LEGAL-REVIEW-033 | Sigedis-related placeholder | What evidence would be needed before enabling any external use? | TBD | 2021-02-11 |
| LEGAL-REVIEW-034 | Branch 21 | What evidence would be needed before enabling any external use? | Platform support | 2022-03-12 |
| LEGAL-REVIEW-035 | Branch 23 | What evidence would be needed before enabling any external use? | Reporting stream | 2023-04-13 |
| LEGAL-REVIEW-036 | Sigedis-related placeholder | What evidence would be needed before enabling any external use? | Former migration team | 2024-05-14 |
| LEGAL-REVIEW-037 | Branch 21 | Which stale assumptions must be explicitly rejected before implementation? | Operations team | 2025-06-15 |
| LEGAL-REVIEW-038 | Branch 23 | Which stale assumptions must be explicitly rejected before implementation? | Benefits stream | 2019-07-16 |
| LEGAL-REVIEW-039 | Sigedis-related placeholder | Which stale assumptions must be explicitly rejected before implementation? | TBD | 2020-08-17 |
| LEGAL-REVIEW-040 | Branch 21 | Which stale assumptions must be explicitly rejected before implementation? | Platform support | 2021-09-18 |
| LEGAL-REVIEW-041 | Branch 23 | Which stale assumptions must be explicitly rejected before implementation? | Reporting stream | 2022-10-19 |
| LEGAL-REVIEW-042 | Sigedis-related placeholder | Which stale assumptions must be explicitly rejected before implementation? | Former migration team | 2023-11-20 |

## Unconsolidated technical decision ledger

| Decision ID | Topic | Preserved fragment | State |
| --- | --- | --- | --- |
| TECH-001 | policy | Unknown values should enter a review queue; older importer silently defaults them. | Unresolved |
| TECH-002 | contract | The replay tool requires a stable sort, but archive exports omit the event sequence. | Superseded? |
| TECH-003 | employer | A local processing date was stored without a zone; do not invent one during migration. | Owner missing |
| TECH-004 | member | Source quality flags are absent from the oldest report shape. | Needs synthetic test |
| TECH-005 | contribution | Possibly obsolete: object version was once derived from export row order. | Unresolved |
| TECH-006 | beneficiary | Unknown values should enter a review queue; older importer silently defaults them. | Superseded? |
| TECH-007 | claim | The replay tool requires a stable sort, but archive exports omit the event sequence. | Owner missing |
| TECH-008 | payment | A local processing date was stored without a zone; do not invent one during migration. | Needs synthetic test |
| TECH-009 | document | Source quality flags are absent from the oldest report shape. | Unresolved |
| TECH-010 | audit event | Possibly obsolete: object version was once derived from export row order. | Superseded? |
| TECH-011 | report | Unknown values should enter a review queue; older importer silently defaults them. | Owner missing |
| TECH-012 | integration envelope | The replay tool requires a stable sort, but archive exports omit the event sequence. | Needs synthetic test |
| TECH-013 | policy | A local processing date was stored without a zone; do not invent one during migration. | Unresolved |
| TECH-014 | contract | Source quality flags are absent from the oldest report shape. | Superseded? |
| TECH-015 | employer | Possibly obsolete: object version was once derived from export row order. | Owner missing |
| TECH-016 | member | Unknown values should enter a review queue; older importer silently defaults them. | Needs synthetic test |
| TECH-017 | contribution | The replay tool requires a stable sort, but archive exports omit the event sequence. | Unresolved |
| TECH-018 | beneficiary | A local processing date was stored without a zone; do not invent one during migration. | Superseded? |
| TECH-019 | claim | Source quality flags are absent from the oldest report shape. | Owner missing |
| TECH-020 | payment | Possibly obsolete: object version was once derived from export row order. | Needs synthetic test |
| TECH-021 | document | Unknown values should enter a review queue; older importer silently defaults them. | Unresolved |
| TECH-022 | audit event | The replay tool requires a stable sort, but archive exports omit the event sequence. | Superseded? |
| TECH-023 | report | A local processing date was stored without a zone; do not invent one during migration. | Owner missing |
| TECH-024 | integration envelope | Source quality flags are absent from the oldest report shape. | Needs synthetic test |
| TECH-025 | policy | Possibly obsolete: object version was once derived from export row order. | Unresolved |
| TECH-026 | contract | Unknown values should enter a review queue; older importer silently defaults them. | Superseded? |
| TECH-027 | employer | The replay tool requires a stable sort, but archive exports omit the event sequence. | Owner missing |
| TECH-028 | member | A local processing date was stored without a zone; do not invent one during migration. | Needs synthetic test |
| TECH-029 | contribution | Source quality flags are absent from the oldest report shape. | Unresolved |
| TECH-030 | beneficiary | Possibly obsolete: object version was once derived from export row order. | Superseded? |
| TECH-031 | claim | Unknown values should enter a review queue; older importer silently defaults them. | Owner missing |
| TECH-032 | payment | The replay tool requires a stable sort, but archive exports omit the event sequence. | Needs synthetic test |
| TECH-033 | document | A local processing date was stored without a zone; do not invent one during migration. | Unresolved |
| TECH-034 | audit event | Source quality flags are absent from the oldest report shape. | Superseded? |
| TECH-035 | report | Possibly obsolete: object version was once derived from export row order. | Owner missing |
| TECH-036 | integration envelope | Unknown values should enter a review queue; older importer silently defaults them. | Needs synthetic test |
| TECH-037 | policy | The replay tool requires a stable sort, but archive exports omit the event sequence. | Unresolved |
| TECH-038 | contract | A local processing date was stored without a zone; do not invent one during migration. | Superseded? |
| TECH-039 | employer | Source quality flags are absent from the oldest report shape. | Owner missing |
| TECH-040 | member | Possibly obsolete: object version was once derived from export row order. | Needs synthetic test |
| TECH-041 | contribution | Unknown values should enter a review queue; older importer silently defaults them. | Unresolved |
| TECH-042 | beneficiary | The replay tool requires a stable sort, but archive exports omit the event sequence. | Superseded? |
| TECH-043 | claim | A local processing date was stored without a zone; do not invent one during migration. | Owner missing |
| TECH-044 | payment | Source quality flags are absent from the oldest report shape. | Needs synthetic test |
| TECH-045 | document | Possibly obsolete: object version was once derived from export row order. | Unresolved |
| TECH-046 | audit event | Unknown values should enter a review queue; older importer silently defaults them. | Superseded? |
| TECH-047 | report | The replay tool requires a stable sort, but archive exports omit the event sequence. | Owner missing |
| TECH-048 | integration envelope | A local processing date was stored without a zone; do not invent one during migration. | Needs synthetic test |
| TECH-049 | policy | Source quality flags are absent from the oldest report shape. | Unresolved |
| TECH-050 | contract | Possibly obsolete: object version was once derived from export row order. | Superseded? |
| TECH-051 | employer | Unknown values should enter a review queue; older importer silently defaults them. | Owner missing |
| TECH-052 | member | The replay tool requires a stable sort, but archive exports omit the event sequence. | Needs synthetic test |
| TECH-053 | contribution | A local processing date was stored without a zone; do not invent one during migration. | Unresolved |
| TECH-054 | beneficiary | Source quality flags are absent from the oldest report shape. | Superseded? |
| TECH-055 | claim | Possibly obsolete: object version was once derived from export row order. | Owner missing |
| TECH-056 | payment | Unknown values should enter a review queue; older importer silently defaults them. | Needs synthetic test |
| TECH-057 | document | The replay tool requires a stable sort, but archive exports omit the event sequence. | Unresolved |
| TECH-058 | audit event | A local processing date was stored without a zone; do not invent one during migration. | Superseded? |
| TECH-059 | report | Source quality flags are absent from the oldest report shape. | Owner missing |
| TECH-060 | integration envelope | Possibly obsolete: object version was once derived from export row order. | Needs synthetic test |
| TECH-061 | policy | Unknown values should enter a review queue; older importer silently defaults them. | Unresolved |
| TECH-062 | contract | The replay tool requires a stable sort, but archive exports omit the event sequence. | Superseded? |
| TECH-063 | employer | A local processing date was stored without a zone; do not invent one during migration. | Owner missing |
| TECH-064 | member | Source quality flags are absent from the oldest report shape. | Needs synthetic test |
| TECH-065 | contribution | Possibly obsolete: object version was once derived from export row order. | Unresolved |
| TECH-066 | beneficiary | Unknown values should enter a review queue; older importer silently defaults them. | Superseded? |
| TECH-067 | claim | The replay tool requires a stable sort, but archive exports omit the event sequence. | Owner missing |
| TECH-068 | payment | A local processing date was stored without a zone; do not invent one during migration. | Needs synthetic test |
| TECH-069 | document | Source quality flags are absent from the oldest report shape. | Unresolved |
| TECH-070 | audit event | Possibly obsolete: object version was once derived from export row order. | Superseded? |
| TECH-071 | report | Unknown values should enter a review queue; older importer silently defaults them. | Owner missing |
| TECH-072 | integration envelope | The replay tool requires a stable sort, but archive exports omit the event sequence. | Needs synthetic test |
| TECH-073 | policy | A local processing date was stored without a zone; do not invent one during migration. | Unresolved |
| TECH-074 | contract | Source quality flags are absent from the oldest report shape. | Superseded? |
| TECH-075 | employer | Possibly obsolete: object version was once derived from export row order. | Owner missing |
| TECH-076 | member | Unknown values should enter a review queue; older importer silently defaults them. | Needs synthetic test |
| TECH-077 | contribution | The replay tool requires a stable sort, but archive exports omit the event sequence. | Unresolved |
| TECH-078 | beneficiary | A local processing date was stored without a zone; do not invent one during migration. | Superseded? |
| TECH-079 | claim | Source quality flags are absent from the oldest report shape. | Owner missing |
| TECH-080 | payment | Possibly obsolete: object version was once derived from export row order. | Needs synthetic test |
| TECH-081 | document | Unknown values should enter a review queue; older importer silently defaults them. | Unresolved |
| TECH-082 | audit event | The replay tool requires a stable sort, but archive exports omit the event sequence. | Superseded? |
| TECH-083 | report | A local processing date was stored without a zone; do not invent one during migration. | Owner missing |
| TECH-084 | integration envelope | Source quality flags are absent from the oldest report shape. | Needs synthetic test |
| TECH-085 | policy | Possibly obsolete: object version was once derived from export row order. | Unresolved |
| TECH-086 | contract | Unknown values should enter a review queue; older importer silently defaults them. | Superseded? |
| TECH-087 | employer | The replay tool requires a stable sort, but archive exports omit the event sequence. | Owner missing |
| TECH-088 | member | A local processing date was stored without a zone; do not invent one during migration. | Needs synthetic test |
| TECH-089 | contribution | Source quality flags are absent from the oldest report shape. | Unresolved |
| TECH-090 | beneficiary | Possibly obsolete: object version was once derived from export row order. | Superseded? |
| TECH-091 | claim | Unknown values should enter a review queue; older importer silently defaults them. | Owner missing |
| TECH-092 | payment | The replay tool requires a stable sort, but archive exports omit the event sequence. | Needs synthetic test |
| TECH-093 | document | A local processing date was stored without a zone; do not invent one during migration. | Unresolved |
| TECH-094 | audit event | Source quality flags are absent from the oldest report shape. | Superseded? |
| TECH-095 | report | Possibly obsolete: object version was once derived from export row order. | Owner missing |
| TECH-096 | integration envelope | Unknown values should enter a review queue; older importer silently defaults them. | Needs synthetic test |
| TECH-097 | policy | The replay tool requires a stable sort, but archive exports omit the event sequence. | Unresolved |
| TECH-098 | contract | A local processing date was stored without a zone; do not invent one during migration. | Superseded? |
| TECH-099 | employer | Source quality flags are absent from the oldest report shape. | Owner missing |
| TECH-100 | member | Possibly obsolete: object version was once derived from export row order. | Needs synthetic test |
