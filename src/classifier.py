"""
classifier.py
=============
Sends a PDF to OpenAI GPT-4o-mini and returns a document classification.

HOW IT WORKS
------------
We send the raw PDF bytes directly to GPT-4o-mini. The model handles
both text-based and scanned/image PDFs natively — no separate extraction
step needed. See ADR-002 for why we chose this approach over building
a custom text/vision extraction pipeline.

The model returns a structured JSON response with:
- document_type: one of the configured taxonomy types or "Unknown"
- confidence: 0.0 to 1.0
- reasoning: plain English explanation of the classification decision

WHY TEMPERATURE=0
-----------------
We set temperature=0 to make the model as deterministic as possible.
The same document should always produce the same classification.
This matters for debugging, regression testing, and coordinator trust.

WHY WE PIN THE MODEL VERSION
-----------------------------
Model behavior can change between versions. We pin the exact version
string so a model update never silently changes classification results
in production. See ADR-004.

WHY TAXONOMY COMES FROM THE DATABASE
------------------------------------
Business taxonomy belongs in configuration/data, not hardcoded source code.
Adding support for a new DME workflow should be a database operation,
not a code deployment.

The classifier dynamically builds its prompt from SQLite taxonomy data.
See ADR-005 for the taxonomy design decision.

WHY WE MOCK IN TESTS
---------------------
Tests never make real OpenAI API calls. Real calls cost money, require
a network connection, and make tests slow and fragile. The real API
is tested once manually by running the full pipeline on actual documents.
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from openai import OpenAI

from src.database import get_document_types

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL = "gpt-4o-mini"
CONFIDENCE_THRESHOLD = 0.80

# Module-level client — instantiated lazily on first classify() call, reused after.
# Tests patch this directly: patch("src.classifier.openai_client")
# None at import time so tests can import the module without OPENAI_API_KEY set.
openai_client: OpenAI | None = None


# ---------------------------------------------------------------------------
# Dynamic prompt generation
# ---------------------------------------------------------------------------

def _build_classification_prompt(
    equipment_type: str = "CPAP",
) -> tuple[str, list[str]]:
    """
    Build the classification prompt dynamically from the taxonomy database.

    Business taxonomy lives in SQLite rather than hardcoded source code.
    This allows adding new DME workflows and document types without
    changing classifier logic.

    Args:
        equipment_type: DME equipment category.

    Returns:
        Tuple of:
        - dynamically generated prompt
        - list of valid document type names
    """
    document_types = get_document_types(equipment_type)

    valid_document_types = [doc["name"] for doc in document_types]

    sections = []

    for index, doc in enumerate(document_types, start=1):
        sections.append(
            f"""
{index}. {doc['name']}
   - {doc['description']}
   - Key identifiers: {doc['key_identifiers']}
"""
        )

    taxonomy_section = "\n".join(sections)

    prompt = f"""
You are a document classifier for a DME (Durable Medical Equipment) provider.
Your job is to identify the type of each medical document in a patient file.

DOCUMENT TYPES
--------------
Classify the document as exactly one of these types:

{taxonomy_section}

UNKNOWN DOCUMENTS
-----------------
If the document does not clearly match any of the above types,
classify it as "Unknown". Do not guess.

OUTPUT FORMAT
-------------
Respond with valid JSON only. No extra text.

{{
  "document_type": "<valid type or Unknown>",
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<short explanation>"
}}
"""

    return prompt, valid_document_types


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ClassificationResult:
    """
    The output of the classification step for a single document.

    Every field is populated for every document — there are no optional
    fields. This makes downstream processing (storage, completeness check)
    predictable and easy to test.
    """
    filename: str
    document_type: str
    confidence: float
    patient_id: str
    reasoning: str
    requires_review: bool
    model: str
    processed_at: str
    pages_processed: int


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------

def classify(
    content,
    confidence_threshold: float = CONFIDENCE_THRESHOLD
) -> ClassificationResult:
    """
    Send a PDF to GPT-4o-mini and return a document classification.

    The PDF bytes are sent directly to the model. GPT-4o-mini handles
    both text-based and scanned/image PDFs natively.

    Args:
        content: ExtractedContent from extractor.py
        confidence_threshold: Minimum confidence threshold.

    Returns:
        ClassificationResult with type, confidence, reasoning, and metadata.
    """
    global openai_client

    if openai_client is None:
        openai_client = OpenAI()

    processed_at = datetime.now(timezone.utc).isoformat()
    patient_id = _parse_patient_id(content.filename)

    prompt, valid_document_types = _build_classification_prompt()

    try:
        response = openai_client.chat.completions.create(
            model=MODEL,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "text",
                            "text": f"Please classify this document. Filename: {content.filename}"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:application/pdf;base64,{_to_base64(content.file_bytes)}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=300
        )

        raw_content = response.choices[0].message.content
        classification = _parse_response(raw_content)

    except Exception as e:
        logger.error(f"Classification failed for {content.filename}: {e}")

        classification = {
            "document_type": "Unknown",
            "confidence": 0.0,
            "reasoning": f"Classification failed due to an error: {str(e)}"
        }

    document_type = classification.get("document_type", "Unknown")
    confidence = float(classification.get("confidence", 0.0))
    reasoning = classification.get("reasoning", "No reasoning provided.")

    # Validate returned taxonomy type
    if document_type not in valid_document_types + ["Unknown"]:
        logger.warning(
            f"Unexpected document type '{document_type}' "
            f"for {content.filename} — marking as Unknown"
        )
        document_type = "Unknown"

    requires_review = (
        confidence < confidence_threshold
        or document_type == "Unknown"
    )

    logger.info(
        f"Classified {content.filename} → {document_type} "
        f"(confidence={confidence:.2f}, review={requires_review})"
    )

    return ClassificationResult(
        filename=content.filename,
        document_type=document_type,
        confidence=confidence,
        patient_id=patient_id,
        reasoning=reasoning,
        requires_review=requires_review,
        model=MODEL,
        processed_at=processed_at,
        pages_processed=content.page_count
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _parse_patient_id(filename: str) -> str:
    """
    Extract the patient number from a filename.

    Examples:
        "Prescription 1.pdf" → "1"
        "Sleep Study Report 3.pdf" → "3"
        "unknown_doc.pdf" → "unknown"
    """
    match = re.search(r"(\\d+)", filename)
    return match.group(1) if match else "unknown"


def _to_base64(file_bytes: bytes) -> str:
    """Encode bytes to base64 string for the OpenAI API."""
    import base64
    return base64.b64encode(file_bytes).decode("utf-8")


def _parse_response(raw_content: str) -> dict:
    """
    Parse the JSON response from OpenAI safely.

    Returns Unknown if parsing fails.
    """
    try:
        cleaned = raw_content.strip()

        if cleaned.startswith("```"):
            cleaned = re.sub(r"```(?:json)?", "", cleaned).strip()

        parsed = json.loads(cleaned)

        if "document_type" not in parsed or "confidence" not in parsed:
            raise ValueError("Response missing required fields")

        return parsed

    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(
            f"Could not parse model response: {e}. "
            f"Raw: {raw_content[:200]}"
        )

        return {
            "document_type": "Unknown",
            "confidence": 0.0,
            "reasoning": "Could not parse model response — flagged for human review."
        }