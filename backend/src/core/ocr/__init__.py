"""OCR module for async image text extraction using vision models.

Supports Qwen-VL via DashScope for image understanding.
"""
import os
import hashlib
import json
import base64
from pathlib import Path
from typing import Optional
from abc import ABC, abstractmethod

import httpx

# Cache directory for OCR results (avoid re-calling API for same file)
_OCR_CACHE_DIR = Path(__file__).parent.parent.parent.parent / "ocr_cache"
_OCR_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _get_file_hash(file_path: str) -> str:
    """Compute MD5 hash of file content for cache key."""
    h = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_ocr_cache(file_hash: str) -> Optional[list[dict]]:
    """Load cached OCR results if they exist."""
    cache_file = _OCR_CACHE_DIR / f"{file_hash}.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _save_ocr_cache(file_hash: str, results: list[dict]) -> None:
    """Save OCR results to cache."""
    cache_file = _OCR_CACHE_DIR / f"{file_hash}.json"
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[OCR] Cache save failed: {e}")


class VisionModel(ABC):
    """Base class for vision models."""

    @abstractmethod
    async def describe_image(self, image_base64: str, prompt: str = None) -> str:
        """Describe image content or extract text."""
        pass


class QwenVL(VisionModel):
    """Qwen Vision-Language Model (DashScope) - async."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ALIYUN_API_KEY", "")
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        self.model = "qwen-vl-plus"
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy-create shared async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
        return self._client

    async def describe_image(self, image_base64: str, prompt: str = None) -> str:
        """Describe image using async Qwen-VL."""
        if not prompt:
            prompt = (
                "请详细描述这张图片的内容。如果图片中包含文字，请提取所有文字内容。"
                "如果图片是图表、表格或示意图，请描述其结构和关键信息。"
            )

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": self.model,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "image": f"data:image/png;base64,{image_base64}"
                                },
                                {
                                    "text": prompt
                                }
                            ]
                        }
                    ]
                },
            }

            response = await self.client.post(
                self.base_url,
                headers=headers,
                json=payload,
            )

            if response.status_code == 200:
                data = response.json()
                output = data.get("output", {})
                choices = output.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    content = message.get("content", [])
                    # Content is a list of dicts: [{"text": "..."}]
                    if isinstance(content, list) and content:
                        return content[0].get("text", "")
                    elif isinstance(content, str):
                        return content

            print(f"[Qwen-VL] API error: {response.status_code} - {response.text[:200]}")
            return ""

        except Exception as e:
            print(f"[Qwen-VL] Error: {e}")
            return ""

    async def close(self):
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class OCRProcessor:
    """Async OCR processor with vision models.

    Uses Qwen-VL (DashScope) for image understanding.
    """

    def __init__(self):
        self.models = []

        # Qwen-VL via DashScope (primary)
        qwen_key = os.getenv("ALIYUN_API_KEY", "")
        if qwen_key:
            self.models.append(("Qwen-VL", QwenVL(qwen_key)))

        if not self.models:
            print("[OCR] Warning: No vision model configured. Set ALIYUN_API_KEY.")

    async def process_image(self, image_base64: str, prompt: str = None) -> str:
        """Process image with fallback models (async).

        Tries each model in order until one succeeds.

        Args:
            image_base64: Base64 encoded image
            prompt: Optional custom prompt

        Returns:
            Image description or extracted text
        """
        for model_name, model in self.models:
            try:
                result = await model.describe_image(image_base64, prompt)
                if result and len(result) > 10:
                    print(f"[OCR] Success with {model_name}")
                    return result
                else:
                    print(f"[OCR] {model_name} returned empty or too short result")
            except Exception as e:
                print(f"[OCR] {model_name} failed: {e}")
                continue

        print("[OCR] All models failed")
        return ""

    async def process_image_with_context(self, image_base64: str, context: str = "") -> str:
        """Process image with document context for better understanding (async).

        Args:
            image_base64: Base64 encoded image
            context: Surrounding text context

        Returns:
            Image description
        """
        prompt = (
            f"这是一份文档中的图片。文档上下文：{context[:200] if context else '无'}\n\n"
            "请详细描述这张图片的内容，包括：\n"
            "1. 图片类型（图表、示意图、照片等）\n"
            "2. 主要内容和结构\n"
            "3. 所有可见的文字内容\n"
            "4. 关键数据或信息"
        )

        return await self.process_image(image_base64, prompt)

    async def close(self):
        """Close all underlying vision model clients."""
        for _, model in self.models:
            await model.close()


# Global OCR processor instance
_ocr_processor = None


def get_ocr_processor() -> OCRProcessor:
    """Get or create global OCR processor instance."""
    global _ocr_processor
    if _ocr_processor is None:
        _ocr_processor = OCRProcessor()
    return _ocr_processor


async def process_pdf_images(file_path: str, doc_id: str, output_dir: str = None) -> list[dict]:
    """Extract and process images from PDF with intelligent async OCR strategy.

    Strategy:
    1. Check cache first (based on file hash)
    2. Try extracting embedded images first (save to uploads/images/{doc_id}/)
    3. If no embedded images, do page screenshots for pages with little text
    4. Limit OCR pages to control API costs

    Args:
        file_path: Path to PDF file
        doc_id: Document ID for naming
        output_dir: Directory to save extracted images (default: uploads/images/{doc_id}/)

    Returns:
        List of dicts with image descriptions and permanent image paths
    """
    from ..chunker.pdf_parser import extract_images_from_pdf, get_page_screenshots
    import pdfplumber

    # Check cache first
    file_hash = _get_file_hash(file_path)
    cached = _load_ocr_cache(file_hash)
    if cached is not None:
        print(f"[OCR] Cache hit for {file_path} ({len(cached)} results)")
        return cached

    # Determine output directory for persistent image storage
    if output_dir is None:
        from ..config import IMAGE_STORAGE_DIR
        output_dir = os.path.join(IMAGE_STORAGE_DIR, doc_id)

    try:
        os.makedirs(output_dir, exist_ok=True)

        # Step 1: Try extracting embedded images
        images = extract_images_from_pdf(file_path, output_dir)

        if images:
            print(f"[OCR] Found {len(images)} embedded images in PDF")
            results = await _process_image_list(images)
            _save_ocr_cache(file_hash, results)
            return results

        # Step 2: No embedded images - use page screenshots
        print("[OCR] No embedded images found, analyzing pages for OCR...")

        from ..config import OCR_MAX_PAGES, OCR_FULL_DOCUMENT

        pages_to_ocr = []

        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)

            if OCR_FULL_DOCUMENT:
                pages_to_ocr = list(range(1, total_pages + 1))
            else:
                max_ocr_pages = OCR_MAX_PAGES

                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""

                    if page_num <= 3:
                        pages_to_ocr.append(page_num)
                        continue

                    visual_indicators = [
                        len(text.strip()) < 200,
                        'chart' in text.lower() or '图' in text,
                        'figure' in text.lower() or 'fig.' in text.lower(),
                        'diagram' in text.lower() or '架构' in text,
                        'table' in text.lower() and len(text.strip()) < 500,
                    ]

                    if any(visual_indicators):
                        pages_to_ocr.append(page_num)

                    if len(pages_to_ocr) >= max_ocr_pages:
                        break

        print(f"[OCR] Selected {len(pages_to_ocr)} pages for screenshot OCR: {pages_to_ocr}")

        all_screenshots = get_page_screenshots(file_path, output_dir)
        selected_screenshots = [s for s in all_screenshots if s["page_num"] in pages_to_ocr]

        results = await _process_image_list(selected_screenshots)
        _save_ocr_cache(file_hash, results)
        return results

    except Exception as e:
        print(f"[OCR] process_pdf_images error: {e}")
        return []


async def _process_image_list(images: list[dict]) -> list[dict]:
    """Process a list of images with async OCR.

    Args:
        images: List of image dicts with image_base64

    Returns:
        List of dicts with descriptions
    """
    ocr = get_ocr_processor()
    results = []

    for img_info in images:
        image_base64 = img_info.get("image_base64", "")
        if not image_base64:
            continue

        # Get image description
        description = await ocr.process_image(image_base64)

        if description:
            results.append({
                "page_num": img_info.get("page_num", 0),
                "image_idx": img_info.get("image_idx", 0),
                "description": description,
                "image_path": img_info.get("image_path"),
                "width": img_info.get("width", 0),
                "height": img_info.get("height", 0),
            })

    return results
