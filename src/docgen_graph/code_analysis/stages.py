import json
from pathlib import Path

from docgen_graph.code_analysis.backends import backend_for
from docgen_graph.code_analysis.history import freeze_history
from docgen_graph.code_analysis.inventory import CodeScope, scope_inventory
from docgen_graph.contracts import AuditDraft, CodeAnalysisDraft
from docgen_graph.knowledge import normalized_assertion
from docgen_graph.storage import digest

CODE_STAGE_NAMES = (
    "inventory_code_scope",
    "analyze_code_unit",
    "verify_code_unit",
    "classify_code_facts",
    "verify_code_classification",
    "publish_code_evidence",
)


def inventory_code_scope(pipeline, state):
    inventory = pipeline.read(state, "inventory_ref")
    settings = getattr(pipeline.model, "settings", None)
    path = getattr(settings, "code_scope_file", None)
    scope = CodeScope.model_validate(json.loads(path.read_text("utf-8"))) if path else CodeScope()
    record = scope_inventory(inventory, scope)
    history = None
    if scope.base_commit or scope.head_commit or scope.patch_paths:
        history = freeze_history(
            pipeline.store,
            Path(state["code"]),
            scope,
            [f["path"] for f in record["files"] if f["disposition"] != "out_of_scope"],
        )
    inventory = {**inventory, "code_units": [u["evidence_ids"] for u in record["units"]]}
    return {
        "code_scope_ref": pipeline.store.put(record),
        "code_history_ref": pipeline.store.put(history),
        "inventory_ref": pipeline.store.put(inventory),
        "code_index": 0,
        "code_provenance_ref": pipeline.store.put([]),
        "route": "analyze_code_unit" if record["units"] else "extract_document_batch",
    }


def _payload(pipeline, state):
    inventory = pipeline.read(state, "inventory_ref")
    scope = pipeline.read(state, "code_scope_ref")
    unit = scope["units"][state["code_index"]]
    spans = pipeline.spans(state)
    return {
        "spans": [spans[key] for key in unit["evidence_ids"]],
        "context": [spans[key] for key in unit["context_ids"]],
        "context_truncated": unit["context_truncated"],
        "omitted_context_ids": unit["omitted_context_ids"],
        "scope_id": scope["scope_id"],
        "analysis": {
            spans[key]["path"]: inventory["analysis"][spans[key]["path"]]
            for key in unit["evidence_ids"]
        },
        "feedback": pipeline.read(state, "feedback_ref", []),
        "history": pipeline.read(state, "code_history_ref"),
        "scope_role": unit["scope_role"],
    }


def analyze_code_unit(pipeline, state):
    payload = _payload(pipeline, state)
    backend = backend_for(
        pipeline.model,
        pipeline.store,
        pipeline.run_id,
        pipeline.store.root / "frozen-code" / state["snapshot_ref"],
    )
    try:
        packet = backend.analyze_unit(payload)
    finally:
        backend.close()
    if packet.status != "ok":
        return pipeline.issue(state, "analyze_code_unit", packet.warnings, "analyze_code_unit")
    draft = {
        "report": "Code evidence candidates",
        "details": [f.model_dump() for f in packet.facts],
    }
    return {
        "draft_ref": pipeline.store.put(draft),
        "code_candidate_ref": pipeline.store.put(packet.model_dump()),
        "route": "verify_code_unit",
    }


def verify_code_unit(pipeline, state):
    payload = _payload(pipeline, state)
    draft = pipeline.read(state, "draft_ref")
    ids = {s["id"] for s in payload["spans"]}
    try:
        records = [normalized_assertion(raw, ids) for raw in draft["details"]]
    except ValueError as error:
        return pipeline.issue(state, "verify_code_unit", [str(error)], "analyze_code_unit")
    missing = ids - {eid for record in records for eid in record["evidence_ids"]}
    audit = pipeline.call("verify_code", {**payload, "draft": draft}, AuditDraft)
    findings = audit["findings"] + (
        [f"Code units lack records: {sorted(missing)}"] if missing else []
    )
    if findings or not audit["accepted"]:
        if state.get("attempt", 0) < pipeline.repair_limit():
            return {
                "attempt": state.get("attempt", 0) + 1,
                "feedback_ref": pipeline.store.put(findings),
                "route": "analyze_code_unit",
            }
        return pipeline.issue(
            state,
            "verify_code_unit",
            findings or ["Code audit rejected candidates"],
            "analyze_code_unit",
        )
    return {"verified_code_ref": pipeline.store.put(records), "route": "classify_code_facts"}


def classify_code_facts(pipeline, state):
    records = pipeline.read(state, "verified_code_ref")
    result = pipeline.call(
        "analyze_code_classification",
        {**_payload(pipeline, state), "facts": records},
        CodeAnalysisDraft,
    )
    return {
        "classified_code_ref": pipeline.store.put(result),
        "route": "verify_code_classification",
    }


def verify_code_classification(pipeline, state):
    original = pipeline.read(state, "verified_code_ref")
    draft = pipeline.read(state, "classified_code_ref")
    semantic = (
        "statement",
        "subject",
        "predicate",
        "scope",
        "modality",
        "conditions",
        "exceptions",
        "evidence_ids",
        "source_role",
        "provenance_ids",
    )
    before = {digest({k: fact.get(k) for k in semantic}) for fact in original}
    after = {digest({k: fact.get(k) for k in semantic}) for fact in draft["details"]}
    findings = (
        []
        if before == after
        else ["Classification changed facts, qualifiers, provenance or evidence"]
    )
    for fact in draft["details"]:
        if not fact.get("classification_reason") or not fact.get("relevance_reason"):
            findings.append("Classification lacks a reason")
    audit = (
        pipeline.call(
            "verify_code_classification",
            {**_payload(pipeline, state), "original": original, "classified": draft},
            AuditDraft,
        )
        if not findings
        else {"accepted": False, "findings": []}
    )
    findings.extend(audit["findings"])
    if findings or not audit["accepted"]:
        return pipeline.issue(
            state,
            "verify_code_classification",
            findings or ["Classification rejected"],
            "classify_code_facts",
        )
    return {
        "code_classification_verified_ref": pipeline.store.put(
            {"accepted": True, "input_hash": digest(draft)}
        ),
        "route": "publish_code_evidence",
    }


def publish_code_evidence(pipeline, state):
    draft = pipeline.read(state, "classified_code_ref")
    audit = pipeline.read(state, "code_classification_verified_ref")
    if not audit["accepted"] or audit["input_hash"] != digest(draft):
        raise ValueError("Classification changed after verification")
    payload = _payload(pipeline, state)
    allowed = {s["id"] for s in payload["spans"]}
    records = [
        normalized_assertion({**raw, "review_status": "verified"}, allowed)
        for raw in draft["details"]
    ]
    provenance = pipeline.read(state, "code_provenance_ref", [])
    provenance.extend(pipeline.read(state, "code_candidate_ref")["provenance"])
    next_index = state["code_index"] + 1
    pipeline.store.write(
        f"runs/{pipeline.run_id}/reports/code-{state['code_index']:04d}.md", draft["report"]
    )
    return {
        "assertions_ref": pipeline.store.put(pipeline.assertions(state) + records),
        "code_provenance_ref": pipeline.store.put(provenance),
        "code_index": next_index,
        "attempt": 0,
        "feedback_ref": "",
        "draft_ref": "",
        "route": "analyze_code_unit"
        if next_index < len(pipeline.read(state, "code_scope_ref")["units"])
        else "extract_document_batch",
    }
