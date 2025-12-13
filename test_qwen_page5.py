#!/usr/bin/env python3
"""
Test Qwen2.5 VL 72B extraction on page 5.
"""

import os
import sys
from pathlib import Path
import time
import uuid

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from pdfpower_extractor.core.extractor import AIExtractor
from pdfpower_extractor.core.config import ExtractionConfig, LLMConfig
from pdfpower_extractor.models.config import get_model_config

def test_qwen_page5():
    """Test Qwen VL extraction on page 5 with debug image saving."""

    pdf_path = "/Users/rob/Desktop/B07001/test_b07001_filled_flat_008.pdf"
    page_num = 5

    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return

    print(f"📄 Testing Qwen2.5 VL 72B on page {page_num} of: {Path(pdf_path).name}")
    print(f"   Using simplified prompts (same as Gemma)")
    print(f"   Debug files saved to: /tmp/powerpdf_extracted_images/")
    print()

    # Get model config for Qwen
    try:
        model_config = get_model_config("qwen_vl_72b")
        print(f"✅ Model config loaded: {model_config.name}")
        print(f"   Endpoint: {model_config.endpoint_id}")
        print(f"   Model ID at endpoint: {model_config.model_id_at_endpoint}")
    except Exception as e:
        print(f"❌ Failed to get model config: {e}")
        print("Available models:")
        from pdfpower_extractor.models.config import list_models
        for model_id, config in list_models().items():
            print(f"  - {model_id}: {config.name}")
        return

    # Create extraction config with debug enabled
    config = ExtractionConfig(
        verbose=True,
        log_prompts=True,
        llm=LLMConfig(
            temperature=0.1,
            max_tokens=4000,
            max_retries=3,
            retry_delay_seconds=2,
            timeout_seconds=60,
        )
    )

    # Create extractor
    extractor = AIExtractor(config=config, model_config=model_config)

    # Create a session directory in /tmp/ for this test
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    session_id = str(uuid.uuid4())[:8]
    session_dir = Path(f"/tmp/powerpdf_extracted_images/session_{timestamp}_{session_id}")
    session_dir.mkdir(parents=True, exist_ok=True)

    print(f"📁 Session directory: {session_dir}")
    print()

    # Extract page 5 with debug image saving
    print(f"🔍 Extracting page {page_num}...")
    try:
        result = extractor.extract_page(
            pdf_path=pdf_path,
            page_num=page_num,
            model_config=model_config,
            debug_save_images=True,
            debug_session_dir=str(session_dir),
            use_markdown=True
        )
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return

    print()
    print("=" * 80)
    print(f"📋 RESULTS - Page {page_num}")
    print("=" * 80)
    print(result['content'])

    if result.get('debug_image_path'):
        print(f"💾 Debug image saved to: {result['debug_image_path']}")

    # Check token usage
    usage = result.get('token_usage')
    if usage:
        print(f"🪙 Token usage: {usage.input_tokens} in, {usage.output_tokens} out")
        print(f"💰 Cost: ${usage.cost:.6f}")

    # Save output to file in project test_results
    output_dir = project_root / "test_results"
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f"qwen_page5_{Path(pdf_path).stem}.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Qwen2.5 VL 72B - Page {page_num} - Simplified Prompts\n")
        f.write(f"PDF: {Path(pdf_path).name}\n")
        f.write(f"Timestamp: {result.get('timestamp', 'N/A')}\n")
        f.write("=" * 80 + "\n\n")
        f.write(result['content'])

    print(f"💾 Full output saved to: {output_file}")

    # ALSO save a copy to the /tmp/ debug session directory
    if usage:
        tmp_output_file = session_dir / f"{Path(pdf_path).stem}_page{page_num:03d}_output.txt"
        with open(tmp_output_file, 'w', encoding='utf-8') as f:
            f.write(f"Qwen2.5 VL 72B - Page {page_num} - Simplified Prompts\n")
            f.write(f"PDF: {Path(pdf_path).name}\n")
            f.write(f"Session: {session_dir.name}\n")
            f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Model: {model_config.model_id_at_endpoint}\n")
            f.write(f"Prompt Type: simplified (via Gemma prompts)\n")
            f.write(f"Token Usage: {usage.input_tokens} in, {usage.output_tokens} out\n")
            f.write(f"Cost: ${usage.cost:.6f}\n")
            f.write("=" * 80 + "\n\n")
            f.write(result['content'])

        print(f"💾 Debug output saved to: {tmp_output_file}")

    # Also check the prompt that was used
    print()
    print("🔍 Checking prompt metadata...")

    if result.get('debug_image_path'):
        image_path = Path(result['debug_image_path'])
        prompt_file = image_path.parent / f"{Path(pdf_path).stem}_page{page_num:03d}_prompts.txt"
        if prompt_file.exists():
            with open(prompt_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Extract prompt type
                import re
                match = re.search(r'Prompt Type: (\w+)', content)
                if match:
                    prompt_type = match.group(1)
                    print(f"✅ Used {prompt_type} prompts (as expected for Qwen)")
                else:
                    print("⚠️ Could not determine prompt type from metadata")
        else:
            print("⚠️ Prompt metadata file not found")

    # List all files in debug directory
    print()
    print("📁 Files in debug directory:")
    for file in sorted(session_dir.iterdir()):
        size_kb = file.stat().st_size / 1024
        print(f"  - {file.name} ({size_kb:.1f} KB)")

if __name__ == "__main__":
    test_qwen_page5()