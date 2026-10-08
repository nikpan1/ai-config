import re
from collections import defaultdict
from itertools import combinations_with_replacement

from docgen.ingestion import estimate_tokens
from docgen.storage import digest, encode


def normalize(text: str) -> str:
    return re.sub(r"\W+", " ", text.casefold()).strip()


def entity_register(entities: list[dict], decisions: list[dict]):
    lookup = {entity["id"]: entity for entity in entities}
    parent = {identifier: identifier for identifier in lookup}

    def root(identifier):
        while parent[identifier] != identifier:
            identifier = parent[identifier]
        return identifier

    for decision in decisions:
        if decision["action"] != "merge_entities":
            continue
        ids = decision["entity_ids"]
        if not set(ids) <= set(lookup):
            raise ValueError("Merge decision references entities outside the current revision")
        signatures = {
            (lookup[key]["kind"], lookup[key]["scope"], lookup[key]["version"]) for key in ids
        }
        if len(signatures) > 1:
            raise ValueError("Entity merge cannot erase type, scope or version distinctions")
        target = root(ids[0])
        for key in ids[1:]:
            parent[root(key)] = target
    groups = defaultdict(list)
    for key in lookup:
        groups[root(key)].append(key)
    register = []
    mapping = {}
    for canonical, members in groups.items():
        row = dict(lookup[canonical])
        row["members"] = members
        row["aliases"] = sorted(
            {
                name
                for key in members
                for name in [lookup[key]["canonical_name"], *lookup[key]["aliases"]]
                if name != row["canonical_name"]
            }
        )
        row["definitions"] = [
            {"entity_id": key, "definition": lookup[key]["definition"]} for key in members
        ]
        evidence = {digest(value): value for key in members for value in lookup[key]["evidence"]}
        row["evidence"] = list(evidence.values())
        row["review_status"] = "reviewed" if len(members) > 1 else row["review_status"]
        register.append(row)
        mapping.update({key: canonical for key in members})
    return register, mapping


def comparison_tasks(
    records: list[dict], kind: str, token_budget: int, entity_names: dict[str, str] | None = None
) -> dict:
    groups = defaultdict(set)
    lookup = {record["id"]: record for record in records}
    entity_names = entity_names or {}
    for record in records:
        if kind == "entities":
            keys = [normalize(name) for name in [record["canonical_name"], *record["aliases"]]]
            keys.extend(
                f"word:{word}" for name in list(keys) for word in name.split() if len(word) > 3
            )
        else:
            keys = ["entity:" + normalize(entity_names.get(key, key)) for key in record["entities"]]
            keys.extend("rule:" + normalize(key) for key in record["rule_keys"])
            keys.extend("scope:" + normalize(record["scope"]) for _ in [0] if record["scope"])
            keys.extend(
                "explicit:" + key.upper()
                for key in re.findall(r"\b(?:CG|RULE|F|INT)-\d+\b", record["statement"], re.I)
            )
        if not keys:
            keys = ["unclassified"]
        for key in keys:
            if key:
                groups[key].add(record["id"])
    tasks, seen, omissions = [], set(), []
    for key, ids in sorted(groups.items()):
        if len(ids) < 2:
            continue
        chunks, chunk, size = [], [], 0
        for identifier in sorted(ids):
            cost = estimate_tokens(encode(lookup[identifier]))
            if cost > token_budget // 2:
                omissions.append(
                    {
                        "record_id": identifier,
                        "group": key,
                        "reason": "Record exceeds comparison partition budget",
                    }
                )
                continue
            if chunk and size + cost > token_budget // 2:
                chunks.append(chunk)
                chunk, size = [], 0
            chunk.append(identifier)
            size += cost
        if chunk:
            chunks.append(chunk)
        for left_index, right_index in combinations_with_replacement(range(len(chunks)), 2):
            left = chunks[left_index]
            right = chunks[right_index] if left_index != right_index else []
            if len(left) + len(right) < 2:
                continue
            signature = digest([left, right])
            if signature in seen:
                continue
            seen.add(signature)
            tasks.append({"id": signature[:20], "group": key, "left": left, "right": right})
    return {
        "tasks": tasks,
        "unperformed": omissions,
        "group_count": len(groups),
        "candidate_policy": "Names, explicit aliases, shared name words, entity, rule and scope; "
        "unrelated groups are not compared. Original records remain intact.",
    }


def split_comparison(task: dict) -> list[dict]:
    left, right = task["left"], task["right"]
    if len(left) + len(right) <= 2:
        return []
    partitions = []
    if right:
        if len(left) >= len(right):
            middle = len(left) // 2
            partitions = [(left[:middle], right), (left[middle:], right)]
        else:
            middle = len(right) // 2
            partitions = [(left, right[:middle]), (left, right[middle:])]
    else:
        middle = len(left) // 2
        first, second = left[:middle], left[middle:]
        partitions = [(first, []), (second, []), (first, second)]
    return [
        {
            "id": digest([task["id"], first, second])[:20],
            "group": task["group"],
            "left": first,
            "right": second,
            "split_from": task["id"],
        }
        for first, second in partitions
        if len(first) + len(second) >= 2
    ]
