"""One pass over handoff lines, in three states: normal, inside a fence, inside a comment.

A heading is tested on the line as written; its title is read from the shown text.
A fence opener is tested before comments. A closer is the same character, at least as
long, with nothing but spaces or tabs after it. A line that began inside a comment is
never a heading or a fence line. `shown` is the line with comments removed, and `""`
when only whitespace is left after a removal.
Inline code spans: backticks form maximal runs. A run of n backticks opens a span only
when a later run of exactly n follows in the same text, and the nearest one closes it;
a run with no such closer is ordinary text. `<!--` inside a span is literal, and text
inside a comment is never searched for runs.
Known limit: a fenced block that itself contains a line starting `## ` is read as
unclosed at that line, and that line is then a level-2 heading.
"""

import re
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from credit_os.handoff.errors import HandoffError

_HEADING = re.compile(r"^(#{1,6}) (.*)$")
_FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_LEVEL_TWO = re.compile(r"^## ")
_BACKTICKS = re.compile(r"`+")
_OPENER = "<!--"
_CLOSER = "-->"


class Node(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Heading(Node):
    level: int
    title: str
    line: int


class Fence(Node):
    open: int
    close: int | None
    end: int
    char: str
    length: int
    info: str

    @property
    def unclosed(self) -> bool:
        return self.close is None


class Comment(Node):
    start: int
    end: int
    text: str


class Scan(Node):
    shown: tuple[str, ...]
    headings: tuple[Heading, ...]
    fences: tuple[Fence, ...]
    comments: tuple[Comment, ...]


class _OpenFence:
    def __init__(self, line: int, char: str, length: int, info: str) -> None:
        self.line = line
        self.char = char
        self.length = length
        self.info = info

    def closes(self, text: str) -> bool:
        run = re.fullmatch(r" {0,3}(" + re.escape(self.char) + r"+)[ \t]*", text)
        return run is not None and len(run.group(1)) >= self.length

    def finish(self, close: int | None, end: int) -> Fence:
        return Fence(
            open=self.line,
            close=close,
            end=end,
            char=self.char,
            length=self.length,
            info=self.info,
        )


class _OpenComment:
    def __init__(self, start: int, first: str) -> None:
        self.start = start
        self.parts = [first]


class _State:
    def __init__(self) -> None:
        self.shown: list[str] = []
        self.headings: list[Heading] = []
        self.fences: list[Fence] = []
        self.comments: list[Comment] = []
        self.fence: _OpenFence | None = None
        self.comment: _OpenComment | None = None


def _hide_continuation(state: _State, pending: _OpenComment, number: int, text: str) -> str | None:
    """Consume a line that began inside a comment; return what follows its `-->`, if any."""
    end = text.find(_CLOSER)
    if end < 0:
        pending.parts.append(text)
        return None
    pending.parts.append(text[:end])
    state.comments.append(
        Comment(start=pending.start, end=number, text="\n".join(pending.parts).strip())
    )
    state.comment = None
    return text[end + len(_CLOSER) :]


def _closers(runs: list[tuple[int, int]]) -> list[int | None]:
    """For each run, the index of the next run of exactly its length, if any."""
    latest: dict[int, int] = {}
    closers: list[int | None] = [None] * len(runs)
    for index in range(len(runs) - 1, -1, -1):
        length = runs[index][1] - runs[index][0]
        closers[index] = latest.get(length)
        latest[length] = index
    return closers


def _next_span(
    runs: list[tuple[int, int]], closers: list[int | None], first: int, pos: int, at: int
) -> tuple[int, int | None]:
    """From run `first`, find a code span opening in `pos..at`; return (next run, span end)."""
    index = first
    while index < len(runs) and runs[index][0] < at:
        closer = closers[index]
        if runs[index][0] >= pos and closer is not None:
            return closer + 1, runs[closer][1]
        index += 1
    return index, None


def _read_comments(state: _State, number: int, text: str, removed: bool) -> str:
    kept: list[str] = []
    runs = [(found.start(), found.end()) for found in _BACKTICKS.finditer(text)]
    closers = _closers(runs)
    pos = 0
    next_run = 0
    at = -1
    while True:
        if at < pos:
            at = text.find(_OPENER, pos)
        if at < 0:
            kept.append(text[pos:])
            break
        next_run, span_end = _next_span(runs, closers, next_run, pos, at)
        if span_end is not None:
            kept.append(text[pos:span_end])
            pos = span_end
            continue
        kept.append(text[pos:at])
        removed = True
        body = at + len(_OPENER)
        end = text.find(_CLOSER, body)
        if end < 0:
            state.comment = _OpenComment(number, text[body:])
            break
        state.comments.append(Comment(start=number, end=number, text=text[body:end].strip()))
        pos = end + len(_CLOSER)
    shown = "".join(kept)
    return "" if removed and not shown.strip() else shown


def _read_commented(state: _State, pending: _OpenComment, number: int, line: str) -> None:
    rest = _hide_continuation(state, pending, number, line)
    state.shown.append("" if rest is None else _read_comments(state, number, rest, True))


def _open_fence(number: int, line: str) -> _OpenFence | None:
    found = _FENCE_OPEN.match(line)
    if found is None:
        return None
    run, rest = found.groups()
    if run[0] == "`" and "`" in rest:
        return None
    return _OpenFence(number, run[0], len(run), rest.strip())


def _read_normal(state: _State, number: int, line: str) -> None:
    opened = _open_fence(number, line)
    if opened is not None:
        state.fence = opened
        state.shown.append(line)
        return
    shown = _read_comments(state, number, line, False)
    state.shown.append(shown)
    heading = _HEADING.match(line)
    if heading is not None:
        level = len(heading.group(1))
        state.headings.append(Heading(level=level, title=shown[level + 1 :].strip(), line=number))


def _read_fenced(state: _State, fence: _OpenFence, number: int, line: str) -> None:
    if _LEVEL_TWO.match(line):
        state.fences.append(fence.finish(None, number - 1))
        state.fence = None
        _read_normal(state, number, line)
        return
    if fence.closes(line):
        state.fences.append(fence.finish(number, number))
        state.fence = None
    state.shown.append(line)


def scan(lines: Sequence[str]) -> Scan:
    state = _State()
    for number, line in enumerate(lines, 1):
        if state.comment is not None:
            _read_commented(state, state.comment, number, line)
        elif state.fence is not None:
            _read_fenced(state, state.fence, number, line)
        else:
            _read_normal(state, number, line)
    if state.comment is not None:
        raise HandoffError(
            state.comment.start, "the HTML comment opened here is never closed by -->"
        )
    if state.fence is not None:
        state.fences.append(state.fence.finish(None, len(lines)))
    return Scan(
        shown=tuple(state.shown),
        headings=tuple(state.headings),
        fences=tuple(state.fences),
        comments=tuple(state.comments),
    )
