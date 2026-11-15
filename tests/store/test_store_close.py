import sqlite3
from collections.abc import Iterator
from contextlib import closing
from functools import partial
from pathlib import Path
from typing import Any

import pytest
import store_attempts_key as key
import store_reply_key as reply_key
import store_status_key as status_key
from test_store_attempts import _call_args, _open, _step, _try
from test_store_status import RUN_ID, Ticker, _create, _dump, _outcome, _query

from credit_os.provider.types import ProviderDataError, Reply, Usage
from credit_os.store import location
from credit_os.store.db import Store, open_store
from credit_os.store.records import Claim

TIMES = {n: f"2026-09-30T12:00:{n:02d}.000000Z" for n in range(1, len(key.SCRIPT_3B2B) + 1)}
CALL_NAMES = tuple(key.OPEN_CALL_COLUMNS)
CALL_SQL = "SELECT module_id, attempt, call_index, exchange_id, provider_call_index, opened_at, "
CALL_SQL += (
    "closed_at, " + ", ".join(CALL_NAMES) + " FROM calls ORDER BY module_id, attempt, call_index"
)
COMPACTION_SQL = (
    "SELECT position, event_id, module_id, attempt, call_index, input_tokens, cached_read_tokens,"
    " cache_write_tokens, output_tokens, billed_usd, outcome, supersedes FROM compactions"
    " WHERE run_id = ? ORDER BY position"
)
STATUS_ERRORS = ("StoreConflict", "StoreRefused")


@pytest.fixture
def ticker() -> Ticker:
    return Ticker()


@pytest.fixture
def store(tmp_path: Path, ticker: Ticker) -> Iterator[Store]:
    with open_store(tmp_path, clock=ticker) as opened:
        yield opened


def _with_call(store: Store, run_id: str | None = None) -> Claim:
    """A running run whose CP-1 attempt 1 has call 0 open on ex-1/0."""
    claim = store.create_run(**(_create() if run_id is None else _create(run_id=run_id)))
    store.start_run(claim)
    _open(store, claim)
    assert store.open_call(claim, **_call_args("CP-1", 1, "ex-1", 0)) == 0
    return claim


def _compactions(folder: Path, run_id: str = RUN_ID) -> list[tuple[Any, ...]]:
    with closing(sqlite3.connect(folder / location.STATE_FILE_NAME)) as raw:
        return raw.execute(COMPACTION_SQL, (run_id,)).fetchall()


def _close_args(reply: object, index: int = 0) -> dict[str, Any]:
    return dict(key._close("CP-1", 1, index, reply))


def _call_state(folder: Path) -> list[tuple[Any, ...]]:
    return _query(folder, CALL_SQL)


def _unchanged(
    tmp_path: Path, ticker: Ticker, store: Store, claim: Claim, args: Any, expected: str
) -> None:
    before, ticker.calls = _dump(tmp_path), 0
    assert _outcome(lambda: store.close_call(claim, **args)) == expected
    assert (ticker.calls, _dump(tmp_path)) == (0, before)


def test_scripted_run(tmp_path: Path, store: Store, ticker: Ticker) -> None:
    claims: dict[int, Claim] = {}
    for row, (name, number, args, expected) in enumerate(key.SCRIPT_3B2B, 1):
        before, ticker.row, ticker.calls = _dump(tmp_path), row, 0
        error, value = _try(partial(_step3, store, claims, name, number, args))
        assert error == expected, row
        assert value == key.SCRIPT_3B2B_RETURNS.get(row), row
        if expected is None and row not in key.NO_WRITE_ROWS_3B2B:
            assert ticker.calls == (0 if row in key.CLOCKLESS_ROWS_3B2B else 1), row
        else:
            assert (ticker.calls, _dump(tmp_path)) == (0, before), row
    assert store.run(RUN_ID).status == key.AFTER_3B2B_STATUS
    events = [(e.kind, e.module_id, e.attempt, dict(e.detail)) for e in store.events(RUN_ID)]
    assert events == list(key.AFTER_3B2B_EVENTS)
    assert _query(tmp_path, "SELECT seq, at FROM events ORDER BY seq") == [
        (seq, TIMES[row]) for seq, row in enumerate(key.AFTER_3B2B_EVENT_ROWS, 1)
    ]
    expected_calls = [
        (m, n, i, ex, p, TIMES[opened], None if closed is None else TIMES[closed])
        for m, n, i, ex, p, opened, closed, _ in key.AFTER_3B2B_CALLS
    ]
    rows = _call_state(tmp_path)
    assert [row[:7] for row in rows] == expected_calls
    for state, call in zip(rows, key.AFTER_3B2B_CALLS, strict=True):
        assert dict(zip(CALL_NAMES, state[7:], strict=True)) == call[7]
    assert [(r[0], r[1], r[2:5], r[10], r[9]) for r in _compactions(tmp_path)] == [
        (p, e, (None, None, None) if c is None else c, o, b)
        for p, e, c, o, b in key.AFTER_3B2B_COMPACTIONS
    ]


def _step3(store: Store, claims: dict[int, Claim], name: str, number: int, args: Any) -> object:
    if name == "close_call":
        store.close_call(claims[number], **args)
        return None
    if name == "record_compactions":
        store.record_compactions(claims[number], **args)
        return None
    return _step(store, claims, name, number, args)


@pytest.mark.parametrize(
    ("reply", "call", "rows"),
    [row[1:] for row in reply_key.CASES],
    ids=[row[0] for row in reply_key.CASES],
)
def test_every_reply_kind_is_stored_as_keyed(
    tmp_path: Path,
    store: Store,
    ticker: Ticker,
    reply: Reply,
    call: dict[str, object],
    rows: tuple[dict[str, object], ...],
) -> None:
    claim = _with_call(store)
    ticker.row, ticker.calls = 2, 0
    store.close_call(claim, **_close_args(reply))
    assert ticker.calls == 1
    [state] = _call_state(tmp_path)
    assert state[6] == TIMES[2]
    assert dict(zip(CALL_NAMES, state[7:], strict=True)) == call
    names = [
        *("position", "event_id", "module_id", "attempt", "call_index"),
        *("input_tokens", "cached_read_tokens", "cache_write_tokens", "output_tokens"),
        *("billed_usd", "outcome", "supersedes"),
    ]
    stored = [dict(zip(names, r, strict=True)) for r in _compactions(tmp_path)]
    assert [
        {k: v for k, v in s.items() if k not in ("module_id", "attempt", "call_index")}
        for s in stored
    ] == list(rows)
    assert all((s["module_id"], s["attempt"], s["call_index"]) == ("CP-1", 1, 0) for s in stored)


@pytest.mark.parametrize(
    ("first", "second", "error", "after", "call_key"),
    [row[1:] for row in key.CLOSE_REPEATS],
    ids=[row[0] for row in key.CLOSE_REPEATS],
)
def test_a_compaction_repeat_through_close_call(
    tmp_path: Path,
    store: Store,
    first: str,
    second: str,
    error: str | None,
    after: str,
    call_key: key.CallKey | None,
) -> None:
    claim = _with_call(store)
    step = {
        "close": lambda: store.close_call(claim, **_close_args(key.REPEAT_FROM_CALL)),
        "record": lambda: store.record_compactions(claim, (key.FINISHED,)),
    }
    assert _outcome(step[first]) is None
    assert _outcome(step[second]) == error
    [row] = _compactions(tmp_path)
    assert (row[1], row[2:5], row[9], row[10], row[11]) == (
        "d-1",
        (None, None, None) if call_key is None else call_key,
        "0.002",
        "done",
        "u-1",
    )
    state = _call_state(tmp_path)[0]
    assert (state[6] is not None) == (after == "closed")


def test_a_reply_that_collides_with_itself_leaves_the_call_open(
    tmp_path: Path, store: Store, ticker: Ticker
) -> None:
    claim = _with_call(store)
    _unchanged(
        tmp_path, ticker, store, claim, _close_args(key.SELF_COLLISION_REPLY), "StoreConflict"
    )
    assert _compactions(tmp_path) == []
    assert _call_state(tmp_path)[0][6] is None


def test_a_reply_cannot_repeat_a_compaction_inside_itself() -> None:
    with pytest.raises(ProviderDataError):
        key._ok(Usage(), None, key.TWICE_COMPACTIONS)


@pytest.mark.parametrize(
    ("charge", "text"),
    [row[1:] for row in key.STORED_CHARGES],
    ids=[row[0] for row in key.STORED_CHARGES],
)
def test_a_charge_is_stored_as_the_exact_text(
    tmp_path: Path, store: Store, charge: Any, text: str
) -> None:
    claim = _with_call(store)
    store.close_call(claim, **_close_args(key._sent_usage(charge)))
    assert _call_state(tmp_path)[0][7 + CALL_NAMES.index("billed_usd")] == text


@pytest.mark.parametrize(
    ("charge", "text"),
    [row[1:] for row in key.STORED_CHARGES],
    ids=[row[0] for row in key.STORED_CHARGES],
)
def test_a_compaction_charge_is_stored_as_the_exact_text(
    tmp_path: Path, store: Store, charge: Any, text: str
) -> None:
    claim = _with_call(store)
    store.close_call(claim, **_close_args(key._bare(charge)))
    assert [row[9] for row in _compactions(tmp_path)] == [text]


def test_a_negative_zero_charge_is_not_a_reply() -> None:
    with pytest.raises(ProviderDataError):
        key._sent_usage(key.NEGATIVE_ZERO)


@pytest.mark.parametrize(
    "reply",
    [row[1] for row in key.UNSTORABLE_REPLIES] + [key.CHILD_REPLY],
    ids=[row[0] for row in key.UNSTORABLE_REPLIES] + ["a Reply subclass"],
)
def test_a_reply_the_store_cannot_hold_leaves_the_call_open(
    tmp_path: Path, store: Store, ticker: Ticker, reply: Reply
) -> None:
    claim = _with_call(store)
    _unchanged(tmp_path, ticker, store, claim, _close_args(reply), "StoreRefused")
    [state] = _call_state(tmp_path)
    assert state[6] is None
    assert dict(zip(CALL_NAMES, state[7:], strict=True)) == key.OPEN_CALL_COLUMNS
    assert _compactions(tmp_path) == []


@pytest.mark.parametrize(
    "args",
    [row[2] for row in key.REFUSED_ARGUMENTS_3B2B] + [row[2] for row in key.MISSING_3B2B],
    ids=[row[0] for row in key.REFUSED_ARGUMENTS_3B2B] + [row[0] for row in key.MISSING_3B2B],
)
def test_refused_close_arguments(tmp_path: Path, store: Store, ticker: Ticker, args: Any) -> None:
    claim = _with_call(store)
    _unchanged(tmp_path, ticker, store, claim, args, "StoreRefused")
    assert _call_state(tmp_path)[0][6] is None


def test_a_claim_that_is_not_a_claim_is_refused(tmp_path: Path, store: Store) -> None:
    _with_call(store)
    before = _dump(tmp_path)
    args: Any = key.MISSING_RUN_CLOSE
    assert _outcome(partial(_write, store, "close_call", "not a claim", args)) == "StoreRefused"
    assert _dump(tmp_path) == before


def test_a_missing_run_is_refused(tmp_path: Path, store: Store, ticker: Ticker) -> None:
    _with_call(store)
    claim = Claim(key.MISSING_RUN_ID, status_key.FOREIGN_TOKEN)
    _unchanged(tmp_path, ticker, store, claim, key.MISSING_RUN_CLOSE, "StoreRefused")
    assert _call_state(tmp_path)[0][6] is None


@pytest.mark.parametrize("status", [s for s in key.NOT_RUNNING if s not in ("created", "rejected")])
def test_a_run_that_is_not_running_takes_no_close(
    tmp_path: Path, store: Store, ticker: Ticker, status: str
) -> None:
    claim = _with_call(store)
    store.end_run(claim, status=status, reason="x")
    _unchanged(tmp_path, ticker, store, claim, key.NOT_RUNNING_CLOSE, "StoreConflict")
    assert _call_state(tmp_path)[0][6] is None


@pytest.mark.parametrize("status", ["created", "rejected"])
def test_a_run_with_no_attempt_takes_no_close(
    tmp_path: Path, store: Store, ticker: Ticker, status: str
) -> None:
    claim = store.create_run(**_create())
    if status == "rejected":
        store.reject_run(claim, reason="x")
    _unchanged(tmp_path, ticker, store, claim, key.NOT_RUNNING_CLOSE, "StoreConflict")


def test_an_old_claim_closes_nothing(tmp_path: Path, store: Store, ticker: Ticker) -> None:
    old = _with_call(store)
    store.claim_run(RUN_ID)
    _unchanged(tmp_path, ticker, store, old, _close_args(key.OK_ZERO), "StoreFenced")
    assert _call_state(tmp_path)[0][6] is None
    assert _compactions(tmp_path) == []


def _write(store: Store, call: str, claim: Any, args: Any) -> None:
    getattr(store, call)(claim, **args)


def test_lookups_and_positions_are_per_run(tmp_path: Path, store: Store) -> None:
    claims = {"A": _with_call(store), "B": _with_call(store, key.SECOND_RUN_ID)}
    run_ids = {"A": RUN_ID, "B": key.SECOND_RUN_ID}
    for call, run, args, error in key.TWO_RUNS_CLOSE:
        assert _outcome(partial(_write, store, call, claims[run], args)) == error
    for run, expected in key.AFTER_TWO_RUNS_CLOSE.items():
        assert [
            (r[0], r[1], (None, None, None) if r[2] is None else r[2:5], r[9])
            for r in _compactions(tmp_path, run_ids[run])
        ] == [(p, e, (None, None, None) if c is None else c, b) for p, e, c, b in expected]
    states = _query(tmp_path, "SELECT run_id, closed_at IS NOT NULL FROM calls ORDER BY run_id")
    assert states == [(RUN_ID, 1), (key.SECOND_RUN_ID, 1)]
