"""The answer key for S-10: `store._earliest_match` exactly as it stood before the fix.

This is the pre-change text of `src/credit_os/signal/store.py` at `origin/main` commit
32cd1494 (the function body, copied verbatim; only its name carries the `_oracle` suffix). It
reads every story that shares the title key and filters by the window in Python. It is the
oracle the new function is compared with and is never edited to follow the new function."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from credit_os.signal.fold import MIN_TITLE_WORDS, TITLE_WINDOW


def earliest_match_oracle(
    db: sqlite3.Connection, source_id: int, lkey: str, tkey: str, published: datetime
) -> int | None:
    """Id of the earliest story with this link key (as a story or a folded duplicate), or, from
    another source, this title key within the window. A source never folds into itself by title,
    and the duplicate-link branch skips the caller's own source."""
    rows = db.execute(
        "SELECT id, published_at, link_key = ? AS same_link FROM stories"
        " WHERE link_key = ? OR (title_key = ? AND source_id != ?)"
        " UNION ALL"
        " SELECT s.id, s.published_at, 1 AS same_link FROM story_duplicates d"
        " JOIN stories s ON s.id = d.story_id WHERE d.link_key = ? AND s.source_id != ?",
        (lkey, lkey, tkey, source_id, lkey, source_id),
    ).fetchall()
    long_title = len(tkey.split()) >= MIN_TITLE_WORDS
    found: list[tuple[datetime, int]] = []
    for row in rows:
        at = datetime.fromisoformat(row["published_at"])
        if row["same_link"] or (long_title and abs(at - published) <= TITLE_WINDOW):
            found.append((at, row["id"]))
    return min(found)[1] if found else None
