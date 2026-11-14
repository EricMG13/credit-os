"""What the ingest tests share (a sibling module, not a conftest: R49): the clock, a recorded
feed standing in for `fetch`, source and group builders and row readers. Expected values are
written by hand in the tests."""

import sqlite3
from datetime import UTC, datetime
from typing import Any

from test_signal_feeds import RSS

from credit_os.signal.fetch import Fetched
from credit_os.signal.groups import Act, create_group
from credit_os.signal.identity import User
from credit_os.signal.store import add_user, propose_source, set_source_state
from credit_os.signal.topics import add_topic

NOW = datetime(2026, 11, 13, 9, tzinfo=UTC)

# The feed's first item, retitled so the topic "merger review" matches it.
MERGER = RSS.replace(b"Authority opens review", b"Authority opens merger review")


class Recorded:
    """Stands for `fetch.fetch`: answers one body for every call and records the calls."""

    def __init__(self, body: bytes, etag: str | None = '"v1"') -> None:
        self.body = body
        self.etag = etag
        self.calls: list[tuple[str, str | None, str | None]] = []

    def __call__(self, url: str, etag: str | None, modified: str | None) -> Fetched:
        self.calls.append((url, etag, modified))
        return Fetched(self.body, self.etag, None)


def approve(db: sqlite3.Connection, name: str, url: str) -> int:
    source_id = propose_source(db, name, "news", url, "x")
    set_source_state(db, source_id, "approved")
    return source_id


def group_with_topic(db: sqlite3.Connection, keyword: str = "merger review") -> int:
    """A writer `ak`, a topic matching `keyword` and a group carrying it; returns the group id."""
    add_user(db, "ak", "writer")
    topic = add_topic(db, "Competition", [keyword], [], "ak")
    return create_group(db, Act(User("ak", "writer"), NOW), "G1", "everyone", [topic])


_COUNTS = {
    "stories": "SELECT count(*) FROM stories",
    "story_duplicates": "SELECT count(*) FROM story_duplicates",
    "topic_stories": "SELECT count(*) FROM topic_stories",
    "threads": "SELECT count(*) FROM threads",
    "source_checks": "SELECT count(*) FROM source_checks",
}


def count(db: sqlite3.Connection, table: str) -> int:
    return int(db.execute(_COUNTS[table]).fetchone()[0])


def snapshot(db: sqlite3.Connection) -> dict[str, list[tuple[Any, ...]]]:
    """Every story-side table's rows, for comparing a database before and after a pass."""
    return {
        "stories": [tuple(r) for r in db.execute("SELECT * FROM stories ORDER BY id")],
        "story_duplicates": [tuple(r) for r in db.execute("SELECT * FROM story_duplicates")],
        "topic_stories": [tuple(r) for r in db.execute("SELECT * FROM topic_stories")],
        "threads": [tuple(r) for r in db.execute("SELECT * FROM threads ORDER BY id")],
    }
