"""Signal's HTTP service, the rules the other service files leave unpinned (S-9, part 6).

Run for real on one loopback port (port 0), one server thread at a time, one connection at a time
(at most a few dozen requests in a test), expected values by literal. Nothing here opens sockets or
threads until the system refuses.
"""

from __future__ import annotations

import logging
import socket
import socketserver
import sqlite3
import struct
import threading
from collections.abc import Iterator
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, cast

import pytest
from ingest_support import approve
from service_support import NOW, Live, raw, read_all, wait_for
from test_signal_feeds import RSS
from test_signal_feedview import build_feed_db

from credit_os.signal import ingest, service, store
from credit_os.signal.fetch import Fetched, LookupCapRefused
from credit_os.signal.service import Loop, make_server, serve

FIXED = b'{"error": "the request could not be read"}'


@pytest.fixture
def svc(tmp_path: Path) -> Iterator[Live]:
    build_feed_db(tmp_path).close()
    live = Live(make_server(tmp_path, "127.0.0.1", 0))
    yield live
    live.close()


# ---- A1-1: the standard library's own replies quote nothing of the request ----


@pytest.mark.parametrize(
    ("line", "status"),
    [
        (b"GET /QZXMARK a HTTP/1.1", b"400 Bad Request"),
        (b"QZXMARK /api/me HTTP/1.1", b"501 Not Implemented"),
        (b"GET /QZXMARK\x1b[2J b HTTP/1.1", b"400 Bad Request"),
    ],
    ids=["syntax", "method", "escape"],
)
def test_the_standard_librarys_own_error_replies_quote_nothing_of_the_request(
    svc: Live, caplog: pytest.LogCaptureFixture, line: bytes, status: bytes
) -> None:
    caplog.set_level(logging.INFO, logger=service.log.name)
    reply = read_all(raw(svc, line + f"\r\nHost: 127.0.0.1:{svc.port}\r\n\r\n".encode()))
    head, _, body = reply.partition(b"\r\n\r\n")
    lines = head.split(b"\r\n")
    assert lines[0] == b"HTTP/1.0 " + status  # a fixed reason phrase, not the request line
    assert b"QZXMARK" not in head and body == FIXED
    assert b"Connection: close" in lines  # the connection is still closed after the reply
    assert b"Content-Type: application/json; charset=utf-8" in lines
    assert b"Content-Length: 42" in lines and len(FIXED) == 42
    assert b"X-Content-Type-Options: nosniff" in lines and b"X-Frame-Options: DENY" in lines
    assert "\x1b" not in caplog.text  # the access line shows the request, escaped
    assert "Bad request syntax" not in caplog.text and "Unsupported method" not in caplog.text


# ---- A1-2: a client reset is logged through logging, never printed ----


def test_a_client_reset_while_the_request_is_read_is_logged_not_printed(
    svc: Live, caplog: pytest.LogCaptureFixture, capfd: pytest.CaptureFixture[str]
) -> None:
    caplog.set_level(logging.INFO, logger=service.log.name)
    sock = raw(svc, b"GET /api/m")  # a request line that never ends, then a reset
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
    sock.close()
    assert wait_for(
        lambda: any("ConnectionResetError" in r.getMessage() for r in caplog.records), 3
    )
    ours = [r for r in caplog.records if "ConnectionResetError" in r.getMessage()]
    assert [r.getMessage() for r in ours] == ["127.0.0.1: request failed (ConnectionResetError)"]
    assert ours[0].levelno == logging.WARNING and ours[0].exc_info is None
    assert "Traceback" not in capfd.readouterr().err
    assert svc.call("GET", "/api/me")[0] == 200


# ---- the wire's unpinned rules (R65 F3) ----


def exchange(live: Live, data: bytes, *, half_close: bool = False) -> bytes:
    """Send ``data`` on one connection and read everything the server answers."""
    sock = raw(live, data)
    try:
        if half_close:
            sock.shutdown(socket.SHUT_WR)
        return read_all(sock)
    finally:
        sock.close()


def answer(reply: bytes) -> tuple[bytes, bytes]:
    """The status line and the body of a reply."""
    head, _, body = reply.partition(b"\r\n\r\n")
    return head.split(b"\r\n")[0], body


def test_a_request_target_that_is_not_a_path_is_a_400(svc: Live) -> None:
    host = f"127.0.0.1:{svc.port}"
    reply = exchange(svc, f"GET http://{host}/api/me HTTP/1.1\r\nHost: {host}\r\n\r\n".encode())
    assert answer(reply) == (
        b"HTTP/1.0 400 Bad Request",
        b'{"error": "the request target must be a path"}',
    )


def test_a_transfer_encoding_header_is_a_411(svc: Live) -> None:
    head = f"GET /api/me HTTP/1.1\r\nHost: 127.0.0.1:{svc.port}\r\nTransfer-Encoding: chunked\r\n"
    reply = exchange(svc, (head + "\r\n0\r\n\r\n").encode())
    assert answer(reply) == (
        b"HTTP/1.0 411 Length Required",
        b'{"error": "a body needs Content-Length"}',
    )


def test_a_body_that_ends_before_its_content_length_is_a_400(svc: Live) -> None:
    host = f"127.0.0.1:{svc.port}"
    head = f"POST /api/me HTTP/1.1\r\nHost: {host}\r\nOrigin: http://{host}\r\n"
    reply = exchange(svc, (head + 'Content-Length: 50\r\n\r\n{"na').encode(), half_close=True)
    assert answer(reply) == (
        b"HTTP/1.0 400 Bad Request",
        b'{"error": "the request body ended early"}',
    )


def test_a_reply_that_cannot_be_encoded_is_the_documented_500_and_is_logged(
    svc: Live, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def echo(*args: object, **kwargs: object) -> None:
        raise store.StoreError("\ud800 is not a thing")  # a store text that cannot be encoded

    monkeypatch.setattr(store, "role_of", echo)
    caplog.set_level(logging.INFO, logger=service.log.name)
    status, _, data = svc.call("POST", "/api/me", body={"name": "ab"})
    assert (status, data) == (500, {"error": "the service failed; see its log"})
    failed = [
        r for r in caplog.records if r.getMessage() == "POST /api/me: reply could not be sent"
    ]
    assert len(failed) == 1 and failed[0].exc_info is not None
    assert failed[0].exc_info[0] is UnicodeEncodeError


def test_a_reply_the_peer_cannot_take_is_logged_at_info_and_not_retried(
    svc: Live, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def gone(self: BaseHTTPRequestHandler, code: int, message: str | None = None) -> None:
        raise BrokenPipeError("peer gone")

    caplog.set_level(logging.INFO, logger=service.log.name)
    monkeypatch.setattr(BaseHTTPRequestHandler, "send_response", gone)
    assert (
        exchange(svc, f"GET /api/me HTTP/1.1\r\nHost: 127.0.0.1:{svc.port}\r\n\r\n".encode()) == b""
    )
    monkeypatch.undo()
    kept = [(r.levelno, r.getMessage(), r.exc_info) for r in caplog.records]
    assert (logging.INFO, "GET /api/me: reply not delivered (peer gone)", None) in kept
    assert not [r for r in caplog.records if r.exc_info]  # no 500 attempt, no traceback
    assert svc.call("GET", "/api/me")[0] == 200


def test_every_reply_says_not_to_cache_it(svc: Live) -> None:
    for path, status in (("/api/me", 200), ("/nowhere", 404)):
        reply = svc.call("GET", path)
        assert reply[0] == status and reply[1]["Cache-Control"] == "no-store"


def test_the_connection_deadline_timer_is_cancelled_when_the_request_is_done(
    svc: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    timers: list[threading.Timer] = []

    class Recording(threading.Timer):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            timers.append(self)

    monkeypatch.setattr(threading, "Timer", Recording)
    assert svc.call("GET", "/api/me")[0] == 200
    assert len(timers) == 1 and timers[0].interval == 2 * service.SOCKET_TIMEOUT
    assert wait_for(lambda: timers[0].finished.is_set(), 3)  # cancelled, not left for 120 s
    timers[0].join(timeout=3)
    assert not timers[0].is_alive()


def test_a_body_of_exactly_65536_bytes_is_accepted_and_one_more_is_not(svc: Live) -> None:
    head = b'{"name": "ab", "pad": "'
    exact = head + b"x" * (65536 - len(head) - 2) + b'"}'
    assert len(exact) == 65536
    status, _, data = svc.call("POST", "/api/me", raw=exact)
    assert (status, data["name"]) == (200, "ab")
    assert svc.call("POST", "/api/me", raw=exact + b" ")[0] == 413


# ---- R69: the `after` digits, two Host lines, the port-80 Origin form ----

AFTER_TEXT = {"error": "invalid after; expected digits"}


@pytest.mark.parametrize(
    ("after", "status", "data"),
    [
        ("%D9%A5", 400, AFTER_TEXT),
        ("1" * 20, 400, AFTER_TEXT),
        ("9" * 4301, 400, AFTER_TEXT),
        ("1000000000000000000", 200, {"count": 0}),
    ],
    ids=["arabic", "digits20", "digits4301", "digits19"],
)
def test_the_after_cursor_is_ascii_digits_of_at_most_nineteen(
    svc: Live, after: str, status: int, data: dict[str, object]
) -> None:
    reply = svc.call("GET", f"/api/feed/new?view=latest&after={after}", cookie="signal_name=Reader")
    assert (reply[0], reply[2]) == (status, data)


def test_two_host_lines_are_refused_even_when_each_is_right(svc: Live) -> None:
    host = f"127.0.0.1:{svc.port}"
    reply = exchange(svc, f"GET /api/me HTTP/1.1\r\nHost: {host}\r\nHost: {host}\r\n\r\n".encode())
    assert answer(reply) == (
        b"HTTP/1.0 403 Forbidden",
        b'{"error": "this address is not the one the service was started on"}',
    )


def test_the_port_80_origin_form_is_accepted_only_on_port_80(
    svc: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = {"name": "ab"}
    bare = {"host": "127.0.0.1:80", "origin": "http://127.0.0.1", "body": body}
    server = cast(service._Server, svc.server)
    monkeypatch.setattr(server, "allowed_hosts", service._hosts("127.0.0.1", 80))
    assert svc.call("POST", "/api/me", **bare)[0] == 403  # started on another port: no bare form
    monkeypatch.setattr(server, "advertised_port", 80)
    assert svc.call("POST", "/api/me", **bare)[0] == 200
    assert svc.call("POST", "/api/me", **(bare | {"origin": "http://127.0.0.1:80"}))[0] == 200
    assert svc.call("POST", "/api/me", **(bare | {"origin": "http://127.0.0.1:81"}))[0] == 403


# ---- R71: the loop, status and serve rules the loop file leaves unpinned ----

FAILED_PASS = "the last ingest pass failed (OperationalError); see the log"
CAPPED = LookupCapRefused("too many lookups are still waiting for an answer")


def good_feed(url: str, etag: str | None, modified: str | None) -> Fetched:
    return Fetched(RSS, None, None)


def capped_feed(url: str, etag: str | None, modified: str | None) -> Fetched:
    raise CAPPED


def two_sources(url: str, etag: str | None, modified: str | None) -> Fetched:
    return (
        capped_feed(url, etag, modified)
        if url == "https://w.org/f"
        else good_feed(url, etag, modified)
    )


def sources(root: Path, *urls: str) -> None:
    db = store.open_db(root)
    for number, url in enumerate(urls):
        approve(db, f"Source {number}", url)
    db.close()


def pass_lines(caplog: pytest.LogCaptureFixture) -> tuple[list[str], int]:
    """The service's INFO count lines and the number of its warnings in a pass."""
    mine = [r for r in caplog.records if r.name == service.log.name]
    counts = [r.getMessage() for r in mine if r.getMessage().startswith("ingest pass:")]
    return counts, len([r for r in mine if r.levelno == logging.WARNING])


def test_a_cap_stop_at_a_source_that_was_checked_before_is_still_a_cap_stop(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    sources(tmp_path, "https://a.org/f")
    loop = Loop(tmp_path, fetch_fn=good_feed)
    loop.run_once(NOW - timedelta(seconds=601))  # a good check is on record at an earlier time
    loop.fetch_fn = capped_feed
    caplog.set_level(logging.INFO, logger=service.log.name)
    loop.run_once(NOW)
    assert pass_lines(caplog) == (["ingest pass: 0 checked, 0 failed"], 1)
    assert loop.last_error is None


def test_a_cap_stop_after_sources_that_were_checked_counts_those_and_warns(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    sources(tmp_path, "https://a.org/f", "https://w.org/f")
    loop = Loop(tmp_path, fetch_fn=two_sources)
    caplog.set_level(logging.INFO, logger=service.log.name)
    loop.run_once(NOW)
    assert pass_lines(caplog) == (["ingest pass: 1 checked, 0 failed"], 1)
    assert loop.last_error is None


@pytest.mark.parametrize("stop", [KeyboardInterrupt, SystemExit], ids=["interrupt", "exit"])
def test_a_pass_does_not_catch_what_is_not_an_exception_and_frees_the_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stop: type[BaseException]
) -> None:
    def interrupted(*args: object, **kwargs: object) -> None:
        raise stop

    monkeypatch.setattr(ingest, "run_due", interrupted)
    loop = Loop(tmp_path)
    with pytest.raises(stop):
        loop.run_once(NOW)
    assert loop.last_error is None and not loop._running.locked()


def test_a_pass_with_no_source_due_is_a_pass_that_returns_and_clears_the_last_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    loop = Loop(tmp_path)  # an empty store: nothing is due
    loop.last_error = "kept"
    caplog.set_level(logging.INFO, logger=service.log.name)
    loop.run_once(NOW)
    assert loop.last_error is None
    assert pass_lines(caplog) == (["ingest pass: 0 checked, 0 failed"], 0)


@pytest.mark.parametrize("fails", [False, True], ids=["pass", "raise"])
def test_the_pass_connection_is_closed_whether_the_pass_returns_or_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fails: bool
) -> None:
    opened: list[sqlite3.Connection] = []
    real = store.open_db

    def recording(root: Path) -> sqlite3.Connection:
        opened.append(real(root))
        return opened[-1]

    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("secret")

    monkeypatch.setattr(store, "open_db", recording)
    if fails:
        monkeypatch.setattr(ingest, "run_due", boom)
    Loop(tmp_path).run_once(NOW)
    assert len(opened) == 1
    with pytest.raises(sqlite3.ProgrammingError):
        opened[0].execute("SELECT 1")


def test_run_until_waits_a_full_tick_between_passes(tmp_path: Path) -> None:
    waits: list[float | None] = []

    class Spy(threading.Event):
        def wait(self, timeout: float | None = None) -> bool:
            waits.append(timeout)
            return super().wait(timeout)

    stop, passes = Spy(), []

    class Recording(Loop):
        def run_once(self, now: datetime) -> None:
            passes.append(now)
            if len(passes) == 2:
                stop.set()

    Recording(tmp_path).run_until(stop, 0.05)
    assert len(passes) == 2 and waits == [0.05, 0.05]


def test_status_counts_approved_sources_only(svc: Live, tmp_path: Path) -> None:
    db = store.open_db(tmp_path)
    store.propose_source(db, "Proposed", "news", "https://p.org/f", "x")  # not approved
    db.close()
    assert svc.call("GET", "/api/status")[2]["sources"] == {"approved": 2, "failing": 0}


def test_port_65535_is_a_valid_port_and_fails_only_if_it_cannot_be_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def cannot(*args: object, **kwargs: object) -> None:
        raise OSError("simulated refusal")

    monkeypatch.setattr(service, "make_server", cannot)  # nothing is bound
    assert serve(tmp_path, "127.0.0.1", 65535) == 2
    assert capsys.readouterr().err == "cannot listen on 127.0.0.1:65535: simulated refusal\n"


def closing(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record each ``server_close`` of the service's server (the real one still runs)."""
    closed: list[str] = []
    real = service._Server.server_close

    def recording(self: service._Server) -> None:
        closed.append("closed")
        real(self)

    monkeypatch.setattr(service._Server, "server_close", recording)
    return closed


def interrupt(self: socketserver.BaseServer, poll_interval: float = 0.5) -> None:
    raise KeyboardInterrupt


def test_the_server_is_closed_when_the_store_cannot_be_opened(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def hang_guard(self: socketserver.BaseServer, poll_interval: float = 0.5) -> None:
        pytest.fail("serve reached serve_forever: the store was never opened")

    closed = closing(monkeypatch)
    monkeypatch.setattr(socketserver.BaseServer, "serve_forever", hang_guard)
    root = tmp_path / "file"
    root.write_text("x")
    assert serve(root, "127.0.0.1", 0) == 2
    assert closed == ["closed"]


def test_the_server_is_closed_at_shutdown_and_the_loop_thread_is_a_daemon(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    daemons: list[bool] = []

    def recording(self: Loop, stop: threading.Event, tick: float) -> None:
        daemons.append(threading.current_thread().daemon)

    closed = closing(monkeypatch)
    monkeypatch.setattr(Loop, "run_until", recording)
    monkeypatch.setattr(socketserver.BaseServer, "serve_forever", interrupt)
    assert serve(tmp_path, "127.0.0.1", 0, tick=0.01) == 0
    assert closed == ["closed"] and daemons == [True]


def test_the_database_exists_when_serve_forever_is_reached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A first request, which may be a cross-site navigation GET, must never create the store."""
    seen: list[bool] = []

    def reached(self: socketserver.BaseServer, poll_interval: float = 0.5) -> None:
        seen.append((tmp_path / "signal" / "signal.db").exists())
        raise KeyboardInterrupt

    def not_now(self: Loop, stop: threading.Event, tick: float) -> None:
        return None  # the loop would open the store too: only `serve` may have

    monkeypatch.setattr(Loop, "run_until", not_now)
    monkeypatch.setattr(socketserver.BaseServer, "serve_forever", reached)
    assert serve(tmp_path, "127.0.0.1", 0) == 0
    assert seen == [True]


def test_a_pass_survives_a_held_write_lock_and_the_next_one_recovers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    sources(tmp_path, "https://a.org/f")
    loop = Loop(tmp_path, fetch_fn=good_feed)
    monkeypatch.setattr(store, "_BUSY_SECONDS", 0.2)
    other = store.open_db(tmp_path)
    other.execute("BEGIN IMMEDIATE")  # a second connection holds the write lock
    try:
        loop.run_once(NOW)  # must not raise
    finally:
        other.execute("ROLLBACK")
        other.close()
    assert loop.last_error == FAILED_PASS
    failed = [r for r in caplog.records if r.getMessage() == "ingest pass failed"]
    assert len(failed) == 1 and failed[0].exc_info is not None
    assert failed[0].exc_info[0] is sqlite3.OperationalError
    loop.run_once(NOW + timedelta(seconds=601))
    assert loop.last_error is None
