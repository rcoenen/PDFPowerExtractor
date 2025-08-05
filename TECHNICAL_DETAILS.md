# Technical Details & Research Findings

## 🔬 Complete Testing Summary

### Context Window Discovery
One of our most critical findings was that **each PDF page requires ~37,000 tokens** regardless of DPI settings:
- 100 DPI: ~37,000 tokens
- 150 DPI: ~37,000 tokens  
- 200 DPI: ~37,000 tokens
- 300 DPI: ~37,000 tokens

This means models need at least 64K context window to process even a single page.

### Chunk Size Testing
We tested processing multiple pages together and found:
- 1-page chunks: 100% accuracy ✅
- 2-page chunks: <100% accuracy (missed email fields)
- 3+ page chunks: Accuracy degrades further

**Conclusion**: Single-page processing is mandatory for reliability.

### Image Format Optimization
- **PNG vs JPEG**: PNG is 4x smaller for binary (B&W) images
- **Color Mode**: Black & white (1-bit) is optimal
- **Preprocessing**: Not required for AI models (unlike traditional OCR)

## 🧪 Traditional OCR Research

### Why We Moved Away from OCR

#### Tesseract Issues
- Cannot reliably distinguish checkbox states
- Produces inconsistent symbols (@, {, 0, C) for checkboxes
- Radio buttons work but checkboxes are problematic at all DPIs

#### PaddleOCR Testing
**Pros**:
- Successfully detected radio buttons (lowercase 'o' vs uppercase 'O')
- Extracted text fields perfectly
- Could work with pdftk flatten + preprocessing

**Cons**:
- 5+ minutes per page processing time
- Large model downloads (~100MB+)
- Brought M2 Mac to a halt despite ARM GPU
- Cold start issues for web deployment
- Would require expensive infrastructure

## 📊 Model Testing Details

### Complete Model Comparison

| Model | Text Fields | Radio Buttons | Checkboxes | Cost/32pg | Verdict |
|-------|-------------|---------------|------------|-----------|---------|
| google/gemini-2.5-flash | ✅ 100% | ✅ 100% | ✅ 100% | $0.0072 | **BEST** |
| anthropic/claude-3-haiku | ✅ 100% | ✅ 100% | ✅ 100% | $0.0280 | Backup |
| google/gemini-flash-1.5-8b | ✅ 100% | ✅ 100% | ❌ 50% | $0.0036 | Failed |
| mistral/mistral-small-3.2 | ✅ 100% | ✅ 100% | ❌ 0% | $0.0019 | Failed |
| openai/gpt-4o-mini | ❌ 0% | ❌ 0% | ❌ 0% | $0.0144 | Failed |

### Key Finding: Checkbox Detection
Checkbox detection is the critical differentiator. Most models can handle text and radio buttons but fail on checkboxes in B&W images.

## 🔧 Implementation Notes

### PDF Processing Pipeline
1. **Analyze pages** to detect form fields vs pure text
2. **Route intelligently**:
   - Pure text → PyMuPDF extraction (free)
   - Form pages → PNG conversion → AI processing
3. **MD5 fingerprinting** for intelligent caching
4. **Merge results** maintaining original page order

### Preprocessing Not Required
Unlike traditional OCR, AI vision models don't need:
- PDF flattening (tested with PyMuPDF/fitz)
- Complex image preprocessing
- Threshold adjustments
- Morphological operations

The models work directly on PNG conversions.

### Cost Optimization Through Routing
Typical PDFs have ~36% pure text pages, resulting in:
- Full AI processing: $0.0072 per 32-page PDF
- Hybrid processing: $0.0045 per 32-page PDF
- Savings: 37.5%

## 🚀 Production Recommendations

### Deployment Requirements
- OpenRouter API key (for model access)
- Poppler (for pdf2image)
- 64K+ context window models only
- Single-page processing pipeline

### Performance Expectations
- Text extraction: <0.1s per page
- AI processing: 3-7s per page
- First run: Full processing time
- Subsequent runs: Instant (MD5 cache hit)

### Scaling Considerations
- Process pages in parallel where possible
- Cache results by PDF MD5 hash
- Use webhooks for async processing
- Consider queue system for large batches