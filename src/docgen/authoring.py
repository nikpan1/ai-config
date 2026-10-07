import html
import re
import shutil
from pathlib import Path

from docgen.models import Chapter, ChapterPlan, Draft, Finding, Knowledge, Outline
from docgen.storage import Store, digest, write_json


def evidence_bundle(graph: Knowledge, parsed: dict, claim_ids: list[str]) -> dict:
    claims = [c for c in graph.claims if c.id in claim_ids and c.status == "accepted"]
    evidence_ids = {e for c in claims for e in c.evidence_ids}
    evidence = [e.model_dump() for e in graph.evidence if e.id in evidence_ids]
    span_ids = {e["span_id"] for e in evidence}
    entities = {e for c in claims for e in c.entity_ids}
    return {
        "claims": [c.model_dump() for c in claims],
        "evidence": evidence,
        "spans": [s for s in parsed["spans"] if s["id"] in span_ids],
        "entities": [e.model_dump() for e in graph.entities if e.id in entities],
        "relationships": [
            r.model_dump()
            for r in graph.relationships
            if set(r.claim_ids) <= set(claim_ids) and r.subject in entities and r.object in entities
        ],
    }


def safe_text(value: str) -> bool:
    return not re.search(r"<[^>]+>|!?\[[^\]]*\]\(|^\s*#{1,6}\s|```", value, re.MULTILINE)


def validate_chapter(chapter: Chapter, plan: ChapterPlan, graph: Knowledge) -> list[Finding]:
    findings: list[Finding] = []

    def error(artifact: str, message: str) -> None:
        findings.append(Finding(severity="error", artifact_id=artifact, message=message))

    if chapter.id != plan.id or chapter.title != plan.title:
        error(chapter.id, "Chapter identity must match approved outline")
    claims = {c.id: c for c in graph.claims if c.status == "accepted"}
    blocks: set[str] = set()
    covered: set[str] = set()
    for block in chapter.blocks:
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", block.id) or block.id in blocks:
            error(block.id, "Invalid or duplicate block ID")
        blocks.add(block.id)
        if not block.content.strip() or not safe_text(block.content):
            error(
                block.id, "Blocks must contain plain text without embedded HTML, links or headings"
            )
        if not block.claim_ids or not set(block.claim_ids) <= set(plan.required_claim_ids):
            error(block.id, "Block must reference claims from its approved chapter")
        if not set(block.claim_ids) <= claims.keys():
            error(block.id, "Unaccepted or unknown claim")
            continue
        required_evidence = {e for c in block.claim_ids for e in claims[c].evidence_ids}
        if set(block.evidence_ids) != required_evidence:
            error(block.id, "Block evidence must match its supporting claims")
        covered.update(block.claim_ids)
    if set(plan.required_claim_ids) - covered:
        error(
            chapter.id,
            "Required claims omitted: " + ", ".join(sorted(set(plan.required_claim_ids) - covered)),
        )
    entities = {e.id: e for e in graph.entities}
    relationships = {r.id: r for r in graph.relationships}
    diagram_ids: set[str] = set()
    for diagram in chapter.diagrams:
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", diagram.id) or diagram.id in diagram_ids:
            error(diagram.id, "Invalid or duplicate diagram ID")
        diagram_ids.add(diagram.id)
        if not diagram.edges:
            error(diagram.id, "A diagram needs supported edges")
        for key, label in diagram.nodes.items():
            if key not in entities or entities[key].name != label:
                error(diagram.id, "Diagram node does not match a source entity")
        for edge in diagram.edges:
            relationship = relationships.get(edge.relationship_id)
            if (
                not relationship
                or relationship.subject != edge.subject
                or relationship.object != edge.object
                or relationship.type != edge.label
                or set(relationship.claim_ids) != set(edge.claim_ids)
                or not set(edge.claim_ids) <= set(plan.required_claim_ids)
                or not set(edge.claim_ids) <= claims.keys()
                or edge.subject not in diagram.nodes
                or edge.object not in diagram.nodes
            ):
                error(diagram.id, "Unsupported diagram relationship")
    return findings


def validate_draft(
    draft: Draft, outline: Outline, graph: Knowledge, parsed: dict, root: Path
) -> list[Finding]:
    findings: list[Finding] = []
    plans = {p.id: p for p in outline.chapters}
    if [c.id for c in draft.chapters] != [p.id for p in outline.chapters]:
        findings.append(
            Finding(
                severity="error",
                artifact_id="draft",
                message="Chapter order differs from approved outline",
            )
        )
    for chapter in draft.chapters:
        if chapter.id in plans:
            findings.extend(validate_chapter(chapter, plans[chapter.id], graph))
    documents = {d["snapshot_id"]: d for d in parsed["documents"]}
    for span in parsed["spans"]:
        document = documents[span["snapshot_id"]]
        raw = (root / document["snapshot"]).read_bytes()
        lines = raw.decode("utf-8-sig").splitlines(keepends=True)
        excerpt = "".join(lines[span["start_line"] - 1 : span["end_line"]])
        if digest(raw) != document["content_hash"] or excerpt != span["excerpt"]:
            findings.append(
                Finding(
                    severity="error",
                    artifact_id=span["id"],
                    message="Source locator or quotation mismatch",
                )
            )
    for row in graph.coverage:
        if row.disposition == "unresolved":
            findings.append(
                Finding(
                    severity="warning",
                    artifact_id=row.evidence_id,
                    message="Unresolved source coverage",
                )
            )
    return findings


def mermaid(diagram: dict) -> str:
    keys = {key: f"n{i}" for i, key in enumerate(diagram["nodes"])}

    def label(value: str) -> str:
        return "".join(c if c.isalnum() or c in " -_" else f"#{ord(c)};" for c in value)

    lines = ["flowchart TD"]
    lines.extend(f'    {keys[key]}["{label(value)}"]' for key, value in diagram["nodes"].items())
    lines.extend(
        f'    {keys[e["subject"]]} -->|"{label(e["label"])}"| {keys[e["object"]]}'
        for e in diagram["edges"]
    )
    return "\n".join(lines) + "\n"


def escaped(value: str) -> str:
    return re.sub(r"([\\`*_{}\[\]<>#!|])", r"\\\1", value)


def chapter_markdown(chapter: Chapter, audit: bool = False) -> str:
    lines = [f"# {escaped(chapter.title)}", ""]
    for block in chapter.blocks:
        block_id = f"{chapter.id}-{block.id}"
        lines.extend([f'<a id="{block_id}"></a>', escaped(block.content), ""])
        if audit:
            lines.extend(
                [
                    "Evidence: "
                    + ", ".join(f"[{e}](../evidence/{e}.md)" for e in block.evidence_ids),
                    "",
                ]
            )
    for diagram in chapter.diagrams:
        lines.extend(
            [
                f"<!-- diagram:{chapter.id}-{diagram.id} -->",
                "```mermaid",
                mermaid(diagram.model_dump()).rstrip(),
                "```",
                "",
            ]
        )
        if audit:
            lines.extend(
                [
                    "Supporting claims: "
                    + ", ".join(sorted({c for e in diagram.edges for c in e.claim_ids})),
                    "",
                ]
            )
    if chapter.gaps:
        lines.extend(["## Clarifications", "", *[f"- {escaped(g)}" for g in chapter.gaps], ""])
    return "\n".join(lines)


def render_draft(directory: Path, draft: Draft) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for chapter in draft.chapters:
        (directory / f"{chapter.id}.md").write_text(chapter_markdown(chapter), "utf-8")


def export_bundle(
    store: Store,
    destination: Path,
    draft: Draft,
    graph: Knowledge,
    parsed: dict,
    outline: Outline,
    revision: str,
    included_images: list[str],
    customer_evidence: bool,
) -> dict:
    customer, audit = destination / "customer", destination / "audit"
    for path in (
        customer / "chapters",
        customer / "diagrams",
        customer / "assets",
        audit / "chapters",
        audit / "evidence",
        audit / "assets",
    ):
        path.mkdir(parents=True, exist_ok=True)
    spans = {s["id"]: s for s in parsed["spans"]}
    assets = {a["id"]: a for a in parsed["images"]}
    provenance: dict = {
        "revision": revision,
        "blocks": {},
        "diagrams": {},
        "claims": [c.model_dump() for c in graph.claims],
        "evidence": [e.model_dump() for e in graph.evidence],
        "sources": parsed["documents"],
    }
    for evidence in graph.evidence:
        lines = [f"# Evidence {evidence.id}", ""]
        if evidence.kind == "reviewer":
            lines += [
                f"Reviewer: {escaped(evidence.reviewer or '')}; {evidence.timestamp}",
                "",
                escaped(evidence.statement or ""),
            ]
        else:
            span = spans[evidence.span_id]
            lines += [
                f"Source: {escaped(span['path'])}, lines {span['start_line']}-{span['end_line']}",
                f"Snapshot SHA-256: {span['snapshot_id']}",
                "",
                "Excerpt from the retained run snapshot; original Markdown is not bundled.",
                "",
                "<pre>" + html.escape(span["excerpt"]) + "</pre>",
            ]
        if evidence.asset_id:
            asset = assets[evidence.asset_id]
            if asset["snapshot"]:
                name = Path(asset["snapshot"]).name
                shutil.copyfile(store.root / asset["snapshot"], audit / "assets" / name)
                lines += ["", f"![Source image](../assets/{name})"]
        (audit / "evidence" / f"{evidence.id}.md").write_text("\n".join(lines) + "\n", "utf-8")
    for chapter in draft.chapters:
        (customer / "chapters" / f"{chapter.id}.md").write_text(chapter_markdown(chapter), "utf-8")
        (audit / "chapters" / f"{chapter.id}.md").write_text(
            chapter_markdown(chapter, True), "utf-8"
        )
        for block in chapter.blocks:
            provenance["blocks"][f"{chapter.id}-{block.id}"] = block.model_dump()
        for diagram in chapter.diagrams:
            diagram_id = f"{chapter.id}-{diagram.id}"
            provenance["diagrams"][diagram_id] = diagram.model_dump()
            (customer / "diagrams" / f"{diagram_id}.mmd").write_text(
                mermaid(diagram.model_dump()), "utf-8"
            )
    preparation = ["# Customer preparation", ""]
    used = {
        claim_id
        for chapter in draft.chapters
        for block in chapter.blocks
        for claim_id in block.claim_ids
    }
    obligations = [c for c in graph.claims if c.id in used and c.obligation]
    glossary = ["# Glossary", ""]
    for entity in sorted(graph.entities, key=lambda e: e.name.casefold()):
        related_claims = [c for c in graph.claims if c.id in used and entity.id in c.entity_ids]
        if not related_claims:
            continue
        block_id = "glossary-" + digest(entity.id)[:16]
        glossary += [f'<a id="{block_id}"></a>', f"## {escaped(entity.name)}", ""]
        if entity.aliases:
            glossary += ["Also called: " + ", ".join(escaped(a) for a in entity.aliases) + ".", ""]
        chapters = [
            ch
            for ch in draft.chapters
            if any(c.id in b.claim_ids for c in related_claims for b in ch.blocks)
        ]
        glossary += [
            "See "
            + ", ".join(f"[{escaped(ch.title)}](chapters/{ch.id}.md)" for ch in chapters)
            + ".",
            "",
        ]
        provenance["blocks"][block_id] = {
            "entity_id": entity.id,
            "claim_ids": [c.id for c in related_claims],
            "evidence_ids": entity.evidence_ids,
        }
    (customer / "glossary.md").write_text("\n".join(glossary), "utf-8")
    seen: set[str] = set()
    for claim in obligations:
        requirement = claim.obligation
        assert requirement is not None
        key = digest([requirement.model_dump(), claim.conditions, claim.exceptions])
        if key in seen:
            continue
        seen.add(key)
        preparation.append(f'<a id="preparation-{key[:16]}"></a>')
        related = [
            c
            for c in obligations
            if c.obligation == requirement
            and c.conditions == claim.conditions
            and c.exceptions == claim.exceptions
        ]
        chapter_ids = [
            ch.id
            for ch in draft.chapters
            if any(c.id in b.claim_ids for c in related for b in ch.blocks)
        ]
        preparation += [
            f"- {escaped(requirement.supplied)} ({requirement.requirement}). "
            f"Provided by: {escaped(requirement.by or 'not specified')}; "
            f"format: {escaped(requirement.format or 'not specified')}; "
            f"stage: {escaped(requirement.stage or 'not specified')}. "
            f"Conditions: {escaped('; '.join(claim.conditions) or 'not specified')}. "
            f"Exceptions: {escaped('; '.join(claim.exceptions) or 'not specified')}. "
            + ", ".join(f"[{ch}](chapters/{ch}.md)" for ch in chapter_ids)
        ]
        provenance["blocks"]["preparation-" + key[:16]] = {
            "claim_ids": [c.id for c in related],
            "evidence_ids": sorted({e for c in related for e in c.evidence_ids}),
        }
    if not obligations:
        preparation.append(
            "Customer preparation requirements are not specified in the approved evidence."
        )
    for chapter in draft.chapters:
        if not any(c.id in b.claim_ids for c in obligations for b in chapter.blocks):
            preparation.append(
                f"\nPreparation details for {escaped(chapter.title)} "
                "are not specified in the approved evidence."
            )
    (customer / "customer-preparation.md").write_text("\n".join(preparation) + "\n", "utf-8")
    index = ["# Customer documentation", "", f"Revision: {revision}", ""]
    index += [f"- [{escaped(ch.title)}](chapters/{ch.id}.md)" for ch in draft.chapters]
    index += ["- [Customer preparation](customer-preparation.md)", "- [Glossary](glossary.md)"]
    for asset_id in included_images:
        asset = assets.get(asset_id)
        if not asset or not asset["snapshot"]:
            raise ValueError(f"Cannot include missing image {asset_id}")
        name = Path(asset["snapshot"]).name
        shutil.copyfile(store.root / asset["snapshot"], customer / "assets" / name)
        index += [f"\n![Reviewed source image](assets/{name})"]
    if customer_evidence:
        shutil.copytree(audit / "evidence", customer / "evidence", dirs_exist_ok=True)
        shutil.copytree(audit / "assets", customer / "assets", dirs_exist_ok=True)
        index += ["", "## Evidence", ""] + [
            f"- [{e.id}](evidence/{e.id}.md)" for e in graph.evidence
        ]
    (customer / "README.md").write_text("\n".join(index) + "\n", "utf-8")
    (audit / "README.md").write_text(
        "# Internal audit edition\n\nSource excerpts and image evidence are bundled; "
        "original Markdown snapshots remain in run storage.\n\n"
        + "\n".join(f"- [{escaped(ch.title)}](chapters/{ch.id}.md)" for ch in draft.chapters)
        + "\n",
        "utf-8",
    )
    write_json(audit / "provenance.json", provenance)
    write_json(
        audit / "coverage.json",
        {
            "sources": [r.model_dump() for r in graph.coverage],
            "outline_exclusions": outline.excluded_claims,
            "gaps": graph.gaps,
        },
    )
    checksums = {
        p.relative_to(destination).as_posix(): digest(p.read_bytes())
        for p in destination.rglob("*")
        if p.is_file()
    }
    write_json(destination / "checksums.json", checksums)
    return {"revision": revision, "checksums": checksums}
