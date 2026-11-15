"""Signal's HTTP service, the group and thread reply values and body rules the other files leave
unpinned (S-9, part 6): whose unread counts are returned, booleans, a thread page's cursor, the
server's clock, the refusal texts of the body helpers, and optional fields.

The same team store and server as `test_signal_service_groups.py` (users ak and ml are writers, rd a
reader; group 1 "TMT" with thread 1, group 2 "Inner" with thread 2). Expected values are literals.
One server thread, one connection at a time, at most 40 requests in a test.
"""

from __future__ import annotations

import urllib.parse
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from service_support import AK_C, ML_C, RD_C, Site, team_site
from threads_support import AK, MIN, T0

from credit_os.signal.groups import Act
from credit_os.signal.store import open_db
from credit_os.signal.threads import start_note


@pytest.fixture
def world(tmp_path: Path) -> Iterator[Site]:
    live = team_site(tmp_path, seeded=True)
    yield live
    live.close()


def zeros(by_group: dict[str, int]) -> dict[str, Any]:
    return {"replies": 0, "threads": 0, "total": 0, "by_group": by_group}


def test_the_unread_counts_and_the_read_reply_are_the_askers_own(world: Site) -> None:
    call = world.call
    assert call("POST", "/api/groups/2/members", cookie=AK_C, body={"name": "ml"})[0] == 200
    assert call("POST", "/api/groups/2/threads", cookie=AK_C, body={"title": "N", "text": "x"})[
        2
    ] == {"thread_id": 3, "joined": False}
    reply = call("POST", "/api/threads/1/comments", cookie=ML_C, body={"text": "r", "parent": 1})
    assert reply[2] == {"id": 4}  # comment 3 is the note of the new thread
    # ak: one reply to its note; ml: two new threads (one in each group); rd: nothing, in no group.
    assert call("GET", "/api/unread", cookie=AK_C)[2] == {
        "replies": 1,
        "threads": 0,
        "total": 1,
        "by_group": {"1": 1},
    }
    assert call("GET", "/api/unread", cookie=ML_C)[2] == {
        "replies": 0,
        "threads": 2,
        "total": 2,
        "by_group": {"1": 1, "2": 1},
    }
    assert call("GET", "/api/unread", cookie=RD_C)[2] == zeros({})
    # Reading thread 1 answers the reader's own counts after the mark.
    read = call("POST", "/api/threads/1/read", cookie=ML_C, body={})
    assert read[2] == {"unread": {"replies": 0, "threads": 1, "total": 1, "by_group": {"2": 1}}}
    assert call("POST", "/api/threads/1/read", cookie=RD_C, body={})[2] == {"unread": zeros({})}
    assert call("POST", "/api/threads/1/read", cookie=AK_C, body={})[2] == {"unread": zeros({})}


def test_member_is_a_json_boolean_in_the_list_and_false_for_a_non_member_in_the_detail(
    world: Site,
) -> None:
    for cookie, expected in ((ML_C, True), (RD_C, False)):
        row = world.call("GET", "/api/groups", cookie=cookie)[2]["groups"][0]
        assert row["member"] is expected  # `0 == False` would pass an integer
        assert world.call("GET", "/api/groups/1", cookie=cookie)[2]["member"] is expected


def test_a_note_start_answers_joined_false_and_a_new_thread_id(world: Site) -> None:
    reply = world.call(
        "POST", "/api/groups/1/threads", cookie=AK_C, body={"title": "T", "text": "x"}
    )
    assert reply[::2] == (200, {"thread_id": 3, "joined": False})


def test_a_thread_page_of_more_than_thirty_has_a_cursor_and_the_next_page_the_rest(
    world: Site,
) -> None:
    db = open_db(world.root)
    for minute in range(2, 33):  # 31 notes, one minute apart after thread 1 (T0 + 1 minute)
        start_note(db, Act(AK, T0 + minute * MIN), 1, f"Note {minute}", "x")
    db.close()
    first = world.call("GET", "/api/groups/1/threads", cookie=ML_C)[2]
    assert [t["id"] for t in first["threads"]] == list(range(33, 3, -1))  # 30 threads, newest first
    assert first["next_before"] == "2026-11-13T09:03:00+00:00,4"
    cursor = urllib.parse.quote(first["next_before"], safe="")
    last = world.call("GET", f"/api/groups/1/threads?before={cursor}", cookie=ML_C)[2]
    assert [t["id"] for t in last["threads"]] == [3, 1] and last["next_before"] is None


def test_the_thread_view_is_read_with_the_servers_clock(world: Site) -> None:
    made = world.call("POST", "/api/threads/1/comments", cookie=AK_C, body={"text": "now"})
    assert made[2] == {"id": 3}
    comments = world.call("GET", "/api/threads/1", cookie=AK_C)[2]["comments"]
    # ak's note was written in 2026-11-13: past its 15-minute edit window; the new one is not.
    assert [(c["id"], c["mine"], c["editable"]) for c in comments] == [
        (1, True, False),
        (3, True, True),
    ]


# ---- the refusal texts of the body helpers, by literal ----

NOT_TEXT = "must be text"
ROWS = {
    "name-none": ("/api/groups", {"name": None, "visibility": "everyone"}, "name"),
    "name-bool": ("/api/groups", {"name": True, "visibility": "everyone"}, "name"),
    "name-list": ("/api/groups", {"name": ["x"], "visibility": "everyone"}, "name"),
    "name-int": ("/api/groups", {"name": 5, "visibility": "everyone"}, "name"),
    "name-gone": ("/api/groups", {"visibility": "everyone"}, "name"),
    "visibility-none": ("/api/groups", {"name": "N", "visibility": None}, "visibility"),
    "visibility-gone": ("/api/groups", {"name": "N"}, "visibility"),
    "member": ("/api/groups/1/members", {"name": None}, "name"),
    "title": ("/api/groups/1/threads", {"title": 5, "text": "x"}, "title"),
    "text": ("/api/groups/1/threads", {"title": "T", "text": None}, "text"),
    "note": ("/api/groups/1/threads", {"story_id": 1, "note": 5}, "note"),
    "comment": ("/api/threads/1/comments", {"text": None}, "text"),
    "comment-gone": ("/api/threads/1/comments", {}, "text"),
    "edit": ("/api/comments/1", {"text": 5}, "text"),
}


@pytest.mark.parametrize("row", list(ROWS))
def test_a_field_that_is_not_text_is_refused_by_name_before_the_store_sees_it(
    world: Site, row: str
) -> None:
    path, body, field = ROWS[row]
    status, _, reply = world.call("POST", path, cookie=AK_C, body=body)
    assert (status, reply) == (400, {"error": f"{field} {NOT_TEXT}"})


# The predecessor (aebec97) refuses `topics: ""` too: its `_ids` is the same `isinstance(list)` check,
# so an empty string is "not a list" there as here. Pinned as refused; behaviour unchanged.
@pytest.mark.parametrize(
    "topics", ["", "1", 5, {}, None], ids=["empty", "digit", "int", "dict", "null"]
)
def test_topics_must_be_a_list(world: Site, topics: object) -> None:
    body = {"name": "N", "visibility": "everyone", "topics": topics}
    status, _, reply = world.call("POST", "/api/groups", cookie=AK_C, body=body)
    assert (status, reply) == (400, {"error": "topics must be a list of whole numbers"})
    assert world.counts()["groups"] == 2


ONLY = [
    ("/api/groups", {"name": "N", "visibility": "everyone", "x": 1}),
    ("/api/groups/1/members", {"name": "rd", "x": 1}),
    ("/api/groups/1/threads", {"story_id": 2, "x": 1}),
    ("/api/groups/1/threads", {"title": "T", "text": "x", "x": 1}),
    ("/api/threads/1/read", {"x": 1}),
    ("/api/threads/1/comments", {"text": "x", "x": 1}),
    ("/api/comments/1", {"text": "x", "x": 1}),
]


@pytest.mark.parametrize("path,body", ONLY, ids=[f"o{n}" for n in range(len(ONLY))])
def test_a_field_the_route_does_not_take_has_one_fixed_refusal(
    world: Site, path: str, body: dict[str, Any]
) -> None:
    before = world.counts()
    status, _, reply = world.call("POST", path, cookie=AK_C, body=body)
    assert (status, reply) == (400, {"error": "the request has a field this route does not take"})
    assert world.counts() == before


@pytest.mark.parametrize(
    "body", [{}, {"title": "T"}, {"text": "x"}], ids=["empty", "title", "text"]
)
def test_a_thread_start_with_neither_a_story_nor_a_title_and_text_says_so(
    world: Site, body: dict[str, Any]
) -> None:
    status, _, reply = world.call("POST", "/api/groups/1/threads", cookie=AK_C, body=body)
    assert (status, reply) == (
        400,
        {"error": "send either story_id (with note) or title and text"},
    )


def test_null_note_and_null_parent_are_absent_and_no_topics_is_an_empty_list(world: Site) -> None:
    share = world.call(
        "POST", "/api/groups/1/threads", cookie=AK_C, body={"story_id": 2, "note": None}
    )
    assert share[::2] == (200, {"thread_id": 3, "joined": False})
    top = world.call(
        "POST", "/api/threads/1/comments", cookie=ML_C, body={"text": "t", "parent": None}
    )
    assert top[::2] == (200, {"id": 3})
    comments = world.call("GET", "/api/threads/1", cookie=ML_C)[2]["comments"]
    assert [(c["id"], c["parent_id"]) for c in comments] == [(1, None), (3, None)]
    group = world.call(
        "POST", "/api/groups", cookie=AK_C, body={"name": "Other", "visibility": "everyone"}
    )
    assert group[::2] == (200, {"id": 3})
