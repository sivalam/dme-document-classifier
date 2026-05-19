"""Patient file completeness checker.

Groups classified documents by patient number (derived from filename
suffix) and flags which document types are missing per patient.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from src.classifier import ClassificationResult, DOCUMENT_TYPES


@dataclass
class PatientRecord:
    """All classified documents belonging to one patient."""
    patient_id: str
    documents: List[ClassificationResult]
    missing_types: List[str]


def group_by_patient(results: List[ClassificationResult]) -> dict[str, List[ClassificationResult]]:
    """Group classification results by patient identifier.

    Patient ID is the numeric suffix in the filename, e.g. "Patient 1".

    Args:
        results: List of classification results across all documents.

    Returns:
        Mapping of patient_id to their list of ClassificationResult objects.
    """
    raise NotImplementedError


def check_completeness(results: List[ClassificationResult]) -> List[PatientRecord]:
    """Check which document types are missing for each patient.

    Args:
        results: All classification results for the document set.

    Returns:
        List of PatientRecord objects, each with a missing_types field.
    """
    raise NotImplementedError
