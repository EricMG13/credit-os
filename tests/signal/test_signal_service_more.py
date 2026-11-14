"""Signal's HTTP service, the rules the other service files leave unpinned (S-9, part 6).

Run for real on one loopback port (port 0), one server thread at a time, one connection at a time
(at most a few dozen requests in a test), expected values by literal. Nothing here opens sockets or
threads until the system refuses.
"""

from __future__ import annotations

import logging
import socket
import struct
from collections.abc import Iterator
from pathlib import Path

import pytest
from service_support import Live, raw, read_all, wait_for
from test_signal_feedview import build_feed_db

from credit_os.signal import service
from credit_os.signal.service import make_server

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
