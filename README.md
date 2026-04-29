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

## Smart Push Logic

Only new and updated books are pushed:
- `notification_type 01/02/03` → enqueued once per target (deduplicated)
- `notification_type 04` (block update) → always re-enqueued
- `notification_type 05` (deleted) → skipped

## Production Notes

- Designed for DigitalOcean Functions (serverless) + Managed PostgreSQL
- `core/run_import.py` is the function entry point
- `core/scheduler.py` runs as a separate long-running process or cron job
