import json
from dataclasses import replace
from pathlib import Path

from docgen_graph.config import Settings
from docgen_graph.contracts import AuditDraft, SectionDraft
from docgen_graph.model import GeminiModel
from docgen_graph.presentation import business_prose_findings, support_findings
from docgen_graph.storage import ArtifactStore


def main():
    settings = replace(Settings.load(), output_tokens=8192, timeout_seconds=180)
    store = ArtifactStore(Path(".docgen/business-validation"))
    model = GeminiModel(settings, store, "business-smoke-20261012")
    template = Path("data/template.md").read_text("utf-8")
    evidence = [
        {
            "id": "code",
            "label": "C1",
            "kind": "code",
            "path": "ProfileService.java",
            "file_hash": "smoke-fixture",
            "start_line": 1,
            "end_line": 6,
            "text": "@Transactional\npublic Result submit(Answers answers) {\n"
            "    if (!answers.processingConsent()) {\n"
            '        throw new IllegalArgumentException("Processing consent required");\n'
            "    }\n}",
        }
    ]
    facts = [
        {
            "id": "consent",
            "statement": "Submission requires processing consent.",
            "evidence_ids": ["code"],
        },
        {
            "id": "transaction",
            "statement": "The submit method has a Transactional annotation.",
            "evidence_ids": ["code"],
        },
    ]
    payload = {
        "template_text": template,
        "section": {"title": "3. Core Functionalities"},
        "mandatory_obligation_ids": [item["id"] for item in facts],
        "assertions": facts,
        "original_evidence": evidence,
        "unit_index": 0,
        "unit_count": 1,
        "approved_visuals": [],
        "template_requirements": [],
    }
    draft = model.call("write_section", payload, SectionDraft)
    findings = support_findings(draft["mappings"], {item["label"]: item for item in evidence})
    findings.extend(business_prose_findings(draft["markdown"], template))
    audit = model.call("verify_section", {**payload, **draft}, AuditDraft)
    result = {"draft": draft, "deterministic_findings": findings, "audit": audit}
    store.write("smoke.json", json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    if findings or not audit["accepted"]:
        raise ValueError("Business authoring smoke failed")


if __name__ == "__main__":
    main()
