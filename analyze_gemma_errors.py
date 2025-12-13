#!/usr/bin/env python3
"""
Analyze specific Gemma errors vs Gemini reference
"""

import re
from pathlib import Path

def extract_field_value(content, field_pattern):
    """Extract field value using regex pattern"""
    pattern = rf'{re.escape(field_pattern)}\s*\n`([^`]+)`'
    match = re.search(pattern, content, re.IGNORECASE)
    return match.group(1) if match else None

def extract_checkbox_state(content, checkbox_label):
    """Extract checkbox state (x) or ( )"""
    # Look for checkbox pattern: - (x) label or - ( ) label
    pattern = rf'- \((.)\)\s*{re.escape(checkbox_label)}'
    match = re.search(pattern, content, re.IGNORECASE)
    return match.group(1) if match else None

def analyze_gemma_errors(gemini_file, gemma_file):
    """Compare Gemini and Gemma outputs for specific errors"""

    with open(gemini_file, 'r') as f:
        gemini = f.read()

    with open(gemma_file, 'r') as f:
        gemma = f.read()

    print("🔍 Gemma Error Analysis")
    print("=" * 60)

    # Test specific fields from your example
    test_fields = [
        ("V-nummer", "0123456789"),
        ("Achternaam", "Brown"),
        ("Voornamen", "Bernicio"),
        ("Geboortedatum", "15-12-1999"),
        ("Geboorteplaats", "Dhaka"),
    ]

    print("\n📋 Field Value Comparison:")
    errors = 0

    for field_name, expected_value in test_fields:
        gemini_value = extract_field_value(gemini, field_name)
        gemma_value = extract_field_value(gemma, field_name)

        print(f"\n{field_name}:")
        print(f"  Gemini: {gemini_value}")
        print(f"  Gemma:  {gemma_value}")

        if gemini_value and gemma_value:
            if gemini_value == gemma_value:
                print(f"  ✅ MATCH")
            else:
                print(f"  ❌ MISMATCH: '{gemini_value}' vs '{gemma_value}'")
                errors += 1
        elif gemini_value and not gemma_value:
            print(f"  ❌ MISSING in Gemma")
            errors += 1
        elif not gemini_value and gemma_value:
            print(f"  ⚠️  Extra field in Gemma")
        else:
            print(f"  ⚠️  Field not found in either")

    # Check checkbox states
    print("\n✅❌ Checkbox State Comparison:")

    # Look for burgerlijke staat (civil status) section
    burgerlijke_pattern = r'Burgerlijke staat.*?\n(.*?)(?=\n\n|\n###|\n##|\n#|$)'

    gemini_burgerlijke = re.search(burgerlijke_pattern, gemini, re.DOTALL | re.IGNORECASE)
    gemma_burgerlijke = re.search(burgerlijke_pattern, gemma, re.DOTALL | re.IGNORECASE)

    if gemini_burgerlijke and gemma_burgerlijke:
        print("\nBurgerlijke staat (Civil Status):")
        print("Gemini selection:")
        print(gemini_burgerlijke.group(0)[:200])
        print("\nGemma selection:")
        print(gemma_burgerlijke.group(0)[:200])

        # Check which option is selected
        gemini_selected = re.findall(r'- \(x\)\s*(.+)', gemini_burgerlijke.group(0))
        gemma_selected = re.findall(r'- \(x\)\s*(.+)', gemma_burgerlijke.group(0))

        print(f"\nGemini selected: {gemini_selected}")
        print(f"Gemma selected: {gemma_selected}")

        if gemini_selected and gemma_selected:
            if gemini_selected[0].strip() != gemma_selected[0].strip():
                print(f"❌ DIFFERENT SELECTION!")
                print(f"   Gemini: {gemini_selected[0]}")
                print(f"   Gemma:  {gemma_selected[0]}")
                errors += 1
            else:
                print(f"✅ Same selection")

    # Check question numbering
    print("\n🔢 Question Numbering Analysis:")

    # Count numbered vs unnumbered questions
    gemini_numbered = len(re.findall(r'#### \d+\.\d+', gemini))
    gemma_numbered = len(re.findall(r'#### \d+\.\d+', gemma))

    gemini_questions = len(re.findall(r'#### ', gemini))
    gemma_questions = len(re.findall(r'### ', gemma))

    print(f"Gemini: {gemini_numbered} numbered questions out of {gemini_questions} total")
    print(f"Gemma:  {gemma_numbered} numbered questions out of {gemma_questions} total")

    if gemini_numbered > 0 and gemma_numbered == 0:
        print("❌ Gemma missing ALL question numbers!")
        errors += 1

    # Summary
    print(f"\n{'='*60}")
    print("📊 SUMMARY")
    print(f"{'='*60}")
    print(f"Total errors detected: {errors}")

    if errors == 0:
        print("✅ No critical errors found")
    elif errors <= 2:
        print("⚠️  Minor issues detected")
    elif errors <= 5:
        print("⚠️  Significant issues detected")
    else:
        print("❌ Critical errors - Gemma output is unreliable")

    return errors

def main():
    import sys

    if len(sys.argv) != 3:
        print("Usage: python analyze_gemma_errors.py <gemini_output.md> <gemma_output.md>")
        sys.exit(1)

    gemini_file = sys.argv[1]
    gemma_file = sys.argv[2]

    if not Path(gemini_file).exists():
        print(f"❌ Gemini file not found: {gemini_file}")
        sys.exit(1)

    if not Path(gemma_file).exists():
        print(f"❌ Gemma file not found: {gemma_file}")
        sys.exit(1)

    errors = analyze_gemma_errors(gemini_file, gemma_file)
    sys.exit(1 if errors > 5 else 0)

if __name__ == '__main__':
    main()