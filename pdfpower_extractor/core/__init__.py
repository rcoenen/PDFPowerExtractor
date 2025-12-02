# Core PDFPowerExtractor modules

from .config import (
    ExtractionConfig,
    LLMConfig,
    ValidationConfig,
    # Presets (all GDPR compliant - EU only)
    gemini_config,
    qwen_config,
    mistral_config,
    nemotron_config,
    # Backwards compatibility
    gemini_flash_config,
    qwen_vl_config,
    mistral_small_config,
    nemotron_vl_config,
)
from .prompts import (
    get_vision_prompt,
    get_system_prompt,
)
from .extractor import AIExtractor
from .processor import PDFProcessor, HybridPDFProcessor
from .analyzer import PDFAnalyzer
from .validator import (
    OutputValidator,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
)

__all__ = [
    # Config
    "ExtractionConfig",
    "LLMConfig",
    "ValidationConfig",
    # Config presets (all GDPR compliant - EU only)
    "gemini_config",
    "qwen_config",
    "mistral_config",
    "nemotron_config",
    # Backwards compatibility
    "gemini_flash_config",
    "qwen_vl_config",
    "mistral_small_config",
    "nemotron_vl_config",
    # Prompts
    "get_vision_prompt",
    "get_system_prompt",
    # Validator
    "OutputValidator",
    "ValidationResult",
    "ValidationIssue",
    "ValidationSeverity",
    # Classes
    "AIExtractor",
    "PDFProcessor",
    "HybridPDFProcessor",  # Backwards compatibility
    "PDFAnalyzer",
]
