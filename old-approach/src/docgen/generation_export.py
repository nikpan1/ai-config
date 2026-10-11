import os
import re
import tempfile
from pathlib import Path
from urllib.parse import quote

from docgen.generation_validation import heading_slug, table_specs
from docgen.planning_helpers import validate_paths
from docgen.storage import atomic_write, digest, file_digest, read_json, write_json


def relative_link(source, target):
    return quote(os.path.relpath(target, source.parent).replace("\\", "/"), safe="/.-_#")


def evidence_id(evidence):
    return digest(evidence)[:20]


def citations(evidence, page):
    target = relative_link(Path(page), Path("sources/index.md"))
    unique = {evidence_id(e): e for e in evidence}
    return " ".join(f"[Source {key[:6]}]({target}#source-{key})" for key in unique)


def table_text(text):
    return text.replace("|", "\\|").replace("\n", " ")


def render_fragment(fragment, job, context, page):
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
                    citations(passage["evidence"], page),
                    "",
                ]
            )
        else:
            prefix = labels.get(passage["kind"])
            lines.extend(
                [
                    (f"**{prefix}:** " if prefix else "")
                    + text
                    + " "
                    + citations(passage["evidence"], page),
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
            lines.append(
                "| "
                + " | ".join(
                    table_text(cell["text"]) + " " + citations(cell["evidence"], page)
                    for cell in row["cells"]
                )
                + " |"
            )
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


def assemble(pipeline, state):
    plans = list(pipeline.rows(state, "pages"))
    sections = {r["id"]: r for r in pipeline.rows(state, "logical-sections")}
    jobs = sorted(pipeline.rows(state, "writing-jobs"), key=lambda j: j["assembly_order"])
    fragments = pipeline.read(state, "fragments_ref", {})
    page_by_section = {key: page for page in plans for key in page["section_ids"]}
    by_id = {p["id"]: p for p in plans}
    evidence = {}
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
            level, parent = 2, section["parent_id"]
            while parent and parent in page["section_ids"]:
                level += 1
                parent = sections[parent]["parent_id"]
            lines.extend(["#" * min(level, 6) + " " + section["title"], ""])
            for job in (j for j in jobs if j["section_id"] == key):
                fragment = pipeline.store.get_object(fragments[job["id"]]["fragment_ref"])
                context = pipeline.store.get_object(job["context_ref"])
                lines.extend([render_fragment(fragment, job, context, page["path"]), ""])
                for obligation in context["originals"]["obligations"]:
                    for entry in obligation["evidence"]:
                        evidence[evidence_id(entry)] = entry
                for target in sorted(set(context["brief"]["canonical_links"].values())):
                    canonical_page = page_by_section[target]
                    href = relative_link(Path(page["path"]), Path(canonical_page["path"]))
                    titles = [sections[s]["title"] for s in canonical_page["section_ids"]]
                    if titles.count(sections[target]["title"]) == 1:
                        href += "#" + quote(heading_slug(sections[target]["title"]))
                    lines.extend(
                        [f"See [{sections[target]['title']}]({href}) for the full explanation.", ""]
                    )
                if job["brief_id"] not in rendered_briefs:
                    for diagram in diagrams.get(job["brief_id"], []):
                        lines.extend(
                            [
                                diagram["markdown"],
                                "",
                                "Diagram source: " + citations(diagram["evidence"], page["path"]),
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
        output[page["path"]] = "\n".join(lines).strip() + "\n"
    blocks = {
        b["id"]: b for b in pipeline.store.iter_table(pipeline.planning_inputs(state).blocks_ref)
    }
    assets = pipeline.read(state, "assets_ref", [])
    sources = {a["path"]: a for a in assets if a["kind"] == "source"}
    source_lines = []
    for key, entry in sorted(evidence.items()):
        block = blocks[entry["block_id"]]
        target = relative_link(
            pipeline.output_root(state) / "sources/index.md", Path(sources[block["path"]]["target"])
        )
        source_lines.extend(
            [
                f"## Source {key}",
                "",
                f"[{block['path']}]({target}) — lines {block['line_start']}–{block['line_end']}. "
                f"Block: `{block['id']}`.",
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
    source_lines.extend(
        ["## Source accounting", "", "| Obligation | Disposition | Reason |", "| --- | --- | --- |"]
    )
    for allocation in pipeline.rows(state, "content-allocations"):
        source_lines.append(
            f"| `{allocation['obligation_id']}` | {allocation['disposition']} | "
            f"{table_text(allocation['reason'])} |"
        )
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
    os.replace(temporary, destination)


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
            "presentation_ref",
            "decisions_ref",
        )
    }
    hashes = {name: digest(text.encode("utf-8")) for name, text in pages.items()}
    manifest = {
        "schema_version": "1",
        "workflow": "documentation_generation",
        "revision": revision,
        "status": status,
        "signature": state["signature"],
        "inputs": pipeline.inputs(state),
        "documentation_path": str(destination),
        "files": hashes,
        "components": {key: state.get(key) for key in records},
        "language_policy": "plain-technical-english-v1",
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
