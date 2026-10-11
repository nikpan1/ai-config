from pathlib import Path
from time import monotonic

from pydantic import Field

from docgen.batching import plan_batches, split_batch
from docgen.config import Settings
from docgen.contracts import Block, Extraction, Record, Verification
from docgen.ingestion import estimate_tokens
from docgen.model import GeminiModel, RequestTooLarge, TruncatedOutput
from docgen.storage import Artifacts, digest, read_json, write_json
from docgen.validation import validate_extraction


class FactScore(Record):
    reference_id: str
    retained_facts: list[bool]
    retained_qualifications: list[bool]
    correct_entity_distinctions: list[bool]
    supporting_claim_ids: list[str]
    explanation: str


class QualityAssessment(Record):
    scores: list[FactScore]
    unsupported_claim_ids: list[str]
    incorrect_entity_merges: list[str]
    lost_qualifications: list[str]
    limitations: list[str]
    review_effort_issues: int = Field(ge=0)


def selected_snapshot(snapshot, reference, target_tokens):
    blocks = [Block.model_validate(block) for block in snapshot["blocks"]]
    selected = set()
    for sample in reference["samples"]:
        matching = [
            block
            for block in blocks
            if block.path == sample["path"]
            and block.snapshot == sample["snapshot"]
            and block.line_start <= sample["line_start"] <= block.line_end
        ]
        if not matching:
            raise ValueError(f"Reference {sample['id']} no longer matches the source snapshot")
        selected.update(block.id for block in matching)
    size = sum(estimate_tokens(block.content) for block in blocks if block.id in selected)
    for block in blocks:
        if size >= target_tokens:
            break
        if block.id not in selected:
            selected.add(block.id)
            size += estimate_tokens(block.content)
    links = {
        key: [
            link
            if link.get("block_id") in selected
            else {
                **link,
                "block_id": None,
                "status": "outside_evaluation_sample",
            }
            for link in values
        ]
        for key, values in snapshot["links"].items()
        if key in selected
    }
    return {
        **snapshot,
        "blocks": [block.model_dump() for block in blocks if block.id in selected],
        "links": links,
    }


def run_variant(
    settings: Settings, store: Artifacts, snapshot, batch_size, run_id, max_batches=None
):
    variant = settings.model_copy(update={"batch_tokens": batch_size})
    model = GeminiModel(variant, store, run_id)
    batches = plan_batches(snapshot, variant)
    initial_count = len(batches)
    blocks = {block["id"]: Block.model_validate(block) for block in snapshot["blocks"]}
    results, index, splits = [], 0, 0
    started = monotonic()
    while index < len(batches) and (max_batches is None or index < max_batches):
        batch = batches[index]
        payload = {
            "batch": batch.model_dump(),
            "owned": [blocks[key].model_dump() for key in batch.owned],
            "context": [blocks[key].model_dump() for key in batch.context],
            "prior_draft": None,
            "feedback": [],
        }
        try:
            extraction = model.call("extract", payload, Extraction)
            defects = validate_extraction(extraction, batch, blocks)
            verification = model.call(
                "verify", {**payload, "extraction": extraction.model_dump()}, Verification
            )
        except (RequestTooLarge, TruncatedOutput):
            batches[index : index + 1] = split_batch(batch, blocks)
            splits += 1
            continue
        results.append(
            {
                "batch": batch.model_dump(),
                "extraction": extraction.model_dump(),
                "code_findings": [defect.model_dump() for defect in defects],
                "verification": verification.model_dump(),
            }
        )
        write_json(store.path(f"evaluation/{run_id}/progress.json"), results)
        index += 1
    result = {
        "batch_tokens": batch_size,
        "initial_batches": initial_count,
        "effective_batches": len(batches),
        "completed_batches": index,
        "splits": splits,
        "seconds": monotonic() - started,
        "results": results,
        "complete_queue": index == len(batches),
        "status": "exploratory",
    }
    write_json(store.path(f"evaluation/{run_id}/result.json"), result)
    return result


def assess_variant(settings, store, variant, reference, snapshot, run_id, include_held_out=False):
    lookup = {block["id"]: block for block in snapshot["blocks"]}
    scored = []
    for index, result in enumerate(variant["results"]):
        owned = [lookup[key] for key in result["batch"]["owned"]]
        annotations = [
            sample
            for sample in reference["samples"]
            if (include_held_out or sample["split"] == "development")
            and any(
                block["path"] == sample["path"]
                and block["line_start"] <= sample["line_start"] <= block["line_end"]
                for block in owned
            )
        ]
        if not annotations:
            continue
        score = GeminiModel(settings, store, run_id).call(
            "evaluate",
            {
                "reference": annotations,
                "owned": owned,
                "extraction": result["extraction"],
            },
            QualityAssessment,
        )
        expected = {sample["id"]: sample for sample in annotations}
        if {item.reference_id for item in score.scores} != set(expected) or len(
            score.scores
        ) != len(expected):
            raise ValueError("Evaluator failed to score each reference passage")
        claims = {claim["id"] for claim in result["extraction"]["claims"]}
        for item in score.scores:
            sample = expected[item.reference_id]
            if (
                len(item.retained_facts) != len(sample["expected_facts"])
                or len(item.retained_qualifications) != len(sample["qualifications"])
                or len(item.correct_entity_distinctions) != len(sample["entity_distinctions"])
                or not set(item.supporting_claim_ids) <= claims
            ):
                raise ValueError("Evaluator returned invalid score dimensions or references")
        scored.append({"batch_index": index, **score.model_dump()})
    judgments = [score for assessment in scored for score in assessment["scores"]]
    facts = [value for score in judgments for value in score["retained_facts"]]
    qualifiers = [value for score in judgments for value in score["retained_qualifications"]]
    distinctions = [value for score in judgments for value in score["correct_entity_distinctions"]]
    assessment = {
        "reference_version": digest(reference),
        "user_reviewed": reference["user_reviewed"],
        "acceptance_established": False,
        "judge": settings.gemini_model,
        "passages_scored": len(judgments),
        "facts_retained": sum(facts),
        "facts_total": len(facts),
        "qualifications_retained": sum(qualifiers),
        "qualifications_total": len(qualifiers),
        "entity_distinctions_correct": sum(distinctions),
        "entity_distinctions_total": len(distinctions),
        "unsupported_additions": sum(len(row["unsupported_claim_ids"]) for row in scored),
        "incorrect_merges": sum(len(row["incorrect_entity_merges"]) for row in scored),
        "assessments": scored,
        "limitation": (
            "Same-model exploratory judgment on an unapproved reference; not acceptance evidence."
        ),
    }
    write_json(store.path(f"evaluation/{run_id}/quality.json"), assessment)
    return assessment


def load_reference(path=Path("evaluation/reference.json")):
    return read_json(path)
