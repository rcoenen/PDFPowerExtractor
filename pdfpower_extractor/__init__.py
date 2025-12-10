"""
PDFPowerExtractor - AI-powered PDF form extraction to structured Markdown
"""

__version__ = "2.0.0"
__author__ = "Robert Coenen"
__email__ = "rcoenen@github.com"

from .core.processor import PDFProcessor
from .core.analyzer import PDFAnalyzer
from .core.extractor import AIExtractor
from .core.errors import (
    ExtractionError,
    BatchResult,
    PageResult,
    PageError,
    ErrorType,
)

__all__ = [
    "PDFProcessor",
    "PDFAnalyzer",
    "AIExtractor",
    # Errors
    "ExtractionError",
    "BatchResult",
    "PageResult",
    "PageError",
    "ErrorType",
]
