# ADR-003: Output Format Selection

**Status:** Accepted

## Context

Results must be easy to verify by a human reviewer and easy to ingest by downstream software systems.

## Decision

Emit two JSON files:
- `classifications.json` — array of per-document classification objects.
- `completeness.json` — array of per-patient completeness objects including `missing_types`.

JSON was chosen over CSV (poor nested structure), SQLite (adds a runtime dependency for a read-only artefact), and plain text (not machine-readable).

## Consequences

**Positive**
- Human-readable with any text editor.
- Directly consumable by REST APIs, pandas, and most ETL tools.
- Schema can be versioned alongside the code.

**Negative**
- Not ideal for very large document sets (thousands of files) where a database would be more efficient.
