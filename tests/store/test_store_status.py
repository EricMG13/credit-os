import itertools
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import closing
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Any

import pytest
import store_runs_key as runs_key
import store_status_key as key
from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule, run_state_machine_as_test

from credit_os.sources.pins import SourceKind, SourcePin
from credit_os.store import errors, location
from credit_os.store.db import Store, open_store
from credit_os.store.errors import StoreError
from credit_os.store.records import Claim

RUN_ID = "run-001"
METHODS = {"start": "start_run", "reject": "reject_run", "end": "end_run", "note": "record_event"}
ARGS: dict[str, dict[str, Any]] = {  # one valid call of each write method, after create (or start)
    "create": {"run_id": "run-002"},
    "claim": {},
    "start": {},
    "reject": {"reason": "x"},
    "end": {"status": "failed", "reason": "x"},
    "note": {"kind": "x", "detail": {}},
}
NAME = r"[a-z][a-z0-9_]{0,63}"


class Ticker:
    """A clock that answers `row` as the seconds of 2026-09-30 12:00 and counts its calls."""

    def __init__(self) -> None:
        self.row = 1
        self.calls = 0

    def __call__(self) -> datetime:
        self.calls += 1
        return datetime(2026, 9, 30, 12, 0, self.row, tzinfo=UTC)


def _create(**override: object) -> dict[str, Any]:
    pins = tuple(
        SourcePin(name=n, sha256=s, size_bytes=z, kind=SourceKind(k))
        for n, s, z, k in runs_key.PINS
    )
    return {**runs_key.CREATE, "pins": pins, **override}


def _outcome(call: Callable[[], object]) -> str | None:
    """The class name of the store error the call raises, or None."""
    try:
        call()
    except StoreError as error:
        return type(error).__name__
    return None


def _call(
    store: Store, claims: dict[int, Claim], name: str, number: int, args: dict[str, Any]
) -> None:
    """Run one SCRIPT-shaped call; a create or a claim keeps the claim it returns."""
    if name == "create":
        claims[1] = store.create_run(**{**_create(), **args})
    elif name == "claim":
        claims[number] = store.claim_run(**{"run_id": RUN_ID, **args})
    else:
        getattr(store, METHODS[name])(claims[number], **args)


def _query(folder: Path, sql: str) -> list[tuple[Any, ...]]:
    with closing(sqlite3.connect(folder / location.STATE_FILE_NAME)) as raw:
        return raw.execute(sql).fetchall()


def _dump(folder: Path) -> list[str]:
    with closing(sqlite3.connect(folder / location.STATE_FILE_NAME)) as raw:
        return list(raw.iterdump())


@pytest.fixture
def ticker() -> Ticker:
    return Ticker()


@pytest.fixture
def store(tmp_path: Path, ticker: Ticker) -> Iterator[Store]:
    with open_store(tmp_path, clock=ticker) as opened:
        yield opened


def _kinds(store: Store) -> list[tuple[str, dict[str, Any]]]:
    return [(e.kind, dict(e.detail)) for e in store.events(RUN_ID)]


def test_scripted_run(tmp_path: Path, store: Store, ticker: Ticker) -> None:
    claims: dict[int, Claim] = {}
    for row, (name, number, args, expected) in enumerate(key.SCRIPT, 1):
        before, ticker.row, ticker.calls = _dump(tmp_path), row, 0
        assert _outcome(partial(_call, store, claims, name, number, args)) == expected, row
        if expected is None:
            assert ticker.calls == 1, row
        else:
            assert (ticker.calls, _dump(tmp_path)) == (0, before), row
    run = store.run(RUN_ID)
    assert (run.status, run.end_reason, run.end_message) == (
        key.AFTER_SCRIPT_STATUS,
        key.AFTER_SCRIPT_END_REASON,
        None,
    )
    times = key.SCRIPT_ROW_TIMES
    assert _query(tmp_path, "SELECT started_at, ended_at FROM runs") == [
        (times[key.STARTED_AT_CALL], times[key.ENDED_AT_CALL])
    ]
    assert _kinds(store) == list(key.AFTER_SCRIPT_EVENTS)
    assert _query(tmp_path, "SELECT seq, at FROM events ORDER BY seq") == [
        (seq, times[row]) for seq, row in enumerate(key.AFTER_SCRIPT_EVENT_ROWS, 1)
    ]
    assert key.fold(_kinds(store)) == run.status


def _in_state(store: Store, name: str) -> dict[int, Claim]:
    """The run created; started too for the calls that need a running run."""
    claims = {1: store.create_run(**_create())}
    if name in ("end", "note"):
        store.start_run(claims[1])
    return claims


@pytest.mark.parametrize(
    ("name", "args"),
    [row[1:] for row in key.REFUSED_ARGUMENTS],
    ids=[r[0] for r in key.REFUSED_ARGUMENTS],
)
def test_refused_arguments(
    tmp_path: Path, store: Store, ticker: Ticker, name: str, args: Any
) -> None:
    claims = _in_state(store, name)
    before, ticker.calls = _dump(tmp_path), 0
    assert _outcome(lambda: _call(store, claims, name, 1, args)) == "StoreRefused"
    assert (ticker.calls, _dump(tmp_path)) == (0, before)


@pytest.mark.parametrize(
    ("run_id", "token"),
    [row[1:] for row in key.REFUSED_CLAIMS],
    ids=[r[0] for r in key.REFUSED_CLAIMS],
)
def test_refused_claims(
    tmp_path: Path, store: Store, ticker: Ticker, run_id: Any, token: Any
) -> None:
    store.create_run(**_create())
    before, ticker.calls = _dump(tmp_path), 0
    claim = Claim(RUN_ID if run_id is None else run_id, token)
    assert _outcome(partial(store.start_run, claim)) == "StoreRefused"
    assert (ticker.calls, _dump(tmp_path)) == (0, before)


def test_not_a_claim(tmp_path: Path, store: Store, ticker: Ticker) -> None:
    store.create_run(**_create())
    before, ticker.calls = _dump(tmp_path), 0
    not_a_claim: Any = key.NOT_A_CLAIM
    assert _outcome(lambda: store.start_run(not_a_claim)) == "StoreRefused"
    assert (ticker.calls, _dump(tmp_path)) == (0, before)


def test_a_missing_run_is_refused_before_the_token(
    tmp_path: Path, store: Store, ticker: Ticker
) -> None:
    assert _outcome(lambda: store.claim_run(RUN_ID)) == "StoreRefused"
    assert _outcome(lambda: store.start_run(Claim(RUN_ID, key.FOREIGN_TOKEN))) == "StoreRefused"
    assert (ticker.calls, _query(tmp_path, "SELECT count(*) FROM events")) == (0, [(0,)])


def test_a_token_that_is_not_the_writer_is_fenced(
    tmp_path: Path, store: Store, ticker: Ticker
) -> None:
    mine = store.create_run(**_create())
    other = store.create_run(**_create(run_id="run-002"))
    claims = [
        Claim(RUN_ID, key.FOREIGN_TOKEN),
        Claim(RUN_ID, other.token),
        Claim("run-002", mine.token),
    ]
    before, ticker.calls = _dump(tmp_path), 0
    for claim in claims:
        assert _outcome(partial(store.start_run, claim)) == "StoreFenced"
    assert (ticker.calls, _dump(tmp_path)) == (0, before)


@pytest.mark.parametrize("name", sorted(METHODS))
def test_the_earlier_holder_is_fenced_after_a_claim(
    tmp_path: Path, store: Store, ticker: Ticker, name: str
) -> None:
    claims = _in_state(store, "end")
    store.claim_run(RUN_ID)
    args = ARGS[name]
    before, ticker.calls = _dump(tmp_path), 0
    assert _outcome(lambda: _call(store, claims, name, 1, args)) == "StoreFenced"
    assert (ticker.calls, _dump(tmp_path)) == (0, before)


def test_a_resume_clears_the_end(tmp_path: Path, store: Store, ticker: Ticker) -> None:
    claim = store.create_run(**_create())
    ticker.row = 2
    store.start_run(claim)
    ticker.row = 3
    store.end_run(claim, status="stopped", reason="cap_reached", message=key.END_MESSAGE)
    ended = "SELECT status, end_reason, end_message, ended_at FROM runs"
    assert _query(tmp_path, ended) == [
        ("stopped", "cap_reached", key.END_MESSAGE_STORED, key.SCRIPT_ROW_TIMES[3])
    ]
    assert store.run(RUN_ID).end_message == key.END_MESSAGE_STORED
    ticker.row = 4
    store.start_run(claim)
    assert _query(tmp_path, ended) == [("running", None, None, None)]
    assert _query(tmp_path, "SELECT started_at FROM runs") == [(key.SCRIPT_ROW_TIMES[2],)]


@pytest.mark.parametrize(
    ("kind", "detail", "module_id", "attempt"),
    [row[1:] for row in key.ACCEPTED_NOTES],
    ids=[r[0] for r in key.ACCEPTED_NOTES],
)
def test_a_note_is_stored_as_given(
    store: Store, kind: str, detail: Any, module_id: str | None, attempt: int | None
) -> None:
    claim = store.create_run(**_create())
    store.start_run(claim)
    store.record_event(claim, kind=kind, detail=detail, module_id=module_id, attempt=attempt)
    last = store.events(RUN_ID)[-1]
    assert (last.kind, last.module_id, last.attempt, dict(last.detail)) == (
        kind,
        module_id,
        attempt,
        detail,
    )


def test_a_reject_stores_its_message(store: Store) -> None:
    store.reject_run(
        store.create_run(**_create()), reason=key.REJECT_REASON, message=key.END_MESSAGE
    )
    run = store.run(RUN_ID)
    assert (run.status, run.end_reason, run.end_message) == (
        "rejected",
        key.REJECT_REASON,
        key.END_MESSAGE_STORED,
    )


@pytest.mark.parametrize("status", key.START_REFUSED_STATUSES)
def test_a_start_from_a_status_that_may_not_start_is_refused(
    tmp_path: Path, store: Store, ticker: Ticker, status: str
) -> None:
    claim = store.create_run(**_create())
    if status == "rejected":
        store.reject_run(claim, reason="x")
    else:
        store.start_run(claim)
    if status == "finished":
        store.end_run(claim, status="finished", reason="done")
    before, ticker.calls = _dump(tmp_path), 0
    assert _outcome(partial(store.start_run, claim)) == "StoreConflict"
    assert (ticker.calls, _dump(tmp_path)) == (0, before)


@pytest.mark.parametrize("call", key.HELD_LOCK_CALLS)
def test_a_held_lock_is_busy_and_writes_nothing(tmp_path: Path, ticker: Ticker, call: str) -> None:
    path = tmp_path / location.STATE_FILE_NAME
    with open_store(tmp_path, clock=ticker, busy_seconds=key.HELD_LOCK_BUSY_SECONDS) as held:
        claims = {1: held.create_run(**_create())}
        if call in ("end", "note"):
            held.start_run(claims[1])
        args = ARGS[call]
        before, ticker.calls = path.read_bytes(), 0
        raw = sqlite3.connect(path, autocommit=True, timeout=0)
        try:
            raw.execute("BEGIN IMMEDIATE")
            assert _outcome(lambda: _call(held, claims, call, 1, args)) == key.HELD_LOCK_ERROR
            assert ticker.calls == 0
        finally:
            try:
                raw.execute("ROLLBACK")
            finally:
                raw.close()
        assert path.read_bytes() == before


class _Machine(RuleBasedStateMachine):
    """One store against the answer key's model; each rule records what it got and expected."""

    def __init__(self, folder: Path) -> None:
        super().__init__()
        ticks = itertools.count(1)
        start = datetime(2026, 9, 30, tzinfo=UTC)
        self.store = open_store(folder, clock=lambda: start + timedelta(seconds=next(ticks)))
        self.model = key.Model()
        self.claims: dict[int, Claim] = {}
        self.actual: str | None = None
        self.expected: str | None = None

    def _claim(self, data: st.DataObject) -> tuple[int, Claim]:
        number = data.draw(st.integers(1, self.model.token + 1))
        return number, self.claims.get(number, Claim(RUN_ID, key.FOREIGN_TOKEN))

    @rule()
    def create(self) -> None:
        made: list[Claim] = []
        self.expected = self.model.create()
        self.actual = _outcome(lambda: made.append(self.store.create_run(**_create())))
        if made:
            self.claims[1] = made[0]

    @rule()
    def claim(self) -> None:
        made: list[Claim] = []
        self.expected = self.model.claim()
        self.actual = _outcome(lambda: made.append(self.store.claim_run(RUN_ID)))
        if made:
            self.claims[self.model.token] = made[0]

    @rule(data=st.data())
    def start(self, data: st.DataObject) -> None:
        number, claim = self._claim(data)
        self.actual = _outcome(lambda: self.store.start_run(claim))
        self.expected = self.model.start(number)

    @rule(data=st.data(), reason=st.from_regex(NAME, fullmatch=True))
    def reject(self, data: st.DataObject, reason: str) -> None:
        number, claim = self._claim(data)
        self.actual = _outcome(lambda: self.store.reject_run(claim, reason=reason))
        self.expected = self.model.reject(number, reason)

    @rule(
        data=st.data(),
        status=st.sampled_from(sorted(key.END_STATUSES)),
        reason=st.from_regex(NAME, fullmatch=True),
    )
    def end(self, data: st.DataObject, status: str, reason: str) -> None:
        number, claim = self._claim(data)
        self.actual = _outcome(lambda: self.store.end_run(claim, status=status, reason=reason))
        self.expected = self.model.end(number, status, reason)

    @rule(
        data=st.data(),
        kind=st.from_regex(NAME, fullmatch=True) | st.sampled_from(sorted(key.STATE_KINDS)),
        detail=st.dictionaries(
            st.text("abc", min_size=1, max_size=3),
            st.none() | st.integers(-5, 5) | st.text("xyz", max_size=3),
            max_size=3,
        ),
    )
    def note(self, data: st.DataObject, kind: str, detail: dict[str, Any]) -> None:
        number, claim = self._claim(data)
        self.actual = _outcome(lambda: self.store.record_event(claim, kind=kind, detail=detail))
        self.expected = self.model.note(number, kind, detail)

    @invariant()
    def agrees_with_the_model(self) -> None:
        assert self.actual == self.expected
        if self.model.status is None:
            assert _outcome(lambda: self.store.run(RUN_ID)) == "StoreRefused"
            return
        run, events = self.store.run(RUN_ID), _kinds(self.store)
        assert (run.status, events) == (self.model.status, self.model.events)
        assert (run.started_at is not None) == self.model.started
        assert key.fold(events) == run.status

    def teardown(self) -> None:
        self.store.close()


def test_the_store_follows_the_model(tmp_path: Path) -> None:
    folders = itertools.count()
    run: Any = run_state_machine_as_test  # hypothesis ships it untyped
    run(
        lambda: _Machine(tmp_path / f"m{next(folders)}"),
        settings=settings(max_examples=50, stateful_step_count=20, deadline=None),
    )


def test_every_error_class_is_exported() -> None:
    assert issubclass(errors.StoreFenced, StoreError)
