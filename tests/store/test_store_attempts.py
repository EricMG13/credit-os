import itertools
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Any

import pytest
import store_attempts_key as key
import store_status_key as status_key
from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule, run_state_machine_as_test
from test_store_status import RUN_ID, Ticker, _call, _create, _dump, _outcome, _query

from credit_os.store import runs
from credit_os.store.db import Store, open_store
from credit_os.store.errors import StoreError
from credit_os.store.records import Claim

TIMES = {n: f"2026-09-30T12:00:{n:02d}.000000Z" for n in range(1, len(key.SCRIPT_3B1) + 1)}
WRITES = ("open_attempt", "open_call")
ATTEMPT_COLUMNS = (
    "SELECT module_id, attempt, state, request, request_sha256, reply, reply_sha256, issues,"
    " fail_reason, opened_at, replied_at, closed_at FROM attempts ORDER BY module_id, attempt"
)
CALL_COLUMNS = "SELECT * FROM calls ORDER BY module_id, attempt, call_index"
CALL_COLUMN_COUNT = 24  # run_id, the key (3), exchange, provider index, hold, 2 times, 15 reply


@pytest.fixture
def ticker() -> Ticker:
    return Ticker()


@pytest.fixture
def store(tmp_path: Path, ticker: Ticker) -> Iterator[Store]:
    with open_store(tmp_path, clock=ticker) as opened:
        yield opened


def _try(call: Callable[[], object]) -> tuple[str | None, object]:
    """The store error class the call raises (or None), and what it returned."""
    try:
        value = call()
    except StoreError as error:
        return type(error).__name__, None
    return None, value


def _step(store: Store, claims: dict[int, Claim], name: str, number: int, args: Any) -> object:
    if name in WRITES:
        return getattr(store, name)(claims[number], **args)
    _call(store, claims, name, number, args)
    return None


def _attempt(module: str, request: int) -> dict[str, Any]:
    return dict(key._attempt(module, request))


def _call_args(module: str, attempt: int, exchange: str, provider: int) -> dict[str, Any]:
    return dict(key._call(module, attempt, exchange, provider))


def _running(store: Store) -> Claim:
    claim = store.create_run(**_create())
    store.start_run(claim)
    return claim


def _open(store: Store, claim: Claim) -> Claim:
    """A running run whose CP-1 attempt 1 is open with REQUESTS[1] and no call."""
    store.open_attempt(claim, **_attempt("CP-1", 1))
    return claim


def test_scripted_run(tmp_path: Path, store: Store, ticker: Ticker) -> None:
    claims: dict[int, Claim] = {}
    for row, (name, number, args, expected) in enumerate(key.SCRIPT_3B1, 1):
        before, ticker.row, ticker.calls = _dump(tmp_path), row, 0
        error, value = _try(partial(_step, store, claims, name, number, args))
        assert error == expected, row
        assert value == key.SCRIPT_3B1_RETURNS.get(row), row
        if expected is None and row not in key.NO_WRITE_ROWS:
            assert ticker.calls == 1, row
        else:
            assert (ticker.calls, _dump(tmp_path)) == (0, before), row
    assert store.run(RUN_ID).status == key.AFTER_3B1_STATUS
    events = [(e.kind, e.module_id, e.attempt, dict(e.detail)) for e in store.events(RUN_ID)]
    assert events == list(key.AFTER_3B1_EVENTS)
    assert _query(tmp_path, "SELECT seq, at FROM events ORDER BY seq") == [
        (seq, TIMES[row]) for seq, row in enumerate(key.AFTER_3B1_EVENT_ROWS, 1)
    ]
    assert _query(tmp_path, ATTEMPT_COLUMNS) == [
        (
            module,
            number,
            state,
            key.REQUESTS[request],
            key.REQUEST_SHA256[request],
            None,
            None,
            None,
            None,
            TIMES[opened],
            None,
            None,
        )
        for module, number, state, request, opened in key.AFTER_3B1_ATTEMPTS
    ]
    calls = _query(tmp_path, CALL_COLUMNS)
    assert [row[1:9] for row in calls] == [
        (module, number, index, exchange, provider, key.HOLD_TEXT, TIMES[opened], None)
        for module, number, index, exchange, provider, opened, _, _ in key.AFTER_3B1_CALLS
    ]
    assert all(len(row) == CALL_COLUMN_COUNT and set(row[9:]) == {None} for row in calls)


@pytest.mark.parametrize(("hold", "text"), key.HOLDS, ids=[text for _, text in key.HOLDS])
def test_a_hold_is_stored_as_the_codec_text(
    store: Store, tmp_path: Path, hold: Any, text: str
) -> None:
    claim = _open(store, _running(store))
    store.open_call(claim, **{**_call_args("CP-1", 1, "ex-1", 0), "hold_usd": hold})
    assert _query(tmp_path, "SELECT hold_usd FROM calls") == [(text,)]


def _refused(
    tmp_path: Path, store: Store, ticker: Ticker, claim: Claim, name: str, args: Any, expected: str
) -> None:
    before, ticker.calls = _dump(tmp_path), 0
    assert _outcome(lambda: getattr(store, name)(claim, **args)) == expected
    assert (ticker.calls, _dump(tmp_path)) == (0, before)


@pytest.mark.parametrize(
    ("name", "args"),
    [row[1:] for row in key.REFUSED_ARGUMENTS],
    ids=[row[0] for row in key.REFUSED_ARGUMENTS],
)
def test_refused_arguments(
    tmp_path: Path, store: Store, ticker: Ticker, name: str, args: Any
) -> None:
    claim = _open(store, _running(store))
    _refused(tmp_path, store, ticker, claim, name, args, "StoreRefused")


@pytest.mark.parametrize(
    ("name", "args"), [row[1:] for row in key.MISSING], ids=[row[0] for row in key.MISSING]
)
def test_an_attempt_the_run_does_not_have_is_refused(
    tmp_path: Path, store: Store, ticker: Ticker, name: str, args: Any
) -> None:
    claim = _open(store, _running(store))
    _refused(tmp_path, store, ticker, claim, name, args, "StoreRefused")


@pytest.mark.parametrize("name", [row[0] for row in key.MISSING_RUN_CALLS])
def test_a_missing_run_is_refused(tmp_path: Path, store: Store, ticker: Ticker, name: str) -> None:
    _open(store, _running(store))
    args = dict(key.MISSING_RUN_CALLS)[name]
    claim = Claim(key.MISSING_RUN_ID, status_key.FOREIGN_TOKEN)
    _refused(tmp_path, store, ticker, claim, name, args, "StoreRefused")


@pytest.mark.parametrize("status", key.NOT_RUNNING)
@pytest.mark.parametrize(
    ("name", "args"),
    [row[1:] for row in key.NOT_RUNNING_CALLS],
    ids=[row[0] for row in key.NOT_RUNNING_CALLS],
)
def test_a_run_that_is_not_running_takes_no_write(
    tmp_path: Path, store: Store, ticker: Ticker, status: str, name: str, args: Any
) -> None:
    claim = store.create_run(**_create())
    if status == "rejected":
        store.reject_run(claim, reason="x")
    elif status != "created":
        store.start_run(claim)
        _open(store, claim)
        store.end_run(claim, status=status, reason="x")
    _refused(tmp_path, store, ticker, claim, name, args, "StoreConflict")


def test_the_call_is_committed_before_open_call_returns(store: Store, tmp_path: Path) -> None:
    claim = _open(store, _running(store))
    assert store.open_call(claim, **_call_args("CP-1", 1, "ex-1", 0)) == 0
    assert _query(tmp_path, "SELECT module_id, attempt, call_index, exchange_id FROM calls") == [
        ("CP-1", 1, 0, "ex-1")
    ]


def test_the_attempt_kinds_are_state_kinds() -> None:
    assert runs.STATE_KINDS == status_key.STATE_KINDS


@pytest.mark.parametrize("kind", key.REFUSED_NOTE_KINDS)
def test_record_event_refuses_an_attempt_kind(
    tmp_path: Path, store: Store, ticker: Ticker, kind: str
) -> None:
    claim = _open(store, _running(store))
    before, ticker.calls = _dump(tmp_path), 0
    refused = _outcome(
        lambda: store.record_event(claim, kind=kind, detail={}, module_id="CP-1", attempt=1)
    )
    assert refused == "StoreRefused"
    assert (ticker.calls, _dump(tmp_path)) == (0, before)


class _Machine(RuleBasedStateMachine):
    """One store against the answer key's model of attempts and calls."""

    def __init__(self, folder: Path) -> None:
        super().__init__()
        self.folder = folder
        ticks = itertools.count(1)
        start = datetime(2026, 9, 30, tzinfo=UTC)
        self.store = open_store(folder, clock=lambda: start + timedelta(seconds=next(ticks)))
        self.model = key.AttemptsModel()
        self.model.create()
        self.claims = {1: self.store.create_run(**_create())}
        self.actual: str | None = None
        self.expected: str | None = None
        self.returned: object = None
        self.expected_return: object = None

    def _claim(self, data: st.DataObject) -> tuple[int, Claim]:
        number = data.draw(st.integers(1, self.model.token + 1))
        return number, self.claims.get(number, Claim(RUN_ID, status_key.FOREIGN_TOKEN))

    @rule()
    def claim(self) -> None:
        made: list[Claim] = []
        self.expected, self.expected_return = self.model.claim(), None
        self.actual, _ = _try(lambda: made.append(self.store.claim_run(RUN_ID)))
        self.returned = None
        if made:
            self.claims[self.model.token] = made[0]

    @rule(data=st.data())
    def start(self, data: st.DataObject) -> None:
        number, claim = self._claim(data)
        self.actual, self.returned = _try(lambda: self.store.start_run(claim))
        self.expected, self.expected_return = self.model.start(number), None

    @rule(data=st.data(), end=st.sampled_from(sorted(status_key.END_STATUSES)))
    def end(self, data: st.DataObject, end: str) -> None:
        number, claim = self._claim(data)
        self.actual, self.returned = _try(lambda: self.store.end_run(claim, status=end, reason="x"))
        self.expected, self.expected_return = self.model.end(number, end, "x"), None

    @rule(data=st.data(), module=st.sampled_from(["CP-1", "CP-2"]), request=st.sampled_from([1, 2]))
    def open_attempt(self, data: st.DataObject, module: str, request: int) -> None:
        number, claim = self._claim(data)
        self.actual, self.returned = _try(
            lambda: self.store.open_attempt(claim, module_id=module, request=key.REQUESTS[request])
        )
        self.expected, self.expected_return = self.model.open_attempt(
            number, module, key.REQUESTS[request]
        )

    @rule(
        data=st.data(),
        module=st.sampled_from(["CP-1", "CP-2"]),
        attempt=st.sampled_from([1, 2]),
        exchange=st.sampled_from(["ex-1", "ex-2"]),
        provider=st.sampled_from([0, 1]),
    )
    def open_call(
        self, data: st.DataObject, module: str, attempt: int, exchange: str, provider: int
    ) -> None:
        number, claim = self._claim(data)
        args = _call_args(module, attempt, exchange, provider)
        self.actual, self.returned = _try(lambda: self.store.open_call(claim, **args))
        self.expected, self.expected_return = self.model.open_call(
            number, module, attempt, exchange, provider
        )

    @invariant()
    def agrees_with_the_model(self) -> None:
        assert (self.actual, self.returned) == (self.expected, self.expected_return)
        assert self.store.run(RUN_ID).status == self.model.status
        events = [
            (e.kind, e.module_id, e.attempt, dict(e.detail)) for e in self.store.events(RUN_ID)
        ]
        assert events == self.model.keyed_events()
        assert (
            self._rows(
                "SELECT module_id, attempt, state, request FROM attempts ORDER BY module_id, attempt"
            )
            == self.model.attempt_rows()
        )
        assert (
            self._rows(
                "SELECT module_id, attempt, call_index, exchange_id, provider_call_index,"
                " closed_at IS NULL FROM calls ORDER BY module_id, attempt, call_index"
            )
            == self.model.call_rows()
        )

    def _rows(self, sql: str) -> list[tuple[Any, ...]]:
        return _query(self.folder, sql)

    def teardown(self) -> None:
        self.store.close()


def test_the_store_follows_the_model(tmp_path: Path) -> None:
    folders = itertools.count()

    run: Any = run_state_machine_as_test  # hypothesis ships it untyped
    run(
        lambda: _Machine(tmp_path / f"m{next(folders)}"),
        settings=settings(max_examples=50, stateful_step_count=20, deadline=None),
    )
