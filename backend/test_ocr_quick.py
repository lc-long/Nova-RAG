"""Quick OCR test with real page screenshot."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv('.env')

from src.core.ocr import get_ocr_processor
from src.core.chunker.pdf_parser import get_page_screenshots

# Get a real page screenshot
pdf_path = os.path.join('..', 'tests', 'novatech_documentation.pdf')
screenshots = get_page_screenshots(pdf_path)

if screenshots:
    # Use page 3 (has chart)
    img = screenshots[2]
    page_num = img["page_num"]
    width = img["width"]
    height = img["height"]
    print(f"Testing with page {page_num} screenshot ({width}x{height})")
    
    ocr = get_ocr_processor()
    result = ocr.process_image(img["image_base64"])
    
    if result:
        print(f"SUCCESS! Description ({len(result)} chars):")
        print(result[:500])
    else:
        print("FAILED: No result")
else:
    print("No screenshots found")
