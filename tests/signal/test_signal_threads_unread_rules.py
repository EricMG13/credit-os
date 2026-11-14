"""Threads under the port's rulings, part 2: reactions, lists, read marks, unread counts and
automatic posts against a Python oracle that shares no code with the module, result order and
page boundaries, hidden == missing, wrong types (R2, R15, R21, R22, P17 and its Low R1).

Expected values are written by hand or by the oracle below; none is computed with the code
under test.
"""

from __future__ import annotations

import random
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Any

import pytest
from feedview_grid import thread
from threads_support import AK, MIN, ML, RD, T0, count, rows, team_db

from credit_os.signal.groups import Act, Forbidden, NotFound, create_group, join
from credit_os.signal.identity import User
from credit_os.signal.store import StoreError, StoreUnusable, read_snapshot
from credit_os.signal.threads import (
    PAGE,
    Unread,
    auto_post,
    mark_read,
    react,
    share_story,
    thread_list,
    unreact,
    unread,
)

NAMES = ("ak", "ml", "rd", "zz")
REGISTERED = ("ak", "ml", "rd")  # the users rows team_db writes; zz has none


def bad(value: object) -> Any:
    """A value of the wrong type, hidden from the type checker (the callee must refuse it)."""
    return value


def at(minute: int) -> str:
    return (T0 + minute * MIN).isoformat()


@dataclass
class World:
    """What the oracle knows, in plain Python: nothing here is read back from the database."""

    open_group: dict[int, bool] = field(default_factory=dict)
    joined: dict[int, dict[str, int]] = field(default_factory=dict)
    threads: dict[int, tuple[int, str | None, int, int]] = field(default_factory=dict)
    comments: dict[int, tuple[int, str, int | None, bool]] = field(default_factory=dict)
    seen: dict[tuple[str, int], int] = field(default_factory=dict)

    def visible(self, name: str, gid: int) -> bool:
        return self.open_group[gid] or name in self.joined[gid]


def _world(db: sqlite3.Connection, seed: int) -> World:
    """Three groups, nine threads, comments with one level of replies, marks: all random, all
    written by plain SQL. Times are minutes after T0, so string order is time order."""
    rng = random.Random(seed)
    world = World()
    for gid in (1, 2, 3):
        world.open_group[gid] = rng.random() < 0.5
        world.joined[gid] = {n: rng.randrange(0, 4) for n in NAMES if rng.random() < 0.6}
        db.execute(
            "INSERT INTO groups(id, name, name_key, visibility, created_by, created_at)"
            " VALUES(?, ?, ?, ?, 'ak', ?)",
            (gid, f"g{gid}", f"g{gid}", "everyone" if world.open_group[gid] else "invited", at(0)),
        )
        for name, minute in world.joined[gid].items():
            db.execute(
                "INSERT INTO group_members(group_id, user_name, joined_at) VALUES(?, ?, ?)",
                (gid, name, at(minute)),
            )
    for tid in range(1, 10):
        gid = (tid - 1) % 3 + 1
        starter = rng.choice((None, *NAMES))
        made, last = rng.randrange(0, 6), rng.randrange(0, 6)
        world.threads[tid] = (gid, starter, made, last)
        db.execute(
            "INSERT INTO threads(id, group_id, title, started_by, created_at, last_activity_at)"
            " VALUES(?, ?, 'n', ?, ?, ?)",
            (tid, gid, starter, at(made), at(last)),
        )
        tops: list[int] = []
        for _ in range(rng.randrange(0, 5)):
            cid = len(world.comments) + 1
            parent = rng.choice(tops) if tops and rng.random() < 0.5 else None
            author, gone = rng.choice(NAMES), rng.random() < 0.2
            world.comments[cid] = (tid, author, parent, gone)
            if parent is None:
                tops.append(cid)
            db.execute(
                "INSERT INTO comments(id, thread_id, parent_id, author, text, created_at,"
                " deleted_at) VALUES(?, ?, ?, ?, 'c', ?, ?)",
                (cid, tid, parent, author, at(0), at(1) if gone else None),
            )
    for name in NAMES:
        for tid in world.threads:
            if rng.random() < 0.3:
                world.seen[(name, tid)] = rng.randrange(0, len(world.comments) + 1)
                db.execute(
                    "INSERT INTO read_marks(user_name, thread_id, seen_comment_id) VALUES(?, ?, ?)",
                    (name, tid, world.seen[(name, tid)]),
                )
    db.commit()
    return world


def _new(world: World, name: str, tid: int) -> bool:
    gid, starter, made, _ = world.threads[tid]
    return (
        starter is not None
        and starter != name
        and name in world.joined[gid]
        and made >= world.joined[gid][name]
        and (name, tid) not in world.seen
    )


def _unread_replies(world: World, name: str, gid: int) -> int:
    total = 0
    for cid, (tid, author, parent, gone) in world.comments.items():
        if world.threads[tid][0] != gid or gone or author == name or parent is None:
            continue
        if world.comments[parent][1] == name and cid > world.seen.get((name, tid), 0):
            total += 1
    return total


@pytest.mark.parametrize("seed", range(12))
def test_unread_counts_match_the_oracle(tmp_path: Path, seed: int) -> None:
    db = team_db(tmp_path)
    world = _world(db, seed)
    for name in NAMES:
        by_group: dict[int, int] = {}
        replies = threads = 0
        for gid in (1, 2, 3):
            fresh = sum(
                1 for tid, t in world.threads.items() if t[0] == gid and _new(world, name, tid)
            )
            answered = _unread_replies(world, name, gid) if world.visible(name, gid) else 0
            replies, threads = replies + answered, threads + fresh
            if fresh + answered:
                by_group[gid] = fresh + answered
        assert unread(db, name) == Unread(replies, threads, by_group), (seed, name)
    db.close()


@pytest.mark.parametrize("seed", range(12))
def test_lists_read_marks_and_reactions_match_the_oracle(tmp_path: Path, seed: int) -> None:
    db = team_db(tmp_path)
    world = _world(db, seed)
    for name in NAMES:
        for gid in (1, 2, 3):
            if not world.visible(name, gid):
                with pytest.raises(NotFound):
                    thread_list(db, name, gid, None)
                continue
            ids = sorted(
                (t for t, v in world.threads.items() if v[0] == gid),
                key=lambda t: (world.threads[t][3], t),
                reverse=True,
            )
            page, cursor = thread_list(db, name, gid, None)
            assert [row.id for row in page] == ids and cursor is None
            for row in page:
                live = [
                    c for c, (t, a, _, gone) in world.comments.items() if t == row.id and not gone
                ]
                newer = any(
                    world.comments[c][1] != name and c > world.seen.get((name, row.id), 0)
                    for c in live
                )
                assert row.comments == len(live)
                assert row.unread == (_new(world, name, row.id) or newer), (seed, name, row.id)
    for name in NAMES:
        for tid, (gid, _, _, _) in world.threads.items():
            if not world.visible(name, gid):
                with pytest.raises(NotFound):
                    mark_read(db, name, tid)
                continue
            mark_read(db, name, tid)
            newest = max((c for c, v in world.comments.items() if v[0] == tid), default=0)
            world.seen[(name, tid)] = max(world.seen.get((name, tid), 0), newest)
    got = {
        (r[0], r[1]): r[2]
        for r in rows(db, "SELECT user_name, thread_id, seen_comment_id FROM read_marks")
    }
    assert got == world.seen
    for name in NAMES:
        user = User(name, "reader" if name == "rd" else "writer")
        for cid, (tid, _, _, gone) in world.comments.items():
            gid = world.threads[tid][0]
            for key in ("agree", "seen"):
                call = partial(react, db, user, cid, key)
                if not world.visible(name, gid):
                    with pytest.raises(NotFound):
                        call()
                elif name not in REGISTERED:  # R54 L3: a reaction needs a users row
                    with pytest.raises(Forbidden):
                        call()
                    with pytest.raises(Forbidden):
                        partial(unreact, db, user, cid, key)()
                elif gone:
                    with pytest.raises(StoreError, match="removed"):
                        call()
                else:
                    call()
                    assert (cid, name, key) in rows(
                        db, "SELECT comment_id, user_name, key FROM reactions"
                    )
                    unreact(db, user, cid, key)
                    assert (cid, name, key) not in rows(
                        db, "SELECT comment_id, user_name, key FROM reactions"
                    )
    db.close()


@pytest.mark.parametrize("total", [0, 1, PAGE - 1, PAGE, PAGE + 1, 2 * PAGE, 2 * PAGE + 1])
def test_thread_list_pages_in_the_oracles_order_with_ties(tmp_path: Path, total: int) -> None:
    db = team_db(tmp_path)
    gid = create_group(db, Act(AK, T0), "TMT", "everyone", [])
    rng = random.Random(total)
    made = {}
    for number in range(1, total + 1):
        made[number] = rng.randrange(0, 8)  # many ties in last activity
        db.execute(
            "INSERT INTO threads(id, group_id, title, started_by, created_at, last_activity_at)"
            " VALUES(?, ?, 'n', 'ak', ?, ?)",
            (number, gid, at(0), at(made[number])),
        )
    db.commit()
    want = sorted(made, key=lambda n: (made[n], n), reverse=True)
    walked: list[int] = []
    cursor = None
    pages = 0
    while True:
        page, cursor = thread_list(db, "rd", gid, cursor)
        pages += 1
        assert len(page) <= PAGE
        walked += [row.id for row in page]
        if cursor is None:
            break
    assert walked == want
    assert pages == max(1, -(-total // PAGE))
    db.close()


def test_hidden_and_missing_look_the_same_for_every_thread_read_and_write(
    tmp_path: Path,
) -> None:
    db = team_db(tmp_path)
    gid = create_group(db, Act(AK, T0), "Deal team", "invited", [])
    tid, _ = share_story(db, Act(AK, T0), gid, 1, "private")
    for who in (ML, RD):
        for hidden, missing in (
            (
                partial(thread_list, db, who.name, gid, None),
                partial(thread_list, db, who.name, 999, None),
            ),
            (partial(mark_read, db, who.name, tid), partial(mark_read, db, who.name, 999)),
            (partial(mark_read, db, who.name, tid), partial(mark_read, db, who.name, 2**70)),
            (partial(react, db, who, 1, "agree"), partial(react, db, who, 999, "agree")),
            (partial(react, db, who, 1, "agree"), partial(react, db, who, 2**70, "agree")),
            (partial(unreact, db, who, 1, "agree"), partial(unreact, db, who, 999, "agree")),
        ):
            with pytest.raises(NotFound) as first:
                hidden()
            with pytest.raises(NotFound) as second:
                missing()
            assert str(first.value) == str(second.value)
    assert count(db, "reactions") == 0 and count(db, "read_marks") == 0
    db.close()


def test_a_member_who_joined_between_the_automatic_post_and_the_claim_sees_a_new_thread(
    tmp_path: Path,
) -> None:
    db = team_db(tmp_path)
    gid = create_group(db, Act(AK, T0), "TMT", "everyone", [])
    db.execute(
        "INSERT INTO topics(name, keywords, kinds, created_by, created_at)"
        " VALUES('x', '[]', '[]', 'ak', 'now')"
    )
    db.execute("INSERT INTO group_topics(group_id, topic_id) VALUES(?, 1)", (gid,))
    db.commit()
    assert auto_post(db, 1, [1], T0 + MIN) == [1]
    join(db, "ml", gid, T0 + 2 * MIN)  # after the automatic post
    assert unread(db, "ml") == Unread(0, 0, {})
    share_story(db, Act(AK, T0 + 3 * MIN), gid, 1, "claimed")
    assert unread(db, "ml") == Unread(0, 1, {gid: 1})
    join(db, "rd", gid, T0 + 4 * MIN)  # after the claim: not new to rd
    assert unread(db, "rd") == Unread(0, 0, {})
    db.close()


def test_a_member_who_read_the_automatic_thread_gets_no_new_count_from_the_claim(
    tmp_path: Path,
) -> None:
    db = team_db(tmp_path)
    gid = create_group(db, Act(AK, T0), "TMT", "everyone", [])
    join(db, "ml", gid, T0)
    thread(db, gid, 1, None)
    mark_read(db, "ml", 1)
    share_story(db, Act(AK, T0 + MIN), gid, 1, None)
    assert unread(db, "ml") == Unread(0, 0, {})
    db.close()


def test_the_sqlite_build_has_the_json_functions_the_statements_use() -> None:
    with sqlite3.connect(":memory:") as db:
        assert db.execute("SELECT sum(value) FROM json_each('[1, 2, 3]')").fetchone()[0] == 6


@pytest.mark.parametrize(
    "call",
    [
        lambda db: thread_list(db, bad(5), 1, None),
        lambda db: thread_list(db, "ak", bad("1"), None),
        lambda db: thread_list(db, "ak", bad(True), None),
        lambda db: thread_list(db, "ak", 1, bad(5)),
        lambda db: thread_list(db, "a\x00b", 1, None),
        lambda db: thread_list(db, "x" * 61, 1, None),
        lambda db: mark_read(db, bad(None), 1),
        lambda db: mark_read(db, "ak", bad("1")),
        lambda db: mark_read(db, "ak", bad(True)),
        lambda db: unread(db, bad(None)),
        lambda db: unread(db, ""),
        lambda db: react(db, bad("ak"), 1, "agree"),
        lambda db: react(db, AK, bad("1"), "agree"),
        lambda db: react(db, AK, 1, bad(5)),
        lambda db: react(db, AK, 1, "y" * 5000),
        lambda db: unreact(db, AK, 1, bad(None)),
        lambda db: unreact(db, User("a\x00b", "writer"), 1, "agree"),
        lambda db: auto_post(db, bad("1"), [1], T0),
        lambda db: auto_post(db, 1, bad("1"), T0),
        lambda db: auto_post(db, 1, [bad("1")], T0),
        lambda db: auto_post(db, 1, [bad(True)], T0),
        lambda db: auto_post(db, 1, [2**70], T0),
        lambda db: auto_post(db, 1, [1], bad("now")),
        lambda db: auto_post(db, 1, [1], T0.replace(tzinfo=None)),
    ],
    ids=[f"row{n}" for n in range(24)],
)
def test_wrong_types_are_a_store_error_and_leave_no_transaction(
    tmp_path: Path, call: Callable[[sqlite3.Connection], Any]
) -> None:
    db = team_db(tmp_path)
    create_group(db, Act(AK, T0), "TMT", "everyone", [])
    thread(db, 1, 1, "ak")
    with pytest.raises(StoreError) as caught:
        call(db)
    assert len(str(caught.value)) < 120
    assert not db.in_transaction
    db.close()


def test_the_readers_and_writers_refuse_to_run_inside_a_foreign_transaction(
    tmp_path: Path,
) -> None:
    db = team_db(tmp_path)
    gid = create_group(db, Act(AK, T0), "TMT", "everyone", [])
    thread(db, gid, 1, "ak")
    for call in (
        partial(thread_list, db, "ak", gid, None),
        partial(unread, db, "ak"),
        partial(mark_read, db, "ak", 1),
        partial(react, db, AK, 1, "agree"),
        partial(auto_post, db, 1, [1], T0),
    ):
        with read_snapshot(db), pytest.raises(StoreUnusable):
            call()
        assert not db.in_transaction
    assert count(db, "read_marks") == 0 and count(db, "reactions") == 0
    db.close()


def test_a_non_member_may_react_to_a_comment_in_an_open_group(tmp_path: Path) -> None:
    """Accepted (R22, R52 Q5): visibility alone decides, so an open group needs no membership."""
    db = team_db(tmp_path)
    gid = create_group(db, Act(AK, T0), "TMT", "everyone", [])
    share_story(db, Act(AK, T0), gid, 1, "x")
    assert rows(db, "SELECT user_name FROM group_members WHERE group_id=?", gid) == [("ak",)]
    react(db, ML, 1, "agree")
    assert rows(db, "SELECT user_name, key FROM reactions") == [("ml", "agree")]
    unreact(db, ML, 1, "agree")
    assert count(db, "reactions") == 0
    db.close()
