"""Build local visual QA fixtures without a model request."""

import os
from pathlib import Path

from docgen.authoring import mermaid
from docgen.config import Settings
from docgen.ingestion import inventory, parse_inventory
from docgen.models import Chapter, DiagramSpec, Draft, Knowledge
from docgen.preview import graph_preview
from docgen.validation import render_diagrams

root = Path("runs/ui-verification").resolve()
root.mkdir(parents=True, exist_ok=True)
parsed = parse_inventory(root, inventory(Path("tests/fixtures/retry.md"), root))
span = next(s for s in parsed["spans"] if s["kind"] == "table")
evidence_id = span["id"]
graph = Knowledge.model_validate(
    {
        "entities": [
            {
                "id": "delivery",
                "type": "capability",
                "name": "Notification delivery",
                "evidence_ids": [evidence_id],
            },
            {
                "id": "retry",
                "type": "process",
                "name": "Transient retry",
                "evidence_ids": [evidence_id],
            },
            {
                "id": "sender",
                "type": "customer_input",
                "name": "Sender address",
                "evidence_ids": [evidence_id],
            },
        ],
        "claims": [
            {
                "id": "retry-claim",
                "assertion": "Retry transient failures up to three times.",
                "conditions": ["Only while delivery remains enabled"],
                "exceptions": ["Never retry permanent failures"],
                "entity_ids": ["delivery", "retry"],
                "evidence_ids": [evidence_id],
                "status": "accepted",
            }
        ],
        "relationships": [
            {
                "id": "requires",
                "subject": "delivery",
                "object": "retry",
                "type": "requires",
                "claim_ids": ["retry-claim"],
            }
        ],
        "coverage": [
            {"evidence_id": evidence_id, "disposition": "covered", "claim_ids": ["retry-claim"]}
        ],
        "evidence": [{"id": evidence_id, "kind": "text", "span_id": evidence_id}],
    }
)
print(graph_preview(root / "graph-preview", graph, parsed, root))
diagram = DiagramSpec(
    id="delivery",
    nodes={"delivery": "Notification delivery", "retry": "Transient retry"},
    edges=[
        {
            "subject": "delivery",
            "object": "retry",
            "label": "requires",
            "relationship_id": "requires",
            "claim_ids": ["retry-claim"],
        }
    ],
)
(root / "diagram.mmd").write_text(mermaid(diagram.model_dump()), "utf-8")
if os.environ.get("DOCGEN_BROWSER"):
    findings = render_diagrams(
        Draft(
            chapters=[
                Chapter(id="delivery", title="Notification delivery", blocks=[], diagrams=[diagram])
            ]
        ),
        root / "rendered",
        Settings(browser_executable=os.environ["DOCGEN_BROWSER"]),
    )
    if findings:
        raise ValueError(findings)
    print("Pinned Mermaid renderer passed")
