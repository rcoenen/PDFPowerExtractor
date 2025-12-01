"""
PDFPowerExtractor - AI-powered PDF form extraction to structured Markdown
"""

__version__ = "2.0.0"
__author__ = "Robert Coenen"
__email__ = "rcoenen@github.com"

from .core.processor import PDFProcessor, HybridPDFProcessor
from .core.analyzer import PDFAnalyzer
from .core.extractor import AIExtractor

__all__ = [
    "PDFProcessor",
    "HybridPDFProcessor",  # Backwards compatibility
    "PDFAnalyzer",
    "AIExtractor",
]
