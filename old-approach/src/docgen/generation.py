from time import monotonic
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import ValidationError

from docgen.generation_assets import prepare_inventory
from docgen.generation_contracts import (
    AssetRequest,
    EditorialPage,
    GenerationDecision,
    TechnicalTerm,
    WritingFragment,
    WritingVerification,
)
from docgen.generation_editorial import (
    content_pages,
    polish_documentation,
    verify_editorial_revision,
)
from docgen.generation_export import assemble, mermaid_text, publish, render_fragment
from docgen.generation_inputs import freeze_inputs, load_plan
from docgen.generation_language import language_contract, language_findings
from docgen.generation_validation import (
    diagram_ids,
    markdown_report,
    table_specs,
    validate_fragment,
    validate_verification,
)
from docgen.ingestion import estimate_tokens
from docgen.model import ModelFailure, RequestTooLarge, TruncatedOutput
from docgen.planning_contracts import PlanningInputs
from docgen.planning_helpers import require_exact
from docgen.storage import digest, encode

STAGES = (
    "validate_generation_inputs",
    "prepare_language_contract",
    "prepare_assets",
    "draft_writing_job",
    "verify_writing_job",
    "write_mermaid_diagrams",
    "assemble_pages",
    "polish_documentation",
    "verify_editorial_revision",
    "validate_documentation",
    "review_markdown_presentation",
    "finalize_documentation",
    "review_generation",
)


class GenerationState(TypedDict, total=False):
    run_id: str
    workflow: str
    signature: str
    plan: str
    brief: str
    cache_mode: str
    preview: bool
    inputs_ref: str
    language_ref: str
    approved_terms_ref: str
    asset_decisions_ref: str
    assets_ref: str
    fragments_ref: str
    draft_ref: str
    verification_ref: str
    feedback_ref: str
    job_index: int
    attempt: int
    diagrams_ref: str
    pages_ref: str
    unpolished_pages_ref: str
    editorial_index: int
    editorial_attempt: int
    editorial_draft_ref: str
    editorial_feedback_ref: str
    editorial_review_ref: str
    page_index: int
    page_reviews_ref: str
    validation_ref: str
    presentation_ref: str
    issues_ref: str
    decisions_ref: str
    review_stage: str
    review_revision: str
    release_approval_ref: str
    route: str
    status: str
    export_path: str
    manifest_path: str


class GenerationPipeline:
    def __init__(self, settings, store, model):
        self.settings, self.store, self.model = settings, store, model

    def read(self, state, key, default=None):
        return self.store.get_object(state[key]) if state.get(key) else default

    def inputs(self, state):
        return self.read(state, "inputs_ref")

    def plan(self, state):
        return self.store.get_object(self.inputs(state)["plan_ref"])

    def planning_inputs(self, state):
        return PlanningInputs.model_validate(self.store.get_object(self.plan(state)["inputs_ref"]))

    def rows(self, state, name):
        return self.store.iter_table(self.plan(state)["components"][name])

    def output_root(self, state):
        return self.store.path(f"runs/{state['run_id']}/documentation/pending")

    def job(self, state):
        order = self.inputs(state)["writing_order"]
        if state.get("job_index", 0) >= len(order):
            return None
        return self.store.table_rows(
            self.plan(state)["components"]["writing-jobs"], [order[state.get("job_index", 0)]]
        )[0]

    def payload(self, state, job):
        context = self.store.get_object(job["context_ref"])
        fragments = self.read(state, "fragments_ref", {})
        dependencies = [
            self.store.get_object(fragments[key]["fragment_ref"])
            for key in job["hard_dependencies"]
        ]
        return {
            "job": job,
            "context": context,
            "tables": table_specs(context, job),
            "diagram_ids": diagram_ids(context, job),
            "language_contract": self.read(state, "language_ref"),
            "generation_inputs": self.inputs(state),
            "completed_dependencies": dependencies,
        }

    def call(self, stage, payload, schema, output_limit=None):
        limit = min(output_limit or self.settings.output_tokens, self.settings.output_tokens)
        if estimate_tokens(encode(payload)) + limit + 4000 > self.settings.request_tokens:
            raise RequestTooLarge(
                "Generation task exceeds request budget; revise upstream job partition"
            )
        return self.model.call(stage, {**payload, "generation_output_limit": limit}, schema)

    def gate(self, state, stage, descriptions, kind="content"):
        revision = digest(
            [
                state.get("inputs_ref"),
                state.get("language_ref"),
                state.get("draft_ref"),
                state.get("pages_ref"),
                state.get("editorial_draft_ref"),
                stage,
                descriptions,
            ]
        )
        issues = [
            {
                "id": "generation-" + digest([revision, index])[:20],
                "revision": revision,
                "stage": stage,
                "kind": kind,
                "description": text,
                "severity": "blocking",
            }
            for index, text in enumerate(descriptions)
        ]
        return {
            "issues_ref": self.store.put(issues, "generation-issues"),
            "review_revision": revision,
            "review_stage": stage,
            "status": "awaiting_review",
            "route": "review_generation",
        }

    def validate_generation_inputs(self, state):
        return {
            "inputs_ref": freeze_inputs(self, state),
            "route": "prepare_language_contract",
            "job_index": 0,
            "attempt": 0,
            "status": "running",
        }

    def prepare_language_contract(self, state):
        contract = language_contract(self, state)
        return {
            "language_ref": self.store.put(contract, "generation-language"),
            "route": "prepare_assets",
        }

    def prepare_assets(self, state):
        assets, findings = prepare_inventory(self, state)
        if findings:
            return self.gate(state, "prepare_assets", findings, "asset")
        return {
            "assets_ref": self.store.put(assets, "generation-assets"),
            "route": "draft_writing_job",
        }

    def draft_writing_job(self, state):
        job = self.job(state)
        if job is None:
            return {"route": "write_mermaid_diagrams"}
        if job["id"] in self.read(state, "fragments_ref", {}):
            return {"job_index": state["job_index"] + 1, "route": "draft_writing_job"}
        payload = self.payload(state, job)
        cache_key = digest([state["signature"], payload])
        cache = self.store.path(f"generation-cache/{cache_key}.json")
        if state.get("cache_mode") == "validated" and cache.exists() and not state.get("attempt"):
            from docgen.storage import read_json

            refs = read_json(cache)
            fragment = WritingFragment.model_validate(self.store.get_object(refs["fragment_ref"]))
            verification = WritingVerification.model_validate(
                self.store.get_object(refs["verification_ref"])
            )
            validate_fragment(fragment, job, payload["context"], payload["language_contract"])
            validate_verification(verification, job, payload["context"])
            if any(f.blocking for f in verification.findings):
                raise ValueError("Failed generation response cannot be reused")
            return self.accept(state, job, refs)
        feedback = self.read(state, "feedback_ref", [])
        if feedback:
            payload.update(feedback=feedback, previous_fragment=self.read(state, "draft_ref"))
        try:
            fragment = self.call("gen_write", payload, WritingFragment, job["max_output_tokens"])
        except TruncatedOutput:
            raise RequestTooLarge(
                "Writing output truncated; split this job in a new plan revision"
            ) from None
        except ValidationError as error:
            return self.repair(state, ["Invalid writing response schema: " + str(error)[:1000]])
        return {
            "draft_ref": self.store.put(fragment, "generation-fragment"),
            "route": "verify_writing_job",
        }

    def repair(self, state, findings):
        if state.get("attempt", 0) < 2:
            return {
                "feedback_ref": self.store.put(findings, "generation-feedback"),
                "attempt": state.get("attempt", 0) + 1,
                "route": "draft_writing_job",
            }
        return self.gate(state, "verify_writing_job", findings)

    def accept(self, state, job, refs):
        fragments = {**self.read(state, "fragments_ref", {}), job["id"]: refs}
        return {
            "fragments_ref": self.store.put(fragments, "generation-fragments"),
            "job_index": state["job_index"] + 1,
            "attempt": 0,
            "draft_ref": "",
            "feedback_ref": "",
            "route": "draft_writing_job",
        }

    def verify_writing_job(self, state):
        job = self.job(state)
        payload = self.payload(state, job)
        fragment = WritingFragment.model_validate(self.read(state, "draft_ref"))
        try:
            validate_fragment(fragment, job, payload["context"], payload["language_contract"])
        except ValueError as error:
            return self.repair(state, [str(error)])
        verification = self.call(
            "gen_verify", {**payload, "fragment": fragment.model_dump()}, WritingVerification
        )
        try:
            validate_verification(verification, job, payload["context"])
        except ValueError as error:
            raise ModelFailure(
                "Invalid independent verification accounting: " + str(error)
            ) from error
        ref = self.store.put(verification, "generation-verification")
        findings = [f.description for f in verification.findings if f.blocking]
        text = render_fragment(fragment.model_dump(), job, payload["context"], "index.md")
        mechanical = language_findings(text)
        if findings:
            return {**self.repair(state, findings), "verification_ref": ref}
        refs = {
            "fragment_ref": state["draft_ref"],
            "verification_ref": ref,
            "language_findings": mechanical,
            "job_revision": digest(job),
        }
        if state.get("cache_mode") == "validated":
            from docgen.storage import write_json

            key = digest([state["signature"], payload])
            write_json(self.store.path(f"generation-cache/{key}.json"), refs)
        return self.accept(state, job, refs)

    def write_mermaid_diagrams(self, state):
        diagrams = {}
        obligations = {o["id"]: o for o in self.rows(state, "content-obligations")}
        for brief in self.rows(state, "section-briefs"):
            for spec in brief["content"]["diagrams"]:
                ids = {
                    key
                    for element in [*spec["nodes"], *spec["edges"]]
                    for key in element["obligation_ids"]
                }
                if ids - set(brief["full_treatment_ids"] + brief["supporting_ids"]):
                    return self.gate(
                        state,
                        "write_mermaid_diagrams",
                        ["Unsupported diagram obligation"],
                        "upstream",
                    )
                evidence = {digest(e): e for key in ids for e in obligations[key]["evidence"]}
                diagrams.setdefault(brief["id"], []).append(
                    {
                        "spec": spec,
                        "evidence": list(evidence.values()),
                        "markdown": mermaid_text(spec),
                    }
                )
        return {
            "diagrams_ref": self.store.put(diagrams, "generation-diagrams"),
            "route": "assemble_pages",
        }

    def assemble_pages(self, state):
        pages = assemble(self, state)
        pages_ref = self.store.put(pages, "generation-pages")
        return {
            "pages_ref": pages_ref,
            "unpolished_pages_ref": pages_ref,
            "editorial_index": 0,
            "editorial_attempt": 0,
            "editorial_draft_ref": "",
            "editorial_feedback_ref": "",
            "editorial_review_ref": "",
            "page_index": 0,
            "page_reviews_ref": "",
            "release_approval_ref": "",
            "route": "polish_documentation",
        }

    def polish_documentation(self, state):
        return polish_documentation(self, state)

    def verify_editorial_revision(self, state):
        return verify_editorial_revision(self, state)

    def validate_documentation(self, state):
        load_plan(self.settings, self.store, self.inputs(state)["plan_ref"])
        pages = self.read(state, "pages_ref")
        report = markdown_report(
            pages, self.output_root(state), self.store, self.read(state, "assets_ref")
        )
        if report["findings"]:
            return self.gate(state, "validate_documentation", report["findings"], "structure")
        fragments = self.read(state, "fragments_ref", {})
        jobs = list(self.rows(state, "writing-jobs"))
        require_exact(fragments, [j["id"] for j in jobs], "Completed generation jobs")
        coverage = []
        for job in jobs:
            refs = fragments[job["id"]]
            if refs["job_revision"] != digest(job):
                raise ValueError("Stale completed fragment")
            validate_fragment(
                WritingFragment.model_validate(self.store.get_object(refs["fragment_ref"])),
                job,
                self.store.get_object(job["context_ref"]),
                self.read(state, "language_ref"),
            )
            coverage.extend(job["output_contract"]["full_treatment_ids"])
        expected = [
            a["obligation_id"]
            for a in self.rows(state, "content-allocations")
            if a["disposition"] == "full_treatment"
        ]
        require_exact(coverage, expected, "Global canonical obligation coverage")
        review_pages = content_pages(self, state)
        reviews = self.read(state, "page_reviews_ref", [])
        require_exact(
            [r["page_id"] for r in reviews],
            [p["id"] for p in review_pages],
            "Reviewed editorial pages",
        )
        by_id = {p["id"]: p for p in review_pages}
        for review in reviews:
            if review["output_hash"] != digest(pages[by_id[review["page_id"]]["path"]]):
                raise ValueError("Editorial review does not match the final page")
        report.update(
            coverage={"canonical": len(coverage), "in_scope": len(expected), "passed": True},
            semantic={"job_checks": len(jobs), "page_reviews": reviews},
            language={name: language_findings(text) for name, text in pages.items()},
            formal_ste_compliance="not_claimed",
        )
        return {
            "validation_ref": self.store.put(report, "generation-validation"),
            "route": "review_markdown_presentation",
        }

    def review_markdown_presentation(self, state):
        pages = self.read(state, "pages_ref")
        report = markdown_report(
            pages, self.output_root(state), self.store, self.read(state, "assets_ref")
        )
        report["representative_pages"] = {
            "long_detail": max(pages, key=lambda key: len(pages[key])),
            "table": next((k for k, v in pages.items() if "| ---" in v), None),
            "mermaid": next((k for k, v in pages.items() if "```mermaid" in v), None),
            "unknowns": next((k for k, v in pages.items() if "Unknown" in v), None),
        }
        report["human_readability_review"] = "pending"
        if report["findings"]:
            return self.gate(state, "review_markdown_presentation", report["findings"], "structure")
        return {
            "presentation_ref": self.store.put(report, "generation-presentation"),
            "route": "finalize_documentation",
        }

    def finalize_documentation(self, state):
        load_plan(self.settings, self.store, self.inputs(state)["plan_ref"])
        assets, findings = prepare_inventory(self, state)
        if findings or assets != self.read(state, "assets_ref"):
            raise ValueError("Source assets changed before publication")
        report = markdown_report(
            self.read(state, "pages_ref"), self.output_root(state), self.store, assets
        )
        if not report["passed"]:
            raise ValueError("Output links changed before publication")
        approval = self.read(state, "release_approval_ref")
        status = "complete" if approval else "ready_for_review"
        path, manifest, revision = publish(self, state, status)
        update = {"export_path": path, "manifest_path": manifest, "status": status}
        if approval:
            return {**update, "route": END}
        return {
            **self.gate(
                state,
                "finalize_documentation",
                [
                    "Review the generated Markdown for content accuracy, reader usefulness, "
                    "language and presentation. "
                    f"Documentation: {path}. Manifest: {manifest}. Revision: {revision}."
                ],
                "release",
            ),
            **update,
        }

    def review_generation(self, state):
        issues = self.read(state, "issues_ref", [])
        response = interrupt(
            {
                "workflow": "documentation_generation",
                "issues": issues,
                "revision": state["review_revision"],
                "export_path": state.get("export_path"),
                "draft_ref": state.get("draft_ref"),
                "editorial_draft_ref": state.get("editorial_draft_ref"),
                "editorial_review_ref": state.get("editorial_review_ref"),
                "manifest_path": state.get("manifest_path"),
            }
        )
        decisions = [GenerationDecision.model_validate(d) for d in response.get("decisions", [])]
        require_exact(
            [d.issue_id for d in decisions], [i["id"] for i in issues], "Review decisions"
        )
        if any(d.revision != state["review_revision"] for d in decisions):
            raise ValueError("Stale generation review decision")
        if any(d.action == "defer" for d in decisions):
            return {"route": "review_generation"}
        history = [*self.read(state, "decisions_ref", []), *(d.model_dump() for d in decisions)]
        update = {
            "decisions_ref": self.store.put(history, "generation-decisions"),
            "issues_ref": "",
            "status": "running",
        }
        if any(d.action == "request_upstream" for d in decisions):
            return {**update, "status": "requires_upstream_revision", "route": END}
        if all(i["kind"] == "release" for i in issues) and all(
            d.action == "approve_release" for d in decisions
        ):
            scopes = {"content_accuracy", "reader_usefulness", "language", "markdown"}
            if any(set(d.reviewed_scope) != scopes for d in decisions):
                raise ValueError("Release approval must identify all reviewed scopes")
            return {
                **update,
                "release_approval_ref": self.store.put(
                    {"decisions": decisions, "pages_ref": state["pages_ref"]},
                    "generation-release-approval",
                ),
                "route": "finalize_documentation",
            }
        if (
            all(d.action == "asset_decision" for d in decisions)
            and state["review_stage"] == "prepare_assets"
        ):
            assets = [
                AssetRequest.model_validate(self.store.get_object(d.correction_ref)).model_dump()
                for d in decisions
            ]
            return {
                **update,
                "asset_decisions_ref": self.store.put(
                    [*self.read(state, "asset_decisions_ref", []), *assets],
                    "generation-asset-decisions",
                ),
                "route": "prepare_assets",
            }
        if all(d.action == "approve_term" for d in decisions):
            terms = [
                TechnicalTerm.model_validate(self.store.get_object(d.correction_ref)).model_dump()
                for d in decisions
            ]
            return {
                **update,
                "approved_terms_ref": self.store.put(
                    [*self.read(state, "approved_terms_ref", []), *terms],
                    "generation-approved-terms",
                ),
                "fragments_ref": "",
                "job_index": 0,
                "attempt": 0,
                "release_approval_ref": "",
                "route": "prepare_language_contract",
            }
        if all(d.action == "correct" for d in decisions):
            refs = {d.correction_ref for d in decisions}
            if len(refs) != 1 or None in refs:
                raise ValueError("Correct the affected fragment with one immutable replacement")
            fragment_ref = next(iter(refs))
            if state["review_stage"] == "verify_editorial_revision":
                page = EditorialPage.model_validate(self.store.get_object(fragment_ref))
                expected = content_pages(self, state)[state.get("editorial_index", 0)]
                if page.page_id != expected["id"]:
                    raise ValueError("Correction is not for the interrupted editorial page")
                return {
                    **update,
                    "editorial_draft_ref": fragment_ref,
                    "editorial_feedback_ref": "",
                    "editorial_attempt": 0,
                    "release_approval_ref": "",
                    "route": "verify_editorial_revision",
                }
            fragment = WritingFragment.model_validate(self.store.get_object(fragment_ref))
            jobs = {j["id"]: j for j in self.rows(state, "writing-jobs")}
            if fragment.job_id not in jobs:
                raise ValueError("Correction changes planned job identity")
            if (
                state["review_stage"] == "verify_writing_job"
                and fragment.job_id != self.job(state)["id"]
            ):
                raise ValueError("Correction is not for the interrupted job")
            validate_fragment(
                fragment,
                jobs[fragment.job_id],
                self.store.get_object(jobs[fragment.job_id]["context_ref"]),
                self.read(state, "language_ref"),
            )
            invalid = {fragment.job_id}
            while True:
                dependent = {
                    j["id"] for j in jobs.values() if set(j["hard_dependencies"]) & invalid
                }
                if dependent <= invalid:
                    break
                invalid |= dependent
            retained = {
                k: v for k, v in self.read(state, "fragments_ref", {}).items() if k not in invalid
            }
            return {
                **update,
                "fragments_ref": self.store.put(retained, "generation-fragments"),
                "job_index": self.inputs(state)["writing_order"].index(fragment.job_id),
                "draft_ref": fragment_ref,
                "attempt": 0,
                "feedback_ref": "",
                "release_approval_ref": "",
                "route": "verify_writing_job",
            }
        raise ValueError(
            "Review cannot waive unsupported content, broken provenance or mandatory coverage"
        )

    def instrument(self, name):
        def run(state):
            started = monotonic()
            result = getattr(self, name)(state)
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
        graph = StateGraph(GenerationState)
        for name in STAGES:
            graph.add_node(name, self.instrument(name))
            graph.add_conditional_edges(name, lambda state: state["route"], [*STAGES, END])
        graph.add_edge(START, STAGES[0])
        return graph.compile(
            checkpointer=checkpointer, interrupt_after=[stop_after] if stop_after else None
        )
