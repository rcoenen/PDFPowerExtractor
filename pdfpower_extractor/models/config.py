"""
AI Model Configuration System for PDFPowerExtractor

Uses Gemini 2.5 Flash Lite via Requesty EU for GDPR compliance.
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
ENDPOINTS = {
    "requesty_eu": APIEndpoint(
        name="Requesty EU",
        base_url="https://router.requesty.ai/v1",
        region=EndpointRegion.EU,
        api_key_env_var="REQUESTY_API_KEY",
        headers_template={
            "Authorization": "Bearer {api_key}",
            "Content-Type": "application/json",
        },
        notes="EU-based endpoint for GDPR compliance"
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
# GEMINI 2.5 FLASH LITE - THE ONLY MODEL WE USE
# =============================================================================

MODEL_CONFIGS: Dict[str, AIModelConfig] = {
    "gemini_flash": AIModelConfig(
        model_id="gemini_flash",
        name="Gemini 2.5 Flash Lite",
        endpoint_id="requesty_eu",
        model_id_at_endpoint="vertex/gemini-2.5-flash-lite",  # Region added dynamically
        parameters=ModelParameters(temperature=0.1),
        pricing=TokenPricing(
            input_cost_per_1m=0.10,     # $0.10 per 1M input tokens
            output_cost_per_1m=0.40,    # $0.40 per 1M output tokens
            image_tokens_estimate=1000,  # ~1000 tokens per page image
        ),
        accuracy=100,
        context_window="1M tokens",
        notes="100% accuracy, GDPR compliant (EU via Vertex, region pooling)"
    ),
}


# =============================================================================
# DEFAULTS & HELPERS
# =============================================================================

DEFAULT_MODEL = "gemini_flash"

# Gemini EU regions for quota pooling (all GDPR compliant)
GEMINI_EU_REGIONS = [
    "europe-central2",   # Warsaw, Poland
    "europe-north1",     # Hamina, Finland
    "europe-west1",      # St. Ghislain, Belgium
    "europe-west4",      # Eemshaven, Netherlands
    "europe-west8",      # Milan, Italy
]

# Track which region to use next (round-robin)
_gemini_region_index = 0

def get_next_gemini_region() -> str:
    """Get next Gemini EU region (round-robin for quota distribution)"""
    global _gemini_region_index
    region = GEMINI_EU_REGIONS[_gemini_region_index % len(GEMINI_EU_REGIONS)]
    _gemini_region_index += 1
    return region

def get_gemini_model_with_region() -> str:
    """Get Gemini model ID with next EU region"""
    region = get_next_gemini_region()
    return f"vertex/gemini-2.5-flash-lite@{region}"

# Quick lookup by simple name
MODEL_ALIASES = {
    "gemini": "gemini_flash",
}


def get_model_config(model_id: str = None) -> AIModelConfig:
    """Get model config by ID or alias (defaults to gemini_flash)"""
    if model_id is None:
        model_id = DEFAULT_MODEL

    # Check alias first
    if model_id in MODEL_ALIASES:
        model_id = MODEL_ALIASES[model_id]

    if model_id not in MODEL_CONFIGS:
        raise ValueError(f"Unknown model: {model_id}. Available: {list(MODEL_CONFIGS.keys())}")

    return MODEL_CONFIGS[model_id]


def list_models() -> Dict[str, AIModelConfig]:
    """Get all available models"""
    return MODEL_CONFIGS.copy()
