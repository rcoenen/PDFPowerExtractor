"""
Extraction configuration for PDFPowerExtractor pipeline.

This module defines all configurable settings for the PDF → AI → Markdown pipeline.
All extraction uses AI vision models (no text-only mode).
"""

from dataclasses import dataclass, field
from typing import Optional, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.config import AIModelConfig


@dataclass
class LLMConfig:
    """LLM-specific configuration"""
    # Temperature settings (0 = deterministic)
    temperature: float = 0.0

    # Top-p sampling (0 or very low for deterministic)
    top_p: float = 0.1

    # Max tokens for response
    max_tokens: int = 4000

    # Retry settings
    max_retries: int = 2
    retry_delay_seconds: float = 1.0

    # Timeout in seconds
    timeout_seconds: int = 60


@dataclass
class ValidationConfig:
    """Output validation settings"""
    # Validate LLM output structure
    validate_output: bool = True

    # Required elements to check
    check_section_headers: bool = True
    check_question_ids: bool = True
    check_radio_groups: bool = True


@dataclass
class ExtractionConfig:
    """
    Configuration for the PDF extraction pipeline.

    Usage:
        # Default: Gemini Flash with markdown output
        config = ExtractionConfig()
        processor = PDFProcessor(pdf_path, config=config)

        # Use different model
        config = ExtractionConfig(model_config_id="qwen_vl_72b")

        # Use preset
        from pdfpower_extractor.core import mistral_config
        processor = PDFProcessor(pdf_path, config=mistral_config())
    """

    # === Model Selection ===
    # Model config ID from models/config.py MODEL_CONFIGS
    # Available: "gemini_flash", "qwen_vl_72b", "mistral_small" (all EU/GDPR compliant)
    model_config_id: str = "gemini_flash"

    # === Sub-configs ===
    llm: LLMConfig = field(default_factory=LLMConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)

    # === Logging/Debug ===
    verbose: bool = False
    log_prompts: bool = False

    def get_model_config(self) -> Optional["AIModelConfig"]:
        """Get the AIModelConfig for this extraction config"""
        from ..models.config import get_model_config
        return get_model_config(self.model_config_id)

    def is_eu(self) -> bool:
        """Check if this config uses an EU endpoint"""
        mc = self.get_model_config()
        return mc.is_eu() if mc else False


# === Preset Configurations ===
# All presets are GDPR compliant (EU endpoints only)

def gemini_config() -> ExtractionConfig:
    """
    Preset for Gemini 2.5 Flash Lite via Requesty EU (Vertex).

    Pricing: $0.10/1M input, $0.40/1M output tokens
    Speed: ~2-3 seconds per page (with 5-region pooling)
    GDPR: Compliant (EU via Vertex - 5 EU regions)
    """
    return ExtractionConfig(model_config_id="gemini_flash")


def qwen_config() -> ExtractionConfig:
    """
    Preset for Qwen 2.5 VL 72B via Nebius (EU).

    Pricing: $0.13/1M input, $0.40/1M output tokens
    Speed: ~10-12 seconds per page
    GDPR: Compliant (EU - Netherlands HQ, Finland/Paris data centers)
    """
    return ExtractionConfig(model_config_id="qwen_vl_72b")


def mistral_config() -> ExtractionConfig:
    """
    Preset for Mistral Small 3.1 24B via Scaleway (EU - Paris).

    Pricing: €0.15/1M input, €0.35/1M output tokens
    Speed: ~4 seconds per page (FASTEST)
    GDPR: Compliant (EU - Paris, France)
    """
    return ExtractionConfig(model_config_id="mistral_small")


# Backwards compatibility aliases
gemini_flash_config = gemini_config
qwen_vl_config = qwen_config
mistral_small_config = mistral_config
