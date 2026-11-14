"""The feed view under the port's rulings, part 2: bad input and its error texts, cursors, views
and kinds, hostile search text, and the note (R10, R15, R33).

Expected values here are written by hand; the shared grid is in `feedview_grid.py`.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from feedview_grid import (
    T0,
    VIEWS,
    cursor,
    grid_db,
    thread,
)

from credit_os.signal import feedview
from credit_os.signal.feedview import (
    MAX_ID,
    CardThread,
    Page,
    ViewError,
    card_for,
    feed,
    new_count,
    save,
    unsave,
)
from credit_os.signal.store import (
    StoreError,
    StoreUnusable,
)


@pytest.fixture
def grid(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    db = grid_db(tmp_path)
    yield db
    db.close()


# --- bad input: types and names are StoreError, request-shaped text is ViewError (R15, R33) ------

UNCLEAN = ["", " ", "a\u200bk", "a\x00k", "x" * 61, "ak ", "a\ud800k", "\u3164"]
NOT_TEXT: list[Any] = [None, 5, 1.5, b"ak", ["ak"], True]


@pytest.mark.parametrize("name", [*UNCLEAN, *NOT_TEXT])
def test_a_name_that_is_not_a_clean_name_is_a_store_error_everywhere(
    grid: sqlite3.Connection, name: Any
) -> None:
    calls: list[Callable[[], object]] = [
        lambda: feed(grid, name, "latest"),
        lambda: new_count(grid, name, "latest", 0),
        lambda: card_for(grid, name, 1),
        lambda: save(grid, name, 1),
        lambda: unsave(grid, name, 1),
    ]
    for call in calls:
        with pytest.raises(StoreError) as refused:
            call()
        assert not isinstance(refused.value, (ViewError, StoreUnusable))
    assert not grid.in_transaction


WRONG_TYPE_FEEDS: list[dict[str, Any]] = [
    {"view": 5},
    {"view": None},
    {"view": b"latest"},
    {"view": "latest", "kind": 5},
    {"view": "latest", "kind": b"news"},
    {"view": "latest", "query": 5},
    {"view": "latest", "query": None},
    {"view": "latest", "query": "\ud800"},
    {"view": "latest", "before": 5},
    {"view": "latest", "before": b"x|1"},
    {"view": "latest", "shared": 1},
    {"view": "latest", "shared": "yes"},
    {"view": "latest", "limit": 5},
]


@pytest.mark.parametrize("bad", WRONG_TYPE_FEEDS)
def test_a_value_of_the_wrong_type_is_a_store_error_not_a_type_error(
    grid: sqlite3.Connection, bad: dict[str, Any]
) -> None:
    with pytest.raises(StoreError) as refused:
        feed(grid, "ak", **bad)
    assert not isinstance(refused.value, (ViewError, StoreUnusable))
    assert not grid.in_transaction


@pytest.mark.parametrize("story", [None, "5", 5.0, True, b"5", [5]])
def test_a_story_id_of_the_wrong_type_is_a_store_error(
    grid: sqlite3.Connection, story: Any
) -> None:
    for call in (card_for, save, unsave):
        with pytest.raises(StoreError) as refused:
            call(grid, "ak", story)
        assert not isinstance(refused.value, ViewError)


@pytest.mark.parametrize(
    "after",
    [
        -1,
        2**63,
        pytest.param(2**20000, id="2**20000"),
        pytest.param(-(2**20000), id="-2**20000"),
        True,
        False,
        "x",
        pytest.param("9" * 5000, id="9-times-5000"),
        1.5,
        None,
        b"1",
    ],
)
def test_a_bad_after_is_a_view_error_with_a_short_text(
    grid: sqlite3.Connection, after: Any
) -> None:
    with pytest.raises(ViewError) as refused:
        new_count(grid, "ak", "latest", after)
    assert len(str(refused.value)) < 200


HUGE = "a" * 10_000
DIGITS = "9" * 10_000
STAMP = "2026-11-13T09:00:00+00:00"
LONG_INPUTS: list[dict[str, Any]] = [
    {"view": HUGE},
    {"view": "topic:" + DIGITS},
    {"view": "topic:" + HUGE},
    {"view": "latest", "kind": HUGE},
    {"view": "latest", "before": HUGE},
    {"view": "latest", "before": HUGE + "|1"},
    {"view": "latest", "before": STAMP + "|" + DIGITS},
    {"view": "latest", "before": STAMP + "|" + HUGE},
    {"view": "latest", "before": "2026-11-13T09:00:00|" + "1"},
]


@pytest.mark.parametrize("bad", LONG_INPUTS)
def test_an_error_text_carries_at_most_120_characters_of_input(
    grid: sqlite3.Connection, bad: dict[str, Any]
) -> None:
    with pytest.raises(ViewError) as refused:
        feed(grid, "ak", **bad)
    text = str(refused.value)
    assert len(text) < 200
    assert "a" * 121 not in text and "9" * 121 not in text


@pytest.mark.parametrize(
    "before",
    [
        "",
        "|",
        "|5",
        "x|5",
        STAMP,
        STAMP + "|",
        STAMP + "|x",
        STAMP + "|-1",
        STAMP + "|1.5",
        STAMP + "|\u0665",
        STAMP + "|" + str(MAX_ID + 1),
        "2026-13-45T99:00:00+00:00|1",
        "\ud800|1",
        "\x00|1",
    ],
)
def test_a_malformed_cursor_is_a_view_error(grid: sqlite3.Connection, before: str) -> None:
    with pytest.raises(ViewError):
        feed(grid, "ak", "latest", before=before)


def test_a_cursor_at_the_last_id_is_accepted(grid: sqlite3.Connection) -> None:
    page = feed(grid, "ak", "latest", before=f"{STAMP}|{MAX_ID}")
    assert [c.id for c in page.cards] == [8, 7, 6, 5, 4, 3, 2, 1]


def test_a_cursor_without_a_bar_or_a_zone_is_refused_for_that_reason(
    grid: sqlite3.Connection,
) -> None:
    with pytest.raises(ViewError, match=r"^malformed cursor 'x'$"):
        feed(grid, "ak", "latest", before="x")
    with pytest.raises(ViewError, match=r"^cursor time '2026-11-13T09:00:00' has no time zone$"):
        feed(grid, "ak", "latest", before="2026-11-13T09:00:00|1")


@pytest.mark.parametrize(
    ("view", "filters", "reason"),
    [
        ("top", {"before": "x"}, r"^unknown view 'top'$"),
        ("top", {"kind": "blog"}, r"^unknown view 'top'$"),
        ("topic:99", {"kind": "blog"}, r"^no topic with id 99$"),
        ("topic:99", {"before": "x"}, r"^no topic with id 99$"),
        ("latest", {"kind": "blog", "before": "x"}, r"^unknown kind 'blog'$"),
    ],
)
def test_the_view_is_refused_before_the_filters_when_a_request_has_two_faults(
    grid: sqlite3.Connection, view: str, filters: dict[str, Any], reason: str
) -> None:
    with pytest.raises(ViewError, match=reason):
        feed(grid, "ak", view, **filters)


@pytest.mark.parametrize(
    "before",
    [
        "0001-01-01T00:00:00+05:00|1",  # UTC would be year 0
        "0001-01-01T00:00:00+23:59|1",
        "9999-12-31T23:59:59-05:00|1",  # UTC would be year 10000
        "9999-12-31T23:59:59.999999-23:59|1",
    ],
)
def test_a_cursor_time_outside_the_utc_range_is_a_view_error(
    grid: sqlite3.Connection, before: str
) -> None:
    with pytest.raises(ViewError, match="out of range"):
        feed(grid, "ak", "latest", before=before)
    assert not grid.in_transaction


def test_cursor_times_at_the_edges_of_year_1_and_9999_are_read(grid: sqlite3.Connection) -> None:
    for early in ("0001-01-01T00:00:00+00:00", "0001-01-01T00:00:00-05:00"):
        assert feed(grid, "ak", "latest", before=early + "|1") == Page((), None, 8)
    for late in ("9999-12-31T23:59:59.999999+00:00", "9999-12-31T23:59:59+05:00"):
        page = feed(grid, "ak", "latest", before=late + "|1")
        assert [c.id for c in page.cards] == [8, 7, 6, 5, 4, 3, 2, 1]


def test_a_failure_of_utc_text_is_mapped_only_when_it_is_bad_input(
    grid: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(_: datetime) -> str:
        raise StoreError("range")

    def unusable(_: datetime) -> str:
        raise StoreUnusable("not input")

    monkeypatch.setattr(feedview, "utc_text", refuse)
    with pytest.raises(ViewError, match="out of range"):
        feed(grid, "ak", "latest", before=cursor(4))
    monkeypatch.setattr(feedview, "utc_text", unusable)
    with pytest.raises(StoreUnusable) as refused:
        feed(grid, "ak", "latest", before=cursor(4))
    assert not isinstance(refused.value, ViewError)


@pytest.mark.parametrize(
    "view",
    [
        "",
        "top",
        "Latest",
        "latest ",
        "topic",
        "topic:",
        "topic: 1",
        "topic:-1",
        "topic:1.5",
        "topic:\u0661",
        "t:1",
        "topics:1",
        "Topic:1",
        "topic:0",
        "topic:3",
        "topic:" + str(MAX_ID),
        "topic:" + str(MAX_ID + 1),
        "\ud800",
        "topic:\ud800",
    ],
)
def test_an_unknown_view_or_topic_is_a_view_error(grid: sqlite3.Connection, view: str) -> None:
    with pytest.raises(ViewError):
        feed(grid, "ak", view)
    with pytest.raises(ViewError):
        new_count(grid, "ak", view, 0)


@pytest.mark.parametrize("kind", ["", "News", "blog", "news ", "\ud800"])
def test_an_unknown_kind_is_a_view_error(grid: sqlite3.Connection, kind: str) -> None:
    with pytest.raises(ViewError):
        feed(grid, "ak", "latest", kind=kind)


def test_a_none_kind_and_before_are_no_filter(grid: sqlite3.Connection) -> None:
    page = feed(grid, "ak", "latest", kind=None, before=None)
    assert [c.id for c in page.cards] == [8, 7, 6, 5, 4, 3, 2, 1]


# --- search text goes through fts_phrase ---------------------------------------------------------

HOSTILE = [
    '"',
    '""',
    '"""',
    'a"b',
    "'",
    "*",
    "**",
    "NEAR",
    "NEAR(a b)",
    "NEAR/2",
    "x AND",
    "AND",
    "OR",
    "NOT",
    "a OR b",
    "-",
    "--",
    "(",
    ")",
    "()",
    "title:x",
    "{title}:x",
    "^x",
    "x*",
    "+",
    ":",
    "a:b",
    "\x00",
    "\x00" * 100,
    "a\x00b",
    "\ufffe",
    "\ufeff",
    "\U0010ffff",
    "\\",
    "%",
    "_",
    "; DROP TABLE stories",
    "x" * 10_000,
    "\u00df" * 10_000,
    '"' * 10_000,
    "(" * 10_000,
    "a " * 5_000,
    "remedy " * 2_000,
    "\u0301" * 500,
    "\t\n\r\x0b\x0c",
    "\u2028\u2029\u00a0",
    "select * from stories",
    "\x1f\x7f",
]


def _hostile_id(query: str) -> str:
    """A short ASCII id: Windows refuses an environment variable over 32,767 characters."""
    head = ascii(query[:24])[1:-1]
    return f"{head}-len{len(query)}"


@pytest.mark.parametrize("query", HOSTILE, ids=_hostile_id)
def test_hostile_search_text_returns_a_page_for_every_view(
    grid: sqlite3.Connection, query: str
) -> None:
    for view in VIEWS:
        assert isinstance(feed(grid, "ak", view, query=query), Page)
    assert grid.execute("SELECT count(*) FROM stories").fetchone()[0] == 8
    assert not grid.in_transaction


def test_search_syntax_is_words_not_operators(grid: sqlite3.Connection) -> None:
    def found(query: str) -> list[int]:
        return [c.id for c in feed(grid, "ak", "latest", query=query).cards]

    assert found("remedy OR delta") == []  # three words that must all be present
    assert found("remedy NOT rates") == []
    assert found("remedy") == [7, 5, 2, 1]
    assert found("remedy rates") == [7, 2]
    assert found("rem*") == []  # no prefix operator
    assert found("title:alpha") == []  # no column filter
    assert found("NEAR(alpha remedy)") == []
    assert found("   ") == [8, 7, 6, 5, 4, 3, 2, 1]  # blank text is no search


def test_only_the_first_hundred_characters_of_a_search_are_used(grid: sqlite3.Connection) -> None:
    padded = "remedy" + " " * 2_000
    assert [c.id for c in feed(grid, "ak", "latest", query=padded).cards] == [7, 5, 2, 1]
    cut = "remedy " + "x" * 200  # the second word is cut at 100 characters and is found nowhere
    assert feed(grid, "ak", "latest", query=cut).cards == ()


def test_search_cut_falls_after_the_hundredth_character(grid: sqlite3.Connection) -> None:
    def found(query: str) -> list[int]:
        return [c.id for c in feed(grid, "ak", "latest", query=query).cards]

    assert found("remedy" + " " * 94 + "absent") == [7, 5, 2, 1]  # the 101st character is cut
    assert found("remedy" + " " * 93 + "a") == []  # the 100th is kept: a term no story has


def test_new_count_accepts_the_largest_id_and_refuses_the_next(grid: sqlite3.Connection) -> None:
    assert new_count(grid, "ak", "latest", MAX_ID) == 0
    with pytest.raises(ViewError):
        new_count(grid, "ak", "latest", MAX_ID + 1)


def test_a_note_is_the_starters_first_live_comment_cut_to_140_and_the_count_is_live_ones(
    grid: sqlite3.Connection,
) -> None:
    stamp = T0.isoformat()
    for story, by, comments in (
        (4, "ml", [("ml", "x" * 10, True), ("ak", "reply", False), ("ml", "y" * 141, False)]),
        (2, "ak", [("ak", "w" * 140, False)]),
    ):
        number = thread(grid, 1, story, None)  # a thread with no comment of its own
        grid.execute("UPDATE threads SET started_by=? WHERE id=?", (by, number))
        for author, text, deleted in comments:
            grid.execute(
                "INSERT INTO comments(thread_id, author, text, created_at, deleted_at)"
                " VALUES(?, ?, ?, ?, ?)",
                (number, author, text, stamp, stamp if deleted else None),
            )
    grid.commit()
    assert card_for(grid, "ml", 4).threads == (CardThread(6, "Open desk", 2, "ml", "y" * 140),)
    assert card_for(grid, "ml", 2).threads == (CardThread(7, "Open desk", 1, "ak", "w" * 140),)


def test_a_note_is_the_first_of_the_starters_live_comments(grid: sqlite3.Connection) -> None:
    number = thread(grid, 1, 4, None)
    grid.execute("UPDATE threads SET started_by='ml' WHERE id=?", (number,))
    for text in ("first note", "second note"):
        grid.execute(
            "INSERT INTO comments(thread_id, author, text, created_at) VALUES(?, 'ml', ?, ?)",
            (number, text, T0.isoformat()),
        )
    grid.commit()
    assert card_for(grid, "ml", 4).threads == (CardThread(6, "Open desk", 2, "ml", "first note"),)


@pytest.mark.parametrize("query", ["remedy", "zzzabsent"])
def test_a_search_page_is_driven_from_the_full_text_table_not_a_scan_of_stories(
    grid: sqlite3.Connection, query: str
) -> None:
    seen: list[str] = []
    grid.set_trace_callback(seen.append)
    feed(grid, "ak", "latest", query=query)
    grid.set_trace_callback(None)
    (page,) = [text for text in seen if text.startswith("SELECT s.id, s.title")]
    first = grid.execute("EXPLAIN QUERY PLAN " + page).fetchone()
    assert first["detail"].startswith("SEARCH s USING INTEGER PRIMARY KEY"), first["detail"]


def test_a_view_error_is_a_value_error_and_not_a_store_error() -> None:
    assert issubclass(ViewError, ValueError)
    assert not issubclass(ViewError, StoreError)
