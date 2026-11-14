"""Read the Basis line that ends a paragraph or list item.

The line starts `Basis: `; its items are split on `; ` and each is a calculation id, an
upstream module, a source file with optional pages, or plain text. Nothing is guessed: a piece
that does not fit is kept as text.

Known limit: source file names are not matched against the Sources table, so a name without an
extension is read as text and a name holding `; ` is split. Page numbers are one to nine
digits; only spaces may surround the dash of a span.
"""

import re
from typing import Literal

from credit_os.handoff.blocks import ListItem, Paragraph
from credit_os.handoff.scan import Node

_PREFIX = "Basis: "
_CALCULATION = re.compile(r"calculation (\S+)")
_MODULE = re.compile(r"(.+) \(CP-([A-Z0-9]+)\)", re.DOTALL)
_EXTENSION = re.compile(r"(?<=.)\.[A-Za-z][A-Za-z0-9]{0,4}", re.DOTALL)
_SPAN = r"[0-9]{1,9}(?: *[-–] *[0-9]{1,9})?"
_PAGE_LIST = re.compile(rf"{_SPAN}(?:, {_SPAN})*")
_PAGES_OPEN = re.compile(r", (pages?) ")
_SPAN_PARTS = re.compile(r"([0-9]+)(?: *[-–] *([0-9]+))?")


class BasisItem(Node):
    kind: Literal["calculation", "module", "source", "text"]
    text: str
    calculation: str | None = None
    name: str | None = None
    code: str | None = None
    file: str | None = None
    pages: tuple[tuple[int, int], ...] = ()


class Basis(Node):
    line: int
    body: tuple[str, ...]
    items: tuple[BasisItem, ...]


def _spans(text: str) -> tuple[tuple[int, int], ...]:
    return tuple((int(first), int(last or first)) for first, last in _SPAN_PARTS.findall(text))


def _with_pages(piece: str, end: int, opened: re.Match[str]) -> BasisItem | None:
    listed = piece[opened.end() :]
    if _PAGE_LIST.fullmatch(listed) is None or (opened.group(1) == "page" and ", " in listed):
        return None
    return BasisItem(kind="source", text=piece, file=piece[:end], pages=_spans(listed))


def _source(piece: str) -> BasisItem | None:
    for found in _EXTENSION.finditer(piece):
        for end in range(found.start() + 2, found.end() + 1):
            if end == len(piece):
                return BasisItem(kind="source", text=piece, file=piece)
            opened = _PAGES_OPEN.match(piece, end)
            if opened is not None:
                return _with_pages(piece, end, opened)
    return None


def _item(piece: str) -> BasisItem:
    calculation = _CALCULATION.fullmatch(piece)
    if calculation is not None:
        return BasisItem(kind="calculation", text=piece, calculation=calculation.group(1))
    module = _MODULE.fullmatch(piece)
    if module is not None:
        return BasisItem(
            kind="module", text=piece, name=module.group(1), code=f"CP-{module.group(2)}"
        )
    return _source(piece) or BasisItem(kind="text", text=piece)


def read_basis(block: Paragraph | ListItem) -> Basis | None:
    last = block.lines[-1] if block.lines else ""
    if not last.startswith(_PREFIX):
        return None
    text = last[len(_PREFIX) :].rstrip().removesuffix(".")
    pieces = [piece.strip() for piece in text.split("; ")]
    return Basis(
        line=block.line + len(block.lines) - 1,
        body=block.lines[:-1],
        items=tuple(_item(piece) for piece in pieces if piece),
    )
