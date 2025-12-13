import json
from pathlib import Path

import fitz
import pytest

from pdfpower_extractor.core.processor import PDFProcessor
from pdfpower_extractor.core.config import ExtractionConfig
from pdfpower_extractor.models.config import TokenUsage


def create_pdf(path: Path, pages: int = 1) -> None:
    """Create a simple PDF with the requested number of pages."""
    doc = fitz.open()
    for _ in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), "Test page")
    doc.save(path)


def _stub_analyzer(total_pages: int = 1, empty_pages=None):
    empty_pages = empty_pages or []

    class StubAnalyzer:
        def __init__(self, pdf):
            self.pdf = pdf

        def analyze(self):
            return {
                "total_pages": total_pages,
                "empty_pages": empty_pages,
                "text_pages": [],
                "form_pages": list(range(1, total_pages + 1)),
                "form_percentage": 100.0,
                "text_percentage": 0.0,
            }

    return StubAnalyzer


def test_audit_log_success(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    create_pdf(pdf_path)

    config = ExtractionConfig()
    config.validation.validate_output = False
    processor = PDFProcessor(str(pdf_path), config=config)
    processor.analyzer = _stub_analyzer()(pdf_path)

    def fake_extract_page(pdf_path, page_num, **kwargs):
        return {
            "content": "### Title\nSome content\n",
            "token_usage": TokenUsage(
                input_tokens=10,
                output_tokens=5,
                total_tokens=15,
                cost=0.01,
                model_id="gemini_flash",
                endpoint="requesty_eu",
            ),
        }

    processor.ai_extractor.extract_page = fake_extract_page

    audit_log = tmp_path / "audit.log"
    output = processor.process(audit_log_path=str(audit_log), audit_retention_hours=None)

    assert "Title" in output
    assert audit_log.exists()
    last_entry = json.loads(audit_log.read_text(encoding="utf-8").splitlines()[-1])
    assert last_entry["status"] == "success"
    assert last_entry["file"] == "sample.pdf"
    assert last_entry["model_id"]
    assert "md5" in last_entry


def test_audit_log_failure(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    create_pdf(pdf_path)

    config = ExtractionConfig()
    config.validation.validate_output = False
    processor = PDFProcessor(str(pdf_path), config=config)
    processor.analyzer = _stub_analyzer()(pdf_path)

    def failing_extract_page(*args, **kwargs):
        raise RuntimeError("boom")

    processor.ai_extractor.extract_page = failing_extract_page

    audit_log = tmp_path / "audit.log"
    with pytest.raises(RuntimeError):
        processor.process(audit_log_path=str(audit_log), audit_retention_hours=None)

    assert audit_log.exists()
    last_entry = json.loads(audit_log.read_text(encoding="utf-8").splitlines()[-1])
    assert last_entry["status"] == "failure"
    assert "boom" in last_entry.get("error", "")
