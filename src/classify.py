"""
classify.py
===========
Entry point for the DME document classifier.

Runs the V1 batch pipeline:

    extract → classify → completeness → store
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.classifier import ClassificationResult, classify
from src.completeness import PatientRecord, check_completeness
from src.database import initialize_database
from src.extractor import extract
from src.storage import write_all

logger = logging.getLogger(__name__)


def find_pdf_files(input_dir: str) -> list[Path]:
    """Return sorted PDF files from the input directory."""
    path = Path(input_dir)

    if not path.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    if not path.is_dir():
        raise ValueError(f"Input path is not a directory: {input_dir}")

    return sorted(path.glob("*.pdf"))


def run_pipeline(
    input_dir: str = "documents",
    output_dir: str = "output",
    confidence_threshold: float = 0.80,
    db_path: str | None = None,
) -> str:
    """Run the end-to-end batch classification pipeline."""
    initialize_database(db_path)

    classifications: list[ClassificationResult] = []
    failures: list[tuple[str, str]] = []

    for pdf_file in find_pdf_files(input_dir):
        try:
            content = extract(str(pdf_file))
            result = classify(content, confidence_threshold=confidence_threshold)
            classifications.append(result)
        except Exception as exc:
            logger.exception("Failed to process %s", pdf_file)
            failures.append((str(pdf_file), str(exc)))

    patient_records = check_completeness(classifications)

    run_id = write_all(
        classifications=classifications,
        patient_records=patient_records,
        output_dir=output_dir,
        db_path=db_path,
    )

    print_summary(run_id, classifications, patient_records, failures)
    return run_id


def print_summary(
    run_id: str,
    classifications: list[ClassificationResult],
    patient_records: list[PatientRecord],
    failures: list[tuple[str, str]],
) -> None:
    """Print a concise run summary for demo and operator feedback."""
    review_count = sum(item.requires_review for item in classifications)
    complete_count = sum(record.is_complete for record in patient_records)

    print()
    print("DME document classification complete")
    print("------------------------------------")
    print(f"Run ID: {run_id}")
    print(f"Documents classified: {len(classifications)}")
    print(f"Documents requiring review: {review_count}")
    print(f"Patients evaluated: {len(patient_records)}")
    print(f"Complete patient files: {complete_count}")
    print(f"Failures: {len(failures)}")

    if failures:
        print()
        print("Failures:")
        for filename, error in failures:
            print(f"- {filename}: {error}")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Classify DME medical PDF documents.",
    )

    parser.add_argument(
        "--input",
        default="documents",
        help="Directory containing PDF files.",
    )
    parser.add_argument(
        "--output",
        default="output",
        help="Directory for JSON and CSV outputs.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.80,
        help="Confidence threshold for human review.",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Optional SQLite database path.",
    )

    return parser


def main() -> None:
    """Run from command line."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    args = build_parser().parse_args()

    run_pipeline(
        input_dir=args.input,
        output_dir=args.output,
        confidence_threshold=args.threshold,
        db_path=args.db,
    )


if __name__ == "__main__":
    main()