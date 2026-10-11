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
    draft_ref = "objects/extraction-705fffb8794e4dbca3c9d90f10a045854ce14142f9ddcfb178b99061e9edbde0.json"
    snapshot_ref = "objects/snapshot-39822e455bb02d8d771433c1f027522cb8b3f166ff768786cf8f29aa1fbdd902.json"
    batches_ref = "objects/batches-51727874c7d6af03934b4aea08570db3ad344528719cbfec11771a43a2151954.json"
    issue_ref = "objects/issues-986a342df74b02e511d7f1f3d657d47a371327fde8a12a42480b002b87a23741.json"
    revision = draft_ref
    draft = store.get(draft_ref)
    blocks = {item.id: item for item in map(Block.model_validate, store.get(snapshot_ref)["blocks"])}
    batches = store.get(batches_ref)
    batch = Batch.model_validate(batches[9])
    affected = {"c24", "c25", "c26", "c29", "c31", "c32"}
    issues = store.get(issue_ref)
    if {item["record_ids"][0].rsplit(":", 1)[-1] for item in issues} != affected:
        raise ValueError("Review issues changed")
    for claim in draft["claims"]:
        if claim["id"] not in affected:
            continue
        source_ids = {item["block_id"] for item in claim["evidence"]}
        if len(source_ids) != 1:
            raise ValueError("Claim spans multiple source blocks")
        block_id = source_ids.pop()
        claim["evidence"] = [{"block_id": block_id, "excerpt": blocks[block_id].content.strip()}]
    replacement = Extraction.model_validate(draft)
    findings = validate_extraction(replacement, batch, blocks)
    if findings:
        raise ValueError([item.model_dump() for item in findings])
    ref = store.put(replacement, "extraction-review-proposal")
    write_json(
        run / "batch-10-correction-proposal.json",
        {
            "revision": revision,
            "issues": [item["id"] for item in issues],
            "affected_claims": sorted(affected),
            "replacement_ref": ref,
            "validation_findings": [],
        },
    )
    write_json(
        run / "review-decision-batch-10.json",
        {
            "decisions": [
                {
                    "issue_id": issues[0]["id"],
                    "revision": revision,
                    "action": "correct",
                    "reviewer": "User (chat approval, 2026-10-11)",
                    "rationale": "Use one exact contiguous source row for each of six affected claims",
                    "replacement": replacement.model_dump(),
                }
            ]
        },
    )
    print(json.dumps({"replacement_ref": ref, "affected_claims": sorted(affected)}))


if __name__ == "__main__":
    main()
