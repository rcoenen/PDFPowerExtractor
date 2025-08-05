# PDFPowerExtractor

**Preserve visual form field relationships when converting PDFs to AI-readable text**

## 🎯 The Problem

The issue isn't that PDF text extraction can't extract questions and answers - it can. The problem is that **questions and answers become disconnected** during extraction. 

When extracting text from a PDF form, traditional tools produce output where the spatial relationship is lost:

```
Page 1:
3.2 Employment Status
3.3 Years of Experience  
3.4 Education Level
...
[hundreds of lines later]
...
● Full-time
☒ 0-2 years
○ Bachelor's Degree
```

To human eyes viewing the PDF, it's obvious that "Full-time" answers question 3.2. But after text extraction, an AI model has no way to reconnect these scattered elements. The visual proximity that makes the relationship clear to humans is completely lost in the extracted text.

## 💡 The Solution

PDFPowerExtractor uses visual AI processing to preserve form field relationships, **enriching PDF-to-text extraction for downstream AI systems** while keeping context structurally sound.

**Why This Matters for AI Systems:**
- AI models need questions and answers in the same context to understand form data
- Traditional extraction breaks spatial relationships that are critical for comprehension
- Enhanced extraction enables accurate AI analysis of form submissions, applications, and surveys
- Preserves the visual context that makes forms interpretable to AI systems

**Key Benefits:**
- ✅ Preserves checkbox states: ☒ (checked) vs ☐ (unchecked)
- ✅ Maintains radio button selections: ● (selected) vs ○ (unselected)  
- ✅ Keeps Q&A relationships intact for AI processing
- ✅ 30-40% cheaper than pure AI processing
- ✅ Feeds clean, contextual data to AI systems for analysis

## 🚀 Installation

### Option 1: Install from PyPI (Coming Soon)
```bash
pip install pdfpower-extractor
```

### Option 2: Install from GitHub
```bash
pip install git+https://github.com/rcoenen/PDFPowerExtractor.git
```

### Option 3: Local Development
```bash
# Clone the repository
git clone https://github.com/rcoenen/PDFPowerExtractor.git
cd PDFPowerExtractor

# Install in development mode
pip install -e .
```

## 🚀 Quick Start

```bash
# Set your OpenRouter API key
export OPENROUTER_API_KEY="your-key-here"

# Extract a PDF (command available globally after installation)
pdfpower extract your-form.pdf

# Or analyze before processing
pdfpower analyze your-form.pdf

# List supported models
pdfpower models
```

## 📦 Using as a Library

```python
from core.processor import HybridPDFProcessor
from core.analyzer import PDFAnalyzer

# Analyze a PDF
analyzer = PDFAnalyzer("your-form.pdf")
summary = analyzer.analyze()
print(f"Potential savings: {summary['savings_percentage']:.1f}%")

# Process a PDF
processor = HybridPDFProcessor("your-form.pdf", "your-openrouter-key")
result = processor.process(model="google/gemini-2.5-flash")
processor.save_results(result, "output.txt")
```

## 💰 Costs

**OpenRouter pricing (August 2025)** - Direct API access may be cheaper

Average cost per 10-page document: **~$0.0014** (less than 0.2 cents)

| Pages | All Form Fields | Typical (36% text) |
|-------|-----------------|-------------------|
| 10    | $0.0023        | $0.0014          |
| 32    | $0.0072        | $0.0045          |
| 100   | $0.0225        | $0.0144          |

## 🧪 Tested Models (August 2025)

### ✅ Models with 100% Accuracy

| Model | Provider | Cost/M tokens (OpenRouter) | Context | Notes |
|-------|----------|---------------------------|---------|-------|
| **google/gemini-2.5-flash** | Google | $0.075/$0.30 | 1M+ | **RECOMMENDED** - Best value |
| anthropic/claude-3-haiku | Anthropic | $0.25/$1.25 | 200K | Reliable backup |

*Note: Costs shown are OpenRouter pricing (August 2025). Direct API access may offer lower rates.*

### ❌ Models That Failed

| Model | Issue | Why It Matters |
|-------|-------|----------------|
| google/gemini-flash-1.5-8b | 50% checkbox accuracy | Version 1.5 insufficient |
| google/gemini-2.5-flash-lite | 50% checkbox accuracy | "Lite" variant insufficient |
| mistral/mistral-small-3.2 | 0% checkbox detection | Cannot see checkbox states |
| openai/gpt-4o-mini | 0% overall accuracy | Complete failure |
| mistral/pixtral-12b | Context too small | 32K < 37K needed per page |

**Critical**: Checkbox detection is the key differentiator. Most models fail here.

## 📋 Technical Requirements

### Critical Context Window Discovery
- **Minimum: 64K tokens** per page
- Each page requires ~37,000 tokens regardless of DPI (100-300)
- Models with <64K context cannot process even a single page

### Processing Requirements
- **Must use 1-page chunks** - Multi-page chunks reduce accuracy
- **DPI: 100-150 optimal** - Higher DPI doesn't improve accuracy
- **Format: PNG, Black & White** - Best compression for form pages

### Why Not Traditional OCR?
We tested traditional OCR approaches:
- **Tesseract**: Cannot detect checkbox states reliably
- **PaddleOCR**: Works but takes 5+ minutes per page, unsuitable for production
- **Resource Requirements**: Would need expensive infrastructure

## 🏗️ Architecture

```
PDFPowerExtractor/
├── pdfpower.py           # Main CLI interface
├── core/
│   ├── analyzer.py       # PDF page content analyzer
│   ├── processor.py      # Hybrid processing engine
│   └── extractor.py      # Text extraction utilities
├── models/
│   └── config.py         # AI model configurations
├── examples/
│   └── sample_form.pdf   # Example PDF form
└── tests/
    └── test_accuracy.py  # Ground truth validation
```

## 🔧 How It Works

1. **Page Analysis**: Analyzes each PDF page to detect form fields vs pure text
2. **Intelligent Routing**:
   - Pure text pages → PyMuPDF extraction (free, instant)
   - Form field pages → AI visual processing (preserves relationships)
3. **Smart Caching**: MD5 fingerprinting prevents unnecessary reprocessing
4. **Result Merging**: Combines all pages in order with processing method labels

## 📊 Features

- **Hybrid Processing**: Automatically chooses optimal method per page
- **Form Preservation**: Maintains visual Q&A relationships
- **Cost Optimization**: ~37% savings through intelligent routing
- **MD5 Caching**: Only regenerates when PDF changes
- **Model Flexibility**: Easy to add new AI models
- **Detailed Reporting**: Shows costs, processing times, and methods

## 🔑 Requirements

- Python 3.8+
- OpenRouter API key
- Dependencies: PyMuPDF, pdf2image, Pillow, requests

## 📝 Example Output

```
HYBRID PDF EXTRACTION RESULTS
================================================================================
Source PDF: application_form.pdf
Source PDF MD5: 7b9f2ea4c8d1e6a3f5b2d9c4e1a7b3f8
Processing Date: 2025-08-05 15:30:00

AI Model Details:
- Model ID: google/gemini-2.5-flash
- Provider: Google via OpenRouter
- Cost: $0.075/$0.30 per million tokens

Processing Summary:
- Text extraction: 11 pages ($0.0000)
- AI processing: 20 pages ($0.0045)
- Total cost: $0.0045 (saved $0.0027)

================================================================================
=== Page 4 (AI Processed) ===
================================================================================
3.2 Employment Status
● Full-time
○ Part-time
○ Self-employed
○ Unemployed

3.3 Years of Experience
☒ 0-2 years
☐ 3-5 years
☐ 5-10 years
☐ 10+ years
```

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines and submit PRs.

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

Built as a solution to the visual-semantic disconnect in PDF form processing, tested extensively on complex multi-language government and enterprise forms to ensure reliability.