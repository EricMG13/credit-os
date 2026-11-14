import ast
import os
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
        assert getattr(errors, name).__bases__ == (StoreError,)


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


_FAILURES = {
    "unique": ("CREATE TABLE t(a TEXT UNIQUE, b TEXT)", ["INSERT INTO t(a) VALUES (?)"] * 2),
    "check": (
        "CREATE TABLE t(a TEXT CHECK(length(a) < 3), b TEXT)",
        ["INSERT INTO t(a) VALUES (?)"],
    ),
    "not null": (
        "CREATE TABLE t(a TEXT, b TEXT NOT NULL)",
        ["INSERT INTO t(a, b) VALUES (?, NULL)"],
    ),
    "foreign key": (
        "CREATE TABLE p(a TEXT PRIMARY KEY); CREATE TABLE t(a TEXT REFERENCES p(a), b TEXT)",
        ["INSERT INTO t(a) VALUES (?)"],
    ),
    "datatype": ("CREATE TABLE t(a INTEGER, b TEXT) STRICT", ["INSERT INTO t(a) VALUES (?)"]),
}


@pytest.mark.parametrize("kind", key.VALUE_FREE_FAILURES)
def test_a_real_failure_message_does_not_carry_the_bound_value(kind: str) -> None:
    schema, statements = _FAILURES[kind]
    with closing(sqlite3.connect(":memory:", autocommit=True)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(schema)
        with pytest.raises(sqlite3.Error) as caught:
            for statement in statements:
                connection.execute(statement, (key.BOUND_VALUE,))
    assert key.BOUND_VALUE not in str(store_error(caught.value, "x"))
    assert type(store_error(caught.value, "x")).__name__ != "StoreUnusable"


_SOURCES = sorted(Path(errors.__file__).parent.glob("*.py"))


@pytest.mark.skipif(
    "MUTANT_UNDER_TEST" in os.environ, reason="mutmut rewrites the modules in place"
)
def test_every_store_error_call_is_raised_from_its_cause_and_every_sql_string_is_literal() -> None:
    assert len(_SOURCES) >= 4
    unliteral: list[str] = []
    for source in _SOURCES:
        tree = ast.parse(source.read_text(encoding="utf-8"))
        raised = {id(n.exc) for n in ast.walk(tree) if isinstance(n, ast.Raise) and n.cause}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name == "store_error":
                assert id(node) in raised, source.name
                assert isinstance(node.args[1], ast.Constant), source.name
            if name == "execute" and not isinstance(node.args[0], ast.Constant):
                unliteral.append(ast.unparse(node.args[0]))
    assert unliteral == ["statement"]


_HOOK_SETTERS = {
    ("txn.py", "write_transaction", "set_authorizer"),
    ("txn.py", "write_transaction", "set_progress_handler"),
    ("txn.py", "_clear_hooks", "set_authorizer"),
    ("txn.py", "_clear_hooks", "set_progress_handler"),
    ("txn.py", "_run", "set_authorizer"),
}


@pytest.mark.skipif(
    "MUTANT_UNDER_TEST" in os.environ, reason="mutmut rewrites the modules in place"
)
def test_only_the_transaction_helper_sets_or_clears_the_connection_hooks() -> None:
    found: set[tuple[str, str, str]] = set()
    for source in _SOURCES:
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for function in ast.walk(tree):
            if not isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            for node in ast.walk(function):
                if isinstance(node, ast.Attribute) and node.attr in {
                    "set_authorizer",
                    "set_progress_handler",
                }:
                    found.add((source.name, function.name, node.attr))
    assert found == _HOOK_SETTERS
