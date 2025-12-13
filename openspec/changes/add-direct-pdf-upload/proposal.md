# Add Direct PDF Upload Support via Z.AI Files API

## Why

Currently we convert PDFs to 150 DPI WEBP images (one per page) before sending to GLM-4.6V models. This approach has limitations:

1. **Quality loss**: Image conversion at 150 DPI loses PDF's native text layer and vector graphics
2. **Concurrent degradation**: Complex prompts cause 50% output reduction when processing multiple images concurrently (documented in GitHub issue #227)
3. **Conversion overhead**: pdf2image conversion adds processing time and complexity
4. **Lost PDF features**: Cannot leverage PDF's native structure (text layer, metadata, annotations)

**Z.AI provides a Files API** (`/paas/v4/files`) that accepts PDFs up to 100MB, which could bypass these limitations.

## What Changes

Add **experimental** direct PDF upload capability alongside existing image-based processing:

1. **New PDF upload module** - Implement Z.AI Files API integration
2. **Test spike with paid model** - Validate GLM-4.6V (106B) can handle full 30-page PDFs directly
3. **Comparison framework** - Compare direct PDF vs image-based quality and performance
4. **Keep both approaches** - Maintain image-based as fallback (proven to work)

**Scope:**
- ✅ Add PDF upload capability for Z.AI endpoints
- ✅ Test with paid GLM-4.6V (106B) model
- ✅ Document quality comparison (direct PDF vs images)
- ❌ NOT replacing image-based processing yet (experimental only)
- ❌ NOT changing default behavior (opt-in flag for testing)

## Impact

**Potential Benefits (if successful):**
- Bypass concurrent degradation issue (different API path)
- Better quality (native PDF processing vs 150 DPI images)
- Simpler pipeline (no image conversion overhead)
- Access to PDF text layer (hybrid approach possible)

**Risks:**
- Z.AI Files API may be for translation only (not vision/OCR)
- Model may not support PDF input (could convert internally anyway)
- Concurrent degradation might still occur (same backend)
- API costs may differ (unknown pricing for file-based processing)

**Affected Components:**
- `pdfpower_extractor/core/extractor.py` - Add PDF upload capability
- `pdfpower_extractor/models/config.py` - Add Files API endpoint configuration
- New module: `pdfpower_extractor/core/pdf_upload.py` - Files API integration
- CLI: Optional `--use-direct-pdf` flag for testing

**Non-Goals:**
- NOT removing image-based processing (keep as proven fallback)
- NOT changing default behavior (experimental feature)
- NOT supporting non-Z.AI providers (Files API is Z.AI-specific)
