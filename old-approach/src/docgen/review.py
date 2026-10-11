from docgen.contracts import Block, Decision, Issue
from docgen.storage import Artifacts, digest


def make_issues(stage: str, revision: str, findings: list[dict]) -> list[dict]:
    issues = []
    for item in findings:
        issue = Issue(
            id="issue-" + digest([stage, revision, item])[:20],
            stage=stage,
            revision=revision,
            kind=item["kind"],
            description=item["description"],
            block_ids=item.get("block_ids", []),
            record_ids=item.get("record_ids", []),
            source_path=item.get("path"),
        )
        issues.append(issue.model_dump())
    return issues


def report(issues: list[dict], blocks: dict[str, Block], revision: str) -> str:
    lines = [
        "# Knowledge review",
        "",
        f"Artifact revision: `{revision}`",
        "",
        "Open issues block finalization. Decisions must name this revision and a reviewer.",
        "",
    ]
    for value in issues:
        issue = Issue.model_validate(value)
        lines.extend(
            [
                f"## {issue.id}",
                "",
                f"Stage: {issue.stage}; type: {issue.kind}",
                "",
                issue.description,
                "",
                f"Records: {', '.join(issue.record_ids) or 'None'}",
                "",
            ]
        )
        if issue.source_path:
            lines.extend([f"Source asset: {issue.source_path}", ""])
        for key in issue.block_ids:
            block = blocks.get(key)
            if block:
                lines.extend(
                    [
                        f"### {block.path}:{block.line_start}-{block.line_end}",
                        "",
                        f"Snapshot: `{block.snapshot}`; block: `{block.id}`",
                        "",
                        "````markdown",
                        block.content.rstrip(),
                        "````",
                        "",
                    ]
                )
    return "\n".join(lines)


def validate_decisions(values: list[dict], issues: list[dict], revision: str) -> list[Decision]:
    decisions = [Decision.model_validate(value) for value in values]
    open_issues = {issue["id"]: issue for issue in issues}
    if len({decision.issue_id for decision in decisions}) != len(decisions):
        raise ValueError("Only one decision per issue is allowed")
    for decision in decisions:
        if decision.revision != revision or decision.issue_id not in open_issues:
            raise ValueError("Decision does not match the current artifact revision and issue")
        issue = open_issues[decision.issue_id]
        if issue.get("stage") == "finalize_knowledge" and decision.action != "defer":
            raise ValueError("Final integrity failures cannot be waived by a review decision")
        if decision.action == "select_authority":
            if issue["kind"] != "conflict" or not decision.claim_ids:
                raise ValueError("Authority selection needs a conflict and selected claims")
            if not set(decision.claim_ids) <= set(issue["record_ids"]):
                raise ValueError("Selected claims must be among the conflicting records")
        elif decision.action == "explain_asset":
            if issue["kind"] != "asset" or not decision.explanation:
                raise ValueError("Asset explanation must be attributed and nonempty")
        elif decision.action == "keep_distinct":
            if issue["kind"] != "ambiguous_entity" or len(set(issue["record_ids"])) < 2:
                raise ValueError(
                    "Keep-distinct requires two separate ambiguous entities; "
                    "otherwise correct the draft"
                )
        elif decision.action == "merge_entities":
            if (
                issue["kind"] != "ambiguous_entity"
                or len(decision.entity_ids) < 2
                or not set(decision.entity_ids) <= set(issue["record_ids"])
            ):
                raise ValueError(
                    "Merge requires at least two entity IDs from the reviewed ambiguity"
                )
        elif decision.action == "acknowledge_unknown":
            if issue["kind"] not in {"source_issue", "missing_context", "missing_link"}:
                raise ValueError(
                    "Acknowledging unknowns cannot approve unsupported facts or conflicts"
                )
        elif decision.action == "correct" and decision.replacement is None:
            raise ValueError("Correction requires a complete replacement extraction")
        elif decision.action == "exclude" and issue["kind"] not in {
            "asset",
            "unreadable",
            "empty_source",
        }:
            raise ValueError("Claims must be corrected with evidence, not approved or discarded")
    return decisions


def persist_decisions(store: Artifacts, previous_ref: str | None, decisions: list[Decision]) -> str:
    previous = store.get(previous_ref) if previous_ref else []
    by_id = {digest(item): item for item in previous}
    for decision in decisions:
        value = decision.model_dump()
        by_id[digest(value)] = value
    return store.put(list(by_id.values()), "decisions")
