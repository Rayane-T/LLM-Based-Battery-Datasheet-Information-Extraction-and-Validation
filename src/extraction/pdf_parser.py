"""
PDF text extraction module using PyMuPDF.

Extracts raw text content from battery datasheet PDFs, handling
multi-page documents and performing basic text cleaning.
"""

import os
import re
from dataclasses import dataclass, field
from typing import List

import fitz  # PyMuPDF


@dataclass
class PageText:
    """Represents extracted text from a single PDF page."""
    page_number: int
    raw_text: str


@dataclass
class DocumentText:
    """Represents extracted text from an entire PDF document."""
    filename: str
    filepath: str
    num_pages: int
    pages: List[PageText] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        """Concatenate all page texts into a single string."""
        return "\n\n".join(page.raw_text for page in self.pages)

    @property
    def cleaned_text(self) -> str:
        """Return cleaned version of the full text."""
        return clean_text(self.full_text)


def clean_text(text: str) -> str:
    """
    Clean extracted PDF text by removing artifacts and normalizing whitespace.
    
    Args:
        text: Raw text extracted from PDF.
    
    Returns:
        Cleaned text string.
    """
    # Replace multiple spaces with single space
    text = re.sub(r'[ \t]+', ' ', text)

    # Replace multiple newlines with double newline
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remove isolated single characters on their own lines (PDF artifacts)
    text = re.sub(r'^\s*[a-zA-Z]\s*$', '', text, flags=re.MULTILINE)

    # Strip leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)

    # Remove empty lines at start/end
    text = text.strip()

    return text


def extract_text_from_pdf(filepath: str) -> DocumentText:
    """
    Extract text from a single PDF file.
    
    Args:
        filepath: Path to the PDF file.
    
    Returns:
        DocumentText object containing extracted text from all pages.
    
    Raises:
        FileNotFoundError: If the PDF file does not exist.
        RuntimeError: If the PDF cannot be opened or parsed.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"PDF file not found: {filepath}")

    try:
        doc = fitz.open(filepath)
    except Exception as e:
        raise RuntimeError(f"Failed to open PDF: {filepath}") from e

    filename = os.path.basename(filepath)
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        raw_text = page.get_text("text")
        pages.append(PageText(page_number=page_num + 1, raw_text=raw_text))

    doc.close()

    return DocumentText(
        filename=filename,
        filepath=filepath,
        num_pages=len(pages),
        pages=pages,
    )


def extract_all_documents(documents_dir: str) -> List[DocumentText]:
    """
    Extract text from all PDF files in a directory.
    
    Args:
        documents_dir: Path to directory containing PDF files.
    
    Returns:
        List of DocumentText objects, one per PDF file.
    """
    if not os.path.isdir(documents_dir):
        raise FileNotFoundError(f"Documents directory not found: {documents_dir}")

    documents = []
    pdf_files = sorted(
        f for f in os.listdir(documents_dir) if f.lower().endswith('.pdf')
    )

    for pdf_file in pdf_files:
        filepath = os.path.join(documents_dir, pdf_file)
        doc_text = extract_text_from_pdf(filepath)
        documents.append(doc_text)

    return documents


if __name__ == "__main__":
    # Quick test: extract text from all datasheets
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from config import DOCUMENTS_DIR

    docs = extract_all_documents(DOCUMENTS_DIR)
    for doc in docs:
        print(f"{'='*60}")
        print(f"File: {doc.filename}")
        print(f"Pages: {doc.num_pages}")
        print(f"Text length: {len(doc.full_text)} chars")
        print(f"Cleaned text length: {len(doc.cleaned_text)} chars")
        print(f"First 500 chars of cleaned text:")
        print(doc.cleaned_text[:500])
        print()
