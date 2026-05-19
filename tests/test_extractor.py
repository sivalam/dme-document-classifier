"""
Tests for extractor.py

Tests cover:
- ExtractedContent dataclass has correct fields and types
- extract() happy path: valid PDF returns ExtractedContent
- extract() preserves filename
- extract() returns non-empty bytes
- extract() correctly detects page count
- extract() raises FileNotFoundError for missing files
- extract() raises ValueError for non-PDF files
- extract() raises ValueError for empty files
- extract_from_s3() raises NotImplementedError in V1
"""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# These tests will FAIL until extractor.py is implemented — that is correct.
# Run with: python -m pytest tests/test_extractor.py -v
# ---------------------------------------------------------------------------


class TestExtractedContent:
    """Tests for the ExtractedContent dataclass."""

    def test_has_required_fields(self):
        """ExtractedContent must have filename, file_bytes, and page_count."""
        from src.extractor import ExtractedContent
        content = ExtractedContent(
            filename="test.pdf",
            file_bytes=b"fake-pdf-bytes",
            page_count=1
        )
        assert content.filename == "test.pdf"
        assert content.file_bytes == b"fake-pdf-bytes"
        assert content.page_count == 1

    def test_filename_is_string(self):
        """filename must be a string."""
        from src.extractor import ExtractedContent
        content = ExtractedContent(
            filename="Prescription 1.pdf",
            file_bytes=b"bytes",
            page_count=1
        )
        assert isinstance(content.filename, str)

    def test_file_bytes_is_bytes(self):
        """file_bytes must be bytes type."""
        from src.extractor import ExtractedContent
        content = ExtractedContent(
            filename="test.pdf",
            file_bytes=b"some bytes",
            page_count=2
        )
        assert isinstance(content.file_bytes, bytes)

    def test_page_count_is_int(self):
        """page_count must be an integer."""
        from src.extractor import ExtractedContent
        content = ExtractedContent(
            filename="test.pdf",
            file_bytes=b"bytes",
            page_count=3
        )
        assert isinstance(content.page_count, int)


class TestExtractFromPath:
    """Tests for the extract() function — local file reading."""

    def test_returns_extracted_content(self, tmp_path):
        """extract() must return an ExtractedContent instance."""
        from src.extractor import extract, ExtractedContent

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake content")

        with patch("src.extractor.PdfReader") as mock_reader:
            mock_reader.return_value.pages = [MagicMock(), MagicMock()]
            result = extract(str(pdf_file))

        assert isinstance(result, ExtractedContent)

    def test_preserves_filename(self, tmp_path):
        """extract() must preserve the original filename."""
        from src.extractor import extract

        pdf_file = tmp_path / "Prescription 1.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake content")

        with patch("src.extractor.PdfReader") as mock_reader:
            mock_reader.return_value.pages = [MagicMock()]
            result = extract(str(pdf_file))

        assert result.filename == "Prescription 1.pdf"

    def test_returns_non_empty_bytes(self, tmp_path):
        """extract() must return non-empty bytes for a valid file."""
        from src.extractor import extract

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 some content here")

        with patch("src.extractor.PdfReader") as mock_reader:
            mock_reader.return_value.pages = [MagicMock()]
            result = extract(str(pdf_file))

        assert len(result.file_bytes) > 0

    def test_detects_page_count(self, tmp_path):
        """extract() must correctly report the number of pages."""
        from src.extractor import extract

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake content")

        with patch("src.extractor.PdfReader") as mock_reader:
            mock_reader.return_value.pages = [MagicMock(), MagicMock(), MagicMock()]
            result = extract(str(pdf_file))

        assert result.page_count == 3

    def test_raises_on_missing_file(self):
        """extract() must raise FileNotFoundError if file does not exist."""
        from src.extractor import extract

        with pytest.raises(FileNotFoundError):
            extract("/nonexistent/path/fake.pdf")

    def test_raises_on_non_pdf(self, tmp_path):
        """extract() must raise ValueError if the file is not a PDF."""
        from src.extractor import extract

        text_file = tmp_path / "not_a_pdf.txt"
        text_file.write_text("this is not a pdf")

        with pytest.raises(ValueError, match="not a PDF"):
            extract(str(text_file))

    def test_raises_on_empty_file(self, tmp_path):
        """extract() must raise ValueError if the file is empty."""
        from src.extractor import extract

        empty_file = tmp_path / "empty.pdf"
        empty_file.write_bytes(b"")

        with pytest.raises(ValueError, match="empty"):
            extract(str(empty_file))


class TestExtractFromS3:
    """
    Tests for extract_from_s3() — production S3 implementation.

    In V1 this raises NotImplementedError by design.
    These tests document the expected interface for when it is implemented.
    """

    def test_raises_not_implemented_in_v1(self):
        """extract_from_s3() must raise NotImplementedError in V1."""
        from src.extractor import extract_from_s3

        with pytest.raises(NotImplementedError):
            extract_from_s3(
                bucket="dme-documents-incoming",
                key="patient-1/Prescription 1.pdf"
            )

    def test_not_implemented_message_is_helpful(self):
        """NotImplementedError message must explain how to implement."""
        from src.extractor import extract_from_s3

        with pytest.raises(NotImplementedError, match="boto3"):
            extract_from_s3(
                bucket="dme-documents-incoming",
                key="patient-1/Prescription 1.pdf"
            )