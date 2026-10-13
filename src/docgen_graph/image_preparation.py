from copy import deepcopy
from html import escape

import httpx
from google.genai import errors
from markdown_it import MarkdownIt
from markdown_it.rules_inline.image import image as parse_image
from pydantic import BaseModel, Field

from docgen_graph.source_documents import document_context, document_spans
from docgen_graph.storage import digest


class ImageDescription(BaseModel):
    description: str = Field(min_length=1, max_length=12000)
    visible_text: list[str]
    relationships: list[str]
    uncertainty: list[str]


def enriched_markdown(text: str, descriptions: dict[str, str]) -> str:
    def image_with_range(state, silent):
        start = state.pos
        matched = parse_image(state, silent)
        if matched and not silent:
            state.tokens[-1].meta["source_range"] = [start, state.pos]
        return matched

    parser = MarkdownIt().enable("table")
    parser.inline.ruler.at("image", image_with_range)
    original_positions = [
        index
        for index, character in enumerate(text)
        if not (character == "\r" and text[index + 1 : index + 2] == "\n")
    ]
    normalized = "".join(text[index] for index in original_positions).replace("\r", "\n")
    original_positions.append(len(text))
    offsets = [0]
    for line in normalized.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    edits = []
    start, stop = 0, len(normalized)
    cursors = {}
    for token in parser.parse(normalized):
        if token.map:
            start, stop = (offsets[index] for index in token.map)
        if token.type != "inline":
            continue
        position = normalized.find(token.content, cursors.get((start, stop), start), stop)
        if position < 0:
            continue
        cursors[(start, stop)] = position + len(token.content)
        for child in token.children or []:
            target = child.attrGet("src") or ""
            if child.type != "image" or target not in descriptions:
                continue
            first, last = child.meta["source_range"]
            title = "AI-generated image interpretation: " + descriptions[target]
            original_title = child.attrGet("title")
            if original_title:
                title = f"{original_title}. {title}"
            title = escape(" ".join(title.split()), quote=True)
            alt = child.content.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
            destination = target.replace("<", "%3C").replace(">", "%3E")
            replacement = f'![{alt}](<{destination}> "{title}")'
            edits.append(
                (
                    original_positions[position + first],
                    original_positions[position + last - 1] + 1,
                    replacement,
                )
            )
    for start, stop, replacement in sorted(edits, reverse=True):
        text = text[:start] + replacement + text[stop:]
    return text


def prepare_image_context(model, store, snapshot: dict, inventory: dict) -> dict:
    result = deepcopy(inventory)
    analyses = []
    descriptions_by_source = {}
    by_id = {span["id"]: span for span in inventory["spans"]}
    for asset in result.get("assets", []):
        if asset.get("disposition") == "rejected" or not asset.get("hash"):
            continue
        content = store.get_bytes(asset["hash"])
        contexts = list(
            dict.fromkeys(
                identifier
                for reference in asset.get("references", [])
                for identifier in reference.get("evidence_ids", [])
                if identifier in by_id
            )
        )
        payload = {
            "source_image": {key: asset.get(key) for key in ("path", "hash", "format")},
            "references": asset.get("references", []),
            "surrounding_text": "\n\n".join(by_id[key]["text"] for key in contexts)[:16000],
        }
        try:
            if asset["format"] == "svg":
                payload["svg_source"] = content.decode("utf-8")
                interpretation = model.call("describe_image", payload, ImageDescription)
                input_mode = "svg_source"
            else:
                mime_type = "image/jpeg" if asset["format"] == "jpeg" else "image/png"
                interpretation = model.call(
                    "describe_image",
                    payload,
                    ImageDescription,
                    images=[{"data": content, "mime_type": mime_type}],
                )
                input_mode = "image_pixels"
            interpretation = ImageDescription.model_validate(interpretation).model_dump()
        except (
            ValueError,
            OSError,
            TimeoutError,
            RuntimeError,
            errors.APIError,
            httpx.TransportError,
        ) as error:
            analyses.append(
                {
                    "source_image_hash": asset["hash"],
                    "path": asset["path"],
                    "status": "unavailable",
                    "error_type": type(error).__name__,
                }
            )
            continue
        record = {
            **interpretation,
            "source_image_hash": asset["hash"],
            "path": asset["path"],
            "provider": getattr(model, "provider", "unknown"),
            "model": model.settings.model,
            "input_mode": input_mode,
            "status": "generated_interpretation",
        }
        record_ref = store.put(record)
        text = (
            f"AI-generated interpretation of image {asset['path']}. "
            "This is model interpretation, not authored source text.\n\n"
            + interpretation["description"]
        )
        for name, key in (
            ("Visible text", "visible_text"),
            ("Observed relationships", "relationships"),
            ("Uncertainty", "uncertainty"),
        ):
            if interpretation[key]:
                text += f"\n\n{name}:\n" + "\n".join(interpretation[key])
        text_hash = store.put_bytes(text.encode())
        spans = document_spans(
            {"kind": "docs", "path": asset["path"] + ".ai-description.md", "hash": text_hash},
            text,
        )
        for span in spans:
            span.update(
                {
                    "role": "generated_image_description",
                    "source_kind": "generated_image_description",
                    "source_image_path": asset["path"],
                    "source_image_hash": asset["hash"],
                    "interpretation_ref": record_ref,
                    "provider": record["provider"],
                    "model": model.settings.model,
                }
            )
        result["spans"].extend(spans)
        asset["interpretation_ref"] = record_ref
        asset["description"] = interpretation["description"]
        asset["interpretation_evidence_ids"] = [span["id"] for span in spans]
        analyses.append({**record, "interpretation_ref": record_ref})
        for reference in asset.get("references", []):
            descriptions_by_source.setdefault(reference["source"], {})[reference["target"]] = (
                interpretation["description"]
            )
    derivatives = []
    for file in snapshot.get("files", []):
        descriptions = descriptions_by_source.get(file["path"])
        if file["kind"] != "docs" or not descriptions:
            continue
        original = store.get_bytes(file["hash"]).decode("utf-8")
        prepared = enriched_markdown(original, descriptions)
        derivatives.append(
            {
                "path": file["path"],
                "original_hash": file["hash"],
                "prepared_hash": store.put_bytes(prepared.encode()),
                "purpose": "image_descriptions_in_markdown_titles",
            }
        )
    result.update(document_context(result["spans"]))
    result["image_analyses"] = analyses
    result["enriched_documents"] = derivatives
    result["revision"] = digest([inventory["revision"], analyses, derivatives])
    return result
