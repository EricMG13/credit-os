"""S-10: `store._earliest_match` reads one row per source, not every story sharing a title.

The oracle is the pre-change function (`store_match_oracle`); the new one must return exactly
what it returns for every store, and its work must not grow with the number of stored rows."""

from __future__ import annotations

import re
import sqlite3
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st
from store_match_oracle import earliest_match_oracle

from credit_os.signal import store
from credit_os.signal.fold import TITLE_WINDOW
from credit_os.signal.store import StoreError, open_db, utc_text

_STORED_FORM = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d{6})?\+00:00")
_LONG = "alpha beta gamma delta"


def _seed_sources(db: sqlite3.Connection, count: int) -> None:
    for number in range(1, count + 1):
        db.execute(
            "INSERT INTO sources(id, name, kind, url, state, proposed_by, created_at)"
            " VALUES(?, ?, 'news', ?, 'approved', 'x', 'now')",
            (number, f"s{number}", f"https://e.org/{number}"),
        )
    db.commit()


def _put_story(
    db: sqlite3.Connection, story_id: int, source_id: int, lkey: str, tkey: str, stamp: str
) -> None:
    db.execute(
        "INSERT OR IGNORE INTO stories(id, source_id, title, link, link_key, title_key,"
        " published_at, fetched_at, summary) VALUES(?, ?, 't', 'l', ?, ?, ?, 'f', '')",
        (story_id, source_id, lkey, tkey, stamp),
    )


# -- Step 3 of the design: the stored form of `published_at` and its order --------------------

_AWARE = st.datetimes(
    timezones=st.integers(-23 * 60 - 59, 23 * 60 + 59).map(
        lambda minutes: timezone(timedelta(minutes=minutes))
    )
)


def _stored(at: datetime) -> str:
    try:
        return utc_text(at)
    except StoreError:  # a time UTC cannot hold is refused by the store; nothing to compare
        assume(False)
        raise


@settings(max_examples=400, deadline=None, derandomize=True)
@given(a=_AWARE, b=_AWARE)
def test_stored_text_order_equals_time_order(a: datetime, b: datetime) -> None:
    ta, tb = _stored(a), _stored(b)
    assert _STORED_FORM.fullmatch(ta)
    assert (ta < tb) == (a < b)
    assert (ta == tb) == (a == b)
    assert (ta > tb) == (a > b)


@settings(max_examples=400, deadline=None, derandomize=True)
@given(micro=st.sampled_from([0, 1, 999_999, 500_000]), other=st.sampled_from([0, 1, 999_999]))
def test_a_whole_second_sorts_before_its_fractions(micro: int, other: int) -> None:
    base = datetime(2026, 3, 1, 12, 0, 5, tzinfo=UTC)
    first, second = base.replace(microsecond=micro), base.replace(microsecond=other)
    assert (utc_text(first) < utc_text(second)) == (micro < other)


# -- Cost: operations, not seconds -------------------------------------------------------------


def _steps(db: sqlite3.Connection, call: object) -> int:
    count = 0

    def tick() -> None:
        nonlocal count
        count += 1

    db.set_progress_handler(tick, 1)
    try:
        assert callable(call)
        call()
    finally:
        db.set_progress_handler(None, 0)
    return count


def _steps_with_rows(tmp_path: Path, rows: int, holder: int, match: object) -> int:
    """VM steps of one match for a caller (source 1) when `rows` stories of source `holder`
    share its long title key, all inside the window."""
    db = open_db(tmp_path / f"k{rows}h{holder}")
    _seed_sources(db, 3)
    when = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
    db.executemany(
        "INSERT INTO stories(source_id, title, link, link_key, title_key, published_at,"
        " fetched_at, summary) VALUES(?, 't', 'l', ?, ?, ?, 'f', '')",
        [(holder, f"e.org/{n}", _LONG, utc_text(when + timedelta(seconds=n))) for n in range(rows)],
    )
    db.commit()
    assert callable(match)
    steps = _steps(db, lambda: match(db, 1, "e.org/new", _LONG, when))
    db.close()
    return steps


@pytest.mark.parametrize("holder", [2, 1], ids=["one other source", "the caller's own source"])
def test_the_work_of_a_match_does_not_grow_with_the_rows_sharing_its_title(
    tmp_path: Path, holder: int
) -> None:
    steps = {
        k: _steps_with_rows(tmp_path, k, holder, store._earliest_match) for k in (100, 800, 3200)
    }
    assert steps[800] <= 2 * steps[100], steps
    assert steps[3200] <= 2 * steps[100], steps


@pytest.mark.parametrize("holder", [2, 1], ids=["one other source", "the caller's own source"])
def test_the_cost_test_can_tell_the_old_function_apart(tmp_path: Path, holder: int) -> None:
    """The oracle's work does grow with the bucket: the test above is not vacuous."""
    small = _steps_with_rows(tmp_path, 100, holder, earliest_match_oracle)
    large = _steps_with_rows(tmp_path, 3200, holder, earliest_match_oracle)
    assert large > 4 * small, (small, large)


def _steps_for_a_title_nobody_shares(tmp_path: Path, sources: int) -> int:
    """VM steps of one match for a title no stored story shares, when every source holds one
    story under a title of its own."""
    db = open_db(tmp_path / f"n{sources}")
    _seed_sources(db, sources)
    for number in range(1, sources + 1):
        _put_story(
            db, number, number, f"e.org/{number}", f"other title {number} words", utc_text(_BASE)
        )
    db.commit()
    steps = _steps(db, lambda: store._earliest_match(db, 1, "e.org/new", _LONG, _BASE))
    db.close()
    return steps


def test_a_title_no_story_shares_costs_the_same_at_300_sources_as_at_10(tmp_path: Path) -> None:
    few = _steps_for_a_title_nobody_shares(tmp_path, 10)
    many = _steps_for_a_title_nobody_shares(tmp_path, 300)
    assert many <= 2 * few, (few, many)


# -- Equality with the oracle on generated stores ---------------------------------------------

_BASE = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
# Offsets of a stored time from the caller's: both window edges exactly, one microsecond either
# side of each, inside, and the same instant.
_EDGES = [
    -TITLE_WINDOW - timedelta(hours=1),
    -TITLE_WINDOW - timedelta(microseconds=1),
    -TITLE_WINDOW,
    -TITLE_WINDOW + timedelta(microseconds=1),
    -timedelta(hours=5),
    timedelta(0),
    timedelta(microseconds=1),
    timedelta(hours=5),
    TITLE_WINDOW - timedelta(microseconds=1),
    TITLE_WINDOW,
    TITLE_WINDOW + timedelta(microseconds=1),
    TITLE_WINDOW + timedelta(hours=1),
]
_TITLES = [_LONG, "alpha beta gamma delta", "one two three four five", "alpha beta gamma", "x y"]
_LINKS = ["e.org/a", "e.org/b", "e.org/c", "e.org/d"]
_CALLER_TIMES = [
    _BASE,
    _BASE.replace(microsecond=500_000),
    _BASE.replace(microsecond=1),
    _BASE.astimezone(timezone(timedelta(hours=5, minutes=30))),
]
_SOURCES = 4

_story = st.tuples(
    st.integers(1, _SOURCES),
    st.sampled_from(_LINKS + ["e.org/e", "e.org/f", "e.org/g"]),
    st.sampled_from(_TITLES),
    st.sampled_from(_EDGES),
)
_dup = st.tuples(st.integers(0, 7), st.integers(1, _SOURCES), st.sampled_from(_LINKS))


def test_the_new_match_equals_the_oracle_on_generated_stores(tmp_path: Path) -> None:
    db = open_db(tmp_path)
    _seed_sources(db, _SOURCES)
    cases = {"run": 0, "matched": 0, "unmatched": 0}

    @settings(
        max_examples=1500,
        deadline=None,
        derandomize=True,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(
        stories=st.lists(_story, max_size=8),
        ids=st.permutations(range(1, 9)),
        dups=st.lists(_dup, max_size=4),
        caller=st.integers(1, _SOURCES),
        lkey=st.sampled_from(_LINKS + ["e.org/none"]),
        tkey=st.sampled_from(_TITLES),
        published=st.sampled_from(_CALLER_TIMES),
    )
    def compare(
        stories: list[tuple[int, str, str, timedelta]],
        ids: list[int],
        dups: list[tuple[int, int, str]],
        caller: int,
        lkey: str,
        tkey: str,
        published: datetime,
    ) -> None:
        db.execute("DELETE FROM story_duplicates")
        db.execute("DELETE FROM stories")
        at = published.astimezone(UTC)
        for number, (source, link, title, offset) in enumerate(stories):
            _put_story(db, ids[number], source, link, title, utc_text(at + offset))
        stored = [r[0] for r in db.execute("SELECT id FROM stories ORDER BY id")]
        for index, source, link in dups:
            if index < len(stored):
                db.execute(
                    "INSERT OR IGNORE INTO story_duplicates(story_id, duplicate_source_id, link,"
                    " link_key, published_at, seen_at) VALUES(?, ?, 'l', ?, 'p', 's')",
                    (stored[index], source, link),
                )
        want = earliest_match_oracle(db, caller, lkey, tkey, published)
        assert store._earliest_match(db, caller, lkey, tkey, published) == want
        cases["run"] += 1
        cases["matched" if want is not None else "unmatched"] += 1

    compare()
    assert cases["run"] >= 1000
    assert cases["matched"] > 100
    assert cases["unmatched"] > 100


@pytest.mark.parametrize(
    "published", [datetime.min.replace(tzinfo=UTC), datetime.max.replace(tzinfo=UTC)]
)
def test_a_window_the_calendar_cannot_hold_is_clamped_and_still_matches_the_oracle(
    tmp_path: Path, published: datetime
) -> None:
    db = open_db(tmp_path)
    _seed_sources(db, 2)
    for number, offset in enumerate([timedelta(0), timedelta(hours=47), timedelta(hours=49)]):
        at = published - offset if published.year == 9999 else published + offset
        _put_story(db, number + 1, 2, f"e.org/{number}", _LONG, utc_text(at))
    want = earliest_match_oracle(db, 1, "e.org/new", _LONG, published)
    assert want is not None
    assert store._earliest_match(db, 1, "e.org/new", _LONG, published) == want


@pytest.mark.parametrize(
    "published",
    [
        datetime(1, 1, 2, 13, 0, tzinfo=timezone(timedelta(hours=-12))),
        datetime(9999, 12, 30, 10, 0, tzinfo=timezone(timedelta(hours=14))),
    ],
    ids=["year 1 at -12:00", "year 9999 at +14:00"],
)
def test_a_caller_time_at_an_offset_near_the_calendar_edge_matches_the_oracle(
    tmp_path: Path, published: datetime
) -> None:
    """In its own offset the time's window would leave the calendar; in UTC it does not."""
    db = open_db(tmp_path)
    _seed_sources(db, 2)
    _put_story(db, 1, 2, "e.org/a", _LONG, utc_text(published.astimezone(UTC)))
    want = earliest_match_oracle(db, 1, "e.org/new", _LONG, published)
    assert want == 1
    assert store._earliest_match(db, 1, "e.org/new", _LONG, published) == want


def test_a_short_title_does_not_read_the_title_branch(tmp_path: Path) -> None:
    db = open_db(tmp_path)
    _seed_sources(db, 2)
    _put_story(db, 1, 2, "e.org/a", "alpha beta gamma", utc_text(_BASE))
    seen: list[str] = []
    db.set_trace_callback(seen.append)
    assert store._earliest_match(db, 1, "e.org/new", "alpha beta gamma", _BASE) is None
    db.set_trace_callback(None)
    assert seen and all("title_key" not in sql for sql in seen), seen


def test_the_title_branch_seeks_the_new_index_once_per_source(tmp_path: Path) -> None:
    db = open_db(tmp_path)
    plan = " | ".join(
        str(row["detail"])
        for row in db.execute("EXPLAIN QUERY PLAN " + store._TITLE_MATCH_SQL, (_LONG, "a", "b", 1))
    )
    assert "idx_stories_title_source_time" in plan
    assert "title_key=? AND source_id=? AND published_at>? AND published_at<?" in plan
    assert "idx_stories_title_key" not in plan.replace("idx_stories_title_source_time", "")


def test_the_guard_statement_is_an_index_search_not_a_scan(tmp_path: Path) -> None:
    db = open_db(tmp_path)
    plan = " | ".join(
        str(row["detail"])
        for row in db.execute("EXPLAIN QUERY PLAN " + store._TITLE_HELD_SQL, (_LONG, 1, _LONG, 1))
    )
    assert plan.count("SEARCH stories USING COVERING INDEX idx_stories_title_source_time") == 2, (
        plan
    )
    assert "SCAN" not in plan, plan


# -- Migration 4 ---------------------------------------------------------------------------------


def _every_row(db: sqlite3.Connection) -> dict[str, list[tuple[object, ...]]]:
    names = [
        str(row[0])
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            " AND name NOT LIKE 'stories_fts%' ORDER BY name"
        )
    ]
    return {
        name: [tuple(row) for row in db.execute(f'SELECT * FROM "{name}" ORDER BY 1, 2')]
        for name in names
    }


def test_migration_4_adds_the_index_to_a_version_3_database_and_keeps_its_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store, "MIGRATIONS", store.MIGRATIONS[:3])
    old = open_db(tmp_path)
    _seed_sources(old, 2)
    _put_story(old, 1, 2, "e.org/a", _LONG, utc_text(_BASE))
    old.execute(
        "INSERT INTO story_duplicates(story_id, duplicate_source_id, link, link_key,"
        " published_at, seen_at) VALUES(1, 1, 'l', 'e.org/dup', ?, 'f')",
        (utc_text(_BASE),),
    )
    old.commit()
    assert store.get_meta(old, "schema_version") == "3"
    assert not _index_exists(old)
    before = _every_row(old)
    assert before["sources"] and before["stories"] and before["story_duplicates"]
    old.close()
    monkeypatch.undo()
    for _ in range(2):  # the second open changes nothing
        new = open_db(tmp_path)
        assert store.get_meta(new, "schema_version") == "4"
        assert _index_exists(new)
        after = _every_row(new)
        before["meta"] = [row for row in before["meta"] if row[0] != "schema_version"]
        after["meta"] = [row for row in after["meta"] if row[0] != "schema_version"]
        assert after == before
        assert store._earliest_match(new, 1, "e.org/new", _LONG, _BASE) == 1
        new.close()


def _index_exists(db: sqlite3.Connection) -> bool:
    return (
        db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='index' AND name='idx_stories_title_source_time'"
        ).fetchone()
        is not None
    )
