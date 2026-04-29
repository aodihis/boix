import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from parser.onix2_parser import parse_onix2
from parser.models import Book, Feed


def test_parse_onix2_returns_feed_and_books(onix21_path: str) -> None:
    feed, books = parse_onix2(onix21_path)
    assert isinstance(feed, Feed)
    assert isinstance(books, list)
    assert len(books) == 1


def test_feed_onix_version(onix21_path: str) -> None:
    feed, _ = parse_onix2(onix21_path)
    assert feed.onix_version == "2.1"


def test_feed_sender_name(onix21_path: str) -> None:
    feed, _ = parse_onix2(onix21_path)
    assert feed.sender_name == "Test Publisher"


def test_book_isbn_matches_onix3(onix21_path: str) -> None:
    # Same ISBN as ONIX 3 book 1 — both parsers produce identical ISBN
    _, books = parse_onix2(onix21_path)
    assert books[0].isbn13 == "9780000000001"


def test_book_notification_type(onix21_path: str) -> None:
    _, books = parse_onix2(onix21_path)
    assert books[0].notification_type_code == "03"


def test_book_title(onix21_path: str) -> None:
    _, books = parse_onix2(onix21_path)
    assert books[0].title is not None
    assert "Test Book" in books[0].title


def test_book_contributor(onix21_path: str) -> None:
    _, books = parse_onix2(onix21_path)
    assert len(books[0].contributors) >= 1
    assert books[0].contributors[0].role_code == "A01"


def test_book_subject(onix21_path: str) -> None:
    _, books = parse_onix2(onix21_path)
    assert len(books[0].subjects) >= 1
    assert books[0].subjects[0].scheme_code == "10"
    assert books[0].subjects[0].is_main_subject is True


def test_book_price(onix21_path: str) -> None:
    _, books = parse_onix2(onix21_path)
    assert len(books[0].prices) >= 1
    assert books[0].prices[0].currency_code == "USD"
    assert books[0].prices[0].price_amount == pytest.approx(24.99)


def test_book_publisher(onix21_path: str) -> None:
    _, books = parse_onix2(onix21_path)
    assert books[0].publisher_name == "Test Publishing House"


def test_blocks_present_empty(onix21_path: str) -> None:
    # ONIX 2.1 has no block concept — blocks_present must always be empty
    _, books = parse_onix2(onix21_path)
    assert books[0].blocks_present == []
