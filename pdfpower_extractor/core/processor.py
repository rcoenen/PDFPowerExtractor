"""
Hybrid PDF Processor - Core processing engine

Supports multiple extraction modes:
- TEXT_ONLY: Pure PyMuPDF extraction with radio/checkbox detection (free, instant)
- AI: Vision-based extraction using configured model (gemini, nano, etc.)

Model and endpoint configuration is handled via ExtractionConfig.model_config_id
which references configurations in models/config.py
"""

import os
import hashlib
import time
from datetime import datetime
from typing import List, Dict, Optional, Callable, Any
import glob
import json

from .analyzer import PDFAnalyzer
from .extractor import TextExtractor, AIExtractor
from .config import ExtractionConfig, ExtractionMode, OutputFormat
from .formatter import MarkdownFormatter, format_as_canonical_markdown
from .validator import OutputValidator, ValidationResult
from ..models.config import TokenUsage


class HybridPDFProcessor:
    """
    Main processor that routes pages based on content analysis and configuration.

    Usage:
        # Text-only mode (no AI, free)
        from pdfpower_extractor.core import text_only_config
        processor = HybridPDFProcessor(pdf_path, config=text_only_config())
        result = processor.process()

        # AI mode with Gemini (US endpoint)
        from pdfpower_extractor.core import gemini_flash_config
        processor = HybridPDFProcessor(pdf_path, config=gemini_flash_config())
        result = processor.process()

        # AI mode with Gemini (EU endpoint)
        from pdfpower_extractor.core import gemini_flash_eu_config
        processor = HybridPDFProcessor(pdf_path, config=gemini_flash_eu_config())
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

        # Get model config for AI modes
        self.model_config = self.config.get_model_config()

        self.analyzer = PDFAnalyzer(pdf_path)
        self.text_extractor = TextExtractor()
        self.ai_extractor = AIExtractor(
            api_key=api_key,
            config=self.config,
            model_config=self.model_config
        )
        self.validator = OutputValidator()
        self.formatter = MarkdownFormatter(
            use_unicode_symbols=(self.config.output_format == OutputFormat.PLAIN_TEXT)
        )

        self.last_cost = 0.0
        self.last_duration = 0.0
        self._md5_hash = None
        self.page_modes: Dict[int, str] = {}
        self.validation_results: Dict[int, ValidationResult] = {}

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
    
    def check_existing_extraction(self, pattern: str = "extracted-*.txt") -> Optional[str]:
        """Check if we have a cached extraction for this PDF"""
        current_md5 = self.calculate_md5()
        
        for file_path in glob.glob(pattern):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    # Check first 20 lines for MD5
                    for i, line in enumerate(f):
                        if i > 20:
                            break
                        if "Source PDF MD5:" in line:
                            existing_md5 = line.split(":", 1)[1].strip()
                            if existing_md5 == current_md5:
                                return file_path
            except:
                continue
        return None
    
    def _determine_extraction_mode(self, summary: Dict) -> ExtractionMode:
        """
        Return the configured extraction mode.
        """
        return self.config.mode

    def process(
        self,
        progress_callback: Optional[Callable[[Any], None]] = None,
        force_ai_extraction: bool = None,
    ) -> str:
        """
        Process the PDF using hybrid approach.

        Args:
            progress_callback: Callback for progress updates
            force_ai_extraction: Override force_ai setting from config

        Returns:
            Extracted text content
        """
        start_time = time.time()

        # Analyze PDF structure
        summary = self.analyzer.analyze()

        # Determine extraction mode
        effective_mode = self._determine_extraction_mode(summary)

        # Determine if we should force AI extraction
        if force_ai_extraction is None:
            force_ai_extraction = self.config.force_ai_extraction

        # For TEXT_ONLY mode, never use AI
        if effective_mode == ExtractionMode.TEXT_ONLY:
            force_ai_extraction = False

        if self.config.verbose:
            print(f"[INFO] Extraction mode: {effective_mode.value}")
            if self.model_config:
                print(f"[INFO] Model: {self.model_config.name}")
                print(f"[INFO] Endpoint: {self.model_config.get_endpoint().name}")
            print(f"[INFO] Force AI: {force_ai_extraction}")

        # Optionally bypass hybrid mode and force AI on all non-empty pages
        if force_ai_extraction:
            # Copy so we don't mutate cached summary
            summary = dict(summary)
            total_pages = summary["total_pages"]
            empty_pages = set(summary.get("empty_pages", []))
            forced_form_pages = [p for p in range(1, total_pages + 1) if p not in empty_pages]
            summary["form_pages"] = forced_form_pages
            summary["text_pages"] = []
            # Recompute cost metrics based on forced AI pages
            cost_per_page = summary["full_ai_cost"] / total_pages if total_pages else 0.0
            hybrid_cost = len(forced_form_pages) * cost_per_page
            savings = summary["full_ai_cost"] - hybrid_cost
            summary.update(
                {
                    "hybrid_cost": hybrid_cost,
                    "savings": savings,
                    "savings_percentage": (savings / summary["full_ai_cost"] * 100) if summary["full_ai_cost"] else 0,
                    "force_ai_extraction": True,
                }
            )

        # Track progress
        total_pages = summary['total_pages']
        processed = 0
        
        # Process results
        results: Dict[int, Dict[str, Any]] = {}
        total_cost = 0.0
        page_modes: Dict[int, str] = {}

        def emit(status: str, page_num: int, mode: str):
            if progress_callback:
                try:
                    progress_callback({
                        "status": status,
                        "page": page_num,
                        "total": total_pages,
                        "mode": mode
                    })
                except Exception:
                    # Fall back to legacy percentage callback
                    try:
                        progress_callback(int(processed / total_pages * 100))
                    except Exception:
                        pass
        
        # Extract text from pure text pages
        for page_num in summary['text_pages']:
            emit("start", page_num, "text_extraction")
            results[page_num] = {
                'content': self.text_extractor.extract_page(self.pdf_path, page_num),
                'method': 'text_extraction',
                'cost': 0.0
            }
            page_modes[page_num] = "TEXT-EXTRACTION"
            processed += 1
            emit("done", page_num, "text_extraction")

        # Process form pages with AI (one page at a time for reliability)
        form_pages = summary['form_pages']
        for page_num in form_pages:
            emit("start", page_num, "ai_extraction")

            result = self.ai_extractor.extract_page(self.pdf_path, page_num)

            # Track token usage
            page_usage = result.get('token_usage', TokenUsage())
            self.page_token_usage[page_num] = page_usage
            self.total_token_usage = self.total_token_usage + page_usage

            # Validate output if configured
            if self.config.validation.validate_output:
                validation = self.validator.validate(result['content'], page_num)
                self.validation_results[page_num] = validation

                if not validation.is_valid and self.config.validation.fallback_to_raw:
                    # Fallback to text extraction on validation failure
                    if self.config.verbose:
                        print(f"[WARN] Page {page_num} validation failed, falling back to text extraction")
                    fallback_content = self.text_extractor.extract_page(self.pdf_path, page_num)
                    results[page_num] = {
                        'content': fallback_content,
                        'method': 'ai_extraction_fallback',
                        'token_usage': page_usage,
                    }
                    page_modes[page_num] = "AI-FALLBACK-TO-TEXT"
                else:
                    results[page_num] = {
                        'content': result['content'],
                        'method': 'ai_extraction',
                        'token_usage': page_usage,
                    }
                    page_modes[page_num] = "AI-VISION-EXTRACTION"
            else:
                results[page_num] = {
                    'content': result['content'],
                    'method': 'ai_extraction',
                    'token_usage': page_usage,
                }
                page_modes[page_num] = "AI-VISION-EXTRACTION"

            total_cost += page_usage.cost
            processed += 1
            emit("done", page_num, "ai_extraction")
        
        # Skip empty pages
        for page_num in summary['empty_pages']:
            results[page_num] = {
                'content': "[This page is empty]\n",
                'method': 'skipped',
                'cost': 0.0
            }
            page_modes[page_num] = "EMPTY"
            processed += 1
            emit("done", page_num, "skipped")

        emit("done", processed, "complete")

        # Store metrics
        self.last_duration = time.time() - start_time
        self.last_cost = total_cost
        self.page_modes = page_modes

        # Update summary costs with actual API-derived totals (no estimation)
        summary["hybrid_cost"] = total_cost
        summary["full_ai_cost"] = total_cost
        summary["savings"] = 0.0
        summary["savings_percentage"] = 0.0

        # Merge results in order with explicit headers, stripping any internal page headers
        merged_content = []
        for page_num in sorted(results.keys()):
            mode_label = page_modes.get(page_num, "unknown")
            body = (results[page_num]['content'] or "").splitlines()
            # drop leading blanks and internal headers like "=== Page"
            while body and not body[0].strip():
                body = body[1:]
            while body and body[0].lstrip().startswith("==="):
                body = body[1:]
            cleaned = "\n".join(body).strip()
            header = "\n".join([
                "=" * 80,
                f"=== Page {page_num} of {total_pages} === METHOD: {mode_label}",
                "=" * 80,
            ])
            merged_content.append(f"{header}\n{cleaned}".rstrip() + "\n")

        # Create header
        effective_model = self.model_config.model_id if self.model_config else None
        header = self._create_header(summary, effective_model, total_cost, effective_mode)

        # Combine content
        raw_output = header + '\n'.join(merged_content)

        # Optionally convert to canonical markdown
        if self.config.output_format == OutputFormat.CANONICAL_MARKDOWN:
            # Just the content without header for markdown conversion
            content_only = '\n'.join(merged_content)
            markdown_content = format_as_canonical_markdown(
                content_only,
                use_unicode=False  # Use ASCII markers for markdown
            )
            return header + markdown_content

        return raw_output
    
    def _create_header(
        self,
        summary: Dict,
        model: str,
        cost: float,
        mode: ExtractionMode = None
    ) -> str:
        """Create extraction result header"""

        from ..models.config import MODEL_CONFIGS

        # Handle TEXT_ONLY mode (no model used)
        if mode == ExtractionMode.TEXT_ONLY or not model:
            model_name = "Text Extraction (PyMuPDF)"
            provider = "Local"
            context_window = "N/A"
            model_display = "None (Text Extraction)"
        else:
            mc = MODEL_CONFIGS.get(model)
            if mc:
                model_name = mc.name
                endpoint = mc.get_endpoint()
                provider = f"{endpoint.name} ({endpoint.region.value.upper()})"
                context_window = mc.context_window
                model_display = f"{mc.model_id} ({mc.model_id_at_endpoint})"
            else:
                model_name = model
                provider = "Unknown"
                context_window = "Unknown"
                model_display = model

        mode_line = ""
        if summary.get("force_ai_extraction"):
            mode_line = "Mode: Forced AI on all non-empty pages (hybrid bypassed)\n"
        elif mode:
            mode_line = f"Mode: {mode.value.upper()}\n"

        lines = [
            "PDF EXTRACTION RESULTS",
            "=" * 80,
            f"Source PDF: {os.path.basename(self.pdf_path)}",
            f"Source PDF MD5: {self.calculate_md5()}",
            f"Processing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Processing Time: {self.last_duration:.1f} seconds",
            "",
            f"AI Model: {model_display}",
            f"- Name: {model_name}",
            f"- Provider: {provider}",
            f"- Context: {context_window}",
        ]
        if mode_line:
            lines.append(mode_line)
        # Calculate estimated vs actual cost (caching savings)
        estimated_cost = self.total_token_usage.input_cost + self.total_token_usage.output_cost
        actual_cost = self.total_token_usage.cost
        cache_savings = estimated_cost - actual_cost if estimated_cost > actual_cost else 0.0

        lines.extend([
            "",
            "Processing Summary:",
            f"- Total pages: {summary['total_pages']}",
            f"- Text extraction: {len(summary['text_pages'])} pages ($0.00)",
            f"- AI processing: {len(summary['form_pages'])} pages",
            f"- Empty pages: {len(summary['empty_pages'])}",
            "",
            "Token Usage:",
            f"- Input tokens: {self.total_token_usage.input_tokens:,}",
            f"- Output tokens: {self.total_token_usage.output_tokens:,}",
            f"- Total tokens: {self.total_token_usage.total_tokens:,}",
            "",
            "Cost (from Requesty API):",
            f"- Actual cost: ${actual_cost:.6f}",
        ])
        if cache_savings > 0:
            lines.append(f"- Cache savings: ${cache_savings:.6f} ({cache_savings/estimated_cost*100:.0f}% saved)")
        lines.append("=" * 80)
        return "\n".join(lines) + "\n"

    def get_token_usage_summary(self) -> Dict:
        """Get detailed token usage summary"""
        return {
            'total': {
                'input_tokens': self.total_token_usage.input_tokens,
                'output_tokens': self.total_token_usage.output_tokens,
                'total_tokens': self.total_token_usage.total_tokens,
                'input_cost': self.total_token_usage.input_cost,
                'output_cost': self.total_token_usage.output_cost,
                'total_cost': self.total_token_usage.cost,
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
            'endpoint': self.total_token_usage.endpoint,
        }

    def save_results(self, content: str, output_file: str):
        """Save extraction results to file"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
