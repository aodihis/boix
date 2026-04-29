import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import ONIX XML file into PostgreSQL")
    parser.add_argument("--file", required=True, help="Path to ONIX XML file")
    parser.add_argument(
        "--push",
        choices=["filemaker", "craftcms", "all", "none"],
        default="none",
        help="Push targets to activate (overrides PUSH_TARGETS env var)",
    )
    args = parser.parse_args()

    if args.push != "none":
        if args.push == "all":
            os.environ["PUSH_TARGETS"] = "filemaker,craftcms"
        else:
            os.environ["PUSH_TARGETS"] = args.push

    from parser.detect import detect_onix_version
    from parser.onix_parser import parse_onix3
    from parser.onix2_parser import parse_onix2
    from db.connection import get_connection
    from db.importer import upsert_feed, upsert_book, block_update

    version = detect_onix_version(args.file)
    print(f"Detected ONIX version: {version}")

    if version == "2.1":
        feed, books = parse_onix2(args.file)
    else:
        feed, books = parse_onix3(args.file)

    print(f"Parsed {len(books)} book(s) from {args.file}")

    conn = get_connection()
    try:
        feed_id = upsert_feed(feed, conn)
        upserted = 0
        enqueued = 0

        for book in books:
            if book.notification_type_code == "04":
                book_id = block_update(book, conn)
            else:
                book_id = upsert_book(book, feed_id, conn)
            upserted += 1
            # Count push queue entries added for this book
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM push_queue WHERE book_id=%s AND status='pending'",
                    (book_id,),
                )
                row = cur.fetchone()
                if row and row[0]:
                    enqueued += 1

        print(f"Done: {upserted} book(s) upserted, {enqueued} enqueued for push")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
