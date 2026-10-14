import json
import sqlite3
from contextlib import closing

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver
from test_source_first_completion import SourceModel, execute, run_inputs

from docgen_graph.completion import citation_findings
from docgen_graph.completion_repairs import (
    apply_repairs,
    assign_document_ids,
    audit_targets,
    citation_targets,
    preserve_planned_sections,
)
from docgen_graph.storage import ArtifactStore
from docgen_graph.workflow import Pipeline

EVIDENCE = [
    {"id": "registration", "text": "Registration requires verification. Guests are exempt."},
    {"id": "retention", "text": "Records are retained for thirty days."},
]


def paragraph(text, evidence_id="registration", quote=None):
    return {
        "text": text,
        "sources": [{"evidence_id": evidence_id, "quote": quote or text}],
        "uncertainty": "",
    }


def document():
    return assign_document_ids(
        {
            "title": "Accounts",
            "sections": [
                {
                    "title": "Registration",
                    "paragraphs": [
                        paragraph("Registration requires verification."),
                        paragraph("Guests are exempt."),
                    ],
                    "image_hashes": [],
                }
            ],
            "limitations": [],
        }
    )


def test_targeted_repair_preserves_unaffected_paragraph_byte_for_byte():
    draft = document()
    draft["sections"][0]["paragraphs"][1]["sources"][0]["quote"] = "Invented quote"
    targets = citation_targets(draft, EVIDENCE)
    repaired, records = apply_repairs(
        draft,
        targets,
        {
            "repairs": [
                {
                    "target_id": targets[0]["target_id"],
                    "paragraphs": [paragraph("Guests are exempt.")],
                },
                {
                    "target_id": draft["sections"][0]["paragraphs"][0]["id"],
                    "paragraphs": [paragraph("Unauthorized replacement")],
                },
            ]
        },
        EVIDENCE,
    )
    assert repaired["sections"][0]["paragraphs"][0] == draft["sections"][0]["paragraphs"][0]
    assert repaired["sections"][0]["paragraphs"][1]["id"] == targets[0]["target_id"]
    assert repaired["sections"][0]["paragraphs"][1]["text"] == "Guests are exempt."
    assert records[0]["outcome"] == "repaired"


def test_failed_repair_preserves_exact_source_excerpt_in_same_section():
    draft = document()
    target = {
        "target_id": draft["sections"][0]["paragraphs"][0]["id"],
        "section_id": draft["sections"][0]["id"],
        "paragraph": draft["sections"][0]["paragraphs"][0],
        "sources": [{"evidence_id": "registration", "quote": "Guests are exempt."}],
    }
    repaired, records = apply_repairs(draft, [target], {"repairs": []}, EVIDENCE)
    assert len(repaired["sections"][0]["paragraphs"]) == 2
    assert repaired["sections"][0]["paragraphs"][0]["text"] == "Guests are exempt."
    assert repaired["sections"][0]["paragraphs"][1] == draft["sections"][0]["paragraphs"][1]
    assert records[0]["outcome"] == "source_extract_fallback"
    assert not citation_findings(repaired, EVIDENCE)


def test_fabricated_paragraph_12_1_does_not_mutate_document():
    draft = document()
    targets, diagnostics = audit_targets(
        draft,
        {
            "findings": [
                {
                    "section_index": 11,
                    "paragraph_index": 0,
                    "severity": "unsupported",
                    "explanation": "Remove paragraph 12.1",
                },
                {
                    "section_index": -1,
                    "paragraph_index": -1,
                    "severity": "contradiction",
                    "explanation": "Reject everything",
                },
            ]
        },
        EVIDENCE,
    )
    assert targets == []
    assert len(diagnostics) == 2
    assert apply_repairs(draft, targets, {}, EVIDENCE)[0] == draft


def test_stable_ids_override_incorrect_positional_address():
    draft = document()
    section = draft["sections"][0]
    targets, diagnostics = audit_targets(
        draft,
        {
            "findings": [
                {
                    "section_id": section["id"],
                    "paragraph_id": section["paragraphs"][1]["id"],
                    "section_index": 12,
                    "paragraph_index": 999,
                    "severity": "unsupported",
                    "explanation": "Check the guest exemption",
                },
            ]
        },
        EVIDENCE,
    )
    assert targets[0]["target_id"] == section["paragraphs"][1]["id"]
    assert not diagnostics
    assert assign_document_ids(draft) == draft


def test_omission_adds_sourced_paragraph_without_replacing_any_original():
    draft = document()
    targets, diagnostics = audit_targets(
        draft,
        {
            "findings": [
                {
                    "section_id": draft["sections"][0]["id"],
                    "severity": "omission",
                    "explanation": "The retention period is missing",
                    "sources": [{"evidence_id": "retention", "quote": EVIDENCE[1]["text"]}],
                },
            ]
        },
        EVIDENCE,
    )
    repaired, records = apply_repairs(draft, targets, {}, EVIDENCE)
    assert repaired["sections"][0]["paragraphs"][:2] == draft["sections"][0]["paragraphs"]
    assert repaired["sections"][0]["paragraphs"][2]["text"] == EVIDENCE[1]["text"]
    assert records and not diagnostics


def test_unsourced_audit_omission_is_diagnostic_not_a_new_claim():
    draft = document()
    targets, diagnostics = audit_targets(
        draft,
        {
            "findings": [
                {
                    "section_id": draft["sections"][0]["id"],
                    "severity": "omission",
                    "explanation": "Invented legal requirement",
                    "sources": [{"evidence_id": "retention", "quote": "Ten years"}],
                },
            ]
        },
        EVIDENCE,
    )
    assert targets == []
    assert diagnostics[0]["reason"] == "Omission has no exact source"


def test_missing_planned_section_is_preserved_from_its_own_sources():
    draft = document()
    plan = {
        "sections": [
            {"id": "retention-section", "title": "Retention", "evidence_ids": ["retention"]}
        ]
    }
    draft, targets = preserve_planned_sections(draft, plan, EVIDENCE)
    repaired, _ = apply_repairs(draft, targets, {}, EVIDENCE)
    assert repaired["sections"][0]["id"] == "retention-section"
    assert repaired["sections"][0]["paragraphs"][0]["text"] == EVIDENCE[1]["text"]


def test_global_sourced_omission_uses_existing_section():
    draft = document()
    targets, diagnostics = audit_targets(
        draft,
        {
            "findings": [
                {
                    "section_index": -1,
                    "paragraph_index": -1,
                    "severity": "omission",
                    "explanation": "Missing guest exemption",
                    "sources": [{"evidence_id": "registration", "quote": "Guests are exempt."}],
                },
            ]
        },
        EVIDENCE,
    )
    assert targets[0]["section_id"] == draft["sections"][0]["id"]
    assert not diagnostics


def test_image_fallback_uses_description_without_generation_metadata():
    draft = document()
    image = {
        "id": "image",
        "role": "generated_image_description",
        "text": "AI-generated image interpretation.\n\nA card shows a draft status.",
        "fallback_text": "A card shows a draft status.",
    }
    draft["sections"][0]["paragraphs"][0]["sources"] = [
        {"evidence_id": "image", "quote": "Unsupported image claim"}
    ]
    targets = citation_targets(draft, EVIDENCE + [image])
    repaired, records = apply_repairs(draft, targets, {}, EVIDENCE + [image])
    assert repaired["sections"][0]["paragraphs"][0]["text"] == image["fallback_text"]
    assert records[0]["outcome"] == "source_extract_fallback"


class DefectiveModel(SourceModel):
    def call(self, stage, payload, schema=None):
        if stage == "source_document_repair":
            self.calls.append(stage)
            raise RuntimeError("Provider unavailable during repair")
        result = super().call(stage, payload, schema)
        if stage == "source_document":
            result["sections"][0]["paragraphs"].append(
                paragraph(
                    "Guests must pay a fee.",
                    payload["sources"]["evidence"][0]["id"],
                    "Invented fee",
                )
            )
        return result


def test_provider_failure_during_repair_retains_topic_and_exact_sources(tmp_path):
    model = DefectiveModel(tmp_path / ".env")
    store, result = execute(tmp_path, model, run_inputs(tmp_path))
    assert model.calls.count("source_document") == 1
    assert model.calls.count("source_document_repair") == 1
    candidate = store.get(result["candidate_ref"])
    assert len(candidate["sections"][0]["paragraphs"]) == 2
    assert "Guests must pay a fee" not in json.dumps(candidate)
    report = store.get(result["source_coverage_ref"])
    assert report["withheld_paragraphs"] == []
    assert report["targeted_repair_counts"] == {"citations": 1}
    assert report["semantic_audit_matches_exported_content"]


def test_restart_after_targeted_repair_never_repeats_completed_generation(tmp_path):
    model = DefectiveModel(tmp_path / ".env")
    inputs = run_inputs(tmp_path)
    store = ArtifactStore(tmp_path / "runtime")
    config = {"configurable": {"thread_id": "preservation"}, "recursion_limit": 150}
    database = store.root / "checkpoints.sqlite"
    with closing(sqlite3.connect(database, check_same_thread=False)) as db:
        graph = Pipeline(store, model, "source-run").build(SqliteSaver(db))
        graph.invoke(inputs, config, interrupt_after=["repair_source_document"])
        checkpoint = graph.get_state(config)
        assert checkpoint.values["completion_repair_counts"] == {"citations": 1}
    initial_calls = list(model.calls)
    with closing(sqlite3.connect(database, check_same_thread=False)) as db:
        graph = Pipeline(store, model, "source-run").build(SqliteSaver(db))
        result = graph.invoke(None, config)
    assert model.calls == initial_calls + ["audit_source_document"]
    assert result["deadline"] == inputs["deadline"]
    assert result["status"] == "complete_with_limitations"


def test_semantic_repair_is_targeted_and_export_matches_the_second_audit(tmp_path):
    class SemanticRepairModel(SourceModel):
        def call(self, stage, payload, schema=None):
            if stage == "source_document_repair":
                self.calls.append(stage)
                assert len(payload["targets"]) == 1
                self.repair_target = payload["targets"][0]["target_id"]
                source = payload["sources"]["evidence"][0]
                return {
                    "repairs": [
                        {
                            "target_id": self.repair_target,
                            "paragraphs": [paragraph("Temporary guests are exempt.", source["id"])],
                        }
                    ]
                }
            result = super().call(stage, payload, schema)
            if stage == "source_document":
                source = payload["sources"]["evidence"][0]
                result["sections"][0]["paragraphs"].append(
                    paragraph(
                        "Temporary guests require verification.", source["id"], source["text"]
                    )
                )
            if stage == "audit_source_document":
                self.audited_document = payload["document"]
                if self.calls.count(stage) == 1:
                    section = payload["document"]["sections"][0]
                    self.untouched = section["paragraphs"][0]
                    result["accepted"] = False
                    result["findings"] = [
                        {
                            "section_id": section["id"],
                            "paragraph_id": section["paragraphs"][1]["id"],
                            "severity": "contradiction",
                            "explanation": "Restore the guest exception",
                        }
                    ]
            return result

    model = SemanticRepairModel(tmp_path / ".env")
    store, result = execute(tmp_path, model, run_inputs(tmp_path))
    candidate = store.get(result["candidate_ref"])
    assert candidate["sections"][0]["paragraphs"][0] == model.untouched
    assert candidate["sections"] == model.audited_document["sections"]
    assert candidate["sections"][0]["paragraphs"][1]["id"] == model.repair_target
    assert model.calls.count("source_document") == 1
    assert model.calls.count("source_document_repair") == 1
    assert model.calls.count("audit_source_document") == 2
    assert store.get(result["source_coverage_ref"])["semantic_audit_matches_exported_content"]


def test_phantom_audit_findings_stay_in_report_and_never_reach_customer_text(tmp_path):
    model = SourceModel(
        tmp_path / ".env",
        audit_findings=[
            {
                "section_index": 11,
                "paragraph_index": 0,
                "severity": "unsupported",
                "explanation": "Withheld paragraph 12.1 because the model invented it",
            }
        ],
    )
    store, result = execute(tmp_path, model, run_inputs(tmp_path))
    markdown = (store.root / "runs/source-run/output/documentation.md").read_text("utf-8")
    assert "12.1" not in markdown and "Withheld" not in markdown
    assert "Temporary guests are exempt" in markdown
    assert "source_document_repair" not in model.calls
    assert store.get(result["source_coverage_ref"])["audit_target_diagnostics"]


@pytest.mark.parametrize(
    "last_outcome,expected_status",
    [
        ("source_extract_fallback", "degraded_source_bundle"),
        ("repaired", "complete_with_limitations"),
    ],
)
def test_final_status_tracks_each_surviving_expanded_paragraph(
    tmp_path, last_outcome, expected_status
):
    store = ArtifactStore(tmp_path / "runtime")
    pipeline = Pipeline(store, SourceModel(tmp_path / ".env"), "source-run")
    span = {
        "id": "a",
        "text": "Registration requires verification. Guests are exempt.",
        "path": "requirements.md",
        "start_line": 1,
        "end_line": 1,
        "file_hash": "f" * 64,
    }
    draft = {
        "title": "Registration",
        "sections": [
            {
                "id": "section-a",
                "title": "Behavior",
                "paragraphs": [
                    {"id": "target", **paragraph("Registration requires verification.", "a")},
                    {"id": "target-2", **paragraph("Guests are exempt.", "a")},
                ],
                "image_hashes": [],
            }
        ],
        "limitations": [],
    }
    records = [
        {
            "target_id": "target",
            "section_id": "section-a",
            "outcome": "source_extract_fallback",
            "replacement_ids": ["target", "target-2"],
        },
        {
            "target_id": "target",
            "section_id": "section-a",
            "outcome": last_outcome,
            "replacement_ids": ["target"],
        },
    ]
    result = pipeline.finalize_source_document(
        {
            "inventory_ref": store.put({"spans": [span]}),
            "completion_draft_ref": store.put(draft),
            "completion_repair_records_ref": store.put(records),
        }
    )
    assert result["status"] == expected_status
    candidate = store.get(result["candidate_ref"])
    assert candidate["sections"] == draft["sections"]
    assert len(candidate["sections"][0]["paragraphs"]) == 2
