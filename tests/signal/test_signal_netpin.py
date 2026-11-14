"""Public-address checks and the pinned connection of Signal's feed fetcher.

Expected values are written by hand. No test connects to a remote address: sockets are
`socket.socketpair` ends (in-process; loopback at most, as on Windows) and resolution is made to
fail loudly.
"""

import http.client
import io
import ipaddress
import socket
import ssl
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.signal import netpin
from credit_os.signal.netpin import (
    ConnectionLike,
    ConnectionTarget,
    PinnedHTTPSConnection,
    ReceivedTooMuch,
    ResponseLike,
    is_public,
    pinned_connection,
    tls_context,
)

IP = "93.184.216.34"
HOST = "feeds.example.org"
LIMIT = 1000  # received bytes a test connection may take, unless the test is about the limit

NON_PUBLIC = [
    # the predecessor's list (tests/test_signal_fetch.py, NON_PUBLIC)
    "127.0.0.1",
    "10.0.0.5",
    "192.168.1.1",
    "169.254.169.254",
    "::1",
    "fc00::1",
    "0.0.0.0",
    "fec0::1",
    "fec0:0:0:ffff::1",
    "ff02::1",
    "ff05::2",
    "224.0.0.1",
    "64:ff9b::a9fe:a9fe",
    "64:ff9b::7f00:1",
    "::a9fe:a9fe",
    "::7f00:1",
    "64:ff9b::808:808",
    "::ffff:127.0.0.1",
    # added here
    "100.64.0.1",
    "100.127.255.255",
    "172.16.0.1",
    "172.31.255.255",
    "192.0.2.1",
    "198.51.100.1",
    "203.0.113.1",
    "198.18.0.1",
    "240.0.0.1",
    "255.255.255.255",
    "::",
    "fe80::1",
    "fe80::1%en0",
    "2001:db8::1",
    "2001:0:4136:e378:8000:63bf:3fff:fdd2",
    "2002:7f00:1::1",
    "2002:808:808::1",
    "64:ff9b:1::1",
    "64:ff9b:1::808:808",
    "::ffff:10.0.0.1",
    "::ffff:0:0",
    "::ffff:a00:1",
    "ff00::",
    "100::1",
]

PUBLIC = [
    "93.184.216.34",
    "8.8.8.8",
    "1.1.1.1",
    "11.0.0.1",
    "100.128.0.1",
    "172.32.0.1",
    "223.255.255.255",
    "2606:4700:4700::1111",
    "2001:4860:4860::8888",
    "2a00:1450::1",
    "::ffff:8.8.8.8",
    "::ffff:808:808",
]

NOT_AN_ADDRESS = ["", "example.org", "999.1.1.1", "127.1", "1.2.3", "::g", " 8.8.8.8", "8.8.8.8\n"]


@pytest.mark.parametrize("address", NON_PUBLIC)
def test_non_public_addresses_are_not_public(address: str) -> None:
    assert is_public(address) is False


@pytest.mark.parametrize("address", PUBLIC)
def test_public_addresses_are_public(address: str) -> None:
    assert is_public(address) is True


@pytest.mark.parametrize("text", NOT_AN_ADDRESS)
def test_text_that_is_not_an_address_is_not_public(text: str) -> None:
    assert is_public(text) is False


V4_NON_PUBLIC = tuple(
    ipaddress.IPv4Network(text)
    for text in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.0.0.0/24",
        "192.0.2.0/24",
        "192.168.0.0/16",
        "198.18.0.0/15",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "224.0.0.0/4",
        "240.0.0.0/4",
    )
)
# ::ffff:0:0/96 is not listed whole: a mapped public IPv4 is public, a mapped non-public one is not
# (test_a_non_public_ipv4_mapped_into_ipv6_is_not_public).
V6_NON_PUBLIC = tuple(
    ipaddress.IPv6Network(text)
    for text in (
        "::/128",
        "::1/128",
        "::/96",
        "64:ff9b::/96",
        "64:ff9b:1::/48",
        "100::/64",
        "2001::/32",
        "2001:db8::/32",
        "2002::/16",
        "3fff::/20",
        "fc00::/7",
        "fe80::/10",
        "fec0::/10",
        "ff00::/8",
    )
)
# 192.0.0.9 and 192.0.0.10 (IANA: globally reachable anycast) are inside 192.0.0.0/24 and are
# public to `ipaddress`; they are not drawn here.
_GLOBALLY_REACHABLE = {ipaddress.IPv4Address("192.0.0.9"), ipaddress.IPv4Address("192.0.0.10")}


def _inside(network: ipaddress.IPv4Network | ipaddress.IPv6Network) -> st.SearchStrategy[int]:
    return st.integers(int(network.network_address), int(network.broadcast_address))


@st.composite
def non_public_v4(draw: st.DrawFn) -> ipaddress.IPv4Address:
    network = draw(st.sampled_from(V4_NON_PUBLIC))
    address = ipaddress.IPv4Address(draw(_inside(network)))
    if address in _GLOBALLY_REACHABLE:
        return ipaddress.IPv4Address("192.0.0.8")
    return address


@given(non_public_v4())
def test_no_non_public_ipv4_range_is_public(address: ipaddress.IPv4Address) -> None:
    assert is_public(str(address)) is False


@pytest.mark.parametrize("network", V6_NON_PUBLIC, ids=str)
@settings(max_examples=100)
@given(data=st.data())
def test_no_address_in_a_non_public_ipv6_network_is_public(
    network: ipaddress.IPv6Network, data: st.DataObject
) -> None:
    address = ipaddress.IPv6Address(data.draw(_inside(network)))
    assert is_public(str(address)) is False


@given(non_public_v4())
def test_a_non_public_ipv4_mapped_into_ipv6_is_not_public(address: ipaddress.IPv4Address) -> None:
    assert is_public(f"::ffff:{address}") is False
    assert is_public(str(ipaddress.IPv6Address((0xFFFF << 32) | int(address)))) is False


@pytest.mark.parametrize(
    "value", [b"\x08\x08\x08\x08", 134744072, None, ipaddress.ip_address("8.8.8.8"), ["8.8.8.8"]]
)
def test_a_value_that_is_not_text_is_not_public(value: object) -> None:
    assert is_public(value) is False


class _LyingStr(str):
    """Text that is a loopback address but whose ``str()`` says a public one."""

    def __str__(self) -> str:
        return "8.8.8.8"


def test_a_str_subclass_is_not_public() -> None:
    assert is_public(_LyingStr("127.0.0.1")) is False
    assert is_public(_LyingStr("8.8.8.8")) is False


@pytest.mark.parametrize(
    "address", ["2001:4860:4860::8888%lo0", "2001:4860:4860::8888%1", "2001:4860:4860::8888%"]
)
def test_an_address_with_a_zone_id_is_not_public(address: str) -> None:
    assert is_public(address) is False


@pytest.mark.parametrize("address", ["192.0.0.9", "192.0.0.10", "::ffff:192.0.0.9"])
def test_the_two_globally_reachable_addresses_of_192_0_0_0_24_are_public(address: str) -> None:
    assert is_public(address) is True


@pytest.mark.parametrize(
    "address",
    ["192.0.0.0", "192.0.0.8", "192.0.0.11", "192.0.0.100", "192.0.0.255", "::ffff:192.0.0.8"],
)
def test_the_rest_of_192_0_0_0_24_is_not_public(address: str) -> None:
    assert is_public(address) is False


ISATAP_NON_PUBLIC = [
    "2001:4860:1:2:0:5efe:7f00:1",
    "2001:4860:1:2:200:5efe:a00:1",
    "2001:4860:1:2:0:5efe:a9fe:a9fe",
    "2001:4860:1:2:200:5efe:c0a8:101",
    "2606:4700::0:5efe:c000:8",
]


@pytest.mark.parametrize("address", ISATAP_NON_PUBLIC)
def test_an_isatap_address_embedding_a_non_public_ipv4_is_not_public(address: str) -> None:
    assert is_public(address) is False


@pytest.mark.parametrize(
    "address", ["2001:4860:1:2:0:5efe:808:808", "2001:4860:1:2:200:5efe:101:101"]
)
def test_an_isatap_address_embedding_a_public_ipv4_is_public(address: str) -> None:
    assert is_public(address) is True


@pytest.mark.parametrize(
    "address", ["2001:4860:1:2:100:5efe:7f00:1", "2001:4860:1:2:0:5eff:7f00:1"]
)
def test_only_the_two_isatap_identifiers_are_read_as_isatap(address: str) -> None:
    assert is_public(address) is True


@pytest.fixture
def tables_call_everything_global(monkeypatch: pytest.MonkeyPatch) -> None:
    """An interpreter's ipaddress tables that call every address global, none reserved, multicast or
    site-local."""
    for cls in (ipaddress.IPv4Address, ipaddress.IPv6Address):
        monkeypatch.setattr(cls, "is_global", property(lambda self: True))
        monkeypatch.setattr(cls, "is_reserved", property(lambda self: False))
        monkeypatch.setattr(cls, "is_multicast", property(lambda self: False))
    monkeypatch.setattr(ipaddress.IPv6Address, "is_site_local", property(lambda self: False))


@pytest.mark.parametrize(
    "address",
    [
        "2002:7f00:1::1",
        "2002:a9fe:a9fe::1",
        "192.0.0.8",
        "192.0.0.255",
        "::ffff:192.0.0.8",
        "192.0.0.11",
        "::ffff:192.0.0.11",
        "2606:4700::0:5efe:c000:8",
        "3fff::1",
        "3fff:fff:ffff:ffff:ffff:ffff:ffff:ffff",
    ],
)
def test_the_explicit_ranges_refuse_whatever_the_interpreters_tables_say(
    tables_call_everything_global: None, address: str
) -> None:
    assert is_public(address) is False


@pytest.mark.parametrize(
    "address",
    [
        "192.0.0.9",
        "192.0.0.10",
        "::ffff:192.0.0.10",
        "192.0.1.0",
        "191.255.255.255",
        "8.8.8.8",
        "2003::1",
        "3fff:1000::1",
    ],
)
def test_the_explicit_ranges_still_pass_the_public_addresses(
    tables_call_everything_global: None, address: str
) -> None:
    assert is_public(address) is True


# tls_context


def test_tls_context_verifies_the_certificate_and_the_host_name() -> None:
    context = tls_context()
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert context.minimum_version >= ssl.TLSVersion.TLSv1_2


def test_tls_context_applies_strict_x509_profile_checks() -> None:
    assert tls_context().verify_flags & ssl.VERIFY_X509_STRICT


def test_tls_context_is_new_each_call() -> None:
    assert tls_context() is not tls_context()


# a pair of connected in-process sockets stands in for the network


class Clock:
    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


class InterruptedClock(Clock):
    """A clock that raises ``error`` on its ``nth`` read."""

    def __init__(self, nth: int, error: BaseException) -> None:
        super().__init__()
        self.reads = 0
        self.nth = nth
        self.error = error

    def __call__(self) -> float:
        self.reads += 1
        if self.reads == self.nth:
            raise self.error
        return self.now


@dataclass
class Wire:
    client: socket.socket
    peer: socket.socket
    connects: list[tuple[tuple[str, int], float]] = field(default_factory=list)
    hostnames: list[str | None] = field(default_factory=list)
    handshake_timeouts: list[float | None] = field(default_factory=list)
    wrap_error: BaseException | None = None
    clock: Clock | None = None
    connect_takes: float = 0.0
    wrapped: list[socket.socket] = field(default_factory=list)

    def create_connection(self, address: tuple[str, int], timeout: float) -> socket.socket:
        self.connects.append((address, timeout))
        self.client.settimeout(timeout)  # as socket.create_connection leaves the socket
        if self.clock is not None:
            self.clock.now += self.connect_takes
        return self.client

    def wrap_socket(self, sock: socket.socket, *, server_hostname: str | None = None) -> Any:
        self.hostnames.append(server_hostname)
        self.handshake_timeouts.append(sock.gettimeout())
        if self.wrap_error is not None:
            raise self.wrap_error
        # a real wrap_socket detaches the socket it is given and returns another object
        tls = socket.socket(fileno=sock.detach())
        self.wrapped.append(tls)
        return tls

    def context(self, monkeypatch: pytest.MonkeyPatch) -> ssl.SSLContext:
        context = tls_context()
        monkeypatch.setattr(context, "wrap_socket", self.wrap_socket)
        return context


def _refuse_lookup(*args: object, **kwargs: object) -> None:
    raise AssertionError("a second lookup was made")


@pytest.fixture
def wire(monkeypatch: pytest.MonkeyPatch) -> Iterator[Wire]:
    client, peer = socket.socketpair()
    carried = Wire(client, peer)
    monkeypatch.setattr(socket, "create_connection", carried.create_connection)
    for name in ("getaddrinfo", "gethostbyname", "gethostbyname_ex"):
        monkeypatch.setattr(socket, name, _refuse_lookup)
    yield carried
    for tls in carried.wrapped:
        tls.close()
    client.close()
    peer.close()


def _connection(
    wire: Wire,
    monkeypatch: pytest.MonkeyPatch,
    clock: Clock,
    *,
    port: int = 443,
    timeout: float = 10.0,
    deadline: float = 100.0,
    max_received: int = LIMIT,
) -> PinnedHTTPSConnection:
    return PinnedHTTPSConnection(
        HOST,
        IP,
        port=port,
        timeout=timeout,
        context=wire.context(monkeypatch),
        deadline=deadline,
        clock=clock,
        max_received=max_received,
    )


# the pinned connection


def test_connect_goes_to_the_checked_address_and_never_looks_the_host_up(
    wire: Wire, monkeypatch: pytest.MonkeyPatch
) -> None:
    _connection(wire, monkeypatch, Clock(), port=8443).connect()
    assert wire.connects == [((IP, 8443), 10.0)]


def test_the_certificate_is_checked_for_the_host_name_not_the_address(
    wire: Wire, monkeypatch: pytest.MonkeyPatch
) -> None:
    _connection(wire, monkeypatch, Clock()).connect()
    assert wire.hostnames == [HOST]


def test_connect_timeout_is_what_is_left_when_that_is_less(
    wire: Wire, monkeypatch: pytest.MonkeyPatch
) -> None:
    _connection(wire, monkeypatch, Clock(95.0)).connect()
    assert wire.connects == [((IP, 443), 5.0)]


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.0.0.1", "::1", "localhost", "", "2002:7f00:1::1"])
def test_connect_refuses_an_address_that_is_not_public_before_any_socket(
    wire: Wire, monkeypatch: pytest.MonkeyPatch, ip: str
) -> None:
    connection = PinnedHTTPSConnection(
        HOST,
        ip,
        port=443,
        timeout=10.0,
        context=wire.context(monkeypatch),
        deadline=100.0,
        clock=Clock(),
        max_received=LIMIT,
    )
    with pytest.raises(ValueError, match="not a public address"):
        connection.connect()
    assert wire.connects == []
    assert wire.hostnames == []
    assert wire.client.fileno() != -1


@pytest.mark.parametrize("now", [100.0, 100.5, 1000.0])
def test_connect_with_the_total_time_spent_makes_no_connection(
    wire: Wire, monkeypatch: pytest.MonkeyPatch, now: float
) -> None:
    with pytest.raises(TimeoutError, match="total time"):
        _connection(wire, monkeypatch, Clock(now)).connect()
    assert wire.connects == []
    assert wire.hostnames == []


def test_the_handshake_is_bounded_by_what_is_left_after_the_connect(
    wire: Wire, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = Clock(90.0)
    wire.clock, wire.connect_takes = clock, 6.0
    _connection(wire, monkeypatch, clock).connect()
    assert wire.connects == [((IP, 443), 10.0)]
    assert wire.handshake_timeouts == [4.0]


def test_the_handshake_keeps_the_per_operation_timeout_when_that_is_less(
    wire: Wire, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = Clock(0.0)
    wire.clock, wire.connect_takes = clock, 1.0
    _connection(wire, monkeypatch, clock).connect()
    assert wire.handshake_timeouts == [10.0]


@pytest.mark.parametrize("taken", [10.0, 12.5])
def test_a_connect_that_spends_the_total_time_closes_the_socket_and_raises(
    wire: Wire, monkeypatch: pytest.MonkeyPatch, taken: float
) -> None:
    clock = Clock(90.0)
    wire.clock, wire.connect_takes = clock, taken
    with pytest.raises(TimeoutError, match="total time"):
        _connection(wire, monkeypatch, clock).connect()
    assert wire.hostnames == []
    assert wire.client.fileno() == -1


@pytest.mark.parametrize(
    "error", [ValueError("bad host"), UnicodeError("label too long"), ssl.SSLError("refused")]
)
def test_a_handshake_that_raises_anything_closes_the_socket_and_raises_it(
    wire: Wire, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    wire.wrap_error = error
    with pytest.raises(type(error)) as raised:
        _connection(wire, monkeypatch, Clock()).connect()
    assert raised.value is error
    assert wire.client.fileno() == -1


def test_an_interrupt_from_the_clock_read_after_the_connect_closes_the_socket(
    wire: Wire, monkeypatch: pytest.MonkeyPatch
) -> None:
    interrupt = KeyboardInterrupt()
    # read 1 is the check before the connect, read 2 the one after it
    with pytest.raises(KeyboardInterrupt) as raised:
        _connection(wire, monkeypatch, InterruptedClock(2, interrupt)).connect()
    assert raised.value is interrupt
    assert wire.client.fileno() == -1


def test_an_interrupt_from_the_handshake_closes_the_socket_and_propagates_unchanged(
    wire: Wire, monkeypatch: pytest.MonkeyPatch
) -> None:
    interrupt = KeyboardInterrupt()
    wire.wrap_error = interrupt
    with pytest.raises(KeyboardInterrupt) as raised:
        _connection(wire, monkeypatch, Clock()).connect()
    assert raised.value is interrupt
    assert wire.client.fileno() == -1


def test_connect_leaves_a_budgeted_socket(wire: Wire, monkeypatch: pytest.MonkeyPatch) -> None:
    connection = _connection(wire, monkeypatch, Clock())
    connection.connect()
    assert isinstance(connection.sock, netpin._BudgetedSocket)


def test_the_request_goes_over_the_socket_the_handshake_returned(
    wire: Wire, monkeypatch: pytest.MonkeyPatch
) -> None:
    connection = _connection(wire, monkeypatch, Clock())
    connection.request("GET", "/", headers={"Host": HOST})
    assert len(wire.wrapped) == 1
    assert wire.wrapped[0] is not wire.client
    assert wire.client.fileno() == -1  # detached, as by a real wrap_socket
    assert wire.peer.recv(4096) == b"GET / HTTP/1.1\r\nHost: feeds.example.org\r\n\r\n"


def test_the_connections_operations_carry_the_per_operation_timeout(
    wire: Wire, monkeypatch: pytest.MonkeyPatch
) -> None:
    connection = _connection(wire, monkeypatch, Clock(), timeout=3.0)
    connection.request("GET", "/", headers={"Host": HOST})
    assert wire.wrapped[0].gettimeout() == 3.0


def test_the_connections_operations_carry_the_time_left_when_that_is_less_than_the_timeout(
    wire: Wire, monkeypatch: pytest.MonkeyPatch
) -> None:
    connection = _connection(wire, monkeypatch, Clock(98.0), timeout=3.0)
    connection.request("GET", "/", headers={"Host": HOST})
    assert wire.wrapped[0].gettimeout() == 2.0


def test_an_answer_read_after_the_total_time_is_spent_is_refused(
    wire: Wire, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = Clock()
    connection = _connection(wire, monkeypatch, clock)
    connection.request("GET", "/", headers={"Host": HOST})
    wire.peer.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 4\r\n\r\nlate")
    clock.now = 100.0  # the deadline
    with pytest.raises(TimeoutError, match="total time"):
        connection.getresponse()


def test_a_request_sends_exactly_the_given_headers_and_the_answer_is_read(
    wire: Wire, monkeypatch: pytest.MonkeyPatch
) -> None:
    wire.peer.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nLast-Modified: x\r\n\r\nok")
    connection = _connection(wire, monkeypatch, Clock())
    connection.request("GET", "/a?b=1", headers={"Host": HOST, "Accept": "text/plain"})
    assert (
        wire.peer.recv(4096)
        == b"GET /a?b=1 HTTP/1.1\r\nHost: feeds.example.org\r\nAccept: text/plain\r\n\r\n"
    )
    response: ResponseLike = connection.getresponse()
    assert response.status == 200
    assert response.getheader("Content-Length") == "2"
    assert response.getheader("Missing") is None
    assert response.read(10) == b"ok"
    connection.close()


def test_a_request_without_a_host_header_names_the_host_and_adds_no_accept_encoding(
    wire: Wire, monkeypatch: pytest.MonkeyPatch
) -> None:
    _connection(wire, monkeypatch, Clock(), port=8443).request("GET", "/", headers=None)
    assert wire.peer.recv(4096) == b"GET / HTTP/1.1\r\nHost: feeds.example.org:8443\r\n\r\n"


def test_a_host_header_in_any_case_replaces_the_default_host_line(
    wire: Wire, monkeypatch: pytest.MonkeyPatch
) -> None:
    _connection(wire, monkeypatch, Clock()).request("GET", "/", headers={"hOsT": "other"})
    assert wire.peer.recv(4096) == b"GET / HTTP/1.1\r\nhOsT: other\r\n\r\n"


@pytest.mark.parametrize(("body", "chunked"), [(b"x", False), ("", False), (None, True)])
def test_a_request_never_sends_a_body(
    wire: Wire, monkeypatch: pytest.MonkeyPatch, body: object, chunked: bool
) -> None:
    connection = _connection(wire, monkeypatch, Clock())
    with pytest.raises(ValueError, match="never sends a body"):
        connection.request("POST", "/", body=body, encode_chunked=chunked)
    assert wire.connects == []


def test_a_response_that_is_not_http_is_refused_by_the_standard_library(
    wire: Wire, monkeypatch: pytest.MonkeyPatch
) -> None:
    wire.peer.sendall(b"garbage\r\n\r\n")
    connection = _connection(wire, monkeypatch, Clock())
    connection.request("GET", "/", headers={})
    with pytest.raises(http.client.BadStatusLine):
        connection.getresponse()


# pinned_connection


def _target(clock: Callable[[], float], deadline: float = 100.0) -> ConnectionTarget:
    return ConnectionTarget(HOST, IP, 443, 10.0, deadline, clock, 4096)


def test_the_production_connector_is_pinned_to_the_checked_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built: list[dict[str, Any]] = []
    clock = Clock()

    class Capture:
        def __init__(self, host: str, ip: str, **kwargs: Any) -> None:
            built.append({"host": host, "ip": ip, **kwargs})

    monkeypatch.setattr(netpin, "PinnedHTTPSConnection", Capture)
    monkeypatch.setattr(netpin, "tls_context", lambda: "context")
    pinned_connection(_target(clock, 55.0))
    assert built == [
        {
            "host": HOST,
            "ip": IP,
            "port": 443,
            "timeout": 10.0,
            "context": "context",
            "deadline": 55.0,
            "clock": clock,
            "max_received": 4096,
        }
    ]


def test_the_connector_makes_a_connection_that_connects_to_the_target_address(
    wire: Wire, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(netpin, "tls_context", lambda: wire.context(monkeypatch))
    connection: ConnectionLike = pinned_connection(_target(Clock()))
    assert isinstance(connection, PinnedHTTPSConnection)
    assert (connection.host, connection.port, connection.timeout) == (HOST, 443, 10.0)
    connection.request("GET", "/", headers={"Host": HOST})
    assert wire.connects == [((IP, 443), 10.0)]
    connection.close()


# the deadline-bounded socket


def _budgeted(
    wire: Wire,
    clock: Clock,
    *,
    timeout: float = 5.0,
    deadline: float = 100.0,
    max_received: int = LIMIT,
) -> netpin._BudgetedSocket:
    return netpin._BudgetedSocket(wire.client, timeout, deadline, clock, max_received)


def test_every_send_and_receive_is_bounded_by_the_per_operation_timeout(wire: Wire) -> None:
    budget = _budgeted(wire, Clock(0.0))
    budget.sendall(b"abc")
    assert wire.client.gettimeout() == 5.0
    assert wire.peer.recv(3) == b"abc"
    wire.peer.sendall(b"hello!")
    wire.client.settimeout(None)
    buffer = bytearray(1)
    assert budget.recv_into(buffer, 1) == 1
    assert bytes(buffer) == b"h"
    assert wire.client.gettimeout() == 5.0


def test_the_time_left_bounds_an_operation_when_it_is_less(wire: Wire) -> None:
    budget = _budgeted(wire, Clock(98.0))
    budget.sendall(b"x")
    assert wire.client.gettimeout() == 2.0


@pytest.mark.parametrize("now", [100.0, 101.0])
def test_with_the_total_time_spent_no_operation_touches_the_socket(wire: Wire, now: float) -> None:
    budget = _budgeted(wire, Clock(now))
    buffer = bytearray(1)
    operations: list[Callable[[], object]] = [
        lambda: budget.recv_into(buffer, 1),
        lambda: budget.sendall(b"x"),
    ]
    for operation in operations:
        with pytest.raises(TimeoutError, match="total time"):
            operation()
    wire.peer.setblocking(False)
    with pytest.raises(BlockingIOError):
        wire.peer.recv(1)


def test_a_silent_peer_times_out_after_the_per_operation_timeout(wire: Wire) -> None:
    budget = _budgeted(wire, Clock(0.0), timeout=0.05)
    with pytest.raises(TimeoutError):
        budget.recv_into(bytearray(1), 1)


def test_makefile_reads_binary_only(wire: Wire) -> None:
    budget = _budgeted(wire, Clock(0.0))
    with pytest.raises(ValueError, match="only binary reads"):
        budget.makefile("r")
    wire.peer.sendall(b"line\n")
    reader = budget.makefile("rb")
    assert isinstance(reader, io.BufferedReader)
    assert reader.readline() == b"line\n"


def test_close_without_a_file_closes_the_socket(wire: Wire) -> None:
    _budgeted(wire, Clock()).close()
    assert wire.client.fileno() == -1


def test_the_socket_stays_open_until_the_last_file_made_by_makefile_closes(wire: Wire) -> None:
    budget = _budgeted(wire, Clock())
    first = budget.makefile("rb")
    second = budget.makefile("rb")
    budget.close()
    assert wire.client.fileno() != -1
    first.close()
    assert wire.client.fileno() != -1
    second.close()
    assert wire.client.fileno() == -1


def test_a_file_closed_before_the_socket_leaves_the_socket_open(wire: Wire) -> None:
    budget = _budgeted(wire, Clock())
    budget.makefile("rb").close()
    assert wire.client.fileno() != -1
    budget.close()
    assert wire.client.fileno() == -1


# the received-bytes limit: counted as the bytes http.client sees, after TLS


def test_a_socket_takes_exactly_its_limit_and_then_the_end_of_the_stream(wire: Wire) -> None:
    reader = _budgeted(wire, Clock(), max_received=5).makefile("rb")
    wire.peer.sendall(b"abcde")
    wire.peer.shutdown(socket.SHUT_WR)
    assert reader.read(10) == b"abcde"


def test_a_socket_refuses_the_byte_after_its_limit(wire: Wire) -> None:
    reader = _budgeted(wire, Clock(), max_received=5).makefile("rb")
    wire.peer.sendall(b"abcdef")
    with pytest.raises(ReceivedTooMuch, match="more than 5 bytes"):
        reader.read(10)


def test_the_count_is_over_every_receive_not_per_call(wire: Wire) -> None:
    budget = _budgeted(wire, Clock(), max_received=5)
    buffer = bytearray(10)
    wire.peer.sendall(b"abc")
    assert budget.recv_into(buffer, 10) == 3
    wire.peer.sendall(b"def")
    with pytest.raises(ReceivedTooMuch):
        budget.recv_into(buffer, 10)


def test_a_socket_reads_no_more_than_one_byte_past_its_limit(wire: Wire) -> None:
    budget = _budgeted(wire, Clock(), max_received=5)
    wire.peer.sendall(b"0123456789")
    with pytest.raises(ReceivedTooMuch):
        budget.recv_into(bytearray(10), 10)
    wire.client.settimeout(2.0)
    assert wire.client.recv(100) == b"6789"  # 6 of the 10 were taken: the limit and one more


def test_a_refused_socket_refuses_every_later_read_and_never_reports_an_end(wire: Wire) -> None:
    budget = _budgeted(wire, Clock(), max_received=2)
    wire.peer.sendall(b"abcd")
    for _ in range(3):
        with pytest.raises(ReceivedTooMuch):
            budget.recv_into(bytearray(4), 4)


def test_a_limit_of_zero_takes_the_first_byte_as_too_much(wire: Wire) -> None:
    budget = _budgeted(wire, Clock(), max_received=0)
    wire.peer.sendall(b"a")
    with pytest.raises(ReceivedTooMuch):
        budget.recv_into(bytearray(4), 4)


def test_received_too_much_is_an_os_error_with_fixed_text() -> None:
    assert issubclass(ReceivedTooMuch, OSError)
    assert str(ReceivedTooMuch(7)) == "the server sent more than 7 bytes"


def test_a_connection_takes_an_answer_of_exactly_its_limit(
    wire: Wire, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 17 + 20 + 2 bytes of status line and headers, then 50 of body: 89 in all
    answer = b"HTTP/1.1 200 OK\r\nContent-Length: 50\r\n\r\n" + b"x" * 50
    assert len(answer) == 89
    wire.peer.sendall(answer)
    connection = _connection(wire, monkeypatch, Clock(), max_received=89)
    connection.request("GET", "/", headers={"Host": HOST})
    assert connection.getresponse().read(50) == b"x" * 50


def test_a_connection_refuses_an_answer_one_byte_over_its_limit(
    wire: Wire, monkeypatch: pytest.MonkeyPatch
) -> None:
    wire.peer.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 50\r\n\r\n" + b"x" * 50)
    connection = _connection(wire, monkeypatch, Clock(), max_received=88)
    connection.request("GET", "/", headers={"Host": HOST})
    with pytest.raises(ReceivedTooMuch):
        connection.getresponse().read(50)
