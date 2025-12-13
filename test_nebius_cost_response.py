#!/usr/bin/env python3
"""
Test to see if Nebius returns cost field in response.
"""

import os
import json

# Mock the API response based on your curl test
nebius_text_response = {
    "id": "chatcmpl-7824c8bf18664a6083345b920227cde4",
    "choices": [{
        "finish_reason": "stop",
        "index": 0,
        "logprobs": None,
        "message": {
            "content": "1 + 1 = 2 \n\nIt's a fundamental concept in mathematics! 😊\n",
            "refusal": None,
            "role": "assistant",
            "annotations": None,
            "audio": None,
            "function_call": None,
            "tool_calls": [],
            "reasoning_content": None
        },
        "stop_reason": 106
    }],
    "created": 1765156739,
    "model": "google/gemma-3-27b-it",
    "object": "chat.completion",
    "service_tier": None,
    "system_fingerprint": None,
    "usage": {
        "completion_tokens": 21,
        "prompt_tokens": 18,
        "total_tokens": 39,
        "completion_tokens_details": None,
        "prompt_tokens_details": None
    },
    "prompt_logprobs": None
}

print("🔍 ANALYZING NEBIUS RESPONSE")
print("=" * 60)
print("📄 Response from your curl test (text-only):")
print(json.dumps(nebius_text_response['usage'], indent=2))
print()

# Check for cost field
usage = nebius_text_response.get('usage', {})
if 'cost' in usage:
    print("✅ Found 'cost' field in usage:", usage['cost'])
else:
    print("❌ NO 'cost' field in usage!")
    print("   Fields present:", list(usage.keys()))
print()

print("🤔 So where did $0.000673 come from in our Qwen test?")
print()
print("POSSIBILITIES:")
print("1. Vision/image responses include 'cost' field (text doesn't)")
print("2. Our code calculated it (but we calculated $0.001018)")
print("3. Different endpoint/version returns cost")
print("4. Bug in our cost calculation logic")
print()

# Let's trace through the extractor logic
print("📝 EXTRACTOR.PY LOGIC TRACE:")
print("   Line 426: api_cost = usage_data.get(\"cost\", 0.0)")
print("   - If 'cost' field exists → api_cost = value")
print("   - If no 'cost' field → api_cost = 0.0")
print()
print("   Line 433: if api_cost:  # True if > 0")
print("   - Uses api_cost (from response)")
print()
print("   Line 438: else:  # api_cost = 0")
print("   - Calculates using config pricing")
print()

print("🔍 CONCLUSION FROM YOUR TEST:")
print("   Your curl shows NO 'cost' field in Nebius response.")
print("   Therefore api_cost = 0.0")
print("   Therefore code would CALCULATE cost, not use API cost.")
print()
print("   But our calculation gives $0.001018, not $0.000673!")
print("   SOMETHING DOESN'T ADD UP!")
print()

print("🚨 NEXT STEPS:")
print("1. Check if vision responses include 'cost' field")
print("2. Debug actual API response in extractor.py")
print("3. Add logging to see what's really happening")