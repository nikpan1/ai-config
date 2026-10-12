import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "old-approach" / "src"))

from docgen.config import Settings
from docgen.contracts import Batch, Block, Extraction
from docgen.storage import Artifacts, write_json
from docgen.validation import validate_extraction


def main() -> None:
    store = Artifacts(Settings(_env_file=ROOT / ".env").workspace)
    run = store.root / "runs" / "furniture-old-knowledge-v2"
    draft_ref = "objects/extraction-630d77bb3574d8bf21cda22fcc4a33eb371cc3905b76cef4ce6dc197d08ab40d.json"
    snapshot_ref = "objects/snapshot-39822e455bb02d8d771433c1f027522cb8b3f166ff768786cf8f29aa1fbdd902.json"
    batches_ref = "objects/batches-3cc68130a011c0a29d2a8288268d2e9f975f7cfe1518ba14388a2d3387c05433.json"
    issue_ref = "objects/issues-b2b7a3fa578934bde6e5469d9d8da50d9c914504586a02806488195e2c90a0f9.json"
    draft = store.get(draft_ref)
    blocks = {item.id: item for item in map(Block.model_validate, store.get(snapshot_ref)["blocks"])}
    batches = store.get(batches_ref)
    batch = Batch.model_validate(batches[12])
    issues = store.get(issue_ref)
    if len(issues) != 2 or {item["kind"] for item in issues} != {"unsupported", "omission"}:
        raise ValueError("Review issues changed")
    claims = {claim["id"]: claim for claim in draft["claims"]}
    claims["c7"]["rule_keys"].remove("SHOPPINGANDDISCOVERY-17-3")
    for key in ("c22", "c23"):
        claims[key]["rule_keys"] = ["SHOPPINGANDDISCOVERY-17-1", "SHOPPINGANDDISCOVERY-17-2"]
        claims[key]["scope"] = "Care and suitability guidance for home shoppers and interior designers"
    if not any("b-d1e3732598e7b5a126b9" in item["owned"] for item in batches[13:]):
        raise ValueError("Returning customer row lacks a later owner")
    replacement = Extraction.model_validate(draft)
    findings = validate_extraction(replacement, batch, blocks)
    if findings:
        raise ValueError([item.model_dump() for item in findings])
    ref = store.put(replacement, "extraction-review-proposal")
    write_json(
        run / "batch-13-correction-proposal.json",
        {
            "revision": draft_ref,
            "issues": [item["id"] for item in issues],
            "affected_claims": ["c7", "c22", "c23"],
            "later_owned_row": "SHOPPINGANDDISCOVERY-17-3",
            "replacement_ref": ref,
            "validation_findings": [],
        },
    )
    write_json(
        run / "review-decision-batch-13.json",
        {
            "decisions": [
                {
                    "issue_id": issues[0]["id"],
                    "revision": draft_ref,
                    "action": "correct",
                    "reviewer": "User (chat approval, 2026-10-11)",
                    "rationale": "Scope claims to the owned source rows and leave row 17-3 to its owning batch",
                    "replacement": replacement.model_dump(),
                }
            ]
        },
    )
    print(json.dumps({"replacement_ref": ref, "affected_claims": ["c7", "c22", "c23"]}))


if __name__ == "__main__":
    main()
