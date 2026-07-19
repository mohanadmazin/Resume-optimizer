"""Tests for document reader limits (PDF pages, DOCX expansion, AI parser)."""
import zipfile

import pytest


class TestPdfPageLimit:
    def test_rejects_pdf_with_more_than_60_pages(self, tmp_path):
        import fitz

        pdf_path = tmp_path / "long.pdf"
        doc = fitz.open()
        for _ in range(65):
            doc.new_page()
        doc.save(str(pdf_path))
        doc.close()

        from app.services.document_reader import extract_text

        with pytest.raises(ValueError, match="exceeds 60 pages"):
            extract_text(str(pdf_path))

    def test_accepts_pdf_with_exactly_60_pages(self, tmp_path):
        import fitz

        pdf_path = tmp_path / "ok.pdf"
        doc = fitz.open()
        for _ in range(60):
            page = doc.new_page()
            text_writer = fitz.TextWriter(page.rect)
            text_writer.append((50, 100), "Hello", fontsize=12)
            text_writer.write_text(page)
        doc.save(str(pdf_path))
        doc.close()

        from app.services.document_reader import extract_text

        result = extract_text(str(pdf_path))
        assert "Hello" in result


class TestDocxExpansionLimit:
    def test_rejects_high_compression_ratio_docx(self, tmp_path):
        docx_path = tmp_path / "ratio.docx"

        with zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED) as zf:
            content = b"\x00" * 1_000_000
            zf.writestr("word/document.xml", content)
            zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')

        from app.services.document_reader import extract_text

        with pytest.raises(ValueError, match="compression ratio"):
            extract_text(str(docx_path))


class TestAiParserInputLimit:
    def test_heuristic_parser_works_for_large_input(self):
        from app.services.resume_parser import parse_resume

        text = "John Doe\njohn@example.com\n" + "Python, SQL, Docker\n" * 1000
        resume = parse_resume(text)
        assert resume.contact.name == "John Doe"
