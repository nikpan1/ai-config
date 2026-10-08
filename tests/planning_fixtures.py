from collections import defaultdict
from pathlib import Path

from conftest import FixtureModel

from docgen.planning import PlanningPipeline
from docgen.storage import write_json
from docgen.workflow import Pipeline, persistent_graph


def knowledge_fixture(tmp_path, settings, store, areas=("Archive",), count=2):
    source = tmp_path / "sources.md"
    text = (
        "\n\n".join(
            f"{area} requirement {index}: Preserve revision {index} on failure; "
            f"run at 02:00 UTC only when approved, unless a hold exists."
            for area in areas
            for index in range(count)
        )
        + "\n"
    )
    source.write_text(text, encoding="utf-8")
    with persistent_graph(Pipeline(settings, store, FixtureModel())) as graph:
        result = graph.invoke(
            {"run_id": "knowledge", "source": str(source), "signature": "fixture"},
            {"configurable": {"thread_id": "knowledge"}, "recursion_limit": 10000},
        )
    assert result["status"] == "complete"
    return result["bundle_ref"]


def planning_state(tmp_path, bundle_ref, brief=None, run_id="planning"):
    template = Path(__file__).resolve().parents[1] / "data/template.md"
    brief_path = tmp_path / f"{run_id}-brief.json"
    write_json(brief_path, brief or {})
    return {
        "run_id": run_id,
        "workflow": "documentation_planning",
        "signature": "fixture",
        "knowledge": bundle_ref,
        "template": str(template),
        "brief": str(brief_path),
        "status": "running",
    }


class PlanningFixtureModel:
    def __init__(self, transform=None):
        self.calls = []
        self.payloads = []
        self.transform = transform

    def call(self, stage, payload, schema):
        self.calls.append(stage)
        self.payloads.append(payload)
        value = getattr(self, stage)(payload)
        result = schema.model_validate(value)
        return self.transform(stage, payload, result) if self.transform else result

    def plan_template(self, payload):
        roles = {
            "Executive Summary": "summary",
            "Core Features and Functionalities": "capabilities",
            "Processes or Flows": "process",
            "Data, States, and Business Rules": "reference",
            "Integrations and Dependencies": "integrations",
            "Roles, Access, and Operational Controls": "access",
            "Limitations, Exceptions, and Open Questions": "limitations",
            "Source References and Coverage": "sources",
        }
        return {
            "rules": [
                {
                    "span_id": s["id"],
                    "role": roles.get(s["heading"], "metadata" if s["level"] <= 1 else "other"),
                    "required": s["level"] <= 2,
                    "repeatable": s["level"] > 2,
                    "example": s["level"] > 2,
                    "requirements": [s["text"]],
                    "forms": ["explanation"],
                    "rationale": "Explicit template span",
                }
                for s in payload["spans"]
            ],
            "application_scope": "functional_unit",
            "allows_extensions": True,
            "citation_rule": "Cite every substantive assertion",
            "audience": None,
            "conflicts": [],
        }

    def plan_units(self, payload):
        records = {r["id"]: r["record"] for r in payload["records"]}
        if payload.get("mode") == "assign_to_fixed_global_units":
            known = {u["title"]: u["id"] for u in payload["fixed_units"]}
            return {
                "units": [],
                "assignments": [
                    {
                        "obligation_id": o["id"],
                        "owner_key": known[
                            records[o["record_id"]].get("statement", "Shared").split()[0]
                        ],
                        "disposition": "included"
                        if o["eligibility"] == "eligible"
                        else o["eligibility"],
                        "consumers": [],
                        "reason": o["reason"] or "Final supported boundary",
                    }
                    for o in payload["obligations"]
                ],
            }
        groups = defaultdict(list)
        for obligation in payload["obligations"]:
            row = records[obligation["record_id"]]
            area = row.get("statement", "Shared").split()[0]
            groups[area].append(obligation)
        units, assignments = [], []
        for area, obligations in groups.items():
            units.append(
                {
                    "key": area,
                    "title": area,
                    "purpose": f"Understand {area}",
                    "outcome": f"Complete {area}",
                    "scope": area,
                    "evidence_obligation_ids": [obligations[0]["id"]],
                    "boundaries": ["Preserve source scope"],
                    "dependencies": [],
                    "rationale": "Distinct evidenced outcome",
                    "alternative": "Detail page is insufficient",
                    "source_epic_id": None,
                }
            )
            for obligation in obligations:
                assignments.append(
                    {
                        "obligation_id": obligation["id"],
                        "owner_key": area,
                        "disposition": "included"
                        if obligation["eligibility"] == "eligible"
                        else obligation["eligibility"],
                        "consumers": [],
                        "reason": obligation["reason"] or "Supported reader goal",
                    }
                )
        return {"units": units, "assignments": assignments}

    def plan_unit_synthesis(self, payload):
        groups = defaultdict(list)
        for unit in payload["candidates"]:
            groups[unit["title"]].append(unit)
        return {
            "groups": [
                {"candidate_keys": [u["key"] for u in units], "unit": units[0]}
                for units in groups.values()
            ]
        }

    def plan_boundaries(self, payload):
        return {
            "checked_obligation_ids": [o["id"] for o in payload["obligations"]],
            "checked_section_ids": [],
            "findings": [],
            "reader_task_findings": [],
        }

    def plan_topics(self, payload):
        span = next(
            (
                s["template_span_id"]
                for s in payload["allowed_sections"]
                if s["role"] == "capabilities"
            ),
            payload["allowed_sections"][0]["template_span_id"],
        )
        return {
            "topics": [
                {
                    "key": "behavior",
                    "title": "Behavior and exceptions",
                    "template_span_id": span,
                    "reader_question": "When can the action run?",
                    "learning_outcome": "Understand timing, approval, holds and failures",
                    "form": "explanation",
                    "obligation_ids": [o["id"] for o in payload["obligations"]],
                    "explanation_order": ["Purpose", "Conditions", "Exceptions"],
                }
            ]
        }

    def plan_subdivision(self, payload):
        return {
            "choices": [
                {
                    "section_id": s["id"],
                    "detail": payload["delivery_mode"] == "multi_page",
                    "profile": "capability",
                    "reader_task": s["reader_question"],
                    "estimated_words": 900,
                    "rationale": "Coherent independent explanation",
                    "alternatives": "Inline treatment",
                }
                for s in payload["sections"]
            ]
        }

    def plan_brief(self, payload):
        return {
            "reader_question": payload["section"]["reader_question"],
            "learning_outcome": payload["section"]["purpose"],
            "instructions": [
                "Preserve all exact records, attached constraints, scope and source references"
            ],
            "explanation_order": ["Goal", "Conditions", "Exceptions"],
            "tables": [],
            "diagrams": [],
            "unknowns": ["No unsupported attributes may be inferred"],
            "boundaries": ["Selected knowledge"],
            "completion_checks": ["Every original field and qualification is represented"],
            "checked_obligation_ids": [o["id"] for o in payload["obligations"]],
        }

    def plan_audit(self, payload):
        return {
            "checked_obligation_ids": [o["id"] for o in payload["obligations"]],
            "checked_section_ids": [b["section_id"] for b in payload["briefs"]],
            "findings": [],
            "reader_task_findings": ["Exception reachable from the unit root"],
        }


def run_plan(state, settings, store, model=None, stop_after=None):
    model = model or PlanningFixtureModel()
    pipeline = PlanningPipeline(settings, store, model)
    config = {"configurable": {"thread_id": state["run_id"]}, "recursion_limit": 10000}
    with persistent_graph(pipeline, stop_after) as graph:
        result = graph.invoke(state, config)
    return result, pipeline, model
