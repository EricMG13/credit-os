import contextlib
from itertools import product
from typing import Any

import pytest
import store_schema_rows_2_key as key
import store_schema_rows_key as rows
from store_rows_2_support import assert_refused, connect_2, dump, insert_sql, update_sql

KEYS = {
    "attempts": ("run_id", "module_id", "attempt"),
    "calls": ("run_id", "module_id", "attempt", "call_index"),
    "compactions": ("run_id", "event_id"),
}
PAIRS = list(product(key.ATTEMPT_STATES, repeat=2))
REFUSED_PAIRS = [p for p in PAIRS if p not in key.ALLOWED_ATTEMPT_MOVES]
PAIR_IDS = [f"{s}->{t}" for s, t in PAIRS]
REFUSED_PAIR_IDS = [f"{s}->{t}" for s, t in REFUSED_PAIRS]


def _read(db: Any, table: str, row: dict[str, object]) -> dict[str, object]:
    where = " AND ".join(f"{c} = ?" for c in KEYS[table])
    db.row_factory = None
    cursor = db.execute(f"SELECT * FROM {table} WHERE {where}", tuple(row[c] for c in KEYS[table]))
    names = [d[0] for d in cursor.description]
    (found,) = cursor.fetchall()
    return dict(zip(names, found, strict=True))


def _reach(db: Any, source: str) -> None:
    for columns in key.ATTEMPT_STATES[source]:
        db.execute(*update_sql("attempts", key.A1, columns))


def _target_update(target: str) -> dict[str, object]:
    updates = key.ATTEMPT_STATES[target]
    return updates[-1] if updates else {"state": "open"}


@pytest.mark.parametrize(
    ("table", "columns"),
    [(t, c) for _, t, c in key.ACCEPTED_INSERTS],
    ids=[label for label, _, _ in key.ACCEPTED_INSERTS],
)
def test_accepted_insert(table: str, columns: dict[str, object]) -> None:
    row = {**key.INSERT_BASES[table], **columns}
    with contextlib.closing(connect_2("FULL")) as db:
        before = db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        db.execute(*insert_sql(table, row))
        assert db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == before + 1
        read = _read(db, table, row)
    assert {c: read[c] for c in row} == row


@pytest.mark.parametrize(
    ("table", "columns", "message"),
    [(t, c, m) for _, t, c, m in key.REFUSED_INSERTS],
    ids=[label for label, _, _, _ in key.REFUSED_INSERTS],
)
def test_refused_insert(table: str, columns: dict[str, object], message: str) -> None:
    sql, values = insert_sql(table, {**key.INSERT_BASES[table], **columns})
    with contextlib.closing(connect_2("FULL")) as db:
        assert_refused(db, sql, values, (message,), exact=False)


@pytest.mark.parametrize(
    ("source", "target"),
    key.ALLOWED_ATTEMPT_MOVES,
    ids=[f"{s}->{t}" for s, t in key.ALLOWED_ATTEMPT_MOVES],
)
def test_attempt_move_accepted(source: str, target: str) -> None:
    with contextlib.closing(connect_2("WITH_ATTEMPT")) as db:
        _reach(db, source)
        db.execute(*update_sql("attempts", key.A1, _target_update(target)))
        (state,) = db.execute(f"SELECT state FROM attempts WHERE {key.A1}").fetchone()
    assert state == target


@pytest.mark.parametrize(("source", "target"), REFUSED_PAIRS, ids=REFUSED_PAIR_IDS)
def test_attempt_move_refused(source: str, target: str) -> None:
    sql, values = update_sql("attempts", key.A1, _target_update(target))
    with contextlib.closing(connect_2("WITH_ATTEMPT")) as db:
        _reach(db, source)
        assert_refused(db, sql, values, key.refused_move_messages(source, target), exact=True)


def test_attempt_moves_cover_all_pairs() -> None:
    allowed = set(key.ALLOWED_ATTEMPT_MOVES)
    assert len(PAIRS) == 25
    assert allowed <= set(PAIRS)
    assert len(allowed) + len(REFUSED_PAIRS) == 25
    assert len(REFUSED_PAIRS) == 21


@pytest.mark.parametrize(
    ("source", "update", "message"),
    [(s, u, m) for _, s, u, m in key.REFUSED_ATTEMPT_UPDATES],
    ids=[label for label, _, _, _ in key.REFUSED_ATTEMPT_UPDATES],
)
def test_refused_attempt_update(source: str, update: dict[str, object], message: str) -> None:
    sql, values = update_sql("attempts", key.A1, update)
    with contextlib.closing(connect_2("WITH_ATTEMPT")) as db:
        _reach(db, source)
        assert_refused(db, sql, values, (message,), exact=False)


def test_closed_ok() -> None:
    sql, values = update_sql("calls", key.C0, {"closed_at": rows.T2, **key.CLOSED_OK})
    with contextlib.closing(connect_2("WITH_CALL")) as db:
        before = dump(db)
        db.execute(sql, values)
        assert dump(db) != before
        read = _read(db, "calls", key.CALL)
    assert {c: read[c] for c in ("closed_at", "kind", "stop_reason")} == {
        "closed_at": rows.T2,
        **key.CLOSED_OK,
    }


@pytest.mark.parametrize(
    ("columns", "message"),
    [(c, m) for _, c, m in key.REFUSED_CLOSES],
    ids=[label for label, _, _ in key.REFUSED_CLOSES],
)
def test_refused_close(columns: dict[str, object], message: str) -> None:
    sql, values = update_sql("calls", key.C0, {"closed_at": rows.T2, **columns})
    with contextlib.closing(connect_2("WITH_CALL")) as db:
        assert_refused(db, sql, values, (message,), exact=False)


def test_refused_close_of_text_raw_is_a_type_error() -> None:
    sql, values = update_sql("calls", key.C0, {"closed_at": rows.T2, **key.CLOSED_OK, "raw": "x"})
    with contextlib.closing(connect_2("WITH_CALL")) as db:
        assert_refused(
            db,
            sql,
            values,
            ("cannot store TEXT value in BLOB column calls.raw",),
            exact=False,
        )


@pytest.mark.parametrize(
    "columns",
    [c for _, c in key.REFUSED_OPEN_CALL_UPDATES],
    ids=[label for label, _ in key.REFUSED_OPEN_CALL_UPDATES],
)
def test_refused_open_call_update(columns: dict[str, object]) -> None:
    sql, values = update_sql("calls", key.C0, columns)
    with contextlib.closing(connect_2("WITH_CALL")) as db:
        assert_refused(db, sql, values, (key.CHECK,), exact=False)
