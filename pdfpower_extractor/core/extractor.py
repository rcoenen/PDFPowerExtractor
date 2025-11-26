"""
Text and AI extraction modules
"""

import os
import base64
import requests
import fitz  # PyMuPDF
from pdf2image import convert_from_path
from io import BytesIO
from typing import Dict


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