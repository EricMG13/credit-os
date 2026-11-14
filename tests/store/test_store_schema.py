import hashlib
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

import store_schema_key as key

from credit_os.store import location, schema
from credit_os.store.db import open_reader, open_store

SYSTEM = r"name NOT LIKE 'sqlite\_%' ESCAPE '\'"


def test_text_matches_the_key() -> None:
    joined = "\n".join(schema.MIGRATION_1).encode("utf-8")
    assert len(schema.MIGRATION_1) == key.MIGRATION_STATEMENTS[1]
    assert hashlib.sha256(joined).hexdigest() == key.MIGRATION_SHA256[1]


def test_each_statement_is_one_statement() -> None:
    for statement in schema.MIGRATION_1:
        assert sqlite3.complete_statement(statement + ";")
        if statement.startswith("CREATE TRIGGER"):
            assert statement.endswith("; END")
            assert statement.count(";") == 1
        else:
            assert ";" not in statement
    assert schema.MIGRATION_1[-1] == "PRAGMA user_version = 1"


def test_no_rollback_conflict_clause() -> None:
    text = " ".join(schema.MIGRATION_1).upper()
    assert "ROLLBACK" not in text
    assert text.count("RAISE(ABORT, '") == text.count("RAISE(")


def _schema_text(folder: Path) -> tuple[list[tuple[Any, ...]], int]:
    with closing(sqlite3.connect(folder / location.STATE_FILE_NAME, autocommit=True)) as raw_db:
        found = raw_db.execute("SELECT type, name, sql FROM sqlite_schema ORDER BY name").fetchall()
        return found, raw_db.execute("PRAGMA user_version").fetchone()[0]


def test_store_applies_migration_once(tmp_path: Path) -> None:
    folder = tmp_path / "state"
    open_store(folder, migrations=(schema.MIGRATION_1,)).close()
    first = _schema_text(folder)
    assert first[1] == 1
    open_store(folder, migrations=(schema.MIGRATION_1,)).close()
    assert _schema_text(folder) == first
    open_reader(folder, migrations=(schema.MIGRATION_1,)).close()


def test_schema_matches_the_key(tmp_path: Path) -> None:
    folder = tmp_path / "state"
    open_store(folder, migrations=(schema.MIGRATION_1,)).close()
    with closing(sqlite3.connect(folder / location.STATE_FILE_NAME, autocommit=True)) as raw_db:
        for table, columns in key.TABLES_AT_1.items():
            found = raw_db.execute(
                'SELECT name, type, "notnull", pk FROM pragma_table_info(?) ORDER BY cid', (table,)
            ).fetchall()
            assert [(n, t, bool(nn), pk) for n, t, nn, pk in found] == list(columns)
        objects = raw_db.execute(
            f"SELECT type, name, tbl_name FROM sqlite_schema WHERE {SYSTEM} ORDER BY type, name"
        ).fetchall()
        assert tuple(objects) == key.OBJECTS_AT_1
        tables = raw_db.execute(
            f"SELECT name, strict FROM pragma_table_list WHERE schema = 'main' AND {SYSTEM}"
        ).fetchall()
        assert tuple(sorted(n for n, strict in tables if strict)) == key.STRICT_TABLES_AT_1
        assert all(strict for _, strict in tables)
