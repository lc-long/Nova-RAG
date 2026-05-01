"""Test OCR - page screenshot approach for vector graphics."""
import os
import sys
import base64

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from src.core.chunker.pdf_parser import extract_images_from_pdf, get_page_screenshots


def test_page_screenshots(pdf_path: str, output_dir: str = None):
    """Test page screenshot extraction."""
    print(f"Testing page screenshots: {pdf_path}")
    print("=" * 50)
    
    screenshots = get_page_screenshots(pdf_path, output_dir)
    
    if not screenshots:
        print("No screenshots generated")
        return
    
    print(f"Generated {len(screenshots)} page screenshots:")
    for s in screenshots:
        print(f"  - Page {s['page_num']}: {s['width']}x{s['height']}, "
              f"base64 length: {len(s['image_base64'])} chars")
        if s.get('image_path'):
            print(f"    Saved to: {s['image_path']}")


def test_image_extraction(pdf_path: str):
    """Test embedded image extraction."""
    print(f"\nTesting embedded image extraction: {pdf_path}")
    print("=" * 50)
    
    images = extract_images_from_pdf(pdf_path)
    print(f"Found {len(images)} embedded images")
    
    return images


if __name__ == "__main__":
    pdf_path = os.path.join(os.path.dirname(__file__), "novatech_documentation.pdf")
    output_dir = os.path.join(os.path.dirname(__file__), "test_screenshots")
    
    if not os.path.exists(pdf_path):
        print(f"PDF not found: {pdf_path}")
        sys.exit(1)
    
    # Test embedded images
    test_image_extraction(pdf_path)
    
    # Test page screenshots
    test_page_screenshots(pdf_path, output_dir)
