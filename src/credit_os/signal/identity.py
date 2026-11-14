"""Display-name identity for Signal: a name in a cookie, the role from the store.

This is not authentication. The cookie is a claim; the role is looked up in the
store. The module is the whole seam the landing-page project replaces.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from urllib.parse import quote, unquote

from credit_os.signal.store import StoreError, role_of

COOKIE = "signal_name"
MAX_NAME = 60
_MAX_AGE = 31536000
_WHITESPACE_CONTROLS = {"\t": " ", "\n": " ", "\r": " "}
# Characters a renderer draws as nothing (Unicode Default_Ignorable_Code_Point, plus the braille
# blank). Most are not control or format characters, so the category test below would keep them;
# a name made of them would look empty, and "AK" plus one would look like "AK". Written as
# escapes so no tool can strip them from the source.
_IGNORABLE = re.compile(
    "[\u00ad\u034f\u061c\u115f-\u1160\u17b4-\u17b5\u180b-\u180f\u200b-\u200f\u202a-\u202e"
    "\u2060-\u206f\u2800\u3164\ufe00-\ufe0f\ufeff\uffa0\ufff0-\ufff8"
    "\U0001bca0-\U0001bca3\U0001d173-\U0001d17a\U000e0000-\U000e0fff]"
)
_MARKS = ("Mn", "Mc", "Me")
MAX_MARKS = 8


class IdentityError(ValueError):
    """The display name is empty once cleaned."""


@dataclass(frozen=True)
class User:
    name: str
    role: str


def _printable(ch: str, keep_newline: bool = False) -> str:
    if ch == "\n" and keep_newline:
        return ch
    if ch in _WHITESPACE_CONTROLS:
        return " "
    if _IGNORABLE.fullmatch(ch):
        return ""
    return "" if unicodedata.category(ch) in ("Cc", "Cf", "Cs") else ch


def _require_str(value: object, what: str) -> str:
    if not isinstance(value, str):
        raise StoreError(f"{what} must be text")
    return value


def _cut_mark_runs(text: str) -> str:
    """Keep at most MAX_MARKS combining marks in a row, so one letter cannot carry a tower."""
    out: list[str] = []
    run = 0
    for ch in text:
        run = run + 1 if unicodedata.category(ch) in _MARKS else 0
        if run <= MAX_MARKS:
            out.append(ch)
    return "".join(out)


def _has_base(text: str) -> bool:
    """Whether some character is neither a space nor a combining mark: marks need a base."""
    return any(ch != " " and unicodedata.category(ch) not in _MARKS for ch in text)


def cleaned(raw: str) -> str:
    """The cleaned text, not cut to MAX_NAME: controls and invisible characters dropped, NFC,
    whitespace collapsed, mark runs cut; empty when nothing but marks and spaces is left."""
    text = unicodedata.normalize("NFC", "".join(_printable(ch) for ch in _require_str(raw, "name")))
    text = _cut_mark_runs(" ".join(text.split()))
    return text if _has_base(text) else ""


def cleaned_text(raw: str, *, multiline: bool) -> str:
    """Free text cleaned by the name rules (controls and invisible characters dropped, NFC, mark
    runs cut to MAX_MARKS) but with its spacing kept and, when `multiline`, its newlines (CRLF and
    CR become LF). Trimmed; empty when nothing but marks and spaces is left. A single-line text
    that holds a line break (LF, CR, U+2028, U+2029, or any character `str.splitlines` splits on
    that cleaning keeps) is a StoreError, not a text with the break turned into a space."""
    text = _require_str(raw, "text")
    if multiline:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    elif "\n" in text or "\r" in text:
        raise StoreError("text must be one line")
    kept = "".join(_printable(ch, multiline) for ch in text)
    if not multiline and "".join(kept.splitlines()) != kept:
        raise StoreError("text must be one line")
    out = _cut_mark_runs(unicodedata.normalize("NFC", kept)).strip()
    return out if _has_base(out.replace("\n", " ")) else ""


def _clean(raw: str) -> str:
    name = cleaned(raw)[:MAX_NAME].strip()
    return name if _has_base(name) else ""


def clean_name(raw: str) -> str:
    """Return the cleaned display name; IdentityError when nothing is left."""
    name = _clean(raw)
    if not name:
        raise IdentityError("display name is empty")
    return name


def require_name(name: object) -> str:
    """`name` itself when it is a name `clean_name` leaves unchanged; otherwise a StoreError.

    For every place that stores a user's name: a stored name is one a cookie can carry."""
    text = _require_str(name, "name")
    if len(text) > MAX_NAME or _clean(text) != text or not text:
        raise StoreError(f"a name must be a clean display name of at most {MAX_NAME} characters")
    return text


def _cookie_value(header: str) -> str | None:
    """First `signal_name` value in a Cookie header; a plain split is safe on any text."""
    for part in header.split(";"):
        key, sep, value = part.partition("=")
        if sep and key.strip() == COOKIE:
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] == '"':
                value = value[1:-1]
            return value
    return None


def current_user(db: sqlite3.Connection, cookie_header: str | None) -> User | None:
    if cookie_header is None:
        return None
    if not _require_str(cookie_header, "cookie header"):
        return None
    value = _cookie_value(cookie_header)
    if value is None:
        return None
    # errors="replace" makes invalid UTF-8 decode to U+FFFD instead of raising.
    name = _clean(unquote(value, errors="replace"))
    if not name:
        return None
    return User(name, role_of(db, name))


def cookie_for(name: str) -> str:
    """The Set-Cookie value for a display name."""
    encoded = quote(clean_name(name), safe="")
    return f"{COOKIE}={encoded}; Path=/; Max-Age={_MAX_AGE}; SameSite=Strict; HttpOnly"
