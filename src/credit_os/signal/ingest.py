"""One ingest pass over the approved sources that are due, and a health summary per source.

A pass handles one source at a time (R40): the parser's worst case is tens of MiB a parse and
the process has eight lookup slots. It starts no thread of its own and no process and makes no
model call; `fetch` starts one daemon lookup thread per hop, and one that overruns outlives its
source, holding a lookup slot until it returns.
Nothing here changes a source's state: a failing source stays approved and is tried again when
it is next due."""

import logging
import re
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from credit_os.signal import fetch
from credit_os.signal.feeds import Entry, FeedError, parse_feed
from credit_os.signal.fetch import Fetched, FetchRefused, LookupCapRefused
from credit_os.signal.fold import link_key
from credit_os.signal.groups import require_stamp
from credit_os.signal.store import (
    Check,
    StoreError,
    StoreUnusable,
    add_story,
    last_check,
    record_check,
    require_id,
    set_meta,
    sources,
    utc_text,
    write_transaction,
)
from credit_os.signal.threads import auto_post
from credit_os.signal.topics import match_story

log = logging.getLogger(__name__)

MIN_INTERVAL = timedelta(seconds=600)
QUIET_AFTER = timedelta(days=7)
HEALTH_WEEKS = 6
MAX_NEW_PER_PASS = 2000
_WEEK = timedelta(days=7)

FetchFn = Callable[[str, str | None, str | None], Fetched]

_SURROGATE = re.compile("[\ud800-\udfff]")  # not storable: record_check would raise (R57 Q4)


@dataclass(frozen=True)
class _Refused:
    """Why a fetch or a parse was refused: the text only, never the exception (R40, R10).

    `lookup_cap` marks `fetch`'s process-wide cap on lookups, which is not the source's fault."""

    reason: str
    lookup_cap: bool = False


def _refused(error: Exception, lookup_cap: bool = False) -> _Refused:
    return _Refused(_SURROGATE.sub("\ufffd", str(error)), lookup_cap)


def _back(now: datetime, span: timedelta) -> datetime:
    """`now` less `span`; a time too close to year 1 for that is a StoreError (R15)."""
    try:
        return now - span
    except OverflowError as error:
        raise StoreError("time is too early to compare") from error


def _is_due(db: sqlite3.Connection, source_id: int, due_before: datetime) -> bool:
    previous = last_check(db, source_id)
    return previous is None or datetime.fromisoformat(previous["at"]) <= due_before


def _fetch(
    fetch_fn: FetchFn, url: str, etag: str | None, modified: str | None
) -> Fetched | _Refused:
    try:
        return fetch_fn(url, etag, modified)
    except LookupCapRefused as error:  # before FetchRefused: it is one
        refused = _refused(error, lookup_cap=True)
    except FetchRefused as error:
        refused = _refused(error)
    return refused  # the exception, which can hold about 8 MiB, ends with the clause


def _kept(stored: str | None, returned: str | None) -> str | None:
    """The validator to store after a 304 (R58 L3): the one sent, else the answer's (RFC 9111
    4.3.4). A stored value that `fetch` dropped as unclean was not sent, so it is cleared or
    replaced by the answer's."""
    sent = fetch.stored(stored)
    return returned if sent is None else sent


def _parse(body: bytes) -> list[Entry] | _Refused:
    try:
        return parse_feed(body)
    except FeedError as error:  # before any ValueError: a FeedError is one
        refused = _refused(error)  # at most 120 characters of the feed's text (R10)
    # Not kept, not logged with its traceback or chain: they hold tens of MiB and uncut feed text.
    return refused


def _store_entry(
    db: sqlite3.Connection, source_id: int, entry: Entry, now: datetime
) -> Literal["new", "old", "skipped"]:
    """Store one entry, match it to topics and post it, all in one transaction (R41).

    An entry the store refuses is "skipped" (R29): `add_story` refuses before its first write,
    so nothing of it is pending. A `StoreError` from the match or the post is a programming
    error, not feed data: it is not caught here, and the entry's writes are rolled back."""
    with write_transaction(db):
        try:
            outcome = add_story(db, source_id, entry, now)
        except StoreUnusable:
            raise
        except StoreError:
            return "skipped"
        if outcome != "new":
            return "old"
        story = db.execute(
            "SELECT id FROM stories WHERE source_id=? AND link_key=?",
            (source_id, link_key(entry.link)),
        ).fetchone()
        auto_post(db, story["id"], match_story(db, story["id"]), now)
        return "new"


def _check_source(
    db: sqlite3.Connection, source: sqlite3.Row, now: datetime, fetch_fn: FetchFn
) -> Check | _Refused:
    """The outcome of fetching and storing one source; a `_Refused` is a lookup-cap refusal."""
    previous = last_check(db, source["id"])
    etag = previous["etag"] if previous else None
    modified = previous["modified"] if previous else None
    fetched = _fetch(fetch_fn, source["url"], etag, modified)
    if isinstance(fetched, _Refused):
        if fetched.lookup_cap:
            return fetched
        return Check(now, False, fetched.reason, etag, modified, 0)
    if fetched.body is None:  # a 304: fetch has merged the validator it sent with the answer's
        kept = (_kept(etag, fetched.etag), _kept(modified, fetched.modified))
        return Check(now, True, "not modified", *kept, 0)
    entries = _parse(fetched.body)
    if isinstance(entries, _Refused):  # refused as a whole: no entry of the feed is stored
        return Check(now, False, entries.reason, etag, modified, 0)
    counts = {"new": 0, "old": 0, "skipped": 0}
    over = 0
    for position, entry in enumerate(entries):
        if counts["new"] >= MAX_NEW_PER_PASS:  # the rest is left unexamined for the next pass
            over = len(entries) - position
            break
        counts[_store_entry(db, source["id"], entry, now)] += 1
    note = f"{counts['new']} new"
    if counts["skipped"]:
        note += f", {counts['skipped']} skipped"
    if over:
        # The answer's validators are not stored: the next pass must fetch the feed again, not
        # get a 304 for entries this pass did not read (R70 item 4).
        note += f", {over} over the cap, left for the next pass"
        return Check(now, True, note, etag, modified, counts["new"])
    return Check(now, True, note, fetched.etag, fetched.modified, counts["new"])


def _unexpected(db: sqlite3.Connection, source_id: int, now: datetime, error: Exception) -> Check:
    previous = last_check(db, source_id)
    return Check(
        now,
        False,
        f"unexpected error ({type(error).__name__}); see the log",
        previous["etag"] if previous else None,
        previous["modified"] if previous else None,
        0,
    )


def run_due(
    db: sqlite3.Connection, now: datetime, fetch_fn: FetchFn | None = None
) -> list[tuple[int, bool, str]]:
    """Check every approved source with no check in the last MIN_INTERVAL, one at a time.

    A refused fetch or an unreadable feed is recorded as a failed check with its own reason.
    A refusal by `fetch`'s lookup cap is not the source's fault (R40): no check is recorded, the
    source stays due, its reason is returned in the results and the pass stops there.
    Any other Exception is logged with its traceback and recorded as a failed check whose
    reason names only the exception type (the text may hold internal detail), keeping the
    previous etag and modified; the pass goes on to the later sources. This is a documented,
    logged fail-open so one bad source cannot starve the rest. A `StoreError` from the match or
    the post is one of these: that entry's transaction is rolled back, earlier entries stay.
    `StoreUnusable` and BaseException are not caught.
    A `now` that is not timezone-aware, or within MIN_INTERVAL of year 1, is a StoreError.
    The pass's time is stored when it ends (`last_pass_at`)."""
    require_stamp(now)
    due_before = _back(now, MIN_INTERVAL)
    run_fetch = fetch_fn if fetch_fn is not None else fetch.fetch
    results: list[tuple[int, bool, str]] = []
    for source in sources(db, "approved"):
        if not _is_due(db, source["id"], due_before):
            continue
        try:
            check = _check_source(db, source, now, run_fetch)
        except StoreUnusable:
            raise  # the store cannot be used: no source is to blame, nothing is recorded
        except Exception as error:
            log.exception("unexpected error checking source %s", source["id"])
            check = _unexpected(db, source["id"], now, error)
        if isinstance(check, _Refused):
            results.append((source["id"], False, check.reason))
            break
        record_check(db, source["id"], check)
        results.append((source["id"], check.ok, check.reason))
    set_meta(db, "last_pass_at", utc_text(now))
    return results


@dataclass(frozen=True)
class Health:
    """One source's state: "never checked" (no check row), "failing" (its last check was not ok),
    "quiet" (ok, but no story published in the last QUIET_AFTER) or "healthy"."""

    state: Literal["healthy", "quiet", "failing", "never checked"]
    last_check: datetime | None
    last_item: datetime | None
    per_week: tuple[int, ...]
    reason: str


def _per_week(published: list[datetime], now: datetime) -> tuple[int, ...]:
    """Counts per 7-day window ending at `now`, oldest first; a window is (start, end]."""
    counts = [0] * HEALTH_WEEKS
    for at in published:
        age = now - at
        if timedelta(0) <= age < HEALTH_WEEKS * _WEEK:
            counts[HEALTH_WEEKS - 1 - age // _WEEK] += 1
    return tuple(counts)


def health(db: sqlite3.Connection, source_id: int, now: datetime) -> Health:
    """The state of one source at `now`, with its stories per week (HEALTH_WEEKS windows). An id
    that is not an exact int, or a `now` that is not aware or is near year 1, is a StoreError."""
    if type(source_id) is not int:
        raise StoreError("source id must be an integer")
    require_id(source_id, "source")
    require_stamp(now)
    quiet_before = _back(now, QUIET_AFTER)
    rows = db.execute(
        "SELECT published_at FROM stories WHERE source_id=?"
        " UNION ALL SELECT published_at FROM story_duplicates WHERE duplicate_source_id=?",
        (source_id, source_id),
    ).fetchall()
    published = [datetime.fromisoformat(row["published_at"]) for row in rows]
    last_item = max(published, default=None)
    previous = last_check(db, source_id)
    if previous is None:
        return Health("never checked", None, last_item, _per_week(published, now), "")
    checked = datetime.fromisoformat(previous["at"])
    state: Literal["healthy", "quiet", "failing"]
    if not previous["ok"]:
        state = "failing"
    elif last_item is None or last_item < quiet_before:
        state = "quiet"
    else:
        state = "healthy"
    return Health(state, checked, last_item, _per_week(published, now), previous["reason"])
