import os
import re
from dataclasses import dataclass, field
from typing import List

import fitz


@dataclass
class PageText:
    page_number: int
    raw_text: str


@dataclass
class DocumentText:
    filename: str
    filepath: str
    num_pages: int
    pages: List[PageText] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n\n".join(page.raw_text for page in self.pages)

    @property
    def cleaned_text(self) -> str:
        return clean_text(self.full_text)


def clean_text(text: str) -> str:
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'^\s*[a-zA-Z]\s*$', '', text, flags=re.MULTILINE)
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    text = text.strip()
    return text


def extract_text_from_pdf(filepath: str) -> DocumentText:
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
