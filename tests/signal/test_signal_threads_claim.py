"""A share that claims an automatic thread is activity (R56 sweep c1): the thread sorts where new
activity sorts. Expected values are written by hand."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from threads_support import AK, MIN, ML, T0, rows, team_db

from credit_os.signal.groups import Act, create_group
from credit_os.signal.identity import User
from credit_os.signal.store import open_db
from credit_os.signal.threads import (
    auto_post,
    share_story,
    start_note,
    thread_list,
    unread,
)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    handle = team_db(tmp_path)
    yield handle
    handle.close()


def _group_with_auto_thread(db: sqlite3.Connection) -> int:
    gid = create_group(db, Act(ML, T0), "TMT", "everyone", [])
    db.execute(
        "INSERT INTO topics(id, name, keywords, kinds, created_by, created_at)"
        " VALUES(1, 'x', '[]', '[]', 'ak', 'now')"
    )
    db.execute("INSERT INTO group_topics(group_id, topic_id) VALUES(?, 1)", (gid,))
    db.commit()
    assert auto_post(db, 1, [1], T0 + MIN) == [1]  # thread 1, activity at minute 1
    return gid


def _activity(db: sqlite3.Connection) -> list[tuple[str, str]]:
    sql = "SELECT created_at, last_activity_at FROM threads ORDER BY id"
    return [(r[0], r[1]) for r in rows(db, sql)]


def test_a_claim_without_a_note_moves_the_thread_to_the_top_of_the_list(
    db: sqlite3.Connection,
) -> None:
    gid = _group_with_auto_thread(db)
    for k in range(35):  # ml's own notes, minutes 10..44: the auto thread would be on page 2
        start_note(db, Act(ML, T0 + (10 + k) * MIN), gid, f"n{k}", "b")
    share_story(db, Act(AK, T0 + 60 * MIN), gid, 1, None)
    page, _ = thread_list(db, "ml", gid, None)
    assert page[0].id == 1 and page[0].unread
    assert unread(db, "ml").threads == 1
    assert _activity(db)[0] == ("2026-11-13T10:00:00+00:00", "2026-11-13T10:00:00+00:00")


def test_a_claim_with_a_note_leaves_the_same_activity_time(db: sqlite3.Connection) -> None:
    gid = _group_with_auto_thread(db)
    share_story(db, Act(AK, T0 + 5 * MIN), gid, 1, "noted")
    assert _activity(db) == [("2026-11-13T09:05:00+00:00", "2026-11-13T09:05:00+00:00")]


def test_a_claim_never_moves_the_activity_time_back(db: sqlite3.Connection) -> None:
    gid = _group_with_auto_thread(db)
    db.execute("UPDATE threads SET last_activity_at='2026-11-13T12:00:00+00:00' WHERE id=1")
    db.commit()
    share_story(db, Act(AK, T0 + 5 * MIN), gid, 1, None)
    assert _activity(db) == [("2026-11-13T09:05:00+00:00", "2026-11-13T12:00:00+00:00")]


def test_two_connections_claiming_at_once_leave_one_claimer_and_one_stamp(
    db: sqlite3.Connection, tmp_path: Path
) -> None:
    gid = _group_with_auto_thread(db)
    barrier = threading.Barrier(2)
    seen: list[tuple[int, bool]] = []

    def worker(user: User, minute: int) -> None:
        conn = open_db(tmp_path)
        try:
            barrier.wait()
            seen.append(share_story(conn, Act(user, T0 + minute * MIN), gid, 1, None))
        finally:
            conn.close()

    workers = [
        threading.Thread(target=worker, args=(AK, 5)),
        threading.Thread(target=worker, args=(ML, 7)),
    ]
    for w in workers:
        w.start()
    for w in workers:
        w.join()
    assert seen == [(1, True), (1, True)]
    ((claimer, created, last),) = rows(
        db, "SELECT started_by, created_at, last_activity_at FROM threads"
    )
    stamp = {"ak": "2026-11-13T09:05:00+00:00", "ml": "2026-11-13T09:07:00+00:00"}[claimer]
    assert (created, last) == (stamp, stamp)
