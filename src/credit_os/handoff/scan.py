import re
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from credit_os.handoff.errors import HandoffError

_HEADING = re.compile(r"^(#{1,6}) (.*)$")
_FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_LEVEL_TWO = re.compile(r"^## ")
_CODE_SPAN = re.compile(r"(`+).+?\1")
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


def _next_opener(text: str, start: int, spans: list[tuple[int, int]]) -> int:
    at = text.find(_OPENER, start)
    while at >= 0 and any(a <= at < b for a, b in spans):
        at = text.find(_OPENER, at + 1)
    return at


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


def _read_comments(state: _State, number: int, text: str, removed: bool) -> str:
    spans = [m.span() for m in _CODE_SPAN.finditer(text)]
    kept: list[str] = []
    pos = 0
    while True:
        at = _next_opener(text, pos, spans)
        if at < 0:
            kept.append(text[pos:])
            break
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


def _open_fence(line: str) -> _OpenFence | None:
    found = _FENCE_OPEN.match(line)
    if found is None:
        return None
    run, rest = found.groups()
    if run[0] == "`" and "`" in rest:
        return None
    return _OpenFence(0, run[0], len(run), rest.strip())


def _read_normal(state: _State, number: int, line: str) -> None:
    opened = _open_fence(line)
    if opened is not None:
        opened.line = number
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
