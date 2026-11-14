"""Signal's HTTP service, group, thread, comment, reaction and unread routes.

Run for real on one loopback port (port 0) over a team store: users ak and ml are writers, rd a
reader, zz no one the store knows. Expected values are written here by hand. Nothing here reaches
beyond 127.0.0.1; at most one server thread is alive at once.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from service_support import (
    AK_C,
    ML_C,
    NEW_GROUP,
    RD_C,
    WRITES,
    ZZ_C,
    Row,
    Site,
    pass_in_progress,
    team,
    team_site,
)
from threads_support import T0

from credit_os.signal import groups, service, store
from credit_os.signal.service import Loop, make_server
from credit_os.signal.store import open_db
from credit_os.signal.threads import auto_post


@pytest.fixture
def site(tmp_path: Path) -> Iterator[Site]:
    live = team_site(tmp_path, seeded=False)
    yield live
    live.close()


@pytest.fixture
def world(tmp_path: Path) -> Iterator[Site]:
    live = team_site(tmp_path, seeded=True)
    yield live
    live.close()


@pytest.fixture
def world_loop(tmp_path: Path) -> Iterator[tuple[Loop, Site]]:
    team(tmp_path, seeded=True)
    loop = Loop(tmp_path)
    live = Site(make_server(tmp_path, "127.0.0.1", 0, loop=loop), tmp_path)
    yield loop, live
    live.close()


# Open to readers (status 200): a person joining or leaving an everyone-group themself, and the
# read route. Every other write is refused to a reader with 403 ...
OPEN_TO_READERS: list[Row] = [
    ("POST", "/api/groups/1/members", {}),
    ("DELETE", "/api/groups/1/members", {}),
    ("POST", "/api/threads/1/read", {}),
]
# ... except a reaction, which a registered reader (rd) may make and an unregistered name (zz) may
# not (R22, R54).
REACTIONS: list[Row] = [
    ("POST", "/api/comments/1/reactions/agree", None),
    ("DELETE", "/api/comments/1/reactions/agree", None),
]

# The invited group's ids in the world are group 2, thread 2, comment 2; 999999 is missing.
HIDDEN_READS: list[Row] = [
    ("GET", "/api/groups/{g}", None),
    ("GET", "/api/groups/{g}/threads", None),
    ("GET", "/api/threads/{t}", None),
]
HIDDEN_WRITES: list[Row] = [
    ("POST", "/api/groups/{g}/members", {}),
    ("POST", "/api/groups/{g}/members", {"name": "ml"}),
    ("DELETE", "/api/groups/{g}/members", {}),
    ("DELETE", "/api/groups/{g}/members", {"name": "ak"}),
    ("POST", "/api/groups/{g}/threads", {"story_id": 1}),
    ("POST", "/api/groups/{g}/threads", {"title": "T", "text": "x"}),
    ("POST", "/api/threads/{t}/read", {}),
    ("POST", "/api/threads/{t}/comments", {"text": "x"}),
    ("POST", "/api/comments/{c}", {"text": "x"}),
    ("DELETE", "/api/comments/{c}", None),
    ("POST", "/api/comments/{c}/reactions/agree", None),
    ("DELETE", "/api/comments/{c}/reactions/agree", None),
]


def test_the_reaction_key_pattern_is_twelve_lowercase_letters(world: Site) -> None:
    assert service._KEY == "([a-z]{1,12})"
    for key in ("a" * 13, "Agree", "ag1ee", "agree%20"):  # no route: 404, not a refused key
        assert world.call("POST", f"/api/comments/1/reactions/{key}", cookie=AK_C)[0] == 404
    status, _, reply = world.call("POST", f"/api/comments/1/reactions/{'a' * 12}", cookie=AK_C)
    assert (status, reply) == (
        400,
        {"error": "invalid reaction; expected one of agree, disagree, seen"},
    )
    assert world.counts()["reactions"] == 0


def test_a_writer_creates_a_group_shares_a_story_and_a_reader_reads_the_thread_with_recorded_feed(
    site: Site,
) -> None:
    status, _, made = site.call(
        "POST", "/api/groups", cookie=AK_C, body=NEW_GROUP | {"name": "TMT"}
    )
    assert (status, made) == (200, {"id": 1})
    status, _, shared = site.call(
        "POST", "/api/groups/1/threads", cookie=AK_C, body={"story_id": 1, "note": "look"}
    )
    assert (status, shared) == (200, {"thread_id": 1, "joined": False})
    status, _, thread = site.call("GET", "/api/threads/1", cookie=RD_C)
    assert status == 200
    assert thread["comments"][0]["text"] == "look"
    assert thread["can_post"] is False
    status, _, rows = site.call("GET", "/api/groups/1/threads", cookie=RD_C)
    assert status == 200 and rows["threads"][0]["source_kind"] == "regulator"
    status, _, page = site.call("GET", "/api/feed?view=latest", cookie=RD_C)
    card = next(c for c in page["cards"] if c["id"] == 1)
    expected = {"id": 1, "group": "TMT", "comments": 1, "shared_by": "ak", "note": "look"}
    assert status == 200 and card["threads"] == [expected]


def test_a_share_onto_a_topics_automatic_thread_is_attributed_over_http(site: Site) -> None:
    db = open_db(site.root)
    db.execute(
        "INSERT INTO topics(name, keywords, kinds, created_by, created_at)"
        " VALUES('x', '[]', '[]', 'ak', 'now')"
    )
    db.commit()
    db.close()
    body = NEW_GROUP | {"name": "TMT", "topics": [1]}
    assert site.call("POST", "/api/groups", cookie=AK_C, body=body)[:1] == (200,)
    assert site.call("POST", "/api/groups/1/members", cookie=ML_C, body={})[0] == 200
    db = open_db(site.root)
    assert auto_post(db, 1, [1], T0 + timedelta(minutes=1)) == [1]
    db.close()
    status, _, shared = site.call(
        "POST", "/api/groups/1/threads", cookie=AK_C, body={"story_id": 1, "note": "look"}
    )
    assert (status, shared) == (200, {"thread_id": 1, "joined": True})
    _, _, page = site.call("GET", "/api/feed?view=latest", cookie=ML_C)
    card = next(c for c in page["cards"] if c["id"] == 1)
    expected = {"id": 1, "group": "TMT", "comments": 1, "shared_by": "ak", "note": "look"}
    assert card["threads"] == [expected]
    _, _, only = site.call("GET", "/api/feed?view=latest&shared=1", cookie=ML_C)
    assert [c["id"] for c in only["cards"]] == [1]


REFUSED = [row for row in WRITES if row not in OPEN_TO_READERS + REACTIONS]
WHO = [RD_C, ZZ_C]  # rd is a reader; zz is no one the store knows, so a reader too


@pytest.mark.parametrize("method,path,body", REFUSED)
def test_a_reader_is_refused_every_write_that_is_not_theirs_and_nothing_changes(
    world: Site, method: str, path: str, body: dict[str, Any] | None
) -> None:
    for who in WHO:
        before = world.counts()
        status, _, reply = world.call(method, path, cookie=who, body=body)
        assert status == 403 and list(reply) == ["error"], reply
        assert world.counts() == before


@pytest.mark.parametrize("method,path,body", OPEN_TO_READERS)
def test_a_reader_may_join_leave_and_mark_read_and_only_those_rows_change(
    world: Site, method: str, path: str, body: dict[str, Any] | None
) -> None:
    for who in WHO:
        before = world.counts()
        status, _, reply = world.call(method, path, cookie=who, body=body)
        assert status == 200, reply
        moves = ("group_members", "read_marks")
        after = world.counts()
        assert {t: n for t, n in after.items() if t not in moves} == {
            t: n for t, n in before.items() if t not in moves
        }


@pytest.mark.parametrize("method,path,body", REACTIONS)
def test_a_registered_reader_may_react_and_an_unregistered_name_may_not(
    world: Site, method: str, path: str, body: dict[str, Any] | None
) -> None:
    before = world.counts()
    status, _, reply = world.call(method, path, cookie=ZZ_C, body=body)
    assert status == 403 and list(reply) == ["error"], reply
    assert world.counts() == before
    status, _, reply = world.call(method, path, cookie=RD_C, body=body)
    assert status == 200, reply
    after = world.counts()
    assert {t: n for t, n in after.items() if t != "reactions"} == {
        t: n for t, n in before.items() if t != "reactions"
    }


@pytest.mark.parametrize("method,path,body", WRITES)
def test_every_write_without_this_sites_origin_is_refused(
    world: Site, method: str, path: str, body: dict[str, Any] | None
) -> None:
    before = world.counts()
    status, _, _ = world.call(
        method, path, cookie=AK_C, body=body, origin="http://elsewhere.test:{port}"
    )
    assert status == 403
    assert world.counts() == before


@pytest.mark.parametrize("method,path,body", HIDDEN_READS + HIDDEN_WRITES)
def test_a_hidden_group_answers_exactly_like_a_missing_one(
    world: Site, method: str, path: str, body: dict[str, Any] | None
) -> None:
    before = world.counts()
    hidden = path.format(g=2, t=2, c=2)
    missing = path.format(g=999999, t=999999, c=999999)
    seen = world.call(method, hidden, cookie=ML_C, body=body)
    gone = world.call(method, missing, cookie=ML_C, body=body)
    assert seen[0] == 404
    assert (seen[0], seen[2]) == (gone[0], gone[2])
    assert world.counts() == before


def test_a_hidden_group_is_absent_from_lists_counts_and_cards(world: Site) -> None:
    listed = world.call("GET", "/api/groups", cookie=ML_C)[2]
    assert [g["id"] for g in listed["groups"]] == [1]
    unread = world.call("GET", "/api/unread", cookie=ML_C)[2]
    assert set(unread["by_group"]) <= {"1"}
    everything = json.dumps(
        [listed, unread, world.call("GET", "/api/feed?view=latest", cookie=ML_C)[2]]
    )
    assert "Inner" not in everything and "secret note" not in everything
    cards = world.call("GET", "/api/feed?view=latest", cookie=ML_C)[2]["cards"]
    assert next(c for c in cards if c["id"] == 2)["threads"] == []
    own = world.call("GET", "/api/feed?view=latest", cookie=AK_C)[2]["cards"]
    assert [t["group"] for t in next(c for c in own if c["id"] == 2)["threads"]] == ["Inner"]


@pytest.mark.parametrize(
    "body",
    [
        b"[]",
        b'{"text": 5}',
        b'{"text": ""}',
        b'{"parent": "1", "text": "x"}',
        b'{"text": "' + b"x" * 4001 + b'"}',
    ],
    ids=["list", "number", "empty", "parent", "long"],
)
def test_a_malformed_comment_is_a_400_not_a_500(world: Site, body: bytes) -> None:
    before = world.counts()
    status, _, reply = world.call("POST", "/api/threads/1/comments", cookie=AK_C, raw=body)
    assert status == 400 and list(reply) == ["error"]
    assert world.counts() == before


@pytest.mark.parametrize(
    "path,body",
    [
        ("/api/groups/1/threads", {"story_id": True}),
        ("/api/groups/1/threads", {"story_id": 1.0}),
        ("/api/groups/1/threads", {"story_id": "1"}),
        ("/api/groups/1/threads", {"story_id": 1, "note": 5}),
        ("/api/groups/1/threads", {"story_id": 1, "title": "T", "text": "x"}),
        ("/api/groups/1/threads", {}),
        ("/api/groups/1/threads", {"title": "T"}),
        ("/api/groups/1/threads", {"story_id": 1, "extra": 1}),
        ("/api/groups", {"name": "N", "visibility": "everyone", "topics": [True]}),
        ("/api/groups", {"name": "N", "visibility": "everyone", "topics": "1"}),
        ("/api/groups", {"name": 5, "visibility": "everyone"}),
        ("/api/groups", {"name": "N", "visibility": None}),
        ("/api/groups", {"name": "N", "visibility": "everyone", "topics": [999]}),
        ("/api/threads/1/comments", {"text": "x", "parent": True}),
        ("/api/threads/1/comments", {"text": "x", "parent": 1.0}),
        ("/api/groups/1/members", {"name": 5}),
        ("/api/comments/1", {"text": None}),
    ],
    ids=[f"row{n}" for n in range(17)],
)
def test_wrong_types_and_shapes_are_a_400_never_a_500(
    world: Site, path: str, body: dict[str, Any]
) -> None:
    before = world.counts()
    status, _, reply = world.call("POST", path, cookie=AK_C, body=body)
    assert status == 400 and list(reply) == ["error"], reply
    assert world.counts() == before


def test_a_comment_posted_during_an_ingest_pass_succeeds_with_recorded_feed(
    world_loop: tuple[Loop, Site],
) -> None:
    loop, site = world_loop  # the loop's fetch function blocks on an Event mid-pass
    with pass_in_progress(loop):
        status, _, made = site.call(
            "POST", "/api/threads/1/comments", cookie=AK_C, body={"text": "during"}
        )
        assert status == 200 and "id" in made
    assert loop.last_error is None


def test_unread_rides_the_poll_and_clears_on_read(world: Site) -> None:
    unread = world.call("GET", "/api/unread", cookie=ML_C)[2]
    assert unread == {"replies": 0, "threads": 1, "total": 1, "by_group": {"1": 1}}
    assert world.call("GET", "/api/groups", cookie=ML_C)[2]["groups"][0]["unread"] == 1
    status, _, read = world.call("POST", "/api/threads/1/read", cookie=ML_C, body={})
    assert status == 200 and read["unread"]["total"] == 0
    assert world.call("GET", "/api/groups", cookie=ML_C)[2]["groups"][0]["unread"] == 0


def test_reading_a_thread_does_not_record_it_as_read(world: Site) -> None:
    world.call("GET", "/api/threads/1", cookie=ML_C)
    assert world.call("GET", "/api/unread", cookie=ML_C)[2]["total"] == 1


def test_group_list_and_detail_carry_what_the_page_needs(world: Site) -> None:
    listed = world.call("GET", "/api/groups", cookie=RD_C)[2]
    assert listed["can_create"] is False
    assert listed["groups"] == [
        {
            "id": 1,
            "name": "TMT",
            "visibility": "everyone",
            "member": False,
            "members": 2,
            "threads": 1,
            "unread": 0,
        }
    ]
    assert world.call("GET", "/api/groups", cookie=AK_C)[2]["can_create"] is True
    detail = world.call("GET", "/api/groups/1", cookie=ML_C)[2]
    assert detail == {
        "id": 1,
        "name": "TMT",
        "visibility": "everyone",
        "member": True,
        "can_manage": True,
        "members": ["ak", "ml"],
    }
    assert world.call("GET", "/api/groups/1", cookie=RD_C)[2]["can_manage"] is False


def test_members_are_joined_added_and_removed_and_the_reply_is_the_list(world: Site) -> None:
    assert world.call("POST", "/api/groups/1/members", cookie=RD_C, body={})[2] == {
        "members": ["ak", "ml", "rd"]
    }
    assert world.call("DELETE", "/api/groups/1/members", cookie=RD_C, body={})[2] == {
        "members": ["ak", "ml"]
    }
    assert world.call("POST", "/api/groups/2/members", cookie=AK_C, body={"name": "ml"})[2] == {
        "members": ["ak", "ml"]
    }
    assert world.call("DELETE", "/api/groups/2/members", cookie=AK_C, body={"name": "ml"})[2] == {
        "members": ["ak"]
    }
    status, _, refused = world.call("DELETE", "/api/groups/2/members", cookie=AK_C, body={})
    assert status == 400 and "writer" in refused["error"]  # the last writer cannot leave


def test_threads_page_comments_and_reactions_round_trip(world: Site) -> None:
    rows = world.call("GET", "/api/groups/1/threads", cookie=ML_C)[2]
    assert rows["next_before"] is None and [r["id"] for r in rows["threads"]] == [1]
    assert world.call("GET", "/api/groups/1/threads?before=bad", cookie=ML_C)[0] == 400
    made = world.call(
        "POST", "/api/threads/1/comments", cookie=ML_C, body={"text": "a", "parent": 1}
    )
    assert made[2] == {"id": 2 + 1}  # comments 1 and 2 exist already (thread 2's note is 2)
    assert world.call("POST", "/api/comments/3/reactions/seen", cookie=AK_C)[2] == {}
    assert world.call("POST", "/api/comments/3/reactions/nope", cookie=AK_C)[0] == 400
    thread = world.call("GET", "/api/threads/1", cookie=AK_C)[2]
    reactions = thread["comments"][1]["reactions"]
    assert reactions == [{"key": "seen", "count": 1, "mine": True}]
    assert world.call("POST", "/api/comments/3", cookie=ML_C, body={"text": "b"})[2] == {}
    assert world.call("DELETE", "/api/comments/3", cookie=ML_C)[2] == {}
    assert world.call("GET", "/api/threads/1", cookie=AK_C)[2]["comments"][1]["removed"] is True


def test_feed_shared_accepts_only_one(world: Site) -> None:
    shared = world.call("GET", "/api/feed?view=latest&shared=1", cookie=ML_C)[2]["cards"]
    assert [c["id"] for c in shared] == [1]  # ak shared story 1 into ml's group
    assert world.call("GET", "/api/feed?view=latest&shared=1", cookie=AK_C)[2]["cards"] == []
    for value in ("0", "true", "", "2"):
        assert world.call("GET", f"/api/feed?view=latest&shared={value}", cookie=ML_C)[0] == 400


SURROGATE_ROUTES = [
    ("POST", "/api/groups"),
    ("POST", "/api/groups/1/members"),
    ("DELETE", "/api/groups/1/members"),
    ("POST", "/api/groups/1/threads"),
    ("POST", "/api/threads/1/comments"),
    ("POST", "/api/comments/1"),
    ("POST", "/api/threads/1/read"),
]


@pytest.mark.parametrize("method,path", SURROGATE_ROUTES)
def test_a_field_name_that_is_a_lone_surrogate_is_an_ordinary_400(
    world: Site, method: str, path: str
) -> None:
    before = world.counts()
    status, _, reply = world.call(method, path, cookie=ZZ_C, raw=b'{"\\ud800": 1}')
    assert status == 400 and list(reply) == ["error"]
    assert "\ud800" not in json.dumps(reply, ensure_ascii=False)  # no client text in a refusal
    assert world.call("GET", "/api/groups", cookie=AK_C)[0] == 200
    assert world.counts() == before


def test_a_refusal_that_cannot_be_encoded_is_the_documented_500_and_is_logged(
    world: Site, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def echo(*args: object, **kwargs: object) -> None:
        raise store.StoreError("\ud800 is not a thing")  # a store text echoing input

    monkeypatch.setattr(groups, "list_groups", echo)
    with caplog.at_level(logging.ERROR, logger=service.log.name):
        status, _, reply = world.call("GET", "/api/groups", cookie=AK_C)
    assert (status, reply) == (500, {"error": "the service failed; see its log"})
    assert any(r.exc_info for r in caplog.records)
    monkeypatch.undo()
    assert world.call("GET", "/api/groups", cookie=AK_C)[0] == 200


@pytest.mark.parametrize(
    "raw", [b"[]", b'{"a": 1}', b'{"text": "x"}', b"5"], ids=["list", "field", "text", "number"]
)
def test_the_read_route_needs_an_empty_json_object(world: Site, raw: bytes) -> None:
    before = world.counts()
    status, _, reply = world.call("POST", "/api/threads/1/read", cookie=ML_C, raw=raw)
    assert status == 400 and list(reply) == ["error"]
    assert world.counts() == before
    assert world.call("POST", "/api/threads/1/read", cookie=ML_C, raw=b"{}")[0] == 200


def test_leaving_an_invited_group_as_a_non_last_member_hides_it_from_the_leaver(
    world: Site,
) -> None:
    world.call("POST", "/api/groups/2/members", cookie=AK_C, body={"name": "ml"})
    status, _, reply = world.call("DELETE", "/api/groups/2/members", cookie=ML_C, body={})
    assert (status, reply) == (200, {"members": []})
    db = open_db(world.root)
    try:
        gone = db.execute("SELECT 1 FROM group_members WHERE group_id=2 AND user_name='ml'")
        assert gone.fetchone() is None
    finally:
        db.close()
    assert world.call("GET", "/api/groups/2", cookie=ML_C)[0] == 404


@pytest.mark.parametrize("method,path,body", WRITES)
def test_every_write_with_no_origin_header_is_refused(
    world: Site, method: str, path: str, body: dict[str, Any] | None
) -> None:
    before = world.counts()
    status, _, _ = world.call(method, path, cookie=AK_C, body=body, origin=None)
    assert status == 403
    assert world.counts() == before


def test_one_story_card_is_the_feed_card_with_only_the_threads_the_user_can_see(
    world: Site,
) -> None:
    status, _, page = world.call("GET", "/api/feed?view=latest", cookie=ML_C)
    from_feed = {c["id"]: c for c in page["cards"]}
    status, _, card = world.call("GET", "/api/stories/1", cookie=ML_C)
    assert status == 200 and card == from_feed[1]
    assert [t["group"] for t in card["threads"]] == ["TMT"]
    # Story 2 is shared only to the invited group "Inner": ml is no member, ak is.
    assert world.call("GET", "/api/stories/2", cookie=ML_C)[2]["threads"] == []
    assert [t["group"] for t in world.call("GET", "/api/stories/2", cookie=AK_C)[2]["threads"]] == [
        "Inner"
    ]


def test_a_missing_story_card_is_a_404_and_a_story_needs_a_name(world: Site) -> None:
    assert world.call("GET", "/api/stories/999999", cookie=ML_C)[0] == 404
    assert world.call("GET", "/api/stories/1")[0] == 401


@pytest.mark.parametrize("ident", ["abc", "-1", "5.0", "1" * 19, "%D9%A5", "5%20"])
def test_story_card_ids_follow_the_path_id_rule(world: Site, ident: str) -> None:
    assert world.call("GET", f"/api/stories/{ident}", cookie=ML_C)[0] == 404
