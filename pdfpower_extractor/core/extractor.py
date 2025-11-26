"""
Text and AI extraction modules
"""

import os
import base64
import requests
import fitz  # PyMuPDF
from pdf2image import convert_from_path
from io import BytesIO
from typing import Dict, List, Tuple


class TextExtractor:
    """Extract text from PDF pages using PyMuPDF"""
    
    def extract_page(self, pdf_path: str, page_num: int) -> str:
        """Extract text from a single page"""
        try:
            with fitz.open(pdf_path) as doc:
                page = doc[page_num - 1]  # Convert to 0-based
                text = page.get_text()
                
                return f"""
{'='*80}
=== Page {page_num} (Text Extraction) ===
{'='*80}
{text.strip()}
"""
        except Exception as e:
            return f"\n=== Page {page_num} (Error) ===\nFailed to extract: {str(e)}\n"


class AIExtractor:
    """Extract content from PDF pages using AI vision models"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
    
    def extract_page(self, pdf_path: str, page_num: int, model: str = "google/gemini-2.5-flash") -> Dict:
        """Extract content from a page using AI"""
        
        try:
            # Convert page to PNG
            images = convert_from_path(
                pdf_path,
                first_page=page_num,
                last_page=page_num,
                dpi=150,
                grayscale=True
            )
            
            if not images:
                raise Exception("Failed to convert page to image")
            
            # Convert to base64
            img_buffer = BytesIO()
            images[0].save(img_buffer, format='PNG')
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
            
            # Prepare API request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            prompt = """Extract all text from this form page. 

For TEXT FIELDS with filled-in values:
- Combine the label and its value on ONE LINE
- If a value appears in a shaded/colored box, put it on the same line as its label
- Use a colon to separate label from value
- Example: "Name field: John_Doe"

For RADIO BUTTONS and CHECKBOXES:
- Put the question/label on its own line with a colon
- List each option on a separate line below
- Use ● for selected and ○ for unselected radio buttons
- Use ☒ for checked and ☐ for unchecked checkboxes
- Example format:
  "Question text:"
  "● selected option"
  "○ unselected option"
  "○ another unselected option"

IMPORTANT: Text fields get their values on the same line, but radio/checkbox groups get options on separate lines."""
            
            data = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{img_base64}"
                                }
                            }
                        ]
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 4000
            }
            
            # Make API request
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Calculate approximate cost
            from ..models.config import MODEL_CONFIGS, DEFAULT_MODEL
            model_config = MODEL_CONFIGS.get(model, MODEL_CONFIGS[DEFAULT_MODEL])
            cost = model_config['cost_per_page']
            
            return {
                'content': f"""
{'='*80}
=== Page {page_num} (AI Processed) ===
{'='*80}
{content}
""",
                'cost': cost
            }
            
        except Exception as e:
            return {
                'content': f"\n=== Page {page_num} (Error) ===\nAI extraction failed: {str(e)}\n",
                'cost': 0.0
            }

    def extract_pages_batch(self, pdf_path: str, pages: List[int], model: str = "google/gemini-2.5-flash") -> Tuple[Dict[int, str], float]:
        """
        Extract a small batch of pages in one multimodal request.

        Returns (content_by_page, total_cost).
        """
        if not pages:
            return {}, 0.0

        try:
            # Convert pages to images
            images = convert_from_path(
                pdf_path,
                first_page=min(pages),
                last_page=max(pages),
                dpi=150,
                grayscale=True
            )
            images_map = {}
            for idx, img in enumerate(images, start=min(pages)):
                if idx in pages:
                    buf = BytesIO()
                    img.save(buf, format='PNG')
                    buf.seek(0)
                    images_map[idx] = base64.b64encode(buf.read()).decode('utf-8')

            # Prepare content parts with clear per-page markers
            content_parts = [
                {
                    "type": "text",
                    "text": (
                        "You will receive multiple PDF pages as images. For EACH page:\n"
                        "- Start with `=== PAGE <page_number> ===`\n"
                        "- Follow the same extraction rules as before (fields on one line; radios/checkboxes with bullets)\n"
                        "- Do NOT merge pages together. Keep each page separate.\n"
                        "- Preserve page order."
                    )
                }
            ]
            for page_num in pages:
                content_parts.append({"type": "text", "text": f"=== INPUT PAGE {page_num} ==="})
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{images_map[page_num]}"}
                })

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": content_parts
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 4000
            }

            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            content = result['choices'][0]['message']['content']

            # Split by our markers
            content_by_page: Dict[int, str] = {}
            current_page = None
            current_lines: List[str] = []
            for line in (content or "").splitlines():
                if line.strip().startswith("=== PAGE ") and "===" in line:
                    # flush previous
                    if current_page is not None:
                        content_by_page[current_page] = "\n".join(current_lines).strip()
                    try:
                        current_page = int(line.split("PAGE")[1].split("===")[0].strip())
                    except Exception:
                        current_page = None
                    current_lines = [line]
                else:
                    current_lines.append(line)
            if current_page is not None:
                content_by_page[current_page] = "\n".join(current_lines).strip()

            # Calculate approximate cost
            from ..models.config import MODEL_CONFIGS, DEFAULT_MODEL
            model_config = MODEL_CONFIGS.get(model, MODEL_CONFIGS[DEFAULT_MODEL])
            total_cost = model_config['cost_per_page'] * len(pages)

            return content_by_page, total_cost

        except Exception as e:
            # Return per-page errors
            return {
                p: f"\n=== Page {p} (Error) ===\nAI extraction failed: {str(e)}\n" for p in pages
            }, 0.0
