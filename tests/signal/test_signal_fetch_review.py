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
    Clock,
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
from credit_os.signal.fetch import MAX_LOOKUPS, FetchRefused, Wiring, check_address, fetch
from credit_os.signal.netpin import ConnectionTarget

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


class _SlotSpy:
    """A semaphore of one slot that notes how it was asked and when it was given back."""

    def __init__(self) -> None:
        self.inner = threading.BoundedSemaphore(1)
        self.acquires: list[tuple[bool, float | None]] = []
        self.released = threading.Event()

    def acquire(self, blocking: bool = True, timeout: float | None = None) -> bool:
        self.acquires.append((blocking, timeout))
        return self.inner.acquire(blocking, timeout)

    def release(self) -> None:
        self.inner.release()
        self.released.set()


def test_a_lookup_never_waits_for_a_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    slots = _SlotSpy()
    monkeypatch.setattr(fetch_module, "_LOOKUP_SLOTS", slots)
    held = Held()
    try:
        with pytest.raises(FetchRefused, match="took too long"):
            fetch_module._bounded(held, "feeds.example.org", 0.01)
        with pytest.raises(FetchRefused, match=TOO_MANY):
            fetch_module._bounded(held, "feeds.example.org", 0.01)
    finally:
        held.release.set()
        assert slots.released.wait(5)  # the late worker gives its slot back to this semaphore
    assert slots.acquires == [(False, None), (False, None)]


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


@pytest.mark.parametrize(
    "failure",
    [
        RuntimeError("can't start new thread"),
        MemoryError("no memory for a thread"),
        OSError("too many threads"),
    ],
    ids=["RuntimeError", "MemoryError", "OSError"],
)
def test_a_thread_that_cannot_be_started_is_a_refusal_and_keeps_its_slot_free(
    monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    def no_thread(self: threading.Thread) -> None:
        raise failure

    with monkeypatch.context() as patched:
        patched.setattr(threading.Thread, "start", no_thread)
        for _ in range(MAX_LOOKUPS + 2):
            with pytest.raises(FetchRefused) as refused:
                check_address(URL, resolve=PUBLIC)
            assert str(refused.value) == NOT_STARTED
    for _ in range(MAX_LOOKUPS + 2):  # every slot is free again
        check_address(URL, resolve=PUBLIC)


@pytest.mark.parametrize(
    "failure",
    [RuntimeError("can't build a thread"), MemoryError("no memory for a thread")],
    ids=["RuntimeError", "MemoryError"],
)
def test_a_thread_that_cannot_be_built_is_a_refusal_and_keeps_its_slot_free(
    monkeypatch: pytest.MonkeyPatch, failure: Exception, caplog: pytest.LogCaptureFixture
) -> None:
    def no_thread(*args: object, **kwargs: object) -> threading.Thread:
        raise failure

    with monkeypatch.context() as patched, caplog.at_level(logging.WARNING, logger=LOGGER):
        patched.setattr(threading, "Thread", no_thread)
        for _ in range(MAX_LOOKUPS + 2):  # more refusals than the 8 slots, none may leak one
            with pytest.raises(FetchRefused) as refused:
                check_address(URL, resolve=PUBLIC)
            assert str(refused.value) == NOT_STARTED
    assert "could not start a lookup thread" in caplog.text
    for _ in range(MAX_LOOKUPS + 2):  # every slot is free again
        check_address(URL, resolve=PUBLIC)


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


# F6: values and limits the tests used to read back from production are pinned by literals
def test_the_first_request_sends_exactly_these_headers() -> None:
    wire = Wire(ok())
    run(wire)
    assert wire.requests == [
        (
            "/x",
            {
                "Host": "feeds.example.org",
                "User-Agent": "Mozilla/5.0 (compatible; signal-feed/1.0)",
                "Accept": (
                    "application/atom+xml, application/rss+xml, application/xml;q=0.9, "
                    "text/xml;q=0.8, */*;q=0.5"
                ),
                "Accept-Encoding": "identity",
                "Connection": "close",
            },
        )
    ]


def test_the_per_operation_timeout_is_ten_seconds_on_every_hop() -> None:
    wire = Wire(redirect("https://other.example.org/y"), ok())
    run(wire)
    assert [t.timeout for t in wire.targets] == [10, 10]


def test_a_logged_connect_detail_is_one_line_of_at_most_200_characters(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def connect(target: ConnectionTarget) -> Wire:
        raise OSError("first\n" + "x" * 5000)

    with caplog.at_level(logging.WARNING, logger=LOGGER), pytest.raises(FetchRefused):
        fetch(URL, None, None, resolve=PUBLIC, wiring=Wiring(connect))
    [record] = caplog.records
    assert record.getMessage() == (
        "could not connect to feeds.example.org: OSError: first " + "x" * 194
    )


class _JoinSpy:
    """Records the timeout of every join of a daemon thread, and joins as usual."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.timeouts: list[float | None] = []
        real = threading.Thread.join

        def join(thread: threading.Thread, timeout: float | None = None) -> None:
            if thread.daemon:
                self.timeouts.append(timeout)
            real(thread, timeout)

        monkeypatch.setattr(threading.Thread, "join", join)


def test_a_lookup_is_waited_for_once_for_the_time_left_and_no_longer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fetch_module, "TOTAL_SECONDS", 0.25)
    spy = _JoinSpy(monkeypatch)
    held = Held()
    try:
        with pytest.raises(FetchRefused, match="took too long"):
            run(Wire(ok()), resolve=held, clock=Clock())
    finally:
        held.release.set()
    assert spy.timeouts == [0.25]


def test_check_address_waits_for_a_lookup_once_for_its_constant_and_no_longer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fetch_module, "LOOKUP_SECONDS", 0.25)
    spy = _JoinSpy(monkeypatch)
    held = Held()
    try:
        _a_lookup_that_overruns(held)
    finally:
        held.release.set()
    assert spy.timeouts == [0.25]
