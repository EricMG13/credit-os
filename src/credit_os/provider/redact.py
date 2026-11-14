"""Redaction of secrets and home directories from text and bytes.

A Redactor never reads the environment on its own: ``from_environ`` takes the mapping it is
given, and ``Redactor()`` matches key shapes only. This module does not import ``os``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping

REPLACEMENT = "[redacted]"
TOKEN_ENV_NAMES = ("COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN")
# Two rules for the left side of a key. A GitHub token shape ("ghp_" and its kin, "github_pat_")
# is redacted after any character, inside a word included: no boundary. An "sk-" key keeps one,
# because "ask-", "risk-" and "task-" are ordinary words: it may not follow a letter or digit,
# except after an escape sequence that ends in one (a "\n", "%0A", an ANSI colour code), which
# that rule would take for a word. One alternative per escape form.
_SK_LEFT_BOUNDARIES = (
    r"(?<![A-Za-z0-9])",  # not the tail of a longer word
    r"(?<=%[0-9A-Fa-f]{2})",  # URL-encoded escape
    r"(?<=%25[0-9A-Fa-f]{2})",  # double-URL-encoded escape
    r"(?<=\\[bfnrt])",  # single-letter escape JSON and Python repr write: \n, \t, \r
    r"(?<=\\u[0-9A-Fa-f]{4})",  # \uXXXX
    r"(?<=\\x[0-9A-Fa-f]{2})",  # \xXX
    r"(?<=\x1b\[[0-9]m)",  # ANSI colour code, 1 to 5 characters of digits and ";"
    r"(?<=\x1b\[[0-9]{2}m)",
    r"(?<=\x1b\[[0-9;]{3}m)",
    r"(?<=\x1b\[[0-9;]{4}m)",
    r"(?<=\x1b\[[0-9;]{5}m)",
)
_SK_BOUNDARY = "|".join(_SK_LEFT_BOUNDARIES)
_SK_KEY = r"sk-(?:(?:or|ant|proj)-[A-Za-z0-9_-]{6,}|[A-Za-z0-9_-]{20,})"
# On its right a GitHub token runs to the end of its word, "_" and "-" included: the letters
# that start the next key ("ghp", "github", "sk") are also body characters, so a match that ended
# where the body's characters end would leave a glued key's "_" or "-" and its body as text. The
# lookahead keeps the minimum body; the rest of the word goes with the token.
_GITHUB_SHAPES = r"(?:gh[pousr]_(?=[A-Za-z0-9]{36})|github_pat_(?=[A-Za-z0-9_]{22}))[A-Za-z0-9_-]+"
_KEY_PATTERN = re.compile(rf"(?:{_SK_BOUNDARY})(?:{_SK_KEY})|{_GITHUB_SHAPES}")
_KEY_PATTERN_BYTES = re.compile(_KEY_PATTERN.pattern.encode("ascii"))
_NAME = r"[^\s\\/:*?\"'<>|(),;]"  # one character of a path segment
# A home directory: "/home/<user>", "/var/home/<user>", "/Users/<user>", "/root", and on Windows
# "<drive>:\Users\<user>", a UNC share's "\\host\share\Users\<user>" (long-path form
# included) or WSL's "/mnt/<drive>/Users/<user>", in either slash, repr-escaped or not, and also
# straight after a written-out "\n", "\r" or "\t". A user name may hold single or repeated
# spaces when a slash or a closing quote follows it. On a Windows-form path a name of several
# words is also taken whole before "," ";" ":" ")" ">" or the line's end (a full stop before
# that end is the sentence's), and "'", "(" and ")" are name characters when a name character or
# a slash follows them. A path inside a longer name or a URL's host part ("example.com/home/x")
# is not one; "file:///home/<user>" is. A closing "." is the sentence's.
_WIN_CHAR = r"[^\s\\/:*?\"'()<>|,;]"
_WIN_WORD = rf"(?:{_WIN_CHAR}|['()](?={_WIN_CHAR}|[\\/]))+"
_WIN_PREFIX = (
    r"(?P<win>(?:[A-Za-z]:|\\\\(?:\?[\\/]+UNC[\\/]+)?[^\s\\/]+[\\/]+[^\s\\/]+|/mnt/[A-Za-z])[\\/]+)"
)
_HOME_PATH = re.compile(
    rf"(?:(?<![\w.-])|(?<=\\[nrt]))(?:{_WIN_PREFIX}|[\\/])"
    rf"(?:(?i:users|home|var[\\/]+home)[\\/]+(?:"
    rf"(?(win)(?>{_WIN_WORD}(?: +{_WIN_WORD})*)|{_NAME}+(?: +{_NAME}+)*)(?=[\\/'\"])"
    rf"|(?(win){_WIN_WORD}(?: +{_WIN_WORD})+(?<!\.)(?=[,;:)>]|\.?(?:\r?\n|\Z))|(?!))"
    rf"|(?(win){_WIN_WORD}|{_NAME}+)(?<!\.))"
    rf"|root(?!{_NAME}))"
)


def home_paths(text: str) -> str:
    """``text`` with each home directory (and so the user name in it) replaced by ``<home>``; the
    rest of each path, and all other text, is kept. It does not redact keys."""
    return _HOME_PATH.sub("<home>", text)


def _replace_spans[T: (str, bytes)](value: T, spans: list[tuple[int, int]], marker: T) -> T:
    """Replace the union of ``spans`` (overlaps merged) in ``value``, once each."""
    out: list[T] = []
    pos = 0
    cur_start = cur_end = -1
    for start, end in sorted(spans):
        if start < cur_end:
            cur_end = max(cur_end, end)
            continue
        if cur_end >= 0:
            out += [value[pos:cur_start], marker]
            pos = cur_end
        cur_start, cur_end = start, end
    if cur_end >= 0:
        out += [value[pos:cur_start], marker]
        pos = cur_end
    out.append(value[pos:])
    return value[:0].join(out)


def _with_stripped(value: str | None) -> tuple[str, ...]:
    return (value, value.strip()) if value and value.strip() else ()


def _json_forms(value: str) -> set[str]:
    """``value`` and its text as ``json.dumps`` writes it inside a string, ASCII-escaped or not,
    and the same again applied to each of those: up to two levels of escaping."""
    forms = {value}
    for _ in range(2):
        forms |= {json.dumps(f, ensure_ascii=a)[1:-1] for f in forms for a in (True, False)}
    return forms


def _utf8(form: str) -> bytes | None:
    try:
        return form.encode("utf-8")
    except UnicodeEncodeError:  # a lone surrogate: no bytes form, its other forms still match
        return None


class Redactor:
    """Matches key shapes and exact values. An exact value is also matched as ``json.dumps``
    writes it inside a string, once or twice escaped (text and bytes). Not matched: other
    serialisers' escapes (upper-case ``\\uXXXX`` hex, ``\\/``, URL or HTML encodings) and deeper
    nesting. A value that is not valid UTF-8 text still matches as text; in bytes only its forms
    that can be encoded match."""

    def __init__(self, exact_values: Iterable[str] = ()) -> None:
        values = sorted(
            {f for v in exact_values if v for f in _json_forms(v)}, key=lambda v: (-len(v), v)
        )
        encoded = sorted(
            {b for v in values if (b := _utf8(v)) is not None}, key=lambda b: (-len(b), b)
        )
        # A lookahead finds every occurrence, including ones that overlap an earlier match.
        self._exact: re.Pattern[str] | None = None
        self._exact_bytes: re.Pattern[bytes] | None = None
        if values:
            self._exact = re.compile("(?=(" + "|".join(re.escape(v) for v in values) + "))")
        if encoded:
            self._exact_bytes = re.compile(
                b"(?=(" + b"|".join(re.escape(b) for b in encoded) + b"))"
            )

    @classmethod
    def from_environ(cls, environ: Mapping[str, str]) -> Redactor:
        # A value read with a trailing line ending is also matched without it; the constructor
        # drops empties and duplicates.
        values = [v for name in TOKEN_ENV_NAMES for v in _with_stripped(environ.get(name))]
        return cls(values)

    def text(self, value: str) -> str:
        spans = [m.span() for m in _KEY_PATTERN.finditer(value)]
        if self._exact is not None:
            spans += [m.span(1) for m in self._exact.finditer(value)]
        return _replace_spans(value, spans, REPLACEMENT)

    def bytes_(self, value: bytes) -> bytes:
        spans = [m.span() for m in _KEY_PATTERN_BYTES.finditer(value)]
        if self._exact_bytes is not None:
            spans += [m.span(1) for m in self._exact_bytes.finditer(value)]
        return _replace_spans(bytes(value), spans, REPLACEMENT.encode("ascii"))
