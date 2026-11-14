"""Carried from the predecessor's tests/test_signal_feedview.py, adapted to credit_os.signal.

`threads.py` is not ported yet, so a thread (what `share_story` makes) is inserted with plain SQL.
"""

from __future__ import annotations

import sqlite3
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from credit_os.signal.feeds import Entry
from credit_os.signal.feedview import (
    CardThread,
    Page,
    ViewError,
    feed,
    new_count,
    save,
    unsave,
)
from credit_os.signal.groups import Act, create_group, join
from credit_os.signal.identity import User
from credit_os.signal.store import (
    add_story,
    add_user,
    open_db,
    propose_source,
    set_source_state,
)
from credit_os.signal.topics import add_topic, follow

AK = User("ak", "writer")
ML = User("ml", "writer")
RD = User("rd", "reader")
T0 = datetime(2026, 11, 13, 9, tzinfo=UTC)
FETCHED = datetime(2026, 11, 13, 9, 40, tzinfo=UTC)
LAST = datetime(2026, 11, 13, 9, 35, tzinfo=UTC)


def team_db(tmp_path: Path) -> sqlite3.Connection:
    """Users ak and ml (writers) and rd (reader); two approved sources with one story each."""
    db = open_db(tmp_path)
    for user in (AK, ML, RD):
        add_user(db, user.name, user.role)
    for number, kind in ((1, "regulator"), (2, "news")):
        propose_source(db, f"Source {number}", kind, f"https://s{number}.org/f", "ak")
        set_source_state(db, number, "approved")
        entry = Entry(f"Story {number}", f"https://s{number}.org/{number}", T0, f"summary {number}")
        assert add_story(db, number, entry, T0) == "new"
    return db


def share(db: sqlite3.Connection, group_id: int, story_id: int, by: str, note: str) -> None:
    """A thread on a story started by a person, with the note as its first comment: the rows
    `threads.share_story` writes, which that module will own once it is ported."""
    stamp = T0.isoformat()
    cur = db.execute(
        "INSERT INTO threads(group_id, story_id, started_by, created_at, last_activity_at)"
        " VALUES(?, ?, ?, ?, ?)",
        (group_id, story_id, by, stamp, stamp),
    )
    db.execute(
        "INSERT INTO comments(thread_id, author, text, created_at) VALUES(?, ?, ?, ?)",
        (cur.lastrowid, by, note, stamp),
    )
    db.commit()


def build_feed_db(root: Path) -> sqlite3.Connection:
    """Two sources, 35 regulator stories one minute apart, a newer wire story, one link fold."""
    db = open_db(root)
    for name, kind, url in (
        ("Authority", "regulator", "https://a.org/f"),
        ("Wire", "news", "https://w.org/f"),
    ):
        set_source_state(db, propose_source(db, name, kind, url, "x"), "approved")
    for n in range(1, 36):
        entry = Entry(
            f"Story {n:02d}",
            f"https://a.org/{n}",
            LAST - timedelta(minutes=35 - n),
            f"Summary {n}",
        )
        add_story(db, 1, entry, FETCHED)
    # Same link as source 1's Story 35: a link fold (titles under four words never fold by title).
    same_link = Entry("Story 35", "https://a.org/35", LAST, "Summary 35")
    assert add_story(db, 2, same_link, FETCHED) == "duplicate"
    wire = Entry(
        "Wire piece on remedy", "https://w.org/1", LAST + timedelta(minutes=1), "About a remedy"
    )
    add_story(db, 2, wire, FETCHED)
    add_topic(db, "Remedy", ["remedy"], [], "x")
    return db


@pytest.fixture
def db_feed(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    db = build_feed_db(tmp_path)
    yield db
    db.close()


@contextmanager
def feed_db() -> Iterator[sqlite3.Connection]:
    with tempfile.TemporaryDirectory() as folder:
        db = build_feed_db(Path(folder))
        try:
            yield db
        finally:
            db.close()


def test_latest_pages_by_30_newest_first(db_feed: sqlite3.Connection) -> None:
    first = feed(db_feed, "ak", "latest")
    assert len(first.cards) == 30 and first.cards[0].title == "Wire piece on remedy"
    assert first.cards[1].title == "Story 35" and first.cards[1].other_sources == 1
    second = feed(db_feed, "ak", "latest", before=first.next_before)
    assert [c.title for c in second.cards] == [f"Story {n:02d}" for n in range(6, 0, -1)]
    assert second.next_before is None


def test_kind_filter_and_card_fields(db_feed: sqlite3.Connection) -> None:
    page = feed(db_feed, "ak", "latest", kind="news")
    (card,) = page.cards
    assert (card.source, card.kind, card.published_at, card.saved, card.topics) == (
        "Wire",
        "news",
        "2026-11-13T09:36:00+00:00",
        False,
        ("Remedy",),
    )


def test_foryou_is_followed_topics_only(db_feed: sqlite3.Connection) -> None:
    assert feed(db_feed, "ak", "foryou").cards == ()
    follow(db_feed, "ak", 1)
    assert [c.title for c in feed(db_feed, "ak", "foryou").cards] == ["Wire piece on remedy"]
    assert feed(db_feed, "ml", "foryou").cards == ()


def test_topic_view_and_unknown_topic(db_feed: sqlite3.Connection) -> None:
    assert len(feed(db_feed, "ak", "topic:1").cards) == 1
    with pytest.raises(ViewError):
        feed(db_feed, "ak", "topic:99")


def test_save_is_personal_idempotent_and_listed(db_feed: sqlite3.Connection) -> None:
    save(db_feed, "ak", 5)
    save(db_feed, "ak", 5)
    assert [c.id for c in feed(db_feed, "ak", "saved").cards] == [5]
    assert feed(db_feed, "ml", "saved").cards == ()
    before = "2026-11-13T09:06:00+00:00|6"
    assert next(c for c in feed(db_feed, "ak", "latest", before=before).cards if c.id == 5).saved
    unsave(db_feed, "ak", 5)
    unsave(db_feed, "ak", 5)
    assert feed(db_feed, "ak", "saved").cards == ()
    with pytest.raises(ViewError):
        save(db_feed, "ak", 9999)


def test_search_matches_all_terms(db_feed: sqlite3.Connection) -> None:
    found = feed(db_feed, "ak", "latest", query="wire remedy").cards
    assert [c.title for c in found] == ["Wire piece on remedy"]
    assert feed(db_feed, "ak", "latest", query="wire absent").cards == ()


@pytest.mark.parametrize(
    "query", ['"', 'a"b', "*", "NEAR", "x AND", "-", "(", "title:x", "\x00", "\u00df" * 300]
)
def test_search_text_is_never_query_syntax(db_feed: sqlite3.Connection, query: str) -> None:
    feed(db_feed, "ak", "latest", query=query)  # must not raise


@settings(suppress_health_check=[HealthCheck.too_slow], deadline=None, max_examples=50)
@given(st.text(max_size=200))
def test_any_search_text_returns_a_page(query: str) -> None:
    with feed_db() as db:
        assert isinstance(feed(db, "ak", "latest", query=query), Page)


@pytest.mark.parametrize(
    "bad",
    [
        {"view": "top"},
        {"view": "latest", "kind": "blog"},
        {"view": "latest", "before": "x"},
        {"view": "topic:abc"},
    ],
)
def test_bad_requests_raise_view_error(db_feed: sqlite3.Connection, bad: dict[str, Any]) -> None:
    with pytest.raises(ViewError):
        feed(db_feed, "ak", **bad)


def test_page_reports_the_newest_story_id(db_feed: sqlite3.Connection) -> None:
    assert feed(db_feed, "ak", "latest").newest == 36


def test_new_count_counts_ids_after_the_cursor(db_feed: sqlite3.Connection) -> None:
    assert new_count(db_feed, "ak", "latest", 36) == 0
    assert new_count(db_feed, "ak", "latest", 30) == 6
    assert new_count(db_feed, "ak", "latest", 0) == 36
    assert new_count(db_feed, "ak", "topic:1", 0) == 1


@pytest.mark.parametrize("after", [-1, 2**63, True, "x", 1.5, None])
def test_new_count_refuses_a_bad_after(db_feed: sqlite3.Connection, after: Any) -> None:
    with pytest.raises(ViewError):
        new_count(db_feed, "ak", "latest", after)


def test_empty_store_newest_is_zero(tmp_path: Path) -> None:
    db = open_db(tmp_path)
    try:
        assert feed(db, "ak", "latest").newest == 0
    finally:
        db.close()


def test_story_stored_after_the_load_with_an_earlier_fetched_at_is_counted(
    db_feed: sqlite3.Connection,
) -> None:
    """An ingest pass stamps fetched_at at its start but commits later."""
    loaded = feed(db_feed, "ak", "latest").newest
    early = FETCHED - timedelta(hours=1)  # earlier than the page load, inserted after it
    entry = Entry("Late commit story", "https://a.org/late", LAST, "Committed after the load")
    assert add_story(db_feed, 1, entry, early) == "new"
    assert new_count(db_feed, "ak", "latest", loaded) == 1


@pytest.mark.parametrize(
    "bad",
    [
        {"view": "topic:99999999999999999999"},
        {"view": "latest", "before": "2026-11-13T09:00:00+00:00|99999999999999999999"},
        {"view": "latest", "before": "2026-11-13T09:00:00|5"},
    ],
)
def test_oversized_ids_and_zoneless_cursor_raise_view_error(
    db_feed: sqlite3.Connection, bad: dict[str, Any]
) -> None:
    with pytest.raises(ViewError):
        feed(db_feed, "ak", **bad)


def test_ids_of_thousands_of_digits_raise_view_error(db_feed: sqlite3.Connection) -> None:
    with pytest.raises(ViewError):
        feed(db_feed, "ak", "topic:" + "9" * 5000)
    with pytest.raises(ViewError):
        feed(db_feed, "ak", "latest", before="2026-11-13T09:00:00+00:00|" + "9" * 5000)


def test_cards_carry_only_visible_threads(tmp_path: Path) -> None:
    db = team_db(tmp_path)
    open_g = create_group(db, Act(AK, T0), "TMT", "everyone", [])
    closed = create_group(db, Act(AK, T0), "Deal team", "invited", [])
    share(db, open_g, 1, "ak", "Heavier than we assumed.")
    share(db, closed, 1, "ak", "secret")
    card = feed(db, "ml", "latest").cards[-1]  # story 1
    assert card.threads == (CardThread(1, "TMT", 1, "ak", "Heavier than we assumed."),)
    assert len(feed(db, "ak", "latest").cards[-1].threads) == 2
    assert feed(db, "ml", "latest").cards[0].threads == ()
    db.close()


def test_shared_filter_and_for_you_follow_membership(tmp_path: Path) -> None:
    db = team_db(tmp_path)
    gid = create_group(db, Act(AK, T0), "TMT", "everyone", [])
    share(db, gid, 1, "ak", "look")
    assert feed(db, "ml", "latest", shared=True).cards == ()
    assert feed(db, "ml", "foryou").cards == ()
    join(db, "ml", gid, T0)
    assert [c.id for c in feed(db, "ml", "latest", shared=True).cards] == [1]
    assert [c.id for c in feed(db, "ml", "foryou").cards] == [1]
    assert [c.id for c in feed(db, "ak", "foryou").cards] == [1]
    assert feed(db, "ak", "latest", shared=True).cards == ()
    assert new_count(db, "ml", "foryou", 0) == 1 and new_count(db, "rd", "foryou", 0) == 0
    db.close()
