from contextlib import contextmanager
from pathlib import Path
from time import monotonic
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import ValidationError

from docgen.batching import plan_batches, split_batch
from docgen.config import Settings
from docgen.contracts import Batch, Block, Comparison, Extraction, Verification
from docgen.ingestion import snapshot_sources
from docgen.model import ModelFailure, RequestTooLarge, TruncatedOutput
from docgen.reconciliation import (
    comparison_at,
    comparison_count,
    comparison_tasks,
    entity_register,
    iter_comparisons,
    replace_comparison,
    split_comparison,
)
from docgen.review import make_issues, persist_decisions, report, validate_decisions
from docgen.storage import Artifacts, atomic_write, digest, write_json, write_jsonl
from docgen.validation import finding, qualify_ids, validate_duplicate_chains, validate_extraction


class PipelineState(TypedDict, total=False):
    run_id: str
    source: str
    selection: str
    workflow: str
    signature: str
    route: str
    snapshot_ref: str
    batches_ref: str
    batch_index: int
    attempt: int
    draft_ref: str
    feedback_ref: str
    verified_ref: str
    records_ref: str
    blocks_ref: str
    entity_plan_ref: str
    entity_index: int
    entity_results_ref: str
    claim_plan_ref: str
    claim_index: int
    claim_results_ref: str
    issues_ref: str
    issue_history_ref: str
    decisions_ref: str
    review_revision: str
    review_stage: str
    review_report: str
    bundle_ref: str
    status: str


class Pipeline:
    def __init__(self, settings: Settings, store: Artifacts, model):
        self.settings = settings
        self.store = store
        self.model = model

    def read(self, state, key, default=None):
        return self.store.get(state[key]) if state.get(key) else default

    def blocks(self, state) -> dict[str, Block]:
        return {
            item["id"]: Block.model_validate(item)
            for item in self.read(state, "snapshot_ref")["blocks"]
        }

    def current_batch(self, state) -> Batch:
        return Batch.model_validate(self.read(state, "batches_ref")[state["batch_index"]])

    def gate(self, state, stage, revision, findings):
        issues = make_issues(stage, revision, findings)
        issues = list({issue["id"]: issue for issue in issues}.values())
        decisions = self.read(state, "decisions_ref", [])
        resolved = {
            item["issue_id"]
            for item in decisions
            if item["revision"] == revision and item["action"] not in {"defer", "correct"}
        }
        issues = [issue for issue in issues if issue["id"] not in resolved]
        if not issues:
            return None
        ref = self.store.put(issues, "issues")
        history = self.read(state, "issue_history_ref", {})
        history.update({issue["id"]: issue for issue in issues})
        blocks = self.blocks(state) if state.get("snapshot_ref") else {}
        report_path = f"runs/{state['run_id']}/review-{digest(issues)[:16]}.md"
        atomic_write(self.store.path(report_path), report(issues, blocks, revision))
        return {
            "route": "review_issues",
            "issues_ref": ref,
            "issue_history_ref": self.store.put(history, "issue-history"),
            "review_stage": stage,
            "review_revision": revision,
            "review_report": report_path,
            "status": "review",
        }

    def snapshot_sources(self, state):
        snapshot = self.read(state, "snapshot_ref")
        if snapshot is None:
            snapshot = snapshot_sources(
                Path(state["source"]),
                self.store,
                min(2000, self.settings.batch_tokens),
                state.get("selection"),
            )
        ref = state.get("snapshot_ref") or self.store.put(snapshot, "snapshot")
        update = {"snapshot_ref": ref}
        gate = self.gate({**state, **update}, "snapshot_sources", ref, snapshot["problems"])
        return {**update, **(gate or {"route": "plan_batches", "status": "running"})}

    def plan_batches(self, state):
        batches = plan_batches(self.read(state, "snapshot_ref"), self.settings)
        ref = self.store.put([batch.model_dump() for batch in batches], "batches")
        return {
            "batches_ref": ref,
            "batch_index": 0,
            "attempt": 0,
            "route": "extract_batch" if batches else "finalize_knowledge",
        }

    def batch_payload(self, state):
        batch = self.current_batch(state)
        blocks = self.blocks(state)
        return {
            "batch": batch.model_dump(),
            "owned": [blocks[key].model_dump() for key in batch.owned],
            "context": [blocks[key].model_dump() for key in batch.context],
            "feedback": self.read(state, "feedback_ref", []),
            "prior_draft": self.read(state, "draft_ref"),
        }

    def split_current(self, state, stage):
        batch = self.current_batch(state)
        if len(batch.owned) < 2:
            revision = state["batches_ref"]
            return self.gate(
                state,
                stage,
                revision,
                [
                    {
                        "kind": "oversized",
                        "description": "Single-block request or response exceeds limits; "
                        "start a new revision with a smaller source block or larger output budget",
                        "block_ids": batch.owned,
                    }
                ],
            )
        batches = self.read(state, "batches_ref")
        children = split_batch(batch, self.blocks(state), self.settings.context_tokens)
        index = state["batch_index"]
        batches[index : index + 1] = [child.model_dump() for child in children]
        owners = {key: value["id"] for value in batches for key in value["owned"]}
        for value in batches:
            value["dependencies"] = sorted(
                {
                    owners[key]
                    for key in value["context"] + value["omitted_context"]
                    if owners[key] != value["id"]
                }
            )
        return {
            "batches_ref": self.store.put(batches, "batches"),
            "attempt": 0,
            "draft_ref": "",
            "feedback_ref": "",
            "route": "extract_batch",
        }

    def extract_batch(self, state):
        try:
            result = self.model.call("extract", self.batch_payload(state), Extraction)
        except (TruncatedOutput, RequestTooLarge):
            return self.split_current(state, "extract_batch")
        except ValidationError:
            issues = [
                finding("unsupported", "Model response failed the extraction schema").model_dump()
            ]
            if state.get("attempt", 0) < 2:
                return {
                    "attempt": state.get("attempt", 0) + 1,
                    "feedback_ref": self.store.put(issues, "feedback"),
                    "route": "extract_batch",
                }
            return self.gate(state, "extract_batch", state["batches_ref"], issues)
        return {"draft_ref": self.store.put(result, "extraction"), "route": "verify_batch"}

    def verify_batch(self, state):
        batch = self.current_batch(state)
        draft = Extraction.model_validate(self.read(state, "draft_ref"))
        defects = validate_extraction(draft, batch, self.blocks(state))
        review_findings = list(draft.findings)
        if not defects:
            payload = self.batch_payload(state)
            payload["extraction"] = payload.pop("prior_draft")
            try:
                verification = self.model.call("verify", payload, Verification)
                if set(verification.checked_block_ids) != set(batch.owned) or len(
                    verification.checked_block_ids
                ) != len(batch.owned):
                    defects.append(finding("omission", "Verifier did not check every owned block"))
                ids = {item.id for item in [*draft.claims, *draft.entities]}
                for item in verification.findings:
                    if (
                        not set(item.block_ids) <= set(batch.owned + batch.context)
                        or not set(item.record_ids) <= ids
                    ):
                        defects.append(
                            finding("unsupported", "Verifier returned invalid references")
                        )
                    elif item.kind in {"omission", "distortion", "unsupported"}:
                        defects.append(item)
                    else:
                        review_findings.append(item)
            except (TruncatedOutput, RequestTooLarge):
                return self.split_current(state, "verify_batch")
            except ValidationError:
                defects.append(finding("unsupported", "Verifier response failed schema validation"))
        if defects and state.get("attempt", 0) < 2:
            return {
                "attempt": state.get("attempt", 0) + 1,
                "route": "extract_batch",
                "feedback_ref": self.store.put([item.model_dump() for item in defects], "feedback"),
            }
        issues = [item.model_dump() for item in [*defects, *review_findings]]
        for issue in issues:
            issue["record_ids"] = [f"{batch.id}:{key}" for key in issue["record_ids"]]
        gate = self.gate(state, "verify_batch", state["draft_ref"], issues)
        if gate:
            return gate
        qualified = qualify_ids(draft, batch.id)
        verified = self.read(state, "verified_ref", {})
        verified[batch.id] = self.store.put(qualified, "verified")
        batches = self.read(state, "batches_ref")
        batches[state["batch_index"]].update(
            status="verified", attempts=state.get("attempt", 0) + 1
        )
        next_index = state["batch_index"] + 1
        return {
            "verified_ref": self.store.put(verified, "verified-index"),
            "batches_ref": self.store.put(batches, "batches"),
            "batch_index": next_index,
            "attempt": 0,
            "draft_ref": "",
            "feedback_ref": "",
            "status": "running",
            "route": "extract_batch" if next_index < len(batches) else "reconcile_entities",
        }

    def records(self, state):
        claims, entities, coverage = [], [], []
        for ref in self.read(state, "verified_ref", {}).values():
            extraction = self.store.get(ref)
            claims.extend(extraction["claims"])
            entities.extend(extraction["entities"])
            coverage.extend(extraction["coverage"])
        return claims, entities, coverage

    def reconcile_entities(self, state):
        return self.reconcile(state, "entities", "entity", "reconcile_claims")

    def reconcile_claims(self, state):
        return self.reconcile(state, "claims", "claim", "finalize_knowledge")

    def comparison_results(self, state, prefix):
        ref = state.get(f"{prefix}_results_ref")
        if not ref:
            return
        value = self.store.get(ref)
        if "previous" in value and "rows" in value:
            for row in self.store.iter_parts(ref):
                yield row["task_id"], row["response_ref"]
        else:
            yield from value.items()

    def reconcile(self, state, kind, prefix, next_stage):
        stage = f"reconcile_{kind}"
        plan_key, index_key, results_key = (
            f"{prefix}_plan_ref",
            f"{prefix}_index",
            f"{prefix}_results_ref",
        )
        plan = self.read(state, plan_key)
        if plan is None:
            claims, entities, _ = self.records(state)
            records = entities if kind == "entities" else claims
            names = {entity["id"]: entity["canonical_name"] for entity in entities}
            plan = comparison_tasks(
                records,
                kind,
                self.settings.reconciliation_tokens,
                names,
                self.settings.workload_tasks,
                store=self.store,
            )
            return {
                plan_key: self.store.put(plan, f"{prefix}-plan"),
                index_key: 0,
                "route": stage,
                "records_ref": state.get("records_ref")
                or self.store.put_table(claims + entities, "reconciliation-records"),
                "blocks_ref": state.get("blocks_ref")
                or self.store.put_table(
                    self.read(state, "snapshot_ref")["blocks"], "reconciliation-blocks"
                ),
            }
        if plan["unperformed"]:
            gate = self.gate(
                state,
                stage,
                state[plan_key],
                [
                    {
                        "kind": "unperformed_comparison",
                        "description": item["reason"],
                        "record_ids": [item["record_id"]],
                    }
                    for item in plan["unperformed"]
                ],
            )
            if gate:
                return gate
        index = state.get(index_key, 0)
        if index >= comparison_count(plan):
            return {"route": next_stage}
        task = comparison_at(plan, index, self.store)
        lookup = {
            row["id"]: row
            for row in self.store.table_rows(state["records_ref"], task["left"] + task["right"])
        }
        payload = {
            "group": task["group"],
            "revision": digest(lookup),
            "left": [lookup[key] for key in task["left"]],
            "right": [lookup[key] for key in task["right"]],
            "source_blocks": self.store.table_rows(
                state["blocks_ref"],
                sorted({e["block_id"] for row in lookup.values() for e in row["evidence"]}),
            ),
        }
        if state.get("attempt", 0):
            payload.update(
                repair_attempt=state["attempt"], feedback=self.read(state, "feedback_ref", [])
            )
        expected = set(task["left"] + task["right"])
        try:
            result = self.model.call(kind, payload, Comparison)
        except (TruncatedOutput, RequestTooLarge):
            children = split_comparison(task)
            if children:
                if comparison_count(plan) - 1 + len(children) > self.settings.workload_tasks:
                    raise ModelFailure(
                        "Split reconciliation queue exceeds workload allowance"
                    ) from None
                plan = replace_comparison(plan, index, children, self.store)
                return {
                    plan_key: self.store.put(plan, f"{prefix}-plan"),
                    "attempt": 0,
                    "feedback_ref": "",
                    "route": stage,
                }
            return self.gate(
                state,
                stage,
                state[plan_key],
                [
                    {
                        "kind": "oversized",
                        "description": "Comparison exceeds budget; reduce reconciliation tokens",
                        "record_ids": sorted(expected),
                    }
                ],
            )
        except ValidationError as error:
            if state.get("attempt", 0) < 2:
                return {
                    "attempt": state.get("attempt", 0) + 1,
                    "feedback_ref": self.store.put([str(error)], "comparison-feedback"),
                    "route": stage,
                }
            return self.gate(
                state,
                stage,
                state[plan_key],
                [
                    {
                        "kind": "unsupported",
                        "description": "Comparison response failed schema validation",
                        "record_ids": sorted(expected),
                    }
                ],
            )
        findings = [item.model_dump() for item in result.findings]
        invalid = []
        if set(result.checked_ids) != expected or len(result.checked_ids) != len(expected):
            invalid.append(
                {"kind": "unsupported", "description": "Comparison did not inspect all records"}
            )
        for relation in result.relations:
            if {relation.left, relation.right} - expected or relation.left == relation.right:
                invalid.append(
                    {
                        "kind": "unsupported",
                        "description": "Comparison has invalid record references",
                    }
                )
            elif relation.kind in {"conflict", "same_entity", "missing_dependency"}:
                finding_kind = {
                    "same_entity": "ambiguous_entity",
                    "missing_dependency": "missing_context",
                }.get(relation.kind, relation.kind)
                evidence = lookup[relation.left]["evidence"] + lookup[relation.right]["evidence"]
                findings.append(
                    {
                        "kind": finding_kind,
                        "description": relation.explanation,
                        "record_ids": [relation.left, relation.right],
                        "block_ids": sorted({item["block_id"] for item in evidence}),
                    }
                )
        for item in result.findings:
            try:
                self.store.table_rows(state["blocks_ref"], item.block_ids)
                valid_blocks = True
            except ValueError:
                valid_blocks = False
            if not set(item.record_ids) <= expected or not valid_blocks:
                invalid.append(
                    {
                        "kind": "unsupported",
                        "description": "Comparison finding has invalid references",
                    }
                )
        if invalid and state.get("attempt", 0) < 2:
            return {
                "attempt": state.get("attempt", 0) + 1,
                "feedback_ref": self.store.put(
                    {"errors": invalid, "expected_record_ids": sorted(expected)},
                    "comparison-feedback",
                ),
                "route": stage,
            }
        findings.extend(invalid)
        ref = self.store.put(result, f"{prefix}-comparison")
        gate = self.gate(state, stage, ref, findings)
        if gate:
            return gate
        previous = state.get(results_key)
        if previous and "previous" not in self.store.get(previous):
            previous = self.store.append_part(
                None,
                [
                    {"task_id": key, "response_ref": value}
                    for key, value in self.comparison_results(state, prefix)
                ],
                f"{prefix}-comparisons",
            )
        return {
            results_key: self.store.append_part(
                previous,
                [{"task_id": task["id"], "response_ref": ref}],
                f"{prefix}-comparisons",
            ),
            index_key: index + 1,
            "attempt": 0,
            "feedback_ref": "",
            "route": stage,
            "status": "running",
        }

    def review_issues(self, state):
        issues = self.read(state, "issues_ref", [])
        response = interrupt(
            {
                "revision": state["review_revision"],
                "issues": issues,
                "report": str(self.store.path(state["review_report"])),
                "message": "Supply revision-bound decisions; deferral keeps the stage paused",
            }
        )
        values = response.get("decisions", []) if isinstance(response, dict) else []
        decisions = validate_decisions(values, issues, state["review_revision"])
        if any(decision.action in {"keep_distinct", "merge_entities"} for decision in decisions):
            _, entities, _ = self.records(state)
            if state["review_stage"] == "verify_batch":
                draft = Extraction.model_validate(self.read(state, "draft_ref"))
                entities.extend(
                    entity.model_dump()
                    for entity in qualify_ids(draft, self.current_batch(state).id).entities
                )
            entity_ids = {entity["id"] for entity in entities}
            issue_lookup = {issue["id"]: issue for issue in issues}
            for decision in decisions:
                if decision.action in {"keep_distinct", "merge_entities"}:
                    if not set(issue_lookup[decision.issue_id]["record_ids"]) <= entity_ids:
                        raise ValueError(
                            "Entity decisions require separate extracted entity records"
                        )
        if not decisions or any(item.action == "defer" for item in decisions):
            ref = persist_decisions(self.store, state.get("decisions_ref"), decisions)
            return {"route": "review_issues", "decisions_ref": ref, "status": "review"}
        corrections = [decision for decision in decisions if decision.action == "correct"]
        if corrections:
            if len(corrections) != 1 or state["review_stage"] not in {
                "extract_batch",
                "verify_batch",
            }:
                raise ValueError("Submit one extraction correction for the affected batch")
            replacement = corrections[0].replacement
            errors = validate_extraction(replacement, self.current_batch(state), self.blocks(state))
            if errors:
                raise ValueError("Corrected extraction failed evidence or coverage validation")
            ref = persist_decisions(self.store, state.get("decisions_ref"), decisions)
            return {
                "decisions_ref": ref,
                "draft_ref": self.store.put(replacement, "extraction"),
                "feedback_ref": "",
                "attempt": 0,
                "route": "verify_batch",
                "status": "running",
            }
        ref = persist_decisions(self.store, state.get("decisions_ref"), decisions)
        if any(decision.action == "merge_entities" for decision in decisions):
            entity_register(entities, self.store.get(ref))
        return {"decisions_ref": ref, "route": state["review_stage"], "status": "running"}

    def finalize_knowledge(self, state):
        claims, entities, coverage = self.records(state)
        blocks = self.blocks(state)
        batches = self.read(state, "batches_ref", [])
        findings = []
        coverage_ids = [item["block_id"] for item in coverage]
        if not validate_duplicate_chains(coverage):
            findings.append(
                {"kind": "unsupported", "description": "Duplicate coverage is cyclic or unresolved"}
            )
        if set(coverage_ids) != set(blocks) or len(coverage_ids) != len(blocks):
            findings.append(
                {
                    "kind": "omission",
                    "description": "Final coverage does not account for every block",
                }
            )
        if any(item["disposition"] == "unresolved" for item in coverage):
            findings.append(
                {"kind": "source_issue", "description": "Unresolved coverage blocks completion"}
            )
        if any(batch["status"] != "verified" for batch in batches):
            findings.append(
                {"kind": "source_issue", "description": "All extraction batches must be verified"}
            )
        comparison_maps = {
            prefix: dict(self.comparison_results(state, prefix)) for prefix in ("entity", "claim")
        }
        for prefix in ("entity", "claim"):
            plan = self.read(state, f"{prefix}_plan_ref", {"tasks": [], "unperformed": []})
            results = comparison_maps[prefix]
            expected = {task["id"] for task in iter_comparisons(plan, self.store)}
            if set(results) != expected or plan["unperformed"]:
                findings.append(
                    {
                        "kind": "unperformed_comparison",
                        "description": "Reconciliation is incomplete",
                    }
                )
        gate = self.gate(
            state, "finalize_knowledge", state.get("verified_ref", state["snapshot_ref"]), findings
        )
        if gate:
            return gate
        decisions = self.read(state, "decisions_ref", [])
        history = self.read(state, "issue_history_ref", {})
        actions = {decision["issue_id"]: decision for decision in decisions}
        corrected = {
            decision["revision"] for decision in decisions if decision["action"] == "correct"
        }
        rejected = set()
        resolved_issues = []
        pending = []
        for issue in history.values():
            action = actions.get(issue["id"])
            if issue["revision"] in corrected:
                resolved_issues.append({**issue, "status": "superseded"})
            elif action and action["action"] != "defer" and action["revision"] == issue["revision"]:
                resolved_issues.append({**issue, "status": "resolved", "decision": action})
                if action["action"] == "select_authority":
                    rejected.update(set(issue["record_ids"]) - set(action["claim_ids"]))
            else:
                pending.append(issue)
        if pending:
            raise ValueError("Issue history contains unresolved decisions; finalization rejected")
        for claim in claims:
            if claim["id"] in rejected:
                claim["review_status"] = "ineligible"
        register, canonical_ids = entity_register(entities, decisions)
        relationships = {}
        for comparisons in comparison_maps.values():
            for comparison_ref in comparisons.values():
                for relation in self.store.get(comparison_ref)["relations"]:
                    relationships[digest(relation)] = {**relation, "revision": comparison_ref}
        bundle = {
            "schema_version": "1",
            "signature": state["signature"],
            "snapshot_ref": state["snapshot_ref"],
            "selection_ref": self.store.put(
                self.read(state, "snapshot_ref")["selection"], "selection"
            )
            if "selection" in self.read(state, "snapshot_ref")
            else None,
            "batches_ref": state["batches_ref"],
            "claims": claims,
            "entities": entities,
            "entity_register": register,
            "canonical_entity_ids": canonical_ids,
            "relationships": list(relationships.values()),
            "coverage": coverage,
            "decisions": decisions,
            "resolved_issues": resolved_issues,
            "entity_comparisons": comparison_maps["entity"],
            "claim_comparisons": comparison_maps["claim"],
            "reviewer_evidence": [
                {"decision": decision, "issue": history[decision["issue_id"]]}
                for decision in decisions
                if decision["action"] == "explain_asset"
            ],
            "unresolved_issues": [],
            "status": "complete",
        }
        ref = self.store.put(bundle, "knowledge")
        destination = self.store.path(f"runs/{state['run_id']}/knowledge/{digest(bundle)}")
        for name, rows in (
            ("claims", claims),
            ("entities", entities),
            ("entity-register", register),
            ("relationships", list(relationships.values())),
            ("coverage", coverage),
            ("decisions", decisions),
            ("blocks", [block.model_dump() for block in blocks.values()]),
        ):
            write_jsonl(destination / f"{name}.jsonl", rows)
        write_json(
            destination / "manifest.json",
            {
                "bundle_ref": ref,
                "revision": digest(bundle),
                "status": "complete",
                "source_count": len(blocks),
            },
        )
        atomic_write(
            destination / "review.md",
            "# Knowledge revision\n\n"
            f"Revision: {digest(bundle)}\n\n{len(blocks)} source blocks; {len(claims)} claims; "
            f"{len(entities)} entity entries; {len(decisions)} recorded decisions.\n\n"
            "Zero unresolved issues. Complete accounting does not prove semantic completeness.\n",
        )
        return {"bundle_ref": ref, "route": END, "status": "complete"}

    def instrument(self, name):
        function = getattr(self, name)

        def run(state):
            started = monotonic()
            result = function(state)
            self.store.event(
                state["run_id"],
                stage=name,
                event="stage_complete",
                seconds=monotonic() - started,
                outputs=result,
                input_revision=digest(state),
            )
            return result

        return run

    def build(self, checkpointer, stop_after=None):
        graph = StateGraph(PipelineState)
        names = [
            "snapshot_sources",
            "plan_batches",
            "extract_batch",
            "verify_batch",
            "reconcile_entities",
            "reconcile_claims",
            "review_issues",
            "finalize_knowledge",
        ]
        for name in names:
            graph.add_node(name, self.instrument(name))
            graph.add_conditional_edges(name, lambda state: state["route"], [*names, END])
        graph.add_edge(START, "snapshot_sources")
        return graph.compile(
            checkpointer=checkpointer, interrupt_after=[stop_after] if stop_after else None
        )


@contextmanager
def persistent_graph(pipeline: Pipeline, stop_after=None):
    with SqliteSaver.from_conn_string(str(pipeline.store.path("checkpoints.sqlite"))) as saver:
        yield pipeline.build(saver, stop_after)
