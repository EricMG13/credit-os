"""Groups: what is stored and what is said (S-5 review T2, B2), and the rulings on topics, names,
bad input and member order."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta, timezone
from functools import partial
from pathlib import Path
from typing import Any

import pytest

from credit_os.signal import groups
from credit_os.signal.groups import (
    Act,
    Forbidden,
    _name_key,
    add_member,
    can_manage,
    can_see,
    create_group,
    join,
    leave,
    list_groups,
    may_post,
    members,
    remove_member,
    require_visible,
    visible_group_ids,
)
from credit_os.signal.identity import MAX_NAME, User
from credit_os.signal.store import StoreError, add_user, open_db
from credit_os.signal.topics import add_topic

AK = User("ak", "writer")
ML = User("ml", "writer")
RD = User("rd", "reader")
OW = User("ow", "owner")
T0 = datetime(2026, 11, 13, 9, tzinfo=UTC)
T0_TEXT = "2026-11-13T09:00:00+00:00"
PLUS2 = datetime(2026, 11, 13, 11, tzinfo=timezone(timedelta(hours=2)))  # the instant of T0
BLANK = "\ufe00\u115f"  # a variation selector and a Hangul filler: both draw nothing

_COUNTS = {
    "groups": "SELECT count(*) FROM groups",
    "group_members": "SELECT count(*) FROM group_members",
    "group_topics": "SELECT count(*) FROM group_topics",
}


def count(db: sqlite3.Connection, table: str) -> int:
    return int(db.execute(_COUNTS[table]).fetchone()[0])


def rows(db: sqlite3.Connection, sql: str, *params: Any) -> list[tuple[Any, ...]]:
    return [tuple(r) for r in db.execute(sql, params).fetchall()]


@pytest.fixture
def db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    handle = open_db(tmp_path)
    for user in (AK, ML, RD, OW):
        add_user(handle, user.name, user.role)
    yield handle
    handle.close()


def _joined_at(db: sqlite3.Connection, gid: int, name: str) -> str:
    found = rows(
        db, "SELECT joined_at FROM group_members WHERE group_id=? AND user_name=?", gid, name
    )
    return str(found[0][0])


def test_times_are_stored_as_utc_text(db: sqlite3.Connection) -> None:
    gid = create_group(db, Act(AK, PLUS2), "Deal team", "everyone", [])
    assert rows(db, "SELECT created_at FROM groups WHERE id=?", gid) == [(T0_TEXT,)]
    join(db, "zz", gid, PLUS2)
    add_member(db, Act(AK, PLUS2), gid, "yy")
    assert [_joined_at(db, gid, who) for who in ("ak", "zz", "yy")] == [T0_TEXT] * 3


def test_a_second_join_or_add_keeps_the_first_join_time(db: sqlite3.Connection) -> None:
    gid = create_group(db, Act(AK, T0), "Open A", "everyone", [])
    join(db, "rd", gid, T0)
    join(db, "rd", gid, T0 + timedelta(hours=5))
    add_member(db, Act(AK, T0 + timedelta(hours=1)), gid, "ml")
    add_member(db, Act(AK, T0 + timedelta(hours=7)), gid, "ml")
    assert _joined_at(db, gid, "rd") == T0_TEXT
    assert _joined_at(db, gid, "ml") == "2026-11-13T10:00:00+00:00"


@pytest.mark.parametrize(
    "name,visibility,topics",
    [
        ("", "everyone", []),
        ("x" * 61, "everyone", []),
        ("ok", "secret", []),
        ("ok", "everyone", [99]),
    ],
)
def test_a_reader_is_forbidden_before_the_input_is_judged(
    db: sqlite3.Connection, name: str, visibility: str, topics: list[int]
) -> None:
    with pytest.raises(Forbidden, match="^only writers and the owner can create groups$"):
        create_group(db, Act(RD, T0), name, visibility, topics)
    assert rows(db, "SELECT count(*) FROM groups") == [(0,)]


def test_forbidden_is_not_a_store_error_and_says_what_each_writer_needs(
    db: sqlite3.Connection,
) -> None:
    assert not issubclass(Forbidden, StoreError)
    gid = create_group(db, Act(AK, T0), "Deal team", "invited", [])
    add_member(db, Act(AK, T0), gid, "rd")
    with pytest.raises(Forbidden, match="^only writers and the owner can manage members$"):
        add_member(db, Act(RD, T0), gid, "x")
    with pytest.raises(Forbidden, match="^only writers and the owner can manage members$"):
        remove_member(db, RD, gid, "ak")


def test_require_visible_returns_the_whole_group_row(db: sqlite3.Connection) -> None:
    gid = create_group(db, Act(AK, PLUS2), "Deal team", "invited", [])
    row = require_visible(db, "ak", gid)
    assert row.keys() == ["id", "name", "name_key", "visibility", "created_by", "created_at"]
    assert tuple(row) == (gid, "Deal team", "deal team", "invited", "ak", T0_TEXT)


def test_the_name_key_folds_compatibility_forms_before_case(db: sqlite3.Connection) -> None:
    assert _name_key("\u1d2c desk") == "a desk"  # U+1D2C MODIFIER LETTER CAPITAL A is "A" in NFKC
    create_group(db, Act(AK, T0), "\u1d2c desk", "everyone", [])
    with pytest.raises(StoreError, match="^that group name is taken$"):
        create_group(db, Act(ML, T0), "a desk", "everyone", [])


def _deny_group_inserts(
    action: int, arg1: str | None, arg2: str | None, db_name: str | None, source: str | None
) -> int:
    if action == sqlite3.SQLITE_INSERT and arg1 == "groups":
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def test_a_database_failure_on_the_insert_is_not_a_taken_name(db: sqlite3.Connection) -> None:
    db.set_authorizer(_deny_group_inserts)  # SQLite itself refuses the INSERT: a real failure
    try:
        with pytest.raises(sqlite3.DatabaseError, match="not authorized") as caught:
            create_group(db, Act(AK, T0), "Brand new", "everyone", [])
    finally:
        db.set_authorizer(None)
    assert not isinstance(caught.value, StoreError)
    assert not db.in_transaction
    assert rows(db, "SELECT count(*) FROM groups") == [(0,)]


def test_an_operational_error_on_the_insert_is_not_a_taken_name(
    db: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    def full(name: str) -> str:
        raise sqlite3.OperationalError("database or disk is full")

    monkeypatch.setattr(groups, "_name_key", full)  # evaluated inside the insert's try block
    with pytest.raises(sqlite3.OperationalError, match="^database or disk is full$") as caught:
        create_group(db, Act(AK, T0), "Brand new", "everyone", [])
    assert not isinstance(caught.value, StoreError)
    assert rows(db, "SELECT count(*) FROM groups") == [(0,)]


@pytest.mark.parametrize("other", ["AK", "Ak", "a", "k", "%", "a_", "_k", "a%", "*", "a*", "?k"])
def test_a_user_name_is_matched_exactly_by_every_visibility_statement(
    db: sqlite3.Connection, other: str
) -> None:
    hidden = create_group(db, Act(AK, T0), "Deal team", "invited", [])
    assert can_see(db, other, hidden) is False
    assert visible_group_ids(db, other) == []
    assert list_groups(db, other) == []
    with pytest.raises(StoreError, match="^no such group$"):
        members(db, other, hidden)


@pytest.mark.parametrize("other", ["AK", "%", "_k", "a%", "*", "a*", "?k"])
def test_the_member_flag_and_a_removal_match_a_user_name_exactly(
    db: sqlite3.Connection, other: str
) -> None:
    open_a = create_group(db, Act(AK, T0), "Open A", "everyone", [])
    join(db, "rd", open_a, T0)
    assert [r["member"] for r in list_groups(db, other)] == [0]
    leave(db, other, open_a)
    remove_member(db, AK, open_a, other)
    assert members(db, "ak", open_a) == ["ak", "rd"]


# ---- topics through json_each --------------------------------------------------------------


def test_a_group_links_its_topics_once(db: sqlite3.Connection) -> None:
    first = add_topic(db, "Rates", ["rate"], [], "ak")
    second = add_topic(db, "Credit", ["credit"], [], "ak")
    gid = create_group(db, Act(AK, T0), "Desk", "everyone", [second, first, second])
    assert sorted(rows(db, "SELECT topic_id FROM group_topics WHERE group_id=?", gid)) == [
        (first,),
        (second,),
    ]


def test_a_missing_topic_is_named_and_nothing_is_written(db: sqlite3.Connection) -> None:
    topic = add_topic(db, "Rates", ["rate"], [], "ak")
    with pytest.raises(StoreError, match="^no topic with id 4242$"):
        create_group(db, Act(AK, T0), "Desk", "everyone", [topic, 4242])
    assert count(db, "groups") == 0 and count(db, "group_topics") == 0


@pytest.mark.parametrize("topics", [[2**63], [-(2**63) - 1], [10**5000]])
def test_a_topic_id_outside_the_range_is_refused_without_its_digits(
    db: sqlite3.Connection, topics: list[int]
) -> None:
    with pytest.raises(StoreError, match="^no topic with that id$"):
        create_group(db, Act(AK, T0), "Desk", "everyone", topics)
    assert count(db, "groups") == 0


# ---- names ---------------------------------------------------------------------------------


@pytest.mark.parametrize("name", [BLANK, BLANK * 20, " " + BLANK + " ", "\u2800\u3164", "\x00\x01"])
def test_a_group_name_of_nothing_visible_is_refused(db: sqlite3.Connection, name: str) -> None:
    with pytest.raises(StoreError, match="^a group name must not be empty$"):
        create_group(db, Act(AK, T0), name, "everyone", [])
    assert count(db, "groups") == 0


def test_invisible_characters_are_dropped_from_a_group_name(db: sqlite3.Connection) -> None:
    gid = create_group(db, Act(AK, T0), "TMT" + BLANK + " desk", "everyone", [])
    assert rows(db, "SELECT name FROM groups WHERE id=?", gid) == [("TMT desk",)]
    with pytest.raises(StoreError, match="^that group name is taken$"):
        create_group(db, Act(ML, T0), "tmt desk", "everyone", [])


def test_the_group_name_limit_is_its_own_and_is_sixty(db: sqlite3.Connection) -> None:
    assert groups.MAX_GROUP_NAME == 60 == MAX_NAME
    assert not hasattr(groups, "MAX_NAME")
    create_group(db, Act(AK, T0), "g" * 60, "everyone", [])
    with pytest.raises(StoreError, match="^a group name is at most 60 characters$"):
        create_group(db, Act(AK, T0), "h" * 61, "everyone", [])


@pytest.mark.parametrize("name", ["", " ml ", "ml" + BLANK, "m\x00l", "x" * (MAX_NAME + 1), "a  b"])
def test_member_names_must_be_clean_names(db: sqlite3.Connection, name: str) -> None:
    gid = create_group(db, Act(AK, T0), "Deal", "everyone", [])  # open: join reaches the name check
    with pytest.raises(StoreError):
        add_member(db, Act(AK, T0), gid, name)
    with pytest.raises(StoreError):
        remove_member(db, AK, gid, name)
    with pytest.raises(StoreError):
        join(db, name, gid, T0)
    assert members(db, "ak", gid) == ["ak"]


@pytest.mark.parametrize("creator", [" ak", "ak" + BLANK, "", "k" * (MAX_NAME + 1)])
def test_a_creator_name_must_be_a_clean_name(db: sqlite3.Connection, creator: str) -> None:
    with pytest.raises(StoreError):
        create_group(db, Act(User(creator, "writer"), T0), "Desk", "everyone", [])
    assert count(db, "groups") == 0


# ---- R15, R10: bad input is a StoreError and carries little of the input -------------------

_HUGE = "Q" * 5000
_LONE = "\ud800"


def _anything(value: object) -> Any:
    """`value` with its type forgotten, so a test can hand a call the wrong kind of thing."""
    return value


class _AlwaysEqual:
    """Not text, and equal to every value: only a check of the type refuses it."""

    def __eq__(self, other: object) -> bool:
        return True

    def __hash__(self) -> int:
        return hash("everyone")


class _EqualsEveryone:
    """Not text, and equal to the visibility "everyone"."""

    def __eq__(self, other: object) -> bool:
        return other == "everyone"

    def __hash__(self) -> int:
        return hash("everyone")


def _bad_calls(db: sqlite3.Connection, gid: int) -> list[Callable[[], object]]:
    bad_ids: list[Any] = ["1", None, 1.5, True, [1]]
    calls: list[Callable[[], object]] = []
    for bad in bad_ids:
        calls += [
            partial(can_see, db, "ak", bad),
            partial(require_visible, db, "ak", bad),
            partial(members, db, "ak", bad),
            partial(join, db, "ak", bad, T0),
            partial(leave, db, "ak", bad),
            partial(add_member, db, Act(AK, T0), bad, "x"),
            partial(remove_member, db, AK, bad, "x"),
            partial(can_manage, db, AK, bad),
            partial(can_manage, db, RD, bad),  # a non-writer: the id is judged before the role
        ]
    bad_users: list[Any] = [None, "ak", Act(AK, T0), 7, ("ak", "writer")]
    for bad in bad_users:
        calls += [partial(may_post, bad), partial(can_manage, db, bad, gid)]
    bad_texts: list[Any] = [None, 5, b"ak", _LONE, ["ak"]]
    for bad in bad_texts:
        calls += [
            partial(can_see, db, bad, gid),
            partial(list_groups, db, bad),
            partial(members, db, bad, gid),
            partial(join, db, bad, gid, T0),
            partial(leave, db, bad, gid),
            partial(add_member, db, Act(AK, T0), gid, bad),
            partial(remove_member, db, AK, gid, bad),
            partial(create_group, db, Act(AK, T0), bad, "everyone", []),
            partial(visible_group_ids, db, bad),
            partial(can_manage, db, User(bad, "reader"), gid),
            partial(can_manage, db, User(bad, "writer"), gid),
        ]
    bad_visibilities: list[Any] = [
        None,
        5,
        _HUGE,
        _LONE,
        ["everyone"],
        _AlwaysEqual(),
        _EqualsEveryone(),
    ]
    for bad in bad_visibilities:
        calls.append(partial(create_group, db, Act(AK, T0), "N", bad, []))
    bad_topics: list[Any] = ["12", 12, None, [None], ["1"], [1.5], [True], [[1]], [_LONE]]
    for bad in bad_topics:
        calls.append(partial(create_group, db, Act(AK, T0), "N", "everyone", bad))
    bad_acts: list[Any] = [
        None,
        "ak",
        AK,
        Act(_anything("ak"), T0),
        Act(AK, _anything(None)),
        Act(AK, _anything("now")),
    ]
    for bad in bad_acts:
        calls.append(partial(create_group, db, bad, "N", "everyone", []))
        calls.append(partial(add_member, db, bad, gid, "x"))
    naive = T0.replace(tzinfo=None)
    calls += [
        lambda: create_group(db, Act(AK, naive), "N", "everyone", []),
        lambda: join(db, "ak", gid, naive),
        lambda: join(db, "ak", gid, _anything(None)),
        lambda: remove_member(db, _anything("ak"), gid, "x"),
        lambda: create_group(db, Act(User(_LONE, "writer"), T0), "N", "everyone", []),
        lambda: add_member(db, Act(User(_LONE, "writer"), T0), gid, "x"),
        lambda: remove_member(db, User(_anything(None), "writer"), gid, "x"),
    ]
    return calls


def test_bad_input_is_a_short_store_error_and_writes_nothing(db: sqlite3.Connection) -> None:
    gid = create_group(db, Act(AK, T0), "Open", "everyone", [])
    before = tuple(count(db, t) for t in _COUNTS)
    calls = _bad_calls(db, gid)
    assert len(calls) > 100
    for call in calls:
        with pytest.raises(StoreError) as caught:
            call()
        text = str(caught.value)
        assert type(caught.value) is StoreError
        assert len(text) <= 120 and "QQQQ" not in text
    assert tuple(count(db, t) for t in _COUNTS) == before


def test_an_oversized_name_is_refused_with_a_message_free_of_it(db: sqlite3.Connection) -> None:
    with pytest.raises(StoreError) as caught:
        create_group(db, Act(AK, T0), _HUGE, "everyone", [])
    assert "QQQQ" not in str(caught.value)
    with pytest.raises(StoreError) as caught:
        add_member(db, Act(AK, T0), 1, _HUGE)
    assert "QQQQ" not in str(caught.value)


def test_a_time_the_database_cannot_hold_is_a_store_error(db: sqlite3.Connection) -> None:
    far = datetime(1, 1, 1, tzinfo=timezone(timedelta(hours=14)))
    with pytest.raises(StoreError):
        create_group(db, Act(AK, far), "Early", "everyone", [])
    assert count(db, "groups") == 0


def test_the_new_group_id_comes_from_new_row_id_and_a_refusal_there_rolls_back(
    db: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(cur: sqlite3.Cursor) -> int:
        raise StoreError("the database did not report the new row's id")

    monkeypatch.setattr(groups, "new_row_id", refuse)
    with pytest.raises(StoreError, match="did not report"):
        create_group(db, Act(AK, T0), "Desk", "everyone", [])
    assert count(db, "groups") == 0 and count(db, "group_members") == 0


# ---- topics: what counts as an id, and which missing one is named ----------------------------


def test_a_boolean_is_not_a_topic_id_even_when_topic_one_exists(db: sqlite3.Connection) -> None:
    assert add_topic(db, "Rates", ["rate"], [], "ak") == 1
    with pytest.raises(StoreError, match="^topic id must be an integer$"):
        create_group(db, Act(AK, T0), "Booly", "everyone", [_anything(True)])
    assert count(db, "groups") == 0 and count(db, "group_topics") == 0


@pytest.mark.parametrize(("topics", "named"), [([7, 8], 7), ([8, 7], 8), ([9, 7, 8], 9)])
def test_the_first_missing_topic_in_list_order_is_named(
    db: sqlite3.Connection, topics: list[int], named: int
) -> None:
    with pytest.raises(StoreError, match=f"^no topic with id {named}$"):
        create_group(db, Act(AK, T0), "Desk", "everyone", topics)


# ---- members come in the order they joined ---------------------------------------------------


def test_members_are_listed_by_join_time_then_by_insertion(db: sqlite3.Connection) -> None:
    gid = create_group(db, Act(AK, T0 + timedelta(hours=2)), "Late desk", "everyone", [])
    add_member(db, Act(AK, T0 + timedelta(hours=1)), gid, "ml")  # inserted later, joined earlier
    add_member(db, Act(AK, T0 + timedelta(hours=1)), gid, "rd")  # same time: insertion order
    assert members(db, "ak", gid) == ["ml", "rd", "ak"]


# ---- the order of refusals: hidden group first, then role, then the name ---------------------


def test_a_hidden_group_is_refused_as_missing_before_a_bad_member_name_is_judged(
    db: sqlite3.Connection,
) -> None:
    hidden = create_group(db, Act(AK, T0), "Deal team", "invited", [])
    for call in (
        lambda: add_member(db, Act(ML, T0), hidden, " ml "),
        lambda: remove_member(db, ML, hidden, " ml "),
    ):
        with pytest.raises(StoreError, match="^no such group$"):
            call()


def test_a_reader_member_is_forbidden_before_a_bad_member_name_is_judged(
    db: sqlite3.Connection,
) -> None:
    gid = create_group(db, Act(AK, T0), "Deal team", "invited", [])
    add_member(db, Act(AK, T0), gid, "rd")
    with pytest.raises(Forbidden):
        add_member(db, Act(RD, T0), gid, " x ")
    with pytest.raises(Forbidden):
        remove_member(db, RD, gid, " x ")
