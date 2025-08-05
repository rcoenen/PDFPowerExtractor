# Quick Start Guide

## 1. Get an OpenRouter API Key

1. Go to [OpenRouter.ai](https://openrouter.ai)
2. Sign up for an account
3. Add credits ($5 is enough for thousands of pages)
4. Copy your API key

## 2. Install PDFPowerExtractor

```bash
# Clone the repository
git clone https://github.com/yourusername/PDFPowerExtractor.git
cd PDFPowerExtractor

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env and add your API key
# OPENROUTER_API_KEY=your-key-here
```

## 3. Test It Out

```bash
# Analyze a PDF to see cost estimates
python pdfpower.py analyze your-form.pdf

# Extract with form preservation
python pdfpower.py extract your-form.pdf

# Check available models
python pdfpower.py models
```

## 4. Understanding the Output

The tool will:
1. Analyze each page to detect form fields
2. Use free text extraction for regular pages
3. Use AI vision for pages with forms
4. Save you ~37% on processing costs
5. Cache results (same PDF = instant retrieval)

## Tips

- First run takes longer (processing)
- Subsequent runs are instant (cached by MD5)
- Use `--force` to regenerate
- Default model (Gemini 2.5 Flash) is recommended
- Check `extracted-*.txt` for results