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
from datetime import datetime
from typing import Dict, Optional, Callable, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from .analyzer import PDFAnalyzer, detect_page_images
import fitz  # PyMuPDF
from .extractor import AIExtractor
from .config import ExtractionConfig
from .validator import OutputValidator, ValidationResult
from ..models.config import TokenUsage


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
    ) -> str:
        """
        Process the PDF using AI vision extraction.

        Args:
            progress_callback: Callback for progress updates
            debug_save_images: If True, save converted images to /tmp/powerpdf_extracted_images/
            extra_metadata: Optional multi-line string to include inside the metadata comment
                before the PDF extraction metadata (keeps a single well-formed comment block).

        Returns:
            Extracted content as Markdown
        """
        start_time = time.time()

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

        # Process pages with AI (parallel with 5 workers for Gemini EU region pooling)
        max_workers = 5

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

        # Process pages in parallel
        page_results = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_single_page, pn): pn for pn in pages_to_process}
            for future in as_completed(futures):
                page_num, result = future.result()
                page_results[page_num] = result
                emit("done", page_num)

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

        # Build markdown output with image detection
        merged_content = []
        toc_entries: List[Tuple[int, str]] = []
        with fitz.open(self.pdf_path) as doc:
            for page_num in sorted(results.keys()):
                body = (results[page_num]['content'] or "").splitlines()
                # Drop leading blanks and internal headers
                while body and not body[0].strip():
                    body = body[1:]
                while body and body[0].lstrip().startswith("==="):
                    body = body[1:]
                cleaned = "\n".join(body).strip()
                page_summary = self._summarize_page(cleaned)
                toc_entries.append((page_num, page_summary))

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
        if "<!-- TOC START -->" not in final_output:
            raise ValueError("Grouped TOC block missing from output; header assembly failed.")
        return final_output

    def _normalize_compact_dates(self, text: str) -> str:
        """
        Insert dashes into compact DDMMYYYY date strings to enforce dd-mm-yyyy format.
        """
        def _repl(match: re.Match) -> str:
            return f"{match.group('day')}-{match.group('month')}-{match.group('year')}"

        return self._compact_date_pattern.sub(_repl, text)

    def _summarize_page(self, text: str) -> str:
        """
        Build a short one-line summary for a page from its extracted content.
        """
        if not text or not text.strip():
            return "Empty page"

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("<!--"):
                continue
            # Remove common markdown prefixes and bullets
            line = line.lstrip("#").lstrip("*").lstrip("-").strip()
            line = line.strip("*").strip()
            if line.lower() in {"this page is empty", "page is empty"}:
                return "Empty page"
            if line:
                summary = line[:120]
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

    def _build_top_level_toc(self, toc_entries: List[Tuple[int, str]]) -> str:
        """
        Build a grouped, hidden TOC block placed after the metadata header.
        """
        lines = ["<!-- TOC START -->", "TABLE OF CONTENTS:"]
        for page_num, summary in toc_entries:
            lines.append(f"- Page {page_num}: {summary}")
        lines.extend(["<!-- TOC END -->", ""])
        return "\n".join(lines)

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
