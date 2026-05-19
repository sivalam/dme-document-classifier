"""
database.py
===========
Manages the SQLite database for the DME document classifier.

TWO PURPOSES
------------
1. Taxonomy storage — document types and equipment categories live here,
   not hardcoded in the classifier prompt. This means adding a new document
   type or equipment category is a database operation, not a code change.

2. Classification results — every classification decision is persisted here
   with full audit trail. See storage.py for the write logic.

WHY SQLITE
----------
SQLite is the right choice for V1:
- Zero infrastructure — one file, no server
- Sufficient for single-process batch workloads
- Easy to inspect with any SQLite viewer
- Migrate to Postgres when concurrent writes or multi-service access needed
See ADR-003 for the full output format decision.

WHY TAXONOMY IN THE DATABASE
-----------------------------
Business rules (what document types exist, what is required for a complete
patient file) belong in data, not hardcoded in source code. A coordinator
or admin should be able to add support for a new DME equipment type by
inserting rows, not by modifying and redeploying code.

The current seed data covers CPAP/sleep apnea workflows. Adding cardiac
monitoring, oxygen therapy, or mobility equipment means inserting a new
equipment_type and its associated document_types. Nothing else changes.
See ADR-005 for the full taxonomy design decision.

SCHEMA DESIGN NOTES
-------------------
- equipment_types: top-level DME categories (CPAP, cardiac, oxygen, etc.)
- document_types: document categories per equipment type, with metadata
  used to build the LLM classification prompt dynamically
- classifications: one row per classified document, per pipeline run
- patient_completeness: one row per patient per run, completeness status
- corrections: human overrides — schema defined now, populated in V2
  when a coordinator UI is built. Every correction is a training example.
- Soft deletes (active flag) — nothing is ever hard deleted. Deactivated
  types are excluded from classification but preserved for audit history.
"""

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

# Default database path — can be overridden in tests
DEFAULT_DB_PATH = Path("output") / "dme_classifier.db"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA = """
-- Equipment categories
-- Each DME type (CPAP, cardiac, oxygen) has its own document taxonomy
CREATE TABLE IF NOT EXISTS equipment_types (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT,
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Document types per equipment category
-- These rows are injected into the LLM classification prompt at runtime
CREATE TABLE IF NOT EXISTS document_types (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_type_id   INTEGER NOT NULL REFERENCES equipment_types(id),
    name                TEXT NOT NULL,
    description         TEXT NOT NULL,
    key_identifiers     TEXT NOT NULL,  -- comma-separated hints for the LLM
    required_for_complete INTEGER NOT NULL DEFAULT 1,  -- part of complete patient file?
    active              INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(equipment_type_id, name)
);

-- Classification results
-- One row per document per pipeline run
CREATE TABLE IF NOT EXISTS classifications (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id              TEXT NOT NULL,
    filename            TEXT NOT NULL,
    document_type       TEXT NOT NULL,
    confidence          REAL NOT NULL,
    patient_id          TEXT NOT NULL,
    reasoning           TEXT,
    requires_review     INTEGER NOT NULL DEFAULT 0,
    model               TEXT NOT NULL,
    processed_at        TEXT NOT NULL,
    pages_processed     INTEGER NOT NULL DEFAULT 0
);

-- Patient file completeness
-- One row per patient per pipeline run
CREATE TABLE IF NOT EXISTS patient_completeness (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id              TEXT NOT NULL,
    patient_id          TEXT NOT NULL,
    status              TEXT NOT NULL,  -- complete | incomplete | cannot_start
    documents_found     TEXT NOT NULL,  -- JSON array
    documents_missing   TEXT NOT NULL,  -- JSON array
    can_start_workflow  INTEGER NOT NULL DEFAULT 0
);

-- Human corrections
-- Schema defined in V1, populated in V2 when coordinator UI is built.
-- Every correction is a future training example for prompt improvement.
CREATE TABLE IF NOT EXISTS corrections (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    classification_id   INTEGER NOT NULL REFERENCES classifications(id),
    original_type       TEXT NOT NULL,
    corrected_type      TEXT NOT NULL,
    corrected_by        TEXT,
    corrected_at        TEXT NOT NULL DEFAULT (datetime('now')),
    notes               TEXT
);
"""

# ---------------------------------------------------------------------------
# Seed data — CPAP/sleep apnea taxonomy
# ---------------------------------------------------------------------------

SEED_DATA = {
    "equipment_type": {
        "name": "CPAP",
        "description": "Continuous Positive Airway Pressure equipment for sleep apnea treatment"
    },
    "document_types": [
        {
            "name": "Prescription",
            "description": "Written by a physician authorizing DME for a patient. May be handwritten on an Rx pad or typed.",
            "key_identifiers": "Rx symbol, DEA number, physician signature, device or medication ordered",
            "required_for_complete": 1
        },
        {
            "name": "Sleep Study Report",
            "description": "Results of a polysomnography or home sleep test. Used to establish medical necessity for CPAP.",
            "key_identifiers": "AHI score, Apnea-Hypopnea Index, sleep stages, oxygen saturation, diagnostic findings",
            "required_for_complete": 1
        },
        {
            "name": "Physician Notes",
            "description": "Clinical documentation of a patient encounter, often in SOAP format.",
            "key_identifiers": "diagnosis, treatment plan, medical history, clinical narrative, SOAP format",
            "required_for_complete": 1
        },
        {
            "name": "Compliance Report",
            "description": "CPAP device usage data showing patient compliance. Required by insurance for continued coverage.",
            "key_identifiers": "usage hours per day, compliance percentage, reporting date range, device data",
            "required_for_complete": 1
        },
        {
            "name": "Order",
            "description": "Standard Written Order for DME equipment with specific equipment codes.",
            "key_identifiers": "HCPCS codes, equipment list, quantities, physician signature, standard written order",
            "required_for_complete": 1
        },
        {
            "name": "Delivery Ticket",
            "description": "Proof that equipment was delivered to the patient. Triggers the billing process.",
            "key_identifiers": "delivery date, patient signature, equipment serial numbers, delivery receipt",
            "required_for_complete": 1
        }
    ]
}


# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------

def get_connection(db_path: str = None) -> sqlite3.Connection:
    """
    Get a SQLite database connection.

    Uses row_factory=sqlite3.Row so results can be accessed by column name
    rather than index — makes code more readable and less brittle.

    Args:
        db_path: Path to the SQLite file. Defaults to output/dme_classifier.db.

    Returns:
        sqlite3.Connection with row_factory set.
    """
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------------------------------------------------------------------
# Schema management
# ---------------------------------------------------------------------------

def initialize_database(db_path: str = None) -> None:
    """
    Create all tables and seed the taxonomy if not already present.

    Safe to call multiple times — uses CREATE TABLE IF NOT EXISTS and
    checks for existing seed data before inserting.

    Args:
        db_path: Path to the SQLite file. Defaults to output/dme_classifier.db.
    """
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
        logger.info("Database schema initialized")

        _seed_if_empty(conn)
    finally:
        conn.close()


def _seed_if_empty(conn: sqlite3.Connection) -> None:
    """
    Seed the taxonomy tables if they are empty.

    Only inserts data on first run — subsequent runs are no-ops.
    This means seed data can be safely modified in the source and
    will take effect when the database is reset.
    """
    existing = conn.execute(
        "SELECT COUNT(*) FROM equipment_types WHERE name = ?",
        (SEED_DATA["equipment_type"]["name"],)
    ).fetchone()[0]

    if existing > 0:
        logger.debug("Taxonomy already seeded — skipping")
        return

    # Insert equipment type
    cursor = conn.execute(
        "INSERT INTO equipment_types (name, description) VALUES (?, ?)",
        (
            SEED_DATA["equipment_type"]["name"],
            SEED_DATA["equipment_type"]["description"]
        )
    )
    equipment_type_id = cursor.lastrowid

    # Insert document types
    for doc_type in SEED_DATA["document_types"]:
        conn.execute(
            """
            INSERT INTO document_types
                (equipment_type_id, name, description, key_identifiers, required_for_complete)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                equipment_type_id,
                doc_type["name"],
                doc_type["description"],
                doc_type["key_identifiers"],
                doc_type["required_for_complete"]
            )
        )

    conn.commit()
    logger.info(
        f"Seeded taxonomy: {SEED_DATA['equipment_type']['name']} "
        f"with {len(SEED_DATA['document_types'])} document types"
    )


# ---------------------------------------------------------------------------
# Taxonomy queries
# ---------------------------------------------------------------------------

def get_document_types(equipment_type_name: str = "CPAP", db_path: str = None) -> list:
    """
    Get all active document types for an equipment category.

    Used by the classifier to build the LLM prompt dynamically.
    Returns only active types — deactivated types are excluded.

    Args:
        equipment_type_name: Equipment category name. Default "CPAP".
        db_path: Path to the SQLite file.

    Returns:
        List of dicts with name, description, key_identifiers, required_for_complete.
    """
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT dt.name, dt.description, dt.key_identifiers, dt.required_for_complete
            FROM document_types dt
            JOIN equipment_types et ON dt.equipment_type_id = et.id
            WHERE et.name = ?
              AND dt.active = 1
              AND et.active = 1
            ORDER BY dt.id
            """,
            (equipment_type_name,)
        ).fetchall()

        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_required_document_names(equipment_type_name: str = "CPAP", db_path: str = None) -> list:
    """
    Get the names of required documents for a complete patient file.

    Used by completeness.py to check which documents are missing.

    Args:
        equipment_type_name: Equipment category name. Default "CPAP".
        db_path: Path to the SQLite file.

    Returns:
        List of document type name strings that are required.
    """
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """
            SELECT dt.name
            FROM document_types dt
            JOIN equipment_types et ON dt.equipment_type_id = et.id
            WHERE et.name = ?
              AND dt.required_for_complete = 1
              AND dt.active = 1
              AND et.active = 1
            ORDER BY dt.id
            """,
            (equipment_type_name,)
        ).fetchall()

        return [row["name"] for row in rows]
    finally:
        conn.close()