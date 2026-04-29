import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from parser.onix_parser import parse_onix3
from parser.models import Book, Feed


def test_parse_onix3_returns_feed_and_books(onix3_path: str) -> None:
    feed, books = parse_onix3(onix3_path)
    assert isinstance(feed, Feed)
    assert isinstance(books, list)
    assert len(books) == 2


def test_feed_onix_version(onix3_path: str) -> None:
    feed, _ = parse_onix3(onix3_path)
    assert feed.onix_version in ("3.0", "3.1")


def test_feed_sender_info(onix3_path: str) -> None:
    feed, _ = parse_onix3(onix3_path)
    assert feed.sender_name == "Test Publisher"
    assert feed.sender_email == "feed@testpublisher.com"


def test_book1_isbn(onix3_path: str) -> None:
    _, books = parse_onix3(onix3_path)
    book1 = next(b for b in books if b.record_reference == "TEST-BOOK-001")
    assert book1.isbn13 == "9780000000001"


def test_book1_notification_type(onix3_path: str) -> None:
    _, books = parse_onix3(onix3_path)
    book1 = next(b for b in books if b.record_reference == "TEST-BOOK-001")
    assert book1.notification_type_code == "03"


def test_book1_title(onix3_path: str) -> None:
    _, books = parse_onix3(onix3_path)
    book1 = next(b for b in books if b.record_reference == "TEST-BOOK-001")
    assert book1.title is not None
    assert "Test Book" in book1.title


def test_book1_has_contributor(onix3_path: str) -> None:
    _, books = parse_onix3(onix3_path)
    book1 = next(b for b in books if b.record_reference == "TEST-BOOK-001")
    assert len(book1.contributors) >= 1
    assert book1.contributors[0].role_code == "A01"


def test_book1_has_subject(onix3_path: str) -> None:
    _, books = parse_onix3(onix3_path)
    book1 = next(b for b in books if b.record_reference == "TEST-BOOK-001")
    assert len(book1.subjects) >= 1
    assert book1.subjects[0].scheme_code == "10"


def test_book1_has_price(onix3_path: str) -> None:
    _, books = parse_onix3(onix3_path)
    book1 = next(b for b in books if b.record_reference == "TEST-BOOK-001")
    assert len(book1.prices) >= 1
    assert book1.prices[0].currency_code == "USD"
    assert book1.prices[0].price_amount == pytest.approx(24.99)


def test_book1_publisher(onix3_path: str) -> None:
    _, books = parse_onix3(onix3_path)
    book1 = next(b for b in books if b.record_reference == "TEST-BOOK-001")
    assert book1.publisher_name == "Test Publishing House"


def test_book1_cover_url(onix3_path: str) -> None:
    _, books = parse_onix3(onix3_path)
    book1 = next(b for b in books if b.record_reference == "TEST-BOOK-001")
    assert book1.cover_url is not None
    assert "9780000000001" in book1.cover_url


def test_book1_description(onix3_path: str) -> None:
    _, books = parse_onix3(onix3_path)
    book1 = next(b for b in books if b.record_reference == "TEST-BOOK-001")
    assert book1.description is not None


def test_book1_blocks_present(onix3_path: str) -> None:
    _, books = parse_onix3(onix3_path)
    book1 = next(b for b in books if b.record_reference == "TEST-BOOK-001")
    assert "DescriptiveDetail" in book1.blocks_present
    assert "ProductSupply" in book1.blocks_present


def test_book2_minimal(onix3_path: str) -> None:
    _, books = parse_onix3(onix3_path)
    book2 = next(b for b in books if b.record_reference == "TEST-BOOK-002")
    assert book2.isbn13 == "9780000000002"
    assert book2.contributors == []
    assert book2.prices == []
    assert book2.subjects == []


def test_block_update_notification_type(onix3_block_update_path: str) -> None:
    _, books = parse_onix3(onix3_block_update_path)
    assert len(books) == 1
    assert books[0].notification_type_code == "04"


def test_block_update_only_product_supply(onix3_block_update_path: str) -> None:
    _, books = parse_onix3(onix3_block_update_path)
    book = books[0]
    assert "ProductSupply" in book.blocks_present
    assert "DescriptiveDetail" not in book.blocks_present
    assert "CollateralDetail" not in book.blocks_present
    assert "PublishingDetail" not in book.blocks_present


def test_block_update_has_new_price(onix3_block_update_path: str) -> None:
    _, books = parse_onix3(onix3_block_update_path)
    book = books[0]
    assert len(book.prices) >= 1
    assert book.prices[0].price_amount == pytest.approx(14.99)
    assert book.prices[0].currency_code == "USD"


def test_block_update_no_title(onix3_block_update_path: str) -> None:
    _, books = parse_onix3(onix3_block_update_path)
    book = books[0]
    assert book.title is None
