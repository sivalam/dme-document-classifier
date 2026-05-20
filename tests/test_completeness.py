"""
Tests for completeness.py

Tests cover:
- group_by_patient() groups documents correctly by patient ID
- group_by_patient() handles a single patient
- check_completeness() flags missing document types
- check_completeness() marks a complete patient correctly
- check_completeness() returns empty list for empty input
- check_completeness() excludes Unknown documents from found set
- check_completeness() sets can_start_workflow correctly
"""

from __future__ import annotations

import pytest
from unittest.mock import patch

from src.classifier import ClassificationResult
from src.completeness import PatientRecord, check_completeness, group_by_patient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_classification(
    filename: str = "Prescription 1.pdf",
    document_type: str = "Prescription",
    patient_id: str = "1",
) -> ClassificationResult:
    """Build a minimal ClassificationResult for testing."""
    return ClassificationResult(
        filename=filename,
        document_type=document_type,
        confidence=0.95,
        patient_id=patient_id,
        reasoning="Test classification.",
        requires_review=False,
        model="gpt-4o-mini",
        processed_at="2024-11-16T10:30:00Z",
        pages_processed=1,
    )


ALL_SIX_TYPES = [
    "Prescription",
    "Sleep Study Report",
    "Physician Notes",
    "Compliance Report",
    "Order",
    "Delivery Ticket",
]


def make_complete_patient(patient_id: str = "1") -> list[ClassificationResult]:
    """Build a full set of 6 classified documents for one patient."""
    return [
        make_classification(
            filename=f"{doc_type} {patient_id}.pdf",
            document_type=doc_type,
            patient_id=patient_id,
        )
        for doc_type in ALL_SIX_TYPES
    ]


def mock_required_documents():
    """Return the 6 required CPAP document type names."""
    return ALL_SIX_TYPES


# ---------------------------------------------------------------------------
# group_by_patient() tests
# ---------------------------------------------------------------------------

class TestGroupByPatient:
    """Tests for group_by_patient()."""

    def test_groups_correctly_by_patient_id(self) -> None:
        """Documents must be grouped by patient_id."""
        docs = [
            make_classification(patient_id="1"),
            make_classification(patient_id="2"),
            make_classification(patient_id="1"),
        ]

        grouped = group_by_patient(docs)

        assert set(grouped.keys()) == {"1", "2"}
        assert len(grouped["1"]) == 2
        assert len(grouped["2"]) == 1

    def test_handles_single_patient(self) -> None:
        """Single patient should produce one group."""
        docs = [
            make_classification(patient_id="1"),
            make_classification(patient_id="1"),
        ]

        grouped = group_by_patient(docs)

        assert list(grouped.keys()) == ["1"]
        assert len(grouped["1"]) == 2

    def test_returns_empty_dict_for_empty_input(self) -> None:
        """Empty input should return empty dict."""
        grouped = group_by_patient([])
        assert grouped == {}


# ---------------------------------------------------------------------------
# check_completeness() tests
# ---------------------------------------------------------------------------

class TestCheckCompleteness:
    """Tests for check_completeness()."""

    def test_complete_patient_has_no_missing_types(self) -> None:
        """A patient with all 6 documents should be marked complete."""
        docs = make_complete_patient("1")

        with patch("src.completeness.get_required_document_names") as mock_req:
            mock_req.return_value = mock_required_documents()
            records = check_completeness(docs)

        assert len(records) == 1
        record = records[0]
        assert record.is_complete is True
        assert record.documents_missing == []
        assert record.can_start_workflow is True

    def test_flags_missing_document_types(self) -> None:
        """A patient missing documents should have them listed."""
        docs = [
            make_classification(document_type="Prescription", patient_id="1"),
            make_classification(document_type="Sleep Study Report", patient_id="1"),
        ]

        with patch("src.completeness.get_required_document_names") as mock_req:
            mock_req.return_value = mock_required_documents()
            records = check_completeness(docs)

        record = records[0]
        assert record.is_complete is False
        assert "Physician Notes" in record.documents_missing
        assert "Compliance Report" in record.documents_missing
        assert "Order" in record.documents_missing
        assert "Delivery Ticket" in record.documents_missing

    def test_empty_input_returns_empty_list(self) -> None:
        """Empty classifications list should return empty records list."""
        with patch("src.completeness.get_required_document_names") as mock_req:
            mock_req.return_value = mock_required_documents()
            records = check_completeness([])

        assert records == []

    def test_unknown_documents_excluded_from_found_set(self) -> None:
        """Unknown document types must not count toward completeness."""
        docs = make_complete_patient("1")
        # Replace one real document with Unknown
        docs[0] = make_classification(
            filename="Prescription 1.pdf",
            document_type="Unknown",
            patient_id="1",
        )

        with patch("src.completeness.get_required_document_names") as mock_req:
            mock_req.return_value = mock_required_documents()
            records = check_completeness(docs)

        record = records[0]
        assert record.is_complete is False
        assert "Prescription" in record.documents_missing

    def test_multiple_patients_evaluated_independently(self) -> None:
        """Each patient must be evaluated against the required set independently."""
        patient1_docs = make_complete_patient("1")
        patient2_docs = [
            make_classification(document_type="Prescription", patient_id="2"),
        ]

        with patch("src.completeness.get_required_document_names") as mock_req:
            mock_req.return_value = mock_required_documents()
            records = check_completeness(patient1_docs + patient2_docs)

        by_patient = {r.patient_id: r for r in records}

        assert by_patient["1"].is_complete is True
        assert by_patient["2"].is_complete is False

    def test_can_start_workflow_matches_is_complete(self) -> None:
        """
        V1: can_start_workflow matches is_complete.

        This is a known V1 limitation — all missing documents are treated
        equally. In V2, can_start_workflow should be True for patients
        missing only downstream documents like Delivery Ticket.
        See docs/PRD.md section 10.
        """
        docs = make_complete_patient("1")
        # Remove only Delivery Ticket — patient should still be able to start
        docs = [d for d in docs if d.document_type != "Delivery Ticket"]

        with patch("src.completeness.get_required_document_names") as mock_req:
            mock_req.return_value = mock_required_documents()
            records = check_completeness(docs)

        record = records[0]
        # V1 behavior: incomplete = cannot start
        assert record.is_complete is False
        assert record.can_start_workflow is False
        # V2 improvement: this patient should be able to start
        # See docs/PRD.md section 10 for the roadmap