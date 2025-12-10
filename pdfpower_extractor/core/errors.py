"""
Extraction Errors and Batch Result Types

Provides structured error handling for batch PDF extraction with
detailed error information that callers can propagate to end users.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum


class ErrorType(Enum):
    """Error categories for extraction failures"""
    PAYMENT = "PaymentError"           # 402 - Payment/quota exceeded
    PAYLOAD_TOO_LARGE = "PayloadTooLargeError"  # 413 - Image too large
    RATE_LIMIT = "RateLimitError"      # 429 - Too many requests
    SERVER = "ServerError"             # 5xx - Server errors
    MODEL_RESPONSE = "ModelResponseError"  # Invalid model response
    NETWORK = "NetworkError"           # Connection issues
    UNKNOWN = "UnknownError"           # Catch-all


# Map HTTP status codes to error types
HTTP_STATUS_TO_ERROR_TYPE = {
    402: ErrorType.PAYMENT,
    413: ErrorType.PAYLOAD_TOO_LARGE,
    429: ErrorType.RATE_LIMIT,
    500: ErrorType.SERVER,
    502: ErrorType.SERVER,
    503: ErrorType.SERVER,
    504: ErrorType.SERVER,
}


def get_error_type_from_status(status_code: int) -> ErrorType:
    """Get error type from HTTP status code"""
    return HTTP_STATUS_TO_ERROR_TYPE.get(status_code, ErrorType.UNKNOWN)


def get_error_type_from_message(message: str) -> Tuple[ErrorType, Optional[int]]:
    """Extract error type and status code from error message"""
    import re

    # Try to extract HTTP status code from message
    # Patterns like "402 Payment Required", "413 Client Error", etc.
    match = re.search(r'\b(4\d{2}|5\d{2})\b', message)
    if match:
        status_code = int(match.group(1))
        return get_error_type_from_status(status_code), status_code

    # Check for keywords
    lower_msg = message.lower()
    if 'payment' in lower_msg or 'quota' in lower_msg or 'billing' in lower_msg:
        return ErrorType.PAYMENT, 402
    if 'too large' in lower_msg or 'payload' in lower_msg:
        return ErrorType.PAYLOAD_TOO_LARGE, 413
    if 'rate limit' in lower_msg or 'too many' in lower_msg:
        return ErrorType.RATE_LIMIT, 429
    if 'connection' in lower_msg or 'timeout' in lower_msg:
        return ErrorType.NETWORK, None

    return ErrorType.UNKNOWN, None


@dataclass
class PageError:
    """Error information for a single page"""
    page_num: int
    error_type: ErrorType
    error_code: Optional[int]
    message: str

    def to_tuple(self) -> Tuple[int, str, str]:
        """Return (page_num, error_type_name, message) tuple"""
        return (self.page_num, self.error_type.value, self.message)


@dataclass
class PageResult:
    """Result for a single page extraction"""
    page_num: int
    success: bool
    content: Optional[str] = None
    error: Optional[PageError] = None
    token_usage: Optional[Any] = None  # TokenUsage from models.config


@dataclass
class BatchResult:
    """
    Result of a batch PDF extraction operation.

    Provides clear success/failure signal with detailed error information
    that callers can propagate to end users.

    Usage:
        result = processor.process()

        if result.success:
            print(result.content)
        else:
            print(result.error_summary)
            for page_num, error_type, msg in result.failed_pages:
                print(f"  Page {page_num}: {msg}")
    """
    pages: Dict[int, PageResult] = field(default_factory=dict)
    total_pages: int = 0
    content: str = ""  # Full extracted markdown (empty if failed with fail_fast)

    @property
    def success(self) -> bool:
        """True if all pages extracted successfully"""
        return all(p.success for p in self.pages.values())

    @property
    def status(self) -> str:
        """
        Status of the batch:
        - "completed": All pages succeeded
        - "failed": One or more pages failed
        - "partial": Some pages failed but content was partially extracted (fail_fast=False)
        """
        if self.success:
            return "completed"
        elif self.content:
            return "partial"
        else:
            return "failed"

    @property
    def pages_completed(self) -> int:
        """Number of pages that extracted successfully"""
        return sum(1 for p in self.pages.values() if p.success)

    @property
    def pages_failed(self) -> int:
        """Number of pages that failed"""
        return sum(1 for p in self.pages.values() if not p.success)

    @property
    def failed_pages(self) -> List[Tuple[int, str, str]]:
        """
        List of failed pages as (page_num, error_type, message) tuples.
        Sorted by page number.
        """
        errors = []
        for page_num in sorted(self.pages.keys()):
            page = self.pages[page_num]
            if not page.success and page.error:
                errors.append(page.error.to_tuple())
        return errors

    @property
    def primary_error(self) -> Optional[PageError]:
        """The first error encountered (by page number)"""
        for page_num in sorted(self.pages.keys()):
            page = self.pages[page_num]
            if not page.success and page.error:
                return page.error
        return None

    @property
    def error_summary(self) -> Optional[str]:
        """
        Human-readable error summary.
        Returns None if all pages succeeded.

        Examples:
        - "Page 5 of 10 failed: 402 Payment Required"
        - "3 of 10 pages failed: page 5 (402 Payment Required), page 8 (413 Payload Too Large)"
        """
        if self.success:
            return None

        failed = self.failed_pages
        if not failed:
            return None

        if len(failed) == 1:
            page_num, error_type, msg = failed[0]
            return f"Page {page_num} of {self.total_pages} failed: {msg}"

        # Multiple failures
        details = [f"page {p} ({m})" for p, _, m in failed[:5]]  # Show first 5
        if len(failed) > 5:
            details.append(f"and {len(failed) - 5} more")

        return f"{len(failed)} of {self.total_pages} pages failed: {', '.join(details)}"


class ExtractionError(Exception):
    """
    Structured exception for extraction failures.

    Contains detailed error information that callers can inspect
    to propagate meaningful error messages to end users.

    Usage:
        try:
            result = processor.process()
        except ExtractionError as e:
            print(f"Error: {e.message}")
            print(f"Status code: {e.error_code}")
            print(f"Pages completed: {e.pages_completed}/{e.pages_total}")
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[int] = None,
        error_type: ErrorType = ErrorType.UNKNOWN,
        failed_pages: Optional[List[Tuple[int, str, str]]] = None,
        pages_completed: int = 0,
        pages_total: int = 0,
        partial_content: str = "",
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.error_type = error_type
        self.error_type_name = error_type.value
        self.failed_pages = failed_pages or []
        self.pages_completed = pages_completed
        self.pages_total = pages_total
        self.partial_content = partial_content

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "message": self.message,
            "error_code": self.error_code,
            "error_type": self.error_type_name,
            "failed_pages": self.failed_pages,
            "pages_completed": self.pages_completed,
            "pages_total": self.pages_total,
            "has_partial_content": bool(self.partial_content),
        }

    @classmethod
    def from_batch_result(cls, batch_result: BatchResult) -> "ExtractionError":
        """Create ExtractionError from a failed BatchResult"""
        primary = batch_result.primary_error

        return cls(
            message=batch_result.error_summary or "Extraction failed",
            error_code=primary.error_code if primary else None,
            error_type=primary.error_type if primary else ErrorType.UNKNOWN,
            failed_pages=batch_result.failed_pages,
            pages_completed=batch_result.pages_completed,
            pages_total=batch_result.total_pages,
            partial_content=batch_result.content,
        )
