# ONIX Book Import — Database Schema Redesign

## Context

The current schema (`onix31_mysql_schema.html`) has 35 tables that faithfully mirror the full ONIX 3.1 XML structure. The goal is a lean, maintainable schema that:

- Reduces to ~5 tables using **PostgreSQL JSONB** for variable/optional data
- Stays version-agnostic (ONIX 2.1 and 3.x normalize to the same schema)
- Handles block updates (notification_type=04) without storing raw XML
- Supports full territory pricing
- Runs on **DigitalOcean** with a serverless ingestion pipeline (Functions + Spaces)
- Is ready to expose via API (CMS/FileMaker sync deferred)

---

## Database: PostgreSQL (not MySQL)

PostgreSQL JSONB is the key enabler for schema simplification:
- Indexed JSON — can query inside JSON arrays efficiently (`@>`, `->>`, `?`)
- Supported on DigitalOcean Managed Databases
- Stores sparse/optional ONIX data without empty columns or extra tables

---

## Why 5 Tables Instead of 35

**Rule:** A field stays as a separate table only if you need to **filter/search on it independently**.

| Data | Approach | Reason |
|---|---|---|
| Identifiers (DOI, SKU, etc.) | JSONB on `books` | Always fetched with book, rarely filtered |
| Languages | JSONB on `books` | 1–3 entries, always loaded together |
| Related products/works | JSONB on `books` | Reference data, not filtered |
| Texts (descriptions, reviews) | JSONB on `books` | Always loaded with book |
| Media (images, audio) | JSONB on `books` | Always loaded with book |
| **Contributors** | Separate table | Need "books by author X" queries |
| **Subjects** | Separate table | Need "books in BISAC category X" queries |
| **Prices** | Separate table | Need "books under $X in USD" queries |

---

## Recommended Schema (5 tables)

### 1. `feeds`
Tracks each ingested ONIX file.
```sql
CREATE TABLE feeds (
  id              SERIAL PRIMARY KEY,
  source_file     TEXT,
  onix_version    VARCHAR(10),   -- '2.1', '3.0', '3.1'
  sender_name     TEXT,
  sender_email    TEXT,
  sent_at         TIMESTAMPTZ,
  ingested_at     TIMESTAMPTZ DEFAULT NOW(),
  source_type     VARCHAR(20)    -- 'api' | 'ftp' | 'spaces' | 'upload' (TBD)
);
```

### 2. `books` (central record with JSONB for variable data)
```sql
CREATE TABLE books (
  id              SERIAL PRIMARY KEY,
  feed_id         INT REFERENCES feeds(id),

  -- Core identity
  record_reference        TEXT UNIQUE NOT NULL,
  notification_type_code  VARCHAR(2),

  -- Top identifiers (flat columns for fast lookup)
  isbn13          VARCHAR(13) UNIQUE,
  isbn10          VARCHAR(10),
  gtin13          VARCHAR(13),
  -- All other identifiers (DOI, proprietary SKU, etc.)
  identifiers     JSONB DEFAULT '[]',
  -- Example: [{"id_type_code":"06","id_type_name":"DOI","id_value":"10.xxx/yyy"}]

  -- Title & Series
  title                   TEXT,
  subtitle                TEXT,
  full_title              TEXT,
  series_name             TEXT,
  series_number           TEXT,

  -- Format
  product_form_code       VARCHAR(3),
  product_form            TEXT,
  edition_number          INT,
  edition_statement       TEXT,
  no_edition              BOOLEAN DEFAULT FALSE,

  -- Publishing
  publisher_name          TEXT,
  imprint_name            TEXT,
  city_of_publication     TEXT,
  country_of_publication  VARCHAR(2),
  country_of_manufacture  VARCHAR(2),
  publishing_status_code  VARCHAR(2),
  publishing_status       TEXT,
  publication_date        DATE,
  availability_code       VARCHAR(2),
  availability            TEXT,

  -- Physical
  page_count      INT,
  height_mm       NUMERIC(6,1),
  width_mm        NUMERIC(6,1),
  thickness_mm    NUMERIC(6,1),
  weight_g        NUMERIC(8,2),

  -- Primary media/text (flattened for fast access)
  cover_url           TEXT,
  short_description   TEXT,
  description         TEXT,

  -- Classification
  language_code           VARCHAR(3),   -- primary text language
  original_language_code  VARCHAR(3),
  audience_code           VARCHAR(3),
  trade_category_code     VARCHAR(10),

  -- Rights
  rights_countries_included   TEXT,
  rights_countries_excluded   TEXT,
  rights_regions              TEXT,

  -- Variable data as JSONB
  languages   JSONB DEFAULT '[]',
  -- Example: [{"language_role_code":"01","language_code":"eng"}]

  texts       JSONB DEFAULT '[]',
  -- Example: [{"text_type_code":"03","text_type":"Description","text_value":"...","textformat":"06","source_title":null}]

  media       JSONB DEFAULT '[]',
  -- Example: [{"resource_type_code":"01","resource_type":"Front cover","resource_link":"https://...","content_date":"20240101"}]

  related     JSONB DEFAULT '[]',
  -- Example: [{"relation_type":"product","relation_code":"06","id_type_code":"15","id_value":"9780007..."}]

  -- Audit
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX books_isbn13_idx       ON books(isbn13);
CREATE INDEX books_identifiers_idx  ON books USING GIN(identifiers);
CREATE INDEX books_texts_idx        ON books USING GIN(texts);
CREATE INDEX books_media_idx        ON books USING GIN(media);
```

### 3. `book_contributors`
Kept normalized — needed for author/role searches.
```sql
CREATE TABLE book_contributors (
  id              SERIAL PRIMARY KEY,
  book_id         INT REFERENCES books(id) ON DELETE CASCADE,
  sequence_number INT,
  role_code       VARCHAR(3),
  role            TEXT,
  names_before_key    TEXT,   -- first name
  key_names           TEXT,   -- last name
  display_name        TEXT,
  inverted_name       TEXT,
  from_language_code  VARCHAR(3),
  biographical_note   TEXT,
  bio_textformat      VARCHAR(5),
  -- Flattened top contributor ID (ISNI, ORCID)
  contributor_id_type  VARCHAR(5),
  contributor_id_value TEXT
);

CREATE INDEX book_contributors_book_idx     ON book_contributors(book_id);
CREATE INDEX book_contributors_keynames_idx ON book_contributors(key_names);
```

### 4. `book_subjects`
Kept normalized — needed for classification filtering.
```sql
CREATE TABLE book_subjects (
  id              SERIAL PRIMARY KEY,
  book_id         INT REFERENCES books(id) ON DELETE CASCADE,
  is_main_subject BOOLEAN DEFAULT FALSE,
  scheme_code     VARCHAR(5),    -- e.g. '10'=BISAC, '93'=Thema
  scheme_name     TEXT,
  scheme_version  TEXT,
  subject_code    TEXT,
  subject_heading_text TEXT
);

CREATE INDEX book_subjects_book_idx   ON book_subjects(book_id);
CREATE INDEX book_subjects_scheme_idx ON book_subjects(scheme_code, subject_code);
```

### 5. `book_prices`
Kept normalized — needed for price/territory queries.
```sql
CREATE TABLE book_prices (
  id              SERIAL PRIMARY KEY,
  book_id         INT REFERENCES books(id) ON DELETE CASCADE,
  -- Supplier (merged from supplier table)
  supplier_name         TEXT,
  supplier_role_code    VARCHAR(2),
  availability_code     VARCHAR(2),
  availability          TEXT,
  -- Price
  price_type_code       VARCHAR(2),
  price_status_code     VARCHAR(2),
  price_amount          NUMERIC(12,4),
  currency_code         VARCHAR(3),
  -- Territory
  countries_included    TEXT,
  countries_excluded    TEXT,
  regions_included      TEXT,
  -- Discount
  discount_code_type_code VARCHAR(3),
  discount_code           TEXT,
  discount_percent        NUMERIC(5,2),
  -- Tax (merged from price_tax)
  tax_type_code           VARCHAR(2),
  tax_rate_code           VARCHAR(2),
  tax_rate_percent        NUMERIC(5,2),
  taxable_amount          NUMERIC(12,4),
  tax_amount              NUMERIC(12,4),
  -- Market (merged from product_supply)
  market_reference              TEXT,
  market_publishing_status_code VARCHAR(2),
  market_date                   DATE
);

CREATE INDEX book_prices_book_idx     ON book_prices(book_id);
CREATE INDEX book_prices_currency_idx ON book_prices(currency_code, price_amount);
```

---

## ONIX Version Backward Compatibility

**Strategy: normalize at the parser layer. The DB schema is version-agnostic.**

### Work needed

1. **Auto-detect version** in `parser/run_import.py`:
   - ONIX 3.x: `<ONIXMessage release="3.0">` or `release="3.1"`
   - ONIX 2.1: `<ONIXMessage release="2.1">` or no release attribute

2. **Create `parser/onix2_parser.py`** — same interface as `onix_parser.py`, outputs the same `Book` object:

   | ONIX 2.1 element | Maps to |
   |---|---|
   | `<BASICMainSubject>` | subject (BISAC, is_main=True) |
   | `<Series><TitleOfSeries>` | series_name |
   | `<MediaFile><MediaFileLink>` | media JSONB |
   | `<SupplyDetail>` (flat under `<Product>`) | book_prices |
   | `<Contributor>` (flat, no sequence) | book_contributors |
   | No block updates in 2.1 | Always treat as full record |

3. **Store version in `feeds.onix_version`** for audit.

---

## Block Updates (No Raw XML Needed)

When `notification_type = 04` (Block Update):

1. Find existing book by `record_reference` (primary) or `isbn13` (fallback)
2. For each block present in the partial update:
   - **DescriptiveDetail** → update title/series/form/physical columns + re-insert contributors/subjects + update languages/identifiers JSONB
   - **CollateralDetail** → update texts/media JSONB + update cover_url/short_description/description
   - **PublishingDetail** → update publishing columns on books
   - **ProductSupply** → delete + re-insert book_prices
3. Always touch `books.updated_at`

Source files are archived to **DigitalOcean Spaces** for re-processing — not stored in DB.

---

## DigitalOcean Architecture (Lambda-equivalent)

```
Publisher / Distributor
        │
        ▼
[ONIX file arrives]
        │
        ├── via HTTP webhook → DO Function (HTTP trigger)
        ├── via FTP/SFTP    → DO Function polls or cron
        └── via upload      → DO Spaces → Spaces trigger → DO Function
                                              │
                                              ▼
                                    [DO Function: onix-ingest]
                                    1. Download file from Spaces
                                    2. Detect ONIX version
                                    3. Parse → Book objects
                                    4. Upsert to PostgreSQL
                                              │
                                              ▼
                                  [DO Managed PostgreSQL]
                                    5 tables, JSONB fields
                                              │
                                              ▼
                                    [API / future CMS sync]
```

- **DigitalOcean Functions** = serverless, scales to zero, billed per invocation
- **DigitalOcean Spaces** = S3-compatible object storage, triggers Functions on upload
- **DO Managed PostgreSQL** = fully managed, automated backups, JSONB support
- The ingestion source (which publisher, API vs FTP) is determined later — the Function just needs a file

---

## Files to Create

| File | Purpose |
|---|---|
| `parser/onix2_parser.py` | ONIX 2.1 adapter, same interface as onix_parser.py |
| `db/schema.sql` | 5-table PostgreSQL schema |
| `db/import.py` | DB write layer (upserts, block update merge logic) |
| `.do/functions/onix-ingest/` | DigitalOcean Function for serverless ingestion |

## Existing Files (unchanged or extended)

| File | Role |
|---|---|
| `parser/onix_parser.py` | Main 3.x parser — already produces `Book` object |
| `parser/run_import.py` | CLI entry — needs version detection added |
| `parser/codelists.py` | Code list resolver — shared by both parsers |
| `docs/bookstore-fields.md` | Field mapping reference |

---

## Verification

1. Run parser on `samples/Onix3sample_refnames.xml` — confirm all fields map correctly
2. Run on `samples/Onix3sample_refnames_blockupdate.xml` — confirm partial merge works
3. Run `onix2_parser.py` on a real ONIX 2.1 file — confirm same `Book` output shape
4. Insert sample into 5-table schema — confirm JSONB fields are queryable
5. Trigger DO Function with a test file — confirm end-to-end pipeline to PostgreSQL
