import sqlite3
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager, suppress
from pathlib import Path
from typing import Any

import pytest
import store_txn_key as key

from credit_os.store import txn
from credit_os.store.errors import (
    StoreBusy,
    StoreConflict,
    StoreError,
    StoreRefused,
    StoreUnusable,
)
from credit_os.store.txn import check_migrations, migrate, write_transaction

LISTS = {0: (), 1: (key.M1,), 2: (key.M1, key.M2), 3: (key.M1, key.M2, key.M3)}
APPLICATION_ID = 77


def _connect(folder: Path, **kwargs: Any) -> sqlite3.Connection:
    connection: sqlite3.Connection = sqlite3.connect(
        folder / "t.sqlite3", autocommit=True, timeout=0.2, **kwargs
    )
    return connection


@contextmanager
def _database(folder: Path, version: int = 0) -> Iterator[sqlite3.Connection]:
    with closing(_connect(folder)) as connection:
        connection.execute(f"PRAGMA application_id = {APPLICATION_ID}")
        migrate(connection, LISTS[version])
        yield connection


def _snapshot(connection: sqlite3.Connection) -> tuple[Any, ...]:
    """Version, schema rows, application id, journal mode, full dump."""

    def one(sql: str) -> list[tuple[Any, ...]]:
        return connection.execute(sql).fetchall()

    schema = tuple(one("SELECT type, name FROM sqlite_schema ORDER BY 1, 2"))
    return (
        one("PRAGMA user_version"),
        schema,
        one("PRAGMA application_id"),
        one("PRAGMA journal_mode"),
        list(connection.iterdump()),
    )


def test_a_tuple_of_tuples_of_text_is_a_valid_migration_list() -> None:
    for migrations in ((), (key.M1,), (key.M1, key.M2)):
        assert check_migrations(migrations) == migrations


@pytest.mark.parametrize(
    "migrations", key.REFUSED_MIGRATION_LISTS, ids=[f"row{i}" for i in range(7)]
)
def test_a_bad_migration_list_is_refused(migrations: object) -> None:
    with pytest.raises(StoreRefused):
        check_migrations(migrations)


@pytest.mark.parametrize("version", [0, 1, 2, 3])
def test_a_fresh_database_reaches_each_version(version: int, tmp_path: Path) -> None:
    with _database(tmp_path, version) as connection:
        found, schema, *_ = _snapshot(connection)
        assert (found, schema) == ([(version,)], key.SCHEMA_AT[version])
        columns = tuple(row[1] for row in connection.execute("PRAGMA table_info(note)"))
        assert columns == key.NOTE_COLUMNS_AT.get(version, ())


def test_a_forward_migration_keeps_the_rows(tmp_path: Path) -> None:
    with _database(tmp_path, 1) as connection:
        connection.execute("INSERT INTO note(body) VALUES ('kept')")
        migrate(connection, LISTS[3])
        assert connection.execute("SELECT body, tag FROM note").fetchall() == [("kept", None)]
        assert _snapshot(connection)[1] == key.SCHEMA_AT[3]


@pytest.mark.parametrize(
    "bad",
    key.BAD_SECOND_MIGRATIONS.values(),
    ids=[f"row{i}" for i in range(len(key.BAD_SECOND_MIGRATIONS))],
)
def test_a_bad_second_migration_is_unusable_and_changes_nothing(
    bad: tuple[str, ...], tmp_path: Path
) -> None:
    with _database(tmp_path, 1) as connection:
        connection.execute("INSERT INTO note(body) VALUES ('kept')")
        before = _snapshot(connection)
        with pytest.raises(StoreUnusable):
            migrate(connection, (key.M1, bad))
        assert _snapshot(connection) == before
        assert not connection.in_transaction
        databases = {row[1] for row in connection.execute("PRAGMA database_list")}
        assert databases <= {"main", "temp"}
        assert connection.execute("SELECT count(*) FROM sqlite_temp_schema").fetchall() == [(0,)]
        migrate(connection, (key.M1, key.M2))
        assert _snapshot(connection)[:2] == ([(2,)], key.SCHEMA_AT[2])


def test_a_failing_first_migration_leaves_no_table(tmp_path: Path) -> None:
    with _database(tmp_path) as connection:
        with pytest.raises(StoreUnusable):
            migrate(connection, ((key.M1[0], key.M1[0]),))
        assert _snapshot(connection)[:2] == ([(0,)], ())


@pytest.mark.parametrize("version", [-1, 4, 2**31 - 1, -(2**31)])
def test_a_version_outside_the_list_is_unusable_before_any_transaction(
    version: int, tmp_path: Path
) -> None:
    with _database(tmp_path) as connection:
        connection.execute(f"PRAGMA user_version = {version}")
        with pytest.raises(StoreUnusable):
            migrate(connection, LISTS[3])
        assert connection.execute("PRAGMA user_version").fetchall() == [(version,)]


def test_a_migration_another_opener_ran_is_skipped(tmp_path: Path) -> None:
    with _database(tmp_path, 1) as connection:
        txn._run(connection, 1, ("CREATE TABLE never(x)", "PRAGMA user_version = 1"))
        assert _snapshot(connection)[1] == key.SCHEMA_AT[1]


@pytest.mark.parametrize("number", [4, 5])
def test_a_migration_numbered_past_the_next_one_is_unusable(number: int, tmp_path: Path) -> None:
    with _database(tmp_path, 2) as connection, pytest.raises(StoreUnusable):
        txn._run(connection, number, key.M3)


def _race(monkeypatch: pytest.MonkeyPatch, other: Callable[[], None]) -> None:
    """Run `other` once, just before the first migration's own transaction starts."""
    real = txn._run

    def placed(connection: sqlite3.Connection, number: int, statements: tuple[str, ...]) -> None:
        monkeypatch.setattr(txn, "_run", real)
        other()
        real(connection, number, statements)

    monkeypatch.setattr(txn, "_run", placed)


def test_an_opener_whose_planned_migrations_another_ran_in_between_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with closing(_connect(tmp_path)) as slow, closing(_connect(tmp_path)) as fast:
        _race(monkeypatch, lambda: migrate(fast, LISTS[2]))
        migrate(slow, LISTS[2])
        assert _snapshot(slow)[:2] == ([(2,)], key.SCHEMA_AT[2])


def test_an_opener_that_finds_a_newer_file_in_its_transaction_is_unusable_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with _database(tmp_path, 1) as old, closing(_connect(tmp_path)) as newer:
        seen: list[tuple[Any, ...]] = []

        def newer_opener() -> None:
            migrate(newer, LISTS[3])
            seen.append(_snapshot(newer))

        _race(monkeypatch, newer_opener)
        with pytest.raises(StoreUnusable):
            migrate(old, LISTS[2])
        assert _snapshot(old) == seen[0]
        assert _snapshot(old)[:2] == ([(3,)], key.SCHEMA_AT[3])


def test_the_write_transaction_commits(tmp_path: Path) -> None:
    with _database(tmp_path, 1) as connection:
        with write_transaction(connection):
            connection.execute("INSERT INTO note(body) VALUES ('a')")
        assert not connection.in_transaction
        with closing(_connect(tmp_path)) as other:
            assert other.execute("SELECT body FROM note").fetchall() == [("a",)]


@pytest.mark.parametrize(
    "raised", [RuntimeError("boom"), KeyboardInterrupt()], ids=["error", "interrupt"]
)
def test_an_exception_rolls_back_leaves_as_itself_and_the_connection_is_reusable(
    raised: BaseException, tmp_path: Path
) -> None:
    with _database(tmp_path, 1) as connection:
        with pytest.raises(type(raised)) as caught, write_transaction(connection):
            connection.execute("INSERT INTO note(body) VALUES ('lost')")
            raise raised
        assert caught.value is raised
        assert not hasattr(raised, "__notes__")  # a rollback that worked adds no note
        assert not connection.in_transaction
        with write_transaction(connection):
            connection.execute("INSERT INTO note(body) VALUES ('kept')")
        assert connection.execute("SELECT body FROM note").fetchall() == [("kept",)]


def test_a_sqlite_error_leaves_as_its_store_error_with_the_cause(tmp_path: Path) -> None:
    with _database(tmp_path, 1) as connection:
        with pytest.raises(StoreConflict) as caught, write_transaction(connection):
            connection.execute("INSERT INTO note(body) VALUES ('lost')")
            connection.execute("INSERT INTO note(body) VALUES (NULL)")
        assert isinstance(caught.value.__cause__, sqlite3.IntegrityError)
        assert not hasattr(caught.value, "__notes__")
        assert not hasattr(caught.value.__cause__, "__notes__")
        assert connection.execute("SELECT count(*) FROM note").fetchall() == [(0,)]


@pytest.mark.parametrize("statement", ["COMMIT", "END", "ROLLBACK", "BEGIN"])
def test_a_body_cannot_end_or_start_a_transaction_and_nothing_is_committed(
    statement: str, tmp_path: Path
) -> None:
    with _database(tmp_path, 1) as connection:
        with pytest.raises(StoreUnusable), write_transaction(connection):
            connection.execute("INSERT INTO note(body) VALUES ('x')")
            connection.execute(statement)
        assert not connection.in_transaction
        assert connection.execute("SELECT count(*) FROM note").fetchall() == [(0,)]


@pytest.mark.parametrize("tail", ["COMMIT", "ROLLBACK"])
def test_a_body_that_ends_then_restarts_a_transaction_is_refused_at_the_first_statement(
    tail: str, tmp_path: Path
) -> None:
    with _database(tmp_path, 1) as connection:
        with pytest.raises(StoreUnusable), write_transaction(connection):
            connection.execute("INSERT INTO note(body) VALUES ('a')")
            connection.execute(tail)
            connection.execute("BEGIN IMMEDIATE")
        assert connection.execute("SELECT count(*) FROM note").fetchall() == [(0,)]


Cause = Callable[[sqlite3.Connection], object]


def _or_rollback(c: sqlite3.Connection) -> object:
    return c.execute("INSERT OR ROLLBACK INTO note(body) VALUES (NULL)")


def _column_rollback(c: sqlite3.Connection) -> object:
    return c.execute("INSERT INTO r(x) VALUES ('a')")


def _trigger_rollback(c: sqlite3.Connection) -> object:
    return c.execute("INSERT INTO note(body) VALUES ('boom')")


def _full(c: sqlite3.Connection) -> object:
    pages = c.execute("PRAGMA page_count").fetchall()[0][0]
    c.execute(f"PRAGMA max_page_count = {pages + 1}")
    return c.execute("INSERT INTO big(x) VALUES (?)", ("x" * 200_000,))


def _interrupt(c: sqlite3.Connection) -> object:
    return c.execute("INSERT INTO note(body) SELECT stop(value) FROM json_each('[1, 2]')")


_CAUSES: dict[str, Cause] = {
    "or-rollback": _or_rollback,
    "column": _column_rollback,
    "trigger": _trigger_rollback,
    "full": _full,
    "interrupt": _interrupt,
}


def _prepared(folder: Path) -> sqlite3.Connection:
    """A raw connection at version 1 with a table, a trigger and a function for each cause."""
    c = sqlite3.connect(folder / "t.sqlite3", autocommit=True, timeout=0.2)
    migrate(c, (key.M1,))
    c.execute("CREATE TABLE r(x TEXT UNIQUE ON CONFLICT ROLLBACK)")
    c.execute("INSERT INTO r(x) VALUES ('a')")
    c.execute("CREATE TABLE big(x TEXT)")
    c.execute(
        "CREATE TRIGGER no BEFORE INSERT ON note WHEN new.body = 'boom' "
        "BEGIN SELECT RAISE(ROLLBACK, 'no'); END"
    )

    def stop(value: int) -> int:
        c.interrupt()
        return value

    c.create_function("stop", 1, stop)
    return c


def _rows(c: sqlite3.Connection) -> list[tuple[Any, ...]]:
    return c.execute("SELECT body FROM note ORDER BY id").fetchall()


@pytest.mark.parametrize("tail", ["write", "write-swallowed", "nothing"])
@pytest.mark.parametrize("cause", list(_CAUSES))
def test_a_body_that_swallows_sqlites_own_rollback_commits_nothing(
    cause: str, tail: str, tmp_path: Path
) -> None:
    ended: list[bool] = []
    with closing(_prepared(tmp_path)) as c:
        with pytest.raises(StoreUnusable) as caught, write_transaction(c):
            c.execute("INSERT INTO note(body) VALUES ('a')")
            try:
                _CAUSES[cause](c)
            except sqlite3.Error:
                pass
            ended.append(not c.in_transaction)
            if tail == "write":
                c.execute("INSERT INTO note(body) VALUES ('b')")
            if tail == "write-swallowed":
                with suppress(sqlite3.Error):
                    c.execute("INSERT INTO note(body) VALUES ('b')")
        assert ended == [True]
        if tail != "write":
            assert "ended inside its body" in str(caught.value)
        assert _rows(c) == []
        assert not c.in_transaction
        c.execute("INSERT INTO note(body) VALUES ('after')")
        assert _rows(c) == [("after",)]


@pytest.mark.parametrize("cause", list(_CAUSES))
def test_a_finally_that_writes_after_sqlites_own_rollback_commits_nothing(
    cause: str, tmp_path: Path
) -> None:
    with closing(_prepared(tmp_path)) as c:
        with pytest.raises((StoreConflict, StoreUnusable)), write_transaction(c):
            c.execute("INSERT INTO note(body) VALUES ('a')")
            try:
                _CAUSES[cause](c)
            finally:
                c.execute("INSERT INTO note(body) VALUES ('b')")
        assert _rows(c) == []


@pytest.mark.parametrize("raise_after", [False, True], ids=["quiet", "raising"])
def test_a_body_that_closes_the_connection_leaves_a_typed_error(
    raise_after: bool, tmp_path: Path
) -> None:
    connection = _connect(tmp_path)
    connection.execute("CREATE TABLE t(x)")
    expected = RuntimeError if raise_after else StoreUnusable
    with pytest.raises(expected) as caught, write_transaction(connection):
        connection.close()
        if raise_after:
            raise RuntimeError("body")
    if raise_after:
        assert any("rollback failed" in note for note in caught.value.__notes__)


def test_a_commit_blocked_by_a_readers_lock_is_busy_and_nothing_is_written(tmp_path: Path) -> None:
    with _database(tmp_path, 1) as connection, closing(_connect(tmp_path)) as reader:
        reader.execute("BEGIN")
        reader.execute("SELECT count(*) FROM note").fetchall()
        with pytest.raises(StoreBusy), write_transaction(connection):
            connection.execute("INSERT INTO note(body) VALUES ('lost')")
        assert not connection.in_transaction
        reader.execute("ROLLBACK")
        assert connection.execute("SELECT count(*) FROM note").fetchall() == [(0,)]
        with write_transaction(connection):
            connection.execute("INSERT INTO note(body) VALUES ('kept')")


def test_a_busy_begin_is_store_busy_and_the_body_does_not_run(tmp_path: Path) -> None:
    with _database(tmp_path, 1) as connection, closing(_connect(tmp_path)) as holder:
        holder.execute("BEGIN IMMEDIATE")
        with pytest.raises(StoreBusy), write_transaction(connection):
            pytest.fail("the body must not run")
        holder.execute("ROLLBACK")


class _RollbackFails(sqlite3.Connection):
    def execute(self, sql: str, *args: Any) -> sqlite3.Cursor:
        if sql == "ROLLBACK":
            raise sqlite3.OperationalError("injected rollback failure")
        return super().execute(sql, *args)


def test_a_failed_rollback_is_noted_on_the_leaving_error_and_its_cause(tmp_path: Path) -> None:
    with closing(_connect(tmp_path, factory=_RollbackFails)) as connection:
        connection.execute("CREATE TABLE t(x INTEGER NOT NULL)")
        with pytest.raises(StoreConflict) as caught, write_transaction(connection):
            connection.execute("INSERT INTO t VALUES (NULL)")
        for error in (caught.value, caught.value.__cause__):
            assert error is not None
            assert any("rollback failed" in note for note in error.__notes__)
        sqlite3.Connection.execute(connection, "ROLLBACK")  # the real one, past the injection
        with pytest.raises(RuntimeError) as plain, write_transaction(connection):
            raise RuntimeError("original")
        assert any("rollback failed" in note for note in plain.value.__notes__)


def test_every_statement_failure_outside_the_listed_ones_is_a_store_error(tmp_path: Path) -> None:
    with _database(tmp_path, 1) as connection, pytest.raises(StoreError):
        migrate(connection, (key.M1, ("SELECT * FROM missing", "PRAGMA user_version = 2")))


def test_quick_check_is_allowed_in_a_migration_only_with_its_table_argument(tmp_path: Path) -> None:
    version_line = "PRAGMA user_version = 2"
    with _database(tmp_path, 1) as connection:
        with pytest.raises(StoreUnusable):
            migrate(connection, (key.M1, ("PRAGMA quick_check", version_line)))
        migrate(connection, (key.M1, ("PRAGMA quick_check(note)", version_line)))
        assert _snapshot(connection)[0] == [(2,)]


def _state_rows(folder: Path) -> list[tuple[Any, ...]]:
    with closing(_connect(folder)) as reader:
        return reader.execute("SELECT x FROM t ORDER BY x").fetchall()


def test_an_interrupt_inside_a_body_statement_leaves_as_store_unusable_and_commits_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    real_stop = txn._stop_outside
    armed: list[bool] = []

    def interrupting(connection: sqlite3.Connection) -> Callable[[], int]:
        real = real_stop(connection)

        def stop() -> int:
            if armed:
                armed.clear()
                raise KeyboardInterrupt  # what a signal handler raises, delivered in the handler
            return real()

        return stop

    monkeypatch.setattr(txn, "_stop_outside", interrupting)
    with closing(_connect(tmp_path)) as connection:
        connection.execute("CREATE TABLE t(x INTEGER)")
        with (
            pytest.raises((StoreUnusable, KeyboardInterrupt)) as caught,
            write_transaction(connection),
        ):
            connection.execute("INSERT INTO t VALUES (1)")
            armed.append(True)
            connection.execute("INSERT INTO t VALUES (2)")
        assert type(caught.value).__name__ == key.INTERRUPTED_ERROR
        assert str(caught.value) == key.INTERRUPTED_MESSAGE
        assert _state_rows(tmp_path) == key.INTERRUPTED_ROWS
        assert not connection.in_transaction
        connection.execute("INSERT INTO t VALUES (3)")
        assert _state_rows(tmp_path) == [(3,)]


def test_a_progress_handler_that_cannot_be_removed_still_lets_the_authorizer_go(
    tmp_path: Path,
) -> None:
    class NoClear(sqlite3.Connection):
        failing = True

        def set_progress_handler(
            self, progress_handler: Callable[[], int | None] | None, n: int
        ) -> None:
            if progress_handler is None and self.failing:
                self.failing = False
                raise sqlite3.ProgrammingError("injected clear failure")
            super().set_progress_handler(progress_handler, n)

    with closing(_connect(tmp_path, factory=NoClear)) as connection:
        connection.execute("CREATE TABLE t(x INTEGER)")
        with pytest.raises(StoreUnusable) as caught, write_transaction(connection):
            connection.execute("INSERT INTO t VALUES (1)")
        assert any(
            note.startswith(key.CLEAR_PROGRESS_NOTE_PREFIX + "injected clear failure")
            for note in caught.value.__notes__
        )
        assert connection.in_transaction is key.CLEAR_PROGRESS_LEFT_OPEN
        assert _state_rows(tmp_path) == key.CLEAR_PROGRESS_ROWS
        connection.set_progress_handler(None, 1)
        connection.execute("BEGIN")
        connection.execute("ROLLBACK")
