"""Ingest rules from the rulings (R10, R15, R29, R34, R40, R41) and the reviews' lists.

Where a test reaches `fetch.fetch` it goes through the port's scripted connector and the guard of
`signal_fetch_support` (named below, so it applies): no test opens a network connection."""

import gc
import logging
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Any, cast

import pytest
from ingest_support import MERGER, NOW, Recorded, approve, count, group_with_topic, snapshot
from signal_fetch_support import (
    PUBLIC,
    Reply,
    Wire,
    no_outside_network,
    redirect,
    wait_for_all_lookup_slots,
)
from test_signal_feeds import RSS

from credit_os.signal import feeds, fetch, ingest
from credit_os.signal.feeds import Entry, FeedError
from credit_os.signal.fetch import Fetched, FetchRefused, LookupCapRefused, Wiring
from credit_os.signal.groups import Act, create_group
from credit_os.signal.identity import User
from credit_os.signal.ingest import health, run_due
from credit_os.signal.store import (
    Check,
    StoreError,
    StoreUnusable,
    add_story,
    get_meta,
    last_check,
    open_db,
    record_check,
    sources,
    write_transaction,
)
from credit_os.signal.topics import add_topic

_guard = no_outside_network  # the guard is autouse; naming it applies it to this file

DTD_FEED = b'<?xml version="1.0"?><!DOCTYPE rss [<!ENTITY x "y">]>' + RSS.split(b"?>", 1)[1]
GOOD = Entry("First story about a merger review", "https://e.org/1", NOW, "")
MORE = Entry("Second story about a merger review", "https://e.org/2", NOW, "")
BAD_TEXT = Entry("lone surrogate \ud800 in a title", "https://e.org/bad", NOW, "")
BAD_TIME = Entry("A story with a naive time", "https://e.org/naive", NOW.replace(tzinfo=None), "")


@pytest.fixture
def db(tmp_path: Path) -> sqlite3.Connection:
    return open_db(tmp_path)


@pytest.fixture
def db_a(db: sqlite3.Connection) -> sqlite3.Connection:
    approve(db, "A", "https://a.org/f")
    return db


def _entries(monkeypatch: pytest.MonkeyPatch, *entries: Entry) -> None:
    monkeypatch.setattr(ingest, "parse_feed", lambda body: list(entries))


def test_the_fetch_cap_and_the_parser_cap_are_the_same_number() -> None:
    assert fetch.MAX_BYTES == feeds.MAX_BYTES == 2_097_152


# A refusal is for the whole feed (R10, feeds review "For the ingest brief" 1 to 3)
def test_a_refused_feed_stores_nothing_and_records_the_reason(db_a: sqlite3.Connection) -> None:
    (result,) = run_due(db_a, NOW, Recorded(DTD_FEED))
    assert result == (1, False, "feed declares a DTD or entities")
    assert all(count(db_a, table) == 0 for table in ("stories", "story_duplicates"))
    check = last_check(db_a, 1)
    assert check is not None
    assert (check["ok"], check["reason"], check["new_stories"]) == (
        0,
        "feed declares a DTD or entities",
        0,
    )
    assert health(db_a, 1, NOW).state == "failing"


def test_a_refused_feed_keeps_the_stored_validators(db_a: sqlite3.Connection) -> None:
    run_due(db_a, NOW, Recorded(RSS, etag='"v1"'))
    run_due(db_a, NOW + timedelta(hours=1), Recorded(b"not xml", etag='"v2"'))
    check = last_check(db_a, 1)
    assert check is not None
    assert (check["ok"], check["etag"]) == (0, '"v1"')


class Survivors:
    """The exceptions of one kind that are alive now and were not alive when this was made.

    The earlier ones are held, so a new exception cannot take a dead one's address."""

    def __init__(self, kind: type[BaseException]) -> None:
        self.kind = kind
        self.before = self._alive()

    def _alive(self) -> list[object]:
        gc.collect()
        return [obj for obj in gc.get_objects() if type(obj) is self.kind]

    def new(self) -> list[object]:
        known = {id(obj) for obj in self.before}
        return [obj for obj in self._alive() if id(obj) not in known]


def test_no_feed_or_fetch_refusal_is_kept_or_logged_with_its_chain(
    db: sqlite3.Connection, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    approve(db, "A", "https://a.org/f")
    approve(db, "B", "https://b.org/f")

    def fn(url: str, etag: str | None, modified: str | None) -> Fetched:
        if "a.org" in url:
            raise FetchRefused("feed is larger than 2 MB") from ValueError("SECRET-CAUSE")
        return Fetched(b"x", None, None)

    def refuse(body: bytes) -> list[Entry]:
        raise FeedError("feed is not valid XML") from ValueError("SECRET-FEED-TEXT")

    monkeypatch.setattr(ingest, "parse_feed", refuse)
    refusals, errors = Survivors(FetchRefused), Survivors(FeedError)
    with caplog.at_level(logging.DEBUG):
        out = run_due(db, NOW, fn)
    assert out == [(1, False, "feed is larger than 2 MB"), (2, False, "feed is not valid XML")]
    assert not caplog.records
    assert "SECRET" not in caplog.text
    assert refusals.new() == [] and errors.new() == []


def test_a_parser_type_error_is_a_caller_bug_not_a_feed_refusal(
    db_a: sqlite3.Connection, caplog: pytest.LogCaptureFixture
) -> None:
    wrong = Fetched(cast(Any, "text, not bytes"), None, None)
    (result,) = run_due(db_a, NOW, lambda u, e, m: wrong)
    assert result == (1, False, "unexpected error (TypeError); see the log")
    assert [r.levelname for r in caplog.records] == ["ERROR"]


def test_an_unsupported_encoding_reason_alone_never_disables_a_source(
    db_a: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    reason = "feed uses an unsupported text encoding (x)"

    def refuse(body: bytes) -> list[Entry]:
        raise FeedError(reason)

    monkeypatch.setattr(ingest, "parse_feed", refuse)
    for step in range(4):
        out = run_due(db_a, NOW + timedelta(hours=step), Recorded(b"x"))
        assert out == [(1, False, reason)]
    assert [(row["id"], row["state"]) for row in sources(db_a)] == [(1, "approved")]


# One bad entry does not lose the others (R29)
@pytest.mark.parametrize("bad", [BAD_TEXT, BAD_TIME], ids=["surrogate", "naive-time"])
def test_an_entry_the_store_refuses_is_skipped_and_counted_and_the_rest_are_stored(
    db_a: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch, bad: Entry
) -> None:
    _entries(monkeypatch, GOOD, bad, MORE)
    (result,) = run_due(db_a, NOW, Recorded(b"x"))
    assert result == (1, True, "2 new, 1 skipped")
    titles = [r["title"] for r in db_a.execute("SELECT title FROM stories ORDER BY id")]
    assert titles == [GOOD.title, MORE.title]
    check = last_check(db_a, 1)
    assert check is not None
    assert (check["ok"], check["new_stories"]) == (1, 2)


def test_a_skipped_entry_is_skipped_again_and_nothing_else_changes(
    db_a: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    _entries(monkeypatch, BAD_TEXT, GOOD)
    run_due(db_a, NOW, Recorded(b"x"))
    before = snapshot(db_a)
    assert run_due(db_a, NOW + timedelta(hours=1), Recorded(b"x")) == [
        (1, True, "0 new, 1 skipped")
    ]
    assert snapshot(db_a) == before


def test_a_store_unusable_error_from_adding_a_story_is_not_a_skip_and_is_not_recorded(
    db_a: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    _entries(monkeypatch, GOOD)

    def unusable(*args: object) -> str:
        raise StoreUnusable("not bad input")

    monkeypatch.setattr(ingest, "add_story", unusable)
    with pytest.raises(StoreUnusable):
        run_due(db_a, NOW, Recorded(b"x"))
    assert count(db_a, "source_checks") == 0


def test_a_pass_stopped_by_store_unusable_does_not_record_its_time(
    db_a: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    _entries(monkeypatch, GOOD)

    def opens_a_transaction(url: str, etag: str | None, modified: str | None) -> Fetched:
        db_a.execute("BEGIN")  # the entry's own write_transaction refuses to nest in it
        return Fetched(b"x", None, None)

    with pytest.raises(StoreUnusable):
        run_due(db_a, NOW, opens_a_transaction)
    db_a.execute("ROLLBACK")
    assert get_meta(db_a, "last_pass_at") is None


def test_a_store_error_from_the_post_is_not_a_skip_and_undoes_the_entry(
    db_a: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    group_with_topic(db_a)
    _entries(monkeypatch, GOOD, MORE)
    calls: list[int] = []

    def refuse(db: sqlite3.Connection, story_id: int, topics: list[int], now: object) -> list[int]:
        calls.append(story_id)
        if len(calls) == 2:
            raise StoreError("a programming error")
        return []

    monkeypatch.setattr(ingest, "auto_post", refuse)
    out = run_due(db_a, NOW, Recorded(b"x"))
    assert out == [(1, False, "unexpected error (StoreError); see the log")]
    assert count(db_a, "stories") == 1  # the first entry stays; the second is rolled back
    assert [r["title"] for r in db_a.execute("SELECT title FROM stories")] == [GOOD.title]


def _two_sources_with_a_failing_second_post(
    db: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch, failure: StoreError
) -> ingest.FetchFn:
    approve(db, "A", "https://a.org/f")
    approve(db, "B", "https://b.org/f")
    other = Entry("A story of the other source", "https://other.org/1", NOW, "")
    feeds_by_body = {b"A": [GOOD, MORE], b"B": [other]}
    monkeypatch.setattr(ingest, "parse_feed", lambda body: feeds_by_body[body])
    calls: list[int] = []

    def post(db: sqlite3.Connection, story_id: int, topics: list[int], now: object) -> list[int]:
        calls.append(story_id)
        if len(calls) == 2:
            raise failure
        return []

    monkeypatch.setattr(ingest, "auto_post", post)

    def fn(url: str, etag: str | None, modified: str | None) -> Fetched:
        return Fetched(b"A" if "a.org" in url else b"B", None, None)

    return fn


def test_a_store_error_from_the_post_fails_that_source_and_the_next_is_still_ingested(
    db: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    fn = _two_sources_with_a_failing_second_post(db, monkeypatch, StoreError("a programming error"))
    with caplog.at_level(logging.ERROR, logger=ingest.log.name):
        out = run_due(db, NOW, fn)
    assert out == [
        (1, False, "unexpected error (StoreError); see the log"),
        (2, True, "1 new"),
    ]
    titles = [r["title"] for r in db.execute("SELECT title FROM stories ORDER BY id")]
    assert titles == [GOOD.title, "A story of the other source"]  # the second entry is undone
    assert "unexpected error checking source 1" in caplog.text
    assert "a programming error" in caplog.text  # the traceback is logged
    assert health(db, 1, NOW).state == "failing"
    assert health(db, 2, NOW).state == "healthy"


def test_a_store_unusable_error_from_the_post_is_re_raised_and_not_recorded(
    db: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    fn = _two_sources_with_a_failing_second_post(db, monkeypatch, StoreUnusable("database gone"))
    with pytest.raises(StoreUnusable):
        run_due(db, NOW, fn)
    assert count(db, "source_checks") == 0
    assert count(db, "stories") == 1  # the entry before the failing one was committed on its own


# A reason the store cannot hold does not stop the pass (R57 Q4)
@pytest.mark.parametrize("lone", [chr(0xD800), chr(0xDFFF)], ids=["high", "low"])
def test_a_lone_surrogate_in_a_refusal_reason_is_replaced_and_the_pass_goes_on(
    db: sqlite3.Connection, lone: str
) -> None:
    approve(db, "A", "https://a.org/f")
    approve(db, "B", "https://b.org/f")

    def fn(url: str, etag: str | None, modified: str | None) -> Fetched:
        if "a.org" in url:
            raise FetchRefused(f"fetch failed: bad {lone} text")
        return Fetched(RSS, None, None)

    out = run_due(db, NOW, fn)
    assert out == [(1, False, "fetch failed: bad \ufffd text"), (2, True, "2 new")]
    check = last_check(db, 1)
    assert check is not None
    assert check["reason"] == "fetch failed: bad \ufffd text"


# One source at a time (R40)
def test_no_second_fetch_starts_before_the_first_source_is_stored(
    db: sqlite3.Connection,
) -> None:
    approve(db, "A", "https://a.org/f")
    approve(db, "B", "https://b.org/f")
    threads_before = threading.active_count()
    seen: list[tuple[str, int, bool, int]] = []

    def fn(url: str, etag: str | None, modified: str | None) -> Fetched:
        first = last_check(db, 1)
        seen.append((url, count(db, "stories"), first is not None, threading.active_count()))
        return Fetched(RSS, None, None)

    run_due(db, NOW, fn)
    assert [row[:3] for row in seen] == [
        ("https://a.org/f", 0, False),
        ("https://b.org/f", 2, True),
    ]
    assert {row[3] for row in seen} == {threads_before}
    assert threading.active_count() == threads_before


# A lookup refusal that comes from the process cap is not the source's fault (R40)
@pytest.mark.parametrize(
    "reason",
    [
        "too many lookups are still waiting for an answer",
        "could not start a lookup of the feed's host",
    ],
    ids=["too-many", "no-start"],
)
def test_a_lookup_cap_refusal_is_not_recorded_against_the_source_and_stops_the_pass(
    db: sqlite3.Connection, reason: str
) -> None:
    approve(db, "A", "https://a.org/f")
    approve(db, "B", "https://b.org/f")
    calls: list[str] = []
    refusals = Survivors(LookupCapRefused)

    def fn(url: str, etag: str | None, modified: str | None) -> Fetched:
        calls.append(url)
        raise LookupCapRefused(reason)

    assert run_due(db, NOW, fn) == [(1, False, reason)]
    assert calls == ["https://a.org/f"]
    assert count(db, "source_checks") == 0
    assert health(db, 1, NOW).state == "never checked"
    assert get_meta(db, "last_pass_at") == NOW.isoformat()
    assert refusals.new() == []
    again = Recorded(RSS)
    assert [r[:2] for r in run_due(db, NOW + timedelta(seconds=1), again)] == [(1, True), (2, True)]


def test_a_plain_refusal_with_a_cap_text_is_the_sources_failure(db: sqlite3.Connection) -> None:
    approve(db, "A", "https://a.org/f")
    approve(db, "B", "https://b.org/f")

    def fn(url: str, etag: str | None, modified: str | None) -> Fetched:
        raise FetchRefused("too many lookups are still waiting for an answer")

    assert [r[:2] for r in run_due(db, NOW, fn)] == [(1, False), (2, False)]
    assert count(db, "source_checks") == 2


def test_the_real_fetch_raises_the_type_ingest_stops_on(monkeypatch: pytest.MonkeyPatch) -> None:
    wait_for_all_lookup_slots()  # no earlier worker is left to release the semaphore patched next
    own = threading.BoundedSemaphore(fetch.MAX_LOOKUPS)  # not the shared one
    monkeypatch.setattr(fetch, "_LOOKUP_SLOTS", own)
    held = 0
    try:
        while own.acquire(blocking=False):
            held += 1
        assert held == 8
        with pytest.raises(LookupCapRefused):
            fetch.fetch("https://a.org/f", None, None, resolve=PUBLIC)
    finally:
        for _ in range(held):
            own.release()

    def no_start(self: threading.Thread) -> None:
        raise RuntimeError("cannot start")

    monkeypatch.setattr(threading.Thread, "start", no_start)
    with pytest.raises(LookupCapRefused):
        fetch.fetch("https://a.org/f", None, None, resolve=PUBLIC)


# What the pass does with fetch's answers (S-2b "For the ingest brief" items 5 and 6)
def _real_fetch(*replies: Reply) -> tuple[Wire, ingest.FetchFn]:
    wire = Wire(*replies)
    return wire, partial(fetch.fetch, resolve=PUBLIC, wiring=Wiring(wire))


def test_a_304_that_repeats_the_validators_sent_stores_them_and_sends_them_again(
    db_a: sqlite3.Connection,
) -> None:
    wire, fn = _real_fetch(
        Reply(200, RSS, {"ETag": '"e1"', "Last-Modified": "Fri, 13 Nov 2026 08:00:00 GMT"}),
        Reply(304, b"", {"ETag": '"e1"'}),
        Reply(304, b""),
    )
    assert run_due(db_a, NOW, fn) == [(1, True, "2 new")]
    assert run_due(db_a, NOW + timedelta(hours=1), fn) == [(1, True, "not modified")]
    sent = wire.requests[1][1]
    assert (sent["If-None-Match"], sent["If-Modified-Since"]) == (
        '"e1"',
        "Fri, 13 Nov 2026 08:00:00 GMT",
    )
    check = last_check(db_a, 1)
    assert check is not None
    assert (check["etag"], check["modified"]) == ('"e1"', "Fri, 13 Nov 2026 08:00:00 GMT")
    run_due(db_a, NOW + timedelta(hours=2), fn)
    assert wire.requests[2][1]["If-None-Match"] == '"e1"'


def test_a_redirected_feed_stores_no_validators(db_a: sqlite3.Connection) -> None:
    _wire, fn = _real_fetch(
        Reply(200, RSS, {"ETag": '"e1"'}),
        redirect("https://c.org/g"),
        Reply(200, RSS, {"ETag": '"other"'}),
    )
    run_due(db_a, NOW, fn)
    run_due(db_a, NOW + timedelta(hours=1), fn)
    check = last_check(db_a, 1)
    assert check is not None
    assert (check["ok"], check["etag"], check["modified"]) == (1, None, None)


def test_a_server_that_refuses_the_validator_is_a_failed_check_with_fetchs_reason(
    db_a: sqlite3.Connection,
) -> None:
    _wire, fn = _real_fetch(Reply(500, b""))
    assert run_due(db_a, NOW, fn) == [(1, False, "server answered HTTP 500")]


# Stories are keyed by fold.link_key; a feed's duplicates are not removed by the parser
def test_stories_are_matched_and_posted_by_link_key_not_by_raw_link(
    db_a: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    group = group_with_topic(db_a)
    shouty = Entry("Authority opens merger review today", "HTTPS://E.ORG/x#top", None, "")
    _entries(monkeypatch, shouty)
    assert run_due(db_a, NOW, Recorded(b"x")) == [(1, True, "1 new")]
    threads = db_a.execute("SELECT group_id, story_id FROM threads").fetchall()
    assert [tuple(r) for r in threads] == [(group, 1)]
    assert run_due(db_a, NOW + timedelta(hours=1), Recorded(b"x")) == [(1, True, "0 new")]


def test_the_same_link_twice_in_a_feed_is_one_story_and_one_post(
    db_a: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    group_with_topic(db_a)
    again = Entry("Another title for the merger review", "https://E.org/1#x", NOW, "other")
    _entries(monkeypatch, GOOD, again, GOOD)
    assert run_due(db_a, NOW, Recorded(b"x")) == [(1, True, "1 new")]
    assert (count(db_a, "stories"), count(db_a, "threads")) == (1, 1)


def test_an_entry_at_the_parser_limits_is_stored(db_a: sqlite3.Connection) -> None:
    link = "https://e.org/" + "a" * (2048 - len("https://e.org/"))
    title, summary = "t" * 500, "s" * 300
    body = (
        f"<rss version='2.0'><channel><item><title>{title}</title><link>{link}</link>"
        f"<description>{summary}</description><pubDate>{'x' * 300}</pubDate></item>"
        "</channel></rss>"
    ).encode()
    assert run_due(db_a, NOW, Recorded(body)) == [(1, True, "1 new")]
    row = db_a.execute("SELECT title, link, summary, published_at FROM stories").fetchone()
    assert (len(row["title"]), len(row["link"]), len(row["summary"])) == (500, 2048, 300)
    assert row["published_at"] == NOW.isoformat()  # a date over 256 characters is None


# Automatic posts and re-runs
def test_an_automatic_post_lands_only_in_groups_carrying_the_stories_topic(
    db_a: sqlite3.Connection,
) -> None:
    ak = User("ak", "writer")
    group_with_topic(db_a)  # G1 carries "merger review"
    other = add_topic(db_a, "Rates", ["interest rates"], [], "ak")
    both = add_topic(db_a, "Both", ["review"], [], "ak")
    create_group(db_a, Act(ak, NOW), "G2", "everyone", [other])
    g3 = create_group(db_a, Act(ak, NOW), "G3", "everyone", [both])
    create_group(db_a, Act(ak, NOW), "G4", "everyone", [])
    run_due(db_a, NOW, Recorded(MERGER))
    rows = db_a.execute("SELECT group_id, story_id, started_by FROM threads ORDER BY id").fetchall()
    # Story 1 ("Authority opens merger review") matches both topics; "No date" matches none.
    assert [tuple(r) for r in rows] == [(1, 1, None), (g3, 1, None)]
    assert [
        r["name"] for r in db_a.execute("SELECT name FROM groups WHERE id IN (1, ?)", (g3,))
    ] == [
        "G1",
        "G3",
    ]


def test_a_rerun_of_the_same_feed_adds_nothing(db_a: sqlite3.Connection) -> None:
    group_with_topic(db_a)
    first_pass = run_due(db_a, NOW, Recorded(MERGER))
    before = snapshot(db_a)
    assert [r[1:] for r in first_pass] == [(True, "2 new")]
    assert before["threads"]
    again = run_due(db_a, NOW + timedelta(hours=1), Recorded(MERGER))
    assert [r[1:] for r in again] == [(True, "0 new")]
    assert snapshot(db_a) == before


# Wrong types are StoreError (R15)
@pytest.mark.parametrize(
    "now", [NOW.replace(tzinfo=None), "2026-11-13", None], ids=["naive", "str", "none"]
)
def test_a_time_that_is_not_an_aware_datetime_is_a_store_error_before_any_fetch(
    db_a: sqlite3.Connection, now: Any
) -> None:
    fn = Recorded(RSS)
    with pytest.raises(StoreError):
        run_due(db_a, now, fn)
    with pytest.raises(StoreError):
        health(db_a, 1, now)
    assert fn.calls == []
    assert get_meta(db_a, "last_pass_at") is None


def test_a_source_id_outside_sqlites_range_is_a_store_error(db_a: sqlite3.Connection) -> None:
    with pytest.raises(StoreError):
        health(db_a, 2**63, NOW)


@pytest.mark.parametrize(
    "source_id",
    ["1", None, 1.0, 1.5, True, b"1"],
    ids=["str", "none", "1.0", "1.5", "bool", "bytes"],
)
def test_a_source_id_that_is_not_an_exact_int_is_a_store_error(
    db_a: sqlite3.Connection, source_id: Any
) -> None:
    with pytest.raises(StoreError):
        health(db_a, source_id, NOW)


# Near year 1 a subtraction overflows: a StoreError, not an OverflowError (R58 Q1, L2)
YEAR_ONE = datetime(1, 1, 1, 0, 5, tzinfo=UTC)


def test_an_aware_time_near_year_one_is_a_store_error_for_a_pass(db_a: sqlite3.Connection) -> None:
    run_due(db_a, NOW, Recorded(RSS))  # the interval is subtracted whether or not a check exists
    fn = Recorded(RSS)
    with pytest.raises(StoreError):
        run_due(db_a, YEAR_ONE, fn)
    assert fn.calls == []


def test_a_time_near_year_one_is_refused_before_any_check_exists(db_a: sqlite3.Connection) -> None:
    fn = Recorded(RSS)  # sweep b5: the interval is subtracted up front, not once a check exists
    with pytest.raises(StoreError):
        run_due(db_a, YEAR_ONE, fn)
    assert fn.calls == []
    assert count(db_a, "source_checks") == 0


def test_health_of_a_never_checked_source_refuses_a_time_near_year_one(
    db_a: sqlite3.Connection,
) -> None:
    with pytest.raises(StoreError):
        health(db_a, 1, YEAR_ONE)


def test_an_aware_time_near_year_one_is_a_store_error_for_health(
    db_a: sqlite3.Connection,
) -> None:
    run_due(db_a, NOW, Recorded(RSS))
    with pytest.raises(StoreError):
        health(db_a, 1, YEAR_ONE)


# R58 L3: a 304 whose validator differs from the one sent does not replace the stored one
_LM1 = "Fri, 13 Nov 2026 08:00:00 GMT"
_LM2 = "Fri, 13 Nov 2026 09:00:00 GMT"


def _stored_after_304(
    db: sqlite3.Connection, first: dict[str, str], second: dict[str, str]
) -> tuple[Wire, tuple[str | None, str | None]]:
    """A 200 with the validators `first`, then a 304 with `second`: what the second check stored."""
    wire, fn = _real_fetch(Reply(200, RSS, first), Reply(304, b"", second), Reply(304, b""))
    run_due(db, NOW, fn)
    assert run_due(db, NOW + timedelta(hours=1), fn) == [(1, True, "not modified")]
    check = last_check(db, 1)
    assert check is not None
    return wire, (check["etag"], check["modified"])


def test_a_304_with_another_etag_keeps_the_stored_one(db_a: sqlite3.Connection) -> None:
    wire, stored = _stored_after_304(db_a, {"ETag": '"e1"'}, {"ETag": '"e2"'})
    assert stored == ('"e1"', None)
    run_due(
        db_a, NOW + timedelta(hours=2), partial(fetch.fetch, resolve=PUBLIC, wiring=Wiring(wire))
    )
    assert wire.requests[2][1]["If-None-Match"] == '"e1"'


def test_a_304_with_another_last_modified_keeps_the_stored_one(db_a: sqlite3.Connection) -> None:
    _wire, stored = _stored_after_304(db_a, {"Last-Modified": _LM1}, {"Last-Modified": _LM2})
    assert stored == (None, _LM1)


def test_a_304_with_the_same_validators_stores_them(db_a: sqlite3.Connection) -> None:
    both = {"ETag": '"e1"', "Last-Modified": _LM1}
    _wire, stored = _stored_after_304(db_a, both, both)
    assert stored == ('"e1"', _LM1)


def test_a_304_keeps_each_validator_on_its_own_terms(db_a: sqlite3.Connection) -> None:
    first = {"ETag": '"e1"', "Last-Modified": _LM1}
    _wire, stored = _stored_after_304(db_a, first, {"ETag": '"e2"', "Last-Modified": _LM1})
    assert stored == ('"e1"', _LM1)


def test_a_304_stores_a_validator_for_a_field_with_none_stored(db_a: sqlite3.Connection) -> None:
    _wire, stored = _stored_after_304(db_a, {"ETag": '"e1"'}, {"Last-Modified": _LM2})
    assert stored == ('"e1"', _LM2)


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        pytest.param({}, (None, _LM1), id="none-returned-clears-it"),
        pytest.param({"ETag": '"new"'}, ('"new"', _LM1), id="none-was-sent-so-new-is-stored"),
    ],
)
def test_a_stored_etag_fetch_dropped_as_unclean_is_cleared_or_replaced(
    db_a: sqlite3.Connection, answer: dict[str, str], expected: tuple[str | None, str | None]
) -> None:
    record_check(db_a, 1, Check(NOW, True, "1 new", "bad\x01tag", _LM1, 1))
    _wire, fn = _real_fetch(Reply(304, b"", answer))
    assert run_due(db_a, NOW + timedelta(hours=1), fn) == [(1, True, "not modified")]
    check = last_check(db_a, 1)
    assert check is not None
    assert (check["etag"], check["modified"]) == expected


# R58 Q2: what the surviving mutants of the first review changed, one test each
def test_a_200_with_an_empty_body_is_a_failed_check_not_a_not_modified(
    db_a: sqlite3.Connection,
) -> None:
    run_due(db_a, NOW, Recorded(RSS, etag='"v1"'))
    (result,) = run_due(db_a, NOW + timedelta(hours=1), Recorded(b""))
    assert result == (1, False, "feed is not valid XML")


def test_a_fetch_refusal_keeps_both_stored_validators(db_a: sqlite3.Connection) -> None:
    run_due(db_a, NOW, lambda u, e, m: Fetched(RSS, '"v1"', _LM1))

    def refused(url: str, etag: str | None, modified: str | None) -> Fetched:
        raise FetchRefused("server answered HTTP 500")

    assert run_due(db_a, NOW + timedelta(hours=1), refused) == [
        (1, False, "server answered HTTP 500")
    ]
    check = last_check(db_a, 1)
    assert check is not None
    assert (check["ok"], check["etag"], check["modified"]) == (0, '"v1"', _LM1)


def test_an_unexpected_error_keeps_both_stored_validators(db_a: sqlite3.Connection) -> None:
    run_due(db_a, NOW, lambda u, e, m: Fetched(RSS, '"v1"', _LM1))

    def broken(url: str, etag: str | None, modified: str | None) -> Fetched:
        raise ZeroDivisionError("boom")

    out = run_due(db_a, NOW + timedelta(hours=1), broken)
    assert out == [(1, False, "unexpected error (ZeroDivisionError); see the log")]
    check = last_check(db_a, 1)
    assert check is not None
    assert (check["etag"], check["modified"]) == ('"v1"', _LM1)


def test_a_plain_value_error_from_the_parser_is_an_unexpected_error_not_a_refused_feed(
    db_a: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    def parse(body: bytes) -> list[Entry]:
        raise ValueError("a parser bug")

    monkeypatch.setattr(ingest, "parse_feed", parse)
    out = run_due(db_a, NOW, Recorded(RSS))
    assert out == [(1, False, "unexpected error (ValueError); see the log")]


def test_a_plain_value_error_from_fetch_is_an_unexpected_error_not_a_refusal(
    db_a: sqlite3.Connection,
) -> None:
    def fn(url: str, etag: str | None, modified: str | None) -> Fetched:
        raise ValueError("a fetch bug")

    assert run_due(db_a, NOW, fn) == [(1, False, "unexpected error (ValueError); see the log")]


# R58 Q4: the health boundaries, by literals (42 days, 7 days)
def test_a_story_exactly_42_days_old_is_in_no_week() -> None:
    assert ingest._per_week([NOW - timedelta(days=42)], NOW) == (0, 0, 0, 0, 0, 0)
    just_inside = NOW - timedelta(days=41, hours=23, minutes=59, seconds=59)
    assert ingest._per_week([just_inside], NOW) == (1, 0, 0, 0, 0, 0)


@pytest.mark.parametrize(
    ("age", "state"),
    [
        pytest.param(timedelta(days=7), "healthy", id="exactly-7-days"),
        pytest.param(timedelta(days=7, seconds=1), "quiet", id="7-days-and-a-second"),
    ],
)
def test_a_source_is_quiet_only_when_its_last_story_is_older_than_7_days(
    db_a: sqlite3.Connection, age: timedelta, state: str
) -> None:
    story = Entry("A story about the central bank", "https://a.org/1", NOW - age, "")
    with write_transaction(db_a):
        add_story(db_a, 1, story, NOW)
    record_check(db_a, 1, Check(NOW, True, "1 new", None, None, 1))
    assert health(db_a, 1, NOW).state == state
