"""Test OCR functionality with PDF images."""
import os
import sys
import base64

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Load .env file
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), '..', 'backend', '.env')
load_dotenv(env_path)

from src.core.chunker.pdf_parser import extract_images_from_pdf
from src.core.ocr import get_ocr_processor


def test_pdf_image_extraction(pdf_path: str):
    """Test PDF image extraction."""
    print(f"Testing PDF image extraction: {pdf_path}")
    print("=" * 50)
    
    images = extract_images_from_pdf(pdf_path)
    
    if not images:
        print("No images found in PDF")
        return []
    
    print(f"Found {len(images)} images:")
    for img in images:
        print(f"  - Page {img['page_num']}, Image {img.get('image_idx', 0)}: "
              f"{img.get('width', 0)}x{img.get('height', 0)}")
    
    return images


def test_ocr_with_sample():
    """Test OCR with a sample image."""
    print("\nTesting OCR processor")
    print("=" * 50)
    
    ocr = get_ocr_processor()
    
    if not ocr.models:
        print("No OCR models configured!")
        print("Please set MINIMAX_API_KEY and MINIMAX_GROUP_ID or ALIYUN_API_KEY")
        return
    
    print(f"Available models: {[name for name, _ in ocr.models]}")
    
    # Create a simple test image (1x1 white pixel PNG)
    # In real usage, this would be an actual image from PDF
    test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    
    print("\nTesting with sample image...")
    result = ocr.process_image(test_image_b64)
    
    if result:
        print(f"OCR Result: {result[:100]}...")
    else:
        print("OCR returned empty result (expected for test image)")


def test_full_pipeline(pdf_path: str):
    """Test full OCR pipeline with PDF."""
    print("\n" + "=" * 50)
    print("Full OCR Pipeline Test")
    print("=" * 50)
    
    # Extract images
    images = extract_images_from_pdf(pdf_path)
    
    if not images:
        print("No images to process")
        return
    
    # Process with OCR
    ocr = get_ocr_processor()
    
    for i, img in enumerate(images[:3]):  # Test first 3 images
        print(f"\nProcessing image {i+1}/{min(len(images), 3)}...")
        
        image_b64 = img.get("image_base64", "")
        if not image_b64:
            print("  No image data")
            continue
        
        result = ocr.process_image(image_b64)
        
        if result:
            print(f"  Description: {result[:150]}...")
        else:
            print("  No description generated")


if __name__ == "__main__":
    # Test with command line argument or default PDF
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = os.path.join(os.path.dirname(__file__), "novatech_documentation.pdf")
    
    if not os.path.exists(pdf_path):
        print(f"PDF not found: {pdf_path}")
        sys.exit(1)
    
    # Test image extraction
    test_pdf_image_extraction(pdf_path)
    
    # Test OCR processor
    test_ocr_with_sample()
    
    # Test full pipeline
    test_full_pipeline(pdf_path)
