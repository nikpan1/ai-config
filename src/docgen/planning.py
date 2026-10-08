from collections import defaultdict
from time import monotonic
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import ValidationError

from docgen.model import ModelFailure, RequestTooLarge, TruncatedOutput
from docgen.planning_contracts import (
    BriefProposal,
    DocumentationUnit,
    LogicalProposal,
    LogicalSection,
    PlanDecision,
    PlanIssue,
    PlanningInputs,
    SectionBrief,
    SemanticAudit,
    Subdivision,
    TemplateContract,
    TemplateInstance,
    TemplateInterpretation,
    UnitAssignment,
    UnitDiscovery,
    UnitSynthesis,
)
from docgen.planning_helpers import (
    bounded_context_groups,
    bounded_groups,
    evidence_context,
    require_exact,
    stable_id,
)
from docgen.planning_inputs import make_obligation, snapshot_inputs
from docgen.storage import digest, encode

STAGES = (
    "snapshot_planning_inputs",
    "compile_template",
    "inventory_content",
    "discover_documentation_units",
    "verify_documentation_units",
    "plan_logical_structure",
    "allocate_content",
    "design_page_tree",
    "write_section_briefs",
    "plan_navigation",
    "plan_writing_jobs",
    "validate_plan",
    "audit_plan",
    "review_plan",
    "finalize_plan",
)


class PlanningState(TypedDict, total=False):
    run_id: str
    workflow: str
    signature: str
    knowledge: str
    template: str
    brief: str
    previous_plan: str
    inputs_ref: str
    components_ref: str
    work_key: str
    work_ref: str
    work_index: int
    results_ref: str
    synthesis_round: int
    candidates_ref: str
    candidate_map_ref: str
    discovery_ref: str
    units_count: int
    attempt: int
    repairs_ref: str
    feedback_ref: str
    stage_feedback_ref: str
    issues_ref: str
    issue_history_ref: str
    decisions_ref: str
    correction_ref: str
    review_stage: str
    review_revision: str
    route: str
    status: str
    plan_ref: str
    export_path: str


class PlanningPipeline:
    def __init__(self, settings, store, model):
        self.settings = settings
        self.store = store
        self.model = model

    def read(self, state, key, default=None):
        return self.store.get(state[key]) if state.get(key) else default

    def inputs(self, state):
        return PlanningInputs.model_validate(self.read(state, "inputs_ref"))

    def components(self, state):
        return self.read(state, "components_ref", {})

    def rows(self, state, name):
        return self.store.iter_table(self.components(state)[name])

    def component(self, state, name):
        return self.store.get(self.components(state)[name])

    def save(self, state, values, route, **updates):
        components = {**self.components(state), **values}
        return {
            "components_ref": self.store.put(components, "plan-components"),
            "route": route,
            "status": "running",
            "work_key": "",
            "work_index": 0,
            "results_ref": "",
            "attempt": 0,
            "feedback_ref": "",
            "stage_feedback_ref": "",
            **updates,
        }

    def table(self, rows, name):
        return self.store.put_table(rows, "plan-" + name)

    def obligations(self, state, ids):
        return self.store.table_rows(self.components(state)["content-obligations"], ids)

    def context(self, state, ids):
        return evidence_context(self.store, self.inputs(state), self.obligations(state, ids))

    def grouped_ids(self, state, rows):
        for group in bounded_context_groups(
            self.store, self.inputs(state), rows, self.settings.planning_tokens
        ):
            yield [row["id"] for row in group]

    def start_work(self, state, key, tasks, stage):
        def numbered():
            for index, task in enumerate(tasks):
                if index >= self.settings.workload_tasks:
                    raise ModelFailure("Planning workload allowance exceeded; queue incomplete")
                yield {"id": str(index), **task}

        ref = self.table(numbered(), "work")
        return {
            "work_key": key,
            "work_ref": ref,
            "work_index": 0,
            "results_ref": "",
            "attempt": 0,
            "route": stage,
        }

    def current_work(self, state):
        count = self.store.get(state["work_ref"])["count"]
        if state["work_index"] >= count:
            return None
        return self.store.table_rows(state["work_ref"], [str(state["work_index"])])[0]

    def accept_work(self, state, result, stage):
        return {
            "results_ref": self.store.append_part(state.get("results_ref"), [result], stage),
            "work_index": state["work_index"] + 1,
            "attempt": 0,
            "feedback_ref": "",
            "correction_ref": "",
            "route": stage,
        }

    def results(self, state):
        return self.store.iter_parts(state.get("results_ref"))

    def model_work(self, state, task, stage, prompt, payload, schema, validate):
        payload = {
            **payload,
            "repair_attempt": state.get("attempt", 0),
            "feedback": self.read(state, "stage_feedback_ref", [])
            + self.read(state, "feedback_ref", []),
        }
        try:
            result = (
                schema.model_validate(self.read(state, "correction_ref"))
                if state.get("correction_ref")
                else self.model.call(prompt, payload, schema)
            )
            value = validate(result)
        except (RequestTooLarge, TruncatedOutput):
            ids = task.get("obligation_ids", [])
            if len(ids) < 2:
                raise ModelFailure(
                    "An indivisible planning request exceeds limits; checkpoint retained"
                ) from None
            middle = len(ids) // 2
            tasks = list(self.store.iter_table(state["work_ref"]))
            index = state["work_index"]
            tasks[index : index + 1] = [
                {**task, "obligation_ids": part} for part in (ids[:middle], ids[middle:])
            ]
            if len(tasks) > self.settings.workload_tasks:
                raise ModelFailure("Split planning queue exceeds workload allowance") from None
            tasks = [{**row, "id": str(i)} for i, row in enumerate(tasks)]
            return {
                "work_ref": self.table(tasks, "split-work"),
                "attempt": 0,
                "feedback_ref": "",
                "route": stage,
            }
        except (ValidationError, ValueError) as error:
            description = str(error)[:2400]
            if state.get("attempt", 0) < 2:
                return {
                    "attempt": state.get("attempt", 0) + 1,
                    "feedback_ref": self.store.put([description], "planning-feedback"),
                    "correction_ref": "",
                    "route": stage,
                }
            return self.review_gate(state, stage, "invalid_planning_artifact", description)
        return self.accept_work(state, value, stage)

    def review_gate(self, state, stage, kind, description, obligation_ids=None, section_ids=None):
        revision = digest(
            [
                state["inputs_ref"],
                self.components(state),
                state.get("work_ref"),
                state.get("work_index"),
                stage,
                description,
            ]
        )
        issue = PlanIssue(
            id=stable_id("issue", revision, kind),
            revision=revision,
            stage=stage,
            kind=kind,
            severity="blocking",
            description=description,
            obligation_ids=obligation_ids or [],
            section_ids=section_ids or [],
            repair_stage=stage,
        ).model_dump()
        history = self.read(state, "issue_history_ref", [])
        return {
            "issues_ref": self.store.put([issue], "plan-issues"),
            "issue_history_ref": self.store.put(history + [issue], "plan-issue-history"),
            "review_stage": stage,
            "review_revision": revision,
            "route": "review_plan",
            "status": "review",
        }

    def snapshot_planning_inputs(self, state):
        inputs = snapshot_inputs(state, self.store)
        return {
            "inputs_ref": self.store.put(inputs, "planning-inputs"),
            "workflow": "documentation_planning",
            "route": "compile_template",
            "status": "running",
        }

    def compile_template(self, state):
        inputs = self.inputs(state)
        template = self.store.get(inputs.template_ref)
        stage = "compile_template"
        if state.get("work_key") != stage:
            tasks = (
                {"spans": group}
                for group in bounded_groups(template["spans"], self.settings.planning_tokens)
            )
            return self.start_work(state, stage, tasks, stage)
        task = self.current_work(state)
        if task:

            def validate(result):
                require_exact(
                    [r.span_id for r in result.rules],
                    [r["id"] for r in task["spans"]],
                    "Template span coverage",
                )
                if result.conflicts:
                    raise ValueError("Template contradiction: " + "; ".join(result.conflicts))
                return result.model_dump()

            return self.model_work(
                state,
                task,
                stage,
                "plan_template",
                {
                    "spans": task["spans"],
                    "preamble": template["spans"][0],
                    "workflow_scope": "functional_unit",
                    "brief": inputs.brief.model_dump(exclude={"delivery_mode"}),
                },
                TemplateInterpretation,
                validate,
            )
        results = list(self.results(state))
        rules = [rule for result in results for rule in result["rules"]]
        scopes = {r["application_scope"] for r in results}
        if scopes != {"functional_unit"}:
            return self.review_gate(
                state,
                stage,
                "template_scope_conflict",
                "This workflow requires a template for each functional unit",
            )
        contract = TemplateContract(
            template_ref=inputs.template_ref,
            template_hash=inputs.template_hash,
            spans=template["spans"],
            rules=rules,
            application_scope="functional_unit",
            allows_extensions=all(r["allows_extensions"] for r in results),
            citation_rule=results[0]["citation_rule"],
            audience=results[0]["audience"],
            page_profiles=["capability", "process", "reference", "limitations", "sources"],
        )
        if contract.audience and inputs.origins["audience"] == "default":
            inputs = inputs.model_copy(
                update={
                    "brief": inputs.brief.model_copy(update={"audience": contract.audience}),
                    "origins": {**inputs.origins, "audience": "template"},
                }
            )
        return self.save(
            state,
            {"template-contract": self.store.put(contract, "template-contract")},
            "inventory_content",
            inputs_ref=self.store.put(inputs, "planning-inputs"),
        )

    def inventory_content(self, state):
        stage = "inventory_content"
        inputs = self.inputs(state)
        if state.get("work_key") != stage:
            tasks = ({"part": ref} for ref in self.store.get(inputs.records_ref)["parts"])
            return self.start_work(state, stage, tasks, stage)
        task = self.current_work(state)
        if task:
            rows = [
                make_obligation(row, inputs).model_dump() for row in self.store.get(task["part"])
            ]
            return self.accept_work(state, {"rows": rows}, stage)
        ref = self.table(
            (row for part in self.results(state) for row in part["rows"]), "content-obligations"
        )
        return self.save(state, {"content-obligations": ref}, "discover_documentation_units")

    def discover_documentation_units(self, state):
        stage = "discover_documentation_units"
        if state.get("work_key") == "assign_units":
            return self.assign_global_units(state)
        if state.get("work_key") == "synthesize_units":
            return self.synthesize_units(state)
        if state.get("work_key") != stage:
            tasks = (
                {"obligation_ids": ids}
                for ids in self.grouped_ids(state, self.rows(state, "content-obligations"))
            )
            return self.start_work(state, stage, tasks, stage)
        task = self.current_work(state)
        if task:
            context = self.context(state, task["obligation_ids"])

            def validate(result):
                require_exact(
                    [a.obligation_id for a in result.assignments],
                    task["obligation_ids"],
                    "Unit ownership",
                )
                keys = [u.key for u in result.units]
                require_exact(keys, set(keys), "Candidate unit keys")
                for unit in result.units:
                    if set(unit.evidence_obligation_ids) - set(task["obligation_ids"]):
                        raise ValueError("Unit has unsupported boundary evidence")
                    if not unit.purpose or not unit.outcome:
                        raise ValueError("A functional unit requires a supported goal and outcome")
                obligations = {r["id"]: r for r in context["obligations"]}
                for assignment in result.assignments:
                    valid_owners = set(keys) | {None}
                    if assignment.owner_key not in valid_owners or set(assignment.consumers) - set(
                        keys
                    ):
                        raise ValueError("Missing unit or consumer reference")
                    obligation = obligations[assignment.obligation_id]
                    expected = obligation["eligibility"]
                    if expected != "eligible" and assignment.disposition != expected:
                        raise ValueError("Inherited eligibility cannot change")
                    if expected == "eligible" and assignment.disposition != "included":
                        if (
                            assignment.disposition != "out_of_scope"
                            or not self.inputs(state).brief.hard_scope
                        ):
                            raise ValueError("Eligible information requires full ownership")
                    if not assignment.reason:
                        raise ValueError("Ownership disposition requires a reason")
                value = result.model_dump()
                mapping = {key: stable_id("candidate", task["id"], key) for key in keys}
                for unit in value["units"]:
                    unit["key"] = mapping[unit["key"]]
                for assignment in value["assignments"]:
                    assignment["owner_key"] = mapping.get(assignment["owner_key"])
                    assignment["consumers"] = [mapping[k] for k in assignment["consumers"]]
                return value

            return self.model_work(
                state,
                task,
                stage,
                "plan_units",
                {
                    **context,
                    "brief": self.inputs(state).brief.model_dump(exclude={"delivery_mode"}),
                },
                UnitDiscovery,
                validate,
            )
        results = list(self.results(state))
        candidates = [unit for part in results for unit in part["units"]]
        if not candidates:
            return self.review_gate(state, stage, "empty_scope", "No supported functional unit")
        discoveries = self.table(results, "discoveries")
        candidates_ref = self.table(candidates, "candidates")
        tasks = (
            {"candidates": group}
            for group in bounded_groups(candidates, self.settings.planning_tokens)
        )
        return {
            **self.start_work(state, "synthesize_units", tasks, stage),
            "discovery_ref": discoveries,
            "candidates_ref": candidates_ref,
            "synthesis_round": 0,
            "candidate_map_ref": self.store.put({}, "candidate-map"),
        }

    def synthesize_units(self, state):
        stage = "discover_documentation_units"
        task = self.current_work(state)
        if task:

            def validate(result):
                require_exact(
                    [key for group in result.groups for key in group.candidate_keys],
                    [row["key"] for row in task["candidates"]],
                    "Global synthesis",
                )
                witnesses = {
                    key for row in task["candidates"] for key in row["evidence_obligation_ids"]
                }
                for group in result.groups:
                    if set(group.unit.evidence_obligation_ids) - witnesses:
                        raise ValueError("Synthesis invented evidence")
                return result.model_dump()

            return self.model_work(
                state,
                task,
                stage,
                "plan_unit_synthesis",
                {
                    "candidates": task["candidates"],
                    "brief": self.inputs(state).brief.model_dump(exclude={"delivery_mode"}),
                },
                UnitSynthesis,
                validate,
            )
        mapping = self.read(state, "candidate_map_ref", {})
        candidates = []
        for result in self.results(state):
            for group in result["groups"]:
                unit = group["unit"]
                key = stable_id("group", sorted(group["candidate_keys"]))
                unit["key"] = key
                for old in group["candidate_keys"]:
                    mapping[old] = key
                candidates.append(unit)
        count = self.store.get(state["work_ref"])["count"]
        if count > 1:
            old_count = self.store.get(state["candidates_ref"])["count"]
            if len(candidates) >= old_count and state["synthesis_round"] >= 2:
                raise ModelFailure(
                    "Global unit registry cannot be reduced within bounded synthesis; "
                    "capacity remains unvalidated and checkpoint is retained"
                )
            groups = list(bounded_groups(candidates, self.settings.planning_tokens))
            return {
                **self.start_work(
                    state, "synthesize_units", ({"candidates": g} for g in groups), stage
                ),
                "candidate_map_ref": self.store.put(mapping, "candidate-map"),
                "candidates_ref": self.table(candidates, "candidates"),
                "synthesis_round": state["synthesis_round"] + 1,
            }
        return self.freeze_units(state, candidates, mapping)

    def freeze_units(self, state, candidates, mapping):
        inputs = self.inputs(state)
        brief = inputs.brief
        previous_units = []
        previous_owners = {}
        if inputs.previous_plan_ref:
            previous = self.store.get(inputs.previous_plan_ref)
            previous_units = list(
                self.store.iter_table(previous["components"]["documentation-units"])
            )
            previous_owners = {
                a["obligation_id"]: a["owner_id"]
                for a in self.store.iter_table(previous["components"]["unit-assignments"])
                if a["disposition"] == "included"
            }
        units, final_keys, used = [], {}, set()
        for candidate in sorted(candidates, key=lambda c: sorted(c["evidence_obligation_ids"])):
            prior = [
                u
                for u in previous_units
                if any(
                    previous_owners.get(key) == u["id"]
                    for key in candidate["evidence_obligation_ids"]
                )
            ]
            identifier = (
                prior[0]["id"]
                if len(prior) == 1 and prior[0]["id"] not in used
                else stable_id("unit", sorted(candidate["evidence_obligation_ids"])[0])
            )
            used.add(identifier)
            final_keys[candidate["key"]] = identifier
            units.append(
                DocumentationUnit(
                    id=identifier,
                    title=candidate["title"],
                    purpose=candidate["purpose"],
                    outcome=candidate["outcome"],
                    audience=brief.audience,
                    scope=candidate["scope"],
                    source_epic_id=candidate["source_epic_id"],
                    evidence_obligation_ids=candidate["evidence_obligation_ids"],
                    boundaries=candidate["boundaries"],
                    dependencies=candidate["dependencies"],
                    discovery_rationale=candidate["rationale"],
                    alternative=candidate["alternative"],
                    verification_status="proposed",
                ).model_dump()
            )

        def final(key):
            if key is None:
                return "shared"
            visited = set()
            while key in mapping:
                if key in visited:
                    raise ValueError("Cyclic unit synthesis mapping")
                visited.add(key)
                key = mapping[key]
            return final_keys[key]

        assignments = []
        for part in self.store.iter_table(state["discovery_ref"]):
            for row in part["assignments"]:
                obligation = self.obligations(state, [row["obligation_id"]])[0]
                included = row["disposition"] == "included"
                owner = final(row["owner_key"]) if included else None
                consumers = sorted({final(k) for k in row["consumers"]} - {owner})
                assignments.append(
                    UnitAssignment(
                        id=stable_id("ownership", row["obligation_id"]),
                        obligation_id=row["obligation_id"],
                        owner_id=owner,
                        disposition=row["disposition"],
                        consuming_unit_ids=consumers,
                        dependencies=consumers,
                        boundary_evidence=[e["block_id"] for e in obligation["evidence"]],
                        decision_refs=obligation["decision_refs"],
                        reason=row["reason"],
                    ).model_dump()
                )
        update = self.save(
            state,
            {
                "documentation-units": self.table(units, "documentation-units"),
                "unit-assignments": self.table(assignments, "unit-assignments"),
            },
            "verify_documentation_units",
            units_count=len(units),
        )
        if brief.unit_policy == "single" and len(units) != 1:
            return {
                **update,
                **self.review_gate(
                    {**state, **update},
                    "discover_documentation_units",
                    "scope_mismatch",
                    "Single-unit policy conflicts with independently supported outcomes",
                ),
            }
        if brief.unit_policy == "explicit":
            names = {row.name.casefold() for row in brief.named_boundaries}
            if {row["title"].casefold() for row in units} != names:
                return {
                    **update,
                    **self.review_gate(
                        {**state, **update},
                        "discover_documentation_units",
                        "scope_mismatch",
                        "Discovered boundaries do not match explicit named boundaries",
                    ),
                }
        updated = {**state, **update}
        tasks = (
            {"obligation_ids": ids}
            for ids in self.grouped_ids(updated, self.rows(updated, "content-obligations"))
        )
        return {
            **update,
            **self.start_work(updated, "assign_units", tasks, "discover_documentation_units"),
        }

    def assign_global_units(self, state):
        stage = "discover_documentation_units"
        task = self.current_work(state)
        if task:
            units = list(self.rows(state, "documentation-units"))
            context = self.context(state, task["obligation_ids"])

            def validate(result):
                if result.units:
                    raise ValueError("Assignment pass cannot introduce new units")
                require_exact(
                    [a.obligation_id for a in result.assignments],
                    task["obligation_ids"],
                    "Global unit ownership",
                )
                known = {u["id"] for u in units}
                obligations = {o["id"]: o for o in context["obligations"]}
                rows = []
                for item in result.assignments:
                    if item.owner_key not in known | {None} or set(item.consumers) - known:
                        raise ValueError("Global assignment references unknown units")
                    obligation = obligations[item.obligation_id]
                    expected = obligation["eligibility"]
                    if expected != "eligible" and item.disposition != expected:
                        raise ValueError("Inherited eligibility cannot change")
                    if expected == "eligible" and item.disposition != "included":
                        if (
                            item.disposition != "out_of_scope"
                            or not self.inputs(state).brief.hard_scope
                        ):
                            raise ValueError("Global assignment omitted eligible knowledge")
                    owner = (item.owner_key or "shared") if item.disposition == "included" else None
                    rows.append(
                        UnitAssignment(
                            id=stable_id("ownership", item.obligation_id),
                            obligation_id=item.obligation_id,
                            owner_id=owner,
                            disposition=item.disposition,
                            consuming_unit_ids=sorted(set(item.consumers) - {owner}),
                            dependencies=sorted(set(item.consumers) - {owner}),
                            boundary_evidence=[e["block_id"] for e in obligation["evidence"]],
                            decision_refs=obligation["decision_refs"],
                            reason=item.reason,
                        ).model_dump()
                    )
                return {"rows": rows}

            return self.model_work(
                state,
                task,
                stage,
                "plan_units",
                {
                    **context,
                    "mode": "assign_to_fixed_global_units",
                    "fixed_units": units,
                    "brief": self.inputs(state).brief.model_dump(exclude={"delivery_mode"}),
                },
                UnitDiscovery,
                validate,
            )
        ref = self.table(
            (row for part in self.results(state) for row in part["rows"]), "unit-assignments"
        )
        return self.save(state, {"unit-assignments": ref}, "verify_documentation_units")

    def verify_documentation_units(self, state):
        stage = "verify_documentation_units"
        if state.get("work_key") != stage:
            tasks = (
                {"obligation_ids": ids}
                for ids in self.grouped_ids(state, self.rows(state, "content-obligations"))
            )
            return self.start_work(state, stage, tasks, stage)
        task = self.current_work(state)
        if task:
            assignments = [
                a
                for a in self.rows(state, "unit-assignments")
                if a["obligation_id"] in task["obligation_ids"]
            ]

            def validate(result):
                require_exact(
                    result.checked_obligation_ids, task["obligation_ids"], "Boundary audit"
                )
                require_exact(result.checked_section_ids, [], "Boundary section audit")
                return result.model_dump()

            return self.model_work(
                state,
                task,
                stage,
                "plan_boundaries",
                {
                    **self.context(state, task["obligation_ids"]),
                    "assignments": assignments,
                    "units": list(self.rows(state, "documentation-units")),
                    "brief": self.inputs(state).brief.model_dump(exclude={"delivery_mode"}),
                    "sections": [],
                    "global_witness_references_validated": True,
                    "owned_obligation_ids": task["obligation_ids"],
                },
                SemanticAudit,
                validate,
            )
        results = list(self.results(state))
        findings = [f for r in results for f in r["findings"]]
        if findings:
            return self.repair(state, findings, stage)
        inputs = self.inputs(state)
        contract = self.component(state, "template-contract")
        units = [
            {**u, "verification_status": "verified"}
            for u in self.rows(state, "documentation-units")
        ]
        instances = []
        for unit in units:
            instances.append(
                TemplateInstance(
                    id=stable_id("instance", unit["id"]),
                    unit_id=unit["id"],
                    contract_ref=self.components(state)["template-contract"],
                    metadata={
                        "title": unit["title"],
                        "purpose": unit["purpose"],
                        "audience": unit["audience"],
                        "scope": unit["scope"],
                        "product_name": inputs.brief.product_name,
                        "last_reviewed": inputs.brief.last_reviewed,
                        "knowledge_revision": inputs.knowledge_revision,
                        "source_set": inputs.selection_ref,
                    },
                    obligation_ids=[r["span_id"] for r in contract["rules"] if r["required"]],
                    exceptions=[],
                    compliance={
                        r["span_id"]: "required" for r in contract["rules"] if r["required"]
                    },
                )
            )
        return self.save(
            state,
            {
                "documentation-units": self.table(units, "documentation-units"),
                "template-instances": self.table(instances, "template-instances"),
                "boundary-audit": self.table(results, "boundary-audit"),
            },
            "plan_logical_structure",
        )

    def plan_logical_structure(self, state):
        from docgen.planning_layout import root_sections

        stage = "plan_logical_structure"
        if state.get("work_key") != stage:
            owners = defaultdict(list)
            for assignment in self.rows(state, "unit-assignments"):
                if assignment["disposition"] == "included":
                    owners[assignment["owner_id"]].append(assignment["obligation_id"])

            def tasks():
                for owner, ids in sorted(owners.items()):
                    for group in self.grouped_ids(state, self.obligations(state, ids)):
                        yield {"owner": owner, "obligation_ids": group}

            return self.start_work(state, stage, tasks(), stage)
        task = self.current_work(state)
        if task:
            roots = root_sections(self, state)
            allowed = [r for r in roots if r["owner_id"] == task["owner"]]

            def validate(result):
                require_exact(
                    [key for topic in result.topics for key in topic.obligation_ids],
                    task["obligation_ids"],
                    "Logical allocation",
                )
                for topic in result.topics:
                    if topic.template_span_id not in {r["template_span_id"] for r in allowed}:
                        raise ValueError("Topic references an unavailable template section")
                    if set(topic.supporting_span_ids) - {r["template_span_id"] for r in allowed}:
                        raise ValueError("Topic mentions an unavailable template section")
                return {"owner": task["owner"], **result.model_dump()}

            return self.model_work(
                state,
                task,
                stage,
                "plan_topics",
                {
                    **self.context(state, task["obligation_ids"]),
                    "allowed_sections": allowed,
                    "owner_id": task["owner"],
                    "brief": self.inputs(state).brief.model_dump(exclude={"delivery_mode"}),
                },
                LogicalProposal,
                validate,
            )
        roots = root_sections(self, state)
        root_lookup = {(r["owner_id"], r["template_span_id"]): r for r in roots}
        sections = {r["id"]: r for r in roots}
        assignments = []
        for result in self.results(state):
            for topic in result["topics"]:
                parent = root_lookup[result["owner"], topic["template_span_id"]]
                identifier = stable_id("section", parent["id"], topic["key"].casefold())
                if identifier not in sections:
                    sections[identifier] = LogicalSection(
                        id=identifier,
                        topic_id=stable_id("topic", identifier),
                        owner_id=result["owner"],
                        template_instance_id=parent["template_instance_id"],
                        template_span_id=parent["template_span_id"],
                        parent_id=parent["id"],
                        title=topic["title"],
                        reader_question=topic["reader_question"],
                        purpose=topic["learning_outcome"],
                        order=len(sections),
                        scope=parent["scope"],
                        form=topic["form"],
                        role="topic",
                        explanation_order=topic["explanation_order"],
                    ).model_dump()
                assignments.extend(
                    {
                        "id": key,
                        "section_id": identifier,
                        "supporting_span_ids": topic["supporting_span_ids"],
                    }
                    for key in topic["obligation_ids"]
                )
        return self.save(
            state,
            {
                "logical-sections": self.table(sections.values(), "logical-sections"),
                "topic-ownership": self.table(assignments, "topic-ownership"),
            },
            "allocate_content",
        )

    def allocate_content(self, state):
        from docgen.planning_layout import allocate

        stage = "allocate_content"
        if state.get("work_key") != stage:
            ref = self.components(state)["unit-assignments"]
            tasks = ({"part": part} for part in self.store.get(ref)["parts"])
            return self.start_work(state, stage, tasks, stage)
        task = self.current_work(state)
        if task:
            rows = allocate(self, state, self.store.get(task["part"]))
            return self.accept_work(state, {"rows": rows}, stage)
        return self.save(
            state,
            {
                "content-allocations": self.table(
                    (row for part in self.results(state) for row in part["rows"]),
                    "content-allocations",
                )
            },
            "design_page_tree",
        )

    def design_page_tree(self, state):
        from docgen.planning_layout import make_pages

        stage = "design_page_tree"
        if state.get("work_key") != stage:
            sections = [s for s in self.rows(state, "logical-sections") if s["role"] == "topic"]
            tasks = (
                {"sections": group}
                for group in bounded_groups(sections, self.settings.planning_tokens)
            )
            return self.start_work(state, stage, tasks, stage)
        task = self.current_work(state)
        if task:
            allocations = list(self.rows(state, "content-allocations"))
            counts = {
                s["id"]: sum(a["canonical_section_id"] == s["id"] for a in allocations)
                for s in task["sections"]
            }
            volumes = {}
            for section in task["sections"]:
                identifiers = [
                    a["obligation_id"]
                    for a in allocations
                    if a["canonical_section_id"] == section["id"]
                ]
                records = self.context(state, identifiers)["records"]
                volumes[section["id"]] = sum(
                    len(
                        str(r["record"].get("statement", r["record"].get("definition", ""))).split()
                    )
                    for r in records
                )

            def validate(result):
                require_exact(
                    [r.section_id for r in result.choices],
                    [s["id"] for s in task["sections"]],
                    "Page subdivision",
                )
                if self.inputs(state).brief.delivery_mode == "single_page" and any(
                    r.detail for r in result.choices
                ):
                    raise ValueError("single_page does not permit unit detail pages")
                return result.model_dump()

            return self.model_work(
                state,
                task,
                stage,
                "plan_subdivision",
                {
                    "sections": task["sections"],
                    "obligation_counts": counts,
                    "supported_statement_words": volumes,
                    "delivery_mode": self.inputs(state).brief.delivery_mode,
                    "split_review_words": self.settings.page_split_words,
                },
                Subdivision,
                validate,
            )
        choices = [r for part in self.results(state) for r in part["choices"]]
        pages = make_pages(self, state, choices)
        return self.save(state, {"pages": self.table(pages, "pages")}, "write_section_briefs")

    def write_section_briefs(self, state):
        from docgen.planning_layout import brief_tasks, validate_brief

        stage = "write_section_briefs"
        if state.get("work_key") != stage:
            return self.start_work(state, stage, brief_tasks(self, state), stage)
        task = self.current_work(state)
        if task:
            ids = task["obligation_ids"]
            obligations = self.obligations(state, ids)
            allocation = {a["obligation_id"]: a for a in self.rows(state, "content-allocations")}
            full = [
                key
                for key in ids
                if allocation[key]["canonical_section_id"] == task["section"]["id"]
            ]
            supporting = [key for key in ids if key not in full]

            def validate(result):
                require_exact(result.checked_obligation_ids, ids, "Brief content")
                validate_brief(result, ids)
                return SectionBrief(
                    id=stable_id("brief", task["section"]["id"], ids),
                    section_id=task["section"]["id"],
                    page_id=task["page_id"],
                    part=state["work_index"],
                    form=task["section"]["form"],
                    template_span_id=task["section"]["template_span_id"],
                    full_treatment_ids=full,
                    supporting_ids=supporting,
                    record_ids=[r["record_id"] for r in obligations],
                    evidence=[e for r in obligations for e in r["evidence"]],
                    constraints={r["id"]: r["constraints"] for r in obligations},
                    canonical_links={
                        key: allocation[key]["canonical_section_id"] for key in supporting
                    },
                    content=result,
                ).model_dump()

            payload = {
                **self.context(state, ids),
                "section": task["section"],
                "full_treatment_ids": full,
                "supporting_ids": supporting,
                "template_requirements": task["requirements"],
                "metadata": task["metadata"],
                "child_topics": task["child_topics"],
            }
            return self.model_work(
                state, task, stage, "plan_brief", payload, BriefProposal, validate
            )
        return self.save(
            state,
            {"section-briefs": self.table(self.results(state), "section-briefs")},
            "plan_navigation",
        )

    def plan_navigation(self, state):
        from docgen.planning_layout import make_navigation

        navigation = make_navigation(self, state)
        return self.save(
            state, {"navigation": self.store.put(navigation, "navigation")}, "plan_writing_jobs"
        )

    def plan_writing_jobs(self, state):
        from docgen.planning_layout import writing_jobs

        return self.save(
            state,
            {"writing-jobs": self.table(writing_jobs(self, state), "writing-jobs")},
            "validate_plan",
        )

    def validate_plan(self, state):
        from docgen.planning_validation import validate_plan

        report = validate_plan(self, state, require_audit=False)
        if report["errors"]:
            return self.review_gate(
                state, "validate_plan", "structural_integrity", "; ".join(report["errors"])
            )
        return self.save(
            state, {"validation-report": self.store.put(report, "plan-validation")}, "audit_plan"
        )

    def audit_plan(self, state):
        stage = "audit_plan"
        if state.get("work_key") != stage:
            tasks = (
                {
                    "brief_id": brief["id"],
                    "obligation_ids": brief["full_treatment_ids"] + brief["supporting_ids"],
                }
                for brief in self.rows(state, "section-briefs")
            )
            return self.start_work(state, stage, tasks, stage)
        task = self.current_work(state)
        if task:
            brief = self.store.table_rows(
                self.components(state)["section-briefs"], [task["brief_id"]]
            )[0]
            contract = self.component(state, "template-contract")
            requirements = {
                "spans": [
                    s
                    for s in contract["spans"]
                    if s["id"] == brief["template_span_id"]
                    or s["parent_id"] == brief["template_span_id"]
                ],
                "rules": [
                    r for r in contract["rules"] if r["span_id"] == brief["template_span_id"]
                ],
                "citation_rule": contract["citation_rule"],
            }

            def validate(result):
                require_exact(
                    result.checked_obligation_ids, task["obligation_ids"], "Semantic audit"
                )
                require_exact(result.checked_section_ids, [brief["section_id"]], "Audited sections")
                for finding in result.findings:
                    if set(finding.obligation_ids) - set(task["obligation_ids"]) or set(
                        finding.section_ids
                    ) - {brief["section_id"]}:
                        raise ValueError("Audit returned references outside its work item")
                return {
                    "brief_id": task["brief_id"],
                    "brief_revision": digest(brief),
                    **result.model_dump(),
                }

            return self.model_work(
                state,
                task,
                stage,
                "plan_audit",
                {
                    **self.context(state, task["obligation_ids"]),
                    "briefs": [brief],
                    "section": self.store.table_rows(
                        self.components(state)["logical-sections"], [brief["section_id"]]
                    )[0],
                    "template_requirements": requirements,
                    "allocations": [
                        a
                        for a in self.rows(state, "content-allocations")
                        if a["obligation_id"] in task["obligation_ids"]
                    ],
                },
                SemanticAudit,
                validate,
            )
        results = list(self.results(state))
        findings = [f for r in results for f in r["findings"]]
        if findings:
            return self.repair(state, findings, stage)
        return self.save(
            state, {"semantic-audit": self.table(results, "semantic-audit")}, "finalize_plan"
        )

    def repair(self, state, findings, stage):
        for item in findings:
            if item["kind"] == "upstream_knowledge_gap":
                return self.review_gate(
                    state,
                    stage,
                    item["kind"],
                    item["description"],
                    item["obligation_ids"],
                    item["section_ids"],
                )
        target = min((f["repair_stage"] for f in findings), key=STAGES.index)
        counts = self.read(state, "repairs_ref", {})
        count = counts.get(target, 0)
        if count >= 2:
            return self.review_gate(state, target, "repairs_exhausted", encode(findings))
        counts[target] = count + 1
        retained = {
            "compile_template": [],
            "discover_documentation_units": ["template-contract", "content-obligations"],
            "plan_logical_structure": [
                "template-contract",
                "content-obligations",
                "documentation-units",
                "unit-assignments",
                "template-instances",
                "boundary-audit",
            ],
        }
        base = retained.get(target)
        if base is None:
            base = retained["plan_logical_structure"] + [
                "logical-sections",
                "topic-ownership",
                "content-allocations",
            ]
            if target == "write_section_briefs":
                base += ["pages"]
        components = {key: ref for key, ref in self.components(state).items() if key in base}
        return {
            "components_ref": self.store.put(components, "plan-components"),
            "work_key": "",
            "work_index": 0,
            "results_ref": "",
            "attempt": 0,
            "repairs_ref": self.store.put(counts, "plan-repairs"),
            "feedback_ref": self.store.put(findings, "planning-feedback"),
            "stage_feedback_ref": self.store.put(findings, "planning-feedback"),
            "route": target,
        }

    def review_plan(self, state):
        issues = self.read(state, "issues_ref", [])
        response = interrupt(
            {
                "workflow": "documentation_planning",
                "revision": state["review_revision"],
                "issues": issues,
                "message": "Submit revision-bound decisions; evidence cannot be waived",
            }
        )
        decisions = [PlanDecision.model_validate(row) for row in response.get("decisions", [])]
        require_exact(
            [d.issue_id for d in decisions], [i["id"] for i in issues], "Review decisions"
        )
        if any(d.revision != state["review_revision"] for d in decisions):
            raise ValueError("Stale planning decision revision")
        corrections = [
            d for d in decisions if d.action in {"correct", "retain_unknown", "inapplicable"}
        ]
        if corrections and (len(corrections) != 1 or not corrections[0].correction_ref):
            raise ValueError("Correction requires one evidence-backed immutable replacement")
        if (
            any(i["kind"] in {"upstream_knowledge_gap", "scope_mismatch"} for i in issues)
            and corrections
        ):
            raise ValueError(
                "This issue requires corrected immutable inputs or a new planning revision"
            )
        values = self.read(state, "decisions_ref", []) + [d.model_dump() for d in decisions]
        update = {"decisions_ref": self.store.put(values, "plan-decisions"), "route": "review_plan"}
        if any(d.action in {"defer", "request_upstream"} for d in decisions):
            return update
        correction = self.store.get_object(corrections[0].correction_ref)
        if correction.get("kind") == "planning_component_patch":
            return {**update, **self.correct_component(state, correction)}
        if not state.get("work_key") or self.current_work(state) is None:
            raise ValueError("Use a component patch when no bounded model work item is pending")
        return {
            **update,
            "correction_ref": corrections[0].correction_ref,
            "route": state["review_stage"],
            "status": "running",
            "attempt": 0,
            "issues_ref": self.store.put([], "plan-issues"),
        }

    def correct_component(self, state, value):
        from docgen.planning_contracts import PlanComponentCorrection
        from docgen.planning_validation import TABLE_SCHEMAS

        correction = PlanComponentCorrection.model_validate(value)
        if correction.base_revision != state["review_revision"]:
            raise ValueError("Stale component correction revision")
        components = self.components(state)
        if correction.component not in components:
            raise ValueError("Correction requires an existing completed component")
        rows = list(self.store.iter_table(correction.replacement_ref))
        for row in rows:
            TABLE_SCHEMAS[correction.component].model_validate(row)
        require_exact(
            [row["id"] for row in rows],
            [row["id"] for row in self.rows(state, correction.component)],
            "Correction preserves component identities; new structure requires a new revision",
        )
        stages = {
            "logical-sections": ("plan_logical_structure", "allocate_content"),
            "pages": ("design_page_tree", "write_section_briefs"),
            "section-briefs": ("write_section_briefs", "plan_navigation"),
        }
        producer, route = stages[correction.component]
        invalidated = {"navigation", "writing-jobs", "validation-report", "semantic-audit"}
        if correction.component != "section-briefs":
            invalidated.add("section-briefs")
        if correction.component == "logical-sections":
            invalidated.update({"pages", "content-allocations"})
        retained = {key: ref for key, ref in components.items() if key not in invalidated}
        retained[correction.component] = correction.replacement_ref
        counts = {
            key: count
            for key, count in self.read(state, "repairs_ref", {}).items()
            if STAGES.index(key) < STAGES.index(producer)
        }
        return {
            "components_ref": self.store.put(retained, "plan-components"),
            "route": route,
            "status": "running",
            "work_key": "",
            "work_index": 0,
            "results_ref": "",
            "attempt": 0,
            "feedback_ref": "",
            "stage_feedback_ref": "",
            "repairs_ref": self.store.put(counts, "plan-repairs"),
            "issues_ref": self.store.put([], "plan-issues"),
            "correction_ref": "",
        }

    def finalize_plan(self, state):
        from docgen.planning_export import finalize

        return finalize(self, state)

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
        graph = StateGraph(PlanningState)
        for name in STAGES:
            graph.add_node(name, self.instrument(name))
            graph.add_conditional_edges(name, lambda state: state["route"], [*STAGES, END])
        graph.add_edge(START, STAGES[0])
        return graph.compile(
            checkpointer=checkpointer, interrupt_after=[stop_after] if stop_after else None
        )
