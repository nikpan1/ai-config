from pathlib import Path
from typing import Any, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from docgen.authoring import (
    evidence_bundle,
    export_bundle,
    render_draft,
    validate_chapter,
    validate_draft,
)
from docgen.config import STAGES, Settings
from docgen.ingestion import batches, inventory, parse_inventory
from docgen.knowledge import (
    apply_resolution,
    consolidate_coverage,
    namespace,
    validate_extraction,
    validate_knowledge,
    validate_outline,
)
from docgen.llm import Gemini, ModelCaller
from docgen.models import (
    Chapter,
    Coverage,
    Diagrams,
    Draft,
    EvidenceRef,
    Extraction,
    ImageAnalysis,
    Knowledge,
    Outline,
    Resolution,
    ReviewDecision,
    SemanticReview,
)
from docgen.storage import Store, digest, now, read_json, write_json
from docgen.validation import check_links, render_diagrams


class State(TypedDict):
    run_id: str
    stage: str


REVIEW_SOURCES = {
    "review_knowledge": "reconcile",
    "review_outline": "outline",
    "review_documentation": "compose",
}


class Pipeline:
    def __init__(self, store: Store, model: ModelCaller | None = None):
        self.store = store
        self.settings = Settings.model_validate(store.manifest["settings"])
        self.model = model or Gemini(self.settings, store)

    def execute(self, stage: str, directory: Path) -> dict:
        store = self.store
        if stage == "inventory":
            result = inventory(Path(store.manifest["source"]), store.root, store.root.parent)
            write_json(directory / "partial.json", result)
            if not result["documents"]:
                raise ValueError("No readable Markdown documents in selected input")
            return result
        if stage == "parse":
            return parse_inventory(store.root, store.output("inventory"))
        if stage == "extract":
            return self.extract(directory)
        if stage == "reconcile":
            graph = Knowledge.model_validate(store.output("extract"))
            resolution = self.model.call(
                "reconcile_entities",
                {
                    "knowledge": graph.model_dump(),
                    "feedback": store.manifest["feedback"].get(stage, ""),
                },
                Resolution,
                directory,
            )
            graph = apply_resolution(graph, resolution)
            from docgen.preview import graph_preview

            graph_preview(directory / "graph-preview", graph, store.output("parse"), store.root)
            return graph.model_dump()
        if stage == "outline":
            graph = Knowledge.model_validate(store.output("review_knowledge")["artifact"])
            planned = self.model.call(
                "plan_outline",
                {
                    "knowledge": graph.model_dump(),
                    "settings": self.settings.model_dump(),
                    "feedback": store.manifest["feedback"].get(stage, ""),
                },
                Outline,
                directory,
            )
            validate_outline(planned, graph)
            return planned.model_dump()
        if stage == "compose":
            return self.compose(directory)
        if stage == "validate":
            graph = Knowledge.model_validate(store.output("review_knowledge")["artifact"])
            draft = Draft.model_validate(store.output("compose"))
            outline = Outline.model_validate(store.output("review_outline")["artifact"])
            parsed = store.output("parse")
            findings = validate_draft(draft, outline, graph, parsed, store.root)
            findings.extend(render_diagrams(draft, directory / "diagrams", self.settings))
            for chapter in draft.chapters:
                claims = [c for b in chapter.blocks for c in b.claim_ids]
                review = self.model.call(
                    "review_semantics",
                    {
                        "chapter": chapter.model_dump(),
                        "evidence": evidence_bundle(graph, parsed, claims),
                    },
                    SemanticReview,
                    directory,
                    images=self.image_paths(graph, claims, parsed),
                )
                findings.extend(review.findings)
            return {
                "draft_revision": digest(draft.model_dump()),
                "passed": not any(f.severity == "error" for f in findings),
                "findings": [f.model_dump() for f in findings],
                "knowledge_gaps": graph.gaps,
                "unresolved_claim_ids": [c.id for c in graph.claims if c.status == "unresolved"],
                "unresolved_conflicts": [
                    c.model_dump() for c in graph.conflicts if c.status == "unresolved"
                ],
                "semantic_support": "Model assessment; domain review still required",
            }
        if stage == "export":
            return self.export(directory)
        raise ValueError(f"Unknown executable stage: {stage}")

    def image_paths(self, graph: Knowledge, claim_ids: list[str], parsed: dict) -> list[Path]:
        evidence_ids = {e for c in graph.claims if c.id in claim_ids for e in c.evidence_ids}
        asset_ids = {e.asset_id for e in graph.evidence if e.id in evidence_ids and e.asset_id}
        return [
            self.store.root / a["snapshot"]
            for a in parsed["images"]
            if a["id"] in asset_ids and a["snapshot"]
        ]

    def extract(self, directory: Path) -> dict:
        parsed = self.store.output("parse")
        graph = Knowledge(
            entities=[],
            claims=[],
            relationships=[],
            coverage=[],
            evidence=parsed["evidence"],
            gaps=parsed["warnings"],
        )
        source_batches = batches(parsed["spans"], self.settings.batch_chars)
        attempt = self.store.active("extract")
        assert attempt is not None
        for index, batch in enumerate(source_batches):
            supplied = {s["id"] for s in batch}
            context = {"spans": batch, "scope": self.settings.scope}
            key = digest([context, attempt["fingerprint"], attempt["dependencies"]])
            result, reused_from = self.recover_extraction_batch(index, key, supplied, attempt)
            if result is None:
                extracted = self.model.call("extract_claims", context, Extraction, directory)
                for repair in range(self.settings.repair_attempts + 1):
                    write_json(
                        directory / "batch-drafts" / f"{index}-{repair}.json",
                        extracted.model_dump(),
                    )
                    try:
                        validate_extraction(extracted, supplied)
                        break
                    except ValueError as exc:
                        write_json(
                            directory / "batch-drafts" / f"{index}-{repair}-error.json",
                            {"error": str(exc)},
                        )
                        if repair == self.settings.repair_attempts:
                            raise
                        extracted = self.model.call(
                            "repair_extraction",
                            {
                                **context,
                                "extraction": extracted.model_dump(),
                                "validation_error": str(exc),
                            },
                            Extraction,
                            directory,
                        )
                result = namespace(extracted, f"b{index}")
            for field in ("entities", "claims", "relationships", "coverage"):
                getattr(graph, field).extend(getattr(result, field))
            write_json(directory / "batches" / f"{index}.json", result.model_dump())
            write_json(
                directory / "batches" / f"{index}.receipt.json",
                {
                    "key": key,
                    "output_hash": digest(result.model_dump()),
                    "reused_from": reused_from,
                },
            )
            write_json(directory / "partial.json", graph.model_dump())
            self.store.event(
                "extraction_batch",
                {
                    "completed": index + 1,
                    "total": len(source_batches),
                    "attempt": attempt["id"],
                    "reused_from": reused_from,
                },
            )
        image_results = []
        for index, asset in enumerate(parsed["images"]):
            evidence = [e for e in graph.evidence if e.asset_id == asset["id"]]
            if asset["status"] == "unresolved" or not asset["snapshot"]:
                graph.coverage.extend(
                    Coverage(evidence_id=e.id, disposition="unresolved", reason=asset["reason"])
                    for e in evidence
                )
                image_results.append(asset)
                continue
            interpretation = self.model.call(
                "analyze_image",
                {
                    "asset": asset,
                    "evidence": [e.model_dump() for e in evidence],
                    "spans": [s for s in parsed["spans"] if s["id"] in asset["span_ids"]],
                },
                ImageAnalysis,
                directory,
                images=[self.store.root / asset["snapshot"]],
            )
            validate_extraction(interpretation, {e.id for e in evidence})
            result = namespace(interpretation, f"image{index}")
            for field in ("entities", "claims", "relationships", "coverage"):
                getattr(graph, field).extend(getattr(result, field))
            image_results.append(
                {
                    **asset,
                    "status": "excluded"
                    if interpretation.classification == "decorative"
                    else "unresolved"
                    if interpretation.classification == "unreadable"
                    else "analyzed",
                    "reason": interpretation.reason,
                }
            )
        write_json(directory / "images.json", image_results)
        consolidate_coverage(graph)
        validate_knowledge(graph)
        return graph.model_dump()

    def recover_extraction_batch(
        self, index: int, key: str, supplied: set[str], current: dict
    ) -> tuple[Extraction | None, int | None]:
        for previous in reversed(self.store.stage("extract")["attempts"]):
            if (
                previous["id"] == current["id"]
                or previous["execution_id"] != current["execution_id"]
                or previous["status"] != "superseded"
            ):
                continue
            folder = self.store.attempt_dir("extract", previous) / "batches"
            try:
                receipt = read_json(folder / f"{index}.receipt.json")
                data = read_json(folder / f"{index}.json")
                if receipt["key"] != key or receipt["output_hash"] != digest(data):
                    continue
                result = Extraction.model_validate(data)
                validate_extraction(result, supplied)
                return result, previous["id"]
            except (OSError, ValueError, KeyError):
                continue
        return None, None

    def compose(self, directory: Path) -> dict:
        graph = Knowledge.model_validate(self.store.output("review_knowledge")["artifact"])
        outline = Outline.model_validate(self.store.output("review_outline")["artifact"])
        parsed = self.store.output("parse")
        chapters = []
        for plan in outline.chapters:
            context = {
                "plan": plan.model_dump(),
                "settings": self.settings.model_dump(),
                "evidence": evidence_bundle(graph, parsed, plan.required_claim_ids),
                "feedback": self.store.manifest["feedback"].get("compose", ""),
            }
            images = self.image_paths(graph, plan.required_claim_ids, parsed)
            chapter = self.model.call("compose_chapter", context, Chapter, directory, images=images)
            for repair in range(self.settings.repair_attempts + 1):
                findings = validate_chapter(chapter, plan, graph)
                write_json(
                    directory / "chapters" / plan.id / f"draft-{repair}.json", chapter.model_dump()
                )
                if not findings:
                    break
                if repair == self.settings.repair_attempts:
                    write_json(directory / "findings.json", [f.model_dump() for f in findings])
                    raise ValueError(
                        "Chapter failed bounded structural repair; inspect findings.json"
                    )
                chapter = self.model.call(
                    "repair_output",
                    {
                        **context,
                        "chapter": chapter.model_dump(),
                        "findings": [f.model_dump() for f in findings],
                    },
                    Chapter,
                    directory,
                    images=images,
                )
            diagrams = self.model.call(
                "plan_diagram",
                {"chapter": chapter.model_dump(), "evidence": context["evidence"]},
                Diagrams,
                directory,
            )
            chapter.diagrams = diagrams.diagrams
            findings = validate_chapter(chapter, plan, graph)
            if findings:
                write_json(directory / "findings.json", [f.model_dump() for f in findings])
                raise ValueError("Unsupported diagram; inspect findings.json")
            chapters.append(chapter)
            write_json(directory / "partial.json", Draft(chapters=chapters).model_dump())
            render_draft(directory / "draft", Draft(chapters=chapters))
        return Draft(chapters=chapters).model_dump()

    def export(self, directory: Path) -> dict:
        approved = self.store.output("review_documentation")
        draft = Draft.model_validate(approved["artifact"])
        revision = approved["revision"]
        validation = self.store.output("validate")
        if not validation["passed"] or validation["draft_revision"] != revision:
            raise ValueError("Export requires passing validation for this exact revision")
        bundle_id = digest([revision, approved["decision"], self.settings.customer_evidence])
        destination = (
            self.store.root.parent.parent / "output" / self.store.manifest["run_id"] / bundle_id
        )
        graph = Knowledge.model_validate(self.store.output("review_knowledge")["artifact"])
        outline = Outline.model_validate(self.store.output("review_outline")["artifact"])
        if (destination / "checksums.json").exists():
            checksums = read_json(destination / "checksums.json")
            if all(
                (destination / p).is_file() and digest((destination / p).read_bytes()) == h
                for p, h in checksums.items()
            ):
                record = {
                    "path": str(destination),
                    "revision": revision,
                    "checksums": checksums,
                    "current": True,
                }
                existing = next(
                    (e for e in self.store.manifest["exports"] if e["path"] == str(destination)),
                    None,
                )
                if existing:
                    existing["current"] = True
                else:
                    self.store.manifest["exports"].append(record)
                self.store.save()
                return record
            raise ValueError(
                "Historical export is corrupt; preserve it and select another output root"
            )
        temporary = directory / "bundle"
        result = export_bundle(
            self.store,
            temporary,
            draft,
            graph,
            self.store.output("parse"),
            outline,
            revision,
            approved["decision"]["included_image_ids"],
            self.settings.customer_evidence,
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        problems = check_links(temporary)
        if problems:
            write_json(directory / "link-errors.json", problems)
            raise ValueError("Export contains broken links; inspect link-errors.json")
        temporary.replace(destination)
        record = {"path": str(destination), **result, "current": True}
        self.store.manifest["exports"].append(record)
        self.store.save()
        return record

    def review_result(self, stage: str, decision: ReviewDecision) -> dict:
        store = self.store
        source = store.output(REVIEW_SOURCES[stage])
        revision = digest(source)
        if decision.revision != revision:
            raise ValueError("Outdated review revision")
        artifact = decision.patch if decision.patch is not None else source
        if stage == "review_knowledge":
            graph = Knowledge.model_validate(artifact)
            original = Knowledge.model_validate(source)
            if not {c.id for c in original.claims} <= {c.id for c in graph.claims}:
                raise ValueError(
                    "Retain original claims; reject or mark unresolved instead of deleting"
                )
            if not {c.id for c in original.conflicts} <= {c.id for c in graph.conflicts}:
                raise ValueError("Retain original conflicts and record their resolution")
            if [e.model_dump() for e in graph.evidence] != [
                e.model_dump() for e in original.evidence
            ]:
                raise ValueError(
                    "Source evidence is immutable; add attributed reviewer statements separately"
                )
            for index, statement in enumerate(decision.statements):
                evidence = EvidenceRef(
                    id="review-" + digest([revision, decision.reviewer, index, statement])[:24],
                    kind="reviewer",
                    statement=statement,
                    reviewer=decision.reviewer,
                    timestamp=now(),
                )
                graph.evidence.append(evidence)
                placeholder = f"review:{index + 1}"
                for claim in graph.claims:
                    claim.evidence_ids = [
                        evidence.id if e == placeholder else e for e in claim.evidence_ids
                    ]
                for entity in graph.entities:
                    entity.evidence_ids = [
                        evidence.id if e == placeholder else e for e in entity.evidence_ids
                    ]
                supported = [c.id for c in graph.claims if evidence.id in c.evidence_ids]
                graph.coverage.append(
                    Coverage(
                        evidence_id=evidence.id,
                        disposition="covered" if supported else "excluded",
                        claim_ids=supported,
                        reason=""
                        if supported
                        else "Attributed statement without a published claim",
                    )
                )
            if decision.patch is None:
                for claim in graph.claims:
                    if claim.status == "candidate":
                        claim.status = "accepted"
            validate_knowledge(graph, approved=True)
            artifact = graph.model_dump()
        elif stage == "review_outline":
            outline = Outline.model_validate(artifact)
            validate_outline(
                outline, Knowledge.model_validate(store.output("review_knowledge")["artifact"])
            )
            artifact = outline.model_dump()
        else:
            if decision.patch is not None:
                raise ValueError("Revise composition before approving changed documentation")
            validation = store.output("validate")
            if not validation["passed"] or validation["draft_revision"] != revision:
                raise ValueError("Resolve validation errors before final approval")
            assets = {a["id"] for a in store.output("parse")["images"] if a["snapshot"]}
            if not set(decision.included_image_ids) <= assets:
                raise ValueError("Selected images must exist in the source snapshot")
        return {
            "artifact": artifact,
            "revision": digest(artifact),
            "source_revision": revision,
            "decision": decision.model_dump(),
            "timestamp": now(),
        }

    def node(self, stage: str) -> Any:
        def run(state: State) -> dict:
            del state
            store = self.store
            active = store.active(stage)
            if active and active["status"] == "completed":
                return {"stage": stage}
            attempt, directory = store.begin(stage, self.settings)
            if stage in REVIEW_SOURCES:
                source = store.output(REVIEW_SOURCES[stage])
                request = {
                    "stage": stage,
                    "revision": digest(source),
                    "artifact": source,
                    "validation": store.output("validate")
                    if stage == "review_documentation"
                    else None,
                }
                write_json(directory / "review-request.json", request)
                attempt["status"] = "waiting_for_review"
                store.manifest["status"] = "waiting_for_review"
                store.persist_attempt(stage, attempt)
                response = interrupt(
                    {
                        "stage": stage,
                        "revision": request["revision"],
                        "request": str(directory / "review-request.json"),
                    }
                )
                decision = ReviewDecision.model_validate(response)
                result = self.review_result(stage, decision)
                write_json(directory / "review.json", result)
                if stage == "review_knowledge":
                    from docgen.preview import graph_preview

                    graph_preview(
                        directory / "graph-preview",
                        Knowledge.model_validate(result["artifact"]),
                        store.output("parse"),
                        store.root,
                    )
                store.commit(stage, attempt, result)
            else:
                try:
                    result = self.execute(stage, directory)
                    store.commit(stage, attempt, result)
                except Exception as exc:
                    attempt.update(status="failed", ended_at=now())
                    write_json(
                        directory / "error.json",
                        {
                            "type": type(exc).__name__,
                            "message": str(exc)
                            if isinstance(exc, ValueError)
                            else "Stage failed; inspect partial artifacts",
                        },
                    )
                    store.manifest["status"] = "failed"
                    store.persist_attempt(stage, attempt)
                    raise
            return {"stage": stage}

        return run

    def run(self, decision: ReviewDecision | None = None) -> dict:
        graph = StateGraph(State)
        previous = START
        for stage in STAGES:
            graph.add_node(stage, self.node(stage))
            graph.add_edge(previous, stage)
            previous = stage
        graph.add_edge(previous, END)
        self.store.manifest["status"] = "running"
        self.store.save()
        with SqliteSaver.from_conn_string(str(self.store.root / "checkpoints.sqlite")) as saver:
            compiled = graph.compile(checkpointer=saver)
            config: RunnableConfig = {
                "configurable": {"thread_id": self.store.manifest["execution_id"]}
            }
            value: Any = (
                Command(resume=decision.model_dump())
                if decision
                else {"run_id": self.store.manifest["run_id"], "stage": ""}
            )
            result = compiled.invoke(value, config=config)
        if "__interrupt__" not in result:
            self.store.manifest["status"] = "completed"
            self.store.save()
        return {"run_id": self.store.manifest["run_id"], "status": self.store.manifest["status"]}


def run_pipeline(
    store: Store,
    model: ModelCaller | None = None,
    decision: ReviewDecision | None = None,
    settings: Settings | None = None,
) -> dict:
    with store.lock():
        effective = settings or Settings.model_validate(store.manifest["settings"])
        invalidated = store.verify(effective)
        if decision and invalidated:
            raise ValueError("Review became stale: " + "; ".join(invalidated))
        store.manifest["settings"] = effective.model_dump()
        store.save()
        if store.manifest["status"] == "cancelled" and not decision:
            raise ValueError("Run cancelled; reset a stage before continuing")
        pipeline = Pipeline(store, model)
        if decision:
            stage = next(
                (s for s in STAGES if store.stage(s)["status"] == "waiting_for_review"), None
            )
            if not stage:
                raise ValueError("No pending review")
            if decision.revision != digest(store.output(REVIEW_SOURCES[stage])):
                raise ValueError("Outdated review revision")
            if decision.action != "approve":
                store.event("review_decision", decision.model_dump())
                if decision.action == "revise":
                    source_stage = REVIEW_SOURCES[stage]
                    store.manifest["feedback"][source_stage] = decision.rationale
                    store.reset(source_stage)
                elif decision.action == "cancel":
                    store.manifest["status"] = "cancelled"
                    store.save()
                return {"status": store.manifest["status"], "action": decision.action}
            pipeline.review_result(stage, decision)
        result = pipeline.run(decision)
        while (
            store.stage("validate")["status"] == "completed"
            and not store.output("validate")["passed"]
        ):
            outline_attempt = store.active("review_outline")
            assert outline_attempt is not None
            key = outline_attempt["output_hash"]
            counts = store.manifest.setdefault("repair_counts", {})
            count = counts.get(key, 0)
            if count >= effective.repair_attempts:
                break
            counts[key] = count + 1
            store.manifest["feedback"]["compose"] = store.output("validate")["findings"]
            store.reset("compose")
            result = pipeline.run()
        return result
