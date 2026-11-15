"""Feed view cost (R70 item 1, M1): operations, not seconds.

The For you page and `new_count(after=0)` read the stories a user's groups have threads on once,
then filter the story scan by that set; their cost is stories plus memberships x threads, not
stories x memberships. Steps are SQLite VM steps (`set_progress_handler`), as in
`test_signal_store_match.py`. Both worlds hold the same 400 stories, 21 open groups and 3 threads
in one group; the user is a member of that group alone, or of it and 19 quiet groups, so the
answers are equal and only the membership count differs.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

from credit_os.signal.feedview import feed, new_count
from credit_os.signal.store import open_db

STORIES = 400
GROUPS = 21
THREAD_STORIES = (7, 150, 399)
BOUND = 2.0  # steps at 20 memberships over steps at 1; measured about 1.0 on the one-list form

# The statement as it was before S-13: a membership EXISTS probed for every story scanned.
_OLD_COUNT = (
    "SELECT COUNT(*) FROM stories s WHERE s.id > :after"
    " AND EXISTS(SELECT 1 FROM threads mt JOIN group_members mm ON mm.group_id = mt.group_id"
    "  WHERE mt.story_id = s.id AND mm.user_name = :user)"
)


def _world(root: Path, memberships: int) -> sqlite3.Connection:
    db = open_db(root)
    db.execute(
        "INSERT INTO sources(id, name, kind, url, state, proposed_by, created_at)"
        " VALUES(1, 'src', 'news', 'https://e.org/f', 'approved', 'x', 'now')"
    )
    db.executemany(
        "INSERT INTO stories(id, source_id, title, link, link_key, title_key, published_at,"
        " fetched_at, summary) VALUES(?, 1, ?, ?, ?, ?, ?, 'f', '')",
        [
            (
                n,
                f"t{n}",
                f"https://e.org/{n}",
                f"e.org/{n}",
                f"t{n}",
                f"2026-11-13T09:00:{n % 60:02d}+00:00",
            )
            for n in range(1, STORIES + 1)
        ],
    )
    db.executemany(
        "INSERT INTO groups(id, name, name_key, visibility, created_by, created_at)"
        " VALUES(?, ?, ?, 'everyone', 'x', 'now')",
        [(g, f"G{g}", f"g{g}") for g in range(1, GROUPS + 1)],
    )
    db.executemany(
        "INSERT INTO group_members(group_id, user_name, joined_at) VALUES(?, 'ann', 'now')",
        [(g,) for g in range(1, memberships + 1)],
    )
    db.executemany(
        "INSERT INTO threads(group_id, story_id, started_by, created_at, last_activity_at)"
        " VALUES(1, ?, 'x', 'now', 'now')",
        [(story,) for story in THREAD_STORIES],
    )
    db.commit()
    return db


def _steps(db: sqlite3.Connection, call: Callable[[], object]) -> int:
    count = 0

    def tick() -> None:
        nonlocal count
        count += 1

    db.set_progress_handler(tick, 1)
    try:
        call()
    finally:
        db.set_progress_handler(None, 0)
    return count


def _ratio(tmp_path: Path, call: Callable[[sqlite3.Connection], object]) -> float:
    few = _world(tmp_path / "few", 1)
    many = _world(tmp_path / "many", 20)
    try:
        return _steps(many, lambda: call(many)) / _steps(few, lambda: call(few))
    finally:
        few.close()
        many.close()


def test_the_for_you_page_costs_the_same_at_one_and_twenty_memberships(tmp_path: Path) -> None:
    assert _ratio(tmp_path, lambda db: feed(db, "ann", "foryou")) <= BOUND


def test_the_new_count_costs_the_same_at_one_and_twenty_memberships(tmp_path: Path) -> None:
    assert _ratio(tmp_path, lambda db: new_count(db, "ann", "foryou", 0)) <= BOUND


def test_the_worlds_give_the_same_answers(tmp_path: Path) -> None:
    for memberships in (1, 20):
        db = _world(tmp_path / f"m{memberships}", memberships)
        page = feed(db, "ann", "foryou")
        assert [card.id for card in page.cards] == [399, 150, 7]
        assert new_count(db, "ann", "foryou", 0) == 3
        assert new_count(db, "ann", "foryou", 150) == 1
        db.close()


def test_the_statement_it_replaced_grows_with_the_memberships(tmp_path: Path) -> None:
    """So the bound above is not vacuous: the old shape costs more than 4 times as much."""
    ratio = _ratio(
        tmp_path, lambda db: db.execute(_OLD_COUNT, {"after": 0, "user": "ann"}).fetchone()
    )
    assert ratio > 4.0
