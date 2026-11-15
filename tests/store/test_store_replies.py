from collections.abc import Iterator, Mapping
from functools import partial
from pathlib import Path
from typing import Any

import pytest
import store_attempts_key as key
import store_status_key as status_key
from test_store_attempts import ATTEMPT_COLUMNS, _attempt, _refused, _try
from test_store_close import CALL_NAMES, CALL_SQL, _compactions, _step3
from test_store_status import RUN_ID, Ticker, _create, _dump, _outcome, _query

from credit_os.store.db import Store, open_store
from credit_os.store.records import Claim

TIMES = {n: f"2026-09-30T12:00:{n:02d}.000000Z" for n in range(1, len(key.SCRIPT_3C1) + 1)}
EVENTS_SQL = "SELECT seq, at FROM events ORDER BY seq"
THREE_WRITES = ("record_reply", "record_verdict", "fail_attempt")


@pytest.fixture
def ticker() -> Ticker:
    return Ticker()


@pytest.fixture
def store(tmp_path: Path, ticker: Ticker) -> Iterator[Store]:
    with open_store(tmp_path, clock=ticker) as opened:
        yield opened


def _step4(store: Store, claims: dict[int, Claim], name: str, number: int, args: Any) -> object:
    if name in THREE_WRITES:
        return getattr(store, name)(claims[number], **args)
    return _step3(store, claims, name, number, args)


def _replay(
    tmp_path: Path,
    store: Store,
    ticker: Ticker,
    script: tuple[tuple[str, int, dict[str, object], str | None], ...],
    returns: Mapping[int, object],
) -> None:
    claims: dict[int, Claim] = {}
    for row, (name, number, args, expected) in enumerate(script, 1):
        before, ticker.row, ticker.calls = _dump(tmp_path), row, 0
        error, value = _try(partial(_step4, store, claims, name, number, args))
        assert error == expected, row
        assert value == returns.get(row), row
        if expected is None:
            assert ticker.calls == 1, row
        else:
            assert (ticker.calls, _dump(tmp_path)) == (0, before), row


def _events(store: Store) -> list[tuple[str, str | None, int | None, dict[str, Any]]]:
    return [(e.kind, e.module_id, e.attempt, dict(e.detail)) for e in store.events(RUN_ID)]


def test_scripted_run(tmp_path: Path, store: Store, ticker: Ticker) -> None:
    _replay(tmp_path, store, ticker, key.SCRIPT_3C1, key.SCRIPT_3C1_RETURNS)
    assert store.run(RUN_ID).status == key.AFTER_3C1_STATUS
    assert _events(store) == list(key.AFTER_3C1_EVENTS)
    assert _query(tmp_path, EVENTS_SQL) == [
        (seq, TIMES[row]) for seq, row in enumerate(key.AFTER_3C1_EVENT_ROWS, 1)
    ]
    assert _query(tmp_path, ATTEMPT_COLUMNS) == [
        (
            module,
            number,
            state,
            key.REQUESTS[request],
            key.REQUEST_SHA256[request],
            reply,
            sha,
            issues,
            reason,
            TIMES[opened],
            None if replied is None else TIMES[replied],
            None if closed is None else TIMES[closed],
        )
        for module, number, state, request, reply, sha, issues, reason, opened, replied, closed in key.AFTER_3C1_ATTEMPTS
    ]
    rows = _query(tmp_path, CALL_SQL)
    assert [row[:7] for row in rows] == [
        (m, n, i, ex, p, TIMES[opened], None if closed is None else TIMES[closed])
        for m, n, i, ex, p, opened, closed, _ in key.AFTER_3C1_CALLS
    ]
    for state, call in zip(rows, key.AFTER_3C1_CALLS, strict=True):
        assert dict(zip(CALL_NAMES, state[7:], strict=True)) == call[7]
    assert _compactions(tmp_path) == []


def test_a_take_over_that_ends_first_fails_the_attempt_on_resume(
    tmp_path: Path, store: Store, ticker: Ticker
) -> None:
    _replay(tmp_path, store, ticker, key.TAKE_OVER_END_FIRST, key.TAKE_OVER_RETURNS)
    assert _events(store) == list(key.AFTER_TAKE_OVER_EVENTS)
    assert [seq_at[1] for seq_at in _query(tmp_path, EVENTS_SQL)] == [
        TIMES[row] for row in key.AFTER_TAKE_OVER_EVENT_ROWS
    ]
    assert _query(tmp_path, "SELECT module_id, attempt, state, closed_at FROM attempts") == [
        (m, n, s, None if closed is None else TIMES[closed])
        for m, n, s, closed in key.AFTER_TAKE_OVER_ATTEMPTS
    ]
    rows = _query(tmp_path, CALL_SQL)
    assert [row[:7] for row in rows] == [
        (m, n, i, ex, p, TIMES[opened], None if closed is None else TIMES[closed])
        for m, n, i, ex, p, opened, closed, _ in key.AFTER_TAKE_OVER_CALLS
    ]
    for state, call in zip(rows, key.AFTER_TAKE_OVER_CALLS, strict=True):
        assert dict(zip(CALL_NAMES, state[7:], strict=True)) == call[7]


def _apply(store: Store, claim: Claim, setup: str) -> None:
    for name, args in key.STATE_SETUPS[setup]:
        getattr(store, name)(claim, **args)


def _running(store: Store, setup: str | None, run_id: str | None = None) -> Claim:
    claim = store.create_run(**(_create() if run_id is None else _create(run_id=run_id)))
    store.start_run(claim)
    if setup is not None:
        _apply(store, claim, setup)
    return claim


def _setup_for(call: str) -> str:
    return "replied" if call == "record_verdict" else "open"


@pytest.mark.parametrize(
    ("setup", "call"),
    [row[1:] for row in key.STATE_CONFLICTS],
    ids=[row[0] for row in key.STATE_CONFLICTS],
)
def test_a_state_that_does_not_allow_the_write_is_a_conflict(
    tmp_path: Path, store: Store, ticker: Ticker, setup: str, call: str
) -> None:
    claim = _running(store, setup)
    _refused(tmp_path, store, ticker, claim, call, key.STATE_CALLS[call], "StoreConflict")


def test_a_verdict_for_another_reply_is_a_conflict(
    tmp_path: Path, store: Store, ticker: Ticker
) -> None:
    claim = _running(store, "replied")
    _refused(
        tmp_path, store, ticker, claim, "record_verdict", key.OTHER_HASH_VERDICT, "StoreConflict"
    )


@pytest.mark.parametrize(
    ("setup", "request_number", "error", "number", "written"),
    [row[1:] for row in key.OPEN_ATTEMPT_REPEATS],
    ids=[row[0] for row in key.OPEN_ATTEMPT_REPEATS],
)
def test_open_attempt_after_each_state(
    tmp_path: Path,
    store: Store,
    ticker: Ticker,
    setup: str,
    request_number: int,
    error: str | None,
    number: int | None,
    written: bool,
) -> None:
    claim = _running(store, setup)
    before, events, ticker.calls = _dump(tmp_path), _events(store), 0
    assert _try(lambda: store.open_attempt(claim, **_attempt("CP-1", request_number))) == (
        error,
        number,
    )
    if not written:
        assert (ticker.calls, _dump(tmp_path)) == (0, before)
        return
    assert ticker.calls == 1
    assert _events(store) == [*events, ("attempt_opened", "CP-1", number, {})]


@pytest.mark.parametrize(
    ("first", "second", "calls"),
    [row[1:] for row in key.TWO_RUNS_STATES],
    ids=[row[0] for row in key.TWO_RUNS_STATES],
)
def test_attempt_lookups_are_per_run(
    store: Store, first: str, second: str, calls: tuple[Any, ...]
) -> None:
    claims = {"A": _running(store, None), "B": _running(store, None, key.SECOND_RUN_ID)}
    _apply(store, claims["A"], first)
    _apply(store, claims["B"], second)
    for name, run, args, error in calls:
        assert _outcome(partial(_write, store, name, claims[run], args)) == error


def _write(store: Store, name: str, claim: Claim, args: Any) -> None:
    getattr(store, name)(claim, **args)


def _refused_rows(
    rows: tuple[tuple[str, str, dict[str, object]], ...],
) -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        ("name", "args"), [row[1:] for row in rows], ids=[row[0] for row in rows]
    )


@_refused_rows(key.REFUSED_ARGUMENTS_3C1)
def test_refused_arguments(
    tmp_path: Path, store: Store, ticker: Ticker, name: str, args: Any
) -> None:
    claim = _running(store, _setup_for(name))
    _refused(tmp_path, store, ticker, claim, name, args, "StoreRefused")


@_refused_rows(key.MISSING_3C1)
def test_an_attempt_the_run_does_not_have_is_refused(
    tmp_path: Path, store: Store, ticker: Ticker, name: str, args: Any
) -> None:
    claim = _running(store, "open")
    _refused(tmp_path, store, ticker, claim, name, args, "StoreRefused")


@pytest.mark.parametrize(
    ("name", "args"), key.MISSING_RUN_3C1, ids=[row[0] for row in key.MISSING_RUN_3C1]
)
def test_a_missing_run_is_refused(
    tmp_path: Path, store: Store, ticker: Ticker, name: str, args: Any
) -> None:
    _running(store, _setup_for(name))
    claim = Claim(key.MISSING_RUN_ID, status_key.FOREIGN_TOKEN)
    _refused(tmp_path, store, ticker, claim, name, args, "StoreRefused")


@pytest.mark.parametrize("status", [s for s in key.NOT_RUNNING if s not in ("created", "rejected")])
@_refused_rows(key.NOT_RUNNING_3C1)
def test_a_run_that_is_not_running_takes_no_write(
    tmp_path: Path, store: Store, ticker: Ticker, status: str, name: str, args: Any
) -> None:
    claim = _running(store, _setup_for(name))
    store.end_run(claim, status=status, reason="x")
    _refused(tmp_path, store, ticker, claim, name, args, "StoreConflict")


@pytest.mark.parametrize(
    ("call", "args", "text"),
    [row[1:] for row in key.ACCEPTED_EDGES_3C1],
    ids=[row[0] for row in key.ACCEPTED_EDGES_3C1],
)
def test_accepted_edges_store_the_keyed_text(
    tmp_path: Path, store: Store, ticker: Ticker, call: str, args: Any, text: str
) -> None:
    claim = _running(store, _setup_for(call))
    events, ticker.calls = len(_events(store)), 0
    getattr(store, call)(claim, **args)
    assert ticker.calls == 1
    assert len(_events(store)) == events + 1
    column = "fail_reason" if call == "fail_attempt" else "issues"
    assert _query(tmp_path, f"SELECT {column} FROM attempts") == [(text,)]


@pytest.mark.parametrize("name", THREE_WRITES)
def test_an_old_claim_writes_nothing(
    tmp_path: Path, store: Store, ticker: Ticker, name: str
) -> None:
    old = _running(store, _setup_for(name))
    store.claim_run(RUN_ID)
    _refused(tmp_path, store, ticker, old, name, key.STATE_CALLS[name], "StoreFenced")
