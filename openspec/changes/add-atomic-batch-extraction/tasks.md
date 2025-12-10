# Tasks: Atomic Batch Extraction

## 1. Error Classification
- [x] 1.1 Create `ExtractionError` base class with error categories
- [x] 1.2 Create specific error types: `PaymentError`, `PayloadTooLargeError`, `RateLimitError`, `ServerError`, `ModelResponseError`
- [x] 1.3 Map HTTP status codes to error types in API response handling

## 2. Batch Result Tracking
- [x] 2.1 Create `BatchResult` dataclass to track page-by-page success/failure
- [x] 2.2 Store page number, success/failure, error details, token usage per page
- [x] 2.3 Add `is_complete` property that returns True only if all pages succeeded
- [x] 2.4 Add `success` property (bool) for simple pass/fail check
- [x] 2.5 Add `status` property ("completed", "failed", "partial")
- [x] 2.6 Add `failed_pages` property returning list of (page_num, error_type, message)
- [x] 2.7 Add `error_summary` property with human-readable failure description
- [x] 2.8 Add `content` property containing extracted markdown (empty string if failed)

## 3. Processor Changes
- [x] 3.1 Add `fail_fast: bool = True` parameter to `ExtractionConfig`
- [x] 3.2 Modify `PDFProcessor.process()` to collect errors per page
- [x] 3.3 If `fail_fast=True`, stop on first failure and raise with context
- [x] 3.4 If `fail_fast=False`, continue processing and collect all failures
- [x] 3.5 Return content with error markers (fail_fast=False) or raise ExtractionError (fail_fast=True)

## 4. Error Reporting
- [x] 4.1 Create clear error message format: "Extraction failed on page X of Y: {reason}"
- [x] 4.2 Include partial results info in error (e.g., "5 of 10 pages completed before failure")
- [ ] 4.3 Log all errors to audit log (if enabled)

## 5. Retry Logic (Optional Enhancement)
- [x] 5.1 Add configurable retry for transient errors (429, 5xx)
- [x] 5.2 Implement exponential backoff (2s, 4s, 8s... max 30s)
- [x] 5.3 Respect `retry-after` header from Nebius API
- [x] 5.4 Added retry logic to HuggingFace requests
- [x] 5.5 Document which errors are retryable vs terminal:
      - Retryable: 429 (rate limit), 502, 503, 529 (server errors)
      - Terminal: 401, 402, 403 (auth/payment errors)

## 6. Structured ExtractionError
- [x] 6.1 Create `ExtractionError` class with fields: `message`, `error_code`, `error_type`, `failed_pages`, `pages_completed`, `pages_total`, `partial_content`
- [x] 6.2 Raise `ExtractionError` instead of plain `Exception` on batch failure
- [x] 6.3 Export `ExtractionError` from `pdfpower_extractor` package for callers to import

## 7. Matey-RAG Integration Updates
- [x] 7.1 Update `shared/pdf_extractor.py` to catch `ExtractionError`
- [x] 7.2 Update `app_fastapi.py` job store to include `error_code`, `error_type`, `pages_completed`, `pages_total`
- [x] 7.3 Update `/api/extract-status` response to include new fields (automatic - job dict is returned)
- [ ] 7.4 Update frontend to display structured error info (optional)

## 8. Testing
- [ ] 8.1 Test fail_fast=True stops on first error
- [ ] 8.2 Test fail_fast=False collects all errors
- [x] 8.3 Test error message formatting
- [ ] 8.4 Test partial result reporting
- [x] 8.5 Test ExtractionError fields are correctly populated
- [x] 8.6 Test Matey-RAG catches and propagates ExtractionError fields
