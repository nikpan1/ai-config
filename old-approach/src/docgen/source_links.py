import html
import re
from urllib.parse import quote, urlsplit, urlunsplit


def source_url_from_markdown(markdown: str) -> str | None:
    lines = markdown.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, separator, value = line.partition(":")
        if separator and key.strip() == "source_url":
            candidate = value.strip().strip('"\'')
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


def visible_phrase(excerpt: str) -> str | None:
    for line in excerpt.splitlines():
        story = re.search(r"\|\s*(As an? [^|]+?)\s*\|", line)
        if story:
            return " ".join(html.unescape(story.group(1)).split())
    for line in excerpt.splitlines():
        if line.lstrip().startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            line = next((cell for cell in cells if len(cell) >= 35), "")
        line = re.sub(r"!\[[^]]*\]\([^)]*\)", "", line)
        line = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", line)
        line = re.sub(r"^\s*(?:#{1,6}\s*|>\s*|[-*+]\s*|\d+[.)]\s*)", "", line)
        line = re.sub(r"[`*_~]", "", line)
        phrase = " ".join(html.unescape(line).split())
        if len(phrase) >= 30 and not phrase.startswith("source_url:"):
            return phrase[:180].rsplit(" ", 1)[0] if len(phrase) > 180 else phrase
    return None


def text_fragment_url(source_url: str, excerpt: str) -> str | None:
    phrase = visible_phrase(excerpt)
    if not phrase:
        return None
    parsed = urlsplit(source_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    encoded = quote(phrase, safe="").replace("-", "%2D")
    fragment = f"{parsed.fragment}:~:text={encoded}" if parsed.fragment else f":~:text={encoded}"
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, fragment))


def source_page(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))
