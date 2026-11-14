import dataclasses
import itertools
import re
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import store_runs_key as key

from credit_os.sources.pins import SourceKind, SourcePin
from credit_os.store import location, runs
from credit_os.store.db import Store, StoreReader, open_reader, open_store
from credit_os.store.errors import StoreConflict, StoreCorrupt, StoreRefused, StoreUnusable

RUN_ID = "run-001"
TABLES = ("runs", "run_sources", "events")
Clock = Callable[[], datetime | float]


def _steps() -> Clock:
    """A clock that starts at CLOCK_FIRST and moves one second on each call."""
    ticks = itertools.count()
    return lambda: key.CLOCK_FIRST + timedelta(seconds=next(ticks))


def _pins(rows: tuple[tuple[str, str, int, str], ...] = key.PINS) -> tuple[SourcePin, ...]:
    return tuple(
        SourcePin(name=name, sha256=sha, size_bytes=size, kind=SourceKind(kind))
        for name, sha, size, kind in rows
    )


def _args(**override: object) -> dict[str, Any]:
    return {**key.CREATE, "pins": _pins(), **override}


def _query(folder: Path, sql: str, *params: object) -> list[tuple[Any, ...]]:
    with closing(sqlite3.connect(folder / location.STATE_FILE_NAME)) as raw:
        return raw.execute(sql, params).fetchall()


def _write_raw(folder: Path, sql: str, *params: object) -> None:
    with closing(sqlite3.connect(folder / location.STATE_FILE_NAME, autocommit=True)) as raw:
        raw.execute(sql, params)


def _nothing_written(folder: Path) -> None:
    assert [_query(folder, f"SELECT count(*) FROM {table}") for table in TABLES] == [[(0,)]] * 3


@pytest.fixture
def store(tmp_path: Path) -> Iterator[Store]:
    with open_store(tmp_path, clock=_steps()) as opened:
        yield opened


@pytest.fixture(params=["store", "reader"])
def handle(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[Store | StoreReader]:
    """The same run read through the writer and through a read-only handle."""
    with open_store(tmp_path, clock=_steps()) as writer, open_reader(tmp_path) as reader:
        writer.create_run(**_args())
        yield writer if request.param == "store" else reader


def test_run_after_create(handle: Store | StoreReader) -> None:
    assert dataclasses.asdict(handle.run(RUN_ID)) == key.RUN_AFTER_CREATE


def test_events_after_create(handle: Store | StoreReader) -> None:
    events = handle.events(RUN_ID)
    assert [(e.seq, e.kind, e.module_id, e.attempt, dict(e.detail)) for e in events] == list(
        key.EVENTS_AFTER_CREATE
    )
    assert {(e.run_id, e.at) for e in events} == {(RUN_ID, key.CLOCK_FIRST)}
    detail: Any = events[0].detail
    with pytest.raises(TypeError):
        detail["x"] = "y"


def test_pins_after_create(handle: Store | StoreReader) -> None:
    pins = handle.pins(RUN_ID)
    assert [(p.name, p.sha256, p.size_bytes, p.kind) for p in pins] == list(key.PINS)


@pytest.mark.parametrize(
    ("clock_value", "text"),
    [(key.CLOCK_OTHER_ZONE, key.CLOCK_FIRST_TEXT), (key.CLOCK_EPOCH, key.CLOCK_EPOCH_TEXT)],
    ids=["zone", "epoch"],
)
def test_the_clock_value_is_stored_as_its_utc_text(
    tmp_path: Path, clock_value: datetime | float, text: str
) -> None:
    with open_store(tmp_path, clock=lambda: clock_value) as opened:
        opened.create_run(**_args())
    assert _query(tmp_path, "SELECT created_at FROM runs") == [(text,)]
    assert _query(tmp_path, "SELECT at FROM events") == [(text,)]


def test_one_clock_call_inside_the_write_transaction(tmp_path: Path) -> None:
    seen: list[bool] = []

    def clock() -> datetime:
        seen.append(opened._live().in_transaction)
        return key.CLOCK_FIRST

    with open_store(tmp_path, clock=clock) as opened:
        opened.create_run(**_args())
    assert seen == [True]


def test_the_token_is_32_lowercase_hex_stored_and_in_no_record(
    store: Store, tmp_path: Path
) -> None:
    claim = store.create_run(**_args())
    other = store.create_run(**_args(run_id="run-002"))
    assert re.fullmatch(f"[0-9a-f]{{{key.TOKEN_LENGTH}}}", claim.token) and claim.run_id == RUN_ID
    assert claim.token != other.token
    assert _query(tmp_path, "SELECT writer FROM runs WHERE run_id = ?", RUN_ID) == [(claim.token,)]
    seen = repr((store.run(RUN_ID), store.pins(RUN_ID), store.events(RUN_ID)))
    assert claim.token not in seen


@pytest.mark.parametrize(
    ("field", "written", "read"),
    key.ROUND_TRIPS,
    ids=[f"{row[0]}{index}" for index, row in enumerate(key.ROUND_TRIPS)],
)
def test_values_read_back_as_given(store: Store, field: str, written: object, read: object) -> None:
    store.create_run(**_args(**{field: written}))
    got = getattr(store.run(RUN_ID), field)
    assert (type(got), repr(got)) == (type(read), repr(read))
    if field == "request":
        assert store.run(RUN_ID).request_sha256 == key.EMPTY_REQUEST_SHA256


def _counting_clock() -> tuple[Clock, list[int]]:
    """A clock that records each call; the list holds one entry per call."""
    calls: list[int] = []

    def clock() -> datetime:
        calls.append(1)
        return key.CLOCK_FIRST

    return clock, calls


@pytest.mark.parametrize(
    ("field", "value"),
    [(field, value) for _, field, value in key.REFUSED_CREATE],
    ids=[f"refused{index}" for index in range(len(key.REFUSED_CREATE))],
)
def test_a_bad_argument_is_refused_and_nothing_is_written(
    tmp_path: Path, field: str, value: object
) -> None:
    clock, calls = _counting_clock()
    with open_store(tmp_path, clock=clock) as opened, pytest.raises(StoreRefused):
        opened.create_run(**_args(**{field: value}))
    assert calls == []
    _nothing_written(tmp_path)


def test_duplicate_pin_names_are_refused(tmp_path: Path) -> None:
    clock, calls = _counting_clock()
    with open_store(tmp_path, clock=clock) as opened, pytest.raises(StoreRefused):
        opened.create_run(**_args(pins=_pins(key.DUPLICATE_PIN_NAMES)))
    assert calls == []
    _nothing_written(tmp_path)


def test_a_pin_size_sqlite_cannot_hold_is_refused_before_anything_happens(tmp_path: Path) -> None:
    name, sha, _, kind = key.PINS[0]
    big = _pins(((name, sha, key.OVERSIZE_PIN_SIZE_BYTES, kind),))
    clock, calls = _counting_clock()
    with open_store(tmp_path, clock=clock) as opened, pytest.raises(StoreRefused):
        opened.create_run(**_args(pins=big))
    assert calls == []
    _nothing_written(tmp_path)


def test_a_failure_after_the_run_row_leaves_the_whole_database_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def dump() -> list[str]:
        with closing(sqlite3.connect(tmp_path / location.STATE_FILE_NAME)) as raw:
            return list(raw.iterdump())

    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("injected")

    with open_store(tmp_path, clock=_steps()) as opened:
        before = dump()
        monkeypatch.setattr(runs, "insert_event", boom)
        with pytest.raises(RuntimeError, match="injected"):
            opened.create_run(**_args())
        assert dump() == before


@pytest.mark.parametrize("value", [key.NAIVE_CLOCK, None], ids=["naive", "none"])
def test_a_clock_value_the_store_cannot_use_is_refused_and_rolled_back(
    tmp_path: Path, value: Any
) -> None:
    with open_store(tmp_path, clock=lambda: value) as opened, pytest.raises(StoreRefused):
        opened.create_run(**_args())
    _nothing_written(tmp_path)


def test_a_taken_run_id_is_a_conflict_and_changes_nothing(store: Store) -> None:
    store.create_run(**_args())
    before = (store.run(RUN_ID), store.pins(RUN_ID), store.events(RUN_ID))
    with pytest.raises(StoreConflict) as caught:
        store.create_run(**_args(issuer_id="issuer-b", pins=_pins(key.PINS[:1])))
    assert type(caught.value).__name__ == key.TAKEN_RUN_ID_ERROR
    assert (store.run(RUN_ID), store.pins(RUN_ID), store.events(RUN_ID)) == before


@pytest.mark.parametrize("method", ["run", "pins", "events"])
@pytest.mark.parametrize("run_id", [key.MISSING_RUN_ID, "bad id"], ids=["missing", "bad"])
def test_a_run_id_never_created_is_refused(
    handle: Store | StoreReader, method: str, run_id: str
) -> None:
    with pytest.raises(StoreRefused):
        getattr(handle, method)(run_id)


@pytest.mark.parametrize(
    ("name", "kind", "fields"),
    [row[1:] for row in key.CORRUPT_PINS],
    ids=[f"corrupt{index}" for index in range(len(key.CORRUPT_PINS))],
)
def test_a_pin_row_the_model_refuses_is_corrupt(
    store: Store, tmp_path: Path, name: str, kind: str, fields: tuple[str, ...]
) -> None:
    store.create_run(**_args(pins=()))
    _write_raw(
        tmp_path,
        "INSERT INTO run_sources(run_id, position, name, sha256, size_bytes, kind)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        RUN_ID,
        key.CORRUPT_PIN_POSITION,
        name,
        "ab" * 32,
        1,
        kind,
    )
    with pytest.raises(StoreCorrupt) as caught:
        store.pins(RUN_ID)
    message = str(caught.value)
    for text in (RUN_ID, str(key.CORRUPT_PIN_POSITION), *fields):
        assert text in message
    for text in ("validation error", "pydantic", "input_value"):
        assert text not in message
    assert max((len(run) for run in re.findall("x+", message)), default=0) <= 121


def test_stored_event_detail_the_codec_refuses_is_corrupt(store: Store, tmp_path: Path) -> None:
    store.create_run(**_args())
    _write_raw(
        tmp_path,
        "INSERT INTO events(run_id, at, kind, detail) VALUES (?, ?, 'note', '{\"cost\": 1.5}')",
        RUN_ID,
        key.CLOCK_FIRST_TEXT,
    )
    with pytest.raises(StoreCorrupt):
        store.events(RUN_ID)


def test_a_read_that_sqlite_refuses_leaves_as_a_store_error(store: Store) -> None:
    store.create_run(**_args())
    store._live().close()
    with pytest.raises(StoreUnusable, match="^read the store: "):
        store.run(RUN_ID)
