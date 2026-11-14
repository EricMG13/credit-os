"""Fetch rules for Signal, on injected resolver, connector and clock: nothing touches a network.

Every test runs under the guard of ``signal_fetch_support`` that fails any name lookup and any
connection to an address outside loopback. Two tests dial 127.0.0.1, a fake peer in this process,
through the real pinned connection.
"""

import socket
import threading
import time
from collections.abc import Iterable
from contextlib import suppress

import pytest
from signal_fetch_support import (
    PUBLIC,
    PUBLIC_IP,
    URL,
    Clock,
    Reply,
    Wire,
    assert_the_guard_is_active,
    fetch_from_peer,
    loopback_peer,
    no_outside_network,
    ok,
    read_request,
    redirect,
    run,
    through_loopback,
)

from credit_os.signal import fetch as fetch_module
from credit_os.signal.fetch import (
    MAX_BYTES,
    Fetched,
    FetchRefused,
    fetch,
)

# The guard is an autouse fixture; naming it here applies it to every test in this file.
_guard = no_outside_network


def test_the_guard_is_active_in_this_file() -> None:
    assert_the_guard_is_active()


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


# Through the real pinned connection to a fake peer on loopback, no TLS; port 443 is redialled
def test_a_fetch_through_the_real_pinned_connection_reaches_the_peer_in_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[bytes] = []

    def answer(conn: socket.socket) -> None:
        seen.append(read_request(conn))
        reply = b'HTTP/1.1 200 OK\r\nContent-Length: 6\r\nETag: "v1"\r\nConnection: close\r\n\r\n'
        conn.sendall(reply + b"<rss/>")

    with loopback_peer(answer) as port:
        tls = through_loopback(monkeypatch, port)
        got = fetch(
            "https://feeds.example.org/x?a=1", None, None, resolve=lambda host: ["127.0.0.1"]
        )
    assert got == Fetched(b"<rss/>", '"v1"', None)
    assert seen[0].startswith(b"GET /x?a=1 HTTP/1.1\r\n")
    assert b"Host: feeds.example.org\r\n" in seen[0]
    assert b"Accept-Encoding: identity\r\n" in seen[0]
    assert tls.hostnames == ["feeds.example.org"]


def test_a_refusal_in_the_body_through_the_real_connection_closes_the_peers_socket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
        through_loopback(monkeypatch, port)
        fetch_from_peer()
    assert outcome == ["closed"]  # while the refusal and its traceback still hold the response
    assert refused.value.__traceback__ is not None


def test_a_peer_that_never_answers_ends_the_fetch_at_the_total_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fetch_module, "TOTAL_SECONDS", 0.3)
    release = threading.Event()

    def answer(conn: socket.socket) -> None:
        read_request(conn)
        release.wait(5)

    started = time.monotonic()
    with loopback_peer(answer) as port:
        through_loopback(monkeypatch, port)
        with pytest.raises(FetchRefused, match="fetch failed: "):
            fetch_from_peer()
        release.set()
    assert 0.2 <= time.monotonic() - started < 3


def test_a_loopback_answer_is_refused_when_no_test_lets_it_through() -> None:
    with pytest.raises(FetchRefused, match="which is not a public address"):
        fetch(URL, None, None, resolve=lambda host: ["127.0.0.1"])
