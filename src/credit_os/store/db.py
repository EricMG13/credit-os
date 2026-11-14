"""The only code that holds the run-state connection: library check, connect, identity, pragmas,
integrity check, stamp, and the two handles. Paths come from `location`, the write transaction
and migrations from `txn`. Every SQL string here is a static literal."""

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Self

from credit_os.store import location, txn
from credit_os.store.errors import (
    StoreCorrupt,
    StoreRefused,
    StoreUnusable,
    safe_text,
    store_error,
)
from credit_os.store.txn import Migration

APPLICATION_ID = 1129467731
MIGRATIONS: tuple[Migration, ...] = ()
_MAXIMUM_BUSY_SECONDS = 3600


class _Handle:
    """A connection and the lock that guards it; closing is safe to repeat."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection: sqlite3.Connection | None = connection
        self._lock = threading.Lock()

    def _live(self) -> sqlite3.Connection:
        if self._connection is None:
            raise StoreUnusable("the store is closed")
        return self._connection

    def close(self) -> None:
        with self._lock:
            connection, self._connection = self._connection, None
            if connection is not None:
                try:
                    connection.close()
                except sqlite3.Error as error:
                    raise store_error(error, "close the store") from error

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class StoreReader(_Handle):
    """A read-only handle; it never writes and never migrates."""


class Store(_Handle):
    @contextmanager
    def _write(self) -> Iterator[sqlite3.Connection]:
        """Take the lock and run one write transaction. The lock is not re-entrant: a method
        that calls another method, or `close()`, inside a transaction deadlocks."""
        with self._lock, txn.write_transaction(self._live()) as connection:
            yield connection


def _check_library() -> None:
    if sqlite3.sqlite_version_info < (3, 37, 0):
        raise StoreUnusable(f"SQLite {sqlite3.sqlite_version} is older than 3.37.0")
    if sqlite3.threadsafety != 3:
        raise StoreUnusable("this SQLite is not built for use from several threads")


def _check_busy_seconds(busy_seconds: object) -> None:
    """A real number above 0 and at most an hour; `nan`, `inf`, a bool, a str and a huge int fail."""
    if isinstance(busy_seconds, int | float) and not isinstance(busy_seconds, bool):
        try:
            if 0 < float(busy_seconds) <= _MAXIMUM_BUSY_SECONDS:
                return
        except OverflowError:
            pass  # an int too large for a float: refused below
    raise StoreRefused(f"busy_seconds must be above 0 and at most {_MAXIMUM_BUSY_SECONDS}")


def _connect(path: Path, mode: str, busy_seconds: float) -> sqlite3.Connection:
    uri = path.as_uri() + "?mode=" + mode
    try:
        return sqlite3.connect(
            uri, uri=True, autocommit=True, timeout=busy_seconds, check_same_thread=False
        )
    except sqlite3.Error as error:
        raise store_error(error, "connect to the state file") from error


def _read_identity(connection: sqlite3.Connection) -> tuple[int, int, bool]:
    """Application id, version, fresh (all zero, no schema rows); one statement, one snapshot."""
    try:
        row = connection.execute(
            "SELECT (SELECT application_id FROM pragma_application_id),"
            " (SELECT user_version FROM pragma_user_version),"
            " (SELECT count(*) FROM sqlite_schema)"
        ).fetchall()[0]
    except sqlite3.Error as error:
        raise store_error(error, "read the file identity") from error
    application_id, version, rows = (int(value) for value in row)
    return application_id, version, application_id == 0 and version == 0 and rows == 0


def _check_identity(identity: tuple[int, int, bool], migrations: tuple[Migration, ...]) -> None:
    application_id, version, fresh = identity
    if not fresh and application_id != APPLICATION_ID:
        raise StoreUnusable("the file belongs to another application")
    if not 0 <= version <= len(migrations):
        raise StoreUnusable(f"the file is at version {version}, outside this code's range")


def _set_pragmas(connection: sqlite3.Connection) -> None:
    try:
        journal = connection.execute("PRAGMA journal_mode=DELETE").fetchall()
    except sqlite3.Error as error:
        code = getattr(error, "sqlite_errorcode", None)
        if isinstance(code, int) and code & 0xFF in (5, 6):  # SQLITE_BUSY, SQLITE_LOCKED
            raise StoreUnusable(
                f"cannot leave write-ahead mode: {safe_text(str(error))}"
            ) from error
        raise store_error(error, "set the journal mode") from error
    try:
        connection.execute("PRAGMA synchronous=FULL")
        synchronous = connection.execute("PRAGMA synchronous").fetchall()
        connection.execute("PRAGMA foreign_keys=ON")
        keys = connection.execute("PRAGMA foreign_keys").fetchall()
    except sqlite3.Error as error:
        raise store_error(error, "set the connection pragmas") from error
    if journal != [("delete",)] or synchronous != [(2,)] or keys != [(1,)]:
        raise StoreUnusable("a pragma did not take the required value")


def _quick_check(connection: sqlite3.Connection) -> None:
    try:
        rows = connection.execute("PRAGMA quick_check").fetchall()
    except sqlite3.Error as error:
        raise store_error(error, "check the file") from error
    if rows != [("ok",)]:
        raise StoreCorrupt("the file failed its integrity check")


def _stamp(store: Store, migrations: tuple[Migration, ...]) -> None:
    """In one write transaction re-read the identity (another opener may have won), then stamp."""
    with store._write() as connection:
        identity = _read_identity(connection)
        _check_identity(identity, migrations)
        if identity[2]:
            connection.execute("PRAGMA application_id = 1129467731")


def open_store(
    folder: Path, *, busy_seconds: float = 30.0, migrations: tuple[Migration, ...] = MIGRATIONS
) -> Store:
    """Open the writer, creating the folder and file when absent and migrating forward."""
    _check_library()
    _check_busy_seconds(busy_seconds)
    migrations = txn.check_migrations(migrations)
    store = Store(_connect(location.prepare(folder), "rw", busy_seconds))
    opened = False
    try:
        connection = store._live()
        # A refusing open must not checkpoint a write-ahead file's frames into the main file.
        try:
            connection.setconfig(sqlite3.SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE, True)
        except sqlite3.Error as error:
            raise store_error(error, "configure the connection") from error
        _check_identity(_read_identity(connection), migrations)
        _quick_check(connection)  # before the pragmas: they may rewrite a write-ahead file
        _set_pragmas(connection)
        _stamp(store, migrations)
        txn.migrate(connection, migrations)
        opened = True
        return store
    finally:
        if not opened:
            store.close()


def _check_reader(connection: sqlite3.Connection, migrations: tuple[Migration, ...]) -> None:
    application_id, version, _ = _read_identity(connection)
    if application_id != APPLICATION_ID:
        raise StoreUnusable("the file is not a credit-os store")
    if version != len(migrations):
        raise StoreUnusable(f"the file is at version {version}, not {len(migrations)}")
    try:
        journal = connection.execute("PRAGMA journal_mode").fetchall()
    except sqlite3.Error as error:
        raise store_error(error, "read the journal mode") from error
    if journal != [("delete",)]:
        raise StoreUnusable("the file is not in delete journal mode")


def open_reader(
    folder: Path, *, busy_seconds: float = 30.0, migrations: tuple[Migration, ...] = MIGRATIONS
) -> StoreReader:
    """Open a read-only handle on a current store; creates, writes and migrates nothing."""
    _check_library()
    _check_busy_seconds(busy_seconds)
    migrations = txn.check_migrations(migrations)
    reader = StoreReader(_connect(location.locate(folder), "ro", busy_seconds))
    opened = False
    try:
        _check_reader(reader._live(), migrations)
        opened = True
        return reader
    finally:
        if not opened:
            reader.close()
