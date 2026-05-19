"""Tests for the PDF extraction module."""
from __future__ import annotations

import pytest
from pathlib import Path

from src.extractor import extract, extract_text_pdfplumber, extract_text_vision, ExtractionResult


class TestExtractTextPdfplumber:
    def test_placeholder(self) -> None:
        pytest.skip("not implemented yet")


class TestExtractTextVision:
    def test_placeholder(self) -> None:
        pytest.skip("not implemented yet")


class TestExtract:
    def test_routes_to_pdfplumber_for_digital_pdf(self) -> None:
        pytest.skip("not implemented yet")

    def test_routes_to_vision_when_text_below_threshold(self) -> None:
        pytest.skip("not implemented yet")

    def test_threshold_boundary(self) -> None:
        pytest.skip("not implemented yet")
