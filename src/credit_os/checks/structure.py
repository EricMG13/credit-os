"""The structure checks: what a handoff's shape must change before it is accepted.

Each check is a pure function of `(document, context)` returning a tuple of `Finding`; none
parses Markdown, and none raises on content. A check that needs the reader view reads it itself;
when `read_reader` refuses the document, or the format is the wrong one for it, it finds
nothing, because `check_reader` reports the refusal (`HandoffError` is the one error converted
here, and it becomes the finding).
Every finding has column 1. Text taken from the handoff inside a reason is bounded by `echo`.

A module is blocked when its Bottom line opens `Not assessable:` or its front matter holds
`module_status` equal to `blocked` (quotes stripped, case-folded). The earlier format has no
Bottom line, so only its front matter can block it.
"""

from credit_os.checks.findings import CheckContext, Finding
from credit_os.checks.text import all_sections, try_reader
from credit_os.handoff.blocks import CodeBlock
from credit_os.handoff.data import Register, read_registers
from credit_os.handoff.document import HandoffDocument, Section
from credit_os.handoff.errors import HandoffError, echo
from credit_os.handoff.reader import Reader, read_reader

_PASSAGES = (
    "Bottom line",
    "Key findings",
    "Contrary evidence and what would change the view",
    "Limitations",
)


def _refusal(check: str, line: int, quoted: str, reason: str) -> Finding:
    return Finding(check=check, severity="refusal", line=line, quoted=quoted, reason=reason)


def _level_three(document: HandoffDocument) -> list[Section]:
    return [section for section in document.sections[2].sections if section.level == 3]


def is_blocked(document: HandoffDocument, reader: Reader) -> bool:
    if reader.blocked:
        return True
    if document.front_matter is None:
        return False
    for entry in document.front_matter.entries:
        if entry.key == "module_status":
            return entry.value.strip("\"'").casefold() == "blocked"
    return False


def check_format(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    reader = try_reader(document)
    if reader is None or reader.format != "earlier":
        return ()
    level_three = _level_three(document)
    line = level_three[0].line if level_three else document.sections[2].line
    quoted = level_three[0].title if level_three else "Findings"
    return (
        _refusal(
            "structure.format",
            line,
            quoted,
            "Write the Findings section as Bottom line, Key findings, Contrary evidence and "
            "what would change the view, and Limitations, not in the earlier format.",
        ),
    )


def check_reader_summary(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    reader = try_reader(document)
    if reader is None or reader.format != "earlier":
        return ()
    section = reader.summary_section
    if section is None or reader.summary is not None:
        return ()
    return (
        Finding(
            check="structure.reader-summary",
            severity="warning",
            line=section.line,
            quoted=section.title,
            reason="Make the Reader summary hold exactly its two tables so that it can be read.",
        ),
    )


def check_reader(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    try:
        read_reader(document)
    except HandoffError as error:
        titles = [s.title for s in _level_three(document) if s.line == error.line]
        quoted = titles[0] if titles else "Findings"
        return (_refusal("structure.reader", error.line, quoted, error.message),)
    return ()


def check_passages(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    reader = try_reader(document)
    if reader is None or reader.format != "new" or context.kind != "prose":
        return ()
    if is_blocked(document, reader):
        return ()
    level_three = _level_three(document)
    for position, title in enumerate(_PASSAGES):
        if position < len(level_three) and level_three[position].title == title:
            continue
        found = level_three[position] if position < len(level_three) else None
        line = found.line if found is not None else document.sections[2].line
        quoted = found.title if found is not None else "Findings"
        return (
            _refusal(
                "structure.passages",
                line,
                quoted,
                f"Put the passage `{title}` at position {position + 1} of the level-3 "
                "sections of Findings.",
            ),
        )
    return ()


def check_fence(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    found: list[Finding] = []
    for section in all_sections(document):
        for block in section.blocks:
            if isinstance(block, CodeBlock) and block.unclosed:
                found.append(
                    _refusal(
                        "structure.fence",
                        block.line,
                        block.lines[0] if block.lines else "",
                        "Close this code block with a fence line, or remove the fence.",
                    )
                )
    return tuple(found)


def _quoted(register: Register, by_line: dict[int, Section], document: HandoffDocument) -> str:
    if register.source == "heading":
        return by_line[register.line].title
    return next(comment.text for comment in document.comments if comment.start == register.line)


def _paired_tags(registers: tuple[Register, ...], by_line: dict[int, Section]) -> frozenset[int]:
    """Lines of the tag registers that belong to a heading register of the same id.

    A tag pairs with the nearest preceding heading register of its id whose section holds it
    and that has no tag yet (ruling D13, R13).
    """
    paired: set[int] = set()
    taken: set[int] = set()
    for tag in (register for register in registers if register.source == "tag"):
        owners = [
            heading.line
            for heading in registers
            if heading.source == "heading"
            and heading.id == tag.id
            and heading.line not in taken
            and by_line[heading.line].line < tag.line <= by_line[heading.line].end
        ]
        if owners:
            taken.add(max(owners))
            paired.add(tag.line)
    return frozenset(paired)


def check_register_id(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    by_line = {section.line: section for section in all_sections(document)}
    registers = read_registers(document)
    paired = _paired_tags(registers, by_line)
    seen: set[str] = set()
    found: list[Finding] = []
    for register in registers:
        if register.source == "tag" and register.line in paired:
            continue
        if register.id in seen:
            found.append(
                _refusal(
                    "structure.register-id",
                    register.line,
                    _quoted(register, by_line, document),
                    f"Give this register an id no earlier register uses, "
                    f"not `{echo(register.id)}`.",
                )
            )
        seen.add(register.id)
    return tuple(found)


def _present(register: Register, wanted: str) -> bool:
    if register.id == wanted:
        return True
    return register.source == "tag" and register.id.rsplit(".", 1)[-1] == wanted


def check_registers(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    reader = try_reader(document)
    if reader is None or reader.format != "new" or is_blocked(document, reader):
        return ()
    registers = read_registers(document)
    missing = [
        wanted
        for wanted in context.required_registers
        if not any(_present(register, wanted) for register in registers)
    ]
    if not missing:
        return ()
    return (
        _refusal(
            "structure.registers",
            document.sections[2].line,
            "Findings",
            f"Add the missing registers: {', '.join(missing)}.",
        ),
    )
