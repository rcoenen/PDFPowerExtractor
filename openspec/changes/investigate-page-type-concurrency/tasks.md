# Investigation Tasks: PAGE_TYPE Concurrency Degradation

## 1. Baseline Testing (Confirm Mystery)
- [ ] 1.1 Run concurrent test WITHOUT PAGE_TYPE (baseline quality check)
- [ ] 1.2 Run concurrent test WITH PAGE_TYPE (confirm degradation)
- [ ] 1.3 Run sequential test WITH PAGE_TYPE (confirm it works)
- [ ] 1.4 Document token counts and quality metrics for all three tests

**Hypothesis to test:** Is degradation PAGE_TYPE-specific or general concurrency issue?

## 2. Timing & Batching Tests
- [ ] 2.1 Test concurrent with 500ms delay between requests (stagger load)
- [ ] 2.2 Test concurrent with 2s delay between requests (avoid batching)
- [ ] 2.3 Test with max_parallel_requests=2 (below concurrency limit)
- [ ] 2.4 Document if timing/parallelism level affects quality

**Hypothesis to test:** Does request timing or hitting the concurrency limit (3) trigger degradation?

## 3. API Response Analysis
- [ ] 3.1 Capture raw JSON responses from concurrent requests (with PAGE_TYPE)
- [ ] 3.2 Capture raw JSON responses from sequential requests (with PAGE_TYPE)
- [ ] 3.3 Compare response metadata: finish_reason, model, usage stats
- [ ] 3.4 Check for hidden truncation or timeout indicators in responses

**Hypothesis to test:** Does Z.AI return different metadata indicating truncation/timeout?

## 4. Prompt Complexity Tests
- [ ] 4.1 Test concurrent with MINIMAL prompt ("extract as markdown")
- [ ] 4.2 Test concurrent with PAGE_TYPE only (no format instructions)
- [ ] 4.3 Test concurrent with full prompt minus PAGE_TYPE
- [ ] 4.4 Identify which prompt component triggers degradation

**Hypothesis to test:** Is PAGE_TYPE adding cognitive load that breaks under concurrency?

## 5. Post-Processing Audit
- [ ] 5.1 Add debug logging before/after normalize_radio_buttons()
- [ ] 5.2 Verify no content stripping in processor.py TOC extraction
- [ ] 5.3 Confirm degradation happens at API level, not post-processing

**Hypothesis to test:** Is PDFPowerExtractor accidentally stripping content?

## 6. External Validation
- [ ] 6.1 Contact Z.AI support about adaptive behavior under concurrent load
- [ ] 6.2 Check Z.AI documentation for batching or timeout policies
- [ ] 6.3 Test with paid GLM-4.6V model (106B) to see if issue is Flash-specific

**Hypothesis to test:** Is this documented Z.AI backend behavior or a bug?

## 7. Decision & Documentation
- [ ] 7.1 Summarize findings in design.md
- [ ] 7.2 Decide: Fix concurrency support OR accept sequential-only
- [ ] 7.3 If sequential-only: Document in config.py and prompts.py
- [ ] 7.4 If fixable: Implement solution and validate
- [ ] 7.5 Update Z.AI endpoint max_parallel_requests to final value

## Testing Environment

**Test PDF:** `/Users/rob/Desktop/B07001/test_b07001_filled_flat.pdf`
**Test Pages:** 1-3 (includes problematic pages 2 and 3)
**Model:** glm-4.6v-flash (glm_4v_flash_zai)
**Endpoint:** Z.AI (https://api.z.ai/api/paas/v4)
**Success Criteria:** 90%+ quality maintained (4,000+ output tokens for 3 pages)

## Priority Order

**Phase 1 (Quick Wins):** Tasks 1.1-1.4, 5.1-5.3 (confirm mystery, rule out post-processing)
**Phase 2 (Root Cause):** Tasks 2.1-2.4, 3.1-3.4, 4.1-4.4 (isolate trigger)
**Phase 3 (Resolution):** Tasks 6.1-6.3, 7.1-7.5 (decide and implement)
