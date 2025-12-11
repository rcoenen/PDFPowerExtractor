"""
PDF Processor - Core processing engine

Uses AI vision models to extract form data from PDFs as structured Markdown.
All extraction is AI-based (no text-only mode).

Model and endpoint configuration is handled via ExtractionConfig.model_config_id
which references configurations in models/config.py
"""

import os
import hashlib
import time
import re
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Callable, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from .analyzer import PDFAnalyzer, detect_page_images
import fitz  # PyMuPDF
from .extractor import AIExtractor
from .config import ExtractionConfig
from .validator import OutputValidator, ValidationResult
from ..models.config import TokenUsage
from .errors import (
    ExtractionError,
    BatchResult,
    PageResult,
    PageError,
    ErrorType,
    get_error_type_from_message,
)


class PDFProcessor:
    """
    Main processor for AI-based PDF form extraction.

    Usage:
        from pdfpower_extractor.core import gemini_config
        processor = PDFProcessor(pdf_path, config=gemini_config())
        result = processor.process()

        # Or with different model
        from pdfpower_extractor.core import mistral_config
        processor = PDFProcessor(pdf_path, config=mistral_config())
        result = processor.process()
    """

    def __init__(
        self,
        pdf_path: str,
        config: Optional[ExtractionConfig] = None,
        api_key: str = None  # Optional override, otherwise resolved from model config
    ):
        self.pdf_path = pdf_path
        self.config = config or ExtractionConfig()

        # Get model config
        self.model_config = self.config.get_model_config()

        self.analyzer = PDFAnalyzer(pdf_path)
        self.ai_extractor = AIExtractor(
            api_key=api_key,
            config=self.config,
            model_config=self.model_config
        )
        self.validator = OutputValidator()

        self.last_cost = 0.0
        self.last_duration = 0.0
        self._md5_hash = None
        self.validation_results: Dict[int, ValidationResult] = {}
        self._compact_date_pattern = re.compile(
            r"\b(?P<day>0[1-9]|[12][0-9]|3[01])"
            r"(?P<month>0[1-9]|1[0-2])"
            r"(?P<year>(19|20)\d{2})\b"
        )

        # Token usage tracking
        self.total_token_usage: TokenUsage = TokenUsage()
        self.page_token_usage: Dict[int, TokenUsage] = {}

    def calculate_md5(self) -> str:
        """Calculate MD5 hash of the PDF file"""
        if self._md5_hash:
            return self._md5_hash

        hash_md5 = hashlib.md5()
        with open(self.pdf_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        self._md5_hash = hash_md5.hexdigest()
        return self._md5_hash

    def process(
        self,
        progress_callback: Optional[Callable[[Any], None]] = None,
        debug_save_images: bool = False,
        extra_metadata: Optional[str] = None,
        audit_log_path: Optional[str] = None,
        audit_log_hook: Optional[Callable[[Dict[str, Any]], None]] = None,
        audit_retention_hours: Optional[int] = 24,
    ) -> str:
        """
        Process the PDF using AI vision extraction.

        Args:
            progress_callback: Callback for progress updates
            debug_save_images: If True, save converted images to /tmp/powerpdf_extracted_images/
            extra_metadata: Optional multi-line string to include inside the metadata comment
                before the PDF extraction metadata (keeps a single well-formed comment block).
            audit_log_path: Optional path to append audit log entries (JSONL); logging is off unless provided.
            audit_log_hook: Optional callable receiving each audit entry dict.
            audit_retention_hours: Optional retention window (hours) for pruning the audit log; set to None to disable pruning.

        Returns:
            Extracted content as Markdown
        """
        start_time = time.time()
        start_dt = datetime.now()
        env_audit_path = os.getenv("PDFPOWER_AUDIT_LOG")
        resolved_audit_log_path = audit_log_path or env_audit_path
        audit_enabled = bool(resolved_audit_log_path or audit_log_hook)
        if audit_enabled and not resolved_audit_log_path:
            resolved_audit_log_path = str(Path.home() / ".pdfpower" / "logs" / "extraction-audit.log")

        exc: Optional[Exception] = None
        try:
            # Create session directory for debug images if enabled
            debug_session_dir = None
            if debug_save_images:
                import uuid
                from pathlib import Path
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                session_id = str(uuid.uuid4())[:8]
                pdf_name = Path(self.pdf_path).stem
                base_dir = Path("/tmp/powerpdf_extracted_images")
                debug_session_dir = base_dir / f"session_{timestamp}_{session_id}_{pdf_name}"
                debug_session_dir.mkdir(parents=True, exist_ok=True)

                if self.config.verbose:
                    print(f"[DEBUG] Image saving enabled: {debug_session_dir}")

            # Analyze PDF structure
            summary = self.analyzer.analyze()
            total_pages = summary['total_pages']
            empty_pages = set(summary.get("empty_pages", []))
            pages_to_process = [p for p in range(1, total_pages + 1) if p not in empty_pages]

            if self.config.verbose:
                print(f"[INFO] Model: {self.model_config.name}")
                print(f"[INFO] Endpoint: {self.model_config.get_endpoint().name}")
                print(f"[INFO] Pages to process: {len(pages_to_process)} (excluding {len(empty_pages)} empty)")

            # Track progress
            processed = 0

            # Process results
            results: Dict[int, Dict[str, Any]] = {}
            total_cost = 0.0

            def emit(status: str, page_num: int):
                if progress_callback:
                    try:
                        progress_callback({
                            "status": status,
                            "page": page_num,
                            "total": total_pages,
                        })
                    except Exception:
                        try:
                            progress_callback(int(processed / total_pages * 100))
                        except Exception:
                            pass

            # Process pages with AI (parallel workers based on endpoint limits)
            endpoint = self.model_config.get_endpoint()
            max_workers = endpoint.max_parallel_requests

            def process_single_page(page_num: int) -> tuple:
                """Process a single page - runs in thread pool"""
                result = self.ai_extractor.extract_page(
                    self.pdf_path,
                    page_num,
                    use_markdown=True,
                    debug_save_images=debug_save_images,
                    debug_session_dir=debug_session_dir
                )
                return page_num, result

            if self.config.verbose:
                print(f"[INFO] Processing {len(pages_to_process)} pages with {max_workers} parallel workers")

            extraction_start = time.time()
            # Process pages in parallel, tracking errors
            page_results = {}
            page_errors: Dict[int, PageError] = {}

            page_timings = {}
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(process_single_page, pn): pn for pn in pages_to_process}
                for future in as_completed(futures):
                    page_num = futures[future]
                    elapsed = time.time() - extraction_start
                    page_timings[page_num] = elapsed
                    try:
                        _, result = future.result()
                        page_results[page_num] = result
                        emit("done", page_num)
                    except Exception as page_err:
                        # Track the error for this page
                        error_msg = str(page_err)
                        error_type, error_code = get_error_type_from_message(error_msg)
                        page_errors[page_num] = PageError(
                            page_num=page_num,
                            error_type=error_type,
                            error_code=error_code,
                            message=error_msg,
                        )
                        if self.config.verbose:
                            print(f"[ERROR] Page {page_num} failed: {error_msg}")
                        emit("error", page_num)

            print(f"[TIMING] Extraction took {time.time() - extraction_start:.2f}s")
            # Show slowest pages
            sorted_timings = sorted(page_timings.items(), key=lambda x: x[1], reverse=True)
            slowest_5 = sorted_timings[:5]
            print(f"[TIMING] Slowest pages: {[(p, f'{t:.1f}s') for p, t in slowest_5]}")

            # Collect results in page order
            for page_num in sorted(page_results.keys()):
                result = page_results[page_num]

                # Track token usage
                page_usage = result.get('token_usage', TokenUsage())
                self.page_token_usage[page_num] = page_usage
                self.total_token_usage = self.total_token_usage + page_usage

                # Validate output if configured
                if self.config.validation.validate_output:
                    validation = self.validator.validate(result['content'], page_num)
                    self.validation_results[page_num] = validation

                results[page_num] = {
                    'content': result['content'],
                    'token_usage': page_usage,
                }

                total_cost += page_usage.cost
                processed += 1

            # Handle empty pages
            for page_num in empty_pages:
                results[page_num] = {
                    'content': "*This page is empty*\n",
                }
                processed += 1
                emit("done", page_num)

            emit("done", total_pages)

            # Store metrics
            self.last_duration = time.time() - start_time
            self.last_cost = total_cost

            # Check for page errors
            if page_errors:
                if self.config.fail_fast:
                    # fail_fast=True (default): Raise ExtractionError immediately
                    batch_result = BatchResult(total_pages=total_pages)
                    for page_num in pages_to_process:
                        if page_num in page_errors:
                            batch_result.pages[page_num] = PageResult(
                                page_num=page_num,
                                success=False,
                                error=page_errors[page_num],
                            )
                        elif page_num in page_results:
                            batch_result.pages[page_num] = PageResult(
                                page_num=page_num,
                                success=True,
                                content=page_results[page_num].get('content', ''),
                                token_usage=page_results[page_num].get('token_usage'),
                            )
                    # Raise structured error
                    raise ExtractionError.from_batch_result(batch_result)
                else:
                    # fail_fast=False: Continue processing, add error markers for failed pages
                    for page_num, page_error in page_errors.items():
                        error_content = f"**⚠️ Page {page_num} extraction failed**\n\nError: {page_error.message}\n"
                        results[page_num] = {
                            'content': error_content,
                            'token_usage': TokenUsage(),
                            'error': page_error,
                        }

            # Build markdown output with image detection
            post_start = time.time()
            merged_content = []
            toc_entries: List[Tuple[int, str, Optional[str]]] = []  # (page_num, description, form_id)
            with fitz.open(self.pdf_path) as doc:
                for page_num in sorted(results.keys()):
                    body = (results[page_num]['content'] or "").splitlines()
                    # Drop leading blanks and internal headers
                    while body and not body[0].strip():
                        body = body[1:]
                    while body and body[0].lstrip().startswith("==="):
                        body = body[1:]
                    cleaned = "\n".join(body).strip()

                    # Extract page description and form ID separately
                    page_summary = self._summarize_page(cleaned)
                    form_id = self._extract_form_id(cleaned)
                    toc_entries.append((page_num, page_summary, form_id))

                    # Detect images on this page using PyMuPDF
                    image_comment = detect_page_images(doc, page_num - 1)  # 0-based index

                    header = f"\n{'='*60}\n{'PAGE ' + str(page_num) + ' OF ' + str(total_pages):^60}\n{'='*60}"
                    normalized = self._normalize_compact_dates(cleaned)
                    toc_comment = f"<!-- TOC PAGE_{page_num:02d}: {page_summary} -->"
                    merged_content.append(f"{toc_comment}\n{header}\n{image_comment}\n{normalized}".rstrip() + "\n")

            # Create header
            file_header = self._create_header(summary, total_cost, extra_metadata)
            toc_block = self._build_top_level_toc(toc_entries)

            final_output = file_header + toc_block + '\n'.join(merged_content)

            print(f"[TIMING] Post-processing took {time.time() - post_start:.2f}s")
            if "<!-- TOC START -->" not in final_output:
                raise ValueError("Grouped TOC block missing from output; header assembly failed.")

            return final_output
        except Exception as err:
            exc = err
            if audit_enabled:
                self._emit_audit_log(
                    status="failure",
                    start_dt=start_dt,
                    end_dt=datetime.now(),
                    error=str(err),
                    audit_log_path=resolved_audit_log_path,
                    audit_log_hook=audit_log_hook,
                    audit_retention_hours=audit_retention_hours,
                )
            raise
        finally:
            if audit_enabled and exc is None:
                self._emit_audit_log(
                    status="success",
                    start_dt=start_dt,
                    end_dt=datetime.now(),
                    error=None,
                    audit_log_path=resolved_audit_log_path,
                    audit_log_hook=audit_log_hook,
                    audit_retention_hours=audit_retention_hours,
                )

    def _normalize_compact_dates(self, text: str) -> str:
        """
        Insert dashes into compact DDMMYYYY date strings to enforce dd-mm-yyyy format.
        """
        def _repl(match: re.Match) -> str:
            return f"{match.group('day')}-{match.group('month')}-{match.group('year')}"

        return self._compact_date_pattern.sub(_repl, text)

    def _is_application_code(self, text: str) -> bool:
        """
        Check if text matches application code pattern: XXX-XXX-XXXX
        where X is alphanumeric (3-3-4 format).

        Examples: K75-19Z-RZLT
        """
        pattern = r'^[A-Z0-9]{3}-[A-Z0-9]{3}-[A-Z0-9]{4}$'
        return bool(re.match(pattern, text.strip(), re.IGNORECASE))

    def _is_doc_identity_code(self, text: str) -> bool:
        """
        Check if text starts with DOC IDENTITY prefix.

        Examples: DOC IDENTITY 0109 PASSPORT SPONSOR 2/2
        """
        return text.strip().upper().startswith("DOC IDENTITY")

    def _parse_doc_identity_description(self, text: str) -> str:
        """
        Extract descriptive text from DOC IDENTITY lines.

        Example:
            Input: "DOC IDENTITY 0109 PASSPORT SPONSOR 2/2"
            Output: "PASSPORT SPONSOR 2/2"
        """
        if not self._is_doc_identity_code(text):
            return text

        # Remove "DOC IDENTITY" prefix and numeric code
        # Pattern: DOC IDENTITY <digits> <description>
        pattern = r'^DOC\s+IDENTITY\s+\d+\s+'
        result = re.sub(pattern, '', text.strip(), flags=re.IGNORECASE)
        return result.strip()

    def _extract_form_id(self, text: str) -> Optional[str]:
        """
        Extract real form ID from page content, excluding DOC IDENTITY codes
        and application codes.

        Returns:
            Form ID string if found (e.g., "B07001", "7103-03"), None otherwise
        """
        if not text:
            return None

        # Look for FORM_ID pattern in the text
        # Pattern: **FORM_ID**: `xxx` or FORM_ID**: `xxx`
        for line in text.splitlines():
            line = line.strip()

            # Match FORM_ID pattern with backticks
            match = re.search(r'\*\*FORM_ID\*\*:\s*`([^`]+)`', line)
            if not match:
                # Try without ** prefix
                match = re.search(r'FORM_ID\*\*:\s*`([^`]+)`', line)

            if match:
                form_id = match.group(1).strip()

                # Exclude DOC IDENTITY codes
                if self._is_doc_identity_code(form_id):
                    return None

                # Exclude application codes (XXX-XXX-XXXX pattern)
                if self._is_application_code(form_id):
                    return None

                # Return real form ID
                return form_id

        return None

    def _summarize_page(self, text: str) -> str:
        """
        Build a short one-line summary for a page from its extracted content.
        Prefers PAGE_TYPE if available (AI-generated page classification).
        Otherwise skips metadata lines (FORM_ID, PAGE_IMAGES, TOC markers)
        and extracts meaningful content.
        """
        if not text or not text.strip():
            return "Empty page"

        # First pass: look for PAGE_TYPE (AI-generated page classification)
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if "PAGE_TYPE" in line and "`" in line:
                match = re.search(r'`([^`]+)`', line)
                if match:
                    page_type = match.group(1).strip()
                    if page_type:
                        return page_type[:120]

        # Second pass: extract from content (fallback if no PAGE_TYPE)
        for raw_line in text.splitlines():
            line = raw_line.strip()

            # Skip empty lines and HTML comments
            if not line or line.startswith("<!--"):
                continue

            # Skip PAGE_TYPE lines (we already checked these above)
            if "PAGE_TYPE" in line:
                continue

            # Skip FORM_ID lines - these are metadata, not content descriptions
            # But check if it's a DOC IDENTITY code first - extract descriptive text
            if "FORM_ID" in line and "`" in line:
                # Extract the value between backticks (handle empty backticks)
                match = re.search(r'`([^`]*)`', line)
                if match:
                    form_id_value = match.group(1).strip()

                    # Skip empty form IDs
                    if not form_id_value:
                        continue

                    # If it's a DOC IDENTITY code, extract descriptive text
                    if self._is_doc_identity_code(form_id_value):
                        description = self._parse_doc_identity_description(form_id_value)
                        if description:
                            return description[:120]

                    # If it's an application code, skip this line
                    if self._is_application_code(form_id_value):
                        continue

                    # Otherwise it's metadata (real form ID), skip to find content
                    continue
                else:
                    # Line has FORM_ID but no backticks - skip it
                    continue

            # Remove common markdown prefixes and bullets
            clean_line = line.lstrip("#").lstrip("*").lstrip("-").strip()
            clean_line = clean_line.strip("*").strip()

            # Check for explicit empty page indicators
            if clean_line.lower() in {"this page is empty", "page is empty"}:
                return "Empty page"

            # Return first meaningful content line
            if clean_line:
                summary = clean_line[:120]
                # Strip leading section numbers:
                # - "1. ", "2. " (number + period + space)
                # - "1 ", "2 " (number + space, no period)
                # - "1.2 ", "4.2.1 " (nested numbering)
                # - "1A. ", "2B. " (number + letter + period)
                summary = re.sub(r'^\d+(\.\d+)*[A-Z]?\.?\s+', '', summary)
                return summary

        return "Empty page"

    def _create_header(self, summary: Dict, cost: float, extra_metadata: Optional[str] = None) -> str:
        """Create extraction result header as hidden HTML comment"""
        from ..models.config import MODEL_CONFIGS

        mc = MODEL_CONFIGS.get(self.model_config.model_id)
        if mc:
            model_name = mc.name
            endpoint = mc.get_endpoint()
            provider = f"{endpoint.name} ({endpoint.region.value.upper()})"
            context_window = mc.context_window
            model_display = f"{mc.model_id} ({mc.model_id_at_endpoint})"
        else:
            model_name = self.model_config.model_id
            provider = "Unknown"
            context_window = "Unknown"
            model_display = self.model_config.model_id

        actual_cost = self.total_token_usage.cost

        lines = ["<!--"]
        if extra_metadata:
            lines.append("EXTRA METADATA")
            lines.extend(extra_metadata.strip().splitlines())
            lines.append("")

        lines.extend([
            "PDF EXTRACTION METADATA",
            f"Source PDF: {os.path.basename(self.pdf_path)}",
            f"MD5: {self.calculate_md5()}",
            f"Processing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Processing Time: {self.last_duration:.1f} seconds",
            f"AI Model: {model_display}",
            f"Model Name: {model_name}",
            f"Provider: {provider}",
            f"Context Window: {context_window}",
            "",
            "Processing Summary:",
            f"- Total pages: {summary['total_pages']}",
            f"- AI processed: {summary['total_pages'] - len(summary.get('empty_pages', []))} pages",
            f"- Empty pages: {len(summary.get('empty_pages', []))}",
            "",
            "Token Usage:",
            f"- Input tokens: {self.total_token_usage.input_tokens:,}",
            f"- Output tokens: {self.total_token_usage.output_tokens:,}",
            f"- Total tokens: {self.total_token_usage.total_tokens:,}",
            "",
            "Cost:",
            f"- Total: ${actual_cost:.6f}",
            "-->",
            "",
        ])

        return "\n".join(lines)

    def _build_top_level_toc(self, toc_entries: List[Tuple[int, str, Optional[str]]]) -> str:
        """
        Build a grouped, hidden TOC block placed after the metadata header.
        Format: "- Page N: <description> [FORM_ID: xxx]" or "- Page N: <description>"
        """
        lines = ["<!-- TOC START -->", "TABLE OF CONTENTS:"]
        for page_num, summary, form_id in toc_entries:
            if form_id:
                lines.append(f"- Page {page_num}: {summary} [FORM_ID: {form_id}]")
            else:
                lines.append(f"- Page {page_num}: {summary}")
        lines.extend(["<!-- TOC END -->", ""])
        return "\n".join(lines)

    def _emit_audit_log(
        self,
        status: str,
        start_dt: datetime,
        end_dt: datetime,
        error: Optional[str],
        audit_log_path: Optional[str],
        audit_log_hook: Optional[Callable[[Dict[str, Any]], None]],
        audit_retention_hours: Optional[int],
        output_path: Optional[str] = None,
    ) -> None:
        """
        Append an audit log entry (JSONL) and optionally invoke a hook.
        """
        try:
            from ..models.config import MODEL_CONFIGS

            mc = MODEL_CONFIGS.get(self.model_config.model_id)
            if mc:
                model_name = mc.name
                endpoint = mc.get_endpoint()
                provider = f"{endpoint.name} ({endpoint.region.value.upper()})"
            else:
                model_name = self.model_config.model_id
                provider = "Unknown"

            entry: Dict[str, Any] = {
                "timestamp": end_dt.isoformat(),
                "status": status,
                "file": os.path.basename(self.pdf_path),
                "md5": self.calculate_md5(),
                "model_id": self.model_config.model_id,
                "model_name": model_name,
                "provider": provider,
                "start_time": start_dt.isoformat(),
                "end_time": end_dt.isoformat(),
                "duration_seconds": (end_dt - start_dt).total_seconds(),
            }
            if output_path:
                entry["output_path"] = output_path
            if error:
                entry["error"] = error

            if audit_log_hook:
                try:
                    audit_log_hook(dict(entry))
                except Exception:
                    pass

            if audit_log_path:
                log_path = Path(audit_log_path).expanduser()
                log_path.parent.mkdir(parents=True, exist_ok=True)

                if audit_retention_hours is not None and log_path.exists():
                    cutoff = datetime.now() - timedelta(hours=audit_retention_hours)
                    kept_lines: List[str] = []
                    for line in log_path.read_text(encoding="utf-8").splitlines():
                        try:
                            data = json.loads(line)
                            ts_raw = data.get("timestamp") or data.get("end_time")
                            if ts_raw and datetime.fromisoformat(ts_raw) < cutoff:
                                continue
                        except Exception:
                            pass
                        kept_lines.append(line)
                    log_path.write_text("\n".join(kept_lines) + ("\n" if kept_lines else ""), encoding="utf-8")

                with log_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, separators=(",", ":")) + "\n")
        except Exception:
            # Do not let audit logging failures break extraction
            pass

    def get_token_usage_summary(self) -> Dict:
        """Get detailed token usage summary"""
        return {
            'total': {
                'input_tokens': self.total_token_usage.input_tokens,
                'output_tokens': self.total_token_usage.output_tokens,
                'total_tokens': self.total_token_usage.total_tokens,
                'cost': self.total_token_usage.cost,
            },
            'per_page': {
                page_num: {
                    'input_tokens': usage.input_tokens,
                    'output_tokens': usage.output_tokens,
                    'cost': usage.cost,
                }
                for page_num, usage in self.page_token_usage.items()
            },
            'model': self.total_token_usage.model_id,
        }

    def save_results(self, content: str, output_file: str):
        """Save extraction results to file"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
