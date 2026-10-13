import html
import re
from collections import defaultdict
from difflib import SequenceMatcher

from markdown_it import MarkdownIt

from docgen_graph.assets import asset_filename, image_references, meaningful_alt
from docgen_graph.authoring.template import bind_plan_sections, heading_tree
from docgen_graph.contracts import ContentUnit, PresentationPlacement, TemplateRequirement
from docgen_graph.presentation import business_prose_findings, exact_support, mapping_occurrences
from docgen_graph.source_links import CITATION_GROUP, citation_labels
from docgen_graph.storage import digest


def compile_requirements(text: str, template_hash: str) -> dict:
    requirements = []
    section = "__document__"
    headings = []
    optional = False
    instruction_block = False
    lines = text.splitlines()
    tokens = MarkdownIt().parse(text)
    heading_lines = {
        token.map[0]: (int(token.tag[1:]), tokens[index + 1].content)
        for index, token in enumerate(tokens)
        if token.type == "heading_open"
    }
    code_lines = {
        line
        for token in tokens
        if token.type in {"fence", "code_block"}
        for line in range(*token.map)
    }

    def add(kind, value, order, columns=None, required=True):
        requirements.append(
            TemplateRequirement(
                id=digest([template_hash, order, kind])[:16],
                kind=kind,
                section=section,
                text=value,
                order=order,
                columns=columns or [],
                required=required and not optional,
            ).model_dump()
        )

    for index, line in enumerate(lines):
        value = line.strip()
        if index in code_lines:
            if value == "```mermaid" and section != "__document__":
                add("flow", "Source-backed primary flow with text alternative", index)
            continue
        if not value:
            continue
        heading = heading_lines.get(index)
        if heading and heading[0] >= 2:
            title = heading[1]
            if section == "__document__" and heading[0] > 2:
                add("style", title, index, required=False)
                continue
            if heading[0] == 2:
                section = title
                headings.append(title)
                optional = bool(re.search(r"\boptional\b", title, re.I))
            else:
                optional = "optional" in title.casefold()
            if "[" not in title:
                add("heading", title, index)
            else:
                add("conditional" if optional else "style", title, index, required=False)
        elif (
            value.startswith("|")
            and index + 1 < len(lines)
            and re.fullmatch(r"[\s|:\-]+", lines[index + 1])
        ):
            columns = [cell.strip() for cell in value.strip("|").split("|")]
            add("metadata" if section == "__document__" else "table", value, index, columns)
            if section == "__document__":
                rows = []
                for row in lines[index + 2 :]:
                    if not row.strip().startswith("|"):
                        break
                    rows.append(row.strip().strip("|").split("|")[0].strip())
                requirements[-1]["rows"] = rows
        elif value.startswith(">"):
            if index == 0 or not lines[index - 1].strip().startswith(">"):
                instruction_block = False
            label = re.search(r"\*\*(.+?)\*\*", value)
            instruction = label and re.search(
                r"instruction|contract|check|cross-reference|preview image|goal", label[1], re.I
            )
            instruction_block = instruction_block or bool(instruction)
            if label and not instruction_block and "purpose" not in label[1].casefold():
                add("callout", label[1].rstrip(":"), index)
            elif value not in {">", "> "}:
                add("style", value, index)
        elif value.startswith("[") and value.endswith("]"):
            kind = (
                "conditional" if re.search(r"\b(?:if|only|optional)\b", value, re.I) else "purpose"
            )
            add(kind, value[1:-1], index)
        elif value.startswith("**"):
            add("style", value, index)
        elif not value.startswith(("---", "<", "</", "|")):
            add("style", value, index, required=False)
    return {
        "schema_version": 2,
        "hash": template_hash,
        "headings": headings,
        "text": text,
        "requirements": requirements,
        "heading_tree": heading_tree(text),
    }


def bounded_fact_groups(facts: list[dict], spans: dict) -> list[list[dict]]:
    groups, current = [], []
    evidence_ids = set()
    for fact in facts:
        combined = evidence_ids | set(fact["evidence_ids"])
        size = sum(len(spans[key]["text"]) for key in combined)
        if current and (len(current) >= 12 or size > 18000):
            groups.append(current)
            current, evidence_ids = [], set()
        current.append(fact)
        evidence_ids.update(fact["evidence_ids"])
    if current:
        groups.append(current)
    return groups


def content_groups(assertions: list[dict], spans: dict) -> list[dict]:
    grouped = defaultdict(list)
    for assertion in assertions:
        subject = assertion["subject"].strip().casefold()
        if subject in {"unspecified", "system", "the system"}:
            subject = "source statements"
        grouped[(subject, assertion["predicate"].strip().casefold())].append(assertion)
    result = []
    for key, items in grouped.items():
        partitions = defaultdict(list)
        for item in items:
            scope = item["scope"] if len(items) > 12 else "all variants"
            partitions[scope].append(item)
        scoped_groups = [
            (scope, group)
            for scope, variants in partitions.items()
            for group in bounded_fact_groups(variants, spans)
        ]
        for scope, variants in scoped_groups:
            evidence_ids = sorted({e for item in variants for e in item["evidence_ids"]})
            result.append(
                {
                    "id": digest([key, scope, [item["id"] for item in variants]])[:16],
                    "topic": " / ".join(key),
                    "kind": spans[evidence_ids[0]]["kind"],
                    "source": spans[evidence_ids[0]]["path"],
                    "obligation_ids": [item["id"] for item in variants],
                    "examples": [item["statement"] for item in variants[:2]],
                    "facts": [
                        {
                            name: item[name]
                            for name in (
                                "id",
                                "statement",
                                "scope",
                                "conditions",
                                "exceptions",
                                "modality",
                                "evidence_ids",
                            )
                        }
                        for item in variants
                    ],
                }
            )
    return result


def content_units(groups: list[dict], sections: list[dict]) -> list[dict]:
    owners = {key: section["title"] for section in sections for key in section["group_ids"]}
    units = []
    for group in groups:
        facts = group["facts"]
        equivalents = defaultdict(list)
        for fact in facts:
            signature = {
                key: value for key, value in fact.items() if key not in {"id", "evidence_ids"}
            }
            equivalents[digest(signature)].append(fact)
        common = [
            {
                "statement": records[0]["statement"],
                "obligation_ids": [item["id"] for item in records],
                "scope": records[0]["scope"],
                "conditions": records[0]["conditions"],
                "exceptions": records[0]["exceptions"],
                "modality": records[0]["modality"],
            }
            for records in equivalents.values()
            if len(records) > 1
        ]
        units.append(
            ContentUnit(
                id=group["id"],
                topic=group["topic"],
                canonical_section=owners.get(group["id"], ""),
                obligation_ids=group["obligation_ids"],
                common_facts=common,
                scoped_variants=facts,
                conditions=sorted({value for item in facts for value in item["conditions"]}),
                exceptions=sorted({value for item in facts for value in item["exceptions"]}),
                evidence_ids=sorted({value for item in facts for value in item["evidence_ids"]}),
            ).model_dump()
        )
    return units


def duplicate_risks(units: list[dict]) -> list[dict]:
    risks = []
    facts = [(unit, fact) for unit in units for fact in unit["scoped_variants"]]
    for index, (unit, fact) in enumerate(facts):
        for other, candidate in facts[index + 1 :]:
            if unit["id"] == other["id"]:
                continue
            left, right = fact["statement"].casefold(), candidate["statement"].casefold()
            if abs(len(left) - len(right)) > max(len(left), len(right)) * 0.2:
                continue
            if SequenceMatcher(None, left, right).ratio() >= 0.9:
                risks.append(
                    {
                        "obligation_ids": [fact["id"], candidate["id"]],
                        "sections": [unit["canonical_section"], other["canonical_section"]],
                        "disposition": "Retain distinct scope and qualifiers; review overlap",
                    }
                )
    return risks


def safe_label(value: str) -> bool:
    return bool(value.strip()) and len(value) <= 180 and not re.search(r'[<>"`{}|;\\\n\r]', value)


def diagram_source(diagram: dict) -> str:
    nodes, edges, kind = diagram["nodes"], diagram["edges"], diagram["kind"]
    lines = ["flowchart LR" if kind == "flowchart" else kind]
    for node in nodes:
        identifier, label = node["id"], node["label"]
        if kind == "flowchart":
            lines.append(f'    {identifier}["{label}"]')
        elif kind == "stateDiagram-v2":
            lines.append(f'    state "{label}" as {identifier}')
        else:
            lines.append(f"    participant {identifier} as {label}")
    for edge in edges:
        source, target, label = edge["source"], edge["target"], edge["label"]
        if kind == "flowchart":
            lines.append(f'    {source} -->|"{label}"| {target}')
        elif kind == "stateDiagram-v2":
            lines.append(f"    {source} --> {target}: {label}")
        else:
            lines.append(f"    {source}->>{target}: {label}")
    return "\n".join(lines)


def validate_diagram(diagram: dict, evidence_ids: set[str]) -> list[str]:
    findings = []
    nodes, edges = diagram["nodes"], diagram["edges"]
    identifiers = [item["id"] for item in nodes + edges]
    if len(identifiers) != len(set(identifiers)) or any(
        not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,39}", item) or item in {"end", "state"}
        for item in identifiers
    ):
        findings.append("Diagram has invalid or duplicate element identifiers")
    if not 2 <= len(nodes) <= 16 or not 1 <= len(edges) <= 24:
        findings.append("Diagram exceeds bounded node/edge limits")
    node_ids = {node["id"] for node in nodes}
    for item in nodes + edges:
        if not safe_label(item["label"]):
            findings.append("Diagram contains unsafe labels")
        if not item["evidence_ids"] or not set(item["evidence_ids"]).issubset(evidence_ids):
            findings.append(f"Diagram element lacks original evidence: {item['id']}")
    for edge in edges:
        if edge["source"] not in node_ids or edge["target"] not in node_ids:
            findings.append("Diagram transition references an unknown node")
    if diagram.get("source") and diagram["source"] != diagram_source(diagram):
        findings.append("Mermaid source differs from validated diagram elements")
    if not diagram["question"].strip() or not diagram["description"].strip():
        findings.append("Diagram needs a reader question and text alternative")
    return findings


def visual_evidence_ids(visuals: list[dict]) -> set[str]:
    return {key for visual in visuals for key in visual["evidence_ids"]} | {
        key
        for visual in visuals
        if visual.get("diagram")
        for item in visual["diagram"]["nodes"] + visual["diagram"]["edges"]
        for key in item["evidence_ids"]
    }


def diagram_element_ids(visuals: list[dict]) -> set[str]:
    return {
        f"{visual['id']}:{item['id']}"
        for visual in visuals
        if visual.get("diagram")
        for item in visual["diagram"]["nodes"] + visual["diagram"]["edges"]
    }


def validate_quality_plan(plan: dict, contract: dict, assets: list[dict], spans: dict) -> list[str]:
    findings = []
    if re.search(r"\b(?:documentation plan|planning artifact)\b", plan["title"], re.I):
        findings.append("Release title must describe the system, not a documentation plan")
    titles = [section["title"] for section in plan["sections"]]
    omitted = {
        item["requirement_id"]
        for item in plan.get("template_decisions", [])
        if item["disposition"] == "inapplicable"
    }
    required_titles = {
        item["text"]
        for item in contract["requirements"]
        if item["kind"] == "heading"
        and item["text"] == item["section"]
        and item["required"]
        and item["id"] not in omitted
    }
    if contract.get("heading_tree"):
        try:
            bind_plan_sections(
                contract["heading_tree"],
                plan["sections"],
                [item["text"] for item in contract["requirements"] if item["id"] in omitted],
            )
        except ValueError as error:
            findings.append(str(error))
    elif [title for title in contract["headings"] if title in titles] != titles:
        findings.append("Plan must retain required heading order")
    if not required_titles.issubset(titles):
        findings.append("Plan must retain required heading order")
    requirements = {item["id"]: item for item in contract["requirements"]}
    decisions = plan.get("template_decisions", [])
    if len({item["requirement_id"] for item in decisions}) != len(decisions):
        findings.append("Template requirement has multiple decisions")
    for decision in decisions:
        if decision["requirement_id"] not in requirements:
            findings.append("Unknown template requirement decision")
        if decision["disposition"] == "inapplicable" and not decision["reason"].strip():
            findings.append("Inapplicable template requirement needs a reviewable reason")
        if not set(decision["evidence_ids"]).issubset(spans):
            findings.append("Template decision references unknown evidence")
    omitted = {
        item["requirement_id"] for item in decisions if item["disposition"] == "inapplicable"
    }
    by_hash = {item["hash"]: item for item in assets if item["hash"]}
    asset_decisions = {item["path"]: item["reason"] for item in plan.get("asset_decisions", [])}
    for path in asset_decisions:
        if path not in {asset["path"] for asset in assets}:
            findings.append("Unknown asset omission decision")
    for asset in assets:
        if (
            asset["references"]
            and asset["disposition"] == "rejected"
            and asset["path"] not in asset_decisions
        ):
            findings.append(
                f"Rejected source asset needs explicit omission review: {asset['path']}"
            )
    seen_images, seen_visuals = set(), set()
    for section in plan["sections"]:
        for visual in section.get("visuals", []):
            for key in visual_evidence_ids([visual]):
                if key in spans and len(spans[key]["text"]) > 1000:
                    if key not in visual.get("support_quotes", {}) and not any(
                        item["evidence_id"] == key for item in visual.get("support_locations", [])
                    ):
                        findings.append(f"Visual needs precise support within evidence: {key}")
            if visual.get("diagram"):
                findings.extend(
                    business_prose_findings(
                        "```mermaid\n"
                        + diagram_source(visual["diagram"])
                        + "\n```\n"
                        + visual["diagram"]["description"],
                        contract.get("text", ""),
                    )
                )
            for key, quote in visual.get("support_quotes", {}).items():
                if key not in spans:
                    findings.append(f"Visual quote references unknown evidence: {key}")
                    continue
                try:
                    exact_support({**spans[key], "label": key}, quote)
                except ValueError as error:
                    findings.append(str(error))
        visuals = section.get("visuals", [])
        if sum(visual["kind"] == "diagram" for visual in visuals) > 1:
            findings.append("At most one primary diagram per section is supported")
        for visual in visuals:
            if visual["id"] in seen_visuals or visual["section"] != section["title"]:
                findings.append("Visual identifier or section placement is invalid")
            seen_visuals.add(visual["id"])
            if not visual["purpose"].strip():
                findings.append("Visual needs a reader purpose")
            if not set(visual["evidence_ids"]).issubset(spans):
                findings.append("Visual references unknown evidence")
            if visual["kind"] == "diagram":
                if not visual.get("diagram"):
                    findings.append("Diagram placement lacks a specification")
                else:
                    findings.extend(validate_diagram(visual["diagram"], set(spans)))
            else:
                asset = by_hash.get(visual["asset_hash"])
                if not asset or asset["disposition"] != "referenced":
                    findings.append("Selected image is unsafe, unknown, or unreferenced")
                    continue
                if visual["asset_hash"] in seen_images:
                    findings.append("An image may have only one reader placement")
                seen_images.add(visual["asset_hash"])
                allowed = {
                    ref["alt"]
                    for item in assets
                    if item["hash"] == asset["hash"]
                    for ref in item["references"]
                    if meaningful_alt(ref["alt"])
                }
                if visual["text_alternative"] not in allowed:
                    findings.append("Image needs meaningful source-provided alternative text")
                supported = {
                    key
                    for item in assets
                    if item["hash"] == asset["hash"]
                    for ref in item["references"]
                    for key in ref.get("evidence_ids", [])
                }
                if not visual["evidence_ids"] or not set(visual["evidence_ids"]).issubset(
                    supported
                ):
                    findings.append("Image placement lacks its source reference evidence")
        for requirement in contract["requirements"]:
            if (
                requirement["section"] == section["title"]
                and requirement["kind"] == "flow"
                and requirement["required"]
                and requirement["id"] not in omitted
                and not any(visual["kind"] == "diagram" for visual in visuals)
            ):
                findings.append("Required primary flow needs a diagram or reviewed inapplicability")
    return findings


def render_visuals(visuals: list[dict], assets: list[dict], evidence: list[dict]) -> str:
    labels = {item["id"]: item["label"] for item in evidence}
    by_hash = {asset["hash"]: asset for asset in assets}
    blocks = []
    for visual in visuals:
        cited = " ".join(
            f"[{'Code' if labels[key].startswith('C') else 'Legacy'} {labels[key]}]"
            for key in sorted(visual_evidence_ids([visual]))
        )
        if visual["kind"] == "image":
            asset = by_hash[visual["asset_hash"]]
            alt = visual["text_alternative"].replace("[", "\\[").replace("]", "\\]")
            content = f"![{alt}](assets/{asset_filename(asset)})"
            title = visual["purpose"]
        else:
            diagram = visual["diagram"]
            content = f"```mermaid\n{diagram_source(diagram)}\n```"
            title = diagram["description"]
        blocks.append(
            "<table>\n  <tr>\n    <td>\n\n"
            + content
            + '\n\n</td>\n  </tr>\n  <tr>\n    <td style="text-align: center;">\n'
            + f"      <strong>{html.escape(title)}</strong>\n"
            + "    </td>\n  </tr>\n</table>\n\n"
            + cited
        )
    return "\n\n".join(blocks)


def position_visuals(markdown: str, visuals: list[dict], assets: list, evidence: list) -> str:
    for visual in visuals:
        title = visual.get("subsection")
        if not title:
            continue
        block = render_visuals([visual], assets, evidence)
        if block not in markdown:
            continue
        heading = re.search(rf"^(###)\s+{re.escape(title)}\s*$", markdown, re.M)
        if not heading:
            continue
        markdown = markdown.replace(block, "", 1)
        heading = re.search(rf"^###\s+{re.escape(title)}\s*$", markdown, re.M)
        following = re.search(r"^#{1,3}\s+", markdown[heading.end() :], re.M)
        end = heading.end() + following.start() if following else len(markdown)
        markdown = markdown[:end].rstrip() + "\n\n" + block + "\n\n" + markdown[end:]
    return markdown.strip()


def placement_records(
    title: str, markdown: str, mappings: list[dict], assertions: dict, evidence: dict
) -> tuple[list[dict], list[str]]:
    findings, placements = [], {}
    identifiers = [item["obligation_id"] for item in mappings]
    if len(identifiers) != len(set(identifiers)):
        findings.append("Invalid or duplicate obligation mapping")
    seen = set()
    for mapping in mapping_occurrences(mappings):
        identifier = mapping["obligation_id"]
        occurrence = (identifier, mapping["passage"])
        if identifier not in assertions or occurrence in seen:
            findings.append("Invalid or duplicate obligation mapping")
            continue
        seen.add(occurrence)
        if mapping.get("disposition") == "out_of_scope":
            if mapping["passage"] or not mapping.get("scope_reason", "").strip():
                findings.append(
                    f"Excluded fact needs an empty passage and scope reason: {identifier}"
                )
            continue
        passage = mapping["passage"]
        if not passage.strip():
            findings.append(f"Documented fact needs a reader passage: {identifier}")
            continue
        start = markdown.find(passage)
        if start < 0 or markdown.count(passage) != 1:
            findings.append(f"Mapped passage is absent or ambiguous: {identifier}")
            continue
        if not set(mapping["citation_ids"]).issubset(citation_labels(passage)):
            findings.append(f"Mapped passage lacks its local citations: {identifier}")
        supported = {evidence[key]["label"] for key in assertions[identifier]["evidence_ids"]}
        if not mapping["citation_ids"] or not set(mapping["citation_ids"]).issubset(supported):
            findings.append(f"Mapping {identifier} may cite only {sorted(supported)}")
        key = digest([title, start, passage])[:20]
        placement = placements.setdefault(
            key,
            PresentationPlacement(
                id=key,
                section=title,
                passage=passage,
                start=start,
                end=start + len(passage),
                kind="table_row"
                if passage.lstrip().startswith("|")
                else "list_item"
                if re.match(r"^\s*(?:[-*]|\d+\.) ", passage)
                else "paragraph",
                obligation_ids=[identifier],
                citation_ids=mapping["citation_ids"],
            ).model_dump(),
        )
        placement["obligation_ids"] = sorted(set(placement["obligation_ids"]) | {identifier})
        placement["citation_ids"] = sorted(
            set(placement["citation_ids"]) | set(mapping["citation_ids"])
        )
    for placement in placements.values():
        if set(citation_labels(placement["passage"])) != set(placement["citation_ids"]):
            findings.append("Placement includes citations without corresponding fact mappings")
    return list(placements.values()), findings


def validate_template_output(
    sections: list[dict], contract: dict, decisions: list[dict]
) -> list[str]:
    findings = []
    omitted = {
        item["requirement_id"] for item in decisions if item["disposition"] == "inapplicable"
    }
    by_title = {section["title"]: section["markdown"] for section in sections}
    omitted_sections = {
        item["section"]
        for item in contract["requirements"]
        if item["kind"] == "heading"
        and item["text"] == item["section"]
        and item["id"] in omitted
        and item["section"] not in by_title
    }
    for requirement in contract["requirements"]:
        if not requirement["required"] or requirement["id"] in omitted:
            continue
        section, kind = requirement["section"], requirement["kind"]
        if section == "__document__":
            for title, body in by_title.items():
                if kind == "metadata" and any(
                    [cell.strip().casefold() for cell in line.strip().strip("|").split("|")]
                    == [column.casefold() for column in requirement["columns"]]
                    for line in body.splitlines()
                    if line.lstrip().startswith("|")
                ):
                    findings.append(f"Document metadata belongs in the export header: {title}")
                if (
                    kind == "style"
                    and re.search(r"\bbracketed\b|\breplace.+\bprompt", requirement["text"], re.I)
                    and requirement["text"] in body
                ):
                    findings.append(f"Copied template instructions in reader prose: {title}")
            continue
        if section in omitted_sections:
            continue
        text = by_title.get(section, "")
        present = True
        if kind == "heading":
            present = requirement["text"] == section or bool(
                re.search(rf"^###\s+{re.escape(requirement['text'])}\s*$", text, re.M)
            )
        elif kind == "table":
            headers = [
                [cell.strip().casefold() for cell in line.strip().strip("|").split("|")]
                for line in text.splitlines()
                if line.lstrip().startswith("|")
            ]
            present = [column.casefold() for column in requirement["columns"]] in headers
        elif kind == "callout":
            present = bool(re.search(rf"^>.*{re.escape(requirement['text'])}", text, re.M | re.I))
        elif kind == "flow":
            present = "```mermaid\n" in text
        if not present:
            findings.append(f"Missing template {kind}: {requirement['text']} in {section}")
    return findings


def reading_text(markdown: str) -> str:
    value = re.sub(r"\]\((?:<[^>\n]*>|[^)\n]*)\)", "]", markdown)
    value = CITATION_GROUP.sub("", value)
    return re.sub(r"[#*`>|]", " ", value)


def section_anchor(title: str) -> str:
    return re.sub(r"[^\w -]", "", title.lower()).replace(" ", "-")


def repetition_report(sections: list[dict]) -> dict:
    occurrences = defaultdict(list)
    candidates = []
    for section in sections:
        for paragraph in section["markdown"].split("\n\n"):
            text = " ".join(reading_text(paragraph).casefold().split())
            if len(text.split()) >= 18 and not paragraph.lstrip().startswith(("|", "```", "#")):
                occurrences[text].append(section["title"])
            if len(text.split()) >= 8 and not paragraph.lstrip().startswith(("```", "#")):
                candidates.append((section["title"], text))
    repeated = [
        {"text": text, "sections": titles}
        for text, titles in occurrences.items()
        if len(titles) > 1
    ]
    return {
        "reader_words": sum(len(reading_text(s["markdown"]).split()) for s in sections),
        "duplicate_paragraphs": repeated,
        "semantic_candidates": [
            {
                "sections": [title, other_title],
                "passages": [text, other],
                "action": "Compare scope, roles and qualifiers before merging; preserve evidence",
            }
            for index, (title, text) in enumerate(candidates)
            for other_title, other in candidates[index + 1 :]
            if title != other_title
            and text != other
            and SequenceMatcher(None, text, other).ratio() >= 0.88
        ],
        "redundant_explanations": "Requires reader assessment; not inferred from word count",
    }


def validate_visual_output(
    markdown: str, visuals: list[dict], assets: list[dict], evidence: list[dict]
) -> list[str]:
    expected = render_visuals(visuals, assets, evidence)
    actual_images = image_references(markdown)
    expected_images = image_references(expected)
    actual = [(item["target"], item["alt"]) for item in actual_images]
    required = [(item["target"], item["alt"]) for item in expected_images]
    findings = []
    if actual != required or any(item.get("finding") for item in actual_images):
        findings.append("Images differ from approved placements")
    diagrams = re.findall(r"```mermaid\s*\n(.*?)\n```", markdown, re.S)
    approved = [diagram_source(visual["diagram"]) for visual in visuals if visual.get("diagram")]
    if diagrams != approved:
        findings.append("Mermaid differs from approved evidence-mapped specifications")
    for visual in visuals:
        block = render_visuals([visual], assets, evidence)
        table = block.partition("</table>")[0] + "</table>"
        if table not in markdown:
            findings.append("Visual must retain its two-row table and centered bold title")
    return findings
