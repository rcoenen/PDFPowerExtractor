## 1. Implementation
- [x] 1.1 Update GEMMA_VISION_PROMPT with explicit radio button detection instructions
- [x] 1.2 Add visual symbol descriptions (filled ◉ vs empty ○) to help model distinguish
- [x] 1.3 Update iteration history comments in prompts.py

## 2. Initial Validation
- [x] 2.1 Run extraction on page 4 of test_b07001_filled_flat_010.pdf with Gemma
- [x] 2.2 Verify Q1.9 "Burgerlijke staat" returns `(x) getrouwd`
- [x] 2.3 Save test artifacts to /tmp/gemma_test_page4_v2/ for comparison
- [x] 2.4 Document results in prompt iteration history comments

## 3. Output Consistency Fix
- [x] 3.1 Test page 4 and page 5 to understand output format inconsistency
- [x] 3.2 v3-v6: Various prompt changes - partial success but inconsistent
- [x] 3.3 v7-v15: Extensive testing - found model NEEDS symbols in prompt for detection
- [x] 3.4 Increased DPI from 150 to 300 for better detection
- [x] 3.5 Added normalize_radio_buttons() post-processor to convert ◉/○ to (x)/( )
- [x] 3.6 Final test: 10/10 accuracy, consistent format

## 4. Code Changes
- [x] 4.1 prompts.py: Updated GEMMA_VISION_PROMPT with two-step detection/output instructions
- [x] 4.2 extractor.py: Changed DPI from 150 to 300
- [x] 4.3 extractor.py: Added normalize_radio_buttons() function
- [x] 4.4 config.py: Changed Gemma temperature from 0.1 to 0.0

## Final Status: COMPLETE
- Radio button detection: 10/10 accuracy
- Output format: Consistent (x)/( ) format, no ◉/○ symbols
- Key insight: Model needs symbols in prompt for detection, post-process to normalize output
