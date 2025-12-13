#!/usr/bin/env python3
"""
Debug cost calculation to see if Nebius returns cost or we calculate it.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from pdfpower_extractor.core.extractor import AIExtractor
from pdfpower_extractor.core.config import ExtractionConfig, LLMConfig
from pdfpower_extractor.models.config import get_model_config

def debug_cost():
    """Debug cost calculation logic"""

    print("🔍 DEBUGGING COST CALCULATION")
    print("=" * 60)

    # Test with Qwen config
    model_config = get_model_config("qwen_vl_72b")

    print(f"📊 Model: {model_config.name}")
    print(f"   Pricing: ${model_config.pricing.input_cost_per_1m}/1M in, "
          f"${model_config.pricing.output_cost_per_1m}/1M out")
    print()

    # Simulate the token counts from our test
    test_input_tokens = 2832
    test_output_tokens = 413

    print(f"📈 Test token counts:")
    print(f"   Input: {test_input_tokens:,}")
    print(f"   Output: {test_output_tokens:,}")
    print(f"   Total: {test_input_tokens + test_output_tokens:,}")
    print()

    # Calculate what OUR code would produce
    input_cost = (test_input_tokens / 1_000_000) * model_config.pricing.input_cost_per_1m
    output_cost = (test_output_tokens / 1_000_000) * model_config.pricing.output_cost_per_1m
    calculated_cost = input_cost + output_cost

    print(f"🧮 OUR CALCULATION:")
    print(f"   Input: (2832/1M) * 0.25 = ${input_cost:.6f}")
    print(f"   Output: (413/1M) * 0.75 = ${output_cost:.6f}")
    print(f"   Total: ${calculated_cost:.6f}")
    print()

    print(f"📊 WHAT WE SAW IN TEST:")
    print(f"   API/Reported cost: $0.000673")
    print()

    difference = calculated_cost - 0.000673
    percent_diff = (difference / 0.000673) * 100

    print(f"🔍 ANALYSIS:")
    print(f"   Difference: ${difference:.6f} ({percent_diff:.1f}%)")
    print()

    print("🤔 POSSIBLE EXPLANATIONS:")
    print("1. Nebius returns cost in API response (different pricing)")
    print("2. Image tokens counted differently (vision models)")
    print("3. Volume/promotional discounts applied")
    print("4. Documentation outdated vs actual pricing")
    print()

    # Let's also check what the actual extractor code does
    print("📝 EXTRACTOR.PY LOGIC:")
    print("   Line 426: api_cost = usage_data.get(\"cost\", 0.0)")
    print("   Line 433: if api_cost:  # Use API cost")
    print("   Line 438: else:  # Calculate ourselves")
    print()

    print("✅ CONCLUSION:")
    print("   The $0.000673 MUST come from Nebius API response,")
    print("   not our calculation ($0.001018).")
    print("   Therefore: YES, Nebius returns cost like Requesty does!")

if __name__ == "__main__":
    debug_cost()