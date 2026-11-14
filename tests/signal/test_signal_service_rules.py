"""Signal's HTTP service: the rules of the error mapping, identity, limits and text bounds.

Every expected value is written here by hand. A patched callee raises the error under test; the
reply and the log are read at the HTTP surface. Loopback only; at most one server thread and a few
client sockets are alive at once.
"""

from __future__ import annotations

import http.client
import json
import socket
import sqlite3
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from service_support import Live, raw, read_all
from test_signal_feedview import build_feed_db
from test_signal_service_wire import POLICY

from credit_os.signal import feedview, groups, identity, service, store, topics
from credit_os.signal.service import make_server

FAILED = {"error": "the service failed; see its log"}
BUSY = {"error": "the store is busy; try again"}


@pytest.fixture
def root(tmp_path: Path) -> Path:
    build_feed_db(tmp_path).close()
    return tmp_path


@pytest.fixture
def svc(root: Path) -> Iterator[Live]:
    live = Live(make_server(root, "127.0.0.1", 0))
    yield live
    live.close()


@pytest.fixture
def cookie() -> str:
    return "signal_name=Reader"


def raising(error: BaseException) -> Callable[..., None]:
    def fail(*args: object, **kwargs: object) -> None:
        raise error

    return fail


# (method, path, module, attribute): where a patched callee raises, one row per kind of route.
SITES = {
    "feed": ("GET", "/api/feed?view=latest", feedview, "feed"),
    "save": ("POST", "/api/stories/5/save", feedview, "save"),
    "follow": ("POST", "/api/topics/1/follow", topics, "follow"),
    "me": ("GET", "/api/me", store, "open_db"),
}


@pytest.mark.parametrize("site", list(SITES))
@pytest.mark.parametrize(
    ("error", "status", "body"),
    [
        (store.StoreUnusable("secret"), 500, FAILED),
        (sqlite3.OperationalError("secret"), 503, BUSY),
    ],
    ids=["unusable", "busy"],
)
def test_an_unusable_or_busy_store_is_a_fixed_text_and_the_cause_stays_in_the_log(
    svc: Live,
    cookie: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    site: str,
    error: BaseException,
    status: int,
    body: dict[str, str],
) -> None:
    method, path, module, attribute = SITES[site]
    monkeypatch.setattr(module, attribute, raising(error))
    got = svc.call(method, path, cookie=cookie)
    assert (got[0], got[2]) == (status, body)
    assert "secret" not in json.dumps(got[2])
    assert "secret" in caplog.text


@pytest.mark.parametrize(
    ("site", "error", "status", "text"),
    [
        ("follow", identity.IdentityError("bad name"), 400, "bad name"),
        ("follow", feedview.ViewError("bad view"), 400, "bad view"),
        ("follow", store.StoreError("bad topic"), 404, "bad topic"),
        ("follow", store.StoreUnusable("secret"), 500, FAILED["error"]),
        ("save", groups.Forbidden("not yours"), 403, "not yours"),
        ("save", feedview.ViewError("bad story"), 404, "bad story"),
        ("save", store.StoreError("bad save"), 400, "bad save"),
        ("feed", groups.NotFound("no such group"), 404, "no such group"),
        ("feed", store.StoreError("bad feed"), 400, "bad feed"),
    ],
    ids=[
        "identity-not-store",
        "view-not-store",
        "store-follow",
        "unusable-follow",
        "forbidden-not-store",
        "view-save",
        "store-save",
        "notfound-by-type",
        "store-feed",
    ],
)
def test_each_error_is_answered_by_its_type_and_the_routes_status(
    svc: Live,
    cookie: str,
    monkeypatch: pytest.MonkeyPatch,
    site: str,
    error: BaseException,
    status: int,
    text: str,
) -> None:
    method, path, module, attribute = SITES[site]
    monkeypatch.setattr(module, attribute, raising(error))
    got = svc.call(method, path, cookie=cookie)
    assert (got[0], got[2]) == (status, {"error": text})


def test_a_view_error_is_400_from_the_feed_and_404_from_the_card_and_the_saves(
    svc: Live, cookie: str
) -> None:
    assert svc.call("GET", "/api/feed?view=top", cookie=cookie)[::2] == (
        400,
        {"error": "unknown view 'top'"},
    )
    assert svc.call("GET", "/api/feed/new?view=top&after=0", cookie=cookie)[::2] == (
        400,
        {"error": "unknown view 'top'"},
    )
    for method, path in (
        ("GET", "/api/stories/9999"),
        ("POST", "/api/stories/9999/save"),
        ("DELETE", "/api/stories/9999/save"),
    ):
        got = svc.call(method, path, cookie=cookie)
        assert (got[0], got[2]) == (404, {"error": "no story with id 9999"}), path


def test_following_a_missing_topic_is_404_and_an_unusable_store_is_500(
    svc: Live, cookie: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    for method in ("POST", "DELETE"):
        got = svc.call(method, "/api/topics/99/follow", cookie=cookie)
        assert (got[0], got[2]) == (404, {"error": "no topic with id 99"}), method
    monkeypatch.setattr(topics, "unfollow", raising(store.StoreUnusable("secret")))
    got = svc.call("DELETE", "/api/topics/1/follow", cookie=cookie)
    assert (got[0], got[2]) == (500, FAILED)


SHOWN = "a" * 60_000


@pytest.mark.parametrize(
    ("path", "refusal"),
    [
        (f"/api/feed?view=latest&shared={SHOWN}", "invalid shared; expected 1"),
        (f"/api/feed/new?view=latest&after={SHOWN}", "invalid after; expected digits"),
        (f"/api/feed?view={SHOWN}", None),
        (f"/api/feed/new?view={SHOWN}&after=0", None),
        (f"/api/feed?view=latest&kind={SHOWN}", None),
        (f"/api/feed?view=latest&before={SHOWN}", None),
    ],
    ids=["shared", "after", "view", "view-new", "kind", "before"],
)
def test_a_long_client_text_is_never_echoed_whole(
    svc: Live, cookie: str, path: str, refusal: str | None
) -> None:
    status, _, data = svc.call("GET", path, cookie=cookie)
    assert status == 400
    assert len(json.dumps(data)) < 400
    assert "a" * 121 not in json.dumps(data)
    if refusal is not None:  # P3: a fixed text, not the value
        assert data == {"error": refusal}


def rows(root: Path, sql: str) -> list[tuple[Any, ...]]:
    db = store.open_db(root)
    try:
        return [tuple(row) for row in db.execute(sql).fetchall()]
    finally:
        db.close()


def test_nothing_in_the_request_but_the_cookie_says_who_acts(
    svc: Live, root: Path, cookie: str
) -> None:
    who = "?name=ml&user=ml&user_name=ml"
    body = {"name": "ml", "user": "ml", "user_name": "ml"}
    assert svc.call("POST", f"/api/stories/5/save{who}", cookie=cookie, body=body)[0] == 200
    assert svc.call("POST", f"/api/topics/1/follow{who}", cookie=cookie, body=body)[0] == 200
    assert [r[:2] for r in rows(root, "SELECT user_name, story_id FROM saves")] == [("Reader", 5)]
    assert rows(root, "SELECT user_name, topic_id FROM topic_follows") == [("Reader", 1)]
    other = "signal_name=Other"
    seen = svc.call("GET", "/api/feed?view=saved&name=Reader&user=Reader", cookie=other)
    assert seen[2]["cards"] == []
    assert (
        svc.call("GET", "/api/topics?name=Reader&user=Reader", cookie=other)[2][0]["following"]
        is False
    )
    assert svc.call("DELETE", f"/api/stories/5/save{who}", cookie=other, body=body)[0] == 200
    assert rows(root, "SELECT user_name, story_id FROM saves")[0][:2] == ("Reader", 5)


def test_two_cookie_lines_are_a_refusal(svc: Live) -> None:
    connection = http.client.HTTPConnection("127.0.0.1", svc.port, timeout=10)
    connection.putrequest("GET", "/api/feed?view=latest", skip_accept_encoding=True)
    connection.putheader("Cookie", "signal_name=Reader")
    connection.putheader("Cookie", "signal_name=Other")
    connection.endheaders()
    response = connection.getresponse()
    assert (response.status, json.loads(response.read())) == (
        400,
        {"error": "send one Cookie header"},
    )
    connection.close()


def test_the_limits_are_these_numbers() -> None:
    assert service.MAX_JSON == 65536
    assert service.SOCKET_TIMEOUT == 60
    assert service.MAX_CONNECTIONS == 64
    assert service.MAX_PER_ADDRESS == 16
    assert service.MAX_PARAMS == 20
    assert service.MAX_AFTER_DIGITS == 19
    assert service._ID == "([0-9]{1,18})"


def parse_reply(data: bytes) -> tuple[int, dict[str, str], Any]:
    head, _, body = data.partition(b"\r\n\r\n")
    lines = head.decode("latin-1").split("\r\n")
    headers = dict(line.split(": ", 1) for line in lines[1:])
    return int(lines[0].split()[1]), headers, json.loads(body)


def sent(live: Live, data: bytes) -> tuple[int, dict[str, str], Any]:
    """Send ``data`` whole, close our side, and read the reply to the end."""
    sock = raw(live, data)
    try:
        sock.shutdown(socket.SHUT_WR)
        return parse_reply(read_all(sock))
    finally:
        sock.close()


def test_twenty_one_query_fields_are_refused_and_twenty_are_not(svc: Live) -> None:
    twenty = "&".join(f"f{n}=1" for n in range(20))
    assert svc.call("GET", f"/api/me?{twenty}")[0] == 200
    got = svc.call("GET", f"/api/me?{twenty}&f20=1")
    assert (got[0], got[2]) == (400, {"error": "the query string is not valid"})


def test_the_library_replies_are_fixed_json_with_the_four_headers(svc: Live) -> None:
    long_line = b"GET /" + b"a" * (65_537 - 5)  # 65,537 bytes, no line end: one past the limit
    many = b"GET /api/me HTTP/1.1\r\n" + b"".join(b"X-%d: 1\r\n" % n for n in range(101))
    for data, status in ((long_line, 414), (many, 431)):
        got = sent(svc, data)
        assert (got[0], got[2]) == (status, {"error": "the request could not be read"})
        assert got[1]["X-Content-Type-Options"] == "nosniff"
        assert got[1]["Cross-Origin-Resource-Policy"] == "same-origin"
        assert got[1]["Content-Security-Policy"] == POLICY
        assert got[1]["X-Frame-Options"] == "DENY"


@pytest.mark.parametrize(
    "lines",
    [
        [b"Content-Length: +5"],
        [b"Content-Length: -1"],
        [b"Content-Length: \xb2"],
        [b"Content-Length: 5", b"Content-Length: 5"],
        [b"Content-Length: 1234567890123456"],
    ],
    ids=["plus", "minus", "superscript", "two-lines", "sixteen-digits"],
)
def test_a_content_length_that_is_not_a_length_is_400(svc: Live, lines: list[bytes]) -> None:
    head = b"POST /api/me HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n" % svc.port
    head += b"Origin: http://127.0.0.1:%d\r\n" % svc.port
    got = sent(svc, head + b"\r\n".join(lines) + b"\r\n\r\n")
    assert (got[0], got[2]) == (400, {"error": "Content-Length is not a length"})


def test_a_length_of_fifteen_digits_is_read_as_a_length(svc: Live) -> None:
    head = b"POST /api/me HTTP/1.1\r\nHost: 127.0.0.1:%d\r\n" % svc.port
    head += b"Origin: http://127.0.0.1:%d\r\nContent-Length: 000000000000014\r\n\r\n" % svc.port
    got = sent(svc, head + b'{"name": "ok"}')
    assert (got[0], got[2]) == (200, {"name": "ok", "role": "reader"})


def test_the_host_names_a_service_answers_to() -> None:
    assert service._hosts("127.0.0.1", 8766) == {"127.0.0.1:8766", "localhost:8766"}
    assert service._hosts("10.0.0.5", 8766) == {"10.0.0.5:8766"}
    assert service._hosts("10.0.0.5", 80) == {"10.0.0.5:80", "10.0.0.5"}
    assert service._hosts("127.0.0.1", 80) == {
        "127.0.0.1:80",
        "localhost:80",
        "127.0.0.1",
        "localhost",
    }


@pytest.mark.parametrize(
    ("address", "family", "expected"),
    [
        ("0.0.0.0", socket.AF_INET, True),
        ("::", socket.AF_INET6, True),
        ("::ffff:0.0.0.0", socket.AF_INET6, True),
        ("93.184.216.34", socket.AF_INET, False),
        ("fe80::1%en0", socket.AF_INET6, False),
    ],
    ids=["ipv4", "ipv6", "mapped", "public", "scoped"],
)
def test_a_name_that_resolves_to_every_interface_is_a_wildcard(
    monkeypatch: pytest.MonkeyPatch, address: str, family: int, expected: bool
) -> None:
    found = [(family, socket.SOCK_STREAM, 6, "", (address, 0))]
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: found)
    assert service._wildcard("any.example") is expected


def test_a_name_that_does_not_resolve_is_not_a_wildcard_and_the_real_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert (service._wildcard(""), service._wildcard("0.0.0.0")) == (True, True)
    assert service._wildcard("127.0.0.1") is False
    monkeypatch.setattr(socket, "getaddrinfo", raising(socket.gaierror("no such name")))
    assert service._wildcard("nowhere.example") is False


class Tracked(sqlite3.Connection):
    closes = 0

    def close(self) -> None:
        self.closes += 1
        super().close()


@pytest.mark.parametrize(
    ("status", "method", "path", "error", "named"),
    [
        (200, "GET", "/api/me", None, True),
        (400, "GET", "/api/feed", None, True),
        (401, "GET", "/api/feed?view=latest", None, False),
        (403, "GET", "/api/feed?view=latest", groups.Forbidden("no"), True),
        (404, "GET", "/api/stories/9999", None, True),
        (500, "GET", "/api/feed?view=latest", store.StoreUnusable("x"), True),
        (503, "GET", "/api/feed?view=latest", sqlite3.OperationalError("x"), True),
    ],
    ids=["200", "400", "401", "403", "404", "500", "503"],
)
def test_the_connection_of_every_reply_is_closed(
    svc: Live,
    cookie: str,
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    method: str,
    path: str,
    error: BaseException | None,
    named: bool,
) -> None:
    opened: list[Tracked] = []
    real_connect, real_open = sqlite3.connect, store.open_db

    def connect(*args: Any, **kwargs: Any) -> sqlite3.Connection:
        return real_connect(*args, factory=Tracked, **kwargs)

    def recording(where: Path) -> sqlite3.Connection:
        db = real_open(where)
        assert isinstance(db, Tracked)
        opened.append(db)
        return db

    monkeypatch.setattr(sqlite3, "connect", connect)
    monkeypatch.setattr(store, "open_db", recording)
    if error is not None:
        monkeypatch.setattr(feedview, "feed", raising(error))
    assert svc.call(method, path, cookie=cookie if named else None)[0] == status
    assert len(opened) == 1
    assert [db.closes for db in opened] == [1]


def test_topics_say_following_with_a_boolean(svc: Live, cookie: str) -> None:
    expected = {"id": 1, "name": "Remedy", "following": False, "stories": 1}
    before = svc.call("GET", "/api/topics", cookie=cookie)[2]
    assert before == [expected] and before[0]["following"] is False
    svc.call("POST", "/api/topics/1/follow", cookie=cookie)
    after = svc.call("GET", "/api/topics", cookie=cookie)[2]
    assert after == [{**expected, "following": True}] and after[0]["following"] is True


def test_feed_is_given_only_its_four_filters_and_shared_only_for_one(
    svc: Live, cookie: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    given: list[dict[str, Any]] = []
    real = feedview.feed

    def recording(*args: Any, **kwargs: Any) -> feedview.Page:
        given.append(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(feedview, "feed", recording)
    query = "view=latest&kind=news&q=remedy&before=2026-11-13T09:00:00%2B00:00|9&shared=1&user=ml"
    assert svc.call("GET", f"/api/feed?{query}", cookie=cookie)[0] == 200
    assert given == [
        {"kind": "news", "query": "remedy", "before": "2026-11-13T09:00:00+00:00|9", "shared": True}
    ]
    for value in ("0", "true", "", "01"):
        got = svc.call("GET", f"/api/feed?view=latest&shared={value}", cookie=cookie)
        assert (got[0], got[2]) == (400, {"error": "invalid shared; expected 1"}), value
    assert len(given) == 1


def test_a_story_card_is_the_feed_card_as_this_user_sees_it(svc: Live, cookie: str) -> None:
    status, _, card = svc.call("GET", "/api/stories/5", cookie=cookie)
    assert (status, card["id"], card["title"], card["saved"]) == (200, 5, "Story 05", False)
    svc.call("POST", "/api/stories/5/save", cookie=cookie)
    assert svc.call("GET", "/api/stories/5", cookie=cookie)[2]["saved"] is True
    assert svc.call("GET", "/api/stories/5", cookie="signal_name=Other")[2]["saved"] is False
