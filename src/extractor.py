"""
extractor.py
============
Reads a PDF file and returns its raw bytes for classification.

WHY THIS MODULE EXISTS
----------------------
This module is a seam in the architecture, a deliberate separation between
"getting the file" and "classifying the file."

In production, documents arrive from many sources — fax, email, portal
uploads, manual drops. Regardless of how they arrive, the design is:

    All incoming documents are received and deposited into S3 first.
    A queue (SQS) notifies the pipeline when a new file lands,
    or the pipeline polls S3 for unprocessed files.
    This module reads from S3 in production.
    In V1 it reads from a local folder.

The classifier never needs to know where the file came from.
It just receives bytes and sends them to OpenAI.

This module also absorbs future extraction complexity. If we ever switch
to a model that does not accept PDFs directly, the text extraction or
image rendering logic goes here. See ADR-002 for the full options.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

logger = logging.getLogger(__name__)


@dataclass
class ExtractedContent:
    """
    The output of the extraction step.

    Contains everything the classifier needs to process a document:
    - filename: preserved for output records and logging
    - file_bytes: raw PDF bytes sent directly to OpenAI
    - page_count: logged with every classification for auditing
    """
    filename: str
    file_bytes: bytes
    page_count: int


def extract(filepath: str) -> ExtractedContent:
    """
    Read a PDF file from a local path and return its contents.

    V1 implementation — reads from local disk.
    In production this will be replaced by extract_from_s3().

    Args:
        filepath: Absolute or relative path to a PDF file.

    Returns:
        ExtractedContent with filename, raw bytes, and page count.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not a PDF or is empty.
    """
    path = Path(filepath)

    # Validate file exists
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    # Validate file extension
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"File is not a PDF: {filepath}")

    # Validate file is not empty
    file_bytes = path.read_bytes()
    if len(file_bytes) == 0:
        raise ValueError(f"File is empty: {filepath}")

    # Count pages for logging and auditability.
    # PdfReader is used only for page counting — not text extraction.
    # Text extraction is handled by the model (see ADR-002).
    try:
        reader = PdfReader(filepath)
        page_count = len(reader.pages)
    except Exception as e:
        # Page count is metadata — it should not block classification.
        logger.warning(f"Could not count pages for {path.name}: {e}")
        page_count = 0

    logger.info(f"Extracted {path.name} — {page_count} page(s)")

    return ExtractedContent(
        filename=path.name,
        file_bytes=file_bytes,
        page_count=page_count
    )


def extract_from_s3(bucket: str, key: str) -> ExtractedContent:
    """
    Read a PDF file from S3 and return its contents.

    Production implementation — all documents land in S3 first regardless
    of how they arrived (fax, email, portal upload, manual drop). The
    pipeline reads from S3 so the classifier never needs to know the
    original source.

    Triggered by:
    - SQS message when a new file lands in S3, or
    - Pipeline polling S3 for unprocessed files

    Args:
        bucket: S3 bucket name (e.g. "dme-documents-incoming")
        key: S3 object key (e.g. "patient-123/Prescription 1.pdf")

    Returns:
        ExtractedContent with filename, raw bytes, and page count.

    Raises:
        NotImplementedError: V1 reads from local disk only.
            Implement using boto3:
            s3 = boto3.client("s3")
            response = s3.get_object(Bucket=bucket, Key=key)
            file_bytes = response["Body"].read()
    """
    raise NotImplementedError(
        "S3 extraction is not implemented in V1. "
        "All documents are read from a local folder in this version. "
        "To implement: use boto3.client('s3').get_object() "
        "and pass the bytes to ExtractedContent. "
        "See docs/ARCHITECTURE.md for the production design."
    )