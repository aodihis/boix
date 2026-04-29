# Viewer Data Contract

This document is the authoritative specification for the Flask+HTMX viewer app (`viewer/`). Both the backend (Agent 8) and the frontend (Agent 9) must implement exactly what is described here. No additions, no omissions.

---

## 1. Book List View (`GET /books`)

### Fields to display in the books table

| DB Column | Display Label | Format / Notes |
|---|---|---|
| `id` | ID | Integer, plain |
| `isbn13` | ISBN-13 | Plain string; show `—` if null |
| `title` | Title | Truncate to 60 chars; append `…` if truncated |
| `publisher_name` | Publisher | Truncate to 40 chars; show `—` if null |
| `publication_date` | Pub Date | Format as `YYYY-MM-DD`; show `—` if null |
| `product_form` | Format | Human label from `books.product_form`; show `—` if null |
| `publishing_status` | Status | Human label from `books.publishing_status`; show `—` if null |
| `notification_type_code` | Notif. | Raw code (e.g. `01`, `04`); show `—` if null |
| `updated_at` | Updated | Relative time: `2 hours ago`, `3 days ago`, etc. |

### Pagination

- 20 books per page (constant; no user-selectable page size).
- Show current page number and total count: `Page 2 of 47 (940 books)`.
- Previous / Next links. Disable Prev on page 1, Next on last page.
- Query parameter: `?page=N` (default 1).

### Search

- Full-text across `title`, `isbn13`, `publisher_name`.
- Case-insensitive `ILIKE %term%` matching.
- HTMX live search: 300 ms debounce, replaces only the `<tbody>` rows (partial `book_rows.html` fragment).
- Query parameter: `?q=term`.
- Pagination and search combine: `?page=2&q=tolkien`.

---

## 2. Book Detail View (`GET /books/<id>`)

All fields are read-only. Null/missing values render as `—`. Sections with no data at all may be omitted from the rendered page.

### Identity

| DB Column | Display Label | Notes |
|---|---|---|
| `id` | Book ID | |
| `record_reference` | Record Reference | |
| `isbn13` | ISBN-13 | |
| `isbn10` | ISBN-10 | |
| `gtin13` | GTIN-13 | |
| `notification_type_code` | Notification Type | |
| `identifiers` | All Identifiers | JSONB array; render as key-value pairs (`type: value`) |

### Title

| DB Column | Display Label |
|---|---|
| `title` | Title |
| `subtitle` | Subtitle |
| `full_title` | Full Title |
| `series_name` | Series |
| `series_number` | Series Number |

### Format

| DB Column | Display Label | Notes |
|---|---|---|
| `product_form` | Product Form | Human label |
| `product_form_code` | Form Code | Raw code in parentheses next to label |
| `edition_number` | Edition Number | |
| `edition_statement` | Edition Statement | |
| `page_count` | Page Count | |
| `height_mm` | Height (mm) | |
| `width_mm` | Width (mm) | |
| `thickness_mm` | Thickness (mm) | |
| `weight_g` | Weight (g) | |

### Publishing

| DB Column | Display Label | Notes |
|---|---|---|
| `publisher_name` | Publisher | |
| `imprint_name` | Imprint | |
| `city_of_publication` | City | |
| `country_of_publication` | Country | 2-letter ISO code |
| `publishing_status` | Publishing Status | Human label |
| `publishing_status_code` | Status Code | Raw code in parentheses next to label |
| `publication_date` | Publication Date | `YYYY-MM-DD` |
| `availability` | Availability | Human label |
| `availability_code` | Availability Code | Raw code |

### Language

| DB Column | Display Label | Notes |
|---|---|---|
| `language_code` | Language | 3-letter ISO code |
| `original_language_code` | Original Language | 3-letter ISO code |
| `languages` | All Languages | JSONB array; render as list of `{role, language_code}` pairs |

### Rights

| DB Column | Display Label |
|---|---|
| `rights_countries_included` | Countries Included |
| `rights_countries_excluded` | Countries Excluded |
| `rights_regions` | Regions |

### Contributors

Source: `book_contributors` table, `WHERE book_id = ?`, sorted by `sequence_number ASC`.

Display columns: `sequence_number`, `display_name`, `role` (human label), `inverted_name`, `biographical_note` (truncated to 300 chars with expand link).

### Subjects

Source: `book_subjects` table, `WHERE book_id = ?`, sorted by `is_main_subject DESC`, then `scheme_code ASC`.

Display columns: `is_main_subject` (badge: "Main" or blank), `scheme_name`, `subject_code`, `subject_heading_text`.

### Prices

Source: `book_prices` table, `WHERE book_id = ?`, sorted by `currency_code ASC`, then `price_amount ASC`.

Group by `supplier_name`. For each price row display: `price_amount`, `currency_code`, `price_type_code` (raw), `availability`, `countries_included`, `discount_percent` (if set), `tax_rate_percent` (if set).

### Media

Source: `books.media` JSONB array.

Each item expected shape: `{"type": "...", "url": "...", "caption": "..."}`.

Render cover images as thumbnails (max 120 px wide). All other media as clickable links with type label.

### Texts

Source: `books.texts` JSONB array.

Each item expected shape: `{"text_type": "...", "content": "..."}`.

Render as collapsible `<details>` sections, one per text type. Label is the `text_type` value. Content is plain text (escape HTML).

### Push Queue Status

Source: `push_queue` table, `WHERE book_id = ?`, grouped by `target` and `status`.

Display a small summary table:

| Target | Pending | Sent | Failed |
|--------|---------|------|--------|
| filemaker | N | N | N |
| craftcms | N | N | N |

Show `0` for missing combinations. Do not show rows for targets with all zeros.

---

## 3. API Endpoints

### `GET /api/books?page=1&q=search_term`

Returns a JSON array of list-view book objects. Each object contains exactly:

```json
{
  "id": 42,
  "isbn13": "9780000000001",
  "title": "The Great Novel",
  "publisher_name": "Acme Books",
  "publication_date": "2023-06-15",
  "product_form": "Paperback",
  "product_form_code": "BC",
  "publishing_status": "Active",
  "publishing_status_code": "04",
  "notification_type_code": "03",
  "updated_at": "2024-01-10T14:22:00Z"
}
```

Null fields are included as `null`, not omitted.

Response envelope:

```json
{
  "books": [...],
  "page": 1,
  "per_page": 20,
  "total": 940
}
```

### `GET /api/books/search?q=search_term`

Returns HTMX partial HTML: a sequence of `<tr>` rows (no surrounding `<table>` or `<tbody>`). This is the fragment loaded into the list page's `<tbody>` by HTMX live search. The row structure must match the full `book_rows.html` template exactly.

### `GET /api/books/<id>`

Returns full book JSON. Shape:

```json
{
  "book": { /* all columns from books table */ },
  "contributors": [ /* all rows from book_contributors WHERE book_id=id */ ],
  "subjects":     [ /* all rows from book_subjects WHERE book_id=id */ ],
  "prices":       [ /* all rows from book_prices WHERE book_id=id */ ],
  "push_status":  [
    {"target": "filemaker", "status": "pending", "count": 1},
    {"target": "craftcms",  "status": "sent",    "count": 1}
  ]
}
```

Returns HTTP 404 with `{"error": "Book not found"}` if the id does not exist.

---

## 4. SQL Queries

All queries are implemented in `viewer/api/queries.py`. No SQL elsewhere.

### `list_books(page: int, per_page: int, search: str) -> list[dict]`

```sql
SELECT id, isbn13, title, publisher_name, publication_date,
       product_form_code, product_form,
       publishing_status_code, publishing_status,
       notification_type_code, updated_at
FROM books
WHERE (%(search)s = '' OR title ILIKE %(pattern)s
       OR isbn13 ILIKE %(pattern)s
       OR publisher_name ILIKE %(pattern)s)
ORDER BY updated_at DESC
LIMIT %(per_page)s OFFSET %(offset)s
```

`pattern` = `'%' + search + '%'`, `offset` = `(page - 1) * per_page`.

### `count_books(search: str) -> int`

```sql
SELECT COUNT(*)
FROM books
WHERE (%(search)s = '' OR title ILIKE %(pattern)s
       OR isbn13 ILIKE %(pattern)s
       OR publisher_name ILIKE %(pattern)s)
```

Same `WHERE` clause as `list_books`.

### `get_book_detail(book_id: int) -> dict | None`

```sql
SELECT * FROM books WHERE id = %(book_id)s
```

Returns `None` if no row found.

### `get_book_contributors(book_id: int) -> list[dict]`

```sql
SELECT * FROM book_contributors
WHERE book_id = %(book_id)s
ORDER BY sequence_number ASC NULLS LAST
```

### `get_book_subjects(book_id: int) -> list[dict]`

```sql
SELECT * FROM book_subjects
WHERE book_id = %(book_id)s
ORDER BY is_main_subject DESC, scheme_code ASC
```

### `get_book_prices(book_id: int) -> list[dict]`

```sql
SELECT * FROM book_prices
WHERE book_id = %(book_id)s
ORDER BY currency_code ASC, price_amount ASC
```

### `get_push_status(book_id: int) -> list[dict]`

```sql
SELECT target, status, COUNT(*) AS count
FROM push_queue
WHERE book_id = %(book_id)s
GROUP BY target, status
ORDER BY target, status
```

Returns list of `{"target": ..., "status": ..., "count": ...}` dicts.

---

## 5. URL Structure

| Method | Path | Handler | Notes |
|--------|------|---------|-------|
| `GET` | `/` | Redirect | 302 to `/books` |
| `GET` | `/books` | Full page | Book list, page 1, no filter |
| `GET` | `/books?page=N&q=term` | Full page | Paginated and/or filtered list |
| `GET` | `/books/<id>` | Full page | Book detail |
| `GET` | `/api/books` | JSON | List-view data |
| `GET` | `/api/books?page=N&q=term` | JSON | Filtered list-view data |
| `GET` | `/api/books/search?q=term` | HTMX partial | `<tr>` rows only |
| `GET` | `/api/books/<id>` | JSON | Full book detail |

All other methods and paths return HTTP 405 or 404 respectively.

---

## 6. No-Write Contract

The viewer MUST NOT:

- Accept `POST`, `PUT`, `PATCH`, or `DELETE` requests on any route.
- Import any module from `core/`.
- Execute any `INSERT`, `UPDATE`, or `DELETE` SQL statement.
- Expose any endpoint that triggers, schedules, or signals an import operation.

The Flask app must be registered with read-only DB credentials where possible. If a shared credential is used, the application layer must never issue write queries.

---

## 7. Error States

| Condition | HTTP Status | User-visible message |
|---|---|---|
| Book id not found | 404 | "Book not found" |
| DB connection failure | 503 | "Database unavailable — please try again later" |
| Empty search results | 200 | "No books found matching your search" (in place of table rows) |
| Empty database (no books at all) | 200 | "No books in database yet" (in place of table) |
| Invalid page parameter (non-integer, < 1) | 400 | Silently clamp to page 1 (do not show error) |

Error pages for 404 and 503 use the standard base template (navbar, footer). They do not redirect.
