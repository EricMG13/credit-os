"""Public-address checks and a pinned, deadline-bounded https connection for Signal's fetcher.

Carried from the predecessor's ``research/webfetch.py`` (commit aebec97): only what Signal's
feed fetcher uses. A leaf: it imports nothing from ``credit_os`` and reads no settings.

``is_public`` says whether an address may be connected to. ``pinned_connection`` connects to the
address that was checked, never to a second lookup of the host name, and verifies the
certificate for the host name. ``deadline`` (on ``clock``) bounds every socket operation.
"""

import http.client
import io
import ipaddress
import socket
import ssl
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol, cast


@dataclass(frozen=True)
class ConnectionTarget:
    host: str
    ip: str
    port: int
    timeout: float
    deadline: float
    clock: Callable[[], float]


class ResponseLike(Protocol):
    status: int

    def getheader(self, name: str, /) -> str | None: ...

    def read(self, amt: int) -> bytes: ...


class ConnectionLike(Protocol):
    def request(self, method: str, url: str, *, headers: Mapping[str, str]) -> None: ...

    def getresponse(self) -> ResponseLike: ...

    def close(self) -> None: ...


def is_public(addr: str) -> bool:
    """is_global after unwrapping ::ffff:a.b.c.d, and not multicast, reserved or site-local."""
    try:
        address: ipaddress.IPv4Address | ipaddress.IPv6Address = ipaddress.ip_address(addr)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    barred = address.is_multicast or address.is_reserved
    if isinstance(address, ipaddress.IPv6Address):
        barred = barred or address.is_site_local
    return address.is_global and not barred


def tls_context() -> ssl.SSLContext:
    return ssl.create_default_context()


class _BudgetedSocket:
    """A socket whose every receive and send is bounded by the fetch's remaining total time."""

    def __init__(
        self, raw: socket.socket, timeout: float, deadline: float, clock: Callable[[], float]
    ) -> None:
        self._raw = raw
        self._timeout = timeout
        self._deadline = deadline
        self._clock = clock
        self._io_refs = 0
        self._closed = False

    def _arm(self) -> None:
        remaining = self._deadline - self._clock()
        if remaining <= 0:
            raise TimeoutError("the total time for the fetch is spent")
        self._raw.settimeout(min(self._timeout, remaining))

    def recv_into(self, buffer: Any, nbytes: int = 0) -> int:
        self._arm()
        return self._raw.recv_into(buffer, nbytes)

    def recv(self, bufsize: int) -> bytes:
        self._arm()
        return self._raw.recv(bufsize)

    def send(self, data: Any) -> int:
        self._arm()
        return self._raw.send(data)

    def sendall(self, data: Any) -> None:
        self._arm()
        self._raw.sendall(data)

    def makefile(self, mode: str = "rb", buffering: int | None = None) -> io.BufferedReader:
        if mode != "rb":
            raise ValueError("only binary reads are supported")
        self._io_refs += 1
        return io.BufferedReader(socket.SocketIO(cast(socket.socket, self), "rb"))

    def _decref_socketios(self) -> None:
        """A file made by ``makefile`` was closed; the raw socket closes with the last one."""
        if self._io_refs > 0:
            self._io_refs -= 1
        if self._closed and self._io_refs == 0:
            self._raw.close()

    def close(self) -> None:
        """As ``socket.socket.close``: the raw socket stays open while a ``makefile`` file is."""
        self._closed = True
        if self._io_refs <= 0:
            self._raw.close()


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """An https connection to a given address that verifies the certificate for the host name.

    ``deadline`` (on ``clock``) bounds every socket operation.
    """

    def __init__(
        self,
        host: str,
        ip: str,
        *,
        port: int,
        timeout: float,
        context: ssl.SSLContext,
        deadline: float,
        clock: Callable[[], float],
    ) -> None:
        super().__init__(host, port=port, timeout=timeout, context=context)
        self._pinned_ip = ip
        self._tls = context
        self._op_timeout = timeout
        self._deadline = deadline
        self._clock = clock

    def connect(self) -> None:
        remaining = self._deadline - self._clock()
        if remaining <= 0:
            raise TimeoutError("the total time for the fetch is spent")
        sock = socket.create_connection(
            (self._pinned_ip, self.port), min(self._op_timeout, remaining)
        )
        try:
            wrapped = self._tls.wrap_socket(sock, server_hostname=self.host)
        except OSError:
            sock.close()
            raise
        budgeted = _BudgetedSocket(wrapped, self._op_timeout, self._deadline, self._clock)
        self.sock = cast(socket.socket, budgeted)

    def request(
        self,
        method: str,
        url: str,
        body: Any = None,
        headers: Mapping[str, Any] | None = None,
        *,
        encode_chunked: bool = False,
    ) -> None:
        """Send exactly the given headers: no Accept-Encoding is added. Never a body."""
        if body is not None or encode_chunked:
            raise ValueError("a fetch never sends a body")
        given = headers or {}
        self.putrequest(
            method,
            url,
            skip_host=any(name.lower() == "host" for name in given),
            skip_accept_encoding=True,
        )
        for name, value in given.items():
            self.putheader(name, value)
        self.endheaders()


def pinned_connection(target: ConnectionTarget) -> ConnectionLike:
    return PinnedHTTPSConnection(
        target.host,
        target.ip,
        port=target.port,
        timeout=target.timeout,
        context=tls_context(),
        deadline=target.deadline,
        clock=target.clock,
    )
