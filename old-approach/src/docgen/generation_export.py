import os
import re
import tempfile
from pathlib import Path
from urllib.parse import quote

from docgen.generation_validation import heading_slug, table_specs
from docgen.planning_helpers import validate_paths
from docgen.source_links import source_url_from_markdown, text_fragment_url
from docgen.storage import atomic_write, digest, file_digest, read_json, write_json
from docgen.storage import publish_directory as move_directory


def relative_link(source, target):
    return quote(os.path.relpath(target, source.parent).replace("\\", "/"), safe="/.-_#")


def evidence_id(evidence):
    return digest(evidence)[:20]


def source_catalog(pipeline, state):
    identifiers = {
        identifier
        for job in pipeline.rows(state, "writing-jobs")
        for identifier in job["obligation_ids"]
    }
    return {
        evidence_id(entry): entry
        for obligation in pipeline.rows(state, "content-obligations")
        if obligation["id"] in identifiers
        for entry in obligation["evidence"]
    }


def source_labels(pipeline, state):
    entries = source_catalog(pipeline, state)
    return {key: f"S{index}" for index, key in enumerate(sorted(entries), 1)}


def source_urls(pipeline, state):
    snapshot = pipeline.store.get_object(pipeline.planning_inputs(state).snapshot_ref)
    return {
        entry["path"]: source_url_from_markdown(
            pipeline.store.path(entry["ref"]).read_text(encoding="utf-8")
        )
        for entry in snapshot["inventory"]
        if entry.get("status") == "parsed"
    }


def citations(evidence, page, source_labels_by_id=None, source_links_by_id=None):
    target = relative_link(Path(page), Path("sources/index.md"))
    unique = {evidence_id(e): e for e in evidence}
    links = []
    for key in unique:
        label = source_labels_by_id[key] if source_labels_by_id is not None else f"Source {key[:6]}"
        anchor = label.lower() if source_labels_by_id is not None else f"source-{key}"
        direct = (source_links_by_id or {}).get(key)
        href = f"<{direct}>" if direct else f"{target}#{anchor}"
        links.append(f"[{label}]({href})")
    return " ".join(links)


def table_text(text):
    return text.replace("|", "\\|").replace("\n", " ")


def render_fragment(
    fragment, job, context, page, source_labels_by_id=None, source_links_by_id=None
):
    lines = []
    labels = {
        "requirement": "Requirement",
        "proposal": "Proposal",
        "observed": "Observed behavior",
        "example": "Example",
        "unknown": "Unknown",
    }
    for passage in fragment["passages"]:
        text = passage["text"]
        if passage["kind"] == "quote":
            lines.extend(
                [
                    "Source quotation:",
                    "",
                    *(
                        "> " + re.sub(r"([\\`*_{}\[\]<>])", r"\\\1", line)
                        for line in text.splitlines()
                    ),
                    "",
                    citations(passage["evidence"], page, source_labels_by_id, source_links_by_id),
                    "",
                ]
            )
        else:
            prefix = labels.get(passage["kind"])
            if passage["kind"] == "requirement" and re.search(
                r"\b(must|shall|required to)\b", text, re.IGNORECASE
            ):
                prefix = None
            lines.extend(
                [
                    (f"**{prefix}:** " if prefix else "")
                    + text
                    + " "
                    + citations(passage["evidence"], page, source_labels_by_id, source_links_by_id),
                    "",
                ]
            )
    specs = {t["index"]: t for t in table_specs(context, job)}
    for table in fragment["tables"]:
        columns = specs[table["index"]]["columns"]
        lines.extend(
            [
                "| " + " | ".join(map(table_text, columns)) + " |",
                "| " + " | ".join("---" for _ in columns) + " |",
            ]
        )
        for row in table["rows"]:
            cells = [table_text(cell["text"]) for cell in row["cells"]]
            row_evidence = [entry for cell in row["cells"] for entry in cell["evidence"]]
            if row_evidence:
                cells[-1] += " " + citations(
                    row_evidence, page, source_labels_by_id, source_links_by_id
                )
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
    return "\n".join(lines).strip()


def mermaid_text(spec):
    def label(value):
        return (
            value.replace("&", "#38;")
            .replace('"', "#quot;")
            .replace("<", "#60;")
            .replace(">", "#62;")
            .replace("\n", " ")
        )

    nodes = {node["id"]: f"n{index}" for index, node in enumerate(spec["nodes"])}
    lines = ["```mermaid", "flowchart TD"]
    for node in spec["nodes"]:
        lines.append(f'    {nodes[node["id"]]}["{label(node["label"])}"]')
    for edge in spec["edges"]:
        lines.append(
            f'    {nodes[edge["source"]]} -->|"{label(edge["label"])}"| {nodes[edge["target"]]}'
        )
    return "\n".join([*lines, "```"])


def empty_section_job(pipeline, job, diagrams):
    if job["obligation_ids"]:
        return False
    context = pipeline.store.get_object(job["context_ref"])
    return not any(
        (
            context["brief"]["content"]["unknowns"],
            context["brief"]["content"]["diagrams"],
            context["brief"]["canonical_links"],
            table_specs(context, job),
            diagrams.get(job["brief_id"]),
        )
    )


def assemble(pipeline, state):
    labels = source_labels(pipeline, state)
    plans = list(pipeline.rows(state, "pages"))
    sections = {r["id"]: r for r in pipeline.rows(state, "logical-sections")}
    jobs = sorted(pipeline.rows(state, "writing-jobs"), key=lambda j: j["assembly_order"])
    fragments = pipeline.read(state, "fragments_ref", {})
    page_by_section = {key: page for page in plans for key in page["section_ids"]}
    by_id = {p["id"]: p for p in plans}
    evidence = source_catalog(pipeline, state)
    blocks = {
        block["id"]: block
        for block in pipeline.store.iter_table(pipeline.planning_inputs(state).blocks_ref)
    }
    urls = source_urls(pipeline, state)
    source_links_by_id = {}
    for key, entry in evidence.items():
        block = blocks[entry["block_id"]]
        if url := urls.get(block["path"]):
            source_links_by_id[key] = text_fragment_url(url, block["content"])
    output = {}
    diagrams = pipeline.read(state, "diagrams_ref", {})
    for page in plans:
        lines = [f"# {page['title']}", ""]
        if page["parent_id"]:
            parent = by_id[page["parent_id"]]
            href = relative_link(Path(page["path"]), Path(parent["path"]))
            lines.extend(
                [
                    f"[Up: {parent['title']}]({href})",
                    "",
                ]
            )
        for child in plans:
            if child["parent_id"] == page["id"]:
                href = relative_link(Path(page["path"]), Path(child["path"]))
                lines.append(f"- [{child['title']}]({href})")
        lines.append("")
        rendered_briefs = set()
        for key in page["section_ids"]:
            section = sections[key]
            section_jobs = [job for job in jobs if job["section_id"] == key]
            empty_leaf = (
                section["role"] not in {"sources", "catalog"}
                and not any(
                    candidate["parent_id"] == key and candidate["id"] in page["section_ids"]
                    for candidate in sections.values()
                )
                and section_jobs
                and all(empty_section_job(pipeline, job, diagrams) for job in section_jobs)
            )
            if empty_leaf:
                continue
            level, parent = 2, section["parent_id"]
            while parent and parent in page["section_ids"]:
                level += 1
                parent = sections[parent]["parent_id"]
            lines.extend(["#" * min(level, 6) + " " + section["title"], ""])
            section_links = set()
            for job in section_jobs:
                fragment = pipeline.store.get_object(fragments[job["id"]]["fragment_ref"])
                context = pipeline.store.get_object(job["context_ref"])
                lines.extend(
                    [
                        render_fragment(
                            fragment, job, context, page["path"], labels, source_links_by_id
                        ),
                        "",
                    ]
                )
                for obligation in context["originals"]["obligations"]:
                    for entry in obligation["evidence"]:
                        evidence[evidence_id(entry)] = entry
                section_links.update(context["brief"]["canonical_links"].values())
                if job["brief_id"] not in rendered_briefs:
                    for diagram in diagrams.get(job["brief_id"], []):
                        lines.extend(
                            [
                                diagram["markdown"],
                                "",
                                "Diagram source: "
                                + citations(
                                    diagram["evidence"], page["path"], labels, source_links_by_id
                                ),
                                "",
                            ]
                        )
                        for edge in diagram["spec"]["edges"]:
                            nodes = {n["id"]: n for n in diagram["spec"]["nodes"]}
                            lines.extend(
                                [
                                    f"- {nodes[edge['source']]['label']} → "
                                    f"{nodes[edge['target']]['label']}: {edge['label']}"
                                ]
                            )
                        lines.append("")
                        for unknown in diagram["spec"]["unknown_transitions"]:
                            lines.extend([f"**Unknown transition:** {unknown}", ""])
                    rendered_briefs.add(job["brief_id"])
            if section_links:
                links = []
                for target in sorted(section_links, key=lambda item: sections[item]["title"]):
                    canonical_page = page_by_section[target]
                    href = relative_link(Path(page["path"]), Path(canonical_page["path"]))
                    titles = [sections[s]["title"] for s in canonical_page["section_ids"]]
                    if titles.count(sections[target]["title"]) == 1:
                        href += "#" + quote(heading_slug(sections[target]["title"]))
                    links.append(f"[{sections[target]['title']}]({href})")
                lines.extend(["Related: " + ", ".join(links) + ".", ""])
        output[page["path"]] = "\n".join(lines).strip() + "\n"
    assets = pipeline.read(state, "assets_ref", [])
    sources = {a["path"]: a for a in assets if a["kind"] == "source"}
    source_lines = []
    for key, entry in sorted(evidence.items(), key=lambda item: int(labels[item[0]][1:])):
        block = blocks[entry["block_id"]]
        target = relative_link(
            pipeline.output_root(state) / "sources/index.md", Path(sources[block["path"]]["target"])
        )
        target = source_links_by_id.get(key) or target
        source_lines.extend(
            [
                f"## {labels[key]}",
                "",
                f"[{block['path']}]({target}) — lines {block['line_start']}–{block['line_end']}.",
                "",
                "Source quotation:",
                "",
            ]
        )
        source_lines.extend(
            "> " + re.sub(r"([\\`*_{}\[\]<>])", r"\\\1", line)
            for line in entry["excerpt"].splitlines()
        )
        source_lines.append("")
    output["sources/index.md"] = (
        output.get("sources/index.md", "# Sources\n\n") + "\n" + "\n".join(source_lines) + "\n"
    )
    linked = [a for a in assets if a["kind"] == "attachment" and a["target"]]
    if linked:
        lines = ["# Attachments", "", "These links require the original source workspace.", ""]
        for asset in linked:
            href = relative_link(
                pipeline.output_root(state) / "attachments/index.md", Path(asset["target"])
            )
            marker = "!" if asset["disposition"] == "image" else ""
            lines.extend([f"{marker}[{asset['purpose']}]({href})", ""])
            if asset.get("explanation"):
                lines.extend(
                    [f"Reviewer explanation ({asset['reviewer']}): {asset['explanation']}", ""]
                )
        output["attachments/index.md"] = "\n".join(lines)
    for name in output:
        if name != "sources/index.md":
            output[name] += (
                "\n[Sources](" + relative_link(Path(name), Path("sources/index.md")) + ")\n"
            )
        if linked and name != "attachments/index.md":
            output[name] += (
                "\n[Attachments](" + relative_link(Path(name), Path("attachments/index.md")) + ")\n"
            )
    validate_paths([{"path": name} for name in output])
    return output


def publish_directory(destination, files):
    if destination.exists():
        actual = {
            p.relative_to(destination).as_posix(): file_digest(p)
            for p in destination.rglob("*")
            if p.is_file()
        }
        expected = {name: digest(text.encode("utf-8")) for name, text in files.items()}
        if actual != expected:
            raise ValueError("Existing immutable output differs")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".generation-", dir=destination.parent))
    for name, text in files.items():
        target = (temporary / name).resolve()
        if not target.is_relative_to(temporary):
            raise ValueError("Export path escapes output directory")
        atomic_write(target, text)
    move_directory(temporary, destination)


def publish(pipeline, state, status):
    from docgen.storage import encode

    pages = pipeline.read(state, "pages_ref")
    revision = digest(
        [
            state["inputs_ref"],
            state["language_ref"],
            state["assets_ref"],
            state["pages_ref"],
            state.get("decisions_ref"),
            status,
        ]
    )
    root = pipeline.store.path(f"runs/{state['run_id']}")
    destination = root / "documentation" / revision
    metadata = root / "generation-metadata" / revision
    records = {
        name: pipeline.read(state, name)
        for name in (
            "inputs_ref",
            "language_ref",
            "assets_ref",
            "fragments_ref",
            "diagrams_ref",
            "unpolished_pages_ref",
            "page_reviews_ref",
            "validation_ref",
            "claim_audit_ref",
            "presentation_ref",
            "decisions_ref",
            "source_labels_ref",
        )
    }
    labels = records["source_labels_ref"]
    source_blocks = {
        block["id"]: block
        for block in pipeline.store.iter_table(pipeline.planning_inputs(state).blocks_ref)
    }
    urls = source_urls(pipeline, state)
    source_map = {}
    for obligation in pipeline.rows(state, "content-obligations"):
        for evidence in obligation["evidence"]:
            key = evidence_id(evidence)
            if key not in labels:
                continue
            block = source_blocks[evidence["block_id"]]
            entry = source_map.setdefault(
                labels[key],
                {
                    "evidence_id": key,
                    "evidence": evidence,
                    "path": block["path"],
                    "line_start": block["line_start"],
                    "line_end": block["line_end"],
                    "source_url": urls.get(block["path"]),
                    "direct_url": text_fragment_url(urls[block["path"]], block["content"])
                    if urls.get(block["path"])
                    else None,
                    "obligation_ids": [],
                },
            )
            if obligation["id"] not in entry["obligation_ids"]:
                entry["obligation_ids"].append(obligation["id"])
    hashes = {name: digest(text.encode("utf-8")) for name, text in pages.items()}
    manifest = {
        "schema_version": "2",
        "workflow": "documentation_generation",
        "revision": revision,
        "status": status,
        "signature": state["signature"],
        "inputs": pipeline.inputs(state),
        "documentation_path": str(destination),
        "files": hashes,
        "components": {key: state.get(key) for key in records},
        "language_policy": "plain-technical-english-v1",
        "citation_scheme": "compact-source-labels-v2",
        "formal_ste_compliance": "not_claimed",
        "human_review": pipeline.read(state, "release_approval_ref", {"status": "not_performed"}),
        "source_location_dependency": True,
        "limitations": [
            "Model review is not proof of complete semantic preservation",
            "Source links depend on the immutable workspace snapshots",
            "No large-corpus generation acceptance has been established",
        ],
    }
    publish_directory(destination, pages)
    files = {
        key.removesuffix("_ref") + ".json": encode(value) + "\n" for key, value in records.items()
    }
    files["source-accounting.json"] = (
        encode(list(pipeline.rows(state, "content-allocations"))) + "\n"
    )
    files["source-map.json"] = encode(source_map) + "\n"
    files["release-report.md"] = (
        f"# Generation release report\n\nStatus: {status}.\n\n"
        "Language: professional plain English, using the user-authorized simplified policy. "
        "No ASD-STE100 compliance or certification is claimed.\n\n"
        f"Human review: {'recorded' if status == 'complete' else 'not performed'}.\n\n"
        "The original assembled pages are in unpolished_pages.json; editorial changes, "
        "coverage references and independent template/readability checks are in page_reviews.json. "
        "Semantic checks, language findings, Markdown checks and evidence coverage "
        "are recorded separately in validation.json and presentation.json. "
        "Source links require this workspace.\n"
    )
    if metadata.exists() and (metadata / "manifest.json").exists():
        if read_json(metadata / "manifest.json") != manifest:
            raise ValueError("Published manifest differs")
        for name, text in files.items():
            if (metadata / name).read_text(encoding="utf-8") != text:
                raise ValueError("Published metadata changed")
    else:
        publish_directory(metadata, files)
        write_json(metadata / "manifest.json", manifest)
    return str(destination), str(metadata / "manifest.json"), revision
