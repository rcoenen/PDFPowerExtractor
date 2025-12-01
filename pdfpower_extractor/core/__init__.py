# Core PDFPowerExtractor modules

from .config import (
    ExtractionConfig,
    ExtractionMode,
    OutputFormat,
    RadioCheckboxConfig,
    LLMConfig,
    TextExtractionConfig,
    ValidationConfig,
    text_only_config,
    gemini_flash_config,
    qwen_vl_config,
    mistral_small_config,
    markdown_output_config,
)
from .prompts import (
    get_vision_prompt,
    get_system_prompt,
    get_text_to_markdown_prompt,
)
from .extractor import TextExtractor, AIExtractor
from .processor import HybridPDFProcessor
from .analyzer import PDFAnalyzer
from .formatter import (
    MarkdownFormatter,
    FormField,
    FormSection,
    FieldType,
    format_as_canonical_markdown,
    convert_symbols_only,
)
from .validator import (
    OutputValidator,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    validate_extraction,
    is_output_valid,
)

__all__ = [
    # Config
    "ExtractionConfig",
    "ExtractionMode",
    "OutputFormat",
    "RadioCheckboxConfig",
    "LLMConfig",
    "TextExtractionConfig",
    "ValidationConfig",
    # Config presets (all AI modes are GDPR compliant - EU only)
    "text_only_config",
    "gemini_flash_config",
    "qwen_vl_config",
    "mistral_small_config",
    "markdown_output_config",
    # Prompts
    "get_vision_prompt",
    "get_system_prompt",
    "get_text_to_markdown_prompt",
    # Formatter
    "MarkdownFormatter",
    "FormField",
    "FormSection",
    "FieldType",
    "format_as_canonical_markdown",
    "convert_symbols_only",
    # Validator
    "OutputValidator",
    "ValidationResult",
    "ValidationIssue",
    "ValidationSeverity",
    "validate_extraction",
    "is_output_valid",
    # Classes
    "TextExtractor",
    "AIExtractor",
    "HybridPDFProcessor",
    "PDFAnalyzer",
]