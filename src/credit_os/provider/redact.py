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
# "<drive>:\Users\<user>", a UNC share's "\\host\share\Users\<user>" (long-path form included),
# WSL's "/mnt/<drive>/Users/<user>" or a backslash-led "\Users\<user>", in either slash,
# repr-escaped or not, also straight after a written-out "\n", "\r" or "\t" when a drive, "\\" or
# "/" follows. A path inside a longer name or a URL's host part ("example.com/home/x") is not
# one; "file:///home/<user>" is. The user name fails closed: it ends only at a character no such
# name can hold, else at the line's end. On a Windows form that is a slash or a character Windows
# reserves in a name (< > : " | ? *) or the line's end; on a POSIX form a "/", a ":" (the passwd
# field separator) or the line's end, and a backslash in it takes the rest of the line. On a
# Windows form a run of backslashes straight before an apostrophe is a
# written-out "\'" (repr, or JSON of a repr), not a separator: it stays in the name, unless the
# run starts a UNC head (a host that begins with "'"). Prose after a name on the same line goes with it.
# The output always covers at least what the fail-closed pattern (_HOME_PATH_PLAIN, main's at 54073086) matches:
# the union of the three patterns' spans is redacted, so no head that pattern finds can be hidden by a name.
_UNC_LEAD = r"\\\\"
_UNC_BODY = r"(?:\?[\\/]+UNC[\\/]+)?[^\s\\/]+[\\/]+[^\s\\/]+"
_UNC = rf"{_UNC_LEAD}{_UNC_BODY}"
_WIN_PREFIX = rf"(?P<win>(?:[A-Za-z]:|{_UNC}|/mnt/[A-Za-z])[\\/]+|\\)"
# A UNC head led by a forward slash, for _HOME_PATH_FWD only: "//srv/share", "//?/UNC/srv/share"; a
# lead of "/" and any run of separators ("/\srv", "///srv"); or a run of backslashes, "/" and any
# further separators ("\/srv", and "\\/srv" as repr writes it). It may not follow ":", "/" or "\", so
# a URL ("https://host/...") is not one. The one exception is a "file:" URL (the whole scheme, any
# case, also straight after a written-out "\n", "\r" or "\t"): "file://srv/share/..." is one, and so
# is "file:" with four or more slashes (an empty authority, then a UNC path); "file:///x" is not.
_FILE = r"(?<=(?:(?<![\w.+-])|(?<=\\[nrt]))(?i:file):)"
_UNC_FWD = (
    r"(?:(?<![:/\\])(?:/[\\/]+|\\+/[\\/]*)"
    rf"|{_FILE}(?:/[\\/]|\\/)(?:[\\/]{{2}}[\\/]*)?)"
)
_HOME_DIRS = r"(?i:users|home|var[\\/]+home)"  # the one list of home folders
_ROOT = rf"root(?!{_NAME})"
_LEAD = r"(?:(?<![\w.-])|(?<=\\[nrt])(?=[A-Za-z]:|\\\\|/))"
_HOME_PATH_PLAIN = re.compile(  # main's pattern at 54073086; its matches are always redacted
    rf"{_LEAD}(?:{_WIN_PREFIX}|/)"
    rf"(?:{_HOME_DIRS}[\\/]+(?(win)[^\\/<>:\"|?*\r\n]|(?:[^/:\\\r\n]|\\[^\r\n]*))+|{_ROOT})"
)
_HOME_PATH = re.compile(
    rf"{_LEAD}(?:{_WIN_PREFIX}|/)"
    rf"(?:{_HOME_DIRS}(?(win)[\\/]++|[\\/]+)"
    rf"(?(win)(?!\\*{_UNC}[\\/]+(?:{_HOME_DIRS}[\\/]|{_ROOT}))"
    r"(?:\\+(?=')|[^\\/<>:\"|?*\r\n])|(?:[^/:\\\r\n]|\\[^\r\n]*))+"
    rf"|{_ROOT})"
)
# The forward-slash UNC form is its own pattern, a Windows form: the _HOME_PATH name rule, with the
# lookahead that stops a name at a following UNC head. _HOME_PATH stays the base's, so a head that
# this pattern's separator run swallows is still found by it.
_HOME_PATH_FWD = re.compile(
    rf"{_LEAD}(?P<win>{_UNC_FWD}{_UNC_BODY}[\\/]+)"
    rf"(?:{_HOME_DIRS}[\\/]++"
    rf"(?:(?!\\*{_UNC}[\\/]+(?:{_HOME_DIRS}[\\/]|{_ROOT}))"
    r"(?:\\+(?=')|[^\\/<>:\"|?*\r\n]))+"
    rf"|{_ROOT})"
)
# A home folder inside a path is a home too (owner ruling, 2026-11-14), but only on a path that is
# one: reached through path segments from a drive, a UNC share (either slash, long-path form
# included) or "/mnt/<drive>/", or from the end of a home the three patterns above matched. It is
# its own pass whose spans join the union, so it never redacts less than they do. A path reaches
# as far as the user-name rule of its form: a Windows path to a reserved character (< > : " | ? *)
# or the line's end, a POSIX path to ":" or the line's end; a space does not end it, since a
# folder name may hold one and the two cannot be told apart, so it fails closed. The span is the
# separators before the folder, the folder, its separators and the user name; the name follows the
# rule of the path's form. A folder must be a whole segment, and "root" has no nested form. A path
# is scanned once: a start inside an earlier start's reach adds nothing and is skipped.
_NEST_START = re.compile(rf"{_LEAD}(?:[A-Za-z]:|{_UNC}|/mnt/[A-Za-z]|{_UNC_FWD}{_UNC_BODY})[\\/]+")
_NEST_WORD = re.compile(r"(?i:users|home)")  # every folder in _HOME_DIRS holds one
_NEST_HEAD = re.compile(rf"(?<![\\/])[\\/]++{_HOME_DIRS}[\\/]++")
_NEST_WIN_NAME = re.compile(
    rf"(?:(?!\\*{_UNC}[\\/]+(?:{_HOME_DIRS}[\\/]|{_ROOT}))(?:\\+(?=')|[^\\/<>:\"|?*\r\n]))+"
)
_NEST_POSIX_NAME = re.compile(r"(?:[^/:\\\r\n]|\\[^\r\n]*)+")
_NEST_WIN_REACH = re.compile(r"[^<>:\"|?*\r\n]*")
_NEST_POSIX_REACH = re.compile(r"[^:\r\n]*")
_NEST_FORMS = {
    True: (_NEST_WIN_REACH, _NEST_WIN_NAME),
    False: (_NEST_POSIX_REACH, _NEST_POSIX_NAME),
}


def _nested_spans(text: str, homes: list[tuple[int, bool]]) -> list[tuple[int, int]]:
    """Spans of the home folders inside paths. ``homes`` is the end and Windows-form flag of each
    match of the three patterns; a match that ends at a separator has the rest of its path."""
    if _NEST_WORD.search(text) is None:  # no folder name anywhere: nothing to find, skip the scan
        return []
    starts = [(m.end(), True) for m in _NEST_START.finditer(text)]
    starts += [(end, win) for end, win in homes if text[end : end + 1] in ("/", "\\")]
    spans: list[tuple[int, int]] = []
    scanned = {True: 0, False: 0}
    for start, win in sorted(starts):
        if start < scanned[win]:
            continue
        reach, name = _NEST_FORMS[win]
        end = next(reach.finditer(text, start)).end()  # the reach pattern matches, empty or not
        at = start
        while (head := _NEST_HEAD.search(text, at, end)) is not None:
            at = head.end()
            if (user := name.match(text, at)) is not None:
                spans.append((head.start(), user.end()))
                at = user.end()
        scanned[win] = max(end, at)
    return spans


def home_paths(text: str) -> str:
    """``text`` with each home directory (and so the user name in it) replaced by ``<home>``; a
    name that no slash or reserved character ends takes the rest of its line. It does not redact
    keys."""
    matches = [
        (m.span(), m.group("win") is not None)
        for p in (_HOME_PATH, _HOME_PATH_FWD, _HOME_PATH_PLAIN)
        for m in p.finditer(text)
    ]
    spans = [span for span, _ in matches]
    spans += _nested_spans(text, [(span[1], win) for span, win in matches])
    return _replace_spans(text, spans, "<home>")


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
