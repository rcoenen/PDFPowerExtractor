# Implementation Tasks: Direct PDF Upload

## Phase 1: Investigation Spike (2-4 hours)

**Goal:** Answer critical unknowns before committing to full implementation.

### 1. Spike Preparation
- [ ] 1.1 Create `/Users/rob/Desktop/B07001/spike_pdf_upload.py` standalone script
- [ ] 1.2 Review Z.AI Files API documentation (if available)
- [ ] 1.3 Review Z.AI chat/completions API docs for file_id parameter support
- [ ] 1.4 Prepare test PDF (single page from test_b07001_filled_flat.pdf)

### 2. Files API Upload Test
- [ ] 2.1 Implement Files API upload (`POST /paas/v4/files`)
- [ ] 2.2 Test with single-page PDF
- [ ] 2.3 Verify file_id returned in response
- [ ] 2.4 Document upload response structure
- [ ] 2.5 Test file retention (check if file accessible after upload)

### 3. Chat Completions Integration Test
- [ ] 3.1 Attempt chat/completions with file_id parameter
- [ ] 3.2 Try different parameter formats (file_id, file, document_id)
- [ ] 3.3 Document what works (or doesn't)
- [ ] 3.4 If works: Test with GLM-4.6V paid (106B) model
- [ ] 3.5 Compare response structure to image-based approach

### 4. Quality Comparison Test
- [ ] 4.1 Process same page via direct PDF upload
- [ ] 4.2 Process same page via image conversion (baseline)
- [ ] 4.3 Compare output tokens, content completeness
- [ ] 4.4 Identify differences (better/worse/same)
- [ ] 4.5 Document quality findings

### 5. Concurrent Processing Test (If 3.x succeeds)
- [ ] 5.1 Upload 3 single-page PDFs
- [ ] 5.2 Process concurrently (3 parallel requests)
- [ ] 5.3 Check for degradation pattern (compare to GitHub issue #227)
- [ ] 5.4 Document if concurrent degradation persists
- [ ] 5.5 Test sequential processing for comparison

### 6. Full PDF Test (If 4.x succeeds)
- [ ] 6.1 Upload full 30-page test_b07001_filled_flat.pdf
- [ ] 6.2 Attempt to process entire PDF in one request
- [ ] 6.3 OR: Test if page_number parameter exists
- [ ] 6.4 Document how multi-page PDFs are handled
- [ ] 6.5 Compare cost and quality to page-by-page image approach

### 7. Spike Findings Report
- [ ] 7.1 Document all test results in `spike_pdf_upload_findings.md`
- [ ] 7.2 Answer critical questions:
   - Does Files API work with GLM-4.6V?
   - Can chat/completions reference uploaded files?
   - Quality vs image-based approach?
   - Concurrent degradation resolved?
- [ ] 7.3 Recommendation: Proceed with integration OR abandon
- [ ] 7.4 Update design.md with findings

---

## Phase 2: Integration (Only if Spike Recommends)

**Prerequisites:**
- ✅ Spike confirms Files API works with vision models
- ✅ Quality equal to or better than images
- ✅ Clear understanding of API usage

### 8. Core Implementation
- [ ] 8.1 Create `pdfpower_extractor/core/pdf_upload.py` module
- [ ] 8.2 Implement `PDFUploader` class with Files API integration
- [ ] 8.3 Add upload caching (avoid re-uploading same PDF)
- [ ] 8.4 Implement file cleanup (delete after processing)
- [ ] 8.5 Add error handling for upload failures

### 9. Extractor Integration
- [ ] 9.1 Add `_extract_via_pdf_upload()` method to AIExtractor
- [ ] 9.2 Detect Z.AI endpoints that support Files API
- [ ] 9.3 Add fallback to image-based if upload fails
- [ ] 9.4 Preserve existing extract_page() behavior (backward compatible)
- [ ] 9.5 Add logging for upload path usage

### 10. Configuration
- [ ] 10.1 Add `use_direct_pdf: bool = False` to ExtractionConfig
- [ ] 10.2 Add `--use-direct-pdf` CLI flag
- [ ] 10.3 Document when to use direct PDF vs images
- [ ] 10.4 Add warning if used with non-Z.AI endpoints
- [ ] 10.5 Update config.py with Files API endpoint details

### 11. Testing
- [ ] 11.1 Add unit tests for PDFUploader class
- [ ] 11.2 Add integration test for upload → extract flow
- [ ] 11.3 Test fallback behavior (upload fails → use images)
- [ ] 11.4 Test with single page, 3 pages, 30 pages
- [ ] 11.5 Validate no regressions in image-based path

### 12. Documentation
- [ ] 12.1 Add usage guide for `--use-direct-pdf` flag
- [ ] 12.2 Document limitations (Z.AI only, experimental)
- [ ] 12.3 Add quality comparison results to README
- [ ] 12.4 Update troubleshooting guide
- [ ] 12.5 Document fallback behavior

---

## Decision Points

**After Task 3.3:** If chat/completions doesn't accept file_id → STOP, abandon proposal
**After Task 4.4:** If quality worse than images → STOP, abandon proposal
**After Task 5.4:** If concurrent degradation persists → Decide if still valuable for sequential use
**After Task 7.3:** DECISION GATE - Proceed to Phase 2 or abandon?

---

## Success Criteria

### Spike Phase
- [ ] All critical questions answered
- [ ] Clear recommendation on whether to proceed
- [ ] If proceeding: Implementation plan validated

### Integration Phase (if applicable)
- [ ] Direct PDF upload works end-to-end
- [ ] Quality ≥ image-based approach
- [ ] No regressions in existing functionality
- [ ] Clear documentation of usage
- [ ] Fallback path tested and working

---

## Estimated Effort

- **Phase 1 (Spike):** 2-4 hours
- **Phase 2 (Integration):** 4-8 hours (if viable)
- **Total (if successful):** 6-12 hours

**Risk:** Could discover non-viable in 1-2 hours (Tasks 2-3), minimal investment
