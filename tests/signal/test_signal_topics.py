from __future__ import annotations

import ast
import json
import sqlite3
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.signal import topics
from credit_os.signal.feeds import Entry
from credit_os.signal.store import (
    StoreError,
    StoreUnusable,
    add_story,
    open_db,
    propose_source,
)
from credit_os.signal.topics import (
    add_topic,
    follow,
    list_topics,
    match_story,
    unfollow,
)

T0 = datetime(2026, 11, 13, 9, tzinfo=UTC)


@contextmanager
def fresh_db() -> Iterator[sqlite3.Connection]:
    with tempfile.TemporaryDirectory() as folder:
        db = open_db(Path(folder))
        try:
            yield db
        finally:
            db.close()


@pytest.fixture
def db_two_sources(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    db = open_db(tmp_path)
    propose_source(db, "Authority", "regulator", "https://a.org/f", "x")
    propose_source(db, "Paper", "news", "https://b.org/f", "x")
    yield db
    db.close()


def rows(db: sqlite3.Connection, sql: str, *params: Any) -> list[tuple[Any, ...]]:
    return [tuple(r) for r in db.execute(sql, params).fetchall()]


def count(db: sqlite3.Connection, table: str) -> int:
    tables = {"topic_stories": "SELECT count(*) FROM topic_stories"}
    return int(db.execute(tables[table]).fetchone()[0])


def test_topic_matches_existing_and_later_stories(db_two_sources: sqlite3.Connection) -> None:
    add_story(
        db_two_sources,
        1,
        Entry("Authority opens merger review", "https://a.org/1", T0, "wholesale access remedy"),
        T0,
    )
    tid = add_topic(db_two_sources, "Competition", ["merger review", "remedy"], [], "ak")
    assert rows(db_two_sources, "SELECT story_id FROM topic_stories WHERE topic_id=?", tid) == [
        (1,)
    ]
    add_story(db_two_sources, 2, Entry("Operator plans merger", "https://b.org/1", T0, ""), T0)
    assert match_story(db_two_sources, 2) == []
    add_story(
        db_two_sources, 2, Entry("Second MERGER REVIEW opened", "https://b.org/2", T0, ""), T0
    )
    assert match_story(db_two_sources, 3) == [tid]
    assert match_story(db_two_sources, 3) == [tid]
    assert count(db_two_sources, "topic_stories") == 2


def test_topic_kind_filter(db_two_sources: sqlite3.Connection) -> None:
    tid = add_topic(db_two_sources, "Reg only", ["review"], ["regulator"], "ak")
    add_story(db_two_sources, 2, Entry("News review of the year", "https://b.org/1", T0, ""), T0)
    add_story(db_two_sources, 1, Entry("Regulator review opens", "https://a.org/1", T0, ""), T0)
    assert match_story(db_two_sources, 1) == [] and match_story(db_two_sources, 2) == [tid]


@pytest.mark.parametrize(
    "keywords,kinds", [([], []), ([" "], []), (["x" * 61], []), (["ok"], ["blog"])]
)
def test_bad_topic_rules_are_refused(
    db_two_sources: sqlite3.Connection, keywords: list[str], kinds: list[str]
) -> None:
    with pytest.raises(StoreError):
        add_topic(db_two_sources, "T", keywords, kinds, "ak")


@pytest.mark.parametrize("keyword", ['say "hello"', "a*", "NEAR", "x AND y", "-", "(", "col:on"])
def test_keywords_with_query_syntax_are_plain_text(
    db_two_sources: sqlite3.Connection, keyword: str
) -> None:
    add_topic(db_two_sources, f"T {keyword}", [keyword], [], "ak")


@settings(deadline=None)
@given(st.text(min_size=1, max_size=60).filter(lambda s: bool(s.strip())))
def test_any_keyword_is_accepted_without_error(keyword: str) -> None:
    try:
        with fresh_db() as db:
            add_topic(db, "T", [keyword], [], "ak")
    except StoreError:
        # Only a keyword SQLite cannot encode (a lone surrogate) may be refused, and only so.
        assert any("\ud800" <= ch <= "\udfff" for ch in keyword)


def test_nul_in_a_keyword_is_plain_text_and_does_not_poison_matching(
    db_two_sources: sqlite3.Connection,
) -> None:
    add_topic(db_two_sources, "Nul", ["a\x00b"], [], "ak")
    add_story(db_two_sources, 1, Entry("Authority review", "https://a.org/1", T0, ""), T0)
    assert match_story(db_two_sources, 1) == []
    add_topic(db_two_sources, "Nul again", ["a\x00b"], [], "ak")


def test_follow_is_personal_and_idempotent(db_two_sources: sqlite3.Connection) -> None:
    tid = add_topic(db_two_sources, "Competition", ["review"], [], "ak")
    follow(db_two_sources, "ak", tid)
    follow(db_two_sources, "ak", tid)
    assert [(r["id"], r["following"]) for r in list_topics(db_two_sources, "ak")] == [(tid, 1)]
    assert [(r["id"], r["following"]) for r in list_topics(db_two_sources, "ml")] == [(tid, 0)]
    unfollow(db_two_sources, "ak", tid)
    unfollow(db_two_sources, "ak", tid)
    assert list_topics(db_two_sources, "ak")[0]["following"] == 0
    with pytest.raises(StoreError):
        follow(db_two_sources, "ak", 999)


def test_a_slice_1_database_gains_the_new_tables(tmp_path: Path) -> None:
    db = open_db(tmp_path)
    try:
        version = db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0]
        assert version == "3"
        names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"topics", "topic_stories", "topic_follows", "saves"} <= names
    finally:
        db.close()


def test_add_topic_links_exactly_what_the_per_story_path_links(tmp_path: Path) -> None:
    database = open_db(tmp_path)
    try:
        words = [
            *("merger", "remedy", "spectrum", "auction", "roaming"),
            *("broadband", "tariff", "licence", "appeal", "fine"),
        ]
        base = datetime(2026, 1, 1, tzinfo=UTC)
        with database:
            for index, kind in enumerate(("regulator", "news", "research")):
                database.execute(
                    "INSERT INTO sources(name, kind, url, state, proposed_by, created_at)"
                    " VALUES(?, ?, ?, 'approved', 'x', ?)",
                    (f"S{index}", kind, f"https://s{index}.org/f", base.isoformat()),
                )
            batch = []
            for i in range(2000):
                at = (base + timedelta(minutes=i)).isoformat()
                title = " ".join(words[(i * k + k) % len(words)] for k in (1, 3, 7))
                summary = " ".join(words[(i * k + 2) % len(words)] for k in (2, 5, 9))
                link = f"https://s{i % 3}.org/{i}"
                batch.append((i % 3 + 1, title, link, link, title, at, at, summary))
            database.executemany(
                "INSERT INTO stories(source_id, title, link, link_key, title_key, published_at,"
                " fetched_at, summary) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                batch,
            )
        keywords = ["merger", "spectrum auction", 'say "tariff"', "no such word"]
        kinds = ["regulator", "research"]
        first = add_topic(database, "New path", keywords, kinds, "x")
        with database:
            second = database.execute(
                "INSERT INTO topics(name, keywords, kinds, created_by, created_at)"
                " VALUES('Old path', ?, ?, 'x', ?)",
                (json.dumps(keywords), json.dumps(kinds), base.isoformat()),
            ).lastrowid
        assert second is not None
        for story_id in range(1, 2001):
            match_story(database, story_id)

        def linked(topic_id: int) -> set[int]:
            return {
                row[0]
                for row in database.execute(
                    "SELECT story_id FROM topic_stories WHERE topic_id=?", (topic_id,)
                )
            }

        assert linked(first) == linked(second)
        assert 0 < len(linked(first)) < 2000
    finally:
        database.close()


# Departures from the predecessor (R1, R2, R13, R15, R27, R29).


def test_follow_and_unfollow_never_end_a_transaction_they_did_not_begin(
    db_two_sources: sqlite3.Connection,
) -> None:
    tid = add_topic(db_two_sources, "Competition", ["review"], [], "ak")
    for action in (follow, unfollow):
        db_two_sources.execute("BEGIN")
        with pytest.raises(StoreUnusable):
            action(db_two_sources, "ak", tid)
        assert db_two_sources.in_transaction
        db_two_sources.execute("ROLLBACK")


def test_every_writer_refuses_a_foreign_transaction_with_store_unusable(
    db_two_sources: sqlite3.Connection,
) -> None:
    db_two_sources.execute("BEGIN")
    with pytest.raises(StoreUnusable):
        add_topic(db_two_sources, "T", ["review"], [], "ak")
    with pytest.raises(StoreUnusable):
        match_story(db_two_sources, 1)
    assert rows(db_two_sources, "SELECT count(*) FROM topics") == [(0,)]
    db_two_sources.execute("ROLLBACK")


def test_the_id_of_a_new_topic_comes_from_the_stores_checked_helper(
    db_two_sources: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(_cur: sqlite3.Cursor) -> int:
        raise StoreError("no id")

    monkeypatch.setattr(topics, "new_row_id", refuse)
    with pytest.raises(StoreError, match="no id"):
        add_topic(db_two_sources, "T", ["review"], [], "ak")
    assert rows(db_two_sources, "SELECT count(*) FROM topics") == [(0,)]


def test_source_has_no_assert_and_assembles_no_sql() -> None:
    tree = ast.parse(Path(topics.__file__).read_text(encoding="utf-8"))
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    for call in (n for n in ast.walk(tree) if isinstance(n, ast.Call)):
        if isinstance(call.func, ast.Attribute) and call.func.attr in ("execute", "executemany"):
            assert isinstance(call.args[0], ast.Constant)


def test_sqlite_json_functions_are_present(db_two_sources: sqlite3.Connection) -> None:
    got = db_two_sources.execute(
        "SELECT json_array_length('[]'), (SELECT group_concat(value) FROM json_each('[1,2]'))"
    ).fetchone()
    assert tuple(got) == (0, "1,2")


def test_all_kinds_in_one_list_and_one_kind_filter_the_same_stories(
    db_two_sources: sqlite3.Connection,
) -> None:
    add_story(db_two_sources, 1, Entry("Regulator review", "https://a.org/1", T0, ""), T0)
    add_story(db_two_sources, 2, Entry("News review", "https://b.org/1", T0, ""), T0)
    both = add_topic(db_two_sources, "Both", ["review"], ["regulator", "news"], "ak")
    none = add_topic(db_two_sources, "Any", ["review"], [], "ak")
    only = add_topic(db_two_sources, "News", ["review"], ["news"], "ak")
    linked = rows(db_two_sources, "SELECT topic_id, story_id FROM topic_stories ORDER BY 1, 2")
    assert linked == [(both, 1), (both, 2), (none, 1), (none, 2), (only, 2)]


LONE = "a\ud800b"


def untyped(value: object) -> Any:
    """A value the type checker cannot see through: these tests pass the wrong type on purpose."""
    return value


BAD_CALLS: list[Callable[[Any], object]] = [
    lambda db: add_topic(db, LONE, ["k"], [], "ak"),
    lambda db: add_topic(db, "T", [LONE], [], "ak"),
    lambda db: add_topic(db, "T", ["k"], [], LONE),
    lambda db: add_topic(db, "T", ["k"], [LONE], "ak"),
    lambda db: follow(db, LONE, 1),
    lambda db: unfollow(db, LONE, 1),
    lambda db: list_topics(db, LONE),
    lambda db: add_topic(db, "n" * 201, ["k"], [], "ak"),
    lambda db: add_topic(db, "T", ["k"], [], "c" * 61),
    lambda db: follow(db, "u" * 61, 1),
    lambda db: add_topic(db, untyped(5), ["k"], [], "ak"),
    lambda db: add_topic(db, "T", "keyword", [], "ak"),
    lambda db: add_topic(db, "T", [untyped(5)], [], "ak"),
    lambda db: add_topic(db, "T", ["k"], untyped("news"), "ak"),
    lambda db: add_topic(db, "T", ["k"], [], untyped(None)),
    lambda db: follow(db, "ak", 2**63),
    lambda db: follow(db, "ak", -(2**64)),
    lambda db: unfollow(db, "ak", 2**70),
    lambda db: follow(db, "ak", untyped("1")),
    lambda db: follow(db, "ak", untyped(True)),
    lambda db: follow(db, untyped(7), 1),
    lambda db: match_story(db, 2**63),
    lambda db: match_story(db, untyped("1")),
    lambda db: list_topics(db, untyped(None)),
]


@pytest.mark.parametrize("call", BAD_CALLS)
def test_bad_input_is_a_store_error_and_writes_nothing(
    db_two_sources: sqlite3.Connection, call: Callable[[Any], object]
) -> None:
    add_topic(db_two_sources, "Base", ["review"], [], "ak")
    with pytest.raises(StoreError):
        call(db_two_sources)
    assert not db_two_sources.in_transaction
    assert rows(db_two_sources, "SELECT count(*) FROM topics") == [(1,)]
    assert rows(db_two_sources, "SELECT count(*) FROM topic_follows") == [(0,)]


def test_a_topic_name_at_the_limit_is_accepted_and_a_duplicate_is_refused(
    db_two_sources: sqlite3.Connection,
) -> None:
    add_topic(db_two_sources, "n" * 200, ["k"], [], "c" * 60)
    with pytest.raises(StoreError, match="already exists"):
        add_topic(db_two_sources, "n" * 200, ["k"], [], "ak")


def test_a_blank_topic_name_is_refused(db_two_sources: sqlite3.Connection) -> None:
    with pytest.raises(StoreError, match="must not be empty"):
        add_topic(db_two_sources, "   ", ["k"], [], "ak")
