"""The feed view under the port's rulings, part 1: the grid oracle, membership and cards,
snapshots, visibility and the writers (R2, R13, R42).

Expected values here are written by hand from the data each test builds (the shared grid is in
`feedview_grid.py`); none is computed with the code under test.
"""

from __future__ import annotations

import itertools
import random
import sqlite3
import tempfile
from collections.abc import Callable, Iterator
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from feedview_grid import (
    FOLLOWS,
    MEMBERS,
    SAVES,
    SOURCES,
    STORIES,
    T0,
    THREADS,
    TOPICS,
    USERS,
    VIEWS,
    cursor,
    grid_db,
    thread,
)
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from credit_os.signal import feedview, groups
from credit_os.signal.feeds import Entry
from credit_os.signal.feedview import (
    MAX_ID,
    Card,
    CardThread,
    ViewError,
    card_for,
    feed,
    new_count,
    save,
    unsave,
)
from credit_os.signal.groups import Act, NotFound, add_member, create_group
from credit_os.signal.identity import User
from credit_os.signal.store import (
    StoreUnusable,
    add_story,
    add_user,
    in_range,
    open_db,
    propose_source,
    set_source_state,
    write_transaction,
)


@pytest.fixture
def grid(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    db = grid_db(tmp_path)
    yield db
    db.close()


def in_view(user: str, view: str, story: int) -> bool:
    if view == "latest":
        return True
    if view == "saved":
        return story in SAVES.get(user, set())
    if view.startswith("topic:"):
        return story in TOPICS[int(view[6:])]
    followed = any(story in TOPICS[topic] for topic in FOLLOWS.get(user, set()))
    return followed or any(user in MEMBERS[g] for g, s, _ in THREADS if s == story)


def is_shared(user: str, story: int) -> bool:
    return any(
        user in MEMBERS[g] and by is not None and by != user for g, s, by in THREADS if s == story
    )


def words_of(story: int) -> set[str]:
    return set(STORIES[story][2].split()) | {"headline", "for", "story", str(story)}


def expected_ids(
    user: str, view: str, kind: str | None, query: str, shared: bool, below: int | None
) -> list[int]:
    found = [
        n
        for n in STORIES
        if in_view(user, view, n)
        and (kind is None or SOURCES[STORIES[n][0]][1] == kind)
        and all(term in words_of(n) for term in query.lower().split())
        and (not shared or is_shared(user, n))
        and (below is None or (STORIES[n][1], n) < (STORIES[below][1], below))
    ]
    return sorted(found, key=lambda n: (STORIES[n][1], n), reverse=True)


def walk(
    db: sqlite3.Connection, user: str, view: str, filters: dict[str, Any]
) -> list[tuple[list[int], str | None]]:
    """Every page from the first, as (ids, next_before)."""
    pages: list[tuple[list[int], str | None]] = []
    while True:
        page = feed(db, user, view, **filters)
        pages.append(([card.id for card in page.cards], page.next_before))
        if page.next_before is None:
            return pages
        filters = {**filters, "before": page.next_before}


def expected_pages(ids: list[int], size: int) -> list[tuple[list[int], str | None]]:
    chunks = [ids[i : i + size] for i in range(0, len(ids), size)] or [[]]
    return [
        (chunk, cursor(chunk[-1]) if i * size + size < len(ids) else None)
        for i, chunk in enumerate(chunks)
    ]


def test_the_grid_state_is_what_the_oracle_assumes(grid: sqlite3.Connection) -> None:
    topics: dict[int, set[int]] = {
        row["topic_id"]: set()
        for row in grid.execute("SELECT DISTINCT topic_id FROM topic_stories")
    }
    for row in grid.execute("SELECT topic_id, story_id FROM topic_stories"):
        topics[row["topic_id"]].add(row["story_id"])
    assert topics == TOPICS
    assert [
        (r[0], r[1], r[2])
        for r in grid.execute("SELECT group_id, story_id, started_by FROM threads ORDER BY id")
    ] == THREADS


@pytest.mark.parametrize("view", VIEWS)
@pytest.mark.parametrize("user", USERS)
def test_every_filter_combination_returns_what_the_oracle_says_page_by_page(
    grid: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch, view: str, user: str
) -> None:
    monkeypatch.setattr(feedview, "PAGE", 3)
    combos = itertools.product(
        (None, "news", "ratings"),
        ("", "remedy", "Rates remedy", "story", "absent"),
        (False, True),
        (None, 4),
    )
    for kind, query, shared, below in combos:
        filters: dict[str, Any] = {"kind": kind, "query": query, "shared": shared}
        if below is not None:
            filters["before"] = cursor(below)
        ids = expected_ids(user, view, kind, query, shared, below)
        label = (user, view, kind, query, shared, below)
        assert walk(grid, user, view, filters) == expected_pages(ids, 3), label


@pytest.mark.parametrize("view", VIEWS)
@pytest.mark.parametrize("user", USERS)
def test_new_count_matches_the_oracle_for_every_view(
    grid: sqlite3.Connection, view: str, user: str
) -> None:
    for after in (0, 1, 3, 7, 8, 100):
        wanted = [n for n in STORIES if n > after and in_view(user, view, n)]
        assert new_count(grid, user, view, after) == len(wanted), (user, view, after)


def test_hand_written_membership_answers(grid: sqlite3.Connection) -> None:
    """The same rules as the oracle, as literals worked out from the thread list above."""
    assert [c.id for c in feed(grid, "ak", "foryou").cards] == [8, 7, 6, 5, 3, 2]
    assert [c.id for c in feed(grid, "ml", "foryou").cards] == [8, 5, 3]
    assert [c.id for c in feed(grid, "rd", "foryou").cards] == [7, 6, 5, 2, 1]
    assert [c.id for c in feed(grid, "ak", "latest", shared=True).cards] == [5]
    assert [c.id for c in feed(grid, "ml", "latest", shared=True).cards] == [3]
    assert [c.id for c in feed(grid, "rd", "latest", shared=True).cards] == [5]


def test_a_cards_fields_and_threads_are_exact_for_each_viewer(grid: sqlite3.Connection) -> None:
    seven = Card(
        7,
        "golf headline for story 7",
        "https://s1.org/7",
        "golf rates remedy",
        "Authority",
        "regulator",
        "2026-11-13T08:15:00+00:00",
        0,
        False,
        ("Remedy", "Rates"),
        (),
    )
    assert card_for(grid, "ml", 7) == seven
    assert card_for(grid, "ak", 8).saved and not card_for(grid, "ml", 8).saved
    both = (
        CardThread(2, "Open desk", 1, "ml", "note 2"),
        CardThread(3, "Closed desk", 1, "ak", "note 3"),
    )
    assert card_for(grid, "ak", 5).threads == both
    assert card_for(grid, "rd", 5).threads == both
    assert card_for(grid, "ml", 5).threads == both[:1]
    assert card_for(grid, "ak", 6).threads == (CardThread(4, "Closed desk", 0, None, None),)
    assert card_for(grid, "ml", 6).threads == ()


def test_card_for_equals_the_card_the_page_statement_builds(grid: sqlite3.Connection) -> None:
    for user in USERS:
        shown = {card.id: card for card in feed(grid, user, "latest").cards}
        assert sorted(shown) == list(STORIES)
        for story, card in shown.items():
            assert card_for(grid, user, story) == card, (user, story)


# --- R42: the card threads are the threads in groups `can_see` says, for generated states ------

NAMES = ("u0", "u1", "u2", "u3", "outsider")


def build_random_state(
    db: sqlite3.Connection, rng: random.Random
) -> tuple[dict[int, str], list[tuple[int, int, int, str | None, list[tuple[str, str, bool]]]]]:
    """Groups (id to name) and threads (id, group, story, started_by, comments), all random."""
    add_user(db, "u0", "writer")
    add_user(db, "u1", "writer")
    set_source_state(db, propose_source(db, "Src", "news", "https://s.org/f", "u0"), "approved")
    for n in range(1, 5):
        entry = Entry(f"title number {n} here", f"https://s.org/{n}", T0, f"summary {n}")
        assert add_story(db, 1, entry, T0) == "new"
    names: dict[int, str] = {}
    for i in range(rng.randint(1, 6)):
        creator = User(rng.choice(("u0", "u1")), "writer")
        visibility = rng.choice(("everyone", "invited"))
        gid = create_group(db, Act(creator, T0), f"Group {i}", visibility, [])
        names[gid] = f"Group {i}"
        for other in NAMES:
            if rng.random() < 0.4:
                add_member(db, Act(creator, T0), gid, other)
    found: list[tuple[int, int, int, str | None, list[tuple[str, str, bool]]]] = []
    for gid in names:
        for story in range(1, 5):
            if rng.random() < 0.5:
                found.append(random_thread(db, rng, gid, story))
    db.commit()
    return names, found


def random_thread(
    db: sqlite3.Connection, rng: random.Random, gid: int, story: int
) -> tuple[int, int, int, str | None, list[tuple[str, str, bool]]]:
    by = rng.choice((*NAMES[:4], None))
    stamp = T0.isoformat()
    cur = db.execute(
        "INSERT INTO threads(group_id, story_id, started_by, created_at, last_activity_at)"
        " VALUES(?, ?, ?, ?, ?)",
        (gid, story, by, stamp, stamp),
    )
    thread_id = int(cur.lastrowid or 0)
    comments: list[tuple[str, str, bool]] = []
    for _ in range(rng.randint(0, 3)):
        author = rng.choice(NAMES[:4])
        text = "x" * rng.choice((5, 140, 141, 300))
        deleted = rng.random() < 0.3
        db.execute(
            "INSERT INTO comments(thread_id, author, text, created_at, deleted_at)"
            " VALUES(?, ?, ?, ?, ?)",
            (thread_id, author, text, stamp, stamp if deleted else None),
        )
        comments.append((author, text, deleted))
    return thread_id, gid, story, by, comments


def note_of(by: str | None, comments: list[tuple[str, str, bool]]) -> str | None:
    for author, text, deleted in comments:
        if not deleted and author == by:
            return text[:140]
    return None


def is_member(db: sqlite3.Connection, user: str, gid: int) -> bool:
    try:
        return user in groups.members(db, user, gid)
    except NotFound:
        return False


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.integers(min_value=0, max_value=2**31))
def test_card_threads_and_membership_clauses_match_the_groups_module(seed: int) -> None:
    rng = random.Random(seed)
    with tempfile.TemporaryDirectory() as folder, closing(open_db(Path(folder))) as db:
        names, found = build_random_state(db, rng)
        for user in NAMES:
            cards = {card.id: card for card in feed(db, user, "latest").cards}
            member_of: set[int] = set()
            shared_with: set[int] = set()
            for story in range(1, 5):
                shown = [
                    CardThread(
                        tid,
                        names[gid],
                        sum(1 for _, _, deleted in comments if not deleted),
                        by,
                        note_of(by, comments),
                    )
                    for tid, gid, s, by, comments in found
                    if s == story and groups.can_see(db, user, gid)
                ]
                assert list(cards[story].threads) == shown, (seed, user, story)
                for _, gid, s, by, _ in found:
                    if s == story and is_member(db, user, gid):
                        member_of.add(story)
                        if by is not None and by != user:
                            shared_with.add(story)
            assert {c.id for c in feed(db, user, "foryou").cards} == member_of, (seed, user)
            assert new_count(db, user, "foryou", 0) == len(member_of)
            shared = {c.id for c in feed(db, user, "latest", shared=True).cards}
            assert shared == shared_with, (seed, user)


def test_the_sqlite_build_has_the_json_functions_the_statements_use(
    grid: sqlite3.Connection,
) -> None:
    assert grid.execute("SELECT count(*) FROM json_each('[4, 5, 6]')").fetchone()[0] == 3
    assert grid.execute("SELECT json_array_length('[1, 2]')").fetchone()[0] == 2


# --- R42: one snapshot per page, the visibility read once --------------------------------------


def test_a_page_is_one_snapshot_whatever_another_connection_commits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with closing(grid_db(tmp_path)) as db, closing(open_db(tmp_path)) as other:
        real = groups.visible_group_ids

        def interleaved(conn: sqlite3.Connection, user_name: str) -> list[int]:
            found = real(conn, user_name)
            entry = Entry("late story arrives here", "https://s1.org/late", T0, "late")
            assert add_story(other, 1, entry, T0) == "new"
            thread(other, 1, 1, "ml")  # a new thread on story 1 in the open group, mid-page
            return found

        monkeypatch.setattr(feedview, "visible_group_ids", interleaved)
        page = feed(db, "ak", "latest")
        monkeypatch.undo()
        assert page.newest == 8  # the story committed mid-page is not in this page
        assert [c.id for c in page.cards] == [8, 7, 6, 5, 4, 3, 2, 1]
        assert page.cards[-1].threads == ()
        after = feed(db, "ak", "latest")
        assert after.newest == 9
        assert after.cards[-1].threads == (CardThread(6, "Open desk", 1, "ml", "note 6"),)


@pytest.mark.parametrize(
    "call, reads",
    [
        (lambda db: feed(db, "ak", "latest"), 1),
        (lambda db: card_for(db, "ak", 5), 1),
        (lambda db: new_count(db, "ak", "foryou", 0), 0),
    ],
)
def test_the_visible_groups_are_read_once_per_call(
    grid: sqlite3.Connection,
    monkeypatch: pytest.MonkeyPatch,
    call: Callable[[sqlite3.Connection], object],
    reads: int,
) -> None:
    calls: list[str] = []
    real = groups.visible_group_ids

    def counting(conn: sqlite3.Connection, user_name: str) -> list[int]:
        calls.append(user_name)
        return real(conn, user_name)

    monkeypatch.setattr(feedview, "visible_group_ids", counting)
    call(grid)
    assert len(calls) == reads


def test_a_call_leaves_no_transaction_open_on_success_or_refusal(grid: sqlite3.Connection) -> None:
    feed(grid, "ak", "latest")
    card_for(grid, "ak", 1)
    new_count(grid, "ak", "latest", 0)
    assert not grid.in_transaction
    with pytest.raises(ViewError):
        feed(grid, "ak", "topic:99")
    with pytest.raises(ViewError):
        card_for(grid, "ak", 99)
    with pytest.raises(ViewError):
        new_count(grid, "ak", "nope", 0)
    assert not grid.in_transaction


@pytest.mark.parametrize(
    "call",
    [
        lambda db: feed(db, "ak", "latest"),
        lambda db: card_for(db, "ak", 1),
        lambda db: new_count(db, "ak", "latest", 0),
        lambda db: save(db, "ak", 2),
        lambda db: unsave(db, "ak", 1),
    ],
)
def test_inside_a_transaction_the_caller_opened_every_call_is_refused_unconverted(
    grid: sqlite3.Connection, call: Callable[[sqlite3.Connection], object]
) -> None:
    grid.execute("BEGIN")
    with pytest.raises(StoreUnusable) as refused:
        call(grid)
    assert not isinstance(refused.value, ViewError)
    assert grid.in_transaction  # still the caller's
    grid.execute("ROLLBACK")
    rows = grid.execute("SELECT story_id FROM saves WHERE user_name='ak' ORDER BY story_id")
    assert [r[0] for r in rows] == [1, 4, 8]  # nothing was written


# --- writers -------------------------------------------------------------------------------------


def test_save_and_unsave_join_an_outer_write_transaction(grid: sqlite3.Connection) -> None:
    with pytest.raises(RuntimeError, match="stop"), write_transaction(grid):
        save(grid, "rd", 3)
        unsave(grid, "ak", 1)
        raise RuntimeError("stop")
    rows = grid.execute("SELECT user_name, story_id FROM saves ORDER BY user_name, story_id")
    assert [tuple(r) for r in rows] == [("ak", 1), ("ak", 4), ("ak", 8), ("ml", 2)]
    with write_transaction(grid):
        save(grid, "rd", 3)
        unsave(grid, "ak", 1)
    rows = grid.execute("SELECT user_name, story_id FROM saves ORDER BY user_name, story_id")
    assert [tuple(r) for r in rows] == [("ak", 4), ("ak", 8), ("ml", 2), ("rd", 3)]


def test_unsave_removes_only_the_callers_save_of_a_story_others_also_saved(
    grid: sqlite3.Connection,
) -> None:
    save(grid, "ml", 1)  # ak and ml have both saved story 1
    unsave(grid, "ak", 1)
    rows = grid.execute("SELECT user_name, story_id FROM saves ORDER BY user_name, story_id")
    assert [tuple(r) for r in rows] == [("ak", 4), ("ak", 8), ("ml", 1), ("ml", 2)]
    assert [c.id for c in feed(grid, "ml", "saved").cards] == [2, 1]
    unsave(grid, "ak", 1)  # not saved any more: a no-op that touches nobody else
    assert grid.execute("SELECT count(*) FROM saves").fetchone()[0] == 4


def test_save_stores_one_utc_time_and_keeps_the_first_save(grid: sqlite3.Connection) -> None:
    save(grid, "rd", 3)
    first = grid.execute("SELECT saved_at FROM saves WHERE user_name='rd'").fetchone()[0]
    assert datetime.fromisoformat(first).utcoffset() == T0.utcoffset()
    assert first.endswith("+00:00")
    save(grid, "rd", 3)
    assert grid.execute("SELECT saved_at FROM saves WHERE user_name='rd'").fetchone()[0] == first
    assert grid.execute("SELECT count(*) FROM saves WHERE user_name='rd'").fetchone()[0] == 1


@pytest.mark.parametrize("action", [save, unsave])
@pytest.mark.parametrize(
    "story", [0, 99, -1, MAX_ID, MAX_ID + 1, -(2**63) - 1, pytest.param(2**20000, id="2**20000")]
)
def test_a_story_that_does_not_exist_is_a_view_error_and_writes_nothing(
    grid: sqlite3.Connection, action: Callable[[sqlite3.Connection, str, int], None], story: int
) -> None:
    with pytest.raises(ViewError, match="no story with"):
        action(grid, "ak", story)
    assert grid.execute("SELECT count(*) FROM saves").fetchone()[0] == 4
    assert not grid.in_transaction


def test_card_for_a_story_that_does_not_exist_is_a_view_error(grid: sqlite3.Connection) -> None:
    for story in (0, 99, -1, MAX_ID, MAX_ID + 1, 2**20000, -(2**20000)):
        with pytest.raises(ViewError, match="no story with"):
            card_for(grid, "ak", story)


def test_max_id_is_the_last_id_sqlite_can_hold() -> None:
    assert in_range(MAX_ID) and not in_range(MAX_ID + 1)


def test_other_sources_counts_each_source_once() -> None:
    stamp = datetime(2026, 11, 13, 9, tzinfo=UTC)
    title = "regulator publishes remedy decision today"
    with tempfile.TemporaryDirectory() as folder, closing(open_db(Path(folder))) as db:
        add_user(db, "ak", "writer")
        for number in (1, 2, 3):
            propose_source(db, f"S{number}", "news", f"https://s{number}.org/f", "ak")
            set_source_state(db, number, "approved")
        assert add_story(db, 1, Entry(title, "https://s1.org/a", stamp, "x"), stamp) == "new"
        assert add_story(db, 2, Entry(title, "https://s2.org/a", stamp, "x"), stamp) == "duplicate"
        assert add_story(db, 2, Entry(title, "https://s2.org/b", stamp, "x"), stamp) == "duplicate"
        assert feed(db, "ak", "latest").cards[0].other_sources == 1
        assert add_story(db, 3, Entry(title, "https://s3.org/a", stamp, "x"), stamp) == "duplicate"
        assert feed(db, "ak", "latest").cards[0].other_sources == 2
