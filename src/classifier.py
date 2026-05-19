"""Document classification module.

Classifies DME medical documents into one of six types using the
GPT-4o-mini chat completion API.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.extractor import ExtractionResult

DOCUMENT_TYPES = [
    "Prescription",
    "Sleep Study Report",
    "Physician Notes",
    "Compliance Report",
    "Order",
    "Delivery Ticket",
]


@dataclass
class ClassificationResult:
    """Result of classifying a single document."""
    file_path: str
    document_type: str
    confidence: float
    raw_response: str


def classify(extraction: ExtractionResult, confidence_threshold: float = 0.80) -> ClassificationResult:
    """Classify a document given its extracted content.

    Sends the extracted text (or image description) to GPT-4o-mini and
    parses the structured response into a ClassificationResult.

    Args:
        extraction: Result from the extractor module.
        confidence_threshold: Minimum confidence to accept a classification.

    Returns:
        ClassificationResult with document type and confidence score.
    """
    raise NotImplementedError


def build_prompt(text: str) -> str:
    """Build the classification prompt sent to the LLM.

    Args:
        text: Extracted document text.

    Returns:
        Formatted prompt string.
    """
    raise NotImplementedError
