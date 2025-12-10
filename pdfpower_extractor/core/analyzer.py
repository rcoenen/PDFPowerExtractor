"""
PDF Page Analyzer - Detects form fields vs pure text pages
"""

import fitz  # PyMuPDF
from typing import List, Dict, Tuple
from ..models.config import MODEL_CONFIGS, DEFAULT_MODEL


def detect_page_images(doc: fitz.Document, page_num: int) -> str:
    """
    Detect images on a PDF page and determine their color mode.

    Args:
        doc: Open PyMuPDF document
        page_num: 0-based page number

    Returns:
        HTML comment string like: <!-- PAGE IMAGES: 1 | IMAGE 1: COLOR -->
        or <!-- PAGE IMAGES: 0 --> if no images
    """
    page = doc[page_num]
    # get_images(full=True) returns tuples:
    # (xref, smask, width, height, bpc, colorspace, alt_colorspace, name, filter, referencer)
    # Index 4 = bpc (bits per component), Index 5 = colorspace
    images = page.get_images(full=True)

    if not images:
        return "<!-- PAGE IMAGES: 0 -->"

    image_descriptions = []
    for idx, img in enumerate(images, 1):
        # Get colorspace and bpc directly from tuple - no image extraction needed!
        bpc = img[4] if len(img) > 4 else 8
        colorspace = img[5] if len(img) > 5 else ""

        # Determine color mode based on colorspace string
        # PyMuPDF returns strings: "DeviceGray", "DeviceRGB", "DeviceCMYK", "ICCBased", etc.
        cs_lower = str(colorspace).lower()
        if "gray" in cs_lower:
            # Check if it's truly B&W or grayscale by looking at bpc
            if bpc == 1:
                color_mode = "BLACK_WHITE"
            else:
                color_mode = "GRAYSCALE"
        elif "rgb" in cs_lower or "cmyk" in cs_lower or "icc" in cs_lower:
            # ICCBased is typically a color profile (RGB/CMYK with ICC profile)
            color_mode = "COLOR"
        else:
            color_mode = "UNKNOWN"

        image_descriptions.append(f"IMAGE {idx}: {color_mode}")

    count = len(images)
    descriptions = " | ".join(image_descriptions)
    return f"<!-- PAGE IMAGES: {count} | {descriptions} -->"


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
        
        # Calculate estimated costs based on token pricing
        model_config = MODEL_CONFIGS[DEFAULT_MODEL]
        pricing = model_config.pricing

        # Estimate cost per page: image tokens (input) + ~500 output tokens
        est_input_tokens = pricing.image_tokens_estimate
        est_output_tokens = 500  # typical output per page
        cost_per_page = (
            (est_input_tokens / 1_000_000) * pricing.input_cost_per_1m +
            (est_output_tokens / 1_000_000) * pricing.output_cost_per_1m
        )

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