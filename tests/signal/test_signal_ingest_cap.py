"""S-11: a source adds at most MAX_NEW_PER_PASS new stories a pass; the rest is counted and left
for the next pass (R70 item 4). Feeds are built in memory; nothing opens a connection. Expected
values are literals."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from ingest_support import NOW, Recorded, approve, count

from credit_os.signal import ingest
from credit_os.signal.feeds import Entry
from credit_os.signal.fetch import Fetched
from credit_os.signal.ingest import run_due
from credit_os.signal.store import Check, last_check, open_db, record_check

CAP = 3
LEFT = "over the cap, left for the next pass"
BAD = Entry("lone surrogate \ud800 in a title", "https://e.org/bad", NOW, "")


def _story(n: int) -> Entry:
    return Entry(f"Story number {n} about a merger review", f"https://e.org/{n}", NOW, "")


class Answering:
    """Stands for `fetch.fetch`: answers one body with a fixed validator pair; records the calls."""

    def __init__(self, etag: str | None, modified: str | None) -> None:
        self.etag, self.modified = etag, modified
        self.calls: list[tuple[str, str | None, str | None]] = []

    def __call__(self, url: str, etag: str | None, modified: str | None) -> Fetched:
        self.calls.append((url, etag, modified))
        return Fetched(b"x", self.etag, self.modified)


@pytest.fixture
def db(tmp_path: Path) -> sqlite3.Connection:
    conn = open_db(tmp_path)
    approve(conn, "A", "https://a.org/f")
    return conn


@pytest.fixture(autouse=True)
def cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ingest, "MAX_NEW_PER_PASS", CAP)


def _feed(monkeypatch: pytest.MonkeyPatch, *entries: Entry) -> None:
    monkeypatch.setattr(ingest, "parse_feed", lambda body: list(entries))


def _links(db: sqlite3.Connection) -> list[str]:
    return [r["link"] for r in db.execute("SELECT link FROM stories ORDER BY id")]


def _hour(n: int) -> datetime:
    return NOW + timedelta(hours=n)


def test_the_constant_is_2000_and_the_real_cap_stops_a_2005_entry_feed_at_2000(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.undo()  # the real constant, not the patched one
    assert ingest.MAX_NEW_PER_PASS == 2000
    db = open_db(tmp_path)
    approve(db, "A", "https://a.org/f")
    items = "".join(
        f"<item><title>Story number {n} about a merger review</title>"
        f"<link>https://e.org/{n}</link></item>"
        for n in range(2005)
    )
    body = (
        f'<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>{items}</channel></rss>'
    )
    fn = Recorded(body.encode())
    assert run_due(db, NOW, fn) == [(1, True, "2000 new, 5 over the cap, left for the next pass")]
    assert count(db, "stories") == 2000
    check = last_check(db, 1)
    assert check is not None
    assert (check["new_stories"], check["etag"]) == (2000, None)
    assert "https://e.org/1999" in _links(db)
    assert "https://e.org/2000" not in _links(db)


def test_a_feed_over_the_cap_stores_the_cap_and_counts_the_rest(
    db: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    _feed(monkeypatch, *[_story(n) for n in range(CAP + 5)])
    assert run_due(db, NOW, Answering('"v1"', "M1")) == [(1, True, f"3 new, 5 {LEFT}")]
    assert _links(db) == ["https://e.org/0", "https://e.org/1", "https://e.org/2"]
    check = last_check(db, 1)
    assert check is not None
    assert (check["ok"], check["new_stories"], check["reason"]) == (1, 3, f"3 new, 5 {LEFT}")
    assert count(db, "source_checks") == 1


def test_at_the_cap_the_validators_sent_are_stored_none_case(
    db: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    _feed(monkeypatch, *[_story(n) for n in range(CAP + 1)])
    fn = Answering('"answer"', "ANSWER")
    run_due(db, NOW, fn)
    assert fn.calls == [("https://a.org/f", None, None)]
    check = last_check(db, 1)
    assert check is not None
    assert (check["etag"], check["modified"]) == (None, None)


def test_at_the_cap_the_validators_sent_are_stored_stored_pair(
    db: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    record_check(db, 1, Check(NOW - timedelta(hours=1), True, "0 new", '"old"', "OLD-DATE", 0))
    _feed(monkeypatch, *[_story(n) for n in range(CAP + 1)])
    fn = Answering('"answer"', "ANSWER")
    run_due(db, NOW, fn)
    assert fn.calls == [("https://a.org/f", '"old"', "OLD-DATE")]
    check = last_check(db, 1)
    assert check is not None
    assert (check["etag"], check["modified"], check["new_stories"]) == ('"old"', "OLD-DATE", 3)


def test_exactly_the_cap_has_no_cap_clause_and_stores_the_answers_validators(
    db: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    record_check(db, 1, Check(NOW - timedelta(hours=1), True, "0 new", '"old"', "OLD-DATE", 0))
    _feed(monkeypatch, *[_story(n) for n in range(CAP)])
    assert run_due(db, NOW, Answering('"answer"', "ANSWER")) == [(1, True, "3 new")]
    check = last_check(db, 1)
    assert check is not None
    assert (check["etag"], check["modified"]) == ('"answer"', "ANSWER")
    assert count(db, "stories") == 3


def test_the_next_passes_store_the_rest_then_say_zero_new(
    db: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    _feed(monkeypatch, *[_story(n) for n in range(CAP + 2)])
    fn = Answering('"v1"', None)
    assert run_due(db, NOW, fn) == [(1, True, f"3 new, 2 {LEFT}")]
    assert run_due(db, _hour(1), fn) == [(1, True, "2 new")]
    assert run_due(db, _hour(2), fn) == [(1, True, "0 new")]
    assert len(_links(db)) == 5
    assert fn.calls[1][1] is None  # the second pass was not a conditional request
    assert fn.calls[2][1] == '"v1"'  # the first uncapped answer's validators are kept


def test_each_pass_makes_progress_old_entries_first_then_the_next_cap(
    db: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    _feed(monkeypatch, *[_story(n) for n in range(2 * CAP + 2)])
    fn = Answering(None, None)
    assert run_due(db, NOW, fn) == [(1, True, f"3 new, 5 {LEFT}")]
    assert run_due(db, _hour(1), fn) == [(1, True, f"3 new, 2 {LEFT}")]
    assert run_due(db, _hour(2), fn) == [(1, True, "2 new")]
    assert run_due(db, _hour(3), fn) == [(1, True, "0 new")]
    assert len(_links(db)) == 8


def test_old_and_skipped_entries_before_the_cap_do_not_count_toward_it(
    db: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    _feed(monkeypatch, _story(0), _story(1))
    run_due(db, NOW, Answering(None, None))
    _feed(monkeypatch, _story(0), BAD, _story(1), *[_story(n) for n in range(2, 7)])
    assert run_due(db, _hour(1), Answering(None, None)) == [
        (1, True, f"3 new, 1 skipped, 2 {LEFT}")
    ]
    assert _links(db) == [f"https://e.org/{n}" for n in range(5)]
    check = last_check(db, 1)
    assert check is not None
    assert check["new_stories"] == 3


def test_a_feed_of_old_and_skipped_entries_only_never_meets_the_cap(
    db: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    _feed(monkeypatch, *[_story(n) for n in range(CAP)])
    run_due(db, NOW, Answering(None, None))
    _feed(monkeypatch, *[_story(n) for n in range(CAP)], *[BAD] * 5)
    fn = Answering('"v2"', None)
    assert run_due(db, _hour(1), fn) == [(1, True, "0 new, 5 skipped")]
    check = last_check(db, 1)
    assert check is not None
    assert check["etag"] == '"v2"'
