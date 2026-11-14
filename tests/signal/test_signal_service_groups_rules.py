"""Signal's HTTP service, group and thread rules (R21, R22, R23, R35, R36, R54, R55, P1).

The same team store as `test_signal_service_groups.py`: users ak and ml are writers, rd a reader,
zz no one the store knows; group 1 "TMT" (everyone; thread 1, comment 1) and group 2 "Inner"
(invited, ak alone; thread 2, comment 2) are ids; 999999 is missing. Expected values are literals.
At most one server thread is alive; a busy database is a second connection holding the write lock
with `store._BUSY_SECONDS` patched to 0.2; nothing here opens sockets or threads in a loop.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from service_support import Site, team

from credit_os.signal import store
from credit_os.signal.service import make_server
from credit_os.signal.store import open_db


@pytest.fixture
def world(tmp_path: Path) -> Iterator[Site]:
    team(tmp_path, seeded=True)
    live = Site(make_server(tmp_path, "127.0.0.1", 0), tmp_path)
    yield live
    live.close()


@pytest.fixture
def site(tmp_path: Path) -> Iterator[Site]:
    team(tmp_path, seeded=False)
    live = Site(make_server(tmp_path, "127.0.0.1", 0), tmp_path)
    yield live
    live.close()


AK_C, ML_C, RD_C, ZZ_C = (f"signal_name={n}" for n in ("ak", "ml", "rd", "zz"))
COOKIE = {"ak": AK_C, "ml": ML_C, "rd": RD_C, "zz": ZZ_C}
NEW_GROUP = {"name": "New", "visibility": "everyone", "topics": []}
TOO_LONG = "x" * 4001
FAILED = {"error": "the service failed; see its log"}
BUSY = {"error": "the store is busy; try again"}
IDS = {"hidden": {"g": 2, "t": 2, "c": 2}, "missing": {"g": 999999, "t": 999999, "c": 999999}}
Row = tuple[str, str, dict[str, Any] | None]

# Every write of the groups and threads routes, on visible group 1, thread 1, comment 1.
WRITES: list[Row] = [
    ("POST", "/api/groups", NEW_GROUP),
    ("POST", "/api/groups/1/members", {}),
    ("POST", "/api/groups/1/members", {"name": "rd"}),
    ("DELETE", "/api/groups/1/members", {}),
    ("DELETE", "/api/groups/1/members", {"name": "ak"}),
    ("POST", "/api/groups/1/threads", {"story_id": 2, "note": "n"}),
    ("POST", "/api/groups/1/threads", {"title": "T", "text": "x"}),
    ("POST", "/api/threads/1/read", {}),
    ("POST", "/api/threads/1/comments", {"text": "hi"}),
    ("POST", "/api/comments/1", {"text": "changed"}),
    ("DELETE", "/api/comments/1", None),
    ("POST", "/api/comments/1/reactions/agree", None),
    ("DELETE", "/api/comments/1/reactions/agree", None),
]

_DUMPS = {
    "groups": "SELECT * FROM groups ORDER BY id",
    "group_members": "SELECT * FROM group_members ORDER BY group_id, user_name",
    "threads": "SELECT * FROM threads ORDER BY id",
    "comments": "SELECT * FROM comments ORDER BY id",
    "reactions": "SELECT * FROM reactions ORDER BY comment_id, user_name, key",
    "read_marks": "SELECT * FROM read_marks ORDER BY user_name, thread_id",
}


def dump(root: Path) -> dict[str, list[tuple[Any, ...]]]:
    """Every row of every table the group and thread routes write."""
    db = open_db(root)
    try:
        return {n: [tuple(r) for r in db.execute(sql).fetchall()] for n, sql in _DUMPS.items()}
    finally:
        db.close()


def path_of(template: str, kind: str) -> str:
    return template.format(**IDS[kind])


# ---- N15 (R55): a bad text is 400 before 404 or 403 ----

TEXT_ROWS = {
    "long-note": ("POST", "/api/groups/{g}/threads", {"title": "T", "text": TOO_LONG}, "long"),
    "empty-note": ("POST", "/api/groups/{g}/threads", {"title": "T", "text": ""}, "empty"),
    "long-title": ("POST", "/api/groups/{g}/threads", {"title": "T" * 121, "text": "x"}, "title"),
    "empty-title": ("POST", "/api/groups/{g}/threads", {"title": "", "text": "x"}, "empty"),
    "long-share": ("POST", "/api/groups/{g}/threads", {"story_id": 1, "note": TOO_LONG}, "long"),
    "long-comment": ("POST", "/api/threads/{t}/comments", {"text": TOO_LONG}, "long"),
    "empty-comment": ("POST", "/api/threads/{t}/comments", {"text": ""}, "empty"),
    "long-edit": ("POST", "/api/comments/{c}", {"text": TOO_LONG}, "long"),
    "empty-edit": ("POST", "/api/comments/{c}", {"text": ""}, "empty"),
}
TEXT_ERROR = {
    "long": {"error": "text is longer than 4000 characters"},
    "title": {"error": "text is longer than 120 characters"},
    "empty": {"error": "text is empty"},
}


@pytest.mark.parametrize("name", list(TEXT_ROWS))
def test_a_bad_text_to_a_hidden_or_a_missing_target_is_the_same_400_and_changes_nothing(
    world: Site, name: str
) -> None:
    method, template, body, kind = TEXT_ROWS[name]
    before = dump(world.root)
    answers = [
        world.call(method, path_of(template, target), cookie=ML_C, body=body)[::2]
        for target in ("hidden", "missing")
    ]
    assert answers == [(400, TEXT_ERROR[kind])] * 2
    assert dump(world.root) == before


@pytest.mark.parametrize(
    "template,body,expected",
    [
        ("/api/groups/{g}/threads", {"story_id": 1, "note": "n"}, "no such group"),
        ("/api/groups/{g}/threads", {"title": "T", "text": "x"}, "no such group"),
        ("/api/threads/{t}/comments", {"text": "x"}, "no such thread"),
        ("/api/comments/{c}", {"text": "x"}, "no such comment"),
    ],
    ids=["share", "note", "comment", "edit"],
)
def test_the_same_requests_with_a_good_text_are_404(
    world: Site, template: str, body: dict[str, Any], expected: str
) -> None:
    for target in ("hidden", "missing"):
        status, _, reply = world.call("POST", path_of(template, target), cookie=ML_C, body=body)
        assert (status, reply) == (404, {"error": expected})
    assert world.counts()["comments"] == 2


@pytest.mark.parametrize("name", ["long-note", "long-comment", "long-edit"])
def test_a_bad_text_from_someone_who_may_not_write_is_400_not_403(world: Site, name: str) -> None:
    method, template, body, _ = TEXT_ROWS[name]
    before = dump(world.root)
    path = template.format(g=1, t=1, c=1)
    for who in (RD_C, ZZ_C):  # a reader; no one: a good text would be 403
        status, _, reply = world.call(method, path, cookie=who, body=body)
        assert (status, reply) == (400, TEXT_ERROR["long"])
    assert dump(world.root) == before


def test_a_bad_edit_by_a_writer_who_is_not_the_author_is_400_not_403(world: Site) -> None:
    before = dump(world.root)
    body = {"text": TOO_LONG}
    status, _, reply = world.call("POST", "/api/comments/1", cookie=ML_C, body=body)
    assert (status, reply) == (400, TEXT_ERROR["long"])  # a good text would be 403
    assert dump(world.root) == before


# ---- N16 (R21, R22, R54): role x key x target ----

KEYS = ("agree", "disagree", "seen", "up", "nope")
BAD_KEY = {"error": "invalid reaction; expected one of agree, disagree, seen"}
ANSWER = {
    "ok": (200, {}),
    "key": (400, BAD_KEY),
    "gone": (400, {"error": "that comment was removed"}),
    "reg": (403, {"error": "only registered users can react"}),
    "none": (404, {"error": "no such comment"}),
}
# The order of the checks: visible, then registered, then the key, then a removed comment.
EXPECTED = {
    ("ml", "live"): ("ok", "ok", "ok", "key", "key"),
    ("rd", "live"): ("ok", "ok", "ok", "key", "key"),
    ("zz", "live"): ("reg",) * 5,
    ("ml", "removed"): ("gone", "gone", "gone", "key", "key"),
    ("rd", "removed"): ("gone", "gone", "gone", "key", "key"),
    ("zz", "removed"): ("reg",) * 5,
    ("ml", "hidden"): ("none",) * 5,
    ("rd", "hidden"): ("none",) * 5,
    ("zz", "hidden"): ("none",) * 5,
    ("ml", "missing"): ("none",) * 5,
    ("rd", "missing"): ("none",) * 5,
    ("zz", "missing"): ("none",) * 5,
}
COMMENT_OF = {"live": 1, "removed": 3, "hidden": 2, "missing": 999999}


@pytest.mark.parametrize("role,target", list(EXPECTED), ids=["-".join(k) for k in EXPECTED])
def test_reactions_by_role_key_and_target(world: Site, role: str, target: str) -> None:
    assert world.call("POST", "/api/threads/1/comments", cookie=AK_C, body={"text": "gone"})[2] == {
        "id": 3
    }
    assert world.call("DELETE", "/api/comments/3", cookie=AK_C)[:1] == (200,)
    wrote = role in ("ml", "rd") and target == "live"
    for method, delta in (("POST", 3 if wrote else 0), ("DELETE", -3 if wrote else 0)):
        before = world.counts()["reactions"]
        for key, code in zip(KEYS, EXPECTED[(role, target)], strict=True):
            path = f"/api/comments/{COMMENT_OF[target]}/reactions/{key}"
            status, _, reply = world.call(method, path, cookie=COOKIE[role])
            assert (status, reply) == ANSWER[code], (method, key)
        assert world.counts()["reactions"] - before == delta


# ---- N17 (P1): a field named twice ----

DUPLICATES = {
    "comment": ("/api/threads/1/comments", b'{"text": 5, "text": "second wins"}'),
    "group": (
        "/api/groups",
        b'{"name": "A", "name": "B", "visibility": "everyone", "topics": []}',
    ),
    "member": ("/api/groups/1/members", b'{"name": "rd", "name": "ml"}'),
    "note": ("/api/groups/1/threads", b'{"title": "T", "text": "x", "text": "y"}'),
}


@pytest.mark.parametrize("name", list(DUPLICATES))
def test_a_body_that_names_a_field_twice_is_400_and_changes_nothing(world: Site, name: str) -> None:
    path, raw = DUPLICATES[name]
    before = dump(world.root)
    status, _, reply = world.call("POST", path, cookie=AK_C, raw=raw)
    assert (status, reply) == (400, {"error": "the request body names a field twice"})
    assert dump(world.root) == before


# ---- N18: no field, query or path names who acts ----

SPOOF = [{}, {"name": "ml"}, {"user": "ml"}, {"user_name": "ml"}, {"author": "ml"}, {"by": "ml"}]


def naming_others(rows: dict[str, list[tuple[Any, ...]]]) -> dict[str, list[tuple[Any, ...]]]:
    return {t: [r for r in found if "ml" in r or "rd" in r] for t, found in rows.items()}


def test_no_row_names_anyone_but_the_cookies_user(site: Site) -> None:
    call = site.call
    assert call("POST", "/api/groups", cookie=AK_C, body=NEW_GROUP | {"name": "TMT"})[2] == {
        "id": 1
    }
    assert call("POST", "/api/groups/1/members", cookie=ML_C, body={})[0] == 200
    shared = call("POST", "/api/groups/1/threads", cookie=AK_C, body={"story_id": 1, "note": "a"})
    assert shared[2] == {"thread_id": 1, "joined": False}
    reply = call("POST", "/api/threads/1/comments", cookie=ML_C, body={"text": "b", "parent": 1})
    assert reply[2] == {"id": 2}
    assert call("POST", "/api/comments/1/reactions/agree", cookie=ML_C)[0] == 200  # ml's
    assert call("POST", "/api/comments/2/reactions/seen", cookie=AK_C)[0] == 200  # ak's
    start = dump(site.root)
    for extra in SPOOF:
        for query in ("", "?name=ml", "?user=ml"):
            call("POST", f"/api/threads/1/read{query}", cookie=AK_C, body=extra)
            call("POST", f"/api/threads/1/comments{query}", cookie=AK_C, body={"text": "c"} | extra)
            call("POST", f"/api/comments/2{query}", cookie=AK_C, body={"text": "edit"} | extra)
            call("DELETE", f"/api/comments/2{query}", cookie=AK_C, body=extra or None)
            call(
                "DELETE", f"/api/comments/1/reactions/agree{query}", cookie=AK_C, body=extra or None
            )
            call(
                "POST",
                f"/api/comments/2/reactions/disagree{query}",
                cookie=AK_C,
                body=extra or None,
            )
            note = {"title": "T", "text": "x"} | extra
            call("POST", f"/api/groups/1/threads{query}", cookie=AK_C, body=note)
    for body in ({"name": "rd"}, {"name": "ml"}):  # a reader names no one, itself included
        for method in ("POST", "DELETE"):
            reply = call(method, "/api/groups/1/members", cookie=RD_C, body=body)
            assert reply[0] == 403
    end = dump(site.root)
    assert naming_others(end) == naming_others(start)
    assert [r[3] for r in end["comments"][len(start["comments"]) :]] == ["ak"] * 6  # 3 + 3 notes
    assert [r[4] for r in end["threads"][len(start["threads"]) :]] == ["ak"] * 3
    assert set(end["reactions"]) - set(start["reactions"]) == {(2, "ak", "disagree")}
    assert end["group_members"] == start["group_members"]
    assert {r[0] for r in set(end["read_marks"]) - set(start["read_marks"])} <= {"ak"}
    comments = call("GET", "/api/threads/1?name=ml", cookie=AK_C)[2]["comments"]
    assert [c["mine"] for c in comments[:2]] == [True, False]  # whose "mine" is ak's


# ---- N19 (R35, R36, F7-13, RR5 R2-1) ----

NAME_ERROR = {"error": "a name must be a clean display name of at most 60 characters"}


@pytest.mark.parametrize("name", [" ml", "ml ", "m\\u200bl", "a" * 61, "", "m\\x00l"])
@pytest.mark.parametrize("method", ["POST", "DELETE"])
def test_an_unclean_member_name_is_400_and_nothing_changes(
    world: Site, method: str, name: str
) -> None:
    before = dump(world.root)
    body = {"name": name.encode().decode("unicode_escape")}
    status, _, reply = world.call(method, "/api/groups/1/members", cookie=AK_C, body=body)
    assert (status, reply) == (400, NAME_ERROR)
    assert dump(world.root) == before


NO_PARENT = {"error": "no such comment in this thread to reply to"}


@pytest.mark.parametrize(
    "parent", [999999, 10**29, 2, 0], ids=["missing", "digits30", "other", "0"]
)
def test_a_reply_to_a_parent_that_is_not_in_the_thread_is_400(world: Site, parent: int) -> None:
    body = {"text": "x", "parent": parent}
    status, _, reply = world.call("POST", "/api/threads/1/comments", cookie=ML_C, body=body)
    assert (status, reply) == (400, NO_PARENT)  # comment 2 is hidden from ml: the same answer
    assert world.counts()["comments"] == 2


NOT_WHOLE = [True, 1.0, "1", 10**29]
WHOLE_ROWS: dict[str, tuple[str, Callable[[Any], dict[str, Any]], str]] = {
    "story_id": ("/api/groups/1/threads", lambda v: {"story_id": v}, "story_id"),
    "parent": ("/api/threads/1/comments", lambda v: {"text": "x", "parent": v}, "parent"),
    "topic": ("/api/groups", lambda v: NEW_GROUP | {"topics": [v]}, "topics"),
}
# The 30-digit integer is a whole number the store cannot hold: its own refusal, still 400.
BIG = {
    "story_id": {"error": "no story with that id"},
    "parent": NO_PARENT,
    "topic": {"error": "no topic with that id"},
}


@pytest.mark.parametrize("field", list(WHOLE_ROWS))
def test_an_id_in_a_body_is_a_whole_number_the_store_can_hold(world: Site, field: str) -> None:
    path, build, label = WHOLE_ROWS[field]
    before = dump(world.root)
    for value in NOT_WHOLE:
        status, _, reply = world.call("POST", path, cookie=ML_C, body=build(value))
        expected = BIG[field] if value == 10**29 else {"error": f"{label} must be a whole number"}
        assert (status, reply) == (400, expected), value
    assert dump(world.root) == before


@contextmanager
def held(root: Path, patch: pytest.MonkeyPatch) -> Iterator[None]:
    """A second connection holds the write lock; the busy wait is patched to 0.2 s."""
    patch.setattr(store, "_BUSY_SECONDS", 0.2)
    other = open_db(root)
    other.execute("BEGIN IMMEDIATE")
    try:
        yield
    finally:
        other.execute("ROLLBACK")
        other.close()


@pytest.mark.parametrize("method,path,body", WRITES, ids=[f"w{i}" for i in range(len(WRITES))])
def test_a_busy_database_is_503_on_every_group_and_thread_write(
    world: Site,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    body: dict[str, Any] | None,
) -> None:
    before = dump(world.root)
    with held(world.root, monkeypatch):
        status, _, reply = world.call(method, path, cookie=AK_C, body=body)
    assert (status, reply) == (503, BUSY)  # never 400, never "that group name is taken"
    assert dump(world.root) == before


def test_a_busy_database_never_reads_as_a_taken_group_name(
    world: Site, monkeypatch: pytest.MonkeyPatch
) -> None:
    with held(world.root, monkeypatch):
        status, _, reply = world.call("POST", "/api/groups", cookie=AK_C, body=NEW_GROUP)
    assert (status, reply) == (503, BUSY)
    assert world.call("POST", "/api/groups", cookie=AK_C, body=NEW_GROUP)[::2] == (200, {"id": 3})
    taken = world.call("POST", "/api/groups", cookie=AK_C, body=NEW_GROUP)
    assert taken[::2] == (400, {"error": "that group name is taken"})  # the real "taken" differs


# ---- the store refuses a connection it cannot use: 500 on every route that reaches it ----

UNUSABLE: list[Row] = [*WRITES, ("GET", "/api/threads/1", None)]


@pytest.mark.parametrize("method,path,body", UNUSABLE, ids=[f"r{i}" for i in range(len(UNUSABLE))])
def test_a_connection_with_a_foreign_transaction_is_a_500_that_says_nothing(
    world: Site,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    method: str,
    path: str,
    body: dict[str, Any] | None,
) -> None:
    real = store.open_db

    def with_open_transaction(root: Path) -> Any:
        db = real(root)
        db.execute("BEGIN")  # a transaction this store did not begin (R29)
        return db

    before = dump(world.root)
    monkeypatch.setattr(store, "open_db", with_open_transaction)
    with caplog.at_level(logging.ERROR):
        status, _, reply = world.call(method, path, cookie=AK_C, body=body)
    assert (status, reply) == (500, FAILED)
    assert "transaction" in caplog.text  # the cause is logged, in no body
    monkeypatch.setattr(store, "open_db", real)
    assert dump(world.root) == before


# ---- NotFound and Forbidden by type, with their own text, on every route ----

MISSING: list[Row] = [
    ("GET", "/api/groups/999999", None),
    ("GET", "/api/groups/999999/threads", None),
    ("GET", "/api/threads/999999", None),
    ("POST", "/api/groups/999999/members", {}),
    ("POST", "/api/groups/999999/members", {"name": "rd"}),
    ("DELETE", "/api/groups/999999/members", {}),
    ("DELETE", "/api/groups/999999/members", {"name": "ak"}),
    ("POST", "/api/groups/999999/threads", {"story_id": 1}),
    ("POST", "/api/groups/999999/threads", {"title": "T", "text": "x"}),
    ("POST", "/api/threads/999999/read", {}),
    ("POST", "/api/threads/999999/comments", {"text": "x"}),
    ("POST", "/api/comments/999999", {"text": "x"}),
    ("DELETE", "/api/comments/999999", None),
    ("POST", "/api/comments/999999/reactions/agree", None),
    ("DELETE", "/api/comments/999999/reactions/agree", None),
]
MISSING_TEXT = ["no such group"] * 2 + ["no such thread"] + ["no such group"] * 6
MISSING_TEXT += ["no such thread"] * 2 + ["no such comment"] * 4


@pytest.mark.parametrize("n", range(len(MISSING)), ids=[f"m{i}" for i in range(len(MISSING))])
def test_a_missing_target_is_404_with_the_kind_in_its_text(world: Site, n: int) -> None:
    method, path, body = MISSING[n]
    status, _, reply = world.call(method, path, cookie=ML_C, body=body)
    assert (status, reply) == (404, {"error": MISSING_TEXT[n]})


# Reader (rd) on the visible rows of the world: the text of each 403, by literal.
FORBIDDEN: list[tuple[Row, str]] = [
    (WRITES[0], "only writers and the owner can create groups"),
    (WRITES[2], "only writers and the owner can manage members"),
    (WRITES[4], "only writers and the owner can manage members"),
    (WRITES[5], "only writers and the owner can share stories"),
    (WRITES[6], "only writers and the owner can start notes"),
    (WRITES[8], "only writers and the owner can comment"),
    (WRITES[9], "only the author can edit a comment, and not a removed one"),
    (WRITES[10], "only the author can delete a comment"),
]


@pytest.mark.parametrize("row,text", FORBIDDEN, ids=[f"f{i}" for i in range(len(FORBIDDEN))])
def test_a_refusal_for_the_role_is_403_with_its_text(world: Site, row: Row, text: str) -> None:
    before = dump(world.root)
    method, path, body = row
    status, _, reply = world.call(method, path, cookie=RD_C, body=body)
    assert (status, reply) == (403, {"error": text})
    assert dump(world.root) == before


# ---- N20 (R23): what every reply carries ----

CARD = {"id", "title", "link", "summary", "source", "kind", "published_at", "other_sources"}
CARD |= {"saved", "topics", "threads"}
COMMENT = {"id", "parent_id", "author", "role", "text", "created_at", "edited", "removed"}
COMMENT |= {"reactions", "mine", "editable"}
UNREAD = {"replies", "threads", "total", "by_group"}
GROUP_ROW = {"id", "name", "visibility", "member", "members", "threads", "unread"}
THREAD_ROW = {"id", "kind", "title", "source", "source_kind", "started_by", "comments"}
THREAD_ROW |= {"last_activity_at", "unread"}
THREAD_VIEW = {"id", "group_id", "group", "story", "title", "started_by", "comments", "can_post"}


def test_every_reply_carries_exactly_the_agreed_fields(world: Site) -> None:
    db = open_db(world.root)
    db.execute(
        "INSERT INTO topics(name, keywords, kinds, created_by, created_at)"
        " VALUES('x', '[]', '[]', 'ak', 'now')"
    )
    db.commit()
    db.close()

    def ask(who: str, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        status, _, reply = world.call(method, path, cookie=COOKIE[who], body=body)
        assert status == 200, (path, reply)
        return reply

    assert set(ask("ml", "GET", "/api/me")) == {"name", "role"}
    status = ask("ml", "GET", "/api/status")
    assert set(status) == {"last_pass_at", "sources", "loop_error"}
    assert set(status["sources"]) == {"approved", "failing"}
    page = ask("ml", "GET", "/api/feed?view=latest")
    assert set(page) == {"cards", "next_before", "newest"}
    card = next(c for c in page["cards"] if c["id"] == 1)
    assert set(card) == CARD
    assert set(card["threads"][0]) == {"id", "group", "comments", "shared_by", "note"}
    assert set(ask("ml", "GET", "/api/feed/new?view=latest&after=0")) == {"count"}
    assert set(ask("ml", "POST", "/api/stories/1/save", {})) == {"saved"}
    topics = ask("ml", "GET", "/api/topics")
    assert set(topics[0]) == {"id", "name", "following", "stories"}
    assert set(ask("ml", "POST", "/api/topics/1/follow", {})) == {"following"}
    listed = ask("ml", "GET", "/api/groups")
    assert set(listed) == {"groups", "can_create"}
    assert set(listed["groups"][0]) == GROUP_ROW
    assert set(ask("ml", "POST", "/api/groups", NEW_GROUP)) == {"id"}
    detail = ask("ml", "GET", "/api/groups/1")
    assert set(detail) == {"id", "name", "visibility", "member", "can_manage", "members"}
    assert set(ask("ml", "POST", "/api/groups/1/members", {})) == {"members"}
    assert set(ask("ml", "DELETE", "/api/groups/1/members", {})) == {"members"}
    ask("ml", "POST", "/api/groups/1/members", {})
    assert set(ask("ml", "POST", "/api/groups/1/threads", {"story_id": 2})) == {
        "thread_id",
        "joined",
    }
    note = ask("ml", "POST", "/api/groups/1/threads", {"title": "T", "text": "x"})
    assert note["thread_id"] == 4  # thread 3 is story 2
    page_of_threads = ask("ml", "GET", "/api/groups/1/threads")
    assert set(page_of_threads) == {"threads", "next_before"}
    assert set(page_of_threads["threads"][0]) == THREAD_ROW
    assert ask("ml", "POST", "/api/threads/1/comments", {"text": "b", "parent": 1}) == {"id": 4}
    for who, key in (("ak", "seen"), ("ak", "disagree"), ("ak", "agree"), ("ml", "seen")):
        ask(who, "POST", f"/api/comments/1/reactions/{key}")  # not in REACTIONS order
    thread = ask("ml", "GET", "/api/threads/1")
    assert set(thread) == THREAD_VIEW
    assert set(thread["comments"][0]) == COMMENT
    assert thread["comments"][0]["reactions"] == [
        {"key": "agree", "count": 1, "mine": False},
        {"key": "disagree", "count": 1, "mine": False},
        {"key": "seen", "count": 2, "mine": True},
    ]
    assert thread["story"] == ask("ml", "GET", "/api/stories/1")  # the feed's card, same user
    assert set(thread["comments"][0]["reactions"][0]) == {"key", "count", "mine"}
    assert ask("ml", "GET", "/api/threads/4")["story"] is None  # a note has no story
    assert set(ask("ml", "POST", "/api/threads/1/read", {})) == {"unread"}
    assert set(ask("ml", "POST", "/api/threads/1/read", {})["unread"]) == UNREAD
    assert set(ask("ml", "GET", "/api/unread")) == UNREAD
    assert ask("ml", "POST", "/api/comments/4", {"text": "edit"}) == {}
    assert ask("ml", "DELETE", "/api/comments/4") == {}
