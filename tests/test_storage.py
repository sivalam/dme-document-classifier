"""Tests for storage.py."""

from __future__ import annotations

import csv
import json
import sqlite3

from src.classifier import ClassificationResult
from src.completeness import PatientRecord
from src.storage import write_all, write_csv, write_json, write_sqlite


def make_classification(
    filename: str = "Prescription 1.pdf",
    document_type: str = "Prescription",
    patient_id: str = "1",
    requires_review: bool = False,
) -> ClassificationResult:
    """Create a test classification result."""
    return ClassificationResult(
        filename=filename,
        document_type=document_type,
        confidence=0.95,
        patient_id=patient_id,
        reasoning="Looks like a prescription.",
        requires_review=requires_review,
        model="gpt-4o-mini",
        processed_at="2024-11-16T10:30:00+00:00",
        pages_processed=1,
    )


def make_patient_record(
    patient_id: str = "1",
    is_complete: bool = True,
    can_start_workflow: bool = True,
) -> PatientRecord:
    """Create a test patient completeness record."""
    return PatientRecord(
        patient_id=patient_id,
        documents_found=["Prescription"],
        documents_missing=[] if is_complete else ["Order"],
        is_complete=is_complete,
        can_start_workflow=can_start_workflow,
    )


class TestWriteJson:
    """Tests for JSON output."""

    def test_writes_json_file(self, tmp_path) -> None:
        """write_json should create a structured JSON file."""
        output_path = tmp_path / "classifications.json"

        write_json(
            classifications=[make_classification()],
            patient_records=[make_patient_record()],
            output_path=output_path,
            run_id="test-run",
        )

        assert output_path.exists()

        data = json.loads(output_path.read_text(encoding="utf-8"))

        assert data["run_id"] == "test-run"
        assert data["total_documents"] == 1
        assert data["documents"][0]["filename"] == "Prescription 1.pdf"
        assert data["patients"]["1"]["is_complete"] is True

    def test_includes_review_exceptions(self, tmp_path) -> None:
        """JSON output should include documents requiring review."""
        output_path = tmp_path / "classifications.json"

        write_json(
            classifications=[
                make_classification(
                    document_type="Unknown",
                    requires_review=True,
                )
            ],
            patient_records=[],
            output_path=output_path,
            run_id="test-run",
        )

        data = json.loads(output_path.read_text(encoding="utf-8"))

        assert len(data["exceptions"]) == 1
        assert data["exceptions"][0]["document_type"] == "Unknown"


class TestWriteCsv:
    """Tests for CSV output."""

    def test_writes_csv_file(self, tmp_path) -> None:
        """write_csv should create a flat CSV file."""
        output_path = tmp_path / "classifications.csv"

        write_csv(
            classifications=[make_classification()],
            output_path=output_path,
        )

        assert output_path.exists()

        with output_path.open("r", encoding="utf-8") as file:
            rows = list(csv.DictReader(file))

        assert len(rows) == 1
        assert rows[0]["filename"] == "Prescription 1.pdf"
        assert rows[0]["document_type"] == "Prescription"
        assert rows[0]["patient_id"] == "1"


class TestWriteSqlite:
    """Tests for SQLite persistence."""

    def test_writes_classification_rows(self, tmp_path) -> None:
        """write_sqlite should persist classification results."""
        db_path = str(tmp_path / "test.db")

        write_sqlite(
            classifications=[make_classification()],
            patient_records=[],
            run_id="test-run",
            db_path=db_path,
        )

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT filename, document_type FROM classifications"
        ).fetchone()
        conn.close()

        assert row == ("Prescription 1.pdf", "Prescription")

    def test_writes_patient_completeness_rows(self, tmp_path) -> None:
        """write_sqlite should persist patient completeness results."""
        db_path = str(tmp_path / "test.db")

        write_sqlite(
            classifications=[],
            patient_records=[
                make_patient_record(
                    patient_id="1",
                    is_complete=False,
                    can_start_workflow=False,
                )
            ],
            run_id="test-run",
            db_path=db_path,
        )

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            """
            SELECT patient_id, status, can_start_workflow
            FROM patient_completeness
            """
        ).fetchone()
        conn.close()

        assert row == ("1", "cannot_start", 0)


class TestWriteAll:
    """Tests for writing all outputs."""

    def test_writes_all_outputs(self, tmp_path) -> None:
        """write_all should write JSON, CSV, and SQLite outputs."""
        output_dir = tmp_path / "output"
        db_path = str(tmp_path / "test.db")

        run_id = write_all(
            classifications=[make_classification()],
            patient_records=[make_patient_record()],
            output_dir=str(output_dir),
            db_path=db_path,
        )

        assert run_id is not None
        assert (output_dir / "classifications.json").exists()
        assert (output_dir / "classifications.csv").exists()

        conn = sqlite3.connect(db_path)
        count = conn.execute(
            "SELECT COUNT(*) FROM classifications"
        ).fetchone()[0]
        conn.close()

        assert count == 1