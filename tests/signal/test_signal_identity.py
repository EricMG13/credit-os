"""Tests for the Signal display-name identity seam."""

from __future__ import annotations

import sqlite3
import tempfile
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.signal.identity import (
    IdentityError,
    User,
    clean_name,
    cleaned,
    cookie_for,
    current_user,
    require_name,
)
from credit_os.signal.store import StoreError, add_user, open_db


@pytest.fixture
def db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    conn = open_db(tmp_path)
    yield conn
    conn.close()


@contextmanager
def fresh_db() -> Iterator[sqlite3.Connection]:
    with tempfile.TemporaryDirectory() as tmp:
        conn = open_db(Path(tmp))
        try:
            yield conn
        finally:
            conn.close()


@pytest.mark.parametrize(
    "raw,want",
    [
        ("  A.  Kovac ", "A. Kovac"),
        ("A\tK\n", "A K"),
        ("x\u200by\x00z", "xyz"),
        ("<b>Eve</b>", "<b>Eve</b>"),
        ("é" * 500, "é" * 60),
        ("é", "é"),
    ],
)
def test_clean_name(raw: str, want: str) -> None:
    assert clean_name(raw) == want


@pytest.mark.parametrize("raw", ["", "   ", "\x00\u200b", "\n\t"])
def test_empty_names_are_refused(raw: str) -> None:
    with pytest.raises(IdentityError):
        clean_name(raw)


def test_cookie_round_trip_and_role(db: sqlite3.Connection) -> None:
    add_user(db, "A. Kovac", "writer")
    header = cookie_for("A. Kovac").split(";")[0]
    assert current_user(db, header) == User("A. Kovac", "writer")
    assert current_user(db, cookie_for("Nobody").split(";")[0]) == User("Nobody", "reader")
    assert current_user(db, None) is None and current_user(db, "other=1") is None
    assert current_user(db, "signal_name=%00%20") is None


def test_cookie_attributes() -> None:
    assert cookie_for("A; B").startswith("signal_name=A%3B%20B; ")
    assert all(
        part in cookie_for("x")
        for part in ("Path=/", "SameSite=Strict", "HttpOnly", "Max-Age=31536000")
    )


def test_clean_name_drops_invisible_characters_before_composing() -> None:
    raw = "e\u200b\u0301"
    assert clean_name(raw) == "é"
    assert clean_name(clean_name(raw)) == clean_name(raw)


def test_lone_surrogate_is_dropped(db: sqlite3.Connection) -> None:
    assert clean_name("Eve\ud800") == "Eve"
    assert cookie_for(clean_name("Eve\ud800")).startswith("signal_name=Eve; ")
    assert current_user(db, "signal_name=Eve\ud800") == User("Eve", "reader")


def test_quoted_cookie_value_loses_one_pair_of_quotes(db: sqlite3.Connection) -> None:
    assert current_user(db, 'signal_name="Al"') == User("Al", "reader")


@settings(deadline=None, max_examples=100)
@given(st.text(max_size=200))
def test_clean_name_is_stable_through_the_cookie(raw: str) -> None:
    try:
        name = clean_name(raw)
    except IdentityError:
        return
    assert clean_name(name) == name
    with fresh_db() as db:
        user = current_user(db, cookie_for(name).split(";")[0])
    assert user is not None and user.name == name


@settings(deadline=None, max_examples=50)
@given(st.text(max_size=300))
def test_any_cookie_header_is_safe(header: str) -> None:
    with fresh_db() as db:
        user = current_user(db, header)
        assert user is None or (0 < len(user.name) <= 60 and user.role == "reader")


# Departures from the predecessor (S3-03, R15, R33).

# Default_Ignorable_Code_Point ranges (Unicode 17) plus U+2800, entered by hand: characters a
# renderer draws as nothing.
IGNORABLE_RANGES = [
    ("\u00ad", "\u00ad"),
    ("\u034f", "\u034f"),
    ("\u061c", "\u061c"),
    ("\u115f", "\u1160"),
    ("\u17b4", "\u17b5"),
    ("\u180b", "\u180f"),
    ("\u200b", "\u200f"),
    ("\u202a", "\u202e"),
    ("\u2060", "\u206f"),
    ("\u2800", "\u2800"),
    ("\u3164", "\u3164"),
    ("\ufe00", "\ufe0f"),
    ("\ufeff", "\ufeff"),
    ("\uffa0", "\uffa0"),
    ("\ufff0", "\ufff8"),
    ("\U0001bca0", "\U0001bca3"),
    ("\U0001d173", "\U0001d17a"),
    ("\U000e0000", "\U000e0fff"),
]


@pytest.mark.parametrize("first,last", IGNORABLE_RANGES)
def test_every_ignorable_character_is_dropped(first: str, last: str) -> None:
    for code in range(ord(first), ord(last) + 1):
        blank = chr(code)
        assert clean_name("A" + blank + "B") == "AB", hex(code)
        with pytest.raises(IdentityError):
            clean_name(blank * 3)


@pytest.mark.parametrize(
    "kept",
    [
        *("\u00ac", "\u00ae", "\u034e", "\u0350", "\u061b", "\u061d", "\u115e", "\u1161"),
        *("\u17b3", "\u17b6", "\u180a", "\u1810", "\u2010", "\u2070", "\u27ff", "\u2801"),
        *("\u3163", "\u3165", "\ufe10", "\uffa1", "\U0001bc9f", "\U0001d172", "\U0001d17b"),
        *("\U000e1000",),
    ],
)
def test_characters_next_to_the_ignorable_ranges_are_kept(kept: str) -> None:
    assert clean_name("A" + kept + "B") == "A" + kept + "B"


def test_a_name_of_blanks_cannot_become_a_user(db: sqlite3.Connection) -> None:
    assert current_user(db, "signal_name=%E3%85%A4%E2%A0%80") is None
    assert current_user(db, "signal_name=%EF%B8%80%E1%85%9F") is None


@pytest.mark.parametrize("mark", ["\u0316", "\u0903", "\u0489"])
def test_a_run_of_marks_is_cut_to_eight(mark: str) -> None:
    assert clean_name("a" + mark * 8) == "a" + mark * 8
    assert clean_name("a" + mark * 9) == "a" + mark * 8
    assert clean_name("a" + mark * 59) == "a" + mark * 8
    assert clean_name("a" + mark * 9 + "b" + mark * 9) == "a" + mark * 8 + "b" + mark * 8


def test_marks_that_alternate_form_one_run() -> None:
    assert clean_name("a" + "\u0316\u0489" * 40) == "a" + "\u0316\u0489" * 4


@pytest.mark.parametrize(
    "raw",
    ["\u0301" * 60, "\u0301", "\u0489" * 3, "\u0301 \u0903", "\u0301 " * 30 + "x"],
)
def test_a_name_with_no_letter_under_its_marks_is_empty(raw: str) -> None:
    with pytest.raises(IdentityError):
        clean_name(raw)


@pytest.mark.parametrize("raw", ["\u0301" * 60, "\u0301", "\u0489 \u0903", "\u3164"])
def test_cleaned_text_with_no_letter_under_its_marks_is_empty(raw: str) -> None:
    assert cleaned(raw) == ""


def test_a_name_of_marks_cannot_become_a_user(db: sqlite3.Connection) -> None:
    assert current_user(db, "signal_name=%CC%81%CC%81") is None


def test_source_and_test_write_invisible_characters_as_escapes() -> None:
    root = Path(__file__).resolve().parents[2]
    paths = [root / "src/credit_os/signal/identity.py", Path(__file__).resolve()]
    for path in paths:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for ch in line:
                hidden = unicodedata.category(ch) in ("Mn", "Mc", "Me", "Cc", "Cf", "Co", "Zs")
                in_range = any(a <= ch <= b for a, b in IGNORABLE_RANGES)
                assert ch == " " or not (ord(ch) > 126 and (hidden or in_range)), (
                    f"{path.name}:{number} holds U+{ord(ch):04X}"
                )


@pytest.mark.parametrize("name", ["A. Kovac", "Eve", "x" * 60, "\u00e9ve", "<b>Eve</b>"])
def test_require_name_returns_a_clean_name_unchanged(name: str) -> None:
    assert require_name(name) == name


@pytest.mark.parametrize(
    "name",
    ["", "   ", "Eve ", " Eve", "E\u202eve", "Eve\x00", "Eve\r\nBob", "A  B", "e\u0301ve"]
    + ["x" * 61, "Eve\ud800", "\u3164", "a" + "\u0316" * 9, "\u0301", "A\tB"],
)
def test_require_name_refuses_a_name_clean_name_would_change_or_refuse(name: str) -> None:
    with pytest.raises(StoreError) as caught:
        require_name(name)
    assert len(str(caught.value)) < 100


@pytest.mark.parametrize("bad", [None, 5, b"Eve", ["Eve"]])
def test_require_name_refuses_what_is_not_text(bad: Any) -> None:
    with pytest.raises(StoreError):
        require_name(bad)


@pytest.mark.parametrize("bad", [None, 5, b"Eve", ["Eve"]])
def test_a_name_that_is_not_text_is_a_store_error(bad: Any) -> None:
    with pytest.raises(StoreError):
        clean_name(bad)
    with pytest.raises(StoreError):
        cookie_for(bad)


@pytest.mark.parametrize("bad", [5, b"signal_name=Eve", ["signal_name=Eve"]])
def test_a_cookie_header_that_is_not_text_is_a_store_error(
    db: sqlite3.Connection, bad: Any
) -> None:
    with pytest.raises(StoreError):
        current_user(db, bad)


def test_an_empty_cookie_header_is_no_user(db: sqlite3.Connection) -> None:
    assert current_user(db, "") is None
