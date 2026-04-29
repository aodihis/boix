from typing import Optional

import psycopg2.extensions
import requests


def _get_craft_base_url(config: dict) -> str:
    if config.get("USE_STUBS", "").lower() == "true":
        port = config.get("CRAFT_STUB_PORT", "5002")
        return f"http://localhost:{port}"
    return config["CRAFTCMS_BASE_URL"]


def _fetch_book(book_id: int, conn: psycopg2.extensions.connection) -> Optional[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT record_reference, isbn13, isbn10, gtin13,
                   title, subtitle, full_title, series_name, series_number,
                   product_form, publisher_name, imprint_name,
                   publishing_status, publication_date, availability,
                   cover_url, short_description, description,
                   language_code, page_count
            FROM books WHERE id=%s
            """,
            (book_id,),
        )
        cols = [d[0] for d in cur.description]
        row = cur.fetchone()
        if row is None:
            return None
        return dict(zip(cols, row))


def _book_to_craft_payload(book_row: dict) -> dict:
    return {
        "title": book_row.get("title", ""),
        "fields": {
            "recordReference": book_row.get("record_reference", ""),
            "isbn13": book_row.get("isbn13", ""),
            "subtitle": book_row.get("subtitle", ""),
            "fullTitle": book_row.get("full_title", ""),
            "seriesName": book_row.get("series_name", ""),
            "productForm": book_row.get("product_form", ""),
            "publisherName": book_row.get("publisher_name", ""),
            "publishingStatus": book_row.get("publishing_status", ""),
            "publicationDate": str(book_row.get("publication_date", "") or ""),
            "availability": book_row.get("availability", ""),
            "coverUrl": book_row.get("cover_url", ""),
            "shortDescription": book_row.get("short_description", ""),
            "description": book_row.get("description", ""),
            "languageCode": book_row.get("language_code", ""),
            "pageCount": book_row.get("page_count", ""),
        },
    }


def push_book_to_craft(
    book_id: int, conn: psycopg2.extensions.connection, config: dict
) -> dict:
    """Reads book from DB and pushes it to Craft CMS. Returns response dict."""
    book_row = _fetch_book(book_id, conn)
    if book_row is None:
        return {"error": f"book_id {book_id} not found"}

    base_url = _get_craft_base_url(config)
    token = config["CRAFTCMS_TOKEN"]

    resp = requests.post(
        f"{base_url}/actions/elements/save",
        json=_book_to_craft_payload(book_row),
        headers={
            "X-Craft-Token": token,
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
