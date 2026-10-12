import re

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


def audit_decisions(aspects: list[dict], decisions: list[dict], facts: list[dict]) -> list[str]:
    findings = []
    expected = {item["id"]: item for item in aspects}
    actual = {item["aspect_id"]: item for item in decisions}
    facts_by_id = {item["id"]: item for item in facts}
    if set(expected) != set(actual) or len(actual) != len(decisions):
        findings.append("Source audit must account for every aspect exactly once")
    for key, decision in actual.items():
        if key not in expected:
            continue
        if decision["status"] == "unresolved" or not decision["fact_ids"]:
            findings.append(f"Unresolved source aspect: {key}")
        for fact_id in decision["fact_ids"]:
            fact = facts_by_id.get(fact_id)
            if not fact or expected[key]["evidence_id"] not in fact["evidence_ids"]:
                findings.append(f"Aspect mapping lacks its original source: {key}")
    return findings


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
) -> dict:
    represented = [
        item
        for item in decisions
        if item["status"] in {"represented", "duplicate"}
        and item["fact_ids"]
        and set(item["fact_ids"]).issubset(mapped)
    ]
    qualified = {
        item["id"]
        for item in aspects
        if item["kind"] in {"condition", "exception", "boundary", "role", "order"}
    }
    unresolved_attachments = [item["path"] for item in attachments if item.get("status") != "ok"]
    return {
        "snapshot_id": snapshot_id,
        "graph_revision": revision,
        "aspects": {"total": len(aspects), "represented": len(represented)},
        "qualifiers": {
            "total": len(qualified),
            "represented": len(qualified & {item["aspect_id"] for item in represented}),
        },
        "blocks": {"total": len({item["evidence_id"] for item in aspects})},
        "unresolved_attachments": unresolved_attachments,
        "complete": len(represented) == len(aspects) and not unresolved_attachments,
    }
