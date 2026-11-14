"""Redaction of secrets and home directories from text and bytes.

A Redactor never reads the environment on its own: ``from_environ`` takes the mapping it is
given, and ``Redactor()`` matches key shapes only. This module does not import ``os``.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Callable, Iterable, Mapping

REPLACEMENT = "[redacted]"
HOME = "<home>"
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
# (owner ruling, 2026-11-14) to the first whitespace, a reserved character on a Windows path (< >
# : " | ? *), ":" on a POSIX path, or the line's end: a folder past a space is not looked for. A
# user name does not stop there: once a folder is found its name follows the rule of the path's form
# (a Windows name runs through spaces to a slash, a reserved character or the line's end), but the
# reach does not continue past the first space inside it, so the tail of a name never starts a
# search in the prose after it. The span is the
# separators before the folder, the folder, its separators and the user name; the name follows the
# rule of the path's form. A folder must be a whole segment, and "root" has no nested form. A path
# is scanned once: a start inside an earlier start's reach is skipped, since the scan of that reach
# meets every folder in it. The user name of one nested home can be the folder of the next
# ("\\home\\users\\jdoeq"), so the search for the next folder resumes where the last one's folder
# ends, not where its name ends; both spans are kept and overlapping spans render as one "<home>".
_NEST_START = re.compile(rf"{_LEAD}(?:[A-Za-z]:|{_UNC}|/mnt/[A-Za-z]|{_UNC_FWD}{_UNC_BODY})[\\/]+")
_NEST_WORD = re.compile(r"(?i:users|home)")  # every folder in _HOME_DIRS holds one
_NEST_HEAD = re.compile(rf"(?<![\\/])[\\/]++{_HOME_DIRS}(?P<folder_end>)[\\/]++")
_NEST_WIN_NAME = re.compile(
    rf"(?:(?!\\*{_UNC}[\\/]+(?:{_HOME_DIRS}[\\/]|{_ROOT}))(?:\\+(?=')|[^\\/<>:\"|?*\r\n]))+"
)
_NEST_POSIX_NAME = re.compile(r"(?:[^/:\\\r\n]|\\[^\r\n]*)+")
_NEST_WIN_REACH = re.compile(r"[^\s<>:\"|?*]*")
_NEST_POSIX_REACH = re.compile(r"[^\s:]*")
_NEST_FORMS = {
    True: (_NEST_WIN_REACH, _NEST_WIN_NAME),
    False: (_NEST_POSIX_REACH, _NEST_POSIX_NAME),
}


def _reach_spans(
    text: str, start: int, end: int, name: re.Pattern[str], spans: list[tuple[int, int]]
) -> int:
    """Append to ``spans`` the nested homes in ``text[start:end]``; return where the last name ended."""
    at = start
    named = 0
    while (head := _NEST_HEAD.search(text, at, end)) is not None:
        at = head.end("folder_end")
        # Inside a name that took the rest of its line, a later head's name ends where that did.
        if head.start() < named and text[named : named + 1] in ("", "\r", "\n"):
            continue
        if (user := name.match(text, head.end())) is not None:
            spans.append((head.start(), user.end()))
            named = max(named, user.end())
    return named


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
        scanned[win] = max(end, _reach_spans(text, start, end, name, spans))
    return spans


def _net_spans(text: str) -> list[tuple[int, int]]:
    """The spans of the pattern net: the three home patterns and the nested pass."""
    matches = [
        (m.span(), m.group("win") is not None)
        for p in (_HOME_PATH, _HOME_PATH_FWD, _HOME_PATH_PLAIN)
        for m in p.finditer(text)
    ]
    spans = [span for span, _ in matches]
    spans += _nested_spans(text, [(span[1], win) for span, win in matches])
    return spans


def home_paths(text: str) -> str:
    """``text`` with each home directory (and so the user name in it) replaced by ``<home>``; a
    name that no slash or reserved character ends takes the rest of its line. It does not redact
    keys. It is a net that claims nothing (decision 0012 point 4): ``Redactor.message`` with
    known paths is the guarantee."""
    return _replace_spans(text, _net_spans(text), HOME)


def _merge(spans: list[tuple[int, int, bool]]) -> list[tuple[int, int, bool]]:
    """The union of ``spans`` (start, end, is a path): overlaps merge, touching spans do not; a
    merged span is a path if any span in it is."""
    merged: list[tuple[int, int, bool]] = []
    for start, end, path in sorted(spans):
        if merged and start < merged[-1][1]:
            last = merged[-1]
            merged[-1] = (last[0], max(last[1], end), last[2] or path)
        else:
            merged.append((start, end, path))
    return merged


def _splice[T: (str, bytes)](
    value: T, merged: list[tuple[int, int, bool]], marker: Callable[[bool], T]
) -> T:
    out: list[T] = []
    pos = 0
    for start, end, path in merged:
        out += [value[pos:start], marker(path)]
        pos = end
    out.append(value[pos:])
    return value[:0].join(out)


def _replace_spans[T: (str, bytes)](value: T, spans: list[tuple[int, int]], marker: T) -> T:
    """Replace the union of ``spans`` (overlaps merged) in ``value``, once each."""
    return _splice(value, _merge([(s, e, False) for s, e in spans]), lambda _: marker)


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


# A known path (decision 0012): its text in every encoding the guarantee names, built once. An
# escape is one to eight backslashes then "u" or "x" and hex digits; a percent escape is "%" with
# the percent itself encoded up to twice ("%25", "%2525"); a separator is a run of 1 to 16 of "/",
# "\\", "%2F" and "%5C". Hex digits are lower case here: the patterns ignore case. Every
# quantifier is bounded, and a backslash run has one parse (linear time, 0012 item 3): a separator
# run is atomic and takes every backslash it can, a word's escape is possessive, and the first
# escape after a separator may reuse the separator's last backslash (a lookbehind), so no failing
# match retries another split of the run.
_ESCAPE = r"\\{1,8}+"
_PERCENT = r"%(?:25){0,2}"
_SEPARATOR = rf"(?>(?:[/\\]|{_PERCENT}(?:2f|5c)){{1,16}})"
_SHARED = "|".join(
    [r"(?<=[/\\]\\)"]
    + [rf"(?<=%{p}(?:2f|5c)\\{{{k}}})" for p in ("", "25", "2525") for k in range(1, 9)]
)
_DRIVE = re.compile(r"[A-Za-z]:")
_LONG_PATH = re.compile(r"[/\\]{2}[?.](?:[/\\]|\Z)")  # "\\?\", "\\.\": a prefix, not a folder


def _units(code: int) -> list[int]:
    return (
        [code] if code < 0x10000 else [0xD800 + ((code - 0x10000) >> 10), 0xDC00 + (code & 0x3FF)]
    )


def _escapes(kind: str, values: Iterable[int], width: int) -> str:
    return _ESCAPE.join(f"{kind}{v:0{width}x}" for v in values)


def _longest_first(forms: Iterable[str]) -> list[str]:
    """``forms`` longest first, then by text: a form that is a prefix of another is tried after it,
    since nothing follows the last character of a name to make a short match fail."""
    return sorted(forms, key=lambda f: (-len(f), f))


def _char_pattern(char: str, after_separator: bool, taken: bool = False) -> str:
    """One character: as written, and each same-length case form of it (as given, lower, upper) as
    ``\\uXXXX`` (a surrogate pair above U+FFFF), ``\\xXX`` (below U+0100), its UTF-8 bytes as
    ``\\xHH`` or ``\\u00HH``, and percent-encoded. The literal is one alternative: the pattern
    ignores case, and two alternatives for one text would let a failing match retry both."""
    plain = {re.escape(char)}
    escaped: set[str] = set()
    for form in {f for f in (char, char.lower(), char.upper()) if len(f) == 1}:
        data = form.encode("utf-8", "surrogatepass")
        escaped |= {_escapes("u", _units(ord(form)), 4), _escapes("x", data, 2)}
        escaped.add(_escapes("u", data, 4))
        plain.add("".join(rf"{_PERCENT}{b:02x}" for b in data))
        if ord(form) < 0x100:
            escaped.add(_escapes("x", [ord(form)], 2))
    lead = rf"(?:{_ESCAPE}|{_SHARED})" if after_separator else rf"{_ESCAPE}"
    lead = "" if taken else lead  # the separator run took the escape's backslashes
    return (
        "(?:"
        + "|".join([lead + "(?:" + "|".join(_longest_first(escaped)) + ")", *_longest_first(plain)])
        + ")"
    )


_SEPARATOR_TOKEN = re.compile(r"%(?:25){0,2}(?:2f|5c)", re.IGNORECASE)


def _form_patterns(form: str, after_separator: bool) -> list[str]:
    """The patterns for one spelling of a folder name. A name that begins with a separator token
    (``%2F``, ``%5C``, ``%252F``) is also matched from just after that token: the atomic separator
    run before it has taken the token, so a zero-width lookbehind stands in for it. Written once
    and never inside a backslash run, so no failing match retries another split of one."""
    found = ["".join(_char_pattern(c, after_separator and i == 0) for i, c in enumerate(form))]
    if after_separator:
        for width in (3, 5, 7):
            if _SEPARATOR_TOKEN.fullmatch(form[:width]):
                rest = "".join(_char_pattern(c, False) for c in form[width:])
                found.append(rf"{_token_lookbehinds(form[:width])}{rest}")
                found.append(
                    _token_lookbehinds(form[:width], 8)
                    + "".join(_char_pattern(c, False, i == 0) for i, c in enumerate(form[width:]))
                )
    return found


def _token_lookbehinds(token: str, backslashes: int = 0) -> str:
    """Zero-width lookbehinds for a separator ``token`` as written and with its leading percent
    encoded once and twice (``%5c`` as ``%255c``, ``%25255c``), each only where the separator run
    still takes it as one token. With ``backslashes`` the token is followed by 1 to that many
    backslashes (one fixed-width lookbehind each: ``re`` has no variable-width one)."""
    seen = [token]
    for depth in (1, 2):
        encoded = "%" + "25" * depth + token[1:]
        if _SEPARATOR_TOKEN.fullmatch(encoded):
            seen.append(encoded)
    counts = range(1, backslashes + 1) if backslashes else (0,)
    return (
        "(?:"
        + "|".join(rf"(?<={re.escape(t)}{chr(92) * 2 * k})" for t in seen for k in counts)
        + ")"
    )


def _word(part: str, after_separator: bool) -> str:
    """A folder name as given, in its whole-name NFC and in its whole-name NFD."""
    forms = {part, unicodedata.normalize("NFC", part), unicodedata.normalize("NFD", part)}
    return (
        "(?:"
        + "|".join(_longest_first({p for f in forms for p in _form_patterns(f, after_separator)}))
        + ")"
    )


def _run(parts: list[str], leading: bool) -> str:
    words = [_word(p, leading or i > 0) for i, p in enumerate(parts)]
    return (_SEPARATOR if leading else "") + _SEPARATOR.join(words)


def _stripped(path: str) -> str:
    """``path`` without surrounding whitespace and trailing separators, until neither is left."""
    text = path
    while (shorter := text.strip().rstrip("/\\")) != text:
        text = shorter
    return text


def _path_patterns(path: str) -> list[str]:
    """The patterns that find a known path: the whole path and its last two folders (the whole
    only if it has one folder). A path with no folder name (a drive and a long-path prefix are
    not one) is refused."""
    text = _stripped(path)
    parts = [p for p in re.split(r"[/\\]+", text) if p]
    folders = [p for p in parts[1 if _LONG_PATH.match(text) else 0 :] if not _DRIVE.fullmatch(p)]
    if not folders:
        raise ValueError("a known path needs at least one folder name")
    whole = _run(parts, text.startswith(("/", "\\")))
    last = _run(folders[-2:], False)
    return [whole] if len(folders) < 2 or last == whole else [whole, last]


class Redactor:
    """Matches key shapes and exact values. An exact value is also matched as ``json.dumps``
    writes it inside a string, once or twice escaped (text and bytes). Not matched: other
    serialisers' escapes (upper-case ``\\uXXXX`` hex, ``\\/``, URL or HTML encodings) and deeper
    nesting. A value that is not valid UTF-8 text still matches as text; in bytes only its forms
    that can be encoded match.

    ``known_paths`` are the paths the launcher knows (decision 0012); ``message`` masks them with
    the keys and the pattern net, and carries the guarantee. ``text`` and ``bytes_`` are keys only."""

    def __init__(
        self, exact_values: Iterable[str] = (), *, known_paths: Iterable[str] = ()
    ) -> None:
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
        # A lookahead finds every occurrence, overlapping ones included.
        self._known = [
            re.compile(f"(?=({p}))", re.IGNORECASE)
            for p in dict.fromkeys(q for path in known_paths for q in _path_patterns(path))
        ]

    @classmethod
    def from_environ(
        cls, environ: Mapping[str, str], *, known_paths: Iterable[str] = ()
    ) -> Redactor:
        # A value read with a trailing line ending is also matched without it; the constructor
        # drops empties and duplicates.
        values = [v for name in TOKEN_ENV_NAMES for v in _with_stripped(environ.get(name))]
        return cls(values, known_paths=known_paths)

    def _key_spans(self, value: str) -> list[tuple[int, int]]:
        spans = [m.span() for m in _KEY_PATTERN.finditer(value)]
        if self._exact is not None:
            spans += [m.span(1) for m in self._exact.finditer(value)]
        return spans

    def text(self, value: str) -> str:
        return _replace_spans(value, self._key_spans(value), REPLACEMENT)

    def message(self, text: str) -> str:
        """``text`` for a stored diagnostic: keys become ``[redacted]``, paths ``<home>``. The
        spans of the keys (as ``text`` finds them), of each known path and of the pattern net
        (``home_paths``) are all found on the unmasked text and masked once as a union; a merged
        span holding any path is ``<home>``, one holding only keys ``[redacted]``. Mask first,
        then cut: a cut (``events`` keeps 500 characters) never splits a name.

        Guaranteed: each known path, and its last two folders under any lead, wherever it
        occurs, with no boundary consulted, as written, as ``\\uXXXX`` or ``\\xXX`` (either hex
        case, one to eight backslashes, UTF-8 bytes included), percent-encoded (the percent
        itself up to twice), in NFC or NFD, each separator a run of up to 16 of ``/``, ``\\``,
        ``%2F``, ``%5C``, in any letter case. Case applies before encoding: each character's escape,
        UTF-8 and percent forms are built from its as-given, lower and upper forms of the same length.

        Not guaranteed: another user's home (the net, best effort); Windows 8.3 short names; a
        case mapping that changes length (``ß`` to ``SS``); a bare user name; a value split
        across strings; other encodings (octal, HTML references, base64); the text of an ``ok``
        reply."""
        spans = [(start, end, False) for start, end in self._key_spans(text)]
        spans += [(start, end, True) for start, end in _net_spans(text)]
        spans += [(m.start(1), m.end(1), True) for p in self._known for m in p.finditer(text)]
        return _splice(text, _merge(spans), lambda path: HOME if path else REPLACEMENT)

    def bytes_(self, value: bytes) -> bytes:
        spans = [m.span() for m in _KEY_PATTERN_BYTES.finditer(value)]
        if self._exact_bytes is not None:
            spans += [m.span(1) for m in self._exact_bytes.finditer(value)]
        return _replace_spans(bytes(value), spans, REPLACEMENT.encode("ascii"))
