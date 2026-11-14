"""The write transaction and the migration runner, on a connection handed in.

Every SQL string here is a static literal; a migration's statements are passed to `execute`
exactly as given.
"""

import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import NoReturn

from credit_os.store.errors import StoreError, StoreRefused, StoreUnusable, safe_text, store_error

Migration = tuple[str, ...]


def check_migrations(migrations: object) -> tuple[Migration, ...]:
    """Return the list when it is a tuple of tuples of str; anything else is StoreRefused."""
    if not isinstance(migrations, tuple) or not all(
        isinstance(migration, tuple) and all(isinstance(text, str) for text in migration)
        for migration in migrations
    ):
        raise StoreRefused("migrations must be a tuple of tuples of statements (str)")
    return migrations


def _note(error: BaseException, text: str) -> None:
    error.add_note(text)
    if error.__cause__ is not None:
        error.__cause__.add_note(text)


@contextmanager
def write_transaction(connection: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """BEGIN IMMEDIATE, yield, COMMIT; any exception rolls back and leaves (a SQLite error as its
    store error). While the body runs, an authorizer denies beginning or ending a transaction, and
    a progress handler stops every statement once SQLite has ended the transaction itself (ROLLBACK
    resolution, RAISE(ROLLBACK), FULL, INTERRUPT, IOERR, NOMEM), so nothing the body runs after that
    is committed: that statement leaves as StoreUnusable (SQLite reports it as interrupted), or as
    "ended inside its body" when the body swallowed the error. Only this module's
    `write_transaction`, `_clear_hooks` and `_run` set or clear these hooks.

    A documented fail-open: a KeyboardInterrupt, or another exception raised by a signal handler,
    that arrives while a body statement runs is delivered inside the progress handler or the
    authorizer, where Python's sqlite3 module clears it. The statement stops and leaves as
    `StoreUnusable: write transaction: interrupted` (or `... not authorized`); nothing is committed
    unless the body swallows the error and carries on: after an interrupted read its other writes
    commit and the interrupt is lost, so a body must never catch `sqlite3.Error`. A StoreUnusable
    from a write transaction may be an interrupt: a caller must treat it as ending its work, and
    never retry or swallow it."""
    try:
        connection.execute("BEGIN IMMEDIATE")
    except sqlite3.Error as error:
        raise store_error(error, "begin a write transaction") from error
    failure = ""
    try:
        try:
            connection.set_authorizer(_deny_transaction)
            connection.set_progress_handler(_stop_outside(connection), 1)
            yield connection
        finally:
            failure = _clear_hooks(connection)
        if failure:
            raise StoreUnusable("the connection was closed inside the write transaction")
        if not connection.in_transaction:
            raise StoreUnusable("the write transaction was ended inside its body")
        connection.execute("COMMIT")
    except BaseException as error:  # roll back and re-raise (a signal-handler exception inside a statement is the documented fail-open)
        failure = " ".join(text for text in (failure, _roll_back(connection)) if text)
        if isinstance(error, sqlite3.Error):
            _leave_mapped(error, failure)
        if failure:
            _note(error, failure)
        raise


def _stop_outside(connection: sqlite3.Connection) -> Callable[[], int]:
    """A progress handler (every VM step) that stops each statement once SQLite itself has ended the transaction."""

    def stop() -> int:
        return 0 if connection.in_transaction else 1

    return stop


def _clear_hooks(connection: sqlite3.Connection) -> str:
    """Remove the progress handler, then the authorizer, each on its own; return the failure texts or empty."""
    failures: list[str] = []
    try:
        connection.set_progress_handler(None, 1)
    except sqlite3.Error as error:
        failures.append(f"progress handler not removed: {safe_text(str(error))}")
    try:
        connection.set_authorizer(None)
    except sqlite3.Error as error:
        failures.append(f"authorizer not removed: {safe_text(str(error))}")
    return " ".join(failures)


def _roll_back(connection: sqlite3.Connection) -> str:
    """Roll back when a transaction is open; return the failure text, empty when it worked."""
    try:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
    except sqlite3.Error as rollback_error:
        return f"rollback failed: {safe_text(str(rollback_error))}"
    return ""


def _leave_mapped(error: sqlite3.Error, failure: str) -> NoReturn:
    """Raise the SQLite error as its store error, with a failed rollback noted on it."""
    try:
        raise store_error(error, "write transaction") from error
    except StoreError as mapped:
        if failure:
            _note(mapped, failure)
        raise


def _version(connection: sqlite3.Connection) -> int:
    try:
        return int(connection.execute("PRAGMA user_version").fetchall()[0][0])
    except sqlite3.Error as error:
        raise store_error(error, "read the schema version") from error


_TEMP_ACTIONS = frozenset(
    {
        sqlite3.SQLITE_CREATE_TEMP_INDEX,
        sqlite3.SQLITE_CREATE_TEMP_TABLE,
        sqlite3.SQLITE_CREATE_TEMP_TRIGGER,
        sqlite3.SQLITE_CREATE_TEMP_VIEW,
    }
)


def _deny_transaction(action: int, *_: object) -> int:
    """No write body may begin, commit, roll back or end a transaction."""
    return sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_TRANSACTION else sqlite3.SQLITE_OK


def _deny(action: int, arg1: str | None, arg2: str | None, *_: object) -> int:
    """A migration also may not attach a database, create a temporary object or touch a pragma
    other than its version line. `quick_check` with a table argument is allowed: SQLite itself
    runs `PRAGMA quick_check(<table>)` inside ALTER TABLE on a STRICT table, and it only reads."""
    if action == sqlite3.SQLITE_PRAGMA:
        name = (arg1 or "").lower()
        allowed = name == "user_version" or (name == "quick_check" and arg2 is not None)
        return sqlite3.SQLITE_OK if allowed else sqlite3.SQLITE_DENY
    denied = _TEMP_ACTIONS | {sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH}
    return sqlite3.SQLITE_DENY if action in denied else _deny_transaction(action)


def _run(connection: sqlite3.Connection, number: int, statements: Migration) -> None:
    """Run migration `number` unless the database is already at or past it."""
    with write_transaction(connection):
        found = _version(connection)
        if found >= number:
            return  # another opener ran it, and maybe more
        if found != number - 1:
            raise StoreUnusable(f"migration {number} found the database at version {found}")
        connection.set_authorizer(_deny)
        try:
            for statement in statements:
                if not statement.strip():
                    raise StoreUnusable(f"migration {number} holds an empty statement")
                connection.execute(statement)
        finally:
            connection.set_authorizer(_deny_transaction)
        if _version(connection) != number:
            raise StoreUnusable(f"migration {number} did not set the version to {number}")


def migrate(connection: sqlite3.Connection, migrations: tuple[Migration, ...]) -> None:
    """Run each migration the database has not had, in order, each in its own transaction."""
    version = _version(connection)  # a cheap early refusal; each migration re-reads in its own
    if not 0 <= version <= len(migrations):
        raise StoreUnusable("the database version is outside this code's migrations")
    for number, statements in enumerate(migrations, start=1):
        if version < number:
            _run(connection, number, statements)
            version = _version(connection)
            if version > len(migrations):
                raise StoreUnusable("the database was migrated past this code's migrations")
