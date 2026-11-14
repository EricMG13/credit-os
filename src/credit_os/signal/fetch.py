"""Fetch feed bytes from owner-approved addresses; the only place Signal uses the network.

Built on ``netpin``: its public-address rule (``netpin.is_public``, which also refuses the NAT64,
IPv4-compatible, 6to4 and ISATAP forms), its pinned TLS connection and its deadline-bounded
socket. This module adds the address rules for feeds (below), conditional requests, 304 and the
feed ``Accept`` value.

Rules:
- An address is printable ASCII without white space, at most 2048 characters (checked before it
  is parsed); one that is not is refused with a fixed reason that carries none of its text. https
  only; the host must be a plain DNS name (no IP literal, userinfo, percent escape or non-ASCII)
  and the port 443, on the first hop as on every redirect hop. The host is resolved once per hop,
  in a daemon thread that is waited for no longer than the time left on the deadline
  (LOOKUP_SECONDS in ``check_address``); every address it resolves to must be public
  (``netpin.is_public``: an answer that is not exact text is not). On a redirect hop the host is
  the server's text: a refusal says "the redirect's host" and the name goes to the log only.
- The connection goes to the first checked address, with the certificate verified for the host
  name. Nothing looks the name up again, so a host that changes its answer after the check
  cannot change where the request goes.
- Redirects (301, 302, 303, 307, 308) are followed by this module's own loop, at most
  MAX_REDIRECTS in all, never through a proxy. Each target is held to the address rules above and
  is resolved, checked and pinned like the first. A redirect response's body is not read, and
  the conditional headers go to the first address only.
- The response is closed as well as the connection on every path, a refusal mid-body included.
- 10 seconds per socket operation (TIMEOUT_SECONDS); one TOTAL_SECONDS deadline for the whole
  fetch, every hop, headers and body included, spent once the clock reaches it; a 2 MB body cap;
  a body shorter than its declared Content-Length, any Content-Encoding other than identity and
  any Transfer-Encoding other than exactly ``chunked`` (any case, no padding) are refused; so is a
  304 to a request that carried no validator. Each connection may receive at most
  MAX_WIRE_BYTES (4 times the cap: headers and chunk framing), counted after TLS decryption;
  more is refused, which is what bounds a chunk size that ``http.client`` reads as "to the end".
- A failure to connect or to complete the TLS handshake gives the caller one fixed reason; its
  detail goes to the log at warning level.

Known ceiling: the system DNS lookup cannot be interrupted by the standard library. A lookup that
overruns its time is abandoned, not stopped: its daemon thread ends when the resolver gives up,
and its late answer is discarded. At most MAX_LOOKUPS such threads are alive at once, counted
from the start of a lookup to the return of the resolver, however late; with none free the lookup
is refused and no thread is started.
"""

import http.client
import logging
import re
import socket
import threading
import time
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

from credit_os.signal import netpin
from credit_os.signal.netpin import ConnectionLike, ConnectionTarget, ResponseLike

TIMEOUT_SECONDS = 10
TOTAL_SECONDS = 10
MAX_BYTES = 2 * 1024 * 1024
MAX_LOOKUPS = 8  # lookup threads alive at once, abandoned ones included
MAX_WIRE_BYTES = 4 * MAX_BYTES  # received per connection: headers and chunk framing, any feed
MAX_REDIRECTS = 3
LOOKUP_SECONDS = 5.0
USER_AGENT = "Mozilla/5.0 (compatible; signal-feed/1.0)"
ACCEPT = (
    "application/atom+xml, application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5"
)
_DEFAULT_PORT = 443
_CHUNK_BYTES = 64 * 1024
_ERROR_TEXT_LIMIT = 200
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})

_log = logging.getLogger(__name__)
_CONNECT_REASON = "could not connect to the feed's server"
_LOOKUP_SLOTS = threading.BoundedSemaphore(MAX_LOOKUPS)
_WIRE_REASON = f"feed answer is larger than {MAX_WIRE_BYTES // 2**20} MB on the wire"

Resolver = Callable[[str], Iterable[str]]
Connector = Callable[[ConnectionTarget], ConnectionLike]
Clock = Callable[[], float]

_LABEL = r"(?:[a-z0-9]|[a-z0-9][a-z0-9-]{0,61}[a-z0-9])"
_ADDRESS = re.compile(r"[\x21-\x7e]{1,2048}")
_NETLOC = re.compile(rf"({_LABEL}(?:\.{_LABEL})+)(?::[0-9]{{1,5}})?")
_DIGITS = re.compile(r"[0-9]{1,18}")
_VALIDATOR = re.compile(r"[\x20-\x7e]{1,256}")


class FetchRefused(ValueError):
    """A fetch rule was broken; the message names it, in at most 200 characters."""

    def __init__(self, reason: object) -> None:
        super().__init__(_short(reason))


@dataclass(frozen=True)
class Fetched:
    """body is None means the server answered 304 Not Modified."""

    body: bytes | None
    etag: str | None
    modified: str | None


@dataclass(frozen=True)
class _Place:
    host: str
    path: str


@dataclass(frozen=True)
class Wiring:
    """The connector and clock a fetch uses; the defaults are the production values."""

    connect: Connector | None = None  # None: netpin.pinned_connection
    clock: Clock = time.monotonic


@dataclass(frozen=True)
class _Budget:
    """What one fetch uses: the resolver, connector and clock, and its one deadline."""

    resolve: Resolver
    connect: Connector
    clock: Clock
    deadline: float

    def check(self) -> None:
        if self.clock() >= self.deadline:
            raise FetchRefused(f"feed took longer than {TOTAL_SECONDS} seconds")

    def lookup(self, host: str) -> Iterable[str]:
        """The resolver's answer, waited for no longer than the time left on the deadline."""
        return _bounded(self.resolve, host, self.deadline - self.clock())


def _short(error: object) -> str:
    return " ".join(str(error).split())[:_ERROR_TEXT_LIMIT]


def _resolve(host: str) -> Iterable[str]:
    return [str(info[4][0]) for info in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)]


class _Outcome:
    """What a lookup thread ended with: its answer, or the exception that ended it.

    As a context manager it holds any exception raised inside it instead of letting it end the
    thread; ``_bounded`` raises it in the caller, so nothing is hidden.
    """

    def __init__(self) -> None:
        self.answer: list[str] = []
        self.error: BaseException | None = None

    def __enter__(self) -> None:
        return None

    def __exit__(self, kind: object, error: BaseException | None, trace: object) -> bool:
        self.error = error
        return error is not None


def _bounded(resolve: Resolver, host: str, seconds: float) -> list[str]:
    """``resolve(host)`` in a daemon thread, waited for ``seconds``; refused if it overruns.

    An exception in the thread is raised here. A late answer lands in a record nothing reads.
    """
    if not _LOOKUP_SLOTS.acquire(blocking=False):
        raise FetchRefused("too many lookups are still waiting for an answer")
    outcome = _Outcome()

    def work() -> None:
        try:
            with outcome:
                outcome.answer = list(resolve(host))
        finally:
            _LOOKUP_SLOTS.release()  # when the resolver returns, however late

    try:
        worker = threading.Thread(target=work, daemon=True)
        worker.start()
    except Exception as error:  # fail closed, whatever stopped the build or start: nothing ran
        _LOOKUP_SLOTS.release()
        _log.warning("could not start a lookup thread: %r", error)
        raise FetchRefused("could not start a lookup of the feed's host") from error
    worker.join(max(seconds, 0.0))
    if worker.is_alive():
        raise FetchRefused("looking up the feed's host took too long")
    if outcome.error is not None:
        raise outcome.error
    return outcome.answer


def _plain_host(netloc: str) -> str:
    # ASCII only before lower-casing: U+212A (Kelvin sign) would otherwise become "k".
    match = _NETLOC.fullmatch(netloc.lower()) if netloc.isascii() else None
    if match is None or len(match.group(1)) > 253:
        raise FetchRefused("feed address must use a plain host name")
    host = match.group(1)
    try:
        socket.inet_aton(host)
    except OSError:
        numeric = host.rsplit(".", 1)[-1].isdigit()
    else:
        numeric = True
    if numeric:
        raise FetchRefused("feed address must use a plain host name")
    return host


def _locate(url: str) -> _Place:
    """The host and request path of an acceptable https address on port 443."""
    if _ADDRESS.fullmatch(url) is None:  # before urlsplit, which drops some characters unseen
        raise FetchRefused("feed address is not valid")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError as error:
        raise FetchRefused("feed address is not valid") from error
    if parts.scheme != "https":
        raise FetchRefused("only https addresses are fetched")
    if not parts.netloc:
        raise FetchRefused("address has no host")
    host = _plain_host(parts.netloc)
    if port not in (None, _DEFAULT_PORT):
        raise FetchRefused(f"feed address must use port {_DEFAULT_PORT}")
    return _Place(host, (parts.path or "/") + (f"?{parts.query}" if parts.query else ""))


def _host_refused(host: str, redirected: bool, reason: Callable[[str], str]) -> FetchRefused:
    """A refusal about ``host``; a redirect's host is the server's text, so it is only logged."""
    if redirected:
        _log.warning("a redirect's host was refused: %s", reason(host))
        return FetchRefused(reason("the redirect's host"))
    return FetchRefused(reason(host))


def _not_public(address: object) -> Callable[[str], str]:
    return lambda who: f"{who} resolves to {address}, which is not a public address"


def _checked(host: str, resolve: Resolver, redirected: bool = False) -> list[str]:
    """Resolve once; every address must be public. Returns them in order."""
    try:
        addresses = list(resolve(host))
    except OSError as error:
        detail = _short(error)
        raise _host_refused(
            host, redirected, lambda who: f"could not resolve {who}: {detail}"
        ) from error
    if not addresses:
        raise _host_refused(host, redirected, lambda who: f"{who} resolved to no address")
    for address in addresses:
        if not netpin.is_public(address):
            raise _host_refused(host, redirected, _not_public(address))
    return addresses


def check_address(url: str, resolve: Resolver | None = None) -> None:
    """Raise FetchRefused unless url is https, a plain host name, resolving only to public IPs."""
    resolver = _resolve if resolve is None else resolve  # looked up now, so tests can replace it
    _checked(_locate(url).host, lambda host: _bounded(resolver, host, LOOKUP_SECONDS))


def _declared_length(response: ResponseLike) -> int | None:
    """The declared length, None if none that http.client would use; refuses the forms it would."""
    raw = response.getheader("Content-Length")  # repeated headers arrive joined with ", "
    declared = (raw or "").strip()
    if _DIGITS.fullmatch(declared):
        return int(declared)
    if "," in declared:
        raise FetchRefused("the response declared an unusable length")
    try:
        usable = (
            int(declared) >= 0
        )  # "+1000", "1_000", 19 digits: http.client reads these as lengths
    except ValueError:
        return None  # http.client ignores what int() rejects
    if usable:
        raise FetchRefused("the response declared an unusable length")
    return None


@contextmanager
def _http_call() -> Iterator[None]:
    """A call into ``http.client`` or the connection: its ``ValueError`` is a refusal."""
    try:
        yield
    except FetchRefused:
        raise
    except ValueError as error:
        raise FetchRefused(f"fetch failed: {_short(error) or type(error).__name__}") from error


@contextmanager
def _connecting(host: str) -> Iterator[None]:
    """Opening the connection, TLS included: a failure gives one reason; the detail is logged."""
    try:
        yield
    except OSError as error:
        _log.warning("could not connect to %s: %s: %s", host, type(error).__name__, _short(error))
        raise FetchRefused(_CONNECT_REASON) from error


def _read_body(response: ResponseLike, budget: _Budget) -> bytes:
    declared = _declared_length(response)
    if declared is not None and declared > MAX_BYTES:
        raise FetchRefused("feed is larger than 2 MB")
    chunks: list[bytes] = []
    got = 0
    while got <= MAX_BYTES:
        with _http_call():
            chunk = response.read(min(_CHUNK_BYTES, MAX_BYTES + 1 - got))
        budget.check()
        if not chunk:
            break
        chunks.append(chunk)
        got += len(chunk)
    if got > MAX_BYTES:
        raise FetchRefused("feed is larger than 2 MB")
    if declared is not None and got < declared:
        raise FetchRefused(f"the response ended early ({got} of {declared} bytes)")
    return b"".join(chunks)


def _redirect_url(current: str, response: ResponseLike, hops: int) -> str:
    if hops >= MAX_REDIRECTS:
        raise FetchRefused(f"more than {MAX_REDIRECTS} redirects")
    location = response.getheader("Location") or ""
    if not location:
        raise FetchRefused("the redirect has no usable location")
    if _ADDRESS.fullmatch(location) is None:  # as sent: urljoin drops TAB, CR and LF unseen
        raise FetchRefused("feed address is not valid")
    try:
        return urljoin(current, location)
    except ValueError as error:
        raise FetchRefused("the redirect has no usable location") from error


def _validator(response: ResponseLike, name: str) -> str | None:
    value = response.getheader(name)
    return value if value is not None and _VALIDATOR.fullmatch(value) else None


def _refuse_encodings(response: ResponseLike) -> None:
    encoding = (response.getheader("Content-Encoding") or "").strip().lower()
    if encoding not in ("", "identity"):
        raise FetchRefused("feed uses a content encoding")
    transfer = response.getheader("Transfer-Encoding")
    if transfer is not None and transfer.lower() != "chunked":  # as http.client: no strip
        raise FetchRefused("feed uses a transfer encoding")


def _answer(
    response: ResponseLike,
    etag: str | None,
    modified: str | None,
    budget: _Budget,
    *,
    redirected: bool,
) -> Fetched:
    if response.status == 304:
        if redirected:
            raise FetchRefused("a redirect target answered 304, but it was sent no validators")
        if not (etag or modified):  # R34: nothing was sent, so nothing can be "not modified"
            raise FetchRefused("the server answered 304, but it was sent no validators")
        # Decision (controller ruling): a clean validator in the 304 replaces the one sent.
        return Fetched(
            None,
            _validator(response, "ETag") or etag,
            _validator(response, "Last-Modified") or modified,
        )
    if response.status != 200:
        raise FetchRefused(f"server answered HTTP {response.status}")
    _refuse_encodings(response)
    body = _read_body(response, budget)
    if redirected:  # validators belong to the first address only
        return Fetched(body, None, None)
    return Fetched(body, _validator(response, "ETag"), _validator(response, "Last-Modified"))


def _stored(value: str | None) -> str | None:
    return value if value is not None and _VALIDATOR.fullmatch(value) else None


def fetch(
    url: str,
    etag: str | None,
    modified: str | None,
    *,
    resolve: Resolver | None = None,
    wiring: Wiring | None = None,
) -> Fetched:
    """Fetch url conditionally; raise FetchRefused for any broken rule, error or bad status."""
    wiring = wiring or Wiring()
    etag = _stored(etag)  # a stored value is held to what a server may send
    modified = _stored(modified)
    budget = _Budget(
        _resolve if resolve is None else resolve,  # looked up now, so tests can replace it
        netpin.pinned_connection if wiring.connect is None else wiring.connect,
        wiring.clock,
        wiring.clock() + TOTAL_SECONDS,
    )
    try:
        return _follow(url, etag, modified, budget)
    except FetchRefused:
        raise
    except netpin.ReceivedTooMuch as error:  # before OSError: a fixed reason, no byte counts
        raise FetchRefused(_WIRE_REASON) from error
    except http.client.HTTPException as error:  # its text can carry what the server sent
        raise FetchRefused(f"fetch failed: {type(error).__name__}") from error
    except OSError as error:
        raise FetchRefused(f"fetch failed: {_short(error) or type(error).__name__}") from error


def _release(connection: ConnectionLike, response: ResponseLike | None) -> None:
    """Close the response, then the connection even if closing the response fails.

    With ``Connection: close`` the connection hands its socket to the response, so closing the
    connection alone leaves the socket open while the response (or a traceback) is held.
    """
    try:
        if response is not None:
            response.close()
    finally:
        connection.close()


def _follow(url: str, etag: str | None, modified: str | None, budget: _Budget) -> Fetched:
    current = url
    hops = 0
    while True:
        place = _locate(current)
        budget.check()  # no lookup once the time is spent, whatever closing the last hop took
        address = _checked(place.host, budget.lookup, hops > 0)[0]
        budget.check()  # the lookup may have ended after the deadline
        headers = {
            "Host": place.host,
            "User-Agent": USER_AGENT,
            "Accept": ACCEPT,
            "Accept-Encoding": "identity",
            "Connection": "close",
        }
        if hops == 0:  # the validators belong to the first address only
            if etag:
                headers["If-None-Match"] = etag
            if modified:
                headers["If-Modified-Since"] = modified
        target = ConnectionTarget(
            place.host,
            address,
            _DEFAULT_PORT,
            TIMEOUT_SECONDS,
            budget.deadline,
            budget.clock,
            MAX_WIRE_BYTES,
        )
        with _connecting(place.host):
            connection = budget.connect(target)
        response: ResponseLike | None = None
        try:
            # inner _connecting first: a certificate failure is both an OSError and a ValueError
            with _http_call(), _connecting(place.host):
                connection.request("GET", place.path, headers=headers)
            with _http_call():
                response = connection.getresponse()
            budget.check()
            if response.status not in _REDIRECT_STATUSES:
                return _answer(response, etag, modified, budget, redirected=hops > 0)
            current = _redirect_url(current, response, hops)
        finally:
            _release(connection, response)
        hops += 1
