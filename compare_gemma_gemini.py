#!/usr/bin/env python3
"""
Compare Gemma 3 27B vs Gemini 2.5 Flash Lite for PDF extraction

This script:
1. Processes a PDF with Gemini 2.5 (reference)
2. Processes the same PDF with Gemma 3 27B (test)
3. Compares the outputs
4. Determines if Gemma is a good replacement based on similarity
"""

import os
import sys
import argparse
import tempfile
from datetime import datetime
from pathlib import Path

def check_api_keys():
    """Check if required API keys are set"""
    required_keys = {
        'REQUESTY_API_KEY': 'Gemini 2.5 Flash Lite via Requesty EU',
        'NEBIUS_API_KEY': 'Gemma 3 27B via Nebius EU'
    }

    missing = []
    for key, description in required_keys.items():
        if not os.getenv(key):
            missing.append(f"{key} ({description})")

    if missing:
        print("❌ Missing API keys:")
        for key in missing:
            print(f"  - {key}")
        print("\nSet them with:")
        print("  export REQUESTY_API_KEY='your-key'")
        print("  export NEBIUS_API_KEY='your-key'")
        return False

    print("✅ All required API keys are set")
    return True

def extract_with_model(pdf_path, model_id, output_dir):
    """Extract PDF using specified model"""
    from pdfpower_extractor.core.config import ExtractionConfig
    from pdfpower_extractor.core.processor import PDFProcessor
    from pdfpower_extractor.models.config import get_model_config

    print(f"\n📄 Processing with {model_id}...")

    # Get model config to check API key
    model_config = get_model_config(model_id)
    endpoint = model_config.get_endpoint()
    api_key = os.getenv(endpoint.api_key_env_var)

    if not api_key:
        print(f"❌ {endpoint.api_key_env_var} not set")
        return None

    # Create config and processor
    config = ExtractionConfig(model_config_id=model_id)
    processor = PDFProcessor(pdf_path, config=config, api_key=api_key)

    # Process PDF
    try:
        result = processor.process()

        # Save output
        output_file = output_dir / f"{Path(pdf_path).stem}_{model_id}.md"
        processor.save_results(result, str(output_file))

        # Get cost and token info
        cost = processor.last_cost
        token_usage = processor.total_token_usage

        print(f"  ✅ Extraction complete")
        print(f"  💰 Cost: ${cost:.6f}")
        print(f"  🪙 Tokens: {token_usage.input_tokens} input, {token_usage.output_tokens} output")
        print(f"  💾 Saved to: {output_file}")

        return {
            'output_file': output_file,
            'content': result,
            'cost': cost,
            'tokens': token_usage,
            'model': model_config.name
        }

    except Exception as e:
        print(f"❌ Error processing with {model_id}: {e}")
        return None

def compare_outputs(gemini_result, gemma_result):
    """Compare Gemini and Gemma outputs"""
    print(f"\n{'='*60}")
    print("COMPARISON RESULTS")
    print(f"{'='*60}")

    # Basic stats
    print(f"\n📊 Basic Statistics:")
    print(f"  Gemini 2.5: {len(gemini_result['content'])} chars, ${gemini_result['cost']:.6f}")
    print(f"  Gemma 3 27B: {len(gemma_result['content'])} chars, ${gemma_result['cost']:.6f}")
    print(f"  Cost difference: ${gemma_result['cost'] - gemini_result['cost']:.6f}")

    # Simple similarity check (exact match)
    if gemini_result['content'] == gemma_result['content']:
        print(f"\n✅ PERFECT MATCH!")
        print("  Gemma output is identical to Gemini reference")
        return 100.0

    # Calculate similarity percentage
    gemini_lines = gemini_result['content'].split('\n')
    gemma_lines = gemma_result['content'].split('\n')

    # Count matching lines (exact match)
    matching_lines = 0
    total_lines = max(len(gemini_lines), len(gemma_lines))

    for i in range(min(len(gemini_lines), len(gemma_lines))):
        if gemini_lines[i] == gemma_lines[i]:
            matching_lines += 1

    similarity = (matching_lines / total_lines) * 100 if total_lines > 0 else 0

    print(f"\n📈 Similarity Analysis:")
    print(f"  Line-by-line match: {similarity:.1f}%")
    print(f"  Matching lines: {matching_lines} of {total_lines}")

    # Check for key markers
    key_markers = ['☒', '☐', '●', '○']  # Checkboxes and radio buttons

    gemini_markers = sum(1 for char in gemini_result['content'] if char in key_markers)
    gemma_markers = sum(1 for char in gemma_result['content'] if char in key_markers)

    print(f"\n🔘 Form Field Markers:")
    print(f"  Gemini: {gemini_markers} markers")
    print(f"  Gemma: {gemma_markers} markers")

    if gemini_markers != gemma_markers:
        print(f"  ⚠️  Marker count mismatch!")

    # Show first difference
    print(f"\n🔍 First Difference Found:")
    for i in range(min(len(gemini_lines), len(gemma_lines))):
        if gemini_lines[i] != gemma_lines[i]:
            print(f"  Line {i+1}:")
            print(f"    Gemini: {gemini_lines[i][:80]}{'...' if len(gemini_lines[i]) > 80 else ''}")
            print(f"    Gemma:  {gemma_lines[i][:80]}{'...' if len(gemma_lines[i]) > 80 else ''}")
            break

    return similarity

def main():
    parser = argparse.ArgumentParser(description='Compare Gemma 3 27B vs Gemini 2.5 Flash Lite')
    parser.add_argument('pdf_path', help='Path to PDF file to test')
    parser.add_argument('--output-dir', '-o', help='Output directory (default: ./comparison_results)')

    args = parser.parse_args()

    pdf_path = args.pdf_path
    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        sys.exit(1)

    # Set output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path.cwd() / 'comparison_results'

    output_dir.mkdir(exist_ok=True)

    print(f"📊 Gemma vs Gemini Comparison Test")
    print(f"{'='*60}")
    print(f"PDF: {pdf_path}")
    print(f"Output directory: {output_dir}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check API keys
    if not check_api_keys():
        sys.exit(1)

    # Process with Gemini (reference)
    gemini_result = extract_with_model(pdf_path, 'gemini_flash', output_dir)
    if not gemini_result:
        print("❌ Failed to process with Gemini")
        sys.exit(1)

    # Process with Gemma (test)
    gemma_result = extract_with_model(pdf_path, 'gemma_3_27b', output_dir)
    if not gemma_result:
        print("❌ Failed to process with Gemma")
        sys.exit(1)

    # Compare outputs
    similarity = compare_outputs(gemini_result, gemma_result)

    # Recommendation
    print(f"\n{'='*60}")
    print("RECOMMENDATION")
    print(f"{'='*60}")

    if similarity == 100:
        print("✅ STRONG RECOMMENDATION: Use Gemma 3 27B")
        print("   Perfect match with Gemini reference")
        print(f"   Cost savings: ${gemini_result['cost'] - gemma_result['cost']:.6f} per document")
    elif similarity >= 90:
        print("✅ GOOD CANDIDATE: Gemma 3 27B")
        print(f"   High similarity ({similarity:.1f}%) with Gemini")
        print("   Minor differences may be acceptable for some use cases")
    elif similarity >= 70:
        print("⚠️  CAUTION REQUIRED: Gemma 3 27B")
        print(f"   Moderate similarity ({similarity:.1f}%) with Gemini")
        print("   Review differences carefully before adopting")
    else:
        print("❌ NOT RECOMMENDED: Gemma 3 27B")
        print(f"   Low similarity ({similarity:.1f}%) with Gemini")
        print("   Significant differences from reference output")

    # Save comparison report
    report_file = output_dir / f"comparison_report_{Path(pdf_path).stem}.txt"
    with open(report_file, 'w') as f:
        f.write(f"Gemma vs Gemini Comparison Report\n")
        f.write(f"{'='*60}\n")
        f.write(f"PDF: {pdf_path}\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write(f"Similarity Score: {similarity:.1f}%\n")
        f.write(f"Gemini Cost: ${gemini_result['cost']:.6f}\n")
        f.write(f"Gemma Cost: ${gemma_result['cost']:.6f}\n")
        f.write(f"Cost Difference: ${gemma_result['cost'] - gemini_result['cost']:.6f}\n\n")

        f.write("Output Files:\n")
        f.write(f"  Gemini: {gemini_result['output_file']}\n")
        f.write(f"  Gemma: {gemma_result['output_file']}\n")

    print(f"\n📋 Full report saved to: {report_file}")
    print(f"\nTo inspect differences:")
    print(f"  diff '{gemini_result['output_file']}' '{gemma_result['output_file']}'")

if __name__ == '__main__':
    main()