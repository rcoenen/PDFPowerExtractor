#!/usr/bin/env python3
"""
Test harness for PDFPowerExtractor

All AI modes are GDPR compliant (EU endpoints only).

Available modes:
- text_only: Pure PyMuPDF extraction (free, instant) - 100% accurate
- gemini: Gemini 2.5 Flash Lite (EU/Vertex) - 100% accurate
- qwen: Qwen 2.5 VL 72B (Nebius EU) - 100% accurate
- mistral: Mistral Small 3.1 24B (Scaleway EU) - 100% accurate, FASTEST

Usage:
    python test_harness.py                    # Uses default mode (text_only)
    python test_harness.py text_only          # Text extraction only (FREE)
    python test_harness.py gemini             # Gemini 2.5 Flash Lite (100% accurate)
    python test_harness.py qwen               # Qwen 2.5 VL 72B (100% accurate)
    python test_harness.py mistral            # Mistral Small 3.1 (FASTEST, 100% accurate)
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from pdfpower_extractor import HybridPDFProcessor
from pdfpower_extractor.core import (
    ExtractionConfig,
    ExtractionMode,
    OutputFormat,
    LLMConfig,
    text_only_config,
    gemini_flash_config,
    qwen_vl_config,
    mistral_small_config,
)

# Configuration
PDF_PATH = "/Users/rob/Desktop/B07001/test_b07001_filled_flat.pdf"
OUTPUT_DIR = "/Users/rob/Desktop/B07001/_power_pdf_testing/"

# === CONFIG PRESETS ===
# All AI modes are GDPR compliant (EU endpoints only)
CONFIG_MAP = {
    "text_only": text_only_config,
    "gemini": gemini_flash_config,
    "qwen": qwen_vl_config,
    "mistral": mistral_small_config,
}

# Default mode - change this or pass as command line arg
DEFAULT_MODE = "text_only"

def progress_callback(info):
    """Show progress during extraction"""
    if isinstance(info, dict):
        status = info.get("status", "")
        page = info.get("page", 0)
        total = info.get("total", 0)
        mode = info.get("mode", "")
        if status == "start":
            print(f"  Processing page {page}/{total} ({mode})...")
        elif status == "done" and mode == "complete":
            print(f"  Complete!")
    else:
        print(f"  Progress: {info}%")

def main():
    # Parse command line args
    mode_name = sys.argv[1].lower() if len(sys.argv) > 1 else DEFAULT_MODE

    if mode_name not in CONFIG_MAP:
        print(f"ERROR: Unknown mode '{mode_name}'")
        print(f"Available modes: {', '.join(CONFIG_MAP.keys())}")
        sys.exit(1)

    # Get config from preset
    config = CONFIG_MAP[mode_name]()
    config.verbose = True

    # Force AI extraction for non-text-only modes
    if config.mode == ExtractionMode.AI:
        config.force_ai_extraction = True

    output_file = os.path.join(OUTPUT_DIR, f"extraction_{mode_name}.txt")

    # Verify input file exists
    if not os.path.exists(PDF_PATH):
        print(f"ERROR: PDF not found: {PDF_PATH}")
        sys.exit(1)

    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Get model info for display
    model_config = config.get_model_config()
    if model_config:
        model_name = model_config.name
        endpoint = model_config.get_endpoint()
        region = "EU" if config.is_eu() else "US"
    else:
        model_name = "None (text extraction)"
        region = "N/A"

    print("=" * 60)
    print("PDFPowerExtractor Test Harness")
    print("=" * 60)
    print(f"Input:  {PDF_PATH}")
    print(f"Output: {output_file}")
    print(f"Mode:   {mode_name}")
    print(f"Model:  {model_name}")
    print(f"Region: {region}")
    print("=" * 60)

    # Create processor with config
    processor = HybridPDFProcessor(PDF_PATH, config=config)

    # Process the PDF
    print(f"\nProcessing PDF...")
    result = processor.process(progress_callback=progress_callback)

    # Save results
    processor.save_results(result, output_file)

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Output saved to: {output_file}")
    print(f"Processing time: {processor.last_duration:.1f} seconds")
    print(f"Total AI cost: ${processor.last_cost:.4f}")

    # Show validation summary if any
    if processor.validation_results:
        errors = sum(1 for v in processor.validation_results.values() if not v.is_valid)
        print(f"Validation: {len(processor.validation_results)} pages checked, {errors} with issues")

    print("=" * 60)

if __name__ == "__main__":
    main()
