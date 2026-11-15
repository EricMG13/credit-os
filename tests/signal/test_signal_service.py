"""Signal's HTTP service, feed routes: names, feed, paging, new count, save, follow, topics.

Run for real on one loopback port (port 0) over a seeded store; nothing here reaches beyond
127.0.0.1. The page is not served (decision 0009), so a path no API route matches is a 404.
"""

from __future__ import annotations

import urllib.parse
from collections.abc import Iterator
from pathlib import Path

import pytest
from service_support import Live
from test_signal_feedview import build_feed_db

from credit_os.signal import feedview
from credit_os.signal.service import make_server


@pytest.fixture
def svc(tmp_path: Path) -> Iterator[Live]:
    build_feed_db(tmp_path).close()
    live = Live(make_server(tmp_path, "127.0.0.1", 0))
    yield live
    live.close()


@pytest.fixture
def cookie() -> str:
    return "signal_name=Reader"


def test_name_then_feed(svc: Live) -> None:
    assert svc.call("GET", "/api/feed?view=latest")[0] == 401
    status, headers, _ = svc.call("POST", "/api/me", body={"name": "  A.  Kovac "})
    assert status == 200 and headers["Set-Cookie"].startswith("signal_name=A.%20Kovac;")
    cookie = headers["Set-Cookie"].split(";")[0]
    assert svc.call("GET", "/api/me", cookie=cookie)[2] == {"name": "A. Kovac", "role": "reader"}
    status, _, data = svc.call("GET", "/api/feed?view=latest", cookie=cookie)
    assert status == 200 and len(data["cards"]) == 30 and data["next_before"]
    assert set(data["cards"][0]) == {
        "id",
        "title",
        "link",
        "summary",
        "source",
        "kind",
        "published_at",
        "other_sources",
        "saved",
        "topics",
        "threads",
    }
    assert svc.call("GET", "/api/feed?view=top", cookie=cookie)[0] == 400
    assert svc.call("POST", "/api/me", body={"name": "   "})[0] == 400


def test_every_other_api_route_needs_a_name(svc: Live) -> None:
    for method, path in (
        ("GET", "/api/feed?view=latest"),
        ("GET", "/api/feed/new?view=latest&after=0"),
        ("POST", "/api/stories/5/save"),
        ("DELETE", "/api/stories/5/save"),
        ("GET", "/api/topics"),
        ("POST", "/api/topics/1/follow"),
        ("DELETE", "/api/topics/1/follow"),
    ):
        status, _, data = svc.call(method, path)
        assert (status, data) == (401, {"error": "choose a display name first"}), path


def test_paging_follows_the_cursor(svc: Live, cookie: str) -> None:
    first = svc.call("GET", "/api/feed?view=latest", cookie=cookie)[2]
    second = svc.call(
        "GET",
        "/api/feed?view=latest&before=" + urllib.parse.quote(first["next_before"]),
        cookie=cookie,
    )[2]
    assert len(second["cards"]) == 6 and second["next_before"] is None


def test_feed_parameters(svc: Live, cookie: str) -> None:
    assert svc.call("GET", "/api/feed", cookie=cookie)[0] == 400
    assert (
        svc.call("GET", "/api/feed?view=latest&kind=news", cookie=cookie)[2]["cards"][0]["kind"]
        == "news"
    )
    assert svc.call("GET", "/api/feed?view=latest&kind=bogus", cookie=cookie)[0] == 400
    assert svc.call("GET", "/api/feed?view=latest&before=junk", cookie=cookie)[0] == 400
    # a repeated parameter uses the first
    assert svc.call("GET", "/api/feed?view=saved&view=latest", cookie=cookie)[2]["cards"] == []
    assert svc.call("GET", "/api/feed?view=%ff", cookie=cookie)[0] == 400
    assert svc.call("GET", "/api/feed?q=remedy&view=latest", cookie=cookie)[2]["cards"][0][
        "title"
    ].startswith("Wire")


def test_feed_carries_the_newest_story_id(svc: Live, cookie: str) -> None:
    assert svc.call("GET", "/api/feed?view=latest", cookie=cookie)[2]["newest"] == 36


def test_new_count(svc: Live, cookie: str) -> None:
    assert svc.call("GET", "/api/feed/new?view=latest&after=0", cookie=cookie)[2] == {"count": 36}
    assert svc.call("GET", "/api/feed/new?view=latest&after=36", cookie=cookie)[2] == {"count": 0}
    assert svc.call("GET", "/api/feed/new?view=latest", cookie=cookie)[0] == 400
    assert svc.call("GET", "/api/feed/new?after=0", cookie=cookie)[0] == 400
    assert svc.call("GET", "/api/feed/new?view=latest&after=x", cookie=cookie)[0] == 400
    assert svc.call("GET", "/api/feed/new?view=latest&after=-1", cookie=cookie)[0] == 400
    assert svc.call("GET", f"/api/feed/new?view=latest&after={'9' * 20}", cookie=cookie)[0] == 400
    assert (
        svc.call("GET", "/api/feed/new?view=latest&since=2026-11-13T09:00:00Z", cookie=cookie)[0]
        == 400
    )


def test_save_and_follow_round_trip(svc: Live, cookie: str) -> None:
    assert svc.call("POST", "/api/stories/5/save", cookie=cookie)[2] == {"saved": True}
    assert [
        c["id"] for c in svc.call("GET", "/api/feed?view=saved", cookie=cookie)[2]["cards"]
    ] == [5]
    assert svc.call("DELETE", "/api/stories/5/save", cookie=cookie)[2] == {"saved": False}
    assert svc.call("POST", "/api/stories/9999/save", cookie=cookie)[0] == 404
    assert svc.call("POST", "/api/topics/1/follow", cookie=cookie)[2] == {"following": True}
    assert svc.call("GET", "/api/topics", cookie=cookie)[2][0]["following"] == 1
    assert svc.call("POST", "/api/topics/99/follow", cookie=cookie)[0] == 404
    assert svc.call("DELETE", "/api/topics/1/follow", cookie=cookie)[2] == {"following": False}
    topic = svc.call("GET", "/api/topics", cookie=cookie)[2][0]
    assert set(topic) == {"id", "name", "following", "stories"} and topic["following"] == 0


@pytest.mark.parametrize("ident", ["abc", "-1", "5.0", "1" * 19, "%D9%A5", "5%20", ""])
def test_ids_in_paths_are_ascii_digits_of_at_most_18(svc: Live, cookie: str, ident: str) -> None:
    assert svc.call("POST", f"/api/stories/{ident}/save", cookie=cookie)[0] == 404
    assert svc.call("POST", f"/api/topics/{ident}/follow", cookie=cookie)[0] == 404


def test_an_eighteen_digit_story_id_is_an_unknown_story(svc: Live, cookie: str) -> None:
    assert svc.call("POST", "/api/stories/" + "9" * 18 + "/save", cookie=cookie)[0] == 404


@pytest.mark.parametrize(
    "origin", [None, "http://evil.example", "https://127.0.0.1:{port}", "null"]
)
def test_a_write_from_another_origin_changes_nothing(
    svc: Live, cookie: str, origin: str | None
) -> None:
    assert svc.call("POST", "/api/stories/5/save", cookie=cookie, origin=origin)[0] == 403
    assert svc.call("POST", "/api/me", body={"name": "Eve"}, origin=origin)[0] == 403
    assert svc.call("GET", "/api/feed?view=saved", cookie=cookie)[2]["cards"] == []


def test_other_host_names_and_cross_site_reads_are_refused(svc: Live, cookie: str) -> None:
    assert svc.call("GET", "/", host="evil.example")[0] == 403
    assert (
        svc.call(
            "GET", "/api/feed?view=latest", cookie=cookie, headers={"Sec-Fetch-Site": "cross-site"}
        )[0]
        == 403
    )


def test_a_host_name_started_in_upper_case_is_reached_as_the_browser_spells_it(
    tmp_path: Path,
) -> None:
    build_feed_db(tmp_path).close()
    live = Live(make_server(tmp_path, "LocalHost", 0))
    try:
        assert live.call("GET", "/api/me", host=f"localhost:{live.port}")[0] == 200
        assert live.call("GET", "/api/me", host=f"LOCALHOST:{live.port}")[0] == 403
    finally:
        live.close()


def test_host_rules_and_fetch_metadata(svc: Live, cookie: str) -> None:
    assert svc.call("GET", "/api/me", host=f"localhost:{svc.port}")[0] == 200
    assert svc.call("GET", "/api/me", host="127.0.0.1")[0] == 403
    assert svc.call("GET", "/api/me", host=f"evil.example:{svc.port}")[0] == 403
    for site in ("same-origin", "none"):
        assert svc.call("GET", "/api/me", headers={"Sec-Fetch-Site": site})[0] == 200
    navigation = {
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Dest": "document",
    }
    # C3: no page is served, so the navigation passes the origin rule and finds no route (404);
    # the same request without the navigation headers is refused (403).
    assert svc.call("GET", "/", headers=navigation)[0] == 404
    assert svc.call("GET", "/", headers={"Sec-Fetch-Site": "cross-site"})[0] == 403
    assert svc.call("GET", "/api/me", headers=navigation)[0] == 200
    assert svc.call("POST", "/api/stories/5/save", cookie=cookie, headers=navigation)[0] == 403
    assert svc.call("GET", "/api/me", headers={"Origin": "http://evil.example"})[0] == 403


def test_search_text_cannot_break_the_api(svc: Live, cookie: str) -> None:
    for q in ['"', "*", "NEAR(", "%00", "a" * 5000]:
        assert (
            svc.call("GET", "/api/feed?view=latest&q=" + urllib.parse.quote(q), cookie=cookie)[0]
            == 200
        )


def test_unknown_paths_and_methods(svc: Live, cookie: str) -> None:
    assert svc.call("GET", "/api/nothing", cookie=cookie)[0] == 404
    assert svc.call("GET", "/nothing")[0] == 404
    assert svc.call("DELETE", "/api/me", cookie=cookie)[0] == 405
    assert svc.call("POST", "/api/feed?view=latest", cookie=cookie)[0] == 405
    assert svc.call("PUT", "/api/me", cookie=cookie)[0] == 405
    assert svc.call("POST", "/")[0] == 404  # C4: was 405 while "/" was the page
    assert svc.call("GET", "/api/stories/5/save", cookie=cookie)[0] == 405


def test_an_unexpected_failure_is_a_plain_500(
    svc: Live, cookie: str, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("secret-cause")

    monkeypatch.setattr(feedview, "feed", boom)
    status, _, data = svc.call("GET", "/api/feed?view=latest", cookie=cookie)
    assert (status, data) == (500, {"error": "the service failed; see its log"})
    assert "secret-cause" in caplog.text
