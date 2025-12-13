# Investigation: PAGE_TYPE Concurrency Degradation

## Why

GLM-4.6V-Flash exhibits mysterious quality degradation when PAGE_TYPE classification is added to prompts in concurrent mode (max_parallel_requests=3), but works perfectly in sequential mode (max_parallel_requests=1).

**Empirical Evidence:**
- Sequential processing: 4,472 output tokens across 3 pages (full extraction)
- Concurrent processing: 3,149 output tokens across 3 pages (30% loss, title-only output)
- Standalone API test: Works perfectly with same prompts and images

**Mystery:** Each page gets its own individual API call with identical prompts and images. There is no shared state between concurrent requests. Yet the Z.AI API returns 30% fewer output tokens when requests arrive concurrently.

**Current Mitigation:** max_parallel_requests=1 for Z.AI endpoint (works but 3x slower)

## What Changes

This is an **investigation change** - no code changes until root cause is identified.

**Investigation Goals:**
1. Isolate whether the issue is PAGE_TYPE-specific or general concurrency degradation
2. Determine if Z.AI backend applies adaptive behavior under concurrent load
3. Identify if request timing, batching, or model-specific timeouts are factors
4. Propose definitive solution (fix concurrency support or document sequential-only requirement)

**Deliverables:**
- Test results documenting degradation patterns
- Root cause analysis (or acknowledgment of unknown backend behavior)
- Decision: Fix concurrency or accept sequential-only for PAGE_TYPE

## Impact

**Affected components:**
- `pdfpower_extractor/models/config.py` - Z.AI endpoint configuration (max_parallel_requests)
- `pdfpower_extractor/core/prompts.py` - GLM_VISION_PROMPT with PAGE_TYPE instruction
- `pdfpower_extractor/core/extractor.py` - API request logic
- `pdfpower_extractor/core/processor.py` - ThreadPoolExecutor concurrency control

**User Impact:**
- Sequential processing: 3x slower (41s vs 13s for 3 pages, ~6 minutes for 30 pages)
- Concurrent processing: Unreliable extraction quality (30% content loss)
- Cost: No impact ($0.065 for 30 pages either way)

**Urgency:** Medium - current sequential workaround is functional but slow
