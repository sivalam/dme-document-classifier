# ADR-003: Output Format

**Status:** Accepted  
**Date:** 2026-05  
**Approvers:** Engineering Lead  
**Decision:** All three — JSON + CSV + SQLite, each serving a distinct purpose

---

## Context

The exercise asks us to "store the classification in some file." The format choice is left open. The problem statement hints at two requirements: ease of verification by humans, and ease of integration into software systems. These are different needs that point to different formats.

During design and implementation a third consumer emerged: a dashboard visualization layer for quickly reviewing workflow readiness and audit outputs without requiring SQL or raw JSON inspection.

We identified three distinct consumers with different needs:
- Software systems need machine-readable, schema-stable output
- Humans need something they can open and verify without writing code
- Operations and reviewers need a lightweight visual layer for spot-checking results

---

## Options Comparison

| | Option 1: CSV Only | Option 2: JSON Only | Option 3: Database Only | Option 4: JSON + CSV + SQLite ✅ |
|---|---|---|---|---|
| **Human readable** | ✅ Opens in Excel | ❌ Requires tooling | ❌ Requires SQL client | ✅ CSV handles this |
| **Machine readable** | ⚠️ Parseable but not structured | ✅ Native for APIs and services | ✅ Queryable | ✅ JSON handles this |
| **Schema and structure** | ❌ No types, no nesting | ✅ Nested structure, typed fields | ✅ Strong schema | ✅ SQLite and JSON support structured fields |
| **Audit trail** | ❌ Overwritten each run | ❌ Overwritten each run | ✅ Appends per run, full history | ✅ SQLite handles this |
| **Analytics over time** | ❌ Manual | ❌ Manual | ✅ SQL queries | ✅ SQLite handles this |
| **Pipeline integration** | ⚠️ Extra parsing needed | ✅ Direct consumption | ⚠️ Requires DB client | ✅ JSON handles this |
| **Portability** | ✅ Any tool | ✅ Any tool | ❌ File must travel with schema | ✅ JSON and CSV are portable |
| **Dashboard visualization** | ⚠️ Limited | ⚠️ Possible but complex | ⚠️ Requires query layer | ✅ JSON drives dashboard directly |
| **Complexity to produce** | Low | Low | Medium | Medium — but one pass writes all three |

---

## Decision

**Produce all three outputs — JSON, CSV, and SQLite.**

Each serves a different consumer:

- **JSON** — the primary output. Consumed by downstream software systems and workflow engines. Contains the full result including patient completeness status and exceptions. Also drives the dashboard visualization directly.
- **CSV** — for human verification. A coordinator or reviewer opens it in Excel to spot-check results. Intentionally flat and simple.
- **SQLite** — for persistence and auditability. Every run appends a new batch of records with a unique run_id — nothing is overwritten. Supports analytics queries over time.
- **Dashboard visualization** — lightweight operational review layer for quickly validating workflow readiness, review queues, and audit outputs without requiring SQL or raw JSON inspection.

All four are written or generated in a single pass — no duplication of logic.

---

## Schema Note

The corrections table is schema-defined in V1 and confirmed present in the database. No corrections have been recorded yet — this table is populated in V2 when a coordinator review UI is built. Every human correction is a future training example for prompt improvement.

```sql
CREATE TABLE corrections (
    id                INTEGER PRIMARY KEY,
    classification_id INTEGER REFERENCES classifications(id),
    original_type     TEXT,
    corrected_type    TEXT,
    corrected_by      TEXT,
    corrected_at      TEXT,
    notes             TEXT
);
```

---

## Trade-offs Accepted

| Trade-off | Mitigation |
|---|---|
| Three outputs adds some complexity | All written by one module in one pass |
| SQLite not suitable for concurrent writes | V1 is single-process batch. Migrate to Postgres when concurrent access needed |
| Schema changes require migration | Use run_id versioning. SQLite ALTER TABLE for additive changes |
| CSV has no schema enforcement | Acceptable — CSV is for human review, not system integration |

---

## When to Revisit

| Trigger | Action |
|---|---|
| Pipeline needs real-time event-driven routing | Add message queue output (SQS, Pub/Sub) alongside JSON |
| Multiple workers processing documents concurrently | Replace SQLite with Postgres |
| Need semantic search over document content | Add vector store output (Pinecone, pgvector) |
| Reporting needs exceed what SQLite queries can serve | Migrate to data warehouse (BigQuery, Redshift) |