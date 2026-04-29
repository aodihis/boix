import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from parser.onix_parser import parse_onix3
from db.importer import upsert_feed, upsert_book
from pushers.filemaker import push_book_to_filemaker
from pushers.craftcms import push_book_to_craft


def _stub_fm_config() -> dict:
    return {
        "USE_STUBS": "true",
        "FM_STUB_PORT": os.environ.get("FM_STUB_PORT", "5001"),
        "FILEMAKER_DB": "testdb",
        "FILEMAKER_LAYOUT": "Books",
        "FILEMAKER_USER": "admin",
        "FILEMAKER_PASSWORD": "admin",
    }


def _stub_craft_config() -> dict:
    return {
        "USE_STUBS": "true",
        "CRAFT_STUB_PORT": os.environ.get("CRAFT_STUB_PORT", "5002"),
        "CRAFTCMS_TOKEN": "stub-token",
    }


def test_push_to_filemaker_stub(db_conn, onix3_path: str) -> None:
    if os.environ.get("USE_STUBS", "").lower() != "true":
        pytest.skip("USE_STUBS not set")

    feed, books = parse_onix3(onix3_path)
    feed_id = upsert_feed(feed, db_conn)
    book = next(b for b in books if b.isbn13 == "9780000000001")
    book_id = upsert_book(book, feed_id, db_conn)

    result = push_book_to_filemaker(book_id, db_conn, _stub_fm_config())
    assert "response" in result
    assert result["response"].get("recordId") is not None


def test_push_to_craft_stub(db_conn, onix3_path: str) -> None:
    if os.environ.get("USE_STUBS", "").lower() != "true":
        pytest.skip("USE_STUBS not set")

    feed, books = parse_onix3(onix3_path)
    feed_id = upsert_feed(feed, db_conn)
    book = next(b for b in books if b.isbn13 == "9780000000001")
    book_id = upsert_book(book, feed_id, db_conn)

    result = push_book_to_craft(book_id, db_conn, _stub_craft_config())
    assert result.get("success") is True


def test_push_to_filemaker_returns_error_for_missing_book(db_conn) -> None:
    if os.environ.get("USE_STUBS", "").lower() != "true":
        pytest.skip("USE_STUBS not set")

    result = push_book_to_filemaker(999999, db_conn, _stub_fm_config())
    assert "error" in result


def test_push_to_craft_returns_error_for_missing_book(db_conn) -> None:
    if os.environ.get("USE_STUBS", "").lower() != "true":
        pytest.skip("USE_STUBS not set")

    result = push_book_to_craft(999999, db_conn, _stub_craft_config())
    assert "error" in result
