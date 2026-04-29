"""Tests that the ONIX 3.x parser produces identical results from short tag and reference tag files."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from parser.onix_parser import parse_onix3
from parser.models import Book, Feed


def test_short_returns_feed_and_books(onix3_shorttags_path: str) -> None:
    feed, books = parse_onix3(onix3_shorttags_path)
    assert isinstance(feed, Feed)
    assert len(books) == 2


def test_short_feed_sender(onix3_shorttags_path: str) -> None:
    feed, _ = parse_onix3(onix3_shorttags_path)
    assert feed.sender_name == "Test Publisher"
    assert feed.sender_email == "feed@testpublisher.com"


def test_short_book1_isbn(onix3_shorttags_path: str) -> None:
    _, books = parse_onix3(onix3_shorttags_path)
    book1 = next(b for b in books if b.record_reference == "TEST-BOOK-001")
    assert book1.isbn13 == "9780000000001"


def test_short_book1_notification_type(onix3_shorttags_path: str) -> None:
    _, books = parse_onix3(onix3_shorttags_path)
    book1 = next(b for b in books if b.record_reference == "TEST-BOOK-001")
    assert book1.notification_type_code == "03"


def test_short_book1_title(onix3_shorttags_path: str) -> None:
    _, books = parse_onix3(onix3_shorttags_path)
    book1 = next(b for b in books if b.record_reference == "TEST-BOOK-001")
    assert book1.title == "The Great Test Book"


def test_short_book1_subtitle(onix3_shorttags_path: str) -> None:
    _, books = parse_onix3(onix3_shorttags_path)
    book1 = next(b for b in books if b.record_reference == "TEST-BOOK-001")
    assert book1.subtitle == "A Complete Guide to Testing"


def test_short_book1_contributor(onix3_shorttags_path: str) -> None:
    _, books = parse_onix3(onix3_shorttags_path)
    book1 = next(b for b in books if b.record_reference == "TEST-BOOK-001")
    assert len(book1.contributors) == 1
    c = book1.contributors[0]
    assert c.role_code == "A01"
    assert c.names_before_key == "Jane"
    assert c.key_names == "Smith"
    assert c.inverted_name == "Smith, Jane"
    assert c.biographical_note == "Jane Smith is a test author."


def test_short_book1_subject(onix3_shorttags_path: str) -> None:
    _, books = parse_onix3(onix3_shorttags_path)
    book1 = next(b for b in books if b.record_reference == "TEST-BOOK-001")
    assert len(book1.subjects) == 1
    assert book1.subjects[0].is_main_subject is True
    assert book1.subjects[0].scheme_code == "10"
    assert book1.subjects[0].subject_code == "FIC000000"


def test_short_book1_language(onix3_shorttags_path: str) -> None:
    _, books = parse_onix3(onix3_shorttags_path)
    book1 = next(b for b in books if b.record_reference == "TEST-BOOK-001")
    assert book1.language_code == "eng"


def test_short_book1_page_count(onix3_shorttags_path: str) -> None:
    _, books = parse_onix3(onix3_shorttags_path)
    book1 = next(b for b in books if b.record_reference == "TEST-BOOK-001")
    assert book1.page_count == 320


def test_short_book1_description(onix3_shorttags_path: str) -> None:
    _, books = parse_onix3(onix3_shorttags_path)
    book1 = next(b for b in books if b.record_reference == "TEST-BOOK-001")
    assert book1.description is not None
    assert "test book" in book1.description.lower()


def test_short_book1_cover_url(onix3_shorttags_path: str) -> None:
    _, books = parse_onix3(onix3_shorttags_path)
    book1 = next(b for b in books if b.record_reference == "TEST-BOOK-001")
    assert book1.cover_url == "https://example.com/covers/9780000000001.jpg"


def test_short_book1_publisher(onix3_shorttags_path: str) -> None:
    _, books = parse_onix3(onix3_shorttags_path)
    book1 = next(b for b in books if b.record_reference == "TEST-BOOK-001")
    assert book1.publisher_name == "Test Publishing House"


def test_short_book1_price(onix3_shorttags_path: str) -> None:
    _, books = parse_onix3(onix3_shorttags_path)
    book1 = next(b for b in books if b.record_reference == "TEST-BOOK-001")
    assert len(book1.prices) == 1
    assert book1.prices[0].price_amount == pytest.approx(24.99)
    assert book1.prices[0].currency_code == "USD"


def test_short_book1_blocks_present(onix3_shorttags_path: str) -> None:
    _, books = parse_onix3(onix3_shorttags_path)
    book1 = next(b for b in books if b.record_reference == "TEST-BOOK-001")
    assert "DescriptiveDetail" in book1.blocks_present
    assert "CollateralDetail" in book1.blocks_present
    assert "PublishingDetail" in book1.blocks_present
    assert "ProductSupply" in book1.blocks_present


def test_short_book2_minimal(onix3_shorttags_path: str) -> None:
    _, books = parse_onix3(onix3_shorttags_path)
    book2 = next(b for b in books if b.record_reference == "TEST-BOOK-002")
    assert book2.isbn13 == "9780000000002"
    assert book2.title == "Minimal Test Book"
    assert book2.contributors == []
    assert book2.prices == []
    assert book2.subjects == []


def test_short_and_reference_produce_same_isbn(
    onix3_path: str, onix3_shorttags_path: str
) -> None:
    """Smoke test: same book, both formats → same ISBN."""
    _, ref_books = parse_onix3(onix3_path)
    _, short_books = parse_onix3(onix3_shorttags_path)
    ref_isbns = {b.isbn13 for b in ref_books}
    short_isbns = {b.isbn13 for b in short_books}
    assert ref_isbns == short_isbns
