"""
Hybrid PDF Processor - Core processing engine
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


class HybridPDFProcessor:
    """Main processor that routes pages based on content analysis"""
    
    def __init__(self, pdf_path: str, api_key: str):
        self.pdf_path = pdf_path
        self.api_key = api_key
        self.analyzer = PDFAnalyzer(pdf_path)
        self.text_extractor = TextExtractor()
        self.ai_extractor = AIExtractor(api_key)
        self.last_cost = 0.0
        self.last_duration = 0.0
        self._md5_hash = None
        self.page_modes: Dict[int, str] = {}
    
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
    
    def process(
        self,
        model: str = "google/gemini-2.5-flash",
        progress_callback: Optional[Callable[[Any], None]] = None,
        force_ai_extraction: bool = False,
        batch_size: int = 5,
    ) -> str:
        """Process the PDF using hybrid approach"""

        start_time = time.time()

        # Analyze PDF structure
        summary = self.analyzer.analyze()

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

        # Process form pages with AI
        form_pages = summary['form_pages']
        for i in range(0, len(form_pages), max(1, batch_size)):
            batch = form_pages[i:i + batch_size]
            # mark batch start
            for page_num in batch:
                emit("start", page_num, "ai_extraction")

            content_map, batch_cost = self.ai_extractor.extract_pages_batch(
                self.pdf_path,
                batch,
                model=model
            )

            for page_num in batch:
                page_content = content_map.get(page_num) or f"\n=== Page {page_num} (Error) ===\nAI extraction failed: missing content\n"
                results[page_num] = {
                    'content': page_content,
                    'method': 'ai_extraction',
                    'cost': batch_cost / len(batch) if batch else 0.0
                }
                page_modes[page_num] = "AI-VISION-EXTRACTION"
                processed += 1
                emit("done", page_num, "ai_extraction")
            total_cost += batch_cost
        
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

        # Update summary costs with actual API-derived totals
        ai_pages_count = len(summary.get("form_pages", [])) or 0
        avg_cost_per_ai_page = (total_cost / ai_pages_count) if ai_pages_count else 0.0
        summary["hybrid_cost"] = total_cost
        summary["full_ai_cost"] = (avg_cost_per_ai_page * summary["total_pages"]) if avg_cost_per_ai_page else total_cost
        savings = summary["full_ai_cost"] - summary["hybrid_cost"]
        summary["savings"] = savings
        summary["savings_percentage"] = (savings / summary["full_ai_cost"] * 100) if summary["full_ai_cost"] else 0.0

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
        header = self._create_header(summary, model, total_cost)

        return header + '\n'.join(merged_content)
    
    def _create_header(self, summary: Dict, model: str, cost: float) -> str:
        """Create extraction result header"""

        from ..models.config import MODEL_CONFIGS
        model_info = MODEL_CONFIGS.get(model, {
            'name': model,
            'provider': 'Via OpenRouter',
            'context_window': 'Unknown'
        })

        mode_line = ""
        if summary.get("force_ai_extraction"):
            mode_line = "Mode: Forced AI on all non-empty pages (hybrid bypassed)\n"

        header = f"""PDF EXTRACTION RESULTS
{'='*80}
Source PDF: {os.path.basename(self.pdf_path)}
Source PDF MD5: {self.calculate_md5()}
Processing Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Processing Time: {self.last_duration:.1f} seconds

AI Model: {model}
- Name: {model_info['name']}
- Provider: {model_info['provider']}
- Context: {model_info['context_window']}
{mode_line if mode_line else ""}

Processing Summary:
- Total pages: {summary['total_pages']}
- Text extraction: {len(summary['text_pages'])} pages ($0.00)
- AI processing: {len(summary['form_pages'])} pages (${cost:.4f})
- Empty pages: {len(summary['empty_pages'])}

Cost Savings:
- Full AI cost: ${summary['full_ai_cost']:.4f}
- Hybrid cost: ${cost:.4f}
- Saved: ${summary['full_ai_cost'] - cost:.4f} ({summary['savings_percentage']:.1f}%)
{'='*80}
"""
        return header
    
    def save_results(self, content: str, output_file: str):
        """Save extraction results to file"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
