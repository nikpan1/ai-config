from collections import defaultdict

from docgen.ingestion import estimate_tokens
from docgen.planning_contracts import (
    ContentAllocation,
    LogicalSection,
    NavigationLink,
    NavigationPlan,
    PagePlan,
    WritingJob,
)
from docgen.planning_helpers import (
    bounded_groups,
    evidence_context,
    safe_slug,
    stable_id,
    validate_dag,
    validate_paths,
)
from docgen.storage import encode


def root_sections(pipeline, state):
    contract = pipeline.component(state, "template-contract")
    spans = {s["id"]: s for s in contract["spans"]}
    roots = [r for r in contract["rules"] if spans[r["span_id"]]["level"] <= 2 and not r["example"]]
    result = []
    for instance in pipeline.rows(state, "template-instances"):
        for index, rule in enumerate(roots):
            span = spans[rule["span_id"]]
            identifier = stable_id("section", instance["id"], span["id"])
            title = "Title and metadata" if span["level"] <= 1 else span["heading"]
            result.append(
                LogicalSection(
                    id=identifier,
                    topic_id=stable_id("topic", identifier),
                    owner_id=instance["unit_id"],
                    template_instance_id=instance["id"],
                    template_span_id=span["id"],
                    parent_id=None,
                    title=title,
                    reader_question=f"What should readers know about {title.lower()}?",
                    purpose="Fulfill template requirements with evidence and explicit unknowns",
                    order=index,
                    scope=instance["metadata"]["scope"],
                    form="; ".join(rule["forms"]) or "explanation",
                    role=rule["role"],
                ).model_dump()
            )
    owners = {a["owner_id"] for a in pipeline.rows(state, "unit-assignments")}
    extra = [("sources", "Source inventory and coverage", "sources")]
    if "shared" in owners:
        extra.append(("shared", "Shared definitions, rules and dependencies", "reference"))
    if pipeline.store.get(pipeline.components(state)["documentation-units"])["count"] > 1:
        extra.append(("collection", "Functional unit catalog", "catalog"))
    for owner, title, role in extra:
        identifier = stable_id("section", owner)
        result.append(
            LogicalSection(
                id=identifier,
                topic_id=stable_id("topic", identifier),
                owner_id=owner,
                template_instance_id=None,
                template_span_id=owner,
                parent_id=None,
                title=title,
                reader_question=f"Where can readers find {title.lower()}?",
                purpose="Provide a complete navigable index with explicit provenance",
                order=0,
                scope="Selected knowledge only",
                form="reference_list",
                role=role,
            ).model_dump()
        )
    return result


def allocate(pipeline, state, assignments):
    sections = {s["id"]: s for s in pipeline.rows(state, "logical-sections")}
    roots = defaultdict(list)
    for section in sections.values():
        if section["parent_id"] is None:
            roots[section["owner_id"]].append(section)
    ids = [a["obligation_id"] for a in assignments if a["disposition"] == "included"]
    topic_rows = {
        r["id"]: r
        for r in pipeline.store.table_rows(pipeline.components(state)["topic-ownership"], ids)
    }
    topics = {key: row["section_id"] for key, row in topic_rows.items()}
    representatives = defaultdict(list)
    for row in pipeline.rows(state, "unit-assignments"):
        selected = representatives[row["owner_id"]]
        if row["disposition"] == "included" and len(selected) < 3:
            selected.append(row["obligation_id"])
    result = []
    for assignment in assignments:
        identifier = assignment["obligation_id"]
        section_id = topics.get(identifier)
        mentions = []
        if section_id:
            if identifier in representatives[assignment["owner_id"]]:
                mentions.extend(
                    s["id"] for s in roots[assignment["owner_id"]] if s["role"] == "summary"
                )
            parent = sections[section_id]["parent_id"]
            if parent:
                mentions.append(parent)
            for span_id in topic_rows[identifier].get("supporting_span_ids", []):
                mentions.extend(
                    s["id"]
                    for s in roots[assignment["owner_id"]]
                    if s["template_span_id"] == span_id
                )
            for consumer in assignment["consuming_unit_ids"]:
                options = roots[consumer]
                match = next((s for s in options if s["role"] == "reference"), options[0])
                mentions.append(match["id"])
        result.append(
            ContentAllocation(
                id=stable_id("allocation", identifier),
                obligation_id=identifier,
                assignment_id=assignment["id"],
                disposition="full_treatment" if section_id else assignment["disposition"],
                canonical_section_id=section_id,
                supporting_section_ids=sorted(set(mentions)),
                reason=assignment["reason"],
                decision_refs=assignment["decision_refs"],
            ).model_dump()
        )
    return result


def make_pages(pipeline, state, choices):
    inputs = pipeline.inputs(state)
    sections = list(pipeline.rows(state, "logical-sections"))
    units = list(pipeline.rows(state, "documentation-units"))
    instances = {i["unit_id"]: i for i in pipeline.rows(state, "template-instances")}
    choices = {row["section_id"]: row for row in choices}
    multi = len(units) > 1
    collection_id = stable_id("page", "collection")
    root_id = collection_id if multi else stable_id("page", units[0]["id"])
    pages = []
    prior = {}
    if inputs.previous_plan_ref:
        previous = pipeline.store.get(inputs.previous_plan_ref)
        prior = {p["id"]: p for p in pipeline.store.iter_table(previous["components"]["pages"])}

    def page(owner, role, title, path, parent, owned, profile, rationale, task, estimate=0):
        identifier = stable_id("page", owned[0]["id"] if role == "detail" else owner)
        if identifier in prior and not (
            multi and prior[identifier]["path"] == "index.md" and role == "unit"
        ):
            path = prior[identifier]["path"]
        instance = instances.get(owner)
        return PagePlan(
            id=identifier,
            owner_id=owner,
            role=role,
            template_instance_id=instance["id"] if instance else None,
            path=path,
            parent_id=parent,
            profile=profile,
            title=title,
            purpose=task,
            audience=inputs.brief.audience,
            reader_task=task,
            scope=instance["metadata"]["scope"] if instance else "Selected evidence only",
            section_ids=[s["id"] for s in owned],
            estimated_words=estimate,
            expected_length=[800, 1800] if role == "detail" else [0, max(1800, estimate)],
            rationale=rationale,
            alternatives="Keep topics inline when independent detail is unnecessary",
            dependencies=[],
            completion_checks=[
                "Every assigned obligation has its full qualifiers and local source reference",
                "Unknown attributes remain explicit; no implementation status is inferred",
                "Every section is assembled once and navigation targets resolve",
            ],
        ).model_dump()

    for unit in units:
        owner = unit["id"]
        owned = [s for s in sections if s["owner_id"] == owner]
        root_page_id = stable_id("page", owner)
        folder = safe_slug(unit["title"]) + "-" + owner[-8:]
        detail = {
            s["id"]
            for s in owned
            if s["id"] in choices
            and choices[s["id"]]["detail"]
            and inputs.brief.delivery_mode != "single_page"
        }
        order = {s["id"]: s["order"] for s in owned if s["parent_id"] is None}
        inline = sorted(
            (s for s in owned if s["id"] not in detail),
            key=lambda s: (
                order.get(s["parent_id"], s["order"]),
                s["parent_id"] is not None,
                s["order"],
            ),
        )
        estimate = sum(choices[s["id"]]["estimated_words"] for s in inline if s["id"] in choices)
        pages.append(
            page(
                owner,
                "unit",
                unit["title"],
                f"{folder}/index.md" if multi else "index.md",
                collection_id if multi else None,
                inline,
                "unit_template",
                "One full template instance for this independently supported reader goal",
                unit["purpose"],
                estimate,
            )
        )
        for section in owned:
            if section["id"] not in detail:
                continue
            choice = choices[section["id"]]
            filename = safe_slug(section["title"]) + "-" + section["id"][-8:] + ".md"
            pages.append(
                page(
                    owner,
                    "detail",
                    section["title"],
                    f"{folder}/{filename}",
                    root_page_id,
                    [section],
                    choice["profile"],
                    choice["rationale"],
                    choice["reader_task"],
                    choice["estimated_words"],
                )
            )
    for owner, role, path in (
        ("collection", "collection", "index.md"),
        ("shared", "shared", "shared/index.md"),
        ("sources", "sources", "sources/index.md"),
    ):
        owned = [s for s in sections if s["owner_id"] == owner]
        if owned:
            pages.append(
                page(
                    owner,
                    role,
                    owned[0]["title"],
                    path,
                    None if role == "collection" else root_id,
                    owned,
                    "reference" if role == "shared" else role,
                    "Explicit collection, shared-reference or source-index role",
                    owned[0]["reader_question"],
                )
            )
    validate_paths(pages)
    return pages


def brief_tasks(pipeline, state):
    sections = list(pipeline.rows(state, "logical-sections"))
    pages = {s: p["id"] for p in pipeline.rows(state, "pages") for s in p["section_ids"]}
    allocations = list(pipeline.rows(state, "content-allocations"))
    instances = {i["id"]: i for i in pipeline.rows(state, "template-instances")}
    contract = pipeline.component(state, "template-contract")
    spans = {s["id"]: s for s in contract["spans"]}
    rules = {r["span_id"]: r for r in contract["rules"]}
    included = [a for a in allocations if a["disposition"] == "full_treatment"]
    for section in sections:
        identifiers = {
            a["obligation_id"]
            for a in included
            if a["canonical_section_id"] == section["id"]
            or section["id"] in a["supporting_section_ids"]
        }
        applicable = []
        if section["template_span_id"] in spans:
            root = section["template_span_id"]
            for span in spans.values():
                cursor = span
                while cursor:
                    if cursor["id"] == root:
                        applicable.append({"span": span, "rule": rules[span["id"]]})
                        break
                    cursor = spans.get(cursor["parent_id"])
        base = {
            "section": section,
            "page_id": pages[section["id"]],
            "requirements": applicable,
            "metadata": instances.get(section["template_instance_id"], {}).get("metadata", {}),
            "child_topics": [
                {"section_id": s["id"], "title": s["title"], "question": s["reader_question"]}
                for s in sections
                if s["parent_id"] == section["id"]
            ],
        }
        if not identifiers:
            yield {**base, "obligation_ids": []}
            continue
        obligations = pipeline.obligations(state, sorted(identifiers))
        for group in bounded_groups(
            obligations,
            min(pipeline.settings.planning_tokens, pipeline.settings.writing_tokens // 3),
            lambda row: evidence_context(pipeline.store, pipeline.inputs(state), [row]),
        ):
            yield {**base, "obligation_ids": [row["id"] for row in group]}


def validate_brief(result, identifiers):
    allowed = set(identifiers)
    for table in result.tables:
        if len(table.columns) != len(set(table.columns)):
            raise ValueError("Duplicate table columns")
        if len({row.id for row in table.rows}) != len(table.rows):
            raise ValueError("Duplicate table row identities")
        for row in table.rows:
            if set(row.obligation_ids) - allowed or (not row.editorial and not row.obligation_ids):
                raise ValueError("Unsupported table row")
    for diagram in result.diagrams:
        nodes = {node.id for node in diagram.nodes}
        if len(nodes) != len(diagram.nodes):
            raise ValueError("Duplicate diagram node identities")
        for node in diagram.nodes:
            if set(node.obligation_ids) - allowed or (
                not node.editorial and not node.obligation_ids
            ):
                raise ValueError("Unsupported diagram node")
        for edge in diagram.edges:
            if (
                {edge.source, edge.target} - nodes
                or set(edge.obligation_ids) - allowed
                or not edge.obligation_ids
            ):
                raise ValueError("Unsupported diagram edge")


def make_navigation(pipeline, state):
    pages = list(pipeline.rows(state, "pages"))
    roots = [p for p in pages if p["parent_id"] is None]
    if len(roots) != 1:
        raise ValueError("Documentation hierarchy must have exactly one root")
    root = roots[0]["id"]
    owners = {s: p["id"] for p in pages for s in p["section_ids"]}
    sections = {s["id"]: s for s in pipeline.rows(state, "logical-sections")}
    links = []
    for page in pages:
        if page["parent_id"]:
            links.extend(
                [
                    NavigationLink(
                        source=page["id"],
                        target=page["parent_id"],
                        kind="parent",
                        reason="Hierarchy",
                    ),
                    NavigationLink(
                        source=page["id"],
                        target=root,
                        kind="root",
                        reason="Collection or unit entry",
                    ),
                    NavigationLink(
                        source=page["parent_id"],
                        target=page["id"],
                        kind="detail",
                        reason=page["reader_task"],
                    ),
                ]
            )
        for section in page["section_ids"]:
            links.append(
                NavigationLink(
                    source=page["id"],
                    target=section,
                    kind="reader_entry",
                    reason=sections[section]["reader_question"],
                )
            )
    for section in sections.values():
        if section["parent_id"]:
            links.append(
                NavigationLink(
                    source=section["parent_id"],
                    target=section["id"],
                    kind="reader_entry",
                    reason=section["reader_question"],
                )
            )
    for brief in pipeline.rows(state, "section-briefs"):
        for target in brief["canonical_links"].values():
            links.append(
                NavigationLink(
                    source=brief["section_id"],
                    target=target,
                    kind="canonical",
                    reason="Canonical treatment with qualifications",
                )
            )
    paths, changes = {}, []
    inputs = pipeline.inputs(state)
    if inputs.previous_plan_ref:
        previous = pipeline.store.get(inputs.previous_plan_ref)
        old = {p["id"]: p for p in pipeline.store.iter_table(previous["components"]["pages"])}
        current = {p["id"]: p for p in pages}
        for key in sorted(set(old) | set(current)):
            if key not in current:
                changes.append({"kind": "removed", "page_id": key, "path": old[key]["path"]})
            elif key not in old:
                changes.append({"kind": "added", "page_id": key, "path": current[key]["path"]})
            elif old[key]["path"] != current[key]["path"]:
                paths[old[key]["path"]] = current[key]["path"]
                changes.append(
                    {
                        "kind": "moved",
                        "page_id": key,
                        "old": old[key]["path"],
                        "new": current[key]["path"],
                    }
                )
    unique = {(link.source, link.target, link.kind): link for link in links}
    return NavigationPlan(
        root=root,
        tree_edges=[[p["parent_id"], p["id"]] for p in pages if p["parent_id"]],
        anchors={key: key for key in owners},
        links=list(unique.values()),
        path_mappings=paths,
        changes=changes,
    )


def writing_jobs(pipeline, state):
    sections = {s["id"]: s for s in pipeline.rows(state, "logical-sections")}
    jobs = []
    for brief in pipeline.rows(state, "section-briefs"):
        identifiers = brief["full_treatment_ids"] + brief["supporting_ids"]
        obligations = pipeline.obligations(state, identifiers)
        groups = list(
            bounded_groups(
                obligations,
                pipeline.settings.writing_tokens // 3,
                lambda row: evidence_context(pipeline.store, pipeline.inputs(state), [row]),
            )
        ) or [[]]
        for fragment, group in enumerate(groups):
            ids = [r["id"] for r in group]
            context = {
                "brief": brief,
                "owned_obligation_ids": ids,
                "originals": evidence_context(pipeline.store, pipeline.inputs(state), group),
                "metadata": pipeline.inputs(state).brief.model_dump(),
                "knowledge_revision": pipeline.inputs(state).knowledge_revision,
                "inherited_references": {
                    "knowledge": pipeline.inputs(state).knowledge_ref,
                    "planning_inputs": state["inputs_ref"],
                    "selection": pipeline.inputs(state).selection_ref,
                    "source_blocks": pipeline.inputs(state).blocks_ref,
                    "phase_1_coverage": pipeline.inputs(state).coverage_ref,
                    "template": pipeline.inputs(state).template_ref,
                    **{
                        key: pipeline.components(state)[key]
                        for key in (
                            "documentation-units",
                            "template-instances",
                            "template-contract",
                            "content-obligations",
                            "content-allocations",
                            "pages",
                            "navigation",
                        )
                    },
                },
            }
            tokens = estimate_tokens(encode(context))
            if tokens > pipeline.settings.writing_tokens:
                raise ValueError(
                    "Writing context exceeds configured bound; smaller briefing work is required"
                )
            jobs.append(
                WritingJob(
                    id=stable_id("job", brief["id"], fragment),
                    section_id=brief["section_id"],
                    page_id=brief["page_id"],
                    brief_id=brief["id"],
                    fragment=fragment,
                    assembly_order=len(jobs),
                    obligation_ids=ids,
                    context_ref=pipeline.store.put(context, "writing-context"),
                    hard_dependencies=[],
                    estimated_input_tokens=tokens,
                    max_output_tokens=pipeline.settings.output_tokens,
                    output_contract={
                        "format": "markdown_section_fragment",
                        "section_id": brief["section_id"],
                        "full_treatment_ids": [i for i in ids if i in brief["full_treatment_ids"]],
                        "supporting_ids": [i for i in ids if i in brief["supporting_ids"]],
                        "allow_new_pages": False,
                        "verify_generated_content": True,
                    },
                    completion_checks=brief["content"]["completion_checks"],
                ).model_dump()
            )
    detail_jobs = [j for j in jobs if sections[j["section_id"]]["role"] == "topic"]
    for job in jobs:
        section = sections[job["section_id"]]
        if section["parent_id"] is None and section["role"] != "catalog":
            job["hard_dependencies"] = [
                j["id"]
                for j in detail_jobs
                if sections[j["section_id"]]["owner_id"] == section["owner_id"]
            ]
        if section["role"] == "catalog":
            job["hard_dependencies"] = [
                j["id"] for j in jobs if sections[j["section_id"]]["role"] == "summary"
            ]
    validate_dag(
        [j["id"] for j in jobs], [(d, j["id"]) for j in jobs for d in j["hard_dependencies"]]
    )
    return jobs
