from typing import Optional
import psycopg2.extensions


def list_books(
    conn: psycopg2.extensions.connection,
    page: int = 1,
    per_page: int = 20,
    search: str = "",
) -> list[dict]:
    cur = conn.cursor()
    pattern = f"%{search}%" if search else ""
    offset = (page - 1) * per_page

    cur.execute(
        """
        SELECT id, isbn13, title, publisher_name, publication_date,
               product_form_code, product_form,
               publishing_status_code, publishing_status,
               notification_type_code, updated_at
        FROM books
        WHERE (%s = '' OR title ILIKE %s
               OR isbn13 ILIKE %s
               OR publisher_name ILIKE %s)
        ORDER BY updated_at DESC
        LIMIT %s OFFSET %s
        """,
        (search, pattern, pattern, pattern, per_page, offset),
    )

    cols = [col[0] for col in cur.description]
    rows = cur.fetchall()
    cur.close()

    return [dict(zip(cols, row)) for row in rows]


def count_books(conn: psycopg2.extensions.connection, search: str = "") -> int:
    cur = conn.cursor()
    pattern = f"%{search}%" if search else ""

    cur.execute(
        """
        SELECT COUNT(*)
        FROM books
        WHERE (%s = '' OR title ILIKE %s
               OR isbn13 ILIKE %s
               OR publisher_name ILIKE %s)
        """,
        (search, pattern, pattern, pattern),
    )

    count = cur.fetchone()[0]
    cur.close()
    return count


def get_book_detail(
    conn: psycopg2.extensions.connection, book_id: int
) -> Optional[dict]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM books WHERE id = %s", (book_id,))
    cols = [col[0] for col in cur.description]
    row = cur.fetchone()
    cur.close()

    if not row:
        return None

    return dict(zip(cols, row))


def get_book_contributors(
    conn: psycopg2.extensions.connection, book_id: int
) -> list[dict]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM book_contributors
        WHERE book_id = %s
        ORDER BY sequence_number ASC NULLS LAST
        """,
        (book_id,),
    )

    cols = [col[0] for col in cur.description]
    rows = cur.fetchall()
    cur.close()

    return [dict(zip(cols, row)) for row in rows]


def get_book_subjects(
    conn: psycopg2.extensions.connection, book_id: int
) -> list[dict]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM book_subjects
        WHERE book_id = %s
        ORDER BY is_main_subject DESC, scheme_code ASC
        """,
        (book_id,),
    )

    cols = [col[0] for col in cur.description]
    rows = cur.fetchall()
    cur.close()

    return [dict(zip(cols, row)) for row in rows]


def get_book_prices(
    conn: psycopg2.extensions.connection, book_id: int
) -> list[dict]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM book_prices
        WHERE book_id = %s
        ORDER BY currency_code ASC, price_amount ASC
        """,
        (book_id,),
    )

    cols = [col[0] for col in cur.description]
    rows = cur.fetchall()
    cur.close()

    return [dict(zip(cols, row)) for row in rows]


def get_push_status(
    conn: psycopg2.extensions.connection, book_id: int
) -> list[dict]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT target, status, COUNT(*) AS count
        FROM push_queue
        WHERE book_id = %s
        GROUP BY target, status
        ORDER BY target, status
        """,
        (book_id,),
    )

    cols = [col[0] for col in cur.description]
    rows = cur.fetchall()
    cur.close()

    return [dict(zip(cols, row)) for row in rows]
