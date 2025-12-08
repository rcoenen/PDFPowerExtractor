## ADDED Requirements
### Requirement: Per-page TOC metadata
The system SHALL emit a table of contents entry for each processed page in the extraction output without altering visible content.

#### Scenario: TOC entry for each page
- **WHEN** a PDF is processed and merged into Markdown
- **THEN** the output includes a hidden TOC comment for every processed page in order, formatted as `<!-- TOC PAGE_XX: <summary> -->`
- **AND** the summary is derived from that page’s extracted content
- **AND** empty pages are marked as empty in their TOC entry

#### Scenario: Grouped TOC block at top
- **WHEN** a PDF is processed and merged into Markdown
- **THEN** the output contains a grouped TOC block immediately after the metadata header and before the first page header
- **AND** the block lists pages in order with their summaries using hidden HTML comments (e.g., `<!-- TOC START --> ... <!-- TOC END -->`)
- **AND** empty pages remain marked as empty in that grouped block
- **AND** generation SHALL fail if the grouped TOC block cannot be emitted

#### Scenario: No extra AI cost
- **WHEN** generating TOC summaries
- **THEN** the system derives them from existing extracted text
- **AND** it does not trigger additional AI calls

#### Scenario: Visible content unaffected
- **WHEN** TOC comments are added
- **THEN** they remain hidden HTML comments that do not change the rendered Markdown content
- **AND** they maintain page order alignment with the merged output
