# ADR-005: Taxonomy Design — Database vs Hardcoded

**Status:** Accepted  
**Date:** 2026-05  
**Approvers:** Engineering Lead  
**Decision:** Option 2 — Database-driven taxonomy with SQLite

---

## Context

The classifier needs a list of document types to classify against. This taxonomy defines the business rules of the system — what documents exist, what identifies each one, and which are required for a complete patient file.

The initial dataset covers CPAP/sleep apnea workflows. In production, DME providers handle many equipment types — wheelchairs, oxygen concentrators, cardiac monitors, hospital beds. Each has its own document variants.

We need to decide where this taxonomy lives.

---

## Options Comparison

| | Option 1: Hardcoded in Prompt | Option 2: Database-Driven ✅ |
|---|---|---|
| **Where taxonomy lives** | String constant in `classifier.py` | `document_types` table in SQLite |
| **Adding a new document type** | Code change + redeploy | INSERT into database, no redeploy |
| **Adding a new equipment category** | Code change + redeploy | INSERT equipment_type + document_types |
| **Multi-DME provider support** | Not supported without code changes | Supported — query by equipment_type |
| **Non-engineer can extend** | ❌ Requires code change | ✅ DB insert or admin UI |
| **V1 implementation complexity** | Low | Low-Medium — SQLite is simple |
| **Prompt building** | Static string | Dynamic — built from DB rows at runtime |
| **Testability** | Simple | Simple — use temp DB in tests |
| **Audit trail** | None | Full — created_at, active flag, soft delete |
| **Showing database design skills** | ❌ | ✅ |

---

## Decision

**Option 2 — Database-driven taxonomy.**

Business rules belong in data, not code. A coordinator or admin should be able to add support for a new DME equipment type by inserting rows, not by modifying and redeploying the application.

The implementation cost is low — SQLite requires no infrastructure and the schema is simple. The benefit is a system that can grow without code changes.

---

## Schema Design

```sql
equipment_types          -- CPAP, Cardiac, Oxygen, Mobility, etc.
    id, name, description, active, created_at

document_types           -- Prescription, Order, Sleep Study, etc.
    id, equipment_type_id (FK), name, description,
    key_identifiers,     -- injected into LLM prompt
    required_for_complete,  -- used by completeness check
    active, created_at
```

**Key design decisions:**
- `key_identifiers` is a text field injected directly into the LLM prompt — the DB drives the prompt content, not the code
- `required_for_complete` drives the completeness check in `completeness.py` — no hardcoded list
- Soft deletes (`active` flag) — deactivated types are excluded from classification but preserved for audit history
- Foreign key from `document_types` to `equipment_types` enforces referential integrity

---

## Trade-offs Accepted

| Trade-off | Mitigation |
|---|---|
| More code than hardcoded string | SQLite is simple — no server, no migrations tool needed for V1 |
| DB must be initialized before classification runs | `initialize_database()` called at pipeline startup — safe to call multiple times |
| Seed data lives in code (not a migration file) | Acceptable for V1 — move to proper migrations (Alembic) when moving to Postgres |
| Tests need temp DB fixture | Simple `tmp_path` fixture in pytest — clean per test |

---

## When to Revisit

| Trigger | Action |
|---|---|
| Multiple services need to read taxonomy | Move to Postgres, expose via API |
| Non-engineers need to manage taxonomy | Build admin UI that writes to document_types table |
| Complex migration needs arise | Add Alembic for proper migration management |
| Taxonomy needs versioning | Add version column to equipment_types |