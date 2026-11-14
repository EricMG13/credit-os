"""Carried from the predecessor's tests/test_signal_threads.py, adapted to credit_os.signal
(part 2: reactions, thread lists, read marks, unread counts, automatic posting, claims).

Changed from the predecessor by ruling: the reaction keys are agree, disagree, seen (R21); a
reader may react (R22), so `react` leaves the reader-refusal test and has a test of its own.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from datetime import timedelta
from pathlib import Path

import pytest
from threads_support import AK, MIN, ML, RD, T0, count, rows, team_db

from credit_os.signal import feedview
from credit_os.signal.groups import Act, Forbidden, add_member, create_group, join, remove_member
from credit_os.signal.store import StoreError
from credit_os.signal.threads import (
    REACTIONS,
    Unread,
    add_comment,
    auto_post,
    delete_comment,
    edit_comment,
    mark_read,
    react,
    read_thread,
    share_story,
    start_note,
    thread_list,
    unreact,
    unread,
)


@pytest.fixture
def db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    handle = team_db(tmp_path)
    yield handle
    handle.close()


@pytest.fixture
def gid(db: sqlite3.Connection) -> int:
    return create_group(db, Act(AK, T0), "TMT", "everyone", [])


def _topic(db: sqlite3.Connection, groups: tuple[int, ...]) -> None:
    db.execute(
        "INSERT INTO topics(name, keywords, kinds, created_by, created_at)"
        " VALUES('x', '[]', '[]', 'ak', 'now')"
    )
    for group in groups:
        db.execute("INSERT INTO group_topics(group_id, topic_id) VALUES(?, 1)", (group,))
    db.commit()


def test_a_reader_cannot_share_post_edit_or_delete(db: sqlite3.Connection, gid: int) -> None:
    tid, _ = share_story(db, Act(AK, T0), gid, 1, "note")
    calls: list[Callable[[], object]] = [
        lambda: share_story(db, Act(RD, T0), gid, 2, None),
        lambda: start_note(db, Act(RD, T0), gid, "T", "x"),
        lambda: add_comment(db, Act(RD, T0), tid, "x", None),
        lambda: edit_comment(db, Act(RD, T0), 1, "x"),
        lambda: delete_comment(db, Act(RD, T0), 1),
    ]
    for call in calls:
        with pytest.raises(Forbidden):
            call()
    assert count(db, "threads") == 1 and count(db, "comments") == 1 and count(db, "reactions") == 0


def test_a_reader_may_react_and_a_hidden_comment_refuses_everyone(db: sqlite3.Connection) -> None:
    open_group = create_group(db, Act(AK, T0), "TMT", "everyone", [])
    share_story(db, Act(AK, T0), open_group, 1, "x")
    react(db, RD, 1, "agree")
    unreact(db, RD, 1, "agree")
    react(db, RD, 1, "seen")
    assert rows(db, "SELECT user_name, key FROM reactions") == [("rd", "seen")]
    closed = create_group(db, Act(AK, T0), "Deal team", "invited", [])
    share_story(db, Act(AK, T0), closed, 2, "y")
    with pytest.raises(StoreError, match="^no such comment$"):
        react(db, RD, 2, "agree")


def test_an_invited_groups_thread_does_not_exist_for_a_non_member(db: sqlite3.Connection) -> None:
    gid = create_group(db, Act(AK, T0), "Deal team", "invited", [])
    tid, _ = share_story(db, Act(AK, T0), gid, 1, "private")
    thread_calls: list[Callable[[], object]] = [
        lambda: read_thread(db, ML, tid, T0),
        lambda: add_comment(db, Act(ML, T0), tid, "x", None),
        lambda: read_thread(db, ML, 999, T0),
        lambda: read_thread(db, ML, 2**70, T0),
    ]
    for call in thread_calls:
        with pytest.raises(StoreError, match="^no such thread$"):
            call()
    comment_calls: list[Callable[[], object]] = [
        lambda: react(db, ML, 1, "agree"),
        lambda: edit_comment(db, Act(ML, T0), 1, "x"),
        lambda: delete_comment(db, Act(ML, T0), 1),
        lambda: react(db, ML, 2**70, "agree"),
    ]
    for call in comment_calls:
        with pytest.raises(StoreError, match="^no such comment$"):
            call()
    group_calls: list[Callable[[], object]] = [
        lambda: thread_list(db, "ml", gid, None),
        lambda: share_story(db, Act(ML, T0), gid, 2, None),
        lambda: start_note(db, Act(ML, T0), gid, "T", "x"),
    ]
    for call in group_calls:
        with pytest.raises(StoreError, match="^no such group$"):
            call()


def test_only_the_author_edits_or_deletes_and_a_removed_comment_keeps_its_place(
    db: sqlite3.Connection, gid: int
) -> None:
    tid, _ = share_story(db, Act(AK, T0), gid, 1, "mine")
    react(db, ML, 1, "seen")
    others: list[Callable[[], object]] = [
        lambda: edit_comment(db, Act(ML, T0), 1, "x"),
        lambda: delete_comment(db, Act(ML, T0), 1),
    ]
    for call in others:
        with pytest.raises(Forbidden):
            call()
    delete_comment(db, Act(AK, T0 + timedelta(days=30)), 1)
    delete_comment(db, Act(AK, T0 + timedelta(days=30)), 1)
    c = read_thread(db, AK, tid, T0).comments[0]
    assert (c.removed, c.text, c.reactions, c.author) == (True, "", (), "ak")
    assert rows(db, "SELECT text FROM comments WHERE id=1") == [("",)]
    assert count(db, "reactions") == 0
    with pytest.raises(Forbidden):
        edit_comment(db, Act(AK, T0), 1, "back")
    with pytest.raises(StoreError):
        react(db, ML, 1, "agree")


def test_reactions_are_a_fixed_set_counted_per_key_and_idempotent(
    db: sqlite3.Connection, gid: int
) -> None:
    tid, _ = share_story(db, Act(AK, T0), gid, 1, "x")
    react(db, AK, 1, "agree")
    react(db, AK, 1, "agree")
    react(db, ML, 1, "agree")
    react(db, ML, 1, "seen")
    got = read_thread(db, AK, tid, T0).comments[0].reactions
    assert tuple((r.key, r.count, r.mine) for r in got) == (("agree", 2, True), ("seen", 1, False))
    assert REACTIONS == ("agree", "disagree", "seen")
    with pytest.raises(StoreError):
        react(db, AK, 1, "fire")
    for old in ("up", "eyes", "check", "question"):
        with pytest.raises(StoreError):
            react(db, AK, 1, old)
    unreact(db, ML, 1, "agree")
    unreact(db, ML, 1, "agree")
    got = read_thread(db, AK, tid, T0).comments[0].reactions
    assert tuple((r.key, r.count) for r in got) == (("agree", 1), ("seen", 1))


def test_thread_list_is_by_last_activity_and_pages_by_30(db: sqlite3.Connection, gid: int) -> None:
    for number in range(31):
        start_note(db, Act(AK, T0 + number * MIN), gid, f"note {number}", "x")
    add_comment(db, Act(ML, T0 + 60 * MIN), 1, "bump", None)
    first, cursor = thread_list(db, "rd", gid, None)
    assert [row.id for row in first][:2] == [1, 31] and len(first) == 30
    assert cursor is not None
    second, end = thread_list(db, "rd", gid, cursor)
    assert [row.id for row in second] == [2] and end is None
    assert first[0].kind == "note" and first[0].title == "note 0" and first[0].comments == 2
    assert first[0].unread is True and thread_list(db, "ak", gid, None)[0][1].unread is False


def test_a_story_thread_lists_the_story_title_and_source(db: sqlite3.Connection, gid: int) -> None:
    share_story(db, Act(AK, T0), gid, 2, None)
    ((row,), _) = thread_list(db, "ak", gid, None)
    assert (row.kind, row.title, row.source, row.comments) == ("story", "Story 2", "Source 2", 0)
    assert row.source_kind == "news"


def test_a_note_thread_row_has_no_source_kind(db: sqlite3.Connection, gid: int) -> None:
    start_note(db, Act(AK, T0), gid, "a note", "x")
    ((row,), _) = thread_list(db, "ak", gid, None)
    assert row.kind == "note" and row.source_kind is None


def test_a_malformed_cursor_is_refused(db: sqlite3.Connection, gid: int) -> None:
    with pytest.raises(feedview.ViewError):
        thread_list(db, "ak", gid, "nonsense")


def _topic_group(db: sqlite3.Connection) -> int:
    """A group carrying a topic, with ml a member, and the automatic thread for story 1."""
    gid = create_group(db, Act(AK, T0), "TMT", "everyone", [])
    join(db, "ml", gid, T0)
    _topic(db, (gid,))
    assert auto_post(db, 1, [1], T0 + MIN) == [1]
    return gid


def test_a_share_onto_an_automatic_thread_claims_it_like_any_share(db: sqlite3.Connection) -> None:
    gid = _topic_group(db)
    add_comment(db, Act(ML, T0 + 2 * MIN), 1, "already here", None)
    assert share_story(db, Act(AK, T0 + 3 * MIN), gid, 1, "Heavier than we assumed.") == (1, True)
    assert rows(db, "SELECT started_by FROM threads") == [("ak",)]
    thread = feedview.card_for(db, "ml", 1).threads[0]
    assert (thread.shared_by, thread.note, thread.comments) == (
        "ak",
        "Heavier than we assumed.",
        2,
    )
    assert [c.id for c in feedview.feed(db, "ml", "latest", shared=True).cards] == [1]
    assert unread(db, "ml") == Unread(0, 1, {gid: 1})
    view = read_thread(db, RD, 1, T0 + 4 * MIN)
    assert [(c.author, c.text) for c in view.comments] == [
        ("ml", "already here"),
        ("ak", "Heavier than we assumed."),
    ]


def test_a_share_without_a_note_still_claims_an_automatic_thread(db: sqlite3.Connection) -> None:
    gid = _topic_group(db)
    assert share_story(db, Act(AK, T0 + 2 * MIN), gid, 1, None) == (1, True)
    assert feedview.card_for(db, "ml", 1).threads[0].shared_by == "ak"
    assert count(db, "comments") == 0


def test_a_second_sharer_does_not_take_over_a_claimed_thread(db: sqlite3.Connection) -> None:
    gid = _topic_group(db)
    share_story(db, Act(AK, T0 + 2 * MIN), gid, 1, "first")
    assert share_story(db, Act(ML, T0 + 3 * MIN), gid, 1, "second") == (1, True)
    assert rows(db, "SELECT started_by FROM threads") == [("ak",)]
    thread = feedview.card_for(db, "rd", 1).threads[0]
    assert (thread.shared_by, thread.note) == ("ak", "first")


def test_auto_post_makes_one_unattributed_thread_per_matching_group(db: sqlite3.Connection) -> None:
    first = create_group(db, Act(AK, T0), "A", "everyone", [])
    second = create_group(db, Act(AK, T0), "B", "invited", [])
    _topic(db, (first, second))
    assert auto_post(db, 1, [1, 1], T0) == [1, 2]
    assert auto_post(db, 1, [1], T0) == []
    assert auto_post(db, 1, [], T0) == []
    assert auto_post(db, 999, [1], T0) == []
    assert rows(db, "SELECT group_id, story_id, started_by FROM threads ORDER BY id") == [
        (first, 1, None),
        (second, 1, None),
    ]


def test_unread_counts_new_threads_and_replies_and_clears_on_read(db: sqlite3.Connection) -> None:
    gid = create_group(db, Act(AK, T0), "TMT", "everyone", [])
    join(db, "ml", gid, T0)
    tid, _ = share_story(db, Act(AK, T0 + MIN), gid, 1, "look")  # comment 1
    assert unread(db, "ml") == Unread(0, 1, {gid: 1}) and unread(db, "ak") == Unread(0, 0, {})
    add_comment(db, Act(ML, T0 + 2 * MIN), tid, "reply to ak", 1)
    assert unread(db, "ak") == Unread(1, 0, {gid: 1})
    mark_read(db, "ak", tid)
    mark_read(db, "ml", tid)
    assert unread(db, "ak") == unread(db, "ml") == Unread(0, 0, {})


def test_threads_from_before_joining_and_automatic_threads_are_not_unread(
    db: sqlite3.Connection,
) -> None:
    gid = create_group(db, Act(AK, T0), "TMT", "everyone", [])
    share_story(db, Act(AK, T0 + MIN), gid, 1, "early")
    join(db, "ml", gid, T0 + 2 * MIN)
    assert unread(db, "ml") == Unread(0, 0, {})
    _topic(db, (gid,))
    assert auto_post(db, 2, [1], T0 + 3 * MIN) == [2]
    assert unread(db, "ml") == Unread(0, 0, {})


def test_a_removed_reply_and_my_own_reply_are_not_unread(db: sqlite3.Connection) -> None:
    gid = create_group(db, Act(AK, T0), "TMT", "everyone", [])
    tid, _ = share_story(db, Act(AK, T0 + MIN), gid, 1, "look")
    add_comment(db, Act(AK, T0 + 2 * MIN), tid, "my own reply", 1)
    reply = add_comment(db, Act(ML, T0 + 3 * MIN), tid, "reply to ak", 1)
    assert unread(db, "ak") == Unread(1, 0, {gid: 1})
    delete_comment(db, Act(ML, T0 + 4 * MIN), reply)
    assert unread(db, "ak") == Unread(0, 0, {})


def test_unread_never_counts_an_invited_group_after_removal_from_it(db: sqlite3.Connection) -> None:
    gid = create_group(db, Act(AK, T0), "Deal team", "invited", [])
    add_member(db, Act(AK, T0), gid, "ml")
    tid = start_note(db, Act(ML, T0 + MIN), gid, "note", "first")
    add_comment(db, Act(AK, T0 + 2 * MIN), tid, "reply to ml", 1)
    assert unread(db, "ml") == Unread(1, 0, {gid: 1})
    remove_member(db, AK, gid, "ml")
    assert unread(db, "ml") == Unread(0, 0, {})


def test_marking_a_hidden_thread_read_is_refused_and_a_mark_never_lowers(
    db: sqlite3.Connection,
) -> None:
    gid = create_group(db, Act(AK, T0), "Deal team", "invited", [])
    tid, _ = share_story(db, Act(AK, T0), gid, 1, "x")
    with pytest.raises(StoreError, match="no such thread"):
        mark_read(db, "ml", tid)
    with pytest.raises(StoreError, match="no such thread"):
        mark_read(db, "ak", 999)
    add_comment(db, Act(AK, T0 + MIN), tid, "second", None)
    mark_read(db, "ak", tid)
    db.execute("UPDATE read_marks SET seen_comment_id = 99")
    db.commit()
    mark_read(db, "ak", tid)
    assert rows(db, "SELECT seen_comment_id FROM read_marks") == [(99,)]


def test_thread_row_unread_follows_marks_and_other_authors(
    db: sqlite3.Connection, gid: int
) -> None:
    tid, _ = share_story(db, Act(AK, T0), gid, 1, "x")

    def flags(who: str) -> list[bool]:
        return [r.unread for r in thread_list(db, who, gid, None)[0]]

    assert flags("ak") == [False] and flags("ml") == [True]  # new to ml; ak started it
    mark_read(db, "ml", tid)
    assert flags("ml") == [False]
    add_comment(db, Act(ML, T0 + MIN), tid, "y", None)
    assert flags("ml") == [False] and flags("ak") == [True]


def test_new_thread_flags_in_a_list_match_the_unread_count(db: sqlite3.Connection) -> None:
    gid = create_group(db, Act(AK, T0), "TMT", "everyone", [])
    join(db, "ml", gid, T0)
    share_story(db, Act(AK, T0 + MIN), gid, 1, None)
    opened, _ = share_story(db, Act(AK, T0 + 2 * MIN), gid, 2, "note")
    start_note(db, Act(ML, T0 + 3 * MIN), gid, "mine", "own")
    mark_read(db, "ml", opened)
    flagged = [r for r in thread_list(db, "ml", gid, None)[0] if r.unread]
    assert [r.id for r in flagged] == [1]
    assert len(flagged) == unread(db, "ml").by_group[gid] == unread(db, "ml").threads
