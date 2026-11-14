import hashlib
import sqlite3
from contextlib import closing
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
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
        without_rowid = raw_db.execute(
            f"SELECT name FROM pragma_table_list WHERE schema = 'main' AND wr AND {SYSTEM} ORDER BY name"
        ).fetchall()
        assert tuple(n for (n,) in without_rowid) == key.WITHOUT_ROWID_TABLES_AT_1


def _raw(foreign_keys: bool) -> sqlite3.Connection:
    raw_db = sqlite3.connect(":memory:", autocommit=True)
    raw_db.execute(f"PRAGMA foreign_keys = {'ON' if foreign_keys else 'OFF'}")
    for statement in schema.MIGRATION_1:
        raw_db.execute(statement)
    for statement, values in key.SEED:
        raw_db.execute(statement, values)
    return raw_db


def _rows(raw_db: sqlite3.Connection) -> list[set[tuple[Any, ...]]]:
    return [
        set(raw_db.execute(f"SELECT * FROM {table}").fetchall())
        for table in ("events", "run_sources", "runs")
    ]


@pytest.mark.parametrize("foreign_keys", [True, False], ids=["fk-on", "fk-off"])
@pytest.mark.parametrize(
    ("statement", "values", "message"),
    [(statement, values, message) for _, statement, values, message in key.ROWID_STATEMENTS],
    ids=[label for label, _, _, _ in key.ROWID_STATEMENTS],
)
def test_no_statement_reaches_a_hidden_rowid(
    statement: str, values: tuple[object, ...], message: str, foreign_keys: bool
) -> None:
    with closing(_raw(foreign_keys)) as raw_db:
        before = _rows(raw_db)
        with pytest.raises(sqlite3.OperationalError) as caught:
            raw_db.execute(statement, values)
        assert str(caught.value) == message
        assert _rows(raw_db) == before


@pytest.mark.parametrize("status", list(key.STATUS_UPDATES))
def test_a_pin_is_added_only_while_its_run_is_created(status: str) -> None:
    insert = "INSERT INTO run_sources(run_id, position, name, sha256, size_bytes, kind) VALUES (?, ?, ?, ?, ?, ?)"
    with closing(_raw(True)) as raw_db:
        for statement, values in key.STATUS_UPDATES[status]:
            raw_db.execute(statement, values)
        before = _rows(raw_db)
        if status == "created":
            raw_db.execute(insert, key.LATE_PIN)
            after = _rows(raw_db)
            assert after[1] > before[1] and len(after[1]) == len(before[1]) + 1
            assert after[0] == before[0] and after[2] == before[2]
        else:
            with pytest.raises(sqlite3.IntegrityError) as caught:
                raw_db.execute(insert, key.LATE_PIN)
            assert str(caught.value) == key.LATE_PIN_MESSAGE
            assert _rows(raw_db) == before


# --- Migration 2 ---------------------------------------------------------------------------------


def test_text_matches_the_key_at_2() -> None:
    joined = "\n".join(schema.MIGRATION_2).encode("utf-8")
    assert len(schema.MIGRATION_2) == key.MIGRATION_STATEMENTS[2]
    assert hashlib.sha256(joined).hexdigest() == key.MIGRATION_SHA256[2]


def test_each_statement_is_one_statement_at_2() -> None:
    for statement in schema.MIGRATION_2:
        assert sqlite3.complete_statement(statement + ";")
        if statement.startswith("CREATE TRIGGER"):
            assert statement.endswith("; END")
            assert statement.count(";") == 1
        else:
            assert ";" not in statement
    assert schema.MIGRATION_2[-1] == "PRAGMA user_version = 2"


def test_no_rollback_conflict_clause_at_2() -> None:
    text = " ".join(schema.MIGRATION_2).upper()
    assert "ROLLBACK" not in text
    assert text.count("RAISE(ABORT, '") == text.count("RAISE(")


def test_store_applies_migration_2_once(tmp_path: Path) -> None:
    folder = tmp_path / "state"
    open_store(folder).close()
    first = _schema_text(folder)
    assert first[1] == 2
    open_store(folder).close()
    assert _schema_text(folder) == first
    open_reader(folder).close()


def test_schema_matches_the_key_at_2(tmp_path: Path) -> None:
    folder = tmp_path / "state"
    open_store(folder).close()
    with closing(sqlite3.connect(folder / location.STATE_FILE_NAME, autocommit=True)) as raw_db:
        for table, columns in key.TABLES_AT_2.items():
            found = raw_db.execute(
                'SELECT name, type, "notnull", pk FROM pragma_table_info(?) ORDER BY cid', (table,)
            ).fetchall()
            assert [(n, t, bool(nn), pk) for n, t, nn, pk in found] == list(columns)
        objects = raw_db.execute(
            f"SELECT type, name, tbl_name FROM sqlite_schema WHERE {SYSTEM} ORDER BY type, name"
        ).fetchall()
        assert tuple(objects) == key.OBJECTS_AT_2
        tables = raw_db.execute(
            f"SELECT name, strict FROM pragma_table_list WHERE schema = 'main' AND {SYSTEM}"
        ).fetchall()
        assert tuple(sorted(n for n, strict in tables if strict)) == key.STRICT_TABLES_AT_2
        assert all(strict for _, strict in tables)
        without_rowid = raw_db.execute(
            "SELECT name FROM pragma_table_list"
            f" WHERE schema = 'main' AND wr AND {SYSTEM} ORDER BY name"
        ).fetchall()
        assert tuple(n for (n,) in without_rowid) == key.WITHOUT_ROWID_TABLES_AT_2
        indexes = raw_db.execute(
            'SELECT t.name, l.name, l.origin, l."unique", l.partial, i.name'
            " FROM pragma_table_list AS t, pragma_index_list(t.name) AS l,"
            " pragma_index_info(l.name) AS i"
            " WHERE t.schema = 'main' AND t.name IN ('attempts', 'calls', 'compactions')"
            " ORDER BY t.name, l.name, i.seqno"
        ).fetchall()
        grouped: dict[str, tuple[str, str, int, int, list[str]]] = {}
        for table, index, origin, unique, partial, column in indexes:
            grouped.setdefault(index, (table, origin, unique, partial, []))[4].append(column)
        found_indexes = sorted((t, o, u, p, tuple(c)) for t, o, u, p, c in grouped.values())
        assert tuple(found_indexes) == key.INDEXES_AT_2
        foreign: dict[str, dict[int, tuple[str, list[str], list[str]]]] = {}
        for table in key.FOREIGN_KEYS_AT_2:
            rows = raw_db.execute(
                'SELECT id, "table", "from", "to" FROM pragma_foreign_key_list(?) ORDER BY id, seq',
                (table,),
            ).fetchall()
            for fk_id, parent, column, parent_column in rows:
                entry = foreign.setdefault(table, {}).setdefault(fk_id, (parent, [], []))
                entry[1].append(column)
                entry[2].append(parent_column)
        for table, expected in key.FOREIGN_KEYS_AT_2.items():
            found_fks = sorted((p, tuple(c), tuple(pc)) for p, c, pc in foreign[table].values())
            assert tuple(found_fks) == expected
        accepted_sql = raw_db.execute(
            "SELECT sql FROM sqlite_schema WHERE name = 'attempts_one_accepted'"
        ).fetchone()[0]
        assert accepted_sql.endswith(key.ONE_ACCEPTED_WHERE)


def _tables(folder: Path) -> list[list[tuple[Any, ...]]]:
    with closing(sqlite3.connect(folder / location.STATE_FILE_NAME)) as raw_db:
        raw_db.text_factory = bytes
        return [
            raw_db.execute(f"SELECT * FROM {table}").fetchall()  # three fixed table names
            for table in ("runs", "run_sources", "events")
        ]


def test_a_file_at_version_1_moves_to_version_2(tmp_path: Path) -> None:
    folder = tmp_path / "state"
    with open_store(folder, migrations=(schema.MIGRATION_1,)) as old:
        old.create_run(
            run_id="run-001",
            issuer_id="iss",
            issuer_name="Issuer",
            as_of=None,
            config_id="cfg",
            cap_usd=Decimal("20"),
            request=b"r",
            pins=(),
        )
    at_1, rows_at_1 = _schema_text(folder), _tables(folder)
    assert at_1[1] == 1 and rows_at_1[0] and rows_at_1[2]
    open_store(folder).close()
    at_2 = _schema_text(folder)
    assert at_2[1] == 2
    assert all(row in at_2[0] for row in at_1[0])
    assert _tables(folder) == rows_at_1
