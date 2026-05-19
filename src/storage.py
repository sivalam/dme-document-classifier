"""Output storage module.

Serialises classification results and completeness reports to disk.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.classifier import ClassificationResult
from src.completeness import PatientRecord


def save_results(
    results: list[ClassificationResult],
    patient_records: list[PatientRecord],
    output_dir: Path,
) -> None:
    """Write classification results and completeness report to output_dir.

    Produces:
    - classifications.json  — per-document classification details
    - completeness.json     — per-patient completeness summary

    Args:
        results: All ClassificationResult objects.
        patient_records: All PatientRecord objects from completeness check.
        output_dir: Directory to write output files into.
    """
    raise NotImplementedError


def to_dict(obj: Any) -> dict:
    """Recursively convert a dataclass instance to a plain dictionary.

    Args:
        obj: Dataclass instance or primitive value.

    Returns:
        JSON-serialisable dictionary.
    """
    raise NotImplementedError
