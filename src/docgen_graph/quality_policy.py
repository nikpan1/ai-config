import math
from collections.abc import Iterable


def evaluate_coverage(
    expected_ids: Iterable[str],
    represented_ids: Iterable[str],
    minimum_coverage: float = 1.0,
) -> dict:
    if not math.isfinite(minimum_coverage) or not 0 < minimum_coverage <= 1:
        raise ValueError("Minimum coverage must be greater than zero and at most one")
    expected = set(expected_ids)
    represented = set(represented_ids)
    covered = expected & represented
    omitted = expected - represented
    unexpected = represented - expected
    ratio = len(covered) / len(expected) if expected else 1.0
    return {
        "total": len(expected),
        "represented": len(covered),
        "coverage_ratio": ratio,
        "minimum_coverage": minimum_coverage,
        "omitted_ids": sorted(omitted),
        "unexpected_ids": sorted(unexpected),
        "complete": not omitted and not unexpected,
        "accepted": ratio >= minimum_coverage and not unexpected,
    }


def coverage_audit_findings(
    findings: list[str], omitted_ids: Iterable[str], accepted: bool
) -> list[str]:
    if not accepted:
        return list(findings)
    tolerated = {f"Unresolved source aspect: {key}" for key in omitted_ids}
    return [finding for finding in findings if finding not in tolerated]
