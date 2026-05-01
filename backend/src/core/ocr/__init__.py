"""OCR module for image text extraction using vision models.

Supports multiple vision models with fallback:
1. MiniMax-VL-01 (primary - user has more tokens)
2. Qwen-VL-Plus (fallback)
"""
import os
import base64
import requests
from typing import Optional
from abc import ABC, abstractmethod


class VisionModel(ABC):
    """Base class for vision models."""
    
    @abstractmethod
    def describe_image(self, image_base64: str, prompt: str = None) -> str:
        """Describe image content or extract text."""
        pass


class MiniMaxVL(VisionModel):
    """MiniMax Vision-Language Model."""
    
    def __init__(self, api_key: str = None, group_id: str = None):
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY", "")
        self.group_id = group_id or os.getenv("MINIMAX_GROUP_ID", "")
        self.base_url = "https://api.minimax.chat/v1"
        self.model = "MiniMax-VL-01"
    
    def describe_image(self, image_base64: str, prompt: str = None) -> str:
        """Describe image using MiniMax-VL."""
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
                "group_id": self.group_id,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                "stream": False,
            }
            
            response = requests.post(
                f"{self.base_url}/text/chatcompletion_v2",
                headers=headers,
                json=payload,
                timeout=30,
            )
            
            if response.status_code == 200:
                data = response.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
            
            print(f"[MiniMax-VL] API error: {response.status_code}")
            return ""
            
        except Exception as e:
            print(f"[MiniMax-VL] Error: {e}")
            return ""


class QwenVL(VisionModel):
    """Qwen Vision-Language Model (DashScope)."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ALIYUN_API_KEY", "")
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        self.model = "qwen-vl-plus"
    
    def describe_image(self, image_base64: str, prompt: str = None) -> str:
        """Describe image using Qwen-VL."""
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
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30,
            )
            
            if response.status_code == 200:
                data = response.json()
                output = data.get("output", {})
                choices = output.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
            
            print(f"[Qwen-VL] API error: {response.status_code}")
            return ""
            
        except Exception as e:
            print(f"[Qwen-VL] Error: {e}")
            return ""


class OCRProcessor:
    """OCR processor with multi-model fallback."""
    
    def __init__(self):
        self.models = []
        
        # Initialize models in priority order
        minimax_key = os.getenv("MINIMAX_API_KEY", "")
        minimax_group = os.getenv("MINIMAX_GROUP_ID", "")
        if minimax_key and minimax_group:
            self.models.append(("MiniMax-VL", MiniMaxVL(minimax_key, minimax_group)))
        
        qwen_key = os.getenv("ALIYUN_API_KEY", "")
        if qwen_key:
            self.models.append(("Qwen-VL", QwenVL(qwen_key)))
    
    def process_image(self, image_base64: str, prompt: str = None) -> str:
        """Process image with fallback models.
        
        Tries each model in order until one succeeds.
        
        Args:
            image_base64: Base64 encoded image
            prompt: Optional custom prompt
            
        Returns:
            Image description or extracted text
        """
        for model_name, model in self.models:
            try:
                result = model.describe_image(image_base64, prompt)
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
    
    def process_image_with_context(self, image_base64: str, context: str = "") -> str:
        """Process image with document context for better understanding.
        
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
        
        return self.process_image(image_base64, prompt)


# Global OCR processor instance
_ocr_processor = None


def get_ocr_processor() -> OCRProcessor:
    """Get or create global OCR processor instance."""
    global _ocr_processor
    if _ocr_processor is None:
        _ocr_processor = OCRProcessor()
    return _ocr_processor


def process_pdf_images(file_path: str, doc_id: str) -> list[dict]:
    """Extract and process all images from PDF.
    
    Args:
        file_path: Path to PDF file
        doc_id: Document ID for naming
        
    Returns:
        List of dicts with image descriptions
    """
    from .pdf_parser import extract_images_from_pdf
    
    # Create temp directory for images
    temp_dir = os.path.join(os.path.dirname(file_path), f"temp_images_{doc_id}")
    
    try:
        # Extract images
        images = extract_images_from_pdf(file_path, temp_dir)
        
        if not images:
            print(f"[OCR] No images found in {file_path}")
            return []
        
        print(f"[OCR] Found {len(images)} images in PDF")
        
        # Process each image
        ocr = get_ocr_processor()
        results = []
        
        for img_info in images:
            image_base64 = img_info.get("image_base64", "")
            if not image_base64:
                continue
            
            # Get image description
            description = ocr.process_image(image_base64)
            
            if description:
                results.append({
                    "page_num": img_info["page_num"],
                    "image_idx": img_info.get("image_idx", 0),
                    "description": description,
                    "image_path": img_info.get("image_path"),
                    "width": img_info.get("width", 0),
                    "height": img_info.get("height", 0),
                })
        
        return results
        
    finally:
        # Cleanup temp directory
        try:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except Exception:
            pass
