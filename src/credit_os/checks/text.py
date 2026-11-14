"""The text of a parsed handoff that checks read, with the file line of each line.

Sentence text of a section is every line of its paragraphs and list items, in file order,
except each block's Basis line (found by `read_basis`). Tables and code blocks give nothing; a
table's label paragraph is an ordinary paragraph and counts. Nested sections follow, depth
first, except a typed data section: it and everything under it give nothing.
Shown text is the sentence text of Findings, Calculations and Gaps. Passage text is the
sentence text of the reader passages that are present, in file order.
"""

from collections.abc import Iterable

from credit_os.handoff.basis import read_basis
from credit_os.handoff.blocks import ListItem, Paragraph
from credit_os.handoff.data import read_data_sections
from credit_os.handoff.document import HandoffDocument, Section
from credit_os.handoff.errors import HandoffError
from credit_os.handoff.reader import Reader, read_reader
from credit_os.handoff.scan import Node


class Line(Node):
    line: int
    text: str


def _block_lines(block: Paragraph | ListItem) -> Iterable[Line]:
    keep = len(block.lines) - (1 if read_basis(block) is not None else 0)
    for offset in range(keep):
        yield Line(line=block.line + offset, text=block.lines[offset])


def _walk(section: Section, skipped: frozenset[int]) -> Iterable[Paragraph | ListItem]:
    if section.line in skipped:
        return
    for block in section.blocks:
        if isinstance(block, Paragraph | ListItem):
            yield block
    for child in section.sections:
        yield from _walk(child, skipped)


def section_blocks(document: HandoffDocument, section: Section) -> Iterable[Paragraph | ListItem]:
    """The paragraphs and list items of `section`, nested sections included, data sections
    (found by heading line) and what is under them excluded, in file order."""
    skipped = frozenset(found.section.line for found in read_data_sections(document))
    return _walk(section, skipped)


def _sentence_text(document: HandoffDocument, sections: tuple[Section, ...]) -> tuple[Line, ...]:
    return tuple(
        line
        for section in sections
        for block in section_blocks(document, section)
        for line in _block_lines(block)
    )


def sentence_text(document: HandoffDocument, section: Section) -> tuple[Line, ...]:
    """The sentence text of one section of `document`, nested sections included."""
    return _sentence_text(document, (section,))


def shown_text(document: HandoffDocument) -> tuple[Line, ...]:
    return _sentence_text(document, document.sections[2:5])


def passage_text(document: HandoffDocument, reader: Reader) -> tuple[Line, ...]:
    passages = (reader.bottom_line, reader.key_findings, reader.contrary, reader.limitations)
    present = sorted((section for section in passages if section is not None), key=_line)
    return _sentence_text(document, tuple(present))


def _line(section: Section) -> int:
    return section.line


def all_sections(document: HandoffDocument) -> list[Section]:
    """Every section at any depth, depth first, in file order."""

    def walk(sections: tuple[Section, ...]) -> Iterable[Section]:
        for section in sections:
            yield section
            yield from walk(section.sections)

    return list(walk(document.sections))


def try_reader(document: HandoffDocument) -> Reader | None:
    """The reader view, or None when `read_reader` refuses the document."""
    try:
        return read_reader(document)
    except HandoffError:
        return None
