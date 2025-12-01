"""
Extraction configuration for PDFPowerExtractor pipeline.

This module defines all configurable settings for the PDF → Text → LLM → Markdown pipeline.
"""

from dataclasses import dataclass, field
from typing import Optional, Literal, List, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from ..models.config import AIModelConfig


class ExtractionMode(Enum):
    """Extraction modes"""
    TEXT_ONLY = "text_only"              # No LLM, pure PyMuPDF extraction (FREE)
    AI = "ai"                            # Use AI model (specify via model_config_id)


class OutputFormat(Enum):
    """Output format options"""
    PLAIN_TEXT = "plain_text"      # Current format with ● ○ symbols
    CANONICAL_MARKDOWN = "markdown" # Structured markdown with headers


@dataclass
class RadioCheckboxConfig:
    """Configuration for radio button and checkbox symbols"""
    # Radio button symbols
    radio_selected: str = "●"      # U+25CF BLACK CIRCLE
    radio_unselected: str = "○"    # U+25CB WHITE CIRCLE

    # Checkbox symbols
    checkbox_checked: str = "☑"    # U+2611 BALLOT BOX WITH CHECK
    checkbox_unchecked: str = "☐"  # U+2610 BALLOT BOX

    # Alternative markdown-style (for canonical format)
    radio_selected_md: str = "(x)"
    radio_unselected_md: str = "( )"
    checkbox_checked_md: str = "[x]"
    checkbox_unchecked_md: str = "[ ]"


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
class TextExtractionConfig:
    """PyMuPDF text extraction settings"""
    # Extraction method: "text" or "blocks" or "dict"
    method: Literal["text", "blocks", "dict"] = "dict"

    # Preserve page boundaries
    preserve_page_boundaries: bool = True

    # Minimum characters to consider page has text (for fallback detection)
    min_chars_for_text_layer: int = 50

    # Encoding
    encoding: str = "utf-8"


@dataclass
class ValidationConfig:
    """Output validation settings"""
    # Validate LLM output structure
    validate_output: bool = True

    # Required elements to check
    check_section_headers: bool = True
    check_question_ids: bool = True
    check_radio_groups: bool = True

    # Fallback to raw text on validation failure
    fallback_to_raw: bool = True


@dataclass
class ExtractionConfig:
    """
    Master configuration for the PDF extraction pipeline.

    Usage:
        # Text-only (free, no AI)
        config = ExtractionConfig(mode=ExtractionMode.TEXT_ONLY)

        # AI extraction with specific model
        config = ExtractionConfig(
            mode=ExtractionMode.AI,
            model_config_id="gemini_flash_openrouter",  # or "gemini_flash_eu" for EU
        )
        processor = HybridPDFProcessor(pdf_path, config=config)
    """

    # === Mode Selection ===
    mode: ExtractionMode = ExtractionMode.TEXT_ONLY

    # === Model Selection (for AI mode) ===
    # Model config ID from models/config.py MODEL_CONFIGS
    # Available: "gemini_flash", "qwen_vl_72b" (all EU/GDPR compliant)
    model_config_id: str = "gemini_flash"

    # === Output Format ===
    output_format: OutputFormat = OutputFormat.PLAIN_TEXT

    # === Force Settings ===
    # Force AI extraction even on text-extractable pages
    force_ai_extraction: bool = False

    # Force vision mode (send images instead of text)
    force_vision: bool = False

    # === Sub-configs ===
    symbols: RadioCheckboxConfig = field(default_factory=RadioCheckboxConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    text_extraction: TextExtractionConfig = field(default_factory=TextExtractionConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)

    # === Logging/Debug ===
    verbose: bool = False
    log_chunks: bool = False
    log_prompts: bool = False

    def get_model_config(self) -> Optional["AIModelConfig"]:
        """Get the AIModelConfig for this extraction config"""
        if self.mode == ExtractionMode.TEXT_ONLY:
            return None
        from ..models.config import get_model_config
        return get_model_config(self.model_config_id)

    def is_eu(self) -> bool:
        """Check if this config uses an EU endpoint"""
        mc = self.get_model_config()
        return mc.is_eu() if mc else False

    def should_use_vision(self, has_text_layer: bool) -> bool:
        """Determine if vision mode should be used"""
        if self.force_vision:
            return True
        if self.mode == ExtractionMode.TEXT_ONLY:
            return False
        # Use vision if no text layer detected
        return not has_text_layer


# === Preset Configurations ===

def text_only_config() -> ExtractionConfig:
    """
    Preset for text-only extraction (no LLM).

    Best for: Flattened PDFs with good text layers.
    Cost: FREE
    Speed: Instant (~0.4 seconds for 30 pages)
    Accuracy: 100% for flattened forms with proper fonts
    """
    return ExtractionConfig(
        mode=ExtractionMode.TEXT_ONLY,
        force_ai_extraction=False,
    )


# --- AI Model configs (all GDPR compliant via Requesty EU) ---

def gemini_flash_config() -> ExtractionConfig:
    """
    Preset for Gemini 2.5 Flash Lite via Requesty EU (Vertex).

    Best for: Scanned PDFs, image-only PDFs, or when text extraction fails.
    Pricing: $0.10/1M input, $0.40/1M output tokens
    Speed: ~2-3 seconds per page
    Accuracy: 100%
    GDPR: Compliant (EU via Vertex europe-central2)
    """
    return ExtractionConfig(
        mode=ExtractionMode.AI,
        model_config_id="gemini_flash",
    )


def qwen_vl_config() -> ExtractionConfig:
    """
    Preset for Qwen 2.5 VL 72B via Nebius (EU).

    Best for: Cost-effective EU-based OCR with excellent quality.
    Pricing: $0.13/1M input, $0.40/1M output tokens
    Speed: ~10-12 seconds per page
    Accuracy: 100%
    GDPR: Compliant (EU - Netherlands HQ, Finland/Paris data centers)
    Compliance: GDPR, SOC2, ISO27001, HIPAA
    """
    return ExtractionConfig(
        mode=ExtractionMode.AI,
        model_config_id="qwen_vl_72b",
    )


def mistral_small_config() -> ExtractionConfig:
    """
    Preset for Mistral Small 3.1 24B via Scaleway (EU - Paris).

    Best for: Fast EU-based OCR with excellent quality.
    Pricing: €0.15/1M input, €0.35/1M output tokens
    Speed: ~4 seconds per page (FASTEST)
    Accuracy: 100%
    GDPR: Compliant (EU - Paris, France)
    """
    return ExtractionConfig(
        mode=ExtractionMode.AI,
        model_config_id="mistral_small",
    )


# --- Other presets ---

def markdown_output_config() -> ExtractionConfig:
    """Preset for canonical markdown output with gemini-flash extraction"""
    return ExtractionConfig(
        mode=ExtractionMode.AI,
        model_config_id="gemini_flash",
        output_format=OutputFormat.CANONICAL_MARKDOWN,
    )
