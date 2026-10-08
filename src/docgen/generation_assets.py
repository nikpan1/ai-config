import posixpath
from urllib.parse import unquote, urlsplit

from docgen.storage import file_digest


def prepare_inventory(pipeline, state):
    inputs = pipeline.planning_inputs(state)
    snapshot = pipeline.store.get_object(inputs.snapshot_ref)
    inventory = {row["path"]: row for row in snapshot["inventory"]}
    requests = {r["path"]: r for r in pipeline.inputs(state)["generation_brief"]["assets"]}
    requests.update({r["path"]: r for r in pipeline.read(state, "asset_decisions_ref", [])})
    locations = {}
    for block in snapshot["blocks"]:
        for link in block["links"]:
            parsed = urlsplit(link["target"])
            target = (
                posixpath.normpath(
                    posixpath.join(posixpath.dirname(block["path"]), unquote(parsed.path))
                )
                if not parsed.scheme
                else link["target"]
            )
            if (
                link["kind"] == "image"
                or target not in inventory
                or inventory[target]["status"] != "parsed"
            ):
                locations.setdefault(target, []).append(block["id"])
    relevant = (
        set(requests)
        | set(locations)
        | {key for key, row in inventory.items() if row["status"] != "parsed"}
    )
    assets, findings = [], []
    for key, entry in inventory.items():
        if entry["status"] == "parsed":
            target = pipeline.store.path(entry["ref"])
            if file_digest(target) != entry["snapshot"]:
                raise ValueError("Source snapshot changed")
            assets.append(
                {
                    "path": key,
                    "kind": "source",
                    "hash": entry["snapshot"],
                    "target": str(target),
                    "disposition": "link",
                    "source_locations": [],
                    "purpose": "Exact original source",
                }
            )
    for key in sorted(relevant):
        request = requests.get(key)
        entry = inventory.get(key)
        if not request:
            findings.append(
                f"Asset requires an explicit link, explanation or exclusion decision: {key}"
            )
            continue
        value = {
            **request,
            "kind": "attachment",
            "source_locations": locations.get(key, []),
            "target": None,
            "hash": entry.get("snapshot") if entry else None,
        }
        if request["disposition"] != "exclude":
            if not entry or not entry.get("ref"):
                findings.append(f"Requested attachment has no immutable source snapshot: {key}")
                continue
            target = pipeline.store.path(entry["ref"])
            if not target.is_file() or file_digest(target) != entry["snapshot"]:
                findings.append(f"Requested attachment is missing or changed: {key}")
                continue
            if request["disposition"] == "image" and not (
                request.get("explanation") and request.get("reviewer")
            ):
                findings.append(f"Image needs an attributed human explanation: {key}")
                continue
            value["target"] = str(target)
        assets.append(value)
    return assets, findings
