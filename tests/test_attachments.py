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


def test_scanned_pdf_stays_unresolved_without_ocr():
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    stream = io.BytesIO()
    writer.write(stream)
    result = extract_attachment("scan.pdf", stream.getvalue())
    assert result["status"] == "unresolved"
    assert any("transcription required" in item for item in result["limitations"])


def test_workbook_formulas_and_uncached_values_remain_visible():
    from openpyxl import Workbook

    workbook = Workbook()
    workbook.active.title = "Limits"
    workbook.active["A1"] = "=2+3"
    stream = io.BytesIO()
    workbook.save(stream)
    result = extract_attachment("limits.xlsx", stream.getvalue())
    assert result["status"] == "unresolved"
    assert result["spans"][0]["formula"] == "=2+3"
    assert result["spans"][0]["locator"] == {
        "kind": "sheet_range",
        "sheet": "Limits",
        "range": "A1",
    }
