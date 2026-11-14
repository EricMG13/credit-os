"""Read side of Signal: feed pages, search, new-story counts and saves.

Every statement here is one static string; nothing is assembled from data. A view and each filter
are parameters the statement tests (`:kind IS NULL OR ...`), so one page statement serves every
view and filter combination, except a search, which has a statement of its own (`_PAGE_SEARCH`).
A page is read inside `store.read_snapshot`, and the groups a user can see are read once per
page, in that snapshot, from `groups.visible_group_ids`; the card-threads statement binds them as
a JSON list. No copy of the visibility rule lives here. The membership clauses (a thread in a
group the user belongs to) are a different rule, stated in the page and count statements, and a
test compares them with `groups.members`.

Input errors: a request-shaped value that is wrong (an unknown view, kind or topic, a malformed
cursor or id text, a story that does not exist) is a `ViewError`, which the service answers with
a 400 or 404. A value of the wrong type or an unclean name is a `StoreError`, a caller's bug.
`StoreUnusable` is never caught here. An error text carries at most 120 characters of input.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import NotRequired, TypedDict, Unpack

from credit_os.signal.groups import visible_group_ids
from credit_os.signal.identity import require_name
from credit_os.signal.store import (
    KINDS,
    StoreError,
    StoreUnusable,
    in_range,
    read_snapshot,
    require_text,
    utc_text,
    write_transaction,
)
from credit_os.signal.topics import fts_phrase

PAGE = 30
MAX_QUERY = 100
MAX_ID = 2**63 - 1
_SHOWN = 120


class ViewError(ValueError):
    """An unknown view, kind, topic or story, or a malformed cursor."""


@dataclass(frozen=True)
class CardThread:
    id: int
    group: str
    comments: int
    shared_by: str | None
    note: str | None


@dataclass(frozen=True)
class Card:
    id: int
    title: str
    link: str
    summary: str
    source: str
    kind: str
    published_at: str
    other_sources: int
    saved: bool
    topics: tuple[str, ...]
    threads: tuple[CardThread, ...]


@dataclass(frozen=True)
class Page:
    cards: tuple[Card, ...]
    next_before: str | None
    newest: int  # highest story id in the whole store when the page was read; 0 if empty


class Filters(TypedDict):
    """Optional keyword arguments of `feed`."""

    kind: NotRequired[str | None]
    query: NotRequired[str]
    before: NotRequired[str | None]
    shared: NotRequired[bool]


_FILTER_KEYS = frozenset({"kind", "query", "before", "shared"})

# The page statements: one for every view (`:view` is latest, foryou, saved or topic) and every
# filter (a filter that is not asked for arrives as NULL, or 0 for `:shared`, and drops out).
# A search has a statement of its own, `_PAGE_SEARCH`, so that SQLite drives it from the FTS
# table (`s.id IN (...)` with no OR beside it): a rare or absent term then costs O(hits), not
# O(stories). Both are constant texts joined here, once, at import (R2, R44).
# `foryou` is a followed topic or a thread in a group the user is a member of (membership, not
# mere visibility). `:shared` is a thread in a group the user is a member of that another person
# started. The cursor is (published_at, id) strictly below `:stamp`, `:cursor_id`.
_PAGE_HEAD = (
    "SELECT s.id, s.title, s.link, s.summary, s.published_at, src.name AS source,"
    " src.kind AS kind,"
    " (SELECT COUNT(DISTINCT d.duplicate_source_id) FROM story_duplicates d"
    "  WHERE d.story_id = s.id) AS other_sources,"
    " EXISTS(SELECT 1 FROM saves me WHERE me.story_id = s.id AND me.user_name = :user) AS saved"
    " FROM stories s JOIN sources src ON src.id = s.source_id"
    " WHERE (:view = 'latest'"
    "  OR (:view = 'foryou' AND ("
    "   EXISTS(SELECT 1 FROM topic_stories ts JOIN topic_follows f ON f.topic_id = ts.topic_id"
    "    WHERE ts.story_id = s.id AND f.user_name = :user)"
    "   OR EXISTS(SELECT 1 FROM threads mt JOIN group_members mm ON mm.group_id = mt.group_id"
    "    WHERE mt.story_id = s.id AND mm.user_name = :user)))"
    "  OR (:view = 'saved'"
    "   AND EXISTS(SELECT 1 FROM saves v WHERE v.story_id = s.id AND v.user_name = :user))"
    "  OR (:view = 'topic'"
    "   AND EXISTS(SELECT 1 FROM topic_stories ts WHERE ts.story_id = s.id"
    "    AND ts.topic_id = :topic)))"
    " AND (:kind IS NULL OR src.kind = :kind)"
)
_MATCH = " AND s.id IN (SELECT rowid FROM stories_fts WHERE stories_fts MATCH :match)"
_PAGE_TAIL = (
    " AND (:shared = 0 OR EXISTS(SELECT 1 FROM threads mt"
    "  JOIN group_members mm ON mm.group_id = mt.group_id"
    "  WHERE mt.story_id = s.id AND mm.user_name = :user"
    "  AND mt.started_by IS NOT NULL AND mt.started_by <> :user))"
    " AND (:stamp IS NULL OR s.published_at < :stamp"
    "  OR (s.published_at = :stamp AND s.id < :cursor_id))"
    " ORDER BY s.published_at DESC, s.id DESC LIMIT :limit"
)
_PAGE = _PAGE_HEAD + _PAGE_TAIL
_PAGE_SEARCH = _PAGE_HEAD + _MATCH + _PAGE_TAIL

# The count statement: the view conditions of `_PAGE`, no filters, ids above `:after`.
_COUNT = (
    "SELECT COUNT(*) FROM stories s WHERE s.id > :after"
    " AND (:view = 'latest'"
    "  OR (:view = 'foryou' AND ("
    "   EXISTS(SELECT 1 FROM topic_stories ts JOIN topic_follows f ON f.topic_id = ts.topic_id"
    "    WHERE ts.story_id = s.id AND f.user_name = :user)"
    "   OR EXISTS(SELECT 1 FROM threads mt JOIN group_members mm ON mm.group_id = mt.group_id"
    "    WHERE mt.story_id = s.id AND mm.user_name = :user)))"
    "  OR (:view = 'saved'"
    "   AND EXISTS(SELECT 1 FROM saves v WHERE v.story_id = s.id AND v.user_name = :user))"
    "  OR (:view = 'topic'"
    "   AND EXISTS(SELECT 1 FROM topic_stories ts WHERE ts.story_id = s.id"
    "    AND ts.topic_id = :topic)))"
)

_CARD_ONE = (
    "SELECT s.id, s.title, s.link, s.summary, s.published_at, src.name AS source,"
    " src.kind AS kind,"
    " (SELECT COUNT(DISTINCT d.duplicate_source_id) FROM story_duplicates d"
    "  WHERE d.story_id = s.id) AS other_sources,"
    " EXISTS(SELECT 1 FROM saves me WHERE me.story_id = s.id AND me.user_name = ?) AS saved"
    " FROM stories s JOIN sources src ON src.id = s.source_id WHERE s.id = ?"
)

_TOPIC_NAMES = (
    "SELECT t.name FROM topic_stories ts JOIN topics t ON t.id = ts.topic_id"
    " WHERE ts.story_id=? ORDER BY t.id"
)

# The visible groups arrive as a JSON list of ids read from `groups.visible_group_ids`.
_CARD_THREADS = (
    "SELECT t.id, g.name AS grp, t.started_by,"
    " (SELECT COUNT(*) FROM comments c WHERE c.thread_id = t.id AND c.deleted_at IS NULL)"
    "  AS comments,"
    " (SELECT substr(c.text, 1, 140) FROM comments c WHERE c.thread_id = t.id"
    "  AND c.author = t.started_by AND c.deleted_at IS NULL ORDER BY c.id LIMIT 1) AS note"
    " FROM threads t JOIN groups g ON g.id = t.group_id"
    " WHERE t.story_id = ? AND t.group_id IN (SELECT value FROM json_each(?)) ORDER BY t.id"
)


def _shown(text: str) -> str:
    """The text for an error message: at most 120 characters of it."""
    return repr(text[:_SHOWN]) + ("..." if len(text) > _SHOWN else "")


def _text(value: object, what: str) -> str:
    if not isinstance(value, str):
        raise StoreError(f"{what} must be text")
    return value


def _id(number: str, what: str) -> int:
    """A decimal id that SQLite can hold, else ViewError."""
    if (
        not number.isascii()
        or not number.isdecimal()
        or len(number) > len(str(MAX_ID))  # before int(): a huge digit string raises ValueError
        or not in_range(int(number))
    ):
        raise ViewError(f"invalid {what} {_shown(number)}")
    return int(number)


def _instant(text: str, what: str) -> str:
    """The stored UTC text of a zoned ISO time, else ViewError."""
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ViewError(f"malformed {what} {_shown(text)}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ViewError(f"{what} {_shown(text)} has no time zone")
    try:
        return utc_text(parsed)
    except StoreUnusable:
        raise
    except StoreError as exc:  # a year-1 or year-9999 time with an offset leaves the UTC range
        raise ViewError(f"{what} {_shown(text)} is out of range") from exc


def _after(after: object) -> int:
    """A story id cursor: an int from 0 to MAX_ID, else ViewError."""
    if isinstance(after, bool) or not isinstance(after, int) or not 0 <= after <= MAX_ID:
        shown = _shown(after) if isinstance(after, str) else type(after).__name__
        raise ViewError(f"invalid after: {shown}")
    return after


def _cursor(before: str) -> tuple[str, int]:
    stamp, bar, number = before.rpartition("|")
    if not bar:
        raise ViewError(f"malformed cursor {_shown(before)}")
    return _instant(stamp, "cursor time"), _id(number, "cursor id")


def _story_id(story_id: object) -> int:
    """A story id: an int (not a bool) else StoreError; one SQLite cannot hold names no story."""
    if type(story_id) is not int:
        raise StoreError("story id must be an integer")
    if not in_range(story_id):
        raise ViewError("no story with that id")  # no number in the text: a huge int cannot print
    return story_id


def _search_match(query: str) -> str | None:
    require_text(query)
    terms = query[:MAX_QUERY].split()
    return " ".join(fts_phrase(term) for term in terms) if terms else None


def _view(db: sqlite3.Connection, view: object) -> tuple[str, int | None]:
    """The view's kind (latest, foryou, saved, topic) and topic id, else ViewError."""
    text = _text(view, "view")
    if text in ("latest", "foryou", "saved"):
        return text, None
    prefix, _, number = text.partition(":")
    if prefix == "topic" and number.isascii() and number.isdecimal():
        topic_id = _id(number, "topic id")
        if db.execute("SELECT 1 FROM topics WHERE id=?", (topic_id,)).fetchone() is None:
            raise ViewError(f"no topic with id {topic_id}")
        return "topic", topic_id
    raise ViewError(f"unknown view {_shown(text)}")


def _kind(kind: object) -> str | None:
    if kind is None:
        return None
    text = _text(kind, "kind")
    if text not in KINDS:
        raise ViewError(f"unknown kind {_shown(text)}")
    return text


def _filter_params(filters: Filters) -> dict[str, object]:
    """The page statement's filter parameters; nothing here reads the database. Validated in this
    order: the unknown key, the type of `shared`, then kind, search and cursor."""
    if not filters.keys() <= _FILTER_KEYS:
        raise StoreError("unknown feed filter")
    shared = filters.get("shared", False)
    if type(shared) is not bool:
        raise StoreError("shared must be true or false")
    kind = _kind(filters.get("kind"))
    match = _search_match(_text(filters.get("query", ""), "query"))
    before = filters.get("before")
    stamp: str | None = None
    cursor_id = 0
    if before is not None:
        stamp, cursor_id = _cursor(_text(before, "before"))
    return {
        "kind": kind,
        "match": match,
        "shared": int(shared),
        "stamp": stamp,
        "cursor_id": cursor_id,
    }


def _topic_names(db: sqlite3.Connection, story_id: int) -> tuple[str, ...]:
    rows = db.execute(_TOPIC_NAMES, (story_id,)).fetchall()
    return tuple(row["name"] for row in rows)


def _card_threads(db: sqlite3.Connection, visible: str, story_id: int) -> tuple[CardThread, ...]:
    found = db.execute(_CARD_THREADS, (story_id, visible)).fetchall()
    return tuple(
        CardThread(row["id"], row["grp"], row["comments"], row["started_by"], row["note"])
        for row in found
    )


def _card(db: sqlite3.Connection, visible: str, row: sqlite3.Row) -> Card:
    return Card(
        id=row["id"],
        title=row["title"],
        link=row["link"],
        summary=row["summary"],
        source=row["source"],
        kind=row["kind"],
        published_at=row["published_at"],
        other_sources=row["other_sources"],
        saved=bool(row["saved"]),
        topics=_topic_names(db, row["id"]),
        threads=_card_threads(db, visible, row["id"]),
    )


def _visible_json(db: sqlite3.Connection, user_name: str) -> str:
    """The ids of the groups the user can see, as JSON: read once per page, in its snapshot."""
    return json.dumps(visible_group_ids(db, user_name))


def card_for(db: sqlite3.Connection, user_name: str, story_id: int) -> Card:
    """The card of one story as the user sees it, else ViewError."""
    who = require_name(user_name)
    sid = _story_id(story_id)
    with read_snapshot(db):
        row = db.execute(_CARD_ONE, (who, sid)).fetchone()
        if row is None:
            raise ViewError(f"no story with id {sid}")
        return _card(db, _visible_json(db, who), row)


def feed(
    db: sqlite3.Connection,
    user_name: str,
    view: str,
    **filters: Unpack[Filters],
) -> Page:
    """One page of stories, newest first. Raises ViewError for an invalid request."""
    who = require_name(user_name)
    with read_snapshot(db):
        name, topic_id = _view(db, view)  # the view is refused before the filters
        wanted = _filter_params(filters)
        match = wanted.pop("match")
        rows = db.execute(
            _PAGE if match is None else _PAGE_SEARCH,
            {
                **wanted,
                **({} if match is None else {"match": match}),
                "user": who,
                "view": name,
                "topic": topic_id,
                "limit": PAGE + 1,
            },
        ).fetchall()
        visible = _visible_json(db, who)
        cards = tuple(_card(db, visible, row) for row in rows[:PAGE])
        newest = int(db.execute("SELECT COALESCE(MAX(id), 0) FROM stories").fetchone()[0])
    last = cards[-1] if len(rows) > PAGE else None
    return Page(cards, f"{last.published_at}|{last.id}" if last else None, newest)


def new_count(db: sqlite3.Connection, user_name: str, view: str, after: int) -> int:
    """Stories in the view with an id above `after`, the `newest` of an earlier page."""
    who = require_name(user_name)
    floor = _after(after)
    with read_snapshot(db):
        name, topic_id = _view(db, view)
        row = db.execute(
            _COUNT, {"after": floor, "user": who, "view": name, "topic": topic_id}
        ).fetchone()
    return int(row[0])


def _require_story(db: sqlite3.Connection, story_id: int) -> None:
    if db.execute("SELECT 1 FROM stories WHERE id=?", (story_id,)).fetchone() is None:
        raise ViewError(f"no story with id {story_id}")


def save(db: sqlite3.Connection, user_name: str, story_id: int) -> None:
    """Save a story for the user; saving it again changes nothing."""
    who = require_name(user_name)
    sid = _story_id(story_id)
    with write_transaction(db):
        _require_story(db, sid)
        db.execute(
            "INSERT OR IGNORE INTO saves(user_name, story_id, saved_at) VALUES(?, ?, ?)",
            (who, sid, utc_text(datetime.now(UTC))),
        )


def unsave(db: sqlite3.Connection, user_name: str, story_id: int) -> None:
    """Remove the user's save of a story; one not saved is a no-op."""
    who = require_name(user_name)
    sid = _story_id(story_id)
    with write_transaction(db):
        _require_story(db, sid)
        db.execute("DELETE FROM saves WHERE user_name=? AND story_id=?", (who, sid))
