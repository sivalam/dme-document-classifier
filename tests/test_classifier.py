"""Tests for the document classification module."""
from __future__ import annotations

import pytest

from src.classifier import classify, build_prompt, ClassificationResult, DOCUMENT_TYPES
from src.extractor import ExtractionResult


class TestBuildPrompt:
    def test_placeholder(self) -> None:
        pytest.skip("not implemented yet")

    def test_includes_all_document_types(self) -> None:
        pytest.skip("not implemented yet")


class TestClassify:
    def test_returns_classification_result(self) -> None:
        pytest.skip("not implemented yet")

    def test_all_six_document_types_recognised(self) -> None:
        pytest.skip("not implemented yet")

    def test_low_confidence_handled(self) -> None:
        pytest.skip("not implemented yet")
