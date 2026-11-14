"""The prose checks: what a module's text must change before its handoff is accepted.

Each check is a pure function of `(document, context)` returning a tuple of `Finding`, all
refusals; none parses Markdown and none raises on content. The two Bottom line checks read the
reader view themselves and find nothing when `read_reader` refuses the document or the format is
the earlier one (`text.try_reader` handles `HandoffError`). The others read the shown text
of Findings, Calculations and Gaps (`text.shown_text`), line by line, one finding per match left
to right; `column` is the 1-based position of the match in its line and `quoted` the matched
text. `prose.provider-marker` reads every text node of the document, at the file line of the
node (a comment at its first line, its column counted in the whole comment text). Text taken
from the handoff inside a reason is bounded by `echo`.
"""

import re
from collections.abc import Iterable

from credit_os.checks.findings import CheckContext, Finding, refusal
from credit_os.checks.text import Line, all_sections, sentence_text, shown_text, try_reader
from credit_os.handoff.basis import read_basis
from credit_os.handoff.blocks import Block, CodeBlock, ListItem, Paragraph
from credit_os.handoff.document import HandoffDocument, Section
from credit_os.handoff.tables import Table

_FIRST_SENTENCE_WORDS = 45
_PASSAGE_WORDS = 180
_OPENERS = ('"', "\u201c", "\u2018", "'")

_SENTENCE_END = re.compile(r"[.!?][\"')\]\u201d\u2019*`]*(?:\s|$)")
# An underscore is not a word character here: a letter or digit may not touch a match, `_` may.
_B = r"(?<![^\W_])"
_A = r"(?![^\W_])"
_MODULE_CODE = re.compile(_B + r"CP-[A-Z0-9]+" + _A)
_PAGE = re.compile(rf"{_B}pp?\.\s*\d|{_B}pages?\s+\d|{_B}pg\.?\s*\d", re.IGNORECASE)
_HASH = re.compile(rf"{_B}[0-9a-fA-F]{{12,}}{_A}|sha256", re.IGNORECASE)
_BRACKET = re.compile(r"\[[^\[\]]{0,80}\]|\u3010[^\u3010\u3011]{0,80}\u3011|[\[\]\u3010\u3011]")
_PHRASES = (
    "handoffs?|this transport|the pack|fact pack|source pack|canonical|helper scripts?"
    "|upstream modules?|downstream (?:modules?|owners?|work|analys[ie]s|use)"
)
_WORDING = re.compile(
    rf"(?i:{_B}(?:{_PHRASES}){_A}|{_B}re-anchor\w*)"
    r"|\b\w*[a-z]_[a-z]\w*"
    r"|\b(?=[A-Z0-9_]*[A-Z])[A-Z0-9]+(?:_[A-Z0-9]+)+\b"
)
_MARKER = re.compile(r"[\ue200-\ue202]|cite\s*turn\d+[a-z]+\d+")


def _bottom_line(document: HandoffDocument) -> Section | None:
    reader = try_reader(document)
    return reader.bottom_line if reader is not None and reader.format == "new" else None


def _opening_line(block: Paragraph | ListItem | CodeBlock | Table) -> str:
    if isinstance(block, Table):
        return " | ".join(block.columns)
    return block.lines[0] if block.lines else ""


def _only_basis(paragraph: Paragraph) -> bool:
    return len(paragraph.lines) == 1 and read_basis(paragraph) is not None


def check_bottom_line(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    section = _bottom_line(document)
    if section is None:
        return ()
    reason = (
        "Open the Bottom line with a sentence of prose that starts with a letter, a quotation "
        "mark or bold text."
    )
    if not section.blocks:
        return (refusal("prose.bottom-line", section.line, section.title, reason),)
    first = section.blocks[0]
    if isinstance(first, Paragraph) and not _only_basis(first):
        start = first.lines[0]
        if start[:1].isalpha() or start[:1] in _OPENERS or start.startswith("**"):
            return ()
    return (refusal("prose.bottom-line", first.line, _opening_line(first), reason),)


def _first_sentence(paragraph: Paragraph) -> str:
    keep = len(paragraph.lines) - (1 if read_basis(paragraph) is not None else 0)
    text = " ".join(paragraph.lines[:keep])
    found = _SENTENCE_END.search(text)
    return text if found is None else text[: found.end()]


def check_bottom_line_length(
    document: HandoffDocument, context: CheckContext
) -> tuple[Finding, ...]:
    section = _bottom_line(document)
    if section is None:
        return ()
    found: list[Finding] = []
    first = section.blocks[0] if section.blocks else None
    if isinstance(first, Paragraph):
        sentence = _first_sentence(first)
        count = len(sentence.split())
        if count > _FIRST_SENTENCE_WORDS:
            found.append(
                refusal(
                    "prose.bottom-line-length",
                    first.line,
                    sentence,
                    f"Shorten the first sentence of the Bottom line to {_FIRST_SENTENCE_WORDS} "
                    f"words or fewer; it has {count} words.",
                )
            )
    total = sum(len(line.text.split()) for line in sentence_text(document, section))
    if total > _PASSAGE_WORDS:
        found.append(
            refusal(
                "prose.bottom-line-length",
                section.line,
                section.title,
                f"Shorten the Bottom line to {_PASSAGE_WORDS} words or fewer; it has "
                f"{total} words.",
            )
        )
    return tuple(found)


def _matches(
    lines: Iterable[Line], check: str, pattern: re.Pattern[str], reason: str
) -> tuple[Finding, ...]:
    return tuple(
        refusal(check, line.line, found.group(), reason, found.start() + 1)
        for line in lines
        for found in pattern.finditer(line.text)
    )


def check_module_code(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    return _matches(
        shown_text(document),
        "prose.module-code",
        _MODULE_CODE,
        "Remove the module code and say what the work found in plain words.",
    )


def check_page(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    return _matches(
        shown_text(document),
        "prose.page",
        _PAGE,
        "Remove the page locator; give the page on the Basis line.",
    )


def check_hash(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    return _matches(
        shown_text(document),
        "prose.hash",
        _HASH,
        "Remove the hash; give the source on the Basis line.",
    )


def check_pipeline_wording(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    return _matches(
        shown_text(document),
        "prose.pipeline-wording",
        _WORDING,
        "Replace the wording about how the analysis was produced with plain credit language.",
    )


def check_bracket(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    reason = "Remove the bracketed reference; give the source on the Basis line."
    found: list[Finding] = []
    for line in shown_text(document):
        for match in _BRACKET.finditer(line.text):
            start = match.start()
            quoted = match.group()
            if len(quoted) == 1:
                quoted = line.text[max(0, start - 20) : start + 21].strip()
            found.append(refusal("prose.bracket", line.line, quoted, reason, start + 1))
    return tuple(found)


def _table_nodes(table: Table) -> Iterable[tuple[int, str]]:
    for name in table.columns:
        yield table.line, name
    for row in table.rows:
        for cell in row.cells:
            yield row.line, cell


def block_nodes(block: Block) -> Iterable[tuple[int, str]]:
    """The text nodes of one block with their file lines."""
    if isinstance(block, Table):
        yield from _table_nodes(block)
        return
    if isinstance(block, CodeBlock):
        yield block.line, block.info
    first = block.line + 1 if isinstance(block, CodeBlock) else block.line
    for offset, text in enumerate(block.lines):
        yield first + offset, text


def _block_nodes(section: Section) -> Iterable[tuple[int, str]]:
    for block in section.blocks:
        yield from block_nodes(block)


def _nodes(document: HandoffDocument) -> Iterable[tuple[int, str]]:
    if document.title is not None:
        yield document.title.line, document.title.title
    if document.front_matter is not None:
        for entry in document.front_matter.entries:
            yield entry.line, entry.value
    for section in all_sections(document):
        yield section.line, section.title
        yield from _block_nodes(section)
    for comment in document.comments:
        yield comment.start, comment.text


def _marker_text(found: re.Match[str]) -> str:
    text = found.group()
    return f"U+{ord(text):04X}" if len(text) == 1 else text


def check_provider_marker(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    reason = "Remove the model-provider citation marker from the text."
    return tuple(
        refusal("prose.provider-marker", line, _marker_text(found), reason, found.start() + 1)
        for line, text in _nodes(document)
        for found in _MARKER.finditer(text)
    )
