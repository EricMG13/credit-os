"""Fetch rules for Signal, the rest: addresses, redirects, validators, status, body and failures.

Run on the helpers and the network guard of ``signal_fetch_support``; nothing touches a network.
"""

import http.client
import ipaddress
import socket
import ssl
from collections.abc import Callable, Iterable
from typing import Any

import pytest
from signal_fetch_support import (
    PUBLIC,
    PUBLIC_IP,
    URL,
    Clock,
    Counting,
    Reply,
    Wire,
    assert_the_guard_is_active,
    no_outside_network,
    ok,
    redirect,
    run,
)

from credit_os.signal import fetch as fetch_module
from credit_os.signal import netpin
from credit_os.signal.fetch import (
    MAX_BYTES,
    Fetched,
    FetchRefused,
    Wiring,
    check_address,
    fetch,
)
from credit_os.signal.netpin import ConnectionTarget

# The guard is an autouse fixture; naming it here applies it to every test in this file.
_guard = no_outside_network


def test_the_guard_is_active_in_this_file() -> None:
    assert_the_guard_is_active()


@pytest.mark.parametrize(
    "url",
    ["http://example.org/feed", "ftp://example.org/f", "https:///nohost", "file:///etc/passwd"],
)
def test_only_https_with_a_host(url: str) -> None:
    with pytest.raises(FetchRefused):
        check_address(url, resolve=PUBLIC)


NON_PUBLIC = [
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
]


@pytest.mark.parametrize("addr", NON_PUBLIC)
def test_non_public_addresses_are_refused(addr: str) -> None:
    with pytest.raises(FetchRefused, match="public"):
        check_address(URL, resolve=lambda h: [addr])


@pytest.mark.parametrize("addr", NON_PUBLIC)
def test_a_redirect_hop_to_a_non_public_address_is_refused(addr: str) -> None:
    wire = Wire(redirect("https://other.example.org/y"), ok())

    def resolve(host: str) -> Iterable[str]:
        return [addr] if host == "other.example.org" else [PUBLIC_IP]

    with pytest.raises(FetchRefused, match="public"):
        run(wire, resolve=resolve)
    assert [t.host for t in wire.targets] == ["feeds.example.org"]


def test_one_private_address_among_public_is_refused() -> None:
    with pytest.raises(FetchRefused):
        check_address(URL, resolve=lambda h: [PUBLIC_IP, "10.0.0.1"])


def test_public_https_passes() -> None:
    check_address(URL, resolve=PUBLIC)
    check_address("https://feeds-1.example.org:8443/x", resolve=PUBLIC)
    check_address("https://WWW.Example.org/feed", resolve=PUBLIC)


def test_check_address_looks_the_resolver_up_at_call_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fetch_module, "_resolve", lambda host: ["10.0.0.1"])
    with pytest.raises(FetchRefused, match="public"):
        check_address(URL)
    with pytest.raises(FetchRefused, match="public"):
        fetch(URL, None, None, wiring=Wiring(Wire(ok())))


def test_unresolvable_host_is_refused() -> None:
    def fail(host: str) -> Iterable[str]:
        raise OSError("name not known")

    with pytest.raises(FetchRefused, match="name not known"):
        check_address(URL, resolve=fail)
    with pytest.raises(FetchRefused, match="resolved to no address"):
        check_address(URL, resolve=lambda h: [])


@pytest.mark.parametrize(
    "url",
    [
        "https://cdn%2einternal.attacker.test/",
        "https://user@feeds.example.org/",
        "https://feeds.example.org\\@evil.example/",
        "https://127.0.0.1/",
        "https://[::1]/",
        "https://[::ffff:169.254.169.254]/",
        "https://2130706433/",
        "https://0x7f.1/",
        "https://127.1/",
        "https://münchen.example/",
        "https://localhost/",
        "https://-a.example.org/",
        "https://a-.example.org/",
        "https://a..example.org/",
        "https://feeds.example.org./",
        f"https://{'a' * 64}.example.org/",
        "https://Keeds.example.org/feed",  # Kelvin sign lower-cases to "k"
    ],
)
def test_host_must_be_a_plain_name(url: str) -> None:
    with pytest.raises(FetchRefused, match="plain host name"):
        check_address(url, resolve=PUBLIC)
    wire = Wire(ok())
    with pytest.raises(FetchRefused):
        run(wire, url)
    assert not wire.targets


@pytest.mark.parametrize("url", ["https://[::1/x", "https://feeds.example.org:99999/x"])
def test_unparseable_addresses_are_refused(url: str) -> None:
    with pytest.raises(FetchRefused):
        check_address(url, resolve=PUBLIC)


def test_non_ascii_start_path_is_refused() -> None:
    wire = Wire(ok())
    with pytest.raises(FetchRefused):
        run(wire, "https://feeds.example.org/actualités")
    assert not wire.targets


def test_private_start_address_is_refused_before_any_connection() -> None:
    wire = Wire(ok())
    with pytest.raises(FetchRefused, match="public"):
        run(wire, "https://internal.example/x")
    assert not wire.targets


# M1: the connection goes to the address that was checked.
def test_no_second_lookup_changes_where_the_request_goes() -> None:
    resolver = Counting([PUBLIC_IP, "93.184.216.35"], ["127.0.0.1"])
    wire = Wire(ok())
    run(wire, resolve=resolver)
    assert resolver.calls == ["feeds.example.org"]
    assert [t.ip for t in wire.targets] == [PUBLIC_IP]
    assert wire.targets[0].port == 443
    assert wire.targets[0].timeout == fetch_module.TIMEOUT_SECONDS


def test_each_hop_is_resolved_once_and_pinned_to_its_own_checked_address() -> None:
    answers = {"feeds.example.org": ["93.184.216.34"], "other.example.org": ["93.184.216.99"]}
    calls: list[str] = []

    def resolve(host: str) -> Iterable[str]:
        calls.append(host)
        return answers[host]

    wire = Wire(redirect("https://other.example.org/y"), ok())
    run(wire, resolve=resolve)
    assert calls == ["feeds.example.org", "other.example.org"]
    assert [(t.host, t.ip) for t in wire.targets] == [
        ("feeds.example.org", "93.184.216.34"),
        ("other.example.org", "93.184.216.99"),
    ]


def test_the_production_connector_is_pinned_to_the_checked_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built: list[dict[str, Any]] = []

    class Capture(Wire):
        def __init__(self, host: str, ip: str, **kwargs: Any) -> None:
            super().__init__(ok())
            built.append({"host": host, "ip": ip, **kwargs})

    monkeypatch.setattr(netpin, "PinnedHTTPSConnection", Capture)
    monkeypatch.setattr(netpin, "tls_context", lambda: "context")
    got = fetch(URL, None, None, resolve=PUBLIC)
    assert got.body == b"<rss/>"
    assert len(built) == 1
    assert (built[0]["host"], built[0]["ip"], built[0]["port"]) == (
        "feeds.example.org",
        PUBLIC_IP,
        443,
    )
    assert built[0]["timeout"] == fetch_module.TIMEOUT_SECONDS


# Redirects
def test_redirect_to_http_is_refused() -> None:
    with pytest.raises(FetchRefused, match="https"):
        run(Wire(redirect("http://feeds.example.org/y")))


def test_redirect_to_a_public_https_address_is_followed_and_its_body_not_read() -> None:
    first = redirect("https://other.example.org/y")
    wire = Wire(first, ok())
    got = run(wire)
    assert got.body == b"<rss/>"
    assert [url for url, _ in wire.requests] == ["/x", "/y"]
    assert first.consumed == 0
    assert wire.closed == 2


def test_relative_location_is_resolved_against_the_current_url() -> None:
    wire = Wire(redirect("/other?a=1"), ok())
    run(wire, "https://feeds.example.org/dir/x")
    assert wire.requests[1][0] == "/other?a=1"
    assert wire.targets[1].host == "feeds.example.org"


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_each_redirect_status_is_followed(status: int) -> None:
    assert run(Wire(redirect("https://other.example.org/y", status), ok())).body == b"<rss/>"


@pytest.mark.parametrize(
    "location",
    [
        "https://other.example:8443/",
        "https://other.example.org:444/",
        "http://other.example.org/",
        "https://127.0.0.1/",
        "https://[::1]/",
        "https://user@other.example.org/",
        "https://cdn%2einternal.attacker.test/feed",
        "https://[::1",
        "https://[feeds.example.org]/feed",
        "https://internal.example/",
        "",
        None,
    ],
)
def test_unacceptable_redirect_targets_are_refused(location: str | None) -> None:
    wire = Wire(redirect(location), ok())
    with pytest.raises(FetchRefused):
        run(wire)
    assert len(wire.targets) == 1
    assert wire.closed == 1


def test_an_explicit_default_port_on_a_redirect_is_accepted() -> None:
    wire = Wire(redirect("https://other.example.org:443/y"), ok())
    run(wire)
    assert wire.targets[1].port == 443


def test_validators_go_to_the_first_address_only() -> None:
    wire = Wire(redirect("https://other.example.org/y"), ok())
    run(wire, etag='"abc"', modified="Fri, 13 Nov 2026 09:00:00 GMT")
    first, second = (headers for _, headers in wire.requests)
    assert first["If-None-Match"] == '"abc"'
    assert first["If-Modified-Since"] == "Fri, 13 Nov 2026 09:00:00 GMT"
    assert "If-None-Match" not in second and "If-Modified-Since" not in second
    assert second["Host"] == "other.example.org"


def test_more_than_three_redirects_are_refused() -> None:
    wire = Wire(*[redirect(f"https://feeds.example.org/{i + 1}") for i in range(10)])
    with pytest.raises(FetchRefused, match="more than 3 redirects"):
        run(wire, "https://feeds.example.org/0")
    assert len(wire.targets) == 4


def test_three_redirects_then_the_feed_succeed() -> None:
    wire = Wire(*[redirect(f"https://feeds.example.org/{i + 1}") for i in range(3)], ok())
    assert run(wire, "https://feeds.example.org/0").body == b"<rss/>"


def test_the_size_cap_is_two_mebibytes() -> None:
    assert MAX_BYTES == 2 * 1024 * 1024


def _answers(*infos: tuple[Any, ...]) -> Callable[..., list[tuple[Any, ...]]]:
    return lambda host, port, **kw: list(infos)


def test_the_system_resolver_yields_each_address_as_exact_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    v4 = (socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC_IP, 443))
    v6 = (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2606:2800:220:1::1", 443, 0, 0))
    monkeypatch.setattr(socket, "getaddrinfo", _answers(v4, v6))
    got = list(fetch_module._resolve("feeds.example.org"))
    assert got == [PUBLIC_IP, "2606:2800:220:1::1"]
    assert all(type(address) is str for address in got)


class Lying(str):
    def __str__(self) -> str:
        return PUBLIC_IP


@pytest.mark.parametrize(
    "answer",
    [b"93.184.216.34", ipaddress.ip_address(PUBLIC_IP), Lying("10.0.0.1"), 1572395042, None],
    ids=["bytes", "ip object", "str subclass", "int", "none"],
)
def test_a_resolver_answer_that_is_not_exact_text_is_refused(answer: Any) -> None:
    wire = Wire(ok())
    with pytest.raises(FetchRefused, match="not a public address"):
        run(wire, resolve=lambda host: [answer])
    assert not wire.targets


@pytest.mark.parametrize("answers", [[PUBLIC_IP, "10.0.0.1"], ["10.0.0.1", PUBLIC_IP]])
def test_a_non_public_answer_refuses_the_host_whatever_its_place(answers: list[str]) -> None:
    wire = Wire(ok())
    with pytest.raises(FetchRefused, match="10.0.0.1, which is not a public address"):
        run(wire, resolve=lambda host: answers)
    assert not wire.targets


def test_of_several_public_answers_the_first_is_pinned() -> None:
    wire = Wire(ok())
    run(wire, resolve=lambda host: ["93.184.216.99", PUBLIC_IP])
    assert [t.ip for t in wire.targets] == ["93.184.216.99"]


def test_a_redirect_to_a_host_with_a_non_public_answer_among_public_is_refused() -> None:
    wire = Wire(redirect("https://other.example.org/y"), ok())

    def resolve(host: str) -> Iterable[str]:
        return [PUBLIC_IP, "10.0.0.1"] if host == "other.example.org" else [PUBLIC_IP]

    with pytest.raises(FetchRefused, match="public"):
        run(wire, resolve=resolve)
    assert [t.host for t in wire.targets] == ["feeds.example.org"]
    assert wire.closed == 1


def test_fetch_asks_netpin_which_addresses_are_public(monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[object] = []

    def verdict(address: object) -> bool:
        asked.append(address)
        return address == "10.0.0.1"

    monkeypatch.setattr(netpin, "is_public", verdict)
    wire = Wire(ok())
    run(wire, resolve=lambda host: ["10.0.0.1"])
    assert asked == ["10.0.0.1"]
    assert [t.ip for t in wire.targets] == ["10.0.0.1"]
    with pytest.raises(FetchRefused, match="public"):
        run(Wire(ok()), resolve=PUBLIC)
    assert asked == ["10.0.0.1", PUBLIC_IP]


def test_fetch_keeps_no_address_check_of_its_own() -> None:
    assert not hasattr(fetch_module, "_is_public")
    assert not hasattr(fetch_module, "_EMBEDDING_V4")


@pytest.mark.parametrize("port", ["0", "00", "000"])
def test_port_zero_is_refused_before_any_lookup_or_connection(port: str) -> None:
    resolver = Counting([PUBLIC_IP])
    wire = Wire(ok())
    with pytest.raises(FetchRefused, match="port"):
        run(wire, f"https://feeds.example.org:{port}/x", resolve=resolver)
    with pytest.raises(FetchRefused, match="port"):
        check_address(f"https://feeds.example.org:{port}/x", resolve=resolver)
    assert not resolver.calls and not wire.targets


def test_port_zero_on_a_redirect_is_refused() -> None:
    wire = Wire(redirect("https://other.example.org:0/y"), ok())
    with pytest.raises(FetchRefused, match="port"):
        run(wire)
    assert len(wire.targets) == 1


# One deadline boundary: time is spent at clock >= deadline, as in the pinned connection
def test_a_clock_exactly_at_the_deadline_after_the_lookup_refuses_without_a_connection() -> None:
    clock = Clock()
    wire = Wire(ok())

    def lookup_ends_at_the_deadline(host: str) -> Iterable[str]:
        clock.advance(fetch_module.TOTAL_SECONDS)
        return [PUBLIC_IP]

    with pytest.raises(FetchRefused, match="longer than 10 seconds"):
        run(wire, resolve=lookup_ends_at_the_deadline, clock=clock)
    assert not wire.targets


def test_a_clock_just_inside_the_deadline_still_connects() -> None:
    clock = Clock()
    wire = Wire(ok())

    def slow(host: str) -> Iterable[str]:
        clock.advance(fetch_module.TOTAL_SECONDS - 0.25)
        return [PUBLIC_IP]

    assert run(wire, resolve=slow, clock=clock).body == b"<rss/>"
    assert len(wire.targets) == 1


def test_a_redirect_lookup_ending_exactly_at_the_deadline_opens_no_second_connection() -> None:
    clock = Clock()
    wire = Wire(redirect("https://other.example.org/y"), ok())

    def resolve(host: str) -> Iterable[str]:
        if host == "other.example.org":
            clock.advance(fetch_module.TOTAL_SECONDS)
        return [PUBLIC_IP]

    with pytest.raises(FetchRefused, match="longer than 10 seconds"):
        run(wire, resolve=resolve, clock=clock)
    assert [t.host for t in wire.targets] == ["feeds.example.org"]


def test_headers_that_arrive_exactly_at_the_deadline_are_refused() -> None:
    clock = Clock()
    wire = Wire(ok())
    wire.on_response = lambda: clock.advance(fetch_module.TOTAL_SECONDS)
    with pytest.raises(FetchRefused, match="longer than 10 seconds"):
        run(wire, clock=clock)


def test_a_body_read_that_ends_exactly_at_the_deadline_is_refused() -> None:
    clock = Clock()
    reply = Reply(200, b"", on_read=lambda: clock.advance(fetch_module.TOTAL_SECONDS))
    with pytest.raises(FetchRefused, match="longer than 10 seconds"):
        run(Wire(reply), clock=clock)


def test_the_production_connector_is_not_reached_at_the_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dialled: list[object] = []

    def record(address: object, *args: object, **kwargs: object) -> socket.socket:
        dialled.append(address)
        raise ConnectionRefusedError("a test refused the dial")

    monkeypatch.setattr(socket, "create_connection", record)
    clock = Clock()

    def lookup_ends_at_the_deadline(host: str) -> Iterable[str]:
        clock.advance(fetch_module.TOTAL_SECONDS)
        return [PUBLIC_IP]

    with pytest.raises(FetchRefused, match="feed took longer than 10 seconds"):
        fetch(URL, None, None, resolve=lookup_ends_at_the_deadline, wiring=Wiring(None, clock))
    assert dialled == []


# Request headers
def test_headers_sent_on_the_first_request() -> None:
    wire = Wire(ok())
    run(wire, etag=None, modified=None)
    ((path, headers),) = wire.requests
    assert path == "/x"
    assert set(headers) == {"Host", "User-Agent", "Accept", "Accept-Encoding", "Connection"}
    assert headers["User-Agent"] == fetch_module.USER_AGENT
    assert headers["Accept-Encoding"] == "identity"


def test_identity_encoding_is_asked_for_on_every_hop() -> None:
    wire = Wire(redirect("https://other.example.org/y"), ok())
    run(wire)
    assert [headers["Accept-Encoding"] for _, headers in wire.requests] == ["identity", "identity"]


def test_a_port_on_the_first_address_is_connected_to_and_named_in_host() -> None:
    wire = Wire(ok())
    run(wire, "https://feeds-1.example.org:8443/x")
    assert wire.targets[0].port == 8443
    assert wire.requests[0][1]["Host"] == "feeds-1.example.org:8443"


# Status and body
def test_304_returns_no_body_and_the_validators_sent() -> (
    None
):  # none came back, so the sent ones stay
    wire = Wire(Reply(304))
    got = run(wire, etag='"abc"', modified="Fri, 13 Nov 2026 09:00:00 GMT")
    assert got == Fetched(None, '"abc"', "Fri, 13 Nov 2026 09:00:00 GMT")


def test_304_prefers_the_validators_the_server_sent() -> None:
    got = run(Wire(Reply(304, headers={"ETag": '"new"', "Last-Modified": "Sat"})), etag='"abc"')
    assert got == Fetched(None, '"new"', "Sat")


BAD_VALIDATORS = {
    "obs-fold": '"a"\r\n X-Folded: evil',
    "nul": '"a\x00b"',
    "del": '"a\x7fb"',
    "tab": '"a\tb"',
    "empty": "",
    "long": "M" * 60000,
    "just over": "M" * 257,
}


@pytest.mark.parametrize("bad", BAD_VALIDATORS.values(), ids=BAD_VALIDATORS)
def test_a_malformed_validator_on_a_200_is_not_returned(bad: str) -> None:
    got = run(Wire(Reply(200, b"<rss/>", {"ETag": bad, "Last-Modified": bad})))
    assert got == Fetched(b"<rss/>", None, None)


def test_a_validator_of_the_longest_allowed_size_is_returned() -> None:
    got = run(Wire(Reply(200, b"<rss/>", {"ETag": "E" * 256})))
    assert got.etag == "E" * 256


def test_validators_on_a_200_after_a_redirect_are_not_returned() -> None:
    wire = Wire(
        redirect("https://other.example.org/y"),
        Reply(200, b"<rss/>", {"ETag": '"h"', "Last-Modified": "Sat"}),
    )
    assert run(wire) == Fetched(b"<rss/>", None, None)


def test_a_304_after_a_redirect_is_refused() -> None:
    wire = Wire(redirect("https://other.example.org/y"), Reply(304, headers={"ETag": '"h"'}))
    with pytest.raises(FetchRefused, match="304"):
        run(wire, etag='"abc"')


def test_a_304_with_a_malformed_validator_keeps_the_one_sent() -> None:
    reply = Reply(304, headers={"ETag": '"a"\r\n X: y', "Last-Modified": "M" * 60000})
    assert run(Wire(reply), etag='"abc"', modified="Fri") == Fetched(None, '"abc"', "Fri")


def test_a_304_with_one_clean_validator_mixes_it_with_the_one_sent() -> None:
    reply = Reply(304, headers={"ETag": '"new"', "Last-Modified": "\x00"})
    assert run(Wire(reply), etag='"abc"', modified="Fri") == Fetched(None, '"new"', "Fri")


STORED_BAD = ['"a"\r\n X: y', "x" * 257, "\x00", ""]


@pytest.mark.parametrize("bad", STORED_BAD, ids=["fold", "long", "nul", "empty"])
def test_a_stored_etag_the_module_would_not_accept_is_not_sent_or_returned(bad: str) -> None:
    wire = Wire(Reply(304))
    got = run(wire, etag=bad, modified="Fri")
    assert "If-None-Match" not in wire.requests[0][1]
    assert got == Fetched(None, None, "Fri")


@pytest.mark.parametrize("bad", STORED_BAD, ids=["fold", "long", "nul", "empty"])
def test_a_stored_modified_the_module_would_not_accept_is_not_sent_or_returned(bad: str) -> None:
    wire = Wire(Reply(304))
    got = run(wire, etag='"abc"', modified=bad)
    assert "If-Modified-Since" not in wire.requests[0][1]
    assert got == Fetched(None, '"abc"', None)


def test_valid_stored_validators_are_sent_and_returned() -> None:
    wire = Wire(Reply(304))
    got = run(wire, etag='"abc"', modified="Fri")
    headers = wire.requests[0][1]
    assert (headers["If-None-Match"], headers["If-Modified-Since"]) == ('"abc"', "Fri")
    assert got == Fetched(None, '"abc"', "Fri")


def test_200_returns_body_and_validators() -> None:
    got = run(Wire(Reply(200, b"<rss/>", {"ETag": '"v2"', "Last-Modified": "Sat"})))
    assert got == Fetched(b"<rss/>", '"v2"', "Sat")


@pytest.mark.parametrize("status", [204, 401, 404, 500])
def test_other_status_is_refused_with_the_status(status: int) -> None:
    with pytest.raises(FetchRefused, match=str(status)):
        run(Wire(Reply(status)))


def test_body_of_exactly_the_cap_is_accepted() -> None:
    got = run(Wire(Reply(200, b"x" * MAX_BYTES)))
    assert got.body is not None and len(got.body) == MAX_BYTES


def test_body_one_byte_over_the_cap_is_refused_without_reading_the_rest() -> None:
    reply = Reply(200, b"x" * (MAX_BYTES * 3))
    with pytest.raises(FetchRefused, match="2 MB"):
        run(Wire(reply))
    assert reply.consumed == MAX_BYTES + 1


def test_a_declared_length_over_the_cap_is_refused_before_reading() -> None:
    reply = Reply(200, b"x" * 10, {"Content-Length": str(MAX_BYTES + 1)})
    with pytest.raises(FetchRefused, match="2 MB"):
        run(Wire(reply))
    assert reply.consumed == 0


def test_a_body_shorter_than_its_declared_length_is_refused() -> None:
    with pytest.raises(FetchRefused, match="ended early"):
        run(Wire(Reply(200, b"<rss/>", {"Content-Length": "1000"})))


def test_a_body_matching_its_declared_length_is_accepted() -> None:
    assert run(Wire(Reply(200, b"<rss/>", {"Content-Length": "6"}))).body == b"<rss/>"


@pytest.mark.parametrize("length", ["+1000", "1_000", "1" * 19, "5, 5", "٥"])
def test_an_unusable_content_length_is_refused(length: str) -> None:
    with pytest.raises(FetchRefused, match="unusable length"):
        run(Wire(Reply(200, b"<rss/>", {"Content-Length": length})))


@pytest.mark.parametrize("length", ["", "-5", "0x10", "abc"])
def test_a_length_http_client_ignores_is_undeclared(length: str) -> None:
    got = run(Wire(Reply(200, b"<rss/>", {"Content-Length": length})))
    assert got.body == b"<rss/>"


@pytest.mark.parametrize("encoding", ["gzip", "br", "deflate"])
def test_a_content_encoding_is_refused(encoding: str) -> None:
    with pytest.raises(FetchRefused, match="content encoding"):
        run(Wire(Reply(200, b"x", {"Content-Encoding": encoding})))


def test_identity_content_encoding_is_accepted() -> None:
    assert run(Wire(Reply(200, b"x", {"Content-Encoding": "Identity"}))).body == b"x"


# Failures
@pytest.mark.parametrize(
    "error",
    [
        OSError("socket broke"),
        TimeoutError("timed out"),
        ssl.SSLCertVerificationError("certificate verify failed"),
        http.client.BadStatusLine("garbage"),
        http.client.IncompleteRead(b"ab", 5),
        ValueError("bad header"),
    ],
    ids=lambda error: type(error).__name__,
)
def test_every_failure_is_a_one_line_refusal(error: Exception) -> None:
    with pytest.raises(FetchRefused) as refused:
        run(Wire(error))
    assert "\n" not in str(refused.value) and str(refused.value)


def test_a_failure_while_connecting_is_a_refusal() -> None:
    def connect(target: ConnectionTarget) -> Any:
        raise OSError("connection refused")

    with pytest.raises(FetchRefused, match="connection refused"):
        fetch(URL, None, None, resolve=PUBLIC, wiring=Wiring(connect))


def _assert_short_line(error: object, absent: tuple[str, ...] = ()) -> None:
    text = str(error)
    assert len(text) <= 200 and "\n" not in text and "\r" not in text
    assert all(piece not in text for piece in absent)


def test_a_long_scheme_is_not_echoed_and_the_reason_is_short() -> None:
    with pytest.raises(FetchRefused) as refused:
        check_address("s" * 60000 + "://feeds.example.org/", resolve=PUBLIC)
    _assert_short_line(refused.value, absent=("sss",))


def test_a_long_host_keeps_every_reason_within_200_characters() -> None:
    host = ".".join(["a" * 63] * 3 + ["b" * 61])
    assert len(host) == 253
    for resolve in (lambda h: ["10.0.0.1"], lambda h: []):
        with pytest.raises(FetchRefused) as refused:
            check_address(f"https://{host}/", resolve=resolve)
        _assert_short_line(refused.value)


def test_a_failure_reason_is_200_characters_in_all() -> None:
    with pytest.raises(FetchRefused) as refused:
        run(Wire(OSError("Q" * 5000)))
    _assert_short_line(refused.value)
    assert str(refused.value).startswith("fetch failed: ")


def test_a_reply_without_a_status_line_puts_no_server_text_in_the_reason() -> None:
    with pytest.raises(FetchRefused) as refused:
        run(Wire(http.client.BadStatusLine("secret-looking body line")))
    _assert_short_line(refused.value, absent=("secret",))
    assert "BadStatusLine" in str(refused.value)


def test_error_text_is_cut_to_one_short_line() -> None:
    with pytest.raises(FetchRefused) as refused:
        run(Wire(OSError("Q" * 5000 + "\nline two")))
    _assert_short_line(refused.value)


def test_a_failure_that_is_not_a_fetch_error_is_not_hidden() -> None:
    with pytest.raises(KeyError):
        run(Wire(KeyError("bug")))


def test_a_redirect_loop_between_two_hosts_ends_at_the_hop_limit() -> None:
    hosts = ["feeds.example.org", "other.example.org"]
    wire = Wire(*[redirect(f"https://{hosts[(i + 1) % 2]}/loop") for i in range(10)])
    with pytest.raises(FetchRefused, match="more than 3 redirects"):
        run(wire)
    assert [t.host for t in wire.targets] == [hosts[i % 2] for i in range(4)]
    assert wire.closed == 4


@pytest.mark.parametrize(
    ("declared", "size", "accepted"),
    [
        (None, MAX_BYTES, True),
        (None, MAX_BYTES + 1, False),
        (MAX_BYTES, MAX_BYTES, True),
        (MAX_BYTES, MAX_BYTES + 1, False),
        (MAX_BYTES + 1, MAX_BYTES, False),
        (MAX_BYTES + 1, MAX_BYTES + 1, False),
    ],
)
def test_the_body_cap_holds_at_the_cap_and_one_over_with_and_without_a_length(
    declared: int | None, size: int, accepted: bool
) -> None:
    headers = {} if declared is None else {"Content-Length": str(declared)}
    reply = Reply(200, b"x" * size, headers)
    if accepted:
        got = run(Wire(reply))
        assert got.body is not None and len(got.body) == MAX_BYTES
    else:
        with pytest.raises(FetchRefused, match="2 MB"):
            run(Wire(reply))
        assert reply.consumed <= MAX_BYTES + 1


def test_a_body_one_byte_short_of_its_declared_cap_length_ended_early() -> None:
    reply = Reply(200, b"x" * (MAX_BYTES - 1), {"Content-Length": str(MAX_BYTES)})
    with pytest.raises(FetchRefused, match="ended early"):
        run(Wire(reply))


def test_a_conditional_request_answered_304_returns_the_sent_validators_and_closes() -> None:
    reply = Reply(304)
    wire = Wire(reply)
    got = run(wire, etag='"abc"', modified="Fri")
    assert got == Fetched(None, '"abc"', "Fri")
    assert wire.requests[0][1]["If-None-Match"] == '"abc"'
    assert wire.requests[0][1]["If-Modified-Since"] == "Fri"
    assert (reply.closed, wire.closed) == (1, 1)
