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
# Set your API key (choose one provider)
export REQUESTY_API_KEY="your-key"      # For Gemini Flash (EU)
export SCW_SECRET_KEY="your-key"        # For Mistral Small (EU)
export NEBIUS_API_KEY="your-key"        # For Qwen VL 72B (EU)

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

## 🧪 Tested Models (November 2025)

### ✅ Models with 100% Accuracy (EU/GDPR Compliant)

| Model | Provider | Speed | Input /1M | Output /1M | Notes |
|-------|----------|-------|-----------|------------|-------|
| **Mistral Small 3.1 24B** | Scaleway (Paris) | 4.1s ⚡ | €0.15 | €0.35 | **FASTEST** |
| Gemini 2.5 Flash Lite | Requesty → Vertex EU | 4.8s | $0.10 | $0.40 | Best value |
| Qwen 2.5 VL 72B | Nebius (Netherlands) | 12.3s | $0.13 | $0.40 | Most thorough |

All models are **100% GDPR compliant** - data processed exclusively in EU data centers.

### ❌ Models That Failed

| Model | Provider | Issue |
|-------|----------|-------|
| Nemotron Nano V2 VL 12B | Nebius EU | Severe hallucination - invents fake fields, repeats content |
| Pixtral 12B | Scaleway EU | No radio button symbol output |
| Gemma 3 27B | Nebius/Scaleway EU | OCR errors (Z→2 substitution) |
| GPT-4.1 Nano | Azure Sweden | ~90% radio button accuracy |
| google/gemini-flash-1.5-8b | OpenRouter | 50% checkbox accuracy |
| openai/gpt-4o-mini | OpenRouter | Complete extraction failure |

**Critical**: Radio button and checkbox detection is the key differentiator. Most models fail here.

### ⚠️ Nemotron VL Detailed Notes

We tested **Nemotron Nano V2 VL 12B** via Nebius EU ($0.07/$0.20 per 1M tokens - 43% cheaper than Gemini). Despite the cost advantage:

- **Hallucination**: Model invents fake numbered questions (e.g., generates 4.85, 4.86... 4.92 when only 4.8 exists)
- **Repetition loops**: Repeats same question until hitting token limit (4000 tokens)
- **Poor radio detection**: Outputs options as plain text without `(x)`/`( )` selection markers
- **Output bloat**: Produces 2x the output of Gemini (48K vs 26K chars) due to fabricated content

Despite extensive prompt engineering (anti-hallucination rules, `/no_think` control token, simplified prompts), the model cannot reliably extract form data. **Not recommended for production use.**

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
- API key for one of the EU providers:
  - `REQUESTY_API_KEY` - Gemini Flash via Requesty EU
  - `SCW_SECRET_KEY` - Mistral Small via Scaleway (Paris)
  - `NEBIUS_API_KEY` - Qwen VL 72B via Nebius (Netherlands)
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