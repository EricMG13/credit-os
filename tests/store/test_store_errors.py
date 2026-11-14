import sqlite3
from collections.abc import Callable
from contextlib import closing
from functools import partial
from pathlib import Path
from typing import Any, cast

import pytest
import store_errors_key as key

from credit_os.store import errors
from credit_os.store.errors import (
    StoreBusy,
    StoreConflict,
    StoreCorrupt,
    StoreError,
    StoreRefused,
    StoreUnusable,
    safe_text,
    store_error,
)

Run = Callable[[sqlite3.Connection], object]


def _raised(connection: sqlite3.Connection, act: Run) -> sqlite3.Error:
    with pytest.raises(sqlite3.Error) as caught:
        act(connection)
    return caught.value


def _failing(tmp_path: Path, setup: Run, act: Run, mode: str = "rwc") -> sqlite3.Error:
    uri = (tmp_path / "f.db").as_uri()
    with closing(sqlite3.connect(uri, uri=True, isolation_level=None)) as connection:
        setup(connection)
    with closing(
        sqlite3.connect(f"{uri}?mode={mode}", uri=True, isolation_level=None)
    ) as connection:
        return _raised(connection, act)


def _busy(tmp_path: Path) -> sqlite3.Error:
    uri = (tmp_path / "busy.db").as_uri()
    with closing(sqlite3.connect(uri, uri=True, isolation_level=None)) as first:
        first.execute("BEGIN IMMEDIATE")
        with closing(sqlite3.connect(uri, uri=True, timeout=0, isolation_level=None)) as second:
            return _raised(second, lambda c: c.execute("BEGIN IMMEDIATE"))


def _not_a_database(tmp_path: Path) -> sqlite3.Error:
    (tmp_path / "f.db").write_bytes(b"this is not a database file, " * 40)
    return _failing(tmp_path, lambda c: None, lambda c: c.execute("SELECT * FROM sqlite_master"))


def _closed(tmp_path: Path) -> sqlite3.Error:
    connection = sqlite3.connect(str(tmp_path / "c.db"))
    connection.close()
    return _raised(connection, lambda c: c.execute("SELECT 1"))


_REAL: dict[int | None, Callable[[Path], sqlite3.Error]] = {
    5: _busy,
    26: _not_a_database,
    None: _closed,
    2067: partial(
        _failing,
        setup=lambda c: c.executescript(
            "CREATE TABLE t (a INTEGER UNIQUE); INSERT INTO t VALUES (1);"
        ),
        act=lambda c: c.execute("INSERT INTO t VALUES (1)"),
    ),
    275: partial(
        _failing,
        setup=lambda c: c.execute("CREATE TABLE t (a INTEGER CHECK (a > 0))"),
        act=lambda c: c.execute("INSERT INTO t VALUES (0)"),
    ),
    787: partial(
        _failing,
        setup=lambda c: c.executescript(
            "CREATE TABLE p (a INTEGER PRIMARY KEY); CREATE TABLE c (a INTEGER REFERENCES p (a));"
        ),
        act=lambda c: c.executescript("PRAGMA foreign_keys = ON; INSERT INTO c VALUES (7);"),
    ),
    1811: partial(
        _failing,
        setup=lambda c: c.executescript(
            "CREATE TABLE t (a INTEGER); CREATE TRIGGER no_insert BEFORE INSERT ON t"
            " BEGIN SELECT RAISE(ABORT, 'refused'); END;"
        ),
        act=lambda c: c.execute("INSERT INTO t VALUES (1)"),
    ),
    8: partial(
        _failing,
        setup=lambda c: c.execute("CREATE TABLE t (a INTEGER)"),
        act=lambda c: c.execute("INSERT INTO t VALUES (1)"),
        mode="ro",
    ),
}


def _constructed(code: Any) -> sqlite3.Error:
    error: Any = sqlite3.OperationalError("constructed")
    if code is not None:
        error.sqlite_errorcode = code
    return cast(sqlite3.Error, error)


@pytest.mark.parametrize(("code", "name"), key.ERROR_CLASS_BY_CODE)
def test_sqlite_code_maps_to_store_error_class(code: int | None, name: str, tmp_path: Path) -> None:
    if code in _REAL:
        original = _REAL[code](tmp_path)
        assert getattr(original, "sqlite_errorcode", None) == code
    else:
        original = _constructed(code)
    mapped = store_error(original, "doing it")
    assert type(mapped) is getattr(errors, name)
    assert isinstance(mapped, StoreError)
    assert str(mapped) == f"doing it: {original}"


def test_the_real_sqlite_rows_are_exactly_the_required_ones() -> None:
    assert set(_REAL) == {5, 2067, 275, 787, 1811, 26, 8, None}
    assert set(_REAL) <= {code for code, _ in key.ERROR_CLASS_BY_CODE}


def test_non_int_code_is_unusable() -> None:
    assert type(store_error(_constructed("5"), "x")) is errors.StoreUnusable


def test_message_escapes_a_lone_surrogate() -> None:
    mapped = store_error(sqlite3.OperationalError("disk \ud800 trouble"), "writing run")
    assert str(mapped) == "writing run: disk \\ud800 trouble"


def test_raise_from_keeps_the_cause() -> None:
    original = sqlite3.OperationalError("boom")
    with pytest.raises(StoreError) as caught:
        raise store_error(original, "x") from original
    assert caught.value.__cause__ is original


def test_store_refused_is_a_value_error_and_the_rest_are_not() -> None:
    assert issubclass(StoreRefused, StoreError)
    assert issubclass(StoreRefused, ValueError)
    for name in ("StoreBusy", "StoreConflict", "StoreCorrupt", "StoreUnusable"):
        assert issubclass(getattr(errors, name), StoreError)
        assert not issubclass(getattr(errors, name), ValueError)


def test_mapped_store_errors_are_siblings_of_one_another() -> None:
    mapped = {StoreBusy, StoreConflict, StoreCorrupt, StoreUnusable}
    used = {type(store_error(_constructed(code), "x")) for code, _ in key.ERROR_CLASS_BY_CODE}
    assert mapped == used
    for first in mapped:
        for second in mapped - {first}:
            assert not issubclass(first, second), (first.__name__, second.__name__)


@pytest.mark.parametrize(("text", "expected"), key.SAFE_TEXT)
def test_safe_text_escapes_lone_surrogates_only_and_binds_to_sqlite(
    text: str, expected: str
) -> None:
    assert safe_text(text) == expected
    with closing(sqlite3.connect(":memory:")) as connection:
        assert connection.execute("SELECT ?", (safe_text(text),)).fetchone() == (expected,)
        if text != expected:
            with pytest.raises(UnicodeEncodeError):
                connection.execute("SELECT ?", (text,))


@pytest.mark.parametrize("value", key.SAFE_TEXT_REFUSED)
def test_safe_text_refuses_non_text(value: Any) -> None:
    with pytest.raises(StoreRefused) as caught:
        safe_text(value)
    assert type(caught.value) is StoreRefused
    assert type(value).__name__ in str(caught.value)
