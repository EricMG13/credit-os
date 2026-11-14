"""Public-address checks and the pinned connection of Signal's feed fetcher.

Expected values are written by hand. No test opens a network connection: sockets are
`socket.socketpair` ends (in-process, no address) and resolution is made to fail loudly.
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
from hypothesis import given
from hypothesis import strategies as st

from credit_os.signal import netpin
from credit_os.signal.netpin import (
    ConnectionLike,
    ConnectionTarget,
    PinnedHTTPSConnection,
    ResponseLike,
    is_public,
    pinned_connection,
    tls_context,
)

IP = "93.184.216.34"
HOST = "feeds.example.org"

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


@st.composite
def non_public_v6(draw: st.DrawFn) -> ipaddress.IPv6Address:
    return ipaddress.IPv6Address(draw(_inside(draw(st.sampled_from(V6_NON_PUBLIC)))))


ANY_V4 = st.integers(0, 2**32 - 1)


@given(non_public_v4())
def test_no_non_public_ipv4_range_is_public(address: ipaddress.IPv4Address) -> None:
    assert is_public(str(address)) is False


@given(non_public_v6())
def test_no_non_public_ipv6_range_is_public(address: ipaddress.IPv6Address) -> None:
    assert is_public(str(address)) is False


@given(non_public_v4())
def test_a_non_public_ipv4_mapped_into_ipv6_is_not_public(address: ipaddress.IPv4Address) -> None:
    assert is_public(f"::ffff:{address}") is False
    assert is_public(str(ipaddress.IPv6Address((0xFFFF << 32) | int(address)))) is False


@given(ANY_V4)
def test_ipv4_compatible_form_is_not_public(value: int) -> None:
    assert is_public(str(ipaddress.IPv6Address(value))) is False


@given(ANY_V4)
def test_nat64_well_known_prefix_is_not_public(value: int) -> None:
    assert is_public(str(ipaddress.IPv6Address((0x64 << 112) | (0xFF9B << 96) | value))) is False


@given(st.integers(0, 2**80 - 1))
def test_nat64_local_use_prefix_is_not_public(tail: int) -> None:
    assert (
        is_public(str(ipaddress.IPv6Address((0x64 << 112) | (0xFF9B << 96) | (1 << 80) | tail)))
        is False
    )


@given(ANY_V4, st.integers(0, 2**80 - 1))
def test_6to4_is_not_public(value: int, tail: int) -> None:
    packed = (0x2002 << 112) | (value << 80) | tail
    assert is_public(str(ipaddress.IPv6Address(packed))) is False


@given(st.integers(0, 2**96 - 1))
def test_teredo_is_not_public(tail: int) -> None:
    assert is_public(str(ipaddress.IPv6Address((0x2001 << 112) | tail))) is False


@given(st.sampled_from(PUBLIC[:3]))
def test_the_checks_do_not_refuse_everything(address: str) -> None:
    assert is_public(address) is True


# tls_context


def test_tls_context_verifies_the_certificate_and_the_host_name() -> None:
    context = tls_context()
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert context.minimum_version >= ssl.TLSVersion.TLSv1_2


def test_tls_context_is_new_each_call() -> None:
    assert tls_context() is not tls_context()


# a pair of connected in-process sockets stands in for the network


class Clock:
    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


@dataclass
class Wire:
    client: socket.socket
    peer: socket.socket
    connects: list[tuple[tuple[str, int], float]] = field(default_factory=list)
    hostnames: list[str | None] = field(default_factory=list)
    wrap_error: OSError | None = None

    def create_connection(self, address: tuple[str, int], timeout: float) -> socket.socket:
        self.connects.append((address, timeout))
        return self.client

    def wrap_socket(self, sock: socket.socket, *, server_hostname: str | None = None) -> Any:
        self.hostnames.append(server_hostname)
        if self.wrap_error is not None:
            raise self.wrap_error
        return sock

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
) -> PinnedHTTPSConnection:
    return PinnedHTTPSConnection(
        HOST,
        IP,
        port=port,
        timeout=timeout,
        context=wire.context(monkeypatch),
        deadline=deadline,
        clock=clock,
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


@pytest.mark.parametrize("now", [100.0, 100.5, 1000.0])
def test_connect_with_the_total_time_spent_makes_no_connection(
    wire: Wire, monkeypatch: pytest.MonkeyPatch, now: float
) -> None:
    with pytest.raises(TimeoutError, match="total time"):
        _connection(wire, monkeypatch, Clock(now)).connect()
    assert wire.connects == []
    assert wire.hostnames == []


def test_a_failed_handshake_closes_the_socket_and_raises_it(
    wire: Wire, monkeypatch: pytest.MonkeyPatch
) -> None:
    wire.wrap_error = ssl.SSLError("handshake refused")
    with pytest.raises(ssl.SSLError, match="handshake refused"):
        _connection(wire, monkeypatch, Clock()).connect()
    assert wire.client.fileno() == -1


def test_connect_leaves_a_budgeted_socket(wire: Wire, monkeypatch: pytest.MonkeyPatch) -> None:
    connection = _connection(wire, monkeypatch, Clock())
    connection.connect()
    assert isinstance(connection.sock, netpin._BudgetedSocket)


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
    return ConnectionTarget(HOST, IP, 443, 10.0, deadline, clock)


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
    wire: Wire, clock: Clock, *, timeout: float = 5.0, deadline: float = 100.0
) -> netpin._BudgetedSocket:
    return netpin._BudgetedSocket(wire.client, timeout, deadline, clock)


def test_every_send_and_receive_is_bounded_by_the_per_operation_timeout(wire: Wire) -> None:
    budget = _budgeted(wire, Clock(0.0))
    budget.sendall(b"abc")
    assert wire.client.gettimeout() == 5.0
    assert wire.peer.recv(3) == b"abc"
    wire.client.settimeout(None)
    assert budget.send(b"d") == 1
    assert wire.client.gettimeout() == 5.0
    wire.peer.sendall(b"hello!")
    wire.client.settimeout(None)
    assert budget.recv(5) == b"hello"
    assert wire.client.gettimeout() == 5.0
    wire.client.settimeout(None)
    buffer = bytearray(1)
    assert budget.recv_into(buffer, 1) == 1
    assert bytes(buffer) == b"!"
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
        lambda: budget.recv(1),
        lambda: budget.recv_into(buffer, 1),
        lambda: budget.send(b"x"),
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
        budget.recv(1)


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
