"""Topics: a named keyword rule over stories, matched through the full-text index, and follows."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from datetime import UTC, datetime

from credit_os.signal.identity import cleaned, require_name
from credit_os.signal.store import (
    KINDS,
    StoreError,
    new_row_id,
    require_id,
    utc_text,
    write_transaction,
)

MAX_KEYWORD = 60
MAX_KEYWORDS = 60
MAX_TOPIC_NAME = 200
MAX_TOPICS = 200
_MAX_KIND = max(len(kind) for kind in KINDS)


def fts_phrase(text: str) -> str:
    """`text` as one quoted FTS5 phrase, so query syntax in it is plain text."""
    return '"' + text.replace("\x00", " ").replace('"', '""') + '"'


def _text(value: object, what: str, limit: int) -> str:
    """A string no longer than `limit`; anything else is a StoreError.

    A lone surrogate, which SQLite cannot encode, never gets past the callers: clean text and
    names drop it, and a kind with one is not a kind."""
    if not isinstance(value, str):
        raise StoreError(f"{what} must be text")
    if len(value) > limit:
        raise StoreError(f"{what} must be at most {limit} characters")
    return value


def _id(number: object, what: str) -> int:
    if type(number) is not int:
        raise StoreError(f"{what} id must be an integer")
    require_id(number, what)
    return number


def _clean_text(value: object, what: str, limit: int) -> str:
    """`value` itself when it is clean text: what `identity.cleaned` returns unchanged.

    Refused, not repaired: the text a user typed is the text stored and shown. The length is
    checked first, so the cleaning never runs on a long input."""
    text = _text(value, what, limit)
    if not cleaned(text):
        raise StoreError(f"{what} must not be empty")
    if cleaned(text) != text:
        raise StoreError(
            f"{what} must be clean text: no control or invisible characters, one space between"
            " words, none at the ends, composed form"
        )
    return text


def _listed(values: object, what: str) -> Sequence[object]:
    """A list or tuple; a bare string is not a list of one."""
    if not isinstance(values, (list, tuple)):
        raise StoreError(f"{what} must be a list of text")
    return values


def _clean_keywords(keywords: object) -> list[str]:
    listed = _listed(keywords, "keywords")
    if not listed:
        raise StoreError("a topic needs at least one keyword")
    if len(listed) > MAX_KEYWORDS:
        raise StoreError(f"a topic holds at most {MAX_KEYWORDS} keywords")
    return [_clean_text(keyword, "keyword", MAX_KEYWORD) for keyword in listed]


def _clean_kinds(kinds: object) -> list[str]:
    texts = [_text(kind, "kind", _MAX_KIND) for kind in _listed(kinds, "kinds")]
    for kind in texts:
        if kind not in KINDS:
            raise StoreError(f"invalid kind; expected one of {', '.join(KINDS)}")
    return texts


def _matches(db: sqlite3.Connection, story_id: int, topic: sqlite3.Row) -> bool:
    """Whether the story meets the topic's rule; one phrase query per keyword."""
    kinds = json.loads(topic["kinds"])
    if kinds:
        kind = db.execute(
            "SELECT src.kind FROM stories s JOIN sources src ON src.id = s.source_id WHERE s.id=?",
            (story_id,),
        ).fetchone()
        if kind is None or kind["kind"] not in kinds:
            return False
    return any(
        db.execute(
            "SELECT 1 FROM stories_fts WHERE stories_fts MATCH ? AND rowid=?",
            (fts_phrase(keyword), story_id),
        ).fetchone()
        for keyword in json.loads(topic["keywords"])
    )


def _link(db: sqlite3.Connection, topic_id: int, story_id: int) -> None:
    db.execute(
        "INSERT OR IGNORE INTO topic_stories(topic_id, story_id) VALUES(?, ?)",
        (topic_id, story_id),
    )


def match_story(db: sqlite3.Connection, story_id: int) -> list[int]:
    """Topic ids whose rule the story meets; records them. Safe to repeat."""
    _id(story_id, "story")
    with write_transaction(db):
        found = [
            topic["id"]
            for topic in db.execute("SELECT * FROM topics ORDER BY id").fetchall()
            if _matches(db, story_id, topic)
        ]
        for topic_id in found:
            _link(db, topic_id, story_id)
    return found


def _link_existing(
    db: sqlite3.Connection, topic_id: int, keywords: Sequence[str], kinds: Sequence[str]
) -> None:
    """Link every stored story that meets the rule: one index query per keyword, not per story.

    One static statement: the kinds travel as a JSON array read through `json_each`, so an empty
    list means every kind and no SQL text is assembled from data."""
    kinds_json = json.dumps(list(kinds))
    for keyword in keywords:
        db.execute(
            "INSERT OR IGNORE INTO topic_stories(topic_id, story_id)"
            " SELECT ?, s.id FROM stories_fts JOIN stories s ON s.id = stories_fts.rowid"
            " JOIN sources src ON src.id = s.source_id"
            " WHERE stories_fts MATCH ?"
            " AND (json_array_length(?) = 0 OR src.kind IN (SELECT value FROM json_each(?)))",
            (topic_id, fts_phrase(keyword), kinds_json, kinds_json),
        )


def add_topic(
    db: sqlite3.Connection,
    name: str,
    keywords: Sequence[str],
    kinds: Sequence[str],
    created_by: str,
) -> int:
    """Create a topic and match every existing story against it before returning."""
    _clean_text(name, "name", MAX_TOPIC_NAME)
    require_name(created_by)
    words = _clean_keywords(keywords)
    allowed = _clean_kinds(kinds)
    with write_transaction(db):
        if db.execute("SELECT count(*) FROM topics").fetchone()[0] >= MAX_TOPICS:
            raise StoreError(f"at most {MAX_TOPICS} topics are allowed")
        try:
            cur = db.execute(
                "INSERT INTO topics(name, keywords, kinds, created_by, created_at)"
                " VALUES(?, ?, ?, ?, ?)",
                (name, json.dumps(words), json.dumps(allowed), created_by, utc_text(_now())),
            )
        except sqlite3.IntegrityError as exc:
            raise StoreError("a topic with that name already exists") from exc
        topic_id = new_row_id(cur)
        _link_existing(db, topic_id, words, allowed)
    return topic_id


def _now() -> datetime:
    return datetime.now(UTC)


def _require_topic(db: sqlite3.Connection, topic_id: int) -> None:
    if db.execute("SELECT 1 FROM topics WHERE id=?", (_id(topic_id, "topic"),)).fetchone() is None:
        raise StoreError(f"no topic with id {topic_id}")


def follow(db: sqlite3.Connection, user_name: str, topic_id: int) -> None:
    require_name(user_name)
    _id(topic_id, "topic")
    with write_transaction(db):
        _require_topic(db, topic_id)
        db.execute(
            "INSERT OR IGNORE INTO topic_follows(user_name, topic_id) VALUES(?, ?)",
            (user_name, topic_id),
        )


def unfollow(db: sqlite3.Connection, user_name: str, topic_id: int) -> None:
    require_name(user_name)
    _id(topic_id, "topic")
    with write_transaction(db):
        _require_topic(db, topic_id)
        db.execute(
            "DELETE FROM topic_follows WHERE user_name=? AND topic_id=?", (user_name, topic_id)
        )


def list_topics(db: sqlite3.Connection, user_name: str) -> list[sqlite3.Row]:
    """Every topic with whether `user_name` follows it and how many stories it holds."""
    require_name(user_name)
    return db.execute(
        "SELECT t.id, t.name,"
        " EXISTS(SELECT 1 FROM topic_follows f WHERE f.topic_id = t.id AND f.user_name = ?)"
        "  AS following,"
        " (SELECT COUNT(*) FROM topic_stories ts WHERE ts.topic_id = t.id) AS stories"
        " FROM topics t ORDER BY t.id",
        (user_name,),
    ).fetchall()
