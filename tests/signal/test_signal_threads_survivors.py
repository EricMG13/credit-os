"""Threads: one behaviour per surviving hand mutant of the task review (S-7 fix round 1).

Each test states, in its docstring or name, the behaviour the mutant breaks. Expected values are
written by hand; the code under test is reached through its public functions only.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from threads_support import AK, MIN, ML, T0, count, rows, team_db

from credit_os.signal import feedview
from credit_os.signal.groups import Act, create_group
from credit_os.signal.store import StoreError, read_snapshot
from credit_os.signal.threads import (
    MAX_TEXT,
    add_comment,
    auto_post,
    delete_comment,
    mark_read,
    react,
    read_thread,
    share_story,
)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    handle = team_db(tmp_path)
    yield handle
    handle.close()


@pytest.fixture
def gid(db: sqlite3.Connection) -> int:
    return create_group(db, Act(AK, T0), "TMT", "everyone", [])


def bad(value: object) -> Any:
    """A value of the wrong type, hidden from the type checker (the callee must refuse it)."""
    return value


def _two_topics(db: sqlite3.Connection) -> None:
    for name in ("one", "two"):
        db.execute(
            "INSERT INTO topics(name, keywords, kinds, created_by, created_at)"
            " VALUES(?, '[]', '[]', 'ak', 'now')",
            (name,),
        )
    db.commit()


def test_auto_post_goes_only_to_groups_carrying_a_matching_topic(db: sqlite3.Connection) -> None:
    _two_topics(db)
    one = create_group(db, Act(AK, T0), "One", "everyone", [1])
    invited_one = create_group(db, Act(AK, T0), "Invited one", "invited", [1])
    create_group(db, Act(AK, T0), "Two", "everyone", [2])
    create_group(db, Act(AK, T0), "None", "everyone", [])
    assert auto_post(db, 1, [1], T0) == [1, 2]
    assert rows(db, "SELECT group_id FROM threads ORDER BY id") == [(one,), (invited_one,)]


def test_the_thread_view_card_lists_only_threads_in_groups_the_viewer_sees(
    db: sqlite3.Connection, gid: int
) -> None:
    tid, _ = share_story(db, Act(AK, T0), gid, 1, "open note")
    hidden = create_group(db, Act(AK, T0), "Deal team", "invited", [])
    share_story(db, Act(AK, T0), hidden, 1, "secret note")
    card = read_thread(db, ML, tid, T0).story
    assert card is not None
    assert [(t.group, t.note) for t in card.threads] == [("TMT", "open note")]
    own = read_thread(db, AK, tid, T0).story
    assert own is not None
    assert [t.group for t in own.threads] == ["TMT", "Deal team"]


def test_a_share_note_keeps_its_newlines_and_may_be_4000_characters(
    db: sqlite3.Connection, gid: int
) -> None:
    share_story(db, Act(AK, T0), gid, 1, "line one\nline two")
    assert rows(db, "SELECT text FROM comments") == [("line one\nline two",)]
    tid, _ = share_story(db, Act(AK, T0), gid, 2, "q" * MAX_TEXT)
    assert rows(db, "SELECT length(text) FROM comments WHERE thread_id=?", tid) == [(MAX_TEXT,)]
    with pytest.raises(StoreError, match="longer than 4000"):
        share_story(db, Act(AK, T0), gid, 1, "q" * (MAX_TEXT + 1))


def test_a_comment_may_be_4000_characters(db: sqlite3.Connection, gid: int) -> None:
    tid, _ = share_story(db, Act(AK, T0), gid, 1, None)
    cid = add_comment(db, Act(AK, T0), tid, "c" * MAX_TEXT, None)
    assert rows(db, "SELECT length(text) FROM comments WHERE id=?", cid) == [(MAX_TEXT,)]
    with pytest.raises(StoreError, match="longer than 4000"):
        add_comment(db, Act(AK, T0), tid, "c" * (MAX_TEXT + 1), None)


def test_replying_to_a_missing_comment_is_a_store_error(db: sqlite3.Connection, gid: int) -> None:
    tid, _ = share_story(db, Act(AK, T0), gid, 1, None)
    with pytest.raises(StoreError, match="^no such comment in this thread to reply to$"):
        add_comment(db, Act(AK, T0), tid, "x", 999)
    assert count(db, "comments") == 0


def test_last_activity_never_moves_back_when_a_member_writes_with_an_earlier_clock(
    db: sqlite3.Connection, gid: int
) -> None:
    tid, _ = share_story(db, Act(AK, T0), gid, 1, None)
    late = T0 + 30 * MIN
    add_comment(db, Act(AK, late), tid, "late", None)
    add_comment(db, Act(ML, T0 + 5 * MIN), tid, "early clock", None)
    assert rows(db, "SELECT last_activity_at FROM threads WHERE id=?", tid) == [(late.isoformat(),)]


def test_deleting_twice_keeps_the_first_removal_time(db: sqlite3.Connection, gid: int) -> None:
    tid, _ = share_story(db, Act(AK, T0), gid, 1, None)
    cid = add_comment(db, Act(AK, T0), tid, "to remove", None)
    delete_comment(db, Act(AK, T0 + MIN), cid)
    delete_comment(db, Act(AK, T0 + 2 * MIN), cid)
    assert rows(db, "SELECT deleted_at FROM comments WHERE id=?", cid) == [
        ((T0 + MIN).isoformat(),)
    ]


def test_a_removed_comment_is_not_editable_even_inside_the_window(
    db: sqlite3.Connection, gid: int
) -> None:
    tid, _ = share_story(db, Act(AK, T0), gid, 1, None)
    cid = add_comment(db, Act(AK, T0), tid, "x", None)
    delete_comment(db, Act(AK, T0 + MIN), cid)
    view = read_thread(db, AK, tid, T0 + 2 * MIN)
    removed = next(c for c in view.comments if c.id == cid)
    assert (removed.removed, removed.mine, removed.editable) == (True, True, False)


def test_sharing_a_story_that_does_not_exist_is_a_store_error(
    db: sqlite3.Connection, gid: int
) -> None:
    with pytest.raises(StoreError, match="^no story with id 99$"):
        share_story(db, Act(AK, T0), gid, 99, None)
    assert count(db, "threads") == 0


def test_a_share_note_must_be_text(db: sqlite3.Connection, gid: int) -> None:
    with pytest.raises(StoreError, match="^a note must be text$"):
        share_story(db, Act(AK, T0), gid, 1, bad(5))


def test_mark_read_and_the_card_builder_refuse_an_unclean_name(
    db: sqlite3.Connection, gid: int
) -> None:
    tid, _ = share_story(db, Act(AK, T0), gid, 1, "x")
    with pytest.raises(StoreError, match="clean display name"):
        mark_read(db, " ak", tid)
    with read_snapshot(db), pytest.raises(StoreError, match="clean display name"):
        feedview.card_in_snapshot(db, " ak", 1)
    assert count(db, "read_marks") == 0


def test_auto_post_takes_a_list_or_a_tuple_of_topic_ids_only(db: sqlite3.Connection) -> None:
    with pytest.raises(StoreError, match="^topic ids must be a list of integers$"):
        auto_post(db, 1, bad({1}), T0)
    assert auto_post(db, 1, (1,), T0) == []


def test_a_reaction_key_must_be_text(db: sqlite3.Connection, gid: int) -> None:
    share_story(db, Act(AK, T0), gid, 1, "x")
    with pytest.raises(StoreError, match="^a reaction must be text$"):
        react(db, AK, 1, bad(5))


def test_a_comment_of_only_marks_around_a_newline_is_empty(
    db: sqlite3.Connection, gid: int
) -> None:
    tid, _ = share_story(db, Act(AK, T0), gid, 1, None)
    with pytest.raises(StoreError, match="^text is empty$"):
        add_comment(db, Act(AK, T0), tid, "\u0301\n\u0301", None)
    assert count(db, "comments") == 0
