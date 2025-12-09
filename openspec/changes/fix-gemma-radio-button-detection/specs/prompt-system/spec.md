## MODIFIED Requirements
### Requirement: Simplified Prompts for Gemma 3 27B
The system SHALL provide optimized prompts for Gemma 3 27B that improve extraction accuracy.

#### Scenario: Gemma prompt characteristics
- **WHEN** designing prompts for Gemma 3 27B
- **THEN** prompts avoid complex Markdown formatting rules
- **AND** prompts use simpler, more natural language instructions
- **AND** prompts focus on content extraction over strict formatting
- **AND** prompts are tested to reduce field mix-ups and checkbox errors

#### Scenario: Gemma radio button detection
- **WHEN** extracting radio button selections from forms
- **THEN** the prompt explicitly describes filled (◉) vs empty (○) visual symbols
- **AND** the model correctly identifies which option is selected
- **AND** the prompt instructs careful visual inspection before marking selections

#### Scenario: Gemma accuracy improvement
- **WHEN** using simplified prompts with Gemma 3 27B
- **THEN** field extraction accuracy improves from current 43% error rate
- **AND** radio button selection errors are reduced
- **AND** question numbering is preserved correctly
- **AND** overall output quality approaches Gemini levels
