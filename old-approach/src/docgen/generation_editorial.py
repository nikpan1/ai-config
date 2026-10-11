from markdown_it import MarkdownIt
from pydantic import ValidationError

from docgen.generation_contracts import EditorialPage, EditorialVerification
from docgen.generation_export import evidence_id
from docgen.generation_validation import heading_slug, markdown_report
from docgen.model import RequestTooLarge, TruncatedOutput
from docgen.planning_helpers import evidence_context, require_exact
from docgen.storage import digest


def content_pages(pipeline, state):
    return [page for page in pipeline.rows(state, "pages") if page["role"] != "sources"]


def markdown_structure(markdown):
    tokens = MarkdownIt("commonmark").enable("table").parse(markdown)
    headings, links, fences, blocks = [], set(), [], []
    row = None
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            headings.append((token.tag, tokens[index + 1].content))
        if token.type == "fence":
            fences.append((token.info, token.content))
            if (
                token.info == "mermaid"
                and index + 2 < len(tokens)
                and tokens[index + 1].type == "paragraph_open"
                and tokens[index + 2].type == "inline"
                and tokens[index + 2].content.startswith("Diagram source:")
            ):
                targets = {
                    child.attrGet("href")
                    for child in tokens[index + 2].children or []
                    if child.type == "link_open"
                }
                blocks.append((token.content, targets))
        if token.type == "tr_open":
            row = []
        if token.type == "tr_close" and row:
            blocks.append(
                (" | ".join(text for text, _ in row), set().union(*(targets for _, targets in row)))
            )
            row = None
        destinations = {
            child.attrGet("href") or child.attrGet("src")
            for child in token.children or []
            if child.type in {"link_open", "image"}
        }
        links.update(destinations)
        if token.type == "inline":
            blocks.append((token.content, destinations))
            if row is not None:
                row.append((token.content, destinations))
    return headings, links, fences, blocks


def editorial_payload(pipeline, state):
    page = content_pages(pipeline, state)[state.get("editorial_index", 0)]
    sections = [
        s for s in pipeline.rows(state, "logical-sections") if s["id"] in page["section_ids"]
    ]
    jobs = [
        j for j in pipeline.rows(state, "writing-jobs") if j["section_id"] in page["section_ids"]
    ]
    ids = {key for job in jobs for key in job["obligation_ids"]}
    obligations = [o for o in pipeline.rows(state, "content-obligations") if o["id"] in ids]
    inputs = pipeline.planning_inputs(state)
    template = pipeline.store.get_object(inputs.template_ref)
    contract = pipeline.store.get_object(pipeline.plan(state)["components"]["template-contract"])
    spans = {s["template_span_id"] for s in sections if s["template_span_id"]}
    while True:
        expanded = spans | {s["id"] for s in contract["spans"] if s["parent_id"] in spans}
        if expanded == spans:
            break
        spans = expanded
    markdown = pipeline.read(state, "unpolished_pages_ref")[page["path"]]
    headings, links, fences, _ = markdown_structure(markdown)
    return {
        "page": page,
        "sections": [
            {
                key: section[key]
                for key in (
                    "id",
                    "title",
                    "parent_id",
                    "template_span_id",
                    "role",
                    "reader_question",
                )
            }
            for section in sections
        ],
        "markdown": markdown,
        "originals": evidence_context(pipeline.store, inputs, obligations),
        "source_catalog": {evidence_id(e): e for o in obligations for e in o["evidence"]},
        "template_markdown": bytes.fromhex(template["bytes_hex"]).decode("utf-8-sig"),
        "template_contract": {
            **contract,
            "spans": [
                {key: span[key] for key in ("id", "heading", "parent_id", "level")}
                for span in contract["spans"]
            ],
        },
        "applicable_template_span_ids": [
            r["span_id"] for r in contract["rules"] if r["span_id"] in spans
        ],
        "brief": inputs.brief.model_dump(),
        "language_contract": pipeline.read(state, "language_ref"),
        "page_tree": [
            {key: page[key] for key in ("id", "title", "path", "section_ids", "parent_id")}
            for page in pipeline.rows(state, "pages")
        ],
        "allocations": [
            a for a in pipeline.rows(state, "content-allocations") if a["obligation_id"] in ids
        ],
        "preserve": {
            "headings": headings,
            "link_destinations": sorted(links),
            "code_fences": fences,
        },
    }


def validate_editorial_page(result, payload):
    if result.page_id != payload["page"]["id"]:
        raise ValueError("Editorial revision changes page identity")
    headings, links, fences, blocks = markdown_structure(result.markdown)
    original_headings, original_links, original_fences, _ = markdown_structure(payload["markdown"])
    protected_slugs = {heading_slug(title) for _, title in original_headings}
    retained = [heading for heading in headings if heading_slug(heading[1]) in protected_slugs]
    if retained != original_headings:
        raise ValueError("Editorial revision changes planned headings or anchors")
    if links != original_links:
        raise ValueError("Editorial revision loses or invents source/navigation destinations")
    if fences != original_fences:
        raise ValueError("Editorial revision changes a protected diagram or code example")
    obligations = {o["id"]: o for o in payload["originals"]["obligations"]}
    page_evidence = {evidence_id(e) for o in obligations.values() for e in o["evidence"]}
    require_exact([c.obligation_id for c in result.coverage], obligations, "Editorial coverage")
    for coverage in result.coverage:
        allowed = {evidence_id(e) for e in obligations[coverage.obligation_id]["evidence"]}
        cited = set(coverage.evidence_ids)
        if cited - page_evidence or not cited & allowed:
            raise ValueError("Editorial coverage cites unrelated evidence")
        if not any(
            coverage.excerpt in text
            and all(
                any(href.endswith("#source-" + key) for href in targets)
                for key in coverage.evidence_ids
            )
            for text, targets in blocks
        ):
            raise ValueError(
                "Editorial coverage lacks a passage with adjacent source links: "
                + coverage.obligation_id
            )


def repair_editorial(pipeline, state, findings):
    if state.get("editorial_attempt", 0) < 1:
        return {
            "editorial_feedback_ref": pipeline.store.put(findings, "editorial-feedback"),
            "editorial_attempt": state.get("editorial_attempt", 0) + 1,
            "route": "polish_documentation",
        }
    return pipeline.gate(state, "verify_editorial_revision", findings)


def polish_documentation(pipeline, state):
    if state.get("editorial_index", 0) >= len(content_pages(pipeline, state)):
        return {"route": "validate_documentation"}
    payload = editorial_payload(pipeline, state)
    payload["feedback"] = pipeline.read(state, "editorial_feedback_ref", [])
    if state.get("editorial_draft_ref"):
        payload["previous_revision"] = pipeline.read(state, "editorial_draft_ref")
    try:
        result = pipeline.call("gen_polish", payload, EditorialPage)
    except ValidationError as error:
        return repair_editorial(
            pipeline, state, ["Invalid editorial response: " + str(error)[:1000]]
        )
    except TruncatedOutput:
        raise RequestTooLarge(
            "Editorial page output truncated; use a smaller planned page"
        ) from None
    return {
        "editorial_draft_ref": pipeline.store.put(result, "editorial-page"),
        "route": "verify_editorial_revision",
    }


def verify_editorial_revision(pipeline, state):
    payload = editorial_payload(pipeline, state)
    result = EditorialPage.model_validate(pipeline.read(state, "editorial_draft_ref"))
    try:
        validate_editorial_page(result, payload)
        pages = {**pipeline.read(state, "pages_ref"), payload["page"]["path"]: result.markdown}
        report = markdown_report(
            pages, pipeline.output_root(state), pipeline.store, pipeline.read(state, "assets_ref")
        )
        if report["findings"]:
            return repair_editorial(pipeline, state, report["findings"])
    except ValueError as error:
        return repair_editorial(pipeline, state, [str(error)])
    review = pipeline.call(
        "gen_page_review",
        {
            **payload,
            "original_markdown": payload["markdown"],
            "markdown": result.markdown,
            "editorial_revision": result.model_dump(exclude={"markdown"}),
        },
        EditorialVerification,
        output_limit=8000,
    )
    try:
        require_exact(
            review.checked_section_ids, payload["page"]["section_ids"], "Editorial section review"
        )
        require_exact(
            review.checked_obligation_ids,
            [o["id"] for o in payload["originals"]["obligations"]],
            "Editorial semantic review",
        )
        require_exact(
            [a.span_id for a in review.template_assessments],
            payload["applicable_template_span_ids"],
            "Editorial template review",
        )
        if any(set(f.obligation_ids) - set(review.checked_obligation_ids) for f in review.findings):
            raise ValueError("Editorial finding references an unrelated obligation")
    except ValueError as error:
        return repair_editorial(pipeline, state, [str(error)])
    record = {
        "page_id": result.page_id,
        "input_hash": digest(payload["markdown"]),
        "output_hash": digest(result.markdown),
        "editorial_ref": state["editorial_draft_ref"],
        "review": review.model_dump(),
    }
    review_ref = pipeline.store.put(record, "editorial-review")
    findings = [f.description for f in review.findings if f.blocking]
    findings.extend(a.explanation for a in review.template_assessments if not a.satisfied)
    if not all(
        [review.narrative_flows, review.repetition_controlled, review.source_links_readable]
    ):
        findings.append(
            "Improve narrative continuity, remove redundant explanations and integrate citations: "
            + review.readability
        )
    if findings:
        return {**repair_editorial(pipeline, state, findings), "editorial_review_ref": review_ref}
    return {
        "pages_ref": pipeline.store.put(pages, "generation-pages"),
        "page_reviews_ref": pipeline.store.put(
            [*pipeline.read(state, "page_reviews_ref", []), record], "generation-page-reviews"
        ),
        "editorial_review_ref": review_ref,
        "editorial_index": state.get("editorial_index", 0) + 1,
        "editorial_attempt": 0,
        "editorial_feedback_ref": "",
        "editorial_draft_ref": "",
        "route": "polish_documentation",
    }
