import io
import zipfile

from docgen_graph.attachments import extract_attachment


def test_csv_preserves_header_cell_and_values():
    result = extract_attachment("limits.csv", b"Role,Limit\nAdmin,10 days\n")
    assert result["status"] == "ok"
    assert result["spans"][-1]["text"] == "Limit: 10 days"
    assert result["spans"][-1]["locator"]["row"] == 2


def test_corrupt_and_unsupported_are_explicit():
    assert extract_attachment("bad.docx", b"bad")["status"] == "unresolved"
    assert extract_attachment("scan.png", b"image")["status"] == "unsupported"


def test_docx_retains_paragraph_and_table_coordinates():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body><w:p><w:r><w:t>Approval required</w:t></w:r></w:p><w:tbl><w:tr><w:tc>"
            "<w:p><w:r><w:t>10 mm</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>",
        )
    result = extract_attachment("rules.docx", stream.getvalue())
    assert result["status"] == "ok"
    assert result["spans"][0]["locator"]["paragraph"] == 1
    assert result["spans"][1]["locator"]["column"] == 1
