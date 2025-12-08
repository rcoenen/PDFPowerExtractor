import fitz
import pytest
from pathlib import Path

from pdfpower_extractor.core.processor import PDFProcessor
from pdfpower_extractor.core.config import ExtractionConfig
from pdfpower_extractor.models.config import TokenUsage


def create_pdf(path: Path, pages: int = 2) -> None:
    """Create a simple PDF with the requested number of pages."""
    doc = fitz.open()
    for _ in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), "Test page")
    doc.save(path)


def test_toc_comments_present_for_pages(tmp_path, monkeypatch):
    pdf_path = tmp_path / "sample.pdf"
    create_pdf(pdf_path, pages=2)

    # Stub analyzer to mark page 2 as empty
    class StubAnalyzer:
        def __init__(self, pdf):
            self.pdf = pdf

        def analyze(self):
            return {
                "total_pages": 2,
                "empty_pages": [2],
                "text_pages": [],
                "form_pages": [1],
                "form_percentage": 50.0,
                "text_percentage": 0.0,
            }

    # Stub extractor to return fixed content for page 1
    def fake_extract_page(pdf_path, page_num, **kwargs):
        return {
            "content": "### Title\nSome content on page 1\n",
            "token_usage": TokenUsage(
                input_tokens=10,
                output_tokens=5,
                total_tokens=15,
                cost=0.01,
                model_id="gemini_flash",
                endpoint="requesty_eu",
            ),
        }

    config = ExtractionConfig()
    config.validation.validate_output = False
    processor = PDFProcessor(str(pdf_path), config=config)

    processor.analyzer = StubAnalyzer(pdf_path)
    processor.ai_extractor.extract_page = fake_extract_page

    output = processor.process()

    assert "<!-- TOC PAGE_01:" in output
    assert "<!-- TOC PAGE_02: Empty page -->" in output
    assert "Title" in output
    assert "<!-- TOC START -->" in output
    assert "<!-- TOC END -->" in output
    assert "- Page 1: Title" in output
    assert "- Page 2: Empty page" in output
    assert output.index("<!-- TOC START -->") < output.index("PAGE 1 OF 2")


def test_missing_grouped_toc_raises(tmp_path, monkeypatch):
    pdf_path = tmp_path / "sample.pdf"
    create_pdf(pdf_path, pages=1)

    config = ExtractionConfig()
    config.validation.validate_output = False
    processor = PDFProcessor(str(pdf_path), config=config)

    # Force grouped TOC omission to ensure we fail loudly
    monkeypatch.setattr(processor, "_build_top_level_toc", lambda entries: "")
    processor.analyzer = type("StubAnalyzer", (), {"analyze": lambda self=None: {"total_pages": 1, "empty_pages": [], "text_pages": [], "form_pages": [1], "form_percentage": 100.0, "text_percentage": 0.0}})
    processor.ai_extractor.extract_page = lambda *args, **kwargs: {"content": "### Title\nBody\n"}

    with pytest.raises(ValueError):
        processor.process()


def test_extra_metadata_in_single_comment(tmp_path, monkeypatch):
    pdf_path = tmp_path / "sample.pdf"
    create_pdf(pdf_path, pages=1)

    config = ExtractionConfig()
    config.validation.validate_output = False
    processor = PDFProcessor(str(pdf_path), config=config)

    processor.analyzer = type("StubAnalyzer", (), {"analyze": lambda self=None: {"total_pages": 1, "empty_pages": [], "text_pages": [], "form_pages": [1], "form_percentage": 100.0, "text_percentage": 0.0}})
    processor.ai_extractor.extract_page = lambda *args, **kwargs: {"content": "### Title\nBody\n"}

    output = processor.process(extra_metadata="Processor: Test\nMethod: test-mode")
    assert "<!--\nEXTRA METADATA\nProcessor: Test" in output
    assert "<!--\n<!--" not in output  # no nested comment open
