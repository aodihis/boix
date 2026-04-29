# CLAUDE.md — ONIX Book Import System

> All agents must read this file before writing any code.

---

## Project Overview

This system ingests ONIX XML book metadata (versions 2.1 and 3.x) into a lean 5-table PostgreSQL schema, then selectively pushes new and updated records to FileMaker Data API and Craft CMS. A separate read-only Flask viewer app provides a browser interface for browsing the database for testing and presentation.

The project splits into two completely independent Python apps sharing only a PostgreSQL database:
1. **`core/`** — main lambda/serverless app: detect → parse XML → upsert to DB → enqueue push → drain push queue
2. **`viewer/`** — read-only Flask+HTMX UI for browsing the database (no writes, ever)

---

## Python Rules

- Python 3.11+ required.
- Type hints on **every** function signature — both parameters and return type.
- PEP8. Format with `black` (line length 100). Run before committing.
- Comments explain WHY only — never WHAT. Remove noise comments.
- Functions ≤ ~40 lines. Single responsibility.
- Use `dataclasses` (not plain dicts) for structured data passed between modules.
- `parser/models.py` field names must exactly match `db/schema.sql` column names — they are a load-bearing contract.
- Use `lxml.etree.iterparse` for all XML parsing — handles large publisher feeds without loading the full tree into memory.
- All configuration via `.env` files. Never hardcode credentials or connection strings.
- No JavaScript frameworks in viewer. HTMX + Bootstrap 5 from CDN only.

---

## Dependency Policy

Two separate `requirements.txt` files. Use **only** the libraries listed here. Do not add any library without first updating this file.

### core/requirements.txt
```
lxml>=4.9
psycopg2-binary>=2.9
requests>=2.31
python-dotenv>=1.0
apscheduler>=3.10
pytest>=8.0
pytest-cov>=5.0
```

### viewer/requirements.txt
```
flask>=3.0
psycopg2-binary>=2.9
python-dotenv>=1.0
```

---

## Configuration

### core app environment variables (core/.env.example)

| Variable | Description |
|----------|-------------|
| `DB_HOST` | PostgreSQL host |
| `DB_PORT` | PostgreSQL port (default 5432) |
| `DB_NAME` | Database name |
| `DB_USER` | Database user |
| `DB_PASSWORD` | Database password |
| `FILEMAKER_BASE_URL` | FileMaker Data API base URL |
| `FILEMAKER_DB` | FileMaker database name |
| `FILEMAKER_LAYOUT` | FileMaker layout name |
| `FILEMAKER_USER` | FileMaker username |
| `FILEMAKER_PASSWORD` | FileMaker password |
| `CRAFTCMS_BASE_URL` | Craft CMS base URL |
| `CRAFTCMS_TOKEN` | Craft CMS API token |
| `USE_STUBS` | `true` routes pushers to localhost stub servers (dev/test) |
| `FM_STUB_PORT` | Port for FileMaker stub server (default 5001) |
| `CRAFT_STUB_PORT` | Port for Craft CMS stub server (default 5002) |
| `PUSH_INTERVAL_SECONDS` | How often the scheduler drains the push queue (default 300) |
| `PUSH_TARGETS` | Comma-separated list of active push targets: `filemaker,craftcms` |

### viewer app environment variables (viewer/.env.example)

| Variable | Description |
|----------|-------------|
| `DB_HOST` | PostgreSQL host |
| `DB_PORT` | PostgreSQL port (default 5432) |
| `DB_NAME` | Database name |
| `DB_USER` | Database user |
| `DB_PASSWORD` | Database password |
| `FLASK_PORT` | Port for the viewer Flask app (default 5000) |

---

## Module Responsibilities

Each file has exactly one responsibility. No overlap. No cross-imports between `core/` and `viewer/`.

| File | Responsibility |
|------|----------------|
| `core/parser/models.py` | Dataclasses only: `Book`, `Contributor`, `Subject`, `Price`, `Feed`. No I/O. |
| `core/parser/detect.py` | `detect_onix_version(path: str) -> str` — returns `'2.1'`, `'3.0'`, or `'3.1'`. Reads first 512 bytes only. |
| `core/parser/codelists.py` | `code_to_label(code_type: str, code: str) -> str` — pure lookup table, no I/O. |
| `core/parser/onix_parser.py` | `parse_onix3(path: str) -> tuple[Feed, list[Book]]` — ONIX 3.x only. |
| `core/parser/onix2_parser.py` | `parse_onix2(path: str) -> tuple[Feed, list[Book]]` — ONIX 2.1 only. Same output shape as `parse_onix3`. |
| `core/db/connection.py` | `get_connection() -> psycopg2.connection` — reads `DB_*` env vars. |
| `core/db/importer.py` | `upsert_feed`, `upsert_book`, `block_update`, `enqueue_push`. All DB writes. No reads from XML. |
| `core/pushers/filemaker.py` | `push_book_to_filemaker(book_id: int, conn, config: dict) -> dict` — reads book from DB, pushes to FM. |
| `core/pushers/craftcms.py` | `push_book_to_craft(book_id: int, conn, config: dict) -> dict` — reads book from DB, pushes to Craft. |
| `core/stubs/filemaker_stub.py` | Flask stub server mimicking FileMaker Data API endpoints. Dev/test only. |
| `core/stubs/craftcms_stub.py` | Flask stub server mimicking Craft CMS API endpoint. Dev/test only. |
| `core/stubs/run_stubs.py` | Starts both stub servers as daemon threads on `FM_STUB_PORT` and `CRAFT_STUB_PORT`. |
| `core/run_import.py` | CLI entry point: detect → parse → upsert → enqueue_push. |
| `core/scheduler.py` | APScheduler `BlockingScheduler` job: drain `push_queue` → FM/Craft on `PUSH_INTERVAL_SECONDS`. |
| `viewer/api/server.py` | Flask app factory: `create_app() -> Flask`. |
| `viewer/api/routes.py` | `GET /books`, `/books/<id>`, `/books/search` (full pages) and `GET /api/books`, `/api/books/search` (JSON/HTMX partial). |
| `viewer/api/queries.py` | `list_books()`, `get_book_detail()`, `get_book_contributors()`, `get_book_subjects()`, `get_book_prices()`, `count_books()`. Read-only SQL, no writes. |

---

## Smart Push Logic

### Enqueue rules (called from `core/db/importer.py` after each upsert)

| `notification_type_code` | Action |
|--------------------------|--------|
| `01`, `02`, `03` (new / notification / advance) | Enqueue only if no row exists in `push_queue` with `status IN ('pending', 'sent')` for this `book_id` + `target` |
| `04` (block update) | Always enqueue — something changed, downstream systems must be updated |
| `05` (deleted) | Skip push entirely; optionally mark book as deleted in `books` table |

### Push queue drain (called by `core/scheduler.py`)

1. `SELECT book_id FROM push_queue WHERE status='pending' AND target=? LIMIT 50`
2. For each: fetch book from DB, push to FileMaker or Craft
3. On success: `UPDATE push_queue SET status='sent', sent_at=NOW()`
4. On failure: `UPDATE push_queue SET status='failed', attempts=attempts+1, error_message=?`
5. Retry: up to 3 attempts total; after 3, leave as `'failed'` for manual inspection

### Deduplication

Before enqueuing, check:
```sql
SELECT 1 FROM push_queue WHERE book_id=? AND target=? AND status IN ('pending','sent')
```
If a row exists, skip enqueue. A `'failed'` status does **not** block re-enqueue — this is intentional, so a previously failed push attempt can be retried by a new upsert event.

---

## FileMaker Data API Contract

### Real API

Auth: `Authorization: Bearer {token}` header on all requests after login.

### Stub endpoints (port `FM_STUB_PORT`, default 5001)

| Method | Path | Response |
|--------|------|----------|
| `POST` | `/fmrest/vLatest/databases/{db}/sessions` | `{"response": {"token": "stub-token"}, "messages": [{"code": "0"}]}` |
| `POST` | `/fmrest/vLatest/databases/{db}/layouts/{layout}/records` | `{"response": {"recordId": "1", "modId": "0"}, "messages": [{"code": "0"}]}` |
| `DELETE` | `/fmrest/vLatest/databases/{db}/sessions/{token}` | `{"response": {}, "messages": [{"code": "0"}]}` |

---

## Craft CMS API Contract

### Real API

Auth: `X-Craft-Token: {CRAFTCMS_TOKEN}` header on all requests.

### Stub endpoint (port `CRAFT_STUB_PORT`, default 5002)

| Method | Path | Response |
|--------|------|----------|
| `POST` | `/actions/elements/save` | `{"success": true, "id": 1}` |

---

## Testing Approach

- `pytest` for all tests.
- Run: `cd core && pytest tests/ -v --cov=. --cov-report=term-missing`
- **Unit tests**: parser functions, codelists, version detect — no DB or network needed.
- **Integration tests**: require real PostgreSQL — point `DB_*` env vars at a Docker container. These tests apply the full schema and verify round-trip upsert/select behavior.
- **Fixture XML files**: hand-crafted minimal ONIX in `core/tests/fixtures/`. Not real publisher data.
  - `onix3_sample.xml` — 2 books: one full, one minimal
  - `onix3_block_update.xml` — `notification_type=04`, `ProductSupply` block only
  - `onix21_sample.xml` — 1 book in ONIX 2.1 element names
- **Stub servers**: started in `conftest.py` as daemon threads for pusher integration tests. `USE_STUBS=true` must be set.

---

## Known Issues

1. **`run_import.py` path inconsistency**: `plan.md` (the schema spec) refers to `parser/run_import.py` as an "existing file" but the implementation plan places the CLI entry at `core/run_import.py`. The implementation plan is authoritative — use `core/run_import.py`.

2. **`'failed'` status and re-enqueue**: The deduplication check intentionally excludes `'failed'` rows — a book that previously failed to push will be re-enqueued on the next upsert event. This is correct behavior but agents must not accidentally block re-enqueue by broadening the `status IN (...)` check to include `'failed'`.

3. **ONIX 2.1 block updates**: ONIX 2.1 has no formal block update concept (no `notification_type=04` semantics). The `onix2_parser.py` should treat all ONIX 2.1 records as full record replacements — always call `upsert_book`, never `block_update`.

---

## Agent Responsibility Map

| Agent | Creates |
|-------|---------|
| Planner (1) | `CLAUDE.md` |
| XML Source Finder (2) | `samples/` |
| Infrastructure (3) | `docker/`, `.gitignore`, `core/.env.example`, `viewer/.env.example` |
| SQL Schema (4) | `db/schema.sql` |
| Python Core (5) | `core/parser/`, `core/db/`, `core/pushers/`, `core/stubs/`, `core/run_import.py`, `core/scheduler.py`, `core/requirements.txt` |
| Testing (6) | `core/tests/` |
| Viewer Contract (7) | `docs/viewer-data-contract.md` |
| Viewer Backend (8) | `viewer/api/`, `viewer/requirements.txt` |
| Viewer Frontend (9) | `viewer/templates/` |
| Docs + Git (10) | `README.md`, `docs/bookstore-fields.md`, git commit |
