"""
classifier.py
=============
Sends a PDF to OpenAI GPT-4o-mini and returns a document classification.

The classifier uses OpenAI's Files API + Responses API flow:
1. Upload the PDF as user data via the Files API.
2. Reference the uploaded file_id in a Responses API call.
3. Parse the model's structured JSON response.
4. Delete the uploaded file after classification to avoid accumulation.

The model returns:
- document_type: one of the configured document types or "Unknown"
- confidence: 0.0 to 1.0
- reasoning: short explanation of the classification decision

WHY FILES API + RESPONSES API
------------------------------
Sending PDFs via chat.completions image_url fails with an invalid MIME
type error. The Files API + Responses API is the correct flow for PDF
ingestion. This was validated during end-to-end testing. See ADR-002.

WHY TEMPERATURE IS NOT SET ON RESPONSES API
--------------------------------------------
The Responses API does not support a temperature parameter directly.
Determinism is achieved through explicit prompt instructions and
structured JSON output requirements.

WHY DOCUMENT TYPES COME FROM THE DATABASE
------------------------------------------
Document types are stored in SQLite, not hardcoded. The classifier
queries them at runtime and builds the prompt dynamically. Adding
support for a new DME equipment type is a database insert — no code
change required. See ADR-005.
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from openai import OpenAI

from src.database import get_document_types

logger = logging.getLogger(__name__)

MODEL = "gpt-4o-mini"
CONFIDENCE_THRESHOLD = 0.80

# Module-level client — lazily initialized on first classify() call.
# Tests patch this directly: patch("src.classifier.openai_client")
openai_client: OpenAI | None = None


def _build_classification_prompt(
    equipment_type: str = "CPAP",
) -> tuple[str, list[str]]:
    """
    Build the classification prompt from database-backed document types.

    Args:
        equipment_type: Equipment category to query. Default "CPAP".

    Returns:
        Tuple of (prompt string, list of valid document type names).
    """
    document_types = get_document_types(equipment_type)
    valid_document_types = [doc["name"] for doc in document_types]

    sections = []
    for index, doc in enumerate(document_types, start=1):
        sections.append(
            f"{index}. {doc['name']}\n"
            f"   - {doc['description']}\n"
            f"   - Key identifiers: {doc['key_identifiers']}\n"
        )

    taxonomy_section = "\n".join(sections)

    prompt = f"""You are a document classifier for a DME (Durable Medical Equipment) provider.
Your job is to identify the type of each medical document in a patient file.

DOCUMENT TYPES
--------------
Classify the document as exactly one of these types:

{taxonomy_section}

UNKNOWN DOCUMENTS
-----------------
If the document does not clearly match any of the above types,
classify it as "Unknown". Do not guess. Unknown documents are
routed to human review.

OUTPUT FORMAT
-------------
Respond with valid JSON only. No extra text before or after the JSON.

{{
  "document_type": "<valid type or Unknown>",
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<one or two sentences explaining your classification>"
}}"""

    return prompt, valid_document_types


@dataclass
class ClassificationResult:
    """
    The output of the classification step for a single document.

    Every field is populated for every document — no optional fields.
    This makes downstream processing predictable and easy to test.
    """

    filename: str
    document_type: str       # One of the configured types or "Unknown"
    confidence: float        # 0.0 to 1.0
    patient_id: str          # Parsed from filename — "Prescription 3.pdf" → "3"
    reasoning: str           # Model explanation — useful for debugging and auditing
    requires_review: bool    # True if confidence < threshold OR type is Unknown
    model: str               # Exact model version — never changes silently
    processed_at: str        # ISO 8601 timestamp
    pages_processed: int


def classify(
    content,
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
) -> ClassificationResult:
    """
    Upload a PDF to OpenAI and return a document classification.

    Uses the Files API + Responses API flow. Uploads the PDF,
    classifies it, then deletes the uploaded file. Classification failures 
    degrade gracefully to Unknown with requires_review=True.

    Args:
        content: ExtractedContent from extractor.py
                 (filename, raw PDF bytes, page count).
        confidence_threshold: Minimum confidence to auto-route.
                              Default 0.80.

    Returns:
        ClassificationResult — always returns, never raises.
    """
    global openai_client

    if openai_client is None:
        openai_client = OpenAI()

    processed_at = datetime.now(timezone.utc).isoformat()
    patient_id = _parse_patient_id(content.filename)
    prompt, valid_document_types = _build_classification_prompt()

    uploaded_file_id = None

    try:
        # Step 1 — Upload the PDF via Files API
        uploaded_file = openai_client.files.create(
            file=(content.filename, content.file_bytes, "application/pdf"),
            purpose="user_data",
        )
        uploaded_file_id = uploaded_file.id

        # Step 2 — Classify via Responses API
        response = openai_client.responses.create(
            model=MODEL,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_file",
                            "file_id": uploaded_file_id,
                        },
                        {
                            "type": "input_text",
                            "text": f"{prompt}\n\nFilename: {content.filename}",
                        },
                    ],
                }
            ],
        )

        classification = _parse_response(response.output_text)

    except Exception as e:
        # Never crash the pipeline on a single document failure.
        # Log the error, mark for human review, and keep going.
        logger.error(f"Classification failed for {content.filename}: {e}")
        classification = {
            "document_type": "Unknown",
            "confidence": 0.0,
            "reasoning": f"Classification failed due to an error: {str(e)}",
        }

    finally:
        # Step 3 — Always clean up the uploaded file.
        # Files accumulate in the OpenAI account if not deleted.
        if uploaded_file_id is not None:
            try:
                openai_client.files.delete(uploaded_file_id)
            except Exception as cleanup_error:
                logger.warning(
                    f"Could not delete uploaded file {uploaded_file_id}: {cleanup_error}"
                )

    document_type = classification.get("document_type", "Unknown")
    confidence = float(classification.get("confidence", 0.0))
    reasoning = classification.get("reasoning", "No reasoning provided.")

    # If the model returns something outside the known document types,
    # treat it as Unknown rather than passing an unexpected value downstream.
    if document_type not in valid_document_types + ["Unknown"]:
        logger.warning(
            f"Unexpected document type '{document_type}' "
            f"for {content.filename} — marking as Unknown"
        )
        document_type = "Unknown"

    # requires_review is True when:
    # 1. Confidence is below threshold — model is uncertain
    # 2. Document type is Unknown — didn't match any known category
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
        pages_processed=content.page_count,
    )


def _parse_patient_id(filename: str) -> str:
    """
    Extract patient number from filename.

    "Prescription 1.pdf" → "1"
    "Sleep Study Report 3.pdf" → "3"
    "unknown_doc.pdf" → "unknown"

    NOTE: In production, patient ID comes from a database or document
    metadata — not the filename. This works for this exercise because
    documents are named consistently.
    """
    match = re.search(r"(\d+)", filename)
    return match.group(1) if match else "unknown"


def _parse_response(raw_content: str) -> dict:
    """
    Parse JSON response from OpenAI.

    Handles two failure modes gracefully:
    1. Response is not valid JSON
    2. Response is missing required fields

    Returns a safe Unknown default rather than raising.
    """
    try:
        cleaned = raw_content.strip()
        # Strip markdown code fences if model wrapped the JSON
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
            "reasoning": "Could not parse model response — flagged for human review.",
        }