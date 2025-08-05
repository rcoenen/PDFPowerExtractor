"""
PDF Page Analyzer - Detects form fields vs pure text pages
"""

import fitz  # PyMuPDF
from typing import List, Dict
from models.config import MODEL_CONFIGS, DEFAULT_MODEL


class PDFAnalyzer:
    """Analyzes PDF pages to determine content type"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = None
        self._summary = None
    
    def analyze(self) -> Dict:
        """Analyze PDF and return summary"""
        if self._summary:
            return self._summary
            
        with fitz.open(self.pdf_path) as doc:
            total_pages = len(doc)
            text_pages = []
            form_pages = []
            empty_pages = []
            
            for page_num in range(total_pages):
                page = doc[page_num]
                page_number = page_num + 1  # 1-based
                
                # Extract text
                text = page.get_text()
                has_text = len(text.strip()) > 0
                
                # Check for form widgets
                widgets = list(page.widgets())
                has_forms = len(widgets) > 0
                
                # Categorize page
                if not has_text and not has_forms:
                    empty_pages.append(page_number)
                elif has_forms:
                    form_pages.append(page_number)
                else:
                    text_pages.append(page_number)
        
        # Calculate costs
        model_config = MODEL_CONFIGS[DEFAULT_MODEL]
        cost_per_page = model_config['cost_per_page']
        
        full_ai_cost = total_pages * cost_per_page
        hybrid_cost = len(form_pages) * cost_per_page
        savings = full_ai_cost - hybrid_cost
        savings_percentage = (savings / full_ai_cost * 100) if full_ai_cost > 0 else 0
        
        self._summary = {
            'total_pages': total_pages,
            'text_pages': text_pages,
            'form_pages': form_pages,
            'empty_pages': empty_pages,
            'text_percentage': len(text_pages) / total_pages * 100,
            'form_percentage': len(form_pages) / total_pages * 100,
            'full_ai_cost': full_ai_cost,
            'hybrid_cost': hybrid_cost,
            'savings': savings,
            'savings_percentage': savings_percentage
        }
        
        return self._summary