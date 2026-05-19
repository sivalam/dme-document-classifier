"""PDF text extraction module.

Dual-path extraction:
- pdfplumber for digital PDFs with selectable text
- GPT-4o-mini vision API for scanned/image-only PDFs
Auto-detects which path based on extracted text length threshold.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExtractionResult:
    """Result of extracting content from a PDF."""
    file_path: str
    text: str
    method: str  # "pdfplumber" | "vision"
    page_count: int


def extract_text_pdfplumber(pdf_path: Path) -> str:
    """Extract text from a digital PDF using pdfplumber.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Concatenated text from all pages.
    """
    raise NotImplementedError


def extract_text_vision(pdf_path: Path) -> str:
    """Extract text from a scanned PDF via GPT-4o-mini vision API.

    Converts each page to an image and sends to the vision endpoint.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Transcribed text from all pages.
    """
    raise NotImplementedError


def extract(pdf_path: Path, text_threshold: int = 50) -> ExtractionResult:
    """Extract content from a PDF, auto-selecting the extraction method.

    If pdfplumber yields fewer than `text_threshold` characters the file
    is treated as a scanned image and routed to the vision path.

    Args:
        pdf_path: Path to the PDF file.
        text_threshold: Minimum character count to consider digital extraction successful.

    Returns:
        ExtractionResult with text and metadata.
    """
    raise NotImplementedError
