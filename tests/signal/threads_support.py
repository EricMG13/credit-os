"""What the threads tests share (a sibling module, not a conftest: R49): users, the team
database, and row and count readers. Expected values are written by hand in the tests."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from credit_os.signal.feeds import Entry
from credit_os.signal.identity import User
from credit_os.signal.store import (
    add_story,
    add_user,
    open_db,
    propose_source,
    set_source_state,
)

AK = User("ak", "writer")
ML = User("ml", "writer")
RD = User("rd", "reader")
T0 = datetime(2026, 11, 13, 9, tzinfo=UTC)
MIN = timedelta(minutes=1)

_COUNTS = {
    "groups": "SELECT count(*) FROM groups",
    "threads": "SELECT count(*) FROM threads",
    "comments": "SELECT count(*) FROM comments",
    "reactions": "SELECT count(*) FROM reactions",
    "read_marks": "SELECT count(*) FROM read_marks",
}


def team_db(tmp_path: Path) -> sqlite3.Connection:
    """Users ak and ml (writers) and rd (reader); two approved sources with one story each."""
    db = open_db(tmp_path)
    for user in (AK, ML, RD):
        add_user(db, user.name, user.role)
    for number, kind in ((1, "regulator"), (2, "news")):
        propose_source(db, f"Source {number}", kind, f"https://s{number}.org/f", "ak")
        set_source_state(db, number, "approved")
        entry = Entry(f"Story {number}", f"https://s{number}.org/{number}", T0, f"summary {number}")
        assert add_story(db, number, entry, T0) == "new"
    return db


def rows(db: sqlite3.Connection, sql: str, *params: Any) -> list[tuple[Any, ...]]:
    return [tuple(r) for r in db.execute(sql, params).fetchall()]


def count(db: sqlite3.Connection, table: str) -> int:
    return int(db.execute(_COUNTS[table]).fetchone()[0])
