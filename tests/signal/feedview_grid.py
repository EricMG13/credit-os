"""The grid state the feed view's rule tests share (one copy, imported by both rule files).

Expected values are written by hand from this data; none is computed with the code under test.
`threads.py` is not ported yet, so a thread is inserted with plain SQL.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from credit_os.signal.feeds import Entry
from credit_os.signal.feedview import save
from credit_os.signal.groups import Act, add_member, create_group, join
from credit_os.signal.identity import User
from credit_os.signal.store import (
    add_story,
    add_user,
    open_db,
    propose_source,
    set_source_state,
)
from credit_os.signal.topics import add_topic, follow

AK = User("ak", "writer")
T0 = datetime(2026, 11, 13, 9, tzinfo=UTC)
USERS = ("ak", "ml", "rd")

# The grid state. Story id: (source id, minutes after 08:00, words). Ties in time: 1 and 2, 3 and
# 4, 6 and 7. A story's text is its first word, "headline for story N", and its words.
STORIES = {
    1: (1, 0, "alpha remedy"),
    2: (2, 0, "bravo remedy rates"),
    3: (3, 5, "charlie rates"),
    4: (1, 5, "delta"),
    5: (2, 10, "echo remedy"),
    6: (3, 15, "foxtrot"),
    7: (1, 15, "golf rates remedy"),
    8: (2, 20, "hotel"),
}
SOURCES = {1: ("Authority", "regulator"), 2: ("Wire", "news"), 3: ("Agency", "ratings")}
TOPICS = {1: {1, 2, 5, 7}, 2: {2, 3, 7}}  # Remedy (remedy), Rates (rates)
FOLLOWS = {"ak": {2}, "rd": {1}}
SAVES = {"ak": {1, 4, 8}, "ml": {2}}
MEMBERS = {1: {"ak", "ml"}, 2: {"ak", "rd"}}  # group 1 is open, group 2 is invited
# (id is the position, from 1): group, story, who started it
THREADS: list[tuple[int, int, str | None]] = [
    (1, 3, "ak"),
    (1, 5, "ml"),
    (2, 5, "ak"),
    (2, 6, None),
    (1, 8, None),
]
VIEWS = ("latest", "foryou", "saved", "topic:1", "topic:2")


def published(story: int) -> str:
    minutes = STORIES[story][1]
    return f"2026-11-13T{8 + minutes // 60:02d}:{minutes % 60:02d}:00+00:00"


def cursor(story: int) -> str:
    return f"{published(story)}|{story}"


def thread(db: sqlite3.Connection, group_id: int, story: int, by: str | None) -> int:
    """What `threads.share_story` or the automatic post writes: a thread, and the starter's note."""
    stamp = T0.isoformat()
    cur = db.execute(
        "INSERT INTO threads(group_id, story_id, started_by, created_at, last_activity_at)"
        " VALUES(?, ?, ?, ?, ?)",
        (group_id, story, by, stamp, stamp),
    )
    thread_id = int(cur.lastrowid or 0)
    if by is not None:
        db.execute(
            "INSERT INTO comments(thread_id, author, text, created_at) VALUES(?, ?, ?, ?)",
            (thread_id, by, f"note {thread_id}", stamp),
        )
    db.commit()
    return thread_id


def grid_db(root: Path) -> sqlite3.Connection:
    db = open_db(root)
    for name, role in (("ak", "writer"), ("ml", "writer"), ("rd", "reader")):
        add_user(db, name, role)
    for number, (name, kind) in SOURCES.items():
        propose_source(db, name, kind, f"https://s{number}.org/f", "ak")
        set_source_state(db, number, "approved")
    for number, (source, minutes, words) in STORIES.items():
        at = datetime(2026, 11, 13, 8, minutes, tzinfo=UTC)
        entry = Entry(
            f"{words.split()[0]} headline for story {number}",
            f"https://s{source}.org/{number}",
            at,
            words,
        )
        assert add_story(db, source, entry, T0) == "new"
    assert add_topic(db, "Remedy", ["remedy"], [], "ak") == 1
    assert add_topic(db, "Rates", ["rates"], [], "ak") == 2
    for name, topic_ids in FOLLOWS.items():
        for topic_id in topic_ids:
            follow(db, name, topic_id)
    for name, story_ids in SAVES.items():
        for story_id in story_ids:
            save(db, name, story_id)
    open_group = create_group(db, Act(AK, T0), "Open desk", "everyone", [])
    join(db, "ml", open_group, T0)
    closed = create_group(db, Act(AK, T0), "Closed desk", "invited", [])
    add_member(db, Act(AK, T0), closed, "rd")
    for group_id, story, by in THREADS:
        thread(db, group_id, story, by)
    return db
