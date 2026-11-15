"""Threads under the security-review rulings of S-7 (R54): who may react, the story id range of
`auto_post`, one-line titles, and text cleaned before the write transaction opens.

Expected values are written by hand. The trace callback records the statements SQLite really
runs, so "no write transaction was opened" is read from the connection, not from the code.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from threads_support import AK, MIN, ML, RD, T0, count, rows, team_db

from credit_os.signal import threads
from credit_os.signal.groups import Act, Forbidden, NotFound, create_group
from credit_os.signal.identity import User, cleaned_text
from credit_os.signal.store import StoreError
from credit_os.signal.threads import (
    MAX_TEXT,
    add_comment,
    auto_post,
    edit_comment,
    react,
    read_thread,
    share_story,
    start_note,
    thread_list,
    unreact,
    unread,
)

STRANGER = User("nobody", "reader")
PRETENDER = User("pretender", "writer")  # claims a role it has no users row for


@pytest.fixture
def db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    handle = team_db(tmp_path)
    yield handle
    handle.close()


@pytest.fixture
def gid(db: sqlite3.Connection) -> int:
    return create_group(db, Act(AK, T0), "TMT", "everyone", [])


def _statements(db: sqlite3.Connection, call: Callable[[], object]) -> list[str]:
    """The SQL text the connection ran during `call`, refused or not."""
    seen: list[str] = []
    db.set_trace_callback(seen.append)
    try:
        with pytest.raises(StoreError):
            call()
    finally:
        db.set_trace_callback(None)
    return seen


# --- R54 L3: a reaction needs a registered user -------------------------------------------


def partial_react(db: sqlite3.Connection, who: User, key: str) -> Callable[[], None]:
    return lambda: react(db, who, 1, key)


def partial_unreact(db: sqlite3.Connection, who: User, key: str) -> Callable[[], None]:
    return lambda: unreact(db, who, 1, key)


@pytest.mark.parametrize("who", [STRANGER, PRETENDER], ids=["reader-name", "claims-writer"])
def test_an_unregistered_name_may_not_react_or_unreact_but_may_read(
    db: sqlite3.Connection, gid: int, who: User
) -> None:
    tid, _ = share_story(db, Act(AK, T0), gid, 1, "x")
    react(db, RD, 1, "agree")
    for call in (partial_react(db, who, "agree"), partial_unreact(db, who, "agree")):
        with pytest.raises(Forbidden, match="^only registered users can react$"):
            call()
    assert rows(db, "SELECT user_name, key FROM reactions") == [("rd", "agree")]
    assert not db.in_transaction
    view = read_thread(db, who, tid, T0)
    assert [(r.key, r.count, r.mine) for r in view.comments[0].reactions] == [("agree", 1, False)]
    assert thread_list(db, who.name, gid, None)[0][0].id == tid
    assert unread(db, who.name).replies == 0


def test_a_registered_reader_still_reacts_whatever_role_the_caller_claims(
    db: sqlite3.Connection, gid: int
) -> None:
    share_story(db, Act(AK, T0), gid, 1, "x")
    react(db, User("rd", "reader"), 1, "agree")
    react(db, User("ml", "reader"), 1, "seen")  # ml's row says writer; the name is registered
    assert rows(db, "SELECT user_name, key FROM reactions ORDER BY user_name") == [
        ("ml", "seen"),
        ("rd", "agree"),
    ]


@pytest.mark.parametrize("call_name", ["react", "unreact"])
def test_an_unregistered_name_gets_the_hidden_comments_answer_when_it_cannot_see_it(
    db: sqlite3.Connection, call_name: str
) -> None:
    hidden = create_group(db, Act(AK, T0), "Deal team", "invited", [])
    share_story(db, Act(AK, T0), hidden, 1, "private")
    call: Callable[[sqlite3.Connection, User, int, str], None] = getattr(threads, call_name)
    with pytest.raises(NotFound) as first:
        call(db, STRANGER, 1, "agree")
    with pytest.raises(NotFound) as second:
        call(db, STRANGER, 999, "agree")
    assert str(first.value) == str(second.value) == "no such comment"
    assert not isinstance(first.value, Forbidden)


def test_an_unregistered_name_is_refused_before_the_reaction_key_is_judged(
    db: sqlite3.Connection, gid: int
) -> None:
    share_story(db, Act(AK, T0), gid, 1, "x")
    with pytest.raises(Forbidden):
        react(db, STRANGER, 1, "fire")


# --- R54 L1 / L2 ---------------------------------------------------------------------------


@pytest.mark.parametrize("story", [2**63, -(2**63) - 1, 10**5000], ids=["max+1", "min-1", "huge"])
def test_auto_post_refuses_a_story_id_sqlite_cannot_hold(
    db: sqlite3.Connection, story: int
) -> None:
    with pytest.raises(StoreError, match="^no story with that id$"):
        auto_post(db, story, [1], T0)
    assert count(db, "threads") == 0 and not db.in_transaction


@pytest.mark.parametrize("ch", ["\u2028", "\u2029"], ids=["U+2028", "U+2029"])
def test_a_title_with_a_unicode_line_separator_is_refused_and_a_comment_keeps_it(
    db: sqlite3.Connection, gid: int, ch: str
) -> None:
    with pytest.raises(StoreError, match="^text must be one line$"):
        start_note(db, Act(AK, T0), gid, f"first{ch}second", "body")
    assert count(db, "threads") == 0
    with pytest.raises(StoreError, match="^text must be one line$"):
        cleaned_text(f"a{ch}b", multiline=False)
    assert cleaned_text(f"a{ch}b", multiline=True) == f"a{ch}b"


CLEANED_AWAY = ["\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85"]  # VT, FF, FS, GS, RS, NEL
REFUSED_BREAKS = ["\n", "\r", "\u2028", "\u2029"]


@pytest.mark.parametrize("ch", CLEANED_AWAY, ids=[f"U+{ord(c):04X}" for c in CLEANED_AWAY])
def test_a_title_with_a_break_that_cleaning_drops_is_stored_cleaned_on_one_line(
    db: sqlite3.Connection, gid: int, ch: str
) -> None:
    assert cleaned_text(f"a{ch}b", multiline=False) == "ab"
    tid = start_note(db, Act(AK, T0), gid, f"first{ch}second", "body")
    assert rows(db, "SELECT title FROM threads WHERE id=?", tid) == [("firstsecond",)]


@pytest.mark.parametrize("ch", REFUSED_BREAKS, ids=[f"U+{ord(c):04X}" for c in REFUSED_BREAKS])
def test_a_title_with_a_break_that_survives_cleaning_is_refused(
    db: sqlite3.Connection, gid: int, ch: str
) -> None:
    with pytest.raises(StoreError, match="^text must be one line$"):
        start_note(db, Act(AK, T0), gid, f"first{ch}second", "body")
    assert count(db, "threads") == 0


# --- R54 L4: text is cleaned before the write transaction opens ------------------------------


def _bad_text_calls(db: sqlite3.Connection, gid: int) -> dict[str, Callable[[], object]]:
    tid, _ = share_story(db, Act(AK, T0), gid, 1, "first")  # comment 1
    reply_to = 1
    return {
        "share-long": lambda: share_story(db, Act(AK, T0), gid, 2, "z" * (MAX_TEXT + 1)),
        "note-long-title": lambda: start_note(db, Act(AK, T0), gid, "T" * 500, "x"),
        "note-empty-text": lambda: start_note(db, Act(AK, T0), gid, "T", "\u200b"),
        "note-two-line-title": lambda: start_note(db, Act(AK, T0), gid, "a\nb", "x"),
        "comment-long": lambda: add_comment(db, Act(AK, T0), tid, "y" * (MAX_TEXT + 1), None),
        "comment-empty": lambda: add_comment(db, Act(AK, T0), tid, " \u200b ", None),
        "reply-long": lambda: add_comment(db, Act(AK, T0), tid, "y" * (MAX_TEXT + 1), reply_to),
        "edit-long": lambda: edit_comment(db, Act(AK, T0 + MIN), 1, "y" * (MAX_TEXT + 1)),
        "edit-empty": lambda: edit_comment(db, Act(AK, T0 + MIN), 1, "\u200b"),
    }


@pytest.mark.parametrize(
    "name",
    [
        "share-long",
        "note-long-title",
        "note-empty-text",
        "note-two-line-title",
        "comment-long",
        "comment-empty",
        "reply-long",
        "edit-long",
        "edit-empty",
    ],
)
def test_a_refused_text_never_opens_a_write_transaction(
    db: sqlite3.Connection, gid: int, name: str
) -> None:
    call = _bad_text_calls(db, gid)[name]
    before = (count(db, "threads"), count(db, "comments"))
    ran = _statements(db, call)
    assert not any(sql.startswith("BEGIN") for sql in ran), ran
    assert (count(db, "threads"), count(db, "comments")) == before
    assert not db.in_transaction


@pytest.mark.parametrize(
    "build",
    [
        lambda db, g, who, bad: share_story(db, Act(who, T0), g, 1, bad),
        lambda db, g, who, bad: start_note(db, Act(who, T0), g, "T", bad),
        lambda db, g, who, bad: add_comment(db, Act(who, T0), 1, bad, None),
        lambda db, g, who, bad: edit_comment(db, Act(who, T0), 1, bad),
    ],
    ids=["share", "note", "comment", "edit"],
)
def test_bad_text_answers_the_same_for_a_hidden_and_a_missing_target(
    db: sqlite3.Connection, build: Callable[..., Any]
) -> None:
    """The refusal of the text does not depend on the group, thread or comment (R54 L4)."""
    hidden = create_group(db, Act(AK, T0), "Deal team", "invited", [])
    share_story(db, Act(AK, T0), hidden, 2, "private")
    for bad in ("y" * (MAX_TEXT + 1), "\u200b"):
        with pytest.raises(StoreError) as hidden_answer:
            build(db, hidden, ML, bad)
        with pytest.raises(StoreError) as missing_answer:
            build(db, 999, ML, bad)
        assert (type(hidden_answer.value), str(hidden_answer.value)) == (
            type(missing_answer.value),
            str(missing_answer.value),
        )


def test_the_good_text_paths_still_write_in_one_transaction(
    db: sqlite3.Connection, gid: int
) -> None:
    seen: list[str] = []
    db.set_trace_callback(seen.append)
    try:
        tid, _ = share_story(db, Act(AK, T0), gid, 1, "note")
        add_comment(db, Act(ML, T0), tid, "reply", 1)
        edit_comment(db, Act(AK, T0 + MIN), 1, "changed")
        start_note(db, Act(AK, T0), gid, "T", "x")
    finally:
        db.set_trace_callback(None)
    assert [s for s in seen if s.startswith("BEGIN")] == ["BEGIN IMMEDIATE"] * 4
    assert rows(db, "SELECT text FROM comments ORDER BY id") == [("changed",), ("reply",), ("x",)]


# --- L4 of the task review: threads uses groups.require_stamp ---------------------------------


def test_threads_checks_a_time_through_groups_require_stamp(
    db: sqlite3.Connection, gid: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    tid, _ = share_story(db, Act(AK, T0), gid, 1, "x")
    called: list[object] = []

    def spy(now: object) -> str:
        called.append(now)
        return "stamp"

    monkeypatch.setattr(threads, "require_stamp", spy)
    read_thread(db, AK, tid, T0)
    auto_post(db, 2, [], T0)
    assert called == [T0, T0]
    naive: datetime = T0.replace(tzinfo=None)
    monkeypatch.undo()
    for call in (lambda: read_thread(db, AK, tid, naive), lambda: auto_post(db, 2, [1], naive)):
        with pytest.raises(StoreError, match="timezone-aware"):
            call()
