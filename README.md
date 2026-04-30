# ONIX Book Import System

Ingests ONIX XML book metadata (versions 2.1 and 3.x) into PostgreSQL, pushes new/updated records to FileMaker and Craft CMS via a smart push queue, and exposes a read-only Flask+HTMX viewer for browsing the database.

## Architecture

Two independent apps sharing one PostgreSQL database:
- **`core/`** — main import app (designed for serverless/lambda): parses ONIX XML, upserts to DB, enqueues pushes
- **`viewer/`** — read-only Flask+HTMX UI for browsing books (local testing and presentation only)

## Prerequisites

- Docker + Docker Compose
- Python 3.11+

## Quick Start (Docker)

```bash
# 1. Copy env files
cp core/.env.example core/.env
cp viewer/.env.example viewer/.env

# 2. Start PostgreSQL + viewer + stubs
docker-compose -f docker/docker-compose.yml up -d

# 3. Import an ONIX file
docker-compose -f docker/docker-compose.yml run --rm core \
  python run_import.py --file ../samples/Onix3sample_refnames.xml

# 4. Open the viewer
open http://localhost:5000/books
```

## Quick Start (Local venv)

```bash
# Core app
cd core
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # edit DB_* vars

# Import a file
python run_import.py --file ../samples/Onix3sample_refnames.xml

# Start push scheduler
python scheduler.py

# Viewer app (separate terminal)
cd viewer
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python api/server.py
```

## Running the Push Scheduler

```bash
cd core
source venv/bin/activate
# Edit .env: set PUSH_TARGETS=filemaker,craftcms and PUSH_INTERVAL_SECONDS=300
# For local testing with stub servers:
# USE_STUBS=true
python scheduler.py
```

## Running Stub Servers (dev/test)

```bash
cd core
source venv/bin/activate
USE_STUBS=true python stubs/run_stubs.py
# FileMaker stub: http://localhost:5001
# Craft CMS stub: http://localhost:5002
```

## Running Tests

```bash
cd core
source venv/bin/activate
# Unit tests only (no DB needed):
pytest tests/test_detect.py tests/test_onix3_parser.py tests/test_onix2_parser.py tests/test_push_queue.py -v

# All tests (requires PostgreSQL running):
DB_HOST=localhost DB_NAME=books DB_USER=books DB_PASSWORD=books \
  pytest tests/ -v --cov=. --cov-report=term-missing
```

## Project Structure

```
books-seed-data/
├── core/               Main import app (lambda-ready)
│   ├── parser/         ONIX 2.1 and 3.x parsers
│   ├── db/             PostgreSQL upsert + push queue logic
│   ├── pushers/        FileMaker and Craft CMS push clients
│   ├── stubs/          Local stub servers for FM and Craft APIs
│   ├── tests/          pytest unit + integration tests
│   ├── run_import.py   CLI entry point
│   └── scheduler.py    APScheduler push queue drainer
├── viewer/             Read-only Flask+HTMX UI
│   ├── api/            Flask routes and DB queries
│   └── templates/      Jinja2 + HTMX + Bootstrap 5 templates
├── db/
│   └── schema.sql      6-table PostgreSQL schema
├── docker/             Docker Compose + Dockerfiles
├── samples/            ONIX XML sample files
├── docs/               Data contracts and field mappings
└── xsd/                ONIX 3.1 XSD schema files
```

## Environment Variables

Point to `core/.env.example` and `viewer/.env.example` for the full list.

## Database Schema

Six tables in PostgreSQL (`db/schema.sql`):

### `feeds`
Tracks each ingested ONIX file.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PK | |
| `source_file` | TEXT | Original file path/name |
| `onix_version` | VARCHAR(10) | `'2.1'`, `'3.0'`, or `'3.1'` |
| `sender_name` | TEXT | |
| `sender_email` | TEXT | |
| `sent_at` | TIMESTAMPTZ | Timestamp from the ONIX header |
| `ingested_at` | TIMESTAMPTZ | When this system processed the file |
| `source_type` | VARCHAR(20) | |

### `books`
Central record per product. Scalar fields are columns; variable-length data is JSONB.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PK | |
| `feed_id` | INT → feeds | |
| `record_reference` | TEXT UNIQUE | ONIX `RecordReference` — natural key |
| `notification_type_code` | VARCHAR(2) | ONIX codelist 1 |
| `isbn13` | VARCHAR(13) UNIQUE | |
| `isbn10` | VARCHAR(10) | |
| `gtin13` | VARCHAR(13) | |
| `identifiers` | JSONB | All `<ProductIdentifier>` entries |
| `title` / `subtitle` / `full_title` | TEXT | |
| `series_name` / `series_number` | TEXT | |
| `product_form_code` / `product_form` | VARCHAR(3) / TEXT | |
| `edition_number` / `edition_statement` | INT / TEXT | |
| `publisher_name` / `imprint_name` | TEXT | |
| `city_of_publication` / `country_of_publication` | TEXT / VARCHAR(2) | |
| `publishing_status_code` / `publishing_status` | VARCHAR(2) / TEXT | |
| `publication_date` | DATE | |
| `availability_code` / `availability` | VARCHAR(2) / TEXT | |
| `page_count` | INT | |
| `height_mm` / `width_mm` / `thickness_mm` | NUMERIC(6,1) | |
| `weight_g` | NUMERIC(8,2) | |
| `cover_url` | TEXT | |
| `short_description` / `description` | TEXT | |
| `language_code` / `original_language_code` | VARCHAR(3) | |
| `audience_code` | VARCHAR(3) | |
| `rights_countries_included` / `_excluded` / `rights_regions` | TEXT | |
| `languages` / `texts` / `media` / `related` | JSONB | Variable ONIX blocks |
| `created_at` / `updated_at` | TIMESTAMPTZ | |

GIN indexes on `identifiers`, `texts`, `media`.

### `book_contributors`
One row per contributor per book (authors, editors, translators, etc.).

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PK | |
| `book_id` | INT → books | CASCADE delete |
| `sequence_number` | INT | ONIX display order |
| `role_code` / `role` | VARCHAR(3) / TEXT | ONIX codelist 17 |
| `names_before_key` / `key_names` / `display_name` / `inverted_name` | TEXT | |
| `from_language_code` | VARCHAR(3) | For translators |
| `biographical_note` | TEXT | |
| `bio_textformat` | VARCHAR(5) | |
| `contributor_id_type` / `contributor_id_value` | VARCHAR(5) / TEXT | e.g. ISNI, ORCID |

### `book_subjects`
One row per subject classification per book.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PK | |
| `book_id` | INT → books | CASCADE delete |
| `is_main_subject` | BOOLEAN | |
| `scheme_code` / `scheme_name` / `scheme_version` | VARCHAR(5) / TEXT / TEXT | e.g. `10` = BISAC |
| `subject_code` | TEXT | |
| `subject_heading_text` | TEXT | Human-readable label |

### `book_prices`
One row per price point per book (currency × territory × type).

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PK | |
| `book_id` | INT → books | CASCADE delete |
| `supplier_name` / `supplier_role_code` | TEXT / VARCHAR(2) | |
| `availability_code` / `availability` | VARCHAR(2) / TEXT | |
| `price_type_code` / `price_status_code` | VARCHAR(2) | |
| `price_amount` | NUMERIC(12,4) | |
| `currency_code` | VARCHAR(3) | ISO 4217 |
| `countries_included` / `countries_excluded` / `regions_included` | TEXT | |
| `discount_code_type_code` / `discount_code` / `discount_percent` | VARCHAR(3) / TEXT / NUMERIC | |
| `tax_type_code` / `tax_rate_code` / `tax_rate_percent` / `taxable_amount` / `tax_amount` | various | |
| `market_reference` / `market_publishing_status_code` / `market_date` | TEXT / VARCHAR(2) / DATE | |

### `push_queue`
Tracks which books need to be pushed to downstream systems.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PK | |
| `book_id` | INT → books | CASCADE delete |
| `target` | VARCHAR(20) | `'filemaker'` or `'craftcms'` |
| `status` | VARCHAR(20) | `pending` → `sent` or `failed` |
| `attempts` | INT | Incremented on each failure; max 3 |
| `last_attempted` / `sent_at` | TIMESTAMPTZ | |
| `error_message` | TEXT | Last failure detail |
| `created_at` | TIMESTAMPTZ | |

---

## Smart Push Logic

Only new and updated books are pushed:
- `notification_type 01/02/03` → enqueued once per target (deduplicated)
- `notification_type 04` (block update) → always re-enqueued
- `notification_type 05` (deleted) → skipped

## Production Notes

- Designed for DigitalOcean Functions (serverless) + Managed PostgreSQL
- `core/run_import.py` is the function entry point
- `core/scheduler.py` runs as a separate long-running process or cron job
