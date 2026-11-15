"""Signal's HTTP service, the ingest loop, `/api/status` and `serve`.

Run for real on one loopback port (port 0) over a seeded store. A pass is driven by calling
`run_once(now)` directly with a recorded feed behind `fetch_fn`: nothing here calls the real
`fetch.fetch` or reaches beyond 127.0.0.1. Tests whose fetch is replaced say so in their names.
"""

from __future__ import annotations

import logging
import socket
import socketserver
import sqlite3
import threading
import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from ingest_support import approve, count
from service_support import (
    NOW,
    Call,
    Live,
    RecordedFeed,
    closed_within,
    pass_in_progress,
    raw,
    wait_for,
)
from test_signal_feedview import build_feed_db

from credit_os.signal import ingest, service, store
from credit_os.signal.feeds import Entry
from credit_os.signal.fetch import Fetched, FetchRefused, LookupCapRefused
from credit_os.signal.service import DEFAULT_HOST, DEFAULT_PORT, Loop, make_server, serve

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


@pytest.fixture
def svc(tmp_path: Path) -> Iterator[Live]:
    build_feed_db(tmp_path).close()
    live = Live(make_server(tmp_path, "127.0.0.1", 0))
    yield live
    live.close()


@pytest.fixture
def cookie() -> str:
    return "signal_name=Reader"


@pytest.fixture
def svc_with_loop(tmp_path: Path) -> Iterator[tuple[Loop, Call]]:
    db = store.open_db(tmp_path)
    source = approve(db, "Authority", "https://a.org/f")
    store.add_story(db, source, Entry("Story one", "https://a.org/1", NOW, "Summary"), NOW)
    db.close()
    loop = Loop(tmp_path, fetch_fn=RecordedFeed())
    live = Live(make_server(tmp_path, "127.0.0.1", 0, loop=loop))
    yield loop, live.call
    live.close()


def test_me_without_a_name_and_status_need_no_name(svc: Live) -> None:
    assert svc.call("GET", "/api/me")[2] == {"name": None}
    assert svc.call("GET", "/api/status")[0] == 200


def test_loop_pass_updates_status_and_recovers_from_a_failing_source_with_recorded_feed(
    svc_with_loop: tuple[Loop, Call],
) -> None:
    # one approved source; fetch replaced: first call raises RuntimeError, later calls RSS
    loop, call = svc_with_loop
    loop.run_once(NOW)
    status = call("GET", "/api/status")[2]  # the source is recorded failing; the pass completes
    assert status["loop_error"] is None and status["sources"] == {"approved": 1, "failing": 1}
    assert status["last_pass_at"] == NOW.isoformat()
    later = NOW + timedelta(seconds=601)
    loop.run_once(later)
    status = call("GET", "/api/status")[2]
    assert status["loop_error"] is None and status["sources"] == {"approved": 1, "failing": 0}
    assert status["last_pass_at"] == later.isoformat()


def test_a_pass_that_raises_at_loop_level_is_shown_by_type_only_with_recorded_feed(
    svc_with_loop: tuple[Loop, Call], monkeypatch: pytest.MonkeyPatch
) -> None:
    loop, call = svc_with_loop
    good_run_due = ingest.run_due

    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("secret")

    monkeypatch.setattr(ingest, "run_due", boom)
    loop.run_once(NOW)  # must not raise
    shown = call("GET", "/api/status")[2]["loop_error"]
    assert shown and "RuntimeError" in shown and "secret" not in shown
    monkeypatch.setattr(ingest, "run_due", good_run_due)
    loop.run_once(NOW + timedelta(seconds=601))
    assert call("GET", "/api/status")[2]["loop_error"] is None


def test_a_save_during_a_pass_succeeds(svc_with_loop: tuple[Loop, Call], cookie: str) -> None:
    loop, call = svc_with_loop  # fetch replaced by one that blocks on an Event mid-pass
    with pass_in_progress(loop):
        assert call("POST", "/api/stories/1/save", cookie=cookie)[0] == 200


def test_status_counts_a_failing_source_with_recorded_feed(
    svc_with_loop: tuple[Loop, Call],
) -> None:
    loop, call = svc_with_loop

    def refused(url: str, etag: str | None, modified: str | None) -> Fetched:
        raise FetchRefused("not a feed")

    loop.fetch_fn = refused
    loop.run_once(NOW)
    assert call("GET", "/api/status")[2]["sources"] == {"approved": 1, "failing": 1}
    assert call("GET", "/api/status")[2]["loop_error"] is None


def test_a_taken_port_names_the_address_and_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def hang_guard(self: socketserver.BaseServer, poll_interval: float = 0.5) -> None:
        pytest.fail("serve reached serve_forever: the taken port was bound a second time")

    # A platform where the second bind succeeds fails here instead of blocking the run (Q4).
    monkeypatch.setattr(socketserver.BaseServer, "serve_forever", hang_guard)
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        port = taken.getsockname()[1]
        assert serve(tmp_path, "127.0.0.1", port) == 2
    message = capsys.readouterr().err.strip()
    assert message.startswith(f"cannot listen on 127.0.0.1:{port}: ") and "\n" not in message


def test_a_trickling_connection_is_closed_at_the_deadline(
    svc: Live, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger=service.log.name)
    monkeypatch.setattr(service, "SOCKET_TIMEOUT", 1)  # the deadline is twice that
    monkeypatch.setattr(service.Handler, "timeout", 5)  # per-read timeout longer than the deadline
    host = f"127.0.0.1:{svc.port}"
    sock = raw(svc, f"GET /api/status HTTP/1.1\r\nHost: {host}\r\nX-Pad: ".encode())
    stop = threading.Event()

    def trickle() -> None:
        while not stop.is_set():
            try:
                sock.sendall(b"a")
            except OSError:
                return
            time.sleep(0.1)

    thread = threading.Thread(target=trickle, daemon=True)
    thread.start()
    try:
        assert closed_within(sock, 3)
    finally:
        stop.set()
        thread.join(timeout=5)
        sock.close()
    assert svc.call("GET", "/api/status")[0] == 200
    cut = [r for r in caplog.records if "connection deadline reached" in r.getMessage()]
    assert len(cut) == 1
    assert cut[0].levelno == logging.INFO and cut[0].getMessage().startswith("127.0.0.1 ")
    assert cut[0].exc_info is None


def test_one_address_has_a_share_of_the_connection_ceiling(
    svc: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(service, "MAX_PER_ADDRESS", 3)
    server = cast(service._Server, svc.server)
    held = [raw(svc, b"") for _ in range(3)]
    try:
        assert wait_for(lambda: server.active_connections == 3)
        extra = raw(svc, b"")
        assert closed_within(extra, 3)
        extra.close()
        assert all(not closed_within(sock, 0.3) for sock in held)
    finally:
        for sock in held:
            sock.close()
    assert wait_for(lambda: server.active_connections == 0)
    assert svc.call("GET", "/api/status")[0] == 200


def test_a_save_waits_for_a_held_write_lock(
    svc_with_loop: tuple[Loop, Call], cookie: str, tmp_path: Path
) -> None:
    _, call = svc_with_loop
    other = sqlite3.connect(
        tmp_path / "signal" / "signal.db", isolation_level=None, check_same_thread=False
    )
    other.execute("BEGIN IMMEDIATE")
    release = threading.Timer(1.0, lambda: other.execute("COMMIT"))
    release.start()
    try:
        started = time.monotonic()
        assert call("POST", "/api/stories/1/save", cookie=cookie)[0] == 200
        assert time.monotonic() - started >= 0.3  # it did wait for the lock
    finally:
        release.join()
        other.close()


# ---- new: one pass at a time, a lookup-cap stop, a pass that raises (N12) ----


def test_a_second_pass_during_a_pass_returns_at_once_and_fetches_nothing(
    svc_with_loop: tuple[Loop, Call], caplog: pytest.LogCaptureFixture
) -> None:
    loop, _ = svc_with_loop
    caplog.set_level(logging.INFO, logger=service.log.name)
    with pass_in_progress(loop) as calls:
        loop.last_error = "kept"
        loop.run_once(NOW + timedelta(seconds=1))  # would wait for the held pass if it did not skip
        assert calls == ["https://a.org/f"] and loop.last_error == "kept"
    assert calls == ["https://a.org/f"] and loop.last_error is None
    skipped = [r for r in caplog.records if "already running" in r.getMessage()]
    assert len(skipped) == 1 and skipped[0].levelno == logging.INFO


def test_a_lookup_cap_stop_is_an_incomplete_pass_not_a_failing_source(
    svc_with_loop: tuple[Loop, Call], caplog: pytest.LogCaptureFixture
) -> None:
    loop, call = svc_with_loop
    db = store.open_db(loop.root)
    approve(db, "Wire", "https://w.org/f")
    db.close()
    calls: list[str] = []

    def capped(url: str, etag: str | None, modified: str | None) -> Fetched:
        calls.append(url)
        raise LookupCapRefused("too many lookups are still waiting for an answer")

    loop.fetch_fn = capped
    caplog.set_level(logging.INFO, logger=service.log.name)
    loop.run_once(NOW)
    assert calls == ["https://a.org/f"]  # the pass stopped at the first source
    assert loop.last_error is None
    db = store.open_db(loop.root)
    assert count(db, "source_checks") == 0
    db.close()
    status = call("GET", "/api/status")[2]
    assert status == {
        "last_pass_at": NOW.isoformat(),
        "sources": {"approved": 2, "failing": 0},
        "loop_error": None,
    }
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1 and warnings[0].name == service.log.name
    infos = [r.getMessage() for r in caplog.records if r.getMessage().startswith("ingest pass:")]
    assert infos == ["ingest pass: 0 checked, 0 failed"]  # counts only, never a reason
    assert warnings[0].exc_info is None
    assert "waiting for an answer" not in caplog.text  # the refusal's text is not logged


def test_a_failing_source_is_counted_and_is_not_a_lookup_cap_stop(
    svc_with_loop: tuple[Loop, Call], caplog: pytest.LogCaptureFixture
) -> None:
    loop, _ = svc_with_loop
    caplog.set_level(logging.INFO, logger=service.log.name)
    loop.fetch_fn = lambda url, etag, modified: (_ for _ in ()).throw(FetchRefused("not a feed"))
    loop.run_once(NOW)
    ours = [(r.levelno, r.getMessage()) for r in caplog.records if r.name == service.log.name]
    assert ours == [(logging.INFO, "ingest pass: 1 checked, 1 failed")]
    assert "not a feed" not in caplog.text  # the reason is the feed's text: stored, never logged


@pytest.mark.parametrize(
    "error",
    [store.StoreUnusable("secret"), sqlite3.OperationalError("secret")],
    ids=["unusable", "busy"],
)
def test_a_pass_that_raises_is_logged_shown_by_type_only_and_cleared_by_the_next(
    svc_with_loop: tuple[Loop, Call],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    error: Exception,
) -> None:
    loop, call = svc_with_loop
    good_run_due = ingest.run_due

    def boom(*args: object, **kwargs: object) -> None:
        raise error

    monkeypatch.setattr(ingest, "run_due", boom)
    loop.run_once(NOW)  # must not raise
    name = type(error).__name__
    assert loop.last_error == f"the last ingest pass failed ({name}); see the log"
    assert call("GET", "/api/status")[2]["loop_error"] == loop.last_error
    failed = [r for r in caplog.records if r.getMessage() == "ingest pass failed"]
    assert len(failed) == 1 and failed[0].levelno == logging.ERROR
    assert failed[0].exc_info is not None and failed[0].exc_info[1] is error
    monkeypatch.setattr(ingest, "run_due", good_run_due)
    loop.run_once(NOW + timedelta(seconds=601))
    assert loop.last_error is None
    assert call("GET", "/api/status")[2]["loop_error"] is None


# ---- new: run_until, serve, the defaults (N13) ----


def test_run_until_passes_the_server_clock_as_aware_utc_and_stops_with_the_event(
    tmp_path: Path,
) -> None:
    seen: list[datetime] = []
    stop = threading.Event()

    class Recording(Loop):
        def run_once(self, now: datetime) -> None:
            seen.append(now)
            assert len(seen) < 5, "run_until did not stop"
            if len(seen) == 2:
                stop.set()

    before = datetime.now(UTC)
    Recording(tmp_path).run_until(stop, 0.01)
    after = datetime.now(UTC)
    assert len(seen) == 2  # a pass, a wait, a pass, then the set event ends it
    assert all(at.tzinfo is not None and at.utcoffset() == timedelta(0) for at in seen)
    assert before <= seen[0] <= seen[1] <= after


def test_run_until_with_the_event_already_set_runs_one_pass_and_returns(tmp_path: Path) -> None:
    calls: list[datetime] = []
    stop = threading.Event()
    stop.set()

    class Recording(Loop):
        def run_once(self, now: datetime) -> None:
            calls.append(now)
            assert len(calls) < 5, "run_until did not stop"

    Recording(tmp_path).run_until(stop, 60.0)  # returns at once: a set event ends the wait
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("host", "port", "message"),
    [
        ("127.0.0.1", 70000, "--port must be from 0 to 65535"),
        ("0.0.0.0", 0, service.WILDCARD_MESSAGE),
    ],
    ids=["port", "wildcard"],
)
def test_serve_refuses_a_bad_address_with_one_line_and_exit_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], host: str, port: int, message: str
) -> None:
    assert serve(tmp_path / "root", host, port) == 2
    assert capsys.readouterr().err == message + "\n"
    assert not (tmp_path / "root").exists()


def test_serve_refuses_a_root_that_is_a_file_with_one_line_and_exit_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def hang_guard(self: socketserver.BaseServer, poll_interval: float = 0.5) -> None:
        pytest.fail("serve reached serve_forever: the store was never opened")

    # A serve that skips opening the store fails here instead of blocking the run (R71 F3).
    monkeypatch.setattr(socketserver.BaseServer, "serve_forever", hang_guard)
    root = tmp_path / "file"
    root.write_text("x")
    assert serve(root, "127.0.0.1", 0) == 2
    message = capsys.readouterr().err
    assert message.startswith(f"cannot open the store under {root}: ")
    assert message.count("\n") == 1 and message.endswith("\n")


def test_serve_returns_0_after_an_interrupt_and_builds_its_loop_with_no_fetch_fn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    built: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    served: list[Loop | None] = []
    configured: list[dict[str, Any]] = []

    class Spy(Loop):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            built.append((args, kwargs))
            super().__init__(*args, **kwargs)

    def interrupted(self: socketserver.BaseServer, poll_interval: float = 0.5) -> None:
        served.append(cast(service._Server, self).loop)
        raise KeyboardInterrupt

    monkeypatch.setattr(service, "Loop", Spy)
    monkeypatch.setattr(socketserver.BaseServer, "serve_forever", interrupted)
    monkeypatch.setattr(logging, "basicConfig", lambda **kwargs: configured.append(kwargs))
    threads = set(threading.enumerate())
    assert serve(tmp_path, "127.0.0.1", 0, tick=0.01) == 0
    assert built == [((tmp_path,), {})]  # no fetch_fn: production fetches for real
    assert len(served) == 1 and isinstance(served[0], Spy)  # the server reads the same loop
    assert configured == [{"level": logging.INFO, "format": LOG_FORMAT}]
    assert capsys.readouterr().err.startswith("serving http://127.0.0.1:")
    assert set(threading.enumerate()) <= threads  # the loop's thread was stopped and joined


def test_the_defaults_are_the_loopback_address_and_port_8766() -> None:
    assert DEFAULT_HOST == "127.0.0.1" and DEFAULT_PORT == 8766


# ---- new: /api/status (N14) ----


def test_status_with_no_loop_and_no_pass_says_so(svc: Live) -> None:
    status, _, data = svc.call("GET", "/api/status")
    assert (status, data) == (
        200,
        {"last_pass_at": None, "sources": {"approved": 2, "failing": 0}, "loop_error": None},
    )


def test_a_busy_store_under_status_is_503_with_a_fixed_text(
    svc: Live, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def busy(*args: object, **kwargs: object) -> None:
        raise sqlite3.OperationalError("secret")

    monkeypatch.setattr(ingest, "health", busy)
    status, _, data = svc.call("GET", "/api/status")
    assert (status, data) == (503, {"error": "the store is busy; try again"})
    assert "secret" in caplog.text  # in the log, with its traceback, in no body
