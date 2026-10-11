import argparse
import re
import sys
from pathlib import Path


def entity_decision(issue, entities, blocks):
    records = [entities[key] for key in issue["record_ids"]]
    if len(records) < 2:
        return None
    names = {record["canonical_name"] for record in records}
    signatures = {(r["kind"], r["scope"], r["version"]) for r in records}
    if (
        len(names) == 1
        and names <= {"ArchiveService", "DeliveryService"}
        and len(signatures) == 1
        and any("stable service identifiers" in block.content for block in blocks.values())
    ):
        return {
            "action": "merge_entities",
            "entity_ids": issue["record_ids"],
            "rationale": "The fixture header explicitly declares this service identifier "
            "to have one identity across all profiles. Type, scope and version agree.",
        }
    profiles = [
        {
            key
            for evidence in record["evidence"]
            for key in re.findall(r"\b[AD]P-\d{3}\b", blocks[evidence["block_id"]].content)
        }
        for record in records
    ]
    for index, record in enumerate(records):
        if record["kind"] != "actor" or len(profiles[index]) != 1:
            continue
        same_role = [
            other
            for other_index, other in enumerate(records)
            if profiles[other_index] == profiles[index]
            and other["canonical_name"].casefold() == record["canonical_name"].casefold()
            and all(other[key] == record[key] for key in ("kind", "scope", "version"))
        ]
        witnesses = set.intersection(
            *({e["block_id"] for e in item["evidence"]} for item in same_role)
        )
        if len(same_role) > 1 and any(
            record["canonical_name"].casefold() in blocks[key].content.casefold()
            for key in witnesses
        ):
            return {
                "action": "merge_entities",
                "entity_ids": [item["id"] for item in same_role],
                "rationale": "These descriptions cite the same explicit role declaration "
                "within one identical source profile, type and version. Merge only those "
                "descriptions; records in other profiles retain separate identities.",
            }
    if (
        all(record["kind"] == "actor" for record in records)
        and len({name.casefold() for name in names}) > 1
    ):
        return {
            "action": "keep_distinct",
            "rationale": "Retain separately labeled source role descriptions. Overlapping "
            "actions do not establish identity or authorize combining their permissions; "
            "each description keeps its own exact scope and evidence.",
        }
    if all(profiles) and all(
        not left.intersection(right)
        for index, left in enumerate(profiles)
        for right in profiles[index + 1 :]
    ):
        return {
            "action": "keep_distinct",
            "rationale": "The fixture declares profile scopes mutually distinct. "
            "These records have disjoint source profile witnesses: "
            + str([sorted(group) for group in profiles])
            + ". Matching labels do not merge those contexts.",
        }
    if len(signatures) > 1:
        return {
            "action": "keep_distinct",
            "rationale": "Retain separate extracted descriptions because their type, scope "
            "or version metadata differ. This is a conservative record-identity decision, "
            "not an assertion that matching names prove separate real-world objects. "
            "Preserve the original definitions, unknown metadata and profile witnesses.",
        }
    if all(len(group) == 1 and group == profiles[0] for group in profiles):
        profile = next(iter(profiles[0]))
        if all(
            re.fullmatch(r"(?:(?:Archive|Delivery) profile )?" + profile, name, re.I)
            for name in names
        ):
            return {
                "action": "merge_entities",
                "entity_ids": issue["record_ids"],
                "rationale": "Both descriptions identify the same explicit fixture profile ID "
                + profile
                + " within the same source-defined service version and scope. "
                "Retain every original definition and evidence reference.",
            }
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--implementation", required=True)
    parser.add_argument("--thread-id", required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(args.implementation).resolve()))

    from langgraph.types import Command

    from docgen.cli import run_config, runtime_signature, status_payload
    from docgen.config import Settings
    from docgen.model import GeminiModel
    from docgen.storage import Artifacts, configure_logging, digest, run_lock, write_json
    from docgen.workflow import Pipeline, persistent_graph

    settings = Settings()
    store = Artifacts(settings.workspace)
    config = run_config(args.thread_id)
    metadata = store.get(f"runs/{args.thread_id}/workflow.json")
    curated_ref = metadata.get("curated_extractions_ref")
    model = GeminiModel(settings, store, args.thread_id)

    class CuratedFixtureInputs:
        def call(self, stage, payload, schema):
            if stage == "extract" and curated_ref and not payload.get("feedback"):
                ref = store.get(curated_ref).get(payload["batch"]["id"])
                if ref:
                    store.event(
                        args.thread_id,
                        stage=stage,
                        event="curated_input_reuse_requires_verification",
                        source_ref=ref,
                    )
                    return schema.model_validate(store.get(ref))
            result = model.call(stage, payload, schema)
            if stage in {"entities", "claims"}:
                expected = {r["id"] for r in payload["left"] + payload["right"]}
                for attempt in range(2):
                    invalid = (
                        set(result.checked_ids) != expected
                        or len(result.checked_ids) != len(expected)
                        or any(
                            {r.left, r.right} - expected or r.left == r.right
                            for r in result.relations
                        )
                    )
                    if not invalid:
                        break
                    result = model.call(
                        stage,
                        {
                            **payload,
                            "repair_attempt": attempt + 1,
                            "feedback": {
                                "error": "Comparison contains invalid record references",
                                "expected_record_ids": sorted(expected),
                                "previous_response": result.model_dump(),
                            },
                        },
                        schema,
                    )
            return result

    pipeline = Pipeline(settings, store, CuratedFixtureInputs())
    configure_logging()
    with run_lock(store, args.thread_id), persistent_graph(pipeline) as graph:
        store.event(
            args.thread_id,
            stage="fixture_orchestration",
            event="autonomous_fixture_policy",
            driver_hash=digest(Path(__file__).read_bytes()),
            implementation=str(Path(args.implementation).resolve()),
        )
        for _ in range(100):
            current = graph.get_state(config)
            state = current.values
            if Path(state["source"]).resolve() != Path(".docgen/phase2-medium-source").resolve():
                raise ValueError(
                    "Autonomous fixture policy applies only to its authored source set"
                )
            if state["signature"] != runtime_signature(settings):
                raise ValueError("Use the matching immutable implementation")
            if state.get("status") == "complete":
                write_json(
                    store.path(f"runs/{args.thread_id}/live-result.json"), status_payload(current)
                )
                return
            payload = None
            if current.interrupts:
                issues = list(
                    {issue["id"]: issue for issue in current.interrupts[0].value["issues"]}.values()
                )
                decisions = []
                blocks = pipeline.blocks(state)
                entities = {
                    entity["id"]: entity
                    for ref in store.get(state["verified_ref"]).values()
                    for entity in store.get(ref)["entities"]
                }
                for issue in issues:
                    resolved = (
                        entity_decision(issue, entities, blocks)
                        if issue["kind"] == "ambiguous_entity"
                        else None
                    )
                    if resolved:
                        decisions.append(
                            {
                                "issue_id": issue["id"],
                                "revision": issue["revision"],
                                "reviewer": "Autonomous synthetic-fixture author; "
                                "not human reviewed",
                                **resolved,
                            }
                        )
                        continue
                    description = issue["description"].lower()
                    excerpts = " ".join(blocks[key].content.lower() for key in issue["block_ids"])
                    identity_unknown = (
                        issue["kind"] == "missing_context"
                        and set(issue["record_ids"]) <= set(entities)
                        and "identity" in description
                        and any(
                            phrase in description
                            for phrase in ("cannot be determined", "not established", "uncertain")
                        )
                    )
                    if (
                        issue["kind"] not in {"source_issue", "missing_context"}
                        or not identity_unknown
                        and not any(
                            term in description
                            for term in (
                                "unknown",
                                "unspecified",
                                "not specify",
                                "not specified",
                                "not explicitly specify",
                                "explicitly omitted",
                                "not defined",
                                "does not define",
                            )
                        )
                        or not identity_unknown
                        and not any(
                            term in excerpts
                            for term in ("unknown", "not specify", "outside this specification")
                        )
                    ):
                        write_json(
                            store.path(f"runs/{args.thread_id}/live-result.json"),
                            status_payload(current),
                        )
                        print(
                            "Fixture review requires a correction; checkpoint preserved",
                            flush=True,
                        )
                        return
                    decisions.append(
                        {
                            "issue_id": issue["id"],
                            "revision": issue["revision"],
                            "action": "acknowledge_unknown",
                            "reviewer": "Autonomous synthetic-fixture author; not human reviewed",
                            "rationale": "The authored fixture leaves this attribute unknown. "
                            "Preserve uncertainty; do not invent behavior or authority.",
                        }
                    )
                payload = Command(resume={"decisions": decisions})
            graph.invoke(payload, config, durability="sync")
        raise ValueError("Fixture orchestration limit reached; checkpoint preserved")


if __name__ == "__main__":
    main()
