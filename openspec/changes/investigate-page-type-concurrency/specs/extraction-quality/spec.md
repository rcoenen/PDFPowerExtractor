# Extraction Quality Investigation

## ADDED Requirements

### Requirement: Concurrent PAGE_TYPE Extraction Quality
The system SHALL maintain extraction quality when using PAGE_TYPE classification in concurrent processing mode.

**Current Status:** Investigation in progress - degradation observed with GLM-4.6V-Flash

**Expected Behavior:**
- Concurrent processing (max_parallel=3) SHALL produce equivalent output quality to sequential processing (max_parallel=1)
- PAGE_TYPE classification SHALL NOT cause content degradation regardless of concurrency level
- Output token counts SHALL be consistent within 10% margin between sequential and concurrent modes

#### Scenario: Concurrent extraction with PAGE_TYPE
- **GIVEN** GLM-4.6V-Flash model with PAGE_TYPE instruction in prompt
- **WHEN** processing 3 pages concurrently (max_parallel_requests=3)
- **THEN** output SHALL contain full content extraction (not title-only)
- **AND** output tokens SHALL be ≥90% of sequential processing baseline

#### Scenario: Sequential extraction with PAGE_TYPE
- **GIVEN** GLM-4.6V-Flash model with PAGE_TYPE instruction in prompt
- **WHEN** processing 3 pages sequentially (max_parallel_requests=1)
- **THEN** output SHALL contain full content extraction
- **AND** output tokens SHALL match baseline (~4,400 tokens for 3 pages)

#### Scenario: Quality consistency across concurrency modes
- **GIVEN** identical prompts, images, and parameters
- **WHEN** processing same pages in sequential vs concurrent mode
- **THEN** content quality SHALL be equivalent
- **AND** token count variation SHALL be <10%

### Requirement: Investigation Test Coverage
The system SHALL include tests to validate PAGE_TYPE extraction quality under various concurrency conditions.

#### Scenario: Baseline quality test without PAGE_TYPE
- **GIVEN** GLM-4.6V-Flash model WITHOUT PAGE_TYPE instruction
- **WHEN** processing pages concurrently (max_parallel_requests=3)
- **THEN** extraction quality SHALL be maintained (baseline established)

#### Scenario: Timing variation test
- **GIVEN** GLM-4.6V-Flash model WITH PAGE_TYPE instruction
- **WHEN** processing with staggered request timing (500ms, 2s delays)
- **THEN** quality impact SHALL be measured and documented

#### Scenario: API response metadata analysis
- **GIVEN** concurrent and sequential test runs
- **WHEN** capturing raw API responses
- **THEN** finish_reason, usage stats, and response metadata SHALL be compared
- **AND** any truncation or timeout indicators SHALL be identified

### Requirement: Root Cause Documentation
Investigation findings SHALL be documented in design.md including:
- Empirical test results with token counts and quality metrics
- Identified root cause or acknowledgment of unknown backend behavior
- Decision on concurrent support: fix, accept sequential-only, or alternative solution
- Mitigation strategy and configuration recommendations

#### Scenario: Investigation completion
- **GIVEN** all investigation tasks completed
- **WHEN** root cause is identified or exhausted
- **THEN** findings SHALL be documented in design.md
- **AND** decision SHALL be made on concurrent PAGE_TYPE support
- **AND** code SHALL be updated to reflect final configuration
