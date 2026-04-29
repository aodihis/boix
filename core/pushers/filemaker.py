import os
from typing import Optional

import psycopg2.extensions
import requests


def _get_fm_base_url(config: dict) -> str:
    if config.get("USE_STUBS", "").lower() == "true":
        port = config.get("FM_STUB_PORT", "5001")
        return f"http://localhost:{port}"
    return config["FILEMAKER_BASE_URL"]


def _book_to_fm_fields(book_row: dict) -> dict:
    """Maps a book dict (from DB SELECT) to FileMaker fieldData."""
    return {
        "RecordReference": book_row.get("record_reference", ""),
        "ISBN13": book_row.get("isbn13", ""),
        "Title": book_row.get("title", ""),
        "Subtitle": book_row.get("subtitle", ""),
        "FullTitle": book_row.get("full_title", ""),
        "SeriesName": book_row.get("series_name", ""),
        "SeriesNumber": book_row.get("series_number", ""),
        "ProductForm": book_row.get("product_form", ""),
        "PublisherName": book_row.get("publisher_name", ""),
        "ImprintName": book_row.get("imprint_name", ""),
        "PublishingStatus": book_row.get("publishing_status", ""),
        "PublicationDate": str(book_row.get("publication_date", "") or ""),
        "Availability": book_row.get("availability", ""),
        "CoverURL": book_row.get("cover_url", ""),
        "ShortDescription": book_row.get("short_description", ""),
        "Description": book_row.get("description", ""),
        "LanguageCode": book_row.get("language_code", ""),
        "PageCount": book_row.get("page_count", ""),
    }


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


def push_book_to_filemaker(
    book_id: int, conn: psycopg2.extensions.connection, config: dict
) -> dict:
    """Reads book from DB and pushes it to FileMaker Data API. Returns response dict."""
    book_row = _fetch_book(book_id, conn)
    if book_row is None:
        return {"error": f"book_id {book_id} not found"}

    base_url = _get_fm_base_url(config)
    db = config["FILEMAKER_DB"]
    layout = config["FILEMAKER_LAYOUT"]

    # Authenticate
    auth_resp = requests.post(
        f"{base_url}/fmrest/vLatest/databases/{db}/sessions",
        json={},
        auth=(config["FILEMAKER_USER"], config["FILEMAKER_PASSWORD"]),
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    auth_resp.raise_for_status()
    token = auth_resp.json()["response"]["token"]

    try:
        # Create record
        create_resp = requests.post(
            f"{base_url}/fmrest/vLatest/databases/{db}/layouts/{layout}/records",
            json={"fieldData": _book_to_fm_fields(book_row)},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        create_resp.raise_for_status()
        return create_resp.json()
    finally:
        # Logout — best-effort
        try:
            requests.delete(
                f"{base_url}/fmrest/vLatest/databases/{db}/sessions/{token}",
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
        except Exception:
            pass
