"""
Tests for database.py

Tests cover:
- Database initializes without errors
- All required tables are created
- CPAP equipment type is seeded on first run
- All 6 CPAP document types are seeded
- Seeding is idempotent — running twice does not duplicate data
- get_document_types() returns correct document types
- get_document_types() returns only active types
- get_required_document_names() returns all 6 required types
- Unknown equipment type returns empty list
"""

import pytest
import sqlite3
import tempfile
import os


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database file for each test."""
    db_path = str(tmp_path / "test.db")
    return db_path


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class TestDatabaseInitialization:
    """Tests for initialize_database()."""

    def test_creates_equipment_types_table(self, temp_db):
        """initialize_database() must create the equipment_types table."""
        from src.database import initialize_database, get_connection

        initialize_database(temp_db)

        conn = get_connection(temp_db)
        result = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='equipment_types'"
        ).fetchone()
        conn.close()

        assert result is not None

    def test_creates_document_types_table(self, temp_db):
        """initialize_database() must create the document_types table."""
        from src.database import initialize_database, get_connection

        initialize_database(temp_db)

        conn = get_connection(temp_db)
        result = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='document_types'"
        ).fetchone()
        conn.close()

        assert result is not None

    def test_creates_classifications_table(self, temp_db):
        """initialize_database() must create the classifications table."""
        from src.database import initialize_database, get_connection

        initialize_database(temp_db)

        conn = get_connection(temp_db)
        result = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='classifications'"
        ).fetchone()
        conn.close()

        assert result is not None

    def test_creates_patient_completeness_table(self, temp_db):
        """initialize_database() must create the patient_completeness table."""
        from src.database import initialize_database, get_connection

        initialize_database(temp_db)

        conn = get_connection(temp_db)
        result = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='patient_completeness'"
        ).fetchone()
        conn.close()

        assert result is not None

    def test_creates_corrections_table(self, temp_db):
        """initialize_database() must create the corrections table."""
        from src.database import initialize_database, get_connection

        initialize_database(temp_db)

        conn = get_connection(temp_db)
        result = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='corrections'"
        ).fetchone()
        conn.close()

        assert result is not None

    def test_idempotent_safe_to_call_twice(self, temp_db):
        """initialize_database() must be safe to call multiple times."""
        from src.database import initialize_database

        initialize_database(temp_db)
        initialize_database(temp_db)  # Should not raise or duplicate data


# ---------------------------------------------------------------------------
# Seed data tests
# ---------------------------------------------------------------------------

class TestSeedData:
    """Tests for taxonomy seed data."""

    def test_cpap_equipment_type_is_seeded(self, temp_db):
        """CPAP equipment type must be seeded on initialization."""
        from src.database import initialize_database, get_connection

        initialize_database(temp_db)

        conn = get_connection(temp_db)
        result = conn.execute(
            "SELECT name FROM equipment_types WHERE name = 'CPAP'"
        ).fetchone()
        conn.close()

        assert result is not None

    def test_six_document_types_are_seeded(self, temp_db):
        """All 6 CPAP document types must be seeded."""
        from src.database import initialize_database, get_connection

        initialize_database(temp_db)

        conn = get_connection(temp_db)
        count = conn.execute(
            """
            SELECT COUNT(*) FROM document_types dt
            JOIN equipment_types et ON dt.equipment_type_id = et.id
            WHERE et.name = 'CPAP'
            """
        ).fetchone()[0]
        conn.close()

        assert count == 6

    def test_all_required_document_types_present(self, temp_db):
        """All 6 document types must be marked as required."""
        from src.database import initialize_database, get_connection

        initialize_database(temp_db)

        conn = get_connection(temp_db)
        count = conn.execute(
            """
            SELECT COUNT(*) FROM document_types dt
            JOIN equipment_types et ON dt.equipment_type_id = et.id
            WHERE et.name = 'CPAP' AND dt.required_for_complete = 1
            """
        ).fetchone()[0]
        conn.close()

        assert count == 6

    def test_seeding_is_idempotent(self, temp_db):
        """Running initialize_database() twice must not duplicate seed data."""
        from src.database import initialize_database, get_connection

        initialize_database(temp_db)
        initialize_database(temp_db)

        conn = get_connection(temp_db)
        count = conn.execute(
            "SELECT COUNT(*) FROM equipment_types WHERE name = 'CPAP'"
        ).fetchone()[0]
        conn.close()

        assert count == 1

    def test_document_types_have_key_identifiers(self, temp_db):
        """Every document type must have key_identifiers for the LLM prompt."""
        from src.database import initialize_database, get_connection

        initialize_database(temp_db)

        conn = get_connection(temp_db)
        empty = conn.execute(
            """
            SELECT COUNT(*) FROM document_types
            WHERE key_identifiers IS NULL OR key_identifiers = ''
            """
        ).fetchone()[0]
        conn.close()

        assert empty == 0


# ---------------------------------------------------------------------------
# Query tests
# ---------------------------------------------------------------------------

class TestGetDocumentTypes:
    """Tests for get_document_types()."""

    def test_returns_six_cpap_types(self, temp_db):
        """get_document_types() must return all 6 CPAP document types."""
        from src.database import initialize_database, get_document_types

        initialize_database(temp_db)
        types = get_document_types("CPAP", temp_db)

        assert len(types) == 6

    def test_returns_dicts_with_required_fields(self, temp_db):
        """Each document type must have name, description, key_identifiers."""
        from src.database import initialize_database, get_document_types

        initialize_database(temp_db)
        types = get_document_types("CPAP", temp_db)

        for doc_type in types:
            assert "name" in doc_type
            assert "description" in doc_type
            assert "key_identifiers" in doc_type

    def test_returns_empty_for_unknown_equipment_type(self, temp_db):
        """get_document_types() must return empty list for unknown equipment."""
        from src.database import initialize_database, get_document_types

        initialize_database(temp_db)
        types = get_document_types("Heart Rate Monitor", temp_db)

        assert types == []


class TestGetRequiredDocumentNames:
    """Tests for get_required_document_names()."""

    def test_returns_six_required_names(self, temp_db):
        """get_required_document_names() must return all 6 required types."""
        from src.database import initialize_database, get_required_document_names

        initialize_database(temp_db)
        names = get_required_document_names("CPAP", temp_db)

        assert len(names) == 6

    def test_returns_strings(self, temp_db):
        """get_required_document_names() must return a list of strings."""
        from src.database import initialize_database, get_required_document_names

        initialize_database(temp_db)
        names = get_required_document_names("CPAP", temp_db)

        for name in names:
            assert isinstance(name, str)

    def test_includes_prescription(self, temp_db):
        """Prescription must be in required documents."""
        from src.database import initialize_database, get_required_document_names

        initialize_database(temp_db)
        names = get_required_document_names("CPAP", temp_db)

        assert "Prescription" in names

    def test_includes_all_expected_types(self, temp_db):
        """All 6 expected document types must be present."""
        from src.database import initialize_database, get_required_document_names

        initialize_database(temp_db)
        names = get_required_document_names("CPAP", temp_db)

        expected = [
            "Prescription",
            "Sleep Study Report",
            "Physician Notes",
            "Compliance Report",
            "Order",
            "Delivery Ticket"
        ]
        for expected_name in expected:
            assert expected_name in names, f"Missing required document type: {expected_name}"