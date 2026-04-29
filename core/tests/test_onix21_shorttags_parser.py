"""Tests that the ONIX 2.1 parser handles short tag files correctly."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from parser.onix2_parser import parse_onix2
from parser.models import Feed


def test_short21_returns_feed_and_books(onix21_shorttags_path: str) -> None:
    feed, books = parse_onix2(onix21_shorttags_path)
    assert isinstance(feed, Feed)
    assert len(books) == 1


def test_short21_feed_sender(onix21_shorttags_path: str) -> None:
    feed, _ = parse_onix2(onix21_shorttags_path)
    assert feed.sender_name == "Test Publisher"
    assert feed.sender_email == "feed@testpublisher.com"


def test_short21_book_isbn(onix21_shorttags_path: str) -> None:
    _, books = parse_onix2(onix21_shorttags_path)
    assert books[0].isbn13 == "9780000000001"


def test_short21_book_notification_type(onix21_shorttags_path: str) -> None:
    _, books = parse_onix2(onix21_shorttags_path)
    assert books[0].notification_type_code == "03"


def test_short21_book_title(onix21_shorttags_path: str) -> None:
    _, books = parse_onix2(onix21_shorttags_path)
    assert books[0].title == "The Great Test Book"


def test_short21_book_contributor(onix21_shorttags_path: str) -> None:
    _, books = parse_onix2(onix21_shorttags_path)
    book = books[0]
    assert len(book.contributors) == 1
    c = book.contributors[0]
    assert c.role_code == "A01"
    assert c.names_before_key == "Jane"
    assert c.key_names == "Smith"
    assert c.inverted_name == "Smith, Jane"


def test_short21_book_publisher(onix21_shorttags_path: str) -> None:
    _, books = parse_onix2(onix21_shorttags_path)
    assert books[0].publisher_name == "Test Publishing House"


def test_short21_book_price(onix21_shorttags_path: str) -> None:
    _, books = parse_onix2(onix21_shorttags_path)
    book = books[0]
    assert len(book.prices) == 1
    assert book.prices[0].price_amount == pytest.approx(24.99)
    assert book.prices[0].currency_code == "USD"


def test_short21_and_reference_produce_same_isbn(
    onix21_path: str, onix21_shorttags_path: str
) -> None:
    """Same book in reference and short tag format produces the same ISBN."""
    _, ref_books = parse_onix2(onix21_path)
    _, short_books = parse_onix2(onix21_shorttags_path)
    assert ref_books[0].isbn13 == short_books[0].isbn13
