from collections import defaultdict
from pathlib import Path

from markdown_it import MarkdownIt

from docgen.contracts import Batch, Block, Claim, Coverage, Decision, Entity, Relation
from docgen.planning_contracts import (
    ContentObligation,
    DocumentationBrief,
    PlanningInputs,
    TemplateSpan,
)
from docgen.reconciliation import entity_register
from docgen.storage import digest, read_json
from docgen.validation import validate_duplicate_chains


def resolve_reference(value, store, field, expected_status):
    if value.startswith("objects/"):
        ref = value
    else:
        path = Path(value).resolve()
        if not path.is_relative_to(store.root):
            raise ValueError("Cross-workspace import is unsupported; use the original workspace")
        manifest = read_json(path)
        if manifest.get("status") != expected_status or field not in manifest:
            raise ValueError(f"Manifest must identify a {expected_status} artifact with {field}")
        ref = manifest[field]
    try:
        result = store.get_object(ref)
    except FileNotFoundError:
        raise ValueError(f"Missing artifact {ref}; the manifest alone is insufficient") from None
    if result.get("status") != expected_status:
        raise ValueError(f"Input must have status={expected_status}")
    if not value.startswith("objects/") and manifest.get("revision") != digest(result):
        raise ValueError("Manifest revision does not match the immutable artifact")
    return ref, result


def validate_knowledge(bundle, store):
    required = {
        "schema_version",
        "signature",
        "snapshot_ref",
        "batches_ref",
        "claims",
        "entities",
        "entity_register",
        "canonical_entity_ids",
        "relationships",
        "coverage",
        "decisions",
        "resolved_issues",
        "entity_comparisons",
        "claim_comparisons",
        "reviewer_evidence",
        "unresolved_issues",
        "status",
    }
    if set(bundle) - required - {"selection_ref"} or required - set(bundle):
        raise ValueError("Unsupported knowledge bundle fields")
    if bundle["schema_version"] != "1" or not bundle["signature"]:
        raise ValueError("Unsupported knowledge schema or missing original signature")
    if bundle["unresolved_issues"]:
        raise ValueError("Unresolved knowledge issues block planning")
    snapshot = store.get_object(bundle["snapshot_ref"])
    blocks = {row["id"]: Block.model_validate(row) for row in snapshot["blocks"]}
    if len(blocks) != len(snapshot["blocks"]):
        raise ValueError("Duplicate block identities")
    inventory = {row["path"]: row for row in snapshot["inventory"]}
    for entry in inventory.values():
        if "ref" not in entry:
            continue
        raw = store.path(entry["ref"]).read_bytes()
        if digest(raw) != entry["snapshot"]:
            raise ValueError("Source snapshot checksum mismatch")
        if entry["status"] == "parsed":
            text = raw.decode("utf-8")
            for block in (b for b in blocks.values() if b.path == entry["path"]):
                if (
                    block.snapshot != entry["snapshot"]
                    or text[block.char_start : block.char_end] != block.content
                    or text[: block.char_start].count("\n") + 1 != block.line_start
                    or text[: max(block.char_start, block.char_end - 1)].count("\n") + 1
                    != block.line_end
                ):
                    raise ValueError("Source block does not match its exact snapshot location")
    if any(block.path not in inventory for block in blocks.values()):
        raise ValueError("Block path is absent from inherited source selection")
    ids = set()
    for kind, schema in (("claims", Claim), ("entities", Entity)):
        for row in bundle[kind]:
            record = schema.model_validate(row)
            if record.id in ids or record.review_status == "draft":
                raise ValueError("Duplicate or draft record in completed knowledge")
            ids.add(record.id)
            for evidence in record.evidence:
                block = blocks.get(evidence.block_id)
                if block is None or evidence.excerpt not in block.content:
                    raise ValueError("Knowledge evidence does not resolve to an exact excerpt")
    entity_ids = {row["id"] for row in bundle["entities"]}
    if any(set(row["entities"]) - entity_ids for row in bundle["claims"]):
        raise ValueError("Claim references missing entities")
    decisions = [Decision.model_validate(row).model_dump() for row in bundle["decisions"]]
    register, mapping = entity_register(bundle["entities"], decisions)
    if register != bundle["entity_register"] or mapping != bundle["canonical_entity_ids"]:
        raise ValueError("Entity register disagrees with effective review decisions")
    for row in bundle["relationships"]:
        relation = Relation.model_validate({k: v for k, v in row.items() if k != "revision"})
        if {relation.left, relation.right} - ids:
            raise ValueError("Relationship references missing records")
    coverage = [Coverage.model_validate(row).model_dump() for row in bundle["coverage"]]
    if (
        len(coverage) != len(blocks)
        or {r["block_id"] for r in coverage} != set(blocks)
        or not validate_duplicate_chains(coverage)
        or any(r["disposition"] == "unresolved" for r in coverage)
        or any(set(r["claim_ids"]) - {c["id"] for c in bundle["claims"]} for r in coverage)
    ):
        raise ValueError("Knowledge extraction coverage is incomplete or invalid")
    for row in store.get_object(bundle["batches_ref"]):
        if Batch.model_validate(row).status != "verified":
            raise ValueError("Knowledge has unverified extraction batches")
    actions = {row["issue_id"]: row for row in decisions}
    corrected_revisions = {row["revision"] for row in decisions if row["action"] == "correct"}
    rejected = set()
    for issue in bundle["resolved_issues"]:
        action = actions.get(issue["id"])
        if issue["status"] == "superseded" and issue["revision"] in corrected_revisions:
            continue
        if issue["status"] != "resolved" or action is None:
            raise ValueError("Incomplete knowledge decision history")
        if action["revision"] != issue["revision"] or action["action"] == "defer":
            raise ValueError("Stale knowledge decision")
        if action["action"] == "keep_distinct":
            members = [key for key in issue["record_ids"] if key in entity_ids]
            if len({mapping[key] for key in members}) != len(members):
                raise ValueError("Entity register erases an explicit keep-distinct decision")
        if action["action"] == "select_authority":
            rejected.update(set(issue["record_ids"]) - set(action["claim_ids"]))
    actual_rejected = {c["id"] for c in bundle["claims"] if c["review_status"] == "ineligible"}
    if actual_rejected != rejected.intersection(c["id"] for c in bundle["claims"]):
        raise ValueError("Claim eligibility disagrees with phase 1 authority decisions")
    for field in ("entity_comparisons", "claim_comparisons"):
        for ref in bundle[field].values():
            store.get_object(ref)
    return snapshot


def template_spans(text):
    lines = text.splitlines(keepends=True)
    tokens = MarkdownIt("commonmark").enable("table").parse(text)
    headings = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.level == 0:
            headings.append((token.map[0], int(token.tag[1:]), tokens[index + 1].content))
    points = [(0, 0, "Preamble")] if not headings or headings[0][0] else []
    points.extend(headings)
    stack, spans = [], []
    for index, (start, level, title) in enumerate(points):
        end = points[index + 1][0] if index + 1 < len(points) else len(lines)
        while stack and stack[-1][0] >= level:
            stack.pop()
        identifier = "template-" + digest([start, level, title])[:16]
        spans.append(
            TemplateSpan(
                id=identifier,
                line_start=start + 1,
                line_end=max(start + 1, end),
                heading=title,
                level=level,
                parent_id=stack[-1][1] if stack else None,
                text="".join(lines[start:end]),
            )
        )
        stack.append((level, identifier))
    return spans


def snapshot_inputs(state, store):
    knowledge_ref, bundle = resolve_reference(state["knowledge"], store, "bundle_ref", "complete")
    snapshot = validate_knowledge(bundle, store)
    selection = (
        store.get_object(bundle["selection_ref"])
        if bundle.get("selection_ref")
        else {
            "schema_version": "1",
            "origin": "snapshot_derived",
            "files": [
                {k: row[k] for k in ("path", "snapshot") if k in row}
                for row in snapshot["inventory"]
            ],
        }
    )
    if selection["files"] != [
        {k: row[k] for k in ("path", "snapshot") if k in row} for row in snapshot["inventory"]
    ]:
        raise ValueError("Source selection does not match the inherited snapshot")
    raw = Path(state["template"]).read_bytes()
    text = raw.decode("utf-8")
    if not text.strip():
        raise ValueError("Template is empty")
    template = {
        "bytes_hex": raw.hex(),
        "hash": digest(raw),
        "text": text,
        "spans": [s.model_dump() for s in template_spans(text)],
    }
    supplied = read_json(Path(state["brief"])) if state.get("brief") else {}
    brief = DocumentationBrief.model_validate(supplied)
    origins = {
        key: "brief" if key in supplied else "default" for key in DocumentationBrief.model_fields
    }
    previous_ref = None
    if state.get("previous_plan"):
        previous_ref, previous = resolve_reference(
            state["previous_plan"], store, "plan_ref", "ready_for_generation"
        )
        if previous["schema_version"] != "1":
            raise ValueError("Unsupported previous plan schema")
        for ref in previous["components"].values():
            store.get(ref)
    record_ids = {r["id"] for r in bundle["claims"] + bundle["entities"]}
    if set(brief.include_record_ids + brief.exclude_record_ids) - record_ids:
        raise ValueError("Brief scope references missing knowledge records")
    records = []
    for kind, rows in (("claim", bundle["claims"]), ("entity", bundle["entities"])):
        for row in rows:
            records.append({"id": row["id"], "kind": kind, "record": row})
    for kind, rows in (
        ("relationship", bundle["relationships"]),
        ("review_decision", bundle["decisions"]),
    ):
        for row in rows:
            records.append({"id": kind + "-" + digest(row)[:24], "kind": kind, "record": row})
    for block in snapshot["blocks"]:
        if block["kind"] in {"table", "list", "bullet_list", "ordered_list", "fence"}:
            records.append(
                {"id": "context-" + block["id"], "kind": "source_context", "record": block}
            )
    lookup = {r["id"]: r for r in bundle["claims"] + bundle["entities"]}
    coverage = {r["block_id"]: r for r in bundle["coverage"]}
    issues = {r["id"]: r for r in bundle["resolved_issues"]}
    record_issues = defaultdict(list)
    for issue in issues.values():
        for identifier in issue.get("record_ids", []):
            record_issues[identifier].append(issue["id"])
    for row in records:
        context = {"decision_refs": record_issues[row["id"]]}
        if row["kind"] == "entity":
            context["canonical_entity_id"] = bundle["canonical_entity_ids"][row["id"]]
        elif row["kind"] == "relationship":
            context["evidence"] = (
                lookup[row["record"]["left"]]["evidence"]
                + lookup[row["record"]["right"]]["evidence"]
            )
        elif row["kind"] == "review_decision":
            context["review_issue"] = issues.get(row["record"]["issue_id"])
        elif row["kind"] == "source_context":
            context["extraction_disposition"] = coverage[row["record"]["id"]]
        row["context"] = context
    return PlanningInputs(
        signature=state["signature"],
        knowledge_ref=knowledge_ref,
        knowledge_revision=digest(bundle),
        knowledge_signature=bundle["signature"],
        snapshot_ref=bundle["snapshot_ref"],
        selection_ref=store.put(selection, "selection"),
        records_ref=store.put_table(records, "knowledge-records"),
        blocks_ref=store.put_table(snapshot["blocks"], "source-blocks"),
        coverage_ref=store.put_table(bundle["coverage"], "extraction-coverage"),
        template_ref=store.put(template, "template"),
        template_hash=digest(raw),
        brief=brief,
        origins=origins,
        previous_plan_ref=previous_ref,
    )


def make_obligation(row, inputs):
    record, kind = row["record"], row["kind"]
    context = row["context"]
    evidence = record.get("evidence", [])
    eligibility, reason = "eligible", None
    decision_refs = list(context["decision_refs"])
    constraints = {
        key: record.get(key)
        for key in (
            "conditions",
            "exceptions",
            "frequency_time",
            "scope",
            "version",
            "modality",
            "source_status",
            "review_status",
        )
        if key in record
    }
    if kind == "claim" and record["review_status"] == "ineligible":
        eligibility, reason = "audit_only", "Ineligible according to phase 1 authority decisions"
    if kind == "entity":
        constraints["canonical_entity_id"] = context["canonical_entity_id"]
    if kind == "relationship":
        evidence = context["evidence"]
        constraints["relationship"] = record
        if record["kind"] in {"same_entity", "conflict", "missing_dependency"}:
            eligibility, reason = "audit_only", "Raw proposal; effective decisions govern meaning"
    if kind == "review_decision":
        decision_refs = [row["id"]]
        constraints["attribution"] = {"kind": "reviewer", "reviewer": record["reviewer"]}
        issue = context["review_issue"]
        if issue:
            constraints["review_issue"] = issue
        if record["action"] not in {"acknowledge_unknown", "explain_asset", "keep_distinct"}:
            eligibility, reason = "audit_only", "Decision retained in the audit trail"
    if kind == "source_context":
        evidence = [{"block_id": record["id"], "excerpt": record["content"]}]
        constraints["context_only"] = True
        constraints["table_columns"] = record["table_columns"]
        constraints["table_row"] = record["table_row"]
        constraints["table_id"] = record["table_id"]
        disposition = context["extraction_disposition"]
        constraints["extraction_disposition"] = disposition
        if disposition["disposition"] != "represented":
            eligibility, reason = "audit_only", disposition["explanation"]
    brief = inputs.brief
    if (
        eligibility == "eligible"
        and kind in {"claim", "entity"}
        and (
            row["id"] in brief.exclude_record_ids
            or (brief.include_record_ids and row["id"] not in brief.include_record_ids)
        )
    ):
        eligibility, reason = "out_of_scope", "Explicit record selection in documentation brief"
    return ContentObligation(
        id="ob-" + digest([row["id"], kind])[:24],
        record_id=row["id"],
        record_kind=kind,
        facet="complete_record",
        record_ref=inputs.records_ref,
        required_fields=[k for k, v in record.items() if v not in (None, [], "", {})],
        evidence=evidence,
        constraints=constraints,
        eligibility=eligibility,
        decision_refs=decision_refs,
        reason=reason,
    )
