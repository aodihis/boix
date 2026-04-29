import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from parser.onix_parser import parse_onix3
from db.importer import upsert_feed, upsert_book


def test_upsert_feed_returns_int(db_conn, onix3_path: str) -> None:
    feed, _ = parse_onix3(onix3_path)
    feed_id = upsert_feed(feed, db_conn)
    assert isinstance(feed_id, int)
    assert feed_id > 0


def test_upsert_book_roundtrip(db_conn, onix3_path: str) -> None:
    feed, books = parse_onix3(onix3_path)
    feed_id = upsert_feed(feed, db_conn)

    book = next(b for b in books if b.isbn13 == "9780000000001")
    book_id = upsert_book(book, feed_id, db_conn)
    assert isinstance(book_id, int)

    with db_conn.cursor() as cur:
        cur.execute("SELECT isbn13, title FROM books WHERE id=%s", (book_id,))
        row = cur.fetchone()

    assert row is not None
    assert row[0] == "9780000000001"
    assert row[1] is not None


def test_upsert_idempotent(db_conn, onix3_path: str) -> None:
    feed, books = parse_onix3(onix3_path)
    feed_id = upsert_feed(feed, db_conn)
    book = next(b for b in books if b.isbn13 == "9780000000001")

    id1 = upsert_book(book, feed_id, db_conn)
    id2 = upsert_book(book, feed_id, db_conn)
    assert id1 == id2


def test_upsert_book_stores_contributors(db_conn, onix3_path: str) -> None:
    feed, books = parse_onix3(onix3_path)
    feed_id = upsert_feed(feed, db_conn)
    book = next(b for b in books if b.isbn13 == "9780000000001")
    book_id = upsert_book(book, feed_id, db_conn)

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT role_code FROM book_contributors WHERE book_id=%s", (book_id,)
        )
        rows = cur.fetchall()

    assert len(rows) >= 1
    assert rows[0][0] == "A01"


def test_upsert_book_stores_subjects(db_conn, onix3_path: str) -> None:
    feed, books = parse_onix3(onix3_path)
    feed_id = upsert_feed(feed, db_conn)
    book = next(b for b in books if b.isbn13 == "9780000000001")
    book_id = upsert_book(book, feed_id, db_conn)

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT scheme_code FROM book_subjects WHERE book_id=%s", (book_id,)
        )
        rows = cur.fetchall()

    assert len(rows) >= 1


def test_upsert_book_stores_prices(db_conn, onix3_path: str) -> None:
    feed, books = parse_onix3(onix3_path)
    feed_id = upsert_feed(feed, db_conn)
    book = next(b for b in books if b.isbn13 == "9780000000001")
    book_id = upsert_book(book, feed_id, db_conn)

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT currency_code, price_amount FROM book_prices WHERE book_id=%s",
            (book_id,),
        )
        rows = cur.fetchall()

    assert len(rows) >= 1
    assert rows[0][0] == "USD"
