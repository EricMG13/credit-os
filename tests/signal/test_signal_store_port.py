from __future__ import annotations

import hashlib
import sqlite3
import stat
import sys
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from credit_os.signal import store
from credit_os.signal.feeds import Entry
from credit_os.signal.store import (
    MIGRATIONS,
    Check,
    StoreError,
    StoreUnusable,
    _enable_wal,
    add_story,
    add_user,
    get_meta,
    in_range,
    last_check,
    new_row_id,
    open_db,
    propose_source,
    record_check,
    require_id,
    require_text,
    role_of,
    set_meta,
    set_source_state,
    sources,
    utc_text,
    write_transaction,
)


@pytest.fixture
def opened(monkeypatch: pytest.MonkeyPatch) -> list[sqlite3.Connection]:
    """Every connection `open_db` makes, so a test can check what became of it. The real
    `sqlite3.connect` still runs."""
    made: list[sqlite3.Connection] = []
    real = sqlite3.connect

    def connect(database: Path, timeout: float) -> sqlite3.Connection:
        db = real(database, timeout=timeout)
        made.append(db)
        return db

    monkeypatch.setattr(sqlite3, "connect", connect)
    return made


# SHA-256 of each predecessor migration script (aebec97), so a database made by one side opens
# on the other and the scripts stay byte-identical.
_MIGRATION_SHA256 = (
    "5ec24ec87588cbcf7db5fac5fdec353455d2a78a5b4edc1d995f481cd8588331",
    "30d2f48e01ca1287e46008d9d8ec1792fa121e81d197a91f4a11c089f49abb7e",
    "bff3a2f1e52dc19fda7bb47ead29b424a97d1b58b26cbea77c97ced93e93b65f",
)


def test_migration_scripts_are_byte_identical_to_the_predecessors() -> None:
    assert tuple(hashlib.sha256(m.encode()).hexdigest() for m in MIGRATIONS) == _MIGRATION_SHA256


def test_every_table_index_and_trigger_exists_after_open(tmp_path: Path) -> None:
    db = open_db(tmp_path)
    rows = db.execute("SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")
    got = {(r["type"], r["name"]) for r in rows}
    tables = [
        "users",
        "sources",
        "source_checks",
        "stories",
        "story_duplicates",
        "stories_fts",
        "topics",
        "topic_stories",
        "topic_follows",
        "saves",
        "groups",
        "group_members",
        "group_topics",
        "threads",
        "comments",
        "reactions",
        "read_marks",
        "meta",
    ]
    triggers = ["stories_ai", "stories_ad", "stories_au"]
    indexes = [
        "idx_story_duplicates_link_key",
        "idx_story_duplicates_story_id",
        "idx_stories_published_at_id",
        "idx_topic_stories_story_id",
        "idx_stories_link_key",
        "idx_stories_title_key",
        "idx_threads_group_activity",
        "idx_threads_story_id",
        "idx_comments_thread_id",
        "idx_comments_parent_id",
        "idx_group_members_user",
    ]
    expected = (
        {("table", n) for n in tables}
        | {("trigger", n) for n in triggers}
        | {("index", n) for n in indexes}
    )
    assert expected <= got


def test_pragmas_and_busy_timeout(tmp_path: Path) -> None:
    db = open_db(tmp_path)
    assert db.execute("PRAGMA secure_delete").fetchone()[0] == 1
    assert db.execute("PRAGMA busy_timeout").fetchone()[0] == 30_000
    assert db.autocommit == sqlite3.LEGACY_TRANSACTION_CONTROL


@pytest.mark.parametrize("version", ["4", "99"])
def test_a_database_with_a_newer_schema_is_refused_untouched_and_closed(
    tmp_path: Path, opened: list[sqlite3.Connection], version: str
) -> None:
    db = open_db(tmp_path)
    add_user(db, "A", "owner")
    db.execute("UPDATE meta SET value=? WHERE key='schema_version'", (version,))
    db.commit()
    db.close()
    path = tmp_path / "signal" / "signal.db"
    before = path.read_bytes()
    opened.clear()
    with pytest.raises(StoreUnusable, match="newer"):
        open_db(tmp_path)
    assert path.read_bytes() == before
    assert len(opened) == 1
    with pytest.raises(sqlite3.ProgrammingError):
        opened[0].execute("SELECT 1")


def test_meta_round_trip_and_missing_key(tmp_path: Path) -> None:
    db = open_db(tmp_path)
    assert get_meta(db, "k") is None
    set_meta(db, "k", "v")
    set_meta(db, "k", "w")
    assert get_meta(db, "k") == "w"


def test_in_range_is_the_sqlite_integer_range() -> None:
    assert in_range(2**63 - 1) and in_range(-(2**63))
    assert not in_range(2**63) and not in_range(-(2**63) - 1)


def test_utc_text_converts_and_refuses_a_naive_time() -> None:
    at = datetime(2026, 11, 13, 10, 0, tzinfo=timezone(timedelta(hours=1)))
    assert utc_text(at) == "2026-11-13T09:00:00+00:00"
    with pytest.raises(StoreError):
        utc_text(datetime(2026, 11, 13, 10, 0, tzinfo=UTC).replace(tzinfo=None))


def _count(db: sqlite3.Connection) -> int:
    return int(db.execute("SELECT count(*) FROM users").fetchone()[0])


def _insert(db: sqlite3.Connection, name: str) -> None:
    db.execute("INSERT INTO users(name, role) VALUES(?, 'reader')", (name,))


def test_outer_block_commits_and_a_second_connection_sees_it_only_then(tmp_path: Path) -> None:
    db = open_db(tmp_path)
    other = open_db(tmp_path)
    with write_transaction(db):
        _insert(db, "outer")
        with write_transaction(db):
            _insert(db, "inner")
        assert db.in_transaction  # the inner block did not commit
        assert _count(other) == 0
    assert not db.in_transaction
    assert _count(other) == 2


def test_inner_exception_caught_inside_the_outer_block_leaves_writes_pending(
    tmp_path: Path,
) -> None:
    db = open_db(tmp_path)
    other = open_db(tmp_path)
    with write_transaction(db):
        try:
            with write_transaction(db):
                _insert(db, "inner")
                raise ValueError("caught by the caller")
        except ValueError:
            pass
        assert db.in_transaction
        assert _count(other) == 0
    assert _count(other) == 1


def test_outer_exception_rolls_back_the_inner_writes(tmp_path: Path) -> None:
    db = open_db(tmp_path)
    with pytest.raises(ValueError, match="boom"), write_transaction(db):
        _insert(db, "outer")
        with write_transaction(db):
            _insert(db, "inner")
        raise ValueError("boom")
    assert not db.in_transaction
    assert _count(db) == 0


def test_a_base_exception_also_rolls_back(tmp_path: Path) -> None:
    db = open_db(tmp_path)
    with pytest.raises(KeyboardInterrupt), write_transaction(db):
        _insert(db, "x")
        raise KeyboardInterrupt
    assert _count(db) == 0


def test_the_write_lock_is_taken_at_begin(tmp_path: Path) -> None:
    db = open_db(tmp_path)
    other = sqlite3.connect(tmp_path / "signal" / "signal.db", timeout=0)
    try:
        with write_transaction(db), pytest.raises(sqlite3.OperationalError, match="locked"):
            other.execute("BEGIN IMMEDIATE")
    finally:
        other.close()


def test_a_block_that_ended_the_transaction_itself_is_not_rolled_back_twice(
    tmp_path: Path,
) -> None:
    db = open_db(tmp_path)
    with pytest.raises(ValueError, match="after commit"), write_transaction(db):
        db.execute("COMMIT")
        raise ValueError("after commit")
    assert not db.in_transaction


def test_an_empty_url_and_an_unknown_source_are_refused(tmp_path: Path) -> None:
    db = open_db(tmp_path)
    with pytest.raises(StoreError):
        propose_source(db, "A", "news", "  ", "x")
    with pytest.raises(StoreError):
        record_check(db, 99, Check(datetime(2026, 11, 13, 9, tzinfo=UTC), True, "", None, None, 0))
    assert sources(db) == []
    sid = propose_source(db, "A", "news", "https://e.org/f", "x")
    assert [r["id"] for r in sources(db)] == [sid]


def test_a_migration_another_opener_already_applied_is_skipped(tmp_path: Path) -> None:
    from credit_os.signal.store import _apply_migration

    db = open_db(tmp_path)
    _apply_migration(db, 1)
    assert get_meta(db, "schema_version") == "3"


def test_a_file_that_is_not_a_database_is_refused_and_closed(
    tmp_path: Path, opened: list[sqlite3.Connection]
) -> None:
    (tmp_path / "signal").mkdir()
    (tmp_path / "signal" / "signal.db").write_bytes(b"this is not a sqlite database" * 100)
    with pytest.raises(sqlite3.DatabaseError):
        open_db(tmp_path)
    assert len(opened) == 1
    with pytest.raises(sqlite3.ProgrammingError):  # a closed connection refuses every use
        opened[0].execute("SELECT 1")


def test_story_keys_ignore_tracking_www_and_slash_but_not_ports(tmp_path: Path) -> None:

    db = open_db(tmp_path)
    for n in (1, 2):
        propose_source(db, f"S{n}", "news", f"https://s{n}.example/feed", "tester")
    t = datetime(2026, 11, 13, 9, tzinfo=UTC)
    first = Entry("One", "https://www.e.org/a/?b=2&a=1&UTM_source=x&fbclid=y", t, "")
    assert add_story(db, 1, first, t) == "new"
    same = Entry("Two", "https://e.org/a?a=1&b=2&gclid=z", t, "")
    assert add_story(db, 1, same, t) == "seen"
    other_port = Entry("Three", "https://e.org:8443/a?a=1&b=2", t, "")
    assert add_story(db, 1, other_port, t) == "new"
    undated = Entry("Four", "https://e.org/c", None, "")
    assert add_story(db, 2, undated, t) == "new"
    future = Entry("Five", "https://e.org/d", t.replace(year=2030), "")
    assert add_story(db, 2, future, t) == "new"
    stamps = db.execute("SELECT published_at FROM stories WHERE source_id=2").fetchall()
    assert {r["published_at"] for r in stamps} == {t.isoformat()}


def test_last_check_with_equal_times_returns_the_one_recorded_later(tmp_path: Path) -> None:
    db = open_db(tmp_path)
    sid = propose_source(db, "A", "news", "https://e.org/f", "x")
    t = datetime(2026, 11, 13, 9, tzinfo=UTC)
    record_check(db, sid, Check(t, False, "first", None, None, 0))
    record_check(db, sid, Check(t, True, "second", None, None, 1))
    row = last_check(db, sid)
    assert row is not None
    assert (row["id"], row["reason"]) == (2, "second")


# L2 of the S-1a review: the three branches of the WAL switch, with real connections.
def test_wal_refused_where_the_connection_cannot_have_it() -> None:
    db = sqlite3.connect(":memory:")
    try:
        with pytest.raises(StoreUnusable, match="'memory'"):
            _enable_wal(db)
    finally:
        db.close()


def _hold_exclusive(path: Path) -> sqlite3.Connection:
    holder = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
    holder.execute("CREATE TABLE z(x)")
    holder.execute("BEGIN EXCLUSIVE")
    return holder


def test_wal_switch_retries_until_the_other_connection_lets_go(tmp_path: Path) -> None:
    path = tmp_path / "x.db"
    holder = _hold_exclusive(path)
    waiter = sqlite3.connect(path, timeout=0)
    release = threading.Timer(0.2, lambda: holder.execute("COMMIT"))
    release.start()
    started = time.monotonic()
    try:
        _enable_wal(waiter)
        waited = time.monotonic() - started
    finally:
        release.join()
        waiter.close()
        holder.close()
    assert waited >= 0.15
    check = sqlite3.connect(path)
    try:
        assert check.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    finally:
        check.close()


def test_wal_switch_gives_up_at_the_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store, "_BUSY_SECONDS", 0.2)
    holder = _hold_exclusive(tmp_path / "y.db")
    waiter = sqlite3.connect(tmp_path / "y.db", timeout=0, check_same_thread=False)
    raised: list[BaseException] = []

    def attempt() -> None:
        try:
            _enable_wal(waiter)
        except sqlite3.OperationalError as exc:
            raised.append(exc)

    # Without a deadline the retry loop never ends while the holder keeps the lock; the join
    # bound turns that hang into a failure.
    thread = threading.Thread(target=attempt, daemon=True)
    thread.start()
    thread.join(timeout=10)
    still_running = thread.is_alive()
    holder.execute("COMMIT")  # lets a loop without a deadline end so cleanup can close
    thread.join(timeout=10)
    waiter.close()
    holder.close()
    assert not still_running, "the WAL switch did not give up at the deadline"
    assert len(raised) == 1
    assert "locked" in str(raised[0])


# R13: a block joins only a transaction an outer write_transaction on this connection began.
def test_a_block_entered_inside_a_callers_own_transaction_is_refused_and_writes_nothing(
    tmp_path: Path,
) -> None:
    db = open_db(tmp_path)
    other = open_db(tmp_path)
    source = propose_source(db, "S1", "news", "https://s1.example/feed", "t")
    t = datetime(2026, 11, 13, 9, tzinfo=UTC)
    db.execute("BEGIN")
    db.execute("SELECT count(*) FROM stories").fetchone()
    with pytest.raises(StoreUnusable, match="transaction"):
        add_story(db, source, Entry("Alpha beta gamma delta", "https://e.org/a", t, ""), t)
    with pytest.raises(StoreUnusable, match="transaction"), write_transaction(db):
        _insert(db, "never")
    assert db.in_transaction  # the caller's transaction is still the caller's
    db.execute("ROLLBACK")
    assert other.execute("SELECT count(*) FROM stories").fetchone()[0] == 0
    assert _count(other) == 0


def test_every_writer_joins_an_outer_block_instead_of_committing_it(tmp_path: Path) -> None:
    db = open_db(tmp_path)
    other = open_db(tmp_path)
    t = datetime(2026, 11, 13, 9, tzinfo=UTC)
    with write_transaction(db):
        add_user(db, "u", "writer")
        source = propose_source(db, "S", "news", "https://s.example/feed", "u")
        set_source_state(db, source, "approved")
        record_check(db, source, Check(t, True, "", None, None, 0))
        set_meta(db, "k", "v")
        assert db.in_transaction
        assert (_count(other), len(sources(other)), get_meta(other, "k")) == (0, 0, None)
        assert last_check(other, source) is None
    assert (_count(other), get_meta(other, "k")) == (1, "v")
    assert [r["state"] for r in sources(other)] == ["approved"]
    assert last_check(other, source) is not None


def test_a_refused_duplicate_inside_a_block_does_not_drop_the_blocks_earlier_write(
    tmp_path: Path,
) -> None:
    db = open_db(tmp_path)
    add_user(db, "taken", "reader")
    with write_transaction(db):
        _insert(db, "first-half")
        with pytest.raises(StoreError, match="already exists"):
            add_user(db, "taken", "writer")
        _insert(db, "second-half")
    names = [r["name"] for r in db.execute("SELECT name FROM users ORDER BY id")]
    assert names == ["taken", "first-half", "second-half"]


def test_a_block_does_not_join_another_connections_block(tmp_path: Path) -> None:
    db = open_db(tmp_path)
    other = open_db(tmp_path)
    with write_transaction(db):
        other.execute("BEGIN")
        with pytest.raises(StoreUnusable, match="transaction"), write_transaction(other):
            _insert(other, "never")
        other.execute("ROLLBACK")


def test_a_block_that_raised_leaves_no_ownership_behind(tmp_path: Path) -> None:
    db = open_db(tmp_path)
    with pytest.raises(ValueError, match="boom"), write_transaction(db):
        raise ValueError("boom")
    db.execute("BEGIN")
    with pytest.raises(StoreUnusable, match="transaction"), write_transaction(db):
        _insert(db, "never")
    db.execute("ROLLBACK")
    with write_transaction(db):
        _insert(db, "fine")
    assert _count(db) == 1


class _InterruptedAdd(set[int]):
    """A marker set whose `add` stores the id and then raises, as a signal delivered right
    after the call would."""

    def add(self, element: int) -> None:
        super().add(element)
        raise KeyboardInterrupt


def test_an_exception_where_the_marker_is_added_leaves_no_marker_behind(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = open_db(tmp_path)
    marks = _InterruptedAdd()
    monkeypatch.setattr(store, "_OWNED", marks)
    with pytest.raises(KeyboardInterrupt), write_transaction(db):
        pytest.fail("the block body must not run")
    assert marks == set()
    assert not db.in_transaction
    monkeypatch.setattr(store, "_OWNED", set())
    add_user(db, "after", "reader")
    assert role_of(db, "after") == "reader"


def test_a_nested_block_after_the_outer_one_ended_the_transaction_is_refused(
    tmp_path: Path,
) -> None:
    db = open_db(tmp_path)
    with pytest.raises(StoreUnusable, match="transaction"), write_transaction(db):
        db.execute("COMMIT")
        with write_transaction(db):
            _insert(db, "never")
    assert _count(db) == 0


# R14: a newer database is refused before any write, journal mode included.
def test_a_newer_database_in_delete_mode_is_refused_untouched(tmp_path: Path) -> None:
    open_db(tmp_path).close()
    path = tmp_path / "signal" / "signal.db"
    raw = sqlite3.connect(path, isolation_level=None)
    raw.execute("UPDATE meta SET value=? WHERE key='schema_version'", (str(len(MIGRATIONS) + 1),))
    assert raw.execute("PRAGMA journal_mode=DELETE").fetchone()[0] == "delete"
    raw.close()
    before = path.read_bytes()
    names = sorted(p.name for p in path.parent.iterdir())
    with pytest.raises(StoreUnusable, match="newer"):
        open_db(tmp_path)
    assert path.read_bytes() == before
    assert (before[18], before[19]) == (1, 1)  # rollback journal, not WAL
    assert sorted(p.name for p in path.parent.iterdir()) == names


# R15: bad input is a StoreError and nothing else.
_T = datetime(2026, 11, 13, 9, tzinfo=UTC)
_NAIVE = _T.replace(tzinfo=None)
_BAD = "\ud800"  # a lone surrogate: SQLite cannot encode it
_FAR = 2**63  # one past the largest id SQLite holds


def _entry(title: str = "Alpha beta gamma delta", published: datetime | None = _T) -> Entry:
    return Entry(title, "https://e.org/a", published, "")


def _bad_calls(db: sqlite3.Connection, source: int) -> dict[str, Callable[[], object]]:
    def check(count: int = 0) -> Check:
        return Check(_T, True, "", None, None, count)

    utc_low = datetime(1, 1, 1, tzinfo=timezone(timedelta(hours=5)))
    utc_high = datetime(9999, 12, 31, 23, tzinfo=timezone(timedelta(hours=-5)))
    return {
        "state id too large": lambda: set_source_state(db, _FAR, "approved"),
        "check id too large": lambda: record_check(db, _FAR, check()),
        "last check id too large": lambda: last_check(db, _FAR),
        "last check id too small": lambda: last_check(db, -_FAR - 1),
        "check count too large": lambda: record_check(db, source, check(_FAR)),
        "story source too large": lambda: add_story(db, _FAR, _entry(), _T),
        "story unknown source": lambda: add_story(db, 999, _entry(), _T),
        "story naive fetched": lambda: add_story(db, source, _entry(), _NAIVE),
        "story naive published": lambda: add_story(db, source, _entry(published=_NAIVE), _T),
        "story link with a port out of range": lambda: add_story(
            db, source, Entry("a b c d", "https://e.org:99999/x", _T, ""), _T
        ),
        "story unencodable title": lambda: add_story(db, source, _entry(_BAD), _T),
        "story unencodable summary": lambda: add_story(
            db, source, Entry("a b c d", "https://e.org/s", _T, _BAD), _T
        ),
        "story unencodable link": lambda: add_story(
            db, source, Entry("a b c d", f"https://e.org/{_BAD}", _T, ""), _T
        ),
        "user unencodable": lambda: add_user(db, _BAD, "reader"),
        "source unencodable": lambda: propose_source(db, "n", "news", f"https://{_BAD}", "x"),
        "source unencodable name": lambda: propose_source(
            db, _BAD, "news", "https://n.example/feed", "x"
        ),
        "source unencodable proposer": lambda: propose_source(
            db, "n", "news", "https://p.example/feed", _BAD
        ),
        "check unencodable": lambda: record_check(db, source, Check(_T, True, _BAD, None, None, 0)),
        "check unencodable etag": lambda: record_check(
            db, source, Check(_T, True, "", _BAD, None, 0)
        ),
        "check unencodable modified": lambda: record_check(
            db, source, Check(_T, True, "", None, _BAD, 0)
        ),
        "meta unencodable key": lambda: set_meta(db, _BAD, "v"),
        "meta unencodable": lambda: set_meta(db, "k", _BAD),
        "role lookup unencodable": lambda: role_of(db, _BAD),
        "meta lookup unencodable": lambda: get_meta(db, _BAD),
        "time before year 1 in UTC": lambda: utc_text(utc_low),
        "time after year 9999 in UTC": lambda: utc_text(utc_high),
    }


def test_bad_input_is_a_store_error_and_leaves_nothing_behind(tmp_path: Path) -> None:
    db = open_db(tmp_path)
    source = propose_source(db, "S", "news", "https://s.example/feed", "t")
    for label, call in _bad_calls(db, source).items():
        with pytest.raises(StoreError) as refused:
            call()
        assert not isinstance(refused.value, StoreUnusable), label
        assert not db.in_transaction, label
    counts = db.execute(
        "SELECT (SELECT count(*) FROM users), (SELECT count(*) FROM stories),"
        " (SELECT count(*) FROM story_duplicates), (SELECT count(*) FROM source_checks)"
    ).fetchone()
    assert tuple(counts) == (0, 0, 0, 0)
    assert get_meta(db, "k") is None


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX file modes")
def test_a_database_file_open_db_creates_is_owner_only(tmp_path: Path) -> None:
    def modes() -> dict[str, int]:
        found = (tmp_path / "signal").glob("signal.db*")
        return {f.name: stat.S_IMODE(f.stat().st_mode) for f in found}

    db = open_db(tmp_path)
    try:
        opened_modes = modes()
        add_user(db, "writer", "reader")
        written_modes = modes()
    finally:
        db.close()
    for seen in (opened_modes, written_modes):
        assert set(seen) == {"signal.db", "signal.db-wal", "signal.db-shm"}
        assert set(seen.values()) == {0o600}
    assert set(modes().values()) == {0o600}


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX file modes")
def test_a_database_file_that_already_exists_keeps_its_mode(tmp_path: Path) -> None:
    open_db(tmp_path).close()
    path = tmp_path / "signal" / "signal.db"
    path.chmod(0o640)
    open_db(tmp_path).close()
    assert stat.S_IMODE(path.stat().st_mode) == 0o640


def test_require_id_refuses_an_unholdable_id_with_the_kind_named() -> None:
    require_id(1, "source")
    require_id(2**63 - 1, "source")
    require_id(-(2**63), "source")
    with pytest.raises(StoreError, match=r"^no widget with that id$"):
        require_id(2**63, "widget")
    with pytest.raises(StoreError, match=r"^no widget with that id$"):
        require_id(-(2**63) - 1, "widget")


@pytest.mark.parametrize("digits", [4_000, 4_301, 5_000])
def test_require_id_refuses_a_huge_id_without_formatting_it(digits: int) -> None:
    for number in (10 ** (digits - 1), -(10 ** (digits - 1))):
        with pytest.raises(StoreError) as caught:
            require_id(number, "widget")
        assert str(caught.value) == "no widget with that id"


def test_new_row_id_returns_the_insert_id_and_refuses_a_missing_one(tmp_path: Path) -> None:
    db = open_db(tmp_path)
    with write_transaction(db):
        cur = db.execute("INSERT INTO users(name, role) VALUES('a', 'reader')")
    assert new_row_id(cur) == 1
    with pytest.raises(StoreError, match="did not report the new row's id"):
        new_row_id(db.cursor())  # a cursor that has run no INSERT reports None


_CET = timezone(timedelta(hours=1))


def test_what_the_writers_store_is_read_back_column_by_column(tmp_path: Path) -> None:
    db = open_db(tmp_path)
    propose_source(db, "Authority Press", "regulator", "https://s1.example/feed", "A. Kovac")
    propose_source(db, "Wire Desk", "news", "https://s2.example/feed", "M. Lind")
    assert [
        tuple(r) for r in db.execute("SELECT id, name, kind, url, state, proposed_by FROM sources")
    ] == [
        (1, "Authority Press", "regulator", "https://s1.example/feed", "proposed", "A. Kovac"),
        (2, "Wire Desk", "news", "https://s2.example/feed", "proposed", "M. Lind"),
    ]
    first = Entry(
        "Wholesale Access Remedy enters Phase Two",
        "https://www.Example.org/News/a/?utm_source=x&b=2",
        datetime(2026, 11, 13, 8, 0, tzinfo=_CET),
        "Phase two begins.",
    )
    assert add_story(db, 1, first, datetime(2026, 11, 13, 9, 30, tzinfo=UTC)) == "new"
    second = Entry(
        "Wholesale access remedy enters phase two",
        "https://other.example/x?id=7",
        datetime(2026, 11, 13, 10, 0, tzinfo=UTC),
        "Other words.",
    )
    assert add_story(db, 2, second, datetime(2026, 11, 13, 11, 15, tzinfo=UTC)) == "duplicate"
    assert [tuple(r) for r in db.execute("SELECT * FROM stories")] == [
        (
            1,
            1,
            "Wholesale Access Remedy enters Phase Two",
            "https://www.Example.org/News/a/?utm_source=x&b=2",
            "example.org/News/a?b=2",
            "wholesale access remedy enters phase two",
            "2026-11-13T07:00:00+00:00",
            "2026-11-13T09:30:00+00:00",
            "Phase two begins.",
        )
    ]
    assert [tuple(r) for r in db.execute("SELECT * FROM story_duplicates")] == [
        (
            1,
            2,
            "https://other.example/x?id=7",
            "other.example/x?id=7",
            "2026-11-13T10:00:00+00:00",
            "2026-11-13T11:15:00+00:00",
        )
    ]
    hits = db.execute("SELECT rowid FROM stories_fts WHERE stories_fts MATCH 'begins'").fetchall()
    assert [r[0] for r in hits] == [1]


def test_last_check_is_the_latest_by_time_not_the_latest_recorded(tmp_path: Path) -> None:
    db = open_db(tmp_path)
    sid = propose_source(db, "A", "news", "https://e.org/f", "x")
    late = datetime(2026, 11, 13, 10, 0, tzinfo=UTC)
    early = datetime(2026, 11, 13, 9, 0, tzinfo=UTC)
    record_check(db, sid, Check(late, True, "later time, recorded first", None, None, 0))
    record_check(db, sid, Check(early, False, "earlier time, recorded second", None, None, 0))
    row = last_check(db, sid)
    assert row is not None
    assert (row["id"], row["at"]) == (1, "2026-11-13T10:00:00+00:00")


def test_store_unusable_is_a_store_error() -> None:
    assert issubclass(StoreUnusable, StoreError)


def test_the_refusals_that_are_not_bad_input_are_not_bad_input_errors(tmp_path: Path) -> None:
    db = open_db(tmp_path)
    add_user(db, "taken", "reader")
    with pytest.raises(StoreError, match="already exists") as duplicate:
        add_user(db, "taken", "writer")
    with pytest.raises(StoreError, match="no source with id 99") as unknown:
        set_source_state(db, 99, "approved")
    assert not isinstance(duplicate.value, StoreUnusable)
    assert not isinstance(unknown.value, StoreUnusable)


def test_require_text_refuses_unencodable_text_and_accepts_the_rest() -> None:
    require_text("plain", None, "caf\u00e9")
    with pytest.raises(StoreError, match="encodable") as refused:
        require_text("plain", None, _BAD)
    assert not isinstance(refused.value, StoreUnusable)


@pytest.mark.parametrize("value", ["99", "three", "0"])
def test_set_meta_refuses_the_key_the_migrations_own(tmp_path: Path, value: str) -> None:
    db = open_db(tmp_path)
    with pytest.raises(StoreError, match="schema_version") as refused:
        set_meta(db, "schema_version", value)
    assert not isinstance(refused.value, StoreUnusable)
    assert not db.in_transaction
    assert get_meta(db, "schema_version") == "3"
    db.close()
    open_db(tmp_path).close()  # the refused write left a database that still opens
