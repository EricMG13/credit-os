"""Threads, comments and reactions inside groups.

Order of checks (a wrong type or an unusable text is a `StoreError`, a caller's bug):
1. Before any transaction: the type of the actor and the time, the type (an integer, not its
   range) of the thread, comment and story ids, the type of a note, and every text (cleaned,
   then refused when empty, too long or, for a title, on more than one line). The refusal of a
   text never depends on a group, thread or comment, so a hidden target and a missing one still
   answer alike, and no write lock is held while a long text is cleaned. `auto_post` also
   range-checks its story and topic ids here.
2. Inside the transaction: visibility (a hidden group, thread or comment answers like a missing
   one: the same `groups.NotFound`, the same text; a group id's type is judged here), then role
   (`groups.Forbidden`), then what only the rows can tell: the range of a story id in
   `share_story` (after visibility and role), a story that does not exist, a reply's parent, a
   reaction's key and a removed comment. An id outside SQLite's range of a thread or comment
   answers like a missing one (`NotFound`; a reply's parent, a `StoreError`).
Roles (R22, amended by R54): only a writer or the owner starts a thread or comments; a reaction
needs a registered user (a `users` row, any role; a typed name is not authentication, so this
bounds invented names per registration only); an unregistered name still reads and may mark
threads read. Reads run in `store.read_snapshot`, writes in `store.write_transaction`. Every
statement is one constant text; `StoreUnusable` is never caught. An error text carries no caller
text except `thread_list`'s malformed-cursor `ViewError`, which quotes up to 120 characters of the
cursor (R10's cut). It may carry a number: a limit, or `share_story`'s story id (`no story with
id N`, an integer already range-checked, at most 19 digits). No refusal carries a topic id.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from credit_os.signal import feedview
from credit_os.signal.groups import (
    Act,
    Forbidden,
    NotFound,
    can_see,
    may_post,
    require_act,
    require_stamp,
    require_user,
    require_visible,
)
from credit_os.signal.identity import User, cleaned_text, require_name
from credit_os.signal.store import (
    StoreError,
    in_range,
    new_row_id,
    read_snapshot,
    require_id,
    role_of,
    write_transaction,
)

EDIT_WINDOW = timedelta(minutes=15)
MAX_TEXT = 4000
MAX_TITLE = 120
MAX_COMMENTS = 500
REACTIONS = ("agree", "disagree", "seen")
PAGE = 30
_NO_THREAD = "no such thread"
_NO_COMMENT = "no such comment"


@dataclass(frozen=True)
class Reaction:
    key: str
    count: int
    mine: bool


@dataclass(frozen=True)
class Comment:
    id: int
    parent_id: int | None
    author: str
    role: str
    text: str
    created_at: str
    edited: bool
    removed: bool
    reactions: tuple[Reaction, ...]
    mine: bool
    editable: bool


@dataclass(frozen=True)
class Unread:
    replies: int
    threads: int
    by_group: dict[int, int]


@dataclass(frozen=True)
class ThreadRow:
    id: int
    kind: Literal["story", "note"]
    title: str
    source: str | None
    source_kind: str | None
    started_by: str | None
    comments: int
    last_activity_at: str
    unread: bool


@dataclass(frozen=True)
class ThreadView:
    id: int
    group_id: int
    group: str
    story: feedview.Card | None
    title: str | None
    started_by: str | None
    comments: tuple[Comment, ...]
    can_post: bool


def _actor(by: object) -> tuple[User, str, str]:
    """The acting user, their clean name and the time as UTC text, else a StoreError."""
    user, stamp = require_act(by)
    return user, require_name(user.name), stamp


def _user(user: object) -> tuple[User, str]:
    checked = require_user(user)
    return checked, require_name(checked.name)


def _id(value: object, what: str) -> int:
    if type(value) is not int:
        raise StoreError(f"{what} id must be an integer")
    return value


def clean_text(raw: str, limit: int, *, multiline: bool = True) -> str:
    """Text as stored, cleaned by `identity.cleaned_text` (a title is one line). Empty or longer
    than `limit` is refused, never cut."""
    text = cleaned_text(raw, multiline=multiline)
    if not text:
        raise StoreError("text is empty")
    if len(text) > limit:
        raise StoreError(f"text is longer than {limit} characters")
    return text


def _thread_row(db: sqlite3.Connection, user_name: str, thread_id: int) -> sqlite3.Row:
    """The thread row when its group is visible; a missing and a hidden thread look the same."""
    row: sqlite3.Row | None = (
        db.execute("SELECT * FROM threads WHERE id=?", (thread_id,)).fetchone()
        if in_range(thread_id)
        else None
    )
    if row is None or not can_see(db, user_name, row["group_id"]):
        raise NotFound(_NO_THREAD)
    return row


def _comment_row(db: sqlite3.Connection, user_name: str, comment_id: int) -> sqlite3.Row:
    """The comment row when its thread's group is visible, else "no such comment"."""
    row: sqlite3.Row | None = (
        db.execute(
            "SELECT c.*, t.group_id FROM comments c JOIN threads t ON t.id = c.thread_id"
            " WHERE c.id=?",
            (comment_id,),
        ).fetchone()
        if in_range(comment_id)
        else None
    )
    if row is None or not can_see(db, user_name, row["group_id"]):
        raise NotFound(_NO_COMMENT)
    return row


def _insert_comment(
    db: sqlite3.Connection, name: str, stamp: str, thread_id: int, parent_id: int | None, text: str
) -> int:
    """Append a comment (the caller holds the write transaction and has cleaned the text)."""
    taken = db.execute("SELECT COUNT(*) FROM comments WHERE thread_id=?", (thread_id,)).fetchone()
    if taken[0] >= MAX_COMMENTS:
        raise StoreError("this thread is full")
    cur = db.execute(
        "INSERT INTO comments(thread_id, parent_id, author, text, created_at)"
        " VALUES(?, ?, ?, ?, ?)",
        (thread_id, parent_id, name, text, stamp),
    )
    db.execute(
        "UPDATE threads SET last_activity_at = MAX(last_activity_at, ?) WHERE id=?",
        (stamp, thread_id),
    )
    return new_row_id(cur)


def share_story(
    db: sqlite3.Connection, by: Act, group_id: int, story_id: int, note: str | None
) -> tuple[int, bool]:
    """Put a story in a group: `(thread_id, joined)`, joined when the thread already existed.

    A share that joins an automatic thread (no sharer yet) claims it, in the same transaction and
    only while it has none; the claim also moves the thread's `created_at` and `last_activity_at`
    up to the share (never back), with or without a note: a member who joined after the automatic
    post and before the claim sees a new thread (P17), and it sorts where new activity sorts (R56)."""
    user, name, stamp = _actor(by)
    sid = _id(story_id, "story")
    if note is not None and not isinstance(note, str):
        raise StoreError("a note must be text")
    text = cleaned_text(note, multiline=True) if note is not None else ""
    if len(text) > MAX_TEXT:
        raise StoreError(f"text is longer than {MAX_TEXT} characters")
    with write_transaction(db):
        require_visible(db, name, group_id)
        if not may_post(user):
            raise Forbidden("only writers and the owner can share stories")
        require_id(sid, "story")
        if db.execute("SELECT 1 FROM stories WHERE id=?", (sid,)).fetchone() is None:
            raise StoreError(f"no story with id {sid}")
        cur = db.execute(
            "INSERT OR IGNORE INTO threads(group_id, story_id, started_by, created_at,"
            " last_activity_at) VALUES(?, ?, ?, ?, ?)",
            (group_id, sid, name, stamp, stamp),
        )
        joined = cur.rowcount == 0
        if joined:
            found = db.execute(
                "SELECT id FROM threads WHERE group_id=? AND story_id=?", (group_id, sid)
            ).fetchone()
            thread_id = int(found["id"])
            db.execute(  # an automatic post has no sharer; this share claims it
                "UPDATE threads SET started_by = ?, created_at = MAX(created_at, ?),"
                " last_activity_at = MAX(last_activity_at, ?)"
                " WHERE id = ? AND started_by IS NULL",
                (name, stamp, stamp, thread_id),
            )
        else:
            thread_id = new_row_id(cur)
        if text:
            _insert_comment(db, name, stamp, thread_id, None, text)
    return thread_id, joined


def start_note(db: sqlite3.Connection, by: Act, group_id: int, title: str, text: str) -> int:
    """A thread with no story; the text is its first comment."""
    user, name, stamp = _actor(by)
    clean_title = clean_text(title, MAX_TITLE, multiline=False)
    body = clean_text(text, MAX_TEXT)
    with write_transaction(db):
        require_visible(db, name, group_id)
        if not may_post(user):
            raise Forbidden("only writers and the owner can start notes")
        cur = db.execute(
            "INSERT INTO threads(group_id, title, started_by, created_at, last_activity_at)"
            " VALUES(?, ?, ?, ?, ?)",
            (group_id, clean_title, name, stamp, stamp),
        )
        thread_id = new_row_id(cur)
        _insert_comment(db, name, stamp, thread_id, None, body)
    return thread_id


def add_comment(
    db: sqlite3.Connection, by: Act, thread_id: int, text: str, parent_id: int | None
) -> int:
    user, name, stamp = _actor(by)
    tid = _id(thread_id, "thread")
    parent = None if parent_id is None else _id(parent_id, "comment")
    body = clean_text(text, MAX_TEXT)
    with write_transaction(db):
        _thread_row(db, name, tid)
        if not may_post(user):
            raise Forbidden("only writers and the owner can comment")
        if parent is not None:
            above = (
                db.execute(
                    "SELECT thread_id, parent_id FROM comments WHERE id=?", (parent,)
                ).fetchone()
                if in_range(parent)
                else None
            )
            if above is None or above["thread_id"] != tid:
                raise StoreError("no such comment in this thread to reply to")
            if above["parent_id"] is not None:
                raise StoreError("replies nest one level; reply to the top-level comment")
        return _insert_comment(db, name, stamp, tid, parent, body)


def edit_comment(db: sqlite3.Connection, by: Act, comment_id: int, text: str) -> None:
    _, name, stamp = _actor(by)
    cid = _id(comment_id, "comment")
    body = clean_text(text, MAX_TEXT)
    with write_transaction(db):
        row = _comment_row(db, name, cid)
        if row["author"] != name or row["deleted_at"] is not None:
            raise Forbidden("only the author can edit a comment, and not a removed one")
        if by.now - datetime.fromisoformat(row["created_at"]) > EDIT_WINDOW:
            raise Forbidden("a comment can be edited for 15 minutes")
        db.execute("UPDATE comments SET text=?, edited_at=? WHERE id=?", (body, stamp, cid))


def delete_comment(db: sqlite3.Connection, by: Act, comment_id: int) -> None:
    """Remove a comment: it keeps its place, loses its text and reactions. Repeating is safe."""
    _, name, stamp = _actor(by)
    cid = _id(comment_id, "comment")
    with write_transaction(db):
        row = _comment_row(db, name, cid)
        if row["author"] != name:
            raise Forbidden("only the author can delete a comment")
        if row["deleted_at"] is not None:
            return
        db.execute("UPDATE comments SET text='', deleted_at=? WHERE id=?", (stamp, cid))
        db.execute("DELETE FROM reactions WHERE comment_id=?", (cid,))


def _reaction_target(db: sqlite3.Connection, name: str, comment_id: int, key: object) -> None:
    """Visibility, then a registered user (R54), then the key, then a removed comment."""
    row = _comment_row(db, name, comment_id)
    if db.execute("SELECT 1 FROM users WHERE name=?", (name,)).fetchone() is None:
        raise Forbidden("only registered users can react")
    if not isinstance(key, str):
        raise StoreError("a reaction must be text")
    if key not in REACTIONS:
        raise StoreError(f"invalid reaction; expected one of {', '.join(REACTIONS)}")
    if row["deleted_at"] is not None:
        raise StoreError("that comment was removed")


def react(db: sqlite3.Connection, user: User, comment_id: int, key: str) -> None:
    _, name = _user(user)
    cid = _id(comment_id, "comment")
    with write_transaction(db):
        _reaction_target(db, name, cid, key)
        db.execute(
            "INSERT OR IGNORE INTO reactions(comment_id, user_name, key) VALUES(?, ?, ?)",
            (cid, name, key),
        )


def unreact(db: sqlite3.Connection, user: User, comment_id: int, key: str) -> None:
    _, name = _user(user)
    cid = _id(comment_id, "comment")
    with write_transaction(db):
        _reaction_target(db, name, cid, key)
        db.execute(
            "DELETE FROM reactions WHERE comment_id=? AND user_name=? AND key=?",
            (cid, name, key),
        )


def _reactions(
    db: sqlite3.Connection, thread_id: int, user_name: str
) -> dict[int, tuple[Reaction, ...]]:
    found = db.execute(
        "SELECT r.comment_id, r.key, COUNT(*) AS n, MAX(r.user_name = ?) AS mine"
        " FROM reactions r JOIN comments c ON c.id = r.comment_id WHERE c.thread_id=?"
        " GROUP BY r.comment_id, r.key",
        (user_name, thread_id),
    ).fetchall()
    by_comment: dict[int, dict[str, Reaction]] = {}
    for row in found:
        by_comment.setdefault(row["comment_id"], {})[row["key"]] = Reaction(
            row["key"], row["n"], bool(row["mine"])
        )
    return {
        comment_id: tuple(keyed[key] for key in REACTIONS if key in keyed)
        for comment_id, keyed in by_comment.items()
    }


def _comments(
    db: sqlite3.Connection, thread_id: int, name: str, now: datetime
) -> tuple[Comment, ...]:
    reactions = _reactions(db, thread_id, name)
    roles: dict[str, str] = {}
    out: list[Comment] = []
    for row in db.execute(
        "SELECT * FROM comments WHERE thread_id=? ORDER BY id", (thread_id,)
    ).fetchall():
        author = row["author"]
        if author not in roles:
            roles[author] = role_of(db, author)
        removed = row["deleted_at"] is not None
        mine = author == name
        out.append(
            Comment(
                id=row["id"],
                parent_id=row["parent_id"],
                author=author,
                role=roles[author],
                text=row["text"],
                created_at=row["created_at"],
                edited=row["edited_at"] is not None,
                removed=removed,
                reactions=reactions.get(row["id"], ()),
                mine=mine,
                editable=mine
                and not removed
                and now - datetime.fromisoformat(row["created_at"]) <= EDIT_WINDOW,
            )
        )
    return tuple(out)


def read_thread(db: sqlite3.Connection, user: User, thread_id: int, now: datetime) -> ThreadView:
    who, name = _user(user)
    tid = _id(thread_id, "thread")
    require_stamp(now)
    with read_snapshot(db):
        thread = _thread_row(db, name, tid)
        group = require_visible(db, name, thread["group_id"])
        story = (
            feedview.card_in_snapshot(db, name, thread["story_id"])
            if thread["story_id"] is not None
            else None
        )
        return ThreadView(
            id=thread["id"],
            group_id=group["id"],
            group=group["name"],
            story=story,
            title=thread["title"],
            started_by=thread["started_by"],
            comments=_comments(db, tid, name, now),
            can_post=may_post(who),
        )


def auto_post(
    db: sqlite3.Connection, story_id: int, topic_ids: Sequence[int], now: datetime
) -> list[int]:
    """A thread for the story in each group carrying one of the topics, unless one exists.
    Returns the new thread ids."""
    sid = _id(story_id, "story")
    require_id(sid, "story")
    if not isinstance(topic_ids, (list, tuple)):
        raise StoreError("topic ids must be a list of integers")
    for topic_id in topic_ids:
        require_id(_id(topic_id, "topic"), "topic")
    stamp = require_stamp(now)
    if not topic_ids:
        return []
    created: list[int] = []
    with write_transaction(db):
        found = db.execute(
            "SELECT DISTINCT gt.group_id FROM group_topics gt"
            " WHERE gt.topic_id IN (SELECT value FROM json_each(?))"
            " AND EXISTS(SELECT 1 FROM stories WHERE id=?) ORDER BY gt.group_id",
            (json.dumps(list(topic_ids)), sid),
        ).fetchall()
        for row in found:
            cur = db.execute(
                "INSERT OR IGNORE INTO threads(group_id, story_id, started_by, created_at,"
                " last_activity_at) VALUES(?, ?, NULL, ?, ?)",
                (row["group_id"], sid, stamp, stamp),
            )
            if cur.rowcount:
                created.append(new_row_id(cur))
    return created


# A thread that is new to `:user`: in a group they belong to, made at or after they joined,
# started by someone else (not automatic), never read.
_NEW_THREAD = (
    "(t.started_by IS NOT NULL AND t.started_by <> :user"
    " AND EXISTS(SELECT 1 FROM group_members m WHERE m.group_id = t.group_id"
    "  AND m.user_name = :user AND t.created_at >= m.joined_at)"
    " AND NOT EXISTS(SELECT 1 FROM read_marks r WHERE r.user_name = :user AND r.thread_id = t.id))"
)

# One page of a group's threads: the cursor is (last_activity_at, id) strictly below `:stamp`,
# `:cursor_id`; with no cursor `:stamp` is NULL and drops out.
_ROWS_HEAD = (
    "SELECT t.id, t.story_id, COALESCE(s.title, t.title) AS title, src.name AS source,"
    " src.kind AS source_kind, t.started_by, t.last_activity_at,"
    " (SELECT COUNT(*) FROM comments c WHERE c.thread_id = t.id AND c.deleted_at IS NULL)"
    "  AS comments, ("
)
_ROWS_TAIL = (
    " OR EXISTS(SELECT 1 FROM comments c WHERE c.thread_id = t.id"
    "  AND c.deleted_at IS NULL AND c.author <> :user AND c.id > COALESCE((SELECT r.seen_comment_id"
    "   FROM read_marks r WHERE r.user_name = :user AND r.thread_id = t.id), 0))) AS unread"
    " FROM threads t LEFT JOIN stories s ON s.id = t.story_id"
    " LEFT JOIN sources src ON src.id = s.source_id WHERE t.group_id = :group"
    " AND (:stamp IS NULL OR t.last_activity_at < :stamp"
    "  OR (t.last_activity_at = :stamp AND t.id < :cursor_id))"
    " ORDER BY t.last_activity_at DESC, t.id DESC LIMIT :limit"
)
_THREAD_ROWS = _ROWS_HEAD + _NEW_THREAD + _ROWS_TAIL


def thread_list(
    db: sqlite3.Connection, user_name: str, group_id: int, before: str | None
) -> tuple[tuple[ThreadRow, ...], str | None]:
    """One page of a group's threads by last activity, newest first, and the next cursor."""
    name = require_name(user_name)
    if before is not None and not isinstance(before, str):
        raise StoreError("before must be text")
    with read_snapshot(db):
        require_visible(db, name, group_id)
        stamp, cursor_id = (None, 0) if before is None else feedview.parse_cursor(before, ",")
        found = db.execute(
            _THREAD_ROWS,
            {
                "user": name,
                "group": group_id,
                "stamp": stamp,
                "cursor_id": cursor_id,
                "limit": PAGE + 1,
            },
        ).fetchall()
    page = tuple(
        ThreadRow(
            id=row["id"],
            kind="story" if row["story_id"] is not None else "note",
            title=row["title"],
            source=row["source"],
            source_kind=row["source_kind"],
            started_by=row["started_by"],
            comments=row["comments"],
            last_activity_at=row["last_activity_at"],
            unread=bool(row["unread"]),
        )
        for row in found[:PAGE]
    )
    last = page[-1] if len(found) > PAGE else None
    return page, f"{last.last_activity_at},{last.id}" if last else None


def mark_read(db: sqlite3.Connection, user_name: str, thread_id: int) -> None:
    """Mark everything in the thread seen; the mark only ever rises."""
    name = require_name(user_name)
    tid = _id(thread_id, "thread")
    with write_transaction(db):
        _thread_row(db, name, tid)
        newest = db.execute(
            "SELECT COALESCE(MAX(id), 0) FROM comments WHERE thread_id=?", (tid,)
        ).fetchone()[0]
        db.execute(
            "INSERT INTO read_marks(user_name, thread_id, seen_comment_id) VALUES(?, ?, ?)"
            " ON CONFLICT(user_name, thread_id) DO UPDATE SET"
            " seen_comment_id = MAX(seen_comment_id, excluded.seen_comment_id)",
            (name, tid, newest),
        )


_UNREAD_HEAD = "SELECT t.group_id AS gid, COUNT(*) AS n FROM threads t WHERE "
_UNREAD_TAIL = " GROUP BY t.group_id"
_UNREAD_THREADS = _UNREAD_HEAD + _NEW_THREAD + _UNREAD_TAIL

# Replies to `:user`'s comments, in the groups `:visible` (a JSON list of ids) names.
_UNREAD_REPLIES = (
    "SELECT t.group_id AS gid, COUNT(*) AS n FROM comments c"
    " JOIN comments p ON p.id = c.parent_id JOIN threads t ON t.id = c.thread_id"
    " WHERE t.group_id IN (SELECT value FROM json_each(:visible))"
    " AND c.deleted_at IS NULL AND c.author <> :user AND p.author = :user"
    " AND c.id > COALESCE((SELECT r.seen_comment_id FROM read_marks r"
    "  WHERE r.user_name = :user AND r.thread_id = t.id), 0)"
    " GROUP BY t.group_id"
)


def unread(db: sqlite3.Connection, user_name: str) -> Unread:
    """New threads in the user's groups and replies to the user's comments, not yet read."""
    name = require_name(user_name)
    with read_snapshot(db):
        new_threads = db.execute(_UNREAD_THREADS, {"user": name}).fetchall()
        replies = db.execute(
            _UNREAD_REPLIES, {"user": name, "visible": feedview.visible_json(db, name)}
        ).fetchall()
    by_group: dict[int, int] = {}
    for row in (*new_threads, *replies):
        by_group[row["gid"]] = by_group.get(row["gid"], 0) + row["n"]
    return Unread(
        replies=sum(row["n"] for row in replies),
        threads=sum(row["n"] for row in new_threads),
        by_group=by_group,
    )
