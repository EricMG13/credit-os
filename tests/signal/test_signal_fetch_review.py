"""R34 F2 to F5 (the whole-branch review of the fetcher): exact chunked, a redirect's host not
echoed, a cap on lookup workers, an unasked 304 refused. Expected texts are written by hand.
"""

import logging
import socket
import threading
import time
from collections.abc import Callable, Iterable

import pytest
from signal_fetch_support import (
    PUBLIC,
    PUBLIC_IP,
    URL,
    Reply,
    Wire,
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
from credit_os.signal.fetch import MAX_LOOKUPS, FetchRefused, check_address

_guard = no_outside_network

LOGGER = "credit_os.signal.fetch"
TOO_MANY = "too many lookups are still waiting for an answer"
NOT_STARTED = "could not start a lookup of the feed's host"


# F2: Transfer-Encoding is exactly chunked, in any case, with nothing around it
PADDED = [
    "chunked ",
    "chunked\t",
    "chunked\x0b",
    "chunked\x0c",
    "chunked\xa0",
    "chunked\x1c",
    " chunked ",
    "CHUNKED\t",
    "\tChUnKeD",
]


@pytest.mark.parametrize("value", PADDED)
def test_a_padded_transfer_encoding_is_refused(value: str) -> None:
    reply = Reply(200, b"<rss/>", {"Transfer-Encoding": value})
    with pytest.raises(FetchRefused, match="transfer encoding"):
        run(Wire(reply))
    assert reply.consumed == 0 and reply.closed == 1


@pytest.mark.parametrize("padding", [b" ", b"\t"], ids=["space", "tab"])
def test_chunked_with_trailing_white_space_on_the_real_wire_is_refused_not_returned_raw(
    monkeypatch: pytest.MonkeyPatch, padding: bytes
) -> None:
    def answer(conn: socket.socket) -> None:
        read_request(conn)
        head = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked" + padding + b"\r\n"
        conn.sendall(head + b"Connection: close\r\n\r\n6\r\n<rss/>\r\n0\r\n\r\n")

    with loopback_peer(answer) as port:
        through_loopback(monkeypatch, port)
        with pytest.raises(FetchRefused, match="transfer encoding"):
            fetch_from_peer()


# F3: a redirect's host is the server's text: logged, not returned
def _after_redirect(other: Callable[[str], Iterable[str]]) -> Callable[[str], Iterable[str]]:
    """A resolver that answers the first host publicly and the redirect's host with ``other``."""

    def resolve(host: str) -> Iterable[str]:
        return [PUBLIC_IP] if host == "feeds.example.org" else other(host)

    return resolve


def _gone(host: str) -> Iterable[str]:
    raise OSError("name not known")


REDIRECT_CASES = [
    (_gone, "could not resolve the redirect's host: name not known"),
    (lambda host: [], "the redirect's host resolved to no address"),
    (
        lambda host: ["10.0.0.1"],
        "the redirect's host resolves to 10.0.0.1, which is not a public address",
    ),
]


@pytest.mark.parametrize(("resolver", "reason"), REDIRECT_CASES, ids=["gone", "empty", "private"])
def test_a_redirects_host_is_logged_and_not_in_the_reason(
    caplog: pytest.LogCaptureFixture, resolver: Callable[[str], Iterable[str]], reason: str
) -> None:
    wire = Wire(redirect("https://other.example.org/y"), ok())
    with caplog.at_level(logging.WARNING, logger=LOGGER), pytest.raises(FetchRefused) as refused:
        run(wire, resolve=_after_redirect(resolver))
    assert str(refused.value) == reason
    [record] = [r for r in caplog.records if r.name == LOGGER]
    assert record.levelno == logging.WARNING
    assert "other.example.org" in record.getMessage()


# F4: at most MAX_LOOKUPS lookup workers alive
class Held:
    """A resolver that does not return until released; counts the calls it received."""

    def __init__(self) -> None:
        self.release = threading.Event()
        self.calls = 0

    def __call__(self, host: str) -> Iterable[str]:
        self.calls += 1
        self.release.wait(10)
        return [PUBLIC_IP]


def _a_lookup_that_overruns(held: Held) -> None:
    with pytest.raises(FetchRefused, match="took too long"):
        check_address(URL, resolve=held)


def _until_a_lookup_is_free() -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            check_address(URL, resolve=PUBLIC)
            return
        except FetchRefused:
            threading.Event().wait(0.01)
    pytest.fail("no lookup slot was freed within 10 seconds of the resolvers returning")


def test_the_lookup_cap_is_eight() -> None:
    assert MAX_LOOKUPS == 8


def test_a_ninth_lookup_while_eight_are_waiting_is_refused_without_a_thread_or_a_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fetch_module, "LOOKUP_SECONDS", 0.01)
    held = Held()
    try:
        for _ in range(8):
            _a_lookup_that_overruns(held)
        threads = threading.active_count()
        with pytest.raises(FetchRefused) as refused:
            check_address(URL, resolve=held)
        assert str(refused.value) == TOO_MANY
        assert (held.calls, threading.active_count()) == (8, threads)
        wire = Wire(ok())
        with pytest.raises(FetchRefused) as through_fetch:
            run(wire, resolve=held)
        assert str(through_fetch.value) == TOO_MANY
        assert not wire.targets
    finally:
        held.release.set()
    _until_a_lookup_is_free()


def test_a_slot_is_released_when_the_late_lookup_returns() -> None:
    held = Held()
    for _ in range(8):
        with pytest.raises(FetchRefused, match="took too long"):
            fetch_module._bounded(held, "feeds.example.org", 0.01)
    with pytest.raises(FetchRefused, match=TOO_MANY):
        fetch_module._bounded(held, "feeds.example.org", 0.01)
    held.release.set()
    _until_a_lookup_is_free()
    assert fetch_module._bounded(PUBLIC, "feeds.example.org", 5) == [PUBLIC_IP]


def test_lookups_that_end_in_an_error_never_use_up_the_cap() -> None:
    def broken(host: str) -> Iterable[str]:
        raise OSError("name not known")

    for _ in range(MAX_LOOKUPS + 2):
        with pytest.raises(FetchRefused, match="could not resolve feeds.example.org"):
            check_address(URL, resolve=broken)


def test_a_thread_that_cannot_be_started_is_a_refusal_and_keeps_its_slot_free(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_thread(self: threading.Thread) -> None:
        raise RuntimeError("can't start new thread")

    monkeypatch.setattr(threading.Thread, "start", no_thread)
    for _ in range(MAX_LOOKUPS + 2):
        with pytest.raises(FetchRefused) as refused:
            check_address(URL, resolve=PUBLIC)
        assert str(refused.value) == NOT_STARTED


# F5: a 304 to a request that carried no validator is refused
@pytest.mark.parametrize(
    ("etag", "modified"),
    [
        (None, None),
        ('"a"\r\nX: y', "M" * 300),
        ("", ""),
    ],
    ids=["nothing stored", "both unusable", "both empty"],
)
def test_a_304_to_a_request_that_carried_no_validator_is_refused(
    etag: str | None, modified: str | None
) -> None:
    reply = Reply(304)
    wire = Wire(reply)
    with pytest.raises(FetchRefused) as refused:
        run(wire, etag=etag, modified=modified)
    assert str(refused.value) == "the server answered 304, but it was sent no validators"
    assert (reply.closed, wire.closed) == (1, 1)
    assert "If-None-Match" not in wire.requests[0][1]
    assert "If-Modified-Since" not in wire.requests[0][1]


def test_a_304_to_a_request_with_only_one_validator_is_accepted() -> None:
    assert run(Wire(Reply(304)), modified="Fri").modified == "Fri"
    assert run(Wire(Reply(304)), etag='"abc"').etag == '"abc"'
