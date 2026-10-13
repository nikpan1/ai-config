import io
from types import SimpleNamespace

from PIL import Image

from docgen_graph.assets import image_references
from docgen_graph.image_preparation import enriched_markdown, prepare_image_context
from docgen_graph.ingestion import inventory, snapshot_inputs
from docgen_graph.storage import ArtifactStore


class ImageModel:
    provider = "controlled-test-double"
    settings = SimpleNamespace(model="gemini-3.8-flash")

    def __init__(self, error=None):
        self.calls = []
        self.error = error

    def call(self, stage, payload, schema, **kwargs):
        self.calls.append((stage, payload, kwargs))
        if self.error:
            raise self.error
        return {
            "description": 'An illustrative form contains a field labelled "Email".',
            "visible_text": ["Email"],
            "relationships": [],
            "uncertainty": ["A visible field does not establish mandatory entry."],
        }


def frozen_images(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    original = '# Guide\n\nIllustrative only. ![Form](form.png "Authored title")\n'
    (docs / "guide.md").write_bytes(original.encode())
    image = io.BytesIO()
    Image.new("RGB", (20, 20), "white").save(image, format="PNG")
    (docs / "form.png").write_bytes(image.getvalue())
    store = ArtifactStore(tmp_path / "artifacts")
    snapshot = snapshot_inputs(store, docs, None, None, "Document the supplied material")
    return store, snapshot, inventory(store, snapshot), original, image.getvalue()


def test_image_analysis_uses_pixels_and_keeps_original_source_provenance(tmp_path):
    store, snapshot, original_inventory, original, image = frozen_images(tmp_path)
    model = ImageModel()
    prepared = prepare_image_context(model, store, snapshot, original_inventory)
    assert model.calls[0][2]["images"] == [{"data": image, "mime_type": "image/png"}]
    assert "Illustrative only" in model.calls[0][1]["surrounding_text"]
    assert len(original_inventory["spans"]) == 1
    generated = next(s for s in prepared["spans"] if s["role"] == "generated_image_description")
    assert generated["source_image_hash"] == snapshot["assets"][0]["hash"]
    assert generated["model"] == "gemini-3.8-flash"
    assert generated["provider"] == "controlled-test-double"
    assert "not authored source text" in generated["text"]
    assert "does not establish mandatory" in generated["text"]
    assert store.get(generated["interpretation_ref"])["input_mode"] == "image_pixels"
    derivative = prepared["enriched_documents"][0]
    assert store.get_bytes(derivative["original_hash"]).decode() == original
    markdown = store.get_bytes(derivative["prepared_hash"]).decode()
    assert "AI-generated image interpretation" in markdown
    assert "Authored title" in markdown
    assert image_references(markdown)[0]["target"] == "form.png"
    assert (tmp_path / "docs/guide.md").read_text("utf-8") == original


def test_unavailable_image_analysis_remains_explicit_without_erasing_source(tmp_path):
    store, snapshot, original_inventory, original, image = frozen_images(tmp_path)
    prepared = prepare_image_context(
        ImageModel(ValueError("Unreadable")), store, snapshot, original_inventory
    )
    assert prepared["spans"] == original_inventory["spans"]
    assert prepared["image_analyses"][0]["status"] == "unavailable"
    assert prepared["enriched_documents"] == []
    assert store.get_bytes(snapshot["assets"][0]["hash"]) == image


def test_image_titles_support_reference_links_quotes_and_parentheses_without_touching_code():
    markdown = (
        "![First](assets/form(1).png)\n\n![Second][ref]\n\n"
        '[ref]: assets/form(1).png "Author title"\n\n'
        "`![Literal](assets/form(1).png)`\n\n"
        "```markdown\n![Literal](assets/form(1).png)\n```\n"
    )
    prepared = enriched_markdown(markdown, {"assets/form(1).png": 'The label reads "A & B".'})
    assert prepared.count("AI-generated image interpretation") == 2
    assert "`![Literal](assets/form(1).png)`" in prepared
    assert "```markdown\n![Literal](assets/form(1).png)\n```" in prepared
    assert len(image_references(prepared)) == 2
    assert all(
        reference["target"] == "assets/form(1).png" for reference in image_references(prepared)
    )


def test_crlf_multiline_paragraph_and_table_images_receive_descriptions():
    markdown = (
        "![Screen](screen.png)\r\nAn authored caption.\r\n\r\n"
        "| Item | View |\r\n| --- | --- |\r\n| Entry | ![Screen](screen.png) |\r\n"
    )
    prepared = enriched_markdown(markdown, {"screen.png": "A visible screen."})
    assert prepared.count("AI-generated image interpretation") == 2
    assert "\r\nAn authored caption.\r\n" in prepared


def test_provider_error_does_not_abort_image_preparation(tmp_path):
    from google.genai.errors import APIError

    store, snapshot, original_inventory, original, image = frozen_images(tmp_path)
    model = ImageModel(
        APIError(503, {"error": {"message": "Unavailable", "status": "UNAVAILABLE"}})
    )
    prepared = prepare_image_context(model, store, snapshot, original_inventory)
    assert prepared["image_analyses"][0]["status"] == "unavailable"
    assert prepared["spans"] == original_inventory["spans"]
