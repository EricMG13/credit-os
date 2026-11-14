"""Carried from the predecessor's tests/test_signal_threads.py, adapted to credit_os.signal
(part 1: sharing, notes, comments, edit and delete, text cleaning, the thread view)."""

from __future__ import annotations

import sqlite3
import threading
import unicodedata
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st
from threads_support import AK, MIN, ML, RD, T0, count, team_db

from credit_os.signal import groups, threads
from credit_os.signal.groups import Act, Forbidden, create_group
from credit_os.signal.identity import User
from credit_os.signal.store import StoreError, open_db
from credit_os.signal.threads import (
    EDIT_WINDOW,
    MAX_COMMENTS,
    MAX_TEXT,
    MAX_TITLE,
    add_comment,
    clean_text,
    delete_comment,
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


@pytest.fixture
def gid(db: sqlite3.Connection) -> int:
    return create_group(db, Act(AK, T0), "TMT", "everyone", [])


def test_first_share_starts_a_thread_and_a_second_share_joins_it(
    db: sqlite3.Connection, gid: int
) -> None:
    assert share_story(db, Act(AK, T0), gid, 1, "Heavier than we assumed.") == (1, False)
    assert share_story(db, Act(ML, T0 + MIN), gid, 1, None) == (1, True)
    assert share_story(db, Act(ML, T0 + 2 * MIN), gid, 1, "Agree.") == (1, True)
    view = read_thread(db, RD, 1, T0 + 3 * MIN)
    assert [(c.author, c.text) for c in view.comments] == [
        ("ak", "Heavier than we assumed."),
        ("ml", "Agree."),
    ]
    assert view.story is not None
    assert view.story.id == 1 and view.started_by == "ak" and view.can_post is False


def test_two_shares_at_once_make_one_thread(tmp_path: Path) -> None:
    first = team_db(tmp_path)
    group = create_group(first, Act(AK, T0), "TMT", "everyone", [])
    barrier = threading.Barrier(2)
    results: list[tuple[int, bool]] = []
    errors: list[Exception] = []

    def run(user: User) -> None:
        try:
            conn = open_db(tmp_path)
            try:
                barrier.wait()
                results.append(share_story(conn, Act(user, T0), group, 1, None))
            finally:
                conn.close()
        except (StoreError, sqlite3.Error) as exc:
            errors.append(exc)

    workers = [
        threading.Thread(target=run, args=(AK,)),
        threading.Thread(target=run, args=(ML,)),
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    assert errors == []
    assert count(first, "threads") == 1
    assert sorted(joined for _, joined in results) == [False, True]
    first.close()


def test_replies_nest_one_level(db: sqlite3.Connection, gid: int) -> None:
    tid, _ = share_story(db, Act(AK, T0), gid, 1, "top")  # comment 1
    r = add_comment(db, Act(ML, T0), tid, "reply", 1)  # comment 2
    with pytest.raises(StoreError):
        add_comment(db, Act(AK, T0), tid, "reply to a reply", r)
    other, _ = share_story(db, Act(AK, T0), gid, 2, "other thread")  # comment 3
    with pytest.raises(StoreError):
        add_comment(db, Act(AK, T0), other, "wrong thread", 1)
    delete_comment(db, Act(AK, T0), 1)
    assert add_comment(db, Act(ML, T0), tid, "after removal", 1) == 4


@pytest.mark.parametrize(
    "after,allowed",
    [(timedelta(minutes=15), True), (timedelta(minutes=15, seconds=1), False)],
)
def test_the_edit_window_is_15_minutes_inclusive(
    db: sqlite3.Connection, gid: int, after: timedelta, allowed: bool
) -> None:
    assert EDIT_WINDOW == timedelta(minutes=15)
    tid, _ = share_story(db, Act(AK, T0), gid, 1, "first")
    if allowed:
        edit_comment(db, Act(AK, T0 + after), 1, "second")
    else:
        with pytest.raises(Forbidden):
            edit_comment(db, Act(AK, T0 + after), 1, "second")
    (c,) = read_thread(db, AK, tid, T0 + after).comments
    assert (c.text, c.edited) == (("second", True) if allowed else ("first", False))
    assert c.editable is allowed or after > EDIT_WINDOW


def test_a_comment_carries_its_authors_current_role(db: sqlite3.Connection, gid: int) -> None:
    tid, _ = share_story(db, Act(ML, T0), gid, 1, "x")
    db.execute("UPDATE users SET role='owner' WHERE name='ml'")
    db.commit()
    assert read_thread(db, RD, tid, T0).comments[0].role == "owner"


@pytest.mark.parametrize(
    "raw,stored", [("  hi \r\n there\x00\u202e ", "hi \n there"), ("e\u0301", "\u00e9")]
)
def test_text_is_cleaned(raw: str, stored: str) -> None:
    assert clean_text(raw, MAX_TEXT) == stored


@pytest.mark.parametrize(
    "raw", ["", "   ", "\u200b", "x" * 4001], ids=["empty", "blank", "zwsp", "long"]
)
def test_empty_or_oversized_text_is_refused(raw: str) -> None:
    with pytest.raises(StoreError):
        clean_text(raw, MAX_TEXT)


def test_a_title_over_the_limit_is_refused_not_cut(db: sqlite3.Connection, gid: int) -> None:
    with pytest.raises(StoreError):
        start_note(db, Act(AK, T0), gid, "t" * (MAX_TITLE + 1), "x")
    assert count(db, "threads") == 0


def test_markup_is_stored_as_typed(db: sqlite3.Connection, gid: int) -> None:
    tid = start_note(
        db, Act(AK, T0), gid, "<b>t</b>", "<img src=x onerror=alert(1)> javascript:alert(1)"
    )
    view = read_thread(db, AK, tid, T0)
    assert view.title == "<b>t</b>" and view.comments[0].text.startswith("<img")
    assert view.story is None


def test_the_501st_comment_is_refused(db: sqlite3.Connection, gid: int) -> None:
    tid, _ = share_story(db, Act(AK, T0), gid, 1, "first")
    for number in range(MAX_COMMENTS - 1):
        add_comment(db, Act(AK, T0), tid, f"c{number}", None)
    assert count(db, "comments") == MAX_COMMENTS
    with pytest.raises(StoreError, match="^this thread is full$"):
        add_comment(db, Act(ML, T0), tid, "one too many", None)
    with pytest.raises(StoreError, match="^this thread is full$"):
        share_story(db, Act(ML, T0), gid, 1, "one too many")
    assert count(db, "comments") == MAX_COMMENTS


def test_a_naive_now_is_refused_like_every_other_entry_point(
    db: sqlite3.Connection, gid: int
) -> None:
    tid, _ = share_story(db, Act(AK, T0), gid, 1, "x")
    naive = T0.replace(tzinfo=None)
    with pytest.raises(StoreError, match="time must be timezone-aware"):
        edit_comment(db, Act(AK, naive), 1, "y")
    with pytest.raises(StoreError, match="time must be timezone-aware"):
        read_thread(db, AK, tid, naive)


def test_a_database_opens_with_secure_delete_on(tmp_path: Path) -> None:
    assert team_db(tmp_path).execute("PRAGMA secure_delete").fetchone()[0] == 1


def test_a_naive_now_on_an_already_removed_comment_is_refused(
    db: sqlite3.Connection, gid: int
) -> None:
    tid, _ = share_story(db, Act(AK, T0), gid, 1, None)
    cid = add_comment(db, Act(AK, T0), tid, "x", None)
    delete_comment(db, Act(AK, T0), cid)
    with pytest.raises(StoreError, match="time must be timezone-aware"):
        delete_comment(db, Act(AK, T0.replace(tzinfo=None)), cid)


@given(st.text(max_size=200))
def test_any_text_is_cleaned_or_refused_never_an_error(raw: str) -> None:
    try:
        text = clean_text(raw, MAX_TEXT)
    except StoreError:
        return
    assert text and all(
        ch == "\n" or unicodedata.category(ch) not in ("Cc", "Cf", "Cs") for ch in text
    )


def test_a_comment_is_cleaned_by_the_identity_rules(db: sqlite3.Connection, gid: int) -> None:
    tid, _ = share_story(db, Act(AK, T0), gid, 1, None)
    mark = "\u0316"
    add_comment(db, Act(AK, T0), tid, "a\u3164b\nc" + mark * 9, None)
    (comment,) = read_thread(db, AK, tid, T0).comments
    assert comment.text == "ab\nc" + mark * 8
    assert clean_text("x\u2800y\n", MAX_TEXT) == "xy"
    with pytest.raises(StoreError, match="^text is empty$"):
        clean_text("\u3164\u2800\n", MAX_TEXT)


def test_a_title_is_one_line_and_cleaned(db: sqlite3.Connection, gid: int) -> None:
    for title in ("two\nlines", "two\rlines"):
        with pytest.raises(StoreError, match="^text must be one line$"):
            start_note(db, Act(AK, T0), gid, title, "x")
    assert count(db, "threads") == 0
    tid = start_note(db, Act(AK, T0), gid, "Rates\u3164 view", "x")
    assert read_thread(db, AK, tid, T0).title == "Rates view"


def test_the_helpers_threads_shares_with_groups_are_public_and_not_aliased() -> None:
    for old in ("_act", "_user", "_stamp"):
        assert not hasattr(groups, old)
    assert not hasattr(threads, "_normalised")
    user, stamp = groups.require_act(Act(AK, T0))
    assert (user, stamp) == (AK, T0.isoformat())
    assert groups.require_user(RD) is RD
    assert groups.require_stamp(T0) == T0.isoformat()
    with pytest.raises(StoreError, match="^the actor must be an Act holding a User$"):
        groups.require_act(object())
    with pytest.raises(StoreError, match="^the user must be a User$"):
        groups.require_user("ak")
    with pytest.raises(StoreError, match="^time must be a datetime$"):
        groups.require_stamp("now")
