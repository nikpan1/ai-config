import argparse
import re
from copy import deepcopy
from pathlib import Path

from docgen.cli import run_config
from docgen.config import Settings
from docgen.contracts import Batch, Extraction
from docgen.ingestion import estimate_tokens
from docgen.model import GeminiModel
from docgen.signatures import runtime_signature
from docgen.storage import Artifacts, encode, read_json, run_lock, write_json
from docgen.validation import validate_duplicate_chains, validate_extraction
from docgen.workflow import Pipeline, persistent_graph


def split_profile_actors(value, blocks, changes):
    expanded, replacements = [], {}

    def profiles(record):
        return {
            profile
            for evidence in record["evidence"]
            for heading in blocks[evidence["block_id"]].headings
            for profile in re.findall(r"\b[AD]P-\d{3}\b", heading)
        }

    for entity in value["entities"]:
        scopes = profiles(entity)
        if entity["kind"] != "actor" or len(scopes) < 2:
            expanded.append(entity)
            continue
        if re.search(r"\b[AD]P-\d{3}\b", entity["definition"]):
            expanded.append(entity)
            continue
        members = {}
        for profile in sorted(scopes):
            scoped = deepcopy(entity)
            scoped["id"] += "_" + profile.lower().replace("-", "")
            scoped["scope"] = (
                ("ArchiveService" if profile.startswith("AP") else "DeliveryService")
                + " version 1, profile "
                + profile
            )
            scoped["evidence"] = [
                e for e in entity["evidence"] if profile in " ".join(blocks[e["block_id"]].headings)
            ]
            scoped["definition"] += (
                f" This description applies only within {profile}; "
                "it grants no authority in any other profile."
            )
            expanded.append(scoped)
            members[profile] = scoped["id"]
        replacements[entity["id"]] = members
        changes.append(
            {
                "record_id": entity["id"],
                "split_members": members,
                "reason": "The authored source denies cross-profile authority; "
                "preserve each witnessed actor scope independently",
            }
        )
    value["entities"] = expanded
    for claim in value["claims"]:
        scopes = profiles(claim)
        claim["entities"] = [
            member
            for key in claim["entities"]
            for member in (
                (
                    [v for k, v in replacements[key].items() if not scopes or k in scopes]
                    or list(replacements[key].values())
                )
                if key in replacements
                else [key]
            )
        ]
    for finding in value["findings"]:
        finding["record_ids"] = [
            member
            for key in finding["record_ids"]
            for member in (list(replacements[key].values()) if key in replacements else [key])
        ]


def curate_scope_metadata(value, batch, blocks, corrections=None):
    changes = []
    scope_blocks = {}
    for block in blocks.values():
        match = re.match(
            r"Scope: ((ArchiveService|DeliveryService) version (\d+), profile ([AD]P-\d{3}))\.",
            block.content,
        )
        if match:
            scope_blocks[match[4]] = (block, match)
    for entity in value["entities"] + value["claims"]:
        if entity.get("canonical_name") in {"ArchiveService", "DeliveryService"}:
            header = next(
                block for block in blocks.values() if "stable service identifiers" in block.content
            )
            before = {key: entity[key] for key in ("scope", "version")}
            entity["scope"] = entity["canonical_name"] + " version 1"
            entity["version"] = "1"
            evidence = {"block_id": header.id, "excerpt": header.content}
            if evidence not in entity["evidence"]:
                entity["evidence"].append(evidence)
            if header.id not in batch.owned + batch.context:
                batch.context.append(header.id)
            changes.append(
                {
                    "record_id": entity["id"],
                    "before": before,
                    "after": {key: entity[key] for key in ("scope", "version")},
                    "reason": "Explicit global service identity and version in the fixture header",
                }
            )
            continue
        profiles = {
            profile
            for evidence in entity["evidence"]
            for heading in blocks[evidence["block_id"]].headings
            for profile in re.findall(r"\b[AD]P-\d{3}\b", heading)
        }
        witnesses = [scope_blocks[key] for key in sorted(profiles) if key in scope_blocks]
        if not witnesses or len(witnesses) != len(profiles):
            continue
        if "aliases" in entity:
            invalid_aliases = [
                alias
                for alias in entity["aliases"]
                if set(re.findall(r"\b[AD]P-\d{3}\b", alias)) - profiles
            ]
            if invalid_aliases:
                entity["aliases"] = [
                    alias for alias in entity["aliases"] if alias not in invalid_aliases
                ]
                changes.append(
                    {
                        "record_id": entity["id"],
                        "removed_aliases": invalid_aliases,
                        "reason": "Alias names a different profile than all original witnesses",
                    }
                )
        before = {key: entity[key] for key in ("scope", "version")}
        explicit_scope = "; ".join(match[1] for _, match in witnesses)
        original_scope = entity["scope"]
        entity["scope"] = (
            explicit_scope
            if not original_scope or original_scope in explicit_scope
            else original_scope
            if explicit_scope in original_scope
            else original_scope + "; source applicability: " + explicit_scope
        )
        versions = {match[3] for _, match in witnesses}
        if entity["version"] is None and len(versions) == 1:
            entity["version"] = next(iter(versions))
        after = {key: entity[key] for key in ("scope", "version")}
        for block, match in witnesses:
            evidence = {"block_id": block.id, "excerpt": match[0]}
            if evidence not in entity["evidence"]:
                entity["evidence"].append(evidence)
                changes.append({"record_id": entity["id"], "added_evidence": evidence})
            if block.id not in batch.owned + batch.context:
                batch.context.append(block.id)
        if before != after:
            changes.append({"record_id": entity["id"], "before": before, "after": after})
        if "manual recovery" in entity.get("definition", "").lower():
            sentence = (
                "The legal hold must be checked again before manual recovery writes anything."
            )
            for block in blocks.values():
                if sentence not in block.content or not any(
                    profile in " ".join(block.headings) for profile in profiles
                ):
                    continue
                evidence = {"block_id": block.id, "excerpt": sentence}
                if evidence not in entity["evidence"]:
                    entity["evidence"].append(evidence)
                    changes.append({"record_id": entity["id"], "added_evidence": evidence})
                if block.id not in batch.owned + batch.context:
                    batch.context.append(block.id)
        if "definition" in entity:
            cited = " ".join(blocks[e["block_id"]].content for e in entity["evidence"])
            missing_numbers = set(re.findall(r"\b\d+\b", entity["definition"])) - set(
                re.findall(r"\b\d+\b", cited)
            )
            for block in blocks.values():
                if not any(profile in " ".join(block.headings) for profile in profiles):
                    continue
                for sentence in re.findall(r"[^.!?]+[.!?]", block.content):
                    if not missing_numbers.intersection(re.findall(r"\b\d+\b", sentence)):
                        continue
                    evidence = {"block_id": block.id, "excerpt": sentence.strip()}
                    if evidence not in entity["evidence"]:
                        entity["evidence"].append(evidence)
                        changes.append({"record_id": entity["id"], "added_evidence": evidence})
                    if block.id not in batch.owned + batch.context:
                        batch.context.append(block.id)
    for record in value["entities"] + value["claims"]:
        correction = (corrections or {}).get(record["id"])
        if correction:
            fields = correction["fields"]
            if set(fields) - {
                "scope",
                "version",
                "evidence",
                "aliases",
                "definition",
                "conditions",
                "exceptions",
            }:
                raise ValueError("Fixture correction changes unsupported record fields")
            changes.append(
                {
                    "record_id": record["id"],
                    "before": {key: record[key] for key in fields},
                    "after": fields,
                    "reason": correction["rationale"],
                    "origin": "autonomous_fixture_correction_requires_verification",
                }
            )
            record.update(fields)
            for evidence in record["evidence"]:
                if evidence["block_id"] not in batch.owned + batch.context:
                    batch.context.append(evidence["block_id"])
    for claim in value["claims"]:
        if claim["modality"] == "implemented":
            claim["modality"] = "requirement"
            changes.append(
                {
                    "record_id": claim["id"],
                    "modality": "requirement",
                    "reason": "The fixture header explicitly denies implementation evidence",
                }
            )
    split_profile_actors(value, blocks, changes)
    mapping = {r["id"]: r["id"].split(":", 1)[1] for r in value["claims"] + value["entities"]}
    for record in value["claims"] + value["entities"]:
        record["id"] = mapping[record["id"]]
        record["review_status"] = "draft"
    for claim in value["claims"]:
        claim["entities"] = [mapping[key] for key in claim["entities"]]
    for row in value["coverage"]:
        row["claim_ids"] = [mapping[key] for key in row["claim_ids"]]
    for finding in value["findings"]:
        finding["record_ids"] = [mapping[key] for key in finding["record_ids"]]
    batch.status = "pending"
    batch.context_tokens = sum(estimate_tokens(encode(blocks[key])) for key in batch.context)
    return value, changes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-thread", required=True)
    parser.add_argument("--target-thread", required=True)
    parser.add_argument("--expected-source-signature", required=True)
    parser.add_argument("--reverify-metadata", action="store_true")
    parser.add_argument("--corrections")
    args = parser.parse_args()
    settings = Settings()
    store = Artifacts(settings.workspace)
    pipeline = Pipeline(settings, store, GeminiModel(settings, store, args.target_thread))
    with run_lock(store, args.target_thread), persistent_graph(pipeline) as graph:
        source = graph.get_state(run_config(args.source_thread))
        state = source.values
        if state["signature"] != args.expected_source_signature:
            raise ValueError("Unexpected extraction implementation; reuse rejected")
        if Path(state["source"]).resolve() != Path(".docgen/phase2-medium-source").resolve():
            raise ValueError("Revision reuse is restricted to the authored evaluation fixture")
        config = run_config(args.target_thread)
        if graph.get_state(config).values:
            raise ValueError("Target thread already exists")
        batches = [Batch.model_validate(b) for b in pipeline.read(state, "batches_ref")]
        verified = pipeline.read(state, "verified_ref")
        if any(b.status != "verified" or b.id not in verified for b in batches):
            raise ValueError("All source batches must have completed verification")
        blocks = pipeline.blocks(state)
        coverage = []
        for batch in batches:
            value = store.get(verified[batch.id])
            extraction = Extraction.model_validate(value)
            if validate_extraction(extraction, batch, blocks):
                raise ValueError("Reused extraction fails evidence or coverage validation")
            coverage.extend(value["coverage"])
        if {r["block_id"] for r in coverage} != set(blocks) or not validate_duplicate_chains(
            coverage
        ):
            raise ValueError("Reused extraction coverage is incomplete")
        history = {
            key: issue
            for key, issue in pipeline.read(state, "issue_history_ref", {}).items()
            if issue["stage"] in {"snapshot_sources", "extract_batch", "verify_batch"}
        }
        decisions = [
            d for d in pipeline.read(state, "decisions_ref", []) if d["issue_id"] in history
        ]
        allowed = {
            "source",
            "selection",
            "snapshot_ref",
            "batches_ref",
            "verified_ref",
            "batch_index",
        }
        reused = {key: value for key, value in state.items() if key in allowed}
        curated_ref = None
        if args.reverify_metadata:
            curated, changes = {}, []
            corrections = read_json(Path(args.corrections)) if args.corrections else {}
            for batch in batches:
                value, edits = curate_scope_metadata(
                    store.get(verified[batch.id]), batch, blocks, corrections
                )
                if validate_extraction(Extraction.model_validate(value), batch, blocks):
                    raise ValueError("Curated extraction fails structural evidence validation")
                curated[batch.id] = store.put(value, "curated-extraction-draft")
                changes.extend(edits)
            curated_ref = store.put(curated, "curated-extractions")
            reused.update(
                verified_ref=store.put({}, "verified-index"),
                batch_index=0,
                batches_ref=store.put([b.model_dump() for b in batches], "batches"),
            )
            history, decisions = {}, []
            write_json(store.path(f"runs/{args.target_thread}/metadata-corrections.json"), changes)
        signature = runtime_signature(settings)
        lineage = {
            "workflow": "knowledge",
            "signature": signature,
            "reuse_policy": (
                "Corrected source-derived drafts; every batch reverified and reconciliation rebuilt"
                if args.reverify_metadata
                else "Verified immutable extraction only; all reconciliation rebuilt"
            ),
            "parent_thread": args.source_thread,
            "parent_checkpoint": source.config,
            "parent_signature": state["signature"],
            "reused_references": reused,
            "curated_extractions_ref": curated_ref,
            "reverification_required": args.reverify_metadata,
        }
        write_json(store.path(f"runs/{args.target_thread}/workflow.json"), lineage)
        store.event(
            args.target_thread, stage="verify_batch", event="explicit_revision_reuse", **lineage
        )
        graph.update_state(
            config,
            {
                **reused,
                "run_id": args.target_thread,
                "workflow": "knowledge",
                "signature": signature,
                "status": "running",
                "route": "extract_batch" if args.reverify_metadata else "reconcile_entities",
                "decisions_ref": store.put(decisions, "decisions"),
                "issue_history_ref": store.put(history, "issue-history"),
            },
            as_node="plan_batches" if args.reverify_metadata else "verify_batch",
        )
    print(f"Created {args.target_thread}; verified extraction reused with explicit lineage")


if __name__ == "__main__":
    main()
