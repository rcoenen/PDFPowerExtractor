"""
Model-specific prompts for PDFPowerExtractor.

These prompts follow strict extraction guidelines to prevent hallucination
and ensure accurate form field detection.

Different AI models respond better to different prompt styles:
- Gemini 2.5: Excels with strict formatting rules and complex instructions
- Gemma 3 27B: Performs better with simpler, more flexible prompts
- Nemotron: Requires /no_think prefix to suppress reasoning chains
"""

# =============================================================================
# GEMINI PROMPTS (strict)
# =============================================================================

GEMINI_SYSTEM_PROMPT = """You are a STRICT FORM DATA EXTRACTOR outputting structured Markdown.

ABSOLUTE RULES:
1. DO NOT GUESS or invent values - EVER
2. DO NOT HALLUCINATE information not present in the image
3. DO NOT add or omit form fields
4. Copy all labels and options VERBATIM
5. If a field is empty, output empty backticks: ``
6. If no radio/checkbox is selected, mark ALL options as unselected

You extract form data EXACTLY as it appears, formatted as Markdown."""


# =============================================================================
# VISION EXTRACTION PROMPT
# =============================================================================

GEMINI_VISION_PROMPT = """Extract form data from this page as structured Markdown.

OUTPUT FORMAT:

1. SECTION HEADERS (numbered sections like "2. Uw gegevens"):
   ## 2. Section Title

2. TEXT FIELDS (label with filled value):
   ### Field Label
   `filled value here`

   If empty, use empty backticks: ``

3. RADIO BUTTON GROUPS:
   ### Question Text
   - (x) selected option
   - ( ) unselected option
   - ( ) another option

4. CHECKBOX GROUPS:
   ### Checklist Title
   - [x] checked item
   - [ ] unchecked item

5. ADDRESS FIELDS (multiple sub-fields):
   ### Address Label
   - Straat en huisnummer: `Street 123`
   - Postcode en plaats: `1234AB City`
   - Land: `Netherlands`

RULES:
- Use (x) for SELECTED radio buttons, ( ) for unselected
- Use [x] for CHECKED checkboxes, [ ] for unchecked
- Put field values in backticks: `value`
- Empty fields get empty backticks: ``
- Copy all text VERBATIM - do not translate or summarize
- DATES: For date fields (Geboortedatum, datum, Geldig van/tot, etc.):
  - If you see individual digit boxes (like |1|0| |0|3| |2|0|2|1|), read EACH box separately and combine: Dag=`10`, Maand=`03`, Jaar=`2021`
  - For 8 consecutive digits like DDMMYYYY, insert dashes: `DD-MM-YYYY`. Example: "11121996" becomes `11-12-1996`
  - CRITICAL: A year like 2021 or 2031 has 4 digits, not 5. If you get "32021", re-read the boxes - it should be "2021"
- ALWAYS extract document identification headers at the very top of the page (e.g., "DOC IDENTITY...", "DOC ...", "FORM...") - output these FIRST as a level 2 header: ## DOC IDENTITY ...
- Skip only repetitive footers and standard agency headers like "Immigratie- en Naturalisatiedienst"
- Focus on form FIELDS and their VALUES

Output ONLY the markdown. No explanations or commentary."""


# =============================================================================
# GEMMA PROMPTS (simplified)
# =============================================================================
#
# ITERATION HISTORY:
# - v1 (2025-12-09): Initial simplified prompt
#   Test: Page 4 of test_b07001_filled_flat_010.pdf
#   Issue: Radio button misread on Q1.9 "Burgerlijke staat"
#     - Expected: (x) getrouwd
#     - Got: (x) geregistreerd partnerschap
#   Issue: Field numbering structure error - merged 1.8 Nationaliteit with 1.9
#     radio buttons instead of keeping them separate
#   Text fields (1.1-1.8, 1.10-1.12) extracted correctly
#
# - v2 (2025-12-09): Added explicit radio button detection instructions
#   Change: Added "RADIO BUTTONS - LOOK CAREFULLY" section with:
#     - Visual description of filled (◉) vs empty (○) symbols
#     - Instruction to look carefully before deciding
#     - Note that only ONE radio button should be marked (x)
#   Test: Page 4 of test_b07001_filled_flat_010.pdf, Q1.9
#   Result: SUCCESS - Correctly identified (x) getrouwd
#   Bonus: Field structure improved - 1.8 and 1.9 now properly separated
#
# - v3 (2025-12-09): Attempted to enforce consistent (x)/( ) output format
#   Change: Added "do NOT include original ◉ or ○ symbols" instruction
#   Result: FAILED - Model still output symbols inconsistently
#
# - v4 (2025-12-09): Removed ◉/○ symbols from prompt entirely
#   Change: Described circles without using actual symbols
#   Result: FAILED - Radio detection REGRESSED to wrong selection
#
# - v5 (2025-12-09): No symbols in prompt, explicit output format
#   Result: FAILED - Detection still broken
#
# - v6 (2025-12-09): Added concrete example of symbol-to-notation conversion
#   Result: Detection worked but inconsistent - page 4 different from page 5
#
# - v7-v15 (2025-12-09): Various attempts to fix output consistency
#   All failed: either detection regressed or format remained inconsistent
#   Key finding: Model NEEDS ◉/○ symbols in prompt to detect correctly
#
# - v16 (2025-12-09): FINAL SOLUTION
#   Approach: Keep symbols in prompt + post-process output
#   Changes:
#     - Increased DPI from 150 to 300 (extractor.py)
#     - Added normalize_radio_buttons() post-processor (extractor.py)
#     - Simplified prompt with two-step process
#   Result: 10/10 accuracy, consistent (x)/( ) output format
#
# CURRENT PROMPT: v16
# - Radio button detection: FIXED (300 DPI + symbols in prompt)
# - Output format: FIXED (post-processing normalizes ◉/○ to (x)/( ))
#

GEMMA_SYSTEM_PROMPT = """You are a form data extractor. Extract all form fields from the image.

Guidelines:
1. Extract text exactly as it appears
2. Don't guess or invent values
3. Include all fields even if empty
4. For radio buttons: carefully examine which circle has ink/fill inside it
5. Format output in a clear, structured way"""

GEMMA_VISION_PROMPT = """Extract all form data from this page.

Include:
- Section headers
- Text fields with their values
- Radio button selections
- Checkbox selections
- Address fields

Format it clearly so it's easy to read. Use headings, bullet points, and mark selected options.

RADIO BUTTONS:
STEP 1 - IDENTIFY: Look for the circle with a dark dot inside (◉ = selected, ○ = not selected)
STEP 2 - OUTPUT: Write (x) for selected, ( ) for unselected. Do NOT write ◉ or ○.

The first option CAN be selected.

For checkboxes: use [x] for checked, [ ] for unchecked
For text fields: put values in backticks like `value`

Extract dates exactly as shown:
- If you see separate boxes for day/month/year, read each box and combine into Dag=`..`, Maand=`..`, Jaar=`..`
- If you see 8 consecutive digits like DDMMYYYY, insert dashes: `DD-MM-YYYY` (e.g., \"11121996\" → `11-12-1996`)
- Do not default to 01/01 when unclear; re-read the boxes if day/month/year conflict
- If multiple date fields or repeats conflict, prefer the one where all three parts (day, month, year) are present and consistent; otherwise leave empty backticks ``

Focus on the form content and ignore repetitive headers/footers."""


# =============================================================================
# QWEN PROMPTS (based on Gemini strict prompts + FORM_ID detection)
# =============================================================================
#
# ITERATION HISTORY:
# - v1 (2025-12-09): Initial - reused Gemini prompts directly
#   Result: Good date consistency, but no FORM_ID detection
#
# - v2 (2025-12-09): Added FORM_ID detection for page footers
#   Change: Added explicit instruction to look for form IDs at bottom middle
#   Pattern: Alphanumeric codes with version separators (B07001/2, 7101-03)
#   Output: **FORM_ID**: `<code>` at start of extraction
#

QWEN_SYSTEM_PROMPT = """You are a STRICT FORM DATA EXTRACTOR outputting structured Markdown.

ABSOLUTE RULES:
1. DO NOT GUESS or invent values - EVER
2. DO NOT HALLUCINATE information not present in the image
3. DO NOT add or omit form fields
4. Copy all labels and options VERBATIM
5. If a field is empty, output empty backticks: ``
6. If no radio/checkbox is selected, mark ALL options as unselected

You extract form data EXACTLY as it appears, formatted as Markdown."""


QWEN_VISION_PROMPT = """Extract form data from this page as structured Markdown.

FORM ID DETECTION (check FIRST):
Look at the BOTTOM MIDDLE of the page for a form identification code.
- Pattern: Alphanumeric code with version (e.g., "B07001/2", "7101-03", "M35-A/1")
- If found, output FIRST: **FORM_ID**: `B07001/2`
- Do NOT report plain page numbers (like "2" or "15") as form IDs
- Form IDs have letters OR version separators (/ or -)

PAGE CLASSIFICATION (output SECOND):
Identify what type of document/page this is and output: **PAGE_TYPE**: `description`
Examples:
- **PAGE_TYPE**: `Partner visa application form`
- **PAGE_TYPE**: `Marriage certificate`
- **PAGE_TYPE**: `Passport copy - applicant`
- **PAGE_TYPE**: `Antecedents declaration`
- **PAGE_TYPE**: `Cover page with table of contents`
- **PAGE_TYPE**: `Instructions and notes`
- **PAGE_TYPE**: `Supporting documents checklist`
Keep it short (3-6 words) and descriptive of the document's purpose.

OUTPUT FORMAT:

1. SECTION HEADERS (numbered sections like "2. Uw gegevens"):
   ## 2. Section Title

2. TEXT FIELDS (label with filled value):
   ### Field Label
   `filled value here`

   If empty, use empty backticks: ``

3. RADIO BUTTON GROUPS:
   ### Question Text
   - (x) selected option
   - ( ) unselected option
   - ( ) another option

4. CHECKBOX GROUPS:
   ### Checklist Title
   - [x] checked item
   - [ ] unchecked item

5. ADDRESS FIELDS (multiple sub-fields):
   ### Address Label
   - Straat en huisnummer: `Street 123`
   - Postcode en plaats: `1234AB City`
   - Land: `Netherlands`

RULES:
- Use (x) for SELECTED radio buttons, ( ) for unselected
- Use [x] for CHECKED checkboxes, [ ] for unchecked
- Put field values in backticks: `value`
- Empty fields get empty backticks: ``
- Copy all text VERBATIM - do not translate or summarize
- DATES: For date fields (Geboortedatum, datum, Geldig van/tot, etc.):
  - If you see individual digit boxes (like |1|0| |0|3| |2|0|2|1|), read EACH box separately and combine: Dag=`10`, Maand=`03`, Jaar=`2021`
  - For 8 consecutive digits like DDMMYYYY, insert dashes: `DD-MM-YYYY`. Example: "11121996" becomes `11-12-1996`
  - CRITICAL: A year like 2021 or 2031 has 4 digits, not 5. If you get "32021", re-read the boxes - it should be "2021"
- Skip only repetitive footers and standard agency headers like "Immigratie- en Naturalisatiedienst"
- Focus on form FIELDS and their VALUES

Output ONLY the markdown. No explanations or commentary."""


# PROMPT REGISTRY (Model-specific prompt mappings)
# =============================================================================

# =============================================================================
# GLM PROMPTS (simplified, no DOC IDENTITY rules)
# =============================================================================
#
# ISSUE: GLM-4.6V-Flash gets confused by Gemini-specific rules like:
# - "ALWAYS extract DOC IDENTITY headers FIRST"
# - Complex date parsing rules
# - Skip specific headers
#
# SOLUTION: Simplified prompts focused on pure content extraction
# RESULT: Full extraction on all page types (tested 2025-12-12)
#

GLM_SYSTEM_PROMPT = """You are a form data extractor. Extract content from images as Github-flavored markdown."""

GLM_VISION_PROMPT = """Extract all content from this page as Github-flavored markdown.

FORMAT:
- Headings: Use ## for main sections, ### for sub-sections
- Text: Copy verbatim, preserve all content
- Lists: Use bullet points (-)
- Radio buttons: (x) for selected, ( ) for unselected
- Checkboxes: [x] for checked, [ ] for unchecked
- Field values: Use backticks `value`
- Empty fields: Use empty backticks ``

RADIO BUTTONS - LOOK CAREFULLY:
Look at each circle/button carefully. The FILLED one (has ink inside) is selected.
Mark selected as (x), unselected as ( ). Only ONE should be marked (x) per group.

For dates: If you see boxes like |1|1| |1|2| |1|9|9|6|, combine them: `11-12-1996`

Output ONLY the markdown. No explanations."""


# Default prompts (used for unknown models and Gemini)
DEFAULT_PROMPTS = (GEMINI_SYSTEM_PROMPT, GEMINI_VISION_PROMPT)

# Model-specific prompt mappings
# Format: model_id_pattern: (system_prompt, vision_prompt)
MODEL_PROMPTS = {
    # Gemma models - use simplified prompts
    "gemma": (GEMMA_SYSTEM_PROMPT, GEMMA_VISION_PROMPT),
    "google/gemma": (GEMMA_SYSTEM_PROMPT, GEMMA_VISION_PROMPT),
    "gemma_3_27b": (GEMMA_SYSTEM_PROMPT, GEMMA_VISION_PROMPT),

    # Nemotron models - add /no_think prefix to system prompt
    "nemotron": ("/no_think\n\n" + GEMINI_SYSTEM_PROMPT, GEMINI_VISION_PROMPT),

    # Gemini models - use default strict prompts (explicit for clarity)
    "gemini": (GEMINI_SYSTEM_PROMPT, GEMINI_VISION_PROMPT),
    "google/gemini": (GEMINI_SYSTEM_PROMPT, GEMINI_VISION_PROMPT),
    "gemini_flash": (GEMINI_SYSTEM_PROMPT, GEMINI_VISION_PROMPT),

    # Qwen VL models - explicit constants (currently Gemma-style prompts)
    "qwen": (QWEN_SYSTEM_PROMPT, QWEN_VISION_PROMPT),
    "qwen2.5": (QWEN_SYSTEM_PROMPT, QWEN_VISION_PROMPT),

    # GLM Flash models - use simplified prompts (9B lightweight model needs simpler instructions)
    "glm_4v_flash": (GLM_SYSTEM_PROMPT, GLM_VISION_PROMPT),
    "glm_4v_flash_gateway": (GLM_SYSTEM_PROMPT, GLM_VISION_PROMPT),
    "glm_4v_flash_zai": (GLM_SYSTEM_PROMPT, GLM_VISION_PROMPT),

    # GLM full models - use Gemini prompts (106B model can handle complex instructions)
    "glm_4v_gateway": (GEMINI_SYSTEM_PROMPT, GEMINI_VISION_PROMPT),
    "glm": (GEMINI_SYSTEM_PROMPT, GEMINI_VISION_PROMPT),
    "glm4": (GEMINI_SYSTEM_PROMPT, GEMINI_VISION_PROMPT),
    "glm_gateway": (GLM_SYSTEM_PROMPT, GLM_VISION_PROMPT),  # Keep simple for gateway default
    "glm_zai": (GLM_SYSTEM_PROMPT, GLM_VISION_PROMPT),  # Keep simple for Z.AI default
}


# =============================================================================
# PROMPT SELECTION (Model-specific)
# =============================================================================

def _get_model_prompts(model: str | None = None) -> tuple:
    """
    Get model-specific prompts (system, vision).

    Args:
        model: Model identifier (e.g., "gemini_flash", "google/gemma-3-27b-it")

    Returns:
        Tuple of (system_prompt, vision_prompt)
    """
    if not model:
        return DEFAULT_PROMPTS

    model_lower = model.lower()

    # Check for model-specific prompts (partial match)
    for pattern, prompts in MODEL_PROMPTS.items():
        if pattern in model_lower:
            return prompts

    # Fallback to default prompts
    return DEFAULT_PROMPTS


def get_system_prompt(model: str | None = None, use_markdown: bool = True) -> str:
    """Get the system prompt for a model"""
    system_prompt, _ = _get_model_prompts(model)
    return system_prompt


def get_vision_prompt(model: str | None = None, use_markdown: bool = True) -> str:
    """Get the vision extraction prompt for a model"""
    _, vision_prompt = _get_model_prompts(model)
    return vision_prompt
