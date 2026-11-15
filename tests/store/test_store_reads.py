import sqlite3
from collections.abc import Iterator, Mapping, MutableMapping
from contextlib import closing
from functools import partial
from pathlib import Path
from typing import Any, cast

import pytest
import store_attempts_key as key
import store_reply_key as reply_key
from test_store_attempts import _attempt, _call_args, _try
from test_store_close import _close_args, _step3, _with_call
from test_store_replies import _apply, _replay, _running
from test_store_status import RUN_ID, Ticker, _create, _outcome

from credit_os.provider.types import Compaction
from credit_os.store import location
from credit_os.store.db import Store, StoreReader, open_reader, open_store
from credit_os.store.records import AttemptRecord, CallRecord, Charges, Claim, CompactionRecord

SHA_OF_REPLY = {key.REPLIES[n]: key.REPLY_SHA256[n] for n in key.REPLIES}
READS = ("attempts", "charges")


@pytest.fixture
def ticker() -> Ticker:
    return Ticker()


@pytest.fixture
def store(tmp_path: Path, ticker: Ticker) -> Iterator[Store]:
    with open_store(tmp_path, clock=ticker) as opened:
        yield opened


def _handles(tmp_path: Path, store: Store) -> Iterator[Store | StoreReader]:
    yield store
    with open_reader(tmp_path) as reader:
        yield reader


def _fields(columns: dict[str, object]) -> dict[str, Any]:
    return dict(key.call_fields(columns))


def _plain(issues: tuple[dict[str, object], ...] | None) -> Any:
    return issues


def _calls(
    rows: tuple[tuple[str, int, int, str, int, int, int | None, dict[str, object]], ...],
) -> tuple[CallRecord, ...]:
    return tuple(
        CallRecord(
            RUN_ID,
            module,
            attempt,
            index,
            exchange,
            provider,
            key.HOLD,
            key.at(opened),
            None if closed is None else key.at(closed),
            **_fields(columns),
        )
        for module, attempt, index, exchange, provider, opened, closed, columns in rows
    )


def _money(charges: Charges) -> list[str | None]:
    """The money texts, so a changed exponent shows where == would not."""
    out: list[str | None] = []
    for call in charges.calls:
        out += [str(call.hold_usd), None if call.billed_usd is None else str(call.billed_usd)]
    for record in charges.compactions:
        billed = record.compaction.billed_usd
        out.append(None if billed is None else str(billed))
    return out


def _expected_money(
    calls: tuple[CallRecord, ...], compactions: tuple[Compaction, ...]
) -> list[Any]:
    out: list[str | None] = []
    for call in calls:
        out += [key.HOLD_TEXT, None if call.billed_usd is None else str(call.billed_usd)]
    for compaction in compactions:
        out.append(None if compaction.billed_usd is None else str(compaction.billed_usd))
    return out


def test_attempts_after_the_scripted_run(tmp_path: Path, store: Store, ticker: Ticker) -> None:
    _replay(tmp_path, store, ticker, key.SCRIPT_3C1, key.SCRIPT_3C1_RETURNS)
    expected = tuple(
        AttemptRecord(
            RUN_ID,
            module,
            number,
            key.REQUESTS[request],
            key.REQUEST_SHA256[request],
            state,
            reply,
            None if reply is None else SHA_OF_REPLY[reply],
            _plain(issues),
            reason,
            opened,
            replied,
            closed,
        )
        for module, number, request, state, reply, issues, reason, opened, replied, closed in (
            key.READ_3C1_ATTEMPTS
        )
    )
    for handle in _handles(tmp_path, store):
        got = handle.attempts(RUN_ID)
        assert got == expected
        assert isinstance(got, tuple)
        for record in got:
            assert record.issues is None or isinstance(record.issues, tuple)
            for issue in record.issues or ():
                assert isinstance(issue, Mapping)
                assert not isinstance(issue, MutableMapping)
                writable: Any = issue
                with pytest.raises(TypeError):
                    writable["code"] = "x"


def test_charges_after_the_scripted_run(tmp_path: Path, store: Store, ticker: Ticker) -> None:
    _replay(tmp_path, store, ticker, key.SCRIPT_3C1, key.SCRIPT_3C1_RETURNS)
    expected = _calls(key.AFTER_3C1_CALLS)
    for handle in _handles(tmp_path, store):
        got = handle.charges(RUN_ID)
        assert got == Charges(expected, ())
        assert _money(got) == _expected_money(expected, ())


def test_charges_after_the_scripted_close_run(tmp_path: Path, store: Store, ticker: Ticker) -> None:
    claims: dict[int, Claim] = {}
    for row, (name, number, args, error) in enumerate(key.SCRIPT_3B2B, 1):
        ticker.row = row
        assert _try(partial(_step3, store, claims, name, number, args))[0] == error, row
    expected = _calls(key.AFTER_3B2B_CALLS)
    compactions = tuple(
        CompactionRecord(
            RUN_ID,
            position,
            None if call is None else call[0],
            None if call is None else call[1],
            None if call is None else call[2],
            compaction,
        )
        for position, call, compaction in key.READ_3B2B_COMPACTIONS
    )
    for handle in _handles(tmp_path, store):
        got = handle.charges(RUN_ID)
        assert got == Charges(expected, compactions)
        assert _money(got) == _expected_money(expected, tuple(c.compaction for c in compactions))


@pytest.mark.parametrize(
    ("reply", "call", "rows"),
    [row[1:] for row in reply_key.CASES],
    ids=[row[0] for row in reply_key.CASES],
)
def test_every_reply_kind_reads_back(
    tmp_path: Path,
    store: Store,
    ticker: Ticker,
    reply: Any,
    call: dict[str, object],
    rows: tuple[dict[str, object], ...],
) -> None:
    claim = _with_call(store)
    ticker.row = 2
    store.close_call(claim, **_close_args(reply))
    expected_call = CallRecord(
        RUN_ID,
        "CP-1",
        1,
        0,
        "ex-1",
        0,
        key.HOLD,
        key.at(1),
        key.at(2),
        **_fields(call),
    )
    compactions = tuple(
        CompactionRecord(RUN_ID, cast(int, row["position"]), "CP-1", 1, 0, key.compaction_of(row))
        for row in rows
    )
    for handle in _handles(tmp_path, store):
        got = handle.charges(RUN_ID)
        assert got == Charges((expected_call,), compactions)
        assert _money(got) == _expected_money(
            (expected_call,), tuple(c.compaction for c in compactions)
        )


def _running_run(store: Store) -> Claim:
    return _running(store, None)


def test_order_is_binary_text_order(tmp_path: Path, store: Store) -> None:
    claim = _running_run(store)
    for module in key.READ_ORDER_MODULES:
        store.open_attempt(claim, **_attempt(module, 1))
    second = key.READ_ORDER_MODULES[1]
    fail: dict[str, Any] = dict(key._fail(second, 1))
    store.fail_attempt(claim, **fail)
    store.open_attempt(claim, **_attempt(second, 1))
    store.open_call(claim, **_call_args("m-b", 1, "ex-1", 0))
    store.open_call(claim, **_call_args("m-a", 1, "ex-1", 1))
    for handle in _handles(tmp_path, store):
        assert [(a.module_id, a.attempt) for a in handle.attempts(RUN_ID)] == list(
            key.READ_ORDER_AFTER
        )
        assert [(c.module_id, c.attempt, c.call_index) for c in handle.charges(RUN_ID).calls] == (
            list(key.READ_ORDER_CALLS)
        )


def test_compactions_are_ordered_by_position(tmp_path: Path, store: Store) -> None:
    claim = _running_run(store)
    store.open_attempt(claim, **_attempt("CP-1", 1))
    store.record_compactions(claim, [key.FINISHED])
    store.record_compactions(claim, [key.UNFINISHED])
    for handle in _handles(tmp_path, store):
        got = handle.charges(RUN_ID).compactions
        assert [(c.position, c.compaction) for c in got] == [
            (0, key.FINISHED),
            (1, key.UNFINISHED),
        ]


def test_reads_are_per_run(tmp_path: Path, store: Store, ticker: Ticker) -> None:
    _replay(tmp_path, store, ticker, key.SCRIPT_3C1, key.SCRIPT_3C1_RETURNS)
    before = store.attempts(RUN_ID), store.charges(RUN_ID)
    ticker.row = 30
    claim = _running(store, None, key.SECOND_RUN_ID)
    _apply(store, claim, "open with call 0")
    for handle in _handles(tmp_path, store):
        [attempt] = handle.attempts(key.SECOND_RUN_ID)
        assert (attempt.run_id, attempt.module_id, attempt.attempt, attempt.state) == (
            key.SECOND_RUN_ID,
            "CP-1",
            1,
            "open",
        )
        [call] = handle.charges(key.SECOND_RUN_ID).calls
        assert (call.run_id, call.call_index, call.exchange_id, call.kind) == (
            key.SECOND_RUN_ID,
            0,
            "ex-1",
            None,
        )
        assert call.usage is None
        assert (handle.attempts(RUN_ID), handle.charges(RUN_ID)) == before
        assert len(before[0]) == 3
        assert len(before[1].calls) == 4


@pytest.mark.parametrize(
    ("run_id", "error"),
    [row[1:] for row in key.READ_REFUSED],
    ids=[row[0] for row in key.READ_REFUSED],
)
@pytest.mark.parametrize("read", READS)
def test_a_read_of_no_run_is_refused(
    tmp_path: Path, store: Store, read: str, run_id: object, error: str
) -> None:
    _running_run(store)
    for handle in _handles(tmp_path, store):
        assert _outcome(partial(getattr(handle, read), run_id)) == error


def test_a_run_with_no_attempt_reads_empty(tmp_path: Path, store: Store) -> None:
    store.create_run(**_create())
    for handle in _handles(tmp_path, store):
        assert handle.attempts(RUN_ID) == ()
        assert handle.charges(RUN_ID) == Charges((), ())


SETUPS = {"replied": "replied", "open call": "open with call 0"}


@pytest.mark.parametrize(
    ("setup", "sql", "parameters", "refused"),
    [row[1:] for row in key.READ_CORRUPT],
    ids=[row[0] for row in key.READ_CORRUPT],
)
def test_a_stored_value_the_reader_refuses_is_corrupt(
    tmp_path: Path, store: Store, setup: str, sql: str, parameters: tuple[object, ...], refused: str
) -> None:
    claim = _running_run(store)
    _apply(store, claim, SETUPS[setup])
    with closing(sqlite3.connect(tmp_path / location.STATE_FILE_NAME)) as raw:
        raw.execute(sql, (RUN_ID, *parameters))
        raw.commit()
    other = next(name for name in READS if name != refused)
    for handle in _handles(tmp_path, store):
        assert _outcome(partial(getattr(handle, refused), RUN_ID)) == "StoreCorrupt"
        getattr(handle, other)(RUN_ID)
