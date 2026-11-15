"""Shared raw-connection helpers for the migration 2 row tests (3a-b1, 3a-b2, 3a-b3).

A plain module, imported by its bare name as the other store tests import their keys.
"""

import sqlite3
from collections.abc import Mapping
from typing import Any

import pytest
import store_schema_rows_2_key as key
import store_schema_rows_key as rows

from credit_os.store import schema

TABLES = ("runs", "run_sources", "events", "attempts", "calls", "compactions")
SETUPS = ("CREATED_RUN", "RUNNING_RUN", "WITH_ATTEMPT", "WITH_CALL", "FULL")


def insert_sql(table: str, row: Mapping[str, object]) -> tuple[str, tuple[object, ...]]:
    """An INSERT naming every column of `row`, with its values in order."""
    names = ", ".join(row)
    marks = ", ".join("?" for _ in row)
    return f"INSERT INTO {table} ({names}) VALUES ({marks})", tuple(row.values())


def update_sql(table: str, where: str, row: Mapping[str, object]) -> tuple[str, tuple[object, ...]]:
    """An UPDATE setting every column of `row` where `where` (text without parameters)."""
    sets = ", ".join(f"{name} = ?" for name in row)
    return f"UPDATE {table} SET {sets} WHERE {where}", tuple(row.values())


def connect_2(setup: str, *, foreign_keys: bool = True) -> sqlite3.Connection:
    """A raw in-memory connection migrated to 2 statement by statement, then `setup` built.

    The caller closes it.
    """
    if setup not in SETUPS:
        raise ValueError(f"unknown setup {setup!r}")
    db = sqlite3.connect(":memory:", autocommit=True)
    try:
        db.execute(f"PRAGMA foreign_keys = {'ON' if foreign_keys else 'OFF'}")
        for statement in (*schema.MIGRATION_1, *schema.MIGRATION_2):
            db.execute(statement)
        db.execute(*insert_sql("runs", rows.RUN))
        if setup != "CREATED_RUN":
            db.execute(*update_sql("runs", "run_id = 'run-001'", rows.RUNNING))
        if setup in ("WITH_ATTEMPT", "WITH_CALL", "FULL"):
            db.execute(*insert_sql("attempts", key.ATTEMPT))
        if setup in ("WITH_CALL", "FULL"):
            db.execute(*insert_sql("calls", key.CALL))
        if setup == "FULL":
            db.execute(*insert_sql("compactions", key.COMPACTION))
            db.execute(*insert_sql("attempts", key.ATTEMPT_2))
    except BaseException:
        db.close()
        raise
    return db


def dump(db: sqlite3.Connection) -> list[list[tuple[Any, ...]]]:
    """Every table in TABLES, its rows sorted by repr."""
    return [sorted(db.execute(f"SELECT * FROM {t}").fetchall(), key=repr) for t in TABLES]


def assert_refused(
    db: sqlite3.Connection,
    sql: str,
    values: tuple[object, ...],
    messages: tuple[str, ...],
    *,
    exact: bool,
    error: type[sqlite3.Error] = sqlite3.IntegrityError,
) -> None:
    """`sql` raises exactly `error` with one of `messages` and no table changes."""
    before = dump(db)
    with pytest.raises(sqlite3.Error) as info:
        db.execute(sql, values)
    assert type(info.value) is error
    text = str(info.value)
    if exact:
        assert text in messages
    else:
        assert text.startswith(messages)
    assert dump(db) == before
