"""
storage.py
==========
Persists pipeline results.

Writes:
- JSON for downstream systems
- CSV for human verification
- SQLite for audit/history
"""

from __future__ import annotations

import csv
import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from src.classifier import ClassificationResult
from src.completeness import PatientRecord
from src.database import get_connection, initialize_database


def write_all(
    classifications: list[ClassificationResult],
    patient_records: list[PatientRecord],
    output_dir: str = "output",
    db_path: str | None = None,
) -> str:
    """Write JSON, CSV, and SQLite outputs for a pipeline run."""
    run_id = _new_run_id()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    write_json(classifications, patient_records, output_path / "classifications.json", run_id)
    write_csv(classifications, output_path / "classifications.csv")
    write_sqlite(classifications, patient_records, run_id, db_path)

    return run_id


def write_json(
    classifications: list[ClassificationResult],
    patient_records: list[PatientRecord],
    output_path: str | Path,
    run_id: str,
) -> None:
    """Write integration-ready JSON output."""
    payload = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_documents": len(classifications),
        "documents": [asdict(item) for item in classifications],
        "patients": {
            record.patient_id: asdict(record)
            for record in patient_records
        },
        "exceptions": [
            asdict(item)
            for item in classifications
            if item.requires_review
        ],
    }

    Path(output_path).write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


def write_csv(
    classifications: list[ClassificationResult],
    output_path: str | Path,
) -> None:
    """Write flat CSV output for coordinator review."""
    fieldnames = [
        "filename",
        "patient_id",
        "document_type",
        "confidence",
        "requires_review",
        "reasoning",
        "model",
        "processed_at",
        "pages_processed",
    ]

    with Path(output_path).open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for item in classifications:
            writer.writerow(asdict(item))


def write_sqlite(
    classifications: list[ClassificationResult],
    patient_records: list[PatientRecord],
    run_id: str,
    db_path: str | None = None,
) -> None:
    """Append classification and completeness results to SQLite."""
    initialize_database(db_path)

    conn = get_connection(db_path)
    try:
        for item in classifications:
            conn.execute(
                """
                INSERT INTO classifications
                    (
                        run_id,
                        filename,
                        document_type,
                        confidence,
                        patient_id,
                        reasoning,
                        requires_review,
                        model,
                        processed_at,
                        pages_processed
                    )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    item.filename,
                    item.document_type,
                    item.confidence,
                    item.patient_id,
                    item.reasoning,
                    int(item.requires_review),
                    item.model,
                    item.processed_at,
                    item.pages_processed,
                ),
            )

        for record in patient_records:
            conn.execute(
                """
                INSERT INTO patient_completeness
                    (
                        run_id,
                        patient_id,
                        status,
                        documents_found,
                        documents_missing,
                        can_start_workflow
                    )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    record.patient_id,
                    _status_for(record),
                    json.dumps(record.documents_found),
                    json.dumps(record.documents_missing),
                    int(record.can_start_workflow),
                ),
            )

        conn.commit()
    finally:
        conn.close()


def _status_for(record: PatientRecord) -> str:
    """Return persisted workflow status for a patient record."""
    if record.is_complete:
        return "complete"

    if not record.can_start_workflow:
        return "cannot_start"

    return "incomplete"


def _new_run_id() -> str:
    """Create a unique run id."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = uuid.uuid4().hex[:8]
    return f"{timestamp}-{suffix}"