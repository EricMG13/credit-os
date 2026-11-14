"""The bytes a fetch takes from the wire are bounded, tested on a real loopback socket.

R34 F1: ``http.client`` reads a chunk-size line of ``-1`` as "read to the end of the stream" inside
one ``read(amt)`` call, so the 2 MiB body cap cannot hold it. The pinned connection counts what it
receives and refuses past ``MAX_WIRE_BYTES``. The peers here close their sockets.
"""

import socket
import tracemalloc

import pytest
from signal_fetch_support import (
    Reply,
    Wire,
    fetch_from_peer,
    loopback_peer,
    no_outside_network,
    read_request,
    redirect,
    run,
    through_loopback,
)

from credit_os.signal.fetch import MAX_BYTES, MAX_WIRE_BYTES, FetchRefused
from credit_os.signal.netpin import ReceivedTooMuch

_guard = no_outside_network

MIB = 1024 * 1024
STREAM = 64 * MIB  # what the hostile peer tries to send
PEAK_LIMIT = 12 * MIB  # 8 MiB wire limit and a margin; a read to the end of the stream is 64 MiB


def test_the_wire_limit_is_four_times_the_body_cap_in_numbers() -> None:
    assert MAX_BYTES == 2 * 1024 * 1024
    assert MAX_WIRE_BYTES == 8 * 1024 * 1024


def test_every_hop_is_given_its_own_wire_limit() -> None:
    wire = Wire(redirect("https://other.example.org/y"), Reply(200, b"<rss/>"))
    run(wire)
    assert [t.max_received for t in wire.targets] == [8 * MIB, 8 * MIB]


def test_a_wire_limit_refusal_has_one_fixed_reason() -> None:
    wire = Wire(Reply(200, b"x", on_read=_too_much))
    with pytest.raises(FetchRefused) as refused:
        run(wire)
    assert str(refused.value) == "feed answer is larger than 8 MB on the wire"
    assert wire.closed == 1


def _too_much() -> None:
    raise ReceivedTooMuch(MAX_WIRE_BYTES)


def test_a_chunk_size_of_minus_one_streams_into_a_refusal_not_into_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent: list[int] = []

    def answer(conn: socket.socket) -> None:
        read_request(conn)
        block = b"x" * MIB
        total = 0
        try:
            conn.sendall(
                b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n-1\r\n"
            )
            while total < STREAM:
                conn.sendall(block)
                total += len(block)
        except OSError:
            pass  # the fetch closed its end: the refusal is what this test is about
        sent.append(total)

    with loopback_peer(answer) as port:
        through_loopback(monkeypatch, port)
        tracemalloc.start()
        tracemalloc.reset_peak()
        try:
            with pytest.raises(FetchRefused) as refused:
                fetch_from_peer()
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
    assert str(refused.value) == "feed answer is larger than 8 MB on the wire"
    assert peak < PEAK_LIMIT
    assert sent[0] < STREAM  # the peer was stopped, it did not finish its 64 MiB


@pytest.mark.parametrize("chunk", [None, 8192], ids=["content length", "8 KiB chunks"])
def test_a_body_of_the_cap_comes_through_the_real_wire(
    monkeypatch: pytest.MonkeyPatch, chunk: int | None
) -> None:
    body = b"y" * MAX_BYTES

    def answer(conn: socket.socket) -> None:
        read_request(conn)
        if chunk is None:
            conn.sendall(
                b"HTTP/1.1 200 OK\r\nContent-Length: 2097152\r\nConnection: close\r\n\r\n" + body
            )
            return
        conn.sendall(b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n")
        for start in range(0, len(body), chunk):
            conn.sendall(b"2000\r\n" + body[start : start + chunk] + b"\r\n")  # 0x2000 = 8192
        conn.sendall(b"0\r\n\r\n")

    with loopback_peer(answer) as port:
        through_loopback(monkeypatch, port)
        got = fetch_from_peer()
    assert got.body == body
