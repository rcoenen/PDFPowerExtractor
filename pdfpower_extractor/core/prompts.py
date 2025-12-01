"""
Model-specific prompts for PDFPowerExtractor.

These prompts follow strict extraction guidelines to prevent hallucination
and ensure accurate form field detection.
"""

# =============================================================================
# SYSTEM PROMPTS (Role Definition)
# =============================================================================

SYSTEM_PROMPT_STRICT = """You are a STRICT TEXT EXTRACTOR, not a creative writer.

ABSOLUTE RULES:
1. DO NOT GUESS or invent values - EVER
2. DO NOT HALLUCINATE information not present in the input
3. DO NOT add or omit questions
4. DO NOT summarize or translate
5. Copy all labels and options VERBATIM from input
6. If something is missing, output empty string or leave option unselected

You extract form data EXACTLY as it appears. Nothing more, nothing less."""


# =============================================================================
# VISION EXTRACTION PROMPTS (for image-based extraction)
# =============================================================================

# Plain text output (default) - uses Unicode symbols
VISION_PROMPT_DEFAULT = """Extract all text from this form page.

For TEXT FIELDS with filled-in values:
- Combine the label and its value on ONE LINE
- If a value appears in a shaded/colored box, put it on the same line as its label
- Use a colon to separate label from value
- Example: "Name field: John_Doe"

For RADIO BUTTONS and CHECKBOXES:
- Put the question/label on its own line with a colon
- List each option on a separate line below
- Use ● for selected and ○ for unselected radio buttons
- Use ☒ for checked and ☐ for unchecked checkboxes
- Example format:
  "Question text:"
  "● selected option"
  "○ unselected option"
  "○ another unselected option"

IMPORTANT: Text fields get their values on the same line, but radio/checkbox groups get options on separate lines."""


VISION_PROMPT_GPT_NANO = """Extract all text from this form page.

For TEXT FIELDS with filled-in values:
- Combine the label and its value on ONE LINE
- If a value appears in a shaded/colored box, put it on the same line as its label
- Use a colon to separate label from value
- Example: "Name field: John_Doe"

For RADIO BUTTONS and CHECKBOXES:
- Put the question/label on its own line with a colon
- List each option on a separate line below
- Use ● for selected and ○ for unselected radio buttons
- Use ☒ for checked and ☐ for unchecked checkboxes
- Example format:
  "Question text:"
  "● selected option"
  "○ unselected option"
  "○ another unselected option"

CRITICAL RULES:
- NEVER use ● for regular bullet points - only for SELECTED radio buttons
- Look carefully for small dots/marks INSIDE circles to determine if selected
- If you don't see a clear fill marker inside, use ○ (unselected)
- When in doubt, mark as ○ (unselected)

IMPORTANT: Text fields get their values on the same line, but radio/checkbox groups get options on separate lines."""


VISION_PROMPT_GEMMA = """Perform precise OCR on this document.

CRITICAL - COMMON OCR ERRORS TO AVOID:
- "Z" is often misread as "2" - look for the diagonal line that makes it Z
- "O" is often misread as "0" - context matters, codes often use letters
- "S" is often misread as "5"
- "I" is often misread as "1"
- Application/Reference IDs typically mix letters AND numbers - read carefully

For TEXT FIELDS with filled-in values:
- Combine the label and its value on ONE LINE
- Use a colon to separate label from value

For RADIO BUTTONS and CHECKBOXES:
- Use ● for selected and ○ for unselected radio buttons
- Use ☒ for checked and ☐ for unchecked checkboxes

Output plain text only. No introductory phrases like "Here's the text". No markdown formatting (no ** or ##)."""


# =============================================================================
# MARKDOWN OUTPUT PROMPTS (direct structured markdown extraction)
# =============================================================================

VISION_PROMPT_MARKDOWN = """Extract form data from this page as structured Markdown.

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
- DATES: For date fields (Geboortedatum, datum, etc.), if you see 8 consecutive digits like DDMMYYYY, insert dashes: `DD-MM-YYYY`. Example: "11121996" becomes `11-12-1996`
- Skip page numbers, headers like "Immigratie- en Naturalisatiedienst"
- Focus on form FIELDS and their VALUES

Output ONLY the markdown. No explanations or commentary."""


SYSTEM_PROMPT_MARKDOWN = """You are a STRICT FORM DATA EXTRACTOR outputting structured Markdown.

ABSOLUTE RULES:
1. DO NOT GUESS or invent values - EVER
2. DO NOT HALLUCINATE information not present in the image
3. DO NOT add or omit form fields
4. Copy all labels and options VERBATIM
5. If a field is empty, output empty backticks: ``
6. If no radio/checkbox is selected, mark ALL options as unselected

You extract form data EXACTLY as it appears, formatted as Markdown."""


# =============================================================================
# TEXT-TO-MARKDOWN PROMPTS (for text-layer extraction with LLM formatting)
# =============================================================================

TEXT_TO_MARKDOWN_SYSTEM = """You are a STRICT TEXT EXTRACTOR converting form text to structured Markdown.

ABSOLUTE RULES:
1. DO NOT GUESS or invent values - EVER
2. DO NOT HALLUCINATE information not present in the input
3. DO NOT add or omit questions
4. Copy all labels and options VERBATIM from input
5. If a value is missing, output empty backticks: ``
6. If no radio/checkbox is selected, mark ALL options as unselected

Radio/Checkbox Symbol Mapping:
- ● (filled circle) = selected radio → output as (x)
- ○ (empty circle) = unselected radio → output as ( )
- ☒ or ☑ (checked box) = checked checkbox → output as [x]
- ☐ (empty box) = unchecked checkbox → output as [ ]

NEVER invent a selection. If you don't see ● or ☒, the option is NOT selected."""


TEXT_TO_MARKDOWN_PROMPT = """Convert the following extracted form text to canonical Markdown format.

INPUT TEXT:
{input_text}

OUTPUT FORMAT RULES:

1. SECTION HEADERS:
   ## 2. Section Name

2. TEXT FIELDS:
   ### 2.1 Field Label
   value: `filled value here`

   (If empty: value: ``)

3. RADIO BUTTON GROUPS:
   ### 2.7 Question Text
   (type: radio)
   - (x) selected option
   - ( ) unselected option
   - ( ) another unselected option

4. CHECKBOX GROUPS:
   ### 5.2 Document Checklist
   (type: checkbox)
   - [x] checked item
   - [ ] unchecked item

5. ADDRESS/MULTI-LINE FIELDS:
   ### 2.9 Address
   Straat en huisnummer: `Street 123`
   Postcode en plaats: `1234AB City`
   Land: `Netherlands`

CRITICAL REMINDERS:
- DO NOT add explanations or commentary
- DO NOT invent values not in the input
- If ● appears → (x), if ○ appears → ( )
- If no ● visible for a radio group → ALL options are ( )
- Copy weird glyphs/characters verbatim into labels

Output ONLY the canonical Markdown. No additional text."""


# =============================================================================
# CANONICAL MARKDOWN TEMPLATE
# =============================================================================

MARKDOWN_TEMPLATE = '''## {section_number}. {section_title}

{section_description}

### {question_id} {question_label}
value: `{value}`

### {question_id} {question_label}
(type: radio)
- (x) {selected_option}
- ( ) {unselected_option}

### {question_id} {question_label}
(type: checkbox)
- [x] {checked_item}
- [ ] {unchecked_item}
'''


# =============================================================================
# PROMPT SELECTION
# =============================================================================

def get_vision_prompt(model: str, use_markdown: bool = False) -> str:
    """Get the appropriate vision extraction prompt for a model

    Args:
        model: Model identifier string
        use_markdown: If True, return markdown-optimized prompt
    """
    if use_markdown:
        return VISION_PROMPT_MARKDOWN

    model_lower = model.lower()
    if "gpt-4.1-nano" in model or "nano" in model_lower:
        return VISION_PROMPT_GPT_NANO
    if "gemma" in model_lower:
        return VISION_PROMPT_GEMMA
    return VISION_PROMPT_DEFAULT


def get_text_to_markdown_prompt(input_text: str) -> str:
    """Get the text-to-markdown conversion prompt with input text"""
    return TEXT_TO_MARKDOWN_PROMPT.format(input_text=input_text)


def get_system_prompt(model: str, use_markdown: bool = False) -> str:
    """Get the system prompt for a model

    Args:
        model: Model identifier string
        use_markdown: If True, return markdown-optimized system prompt
    """
    if use_markdown:
        return SYSTEM_PROMPT_MARKDOWN
    return SYSTEM_PROMPT_STRICT
