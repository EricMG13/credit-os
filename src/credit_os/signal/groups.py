"""Groups and membership, and the one rule that decides which groups a user can see.

Roles: `reader`, `writer` and `owner` (`store.ROLES`). A writer or the owner creates groups and
adds or removes members of a group they can see; a reader joins open groups, leaves the groups
they are in, and reads. A group that is hidden from a user and one that does not exist read the
same to them: the same `NotFound`, with the same text.

One exception, kept from the predecessor (ruling P12, R36): a group name is unique across all
groups, hidden ones included, so `create_group` refuses a name held by a group the caller cannot
see with "that group name is taken". A writer can learn that a hidden name exists, and can hold a
name nobody else sees; names are not folded across look-alike scripts. No rename or delete exists.

The role comes with the caller's `Act` or `User`, as the cookie lookup found it; it is not read
again inside the write transaction. Every other check a write depends on is made inside it.
"""

from __future__ import annotations

import json
import sqlite3
import unicodedata
from dataclasses import dataclass
from datetime import datetime

from credit_os.signal.identity import User, cleaned, require_name
from credit_os.signal.store import (
    StoreError,
    in_range,
    new_row_id,
    require_id,
    require_text,
    utc_text,
    write_transaction,
)

VISIBILITIES = ("everyone", "invited")
MAX_GROUP_NAME = 60
_NO_GROUP = "no such group"
_NEEDS_WRITER = "an invited group needs a writer member"


@dataclass(frozen=True)
class Act:
    """Who is acting and when."""

    user: User
    now: datetime


class Forbidden(Exception):
    """The user may not do this; the service answers 403."""


class NotFound(StoreError):
    """No such group, or one hidden from the caller; the service answers 404."""


def _name_key(name: str) -> str:
    """NFKC(casefold(NFKC(name))): one more NFKC after the fold, since folding can produce
    characters that have a compatibility form (U+03B0 and U+03AB U+0301 meet only that way)."""
    folded = unicodedata.normalize("NFKC", name).casefold()
    return unicodedata.normalize("NFKC", folded)


def require_user(user: object) -> User:
    if not isinstance(user, User):
        raise StoreError("the user must be a User")
    return user


def may_post(user: User) -> bool:
    """A writer or the owner may create groups and manage members."""
    return require_user(user).role in ("writer", "owner")


def require_stamp(now: object) -> str:
    if not isinstance(now, datetime):
        raise StoreError("time must be a datetime")
    return utc_text(now)


def require_act(by: object) -> tuple[User, str]:
    """The acting user and the time as UTC text, or a StoreError for anything else."""
    if not isinstance(by, Act):
        raise StoreError("the actor must be an Act holding a User")
    return require_user(by.user), require_stamp(by.now)


def _group_id(group_id: object) -> int:
    if type(group_id) is not int:
        raise StoreError("group id must be an integer")
    return group_id


def _who(user_name: object) -> str:
    """A user name used only to look rows up: any text SQLite can encode."""
    if not isinstance(user_name, str):
        raise StoreError("name must be text")
    require_text(user_name)
    return user_name


def _group_name(raw: object) -> str:
    """The cleaned group name; empty (or only characters that draw nothing) or too long is refused.

    Judged after cleaning and NFC, so the limit is on what is stored and shown."""
    if not isinstance(raw, str):
        raise StoreError("a group name must be text")
    name = cleaned(raw)
    if not name:
        raise StoreError("a group name must not be empty")
    if len(name) > MAX_GROUP_NAME:
        raise StoreError(f"a group name is at most {MAX_GROUP_NAME} characters")
    return name


def _topic_ids(topic_ids: object) -> list[int]:
    if not isinstance(topic_ids, (list, tuple)):
        raise StoreError("topic ids must be a list of integers")
    found: list[int] = []
    for topic_id in topic_ids:
        if type(topic_id) is not int:
            raise StoreError("topic id must be an integer")
        require_id(topic_id, "topic")
        found.append(topic_id)
    return found


def create_group(
    db: sqlite3.Connection,
    by: Act,
    name: str,
    visibility: str,
    topic_ids: list[int] | tuple[int, ...],
) -> int:
    """Create a group with the actor as its first member; return its id."""
    user, stamp = require_act(by)
    if not may_post(user):
        raise Forbidden("only writers and the owner can create groups")
    group_name = _group_name(name)
    if not isinstance(visibility, str) or visibility not in VISIBILITIES:
        raise StoreError("invalid visibility; expected one of everyone, invited")
    topics_json = json.dumps(_topic_ids(topic_ids))
    creator = require_name(user.name)
    with write_transaction(db):
        missing = db.execute(
            "SELECT j.value FROM json_each(?) j"
            " WHERE j.value NOT IN (SELECT id FROM topics) ORDER BY j.key LIMIT 1",
            (topics_json,),
        ).fetchone()
        if missing is not None:
            raise StoreError(f"no topic with id {missing[0]}")
        try:
            cur = db.execute(
                "INSERT INTO groups(name, name_key, visibility, created_by, created_at)"
                " VALUES(?, ?, ?, ?, ?)",
                (group_name, _name_key(group_name), visibility, creator, stamp),
            )
        except sqlite3.IntegrityError as exc:
            raise StoreError("that group name is taken") from exc
        group_id = new_row_id(cur)
        db.execute(
            "INSERT OR IGNORE INTO group_topics(group_id, topic_id)"
            " SELECT ?, j.value FROM json_each(?) j",
            (group_id, topics_json),
        )
        db.execute(
            "INSERT INTO group_members(group_id, user_name, joined_at) VALUES(?, ?, ?)",
            (group_id, creator, stamp),
        )
    return group_id


def _visible_row(db: sqlite3.Connection, user_name: str, group_id: int) -> sqlite3.Row | None:
    """The group row when it exists and is open to everyone or the user is a member.

    This statement and `list_groups` hold the visibility rule; a test compares them. An id
    SQLite cannot hold names no row, as a missing group does."""
    if not in_range(group_id):
        return None
    row: sqlite3.Row | None = db.execute(
        "SELECT g.* FROM groups g WHERE g.id = ? AND (g.visibility = 'everyone' OR EXISTS("
        "SELECT 1 FROM group_members vm WHERE vm.group_id = g.id AND vm.user_name = ?))",
        (group_id, user_name),
    ).fetchone()
    return row


def can_see(db: sqlite3.Connection, user_name: str, group_id: int) -> bool:
    """The group exists and is open to everyone, or the user is a member."""
    return _visible_row(db, _who(user_name), _group_id(group_id)) is not None


def require_visible(db: sqlite3.Connection, user_name: str, group_id: int) -> sqlite3.Row:
    """The group row; a missing group and a hidden one raise the same error."""
    row = _visible_row(db, _who(user_name), _group_id(group_id))
    if row is None:
        raise NotFound(_NO_GROUP)
    return row


def can_manage(db: sqlite3.Connection, user: User, group_id: int) -> bool:
    """The user may manage the group's members: a writer or the owner who can see it."""
    who = _who(require_user(user).name)
    gid = _group_id(group_id)
    return may_post(user) and _visible_row(db, who, gid) is not None


def join(db: sqlite3.Connection, user_name: str, group_id: int, now: datetime) -> None:
    """Join an open group; an invited group is only joined by being added (or already in)."""
    member = require_name(user_name)
    stamp = require_stamp(now)
    gid = _group_id(group_id)
    with write_transaction(db):
        require_visible(db, member, gid)
        db.execute(
            "INSERT OR IGNORE INTO group_members(group_id, user_name, joined_at) VALUES(?, ?, ?)",
            (gid, member, stamp),
        )


def _drop_member(db: sqlite3.Connection, group_id: int, user_name: str) -> None:
    """Delete one membership; refuse, before deleting, when that would leave an invited group with
    no manager: a member whose stored role is writer or owner, or its creator (who held that
    power when the group was made). A caller that catches the refusal and commits keeps the group
    as it was.

    A group that does not exist, or a user who is not in it, is a no-op: the same outcome whether
    the group is hidden from the caller or missing."""
    if not in_range(group_id):
        return
    orphaned = db.execute(
        "SELECT 1 FROM groups g WHERE g.id = ? AND g.visibility = 'invited'"
        " AND EXISTS(SELECT 1 FROM group_members d WHERE d.group_id = g.id AND d.user_name = ?)"
        " AND NOT EXISTS("
        "SELECT 1 FROM group_members m LEFT JOIN users u ON u.name = m.user_name"
        " WHERE m.group_id = g.id"
        " AND m.user_name <> ?"
        " AND (u.role IN ('writer', 'owner') OR m.user_name = g.created_by))",
        (group_id, user_name, user_name),
    ).fetchone()
    if orphaned:
        raise StoreError(_NEEDS_WRITER)
    db.execute("DELETE FROM group_members WHERE group_id=? AND user_name=?", (group_id, user_name))


def leave(db: sqlite3.Connection, user_name: str, group_id: int) -> None:
    """Leave a group; one not joined, hidden or missing is a no-op. An invited group keeps a manager."""
    name = _who(user_name)
    gid = _group_id(group_id)
    with write_transaction(db):
        _drop_member(db, gid, name)


def add_member(db: sqlite3.Connection, by: Act, group_id: int, name: str) -> str:
    """Add a member to a group the actor can see; return the name. Needs a writer or the owner."""
    actor, stamp = require_act(by)
    gid = _group_id(group_id)
    actor_name = _who(actor.name)
    with write_transaction(db):
        require_visible(db, actor_name, gid)
        if not may_post(actor):
            raise Forbidden("only writers and the owner can manage members")
        member = require_name(name)
        db.execute(
            "INSERT OR IGNORE INTO group_members(group_id, user_name, joined_at) VALUES(?, ?, ?)",
            (gid, member, stamp),
        )
    return member


def remove_member(db: sqlite3.Connection, actor: User, group_id: int, name: str) -> None:
    """Remove a member from a group the actor can see. Needs a writer or the owner."""
    if not isinstance(actor, User):
        raise StoreError("the actor must be a User")
    gid = _group_id(group_id)
    actor_name = _who(actor.name)
    with write_transaction(db):
        require_visible(db, actor_name, gid)
        if not may_post(actor):
            raise Forbidden("only writers and the owner can manage members")
        _drop_member(db, gid, require_name(name))


def visible_group_ids(db: sqlite3.Connection, user_name: str) -> list[int]:
    """The ids of the groups the user can see, ascending. A third copy of the visibility rule,
    for callers that filter other tables by group (compared with the other two in a test)."""
    who = _who(user_name)
    found = db.execute(
        "SELECT g.id FROM groups g WHERE (g.visibility = 'everyone' OR EXISTS("
        "SELECT 1 FROM group_members vm WHERE vm.group_id = g.id AND vm.user_name = ?))"
        " ORDER BY g.id",
        (who,),
    ).fetchall()
    return [int(row["id"]) for row in found]


def list_groups(db: sqlite3.Connection, user_name: str) -> list[sqlite3.Row]:
    """Visible groups by name: id, name, visibility, member flag, member and thread counts."""
    who = _who(user_name)
    return db.execute(
        "SELECT g.id, g.name, g.visibility,"
        " EXISTS(SELECT 1 FROM group_members m WHERE m.group_id = g.id AND m.user_name = ?)"
        "  AS member,"
        " (SELECT COUNT(*) FROM group_members m WHERE m.group_id = g.id) AS members,"
        " (SELECT COUNT(*) FROM threads t WHERE t.group_id = g.id) AS threads"
        " FROM groups g WHERE (g.visibility = 'everyone' OR EXISTS("
        "SELECT 1 FROM group_members vm WHERE vm.group_id = g.id AND vm.user_name = ?))"
        " ORDER BY g.name_key, g.id",
        (who, who),
    ).fetchall()


def members(db: sqlite3.Connection, user_name: str, group_id: int) -> list[str]:
    """The names in a group the user can see, in the order they joined."""
    require_visible(db, user_name, group_id)
    found = db.execute(
        "SELECT user_name FROM group_members WHERE group_id=? ORDER BY joined_at, rowid",
        (group_id,),
    ).fetchall()
    return [str(row["user_name"]) for row in found]
