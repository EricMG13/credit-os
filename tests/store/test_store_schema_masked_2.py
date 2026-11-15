import contextlib

import pytest
import store_reply_key as replies
import store_schema_masked_2_key as key
import store_schema_rows_2_key as rows_key
import store_schema_rows_key as rows
from store_rows_2_support import assert_refused, connect_2, update_sql

CALL_KEY = {"run_id": "run-001", "module_id": "CP-1", "attempt": 1, "call_index": 0}


@pytest.mark.parametrize(
    ("setup", "triggers", "prelude", "sql", "values", "start"),
    [row[1:] for row in key.MASKED_CONSTRAINTS],
    ids=[row[0] for row in key.MASKED_CONSTRAINTS],
)
def test_masked_constraint_refuses(
    setup: str,
    triggers: tuple[str, ...],
    prelude: tuple[rows_key.Statement, ...],
    sql: str,
    values: tuple[object, ...],
    start: str,
) -> None:
    with contextlib.closing(connect_2(setup)) as db:
        for name in triggers:
            db.execute(f"DROP TRIGGER {name}")
        for statement, statement_values in prelude:
            db.execute(statement, statement_values)
        assert_refused(db, sql, values, (start,), exact=False)


@pytest.mark.parametrize(
    ("call", "compactions"),
    [(case[2], case[3]) for case in replies.CASES],
    ids=[case[0] for case in replies.CASES],
)
def test_reply_columns_accepted(
    call: dict[str, object], compactions: tuple[dict[str, object], ...]
) -> None:
    with contextlib.closing(connect_2("WITH_CALL")) as db:
        for row in compactions:
            columns = {**CALL_KEY, **row}
            names = ", ".join(columns)
            marks = ", ".join("?" for _ in columns)
            db.execute(
                f"INSERT INTO compactions ({names}) VALUES ({marks})", tuple(columns.values())
            )
        db.execute(*update_sql("calls", rows_key.C0, {"closed_at": rows.T2, **call}))
        cursor = db.execute(f"SELECT * FROM calls WHERE {rows_key.C0}")
        call_names = [d[0] for d in cursor.description]
        (found,) = cursor.fetchall()
        read = dict(zip(call_names, found, strict=True))
        stored = db.execute("SELECT * FROM compactions WHERE run_id = 'run-001' ORDER BY position")
        compaction_names = [d[0] for d in stored.description]
        stored_rows = [dict(zip(compaction_names, r, strict=True)) for r in stored.fetchall()]
    assert {name: read[name] for name in (*call, "closed_at")} == {"closed_at": rows.T2, **call}
    assert stored_rows == [{**CALL_KEY, **row} for row in compactions]
