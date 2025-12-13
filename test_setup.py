#!/usr/bin/env python3
"""Test PDFPowerExtractor setup"""

import os
import sys

print("Testing PDFPowerExtractor setup...")
print("-" * 50)

# Check Python version
print(f"Python version: {sys.version}")

# Check required modules
modules_to_check = [
    ('click', 'CLI framework'),
    ('PyMuPDF', 'PDF processing'),
    ('pdf2image', 'PDF to image conversion'),
    ('PIL', 'Image processing (Pillow)'),
    ('requests', 'API calls'),
    ('dotenv', 'Environment variables')
]

missing_modules = []

for module_name, description in modules_to_check:
    try:
        if module_name == 'PyMuPDF':
            import fitz
        elif module_name == 'PIL':
            import PIL
        elif module_name == 'dotenv':
            import dotenv
        else:
            __import__(module_name)
        print(f"✓ {module_name} ({description})")
    except ImportError:
        print(f"✗ {module_name} ({description}) - NOT INSTALLED")
        missing_modules.append(module_name)

print("-" * 50)

# Check environment
if os.getenv('OPENROUTER_API_KEY'):
    print("✓ OPENROUTER_API_KEY is set")
else:
    print("✗ OPENROUTER_API_KEY not found in environment")
    print("  Set it with: export OPENROUTER_API_KEY='your-key-here'")

print("-" * 50)

# Check local modules
try:
    from core.processor import PDFProcessor
    from core.analyzer import PDFAnalyzer
    from core.extractor import TextExtractor, AIExtractor
    from models.config import MODEL_CONFIGS, DEFAULT_MODEL
    print("✓ All core modules can be imported")
except ImportError as e:
    print(f"✗ Error importing modules: {e}")

print("-" * 50)

if missing_modules:
    print(f"\n⚠️  Missing modules: {', '.join(missing_modules)}")
    print("Install with: pip install -r requirements.txt")
else:
    print("\n✅ All required modules are installed!")
    
if not os.getenv('OPENROUTER_API_KEY'):
    print("\n⚠️  Don't forget to set your OPENROUTER_API_KEY!")
    
print("\nTo test the extractor:")
print("  python pdfpower.py analyze your-pdf.pdf")
print("  python pdfpower.py extract your-pdf.pdf")