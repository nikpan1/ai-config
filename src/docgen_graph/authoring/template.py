import re

from markdown_it import MarkdownIt

from docgen_graph.documentation_contracts import HeadingNode
from docgen_graph.storage import digest


def heading_tree(text: str) -> list[dict]:
    tokens = MarkdownIt().parse(text)
    nodes, parents, numbers = [], {}, set()
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        level = int(token.tag[1:])
        title = tokens[index + 1].content
        number = re.match(r"^(\d+(?:\.\d+)*)(?:\.)?\s+", title)
        prefix = number[1] if number else ""
        placeholder = bool(re.search(r"\[[^]]+\]|\{[^}]+\}", title))
        if prefix and prefix in numbers and not placeholder:
            raise ValueError(f"Duplicate fixed template number: {prefix}")
        numbers.add(prefix)
        parent = next((parents[key] for key in sorted(parents, reverse=True) if key < level), None)
        if prefix and parent and parent["number"] and not prefix.startswith(parent["number"] + "."):
            raise ValueError(f"Template number {prefix} conflicts with parent {parent['number']}")
        optional = bool(re.search(r"\boptional\b", title, re.I))
        node = HeadingNode(
            section_id="section-" + digest([len(nodes), level])[:12],
            parent_id=parent["section_id"] if parent else "",
            level=level,
            title=title,
            number=prefix,
            placeholder=placeholder,
            required=not optional,
            order=len(nodes),
            minimum=0 if optional else 1,
            maximum=100 if placeholder else 1,
        ).model_dump()
        parents = {key: value for key, value in parents.items() if key < level}
        parents[level] = node
        nodes.append(node)
    return nodes


def number_generated_headings(markdown: str, parent_number: str, fixed_titles: list[str]) -> str:
    if not parent_number:
        return markdown
    tokens = MarkdownIt().parse(markdown)
    lines = markdown.splitlines()
    fixed = {
        node["title"]: node["number"]
        for node in heading_tree("\n".join("### " + value for value in fixed_titles))
    }
    used = [
        int(value.rsplit(".", 1)[-1])
        for value in fixed.values()
        if value.startswith(parent_number + ".")
    ]
    counter = max(used, default=0)
    parents = {2: parent_number}
    counters = {}
    links = {}
    for index, token in enumerate(tokens):
        if token.type != "heading_open" or int(token.tag[1:]) < 3:
            continue
        level = int(token.tag[1:])
        title = tokens[index + 1].content
        if title in fixed:
            number = fixed[title]
        else:
            parent = parents.get(level - 1, parent_number)
            if level == 3:
                counter += 1
                number = f"{parent}.{counter}"
            else:
                counters[parent] = counters.get(parent, 0) + 1
                number = f"{parent}.{counters[parent]}"
            plain = re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", title)
            lines[token.map[0]] = "#" * level + f" {number} {plain}"
            old_anchor = re.sub(r"[^\w -]", "", title.lower()).replace(" ", "-")
            new_anchor = re.sub(r"[^\w -]", "", f"{number} {plain}".lower()).replace(" ", "-")
            links[old_anchor] = new_anchor
        parents[level] = number
    code_lines = {
        line
        for token in tokens
        if token.type in {"fence", "code_block"}
        for line in range(*token.map)
    }
    for index, line in enumerate(lines):
        if index not in code_lines:
            lines[index] = re.sub(
                r"\]\(#([^)]+)\)", lambda match: "](#" + links.get(match[1], match[1]) + ")", line
            )
    return "\n".join(lines)


def document_title(proposed: str, template: str, brief: str) -> str:
    titles = [
        node["title"]
        for node in heading_tree(template)
        if node["level"] == 1 and not node["placeholder"]
    ]
    if titles:
        return titles[0]
    working = re.search(
        r"^(?:documentation|document|draft|working|implementation|development)\s+plan\b"
        r"|^plan(?:\s+(?:dokumentacji|roboczy|wdrożenia))?$"
        r"|^plan for (?:documentation|document|writing)\b|^planning artifact\b",
        proposed.strip(),
        re.I,
    )
    if not working:
        return proposed
    return (
        "Product documentation"
        if not brief.strip()
        else re.sub(r"\s+", " ", brief.strip()).rstrip(".")[:120]
    )


def bind_plan_sections(tree: list[dict], sections: list[dict], omitted_titles=()) -> list[dict]:
    headings = [node for node in tree if node["level"] == 2]
    result, position = [], 0
    for index, heading in enumerate(headings):
        if not heading["placeholder"]:
            if position < len(sections) and sections[position]["title"] == heading["title"]:
                result.append({**sections[position], "section_id": heading["section_id"]})
                position += 1
            elif heading["required"] and heading["title"] not in omitted_titles:
                raise ValueError(f"Missing fixed template heading: {heading['title']}")
            continue
        following = next(
            (node["title"] for node in headings[index + 1 :] if not node["placeholder"]), None
        )
        count = 0
        while position < len(sections) and sections[position]["title"] != following:
            section = dict(sections[position])
            title = section["title"]
            if "[" in title or "{" in title:
                raise ValueError("A template placeholder needs a concrete reader heading")
            count += 1
            if count > heading["maximum"]:
                raise ValueError("Template slot cardinality exceeded")
            section["section_id"] = f"{heading['section_id']}-{count}"
            if heading["number"]:
                prefix, _, last = heading["number"].rpartition(".")
                number = str(int(last) + count - 1)
                number = prefix + "." + number if prefix else number
                plain = re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", title)
                section["title"] = f"{number} {plain}"
            result.append(section)
            position += 1
        if count < heading["minimum"]:
            raise ValueError("A required template slot was not populated")
    if position != len(sections):
        raise ValueError("Generated section is outside the template slots")
    numbers = [re.match(r"^(\d+(?:\.\d+)*)\.?\s", item["title"]) for item in result]
    values = [item[1] for item in numbers if item]
    if len(values) != len(set(values)):
        raise ValueError("Generated numbering conflicts with a fixed template number")
    return result
