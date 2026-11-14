from __future__ import annotations

import ast
import json
import sqlite3
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
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
@given(
    st.text(alphabet=st.characters(min_codepoint=33, max_codepoint=126), min_size=1, max_size=60)
)
def test_any_visible_ascii_keyword_is_accepted_as_plain_text(keyword: str) -> None:
    with fresh_db() as db:
        add_topic(db, "T", [keyword], [], "ak")
        assert rows(db, "SELECT keywords FROM topics") == [(json.dumps([keyword]),)]


@settings(deadline=None)
@given(st.text(alphabet=st.characters(min_codepoint=0xD800, max_codepoint=0xDFFF), min_size=1))
def test_a_keyword_holding_a_lone_surrogate_is_refused(keyword: str) -> None:
    with fresh_db() as db, pytest.raises(StoreError):
        add_topic(db, "T", ["a" + keyword], [], "ak")


def test_nul_in_a_keyword_is_refused_and_the_phrase_builder_still_neutralises_it() -> None:
    with fresh_db() as db, pytest.raises(StoreError):
        add_topic(db, "Nul", ["a\x00b"], [], "ak")
    assert topics.fts_phrase("a\x00b") == '"a b"'


def test_a_quote_in_a_keyword_is_doubled_so_the_phrase_matches_the_words(
    db_two_sources: sqlite3.Connection,
) -> None:
    add_story(db_two_sources, 1, Entry("They say hello today", "https://a.org/1", T0, ""), T0)
    assert topics.fts_phrase('say "hello"') == '"say ""hello"""'
    tid = add_topic(db_two_sources, "Quoted", ['say "hello"'], [], "ak")
    assert rows(db_two_sources, "SELECT story_id FROM topic_stories WHERE topic_id=?", tid) == [
        (1,)
    ]


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


WORDS = ["merger", "remedy", "spectrum", "auction", "roaming", "broadband", "tariff", "fine"]
KIND_NAMES = ["regulator", "news", "research"]


def phrase_in(phrase: list[str], tokens: list[str]) -> bool:
    size = len(phrase)
    return any(tokens[i : i + size] == phrase for i in range(len(tokens) - size + 1))


def test_add_topic_links_exactly_what_the_rule_says_and_the_per_story_path_agrees(
    tmp_path: Path,
) -> None:
    database = open_db(tmp_path)
    try:
        base = datetime(2026, 1, 1, tzinfo=UTC)
        with database:
            for index, kind in enumerate(KIND_NAMES):
                database.execute(
                    "INSERT INTO sources(name, kind, url, state, proposed_by, created_at)"
                    " VALUES(?, ?, ?, 'approved', 'x', ?)",
                    (f"S{index}", kind, f"https://s{index}.org/f", base.isoformat()),
                )
        keywords = ["merger", "spectrum auction", "tariff", "no such word"]
        kinds = ["regulator", "research"]
        stored: list[tuple[int, int, list[str], list[str]]] = []
        for i in range(1, 401):
            title = [WORDS[i % 8], WORDS[(i * 3 + 1) % 8]]
            summary = [WORDS[(i * 5 + 2) % 8], WORDS[(i * 7 + 3) % 8]]
            kind_index = i % 3
            stored.append((i, kind_index, title, summary))
            add_story(
                database,
                kind_index + 1,
                Entry(" ".join(title), f"https://s{kind_index}.org/{i}", base, " ".join(summary)),
                base,
            )
        by_hand = {
            story
            for story, kind_index, title, summary in stored
            if KIND_NAMES[kind_index] in kinds
            and any(
                phrase_in(keyword.split(), tokens)
                for keyword in keywords
                for tokens in (title, summary)
            )
        }
        first_keyword_only = {
            story
            for story, kind_index, title, summary in stored
            if KIND_NAMES[kind_index] in kinds and "merger" in title + summary
        }
        every_allowed = {s for s, kind_index, _, _ in stored if KIND_NAMES[kind_index] in kinds}
        # The data can tell a rule from a shortcut: each keyword adds stories, the kinds exclude some.
        assert first_keyword_only < by_hand < every_allowed

        def linked(topic_id: int) -> set[int]:
            return {
                row[0]
                for row in database.execute(
                    "SELECT story_id FROM topic_stories WHERE topic_id=?", (topic_id,)
                )
            }

        with database:
            old = database.execute(
                "INSERT INTO topics(name, keywords, kinds, created_by, created_at)"
                " VALUES('Old path', ?, ?, 'x', ?)",
                (json.dumps(keywords), json.dumps(kinds), base.isoformat()),
            ).lastrowid
        assert old is not None
        new = add_topic(database, "New path", keywords, kinds, "x")
        assert linked(new) == by_hand
        assert linked(old) == set()
        for story_id in range(1, 401):
            match_story(database, story_id)
        assert linked(old) == by_hand
        assert linked(new) == by_hand
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
    lambda db: add_topic(db, "T", ["k"], ["x" * 100], "ak"),
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
    lambda db: follow(db, "Eve ", 1),
    lambda db: follow(db, "", 1),
    lambda db: unfollow(db, "E\u202eve", 1),
    lambda db: list_topics(db, "A  B"),
    lambda db: add_topic(db, "T", ["k"], [], "e\u0301ve"),
    lambda db: add_topic(db, "T", ["k"], [], ""),
    lambda db: add_topic(db, "T", ["k"], [], "\u3164"),
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


# R33: topic text is clean text (A5), capped (A7), and errors do not echo input (A3).

UNCLEAN_TEXT = [
    "Competition\u200b",
    " Competition",
    "Competition ",
    "Compe\u00adtition",
    "\x1b[2J\x1b[31mCompetition",
    "Line one\r\nLine two",
    "\u202eecnaniF",
    "Nul\x00name",
    "a  b",
    "e\u0301",
    "\u3164",
    "\ufe0f",
    "a" + "\u0316" * 9,
]


@pytest.mark.parametrize("text", UNCLEAN_TEXT)
def test_a_topic_name_that_is_not_clean_text_is_refused(
    db_two_sources: sqlite3.Connection, text: str
) -> None:
    with pytest.raises(StoreError):
        add_topic(db_two_sources, text, ["k"], [], "ak")
    assert rows(db_two_sources, "SELECT count(*) FROM topics") == [(0,)]


@pytest.mark.parametrize("text", UNCLEAN_TEXT)
def test_a_keyword_that_is_not_clean_text_is_refused(
    db_two_sources: sqlite3.Connection, text: str
) -> None:
    with pytest.raises(StoreError):
        add_topic(db_two_sources, "T", ["fine", text], [], "ak")
    assert rows(db_two_sources, "SELECT count(*) FROM topics") == [(0,)]


@pytest.mark.parametrize("text", ["Competition", "M&A review", "\u65e5\u672c", "\u00e9ve", "a-b"])
def test_clean_text_is_stored_exactly_as_given(
    db_two_sources: sqlite3.Connection, text: str
) -> None:
    add_topic(db_two_sources, text, [text], [], "ak")
    assert rows(db_two_sources, "SELECT name, keywords FROM topics") == [(text, json.dumps([text]))]


def test_the_keyword_limit_is_sixty_characters(db_two_sources: sqlite3.Connection) -> None:
    add_topic(db_two_sources, "At the limit", ["k" * 60], [], "ak")
    with pytest.raises(StoreError):
        add_topic(db_two_sources, "Over", ["k" * 61], [], "ak")


def test_a_topic_holds_at_most_sixty_keywords(db_two_sources: sqlite3.Connection) -> None:
    add_topic(db_two_sources, "Sixty", [f"word{i}" for i in range(60)], [], "ak")
    with pytest.raises(StoreError, match="at most 60 keywords"):
        add_topic(db_two_sources, "Sixty one", [f"word{i}" for i in range(61)], [], "ak")
    with pytest.raises(StoreError, match="at most 60 keywords"):
        add_topic(db_two_sources, "Huge", [f"w{i}" for i in range(100_000)], [], "ak")
    assert rows(db_two_sources, "SELECT count(*) FROM topics") == [(1,)]


def test_there_are_at_most_two_hundred_topics(db_two_sources: sqlite3.Connection) -> None:
    for number in range(200):
        add_topic(db_two_sources, f"Topic {number}", ["k"], [], "ak")
    with pytest.raises(StoreError, match="at most 200 topics"):
        add_topic(db_two_sources, "One too many", ["k"], [], "ak")
    assert rows(db_two_sources, "SELECT count(*) FROM topics") == [(200,)]


HOSTILE = "\x1b[2J\r\nX-Injected: 1\u202e\x00"
BIG = 1_000_000

ECHO_CALLS: list[Callable[[Any], object]] = [
    lambda db: add_topic(db, "T1", ["k" * BIG], [], "ak"),
    lambda db: add_topic(db, "T2", [HOSTILE * 50_000], [], "ak"),
    lambda db: add_topic(db, "T3", ["k"], ["x" * BIG], "ak"),
    lambda db: add_topic(db, "T4", ["k"], [HOSTILE], "ak"),
    lambda db: add_topic(db, "T5", ["k"], ["blog"], "ak"),
    lambda db: add_topic(db, "n" * BIG, ["k"], [], "ak"),
    lambda db: add_topic(db, HOSTILE, ["k"], [], "ak"),
    lambda db: add_topic(db, "T6", [HOSTILE], [], "ak"),
    lambda db: add_topic(db, "Base", ["k"], [], "ak"),
    lambda db: follow(db, "u" * BIG, 1),
    lambda db: list_topics(db, HOSTILE * 1000),
    lambda db: unfollow(db, "ak", 2**62),
    lambda db: match_story(db, 2**80),
]


@pytest.mark.parametrize("call", ECHO_CALLS)
def test_an_error_text_does_not_grow_with_the_input(
    db_two_sources: sqlite3.Connection, call: Callable[[Any], object]
) -> None:
    add_topic(db_two_sources, "Base", ["review"], [], "ak")
    with pytest.raises(StoreError) as caught:
        call(db_two_sources)
    text = str(caught.value)
    assert len(text) < 200
    assert "k" * 20 not in text and "X-Injected" not in text and "\x1b" not in text


# Transactions, follows and listing (Q3, Q4).


def test_a_topic_and_its_links_are_one_transaction(db_two_sources: sqlite3.Connection) -> None:
    add_story(db_two_sources, 1, Entry("Authority review", "https://a.org/1", T0, ""), T0)
    db_two_sources.execute(
        "CREATE TEMP TRIGGER refuse_links BEFORE INSERT ON topic_stories"
        " BEGIN SELECT RAISE(ABORT, 'link refused'); END"
    )
    with pytest.raises(sqlite3.DatabaseError, match="link refused"):
        add_topic(db_two_sources, "Competition", ["review"], [], "ak")
    assert not db_two_sources.in_transaction
    assert rows(db_two_sources, "SELECT count(*) FROM topics") == [(0,)]
    db_two_sources.execute("DROP TRIGGER refuse_links")
    assert add_topic(db_two_sources, "Competition", ["review"], [], "ak") == 1


def test_unfollow_refuses_a_missing_topic_and_writes_nothing(
    db_two_sources: sqlite3.Connection,
) -> None:
    with pytest.raises(StoreError, match="no topic with id 999"):
        unfollow(db_two_sources, "ak", 999)
    assert not db_two_sources.in_transaction


def test_unfollow_removes_only_that_users_follow_of_that_topic(
    db_two_sources: sqlite3.Connection,
) -> None:
    one = add_topic(db_two_sources, "One", ["review"], [], "ak")
    two = add_topic(db_two_sources, "Two", ["review"], [], "ak")
    for user, topic in [("ak", one), ("ml", one), ("ak", two)]:
        follow(db_two_sources, user, topic)
    unfollow(db_two_sources, "ak", one)
    assert rows(db_two_sources, "SELECT user_name, topic_id FROM topic_follows ORDER BY 1, 2") == [
        ("ak", two),
        ("ml", one),
    ]


def test_list_topics_gives_every_topic_in_id_order_with_its_follow_and_story_count(
    db_two_sources: sqlite3.Connection,
) -> None:
    add_story(db_two_sources, 1, Entry("Merger review", "https://a.org/1", T0, ""), T0)
    add_story(db_two_sources, 2, Entry("Merger remedy", "https://b.org/1", T0, ""), T0)
    add_story(db_two_sources, 2, Entry("Spectrum auction", "https://b.org/2", T0, ""), T0)
    first = add_topic(db_two_sources, "Merger", ["merger"], [], "ak")
    second = add_topic(db_two_sources, "Spectrum", ["spectrum"], [], "ak")
    third = add_topic(db_two_sources, "Nothing", ["absent"], [], "ak")
    follow(db_two_sources, "ml", second)
    got = [tuple(r) for r in list_topics(db_two_sources, "ml")]
    assert got == [
        (first, "Merger", 0, 2),
        (second, "Spectrum", 1, 1),
        (third, "Nothing", 0, 0),
    ]


def test_match_story_gives_the_topic_ids_in_ascending_order(
    db_two_sources: sqlite3.Connection,
) -> None:
    add_story(db_two_sources, 1, Entry("Merger review", "https://a.org/1", T0, ""), T0)
    low = add_topic(db_two_sources, "Low", ["review"], [], "ak")
    high = add_topic(db_two_sources, "High", ["merger"], [], "ak")
    assert match_story(db_two_sources, 1) == [low, high]
