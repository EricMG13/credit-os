"""Threads: one test per hand mutant that survived the sweep (S-7 fix 2, sweep b3 and c7).

Limits are pinned by literals (title 120, 500 comments), not read from the module. Expected
values are written by hand; the code under test is reached through its public functions.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from threads_support import AK, MIN, ML, T0, rows, team_db

from credit_os.signal.groups import Act, create_group
from credit_os.signal.identity import cleaned, cleaned_text
from credit_os.signal.store import StoreError
from credit_os.signal.threads import (
    add_comment,
    auto_post,
    edit_comment,
    read_thread,
    share_story,
    start_note,
)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    handle = team_db(tmp_path)
    yield handle
    handle.close()


def test_the_view_names_the_threads_group_not_the_threads_own_id(db: sqlite3.Connection) -> None:
    create_group(db, Act(AK, T0), "first", "everyone", [])
    second = create_group(db, Act(AK, T0), "second", "everyone", [])
    tid, _ = share_story(db, Act(AK, T0), second, 1, None)
    assert (tid, second) == (1, 2)
    assert read_thread(db, AK, tid, T0).group_id == 2


def test_a_reply_shows_its_parent_and_an_edited_comment_keeps_its_creation_time(
    db: sqlite3.Connection,
) -> None:
    gid = create_group(db, Act(AK, T0), "G", "everyone", [])
    tid, _ = share_story(db, Act(AK, T0), gid, 1, None)
    parent = add_comment(db, Act(AK, T0 + MIN), tid, "p", None)
    reply = add_comment(db, Act(ML, T0 + 2 * MIN), tid, "r", parent)
    edit_comment(db, Act(AK, T0 + 4 * MIN), parent, "p edited")
    by_id = {c.id: c for c in read_thread(db, AK, tid, T0 + 5 * MIN).comments}
    assert by_id[reply].parent_id == parent
    assert by_id[parent].parent_id is None
    assert by_id[parent].created_at == "2026-11-13T09:01:00+00:00"
    assert by_id[parent].edited


def test_two_comments_by_one_author_both_show_that_authors_role(db: sqlite3.Connection) -> None:
    gid = create_group(db, Act(AK, T0), "G", "everyone", [])
    tid, _ = share_story(db, Act(AK, T0), gid, 1, None)
    add_comment(db, Act(AK, T0 + MIN), tid, "one", None)
    add_comment(db, Act(AK, T0 + 2 * MIN), tid, "two", None)
    add_comment(db, Act(ML, T0 + 3 * MIN), tid, "three", None)
    view = read_thread(db, AK, tid, T0 + 4 * MIN)
    assert [(c.author, c.role) for c in view.comments] == [
        ("ak", "writer"),
        ("ak", "writer"),
        ("ml", "writer"),
    ]


def test_a_title_of_120_characters_is_kept_and_one_of_121_is_refused(
    db: sqlite3.Connection,
) -> None:
    gid = create_group(db, Act(AK, T0), "G", "everyone", [])
    start_note(db, Act(AK, T0), gid, "t" * 120, "b")
    with pytest.raises(StoreError, match="^text is longer than 120 characters$"):
        start_note(db, Act(AK, T0), gid, "t" * 121, "b")
    assert rows(db, "SELECT length(title) FROM threads") == [(120,)]


def test_the_500th_comment_is_stored_and_the_501st_is_refused(db: sqlite3.Connection) -> None:
    gid = create_group(db, Act(AK, T0), "G", "everyone", [])
    tid, _ = share_story(db, Act(AK, T0), gid, 1, None)
    db.executemany(
        "INSERT INTO comments(thread_id, author, text, created_at) VALUES(?, 'ak', 'c', ?)",
        [(tid, "2026-11-13T09:00:00+00:00")] * 499,
    )
    db.commit()
    add_comment(db, Act(AK, T0 + MIN), tid, "the 500th", None)
    with pytest.raises(StoreError, match="^this thread is full$"):
        add_comment(db, Act(AK, T0 + 2 * MIN), tid, "the 501st", None)
    assert rows(db, "SELECT count(*) FROM comments") == [(500,)]


def test_an_automatic_thread_is_stamped_with_the_time_it_was_posted(
    db: sqlite3.Connection,
) -> None:
    gid = create_group(db, Act(AK, T0), "G", "everyone", [])
    db.execute(
        "INSERT INTO topics(id, name, keywords, kinds, created_by, created_at)"
        " VALUES(1, 'x', '[]', '[]', 'ak', 'now')"
    )
    db.execute("INSERT INTO group_topics(group_id, topic_id) VALUES(?, 1)", (gid,))
    db.commit()
    assert auto_post(db, 1, [1], T0 + 7 * MIN) == [1]
    assert rows(db, "SELECT created_at, last_activity_at FROM threads") == [
        ("2026-11-13T09:07:00+00:00", "2026-11-13T09:07:00+00:00")
    ]


def test_marks_are_normalised_before_runs_of_them_are_cut() -> None:
    """An e, an acute accent and 8 low marks make 9 marks before NFC and 8 after it (the e and
    the accent fuse). Cutting runs before NFC would keep only 8 of the 9 and lose one more."""
    raw = "e\u0301" + "\u0316" * 8
    assert cleaned_text(raw, multiline=True) == "\u00e9" + "\u0316" * 8
    assert cleaned_text(raw, multiline=False) == "\u00e9" + "\u0316" * 8
    assert cleaned(raw) == "\u00e9" + "\u0316" * 8
