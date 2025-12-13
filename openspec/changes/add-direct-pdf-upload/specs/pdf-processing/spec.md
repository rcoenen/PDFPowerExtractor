# PDF Processing Capability

## ADDED Requirements

### Requirement: Direct PDF Upload Support

The system SHALL support uploading PDFs directly to Z.AI's Files API as an alternative to image conversion.

**Purpose:** Enable native PDF processing to potentially improve quality and bypass concurrent degradation issues observed with image-based processing.

#### Scenario: Upload single-page PDF
- **GIVEN** a single-page PDF file
- **WHEN** user requests extraction with `--use-direct-pdf` flag
- **THEN** PDF SHALL be uploaded via Z.AI Files API (`POST /paas/v4/files`)
- **AND** upload response SHALL contain file_id
- **AND** file_id SHALL be used in subsequent chat/completions request

#### Scenario: Upload fails, fallback to images
- **GIVEN** a PDF that fails to upload to Files API
- **WHEN** upload returns error response
- **THEN** system SHALL fall back to image-based processing
- **AND** log warning about fallback
- **AND** processing SHALL continue without user intervention

#### Scenario: Non-Z.AI endpoint with direct PDF flag
- **GIVEN** model configuration uses non-Z.AI endpoint (e.g., Gemini, Qwen)
- **WHEN** user specifies `--use-direct-pdf` flag
- **THEN** system SHALL log warning that direct PDF only works with Z.AI
- **AND** fall back to image-based processing
- **AND** extraction SHALL proceed normally

### Requirement: PDF Upload Caching

The system SHALL cache uploaded file_ids to avoid re-uploading identical PDFs.

**Rationale:** Files API retains uploads for 180 days. Re-uploading the same PDF wastes bandwidth and API quota.

#### Scenario: Re-process same PDF
- **GIVEN** a PDF with MD5 hash `abc123` was uploaded previously
- **WHEN** processing the same PDF again within 180 days
- **THEN** system SHALL reuse cached file_id
- **AND** NOT upload PDF again
- **AND** verify file still exists before using cached file_id

#### Scenario: Cached file expired
- **GIVEN** a PDF with cached file_id from >180 days ago
- **WHEN** attempting to use cached file_id
- **THEN** system SHALL detect file no longer exists
- **AND** upload PDF again
- **AND** update cache with new file_id

### Requirement: Experimental Feature Flag

Direct PDF upload SHALL be opt-in via configuration flag, NOT default behavior.

**Rationale:** Feature is experimental and needs production validation before becoming default.

#### Scenario: Default behavior unchanged
- **GIVEN** no `--use-direct-pdf` flag specified
- **WHEN** processing any PDF
- **THEN** system SHALL use image-based processing (current behavior)
- **AND** NOT attempt PDF upload

#### Scenario: Explicit opt-in
- **GIVEN** `--use-direct-pdf` flag specified
- **AND** Z.AI endpoint configured
- **WHEN** processing PDF
- **THEN** system SHALL attempt direct PDF upload
- **AND** use uploaded file_id in chat/completions

### Requirement: File Cleanup

The system SHALL clean up uploaded files after processing to avoid quota exhaustion.

#### Scenario: Successful processing with cleanup
- **GIVEN** PDF uploaded to Files API with file_id `file-abc123`
- **WHEN** extraction completes successfully
- **THEN** system SHALL delete uploaded file via Files API
- **AND** remove file_id from cache
- **AND** log cleanup action

#### Scenario: Processing fails, cleanup still occurs
- **GIVEN** PDF uploaded but processing fails
- **WHEN** error occurs during extraction
- **THEN** system SHALL still attempt to delete uploaded file
- **AND** NOT leave orphaned files in Z.AI storage

### Requirement: Quality Comparison Logging

The system SHALL log quality metrics when direct PDF is used to enable comparison.

#### Scenario: Log extraction metrics
- **GIVEN** extraction via direct PDF upload
- **WHEN** processing completes
- **THEN** system SHALL log:
  - Processing method (direct_pdf vs image)
  - Output token count
  - Processing time
  - Model used
  - File size
- **AND** enable comparison analysis

## MODIFIED Requirements

None - this is net-new functionality.

## REMOVED Requirements

None - preserves existing image-based processing.
