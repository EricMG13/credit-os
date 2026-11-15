"""Signal's HTTP service: the wire (requests, identity, limits) and the one error mapping.

Plain ``http.server``; no framework. The service has no login and may be reachable from other
machines, so every request is hostile input. Every request is checked before any body byte is read:

* ``Host`` must be exactly ``<host>:<port>`` as started (and ``localhost:<port>`` when the host is
  ``127.0.0.1``); otherwise 403. On port 80 the port may be left out of ``Host`` and ``Origin``.
* A request target must be a path (it starts with ``/``): an absolute URI is 400.
* Every request other than GET must carry ``Origin: http://<Host>``; otherwise 403 and no change.
  A GET that carries ``Origin`` must carry the same value. Any request whose ``Sec-Fetch-Site`` is
  present and is not ``same-origin`` or ``none`` is 403, except a top-level navigation: a GET with
  ``Sec-Fetch-Mode: navigate`` and ``Sec-Fetch-Dest: document``. A request with neither header (not
  a browser) is served.
* Every response carries ``Cross-Origin-Resource-Policy: same-origin``, ``nosniff`` and the page
  policy ``Content-Security-Policy``.
* At most ``MAX_CONNECTIONS`` connections are open, and at most ``MAX_PER_ADDRESS`` per remote
  address; one beyond either is closed at once. A connection is shut down ``2 * SOCKET_TIMEOUT``
  seconds after it opens, however it trickles. An HTTP/0.9 request line is closed without a reply.
* A JSON body needs ``Content-Length`` (else 411), is at most 64 KiB (else 413) and must be a JSON
  object (else 400) that names no field twice. Every connection serves one request and closes.

The service serves no file: a path no API route matches is 404 for every method (decision 0009).
Identity is a display name in one ``Cookie`` header, not authentication; only
``identity.current_user`` turns it into a user. Each request opens its own database connection and
closes it.

A refusal is ``{"error": "<plain sentence>"}``. Store, view and identity errors are mapped in one
place, ``Handler._api``, by type and most specific first: ``StoreUnusable`` 500 (fixed text, traceback
logged), ``NotFound`` 404, ``Forbidden`` 403, ``ViewError`` the route's ``view_status``,
``IdentityError`` 400, any other ``StoreError`` the route's ``store_status``,
``sqlite3.OperationalError`` 503 (fixed text, traceback logged). An unexpected failure is 500
``{"error": "the service failed; see its log"}``, its cause in the log only.
"""

from __future__ import annotations

import dataclasses
import ipaddress
import json
import logging
import re
import socket
import sqlite3
import sys
import threading
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast

from credit_os.signal import feedview, groups, identity, ingest, store, threads, topics

__all__ = ["DEFAULT_HOST", "DEFAULT_PORT", "Handler", "Loop", "make_server", "serve"]

log = logging.getLogger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8766
MAX_JSON = 64 * 1024
# Seconds one socket read may wait. It is per read, so a client trickling bytes would never hit it;
# the absolute limit is the connection deadline, 2 * SOCKET_TIMEOUT from accept (Handler.setup).
SOCKET_TIMEOUT = 60
# Each connection holds a thread for up to the deadline; a few colleagues use the service.
MAX_CONNECTIONS = 64
MAX_PER_ADDRESS = 16  # one remote address may hold this many of the MAX_CONNECTIONS
MAX_PARAMS = 20
MAX_AFTER_DIGITS = len(str(feedview.MAX_ID))
_POLICY = (
    "default-src 'none'; script-src 'self'; style-src 'self'; font-src 'self'; "
    "img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'; "
    "frame-ancestors 'none'"
)
_JSON = "application/json; charset=utf-8"
_FAILED = "the service failed; see its log"
_BUSY = "the store is busy; try again"
_NEEDS_NAME = "choose a display name first"
WILDCARD_MESSAGE = (
    "--host: pass this machine's own address, not 0.0.0.0 (no Host header would match)"
)


class _Reply(Exception):  # control flow: it carries the response, not a failure
    def __init__(self, status: int, body: Any, headers: dict[str, str] | None = None) -> None:
        super().__init__(status)
        self.status, self.body, self.headers = status, body, headers or {}


def _refuse(status: int, text: str) -> _Reply:
    return _Reply(status, {"error": text})


def _no_check_at(db: sqlite3.Connection, source_id: int, now: datetime) -> bool:
    """True when ``source_id`` has no check recorded at this pass's time: its last result, not ok,
    then came from the lookup cap (no row is written for it), whatever the reason's text says."""
    row = store.last_check(db, source_id)
    return row is None or row["at"] != store.utc_text(now)


class Loop:
    """The background ingest loop: one pass per tick over the approved sources that are due.

    ``fetch_fn`` is for tests only (a recorded feed standing in for ``fetch.fetch``); ``serve``
    builds ``Loop(root)``, so production always fetches for real."""

    def __init__(self, root: Path, fetch_fn: ingest.FetchFn | None = None) -> None:
        self.root = root
        self.fetch_fn = fetch_fn
        self.last_error: str | None = None
        self._running = threading.Lock()  # held for the length of one pass

    def run_once(self, now: datetime) -> None:
        """One pass on this thread's own connection and no transaction, one at a time in this
        process: while a pass runs, this call logs and returns. Two processes on one root are not
        prevented and a pass has no time budget (it can hold the write lock for a long while).

        A pass that returns clears ``last_error``. One that stops at the lookup cap is incomplete,
        not failing: a warning, the sources left stay due, ``last_error`` stays ``None``."""
        if not self._running.acquire(blocking=False):
            log.info("an ingest pass is already running; this tick is skipped")
            return
        try:
            db = store.open_db(self.root)
            try:
                results = ingest.run_due(db, now, self.fetch_fn)
                capped = (
                    bool(results) and not results[-1][1] and _no_check_at(db, results[-1][0], now)
                )
            finally:
                db.close()
        except Exception as error:
            # The one documented fail-open of the loop, at the thread's top level only: whatever a
            # pass raises (StoreUnusable, a locked database, a bad `now`, a bug) must not end the
            # service. The traceback goes to the log, /api/status shows the type name only, never
            # the cause, nothing is recorded in the store, and the next tick tries again.
            # KeyboardInterrupt and SystemExit (BaseException) are not caught.
            log.exception("ingest pass failed")
            self.last_error = f"the last ingest pass failed ({type(error).__name__}); see the log"
        else:
            self.last_error = None
            checked = results[:-1] if capped else results
            failed = sum(not ok for _, ok, _ in checked)
            log.info("ingest pass: %d checked, %d failed", len(checked), failed)
            if capped:
                log.warning("ingest pass stopped at the lookup cap; later sources stay due")
        finally:
            self._running.release()

    def run_until(self, stop: threading.Event, tick: float) -> None:
        while True:
            self.run_once(datetime.now(UTC))
            if stop.wait(tick):
                return


@dataclass
class _Req:
    """What a route handler may use: its own connection, who asked, and the request's parts."""

    db: sqlite3.Connection
    user: identity.User | None
    groups: tuple[str, ...]
    params: dict[str, str]
    body: Callable[[], dict[str, Any]]
    loop: Loop | None

    @property
    def person(self) -> identity.User:
        if self.user is None:
            raise _refuse(401, _NEEDS_NAME)
        return self.user

    def param(self, name: str) -> str:
        if name not in self.params:
            raise _refuse(400, f"the request needs {name}")
        return self.params[name]


def _me(req: _Req) -> _Reply:
    if req.user is None:
        return _Reply(200, {"name": None})
    return _Reply(200, {"name": req.user.name, "role": req.user.role})


def _set_me(req: _Req) -> _Reply:
    name = req.body().get("name")
    if not isinstance(name, str):
        raise _refuse(400, "the request needs a name")
    cleaned, cookie = identity.clean_name(name), identity.cookie_for(name)
    return _Reply(
        200, {"name": cleaned, "role": store.role_of(req.db, cleaned)}, {"Set-Cookie": cookie}
    )


def _feed(req: _Req) -> _Reply:
    filters: feedview.Filters = {}
    if "kind" in req.params:
        filters["kind"] = req.params["kind"]
    if "q" in req.params:
        filters["query"] = req.params["q"]
    if "before" in req.params:
        filters["before"] = req.params["before"]
    if "shared" in req.params:
        if req.params["shared"] != "1":
            raise _refuse(400, "invalid shared; expected 1")
        filters["shared"] = True
    page = feedview.feed(req.db, req.person.name, req.param("view"), **filters)
    cards = [dataclasses.asdict(card) for card in page.cards]
    return _Reply(200, {"cards": cards, "next_before": page.next_before, "newest": page.newest})


def _feed_new(req: _Req) -> _Reply:
    after = req.param("after")
    if not (after.isascii() and after.isdecimal() and len(after) <= MAX_AFTER_DIGITS):
        raise _refuse(400, "invalid after; expected digits")
    count = feedview.new_count(req.db, req.person.name, req.param("view"), int(after))
    return _Reply(200, {"count": count})


def _story(
    req: _Req, action: Callable[[sqlite3.Connection, str, int], None], saved: bool
) -> _Reply:
    action(req.db, req.person.name, int(req.groups[0]))
    return _Reply(200, {"saved": saved})


def _topic(req: _Req, action: Callable[[sqlite3.Connection, str, int], None], on: bool) -> _Reply:
    action(req.db, req.person.name, int(req.groups[0]))
    return _Reply(200, {"following": on})


def _story_card(req: _Req) -> _Reply:
    """One card as the feed shows it to this user; threads of hidden groups are absent."""
    card = feedview.card_for(req.db, req.person.name, int(req.groups[0]))
    return _Reply(200, dataclasses.asdict(card))


def _save(req: _Req) -> _Reply:
    return _story(req, feedview.save, True)


def _unsave(req: _Req) -> _Reply:
    return _story(req, feedview.unsave, False)


def _follow(req: _Req) -> _Reply:
    return _topic(req, topics.follow, True)


def _unfollow(req: _Req) -> _Reply:
    return _topic(req, topics.unfollow, False)


def _topics(req: _Req) -> _Reply:
    rows = topics.list_topics(req.db, req.person.name)
    return _Reply(
        200,
        [
            {
                "id": row["id"],
                "name": row["name"],
                "following": bool(row["following"]),
                "stories": row["stories"],
            }
            for row in rows
        ],
    )


def _only(body: dict[str, Any], *allowed: str) -> dict[str, Any]:
    if set(body) - set(allowed):  # a fixed text: a refusal never carries client text
        raise _refuse(400, "the request has a field this route does not take")
    return body


def _str(body: dict[str, Any], name: str) -> str:
    value = body.get(name)
    if not isinstance(value, str):
        raise _refuse(400, f"{name} must be text")
    return value


def _opt_str(body: dict[str, Any], name: str) -> str | None:
    return None if body.get(name) is None else _str(body, name)


def _whole(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _refuse(400, f"{name} must be a whole number")
    return value


def _opt_whole(body: dict[str, Any], name: str) -> int | None:
    return None if body.get(name) is None else _whole(body[name], name)


def _ids(body: dict[str, Any], name: str) -> list[int]:
    value = body.get(name, [])
    if not isinstance(value, list):
        raise _refuse(400, f"{name} must be a list of whole numbers")
    return [_whole(item, name) for item in value]


def _act(req: _Req) -> groups.Act:
    return groups.Act(req.person, datetime.now(UTC))


def _unread_json(unread: threads.Unread) -> dict[str, Any]:
    return {
        "replies": unread.replies,
        "threads": unread.threads,
        "total": unread.replies + unread.threads,
        "by_group": {str(group): count for group, count in unread.by_group.items()},
    }


def _group_list(req: _Req) -> _Reply:
    person = req.person
    by_group = threads.unread(req.db, person.name).by_group
    found = [
        {
            "id": row["id"],
            "name": row["name"],
            "visibility": row["visibility"],
            "member": bool(row["member"]),
            "members": row["members"],
            "threads": row["threads"],
            "unread": by_group.get(row["id"], 0),
        }
        for row in groups.list_groups(req.db, person.name)
    ]
    return _Reply(200, {"groups": found, "can_create": groups.may_post(person)})


def _group_create(req: _Req) -> _Reply:
    body = _only(req.body(), "name", "visibility", "topics")
    name, visibility, topic_ids = _str(body, "name"), _str(body, "visibility"), _ids(body, "topics")
    return _Reply(200, {"id": groups.create_group(req.db, _act(req), name, visibility, topic_ids)})


def _group_get(req: _Req) -> _Reply:
    person, group_id = req.person, int(req.groups[0])
    row = groups.require_visible(req.db, person.name, group_id)
    names = groups.members(req.db, person.name, group_id)
    return _Reply(
        200,
        {
            "id": row["id"],
            "name": row["name"],
            "visibility": row["visibility"],
            "member": person.name in names,
            "can_manage": groups.can_manage(req.db, person, group_id),
            "members": names,
        },
    )


def _member_add(req: _Req) -> _Reply:
    body, group_id = _only(req.body(), "name"), int(req.groups[0])
    if not body:  # {}: the caller joins
        groups.join(req.db, req.person.name, group_id, datetime.now(UTC))
    else:
        groups.add_member(req.db, _act(req), group_id, _str(body, "name"))
    return _Reply(200, {"members": _visible_members(req, group_id)})


def _member_remove(req: _Req) -> _Reply:
    body, group_id = _only(req.body(), "name"), int(req.groups[0])
    if not body:  # {}: the caller leaves; a hidden or missing group is a 404 like everywhere else
        groups.require_visible(req.db, req.person.name, group_id)
        groups.leave(req.db, req.person.name, group_id)
    else:
        groups.remove_member(req.db, req.person, group_id, _str(body, "name"))
    return _Reply(200, {"members": _visible_members(req, group_id)})


def _visible_members(req: _Req, group_id: int) -> list[str]:
    """The member list for the reply; a person who just left an invited group no longer sees it."""
    if not groups.can_see(req.db, req.person.name, group_id):
        return []
    return groups.members(req.db, req.person.name, group_id)


def _thread_page(req: _Req) -> _Reply:
    page, next_before = threads.thread_list(
        req.db, req.person.name, int(req.groups[0]), req.params.get("before")
    )
    return _Reply(
        200, {"threads": [dataclasses.asdict(row) for row in page], "next_before": next_before}
    )


def _thread_start(req: _Req) -> _Reply:
    """A shared story or a note. The text is passed as sent: ``threads`` cleans it, and refuses a
    bad one before it looks at the group (R55), so no check here depends on what is stored."""
    body, group_id = req.body(), int(req.groups[0])
    if "story_id" in body:
        _only(body, "story_id", "note")
        story_id, note = _whole(body["story_id"], "story_id"), _opt_str(body, "note")
        thread_id, joined = threads.share_story(req.db, _act(req), group_id, story_id, note)
        return _Reply(200, {"thread_id": thread_id, "joined": joined})
    if "title" in body and "text" in body:
        _only(body, "title", "text")
        title, text = _str(body, "title"), _str(body, "text")
        return _Reply(
            200,
            {
                "thread_id": threads.start_note(req.db, _act(req), group_id, title, text),
                "joined": False,
            },
        )
    raise _refuse(400, "send either story_id (with note) or title and text")


def _thread_get(req: _Req) -> _Reply:
    view = threads.read_thread(req.db, req.person, int(req.groups[0]), datetime.now(UTC))
    return _Reply(200, dataclasses.asdict(view))


def _thread_read(req: _Req) -> _Reply:
    _only(req.body())  # {} and nothing else
    name = req.person.name
    threads.mark_read(req.db, name, int(req.groups[0]))
    return _Reply(200, {"unread": _unread_json(threads.unread(req.db, name))})


def _comment_add(req: _Req) -> _Reply:
    body = _only(req.body(), "text", "parent")
    text, parent = _str(body, "text"), _opt_whole(body, "parent")
    return _Reply(
        200, {"id": threads.add_comment(req.db, _act(req), int(req.groups[0]), text, parent)}
    )


def _comment_edit(req: _Req) -> _Reply:
    text = _str(_only(req.body(), "text"), "text")
    threads.edit_comment(req.db, _act(req), int(req.groups[0]), text)
    return _Reply(200, {})


def _comment_delete(req: _Req) -> _Reply:
    threads.delete_comment(req.db, _act(req), int(req.groups[0]))
    return _Reply(200, {})


def _reaction(
    action: Callable[[sqlite3.Connection, identity.User, int, str], None],
) -> Callable[[_Req], _Reply]:
    """A reaction route: the comment, then the key, from the path. ``threads`` decides who may
    react (a registered user, R54) and which keys exist (R21); the key is at most twelve letters."""

    def run(req: _Req) -> _Reply:
        action(req.db, req.person, int(req.groups[0]), req.groups[1])
        return _Reply(200, {})

    return run


def _unread_get(req: _Req) -> _Reply:
    return _Reply(200, _unread_json(threads.unread(req.db, req.person.name)))


def _status(req: _Req) -> _Reply:
    """What is known without a name: when a pass last returned (not that every source was visited:
    a pass can stop early), how many sources are approved and failing, the loop's last error."""
    now = datetime.now(UTC)
    approved = store.sources(req.db, "approved")
    failing = sum(ingest.health(req.db, row["id"], now).state == "failing" for row in approved)
    return _Reply(
        200,
        {
            "last_pass_at": store.get_meta(req.db, "last_pass_at"),
            "sources": {"approved": len(approved), "failing": failing},
            "loop_error": req.loop.last_error if req.loop is not None else None,
        },
    )


@dataclass(frozen=True)
class _Route:
    method: str
    pattern: re.Pattern[str]
    handler: Callable[[_Req], _Reply]
    open_to_all: bool = False  # only /api/me and /api/status work without a display name
    view_status: int = 400  # what a feedview.ViewError from this route is answered with
    store_status: int = 400  # what a plain store.StoreError from this route is answered with


_ID = "([0-9]{1,18})"  # ASCII digits only (a str pattern's \d also matches other scripts)
_KEY = "([a-z]{1,12})"  # a reaction key: lowercase ASCII letters
_ROUTES = (
    _Route("GET", re.compile("/api/me"), _me, open_to_all=True),
    _Route("POST", re.compile("/api/me"), _set_me, open_to_all=True),
    _Route("GET", re.compile("/api/status"), _status, open_to_all=True),
    _Route("GET", re.compile("/api/feed"), _feed),
    _Route("GET", re.compile("/api/feed/new"), _feed_new),
    _Route("GET", re.compile(f"/api/stories/{_ID}"), _story_card, view_status=404),
    _Route("POST", re.compile(f"/api/stories/{_ID}/save"), _save, view_status=404),
    _Route("DELETE", re.compile(f"/api/stories/{_ID}/save"), _unsave, view_status=404),
    _Route("GET", re.compile("/api/topics"), _topics),
    _Route("POST", re.compile(f"/api/topics/{_ID}/follow"), _follow, store_status=404),
    _Route("DELETE", re.compile(f"/api/topics/{_ID}/follow"), _unfollow, store_status=404),
    _Route("GET", re.compile("/api/groups"), _group_list),
    _Route("POST", re.compile("/api/groups"), _group_create),
    _Route("GET", re.compile(f"/api/groups/{_ID}"), _group_get),
    _Route("POST", re.compile(f"/api/groups/{_ID}/members"), _member_add),
    _Route("DELETE", re.compile(f"/api/groups/{_ID}/members"), _member_remove),
    _Route("GET", re.compile(f"/api/groups/{_ID}/threads"), _thread_page),
    _Route("POST", re.compile(f"/api/groups/{_ID}/threads"), _thread_start),
    _Route("GET", re.compile(f"/api/threads/{_ID}"), _thread_get),
    _Route("POST", re.compile(f"/api/threads/{_ID}/read"), _thread_read),
    _Route("POST", re.compile(f"/api/threads/{_ID}/comments"), _comment_add),
    _Route("POST", re.compile(f"/api/comments/{_ID}"), _comment_edit),
    _Route("DELETE", re.compile(f"/api/comments/{_ID}"), _comment_delete),
    _Route("POST", re.compile(f"/api/comments/{_ID}/reactions/{_KEY}"), _reaction(threads.react)),
    _Route(
        "DELETE", re.compile(f"/api/comments/{_ID}/reactions/{_KEY}"), _reaction(threads.unreact)
    ),
    _Route("GET", re.compile("/api/unread"), _unread_get),
)


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    # On Windows SO_REUSEADDR lets a second socket bind a port that is in use.
    allow_reuse_address = sys.platform != "win32"
    root: Path
    allowed_hosts: frozenset[str]
    advertised_port: int = 0
    loop: Loop | None = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.active_connections = 0
        self._per_address: dict[str, int] = {}
        self._count = threading.Lock()
        super().__init__(*args, **kwargs)

    def verify_request(self, request: Any, client_address: Any) -> bool:
        with self._count:
            address = str(client_address[0])
            if (
                self.active_connections >= MAX_CONNECTIONS
                or self._per_address.get(address, 0) >= MAX_PER_ADDRESS
            ):
                return False  # closed by the server loop with no handler thread
            self.active_connections += 1
            self._per_address[address] = self._per_address.get(address, 0) + 1
        return True

    def _release(self, client_address: Any) -> None:
        address = str(client_address[0])
        with self._count:
            self.active_connections -= 1
            if self._per_address[address] <= 1:
                del self._per_address[address]
            else:
                self._per_address[address] -= 1

    def process_request(self, request: Any, client_address: Any) -> None:
        try:
            super().process_request(request, client_address)
        except BaseException:
            # the handler thread never ran (the OS refused it), so it cannot release
            self._release(client_address)
            raise

    def process_request_thread(self, request: Any, client_address: Any) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._release(client_address)


def _params(query: str) -> dict[str, str]:
    """The query's parameters, blanks kept, the first of a repeated one."""
    try:
        found = urllib.parse.parse_qs(
            query, keep_blank_values=True, errors="strict", max_num_fields=MAX_PARAMS
        )
    except (UnicodeDecodeError, ValueError):  # not UTF-8, or too many fields
        raise _refuse(400, "the query string is not valid") from None
    return {name: values[0] for name, values in found.items()}


def _no_repeats(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """The ``object_pairs_hook`` of a request body: a field named twice is a refusal."""
    found = dict(pairs)
    if len(found) != len(pairs):
        raise _refuse(400, "the request body names a field twice")
    return found


# Control characters (U+0000-U+001F, U+007F-U+009F) and the backslash, written as escapes: what the
# standard library's own log_message does, so a request line cannot write terminal escape
# sequences or forge a log line.
_LOG_ESCAPES = {code: f"\\x{code:02x}" for code in (*range(0x20), *range(0x7F, 0xA0))}
_LOG_ESCAPES[ord("\\")] = "\\\\"


class Handler(BaseHTTPRequestHandler):
    timeout = SOCKET_TIMEOUT
    server_version = "Signal"
    sys_version = ""
    # The replies http.server writes itself (400, 414, 431, 501) are fixed JSON that quotes nothing.
    error_message_format = '{"error": "the request could not be read"}'
    error_content_type = _JSON
    _deadline: threading.Timer | None = None

    def setup(self) -> None:
        super().setup()
        # The absolute limit on this connection: the socket timeout is per read and a trickling
        # client never reaches it, so a timer shuts the socket down 2 * SOCKET_TIMEOUT after accept.
        self._deadline = threading.Timer(
            2 * SOCKET_TIMEOUT, self._expire, args=(self.connection, self.client_address[0])
        )
        self._deadline.daemon = True
        self._deadline.start()

    @staticmethod
    def _expire(connection: socket.socket, client: str) -> None:
        try:
            connection.shutdown(socket.SHUT_RDWR)
        except OSError:  # already closed by the handler or the peer: nothing left to cut
            return
        log.info("%s connection deadline reached", client)

    def finish(self) -> None:
        if self._deadline is not None:
            self._deadline.cancel()
        super().finish()

    @property
    def _service(self) -> _Server:
        return cast(_Server, self.server)

    def _request(self) -> str:
        """The method and target as a log line may show them: control characters escaped."""
        return f"{self.command} {self.path}".translate(_LOG_ESCAPES)

    def log_message(self, format: str, *args: Any) -> None:
        log.info("%s %s", self.address_string(), (format % args).translate(_LOG_ESCAPES))

    def do_GET(self) -> None:
        self._serve()

    do_POST = do_DELETE = do_PUT = do_PATCH = do_HEAD = do_OPTIONS = do_GET

    def _serve(self) -> None:
        if self.request_version == "HTTP/0.9":
            self.close_connection = True  # no headers exist to check and none can be sent
            log.info("%s: HTTP/0.9 request closed", self.address_string())
            return
        try:
            if not self.path.startswith("/"):
                raise _refuse(400, "the request target must be a path")
            self._check_origin()
            if self.headers.get("Transfer-Encoding") is not None:
                raise _refuse(411, "a body needs Content-Length")
            self._reply(self._dispatch(urllib.parse.urlsplit(self.path)))
        except _Reply as reply:
            self._reply(reply)
        except Exception:
            # The one catch-all of a request, documented: whatever a handler raises becomes a 500
            # with fixed text. The traceback goes to the log; neither it nor the exception text
            # reaches the client. KeyboardInterrupt and SystemExit (BaseException) are not caught.
            log.exception("%s", self._request())
            self._send(_refuse(500, _FAILED))

    def _check_origin(self) -> None:
        hosts = self.headers.get_all("Host") or []
        if len(hosts) != 1 or hosts[0] not in self._service.allowed_hosts:
            raise _refuse(403, "this address is not the one the service was started on")
        site = self.headers.get_all("Sec-Fetch-Site")
        if site is not None and site not in (["same-origin"], ["none"]) and not self._navigation():
            raise _refuse(403, "the request came from another site")
        origins = self.headers.get_all("Origin") or []
        acceptable = [f"http://{hosts[0]}"]
        if self._service.advertised_port == 80 and hosts[0].endswith(":80"):
            acceptable.append(f"http://{hosts[0][:-3]}")  # browsers leave the default port out
        if (self.command != "GET" or origins) and not (
            len(origins) == 1 and origins[0] in acceptable
        ):
            raise _refuse(403, "the request did not come from the service's own page")

    def _navigation(self) -> bool:
        """A top-level navigation to a document: only a GET with both fetch-metadata values."""
        return (
            self.command == "GET"
            and self.headers.get_all("Sec-Fetch-Mode") == ["navigate"]
            and self.headers.get_all("Sec-Fetch-Dest") == ["document"]
        )

    def end_headers(self) -> None:
        # Here, not in _send, so the replies http.server writes itself (501, 400, 414) carry them.
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", _POLICY)
        self.send_header("X-Frame-Options", "DENY")
        super().end_headers()

    def _reply(self, reply: _Reply) -> None:
        """Send a reply; one that cannot be built or encoded (any failure but a dead socket, which
        `_send` handles) is logged with its traceback and becomes the documented 500."""
        try:
            self._send(reply)
        except Exception:
            log.exception("%s: reply could not be sent", self._request())
            self._send(_refuse(500, _FAILED))

    def _send(self, reply: _Reply) -> None:
        data = json.dumps(reply.body, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": _JSON, "Cache-Control": "no-store", **reply.headers}
        try:
            self.send_response(reply.status)
            self.send_header("Content-Length", str(len(data)))
            for name, value in headers.items():
                self.send_header(name, value)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)
        except OSError as error:  # the peer went away or stalled: nothing more can be said to it
            log.info("%s: reply not delivered (%s)", self._request(), error)

    def _json_body(self) -> dict[str, Any]:
        values = self.headers.get_all("Content-Length") or []
        if not values:
            raise _refuse(411, "a body needs Content-Length")
        text = values[0].strip()
        if len(values) != 1 or not (text.isascii() and text.isdigit()) or len(text) > 15:
            raise _refuse(400, "Content-Length is not a length")
        length = int(text)
        if length > MAX_JSON:
            raise _refuse(413, f"a request body is at most {MAX_JSON // 1024} KiB")
        try:
            data = self.rfile.read(length)
        except OSError as error:  # the body stalled past the socket timeout or the peer reset
            log.info("%s: request body did not arrive (%s)", self._request(), error)
            raise _refuse(400, "the request body did not arrive") from None
        if len(data) != length:
            raise _refuse(400, "the request body ended early")
        try:
            body = json.loads(data.decode("utf-8"), object_pairs_hook=_no_repeats)
        except (ValueError, RecursionError):  # bad UTF-8, bad JSON, or nesting past the parser
            raise _refuse(400, "the request body is not valid JSON") from None
        if not isinstance(body, dict):
            raise _refuse(400, "the request body must be a JSON object")
        return body

    def _dispatch(self, url: urllib.parse.SplitResult) -> _Reply:
        allowed: list[str] = []
        for route in _ROUTES:
            found = route.pattern.fullmatch(url.path)
            if found is None:
                continue
            if route.method == self.command:
                return self._api(route, found.groups(), url.query)
            allowed.append(route.method)
        if allowed:
            raise _Reply(405, {"error": "method not allowed"}, {"Allow": ", ".join(allowed)})
        raise _refuse(404, "not found")

    def _cookie(self) -> str | None:
        lines = self.headers.get_all("Cookie") or []
        if len(lines) > 1:
            raise _refuse(400, "send one Cookie header")
        return lines[0] if lines else None

    def _api(self, route: _Route, captured: tuple[str, ...], query: str) -> _Reply:
        """Run one route on this request's own connection; the one place store, view and identity
        errors become statuses (most specific first; the text is ``str(error)`` and nothing else)."""
        params = _params(query)
        try:
            return self._run(route, captured, params)
        except store.StoreUnusable:
            log.exception("%s", self._request())
            raise _refuse(500, _FAILED) from None
        except groups.NotFound as error:
            raise _refuse(404, str(error)) from None
        except groups.Forbidden as error:
            raise _refuse(403, str(error)) from None
        except feedview.ViewError as error:
            raise _refuse(route.view_status, str(error)) from None
        except identity.IdentityError as error:
            raise _refuse(400, str(error)) from None
        except store.StoreError as error:
            raise _refuse(route.store_status, str(error)) from None
        except sqlite3.OperationalError:
            log.exception("%s", self._request())
            raise _refuse(503, _BUSY) from None

    def _run(self, route: _Route, captured: tuple[str, ...], params: dict[str, str]) -> _Reply:
        db = store.open_db(self._service.root)  # this request's own connection
        try:
            user = identity.current_user(db, self._cookie())
            if user is None and not route.open_to_all:
                raise _refuse(401, _NEEDS_NAME)
            return route.handler(
                _Req(db, user, captured, params, self._json_body, self._service.loop)
            )
        finally:
            db.close()


def _wildcard(host: str) -> bool:
    """True when ``host`` is empty or resolves to an address that means every interface."""
    if not host:
        return True
    try:
        found = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError):
        return False  # not an address: binding it fails with its own message
    for *_, sockaddr in found:
        address = ipaddress.ip_address(str(sockaddr[0]).partition("%")[0])
        mapped = getattr(address, "ipv4_mapped", None)
        if address.is_unspecified or (mapped is not None and mapped.is_unspecified):
            return True
    return False


def _hosts(host: str, port: int) -> frozenset[str]:
    names = [host, "localhost"] if host == "127.0.0.1" else [host]
    allowed = {f"{name}:{port}" for name in names}
    if port == 80:
        allowed.update(names)  # a browser leaves the default port out of Host
    return frozenset(allowed)


def make_server(
    root: Path, host: str, port: int, *, loop: Loop | None = None
) -> ThreadingHTTPServer:
    """A server bound to ``host:port`` (port 0 picks one); not yet serving.

    Raises ValueError for a wildcard host, before binding or creating any file."""
    if _wildcard(host):
        raise ValueError(WILDCARD_MESSAGE)
    server = _Server((host, port), Handler)
    port = server.server_address[1]
    server.root, server.allowed_hosts, server.advertised_port = root, _hosts(host, port), port
    server.loop = loop
    return server


def serve(root: Path, host: str, port: int, *, tick: float = 60.0) -> int:
    """Run the service and its ingest loop until interrupted; 2 when it cannot start."""
    if not 0 <= port <= 65535:
        print("--port must be from 0 to 65535", file=sys.stderr)
        return 2
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    loop = Loop(root)
    try:
        server = make_server(root, host, port, loop=loop)
    except ValueError as error:  # a wildcard address
        print(error, file=sys.stderr)
        return 2
    except (OSError, OverflowError) as error:  # the address cannot be bound
        print(f"cannot listen on {host}:{port}: {error}", file=sys.stderr)
        return 2
    try:
        store.open_db(root).close()  # a store that cannot be opened fails here, not per request
    except (OSError, sqlite3.Error, store.StoreError) as error:
        server.server_close()
        print(f"cannot open the store under {root}: {error}", file=sys.stderr)
        return 2
    stop = threading.Event()
    worker = threading.Thread(target=loop.run_until, args=(stop, tick), daemon=True)
    worker.start()
    print(f"serving http://{host}:{server.server_address[1]}/", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()
        worker.join(timeout=5)
    return 0
