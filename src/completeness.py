"""
completeness.py
================
Checks whether each patient file contains all required document types.

WHY THIS MODULE EXISTS
----------------------
Classification alone is not the business outcome.

The actual operational question is:

    "Can the workflow start for this patient?"

A DME coordinator does not care only that documents were classified.
They care whether the patient packet is complete enough to:
- submit insurance claims
- deliver equipment
- begin billing
- pass compliance audits

This module converts document-level classifications into patient-level
workflow readiness.

WHY REQUIREMENTS COME FROM THE DATABASE
---------------------------------------
Required document types are business configuration, not source code.

Different DME workflows require different document sets:
- CPAP
- oxygen therapy
- cardiac monitoring
- mobility equipment

The completeness checker reads required document types dynamically
from the taxonomy database rather than hardcoding rules.

This allows new workflows to be added without code changes.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.classifier import ClassificationResult
from src.database import get_required_document_names


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class PatientRecord:
    """
    Completeness result for a single patient.

    Attributes:
        patient_id: Patient identifier.
        documents_found: Document types found for the patient.
        documents_missing: Required document types still missing.
        is_complete: True if all required docs exist.
        can_start_workflow: Business-level workflow gate.
    """

    patient_id: str
    documents_found: list[str]
    documents_missing: list[str]
    is_complete: bool
    can_start_workflow: bool


# ---------------------------------------------------------------------------
# Grouping
# ---------------------------------------------------------------------------

def group_by_patient(
    classifications: list[ClassificationResult]
) -> dict[str, list[ClassificationResult]]:
    """
    Group classification results by patient ID.

    Args:
        classifications: List of classified documents.

    Returns:
        Dict keyed by patient_id.
    """
    grouped: dict[str, list[ClassificationResult]] = {}

    for classification in classifications:
        grouped.setdefault(
            classification.patient_id,
            []
        ).append(classification)

    return grouped


# ---------------------------------------------------------------------------
# Completeness checking
# ---------------------------------------------------------------------------

def check_completeness(
    classifications: list[ClassificationResult],
    equipment_type: str = "CPAP",
) -> list[PatientRecord]:
    """
    Determine whether each patient file is complete.

    Args:
        classifications: Classified documents.
        equipment_type: DME workflow category.

    Returns:
        List of PatientRecord results.
    """
    if not classifications:
        return []

    required_documents = set(
        get_required_document_names(equipment_type)
    )

    grouped = group_by_patient(classifications)

    results: list[PatientRecord] = []

    for patient_id, patient_docs in grouped.items():

        found_documents = set(
            doc.document_type
            for doc in patient_docs
            if doc.document_type != "Unknown"
        )

        missing_documents = sorted(
            required_documents - found_documents
        )

        is_complete = len(missing_documents) == 0

        results.append(
            PatientRecord(
                patient_id=patient_id,
                documents_found=sorted(found_documents),
                documents_missing=missing_documents,
                is_complete=is_complete,
                can_start_workflow=is_complete,
            )
        )

    return results