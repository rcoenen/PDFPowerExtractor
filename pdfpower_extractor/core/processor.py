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
from datetime import datetime
from typing import Dict, Optional, Callable, Any
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
    ) -> str:
        """
        Process the PDF using AI vision extraction.

        Args:
            progress_callback: Callback for progress updates

        Returns:
            Extracted content as Markdown
        """
        start_time = time.time()

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
            result = self.ai_extractor.extract_page(self.pdf_path, page_num, use_markdown=True)
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
        with fitz.open(self.pdf_path) as doc:
            for page_num in sorted(results.keys()):
                body = (results[page_num]['content'] or "").splitlines()
                # Drop leading blanks and internal headers
                while body and not body[0].strip():
                    body = body[1:]
                while body and body[0].lstrip().startswith("==="):
                    body = body[1:]
                cleaned = "\n".join(body).strip()

                # Detect images on this page using PyMuPDF
                image_comment = detect_page_images(doc, page_num - 1)  # 0-based index

                header = f"\n{'='*60}\n{'PAGE ' + str(page_num) + ' OF ' + str(total_pages):^60}\n{'='*60}"
                merged_content.append(f"{header}\n{image_comment}\n{cleaned}".rstrip() + "\n")

        # Create header
        file_header = self._create_header(summary, total_cost)

        return file_header + '\n'.join(merged_content)

    def _create_header(self, summary: Dict, cost: float) -> str:
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

        lines = [
            "<!--",
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
        ]

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


# Backwards compatibility alias
HybridPDFProcessor = PDFProcessor
