import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.importer import enqueue_push


def _make_conn(fetchone_result=None) -> MagicMock:
    """Returns a mock psycopg2 connection whose cursor fetchone returns the given value."""
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    cur.fetchone = MagicMock(return_value=fetchone_result)
    conn = MagicMock()
    conn.cursor = MagicMock(return_value=cur)
    return conn, cur


def test_enqueue_skips_if_already_pending() -> None:
    with patch.dict(os.environ, {"PUSH_TARGETS": "filemaker"}):
        # fetchone returns a row → book already pending
        conn, cur = _make_conn(fetchone_result=(1,))
        enqueue_push(1, "03", conn)
        # INSERT should NOT have been called
        insert_calls = [c for c in cur.execute.call_args_list if "INSERT" in str(c)]
        assert len(insert_calls) == 0


def test_enqueue_inserts_for_new_book() -> None:
    with patch.dict(os.environ, {"PUSH_TARGETS": "filemaker"}):
        # fetchone returns None → not yet in queue
        conn, cur = _make_conn(fetchone_result=None)
        enqueue_push(1, "03", conn)
        insert_calls = [c for c in cur.execute.call_args_list if "INSERT" in str(c)]
        assert len(insert_calls) == 1


def test_block_update_always_enqueues() -> None:
    with patch.dict(os.environ, {"PUSH_TARGETS": "filemaker"}):
        # notification_type 04 must insert regardless — no SELECT check
        conn, cur = _make_conn(fetchone_result=(1,))
        enqueue_push(2, "04", conn)
        insert_calls = [c for c in cur.execute.call_args_list if "INSERT" in str(c)]
        assert len(insert_calls) == 1


def test_deleted_notification_skips_enqueue() -> None:
    with patch.dict(os.environ, {"PUSH_TARGETS": "filemaker"}):
        conn, cur = _make_conn(fetchone_result=None)
        enqueue_push(3, "05", conn)
        # No INSERT, no SELECT — early return
        assert cur.execute.call_count == 0


def test_enqueue_multiple_targets() -> None:
    with patch.dict(os.environ, {"PUSH_TARGETS": "filemaker,craftcms"}):
        conn, cur = _make_conn(fetchone_result=None)
        enqueue_push(4, "03", conn)
        insert_calls = [c for c in cur.execute.call_args_list if "INSERT" in str(c)]
        assert len(insert_calls) == 2


def test_enqueue_no_targets_does_nothing() -> None:
    with patch.dict(os.environ, {"PUSH_TARGETS": ""}):
        conn, cur = _make_conn(fetchone_result=None)
        enqueue_push(5, "03", conn)
        assert cur.execute.call_count == 0


def test_failed_status_does_not_block_reenqueue() -> None:
    # A 'failed' row must not prevent re-enqueue — the SELECT only checks pending/sent
    with patch.dict(os.environ, {"PUSH_TARGETS": "filemaker"}):
        # fetchone returns None (no pending/sent row, only a failed one)
        conn, cur = _make_conn(fetchone_result=None)
        enqueue_push(6, "03", conn)
        insert_calls = [c for c in cur.execute.call_args_list if "INSERT" in str(c)]
        assert len(insert_calls) == 1
