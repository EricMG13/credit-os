import sqlite3
from collections.abc import Callable, Iterator
from itertools import permutations
from typing import Any

import pytest
import store_schema_rows_key as rows

from credit_os.store import schema

Row = dict[str, object]
Connect = Callable[..., sqlite3.Connection]
TABLES = ("runs", "run_sources", "events")
BASE: dict[str, Row] = {"runs": rows.RUN, "run_sources": rows.PIN, "events": rows.EVENT}
LIVE = ("running", "finished", "stopped", "failed")
ENDED = ("rejected", "finished", "stopped", "failed")
MOVES = list(permutations(rows.STATUSES, 2))
_STOPPED: Row = {"status": "stopped", "ended_at": rows.T2, "end_reason": "cap"}
# The updates that bring the valid RUN, by allowed moves only, to each status.
SETUP: dict[str, tuple[Row, ...]] = {
    "created": (),
    "running": (rows.RUNNING,),
    "stopped": (rows.RUNNING, _STOPPED),
    "failed": (rows.RUNNING, {**_STOPPED, "status": "failed"}),
    **rows.FINAL_STATUSES_SETUP,
}
ACCEPTED = rows.ACCEPTED_ROWS
INSERTS = rows.REFUSED_ROWS + rows.REFUSED_ROWS_V2
STATEMENTS = rows.REFUSED_STATEMENTS + rows.REFUSED_STATEMENTS_V2
FINAL_CASES = [
    (status, case[0], case[1], case[2], case[3])
    for status in rows.FINAL_STATUSES_SETUP
    for case in rows.FINAL_RUN_STATEMENTS
]


@pytest.fixture
def connect() -> Iterator[Connect]:
    """Open raw connections migrated to 1 by running the statements one by one; close them after."""
    opened: list[sqlite3.Connection] = []

    def make(foreign_keys: bool = True) -> sqlite3.Connection:
        db = sqlite3.connect(":memory:", autocommit=True)
        opened.append(db)
        db.execute(f"PRAGMA foreign_keys = {'ON' if foreign_keys else 'OFF'}")
        for statement in schema.MIGRATION_1:
            db.execute(statement)
        return db

    yield make
    for db in opened:
        db.close()


@pytest.fixture
def raw(connect: Connect) -> sqlite3.Connection:
    return connect()


def _insert_sql(table: str, values: Row) -> tuple[str, tuple[object, ...]]:
    names = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    return f"INSERT INTO {table} ({names}) VALUES ({marks})", tuple(values.values())


def _update_sql(columns: Row) -> tuple[str, tuple[object, ...]]:
    sets = ", ".join(f"{name} = ?" for name in columns)
    return f"UPDATE runs SET {sets} WHERE run_id = ?", (*columns.values(), "run-001")


def _insert(db: sqlite3.Connection, table: str, values: Row) -> None:
    db.execute(*_insert_sql(table, values))


def _update(db: sqlite3.Connection, columns: Row) -> None:
    db.execute(*_update_sql(columns))


def _snapshot(db: sqlite3.Connection) -> list[list[tuple[Any, ...]]]:
    return [db.execute(f"SELECT * FROM {t} ORDER BY rowid").fetchall() for t in TABLES]


def _refused(
    db: sqlite3.Connection,
    statement: tuple[str, tuple[object, ...]],
    messages: tuple[str, ...] | None = None,
) -> None:
    """The statement raises IntegrityError (with one of the messages, if given); nothing changed."""
    before = _snapshot(db)
    with pytest.raises(sqlite3.IntegrityError) as refused:
        db.execute(*statement)
    if messages is not None:
        assert str(refused.value) in messages
    assert _snapshot(db) == before


def _at(db: sqlite3.Connection, status: str) -> sqlite3.Connection:
    for columns in SETUP[status]:
        _update(db, columns)
    assert db.execute("SELECT status FROM runs").fetchone() == (status,)
    return db


@pytest.fixture
def full(raw: sqlite3.Connection) -> sqlite3.Connection:
    for table in TABLES:
        _insert(raw, table, BASE[table])
    return raw


@pytest.mark.parametrize(("label", "table", "columns"), ACCEPTED, ids=[r[0] for r in ACCEPTED])
def test_accepted_row(raw: sqlite3.Connection, label: str, table: str, columns: Row) -> None:
    _insert(raw, "runs", rows.RUN)
    before = _snapshot(raw)
    _insert(raw, table, {**BASE[table], **columns})
    after = _snapshot(raw)
    index = TABLES.index(table)
    assert len(after[index]) == len(before[index]) + 1
    assert after[index][:-1] == before[index]


@pytest.mark.parametrize(("label", "table", "columns"), INSERTS, ids=[r[0] for r in INSERTS])
def test_refused_row(full: sqlite3.Connection, label: str, table: str, columns: Row) -> None:
    _refused(full, _insert_sql(table, {**BASE[table], **columns}))


@pytest.mark.parametrize(
    ("label", "sql", "params", "message"), STATEMENTS, ids=[r[0] for r in STATEMENTS]
)
def test_refused_statement(
    full: sqlite3.Connection, label: str, sql: str, params: tuple[object, ...], message: str
) -> None:
    _refused(full, (sql, params), (message,))


@pytest.mark.parametrize(
    ("label", "columns"), rows.REFUSED_ENDS, ids=[r[0] for r in rows.REFUSED_ENDS]
)
def test_refused_end(connect: Connect, label: str, columns: Row) -> None:
    db = connect()
    _insert(db, "runs", rows.RUN)
    _update(db, rows.RUNNING)
    _refused(db, _update_sql(columns))


@pytest.mark.parametrize(
    ("label", "columns"), rows.REFUSED_STARTS, ids=[r[0] for r in rows.REFUSED_STARTS]
)
def test_refused_start(raw: sqlite3.Connection, label: str, columns: Row) -> None:
    _insert(raw, "runs", rows.RUN)
    _refused(raw, _update_sql(columns))


def _target(status: str) -> Row:
    """The columns a row needs to hold `status`; started_at is the one it already has once set."""
    columns: Row = {"status": status}
    if status in ENDED:
        columns |= {"ended_at": rows.T2, "end_reason": "x"}
    else:
        columns |= {"ended_at": None, "end_reason": None, "end_message": None}
    if status in LIVE:
        columns["started_at"] = rows.T1
    return columns


def _ids(pairs: list[tuple[str, str]]) -> list[str]:
    return [f"{a}>{b}" for a, b in pairs]


def test_moves_cover_every_ordered_pair() -> None:
    assert len(MOVES) == 30
    assert set(rows.ALLOWED_MOVES) <= set(MOVES)
    assert set(rows.TWO_NET_MOVES) <= set(MOVES) - set(rows.ALLOWED_MOVES)
    assert len(rows.TWO_NET_MOVES) == 8


@pytest.mark.parametrize(("source", "target"), MOVES, ids=_ids(MOVES))
def test_status_move(connect: Connect, source: str, target: str) -> None:
    db = connect()
    _insert(db, "runs", rows.RUN)
    _at(db, source)
    if (source, target) in rows.ALLOWED_MOVES:
        _update(db, _target(target))
        assert db.execute("SELECT status FROM runs").fetchone() == (target,)
    else:
        _refused(db, _update_sql(_target(target)), (rows.MOVE_REFUSED_MESSAGE,))


@pytest.mark.parametrize(("source", "target"), MOVES, ids=_ids(MOVES))
def test_only_the_move_rule_refuses_a_consistent_row(
    connect: Connect, source: str, target: str
) -> None:
    db = connect()
    _insert(db, "runs", rows.RUN)
    _at(db, source)
    db.execute("DROP TRIGGER runs_status_moves")  # a test-only copy
    if (source, target) in rows.TWO_NET_MOVES:
        _refused(db, _update_sql(_target(target)))
    else:
        _update(db, _target(target))
        assert db.execute("SELECT status FROM runs").fetchone() == (target,)


@pytest.mark.parametrize("status", rows.STATUSES)
def test_same_status_is_refused(connect: Connect, status: str) -> None:
    db = connect()
    _insert(db, "runs", rows.RUN)
    _refused(_at(db, status), _update_sql({"status": status}), rows.SAME_STATUS_MESSAGES[status])


@pytest.mark.parametrize(
    ("status", "label", "sql", "params", "message"),
    FINAL_CASES,
    ids=[f"{c[0]}-{c[1]}" for c in FINAL_CASES],
)
def test_final_run_statement(
    full: sqlite3.Connection,
    status: str,
    label: str,
    sql: str,
    params: tuple[object, ...],
    message: str,
) -> None:
    _refused(_at(full, status), (sql, params), (message,))


@pytest.mark.parametrize(
    ("label", "sql", "params", "message"),
    rows.ORPHAN_STATEMENTS,
    ids=[r[0] for r in rows.ORPHAN_STATEMENTS],
)
def test_orphan_is_refused_without_foreign_keys(
    connect: Connect, label: str, sql: str, params: tuple[object, ...], message: str
) -> None:
    db = connect(foreign_keys=False)
    _refused(db, (sql, params), (message,))
    assert _snapshot(db) == [[], [], []]


def test_events_index_columns(raw: sqlite3.Connection) -> None:
    query = "SELECT seqno, name FROM pragma_index_info('events_by_run') ORDER BY seqno"
    assert tuple(raw.execute(query).fetchall()) == rows.EVENTS_INDEX_COLUMNS


def test_second_start_time_is_refused(raw: sqlite3.Connection) -> None:
    _insert(raw, "runs", rows.RUN)
    _update(raw, rows.RUNNING)
    before = _snapshot(raw)
    with pytest.raises(sqlite3.IntegrityError) as refused:
        raw.execute("UPDATE runs SET started_at = ?", (rows.T2,))
    assert str(refused.value) == rows.START_FIXED_MESSAGE
    assert _snapshot(raw) == before


def test_event_sequence_is_never_reused(raw: sqlite3.Connection) -> None:
    _insert(raw, "runs", rows.RUN)
    for expected in range(rows.FIRST_SEQ, rows.FIRST_SEQ + 3):
        _insert(raw, "events", rows.EVENT)
        assert raw.execute("SELECT max(seq) FROM events").fetchone() == (expected,)
    raw.execute("DROP TRIGGER events_no_delete")
    raw.execute("DELETE FROM events WHERE seq = ?", (rows.FIRST_SEQ + 2,))
    last = raw.execute("SELECT seq FROM sqlite_sequence WHERE name = 'events'").fetchone()
    assert last == (rows.FIRST_SEQ + 2,)
    _insert(raw, "events", rows.EVENT)
    assert raw.execute("SELECT max(seq) FROM events").fetchone() == (rows.FIRST_SEQ + 3,)


@pytest.mark.parametrize(
    "writer", ["a" * 31, "a" * 33, "a" * 32 + "\x00junk"], ids=["short", "long", "nul-tail"]
)
def test_writer_is_exactly_thirty_two_characters(full: sqlite3.Connection, writer: str) -> None:
    _refused(full, _insert_sql("runs", {**rows.RUN, "run_id": "run-x", "writer": writer}))


@pytest.mark.parametrize("status", rows.LIVE_STATUSES)
def test_event_is_accepted_on_a_live_run(raw: sqlite3.Connection, status: str) -> None:
    _insert(raw, "runs", rows.RUN)
    _at(raw, status)
    before = _snapshot(raw)
    _insert(raw, "events", rows.EVENT)
    after = _snapshot(raw)
    assert len(after[TABLES.index("events")]) == len(before[TABLES.index("events")]) + 1
    assert after[:2] == before[:2]
