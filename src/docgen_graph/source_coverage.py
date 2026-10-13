import re

from docgen_graph.quality_policy import coverage_audit_findings, evaluate_coverage
from docgen_graph.storage import digest


def validate_aspect_inventory(aspects: list[dict], spans: dict) -> tuple[list[dict], list[str]]:
    normalized, findings = [], []
    for aspect in aspects:
        evidence = spans.get(aspect["evidence_id"])
        if not evidence or aspect["quote"] not in evidence["text"]:
            findings.append(f"Aspect quote does not resolve: {aspect['evidence_id']}")
            continue
        start = evidence["text"].index(aspect["quote"])
        normalized.append(
            {
                **aspect,
                "id": digest([aspect["evidence_id"], start, aspect["kind"], aspect["quote"]])[:24],
                "start": start,
                "end": start + len(aspect["quote"]),
            }
        )
    return normalized, findings


def audit_decisions(
    aspects: list[dict],
    decisions: list[dict],
    facts: list[dict],
    minimum_coverage: float = 1.0,
) -> list[str]:
    findings = []
    expected = {item["id"]: item for item in aspects}
    actual = {item["aspect_id"]: item for item in decisions}
    facts_by_id = {item["id"]: item for item in facts}
    if len(expected) != len(aspects):
        findings.append("Source aspect inventory contains duplicate identifiers")
    if set(expected) != set(actual) or len(actual) != len(decisions):
        findings.append("Source audit must account for every aspect exactly once")
    represented = set()
    for key, decision in actual.items():
        if key not in expected:
            continue
        if decision["status"] not in {"represented", "duplicate", "unresolved"}:
            findings.append(f"Unknown source aspect disposition: {key}")
        elif decision["status"] == "unresolved" or not decision["fact_ids"]:
            findings.append(f"Unresolved source aspect: {key}")
        else:
            represented.add(key)
        for fact_id in decision["fact_ids"]:
            fact = facts_by_id.get(fact_id)
            if not fact or expected[key]["evidence_id"] not in fact["evidence_ids"]:
                findings.append(f"Aspect mapping lacks its original source: {key}")
                represented.discard(key)
    policy = evaluate_coverage(expected, represented, minimum_coverage)
    return coverage_audit_findings(findings, policy["omitted_ids"], policy["accepted"])


def source_audit_findings(
    aspects: list[dict],
    decisions: list[dict],
    facts: list[dict],
    *,
    all_aspects: list[dict],
    prior_decisions: list[dict],
    minimum_coverage: float = 1.0,
) -> list[str]:
    findings = audit_decisions(aspects, decisions, facts)
    expected = {item["id"] for item in all_aspects}
    combined = prior_decisions + decisions
    decided = {item["aspect_id"] for item in combined}
    if len(expected) != len(all_aspects):
        findings.append("Complete source aspect inventory contains duplicate identifiers")
    if len(decided) != len(combined) or not decided.issubset(expected):
        findings.append("Source audit batches must account for distinct original aspects")
    omitted = {
        item["aspect_id"]
        for item in combined
        if item["status"] == "unresolved" or not item["fact_ids"]
    }
    policy = evaluate_coverage(expected, expected - omitted, minimum_coverage)
    return coverage_audit_findings(findings, omitted, policy["accepted"])


def protected_values(text: str) -> set[str]:
    return set(
        re.findall(
            r"\b\d+(?:[.,]\d+)?\s*(?:%|mm|cm|km|ms|kg|days?|hours?|minutes?|seconds?|PLN|EUR|USD)\b"
            r"|\b(?:only|must|may|cannot|never|unless|except|before|after|at least|at most)\b",
            text,
            re.I,
        )
    )


def editorial_findings(original: str, edited: str) -> list[str]:
    before = {value.casefold() for value in protected_values(original)}
    after = {value.casefold() for value in protected_values(edited)}
    findings = []
    missing = before - after
    if missing:
        findings.append(f"Editorial change requires qualifier audit: {sorted(missing)}")
    cause = (
        r"\b(?:because|therefore|in order to|for security|for compliance|to improve performance)\b"
    )
    if len(re.findall(cause, edited, re.I)) > len(re.findall(cause, original, re.I)):
        findings.append("New causal relationship requires independent source support")
    return findings


def coverage_report(
    aspects: list[dict],
    decisions: list[dict],
    mapped: set[str],
    snapshot_id: str,
    revision: str,
    attachments: list[dict],
    minimum_coverage: float = 1.0,
) -> dict:
    expected = {item["id"]: item for item in aspects}
    actual = {item["aspect_id"]: item for item in decisions}
    represented = {
        item["aspect_id"]
        for item in decisions
        if item["status"] in {"represented", "duplicate"}
        and item["fact_ids"]
        and set(item["fact_ids"]).issubset(mapped)
    }
    integrity_findings = []
    if len(expected) != len(aspects):
        integrity_findings.append("Source aspect inventory contains duplicate identifiers")
    if set(expected) != set(actual) or len(actual) != len(decisions):
        integrity_findings.append("Source audit must account for every aspect exactly once")
    if any(item["status"] not in {"represented", "duplicate", "unresolved"} for item in decisions):
        integrity_findings.append("Source audit contains an unknown disposition")
    policy = evaluate_coverage(expected, represented, minimum_coverage)
    qualified = {
        item["id"]
        for item in aspects
        if item["kind"] in {"condition", "exception", "boundary", "role", "order"}
    }
    unresolved_attachments = [item["path"] for item in attachments if item.get("status") != "ok"]
    return {
        "snapshot_id": snapshot_id,
        "graph_revision": revision,
        "aspects": {"total": policy["total"], "represented": policy["represented"]},
        "qualifiers": {
            "total": len(qualified),
            "represented": len(qualified & represented),
            "coverage_ratio": len(qualified & represented) / len(qualified) if qualified else 1.0,
        },
        "blocks": {"total": len({item["evidence_id"] for item in aspects})},
        "unresolved_attachments": unresolved_attachments,
        "coverage_ratio": policy["coverage_ratio"],
        "minimum_coverage": minimum_coverage,
        "omitted_aspects": [
            {
                **expected[key],
                "reason": actual.get(key, {}).get("reason") or "No mapped supporting facts",
                "fact_ids": actual.get(key, {}).get("fact_ids", []),
            }
            for key in policy["omitted_ids"]
        ],
        "integrity_findings": integrity_findings,
        "complete": policy["complete"] and not unresolved_attachments and not integrity_findings,
        "accepted": policy["accepted"] and not unresolved_attachments and not integrity_findings,
    }
