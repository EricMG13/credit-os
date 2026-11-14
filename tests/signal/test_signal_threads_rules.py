"""Threads under the port's rulings, part 1: visibility against an oracle that shares no code
with the module, role refusals, hidden == missing, the share row against the rows the feed view
tests insert by SQL, the public feed view names (R22, R2, R15, R42).

Expected values are written by hand or by the Python oracle below; none is computed with the
code under test.
"""

from __future__ import annotations

import random
import sqlite3
from collections.abc import Callable, Iterator
from functools import partial
from pathlib import Path
from typing import Any

import pytest
from feedview_grid import thread
from threads_support import AK, MIN, ML, RD, T0, count, rows, team_db

from credit_os.signal import feedview
from credit_os.signal.feedview import CardThread, card_for
from credit_os.signal.groups import Act, Forbidden, NotFound, create_group
from credit_os.signal.identity import User
from credit_os.signal.store import StoreError, StoreUnusable, read_snapshot
from credit_os.signal.threads import (
    add_comment,
    delete_comment,
    edit_comment,
    read_thread,
    share_story,
    start_note,
)


def bad(value: object) -> Any:
    """A value of the wrong type, hidden from the type checker (the callee must refuse it)."""
    return value


_ALL = {
    "threads": "SELECT * FROM threads ORDER BY id",
    "comments": "SELECT * FROM comments ORDER BY id",
}
ZZ = User("zz", "writer")
USERS = (AK, ML, RD, ZZ)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    handle = team_db(tmp_path)
    yield handle
    handle.close()


def _state(db: sqlite3.Connection, seed: int) -> tuple[dict[int, bool], dict[int, set[str]]]:
    """Three groups with a random visibility and members, each with one note thread whose one
    comment is ak's. Written by plain SQL; returns (is open, members) as the oracle's facts."""
    rng = random.Random(seed)
    opened: dict[int, bool] = {}
    members: dict[int, set[str]] = {}
    for gid in (1, 2, 3):
        opened[gid] = rng.random() < 0.5
        members[gid] = {u.name for u in USERS if rng.random() < 0.5}
        db.execute(
            "INSERT INTO groups(id, name, name_key, visibility, created_by, created_at)"
            " VALUES(?, ?, ?, ?, 'ak', ?)",
            (gid, f"g{gid}", f"g{gid}", "everyone" if opened[gid] else "invited", T0.isoformat()),
        )
        for name in members[gid]:
            db.execute(
                "INSERT INTO group_members(group_id, user_name, joined_at) VALUES(?, ?, ?)",
                (gid, name, T0.isoformat()),
            )
        db.execute(
            "INSERT INTO threads(id, group_id, title, started_by, created_at, last_activity_at)"
            " VALUES(?, ?, 'n', 'ak', ?, ?)",
            (gid, gid, T0.isoformat(), T0.isoformat()),
        )
        db.execute(
            "INSERT INTO comments(id, thread_id, author, text, created_at) VALUES(?, ?, 'ak', 'c', ?)",
            (gid, gid, T0.isoformat()),
        )
    db.commit()
    return opened, members


def _expect(visible: bool, writer: bool, author_ok: bool = True) -> type[Exception] | None:
    """The oracle: hidden is NotFound, then a reader or a non-author is Forbidden, else it works."""
    if not visible:
        return NotFound
    return None if writer and author_ok else Forbidden


def _outcome(call: Callable[[], object]) -> type[Exception] | None:
    try:
        call()
    except (NotFound, Forbidden) as exc:
        return type(exc)
    return None


@pytest.mark.parametrize("seed", range(12))
def test_visibility_and_roles_match_an_independent_oracle(tmp_path: Path, seed: int) -> None:
    db = team_db(tmp_path)
    opened, members = _state(db, seed)

    def seen(user: User, gid: int) -> bool:
        return opened[gid] or user.name in members[gid]

    for user in USERS:
        for gid in (1, 2, 3):
            want = None if seen(user, gid) else NotFound
            assert _outcome(partial(read_thread, db, user, gid, T0)) == want
    for user in USERS:
        for gid in (1, 2, 3):
            writer = user.role == "writer"
            act = Act(user, T0 + MIN)
            visible = seen(user, gid)
            assert _outcome(partial(add_comment, db, act, gid, "x", None)) == _expect(
                visible, writer
            )
            assert _outcome(partial(start_note, db, act, gid, "t", "x")) == _expect(visible, writer)
            assert _outcome(partial(share_story, db, act, gid, 1, None)) == _expect(visible, writer)
    for user in USERS:
        for gid in (1, 2, 3):
            act = Act(user, T0 + MIN)
            mine = user.name == "ak"
            assert _outcome(partial(edit_comment, db, act, gid, "y")) == _expect(
                seen(user, gid), True, mine
            )
    for user in USERS:
        for gid in (1, 2, 3):
            act = Act(user, T0 + MIN)
            assert _outcome(partial(delete_comment, db, act, gid)) == _expect(
                seen(user, gid), True, user.name == "ak"
            )
    db.close()


def test_a_refused_write_changes_nothing(db: sqlite3.Connection) -> None:
    gid = create_group(db, Act(AK, T0), "Deal team", "invited", [])
    tid, _ = share_story(db, Act(AK, T0), gid, 1, "private")
    before = (count(db, "threads"), count(db, "comments"), rows(db, "SELECT * FROM threads"))
    for user in (RD, ML):
        for call in (
            partial(share_story, db, Act(user, T0 + MIN), gid, 2, "x"),
            partial(start_note, db, Act(user, T0 + MIN), gid, "t", "x"),
            partial(add_comment, db, Act(user, T0 + MIN), tid, "x", None),
            partial(edit_comment, db, Act(user, T0 + MIN), 1, "x"),
            partial(delete_comment, db, Act(user, T0 + MIN), 1),
        ):
            with pytest.raises((NotFound, Forbidden)):
                call()
    assert before == (
        count(db, "threads"),
        count(db, "comments"),
        rows(db, "SELECT * FROM threads"),
    )


@pytest.mark.parametrize("who", [RD, User("nobody", "reader")], ids=["member-reader", "stranger"])
def test_a_reader_is_refused_every_thread_write_with_forbidden(
    db: sqlite3.Connection, who: User
) -> None:
    gid = create_group(db, Act(AK, T0), "TMT", "everyone", [])
    tid, _ = share_story(db, Act(AK, T0), gid, 1, "x")
    for call in (
        partial(share_story, db, Act(who, T0), gid, 2, None),
        partial(start_note, db, Act(who, T0), gid, "T", "x"),
        partial(add_comment, db, Act(who, T0), tid, "x", None),
    ):
        with pytest.raises(Forbidden):
            call()
    assert (count(db, "threads"), count(db, "comments")) == (1, 1)


def test_an_owner_may_share_comment_and_start_a_note(db: sqlite3.Connection) -> None:
    owner = User("ow", "owner")
    gid = create_group(db, Act(AK, T0), "TMT", "everyone", [])
    tid, _ = share_story(db, Act(owner, T0), gid, 1, "x")
    add_comment(db, Act(owner, T0), tid, "y", None)
    start_note(db, Act(owner, T0), gid, "T", "z")
    assert count(db, "comments") == 3


def test_hidden_and_missing_look_the_same_for_every_read_and_write(
    db: sqlite3.Connection,
) -> None:
    gid = create_group(db, Act(AK, T0), "Deal team", "invited", [])
    tid, _ = share_story(db, Act(AK, T0), gid, 1, "private")
    for who in (ML, RD):
        for hidden, missing in (
            (partial(read_thread, db, who, tid, T0), partial(read_thread, db, who, 999, T0)),
            (partial(read_thread, db, who, tid, T0), partial(read_thread, db, who, 2**70, T0)),
            (
                partial(add_comment, db, Act(who, T0), tid, "x", None),
                partial(add_comment, db, Act(who, T0), 999, "x", None),
            ),
            (
                partial(edit_comment, db, Act(who, T0), 1, "x"),
                partial(edit_comment, db, Act(who, T0), 999, "x"),
            ),
            (
                partial(delete_comment, db, Act(who, T0), 1),
                partial(delete_comment, db, Act(who, T0), 2**70),
            ),
            (
                partial(start_note, db, Act(who, T0), gid, "T", "x"),
                partial(start_note, db, Act(who, T0), 999, "T", "x"),
            ),
            (
                partial(share_story, db, Act(who, T0), gid, 2, None),
                partial(share_story, db, Act(who, T0), 999, 2, None),
            ),
        ):
            with pytest.raises(NotFound) as first:
                hidden()
            with pytest.raises(NotFound) as second:
                missing()
            assert str(first.value) == str(second.value)
            assert str(first.value) in ("no such thread", "no such comment", "no such group")


def test_a_share_writes_the_rows_the_feed_view_tests_insert_by_sql(tmp_path: Path) -> None:
    shared = team_db(tmp_path / "a")
    by_sql = team_db(tmp_path / "b")
    for handle in (shared, by_sql):
        create_group(handle, Act(AK, T0), "TMT", "everyone", [])
    assert share_story(shared, Act(AK, T0), 1, 1, "note 1") == (1, False)
    assert thread(by_sql, 1, 1, "ak") == 1
    for table in ("threads", "comments"):
        assert rows(shared, _ALL[table]) == rows(by_sql, _ALL[table])
    assert card_for(shared, "ml", 1) == card_for(by_sql, "ml", 1)
    assert card_for(shared, "ml", 1).threads == (CardThread(1, "TMT", 1, "ak", "note 1"),)
    shared.close()
    by_sql.close()


def test_a_share_claims_an_automatic_thread_and_the_card_shows_it(db: sqlite3.Connection) -> None:
    gid = create_group(db, Act(AK, T0), "TMT", "everyone", [])
    thread(db, gid, 1, None)
    assert card_for(db, "ml", 1).threads == (CardThread(1, "TMT", 0, None, None),)
    with pytest.raises(Forbidden):
        share_story(db, Act(RD, T0 + MIN), gid, 1, "no")
    assert rows(db, "SELECT started_by FROM threads") == [(None,)]
    assert share_story(db, Act(AK, T0 + 3 * MIN), gid, 1, "claimed") == (1, True)
    assert share_story(db, Act(ML, T0 + 4 * MIN), gid, 1, None) == (1, True)
    assert card_for(db, "rd", 1).threads == (CardThread(1, "TMT", 1, "ak", "claimed"),)
    assert rows(db, "SELECT started_by, created_at FROM threads") == [
        ("ak", (T0 + 3 * MIN).isoformat())
    ]


def test_a_claim_never_moves_created_at_back(db: sqlite3.Connection) -> None:
    gid = create_group(db, Act(AK, T0), "TMT", "everyone", [])
    thread(db, gid, 1, None)
    share_story(db, Act(AK, T0 - MIN), gid, 1, None)
    assert rows(db, "SELECT started_by, created_at FROM threads") == [("ak", T0.isoformat())]


def test_the_thread_view_reads_its_card_inside_its_own_snapshot(db: sqlite3.Connection) -> None:
    gid = create_group(db, Act(AK, T0), "TMT", "everyone", [])
    tid, _ = share_story(db, Act(AK, T0), gid, 1, "look")
    view = read_thread(db, ML, tid, T0)
    assert view.story == card_for(db, "ml", 1)
    assert (view.group, view.group_id, view.can_post) == ("TMT", gid, True)
    with read_snapshot(db), pytest.raises(StoreUnusable):
        read_thread(db, ML, tid, T0)
    assert not db.in_transaction


def test_the_card_builder_needs_the_callers_transaction(db: sqlite3.Connection) -> None:
    expected = card_for(db, "ak", 1)
    with pytest.raises(StoreUnusable):
        feedview.card_in_snapshot(db, "ak", 1)
    with read_snapshot(db):
        assert feedview.card_in_snapshot(db, "ak", 1) == expected
        with pytest.raises(feedview.ViewError):
            feedview.card_in_snapshot(db, "ak", 99)


def test_feedview_parsers_have_public_names_and_no_private_alias() -> None:
    for old in ("_id", "_instant", "_visible_json", "_cursor"):
        assert not hasattr(feedview, old)
    assert feedview.parse_cursor("2026-11-13T09:00:00+00:00,5", ",") == (T0.isoformat(), 5)
    assert feedview.parse_cursor("2026-11-13T09:00:00+00:00|5", "|") == (T0.isoformat(), 5)
    assert feedview.parse_id("12", "x") == 12
    assert feedview.parse_instant("2026-11-13T10:00:00+01:00", "x") == T0.isoformat()
    with pytest.raises(feedview.ViewError):
        feedview.parse_cursor("nonsense", ",")


@pytest.mark.parametrize(
    "call",
    [
        lambda db: share_story(db, bad("ak"), 1, 1, None),
        lambda db: share_story(db, Act(AK, T0), bad("1"), 1, None),
        lambda db: share_story(db, Act(AK, T0), 1, bad(True), None),
        lambda db: share_story(db, Act(AK, T0), 1, 1, bad(5)),
        lambda db: share_story(db, Act(AK, T0), 1, 2**70, None),
        lambda db: start_note(db, Act(AK, T0), 1, bad(5), "x"),
        lambda db: start_note(db, Act(AK, T0), 1, "t", bad(None)),
        lambda db: add_comment(db, Act(AK, T0), bad("1"), "x", None),
        lambda db: add_comment(db, Act(AK, T0), 1, "x", bad("1")),
        lambda db: add_comment(db, Act(AK, T0), 1, "x", bad(True)),
        lambda db: add_comment(db, Act(User("x" * 61, "writer"), T0), 1, "x", None),
        lambda db: add_comment(db, Act(User("a\x00b", "writer"), T0), 1, "x", None),
        lambda db: add_comment(db, Act(bad("ak"), T0), 1, "x", None),
        lambda db: add_comment(db, Act(AK, bad("now")), 1, "x", None),
        lambda db: edit_comment(db, Act(AK, T0), bad(None), "x"),
        lambda db: delete_comment(db, Act(AK, T0), bad(1.0)),
        lambda db: read_thread(db, bad("ak"), 1, T0),
        lambda db: read_thread(db, AK, bad("1"), T0),
        lambda db: read_thread(db, AK, 1, bad("now")),
    ],
    ids=[
        "share-actor",
        "share-group",
        "share-story-bool",
        "share-note",
        "share-story-huge",
        "note-title",
        "note-text",
        "comment-thread",
        "comment-parent",
        "comment-parent-bool",
        "comment-long-name",
        "comment-control-name",
        "comment-actor-name",
        "comment-time",
        "edit-id",
        "delete-id",
        "read-user",
        "read-id",
        "read-time",
    ],
)
def test_wrong_types_are_a_store_error(
    db: sqlite3.Connection, call: Callable[[sqlite3.Connection], Any]
) -> None:
    create_group(db, Act(AK, T0), "TMT", "everyone", [])
    thread(db, 1, 1, "ak")
    with pytest.raises(StoreError):
        call(db)
    assert not db.in_transaction


def test_an_error_text_never_carries_the_input(db: sqlite3.Connection) -> None:
    gid = create_group(db, Act(AK, T0), "TMT", "everyone", [])
    for call in (
        partial(start_note, db, Act(AK, T0), gid, "T" * 5000, "x"),
        partial(start_note, db, Act(AK, T0), gid, "T", "y" * 5000),
        partial(share_story, db, Act(AK, T0), gid, 1, "z" * 5000),
        partial(add_comment, db, Act(User("n" * 5000, "writer"), T0), 1, "x", None),
    ):
        with pytest.raises(StoreError) as caught:
            call()
        assert len(str(caught.value)) < 120


def test_edit_and_delete_check_authorship_only_not_the_current_role(
    db: sqlite3.Connection,
) -> None:
    """Accepted limit (S3-12, R52 Q3): a demoted author still edits and deletes their comment."""
    gid = create_group(db, Act(AK, T0), "TMT", "everyone", [])
    tid, _ = share_story(db, Act(AK, T0), gid, 1, "first")
    add_comment(db, Act(AK, T0), tid, "second", None)
    db.execute("UPDATE users SET role='reader' WHERE name='ak'")
    db.commit()
    demoted = User("ak", "reader")
    edit_comment(db, Act(demoted, T0 + MIN), 1, "changed")
    delete_comment(db, Act(demoted, T0 + MIN), 2)
    assert rows(db, "SELECT id, text, deleted_at IS NOT NULL FROM comments ORDER BY id") == [
        (1, "changed", 0),
        (2, "", 1),
    ]
    with pytest.raises(Forbidden):
        add_comment(db, Act(demoted, T0 + MIN), tid, "new", None)
