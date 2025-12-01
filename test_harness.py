#!/usr/bin/env python3
"""
Test harness for PDFPowerExtractor

All AI modes are GDPR compliant (EU endpoints only).

Available models:
- gemini: Gemini 2.5 Flash Lite (EU/Vertex) - default
- qwen: Qwen 2.5 VL 72B (Nebius EU)
- mistral: Mistral Small 3.1 24B (Scaleway EU) - FASTEST

Usage:
    python test_harness.py              # Default (Gemini)
    python test_harness.py gemini       # Gemini 2.5 Flash Lite
    python test_harness.py qwen         # Qwen 2.5 VL 72B
    python test_harness.py mistral      # Mistral Small 3.1 (FASTEST)
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from pdfpower_extractor import PDFProcessor
from pdfpower_extractor.core import (
    ExtractionConfig,
    gemini_config,
    qwen_config,
    mistral_config,
)

# Configuration
PDF_PATH = "/Users/rob/Desktop/B07001/test_b07001_filled_flat.pdf"
OUTPUT_DIR = "/Users/rob/Desktop/B07001/_power_pdf_testing/"

# === CONFIG PRESETS ===
CONFIG_MAP = {
    "gemini": gemini_config,
    "qwen": qwen_config,
    "mistral": mistral_config,
}

# Default model
DEFAULT_MODEL = "gemini"

def progress_callback(info):
    """Show progress during extraction"""
    if isinstance(info, dict):
        status = info.get("status", "")
        page = info.get("page", 0)
        total = info.get("total", 0)
        if status == "done" and page == total:
            print(f"  Complete!")
    else:
        print(f"  Progress: {info}%")

def main():
    # Parse command line args
    model_name = sys.argv[1].lower() if len(sys.argv) > 1 else DEFAULT_MODEL

    if model_name not in CONFIG_MAP:
        print(f"ERROR: Unknown model '{model_name}'")
        print(f"Available models: {', '.join(CONFIG_MAP.keys())}")
        sys.exit(1)

    # Get config from preset
    config = CONFIG_MAP[model_name]()
    config.verbose = True

    output_file = os.path.join(OUTPUT_DIR, f"extraction_{model_name}.md")

    # Verify input file exists
    if not os.path.exists(PDF_PATH):
        print(f"ERROR: PDF not found: {PDF_PATH}")
        sys.exit(1)

    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Get model info for display
    model_config = config.get_model_config()
    model_display = model_config.name
    endpoint = model_config.get_endpoint()
    region = "EU" if config.is_eu() else "US"

    print("=" * 60)
    print("PDFPowerExtractor Test Harness")
    print("=" * 60)
    print(f"Input:  {PDF_PATH}")
    print(f"Output: {output_file}")
    print(f"Model:  {model_display}")
    print(f"Region: {region}")
    print("=" * 60)

    # Create processor with config
    processor = PDFProcessor(PDF_PATH, config=config)

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
