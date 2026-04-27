"""DOCX document parser using python-docx with UTF-8 preservation."""
from docx import Document
from docx.oxml.text.paragraph import CT_P
from lxml import etree


def extract_text_from_docx(file_path: str) -> str:
    """Extract all text from DOCX file preserving Unicode."""
    doc = Document(file_path)
    paragraphs = []

    for para in doc.paragraphs:
        p_elem = para._element
        texts = []
        for r in p_elem.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
            if r.text:
                texts.append(r.text)
        text = ''.join(texts)
        if text.strip():
            paragraphs.append(text)

    return "\n\n".join(paragraphs)