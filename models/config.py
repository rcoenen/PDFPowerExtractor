"""
Model configurations for PDFPowerExtractor
"""

# Model configurations with test results
MODEL_CONFIGS = {
    "google/gemini-2.5-flash": {
        "name": "Google Gemini 2.5 Flash",
        "provider": "Google via OpenRouter",
        "context_window": "1M+ tokens",
        "cost_per_page": 0.000225,  # Based on 32-page = $0.0072
        "accuracy": 100,
        "supports_checkboxes": True,
        "supports_radio": True,
        "supports_text": True,
        "notes": "RECOMMENDED - Best value, fastest"
    },
    "anthropic/claude-3-haiku": {
        "name": "Anthropic Claude 3 Haiku",
        "provider": "Anthropic via OpenRouter",
        "context_window": "200K tokens",
        "cost_per_page": 0.000875,  # Based on 32-page = $0.0280
        "accuracy": 100,
        "supports_checkboxes": True,
        "supports_radio": True,
        "supports_text": True,
        "notes": "Reliable backup option"
    },
    "google/gemini-flash-1.5-8b": {
        "name": "Google Gemini Flash 1.5 8B",
        "provider": "Google via OpenRouter",
        "context_window": "1M tokens",
        "cost_per_page": 0.0001125,
        "accuracy": 83,  # 100% text/radio, 50% checkboxes
        "supports_checkboxes": False,  # Only 50% accuracy
        "supports_radio": True,
        "supports_text": True,
        "notes": "FAILED - Checkbox detection only 50% accurate"
    },
    "google/gemini-2.5-flash-lite": {
        "name": "Google Gemini 2.5 Flash Lite",
        "provider": "Google via OpenRouter",
        "context_window": "1M tokens",
        "cost_per_page": 0.0003,
        "accuracy": 83,  # 100% text/radio, 50% checkboxes
        "supports_checkboxes": False,  # Only 50% accuracy
        "supports_radio": True,
        "supports_text": True,
        "notes": "FAILED - 'Lite' variant has checkbox issues"
    },
    "openai/gpt-4o-mini": {
        "name": "OpenAI GPT-4o Mini",
        "provider": "OpenAI via OpenRouter",
        "context_window": "128K tokens",
        "cost_per_page": 0.00045,
        "accuracy": 0,
        "supports_checkboxes": False,
        "supports_radio": False,
        "supports_text": False,
        "notes": "FAILED - Complete extraction failure"
    },
    "mistral/mistral-small-3.2": {
        "name": "Mistral Small 3.2",
        "provider": "Mistral via OpenRouter",
        "context_window": "128K tokens",
        "cost_per_page": 0.00006,
        "accuracy": 67,
        "supports_checkboxes": False,  # Cannot detect checkbox states
        "supports_radio": True,
        "supports_text": True,
        "notes": "FAILED - No checkbox detection"
    }
}

# Default model based on testing
DEFAULT_MODEL = "google/gemini-2.5-flash"

# Models that passed all tests
VERIFIED_MODELS = [
    "google/gemini-2.5-flash",
    "anthropic/claude-3-haiku"
]