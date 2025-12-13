# Technical Design: Direct PDF Upload via Z.AI Files API

## Context

We discovered Z.AI provides a Files API (`POST /paas/v4/files`) that accepts PDFs directly (up to 100MB). This could potentially bypass the current image conversion approach and solve the concurrent degradation issue.

**Current Approach:**
```
PDF → pdf2image (150 DPI) → WEBP → base64 → /chat/completions → Model
```

**Proposed Alternative:**
```
PDF → /files upload → file_id → /chat/completions (with file_id?) → Model
```

## Open Questions (Critical)

### 1. Is Files API for Vision Models?

**Question:** Does Z.AI's Files API support vision/OCR tasks, or is it only for translation with auxiliary files (glossaries)?

**API Description says:**
> "This API is designed for uploading auxiliary files (such as glossaries, terminology lists) to support the translation service."

**Evidence:**
- ❌ Description mentions "translation service" specifically
- ❌ Examples show glossaries, terminology lists (not OCR documents)
- ✅ Accepts PDFs (suggests document support)
- ❓ No documentation of vision model compatibility

**Decision needed:** Test if GLM-4.6V can reference uploaded files, or if Files API is translation-only.

### 2. How to Reference Uploaded Files?

**Question:** Does `/chat/completions` accept a file_id parameter to reference uploaded PDFs?

**Current unknowns:**
- Parameter name (`file_id`, `file`, `document_id`?)
- Request format (JSON field, multipart, header?)
- Multiple file support (process 30 pages as 30 uploads or 1 PDF upload?)

**Need to:**
- Read Z.AI chat/completions API docs
- Test if file_id is accepted
- Determine if model processes entire PDF or needs page numbers

### 3. Does Model Convert to Images Internally?

**Question:** If we upload PDF, does GLM-4.6V:
- A) Process PDF natively (text layer + layout)
- B) Convert to images internally (same as our approach)
- C) Reject PDF for vision models

**Impact:**
- If (A): Major quality improvement
- If (B): No advantage, adds complexity
- If (C): Files API unusable for OCR

### 4. Concurrent Processing

**Question:** Would direct PDF upload bypass the concurrent degradation issue?

**Scenarios:**
1. Upload 1 PDF with 30 pages → Model processes all pages → Returns combined output
   - *Unclear:* How does concurrency work here?
2. Upload 30 separate 1-page PDFs → Process concurrently → Could still degrade
   - *Likely:* Same backend, same issue

**Unknown:** Whether Files API uses different serving infrastructure.

## Proposed Architecture

### Phase 1: Investigation Spike

**Goal:** Answer open questions before full implementation

```python
# Spike script (standalone, not integrated)
class PDFUploadSpike:
    def test_upload():
        # 1. Upload test PDF to /files
        # 2. Attempt to reference in /chat/completions
        # 3. Document what works/doesn't work

    def test_concurrent():
        # Upload 3 PDFs, process concurrently
        # Compare quality to image-based approach

    def test_full_pdf():
        # Upload 30-page PDF
        # See if model can process entire document
```

**Deliverable:** Report documenting:
- ✅/❌ Files API compatible with GLM-4.6V
- ✅/❌ Concurrent processing works
- ✅/❌ Quality better than images
- ✅/❌ Pricing acceptable

### Phase 2: Integration (If Spike Succeeds)

Only proceed if spike proves viable.

```python
class AIExtractor:
    def extract_page(self, pdf_path, page_num, use_direct_pdf=False):
        if use_direct_pdf and self._supports_pdf_upload():
            return self._extract_via_pdf_upload(pdf_path, page_num)
        else:
            return self._extract_via_image(pdf_path, page_num)  # Current
```

**Config flag:**
```python
class ExtractionConfig:
    use_direct_pdf: bool = False  # Experimental, opt-in
```

## Decision Criteria

### When to Use Direct PDF Upload

**If spike succeeds:**
- ✅ Use for: Single-page or sequential processing
- ✅ Use for: Large PDFs where quality matters more than speed
- ❌ Avoid: If concurrent degradation persists
- ❌ Avoid: If quality is worse than images

**Fallback strategy:**
- Keep image-based as default
- Direct PDF as opt-in experimental feature
- Monitor production usage before making default

### When to Abandon Direct PDF

**Abandon if:**
- Files API doesn't support vision models
- chat/completions doesn't accept file references
- Quality worse than image-based approach
- Concurrent degradation still occurs
- Pricing significantly higher

## Implementation Plan (Conditional)

### Spike Phase (Tasks 1.1-1.6)
1. Create standalone spike script
2. Test Files API upload
3. Test chat/completions with file_id
4. Compare quality (direct PDF vs images)
5. Test concurrent processing
6. Document findings

### Integration Phase (If Viable)
1. Add pdf_upload.py module
2. Extend AIExtractor with upload capability
3. Add --use-direct-pdf CLI flag
4. Document usage and limitations
5. Add tests for upload path

## Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Files API is translation-only | High | Blocks proposal | Spike discovers early (1-2 hours work) |
| No file_id support in chat | Medium | Blocks proposal | Spike discovers early |
| Quality worse than images | Low | Reduces value | Keep image-based as default |
| Same concurrent degradation | Medium | Reduces value | Document, keep sequential option |
| Undocumented API changes | Low | Future breakage | Monitor, maintain fallback |

## Success Metrics

**Spike Success:**
- [ ] Files API accepts PDF upload
- [ ] chat/completions accepts file_id reference
- [ ] Model produces output (not error)
- [ ] Output quality ≥ image-based approach

**Integration Success:**
- [ ] Direct PDF extraction works end-to-end
- [ ] Quality maintained or improved vs images
- [ ] No regressions in existing image-based path
- [ ] Clear documentation of when to use each approach

## Open Questions for User

Before starting spike, clarify:

1. **Model preference:** Should spike test Flash (9B) or paid (106B)?
   - *Suggestion:* Start with paid (106B) since it has higher capacity

2. **Test scope:** Full 30-page PDF or start with single page?
   - *Suggestion:* Start single-page, then 3-page, then 30-page

3. **Quality bar:** What quality threshold makes this worthwhile?
   - *Suggestion:* Must match or exceed current image-based quality

4. **Timeline:** Is this urgent or exploratory?
   - *Suggestion:* Spike should take 2-4 hours, can decide after
