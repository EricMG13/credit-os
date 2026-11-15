"""What the service tests share (a sibling module, not a conftest: R49): a server on a thread, the
helper that talks to it, and the raw-socket helpers. Everything binds 127.0.0.1 on port 0."""

from __future__ import annotations

import http.client
import json
import socket
import struct
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

from test_signal_feeds import RSS
from threads_support import AK, ML, T0, team_db

from credit_os.signal.fetch import Fetched
from credit_os.signal.groups import Act, create_group, join
from credit_os.signal.service import Loop, make_server
from credit_os.signal.store import open_db
from credit_os.signal.threads import share_story

NOW = datetime(2026, 11, 13, 10, 0, tzinfo=UTC)
Call = Callable[..., tuple[int, http.client.HTTPMessage, Any]]  # the shape of ``Live.call``
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
        connection = lingering_connection(self.port, 20)
        try:
            connection.request(method, path, body=data, headers=sent)
            response = connection.getresponse()
            text = response.read().decode("utf-8", errors="replace")
            kind = response.getheader("Content-Type") or ""
            return response.status, response.headers, json.loads(text) if "json" in kind else text
        finally:
            connection.close()


LINGER_RESET = struct.pack("ii", 1, 0)  # SO_LINGER on, 0 s: close sends a reset, no TIME_WAIT


def lingering_connection(port: int, timeout: float) -> http.client.HTTPConnection:
    """An HTTP connection to 127.0.0.1:``port``, already connected, closing with a reset."""
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    connection.connect()
    assert connection.sock is not None
    connection.sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, LINGER_RESET)
    return connection


def raw(live: Live, data: bytes) -> socket.socket:
    """A connection to the live server with ``data`` already sent (the caller closes it)."""
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, LINGER_RESET)
    sock.settimeout(10)
    sock.connect(("127.0.0.1", live.port))
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


class RecordedFeed:
    """Stands for ``fetch.fetch`` in a pass: records each URL; the first call raises (a host that
    fell over), every later one returns the recorded feed ``RSS``."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, url: str, etag: str | None, modified: str | None) -> Fetched:
        self.calls.append(url)
        if len(self.calls) == 1:
            raise RuntimeError("the feed host fell over")
        return Fetched(RSS, None, None)


@contextmanager
def pass_in_progress(loop: Loop) -> Iterator[list[str]]:
    """Hold one pass inside its fetch (a recorded feed behind an Event) while the body runs; the
    body gets the URLs fetched so far. The wait is 5 s, so a pass that is not held fails the test."""
    entered, release = threading.Event(), threading.Event()
    calls: list[str] = []

    def blocked(url: str, etag: str | None, modified: str | None) -> Fetched:
        calls.append(url)
        entered.set()
        assert release.wait(timeout=5)
        return Fetched(RSS, None, None)

    loop.fetch_fn = blocked
    worker = threading.Thread(target=loop.run_once, args=(NOW,))
    worker.start()
    try:
        assert entered.wait(timeout=5)
        yield calls
    finally:
        release.set()
        worker.join(timeout=10)
    assert not worker.is_alive()


_TABLES = {
    "groups": "SELECT count(*) FROM groups",
    "group_members": "SELECT count(*) FROM group_members",
    "threads": "SELECT count(*) FROM threads",
    "comments": "SELECT count(*) FROM comments",
    "reactions": "SELECT count(*) FROM reactions",
    "read_marks": "SELECT count(*) FROM read_marks",
}


class Site(Live):
    """A server over a team database (users ak and ml are writers, rd a reader)."""

    def __init__(self, server: ThreadingHTTPServer, root: Path) -> None:
        super().__init__(server)
        self.root = root

    def counts(self) -> dict[str, int]:
        db = open_db(self.root)
        try:
            return {name: db.execute(sql).fetchone()[0] for name, sql in _TABLES.items()}
        finally:
            db.close()


def team(root: Path, *, seeded: bool) -> None:
    """The team's users, sources and stories; seeded adds group 1 "TMT" (everyone; ak made it, ml
    joined at T0) with thread 1 (story 1, ak's note "look", at T0 + 1 minute) and group 2 "Inner"
    (invited; ak the only member) with thread 2 (story 2, ak's note "secret note")."""
    db = team_db(root)
    if seeded:
        tmt = create_group(db, Act(AK, T0), "TMT", "everyone", [])
        join(db, ML.name, tmt, T0)
        later = T0 + timedelta(minutes=1)
        share_story(db, Act(AK, later), tmt, 1, "look")
        inner = create_group(db, Act(AK, T0), "Inner", "invited", [])
        share_story(db, Act(AK, later), inner, 2, "secret note")
    db.close()


def team_site(root: Path, *, seeded: bool) -> Site:
    """The team store (see ``team``) behind a server on a thread; the caller closes it."""
    team(root, seeded=seeded)
    return Site(make_server(root, "127.0.0.1", 0), root)


AK_C, ML_C, RD_C, ZZ_C = (f"signal_name={n}" for n in ("ak", "ml", "rd", "zz"))
NEW_GROUP = {"name": "New", "visibility": "everyone", "topics": []}
Row = tuple[str, str, dict[str, Any] | None]

# Every POST and DELETE route of the groups and threads table, on the world's visible group 1,
# thread 1, comment 1.
WRITES: list[Row] = [
    ("POST", "/api/groups", NEW_GROUP),
    ("POST", "/api/groups/1/members", {}),
    ("POST", "/api/groups/1/members", {"name": "rd"}),
    ("DELETE", "/api/groups/1/members", {}),
    ("DELETE", "/api/groups/1/members", {"name": "ak"}),
    ("POST", "/api/groups/1/threads", {"story_id": 2, "note": "n"}),
    ("POST", "/api/groups/1/threads", {"title": "T", "text": "x"}),
    ("POST", "/api/threads/1/read", {}),
    ("POST", "/api/threads/1/comments", {"text": "hi"}),
    ("POST", "/api/comments/1", {"text": "changed"}),
    ("DELETE", "/api/comments/1", None),
    ("POST", "/api/comments/1/reactions/agree", None),
    ("DELETE", "/api/comments/1/reactions/agree", None),
]
