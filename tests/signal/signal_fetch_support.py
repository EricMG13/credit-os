"""Helpers shared by the fetcher's test files; not a test module (as ``tests/provider`` does).

``no_outside_network`` is the guard every fetch test runs under: it fails any lookup of a name and
any connection to an address outside loopback. Each test file imports it by name, which is what
applies it (it is autouse). ``Wire``, ``Reply``, ``Clock`` and ``Counting`` stand for the
connector, the response, the clock and the resolver; ``run`` calls ``fetch`` on them.
"""

import ipaddress
import socket
import threading
import time
from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import contextmanager
from typing import Any

import pytest

from credit_os.signal import netpin
from credit_os.signal.fetch import Fetched, Wiring, fetch
from credit_os.signal.netpin import ConnectionTarget

PUBLIC_IP = "93.184.216.34"
URL = "https://feeds.example.org/x"
TEST_NET = "192.0.2.1"  # RFC 5737 documentation address: no real host answers on it


def install_guard(
    monkeypatch: pytest.MonkeyPatch,
    *,
    lookup: Callable[..., Any] = socket.getaddrinfo,
    connect: Callable[..., Any] = socket.socket.connect,
) -> None:
    """Fail any lookup of a name and any connect to an address that is not loopback.

    ``lookup`` and ``connect`` are what a permitted call reaches; the defaults are the real ones.
    """

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


@pytest.fixture(autouse=True)
def no_outside_network(monkeypatch: pytest.MonkeyPatch) -> None:
    install_guard(monkeypatch)


def assert_the_guard_is_active() -> None:
    """Fail unless a name lookup and a connect off loopback are both stopped by the guard."""
    with pytest.raises(pytest.fail.Exception, match="looked up the name"):
        socket.getaddrinfo("feeds.example.org", 443)
    with socket.socket() as sock:
        sock.settimeout(0.05)
        with pytest.raises(pytest.fail.Exception, match="connected to"):
            sock.connect((TEST_NET, 443))
    assert socket.getaddrinfo("127.0.0.1", 443)


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
        on_close: Callable[[], None] | None = None,
    ) -> None:
        self.status = status
        self.headers = {name.lower(): value for name, value in (headers or {}).items()}
        self.body = body
        self.consumed = 0
        self.on_read = on_read
        self.on_close = on_close
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
        if self.on_close is not None:
            self.on_close()


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


def through_loopback(monkeypatch: pytest.MonkeyPatch, port: int) -> NoTLS:
    """Let 127.0.0.1 pass the one address check, leave TLS out, and dial ``port`` for 443.

    A fetch dials port 443 only, which a test cannot listen on; the pinned connection is real and
    its dial to (127.0.0.1, 443) goes to the peer's port instead.
    """
    tls = NoTLS()
    dial = socket.create_connection
    monkeypatch.setattr(netpin, "is_public", lambda addr: addr == "127.0.0.1")
    monkeypatch.setattr(netpin, "tls_context", lambda: tls)

    def redialled(address: tuple[str, int], *args: Any, **kwargs: Any) -> socket.socket:
        host, number = address
        return dial((host, port if number == 443 else number), *args, **kwargs)

    monkeypatch.setattr(socket, "create_connection", redialled)
    return tls


def fetch_from_peer() -> Fetched:
    return fetch(URL, None, None, resolve=lambda host: ["127.0.0.1"])
