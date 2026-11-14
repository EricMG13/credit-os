"""Fetch rules for Signal, on injected resolver, connector and clock: nothing touches a network.

Every test runs under a guard that fails any name lookup and any connection to an address outside
loopback. Two tests dial 127.0.0.1, a fake peer in this process, through the real pinned connection.
"""

import ipaddress
import socket
import threading
import time
from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import contextmanager, suppress
from typing import Any

import pytest

from credit_os.signal import fetch as fetch_module
from credit_os.signal import netpin
from credit_os.signal.fetch import (
    MAX_BYTES,
    Fetched,
    FetchRefused,
    Wiring,
    fetch,
)
from credit_os.signal.netpin import ConnectionTarget

PUBLIC_IP = "93.184.216.34"
URL = "https://feeds.example.org/x"


@pytest.fixture(autouse=True)
def no_outside_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail any lookup of a name and any connect to an address that is not loopback."""
    lookup = socket.getaddrinfo
    connect = socket.socket.connect

    def guarded_lookup(host: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pytest.fail(f"a test looked up the name {host!r}")
        return lookup(host, *args, **kwargs)

    def guarded_connect(self: socket.socket, address: Any) -> None:
        host = address[0] if isinstance(address, tuple) else address
        try:
            outside = not ipaddress.ip_address(host).is_loopback
        except ValueError:
            outside = True
        if outside:
            pytest.fail(f"a test connected to {address!r}")
        connect(self, address)

    monkeypatch.setattr(socket, "getaddrinfo", guarded_lookup)
    monkeypatch.setattr(socket.socket, "connect", guarded_connect)


def PUBLIC(host: str) -> Iterable[str]:
    return [PUBLIC_IP]


def _map(host: str) -> Iterable[str]:
    return ["10.0.0.1"] if host == "internal.example" else [PUBLIC_IP]


class Reply:
    def __init__(
        self,
        status: int,
        body: bytes = b"",
        headers: Mapping[str, str] | None = None,
        on_read: Callable[[], None] | None = None,
    ) -> None:
        self.status = status
        self.headers = {name.lower(): value for name, value in (headers or {}).items()}
        self.body = body
        self.consumed = 0
        self.on_read = on_read
        self.closed = 0

    def getheader(self, name: str, /) -> str | None:
        return self.headers.get(name.lower())

    def read(self, amt: int) -> bytes:
        if self.on_read is not None:
            self.on_read()
        chunk = self.body[self.consumed : self.consumed + amt]
        self.consumed += len(chunk)
        return chunk

    def close(self) -> None:
        self.closed += 1


def redirect(location: str | None, status: int = 302) -> Reply:
    return Reply(status, b"r" * 100, {"Location": location} if location else None)


class Wire:
    """A connector that answers each request from a script, in order, and records what it saw."""

    def __init__(self, *replies: Reply | Exception) -> None:
        self.script = list(replies)
        self.targets: list[ConnectionTarget] = []
        self.requests: list[tuple[str, dict[str, str]]] = []
        self.closed = 0
        self.on_response: Callable[[], None] = lambda: None

    def __call__(self, target: ConnectionTarget) -> "Wire":
        self.targets.append(target)
        return self

    def request(self, method: str, url: str, *, headers: Mapping[str, str]) -> None:
        assert method == "GET"
        self.requests.append((url, dict(headers)))

    def getresponse(self) -> Reply:
        self.on_response()
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        return step

    def close(self) -> None:
        self.closed += 1


class Counting:
    """A resolver that answers from a list, one answer per call, then repeats the last."""

    def __init__(self, *answers: list[str]) -> None:
        self.answers = list(answers)
        self.calls: list[str] = []

    def __call__(self, host: str) -> Iterable[str]:
        self.calls.append(host)
        return self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def run(
    wire: Wire,
    url: str = URL,
    etag: str | None = None,
    modified: str | None = None,
    **kw: Any,
) -> Fetched:
    kw.setdefault("resolve", _map)
    clock = kw.pop("clock", time.monotonic)
    return fetch(url, etag, modified, wiring=Wiring(wire, clock), **kw)


def ok() -> Reply:
    return Reply(200, b"<rss/>")


def test_the_guard_refuses_a_name_lookup_and_a_connect_outside_loopback() -> None:
    with pytest.raises(pytest.fail.Exception, match="looked up the name"):
        socket.getaddrinfo("feeds.example.org", 443)
    with pytest.raises(pytest.fail.Exception, match="connected to"):
        socket.create_connection((PUBLIC_IP, 443), 1)
    assert socket.getaddrinfo("127.0.0.1", 443)


# Total deadline, on a fake clock
def test_a_clock_past_the_deadline_refuses_before_any_connection() -> None:
    clock = Clock()
    wire = Wire(ok())

    def slow(host: str) -> Iterable[str]:
        clock.advance(11)
        return [PUBLIC_IP]

    with pytest.raises(FetchRefused, match="longer than 10 seconds"):
        run(wire, resolve=slow, clock=clock)
    assert not wire.targets


def test_a_slow_redirect_hop_lookup_opens_no_second_connection() -> None:
    clock = Clock()
    wire = Wire(redirect("https://other.example.org/y"), ok())

    def slow_hop(host: str) -> Iterable[str]:
        if host == "other.example.org":
            clock.advance(11)
        return [PUBLIC_IP]

    with pytest.raises(FetchRefused, match="longer than 10 seconds"):
        run(wire, resolve=slow_hop, clock=clock)
    assert [t.host for t in wire.targets] == ["feeds.example.org"]


def test_the_deadline_is_one_for_every_hop_and_handed_to_the_connection() -> None:
    clock = Clock()
    wire = Wire(redirect("https://other.example.org/y"), ok())
    run(wire, clock=clock)
    assert {t.deadline for t in wire.targets} == {1000.0 + fetch_module.TOTAL_SECONDS}
    assert all(t.clock is clock for t in wire.targets)


def test_headers_that_arrive_after_the_deadline_are_refused() -> None:
    clock = Clock()
    wire = Wire(ok())
    wire.on_response = lambda: clock.advance(11)
    with pytest.raises(FetchRefused, match="longer than 10 seconds"):
        run(wire, clock=clock)


def test_a_body_that_trickles_past_the_deadline_is_refused() -> None:
    clock = Clock()
    reply = Reply(200, b"x" * 100, on_read=lambda: clock.advance(6))
    with pytest.raises(FetchRefused, match="longer than 10 seconds"):
        run(Wire(reply), clock=clock)


def test_a_body_end_reached_after_the_deadline_is_refused() -> None:
    clock = Clock()
    reply = Reply(200, b"", on_read=lambda: clock.advance(11))
    with pytest.raises(FetchRefused, match="longer than 10 seconds"):
        run(Wire(reply), clock=clock)


# The pin is the last guard: fetch's own check off, a private answer, the production connector
def test_a_private_address_that_passes_fetchs_check_is_refused_by_the_pin_and_not_dialled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dialled: list[object] = []

    def record(address: object, *args: object, **kwargs: object) -> socket.socket:
        dialled.append(address)
        raise ConnectionRefusedError("a test refused the dial")

    monkeypatch.setattr(socket, "create_connection", record)
    monkeypatch.setattr(fetch_module, "_checked", lambda host, resolve: ["10.0.0.1"])
    with pytest.raises(FetchRefused, match="fetch failed: the pinned address is not a public"):
        fetch(URL, None, None, resolve=PUBLIC)
    assert dialled == []


def explode() -> None:
    raise ZeroDivisionError("a test read failed")


# The response is closed as well as the connection, on every path
@pytest.mark.parametrize(
    "reply",
    [
        Reply(200, b"<rss/>"),
        Reply(304),
        Reply(404),
        Reply(200, b"x" * (MAX_BYTES + 1)),
        Reply(200, b"<rss/>", {"Content-Length": "1000"}),
        Reply(200, b"x", {"Content-Encoding": "gzip"}),
        Reply(200, b"x", {"Content-Length": str(MAX_BYTES + 1)}),
        Reply(200, b"<rss/>", on_read=explode),
    ],
    ids=["200", "304", "404", "over the cap", "ended early", "encoding", "declared", "read fails"],
)
def test_the_response_is_closed_on_every_path(reply: Reply) -> None:
    wire = Wire(reply)
    with suppress(FetchRefused, ZeroDivisionError):
        run(wire)
    assert (reply.closed, wire.closed) == (1, 1)


def test_every_redirect_response_is_closed_and_the_connection_after_each() -> None:
    first, last = redirect("https://other.example.org/y"), ok()
    run(Wire(first, last))
    assert (first.closed, last.closed) == (1, 1)


def test_a_redirect_that_is_refused_closes_its_response() -> None:
    reply = redirect("http://feeds.example.org/y")
    wire = Wire(reply)
    with pytest.raises(FetchRefused):
        run(wire)
    assert (reply.closed, wire.closed) == (1, 1)


def test_a_response_that_fails_to_close_still_closes_the_connection() -> None:
    class Stuck(Reply):
        def close(self) -> None:
            raise OSError("socket already gone")

    wire = Wire(Stuck(200, b"<rss/>"))
    with pytest.raises(FetchRefused, match="socket already gone"):
        run(wire)
    assert wire.closed == 1


def test_a_failure_before_any_response_closes_only_the_connection() -> None:
    wire = Wire(OSError("socket broke"))
    with pytest.raises(FetchRefused):
        run(wire)
    assert wire.closed == 1


# Through the real pinned connection to a fake peer on loopback, no TLS
class NoTLS:
    """Stands for the TLS context: hands the socket back unwrapped and notes the host name."""

    def __init__(self) -> None:
        self.hostnames: list[str] = []

    def wrap_socket(self, sock: socket.socket, *, server_hostname: str) -> socket.socket:
        self.hostnames.append(server_hostname)
        return sock


def read_request(conn: socket.socket) -> bytes:
    data = b""
    while b"\r\n\r\n" not in data:
        data += conn.recv(4096)
    return data


@contextmanager
def loopback_peer(answer: Callable[[socket.socket], None]) -> Iterator[int]:
    """Serve one connection on 127.0.0.1 with ``answer``; yields the port."""
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.settimeout(5)

    def serve() -> None:
        conn, _ = listener.accept()
        with conn:
            conn.settimeout(5)
            answer(conn)

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        yield listener.getsockname()[1]
    finally:
        thread.join(10)
        listener.close()


def fetch_from(port: int) -> Fetched:
    url = f"https://feeds.example.org:{port}/x"
    return fetch(url, None, None, resolve=lambda host: ["127.0.0.1"])


def through_loopback(monkeypatch: pytest.MonkeyPatch) -> NoTLS:
    """Let 127.0.0.1 pass the one address check, and leave TLS out of the connection."""
    tls = NoTLS()
    monkeypatch.setattr(netpin, "is_public", lambda addr: addr == "127.0.0.1")
    monkeypatch.setattr(netpin, "tls_context", lambda: tls)
    return tls


def test_a_fetch_through_the_real_pinned_connection_reaches_the_peer_in_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tls = through_loopback(monkeypatch)
    seen: list[bytes] = []

    def answer(conn: socket.socket) -> None:
        seen.append(read_request(conn))
        reply = b'HTTP/1.1 200 OK\r\nContent-Length: 6\r\nETag: "v1"\r\nConnection: close\r\n\r\n'
        conn.sendall(reply + b"<rss/>")

    with loopback_peer(answer) as port:
        got = fetch(
            f"https://feeds.example.org:{port}/x?a=1",
            None,
            None,
            resolve=lambda host: ["127.0.0.1"],
        )
    assert got == Fetched(b"<rss/>", '"v1"', None)
    assert seen[0].startswith(b"GET /x?a=1 HTTP/1.1\r\n")
    assert f"Host: feeds.example.org:{port}\r\n".encode() in seen[0]
    assert b"Accept-Encoding: identity\r\n" in seen[0]
    assert tls.hostnames == ["feeds.example.org"]


def test_a_refusal_in_the_body_through_the_real_connection_closes_the_peers_socket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    through_loopback(monkeypatch)
    outcome: list[str] = []

    def answer(conn: socket.socket) -> None:
        read_request(conn)
        conn.sendall(b"HTTP/1.1 200 OK\r\nConnection: close\r\n\r\n" + b"x" * (MAX_BYTES + 1))
        try:
            outcome.append("closed" if conn.recv(1) == b"" else "data")
        except ConnectionResetError:
            outcome.append("closed")
        except TimeoutError:
            outcome.append("still open")

    with loopback_peer(answer) as port, pytest.raises(FetchRefused, match="2 MB") as refused:
        fetch_from(port)
    assert outcome == ["closed"]  # while the refusal and its traceback still hold the response
    assert refused.value.__traceback__ is not None


def test_a_peer_that_never_answers_ends_the_fetch_at_the_total_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    through_loopback(monkeypatch)
    monkeypatch.setattr(fetch_module, "TOTAL_SECONDS", 0.3)
    release = threading.Event()

    def answer(conn: socket.socket) -> None:
        read_request(conn)
        release.wait(5)

    started = time.monotonic()
    with loopback_peer(answer) as port:
        with pytest.raises(FetchRefused, match="fetch failed: "):
            fetch_from(port)
        release.set()
    assert 0.2 <= time.monotonic() - started < 3


def test_a_loopback_answer_is_refused_when_no_test_lets_it_through() -> None:
    with pytest.raises(FetchRefused, match="which is not a public address"):
        fetch(URL, None, None, resolve=lambda host: ["127.0.0.1"])
