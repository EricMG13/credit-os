import inspect
import os
import sqlite3
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest
import store_open_key as key
import store_txn_key as txn_key

from credit_os.store import db, location
from credit_os.store.db import Store, open_reader, open_store
from credit_os.store.errors import (
    StoreBusy,
    StoreCorrupt,
    StoreError,
    StoreRefused,
    StoreUnusable,
)

Patch = pytest.MonkeyPatch
Lists = tuple[tuple[str, ...], ...]
M1, M2, M3 = txn_key.M1, txn_key.M2, txn_key.M3
OPENERS: list[Callable[..., Any]] = [open_store, open_reader]


def _file(folder: Path) -> Path:
    return folder / location.STATE_FILE_NAME


def _raw(folder: Path) -> sqlite3.Connection:
    return sqlite3.connect(_file(folder), autocommit=True)


def _rows(folder: Path, sql: str) -> list[tuple[Any, ...]]:
    with closing(_raw(folder)) as connection:
        return connection.execute(sql).fetchall()


def _store_at(folder: Path, migrations: Lists) -> Path:
    open_store(folder, migrations=migrations).close()
    return folder


def _both_raise(error: type[Exception], folder: Path, **kwargs: Any) -> None:
    for opener in OPENERS:
        with pytest.raises(error):
            opener(folder, **kwargs)


def _make_wal(folder: Path) -> None:
    with closing(_raw(folder)) as connection:
        assert connection.execute("PRAGMA journal_mode=WAL").fetchall() == [("wal",)]


def test_a_fresh_store_has_the_id_and_a_delete_journal_and_reopening_changes_nothing(
    tmp_path: Path,
) -> None:
    folder = _store_at(tmp_path / "state", (M1,))
    before = _file(folder).read_bytes()
    open_store(folder, migrations=(M1,)).close()
    assert _file(folder).read_bytes() == before
    assert db.APPLICATION_ID == key.APPLICATION_ID
    assert _rows(folder, "PRAGMA application_id") == [(key.APPLICATION_ID,)]
    assert _rows(folder, "PRAGMA journal_mode") == [(key.JOURNAL_MODE,)]


def test_a_library_below_the_minimum_or_not_threadsafe_is_unusable_and_nothing_is_created(
    monkeypatch: Patch, tmp_path: Path
) -> None:
    for name, bad in (("sqlite_version_info", (3, 36, 9)), ("threadsafety", 1)):
        with monkeypatch.context() as patch:
            patch.setattr(sqlite3, name, bad)
            _both_raise(StoreUnusable, tmp_path / "state")
    assert list(tmp_path.iterdir()) == []
    monkeypatch.setattr(sqlite3, "sqlite_version_info", key.MINIMUM_SQLITE)
    monkeypatch.setattr(sqlite3, "threadsafety", key.REQUIRED_THREADSAFETY)
    open_store(tmp_path / "state").close()


@pytest.mark.parametrize(
    ("name", "bad", "words"), key.READER_BAD_LIBRARIES, ids=[r[0] for r in key.READER_BAD_LIBRARIES]
)
def test_a_bad_library_refuses_the_reader_of_a_current_store_and_the_bytes_stay(
    name: str, bad: object, words: str, monkeypatch: Patch, tmp_path: Path
) -> None:
    folder = _store_at(tmp_path / "state", (M1,))
    before = _file(folder).read_bytes()
    monkeypatch.setattr(sqlite3, name, bad)
    with pytest.raises(StoreUnusable, match=words):
        open_reader(folder, migrations=(M1,))
    assert _file(folder).read_bytes() == before


def test_a_reader_journal_mode_read_back_other_than_delete_is_unusable_and_closed(
    monkeypatch: Patch, tmp_path: Path
) -> None:
    folder = _store_at(tmp_path / "state", (M1,))
    made: list[sqlite3.Connection] = []

    class ReadBack(sqlite3.Connection):
        def execute(self, statement: str, *args: Any) -> sqlite3.Cursor:
            if statement == "PRAGMA journal_mode":
                return super().execute(f"SELECT {key.READER_JOURNAL_READ_BACK!r}")
            return super().execute(statement, *args)

    real = sqlite3.connect

    def spy(*args: Any, **kwargs: Any) -> sqlite3.Connection:
        made.append(real(*args, factory=ReadBack, **kwargs))
        return made[-1]

    monkeypatch.setattr(sqlite3, "connect", spy)
    with pytest.raises(StoreUnusable) as caught:
        open_reader(folder, migrations=(M1,))
    assert str(caught.value) == key.READER_JOURNAL_MESSAGE
    assert len(made) == 1
    with pytest.raises(sqlite3.ProgrammingError):
        made[0].execute("SELECT 1")


def test_a_journal_step_error_with_no_sqlite_code_is_unusable_and_names_the_step(
    monkeypatch: Patch, tmp_path: Path
) -> None:
    class NoCode(sqlite3.Connection):
        def execute(self, statement: str, *args: Any) -> sqlite3.Cursor:
            if statement == "PRAGMA journal_mode=DELETE":
                raise sqlite3.ProgrammingError(key.CODELESS_JOURNAL_ERROR_TEXT)
            return super().execute(statement, *args)

    real = sqlite3.connect
    monkeypatch.setattr(sqlite3, "connect", lambda *a, **k: real(*a, factory=NoCode, **k))
    with pytest.raises(StoreUnusable) as caught:
        open_store(tmp_path / "state")
    assert str(caught.value) == key.CODELESS_JOURNAL_MESSAGE


def test_a_close_failure_is_mapped_by_its_code_and_keeps_sqlites_text(
    monkeypatch: Patch, tmp_path: Path
) -> None:
    injected = sqlite3.DatabaseError(key.CLOSE_ERROR_TEXT)
    injected.sqlite_errorcode = key.CLOSE_ERROR_CODE

    class CorruptClose(sqlite3.Connection):
        def close(self) -> None:
            super().close()
            raise injected

    real = sqlite3.connect
    monkeypatch.setattr(sqlite3, "connect", lambda *a, **k: real(*a, factory=CorruptClose, **k))
    store = open_store(tmp_path / "state")
    with pytest.raises(StoreError) as caught:
        store.close()
    assert type(caught.value).__name__ == key.CLOSE_ERROR_CLASS
    assert str(caught.value) == key.CLOSE_ERROR_MESSAGE
    assert caught.value.__cause__ is injected


def _two_threads(
    tmp_path: Path, holder_row: str, second: Callable[[Store], None]
) -> tuple[Path, list[str]]:
    """Thread A holds `_write()` with one row; thread B, once A is inside, runs `second`."""
    folder = tmp_path / "state"
    store = open_store(folder, migrations=(M1,))
    inside = threading.Event()
    errors: list[str] = []

    def other() -> None:
        inside.wait(10)
        try:
            second(store)
        except (StoreError, sqlite3.Error) as error:
            errors.append(f"second: {type(error).__name__}: {error}")

    def holder() -> None:
        try:
            with store._write() as connection:
                connection.execute("INSERT INTO note(body) VALUES (?)", (holder_row,))
                inside.set()
                time.sleep(0.3)
        except (StoreError, sqlite3.Error) as error:
            errors.append(f"first: {type(error).__name__}: {error}")

    threads = [threading.Thread(target=holder), threading.Thread(target=other)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
    assert not any(thread.is_alive() for thread in threads)
    store.close()
    return folder, errors


def test_a_second_write_waits_for_the_first_on_the_store_lock(tmp_path: Path) -> None:
    def write(store: Store) -> None:
        with store._write() as connection:
            connection.execute("INSERT INTO note(body) VALUES ('second')")

    folder, errors = _two_threads(tmp_path, "first", write)
    assert errors == []
    found = sorted(row[0] for row in _rows(folder, "SELECT body FROM note"))
    assert found == sorted(key.LOCK_WRITE_ROWS)


def test_a_close_waits_for_a_write_in_flight_on_the_store_lock(tmp_path: Path) -> None:
    folder, errors = _two_threads(tmp_path, "kept", lambda store: store.close())
    assert errors == []
    found = [row[0] for row in _rows(folder, "SELECT body FROM note")]
    assert found == list(key.LOCK_CLOSE_ROWS)


def test_the_default_wait_is_the_keys() -> None:
    for opener in OPENERS:
        assert (
            inspect.signature(opener).parameters["busy_seconds"].default == key.DEFAULT_BUSY_SECONDS
        )


@pytest.mark.parametrize(
    "seconds",
    key.REFUSED_BUSY_SECONDS,
    ids=[f"row{i}" for i in range(len(key.REFUSED_BUSY_SECONDS))],
)
def test_a_refused_busy_seconds_creates_nothing(seconds: object, tmp_path: Path) -> None:
    _both_raise(StoreRefused, tmp_path / "state", busy_seconds=seconds)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("seconds", key.ACCEPTED_BUSY_SECONDS, ids=repr)
def test_an_accepted_busy_seconds_opens(seconds: float, tmp_path: Path) -> None:
    open_store(tmp_path / "state", busy_seconds=seconds).close()
    open_reader(tmp_path / "state", busy_seconds=seconds).close()


def test_a_bad_migration_list_is_refused_before_anything_is_created(tmp_path: Path) -> None:
    for migrations in txn_key.REFUSED_MIGRATION_LISTS:
        _both_raise(StoreRefused, tmp_path / "state", migrations=migrations)
    assert list(tmp_path.iterdir()) == []


def test_a_newer_schema_is_unusable_and_the_bytes_stay(tmp_path: Path) -> None:
    folder = _store_at(tmp_path / "state", (M1, M2))
    before = _file(folder).read_bytes()
    with pytest.raises(StoreUnusable):
        open_store(folder, migrations=(M1,))
    assert _file(folder).read_bytes() == before


@pytest.mark.parametrize("application_id", [0, 7])
def test_another_applications_file_is_unusable_and_the_bytes_stay(
    application_id: int, tmp_path: Path
) -> None:
    with closing(_raw(tmp_path)) as connection:
        connection.execute("CREATE TABLE other(x)")
        connection.execute(f"PRAGMA application_id = {application_id}")
    before = _file(tmp_path).read_bytes()
    _both_raise(StoreUnusable, tmp_path)
    assert _file(tmp_path).read_bytes() == before


@pytest.mark.parametrize("version", key.REFUSED_VERSIONS)
@pytest.mark.parametrize("count", [0, 3])
def test_a_version_outside_32_bit_range_of_the_list_is_unusable_for_any_list(
    version: int, count: int, tmp_path: Path
) -> None:
    _store_at(tmp_path, ())
    _rows(tmp_path, f"PRAGMA user_version = {version}")
    before = _file(tmp_path).read_bytes()
    _both_raise(StoreUnusable, tmp_path, migrations=(M1, M2, M3)[:count])
    assert _file(tmp_path).read_bytes() == before


def test_non_database_bytes_are_corrupt_and_the_bytes_stay(tmp_path: Path) -> None:
    _file(tmp_path).write_bytes(b"this is not a database " * 200)
    before = _file(tmp_path).read_bytes()
    with pytest.raises(StoreCorrupt):
        open_store(tmp_path)
    assert _file(tmp_path).read_bytes() == before


_CHILD = r"""
import os, sqlite3, sys
c = sqlite3.connect(sys.argv[1], autocommit=True)
c.execute("PRAGMA journal_mode=WAL")
c.execute("PRAGMA wal_autocheckpoint=0")
c.execute("CREATE TABLE other(x)")
c.execute("INSERT INTO other VALUES (1)")
c.execute("PRAGMA application_id = " + sys.argv[2])
c.execute("PRAGMA user_version = " + sys.argv[3])
os._exit(0)
"""


@pytest.mark.parametrize(("application_id", "version"), [(7, 0), (key.APPLICATION_ID, 5)])
def test_a_refused_write_ahead_file_keeps_its_bytes_and_its_wal(
    application_id: int, version: int, tmp_path: Path
) -> None:
    # The child exits without a checkpoint, as after a crash: the frames stay in the -wal file.
    args = [sys.executable, "-c", _CHILD, str(_file(tmp_path)), str(application_id), str(version)]
    subprocess.run(args, check=True)
    wal = tmp_path / (location.STATE_FILE_NAME + "-wal")
    before = (_file(tmp_path).read_bytes(), wal.read_bytes())
    with pytest.raises(StoreUnusable):
        open_store(tmp_path, migrations=())
    assert (_file(tmp_path).read_bytes(), wal.read_bytes()) == before


def test_a_held_write_ahead_file_is_unusable_and_a_free_one_is_converted(tmp_path: Path) -> None:
    folder = _store_at(tmp_path / "state", (M1,))
    _make_wal(folder)
    with closing(_raw(folder)) as holder:
        holder.execute("BEGIN")
        holder.execute("SELECT count(*) FROM note").fetchall()
        with pytest.raises(StoreUnusable) as caught:
            open_store(folder, busy_seconds=0.2, migrations=(M1,))
        assert not isinstance(caught.value, StoreBusy)
        holder.execute("ROLLBACK")
    open_store(folder, migrations=(M1,)).close()
    assert _rows(folder, "PRAGMA journal_mode") == [(key.JOURNAL_MODE,)]


def test_the_stores_connection_has_its_pragmas_autocommit_and_foreign_keys(tmp_path: Path) -> None:
    # Reads the store's private connection: these are per connection.
    with open_store(tmp_path, migrations=(M1, M2, M3)) as store:
        connection = store._live()
        assert connection.autocommit is True
        assert connection.execute("PRAGMA synchronous").fetchall() == [(key.SYNCHRONOUS_FULL,)]
        assert connection.execute("PRAGMA foreign_keys").fetchall() == [(key.FOREIGN_KEYS_ON,)]
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO reply(note_id) VALUES (99)")


def _inject(
    monkeypatch: Patch, sql: str, replace: str | None, code: int = 0, part: bool = False
) -> None:

    class Injected(sqlite3.Connection):
        def execute(self, statement: str, *args: Any) -> sqlite3.Cursor:
            if statement != sql and not (part and sql in statement):
                return super().execute(statement, *args)
            if replace is not None:
                return super().execute(replace)
            error = sqlite3.OperationalError("injected")
            error.sqlite_errorcode = code
            raise error

    real = sqlite3.connect
    monkeypatch.setattr(sqlite3, "connect", lambda *a, **k: real(*a, factory=Injected, **k))


_STEPS = [  # (statement part, step named in the error, opener)
    ("pragma_application_id", "read the file identity", open_store),
    ("journal_mode=DELETE", "set the journal mode", open_store),
    ("synchronous=FULL", "set the connection pragmas", open_store),
    ("PRAGMA quick_check", "check the file", open_store),
    ("PRAGMA user_version", "read the schema version", open_store),
    ("PRAGMA journal_mode", "read the journal mode", open_reader),
]


@pytest.mark.parametrize(("part", "step", "opener"), _STEPS, ids=[s[1] for s in _STEPS])
def test_a_sqlite_error_at_each_step_is_mapped_and_names_the_step(
    part: str, step: str, opener: Any, monkeypatch: Patch, tmp_path: Path
) -> None:
    folder = _store_at(tmp_path / "state", (M1,))
    _inject(monkeypatch, part, None, code=11, part=True)
    with pytest.raises(StoreCorrupt, match=step):
        opener(folder, migrations=(M1,))


def test_a_connect_failure_and_a_close_failure_are_mapped(
    monkeypatch: Patch, tmp_path: Path
) -> None:
    class Noisy(sqlite3.Connection):
        def close(self) -> None:
            super().close()
            raise sqlite3.DatabaseError("injected")

    real = sqlite3.connect
    monkeypatch.setattr(sqlite3, "connect", lambda *a, **k: real(*a, factory=Noisy, **k))
    store = open_store(tmp_path / "state")
    with pytest.raises(StoreUnusable, match="close the store"):
        store.close()
    monkeypatch.undo()
    refused = sqlite3.DatabaseError("injected")
    refused.sqlite_errorcode = 11

    def refuse(*args: Any, **kwargs: Any) -> None:
        raise refused

    monkeypatch.setattr(sqlite3, "connect", refuse)
    with pytest.raises(StoreCorrupt, match="connect to the state file"):
        open_store(tmp_path / "state")


_READ_BACK_SQL = {
    "journal_mode": "PRAGMA journal_mode=DELETE",
    "synchronous": "PRAGMA synchronous",
    "foreign_keys": "PRAGMA foreign_keys",
}


@pytest.mark.parametrize("pragma", list(key.BAD_READ_BACKS))
def test_a_pragma_that_reads_back_wrong_is_unusable(
    pragma: str, monkeypatch: Patch, tmp_path: Path
) -> None:
    value = key.BAD_READ_BACKS[pragma]
    _inject(monkeypatch, _READ_BACK_SQL[pragma], f"SELECT {value!r}")
    with pytest.raises(StoreUnusable):
        open_store(tmp_path / "state")


@pytest.mark.parametrize(
    ("code", "error"), [(26, StoreCorrupt), (6, StoreUnusable), (5, StoreUnusable)]
)
def test_a_journal_mode_error_is_mapped_by_its_code(
    code: int, error: type[Exception], monkeypatch: Patch, tmp_path: Path
) -> None:
    _inject(monkeypatch, "PRAGMA journal_mode=DELETE", None, code)
    with pytest.raises(error) as caught:
        open_store(tmp_path / "state")
    assert type(caught.value) is error


def test_quick_check_rows_that_are_not_ok_are_corrupt(tmp_path: Path) -> None:
    folder = _store_at(tmp_path / "state", (M1,))
    loose = "CREATE TABLE note(id INTEGER PRIMARY KEY, body TEXT) STRICT"
    for sql_in, sql_out in ((M1[0], loose), (loose, M1[0])):
        with closing(_raw(folder)) as connection:
            if sql_in == loose:
                connection.execute("INSERT INTO note(body) VALUES (NULL)")
            connection.execute("PRAGMA writable_schema=ON")
            connection.execute("UPDATE sqlite_schema SET sql=? WHERE name='note'", (sql_out,))
    with closing(_raw(folder)) as connection:
        assert connection.execute("PRAGMA quick_check").fetchall() != [("ok",)]
    with pytest.raises(StoreCorrupt, match="integrity check"):
        open_store(folder, migrations=(M1,))


def test_a_damaged_page_is_corrupt(tmp_path: Path) -> None:
    folder = _store_at(tmp_path / "state", (M1,))
    with closing(_raw(folder)) as connection:
        connection.execute("INSERT INTO note(body) VALUES ('a')")
    with _file(folder).open("r+b") as handle:  # page 2 (4096-byte pages) holds `note`
        handle.seek(4096)
        handle.write(b"\xff" * 64)
    with pytest.raises(StoreCorrupt):
        open_store(folder, migrations=(M1,))


def test_a_held_lock_is_busy_within_the_wait_and_nothing_is_written(tmp_path: Path) -> None:
    folder = _store_at(tmp_path / "state", (M1,))
    before = _file(folder).read_bytes()
    with closing(_raw(folder)) as holder:
        holder.execute("BEGIN IMMEDIATE")
        start = time.monotonic()
        with pytest.raises(StoreBusy):
            open_store(folder, busy_seconds=0.2, migrations=(M1, M2))
        assert time.monotonic() - start < 3  # the wait is busy_seconds, not SQLite's 5 s
        holder.execute("ROLLBACK")
    assert _file(folder).read_bytes() == before
    open_store(folder, migrations=(M1, M2)).close()
    assert _rows(folder, "PRAGMA user_version") == [(2,)]


def test_a_failed_open_closes_its_connection(monkeypatch: Patch, tmp_path: Path) -> None:
    made: list[sqlite3.Connection] = []
    real = sqlite3.connect

    def spy(*args: Any, **kwargs: Any) -> sqlite3.Connection:
        made.append(real(*args, **kwargs))
        return made[-1]

    folder = _store_at(tmp_path / "state", (M1, M2))
    monkeypatch.setattr(sqlite3, "connect", spy)
    for opener in OPENERS:
        with pytest.raises(StoreUnusable):
            opener(folder, migrations=(M1,))
    assert len(made) == 2
    for connection in made:
        with pytest.raises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")


def test_the_reader_opens_a_current_store_cannot_write_and_changes_no_byte(tmp_path: Path) -> None:
    folder = _store_at(tmp_path / "state", (M1, M2))
    before = _file(folder).read_bytes()
    with open_reader(folder, migrations=(M1, M2)) as reader:
        write = reader._live().execute
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            write("CREATE TABLE x(y)")
    for older_or_newer in ((M1,), (M1, M2, M3)):
        with pytest.raises(StoreUnusable):
            open_reader(folder, migrations=older_or_newer)
    assert _file(folder).read_bytes() == before


def test_close_twice_use_after_close_and_the_context_managers(tmp_path: Path) -> None:
    store = open_store(tmp_path)
    store.close()
    store.close()
    with pytest.raises(StoreUnusable), store._write():  # private helper, reached on purpose
        pass
    with open_store(tmp_path) as again, open_reader(tmp_path) as reader:
        pass
    for handle in (again, reader):
        with pytest.raises(StoreUnusable):
            handle._live()
        handle.close()


def test_one_write_transaction_from_one_other_thread_works(tmp_path: Path) -> None:
    errors: list[BaseException] = []

    def write(store: Any) -> None:
        try:
            with store._write() as connection:
                connection.execute("INSERT INTO note(body) VALUES ('from a thread')")
        except StoreUnusable as error:
            errors.append(error)

    with open_store(tmp_path, migrations=(M1,)) as store:
        thread = threading.Thread(target=write, args=(store,))
        thread.start()
        thread.join(timeout=60)
    assert errors == []
    assert _rows(tmp_path, "SELECT body FROM note") == [("from a thread",)]


def test_two_threads_opening_the_same_fresh_folder_migrate_once(tmp_path: Path) -> None:
    results: list[str] = []

    def opener() -> None:
        try:
            open_store(tmp_path / "state", migrations=(M1, M2)).close()
            results.append("opened")
        except StoreUnusable as error:
            results.append(str(error))

    threads = [threading.Thread(target=opener) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert results == ["opened", "opened"]
    assert _rows(tmp_path / "state", "PRAGMA user_version") == [(2,)]


def _stamp_race(monkeypatch: Patch, action: Callable[[], None]) -> None:
    real = db._quick_check
    done: list[bool] = []

    def placed(connection: sqlite3.Connection) -> None:
        real(connection)
        if not done:
            done.append(True)
            action()

    monkeypatch.setattr(db, "_quick_check", placed)


def test_the_stamp_rechecks_the_identity_against_a_newer_opener_and_another_program(
    monkeypatch: Patch, tmp_path: Path
) -> None:
    newer, theirs = tmp_path / "newer", tmp_path / "theirs"
    _stamp_race(monkeypatch, lambda: open_store(newer, migrations=(M1, M2)).close())
    with pytest.raises(StoreUnusable):
        open_store(newer, migrations=(M1,))
    assert _rows(newer, "PRAGMA user_version") == [(2,)]
    monkeypatch.undo()

    def other_program() -> None:
        with closing(_raw(theirs)) as connection:
            connection.execute("CREATE TABLE theirs(x)")

    _stamp_race(monkeypatch, other_program)
    with pytest.raises(StoreUnusable):
        open_store(theirs, migrations=(M1,))
    assert _rows(theirs, "PRAGMA application_id") == [(0,)]


_WAL_CHILD = r"""
import os, sqlite3, sys
c = sqlite3.connect(sys.argv[1], autocommit=True)
c.execute("PRAGMA journal_mode=WAL")
c.execute("PRAGMA wal_autocheckpoint=0")
c.execute("INSERT INTO note(body) VALUES ('in the wal')")
os._exit(0)
"""


def test_a_corrupt_write_ahead_file_is_corrupt_and_its_bytes_and_wal_stay(tmp_path: Path) -> None:
    folder = _store_at(tmp_path / "state", (M1,))
    loose = "CREATE TABLE note(id INTEGER PRIMARY KEY, body TEXT) STRICT"
    for after_sql, row in ((loose, False), (M1[0], True)):
        with closing(_raw(folder)) as connection:
            if row:
                connection.execute("INSERT INTO note(body) VALUES (NULL)")
            connection.execute("PRAGMA writable_schema=ON")
            connection.execute("UPDATE sqlite_schema SET sql=? WHERE name='note'", (after_sql,))
    subprocess.run([sys.executable, "-c", _WAL_CHILD, str(_file(folder))], check=True)
    wal = folder / (location.STATE_FILE_NAME + "-wal")
    before = (_file(folder).read_bytes(), wal.read_bytes())
    with pytest.raises(StoreCorrupt, match="integrity"):
        open_store(folder, migrations=(M1,))
    assert (_file(folder).read_bytes(), wal.read_bytes()) == before


def test_a_failing_setconfig_is_mapped_and_closes_the_connection(
    monkeypatch: Patch, tmp_path: Path
) -> None:
    made: list[sqlite3.Connection] = []
    real = sqlite3.connect

    class NoConfig(sqlite3.Connection):
        def setconfig(self, op: int, enable: bool = True, /) -> bool:
            error = sqlite3.DatabaseError("injected")
            error.sqlite_errorcode = 11
            raise error

    def spy(*args: Any, **kwargs: Any) -> sqlite3.Connection:
        made.append(real(*args, factory=NoConfig, **kwargs))
        return made[-1]

    monkeypatch.setattr(sqlite3, "connect", spy)
    with pytest.raises(StoreCorrupt, match="configure the connection"):
        open_store(tmp_path / "state")
    with pytest.raises(sqlite3.ProgrammingError):
        made[0].execute("SELECT 1")


def test_the_maximum_wait_is_the_keys(tmp_path: Path) -> None:
    open_store(tmp_path / "state", busy_seconds=key.MAXIMUM_BUSY_SECONDS).close()
    _both_raise(StoreRefused, tmp_path / "state", busy_seconds=key.MAXIMUM_BUSY_SECONDS + 1)


@pytest.mark.skipif(
    sys.platform == "win32" or not hasattr(os, "geteuid") or os.geteuid() == 0,
    reason="POSIX modes; root can write",
)
def test_a_denial_the_writable_check_cannot_see_fails_at_the_first_write(
    monkeypatch: Patch, tmp_path: Path
) -> None:
    folder = _store_at(tmp_path / "state", ())
    _file(folder).chmod(key.UNSEEN_DENIAL_FILE_MODE)
    try:
        monkeypatch.setattr(os, "access", lambda *args, **kwargs: True)
        before = _file(folder).read_bytes()
        with pytest.raises(Exception) as raised:
            open_store(folder, migrations=(M1,))
        assert type(raised.value).__name__ == key.UNSEEN_DENIAL_ERROR
        assert getattr(raised.value.__cause__, "sqlite_errorcode", 0) == key.UNSEEN_DENIAL_CODE
        assert _file(folder).read_bytes() == before
    finally:
        _file(folder).chmod(0o600)
