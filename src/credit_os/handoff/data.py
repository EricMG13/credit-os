"""Typed readings of values, the Sources table, data sections and registers of a parsed handoff.

A gap is a value the module wrote to say content is missing; the parser marks no cell itself,
the caller applies `read_value` to the cells it means. `sources_table` and `source_names` read
the table directly under `## Sources` and never refuse. `read_data_sections` and
`read_registers` list the typed sections and table registers; a table or text that cannot be
read is None, never a refusal. A typed section is found by its title prefix at any depth; a
register is a heading `id — title` or a `table-id` comment tag. Of several tags before one
table, only the last in the text names it.
"""

import re
from typing import Literal

from credit_os.handoff.blocks import CodeBlock, ListItem, Paragraph
from credit_os.handoff.document import HandoffDocument, Section
from credit_os.handoff.scan import Comment, Node
from credit_os.handoff.tables import Table

_GAP_EXACT = ("", "—", "Insufficient Information", "Not reconstructed")
_GAP_PREFIX = ("Not supplied", "Not calculable")


class Gap(Node):
    text: str


def read_value(text: str) -> Gap | str:
    if text in _GAP_EXACT or text.startswith(_GAP_PREFIX):
        return Gap(text=text)
    return text


def passage_value(block: Paragraph | ListItem) -> Gap | str:
    return read_value(" ".join(block.lines))


def sources_table(document: HandoffDocument) -> Table | None:
    tables = [block for block in document.sections[1].blocks if isinstance(block, Table)]
    return tables[0] if len(tables) == 1 else None


def source_names(document: HandoffDocument) -> tuple[str, ...]:
    table = sources_table(document)
    if table is None:
        return ()
    return tuple(row.cells[0] for row in table.rows if row.cells[0])


_PREFIXES: tuple[tuple[str, Literal["chart", "events", "map", "forecast", "confidence"]], ...] = (
    ("Chart data: ", "chart"),
    ("Events: ", "events"),
    ("Map: ", "map"),
    ("Forecast inputs", "forecast"),
    ("Confidence inputs", "confidence"),
)
_HEADING_ID = re.compile(r"([A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+) — ")
_TAG = re.compile(r"table-id: ([A-Za-z0-9_.:-]+)")


class DataSection(Node):
    kind: Literal["chart", "events", "map", "forecast", "confidence"]
    name: str
    section: Section
    table: Table | None
    text: str | None


class Register(Node):
    id: str
    source: Literal["heading", "tag"]
    line: int
    table: Table | None


def _walk(sections: tuple[Section, ...]) -> list[Section]:
    out: list[Section] = []
    for section in sections:
        out.append(section)
        out.extend(_walk(section.sections))
    return out


def _one_table(section: Section) -> Table | None:
    tables = [block for block in section.blocks if isinstance(block, Table)]
    return tables[0] if len(tables) == 1 else None


def _forecast_text(section: Section) -> str | None:
    code = [block for block in section.blocks if isinstance(block, CodeBlock)]
    if len(code) == 1 and not code[0].unclosed and code[0].info == "json":
        return "\n".join(code[0].lines)
    return None


def _data_section(section: Section) -> DataSection | None:
    for prefix, kind in _PREFIXES:
        if not section.title.startswith(prefix):
            continue
        name = section.title[len(prefix) :].strip()
        table = None if kind == "forecast" else _one_table(section)
        if kind == "confidence" and table is not None and table.columns != ("Input", "Value"):
            table = None
        text = _forecast_text(section) if kind == "forecast" else None
        return DataSection(kind=kind, name=name, section=section, table=table, text=text)
    return None


def read_data_sections(document: HandoffDocument) -> tuple[DataSection, ...]:
    found = (_data_section(section) for section in _walk(document.sections))
    return tuple(item for item in found if item is not None)


def _tag_table(owner: Section | None, comment: Comment, later_tags: list[Comment]) -> Table | None:
    if owner is None:
        return None
    later = [block for block in owner.blocks if block.line > comment.end]
    if not later or not isinstance(later[0], Table):
        return None
    table = later[0]
    between = [tag for tag in later_tags if tag.start < table.line]
    return None if between else table


def read_registers(document: HandoffDocument) -> tuple[Register, ...]:
    sections = _walk(document.sections)
    found: list[Register] = []
    for section in sections:
        match = _HEADING_ID.match(section.title)
        if match is not None:
            found.append(
                Register(
                    id=match.group(1),
                    source="heading",
                    line=section.line,
                    table=_one_table(section),
                )
            )
    tags = [
        (comment, match)
        for comment in document.comments
        if (match := _TAG.fullmatch(comment.text)) is not None
    ]
    for index, (comment, match) in enumerate(tags):
        owners = [section for section in sections if section.line <= comment.start]
        owner = owners[-1] if owners else None
        later = [other for other, _ in tags[index + 1 :]]
        found.append(
            Register(
                id=match.group(1),
                source="tag",
                line=comment.start,
                table=_tag_table(owner, comment, later),
            )
        )
    return tuple(sorted(found, key=lambda register: register.line))
