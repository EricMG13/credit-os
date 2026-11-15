import contextlib
import sqlite3

import pytest
import store_schema_rows_2_key as rows_key
import store_schema_triggers_2_key as key
from store_rows_2_support import assert_refused, connect_2

ATTEMPT_STATE = f"SELECT state, fail_reason FROM attempts WHERE {rows_key.A1}"
CALL_STATE = f"SELECT closed_at, kind FROM calls WHERE {rows_key.C0}"
# What each accepted script leaves, written here from the key's comment, not read from the script.
ACCEPTED_FINAL_STATE = {"reply after its call closed": "accepted"}


@pytest.mark.parametrize(
    ("setup", "prelude", "sql", "values", "messages"),
    [(s, p, q, v, m) for _, s, p, q, v, m in key.REFUSED_STATEMENTS],
    ids=[row[0] for row in key.REFUSED_STATEMENTS],
)
def test_refused_statement(
    setup: str,
    prelude: tuple[rows_key.Statement, ...],
    sql: str,
    values: tuple[object, ...],
    messages: tuple[str, ...],
) -> None:
    with contextlib.closing(connect_2(setup)) as db:
        for statement, statement_values in prelude:
            db.execute(statement, statement_values)
        assert_refused(db, sql, values, messages, exact=True)


@pytest.mark.parametrize(
    ("sql", "values", "message"),
    [(q, v, m) for _, q, v, m in key.ORPHAN_STATEMENTS_2],
    ids=[row[0] for row in key.ORPHAN_STATEMENTS_2],
)
def test_orphan_refused(sql: str, values: tuple[object, ...], message: str) -> None:
    with contextlib.closing(connect_2("FULL", foreign_keys=False)) as db:
        assert_refused(db, sql, values, (message,), exact=True)


@pytest.mark.parametrize("foreign_keys", [True, False], ids=["fk-on", "fk-off"])
@pytest.mark.parametrize(
    ("sql", "values", "message"),
    [(q, v, m) for _, q, v, m in key.ROWID_STATEMENTS_2],
    ids=[row[0] for row in key.ROWID_STATEMENTS_2],
)
def test_rowid_refused(
    sql: str, values: tuple[object, ...], message: str, foreign_keys: bool
) -> None:
    with contextlib.closing(connect_2("FULL", foreign_keys=foreign_keys)) as db:
        assert_refused(db, sql, values, (message,), exact=True, error=sqlite3.OperationalError)


@pytest.mark.parametrize("name", list(key.TAKE_OVER_SCRIPTS), ids=list(key.TAKE_OVER_SCRIPTS))
def test_take_over(name: str) -> None:
    with contextlib.closing(connect_2("FULL")) as db:
        for sql, values, messages in key.TAKE_OVER_SCRIPTS[name]:
            if messages is None:
                db.execute(sql, values)
            else:
                assert_refused(db, sql, values, messages, exact=True)
        assert db.execute(CALL_STATE).fetchall() == [(None, None)]
        assert db.execute(ATTEMPT_STATE).fetchall() == [("failed", "interrupted")]


@pytest.mark.parametrize("name", list(key.ACCEPTED_SCRIPTS), ids=list(key.ACCEPTED_SCRIPTS))
def test_accepted_script(name: str) -> None:
    with contextlib.closing(connect_2("FULL")) as db:
        for sql, values in key.ACCEPTED_SCRIPTS[name]:
            db.execute(sql, values)
        assert db.execute(ATTEMPT_STATE).fetchall() == [(ACCEPTED_FINAL_STATE[name], None)]
