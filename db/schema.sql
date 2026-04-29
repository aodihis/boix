-- ONIX Book Import — PostgreSQL Schema

-- Feeds table: tracks ingested ONIX files
CREATE TABLE IF NOT EXISTS feeds (
  id              SERIAL PRIMARY KEY,
  source_file     TEXT,
  onix_version    VARCHAR(10),
  sender_name     TEXT,
  sender_email    TEXT,
  sent_at         TIMESTAMPTZ,
  ingested_at     TIMESTAMPTZ DEFAULT NOW(),
  source_type     VARCHAR(20)
);

-- Books table: central record with JSONB for variable data
CREATE TABLE IF NOT EXISTS books (
  id              SERIAL PRIMARY KEY,
  feed_id         INT REFERENCES feeds(id),

  -- Core identity
  record_reference        TEXT UNIQUE NOT NULL,
  notification_type_code  VARCHAR(2),

  -- Top identifiers
  isbn13          VARCHAR(13) UNIQUE,
  isbn10          VARCHAR(10),
  gtin13          VARCHAR(13),
  identifiers     JSONB DEFAULT '[]',

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

  -- Primary media/text
  cover_url           TEXT,
  short_description   TEXT,
  description         TEXT,

  -- Classification
  language_code           VARCHAR(3),
  original_language_code  VARCHAR(3),
  audience_code           VARCHAR(3),
  trade_category_code     VARCHAR(10),

  -- Rights
  rights_countries_included   TEXT,
  rights_countries_excluded   TEXT,
  rights_regions              TEXT,

  -- Variable data as JSONB
  languages   JSONB DEFAULT '[]',
  texts       JSONB DEFAULT '[]',
  media       JSONB DEFAULT '[]',
  related     JSONB DEFAULT '[]',

  -- Audit
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS books_isbn13_idx       ON books(isbn13);
CREATE INDEX IF NOT EXISTS books_identifiers_idx  ON books USING GIN(identifiers);
CREATE INDEX IF NOT EXISTS books_texts_idx        ON books USING GIN(texts);
CREATE INDEX IF NOT EXISTS books_media_idx        ON books USING GIN(media);

-- Book contributors: normalized for author/role searches
CREATE TABLE IF NOT EXISTS book_contributors (
  id              SERIAL PRIMARY KEY,
  book_id         INT REFERENCES books(id) ON DELETE CASCADE,
  sequence_number INT,
  role_code       VARCHAR(3),
  role            TEXT,
  names_before_key    TEXT,
  key_names           TEXT,
  display_name        TEXT,
  inverted_name       TEXT,
  from_language_code  VARCHAR(3),
  biographical_note   TEXT,
  bio_textformat      VARCHAR(5),
  contributor_id_type  VARCHAR(5),
  contributor_id_value TEXT
);

CREATE INDEX IF NOT EXISTS book_contributors_book_idx     ON book_contributors(book_id);
CREATE INDEX IF NOT EXISTS book_contributors_keynames_idx ON book_contributors(key_names);

-- Book subjects: normalized for classification filtering
CREATE TABLE IF NOT EXISTS book_subjects (
  id              SERIAL PRIMARY KEY,
  book_id         INT REFERENCES books(id) ON DELETE CASCADE,
  is_main_subject BOOLEAN DEFAULT FALSE,
  scheme_code     VARCHAR(5),
  scheme_name     TEXT,
  scheme_version  TEXT,
  subject_code    TEXT,
  subject_heading_text TEXT
);

CREATE INDEX IF NOT EXISTS book_subjects_book_idx   ON book_subjects(book_id);
CREATE INDEX IF NOT EXISTS book_subjects_scheme_idx ON book_subjects(scheme_code, subject_code);

-- Book prices: normalized for price/territory queries
CREATE TABLE IF NOT EXISTS book_prices (
  id              SERIAL PRIMARY KEY,
  book_id         INT REFERENCES books(id) ON DELETE CASCADE,
  -- Supplier
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
  -- Tax
  tax_type_code           VARCHAR(2),
  tax_rate_code           VARCHAR(2),
  tax_rate_percent        NUMERIC(5,2),
  taxable_amount          NUMERIC(12,4),
  tax_amount              NUMERIC(12,4),
  -- Market
  market_reference              TEXT,
  market_publishing_status_code VARCHAR(2),
  market_date                   DATE
);

CREATE INDEX IF NOT EXISTS book_prices_book_idx     ON book_prices(book_id);
CREATE INDEX IF NOT EXISTS book_prices_currency_idx ON book_prices(currency_code, price_amount);

-- Push queue: tracks which books need to be sent to FileMaker / Craft CMS
CREATE TABLE IF NOT EXISTS push_queue (
  id              SERIAL PRIMARY KEY,
  book_id         INT REFERENCES books(id) ON DELETE CASCADE,
  target          VARCHAR(20) NOT NULL,
  status          VARCHAR(20) DEFAULT 'pending',
  attempts        INT DEFAULT 0,
  last_attempted  TIMESTAMPTZ,
  sent_at         TIMESTAMPTZ,
  error_message   TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS push_queue_status_idx ON push_queue(status, target);
CREATE INDEX IF NOT EXISTS push_queue_book_idx   ON push_queue(book_id);
