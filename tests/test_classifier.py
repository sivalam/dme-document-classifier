"""
Tests for classifier.py

Tests cover:
- ClassificationResult dataclass has correct fields and types
- classify() returns a ClassificationResult
- classify() returns a valid document type from configured types
- classify() returns confidence between 0 and 1
- classify() sets requires_review=True when confidence is below threshold
- classify() sets requires_review=True for Unknown document type
- classify() sets requires_review=False when confidence is high
- classify() handles unexpected document types from model
- classify() handles malformed JSON response gracefully
- classify() preserves filename
- classify() extracts patient_id from filename
- classify() records the model version
- classify() records a timestamp
- classify() always deletes uploaded file after classification

NOTE: These tests mock the OpenAI Files API and Responses API —
no real API calls are made. Real API behavior is verified manually
by running the full pipeline against the actual documents.
"""

import json
import pytest
from unittest.mock import patch, MagicMock, call
from datetime import datetime


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def make_mock_response(document_type="Prescription", confidence=0.95):
    """
    Build a fake OpenAI Responses API response.
    Matches the actual response.output_text structure used in classifier.py.
    """
    mock_response = MagicMock()
    mock_response.output_text = json.dumps({
        "document_type": document_type,
        "confidence": confidence,
        "reasoning": f"Document appears to be a {document_type}."
    })
    return mock_response


def make_mock_uploaded_file(file_id="file-test-123"):
    """Build a fake OpenAI Files API upload response."""
    mock_file = MagicMock()
    mock_file.id = file_id
    return mock_file


def mock_document_types():
    """Return fake database-backed document type rows."""
    return [
        {"name": "Prescription", "description": "Prescription desc", "key_identifiers": "Rx, DEA number"},
        {"name": "Sleep Study Report", "description": "Sleep study desc", "key_identifiers": "AHI score"},
        {"name": "Physician Notes", "description": "Physician notes desc", "key_identifiers": "SOAP format"},
        {"name": "Compliance Report", "description": "Compliance desc", "key_identifiers": "usage hours"},
        {"name": "Order", "description": "Order desc", "key_identifiers": "HCPCS codes"},
        {"name": "Delivery Ticket", "description": "Delivery desc", "key_identifiers": "patient signature"},
    ]


def make_content(filename="Prescription 1.pdf", page_count=1):
    """Build a fake ExtractedContent object."""
    from src.extractor import ExtractedContent
    return ExtractedContent(
        filename=filename,
        file_bytes=b"%PDF fake bytes",
        page_count=page_count
    )


def run_classify(filename="Prescription 1.pdf", document_type="Prescription",
                 confidence=0.95, page_count=1):
    """
    Helper that runs classify() with all external dependencies mocked.
    Mocks: get_document_types, openai_client.files.create,
           openai_client.responses.create, openai_client.files.delete.
    """
    from src.classifier import classify

    content = make_content(filename=filename, page_count=page_count)

    with patch("src.classifier.get_document_types") as mock_types, \
         patch("src.classifier.openai_client") as mock_client:

        mock_types.return_value = mock_document_types()
        mock_client.files.create.return_value = make_mock_uploaded_file()
        mock_client.responses.create.return_value = make_mock_response(
            document_type=document_type,
            confidence=confidence
        )

        result = classify(content)

    return result, mock_client


# ---------------------------------------------------------------------------
# ClassificationResult dataclass tests
# ---------------------------------------------------------------------------

class TestClassificationResult:
    """Tests for the ClassificationResult dataclass."""

    def test_has_required_fields(self):
        """ClassificationResult must have all required fields."""
        from src.classifier import ClassificationResult

        result = ClassificationResult(
            filename="Prescription 1.pdf",
            document_type="Prescription",
            confidence=0.97,
            patient_id="1",
            reasoning="Looks like a prescription.",
            requires_review=False,
            model="gpt-4o-mini",
            processed_at="2024-11-16T10:30:00Z",
            pages_processed=1
        )

        assert result.filename == "Prescription 1.pdf"
        assert result.document_type == "Prescription"
        assert result.confidence == 0.97
        assert result.patient_id == "1"
        assert result.requires_review is False
        assert result.model == "gpt-4o-mini"
        assert result.pages_processed == 1

    def test_confidence_is_float(self):
        """confidence must be a float."""
        from src.classifier import ClassificationResult

        result = ClassificationResult(
            filename="test.pdf", document_type="Order", confidence=0.85,
            patient_id="1", reasoning="Order.", requires_review=False,
            model="gpt-4o-mini", processed_at="2024-11-16T10:30:00Z", pages_processed=1
        )
        assert isinstance(result.confidence, float)

    def test_requires_review_is_bool(self):
        """requires_review must be a boolean."""
        from src.classifier import ClassificationResult

        result = ClassificationResult(
            filename="test.pdf", document_type="Unknown", confidence=0.40,
            patient_id="1", reasoning="Unclear.", requires_review=True,
            model="gpt-4o-mini", processed_at="2024-11-16T10:30:00Z", pages_processed=1
        )
        assert isinstance(result.requires_review, bool)


# ---------------------------------------------------------------------------
# classify() function tests
# ---------------------------------------------------------------------------

class TestClassifyFunction:
    """Tests for the classify() function."""

    def test_returns_classification_result(self):
        """classify() must return a ClassificationResult instance."""
        from src.classifier import ClassificationResult

        result, _ = run_classify()
        assert isinstance(result, ClassificationResult)

    def test_returns_valid_document_type(self):
        """classify() must return a document type from the configured types."""
        result, _ = run_classify(document_type="Order")

        valid_types = [doc["name"] for doc in mock_document_types()] + ["Unknown"]
        assert result.document_type in valid_types

    def test_confidence_between_zero_and_one(self):
        """classify() must return a confidence score between 0 and 1."""
        result, _ = run_classify(confidence=0.88)
        assert 0.0 <= result.confidence <= 1.0

    def test_requires_review_true_when_low_confidence(self):
        """classify() must set requires_review=True when confidence is below threshold."""
        result, _ = run_classify(confidence=0.55)
        assert result.requires_review is True

    def test_requires_review_false_when_high_confidence(self):
        """classify() must set requires_review=False when confidence is above threshold."""
        result, _ = run_classify(document_type="Delivery Ticket", confidence=0.96)
        assert result.requires_review is False

    def test_requires_review_true_for_unknown_type(self):
        """classify() must set requires_review=True when document type is Unknown."""
        result, _ = run_classify(document_type="Unknown", confidence=0.90)
        assert result.requires_review is True

    def test_unexpected_type_becomes_unknown(self):
        """Document types outside the known list must be converted to Unknown."""
        result, _ = run_classify(document_type="Totally Unexpected Type", confidence=0.99)
        assert result.document_type == "Unknown"
        assert result.requires_review is True

    def test_preserves_filename(self):
        """classify() must preserve the original filename in the result."""
        result, _ = run_classify(filename="Sleep Study Report 2.pdf")
        assert result.filename == "Sleep Study Report 2.pdf"

    def test_extracts_patient_id_from_filename(self):
        """classify() must parse the patient ID from the filename."""
        result, _ = run_classify(filename="Prescription 3.pdf")
        assert result.patient_id == "3"

    def test_records_model_version(self):
        """classify() must record the exact model version used."""
        result, _ = run_classify()
        assert result.model == "gpt-4o-mini"

    def test_records_timestamp(self):
        """classify() must record a valid ISO 8601 processed_at timestamp."""
        result, _ = run_classify()
        assert result.processed_at is not None
        datetime.fromisoformat(result.processed_at)

    def test_uses_files_api_to_upload(self):
        """classify() must upload the PDF via the Files API."""
        _, mock_client = run_classify(filename="Order 1.pdf")
        mock_client.files.create.assert_called_once()

        call_kwargs = mock_client.files.create.call_args
        assert call_kwargs.kwargs["purpose"] == "user_data"

    def test_uses_responses_api_to_classify(self):
        """classify() must call the Responses API with the uploaded file_id."""
        _, mock_client = run_classify()
        mock_client.responses.create.assert_called_once()

        call_args = mock_client.responses.create.call_args
        input_content = call_args.kwargs["input"][0]["content"]
        file_input = next(c for c in input_content if c["type"] == "input_file")
        assert file_input["file_id"] == "file-test-123"

    def test_deletes_uploaded_file_after_classification(self):
        """classify() must delete the uploaded file after classification."""
        _, mock_client = run_classify()
        mock_client.files.delete.assert_called_once_with("file-test-123")

    def test_deletes_uploaded_file_even_on_classification_failure(self):
        """classify() must delete the uploaded file even if classification fails."""
        from src.classifier import classify
        from src.extractor import ExtractedContent

        content = ExtractedContent(
            filename="test.pdf",
            file_bytes=b"%PDF fake bytes",
            page_count=1
        )

        with patch("src.classifier.get_document_types") as mock_types, \
             patch("src.classifier.openai_client") as mock_client:

            mock_types.return_value = mock_document_types()
            mock_client.files.create.return_value = make_mock_uploaded_file("file-cleanup-test")
            # Simulate responses.create failing
            mock_client.responses.create.side_effect = Exception("API error")

            result = classify(content)

        # File must be deleted even though classification failed
        mock_client.files.delete.assert_called_once_with("file-cleanup-test")
        # Result should degrade gracefully
        assert result.document_type == "Unknown"
        assert result.requires_review is True

    def test_handles_malformed_json_response(self):
        """classify() must handle malformed JSON from OpenAI gracefully."""
        from src.classifier import classify
        from src.extractor import ExtractedContent

        content = ExtractedContent(
            filename="test.pdf",
            file_bytes=b"%PDF fake bytes",
            page_count=1
        )

        mock_response = MagicMock()
        mock_response.output_text = "I cannot process this document."

        with patch("src.classifier.get_document_types") as mock_types, \
             patch("src.classifier.openai_client") as mock_client:

            mock_types.return_value = mock_document_types()
            mock_client.files.create.return_value = make_mock_uploaded_file()
            mock_client.responses.create.return_value = mock_response

            result = classify(content)

        assert result.document_type == "Unknown"
        assert result.requires_review is True

    def test_patient_id_unknown_when_no_number_in_filename(self):
        """classify() must return 'unknown' patient_id when filename has no number."""
        result, _ = run_classify(filename="mystery_document.pdf")
        assert result.patient_id == "unknown"