"""The Request checks: the as-of date and the issuer must be stated where a reader looks first.

Each check is a pure function of `(document, context)` returning refusals at the `## Request`
heading (every `column` is 1); neither needs the reader view. Request text is the title of each
section nested in Request and the text nodes of every block in Request and below, in file order;
comments are not text. The as-of date is found when one node holds `as_of.isoformat()` with no
ASCII digit directly before or after it. The issuer is found when the title, or one declaration
of Request (a paragraph or list item with its lines joined by one space, a table cell, a code
line), holds one of `issuer_names` as whole words after both sides are casefolded and their
whitespace runs folded to one space: no letter or digit may touch it. Plain substring search; no
pattern is compiled from context text. Text taken from context inside a reason is bounded by
`echo`.
"""

from collections.abc import Iterable

from credit_os.checks.findings import CheckContext, Finding, refusal
from credit_os.checks.prose import block_nodes
from credit_os.handoff.blocks import Block, CodeBlock, ListItem, Paragraph
from credit_os.handoff.document import HandoffDocument, Section
from credit_os.handoff.errors import echo

_DIGITS = frozenset("0123456789")


def _request_sections(document: HandoffDocument) -> list[Section]:
    """The Request section, then every section nested in it, depth first."""

    def walk(section: Section) -> Iterable[Section]:
        yield section
        for child in section.sections:
            yield from walk(child)

    return list(walk(document.sections[0]))


def _text_nodes(document: HandoffDocument) -> Iterable[str]:
    for section in _request_sections(document):
        if section is not document.sections[0]:
            yield section.title
        for block in section.blocks:
            for _, text in block_nodes(block):
                yield text


def _touches(text: str, start: int, end: int, digits_only: bool) -> bool:
    before = text[start - 1] if start > 0 else ""
    after = text[end] if end < len(text) else ""
    if digits_only:
        return (before != "" and before in _DIGITS) or (after != "" and after in _DIGITS)
    return before.isalnum() or after.isalnum()


def _holds(text: str, wanted: str, digits_only: bool) -> bool:
    start = text.find(wanted)
    while start != -1:
        if not _touches(text, start, start + len(wanted), digits_only):
            return True
        start = text.find(wanted, start + 1)
    return False


def _fold(text: str) -> str:
    return " ".join(text.split()).casefold()


def _declarations(document: HandoffDocument) -> Iterable[str]:
    if document.title is not None:
        yield document.title.title
    for section in _request_sections(document):
        for block in section.blocks:
            yield from _block_declarations(block)


def _block_declarations(block: Block) -> Iterable[str]:
    if isinstance(block, Paragraph | ListItem):
        yield " ".join(block.lines)
    elif isinstance(block, CodeBlock):
        yield from block.lines
    else:
        for _, text in block_nodes(block):
            yield text


def check_as_of(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    if context.as_of is None:
        return ()
    wanted = context.as_of.isoformat()
    if any(_holds(text, wanted, True) for text in _text_nodes(document)):
        return ()
    return (
        refusal(
            "request.as-of",
            document.sections[0].line,
            "Request",
            f"State the as-of date {wanted} in ## Request.",
        ),
    )


def check_issuer(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    if not context.issuer_names:
        return ()
    names = [_fold(name) for name in context.issuer_names]
    if any(_holds(_fold(text), name, False) for text in _declarations(document) for name in names):
        return ()
    return (
        refusal(
            "request.issuer",
            document.sections[0].line,
            "Request",
            f"Name the selected issuer in the title or in ## Request: "
            f"{echo(context.issuer_names[0])}.",
        ),
    )
