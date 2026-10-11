import re
from collections import defaultdict
from itertools import combinations, combinations_with_replacement

from docgen.ingestion import estimate_tokens
from docgen.storage import digest, encode


def normalize(text: str) -> str:
    return re.sub(r"\W+", " ", text.casefold()).strip()


def comparison_record(record):
    statement = record.get("statement", record.get("definition"))
    return {
        **record,
        "evidence": [
            {"block_id": item["block_id"], "excerpt_from_statement": True}
            if item["excerpt"] == statement
            else item
            for item in record["evidence"]
        ],
    }


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
    records: list[dict],
    kind: str,
    token_budget: int,
    entity_names: dict[str, str] | None = None,
    task_limit: int | None = None,
    store=None,
    policy: str = "strict",
) -> dict:
    if policy not in {"strict", "exact"}:
        raise ValueError("Unknown comparison policy")
    representatives = {}
    if policy == "exact":
        equivalent = defaultdict(list)
        for record in records:
            equivalent[digest({key: value for key, value in record.items() if key != "id"})].append(
                record["id"]
            )
        representatives = {sorted(members)[0]: sorted(members) for members in equivalent.values()}
        selected = set(representatives)
        records = [record for record in records if record["id"] in selected]
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
    omissions = []
    largest_groups = sorted(
        ({"key": key, "records": len(ids)} for key, ids in groups.items()),
        key=lambda group: group["records"],
        reverse=True,
    )[:20]
    group_keys = defaultdict(set)
    for key, ids in groups.items():
        for identifier in ids:
            group_keys[identifier].add(key)
    relationship_count = 0

    def counted_tasks():
        nonlocal relationship_count
        for task in iter_comparison_tasks(
            lookup, groups, token_budget, task_limit, omissions, policy, group_keys
        ):
            relationship_count += len(task.get("required_pairs", []))
            yield task

    tasks = counted_tasks()
    if store is None:
        task_fields = {"tasks": list(tasks)}
    else:
        ref = store.put_table(
            ({"id": str(index), "task": task} for index, task in enumerate(tasks)),
            "comparison-queue",
        )
        task_fields = {"tasks_ref": ref, "task_count": store.get(ref)["count"]}
    return {
        **task_fields,
        "unperformed": omissions,
        "group_count": len(groups),
        "largest_groups": largest_groups,
        "candidate_policy_version": "1",
        "comparison_policy_version": "2" if policy == "exact" else "1",
        "representative_members": representatives,
        "exact_pairs_discharged": sum(
            len(members) * (len(members) - 1) // 2 for members in representatives.values()
        ),
        "required_relationships": relationship_count if policy == "exact" else None,
        "candidate_policy": "Names, explicit aliases, shared name words, entity, rule and scope; "
        "unrelated groups are not compared. Original records remain intact.",
    }


def iter_comparison_tasks(
    lookup, groups, token_budget, task_limit, omissions, policy="strict", group_keys=None
):
    seen = set()
    produced = 0
    for key, ids in sorted(groups.items()):
        if len(ids) < 2:
            continue
        chunks, chunk, size = [], [], 0
        for identifier in sorted(ids):
            record = (
                comparison_record(lookup[identifier]) if policy == "exact" else lookup[identifier]
            )
            cost = estimate_tokens(encode(record))
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
            if policy == "strict":
                if signature in seen:
                    continue
                admit_comparison(produced, task_limit)
                seen.add(signature)
                produced += 1
                yield {"id": signature[:20], "group": key, "left": left, "right": right}
                continue
            candidates = ((a, b) for a in left for b in right) if right else combinations(left, 2)
            required = [[a, b] for a, b in candidates if key == min(group_keys[a] & group_keys[b])]
            if not required:
                continue
            pair_limit = max(1, token_budget // 4)
            pair_batch, pair_tokens = [], 0
            for pair in required:
                cost = estimate_tokens(encode(pair))
                if pair_batch and pair_tokens + cost > pair_limit:
                    admit_comparison(produced, task_limit)
                    produced += 1
                    yield relationship_task(
                        key,
                        left,
                        right,
                        pair_batch,
                        [sorted(group_keys[a] & group_keys[b]) for a, b in pair_batch],
                    )
                    pair_batch, pair_tokens = [], 0
                pair_batch.append(pair)
                pair_tokens += cost
            if pair_batch:
                admit_comparison(produced, task_limit)
                produced += 1
                yield relationship_task(
                    key,
                    left,
                    right,
                    pair_batch,
                    [sorted(group_keys[a] & group_keys[b]) for a, b in pair_batch],
                )


def admit_comparison(produced, task_limit):
    if task_limit is not None and produced >= task_limit:
        from docgen.model import ModelFailure

        raise ModelFailure(
            "Reconciliation workload allowance exceeded; no candidate tail was discarded"
        )


def relationship_task(group, left, right, pairs, contexts):
    used = {identifier for pair in pairs for identifier in pair}
    selected_left = [identifier for identifier in left if identifier in used]
    selected_right = [identifier for identifier in right if identifier in used]
    shared_contexts = sorted(set.intersection(*(set(item) for item in contexts)))
    return {
        "id": digest([group, selected_left, selected_right, pairs])[:20],
        "group": group,
        "left": selected_left,
        "right": selected_right,
        "required_pairs": pairs,
        "shared_contexts": shared_contexts,
        "pair_contexts": [sorted(set(item) - set(shared_contexts)) for item in contexts],
    }


def comparison_count(plan):
    return plan["task_count"] if "tasks_ref" in plan else len(plan["tasks"])


def comparison_at(plan, index, store):
    if "tasks_ref" in plan:
        return store.table_rows(plan["tasks_ref"], [str(index)])[0]["task"]
    return plan["tasks"][index]


def iter_comparisons(plan, store):
    if "tasks_ref" in plan:
        for row in store.iter_table(plan["tasks_ref"]):
            yield row["task"]
    else:
        yield from plan["tasks"]


def replace_comparison(plan, index, children, store):

    def replacement():
        for position, row in enumerate(iter_comparisons(plan, store)):
            yield from children if position == index else [row]

    ref = store.put_table(
        ({"id": str(position), "task": task} for position, task in enumerate(replacement())),
        "comparison-queue",
    )
    return {
        **{key: value for key, value in plan.items() if key != "tasks"},
        "tasks_ref": ref,
        "task_count": store.get(ref)["count"],
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
    children = []
    for first, second in partitions:
        if len(first) + len(second) < 2:
            continue
        if "required_pairs" in task:
            available = {
                tuple(sorted(pair))
                for pair in (
                    ((a, b) for a in first for b in second) if second else combinations(first, 2)
                )
            }
            selected = [
                (pair, sorted(set(task["shared_contexts"]) | set(context)))
                for pair, context in zip(task["required_pairs"], task["pair_contexts"], strict=True)
                if tuple(sorted(pair)) in available
            ]
            pairs = [pair for pair, _ in selected]
            if not pairs:
                continue
            child = relationship_task(
                task["group"], first, second, pairs, [context for _, context in selected]
            )
        else:
            child = {
                "id": digest([task["id"], first, second])[:20],
                "group": task["group"],
                "left": first,
                "right": second,
            }
        children.append({**child, "split_from": task["id"]})
    return children
