"""The predecessor's ingest tests, carried: one pass over the stored sources, and source health.

Every test feeds `run_due` a recorded feed in place of `fetch`: nothing opens a connection."""

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from ingest_support import MERGER, NOW, Recorded, approve, count, group_with_topic
from test_signal_feeds import RSS

from credit_os.signal import ingest
from credit_os.signal.fetch import Fetched, FetchRefused
from credit_os.signal.groups import Act, create_group
from credit_os.signal.identity import User
from credit_os.signal.ingest import health, run_due
from credit_os.signal.store import (
    add_user,
    get_meta,
    last_check,
    open_db,
    propose_source,
    set_source_state,
)
from credit_os.signal.topics import add_topic


@pytest.fixture
def db(tmp_path: Path) -> sqlite3.Connection:
    return open_db(tmp_path)


@pytest.fixture
def db_a(db: sqlite3.Connection) -> sqlite3.Connection:
    approve(db, "A", "https://a.org/f")
    return db


def test_only_approved_sources_are_fetched_with_recorded_feed(db: sqlite3.Connection) -> None:
    a = approve(db, "A", "https://a.org/f")
    propose_source(db, "B", "news", "https://b.org/f", "x")  # stays proposed
    p = propose_source(db, "P", "news", "https://p.org/f", "x")
    set_source_state(db, p, "paused")
    fn = Recorded(RSS)
    assert run_due(db, NOW, fn) == [(a, True, "2 new")]
    assert [c[0] for c in fn.calls] == ["https://a.org/f"]


def test_source_is_not_checked_again_within_600_seconds_with_recorded_feed(
    db_a: sqlite3.Connection,
) -> None:
    fn = Recorded(RSS)
    run_due(db_a, NOW, fn)
    assert run_due(db_a, NOW + timedelta(seconds=599), fn) == []
    assert len(run_due(db_a, NOW + timedelta(seconds=600), fn)) == 1


def test_second_pass_sends_validators_and_adds_nothing_with_recorded_feed(
    db_a: sqlite3.Connection,
) -> None:
    fn = Recorded(RSS)
    run_due(db_a, NOW, fn)
    assert run_due(db_a, NOW + timedelta(hours=1), fn)[0][2] == "0 new"
    assert fn.calls[1][1] == '"v1"'
    assert count(db_a, "stories") == 2
    assert count(db_a, "story_duplicates") == 0


def test_failing_source_is_recorded_and_others_still_run_with_recorded_feed(
    db: sqlite3.Connection,
) -> None:
    bad = approve(db, "Bad", "https://bad.org/f")
    good = approve(db, "Good", "https://good.org/f")

    def fn(url: str, etag: str | None, modified: str | None) -> Fetched:
        if "bad" in url:
            raise FetchRefused("feed is larger than 2 MB")
        return Fetched(RSS, None, None)

    assert run_due(db, NOW, fn) == [(bad, False, "feed is larger than 2 MB"), (good, True, "2 new")]
    assert health(db, bad, NOW).state == "failing"
    assert health(db, bad, NOW).reason == "feed is larger than 2 MB"


def test_unparseable_feed_is_failing_with_the_parser_reason_with_recorded_feed(
    db_a: sqlite3.Connection,
) -> None:
    run_due(db_a, NOW, Recorded(b"not xml"))
    assert health(db_a, 1, NOW).state == "failing"
    assert health(db_a, 1, NOW).reason


REASON = "unexpected error (RuntimeError); see the log"


class RaisesForA:
    """A fetch that raises for source A's address and answers the recorded feed for the rest."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, url: str, etag: str | None, modified: str | None) -> Fetched:
        self.calls.append(url)
        if "a.org" in url:
            raise RuntimeError("boom 10.0.0.5")
        return Fetched(RSS, None, None)


def _two_sources_first_raises(db: sqlite3.Connection) -> tuple[int, int, RaisesForA]:
    a = approve(db, "A", "https://a.org/f")
    b = approve(db, "B", "https://b.org/f")
    return a, b, RaisesForA()


def test_an_unexpected_error_fails_that_source_and_the_rest_still_run_with_recorded_feed(
    db: sqlite3.Connection, caplog: pytest.LogCaptureFixture
) -> None:
    a, b, fn = _two_sources_first_raises(db)
    out = run_due(db, NOW, fn)
    assert out == [(a, False, REASON), (b, True, "2 new")]
    reasons = [row["reason"] for row in db.execute("SELECT reason FROM source_checks")]
    assert reasons and not any("10.0.0.5" in reason for reason in reasons)
    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert errors and errors[0].exc_info is not None
    assert "Traceback" in caplog.text and "boom 10.0.0.5" in caplog.text
    assert str(a) in errors[0].getMessage()


def test_a_source_that_raised_is_not_retried_within_600_seconds_with_recorded_feed(
    db: sqlite3.Connection,
) -> None:
    _a, _b, fn = _two_sources_first_raises(db)
    run_due(db, NOW, fn)
    fn.calls.clear()
    assert run_due(db, NOW + timedelta(seconds=60), fn) == []
    assert fn.calls == []
    run_due(db, NOW + timedelta(seconds=601), fn)
    assert sorted(fn.calls) == ["https://a.org/f", "https://b.org/f"]


def test_health_reports_a_source_that_raised_as_failing_with_recorded_feed(
    db: sqlite3.Connection,
) -> None:
    a, _b, fn = _two_sources_first_raises(db)
    run_due(db, NOW, fn)
    h = health(db, a, NOW)
    assert (h.state, h.reason) == ("failing", REASON)


def test_not_modified_is_ok_and_keeps_validators_with_recorded_feed(
    db_a: sqlite3.Connection,
) -> None:
    run_due(db_a, NOW, Recorded(RSS))
    # A real fetch merges the validator it sent into the 304's answer (S-2b, item 5); the
    # predecessor's stand-in answered None and ingest kept the old value. Ingest stores the
    # validator it sent, else the answer's (R58), so the stand-in answers as fetch does.
    out = run_due(db_a, NOW + timedelta(hours=1), lambda u, e, m: Fetched(None, e, m))
    assert out == [(1, True, "not modified")]
    seen: list[str | None] = []

    def fn(u: str, e: str | None, m: str | None) -> Fetched:
        seen.append(e)
        return Fetched(RSS, e, None)

    run_due(db_a, NOW + timedelta(hours=2), fn)
    assert seen == ['"v1"']


def test_health_states_and_weekly_counts_with_recorded_feed(db_a: sqlite3.Connection) -> None:
    assert health(db_a, 1, NOW).state == "never checked"
    run_due(db_a, NOW, Recorded(RSS))  # one item dated 13 Nov 08:00Z, one undated -> NOW
    h = health(db_a, 1, NOW)
    assert (h.state, h.per_week) == ("healthy", (0, 0, 0, 0, 0, 2))
    later = NOW + timedelta(days=8)
    run_due(db_a, later, Recorded(RSS))
    assert health(db_a, 1, later).state == "quiet"
    assert health(db_a, 1, later).per_week == (0, 0, 0, 0, 2, 0)


def test_source_whose_items_all_fold_is_healthy_with_its_items(db: sqlite3.Connection) -> None:
    body = (
        b'<rss version="2.0"><channel><item><title>Case 1 merger inquiry opened today</title>'
        b"<link>https://r.example.org/cases/1</link>"
        b"<pubDate>Fri, 13 Nov 2026 08:00:00 +0000</pubDate></item></channel></rss>"
    )
    for name in ("cases", "news"):
        sid = propose_source(db, name, "regulator", f"https://r.example.org/{name}.rss", "x")
        set_source_state(db, sid, "approved")
    run_due(db, NOW, Recorded(body))
    first, second = health(db, 1, NOW), health(db, 2, NOW)
    assert count(db, "story_duplicates") == 1
    assert second.state == "healthy"
    assert second.last_item == datetime(2026, 11, 13, 8, tzinfo=UTC)
    assert second.per_week == first.per_week == (0, 0, 0, 0, 0, 1)


def test_story_exactly_seven_days_old_is_in_the_previous_week() -> None:
    assert ingest._per_week([NOW - timedelta(days=7)], NOW) == (0, 0, 0, 0, 1, 0)


def test_a_new_story_posts_into_groups_that_carry_its_topic_with_recorded_feed(
    db_a: sqlite3.Connection,
) -> None:
    with_topic = group_with_topic(db_a)
    create_group(db_a, Act(User("ak", "writer"), NOW), "G2", "everyone", [])
    run_due(db_a, NOW, Recorded(MERGER))
    found = db_a.execute(
        "SELECT group_id, story_id, started_by, created_at FROM threads"
    ).fetchall()
    assert [tuple(r) for r in found] == [(with_topic, 1, None, NOW.isoformat())]
    run_due(db_a, NOW + timedelta(hours=1), Recorded(MERGER))
    assert count(db_a, "threads") == 1


def _fail_once_on_call(monkeypatch: pytest.MonkeyPatch, name: str, call_number: int) -> None:
    real = getattr(ingest, name)
    calls: list[tuple[object, ...]] = []

    def flaky(*args: object) -> object:
        calls.append(args)
        if len(calls) == call_number:
            raise sqlite3.OperationalError("database is locked")
        return real(*args)

    monkeypatch.setattr(ingest, name, flaky)


def _counts(db: sqlite3.Connection) -> tuple[int, int, int]:
    return (count(db, "stories"), count(db, "topic_stories"), count(db, "threads"))


@pytest.mark.parametrize("step", ["auto_post", "match_story"])
def test_a_failed_match_or_post_keeps_nothing_with_recorded_feed_and_an_injected_fault(
    db_a: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch, step: str
) -> None:
    group = group_with_topic(db_a)
    _fail_once_on_call(monkeypatch, step, 1)
    (result,) = run_due(db_a, NOW, Recorded(MERGER))
    assert result[1:] == (False, "unexpected error (OperationalError); see the log")
    assert _counts(db_a) == (0, 0, 0)
    assert run_due(db_a, NOW + timedelta(seconds=601), Recorded(MERGER))[0][1:] == (
        True,
        "2 new",
    )
    threads = db_a.execute("SELECT group_id, story_id, started_by FROM threads").fetchall()
    assert [tuple(row) for row in threads] == [(group, 1, None)]
    assert count(db_a, "topic_stories") == 1


def test_an_entry_stored_before_the_failing_one_stays_with_recorded_feed_and_an_injected_fault(
    db_a: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    group_with_topic(db_a)
    _fail_once_on_call(monkeypatch, "auto_post", 2)
    (result,) = run_due(db_a, NOW, Recorded(MERGER))
    assert result[1] is False
    assert _counts(db_a) == (1, 1, 1)
    assert run_due(db_a, NOW + timedelta(seconds=601), Recorded(MERGER))[0][1:] == (
        True,
        "1 new",
    )
    assert _counts(db_a) == (2, 1, 1)


def test_pass_records_its_time_and_matches_new_stories_with_recorded_feed(
    db_a: sqlite3.Connection,
) -> None:
    add_user(db_a, "ak", "writer")
    tid = add_topic(db_a, "Opens", ["opens review"], [], "ak")
    assert tid == 1
    run_due(db_a, NOW, Recorded(RSS))
    assert get_meta(db_a, "last_pass_at") == NOW.isoformat()
    assert count(db_a, "topic_stories") == 1
    run_due(db_a, NOW + timedelta(seconds=30), Recorded(RSS))
    assert get_meta(db_a, "last_pass_at") == (NOW + timedelta(seconds=30)).isoformat()


def _feed(*items: tuple[str, str, str]) -> bytes:
    body = "".join(
        f"<item><title>{t}</title><link>{u}</link><pubDate>{d}</pubDate></item>"
        for t, u, d in items
    )
    return f'<rss version="2.0"><channel>{body}</channel></rss>'.encode()


OLD = (
    "An old story about the central bank",
    "https://e.org/old",
    "Thu, 15 Oct 2026 08:00:00 +0000",
)
NEW = (
    "A new story about the merger review",
    "https://e.org/new",
    "Thu, 12 Nov 2026 08:00:00 +0000",
)
THIRD = (
    "A third story about interest rates",
    "https://e.org/third",
    "Thu, 12 Nov 2026 08:00:00 +0000",
)


def test_health_reports_the_newest_story_and_the_time_of_the_last_check(
    db_a: sqlite3.Connection,
) -> None:
    run_due(db_a, NOW, Recorded(_feed(OLD, NEW)))
    h = health(db_a, 1, NOW)
    assert (h.state, h.last_item, h.last_check) == (
        "healthy",
        datetime(2026, 11, 12, 8, tzinfo=UTC),
        NOW,
    )


def test_a_source_checked_ok_whose_feed_has_no_item_is_quiet(db_a: sqlite3.Connection) -> None:
    assert run_due(db_a, NOW, Recorded(_feed())) == [(1, True, "0 new")]
    assert health(db_a, 1, NOW).state == "quiet"


def test_a_check_counts_only_the_stories_new_in_that_pass(db_a: sqlite3.Connection) -> None:
    run_due(db_a, NOW, Recorded(_feed(OLD, NEW)))
    later = NOW + timedelta(hours=1)
    assert run_due(db_a, later, Recorded(_feed(OLD, NEW, THIRD))) == [(1, True, "1 new")]
    check = last_check(db_a, 1)
    assert check is not None
    assert check["new_stories"] == 1


def test_an_entry_folded_into_another_sources_story_is_not_counted_as_new(
    db: sqlite3.Connection,
) -> None:
    approve(db, "A", "https://a.org/f")
    approve(db, "B", "https://b.org/f")
    out = run_due(db, NOW, Recorded(_feed(NEW)))
    assert out == [(1, True, "1 new"), (2, True, "0 new")]
    counts = [
        tuple(r) for r in db.execute("SELECT source_id, new_stories FROM source_checks ORDER BY id")
    ]
    assert counts == [(1, 1), (2, 0)]
