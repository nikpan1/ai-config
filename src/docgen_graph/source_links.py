import html
import re
from functools import lru_cache
from html.parser import HTMLParser
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from markdown_it import MarkdownIt

CITATION_GROUP = re.compile(
    r"\[(Code|Legacy) ((?:(?:Code|Legacy) )?[CD]\d+)(?:,\s*(?:(?:Code|Legacy) )?[CD]\d+)*\]"
)


def citation_labels(markdown: str) -> list[str]:
    return [
        label
        for match in CITATION_GROUP.finditer(markdown)
        for label in re.findall(r"[CD]\d+", match.group())
    ]


def normalize_citation_syntax(markdown: str) -> str:
    pattern = (
        CITATION_GROUP.pattern
        + r"|```[\s\S]*?```|`[^`\n]*`|(?P<short>\[[CD]\d+\])(?!\()"
        + r"|(?P<bare>\b(?:Legacy|Code)\s+[CD]\d+\b)"
    )
    return re.sub(
        pattern,
        lambda match: (
            f"[{match['bare']}]"
            if match["bare"]
            else f"[{'Code' if match['short'][1] == 'C' else 'Legacy'} {match['short'][1:-1]}]"
            if match["short"]
            else match.group()
        ),
        markdown,
    )


def normalize_section_links(markdown: str, section_targets: dict[str, str]) -> str:
    targets = {title.casefold(): href for title, href in section_targets.items()}
    pattern = (
        r"```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]*`|"
        r"(?<!!)\[(?P<label>[^\]\n]+)\]\((?P<target>[^)\n]+)\)"
    )

    def replace(match: re.Match) -> str:
        if match["target"] is None:
            return match.group()
        target = unquote(match["target"].strip().strip("<>")).removeprefix("#")
        href = targets.get(target.casefold())
        return f"[{match['label']}]({href})" if href else match.group()

    return re.sub(pattern, replace, markdown)


def link_citations(markdown: str, direct_links: dict[str, str]) -> str:
    def replace(match: re.Match) -> str:
        if markdown[match.end() :].startswith("("):
            return match.group()
        kind = match.group(1)
        labels = re.findall(r"[CD]\d+", match.group())
        return " ".join(
            f"[{kind} {label}](<{direct_links.get(label) or f'../evidence/{label}.md'}>)"
            for label in labels
        )

    return CITATION_GROUP.sub(replace, markdown)


def source_url_from_markdown(markdown: str) -> str | None:
    lines = markdown.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, separator, value = line.partition(":")
        if separator and key.strip() == "source_url":
            candidate = value.strip().strip("\"'")
            parsed = urlsplit(candidate)
            if (
                parsed.scheme in {"http", "https"}
                and parsed.netloc
                and not any(character.isspace() for character in candidate)
                and ":~:" not in parsed.fragment
            ):
                return candidate
            return None
    return None


class _VisibleHtml(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0
        self.stack = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        concealed = (
            tag in {"script", "style", "template", "svg"}
            or "hidden" in attributes
            or attributes.get("aria-hidden") == "true"
        )
        if tag not in {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }:
            self.stack.append((tag, concealed))
            self.hidden += int(concealed)
        if not self.hidden and tag in {
            "p",
            "div",
            "td",
            "th",
            "tr",
            "li",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "br",
        }:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                self.hidden -= sum(int(hidden) for _, hidden in self.stack[index:])
                del self.stack[index:]
                break
        if not self.hidden and tag in {"p", "div", "td", "th", "tr", "li"}:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def visible_html_text(source: str) -> str:
    parser = _VisibleHtml()
    parser.feed(source)
    return " ".join(html.unescape("".join(parser.parts)).split())


@lru_cache(maxsize=16)
def visible_segments(markdown: str) -> list[dict]:
    lines = markdown.splitlines()
    offset = 0
    if lines and lines[0].strip() == "---":
        for index, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                offset = index + 1
                break
    parser = MarkdownIt("commonmark").enable("table")
    segments = []
    for token in parser.parse("\n".join(lines[offset:])):
        if token.type != "inline":
            continue
        parts = []
        for child in token.children or []:
            if child.type in {"text", "code_inline"}:
                parts.append(child.content)
            elif child.type in {"softbreak", "hardbreak"}:
                parts.append(" ")
        value = " ".join(html.unescape("".join(parts)).split())
        if value:
            mapping = token.map or [0, 0]
            segments.append(
                {
                    "text": value,
                    "start_line": mapping[0] + offset + 1,
                    "end_line": mapping[1] + offset,
                }
            )
    return segments


def _encoded(value: str) -> str:
    return quote(value, safe="").replace("-", "%2D")


@lru_cache(maxsize=4)
def _phrase_locations(page_text: str) -> dict[str, list[int]]:
    words = list(re.finditer(r"\w+(?:[’']\w+)*", page_text, re.UNICODE))
    locations = {}
    for first, word in enumerate(words):
        for last in range(first + 2, min(first + 12, len(words)) + 1):
            phrase = page_text[word.start() : words[last - 1].end()]
            locations.setdefault(phrase, []).append(word.start())
    return locations


def select_text_fragment(
    excerpt: str,
    page_markdown: str | None = None,
    support_quote: str | None = None,
    destination_text: str | None = None,
    claim: str | None = None,
) -> dict:
    full_segments = visible_segments(page_markdown or excerpt)
    segments = full_segments
    if page_markdown:
        excerpt_lines = excerpt.splitlines()
        page_lines = page_markdown.splitlines()
        line = next(
            (
                index + 1
                for index in range(len(page_lines))
                if page_lines[index : index + len(excerpt_lines)] == excerpt_lines
            ),
            None,
        )
        if line is not None:
            segments = [
                item
                for item in segments
                if line <= item["start_line"] <= line + len(excerpt_lines) - 1
            ]
        else:
            local = {item["text"] for item in visible_segments(excerpt)}
            segments = [
                item
                for item in segments
                if any(text in item["text"] or item["text"] in text for text in local)
            ]
    if support_quote:
        projected_quote = " ".join(item["text"] for item in visible_segments(support_quote))
        normalized_quote = projected_quote or " ".join(html.unescape(support_quote).split())
        if support_quote not in excerpt and not any(
            normalized_quote in item["text"] for item in segments
        ):
            return {
                "status": "fallback",
                "reason": "Support quote is absent from the immutable source range",
            }
        segments = [item for item in segments if normalized_quote in item["text"]]
    page_text = destination_text or "\n".join(
        item["text"] for item in visible_segments(page_markdown or excerpt)
    )
    page_text = " ".join(html.unescape(page_text).split())
    if support_quote and destination_text is not None and normalized_quote not in page_text:
        return {
            "status": "fallback",
            "reason": "Support quote is absent from the supplied HTML export",
        }
    locations = _phrase_locations(page_text)
    claim_words = {
        word.casefold()
        for word in re.findall(r"\w+", claim or "")
        if (len(word) >= 4 or (len(word) >= 2 and any(char.isdigit() for char in word)))
        and word.casefold()
        not in {"legacy", "code", "source", "that", "this", "with", "from", "into", "when"}
    }
    critical = (
        (
            {word.casefold() for word in re.findall(r"\w+", claim or support_quote)}
            & {word.casefold() for word in re.findall(r"\w+", normalized_quote)}
            & {
                "only",
                "unless",
                "except",
                "without",
                "before",
                "after",
                "must",
                "never",
                "cannot",
                "required",
            }
        )
        if support_quote
        else set()
    )
    best = None
    for segment in segments:
        value = segment["text"]
        row_words = {
            word.casefold()
            for row_segment in full_segments
            if row_segment["start_line"] == segment["start_line"]
            for word in re.findall(r"\w+", row_segment["text"])
        }
        supported_by_row = bool(support_quote) and len(row_words & claim_words) >= 2
        segment_index = full_segments.index(segment)
        previous = full_segments[segment_index - 1] if segment_index else None
        following = (
            full_segments[segment_index + 1] if segment_index + 1 < len(full_segments) else None
        )
        if support_quote:
            start = value.find(normalized_quote)
            if start < 0:
                continue
            area = normalized_quote
            area_start = start
        else:
            area = value
            area_start = 0
        words = list(re.finditer(r"\w+(?:[’']\w+)*", area, re.UNICODE))
        if support_quote and len(words) >= 5:
            target = area[words[0].start() : words[-1].end()]
            target_words = {word.casefold() for word in re.findall(r"\w+", target)}
            if not claim_words or len(target_words & claim_words) >= 2 or supported_by_row:
                for start_count in range(2, min(4, len(words) - 2) + 1):
                    start_phrase = area[words[0].start() : words[start_count - 1].end()]
                    for end_count in range(2, min(4, len(words) - start_count) + 1):
                        end_phrase = area[words[-end_count].start() : words[-1].end()]
                        end_positions = locations.get(end_phrase, [])
                        ranges = []
                        for position in locations.get(start_phrase, []):
                            end = next(
                                (
                                    candidate
                                    for candidate in end_positions
                                    if candidate >= position + len(start_phrase)
                                ),
                                None,
                            )
                            if end is not None:
                                ranges.append(page_text[position : end + len(end_phrase)])
                        if ranges == [target]:
                            directive = f"{_encoded(start_phrase)},{_encoded(end_phrase)}"
                            key = (len(directive), True, directive, segment["start_line"])
                            if best is None or key < best[0]:
                                best = (key, target, segment, directive)
        for first in range(len(words)):
            for last in range(first + 2, min(first + 12, len(words)) + 1):
                phrase = area[words[first].start() : words[last - 1].end()]
                encoded_phrase = _encoded(phrase)
                if best is not None and len(encoded_phrase) >= best[0][0]:
                    break
                content_words = [
                    word.group()
                    for word in words[first:last]
                    if len(word.group()) >= 4
                    or (len(word.group()) >= 2 and any(char.isdigit() for char in word.group()))
                ]
                if len(content_words) < 2:
                    continue
                candidate_words = {word.casefold() for word in content_words}
                if critical - candidate_words:
                    continue
                if claim_words and len(candidate_words & claim_words) < 2:
                    if not supported_by_row or phrase != normalized_quote:
                        continue
                directive = encoded_phrase
                occurrences = locations.get(phrase, [])
                if not occurrences:
                    continue
                if len(occurrences) > 12:
                    continue
                if len(occurrences) != 1:
                    before = value[: area_start + words[first].start()]
                    after = value[area_start + words[last - 1].end() :]
                    if previous and previous["start_line"] == segment["start_line"]:
                        before = previous["text"] + " " + before
                    if following and following["start_line"] == segment["start_line"]:
                        after = after + " " + following["text"]
                    prefixes = [
                        before[match.start() :].strip()
                        for match in list(re.finditer(r"\w+", before))[-8:]
                    ]
                    suffixes = [
                        after[: match.end()].strip()
                        for match in list(re.finditer(r"\w+", after))[:8]
                    ]
                    options = []
                    for prefix in [""] + prefixes:
                        for suffix in [""] + suffixes:
                            if not prefix and not suffix:
                                continue
                            matches = [
                                position
                                for position in occurrences
                                if (not prefix or page_text[:position].rstrip().endswith(prefix))
                                and (
                                    not suffix
                                    or page_text[position + len(phrase) :]
                                    .lstrip()
                                    .startswith(suffix)
                                )
                            ]
                            if len(matches) == 1:
                                candidate = (
                                    f"{_encoded(prefix)}-,{directive}" if prefix else directive
                                )
                                if suffix:
                                    candidate += f",-{_encoded(suffix)}"
                                options.append(candidate)
                    if not options:
                        continue
                    directive = min(options, key=lambda item: (len(item.encode("ascii")), item))
                key = (
                    len(directive),
                    directive != encoded_phrase,
                    directive,
                    segment["start_line"],
                )
                if best is None or key < best[0]:
                    best = (key, phrase, segment, directive)
    if best is None:
        return {"status": "fallback", "reason": "No unique evidence-bearing visible text locator"}
    _, phrase, segment, directive = best
    return {
        "status": "verified_html" if destination_text is not None else "markdown_projection_only",
        "directive": directive,
        "phrase": phrase,
        "start_line": segment["start_line"],
        "end_line": segment["end_line"],
    }


def visible_phrase(excerpt: str) -> str | None:
    return select_text_fragment(excerpt).get("phrase")


def text_fragment_url(
    source_url: str,
    excerpt: str,
    page_markdown: str | None = None,
    support_quote: str | None = None,
    destination_text: str | None = None,
    claim: str | None = None,
) -> str | None:
    result = select_text_fragment(excerpt, page_markdown, support_quote, destination_text, claim)
    if result["status"] == "fallback":
        return None
    parsed = urlsplit(source_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    fragment = (
        f"{parsed.fragment}:~:text={result['directive']}"
        if parsed.fragment
        else f":~:text={result['directive']}"
    )
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, fragment))


def source_page(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))
