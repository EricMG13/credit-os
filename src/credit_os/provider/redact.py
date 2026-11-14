"""Redaction of secrets and home directories from text and bytes.

A Redactor never reads the environment on its own: ``from_environ`` takes the mapping it is
given, and ``Redactor()`` matches key shapes only. This module does not import ``os``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

REPLACEMENT = "[redacted]"
TOKEN_ENV_NAMES = ("COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN")
# A key may follow "_" or any other non-key character; only a preceding letter or digit marks the
# "sk-" (or "ghp_"-style or "github_pat_" prefix) as the tail of a longer word such as "risk-".
# It may also follow an escape sequence that ends in a letter or digit, which that rule would
# take for a word: one alternative of the left boundary per escape form.
_LEFT_BOUNDARIES = (
    r"(?<![A-Za-z0-9])",  # not the tail of a longer word
    r"(?<=%[0-9A-Fa-f]{2})",  # URL-encoded escape
    r"(?<=%25[0-9A-Fa-f]{2})",  # double-URL-encoded escape
    r"(?<=\\[a-z])",  # backslash escape such as \n, \t, \r
    r"(?<=\\u[0-9A-Fa-f]{4})",  # \uXXXX
    r"(?<=\\x[0-9A-Fa-f]{2})",  # \xXX
    r"(?<=\x1b\[[0-9]m)",  # ANSI colour code, 1 to 5 characters of digits and ";"
    r"(?<=\x1b\[[0-9]{2}m)",
    r"(?<=\x1b\[[0-9;]{3}m)",
    r"(?<=\x1b\[[0-9;]{4}m)",
    r"(?<=\x1b\[[0-9;]{5}m)",
)
_KEY_BOUNDARY = "|".join(_LEFT_BOUNDARIES)
_KEY_PATTERN = re.compile(
    rf"(?:{_KEY_BOUNDARY})(sk-(or|ant|proj)-[A-Za-z0-9_-]{{6,}}"
    r"|sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})"
)
_KEY_PATTERN_BYTES = re.compile(_KEY_PATTERN.pattern.encode("ascii"))
_NAME = r"[^\s\\/:*?\"'<>|(),;]"  # one character of a path segment
# A home directory: "/home/<user>", "/var/home/<user>", "/Users/<user>", "/root", and on Windows
# "<drive>:\Users\<user>", a UNC share's "\\host\share\Users\<user>" or WSL's
# "/mnt/<drive>/Users/<user>", in either slash, repr-escaped or not. A Windows user name may hold
# spaces when a backslash or a closing quote follows it. A path inside a longer name or a URL's
# host part ("example.com/home/x") is not one; "file:///home/<user>" is. A closing "." is the
# sentence's.
_HOME_PATH = re.compile(
    r"(?<![\w.-])(?:(?:[A-Za-z]:|\\\\[^\s\\/]+[\\/]+[^\s\\/]+|/mnt/[A-Za-z])[\\/]+|[\\/])"
    rf"(?:(?i:users|home|var[\\/]+home)[\\/]+"
    rf"(?:{_NAME}+(?: {_NAME}+)*(?=[\\'\"])|{_NAME}+(?<!\.))"
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
    return (value, value.strip()) if value else ()


class Redactor:
    def __init__(self, exact_values: Iterable[str] = ()) -> None:
        values = sorted({v for v in exact_values if v}, key=lambda v: (-len(v), v))
        # A lookahead finds every occurrence, including ones that overlap an earlier match.
        self._exact: re.Pattern[str] | None = None
        self._exact_bytes: re.Pattern[bytes] | None = None
        if values:
            self._exact = re.compile("(?=(" + "|".join(re.escape(v) for v in values) + "))")
            self._exact_bytes = re.compile(
                b"(?=(" + b"|".join(re.escape(v.encode("utf-8")) for v in values) + b"))"
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
