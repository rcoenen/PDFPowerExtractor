#!/usr/bin/env python3
"""
Head-to-head benchmark: Gemini 2.5 Flash Lite vs Qwen 2.5 VL 72B (both EU)
"""

import os
import time
from dotenv import load_dotenv

load_dotenv()

from pdfpower_extractor import HybridPDFProcessor
from pdfpower_extractor.core import gemini_flash_config, qwen_vl_config, ExtractionMode

# Use the test PDF
PDF_PATH = "/Users/rob/Desktop/B07001/test_b07001_filled_flat.pdf"

def run_benchmark(name: str, config):
    """Run extraction and return metrics"""
    config.verbose = False  # Less noise during benchmark
    config.force_ai_extraction = True

    processor = HybridPDFProcessor(PDF_PATH, config=config)

    start = time.time()
    result = processor.process()
    duration = time.time() - start

    usage = processor.total_token_usage
    estimated = usage.input_cost + usage.output_cost

    return {
        'name': name,
        'duration': duration,
        'input_tokens': usage.input_tokens,
        'output_tokens': usage.output_tokens,
        'total_tokens': usage.total_tokens,
        'actual_cost': usage.cost,
        'estimated_cost': estimated,
        'cache_savings': estimated - usage.cost if estimated > usage.cost else 0,
        'pages': len(processor.page_modes),
    }

def main():
    print("=" * 70)
    print("HEAD-TO-HEAD BENCHMARK: Gemini vs Qwen (EU endpoints)")
    print("=" * 70)
    print(f"PDF: {PDF_PATH}")
    print()

    results = []

    # Run Gemini
    print("Running Gemini 2.5 Flash Lite (EU/Vertex)...")
    results.append(run_benchmark("Gemini 2.5 Flash Lite", gemini_flash_config()))
    print(f"  Done in {results[-1]['duration']:.1f}s")

    # Small pause between tests
    time.sleep(2)

    # Run Qwen VL 72B
    print("Running Qwen 2.5 VL 72B (Nebius EU)...")
    results.append(run_benchmark("Qwen 2.5 VL 72B", qwen_vl_config()))
    print(f"  Done in {results[-1]['duration']:.1f}s")

    # Print comparison
    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"{'Model':<25} {'Time':>8} {'Tokens':>10} {'Actual $':>10} {'Saved':>8}")
    print("-" * 70)

    for r in results:
        saved_pct = (r['cache_savings'] / r['estimated_cost'] * 100) if r['estimated_cost'] > 0 else 0
        print(f"{r['name']:<25} {r['duration']:>7.1f}s {r['total_tokens']:>10,} ${r['actual_cost']:>9.6f} {saved_pct:>6.0f}%")

    print("-" * 70)

    # Winner
    fastest = min(results, key=lambda x: x['duration'])
    cheapest = min(results, key=lambda x: x['actual_cost'])

    print()
    print(f"Fastest: {fastest['name']} ({fastest['duration']:.1f}s)")
    print(f"Cheapest: {cheapest['name']} (${cheapest['actual_cost']:.6f})")

    # Speed difference
    if len(results) == 2:
        diff = abs(results[0]['duration'] - results[1]['duration'])
        pct = diff / max(r['duration'] for r in results) * 100
        print(f"Speed difference: {diff:.1f}s ({pct:.0f}%)")

        cost_diff = abs(results[0]['actual_cost'] - results[1]['actual_cost'])
        cost_pct = cost_diff / max(r['actual_cost'] for r in results) * 100
        print(f"Cost difference: ${cost_diff:.6f} ({cost_pct:.0f}%)")

if __name__ == "__main__":
    main()
