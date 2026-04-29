import os

from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

load_dotenv()


def drain_push_queue(target: str, config: dict) -> None:
    from db.connection import get_connection
    from pushers.filemaker import push_book_to_filemaker
    from pushers.craftcms import push_book_to_craft

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, book_id, attempts FROM push_queue
                WHERE status='pending' AND target=%s
                ORDER BY created_at
                LIMIT 50
                """,
                (target,),
            )
            rows = cur.fetchall()

        for queue_id, book_id, attempts in rows:
            try:
                if target == "filemaker":
                    push_book_to_filemaker(book_id, conn, config)
                elif target == "craftcms":
                    push_book_to_craft(book_id, conn, config)

                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE push_queue SET status='sent', sent_at=NOW(), last_attempted=NOW() WHERE id=%s",
                        (queue_id,),
                    )
                conn.commit()
                print(f"[scheduler] pushed book_id={book_id} to {target}")

            except Exception as exc:
                new_attempts = attempts + 1
                with conn.cursor() as cur:
                    if new_attempts >= 3:
                        cur.execute(
                            """
                            UPDATE push_queue
                            SET status='failed', attempts=%s, last_attempted=NOW(), error_message=%s
                            WHERE id=%s
                            """,
                            (new_attempts, str(exc), queue_id),
                        )
                        print(f"[scheduler] FAILED (max attempts) book_id={book_id} target={target}: {exc}")
                    else:
                        cur.execute(
                            """
                            UPDATE push_queue
                            SET status='failed', attempts=%s, last_attempted=NOW(), error_message=%s
                            WHERE id=%s
                            """,
                            (new_attempts, str(exc), queue_id),
                        )
                        print(f"[scheduler] failed attempt {new_attempts} book_id={book_id} target={target}: {exc}")
                conn.commit()
    finally:
        conn.close()


def main() -> None:
    interval_seconds = int(os.environ.get("PUSH_INTERVAL_SECONDS", "300"))
    targets_env = os.environ.get("PUSH_TARGETS", "")
    targets = [t.strip() for t in targets_env.split(",") if t.strip()]

    config = {
        "USE_STUBS": os.environ.get("USE_STUBS", "false"),
        "FM_STUB_PORT": os.environ.get("FM_STUB_PORT", "5001"),
        "CRAFT_STUB_PORT": os.environ.get("CRAFT_STUB_PORT", "5002"),
        "FILEMAKER_BASE_URL": os.environ.get("FILEMAKER_BASE_URL", ""),
        "FILEMAKER_DB": os.environ.get("FILEMAKER_DB", ""),
        "FILEMAKER_LAYOUT": os.environ.get("FILEMAKER_LAYOUT", ""),
        "FILEMAKER_USER": os.environ.get("FILEMAKER_USER", ""),
        "FILEMAKER_PASSWORD": os.environ.get("FILEMAKER_PASSWORD", ""),
        "CRAFTCMS_BASE_URL": os.environ.get("CRAFTCMS_BASE_URL", ""),
        "CRAFTCMS_TOKEN": os.environ.get("CRAFTCMS_TOKEN", ""),
    }

    scheduler = BlockingScheduler()

    for target in targets:
        scheduler.add_job(
            drain_push_queue,
            "interval",
            seconds=interval_seconds,
            args=[target, config],
            id=f"drain_{target}",
        )
        print(f"[scheduler] scheduled drain for target={target} every {interval_seconds}s")

    scheduler.start()


if __name__ == "__main__":
    main()
