import json
import os
from typing import Optional

import psycopg2.extensions

from parser.models import Book, Contributor, Feed, Price, Subject


def upsert_feed(feed: Feed, conn: psycopg2.extensions.connection) -> int:
    """Inserts a feed record and returns the new feed_id."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO feeds (source_file, onix_version, sender_name, sender_email, sent_at, source_type)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                feed.source_file,
                feed.onix_version,
                feed.sender_name,
                feed.sender_email,
                feed.sent_at,
                feed.source_type,
            ),
        )
        row = cur.fetchone()
        conn.commit()
        return row[0]


def upsert_book(book: Book, feed_id: int, conn: psycopg2.extensions.connection) -> int:
    """Upserts a full book record and returns book_id."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO books (
                feed_id, record_reference, notification_type_code,
                isbn13, isbn10, gtin13, identifiers,
                title, subtitle, full_title, series_name, series_number,
                product_form_code, product_form, edition_number, edition_statement, no_edition,
                publisher_name, imprint_name, city_of_publication,
                country_of_publication, country_of_manufacture,
                publishing_status_code, publishing_status, publication_date,
                availability_code, availability,
                page_count, height_mm, width_mm, thickness_mm, weight_g,
                cover_url, short_description, description,
                language_code, original_language_code, audience_code, trade_category_code,
                rights_countries_included, rights_countries_excluded, rights_regions,
                languages, texts, media, related,
                updated_at
            ) VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s, NOW()
            )
            ON CONFLICT (record_reference) DO UPDATE SET
                feed_id=EXCLUDED.feed_id,
                notification_type_code=EXCLUDED.notification_type_code,
                isbn13=EXCLUDED.isbn13,
                isbn10=EXCLUDED.isbn10,
                gtin13=EXCLUDED.gtin13,
                identifiers=EXCLUDED.identifiers,
                title=EXCLUDED.title,
                subtitle=EXCLUDED.subtitle,
                full_title=EXCLUDED.full_title,
                series_name=EXCLUDED.series_name,
                series_number=EXCLUDED.series_number,
                product_form_code=EXCLUDED.product_form_code,
                product_form=EXCLUDED.product_form,
                edition_number=EXCLUDED.edition_number,
                edition_statement=EXCLUDED.edition_statement,
                no_edition=EXCLUDED.no_edition,
                publisher_name=EXCLUDED.publisher_name,
                imprint_name=EXCLUDED.imprint_name,
                city_of_publication=EXCLUDED.city_of_publication,
                country_of_publication=EXCLUDED.country_of_publication,
                country_of_manufacture=EXCLUDED.country_of_manufacture,
                publishing_status_code=EXCLUDED.publishing_status_code,
                publishing_status=EXCLUDED.publishing_status,
                publication_date=EXCLUDED.publication_date,
                availability_code=EXCLUDED.availability_code,
                availability=EXCLUDED.availability,
                page_count=EXCLUDED.page_count,
                height_mm=EXCLUDED.height_mm,
                width_mm=EXCLUDED.width_mm,
                thickness_mm=EXCLUDED.thickness_mm,
                weight_g=EXCLUDED.weight_g,
                cover_url=EXCLUDED.cover_url,
                short_description=EXCLUDED.short_description,
                description=EXCLUDED.description,
                language_code=EXCLUDED.language_code,
                original_language_code=EXCLUDED.original_language_code,
                audience_code=EXCLUDED.audience_code,
                trade_category_code=EXCLUDED.trade_category_code,
                rights_countries_included=EXCLUDED.rights_countries_included,
                rights_countries_excluded=EXCLUDED.rights_countries_excluded,
                rights_regions=EXCLUDED.rights_regions,
                languages=EXCLUDED.languages,
                texts=EXCLUDED.texts,
                media=EXCLUDED.media,
                related=EXCLUDED.related,
                updated_at=NOW()
            RETURNING id
            """,
            (
                feed_id,
                book.record_reference,
                book.notification_type_code,
                book.isbn13,
                book.isbn10,
                book.gtin13,
                json.dumps(book.identifiers),
                book.title,
                book.subtitle,
                book.full_title,
                book.series_name,
                book.series_number,
                book.product_form_code,
                book.product_form,
                book.edition_number,
                book.edition_statement,
                book.no_edition,
                book.publisher_name,
                book.imprint_name,
                book.city_of_publication,
                book.country_of_publication,
                book.country_of_manufacture,
                book.publishing_status_code,
                book.publishing_status,
                book.publication_date,
                book.availability_code,
                book.availability,
                book.page_count,
                book.height_mm,
                book.width_mm,
                book.thickness_mm,
                book.weight_g,
                book.cover_url,
                book.short_description,
                book.description,
                book.language_code,
                book.original_language_code,
                book.audience_code,
                book.trade_category_code,
                book.rights_countries_included,
                book.rights_countries_excluded,
                book.rights_regions,
                json.dumps(book.languages),
                json.dumps(book.texts),
                json.dumps(book.media),
                json.dumps(book.related),
            ),
        )
        row = cur.fetchone()
        book_id = row[0]

        _upsert_contributors(book_id, book.contributors, cur)
        _upsert_subjects(book_id, book.subjects, cur)
        _upsert_prices(book_id, book.prices, cur)

        conn.commit()

    enqueue_push(book_id, book.notification_type_code, conn)
    return book_id


def block_update(book: Book, conn: psycopg2.extensions.connection) -> int:
    """Applies a partial block update to an existing book. Returns book_id."""
    with conn.cursor() as cur:
        # Find existing book
        cur.execute(
            "SELECT id FROM books WHERE record_reference=%s", (book.record_reference,)
        )
        row = cur.fetchone()
        if row is None and book.isbn13:
            cur.execute("SELECT id FROM books WHERE isbn13=%s", (book.isbn13,))
            row = cur.fetchone()
        if row is None:
            raise ValueError(
                f"block_update: no existing book for record_reference={book.record_reference}"
            )
        book_id = row[0]

        for block in book.blocks_present:
            if block == "DescriptiveDetail":
                cur.execute(
                    """
                    UPDATE books SET
                        title=%s, subtitle=%s, full_title=%s,
                        series_name=%s, series_number=%s,
                        product_form_code=%s, product_form=%s,
                        edition_number=%s, edition_statement=%s, no_edition=%s,
                        country_of_manufacture=%s,
                        page_count=%s, height_mm=%s, width_mm=%s, thickness_mm=%s, weight_g=%s,
                        language_code=%s, original_language_code=%s,
                        audience_code=%s,
                        languages=%s, identifiers=%s,
                        updated_at=NOW()
                    WHERE id=%s
                    """,
                    (
                        book.title,
                        book.subtitle,
                        book.full_title,
                        book.series_name,
                        book.series_number,
                        book.product_form_code,
                        book.product_form,
                        book.edition_number,
                        book.edition_statement,
                        book.no_edition,
                        book.country_of_manufacture,
                        book.page_count,
                        book.height_mm,
                        book.width_mm,
                        book.thickness_mm,
                        book.weight_g,
                        book.language_code,
                        book.original_language_code,
                        book.audience_code,
                        json.dumps(book.languages),
                        json.dumps(book.identifiers),
                        book_id,
                    ),
                )
                _upsert_contributors(book_id, book.contributors, cur)
                _upsert_subjects(book_id, book.subjects, cur)

            elif block == "CollateralDetail":
                cur.execute(
                    """
                    UPDATE books SET
                        cover_url=%s, short_description=%s, description=%s,
                        texts=%s, media=%s,
                        updated_at=NOW()
                    WHERE id=%s
                    """,
                    (
                        book.cover_url,
                        book.short_description,
                        book.description,
                        json.dumps(book.texts),
                        json.dumps(book.media),
                        book_id,
                    ),
                )

            elif block == "PublishingDetail":
                cur.execute(
                    """
                    UPDATE books SET
                        publisher_name=%s, imprint_name=%s,
                        city_of_publication=%s, country_of_publication=%s,
                        publishing_status_code=%s, publishing_status=%s,
                        publication_date=%s,
                        rights_countries_included=%s, rights_countries_excluded=%s,
                        rights_regions=%s,
                        updated_at=NOW()
                    WHERE id=%s
                    """,
                    (
                        book.publisher_name,
                        book.imprint_name,
                        book.city_of_publication,
                        book.country_of_publication,
                        book.publishing_status_code,
                        book.publishing_status,
                        book.publication_date,
                        book.rights_countries_included,
                        book.rights_countries_excluded,
                        book.rights_regions,
                        book_id,
                    ),
                )

            elif block == "ProductSupply":
                cur.execute("DELETE FROM book_prices WHERE book_id=%s", (book_id,))
                _upsert_prices(book_id, book.prices, cur)
                if book.availability_code:
                    cur.execute(
                        "UPDATE books SET availability_code=%s, availability=%s, updated_at=NOW() WHERE id=%s",
                        (book.availability_code, book.availability, book_id),
                    )

        # Always touch updated_at even if no blocks matched
        cur.execute("UPDATE books SET updated_at=NOW() WHERE id=%s", (book_id,))
        conn.commit()

    enqueue_push(book_id, book.notification_type_code, conn)
    return book_id


def enqueue_push(
    book_id: int,
    notification_type_code: Optional[str],
    conn: psycopg2.extensions.connection,
) -> None:
    """Enqueues book for push to configured targets based on smart push logic."""
    if notification_type_code == "05":
        return

    targets_env = os.environ.get("PUSH_TARGETS", "")
    targets = [t.strip() for t in targets_env.split(",") if t.strip()]
    if not targets:
        return

    with conn.cursor() as cur:
        for target in targets:
            if notification_type_code == "04":
                # Block update: always enqueue
                cur.execute(
                    """
                    INSERT INTO push_queue (book_id, target, status)
                    VALUES (%s, %s, 'pending')
                    """,
                    (book_id, target),
                )
            else:
                # New/advance/confirmed: only if no pending/sent entry exists
                cur.execute(
                    """
                    SELECT 1 FROM push_queue
                    WHERE book_id=%s AND target=%s AND status IN ('pending','sent')
                    """,
                    (book_id, target),
                )
                if cur.fetchone() is None:
                    cur.execute(
                        """
                        INSERT INTO push_queue (book_id, target, status)
                        VALUES (%s, %s, 'pending')
                        """,
                        (book_id, target),
                    )
        conn.commit()


def _upsert_contributors(
    book_id: int,
    contributors: list[Contributor],
    cur: psycopg2.extensions.cursor,
) -> None:
    cur.execute("DELETE FROM book_contributors WHERE book_id=%s", (book_id,))
    for c in contributors:
        cur.execute(
            """
            INSERT INTO book_contributors (
                book_id, sequence_number, role_code, role,
                names_before_key, key_names, display_name, inverted_name,
                from_language_code, biographical_note, bio_textformat,
                contributor_id_type, contributor_id_value
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                book_id,
                c.sequence_number,
                c.role_code,
                c.role,
                c.names_before_key,
                c.key_names,
                c.display_name,
                c.inverted_name,
                c.from_language_code,
                c.biographical_note,
                c.bio_textformat,
                c.contributor_id_type,
                c.contributor_id_value,
            ),
        )


def _upsert_subjects(
    book_id: int,
    subjects: list[Subject],
    cur: psycopg2.extensions.cursor,
) -> None:
    cur.execute("DELETE FROM book_subjects WHERE book_id=%s", (book_id,))
    for s in subjects:
        cur.execute(
            """
            INSERT INTO book_subjects (
                book_id, is_main_subject, scheme_code, scheme_name,
                scheme_version, subject_code, subject_heading_text
            ) VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                book_id,
                s.is_main_subject,
                s.scheme_code,
                s.scheme_name,
                s.scheme_version,
                s.subject_code,
                s.subject_heading_text,
            ),
        )


def _upsert_prices(
    book_id: int,
    prices: list[Price],
    cur: psycopg2.extensions.cursor,
) -> None:
    cur.execute("DELETE FROM book_prices WHERE book_id=%s", (book_id,))
    for p in prices:
        cur.execute(
            """
            INSERT INTO book_prices (
                book_id,
                supplier_name, supplier_role_code,
                availability_code, availability,
                price_type_code, price_status_code,
                price_amount, currency_code,
                countries_included, countries_excluded, regions_included,
                discount_code_type_code, discount_code, discount_percent,
                tax_type_code, tax_rate_code, tax_rate_percent,
                taxable_amount, tax_amount,
                market_reference, market_publishing_status_code, market_date
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                book_id,
                p.supplier_name,
                p.supplier_role_code,
                p.availability_code,
                p.availability,
                p.price_type_code,
                p.price_status_code,
                p.price_amount,
                p.currency_code,
                p.countries_included,
                p.countries_excluded,
                p.regions_included,
                p.discount_code_type_code,
                p.discount_code,
                p.discount_percent,
                p.tax_type_code,
                p.tax_rate_code,
                p.tax_rate_percent,
                p.taxable_amount,
                p.tax_amount,
                p.market_reference,
                p.market_publishing_status_code,
                p.market_date,
            ),
        )
