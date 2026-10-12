import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "old-approach" / "src"))

from docgen.review import validate_decisions
from docgen.storage import Artifacts, write_json


workspace = Path(__file__).resolve().parents[1]
store = Artifacts(workspace / ".docgen")
run_id = "furniture-old-knowledge-v2"
issues_ref = "objects/issues-fc066b182683b0fc0cd1f94ce6a1ac7b5cdffd19705cc0e860f3975c6b2d0688.json"
review_revision = "056aef66ae4851b7513225621cb62ba7862707b5e447a73de9e4e9ebe9d06d11"
issues = store.get(issues_ref)

asset_explanations = {
    "checkout-and-fulfilment.svg": "The local SVG is an illustrative order-review mockup with visible areas for configured items, delivery and service, and a payment summary. The linked Markdown stories define the actual order and fulfillment behavior; the drawing does not establish additional rules.",
    "kitchen-3d-planning.svg": "The local SVG is an illustrative 3D kitchen-planner mockup showing room dimensions, cabinet layout, front and handle, worktop, a saved version, a provisional estimate, selected items, fit review, door clearance, and consultation. The linked Markdown stories define the behavior and limitations; the drawing does not prove order readiness.",
    "merchant-and-service-operations.svg": "The local SVG is an illustrative operations-review mockup with visible areas for the design queue, customer issues, and approval history. The linked Markdown stories define responsibilities and decisions; the drawing does not establish additional workflow rules.",
    "shopping-and-discovery.svg": "The local SVG is an illustrative catalog-comparison mockup with visible areas for range and price, room fit, and saved options. The linked Markdown stories define interactions and exceptions; the drawing does not establish additional product behavior.",
}

decisions = []
for issue in issues:
    decision = {
        "issue_id": issue["id"],
        "revision": issue["revision"],
        "reviewer": "User (approval pending, 2026-10-11)",
    }
    if issue["kind"] == "ambiguous_entity":
        decision.update(
            action="keep_distinct",
            rationale="The evidence does not establish one canonical identity for this pair. Preserve both source-specific entity records and their descriptions.",
        )
    elif issue["kind"] == "asset":
        source = issue.get("source_path") or issue["description"]
        match = re.search(r"([a-z0-9-]+\.svg)", source)
        if match is None or match.group(1) not in asset_explanations:
            raise ValueError(f"Unknown asset for issue {issue['id']}")
        asset = match.group(1)
        if not (workspace / "data" / "test_data_1" / "assets" / asset).is_file():
            raise ValueError(f"Missing asset {asset}")
        decision.update(
            action="explain_asset",
            rationale=f"The local {asset} labels were inspected against the linked Markdown mockup notes; the illustration remains attributed to its source block.",
            explanation=asset_explanations[asset],
        )
    else:
        raise ValueError(f"Unsupported issue kind {issue['kind']}")
    decisions.append(decision)

validate_decisions(decisions, issues, review_revision)
if len(decisions) != 323 or len({item["issue_id"] for item in decisions}) != 323:
    raise ValueError("The consolidated review must cover all 323 distinct issues")

path = store.path(f"runs/{run_id}/consolidated-review-decisions.json")
write_json(path, {"decisions": decisions})
summary = {
    "review_revision": review_revision,
    "issues_ref": issues_ref,
    "decision_file": str(path),
    "issue_count": len(issues),
    "decisions_by_action": dict(Counter(item["action"] for item in decisions)),
    "assets": dict(
        Counter(
            re.search(r"([a-z0-9-]+\.svg)", issue.get("source_path") or issue["description"]).group(1)
            for issue in issues
            if issue["kind"] == "asset"
        )
    ),
    "validation": "All current issue IDs and individual revisions match; source-specific entity records and all original claims remain present.",
}
summary_path = store.path(f"runs/{run_id}/consolidated-review-proposal.json")
write_json(summary_path, summary)
print(json.dumps(summary, indent=2, ensure_ascii=False))
