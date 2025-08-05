"""
Hybrid PDF Processor - Core processing engine
"""

import os
import hashlib
import time
from datetime import datetime
from typing import List, Dict, Optional, Callable
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
        progress_callback: Optional[Callable] = None
    ) -> str:
        """Process the PDF using hybrid approach"""
        
        start_time = time.time()
        
        # Analyze PDF structure
        summary = self.analyzer.analyze()
        
        # Track progress
        total_pages = summary['total_pages']
        processed = 0
        
        # Process results
        results = {}
        total_cost = 0.0
        
        # Extract text from pure text pages
        for page_num in summary['text_pages']:
            if progress_callback:
                progress_callback(int(processed / total_pages * 100))
            
            results[page_num] = {
                'content': self.text_extractor.extract_page(self.pdf_path, page_num),
                'method': 'text_extraction',
                'cost': 0.0
            }
            processed += 1
        
        # Process form pages with AI
        for page_num in summary['form_pages']:
            if progress_callback:
                progress_callback(int(processed / total_pages * 100))
            
            result = self.ai_extractor.extract_page(
                self.pdf_path, 
                page_num,
                model=model
            )
            
            results[page_num] = {
                'content': result['content'],
                'method': 'ai_extraction',
                'cost': result['cost']
            }
            total_cost += result['cost']
            processed += 1
        
        # Skip empty pages
        for page_num in summary['empty_pages']:
            results[page_num] = {
                'content': f"\n=== Page {page_num} (Empty) ===\n[This page is empty]\n",
                'method': 'skipped',
                'cost': 0.0
            }
            processed += 1
        
        if progress_callback:
            progress_callback(100)
        
        # Store metrics
        self.last_duration = time.time() - start_time
        self.last_cost = total_cost
        
        # Merge results in order
        merged_content = []
        for page_num in sorted(results.keys()):
            merged_content.append(results[page_num]['content'])
        
        # Create header
        header = self._create_header(summary, model, total_cost)
        
        return header + '\n\n'.join(merged_content)
    
    def _create_header(self, summary: Dict, model: str, cost: float) -> str:
        """Create extraction result header"""
        
        from models.config import MODEL_CONFIGS
        model_info = MODEL_CONFIGS.get(model, {
            'name': model,
            'provider': 'Via OpenRouter',
            'context_window': 'Unknown'
        })
        
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