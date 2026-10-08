from pathlib import Path

from docgen.storage import atomic_write, digest, write_json


def main():
    root = Path("data/legacy-insurance")
    samples = []

    def add(filename, needle, facts, qualifications=(), distinctions=()):
        raw = (root / filename).read_bytes()
        lines = raw.decode("utf-8").splitlines()
        number = next(index for index, line in enumerate(lines, 1) if needle in line)
        samples.append(
            {
                "id": f"reference-{len(samples) + 1:02}",
                "path": filename,
                "snapshot": digest(raw),
                "line_start": number,
                "line_end": number,
                "excerpt": lines[number - 1],
                "expected_facts": list(facts),
                "qualifications": list(qualifications),
                "entity_distinctions": list(distinctions),
                "split": "held_out" if (len(samples) + 1) % 4 == 0 else "development",
            }
        )

    product = "product-and-feature-register.md"
    functional = "functional-specification.md"
    integration = "integration-data-and-compliance.md"
    add(
        product,
        "Northstar Benefits Platform is",
        [
            "The fictional platform was called benefit desk, policy hub, "
            "employer console and pension admin.",
            "The old names remain because index filters disagree.",
        ],
        ["Fictional platform; aliases are historical, not distinct implementations."],
    )
    add(
        product,
        "The register describes supposed behaviour",
        [
            "Descriptions are supposed behavior, not implemented capability.",
            "Status labels were copied between invented migration waves and are "
            "not release evidence.",
        ],
    )
    add(
        product,
        "Policy and contract are sometimes",
        [
            "Policy and contract sometimes refer to the same object.",
            "Accounting and coverage boundaries have not been reconciled.",
        ],
        distinctions=["Policy and contract must not be unconditionally merged."],
    )
    add(
        product,
        "Branch 21 and Branch 23 are catalogue",
        [
            "Branch 21 and Branch 23 are catalogue labels awaiting review.",
            "Sigedis work is a disabled placeholder; no legal meaning is assigned.",
        ],
    )
    actors = [
        (
            "Employer operator",
            "One synthetic employer",
            "Scope inheritance missing",
            "Operations team",
        ),
        (
            "Benefits operator",
            "One plan revision",
            "Old screen calls this administrator",
            "Benefits stream",
        ),
        ("Claims reviewer", "Assigned queue", "Batch access not reconciled", "TBD"),
        (
            "Payment reviewer",
            "Read-only historical view",
            "Scope inheritance missing",
            "Platform support",
        ),
        (
            "Report operator",
            "One synthetic employer",
            "Old screen calls this administrator",
            "Reporting stream",
        ),
        (
            "Tenant administrator",
            "One plan revision",
            "Batch access not reconciled",
            "Former migration team",
        ),
        ("Audit reader", "Assigned queue", "Scope inheritance missing", "Operations team"),
        (
            "Batch identity",
            "Read-only historical view",
            "Old screen calls this administrator",
            "Benefits stream",
        ),
        ("Document reviewer", "One synthetic employer", "Batch access not reconciled", "TBD"),
        ("Support operator", "One plan revision", "Scope inheritance missing", "Platform support"),
        (
            "Configuration reviewer",
            "Assigned queue",
            "Old screen calls this administrator",
            "Reporting stream",
        ),
        (
            "Migration observer",
            "Read-only historical view",
            "Batch access not reconciled",
            "Former migration team",
        ),
    ]
    for actor, scope, ambiguity, owner in actors:
        add(
            product,
            f"| {actor} |",
            [
                f"Actor label: {actor}.",
                f"Approximate scope: {scope}.",
                f"Known ambiguity: {ambiguity}.",
                f"Review owner: {owner}.",
            ],
            ["Approximate scope, not confirmed permission behavior."],
            ["Shared administrator label does not prove roles are identical."]
            if "administrator" in ambiguity
            else [],
        )
    add(
        functional,
        "“Must” indicates",
        ["Must denotes a historical draft rule, not verified implementation."],
    )
    add(
        functional,
        "This section requires: Effective date",
        ["F-001 requires the effective date to equal the recorded approval date."],
        ["Draft rule; incompatible with F-002 and no authority selected."],
    )
    add(
        functional,
        "Resolution: not agreed.",
        [
            "Both incompatible statements are fixture inputs and resolution is not agreed.",
            "Neither statement silently supersedes the other.",
        ],
    )
    rules = [
        ("RULE-001:", "Effective date must equal the recorded approval date."),
        ("RULE-002:", "A proposed policy has no payable balance."),
        ("RULE-003:", "The policy must carry a synthetic tenant scope before any lookup."),
        (
            "RULE-004:",
            "An exact replay uses the original logical request key; changed "
            "content under it goes to a discrepancy queue.",
        ),
        (
            "RULE-005:",
            "Preserve the input revision on downstream failure; screen success "
            "behavior is unresolved.",
        ),
        (
            "RULE-006:",
            "An operator may request rollback, but cancellation versus "
            "compensating entry is undefined.",
        ),
    ]
    for needle, fact in rules:
        add(functional, needle, [fact], ["Historical draft rule, not implementation evidence."])
    add(
        functional,
        "Edge case: a policy updated",
        [
            "An update just before batch cutoff can appear in a report but be "
            "absent from the next queue.",
            "No ordering contract was agreed.",
        ],
    )
    add(
        functional,
        "Edge case: an empty attachment list",
        [
            "An empty attachment list means not supplied in UI but clear "
            "existing attachments in an old import note.",
            "This ambiguity must remain visible for migration review.",
        ],
    )
    add(
        integration,
        "Null, omitted, and empty string",
        [
            "Null, omitted and empty string are distinct in the canonical proposal.",
            "Old CSV import sometimes merges them.",
        ],
        ["Canonical proposal, not guaranteed implementation."],
    )
    add(
        integration,
        "The policy record is",
        [
            "Policy is a fictional persistence boundary; its older export "
            "counterpart is called contract.",
            "The rename was not propagated to reports.",
        ],
        distinctions=["Do not erase policy/contract scope distinctions."],
    )
    fields = [
        (
            "DATA-001",
            "fixture_key",
            "opaque text",
            "Required",
            "Synthetic record reference; never a policy number or real identity",
            "Possibly obsolete",
        ),
        (
            "DATA-002",
            "tenant_scope",
            "opaque text",
            "Required",
            "Partition boundary used before any business lookup",
            "Duplicate alias",
        ),
        (
            "DATA-003",
            "revision_no",
            "integer",
            "Required",
            "Monotonic within this fixture object, not across entities",
            "Unreviewed",
        ),
        (
            "DATA-004",
            "state_code",
            "enum text",
            "Required",
            "Draft state vocabulary depends on the owning feature",
            "Draft",
        ),
        (
            "DATA-005",
            "effective_on",
            "date text",
            "Conditional",
            "Business effective date; missing date interpretation unresolved",
            "Possibly obsolete",
        ),
        (
            "DATA-006",
            "recorded_at",
            "timestamp text",
            "Required",
            "Processing timestamp; source zone missing in old import",
            "Duplicate alias",
        ),
        (
            "DATA-007",
            "source_ref",
            "opaque text",
            "Optional",
            "Reference to the internal staging envelope",
            "Unreviewed",
        ),
        (
            "DATA-008",
            "previous_ref",
            "opaque text",
            "Optional",
            "Predecessor revision; must not form a cycle",
            "Draft",
        ),
        (
            "DATA-009",
            "owner_queue",
            "enum text",
            "Optional",
            "Queue label rather than a named individual",
            "Possibly obsolete",
        ),
        (
            "DATA-010",
            "review_status",
            "enum text",
            "Required",
            "Review completeness is separate from business approval",
            "Duplicate alias",
        ),
        (
            "DATA-011",
            "reason_code",
            "enum text",
            "Conditional",
            "Code values differ between the old desk and the new queue",
            "Unreviewed",
        ),
    ]
    for identifier, field, data_type, presence, meaning, quality in fields:
        add(
            integration,
            f"| {identifier} |",
            [
                f"{identifier}: policy field {field}.",
                f"Draft type: {data_type}; presence: {presence}.",
                meaning,
                f"Source quality: {quality}.",
            ],
            ["Draft data contract; preserve conditional or optional presence."],
        )
    assert len(samples) == 40
    reference = {
        "version": 1,
        "prepared_by": "Codex",
        "review_status": "provisional",
        "user_reviewed": False,
        "samples": samples,
    }
    write_json(Path("evaluation/reference.json"), reference)
    lines = [
        "# Provisional evaluation reference",
        "",
        "40 annotated passages: 30 development and 10 held out.",
        "Prepared autonomously from synthetic source material. User review has not occurred.",
        "Exploratory evaluation is allowed; acceptance must not be claimed "
        "against this unapproved set.",
        "",
    ]
    for sample in samples:
        lines.extend(
            [
                f"## {sample['id']} ({sample['split']})",
                "",
                f"Source: {sample['path']}:{sample['line_start']}",
                "",
                sample["excerpt"],
                "",
            ]
        )
        lines.extend(
            f"- {fact}"
            for fact in sample["expected_facts"]
            + sample["qualifications"]
            + sample["entity_distinctions"]
        )
        lines.append("")
    atomic_write(Path("evaluation/reference-review.md"), "\n".join(lines))


if __name__ == "__main__":
    main()
