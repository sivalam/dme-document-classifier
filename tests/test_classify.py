"""Tests for classify.py orchestration."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.classifier import ClassificationResult
from src.completeness import PatientRecord
from src.extractor import ExtractedContent


def make_classification() -> ClassificationResult:
    """Create a test classification."""
    return ClassificationResult(
        filename="Prescription 1.pdf",
        document_type="Prescription",
        confidence=0.95,
        patient_id="1",
        reasoning="Looks like a prescription.",
        requires_review=False,
        model="gpt-4o-mini",
        processed_at="2024-11-16T10:30:00+00:00",
        pages_processed=1,
    )


def make_patient_record() -> PatientRecord:
    """Create a test completeness result."""
    return PatientRecord(
        patient_id="1",
        documents_found=["Prescription"],
        documents_missing=[],
        is_complete=True,
        can_start_workflow=True,
    )


class TestFindPdfFiles:
    """Tests for PDF discovery."""

    def test_finds_pdf_files(self, tmp_path) -> None:
        """Should return sorted PDF files only."""
        from src.classify import find_pdf_files

        (tmp_path / "b.pdf").write_bytes(b"fake")
        (tmp_path / "a.pdf").write_bytes(b"fake")
        (tmp_path / "notes.txt").write_text("ignore")

        files = find_pdf_files(str(tmp_path))

        assert [file.name for file in files] == ["a.pdf", "b.pdf"]

    def test_missing_directory_raises(self) -> None:
        """Missing directory should raise."""
        from src.classify import find_pdf_files

        with pytest.raises(FileNotFoundError):
            find_pdf_files("missing-directory")


class TestRunPipeline:
    """Tests for end-to-end orchestration."""

    def test_run_pipeline_calls_modules(self, tmp_path) -> None:
        """Pipeline should orchestrate extract/classify/store flow."""
        from src.classify import run_pipeline

        input_dir = tmp_path / "documents"
        input_dir.mkdir()

        (input_dir / "Prescription 1.pdf").write_bytes(b"%PDF fake")

        with patch("src.classify.initialize_database"):
            with patch("src.classify.extract") as mock_extract:
                with patch("src.classify.classify") as mock_classify:
                    with patch("src.classify.check_completeness") as mock_completeness:
                        with patch("src.classify.write_all") as mock_write_all:

                            mock_extract.return_value = ExtractedContent(
                                filename="Prescription 1.pdf",
                                file_bytes=b"%PDF fake",
                                page_count=1,
                            )

                            mock_classify.return_value = make_classification()
                            mock_completeness.return_value = [make_patient_record()]
                            mock_write_all.return_value = "test-run"

                            run_id = run_pipeline(
                                input_dir=str(input_dir),
                                output_dir=str(tmp_path / "output"),
                            )

        assert run_id == "test-run"

        mock_extract.assert_called_once()
        mock_classify.assert_called_once()
        mock_completeness.assert_called_once()
        mock_write_all.assert_called_once()

    def test_pipeline_continues_on_failure(self, tmp_path) -> None:
        """One bad file should not stop the batch."""
        from src.classify import run_pipeline

        input_dir = tmp_path / "documents"
        input_dir.mkdir()

        (input_dir / "bad.pdf").write_bytes(b"%PDF fake")

        with patch("src.classify.initialize_database"):
            with patch("src.classify.extract") as mock_extract:
                with patch("src.classify.check_completeness") as mock_completeness:
                    with patch("src.classify.write_all") as mock_write_all:

                        mock_extract.side_effect = ValueError("bad pdf")
                        mock_completeness.return_value = []
                        mock_write_all.return_value = "test-run"

                        run_id = run_pipeline(
                            input_dir=str(input_dir),
                            output_dir=str(tmp_path / "output"),
                        )

        assert run_id == "test-run"