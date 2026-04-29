import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from parser.onix_parser import parse_onix3
from db.importer import upsert_feed, upsert_book, block_update


def test_block_update_changes_price_not_title(
    db_conn, onix3_path: str, onix3_block_update_path: str
) -> None:
    # Insert the full book first
    feed, books = parse_onix3(onix3_path)
    feed_id = upsert_feed(feed, db_conn)
    book = next(b for b in books if b.isbn13 == "9780000000001")
    book_id = upsert_book(book, feed_id, db_conn)

    # Record title before block update
    with db_conn.cursor() as cur:
        cur.execute("SELECT title FROM books WHERE id=%s", (book_id,))
        title_before = cur.fetchone()[0]

    # Apply block update (ProductSupply only — new price 14.99)
    _, update_books = parse_onix3(onix3_block_update_path)
    update_book = update_books[0]
    block_update(update_book, db_conn)

    # Title must be unchanged
    with db_conn.cursor() as cur:
        cur.execute("SELECT title FROM books WHERE id=%s", (book_id,))
        title_after = cur.fetchone()[0]

    assert title_before == title_after

    # Price must be updated to 14.99
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT price_amount FROM book_prices WHERE book_id=%s", (book_id,)
        )
        prices = cur.fetchall()

    assert len(prices) >= 1
    assert float(prices[0][0]) == pytest.approx(14.99)


def test_block_update_raises_for_unknown_record(db_conn) -> None:
    from parser.models import Book

    orphan = Book(
        record_reference="DOES-NOT-EXIST-XYZ",
        notification_type_code="04",
        blocks_present=["ProductSupply"],
    )
    with pytest.raises(ValueError, match="no existing book"):
        block_update(orphan, db_conn)
