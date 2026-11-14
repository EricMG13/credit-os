"""Fetch rules R30 and the review's gaps: address text, port 443, connect reason, bounded lookups,
transfer encoding, what a ValueError means, and the deadline's remaining corners.

Run on ``signal_fetch_support``; nothing touches a network beyond a loopback peer.
"""

import logging
import socket
import ssl
import threading
import time
from collections.abc import Iterable
from typing import Any

import pytest
from signal_fetch_support import (
    PUBLIC,
    PUBLIC_IP,
    TEST_NET,
    URL,
    Clock,
    Counting,
    Reply,
    Wire,
    assert_the_guard_is_active,
    fetch_from_peer,
    install_guard,
    loopback_peer,
    no_outside_network,
    ok,
    read_request,
    redirect,
    run,
    through_loopback,
)

from credit_os.signal import fetch as fetch_module
from credit_os.signal import netpin
from credit_os.signal.fetch import (
    LOOKUP_SECONDS,
    Fetched,
    FetchRefused,
    Wiring,
    check_address,
    fetch,
)
from credit_os.signal.netpin import ConnectionTarget

# The guard is an autouse fixture; naming it here applies it to every test in this file.
_guard = no_outside_network

LOGGER = "credit_os.signal.fetch"
NOT_VALID = "feed address is not valid"
CONNECT_REASON = "could not connect to the feed's server"
LOOKUP_REASON = "looking up the feed's host took too long"
DEADLINE = "feed took longer than 10 seconds"


def test_the_guard_is_active_in_this_file() -> None:
    assert_the_guard_is_active()


def test_the_guard_stops_a_connect_off_loopback_before_it_reaches_a_socket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reached: list[Any] = []
    looked_up: list[Any] = []

    def lookup(host: Any, *args: Any, **kwargs: Any) -> list[Any]:
        looked_up.append(host)
        return []

    def connect(sock: socket.socket, address: Any) -> None:
        reached.append(address)

    install_guard(monkeypatch, lookup=lookup, connect=connect)
    with socket.socket() as sock:
        for outside in [(TEST_NET, 443), ("2001:db8::1", 443, 0, 0), ("feeds.example.org", 443)]:
            with pytest.raises(pytest.fail.Exception, match="connected to"):
                sock.connect(outside)
        sock.connect(("127.0.0.1", 9))  # permitted: recorded, never dialled
    with pytest.raises(pytest.fail.Exception, match="looked up the name"):
        socket.getaddrinfo("feeds.example.org", 443)
    socket.getaddrinfo("127.0.0.1", 443)
    assert reached == [("127.0.0.1", 9)]
    assert looked_up == ["127.0.0.1"]


# R30 address text: [\x21-\x7e]{1,2048}, checked before urlsplit, one fixed reason
BAD_TEXT = {
    "tab in the host": "https://feeds.trusted-bank.example\t.attacker.example/rss",
    "cr in the host": "https://feeds.trusted-bank.example\r.attacker.example/rss",
    "lf in the host": "https://feeds.trusted-bank.example\n.attacker.example/rss",
    "escape in a fragment": "https://attacker.example/#\x1b[2K\x1b[Ghttps://feeds.example.com/",
    "right-to-left override": "https://attacker.example/#\N{RIGHT-TO-LEFT OVERRIDE}sr/elpmaxe.knab",
    "leading control": "\x1b[8mhttps://attacker.example/",
    "leading space": " https://feeds.example.org/",
    "space in the path": "https://feeds.example.org/a b",
    "nul": "https://feeds.example.org/a\x00b",
    "del": "https://feeds.example.org/?q=\x7f",
    "non-ascii path": "https://feeds.example.org/actualités",
    "non-ascii host": "https://m\u00fcnchen.example/",
    "kelvin sign host": "https://\u212aeeds.example.org/feed",
    "100 KB": "https://feeds.example.org/" + "a" * 100_000,
    "2049 characters": "https://feeds.example.org/" + "a" * (2049 - 26),
    "empty": "",
}


@pytest.mark.parametrize("url", BAD_TEXT.values(), ids=BAD_TEXT)
def test_address_text_outside_printable_ascii_is_refused_with_a_fixed_reason(url: str) -> None:
    resolver = Counting([PUBLIC_IP])
    wire = Wire(ok())
    with pytest.raises(FetchRefused) as proposed:
        check_address(url, resolve=resolver)
    with pytest.raises(FetchRefused) as fetched:
        run(wire, url, resolve=resolver)
    assert (str(proposed.value), str(fetched.value)) == (NOT_VALID, NOT_VALID)
    assert not resolver.calls and not wire.targets


def test_the_text_is_refused_before_urlsplit_reads_it(monkeypatch: pytest.MonkeyPatch) -> None:
    def never(url: str) -> Any:
        raise AssertionError("urlsplit read an address that is not printable ASCII")

    monkeypatch.setattr(fetch_module, "urlsplit", never)
    with pytest.raises(FetchRefused, match=NOT_VALID):
        check_address("https://feeds.example.org/\t", resolve=PUBLIC)


def test_an_address_of_exactly_2048_characters_is_read_and_one_more_is_not() -> None:
    longest = "https://feeds.example.org/" + "a" * (2048 - 26)
    assert len(longest) == 2048
    check_address(longest, resolve=PUBLIC)
    assert run(Wire(ok()), longest).body == b"<rss/>"
    with pytest.raises(FetchRefused, match=NOT_VALID):
        check_address(longest + "a", resolve=PUBLIC)


@pytest.mark.parametrize("netloc", ["\u212aeeds.example.org", "m\u00fcnchen.example"])
def test_the_host_rule_itself_refuses_non_ascii_whatever_its_caller_checked(netloc: str) -> None:
    # U+212A (Kelvin sign) lower-cases to "k"; the rule must see it before lower-casing.
    with pytest.raises(FetchRefused, match="plain host name"):
        fetch_module._plain_host(netloc)


def test_a_printable_fragment_is_not_part_of_the_request() -> None:
    wire = Wire(ok())
    run(wire, "https://feeds.example.org/x?a=1#top")
    assert wire.requests[0][0] == "/x?a=1"


@pytest.mark.parametrize(
    "url",
    [
        "https://next.example.com:PWNED-see-evil-example/",
        "https://[PWNED-call-evil-example]/",
        "https://[::PWNED::1]/",
        "https://[vPWNED]/",
        "https://next.example.com:99999/",
        "https://[::1/x",
    ],
)
def test_an_address_urlsplit_cannot_read_gives_no_text_of_it(url: str) -> None:
    with pytest.raises(FetchRefused) as refused:
        check_address(url, resolve=PUBLIC)
    assert str(refused.value) == NOT_VALID


@pytest.mark.parametrize(
    ("location", "reason"),
    [
        ("https://next.example.org:PWNED-see-evil-example/", NOT_VALID),
        ("https://[PWNED-call-evil-example]/", "the redirect has no usable location"),
        ("https://next.example.org/PWNED\x00\x1b[31m", NOT_VALID),
        ("https://next.example.org/" + "PWNED" * 1000, NOT_VALID),
        ("/actualités", NOT_VALID),
    ],
    ids=["port text", "bracket host", "control characters", "long", "non-ascii"],
)
def test_a_redirect_to_an_address_that_is_not_valid_gives_no_text_of_it(
    location: str, reason: str
) -> None:
    wire = Wire(redirect(location), ok())
    with pytest.raises(FetchRefused) as refused:
        run(wire)
    assert str(refused.value) == reason
    assert len(wire.targets) == 1


@pytest.mark.parametrize(
    "location",
    [
        "https://next.example.org/x\tyz",
        "https://next.exa\tmple.org/x",
        "https://next.example.org/x ",
        "https://next.example.org/x\r\ny",
        "https://next.example.org/caf\u00e9",
        "https://next.example.org/" + "a" * (2049 - len("https://next.example.org/")),
    ],
    ids=["tab in path", "tab in host", "trailing space", "crlf", "non-ascii", "2049 long"],
)
def test_a_redirect_is_checked_as_the_server_sent_it(location: str) -> None:
    wire = Wire(redirect(location), ok())
    with pytest.raises(FetchRefused) as refused:
        run(wire)
    assert str(refused.value) == NOT_VALID
    assert len(wire.targets) == 1


@pytest.mark.parametrize(
    ("location", "path"),
    [("/other?a=1", "/other?a=1"), ("https://other.example.org/y", "/y")],
    ids=["relative", "absolute"],
)
def test_a_normal_redirect_is_still_followed(location: str, path: str) -> None:
    wire = Wire(redirect(location), ok())
    run(wire)
    assert len(wire.targets) == 2
    assert wire.requests[1][0] == path


# R30 port: the first hop uses 443, as every redirect hop does
@pytest.mark.parametrize("port", ["8443", "80", "444", "65535", "0", "00"])
def test_the_first_hop_must_use_port_443(port: str) -> None:
    resolver = Counting([PUBLIC_IP])
    wire = Wire(ok())
    url = f"https://feeds.example.org:{port}/x"
    with pytest.raises(FetchRefused, match="port"):
        run(wire, url, resolve=resolver)
    with pytest.raises(FetchRefused, match="port"):
        check_address(url, resolve=resolver)
    assert not resolver.calls and not wire.targets


def test_an_explicit_443_on_the_first_hop_is_accepted_and_the_host_header_is_bare() -> None:
    wire = Wire(ok())
    run(wire, "https://feeds.example.org:443/x")
    check_address("https://feeds.example.org:443/x", resolve=PUBLIC)
    assert wire.targets[0].port == 443
    assert wire.requests[0][1]["Host"] == "feeds.example.org"


# R30 connect reason: one fixed reason, the detail in the log
CONNECT_FAILURES = {
    "refused": ConnectionRefusedError(61, "Connection refused"),
    "timed out": TimeoutError("timed out"),
    "handshake timeout": ssl.SSLError("The handshake operation timed out"),
    "certificate": ssl.SSLCertVerificationError("certificate verify failed: hostname mismatch"),
    "unreachable": OSError(65, "No route to host"),
}


@pytest.mark.parametrize("error", CONNECT_FAILURES.values(), ids=CONNECT_FAILURES)
def test_a_connector_that_fails_gives_the_fixed_reason_and_logs_the_detail(
    error: OSError, caplog: pytest.LogCaptureFixture
) -> None:
    def connect(target: ConnectionTarget) -> Any:
        raise error

    with caplog.at_level(logging.WARNING, logger=LOGGER), pytest.raises(FetchRefused) as refused:
        fetch(URL, None, None, resolve=PUBLIC, wiring=Wiring(connect))
    assert str(refused.value) == CONNECT_REASON
    (record,) = caplog.records
    assert record.name == LOGGER and record.levelno == logging.WARNING
    message = record.getMessage()
    assert "feeds.example.org" in message and str(error.args[-1]) in message


@pytest.mark.parametrize("error", CONNECT_FAILURES.values(), ids=CONNECT_FAILURES)
def test_a_request_that_cannot_connect_gives_the_fixed_reason_and_closes(
    error: OSError, caplog: pytest.LogCaptureFixture
) -> None:
    class Unreachable(Wire):
        def request(self, method: str, url: str, *, headers: Any) -> None:
            raise error

    wire = Unreachable()
    with caplog.at_level(logging.WARNING, logger=LOGGER), pytest.raises(FetchRefused) as refused:
        run(wire)
    assert str(refused.value) == CONNECT_REASON
    assert wire.closed == 1
    assert len(caplog.records) == 1 and str(error.args[-1]) in caplog.records[0].getMessage()


def test_a_real_refused_connection_gives_the_fixed_reason(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        closed_port = probe.getsockname()[1]
    through_loopback(monkeypatch, closed_port)
    with caplog.at_level(logging.WARNING, logger=LOGGER), pytest.raises(FetchRefused) as refused:
        fetch_from_peer()
    assert str(refused.value) == CONNECT_REASON
    (record,) = caplog.records
    assert "ConnectionRefusedError" in record.getMessage()


def test_a_failure_after_the_connection_is_not_a_connect_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with (
        caplog.at_level(logging.WARNING, logger=LOGGER),
        pytest.raises(FetchRefused, match="fetch failed: socket broke"),
    ):
        run(Wire(OSError("socket broke")))
    assert not caplog.records


# R30 lookup bound: a daemon worker joined for the time left (fetch) or LOOKUP_SECONDS
class Hanging:
    """A resolver that does not answer until released, then answers; notes how it ended."""

    def __init__(self) -> None:
        self.release = threading.Event()
        self.finished = threading.Event()
        self.daemon: list[bool] = []
        self.threads: list[str] = []

    def __call__(self, host: str) -> Iterable[str]:
        self.daemon.append(threading.current_thread().daemon)
        self.threads.append(threading.current_thread().name)
        self.release.wait(10)
        self.finished.set()
        return [PUBLIC_IP]


def test_the_default_lookup_bound_is_five_seconds() -> None:
    assert LOOKUP_SECONDS == 5.0


def test_a_lookup_that_overruns_the_deadline_is_refused_and_its_late_answer_discarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fetch_module, "TOTAL_SECONDS", 0.3)
    hanging = Hanging()
    wire = Wire(ok())
    started = time.monotonic()
    with pytest.raises(FetchRefused) as refused:
        run(wire, resolve=hanging)
    took = time.monotonic() - started
    assert str(refused.value) == LOOKUP_REASON
    assert 0.2 <= took < 2
    assert hanging.daemon == [True] and hanging.threads[0] != threading.current_thread().name
    hanging.release.set()
    assert hanging.finished.wait(5)
    assert not wire.targets


def test_a_lookup_is_given_the_time_left_and_not_the_whole_deadline() -> None:
    clock = Clock()
    hanging = Hanging()
    first = Reply(302, b"", {"Location": "https://other.example.org/y"})
    wire = Wire(first, ok())
    wire.on_response = lambda: clock.advance(9.7) if not wire.targets[1:] else None

    def resolve(host: str) -> Iterable[str]:
        return [PUBLIC_IP] if host == "feeds.example.org" else hanging(host)

    started = time.monotonic()
    with pytest.raises(FetchRefused) as refused:
        run(wire, resolve=resolve, clock=clock)
    assert str(refused.value) == LOOKUP_REASON
    assert time.monotonic() - started < 3  # 0.3 s were left, not 10
    assert [t.host for t in wire.targets] == ["feeds.example.org"]
    hanging.release.set()


def test_check_address_bounds_the_lookup_by_its_own_constant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fetch_module, "LOOKUP_SECONDS", 0.2)
    hanging = Hanging()
    started = time.monotonic()
    with pytest.raises(FetchRefused) as refused:
        check_address(URL, resolve=hanging)
    assert str(refused.value) == LOOKUP_REASON
    assert 0.1 <= time.monotonic() - started < 2
    assert hanging.daemon == [True]
    hanging.release.set()


def test_the_default_resolver_is_bounded_too(monkeypatch: pytest.MonkeyPatch) -> None:
    release = threading.Event()

    def slow(host: str, port: int, **kwargs: Any) -> list[tuple[Any, ...]]:
        release.wait(10)
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC_IP, port))]

    monkeypatch.setattr(socket, "getaddrinfo", slow)
    monkeypatch.setattr(fetch_module, "LOOKUP_SECONDS", 0.2)
    with pytest.raises(FetchRefused, match=LOOKUP_REASON):
        check_address(URL)
    release.set()


def test_a_lookup_that_answers_in_time_is_used_from_a_worker_thread() -> None:
    seen: list[str] = []

    def resolve(host: str) -> Iterable[str]:
        seen.append(threading.current_thread().name)
        return [PUBLIC_IP]

    wire = Wire(ok())
    run(wire, resolve=resolve)
    check_address(URL, resolve=resolve)
    assert len(seen) == 2 and threading.current_thread().name not in seen
    assert [t.ip for t in wire.targets] == [PUBLIC_IP]


@pytest.mark.parametrize("via", ["fetch", "check_address"])
def test_an_error_in_the_lookup_worker_is_raised_in_the_caller(via: str) -> None:
    def broken(host: str) -> Iterable[str]:
        raise KeyError("a defect in the resolver")

    with pytest.raises(KeyError, match="a defect in the resolver"):
        if via == "fetch":
            run(Wire(ok()), resolve=broken)
        else:
            check_address(URL, resolve=broken)


@pytest.mark.parametrize("via", ["fetch", "check_address"])
def test_a_failed_lookup_keeps_its_reason(via: str) -> None:
    def fail(host: str) -> Iterable[str]:
        raise OSError("name not known")

    with pytest.raises(FetchRefused, match="could not resolve feeds.example.org: name not known"):
        if via == "fetch":
            run(Wire(ok()), resolve=fail)
        else:
            check_address(URL, resolve=fail)


# R30 Transfer-Encoding: absent or exactly chunked
@pytest.mark.parametrize(
    "value",
    ["gzip, chunked", "gzip", "identity", "chunked, chunked", "chunked, gzip", "", "x", "chunk"],
)
def test_a_transfer_encoding_other_than_chunked_is_refused(value: str) -> None:
    reply = Reply(200, b"<rss/>", {"Transfer-Encoding": value})
    with pytest.raises(FetchRefused, match="transfer encoding"):
        run(Wire(reply))
    assert reply.consumed == 0 and reply.closed == 1


@pytest.mark.parametrize("value", ["chunked", "Chunked", "CHUNKED", "cHuNkEd"])
def test_a_transfer_encoding_of_chunked_is_accepted_in_any_case(value: str) -> None:
    assert run(Wire(Reply(200, b"<rss/>", {"Transfer-Encoding": value}))).body == b"<rss/>"


def test_no_transfer_encoding_is_accepted() -> None:
    assert run(Wire(ok())).body == b"<rss/>"


def test_gzip_then_chunked_on_the_real_wire_is_refused_not_returned_raw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def answer(conn: socket.socket) -> None:
        read_request(conn)
        head = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: gzip, chunked\r\nConnection: close\r\n\r\n"
        conn.sendall(head + b"6\r\n<rss/>\r\n0\r\n\r\n")

    with loopback_peer(answer) as port:
        through_loopback(monkeypatch, port)
        with pytest.raises(FetchRefused, match="transfer encoding"):
            fetch_from_peer()


def test_plain_chunked_on_the_real_wire_is_decoded(monkeypatch: pytest.MonkeyPatch) -> None:
    def answer(conn: socket.socket) -> None:
        read_request(conn)
        head = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n"
        conn.sendall(head + b"6\r\n<rss/>\r\n0\r\n\r\n")

    with loopback_peer(answer) as port:
        through_loopback(monkeypatch, port)
        assert fetch_from_peer() == Fetched(b"<rss/>", None, None)


# R30 ValueError: only http.client's calls are covered
def test_a_value_error_from_fetchs_own_code_is_not_hidden(monkeypatch: pytest.MonkeyPatch) -> None:
    def defect(response: object, budget: object) -> bytes:
        raise ValueError("a defect inside fetch")

    monkeypatch.setattr(fetch_module, "_read_body", defect)
    with pytest.raises(ValueError, match="a defect inside fetch") as raised:
        run(Wire(ok()))
    assert not isinstance(raised.value, FetchRefused)


def test_a_value_error_from_reading_the_body_is_a_refusal() -> None:
    def explode() -> None:
        raise ValueError("I/O operation on closed file")

    with pytest.raises(FetchRefused, match="fetch failed: I/O operation on closed file"):
        run(Wire(Reply(200, b"<rss/>", on_read=explode)))


def test_a_value_error_from_sending_the_request_is_a_refusal() -> None:
    class Rejects(Wire):
        def request(self, method: str, url: str, *, headers: Any) -> None:
            raise ValueError("Invalid header value")

    wire = Rejects()
    with pytest.raises(FetchRefused, match="fetch failed: Invalid header value"):
        run(wire)
    assert wire.closed == 1


# Review Lows and Infos
def test_a_deadline_made_fresh_for_a_later_hop_is_caught() -> None:
    clock = Clock()
    wire = Wire(redirect("https://other.example.org/y"), ok())
    wire.on_response = lambda: clock.advance(1)
    run(wire, clock=clock)
    assert [t.deadline for t in wire.targets] == [1010.0, 1010.0]


def test_the_response_is_closed_when_the_check_after_the_headers_refuses() -> None:
    clock = Clock()
    reply = ok()
    wire = Wire(reply)
    wire.on_response = lambda: clock.advance(11)
    with pytest.raises(FetchRefused, match=DEADLINE):
        run(wire, clock=clock)
    assert (reply.closed, wire.closed) == (1, 1)


@pytest.mark.parametrize("status", [304, 404])
def test_a_304_and_a_404_that_arrive_after_the_deadline_are_refused(status: int) -> None:
    clock = Clock()
    wire = Wire(Reply(status))
    wire.on_response = lambda: clock.advance(11)
    with pytest.raises(FetchRefused, match=DEADLINE):
        run(wire, etag='"abc"', clock=clock)


def test_a_redirect_whose_close_spends_the_deadline_is_not_followed_to_a_lookup() -> None:
    clock = Clock()
    resolver = Counting([PUBLIC_IP])
    first = Reply(
        302, b"", {"Location": "https://other.example.org/y"}, on_close=lambda: clock.advance(11)
    )
    wire = Wire(first, ok())
    with pytest.raises(FetchRefused, match=DEADLINE):
        run(wire, resolve=resolver, clock=clock)
    assert resolver.calls == ["feeds.example.org"]
    assert [t.host for t in wire.targets] == ["feeds.example.org"]


@pytest.mark.parametrize("host", ["1.2.3.4.5", "256.1.1.1", "feeds.example.123", "1.2.3.04.7"])
def test_a_host_ending_in_digits_that_is_not_an_address_is_refused_unlooked_up(host: str) -> None:
    resolver = Counting([PUBLIC_IP])
    wire = Wire(ok())
    with pytest.raises(FetchRefused, match="plain host name"):
        run(wire, f"https://{host}/x", resolve=resolver)
    with pytest.raises(FetchRefused, match="plain host name"):
        check_address(f"https://{host}/x", resolve=resolver)
    assert not resolver.calls and not wire.targets


def test_a_host_of_254_characters_is_refused_and_one_of_253_is_not() -> None:
    longest = ".".join(["a" * 63] * 3 + ["b" * 61])
    too_long = ".".join(["a" * 63] * 3 + ["b" * 62])
    assert (len(longest), len(too_long)) == (253, 254)
    check_address(f"https://{longest}/", resolve=PUBLIC)
    resolver = Counting([PUBLIC_IP])
    wire = Wire(ok())
    with pytest.raises(FetchRefused, match="plain host name"):
        run(wire, f"https://{too_long}/", resolve=resolver)
    assert not resolver.calls and not wire.targets


def test_a_pinned_connection_replaced_after_import_is_the_one_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wire = Wire(ok())
    made: list[ConnectionTarget] = []

    def replacement(target: ConnectionTarget) -> Wire:
        made.append(target)
        return wire

    monkeypatch.setattr(netpin, "pinned_connection", replacement)
    assert fetch(URL, None, None, resolve=PUBLIC).body == b"<rss/>"
    assert [(t.host, t.ip, t.port) for t in made] == [("feeds.example.org", PUBLIC_IP, 443)]
