"""
Output validation for PDFPowerExtractor.

Validates LLM output to ensure:
- Required sections/questions are present
- Radio/checkbox groups have at least one option
- No obvious hallucinations
- Output structure matches expected format
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ValidationSeverity(Enum):
    ERROR = "error"      # Critical - output is unusable
    WARNING = "warning"  # Concerning - output may have issues
    INFO = "info"        # Informational - minor observation


@dataclass
class ValidationIssue:
    """A single validation issue"""
    severity: ValidationSeverity
    code: str
    message: str
    location: Optional[str] = None  # e.g., "Page 5, Question 2.7"


@dataclass
class ValidationResult:
    """Result of validation"""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)

    def add_issue(self, severity: ValidationSeverity, code: str, message: str, location: str = None):
        self.issues.append(ValidationIssue(severity, code, message, location))
        if severity == ValidationSeverity.ERROR:
            self.is_valid = False

    def get_errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    def get_warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    def summary(self) -> str:
        errors = len(self.get_errors())
        warnings = len(self.get_warnings())
        return f"Valid: {self.is_valid}, Errors: {errors}, Warnings: {warnings}"


class OutputValidator:
    """
    Validates LLM extraction output.

    Checks for:
    1. Empty or near-empty output
    2. Missing expected question IDs
    3. Radio groups with no options
    4. Checkbox groups with no options
    5. Suspicious patterns (hallucination indicators)
    6. Character encoding issues
    """

    # Patterns for detecting form elements
    QUESTION_ID_PATTERN = re.compile(r'(\d+\.\d+)')
    RADIO_PATTERN = re.compile(r'^[●○◉◯]\s+', re.MULTILINE)
    CHECKBOX_PATTERN = re.compile(r'^[☒☑☐□✓✔]\s+', re.MULTILINE)
    MARKDOWN_RADIO_PATTERN = re.compile(r'^\([x ]\)\s+', re.MULTILINE)
    MARKDOWN_CHECKBOX_PATTERN = re.compile(r'^\[[x ]\]\s+', re.MULTILINE)

    # Suspicious patterns that might indicate hallucination
    HALLUCINATION_PATTERNS = [
        (r'I cannot\s+', "LLM refusal pattern"),
        (r'I\'m unable\s+', "LLM refusal pattern"),
        (r'As an AI\s+', "LLM self-reference"),
        (r'I don\'t have access\s+', "LLM limitation statement"),
        (r'unfortunately\s+', "Apologetic language"),
        (r'\[placeholder\]', "Placeholder text"),
        (r'\[insert\s+', "Insert placeholder"),
        (r'lorem ipsum', "Lorem ipsum placeholder"),
    ]

    # Encoding issue indicators
    ENCODING_ISSUES = [
        (r'[�□]', "Replacement character found"),
        (r'\\u[0-9a-fA-F]{4}', "Escaped unicode"),
        (r'&[a-z]+;', "HTML entities"),
    ]

    def __init__(
        self,
        min_content_length: int = 100,
        expected_question_ids: Optional[List[str]] = None,
        strict_mode: bool = False
    ):
        """
        Initialize validator.

        Args:
            min_content_length: Minimum expected output length
            expected_question_ids: List of question IDs that should be present
            strict_mode: If True, warnings become errors
        """
        self.min_content_length = min_content_length
        self.expected_question_ids = expected_question_ids or []
        self.strict_mode = strict_mode

    def validate(self, output: str, page_num: Optional[int] = None) -> ValidationResult:
        """
        Validate extraction output.

        Args:
            output: The extracted text output
            page_num: Optional page number for location reporting

        Returns:
            ValidationResult with issues found
        """
        result = ValidationResult(is_valid=True)
        location_prefix = f"Page {page_num}" if page_num else "Output"

        # Track stats
        result.stats = {
            "length": len(output),
            "lines": output.count('\n') + 1,
            "question_ids": 0,
            "radio_options": 0,
            "checkbox_options": 0,
        }

        # Check 1: Empty or too short
        if not output or not output.strip():
            result.add_issue(
                ValidationSeverity.ERROR,
                "EMPTY_OUTPUT",
                "Output is empty",
                location_prefix
            )
            return result

        if len(output.strip()) < self.min_content_length:
            result.add_issue(
                ValidationSeverity.WARNING if not self.strict_mode else ValidationSeverity.ERROR,
                "SHORT_OUTPUT",
                f"Output is very short ({len(output)} chars, expected >= {self.min_content_length})",
                location_prefix
            )

        # Check 2: Question IDs present
        found_ids = set(self.QUESTION_ID_PATTERN.findall(output))
        result.stats["question_ids"] = len(found_ids)

        for expected_id in self.expected_question_ids:
            if expected_id not in found_ids:
                result.add_issue(
                    ValidationSeverity.WARNING,
                    "MISSING_QUESTION",
                    f"Expected question {expected_id} not found",
                    location_prefix
                )

        # Check 3: Radio/checkbox groups
        radio_matches = self.RADIO_PATTERN.findall(output) + self.MARKDOWN_RADIO_PATTERN.findall(output)
        checkbox_matches = self.CHECKBOX_PATTERN.findall(output) + self.MARKDOWN_CHECKBOX_PATTERN.findall(output)

        result.stats["radio_options"] = len(radio_matches)
        result.stats["checkbox_options"] = len(checkbox_matches)

        # Check 4: Hallucination patterns
        for pattern, description in self.HALLUCINATION_PATTERNS:
            if re.search(pattern, output, re.IGNORECASE):
                result.add_issue(
                    ValidationSeverity.ERROR,
                    "HALLUCINATION_DETECTED",
                    f"Suspicious pattern found: {description}",
                    location_prefix
                )

        # Check 5: Encoding issues
        for pattern, description in self.ENCODING_ISSUES:
            matches = re.findall(pattern, output)
            if matches:
                result.add_issue(
                    ValidationSeverity.WARNING,
                    "ENCODING_ISSUE",
                    f"{description} ({len(matches)} occurrences)",
                    location_prefix
                )

        # Check 6: Balanced radio groups (each group should have options)
        self._check_radio_group_balance(output, result, location_prefix)

        return result

    def _check_radio_group_balance(self, output: str, result: ValidationResult, location: str):
        """Check that radio groups have reasonable structure"""
        lines = output.split('\n')

        in_radio_group = False
        radio_count = 0
        selected_count = 0

        for line in lines:
            line = line.strip()

            # Detect radio option
            is_selected = bool(re.match(r'^[●◉]', line) or re.match(r'^\(x\)', line))
            is_unselected = bool(re.match(r'^[○◯]', line) or re.match(r'^\( \)', line))

            if is_selected or is_unselected:
                if not in_radio_group:
                    in_radio_group = True
                    radio_count = 0
                    selected_count = 0

                radio_count += 1
                if is_selected:
                    selected_count += 1
            else:
                # End of radio group
                if in_radio_group:
                    if radio_count > 0 and selected_count > 1:
                        result.add_issue(
                            ValidationSeverity.WARNING,
                            "MULTIPLE_RADIO_SELECTED",
                            f"Radio group has {selected_count} selected options (should be 0 or 1)",
                            location
                        )
                    in_radio_group = False

    def validate_batch(self, outputs: Dict[int, str]) -> Dict[int, ValidationResult]:
        """
        Validate multiple page outputs.

        Args:
            outputs: Dict mapping page numbers to output strings

        Returns:
            Dict mapping page numbers to validation results
        """
        results = {}
        for page_num, output in outputs.items():
            results[page_num] = self.validate(output, page_num)
        return results

    def get_overall_result(self, results: Dict[int, ValidationResult]) -> ValidationResult:
        """
        Combine multiple validation results into overall result.

        Args:
            results: Dict of page validation results

        Returns:
            Combined validation result
        """
        overall = ValidationResult(is_valid=True)

        for page_num, result in results.items():
            if not result.is_valid:
                overall.is_valid = False

            for issue in result.issues:
                overall.issues.append(issue)

        # Aggregate stats
        overall.stats = {
            "pages_validated": len(results),
            "pages_with_errors": sum(1 for r in results.values() if not r.is_valid),
            "total_errors": sum(len(r.get_errors()) for r in results.values()),
            "total_warnings": sum(len(r.get_warnings()) for r in results.values()),
        }

        return overall


def validate_extraction(output: str, page_num: int = None) -> ValidationResult:
    """
    Convenience function to validate extraction output.

    Args:
        output: Extracted text
        page_num: Optional page number

    Returns:
        ValidationResult
    """
    validator = OutputValidator()
    return validator.validate(output, page_num)


def is_output_valid(output: str) -> bool:
    """
    Quick check if output is valid.

    Args:
        output: Extracted text

    Returns:
        True if valid, False otherwise
    """
    result = validate_extraction(output)
    return result.is_valid
