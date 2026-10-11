import re

from docgen.contracts import Batch, Block, Extraction, Finding


def finding(kind, description, blocks=(), records=()):
    return Finding(
        kind=kind, description=description, block_ids=list(blocks), record_ids=list(records)
    )


def validate_extraction(
    result: Extraction, batch: Batch, blocks: dict[str, Block]
) -> list[Finding]:
    findings = []
    allowed = set(batch.owned + batch.context)
    claim_ids = [claim.id for claim in result.claims]
    entity_ids = [entity.id for entity in result.entities]
    if len(set(claim_ids + entity_ids)) != len(claim_ids + entity_ids):
        findings.append(finding("unsupported", "Record IDs must be unique"))
    for record in [*result.claims, *result.entities]:
        for evidence in record.evidence:
            if evidence.block_id not in allowed:
                findings.append(
                    finding(
                        "unsupported",
                        "Evidence references an unavailable source block",
                        records=[record.id],
                    )
                )
            elif evidence.excerpt not in blocks[evidence.block_id].content:
                findings.append(
                    finding(
                        "unsupported",
                        "Evidence excerpt is not an exact source substring",
                        [evidence.block_id],
                        [record.id],
                    )
                )
    for claim in result.claims:
        if not set(claim.entities) <= set(entity_ids):
            findings.append(
                finding("unsupported", "Claim references unknown entities", records=[claim.id])
            )
        if not {e.block_id for e in claim.evidence} & set(batch.owned):
            findings.append(
                finding("unsupported", "Claim has no owned-source evidence", records=[claim.id])
            )
    coverage_ids = [coverage.block_id for coverage in result.coverage]
    if len(coverage_ids) != len(set(coverage_ids)) or set(coverage_ids) != set(batch.owned):
        findings.append(
            finding(
                "omission",
                "Coverage must account for every owned block exactly once",
                set(batch.owned) - set(coverage_ids),
            )
        )
    claims = {claim.id: claim for claim in result.claims}
    for coverage in result.coverage:
        if not set(coverage.claim_ids) <= set(claims):
            findings.append(
                finding("unsupported", "Coverage references unknown claims", [coverage.block_id])
            )
        if coverage.disposition == "represented":
            supported = [
                key
                for key in coverage.claim_ids
                if key in claims and coverage.block_id in {e.block_id for e in claims[key].evidence}
            ]
            if not supported or len(supported) != len(coverage.claim_ids):
                findings.append(
                    finding(
                        "omission", "Represented block lacks supporting claims", [coverage.block_id]
                    )
                )
        if coverage.disposition == "duplicate":
            target = coverage.duplicate_of
            if target not in allowed or target == coverage.block_id:
                findings.append(
                    finding("unsupported", "Invalid duplicate target", [coverage.block_id])
                )
            elif blocks[target].content != blocks[coverage.block_id].content:
                findings.append(
                    finding(
                        "unsupported",
                        "Nonidentical duplicate requires represented claims",
                        [coverage.block_id],
                    )
                )
        if coverage.disposition == "excluded" and coverage.block_id in blocks:
            block = blocks[coverage.block_id]
            structural = block.kind == "heading" or (
                block.kind == "table" and block.table_row in {0, 1}
            )
            structural = structural or bool(
                re.fullmatch(r"\s*<a\s+id=[\"\'][^\"\']+[\"\']\s*>\s*</a>\s*", block.content)
            )
            structural = structural or (
                block.kind == "bullet_list"
                and all(
                    not line.strip() or re.fullmatch(r"\s*[-*+] \[[^\]]+\]\([^\n]+\)\s*", line)
                    for line in block.content.splitlines()
                )
            )
            if not structural:
                findings.append(
                    finding(
                        "omission",
                        "Exclusion of nonstructural source requires review",
                        [coverage.block_id],
                    )
                )
        if coverage.disposition == "unresolved":
            findings.append(finding("source_issue", coverage.explanation, [coverage.block_id]))
    all_ids = set(claim_ids + entity_ids)
    for item in result.findings:
        if not set(item.block_ids) <= allowed or not set(item.record_ids) <= all_ids:
            findings.append(
                finding("unsupported", "Finding references unknown source or record IDs")
            )
    return findings


def qualify_ids(result: Extraction, batch_id: str) -> Extraction:
    mapping = {
        record.id: f"{batch_id}:{record.id}" for record in [*result.claims, *result.entities]
    }
    value = result.model_dump()
    for claim in value["claims"]:
        claim["id"] = mapping[claim["id"]]
        claim["entities"] = [mapping[key] for key in claim["entities"]]
        claim["review_status"] = "verified"
    for entity in value["entities"]:
        entity["id"] = mapping[entity["id"]]
        entity["review_status"] = "verified"
    for coverage in value["coverage"]:
        coverage["claim_ids"] = [mapping[key] for key in coverage["claim_ids"]]
    for item in value["findings"]:
        item["record_ids"] = [mapping[key] for key in item["record_ids"]]
    return Extraction.model_validate(value)


def validate_duplicate_chains(coverage: list[dict]) -> bool:
    lookup = {item["block_id"]: item for item in coverage}
    for item in coverage:
        seen = set()
        while item["disposition"] == "duplicate":
            if item["block_id"] in seen or item["duplicate_of"] not in lookup:
                return False
            seen.add(item["block_id"])
            item = lookup[item["duplicate_of"]]
        if item["disposition"] not in {"represented", "excluded"}:
            return False
    return True
