"""What the service tests share (a sibling module, not a conftest: R49): a server on a thread, the
helper that talks to it, and the raw-socket helpers. Everything binds 127.0.0.1 on port 0."""

from __future__ import annotations

import http.client
import json
import socket
import threading
import time
from collections.abc import Callable
from http.server import ThreadingHTTPServer
from typing import Any

SAME = object()  # "the page's own origin", the default for a request that is not a GET


class Live:
    """A server on a thread and the helper that talks to it."""

    def __init__(self, server: ThreadingHTTPServer) -> None:
        self.server = server
        self.port: int = server.server_address[1]
        self.thread = threading.Thread(
            target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True
        )
        self.thread.start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=10)

    def call(
        self, method: str, path: str, **request: Any
    ) -> tuple[int, http.client.HTTPMessage, Any]:
        """Keywords: body (JSON object), raw (bytes), origin (default: the page's own; None for
        none; ``{port}`` is filled in), cookie, host, headers."""
        sent = {"Host": request.get("host") or f"127.0.0.1:{self.port}"}
        origin = request.get("origin", SAME)
        if origin is SAME:
            origin = f"http://127.0.0.1:{self.port}"
        if origin is not None and method != "GET":
            sent["Origin"] = str(origin).replace("{port}", str(self.port))
        if request.get("cookie"):
            sent["Cookie"] = request["cookie"]
        sent.update(request.get("headers") or {})
        body, raw = request.get("body"), request.get("raw")
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=20)
        try:
            connection.request(method, path, body=data, headers=sent)
            response = connection.getresponse()
            text = response.read().decode("utf-8", errors="replace")
            kind = response.getheader("Content-Type") or ""
            return response.status, response.headers, json.loads(text) if "json" in kind else text
        finally:
            connection.close()


def raw(live: Live, data: bytes) -> socket.socket:
    """A connection to the live server with ``data`` already sent (the caller closes it)."""
    sock = socket.create_connection(("127.0.0.1", live.port), timeout=10)
    sock.sendall(data)
    return sock


def closed_within(sock: socket.socket, seconds: float) -> bool:
    """True when the server closed the connection (EOF or reset) within ``seconds``."""
    sock.settimeout(seconds)
    try:
        while sock.recv(4096):
            pass
    except (ConnectionResetError, BrokenPipeError):
        return True
    except TimeoutError:
        return False
    return True


def read_all(sock: socket.socket) -> bytes:
    """Everything the server sends until it closes the connection."""
    sock.settimeout(10)
    reply = b""
    while chunk := sock.recv(4096):
        reply += chunk
    return reply


def wait_for(check: Callable[[], bool], seconds: float = 2.0) -> bool:
    """True once ``check()`` holds, polled for at most ``seconds``."""
    deadline = time.monotonic() + seconds
    while not check():
        if time.monotonic() > deadline:
            return False
        time.sleep(0.01)
    return True
