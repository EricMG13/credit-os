"""Groups: the rulings of the port (R1, R2, R13, R15, R22, R27, R29, R32, R33), not carried."""

from __future__ import annotations

import ast
import sqlite3
import tempfile
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.signal import groups
from credit_os.signal.groups import (
    Act,
    Forbidden,
    NotFound,
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
from credit_os.signal.identity import User
from credit_os.signal.store import StoreError, StoreUnusable, add_user, open_db, write_transaction
from credit_os.signal.topics import add_topic

AK = User("ak", "writer")
ML = User("ml", "writer")
RD = User("rd", "reader")
OW = User("ow", "owner")
T0 = datetime(2026, 11, 13, 9, tzinfo=UTC)
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


def test_sqlite_has_the_json_functions_the_statements_use(db: sqlite3.Connection) -> None:
    assert rows(db, "SELECT count(*) FROM json_each(?)", "[4, 5]") == [(2,)]


# ---- R2: static SQL; one visibility rule ---------------------------------------------------


def test_every_statement_is_one_constant_string_and_nothing_asserts() -> None:
    tree = ast.parse(Path(groups.__file__).read_text(encoding="utf-8"))
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    calls = [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr in ("execute", "executemany", "executescript")
    ]
    assert len(calls) >= 8
    for call in calls:
        assert isinstance(call.args[0], ast.Constant)


# Group (name, visibility, members), written by hand. Name order is not id order.
_MATRIX = [
    ("Zulu", "everyone", ["ak"]),
    ("alpha", "invited", ["ak", "rd"]),
    ("Mike", "everyone", ["ml", "rd"]),
    ("Bravo", "invited", ["ml"]),
    ("Kilo", "invited", ["ak", "ml"]),
    ("Delta", "everyone", ["ak", "ml", "rd"]),
]
# What list_groups must give each user: ids in name order, by hand. Ids follow _MATRIX order 1..6.
_EXPECTED_ORDER = {
    "ak": [2, 6, 5, 3, 1],
    "ml": [4, 6, 5, 3, 1],
    "rd": [2, 6, 3, 1],
    "ow": [6, 3, 1],
    "stranger": [6, 3, 1],
}
# What visible_group_ids must give each user: the same groups, in ascending id order, by hand.
_EXPECTED_IDS = {
    "ak": [1, 2, 3, 5, 6],
    "ml": [1, 3, 4, 5, 6],
    "rd": [1, 2, 3, 6],
    "ow": [1, 3, 6],
    "stranger": [1, 3, 6],
}


def _build_matrix(db: sqlite3.Connection) -> list[int]:
    ids = []
    writers = {"ak": AK, "ml": ML}
    for name, visibility, who in _MATRIX:
        owner = writers[who[0] if who[0] in writers else "ak"]
        gid = create_group(db, Act(owner, T0), name, visibility, [])
        ids.append(gid)
        for member in who:
            if member != owner.name:
                add_member(db, Act(owner, T0), gid, member)
    return ids


def test_list_groups_agrees_with_can_see_in_set_and_order(db: sqlite3.Connection) -> None:
    ids = _build_matrix(db)
    assert ids == [1, 2, 3, 4, 5, 6]
    probes = [*ids, 0, -1, 7, 2**63 - 1, 2**63, -(2**63) - 1, 10**5000]
    for user, expected in _EXPECTED_ORDER.items():
        listed = [row["id"] for row in list_groups(db, user)]
        assert listed == expected
        assert {g for g in probes if can_see(db, user, g)} == set(expected)
        assert visible_group_ids(db, user) == _EXPECTED_IDS[user]
        assert {g for g in probes if groups._visible_row(db, user, g) is not None} == set(expected)
    first = list_groups(db, "ak")[0]
    assert tuple(first) == (2, "alpha", "invited", 1, 2, 0)


_STATE_USERS = ("ak", "ml", "rd", "ow", "stranger")
_group_states = st.lists(
    st.tuples(
        st.sampled_from(("everyone", "invited")), st.sets(st.sampled_from(_STATE_USERS[1:4]))
    ),
    max_size=8,
)


@settings(deadline=None, max_examples=60)
@given(_group_states)
def test_the_three_visibility_statements_agree_over_generated_states(
    states: list[tuple[str, set[str]]],
) -> None:
    with tempfile.TemporaryDirectory() as folder:
        handle = open_db(Path(folder))
        try:
            for known in (AK, ML, RD, OW):
                add_user(handle, known.name, known.role)
            held: dict[int, tuple[str, set[str]]] = {}
            for number, (visibility, others) in enumerate(states):
                gid = create_group(handle, Act(AK, T0), f"g{number}", visibility, [])
                for other in sorted(others):
                    add_member(handle, Act(AK, T0), gid, other)
                held[gid] = (visibility, others | {"ak"})
            probe_ids = [*held, 0, -1, len(held) + 1, 2**63]
            for user in _STATE_USERS:
                # The rule restated here, from the generated state and not from the SQL.
                expected = sorted(
                    g for g, (vis, who) in held.items() if vis == "everyone" or user in who
                )
                assert visible_group_ids(handle, user) == expected
                assert sorted(row["id"] for row in list_groups(handle, user)) == expected
                seen = [g for g in probe_ids if groups._visible_row(handle, user, g) is not None]
                assert sorted(seen) == expected
        finally:
            handle.close()


def _add_threads(db: sqlite3.Connection, gid: int, how_many: int) -> None:
    for number in range(how_many):
        db.execute(
            "INSERT INTO threads(group_id, title, started_by, created_at, last_activity_at)"
            " VALUES(?, ?, 'ak', 'x', 'x')",
            (gid, f"t{gid}-{number}"),
        )
    db.commit()


def test_list_groups_counts_each_groups_own_threads_and_members(db: sqlite3.Connection) -> None:
    alpha = create_group(db, Act(AK, T0), "Alpha", "everyone", [])
    bravo = create_group(db, Act(AK, T0), "Bravo", "everyone", [])
    hidden = create_group(db, Act(AK, T0), "Hidden", "invited", [])
    join(db, "rd", bravo, T0)
    add_member(db, Act(AK, T0), hidden, "ml")
    add_member(db, Act(AK, T0), hidden, "ow")
    for gid, how_many in ((alpha, 1), (bravo, 2), (hidden, 5)):
        _add_threads(db, gid, how_many)
    # A reader outside the hidden group: its 5 threads and 3 members are in no count.
    assert [tuple(r) for r in list_groups(db, "rd")] == [
        (alpha, "Alpha", "everyone", 0, 1, 1),
        (bravo, "Bravo", "everyone", 1, 2, 2),
    ]
    # A member of it sees all three groups, each with its own counts.
    assert [tuple(r) for r in list_groups(db, "ml")] == [
        (alpha, "Alpha", "everyone", 0, 1, 1),
        (bravo, "Bravo", "everyone", 0, 2, 2),
        (hidden, "Hidden", "invited", 1, 3, 5),
    ]


# ---- hidden and missing read the same ------------------------------------------------------


def _outcome(call: Callable[[int], object], group_id: int) -> tuple[str, str]:
    try:
        result = call(group_id)
    except StoreError as exc:
        return type(exc).__name__, str(exc)
    return "returned", repr(result)


def test_no_such_group_is_a_not_found_that_is_a_store_error(db: sqlite3.Connection) -> None:
    assert issubclass(NotFound, StoreError) and not issubclass(NotFound, Forbidden)
    hidden = create_group(db, Act(AK, T0), "Deal team", "invited", [])
    for gid in (hidden, hidden + 100):
        with pytest.raises(NotFound, match="^no such group$") as caught:
            require_visible(db, "ml", gid)
        assert type(caught.value) is NotFound


def test_a_hidden_group_and_a_missing_group_are_indistinguishable(db: sqlite3.Connection) -> None:
    hidden = create_group(db, Act(AK, T0), "Deal team", "invited", [])
    missing_ids = [hidden + 100, 0, -5, 2**63, 10**5000]
    operations: list[Callable[[int], object]] = [
        lambda g: can_see(db, "ml", g),
        lambda g: require_visible(db, "ml", g),
        lambda g: members(db, "ml", g),
        lambda g: join(db, "ml", g, T0),
        lambda g: leave(db, "ml", g),
        lambda g: add_member(db, Act(ML, T0), g, "rd"),
        lambda g: remove_member(db, ML, g, "ak"),
        lambda g: add_member(db, Act(RD, T0), g, "rd"),  # a reader: Forbidden must not show
        lambda g: remove_member(db, RD, g, "ak"),
    ]
    before = (count(db, "groups"), count(db, "group_members"))
    for operation in operations:
        reference = _outcome(operation, hidden)
        assert reference[0] in ("returned", "NotFound")
        for missing in missing_ids:
            assert _outcome(operation, missing) == reference
    assert (count(db, "groups"), count(db, "group_members")) == before
    assert members(db, "ak", hidden) == ["ak"]


# ---- R13: transaction ownership ------------------------------------------------------------


def _writers(db: sqlite3.Connection, gid: int) -> list[Callable[[], object]]:
    return [
        lambda: create_group(db, Act(AK, T0), "Another", "everyone", []),
        lambda: join(db, "rd", gid, T0),
        lambda: leave(db, "rd", gid),
        lambda: add_member(db, Act(AK, T0), gid, "ml"),
        lambda: remove_member(db, AK, gid, "rd"),
    ]


def test_a_writer_refuses_a_transaction_it_does_not_own_and_writes_nothing(
    db: sqlite3.Connection,
) -> None:
    gid = create_group(db, Act(AK, T0), "Open", "everyone", [])
    join(db, "rd", gid, T0)
    before = (count(db, "groups"), count(db, "group_members"))
    db.execute("BEGIN")
    try:
        for call in _writers(db, gid):
            with pytest.raises(StoreUnusable):
                call()
    finally:
        db.execute("ROLLBACK")
    assert (count(db, "groups"), count(db, "group_members")) == before


def test_each_writer_makes_its_checks_between_begin_and_commit(db: sqlite3.Connection) -> None:
    gid = create_group(db, Act(AK, T0), "Open", "everyone", [])
    join(db, "rd", gid, T0)
    topic = add_topic(db, "Rates", ["rate"], [], "ak")
    calls: list[Callable[[], object]] = [
        lambda: create_group(db, Act(AK, T0), "Another", "everyone", [topic]),
        lambda: join(db, "ml", gid, T0),
        lambda: leave(db, "rd", gid),
        lambda: add_member(db, Act(AK, T0), gid, "ml"),
        lambda: remove_member(db, AK, gid, "ml"),
    ]
    for call in calls:
        log: list[str] = []
        db.set_trace_callback(log.append)
        call()
        db.set_trace_callback(None)
        assert log[0] == "BEGIN IMMEDIATE" and log[-1] == "COMMIT"
        selects = [line for line in log if line.lstrip().upper().startswith("SELECT")]
        assert selects, log


def test_a_failed_create_leaves_no_partial_rows(db: sqlite3.Connection) -> None:
    create_group(db, Act(AK, T0), "Taken", "everyone", [])
    before = tuple(count(db, t) for t in _COUNTS)
    for name, topics in (("taken", []), ("Fresh", [4242])):
        with pytest.raises(StoreError):
            create_group(db, Act(AK, T0), name, "everyone", topics)
    assert tuple(count(db, t) for t in _COUNTS) == before


def test_an_outer_transaction_that_fails_undoes_a_group_made_inside_it(
    db: sqlite3.Connection,
) -> None:
    with pytest.raises(RuntimeError, match="^stop$"), write_transaction(db):
        create_group(db, Act(AK, T0), "Inside", "everyone", [])
        raise RuntimeError("stop")
    assert count(db, "groups") == 0 and count(db, "group_members") == 0


def test_a_refused_removal_the_caller_catches_inside_its_transaction_removes_nothing(
    db: sqlite3.Connection,
) -> None:
    gid = create_group(db, Act(AK, T0), "Deal team", "invited", [])
    add_member(db, Act(AK, T0), gid, "rd")
    calls: list[Callable[[], object]] = [
        lambda: leave(db, "ak", gid),
        lambda: remove_member(db, AK, gid, "ak"),
    ]
    for call in calls:
        # The refusal is caught and the block commits: what the refusal protects must still hold.
        with write_transaction(db), pytest.raises(StoreError, match="^an invited group needs"):
            call()
        assert _all_members(db) == [(1, "ak"), (1, "rd")]


# ---- roles ---------------------------------------------------------------------------------


def test_roles_decide_who_manages_groups(db: sqlite3.Connection) -> None:
    assert [may_post(u) for u in (RD, AK, OW, User("x", "admin"))] == [False, True, True, False]
    gid = create_group(db, Act(OW, T0), "Owner desk", "invited", [])
    assert add_member(db, Act(OW, T0), gid, "ak") == "ak"
    assert [can_manage(db, u, gid) for u in (OW, AK, ML, RD)] == [True, True, False, False]
    assert can_manage(db, User("zz", "writer"), 999) is False
    # A reader who is a member sees the group and still does not manage it.
    add_member(db, Act(OW, T0), gid, "rd")
    open_desk = create_group(db, Act(OW, T0), "Open desk", "everyone", [])
    join(db, "rd", open_desk, T0)
    assert members(db, "rd", gid) == ["ow", "ak", "rd"]
    assert [can_manage(db, RD, g) for g in (gid, open_desk)] == [False, False]
    assert [can_manage(db, AK, g) for g in (gid, open_desk)] == [True, True]
    with pytest.raises(Forbidden):
        create_group(db, Act(User("x", "admin"), T0), "No", "everyone", [])
    open_group = create_group(db, Act(AK, T0), "Open", "everyone", [])
    join(db, "rd", open_group, T0)
    leave(db, "rd", open_group)
    assert members(db, "rd", open_group) == ["ak"]


# ---- the invited-group rule: who counts as its manager ---------------------------------------


def test_an_invited_group_may_be_left_to_its_creator_alone_whatever_the_creators_stored_role(
    db: sqlite3.Connection,
) -> None:
    demoted = User("dm", "writer")  # stored as a reader: the Act still carries the writer role
    add_user(db, "dm", "reader")
    first = create_group(db, Act(demoted, T0), "By a demoted creator", "invited", [])
    add_member(db, Act(demoted, T0), first, "ak")
    leave(db, "ak", first)  # the creator remains, so the group still has its manager
    assert members(db, "dm", first) == ["dm"]
    stranger = User("nb", "writer")  # not stored at all
    second = create_group(db, Act(stranger, T0), "By an unstored creator", "invited", [])
    add_member(db, Act(stranger, T0), second, "rd")
    leave(db, "rd", second)
    assert members(db, "nb", second) == ["nb"]


def test_an_invited_group_may_be_left_to_an_owner_member(db: sqlite3.Connection) -> None:
    gid = create_group(db, Act(AK, T0), "Owner kept", "invited", [])
    add_member(db, Act(AK, T0), gid, "ow")
    add_member(db, Act(AK, T0), gid, "rd")
    leave(db, "ak", gid)  # the creator is gone; the owner is the manager
    assert members(db, "ow", gid) == ["ow", "rd"]
    with pytest.raises(StoreError, match="^an invited group needs a writer member$"):
        leave(db, "ow", gid)
    assert members(db, "ow", gid) == ["ow", "rd"]


def test_the_manager_check_excludes_exactly_the_leaver(db: sqlite3.Connection) -> None:
    add_user(db, "_k", "writer")
    gid = create_group(db, Act(AK, T0), "Exact leaver", "invited", [])
    add_member(db, Act(AK, T0), gid, "_k")
    leave(db, "_k", gid)  # ak, whose name _k would match as a pattern, is still the manager
    assert members(db, "ak", gid) == ["ak"]


def _all_members(db: sqlite3.Connection) -> list[tuple[Any, ...]]:
    return rows(db, "SELECT group_id, user_name FROM group_members ORDER BY group_id, user_name")


def test_leaving_or_being_removed_from_one_group_leaves_only_that_group(
    db: sqlite3.Connection,
) -> None:
    open_a = create_group(db, Act(AK, T0), "Open A", "everyone", [])
    open_b = create_group(db, Act(ML, T0), "Open B", "everyone", [])
    secret = create_group(db, Act(ML, T0), "ML only", "invited", [])  # ak cannot see it
    assert (open_a, open_b, secret) == (1, 2, 3)
    join(db, "rd", open_a, T0)
    join(db, "rd", open_b, T0)
    add_member(db, Act(ML, T0), secret, "rd")
    assert _all_members(db) == [(1, "ak"), (1, "rd"), (2, "ml"), (2, "rd"), (3, "ml"), (3, "rd")]
    leave(db, "rd", open_a)
    kept = [(1, "ak"), (2, "ml"), (2, "rd"), (3, "ml"), (3, "rd")]
    assert _all_members(db) == kept
    join(db, "rd", open_a, T0)
    remove_member(db, AK, open_a, "rd")  # ak is not in group 3 and cannot see it
    assert _all_members(db) == kept


def test_an_invited_group_needs_a_manager_of_its_own_not_one_of_another_group(
    db: sqlite3.Connection,
) -> None:
    deal = create_group(db, Act(AK, T0), "Deal team", "invited", [])
    add_member(db, Act(AK, T0), deal, "rd")
    create_group(db, Act(ML, T0), "ML desk", "everyone", [])  # ml, a writer, is in this one only
    calls: list[Callable[[], object]] = [
        lambda: leave(db, "ak", deal),
        lambda: remove_member(db, AK, deal, "ak"),
    ]
    for call in calls:
        with pytest.raises(StoreError, match="^an invited group needs a writer member$"):
            call()
    assert _all_members(db) == [(1, "ak"), (1, "rd"), (2, "ml")]


def test_a_reader_learns_nothing_from_a_taken_name(db: sqlite3.Connection) -> None:
    create_group(db, Act(AK, T0), "Deal team", "invited", [])  # hidden from rd
    for name in ("deal TEAM", "Free name"):
        with pytest.raises(Forbidden, match="^only writers and the owner can create groups$"):
            create_group(db, Act(RD, T0), name, "everyone", [])
    assert count(db, "groups") == 1 and count(db, "group_members") == 1
