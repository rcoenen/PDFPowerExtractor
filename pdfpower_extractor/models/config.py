"""
AI Model Configuration System for PDFPowerExtractor

Defines endpoints, API keys, model parameters, and regional settings.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum


# =============================================================================
# ENDPOINTS
# =============================================================================

class EndpointRegion(Enum):
    """Geographic region for data processing compliance"""
    US = "us"
    EU = "eu"


@dataclass
class APIEndpoint:
    """API endpoint configuration"""
    name: str
    base_url: str
    region: EndpointRegion
    api_key_env_var: str  # Environment variable name for API key
    headers_template: Dict[str, str] = field(default_factory=dict)
    notes: str = ""

    def get_chat_url(self) -> str:
        """Get the chat completions URL"""
        return f"{self.base_url}/chat/completions"


# Available endpoints
# NOTE: OpenRouter has NO EU servers. Only Requesty provides EU-based routing.
ENDPOINTS = {
    "openrouter": APIEndpoint(
        name="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        region=EndpointRegion.US,
        api_key_env_var="OPENROUTER_API_KEY",
        headers_template={
            "Authorization": "Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/PDFPowerExtractor",
        },
        notes="Multi-provider gateway, US-only (no EU servers)"
    ),
    "requesty_eu": APIEndpoint(
        name="Requesty EU",
        base_url="https://router.requesty.ai/v1",
        region=EndpointRegion.EU,
        api_key_env_var="REQUESTY_API_KEY",
        headers_template={
            "Authorization": "Bearer {api_key}",
            "Content-Type": "application/json",
        },
        notes="EU-based endpoint for GDPR compliance - the ONLY EU option"
    ),
    "openai_direct": APIEndpoint(
        name="OpenAI Direct",
        base_url="https://api.openai.com/v1",
        region=EndpointRegion.US,
        api_key_env_var="OPENAI_API_KEY",
        headers_template={
            "Authorization": "Bearer {api_key}",
            "Content-Type": "application/json",
        },
        notes="Direct OpenAI API (US-only)"
    ),
    "google_direct": APIEndpoint(
        name="Google AI Direct",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        region=EndpointRegion.US,
        api_key_env_var="GOOGLE_API_KEY",
        headers_template={
            "Content-Type": "application/json",
        },
        notes="Direct Google AI API (US-only, different request format)"
    ),
    "nebius_eu": APIEndpoint(
        name="Nebius Token Factory (EU)",
        base_url="https://api.tokenfactory.nebius.com/v1",
        region=EndpointRegion.EU,
        api_key_env_var="NEBIUS_API_KEY",
        headers_template={
            "Authorization": "Bearer {api_key}",
            "Content-Type": "application/json",
        },
        notes="EU-based (Netherlands/Finland/Paris) - GDPR, SOC2, ISO27001 compliant"
    ),
    "huggingface_nebius": APIEndpoint(
        name="HuggingFace → Nebius (EU)",
        base_url="huggingface://nebius",  # Special marker for HF client
        region=EndpointRegion.EU,
        api_key_env_var="HF_TOKEN",
        headers_template={},  # Not used - HF client handles auth
        notes="Routes through HuggingFace to Nebius EU. GDPR compliant."
    ),
    "scaleway_eu": APIEndpoint(
        name="Scaleway (EU - Paris)",
        base_url="https://api.scaleway.ai/v1",
        region=EndpointRegion.EU,
        api_key_env_var="SCW_SECRET_KEY",
        headers_template={
            "Authorization": "Bearer {api_key}",
            "Content-Type": "application/json",
        },
        notes="EU-based (Paris, France) - GDPR compliant. Uses SCW_SECRET_KEY."
    ),
}


# =============================================================================
# MODEL PARAMETERS
# =============================================================================

@dataclass
class ModelParameters:
    """Model-specific generation parameters"""
    temperature: float = 0.0          # 0 = deterministic
    top_p: float = 0.1                # Low for consistent output
    max_tokens: int = 4000            # Max response length
    presence_penalty: float = 0.0     # Penalize repetition
    frequency_penalty: float = 0.0    # Penalize frequent tokens

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API request format"""
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "presence_penalty": self.presence_penalty,
            "frequency_penalty": self.frequency_penalty,
        }


@dataclass
class TokenPricing:
    """Token-based pricing for a model (costs per 1M tokens)"""
    input_cost_per_1m: float = 0.0    # Cost per 1M input tokens
    output_cost_per_1m: float = 0.0   # Cost per 1M output tokens

    # For vision models, image tokens are often calculated differently
    # These are estimates per image/page at typical DPI
    image_tokens_estimate: int = 1000  # Estimated tokens per image

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate total cost from token counts"""
        input_cost = (input_tokens / 1_000_000) * self.input_cost_per_1m
        output_cost = (output_tokens / 1_000_000) * self.output_cost_per_1m
        return input_cost + output_cost


@dataclass
class TokenUsage:
    """Tracks token usage and costs for an API call"""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0

    # Breakdown
    input_cost: float = 0.0
    output_cost: float = 0.0

    # Metadata
    model_id: str = ""
    endpoint: str = ""

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        """Add two TokenUsage instances together"""
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            cost=self.cost + other.cost,
            input_cost=self.input_cost + other.input_cost,
            output_cost=self.output_cost + other.output_cost,
            model_id=self.model_id or other.model_id,
            endpoint=self.endpoint or other.endpoint,
        )


# =============================================================================
# MODEL CONFIGURATIONS
# =============================================================================

@dataclass
class AIModelConfig:
    """Complete configuration for an AI model"""
    # Identity
    model_id: str                     # e.g., "gemini_flash"
    name: str                         # Human-readable name

    # Endpoint
    endpoint_id: str                  # Key in ENDPOINTS dict
    model_id_at_endpoint: str = None  # Model ID to send to the API

    # Parameters
    parameters: ModelParameters = field(default_factory=ModelParameters)

    # Pricing (per 1M tokens)
    pricing: TokenPricing = field(default_factory=TokenPricing)

    # Capabilities & metrics
    accuracy: int = 0                 # 0-100 percentage
    context_window: str = ""          # e.g., "1M+ tokens"

    # Feature support
    supports_vision: bool = True
    supports_checkboxes: bool = True
    supports_radio: bool = True
    supports_text: bool = True

    # Notes
    notes: str = ""

    def __post_init__(self):
        if self.model_id_at_endpoint is None:
            self.model_id_at_endpoint = self.model_id

    def get_endpoint(self) -> APIEndpoint:
        """Get the endpoint configuration"""
        return ENDPOINTS[self.endpoint_id]

    def is_eu(self) -> bool:
        """Check if this model uses an EU endpoint"""
        return self.get_endpoint().region == EndpointRegion.EU

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> TokenUsage:
        """Calculate cost and return TokenUsage from token counts"""
        input_cost = (input_tokens / 1_000_000) * self.pricing.input_cost_per_1m
        output_cost = (output_tokens / 1_000_000) * self.pricing.output_cost_per_1m
        return TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost=input_cost + output_cost,
            input_cost=input_cost,
            output_cost=output_cost,
            model_id=self.model_id,
            endpoint=self.endpoint_id,
        )


# =============================================================================
# AVAILABLE MODEL CONFIGURATIONS
# =============================================================================
# All models route through Requesty EU for GDPR compliance.
# Pricing is per 1M tokens - from Requesty dashboard.

MODEL_CONFIGS: Dict[str, AIModelConfig] = {
    # --- GEMINI 2.5 FLASH LITE via Requesty (EU / Vertex) ---
    "gemini_flash": AIModelConfig(
        model_id="gemini_flash",
        name="Gemini 2.5 Flash Lite",
        endpoint_id="requesty_eu",
        model_id_at_endpoint="vertex/gemini-2.5-flash-lite@europe-central2",
        parameters=ModelParameters(temperature=0.1),
        pricing=TokenPricing(
            input_cost_per_1m=0.10,     # $0.10 per 1M input tokens
            output_cost_per_1m=0.40,    # $0.40 per 1M output tokens
            image_tokens_estimate=1000,  # ~1000 tokens per page image
        ),
        accuracy=100,
        context_window="1M tokens",
        notes="RECOMMENDED - 100% accuracy, GDPR compliant (EU via Vertex)"
    ),


    # --- QWEN 2.5 VL 72B via HuggingFace → Nebius (EU) ---
    # Uses HF_TOKEN - good if you don't have a Nebius API key
    "qwen_vl_72b_hf": AIModelConfig(
        model_id="qwen_vl_72b_hf",
        name="Qwen 2.5 VL 72B (via HF → Nebius EU)",
        endpoint_id="huggingface_nebius",
        model_id_at_endpoint="Qwen/Qwen2.5-VL-72B-Instruct",
        parameters=ModelParameters(temperature=0.0, top_p=0.1),
        pricing=TokenPricing(
            input_cost_per_1m=0.13,     # $0.13 per 1M input tokens
            output_cost_per_1m=0.40,    # $0.40 per 1M output tokens
            image_tokens_estimate=2600,  # ~2600 tokens per page image (measured)
        ),
        accuracy=100,
        context_window="32K tokens",
        notes="GDPR compliant (EU). Routes via HuggingFace. Uses HF_TOKEN."
    ),

    # --- QWEN 2.5 VL 72B via Direct Nebius API (EU) ---
    # Uses NEBIUS_API_KEY - direct connection, potentially faster
    "qwen_vl_72b": AIModelConfig(
        model_id="qwen_vl_72b",
        name="Qwen 2.5 VL 72B (Nebius EU Direct)",
        endpoint_id="nebius_eu",
        model_id_at_endpoint="Qwen/Qwen2.5-VL-72B-Instruct",
        parameters=ModelParameters(temperature=0.0, top_p=0.1),
        pricing=TokenPricing(
            input_cost_per_1m=0.13,     # $0.13 per 1M input tokens
            output_cost_per_1m=0.40,    # $0.40 per 1M output tokens
            image_tokens_estimate=2600,  # ~2600 tokens per page image (measured)
        ),
        accuracy=100,
        context_window="32K tokens",
        notes="GDPR compliant (EU - Netherlands/Finland). Direct API. Uses NEBIUS_API_KEY."
    ),

    # --- MISTRAL SMALL 3.1 24B via Scaleway (EU - Paris) ---
    "mistral_small": AIModelConfig(
        model_id="mistral_small",
        name="Mistral Small 3.1 24B (Scaleway EU)",
        endpoint_id="scaleway_eu",
        model_id_at_endpoint="mistral-small-3.1-24b-instruct-2503",
        parameters=ModelParameters(temperature=0.0, top_p=0.1),
        pricing=TokenPricing(
            input_cost_per_1m=0.15,     # €0.15 per 1M input tokens
            output_cost_per_1m=0.35,    # €0.35 per 1M output tokens
            image_tokens_estimate=2256,  # measured from test
        ),
        accuracy=100,
        context_window="32K tokens",
        notes="FASTEST EU option. GDPR compliant (Paris). Uses SCW_SECRET_KEY."
    ),

}


# =============================================================================
# DEFAULTS & HELPERS
# =============================================================================

# Default model (all EU via Requesty for GDPR)
DEFAULT_MODEL = "gemini_flash"

# Quick lookup by simple name
MODEL_ALIASES = {
    "gemini": "gemini_flash",
    "qwen": "qwen_vl_72b",
    "nebius": "qwen_vl_72b",
    "mistral": "mistral_small",
    "scaleway": "mistral_small",
}


def get_model_config(model_id: str) -> AIModelConfig:
    """Get model config by ID or alias"""
    # Check alias first
    if model_id in MODEL_ALIASES:
        model_id = MODEL_ALIASES[model_id]

    if model_id not in MODEL_CONFIGS:
        raise ValueError(f"Unknown model: {model_id}. Available: {list(MODEL_CONFIGS.keys())}")

    return MODEL_CONFIGS[model_id]


def list_models() -> Dict[str, AIModelConfig]:
    """Get all available models (all EU/GDPR compliant)"""
    return MODEL_CONFIGS.copy()


# =============================================================================
# FAILED MODELS (for reference, do not use)
# =============================================================================

FAILED_MODELS = {
    "google/gemini-flash-1.5-8b": "50% checkbox accuracy",
    "google/gemini-2.5-flash-lite": "50% checkbox accuracy",
    "openai/gpt-4o-mini": "Complete extraction failure",
    "mistral/mistral-small-3.2": "No checkbox detection",
    "mistral/pixtral-12b": "Context window too small",
}

# =============================================================================
# TESTED BUT REJECTED - US ONLY (no EU option available)
# =============================================================================
# These models were tested and work well, but are only available via US providers.
# Cannot be used for GDPR-compliant EU processing.

TESTED_US_ONLY = {
    "Qwen/Qwen2.5-VL-7B-Instruct": {
        "provider": "Hyperbolic (US)",
        "performance": "Excellent - 3.22s, 35 input tokens, clean output",
        "pricing": "$0.20/M input, $0.20/M output",
        "reason_rejected": "US only - not available on any EU provider (Nebius, etc.)",
        "notes": "Fastest and cheapest option tested, but no EU availability",
    },
    "meta-llama/Llama-3.2-11B-Vision-Instruct": {
        "provider": "None available via HuggingFace",
        "performance": "Not tested - no provider available",
        "pricing": "N/A",
        "reason_rejected": "Not available on any HuggingFace Inference Provider",
        "notes": "Listed on HuggingFace but not deployed by any inference provider",
    },
}

# =============================================================================
# TESTED BUT REJECTED - ACCURACY ISSUES
# =============================================================================
# These models were tested and available in EU, but have accuracy problems.

TESTED_ACCURACY_ISSUES = {
    "google/gemma-3-27b-it": {
        "provider": "Nebius (EU), Scaleway (EU)",
        "performance": "Fast - 4.15s, 284 input tokens",
        "pricing": "$0.10/M input, $0.30/M output (cheapest EU)",
        "reason_rejected": "OCR accuracy issues - misreads Z as 2, adds unwanted markdown",
        "tested_error": "K75-19Z-RZLT → K75-192-RZLT (Z→2 substitution)",
        "notes": "Gemma is not optimized for OCR tasks. Even with explicit prompts warning about Z/2 confusion, it still makes errors. Not suitable for form data where 100% accuracy is required.",
    },
    "azure/gpt-4.1-nano": {
        "provider": "Requesty EU → Azure Sweden",
        "performance": "Fast - ~2s per page",
        "pricing": "$0.10/M input, $0.40/M output",
        "reason_rejected": "~90% accuracy - misses subtle radio button fill markers",
        "tested_error": "Fails to detect filled radio buttons when fill marker is small or faint",
        "notes": "GPT-4.1 Nano struggles with detecting small graphical elements like radio button fills. Not suitable for form data where 100% accuracy is required.",
    },
    "mistral/pixtral-12b-2409": {
        "provider": "Scaleway (EU - Paris)",
        "performance": "6.3s, 3064 input tokens, 408 output tokens",
        "pricing": "€0.20/M input, €0.20/M output",
        "reason_rejected": "Does not output radio button symbols (● ○) - outputs garbage dots instead",
        "tested_error": "Radio button section filled with repeated '.' characters instead of proper symbols",
        "notes": "Pixtral fails to follow instructions for radio button symbol output. Not suitable for form extraction.",
    },
}
