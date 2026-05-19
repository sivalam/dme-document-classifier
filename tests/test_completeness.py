"""Tests for the patient completeness checker."""
from __future__ import annotations

import pytest

from src.completeness import check_completeness, group_by_patient, PatientRecord
from src.classifier import ClassificationResult


class TestGroupByPatient:
    def test_groups_correctly_by_suffix(self) -> None:
        pytest.skip("not implemented yet")

    def test_handles_single_patient(self) -> None:
        pytest.skip("not implemented yet")


class TestCheckCompleteness:
    def test_flags_missing_document_types(self) -> None:
        pytest.skip("not implemented yet")

    def test_complete_patient_has_no_missing_types(self) -> None:
        pytest.skip("not implemented yet")

    def test_empty_input_returns_empty_list(self) -> None:
        pytest.skip("not implemented yet")
