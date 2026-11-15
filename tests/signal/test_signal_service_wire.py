"""Signal's HTTP service, wire level: what a request may carry and how the service answers it.

Run for real on one loopback port (port 0) over a seeded store. The page is not served (decision
0009), so every path outside the API is a 404 JSON reply that carries the four security headers.
Expected values are literals. Nothing here reaches beyond 127.0.0.1.
"""

from __future__ import annotations

import logging
import socket
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import pytest
from service_support import Live, closed_within, lingering_connection, raw, read_all, wait_for
from test_signal_feedview import build_feed_db

from credit_os.signal import identity, service
from credit_os.signal.service import make_server

POLICY = (
    "default-src 'none'; script-src 'self'; style-src 'self'; font-src 'self'; "
    "img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'; "
    "frame-ancestors 'none'"
)


@pytest.fixture
def svc(tmp_path: Path) -> Iterator[Live]:
    build_feed_db(tmp_path).close()
    live = Live(make_server(tmp_path, "127.0.0.1", 0))
    yield live
    live.close()


def test_no_path_outside_the_api_is_served(svc: Live) -> None:
    for path in (
        "/",
        "/static/signal.js",
        "/static/../store.py",
        "/static/store.py",
        "/static/%2e%2e/cli.py",
        "/signal/signal.db",
        "/static/",
    ):
        status, headers, data = svc.call("GET", path)
        assert (status, data) == (404, {"error": "not found"}), path
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["Cross-Origin-Resource-Policy"] == "same-origin"
        assert headers["Content-Security-Policy"] == POLICY
        assert headers["Content-Type"] == "application/json; charset=utf-8"


def test_page_policy_is_exact_and_on_every_response(svc: Live) -> None:
    for path in ("/api/me", "/nowhere", "/"):
        status, headers, _ = svc.call("GET", path)
        assert status == (200 if path == "/api/me" else 404), path
        assert headers["Content-Security-Policy"] == POLICY
        assert headers["X-Frame-Options"] == "DENY"
    assert svc.call("GET", "/")[2] == {"error": "not found"}


def test_bodies_are_capped_and_must_be_json(svc: Live) -> None:
    assert svc.call("POST", "/api/me", raw=b"x" * (64 * 1024 + 1))[0] == 413
    assert svc.call("POST", "/api/me", raw=b"{not json")[0] == 400
    assert svc.call("POST", "/api/me", raw=b"[]")[0] == 400
    assert svc.call("POST", "/api/me", body={"name": 5})[0] == 400


@pytest.mark.parametrize(
    "body",
    [b'{"name": "a", "name": "b"}', b'{"name": "a", "x": {"k": 1, "k": 2}}'],
    ids=["top-level", "nested"],
)
def test_a_json_body_that_names_a_field_twice_is_refused_and_sets_no_cookie(
    svc: Live, body: bytes
) -> None:
    status, headers, data = svc.call("POST", "/api/me", raw=body)
    assert (status, data) == (400, {"error": "the request body names a field twice"})
    assert "Set-Cookie" not in headers
    assert svc.call("POST", "/api/me", raw=b'{"name": "a"}')[0] == 200


def test_a_json_body_needs_content_length(svc: Live) -> None:
    connection = lingering_connection(svc.port, 20)
    connection.putrequest("POST", "/api/me", skip_accept_encoding=True)
    connection.putheader("Origin", f"http://127.0.0.1:{svc.port}")
    connection.endheaders()
    assert connection.getresponse().status == 411
    connection.close()


def test_a_wildcard_host_is_refused_at_start(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="own address"):
        make_server(tmp_path, "0.0.0.0", 0)
    assert not (tmp_path / "signal").exists()


def test_a_short_body_is_a_refusal_not_a_traceback(
    svc: Live, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(service.Handler, "timeout", 1)
    caplog.set_level(logging.INFO)
    host = f"127.0.0.1:{svc.port}"
    head = f"POST /api/me HTTP/1.1\r\nHost: {host}\r\nOrigin: http://{host}\r\n"
    sock = raw(svc, (head + 'Content-Length: 50\r\n\r\n{"na').encode())
    reply = read_all(sock)
    sock.close()
    assert reply.split(b"\r\n")[0].split()[1] == b"400"
    assert b"the request body did not arrive" in reply
    assert not [record for record in caplog.records if record.exc_info]


def test_an_http_09_request_line_gets_no_500(svc: Live, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger=service.log.name)
    sock = raw(svc, b"GET /api/me\r\n")
    sock.shutdown(socket.SHUT_WR)  # Python 3.12.14 reads headers after a two-word line, to EOF
    reply = read_all(sock)
    sock.close()
    assert wait_for(lambda: any("HTTP/0.9" in r.getMessage() for r in caplog.records))
    assert b"the service failed" not in reply and b" 500 " not in reply
    assert not [record for record in caplog.records if record.exc_info]


def test_the_service_serves_no_file_from_the_root(svc: Live) -> None:
    for path in ("/signal/signal.db", "/signal.db", "/static/signal.db", "/..%2fsignal/signal.db"):
        assert svc.call("GET", path)[0] == 404


def test_a_second_request_on_the_same_connection_gets_no_reply(svc: Live) -> None:
    request = f"GET /api/me HTTP/1.1\r\nHost: 127.0.0.1:{svc.port}\r\n\r\n".encode()
    sock = raw(svc, request + request)
    reply = read_all(sock)
    sock.close()
    assert reply.count(b"HTTP/1.0 200 OK") == 1
    assert reply.count(b'{"name": null}') == 1


def test_a_connection_past_the_ceiling_is_closed_and_the_held_ones_stay(
    svc: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    server = cast(service._Server, svc.server)
    monkeypatch.setattr(service, "MAX_CONNECTIONS", 2)
    held = [raw(svc, b"") for _ in range(2)]
    try:
        assert wait_for(lambda: server.active_connections == 2)
        extra = raw(svc, b"")
        assert closed_within(extra, 2)
        extra.close()
        assert all(not closed_within(sock, 0.2) for sock in held)
        assert server.active_connections == 2
    finally:
        for sock in held:
            sock.close()
    assert wait_for(lambda: server.active_connections == 0)
    assert svc.call("GET", "/api/me")[0] == 200


def test_a_thread_that_cannot_start_releases_its_slot(
    svc: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    server = cast(service._Server, svc.server)
    start = threading.Thread.start

    def refuse_handler_thread(thread: threading.Thread) -> None:
        if getattr(thread, "_target", None) == server.process_request_thread:
            raise RuntimeError("can't start new thread")
        start(thread)

    monkeypatch.setattr(threading.Thread, "start", refuse_handler_thread)
    sock = raw(svc, b"")
    assert closed_within(sock, 2)
    sock.close()
    assert server.active_connections == 0
    assert server._per_address == {}


def test_a_request_line_cannot_write_control_characters_to_the_log(
    svc: Live, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger=service.log.name)
    host = f"127.0.0.1:{svc.port}"
    line = f"GET /x\x1b[2J\x7f\x9b\r HTTP/1.1\r\nHost: {host}\r\n\r\n"  # ESC, DEL, a C1 byte, CR
    sock = raw(svc, line.encode("latin-1"))
    assert read_all(sock).split(b"\r\n")[0] == b"HTTP/1.0 404 Not Found"
    sock.close()
    messages = [record.getMessage() for record in caplog.records]
    assert '127.0.0.1 "GET /x\\x1b[2J\\x7f\\x9b\\x0d HTTP/1.1" 404 -' in messages
    for message in messages:
        assert not [c for c in message if ord(c) < 0x20 or 0x7F <= ord(c) <= 0x9F]


def test_a_failure_log_line_cannot_write_control_characters_either(
    svc: Live, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("secret-cause")

    monkeypatch.setattr(identity, "current_user", boom)
    host = f"127.0.0.1:{svc.port}"
    sock = raw(svc, f"GET /api/me?\x1b[2J\\n HTTP/1.1\r\nHost: {host}\r\n\r\n".encode())
    reply = read_all(sock)
    sock.close()
    assert b'{"error": "the service failed; see its log"}' in reply and b"secret-cause" not in reply
    failed = [r for r in caplog.records if r.exc_info]
    assert [r.getMessage() for r in failed] == ["GET /api/me?\\x1b[2J\\\\n"]
