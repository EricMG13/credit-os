"""`parse(bytes)` is the one reader of handoff bytes and returns a typed `HandoffDocument`.

`reader.read_reader(document)`, `basis.read_basis(block)` and the views in `data` are typed
readings of what it returns.

The file must hold the six level-2 sections in order; an optional front matter and one
level-1 title come first. Sections nest by heading level and own the blocks under them.
"""

import hashlib
from bisect import bisect_right

from credit_os.handoff.blocks import Block, read_blocks
from credit_os.handoff.errors import HandoffError, echo
from credit_os.handoff.frontmatter import FrontMatter, read_front_matter
from credit_os.handoff.lines import count_terminators, split_lines
from credit_os.handoff.scan import Comment, Heading, Node, scan

_REQUIRED = ("Request", "Sources", "Findings", "Calculations", "Gaps", "Next module")


class Section(Node):
    level: int
    title: str
    line: int
    end: int
    blocks: tuple[Block, ...]
    sections: tuple["Section", ...]


class HandoffDocument(Node):
    sha256: str
    line_count: int
    front_matter: FrontMatter | None
    title: Heading | None
    sections: tuple[Section, ...]
    comments: tuple[Comment, ...]


def _decode(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as bad:
        line = 1 + count_terminators(data[: bad.start].decode("utf-8"))
        raise HandoffError(line, "the file is not valid UTF-8") from bad


def _check_skeleton(headings: tuple[Heading, ...], line_count: int) -> Heading:
    level_two = [heading for heading in headings if heading.level == 2]
    for index, heading in enumerate(level_two):
        if index >= len(_REQUIRED):
            raise HandoffError(
                heading.line,
                f"level-2 heading `{echo(heading.title)}` is not allowed after `Next module`",
            )
        if heading.title != _REQUIRED[index]:
            raise HandoffError(
                heading.line,
                f"level-2 heading `{echo(heading.title)}` found where `{_REQUIRED[index]}` is required",
            )
    if len(level_two) < len(_REQUIRED):
        raise HandoffError(
            max(line_count, 1), f"level-2 heading `{_REQUIRED[len(level_two)]}` is missing"
        )
    return level_two[0]


def _check_head(headings: tuple[Heading, ...], request: Heading) -> Heading | None:
    """Check headings around `## Request`; return the level-1 title, if any."""
    title: Heading | None = None
    for heading in headings:
        if heading.level == 1:
            if title is not None or heading.line > request.line:
                raise HandoffError(
                    heading.line, "a level-1 heading is allowed only once, before `## Request`"
                )
            title = heading
    for heading in headings:
        if heading.line < request.line and heading.level > 2:
            raise HandoffError(heading.line, "heading before `## Request` belongs to no section")
    return title


def _build(
    index: int,
    body: list[Heading],
    ends: list[int],
    children: list[list[int]],
    owned: list[list[Block]],
) -> Section:
    heading = body[index]
    return Section(
        level=heading.level,
        title=heading.title,
        line=heading.line,
        end=ends[index],
        blocks=tuple(owned[index]),
        sections=tuple(_build(child, body, ends, children, owned) for child in children[index]),
    )


def _sections(
    body: list[Heading], blocks: tuple[Block, ...], line_count: int
) -> tuple[Section, ...]:
    ends = [line_count] * len(body)
    children: list[list[int]] = [[] for _ in body]
    top: list[int] = []
    open_: list[int] = []
    for index, heading in enumerate(body):
        while open_ and body[open_[-1]].level >= heading.level:
            ends[open_.pop()] = heading.line - 1
        (children[open_[-1]] if open_ else top).append(index)
        open_.append(index)
    starts = [heading.line for heading in body]
    owned: list[list[Block]] = [[] for _ in body]
    for block in blocks:
        owned[bisect_right(starts, block.line) - 1].append(block)
    return tuple(_build(index, body, ends, children, owned) for index in top)


def parse(data: bytes) -> HandoffDocument:
    lines = split_lines(_decode(data))
    front_matter = read_front_matter(lines)
    skip = 0 if front_matter is None else front_matter.end
    result = scan(("",) * skip + lines[skip:])
    request = _check_skeleton(result.headings, len(lines))
    title = _check_head(result.headings, request)
    for block in read_blocks(result, skip + 1, request.line - 1):
        raise HandoffError(block.line, "text before `## Request` belongs to no section")
    body = [heading for heading in result.headings if heading.line >= request.line]
    blocks = read_blocks(result, request.line)
    return HandoffDocument(
        sha256=hashlib.sha256(data).hexdigest(),
        line_count=len(lines),
        front_matter=front_matter,
        title=title,
        sections=_sections(body, blocks, len(lines)),
        comments=result.comments,
    )
