"""
Text and AI extraction modules
"""

import os
import base64
import time
import requests
import fitz  # PyMuPDF
from pdf2image import convert_from_path
from io import BytesIO
from typing import Dict, List, Tuple, Optional
import tempfile
import uuid
from pathlib import Path

import re
from .config import ExtractionConfig, LLMConfig
from .prompts import get_vision_prompt, get_system_prompt
from ..models.config import AIModelConfig, get_model_config, ENDPOINTS, TokenUsage


def normalize_radio_buttons(content: str) -> str:
    """
    Normalize radio button output to consistent (x)/( ) format.
    Converts various formats like '◉ option (x)' or '◉ option' to '(x) option'.
    """
    lines = content.split('\n')
    normalized = []

    for line in lines:
        # Pattern: ◉ option text (x) or ◉ option text -> (x) option text
        if '◉' in line:
            # Remove (x) if present after option text
            line = re.sub(r'\s*\(x\)\s*$', '', line)
            # Replace ◉ with (x)
            line = line.replace('◉', '(x)')

        # Pattern: ○ option text ( ) or ○ option text -> ( ) option text
        if '○' in line:
            # Remove ( ) if present after option text
            line = re.sub(r'\s*\(\s*\)\s*$', '', line)
            # Replace ○ with ( )
            line = line.replace('○', '( )')

        normalized.append(line)

    return '\n'.join(normalized)

# Optional HuggingFace support
try:
    from huggingface_hub import InferenceClient
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False


class TextExtractor:
    """Extract text from PDF pages using PyMuPDF with radio/checkbox detection"""

    # Wingdings character mappings for form elements (empty states)
    WINGDINGS_RADIO = {
        '\uf0a1',  # Empty radio button circle
        '\uf0a2',  # Alternative empty radio
    }

    WINGDINGS_CHECKBOX = {
        '\uf06d',  # Empty checkbox
        '\uf06e',  # Alternative empty checkbox
    }

    # ZapfDingbats characters that indicate a filled/selected state
    ZAPF_FILLED_MARKERS = {
        'G',       # Filled bullet (common)
        'l',       # Filled circle
        'n',       # Filled square (checkmark)
        '\u2714',  # Heavy check mark
        '\u2713',  # Check mark
        '4',       # Checkmark in some encodings
    }

    def _find_filled_positions(self, page) -> List[Tuple[float, float]]:
        """Find positions of filled indicators (graphics AND ZapfDingbats text markers)"""
        filled_positions = []

        # Method 1: Look for small black filled shapes (graphic dots)
        paths = page.get_drawings()
        for path in paths:
            rect = path.get("rect")
            fill = path.get("fill")
            if not rect or not fill:
                continue
            # Black or very dark fill
            if fill == (0.0, 0.0, 0.0) or (isinstance(fill, tuple) and all(c < 0.1 for c in fill)):
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                # Small roughly square shape (radio button dot is typically 3-8 pixels)
                if 2 < w < 12 and 2 < h < 12 and abs(w - h) < 3:
                    center_x = (rect[0] + rect[2]) / 2
                    center_y = (rect[1] + rect[3]) / 2
                    filled_positions.append((center_x, center_y))

        # Method 2: Look for ZapfDingbats fill marker characters
        blocks = page.get_text("dict")
        for block in blocks.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    font = span.get("font", "")
                    if "ZapfDingbats" in font:
                        text = span.get("text", "")
                        if any(c in self.ZAPF_FILLED_MARKERS for c in text):
                            bbox = span.get("bbox", [0, 0, 0, 0])
                            center_x = (bbox[0] + bbox[2]) / 2
                            center_y = (bbox[1] + bbox[3]) / 2
                            filled_positions.append((center_x, center_y))

        return filled_positions

    def _extract_with_radio_detection(self, page, page_num: int) -> str:
        """Extract text with proper radio button state detection"""
        # Get all filled indicator positions (graphics + ZapfDingbats markers)
        filled_positions = self._find_filled_positions(page)

        # Get text with position information
        blocks = page.get_text("dict")

        # Build list of all text spans with their positions
        lines_output = []

        for block in blocks.get("blocks", []):
            if block.get("type") != 0:  # Skip non-text blocks
                continue

            for line in block.get("lines", []):
                line_bbox = line.get("bbox", [0, 0, 0, 0])
                line_y = (line_bbox[1] + line_bbox[3]) / 2  # Vertical center

                # Process spans in this line
                line_text = ""

                for span in line.get("spans", []):
                    text = span.get("text", "")
                    font = span.get("font", "")
                    span_bbox = span.get("bbox", [0, 0, 0, 0])
                    span_center_y = (span_bbox[1] + span_bbox[3]) / 2

                    # Handle Wingdings radio buttons
                    if "Wingdings" in font:
                        for char in text:
                            if char in self.WINGDINGS_RADIO:
                                # Check if this radio is filled (marker nearby)
                                is_filled = False
                                for fx, fy in filled_positions:
                                    # Filled marker should be within ~25px horizontally and ~8px vertically
                                    if abs(fx - span_bbox[0]) < 25 and abs(fy - span_center_y) < 8:
                                        is_filled = True
                                        break
                                line_text += "● " if is_filled else "○ "
                            elif char in self.WINGDINGS_CHECKBOX:
                                # Check if checkbox is filled
                                is_filled = False
                                for fx, fy in filled_positions:
                                    if abs(fx - span_bbox[0]) < 25 and abs(fy - span_center_y) < 8:
                                        is_filled = True
                                        break
                                line_text += "☒ " if is_filled else "☐ "
                            # Skip other Wingdings chars (decorative)

                    # Skip ZapfDingbats fill markers (already processed as position data)
                    elif "ZapfDingbats" in font:
                        # These are fill indicators, not content - skip them
                        pass

                    else:
                        # Regular text
                        line_text += text

                line_text = line_text.strip()
                if line_text:
                    lines_output.append(line_text)

        return "\n".join(lines_output)

    def extract_page(self, pdf_path: str, page_num: int) -> str:
        """Extract text from a single page with radio/checkbox detection"""
        try:
            with fitz.open(pdf_path) as doc:
                page = doc[page_num - 1]  # Convert to 0-based

                # Use enhanced extraction with radio button detection
                text = self._extract_with_radio_detection(page, page_num)

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

    def __init__(
        self,
        api_key: str = None,
        config: Optional[ExtractionConfig] = None,
        model_config: Optional[AIModelConfig] = None
    ):
        """
        Initialize AI extractor.

        Args:
            api_key: API key (overrides env var from model config)
            config: Extraction config for LLM parameters
            model_config: AI model configuration (endpoint, model ID, etc.)
        """
        self.config = config or ExtractionConfig()
        self.model_config = model_config

        # Resolve API key from: explicit param > env var from model config > default env var
        if api_key:
            self.api_key = api_key
        elif model_config:
            env_var = model_config.get_endpoint().api_key_env_var
            self.api_key = os.environ.get(env_var, "")
        else:
            self.api_key = os.environ.get("OPENROUTER_API_KEY", "")

    def extract_page(
        self,
        pdf_path: str,
        page_num: int,
        model: str = None,
        model_config: Optional[AIModelConfig] = None,
        llm_config: Optional[LLMConfig] = None,
        use_markdown: bool = False,
        debug_save_images: bool = False,
        debug_session_dir: Optional[str] = None
    ) -> Dict:
        """
        Extract content from a page using AI vision.

        Args:
            pdf_path: Path to PDF file
            page_num: Page number (1-indexed)
            model: Model identifier (legacy, use model_config instead)
            model_config: AI model configuration (overrides self.model_config)
            llm_config: Optional LLM config override
            use_markdown: If True, use markdown-optimized prompts for structured output
            debug_save_images: If True, save converted images to /tmp/powerpdf_extracted_images/
            debug_session_dir: Optional session directory path (created by processor if None)
        """
        # Resolve model config: param > instance > default
        mc = model_config or self.model_config
        if mc is None and model:
            # Legacy: model string passed directly - try to find matching config
            try:
                mc = get_model_config(model)
            except ValueError:
                # Fall back to creating minimal config for OpenRouter
                pass

        # Get endpoint and model ID
        if mc:
            endpoint = mc.get_endpoint()
            api_url = endpoint.get_chat_url()
            model_id = mc.model_id_at_endpoint

            # Use region pooling for Gemini Flash to avoid quota limits
            if mc.model_id == "gemini_flash":
                from ..models.config import get_gemini_model_with_region
                model_id = get_gemini_model_with_region()
                if self.config and self.config.verbose:
                    region = model_id.split("@")[-1]
                    print(f"    Using Gemini region: {region}")

            api_key = os.environ.get(endpoint.api_key_env_var, self.api_key)
        else:
            # Legacy fallback: OpenRouter
            api_url = "https://openrouter.ai/api/v1/chat/completions"
            model_id = model or "google/gemini-2.5-flash"
            api_key = self.api_key

        cfg = llm_config or self.config.llm

        try:
            # Convert page to PNG (color preserved for Gemini to analyze)
            images = convert_from_path(
                pdf_path,
                first_page=page_num,
                last_page=page_num,
                dpi=150  # 150 DPI balances speed vs accuracy (was 300)
            )

            if not images:
                raise Exception("Failed to convert page to image")

            # Debug: Save image to /tmp/powerpdf_extracted_images/ if enabled
            saved_image_path = None
            if debug_save_images:
                # Use provided session directory or create one
                if debug_session_dir:
                    session_dir = Path(debug_session_dir)
                else:
                    # Fallback: create session directory with timestamp
                    session_id = str(uuid.uuid4())[:8]
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    base_dir = Path("/tmp/powerpdf_extracted_images")
                    session_dir = base_dir / f"session_{timestamp}_{session_id}"
                    session_dir.mkdir(parents=True, exist_ok=True)

                # Generate filename
                pdf_name = Path(pdf_path).stem
                image_filename = f"{pdf_name}_page{page_num:03d}.png"
                image_path = session_dir / image_filename

                # Save image
                images[0].save(image_path, format='PNG')
                saved_image_path = str(image_path)

                if self.config and self.config.verbose:
                    print(f"    💾 Debug: Saved image to {saved_image_path}")

            # Convert to base64 using endpoint's preferred format
            img_buffer = BytesIO()
            img_format = 'PNG'
            img_mime = 'image/png'

            if mc:
                endpoint = mc.get_endpoint()
                fmt = endpoint.image_format.lower()
                quality = endpoint.image_quality

                # Ensure RGB for lossy formats
                img = images[0]
                if fmt in ('jpeg', 'webp_lossy') and img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')

                if fmt == 'webp_lossless':
                    img.save(img_buffer, format='WEBP', lossless=True)
                    img_mime = 'image/webp'
                    img_format = 'WEBP'
                elif fmt == 'webp_lossy':
                    img.save(img_buffer, format='WEBP', quality=quality)
                    img_mime = 'image/webp'
                    img_format = 'WEBP'
                elif fmt == 'jpeg':
                    img.save(img_buffer, format='JPEG', quality=quality)
                    img_mime = 'image/jpeg'
                    img_format = 'JPEG'
                else:  # png (default)
                    images[0].save(img_buffer, format='PNG')

                # Check payload limit and compress further if needed
                if endpoint.max_payload_mb > 0:
                    size_mb = len(img_buffer.getvalue()) / (1024 * 1024)
                    if size_mb > endpoint.max_payload_mb * 0.8:
                        img_buffer = BytesIO()
                        img.save(img_buffer, format='WEBP', quality=min(quality, 85))
                        img_mime = 'image/webp'
                        img_format = 'WEBP'
                        if self.config and self.config.verbose:
                            new_size_mb = len(img_buffer.getvalue()) / (1024 * 1024)
                            print(f"    📦 Compressed: {size_mb:.1f}MB → {new_size_mb:.1f}MB (limit: {endpoint.max_payload_mb}MB)")

                img_buffer.seek(0)
            else:
                images[0].save(img_buffer, format='PNG')
                img_buffer.seek(0)

            img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')

            # Prepare API request headers
            if mc:
                endpoint = mc.get_endpoint()
                headers = {}
                for key, value in endpoint.headers_template.items():
                    headers[key] = value.format(api_key=api_key)
            else:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }

            # Get model-specific prompts (use markdown prompts if requested)
            system_prompt = get_system_prompt(model_id, use_markdown=use_markdown)
            user_prompt = get_vision_prompt(model_id, use_markdown=use_markdown)

            # Debug: Save prompts if debug_save_images is enabled
            if debug_save_images and saved_image_path:
                # Use the same session directory as the image
                session_dir = Path(saved_image_path).parent
                prompt_filename = f"{Path(pdf_path).stem}_page{page_num:03d}_prompts.txt"
                prompt_path = session_dir / prompt_filename

                # Determine prompt type (simplified vs strict)
                prompt_type = "custom"
                if "STRICT FORM DATA EXTRACTOR" in system_prompt:
                    prompt_type = "strict"
                elif "form data extractor" in system_prompt.lower():
                    prompt_type = "simplified"

                with open(prompt_path, 'w', encoding='utf-8') as f:
                    f.write(f"=== PROMPT METADATA ===\n")
                    f.write(f"Model: {model_id}\n")
                    f.write(f"Prompt Type: {prompt_type}\n")
                    f.write(f"Use Markdown: {use_markdown}\n")
                    f.write(f"Page: {page_num}\n")
                    f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"\n{'='*50}\n\n")
                    f.write(f"=== SYSTEM PROMPT ===\n")
                    f.write(f"\n{'='*50}\n\n")
                    f.write(system_prompt)
                    f.write(f"\n\n{'='*50}\n\n")
                    f.write(f"=== USER PROMPT ===\n")
                    f.write(f"\n{'='*50}\n\n")
                    f.write(user_prompt)

                if self.config and self.config.verbose:
                    print(f"    📝 Debug: Saved {prompt_type} prompts to {prompt_path}")

            # Build messages with system prompt
            messages = []
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{img_mime};base64,{img_base64}"
                        }
                    }
                ]
            })

            # Get model parameters (from model config or LLM config)
            if mc:
                params = mc.parameters.to_dict()
                # Override with LLM config if provided
                params["temperature"] = cfg.temperature if cfg.temperature != 0.0 else params["temperature"]
                params["max_tokens"] = cfg.max_tokens
            else:
                params = {
                    "temperature": cfg.temperature,
                    "max_tokens": cfg.max_tokens,
                }
                if cfg.top_p > 0:
                    params["top_p"] = cfg.top_p

            data = {
                "model": model_id,
                "messages": messages,
                **params,
            }

            if self.config.log_prompts:
                print(f"[DEBUG] Model: {model_id}")
                print(f"[DEBUG] Endpoint: {api_url}")
                print(f"[DEBUG] Temperature: {params.get('temperature')}, Top-P: {params.get('top_p')}")
                print(f"[DEBUG] Prompt length: {len(user_prompt)} chars")

            # Check if this is a HuggingFace routed endpoint
            if api_url.startswith("huggingface://"):
                # Extract provider from URL (e.g., "huggingface://nebius" -> "nebius")
                hf_provider = api_url.replace("huggingface://", "").split("/")[0]
                result = self._make_huggingface_request(
                    provider=hf_provider,
                    model_id=model_id,
                    img_base64=img_base64,
                    user_prompt=user_prompt,
                    cfg=cfg,
                    mc=mc
                )
            else:
                # Make standard REST API request with retry logic
                result = self._make_request_with_retry(api_url, headers, data, cfg)

            content = result['choices'][0]['message']['content']

            # Normalize radio button output (convert ◉/○ to (x)/( ))
            content = normalize_radio_buttons(content)

            # Parse token usage from API response
            usage_data = result.get("usage") or {}
            input_tokens = usage_data.get("prompt_tokens", 0)
            output_tokens = usage_data.get("completion_tokens", 0)
            total_tokens = usage_data.get("total_tokens", input_tokens + output_tokens)

            # Use API's reported cost directly (Requesty returns this, Nebius does not)
            api_cost = usage_data.get("cost", 0.0)

            # Model info for reporting
            model_id = mc.model_id if mc else "unknown"
            endpoint = mc.endpoint_id if mc else "unknown"

            # Only calculate cost ourselves if API didn't provide it
            if api_cost:
                actual_cost = api_cost
                input_cost = 0.0  # Not needed - using actual
                output_cost = 0.0
            elif mc:
                input_cost = (input_tokens / 1_000_000) * mc.pricing.input_cost_per_1m
                output_cost = (output_tokens / 1_000_000) * mc.pricing.output_cost_per_1m
                actual_cost = input_cost + output_cost
            else:
                input_cost = 0.0
                output_cost = 0.0
                actual_cost = 0.0

            token_usage = TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost=actual_cost,
                input_cost=input_cost,
                output_cost=output_cost,
                model_id=model_id,
                endpoint=endpoint,
            )

            if self.config.verbose:
                print(f"[TOKENS] Page {page_num}: in={input_tokens}, out={output_tokens}, cost=${actual_cost:.6f}")

            return {
                'content': f"""
{'='*80}
=== Page {page_num} (AI Processed) ===
{'='*80}
{content}
""",
                'token_usage': token_usage,
                'debug_image_path': saved_image_path,
            }

        except Exception as e:
            # Re-raise the exception so the processor can track it as a page error
            # Previously this swallowed errors and returned them as content,
            # which prevented proper batch error handling
            raise RuntimeError(f"AI extraction failed: {str(e)}") from e

    def _make_request_with_retry(self, api_url: str, headers: Dict, data: Dict, cfg: LLMConfig) -> Dict:
        """Make API request with retry logic for rate limiting and resource exhaustion"""
        last_error = None
        max_retries = cfg.max_retries + 2  # Extra retries for rate limiting

        for attempt in range(max_retries + 1):
            try:
                response = requests.post(
                    api_url,
                    headers=headers,
                    json=data,
                    timeout=cfg.timeout_seconds
                )

                  # Check for rate limiting / resource exhausted / server errors
                if response.status_code in (429, 500, 503, 529):
                    if attempt < max_retries:
                        # Check for retry-after header (Nebius sends this)
                        retry_after = response.headers.get('retry-after')
                        if retry_after:
                            try:
                                wait_time = min(float(retry_after), 60)
                            except ValueError:
                                wait_time = min(2 ** (attempt + 1), 30)
                        else:
                            # Exponential backoff: 2s, 4s, 8s, 16s... (max 30s)
                            wait_time = min(2 ** (attempt + 1), 30)
                        if self.config and self.config.verbose:
                            print(f"    ⏳ Rate limited (attempt {attempt + 1}/{max_retries}), waiting {wait_time:.0f}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        response.raise_for_status()

                # Check for resource exhausted in response body (Gemini specific)
                if response.status_code == 200:
                    result = response.json()
                    # Check if response indicates resource exhaustion (quota exceeded)
                    error_msg = str(result.get('error', {}).get('message', '')).lower()
                    if 'resource' in error_msg and 'exhausted' in error_msg:
                        # This is a quota error, not rate limiting - don't retry forever
                        if attempt < 2:  # Only retry twice for quota errors
                            wait_time = 5
                            if self.config and self.config.verbose:
                                print(f"    ⏳ Quota exhausted (attempt {attempt + 1}), waiting {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                        else:
                            raise Exception(f"API quota exhausted: {result.get('error', {}).get('message', 'Unknown error')}")
                    return result

                # Check for quota error in non-200 responses
                if response.status_code in (400, 403):
                    error_text = response.text.lower()
                    if 'quota' in error_text or ('resource' in error_text and 'exhausted' in error_text):
                        raise Exception(f"API quota exhausted (HTTP {response.status_code}): {response.text[:200]}")

                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                last_error = e
                error_str = str(e).lower()

                # Check for rate limiting in error message
                if 'resource' in error_str or 'exhausted' in error_str or '429' in error_str:
                    if attempt < max_retries:
                        wait_time = min(2 ** (attempt + 1), 30)
                        if self.config and self.config.verbose:
                            print(f"    ⏳ API error (attempt {attempt + 1}), waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue

                if attempt < cfg.max_retries:
                    time.sleep(cfg.retry_delay_seconds)
                    continue
                raise

        raise last_error

    def _make_huggingface_request(
        self,
        provider: str,
        model_id: str,
        img_base64: str,
        user_prompt: str,
        cfg: LLMConfig,
        mc: AIModelConfig
    ) -> Dict:
        """Make request via HuggingFace Inference Provider with retry logic"""
        if not HF_AVAILABLE:
            raise ImportError("huggingface_hub not installed. Run: pip install huggingface_hub")

        api_key = os.environ.get("HF_TOKEN", "")
        if not api_key:
            raise ValueError("HF_TOKEN environment variable not set")

        client = InferenceClient(provider=provider, api_key=api_key)
        img_data_url = f"data:image/png;base64,{img_base64}"

        max_retries = cfg.max_retries + 2  # Extra retries for rate limiting
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": img_data_url}},
                            {"type": "text", "text": user_prompt}
                        ]
                    }],
                    max_tokens=cfg.max_tokens,
                    temperature=mc.parameters.temperature if mc else cfg.temperature,
                )

                # Convert HF response to standard format
                content = response.choices[0].message.content
                usage = response.usage

                return {
                    "choices": [{"message": {"content": content}}],
                    "usage": {
                        "prompt_tokens": usage.prompt_tokens if usage else 0,
                        "completion_tokens": usage.completion_tokens if usage else 0,
                        "total_tokens": (usage.prompt_tokens + usage.completion_tokens) if usage else 0,
                    }
                }

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Retry on rate limiting (429) or server errors (5xx)
                if '429' in error_str or 'rate' in error_str or '503' in error_str or '502' in error_str:
                    if attempt < max_retries:
                        wait_time = min(2 ** (attempt + 1), 30)
                        if self.config and self.config.verbose:
                            print(f"    ⏳ HF rate limited (attempt {attempt + 1}/{max_retries}), waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue

                # Don't retry on payment/auth errors
                if '402' in error_str or '401' in error_str or '403' in error_str:
                    raise

                # Retry other errors with shorter backoff
                if attempt < cfg.max_retries:
                    time.sleep(cfg.retry_delay_seconds)
                    continue
                raise

        raise last_error
