# Change: Fix Gemma Radio Button Detection

## Why
Gemma 3 27B incorrectly identifies which radio button is selected in forms. Testing with page 4 of test_b07001_filled_flat_010.pdf showed Gemma selected "geregistreerd partnerschap" when the correct answer was "getrouwd" (Q1.9 Burgerlijke staat). The model confuses filled circles (◉) with empty circles (○).

## What Changes
- Update Gemma vision prompt with explicit radio button detection instructions
- Add visual description of filled vs empty radio button symbols
- Document iteration in prompt comments for future tuning

## Impact
- Affected specs: prompt-system
- Affected code: `pdfpower_extractor/core/prompts.py` (GEMMA_VISION_PROMPT)
- Test case: Page 4, Q1.9 "Burgerlijke staat" - expected `(x) getrouwd`
