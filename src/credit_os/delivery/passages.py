"""Select module-written passages into the library slice, word for word, and read a cell.

Delivery adds no analysis: a passage is the module's own paragraphs and list items, joined with
one space, with the Basis lines left out. Every split is at a mark a `handoff` reader returns
(the bold lead, the deeper heading); nothing here reads Markdown or does arithmetic.

Every builder raises `DeliveryRefused` when the passage cannot be written as the library shows
it (a table or code block in a prose passage, a source name or a module, table or digest code in
a narrative sentence, a shape the slice has no place for). A refusal means the run cannot be
written: the caller leaves that run out with the reason and never aborts the whole library. A
message names the rule and the builder, never passage text or a name.

Values are plain dicts with the slice's own camelCase keys; `trace` is None here, attached later.
"""

from collections.abc import Sequence
from decimal import Decimal

from credit_os.checks.figures import CODE, read_figures
from credit_os.checks.passages import limitation_texts, normalise_limitation
from credit_os.delivery.errors import DeliveryRefused
from credit_os.handoff.basis import read_basis
from credit_os.handoff.blocks import ListItem, Paragraph
from credit_os.handoff.data import Gap, read_value
from credit_os.handoff.document import HandoffDocument, Section
from credit_os.handoff.lead import read_lead
from credit_os.handoff.reader import Reader

_DASH = "—"
_NOT_ASSESSABLE = "Not assessable:"


def narrative_leaks(text: str, names: Sequence[str]) -> tuple[str, ...]:
    """Every source name (plain substring) and every module, table or digest code in `text`."""
    found: list[tuple[int, str]] = [(m.start(), m.group(0)) for m in CODE.finditer(text)]
    for name in names:
        if not name:
            continue
        start = text.find(name)
        while start >= 0:
            found.append((start, name))
            start = text.find(name, start + len(name))
    found.sort(key=lambda item: item[0])
    return tuple(item[1] for item in found)


def _refuse(builder: str, rule: str) -> DeliveryRefused:
    return DeliveryRefused(f"{builder}: {rule}")


def _clean(builder: str, names: Sequence[str], *texts: str) -> None:
    for text in texts:
        if narrative_leaks(text, names):
            raise _refuse(builder, "source name or code in narrative")


def _text(block: object, builder: str) -> str:
    if not isinstance(block, Paragraph | ListItem):
        raise _refuse(builder, "table or code block in passage")
    basis = read_basis(block)
    return " ".join(block.lines if basis is None else basis.body)


def _joined(texts: Sequence[str]) -> str:
    return " ".join(text for text in texts if text)


def _lead_and_rest(texts: list[str], first: object) -> tuple[str, str]:
    lead = read_lead(first) if isinstance(first, Paragraph | ListItem) else None
    if lead is None:
        return _joined(texts), ""
    return lead.label, _joined([" ".join(lead.rest), *texts[1:]])


def bottom_line(reader: Reader, names: Sequence[str]) -> dict[str, object]:
    """The bottom line; refused when the run is blocked or the passage has no usable text.

    A `DeliveryRefused` from here means the run cannot be written: its caller (PR 7) leaves the
    run out with the reason, as R1 does, and never aborts the whole library.
    """
    section = reader.bottom_line
    if reader.blocked or section is None:
        raise _refuse("bottom line", "no readable passage")
    if section.sections:
        raise _refuse("bottom line", "sub-heading in passage")
    texts = [_text(block, "bottom line") for block in section.blocks]
    if not _joined(texts):
        raise _refuse("bottom line", "no text")
    lead, rest = _lead_and_rest(texts, section.blocks[0])
    _clean("bottom line", names, lead, rest, _joined([lead, rest]))
    return {"label": section.title, "lead": lead, "rest": rest, "trace": None}


def findings(reader: Reader, names: Sequence[str]) -> tuple[dict[str, object], ...]:
    """Each paragraph or list item of Key findings, numbered; empty when the section is missing.

    A `DeliveryRefused` from here means the run cannot be written: its caller (PR 7) leaves the
    run out with the reason, as R1 does, and never aborts the whole library.
    """
    section = reader.key_findings
    if section is None:
        return ()
    if section.sections:
        raise _refuse("findings", "sub-heading in passage")
    out: list[dict[str, object]] = []
    for block in section.blocks:
        text = _text(block, "findings")
        if not text:
            continue
        lead, body = _lead_and_rest([text], block)
        _clean("findings", names, lead, body, _joined([lead, body]))
        out.append({"number": f"{len(out) + 1:02d}", "lead": lead, "body": body, "trace": None})
    return tuple(out)


def _part(title: str, texts: Sequence[str], names: Sequence[str]) -> dict[str, object]:
    text = _joined(texts)
    _clean("contrary evidence", names, title, text, _joined([title, text]))
    return {"title": title, "text": text, "trace": None}


def _direct_parts(section: Section) -> list[tuple[str, list[str]]]:
    parts: list[tuple[str, list[str]]] = []
    for block in section.blocks:
        text = _text(block, "contrary evidence")
        lead = read_lead(block) if isinstance(block, Paragraph | ListItem) else None
        if lead is not None:
            parts.append((lead.label, [" ".join(lead.rest)]))
        elif not text:
            continue
        elif parts:
            parts[-1][1].append(text)
        else:
            parts.append((section.title, [text]))
    return parts


def _sub_part(sub: Section) -> tuple[str, list[str]]:
    if sub.sections:
        raise _refuse("contrary evidence", "deeper heading in sub-section")
    for block in sub.blocks:
        if isinstance(block, Paragraph | ListItem) and read_lead(block) is not None:
            raise _refuse("contrary evidence", "lead mark in sub-section")
    return sub.title, [_text(block, "contrary evidence") for block in sub.blocks]


def contrary_and_change(
    reader: Reader, names: Sequence[str]
) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    """The contrary evidence and, when a second part exists, the change view; refused over two.

    A `DeliveryRefused` from here means the run cannot be written: its caller (PR 7) leaves the
    run out with the reason, as R1 does, and never aborts the whole library.
    """
    section = reader.contrary
    if section is None:
        return None, None
    parts = _direct_parts(section) + [_sub_part(sub) for sub in section.sections]
    if not parts:
        return None, None
    if len(parts) > 2:
        raise _refuse("contrary evidence", "more than two parts")
    built = [_part(title, texts, names) for title, texts in parts]
    return built[0], built[1] if len(built) == 2 else None


def limitations(document: HandoffDocument, names: Sequence[str]) -> tuple[dict[str, object], ...]:
    """The limitation items, deduplicated by normalised text keeping the first, in file order.

    A `DeliveryRefused` from here means the run cannot be written: its caller (PR 7) leaves the
    run out with the reason, as R1 does, and never aborts the whole library.
    """
    seen: set[str] = set()
    out: list[dict[str, object]] = []
    for text in limitation_texts(document):
        key = normalise_limitation(text)
        if key in seen:
            continue
        seen.add(key)
        _clean("limitations", names, text)
        out.append({"text": text, "trace": None})
    return tuple(out)


def blocked_reason(reader: Reader, names: Sequence[str]) -> str:
    """The reason a blocked run gives; refused when the run is not blocked or the reason is empty.

    A `DeliveryRefused` from here means the run cannot be written: its caller (PR 7) leaves the
    run out with the reason, as R1 does, and never aborts the whole library.
    """
    section = reader.bottom_line
    if reader.blocked is not True or section is None:
        raise _refuse("blocked reason", "run is not blocked")
    first = section.blocks[0]
    if not isinstance(first, Paragraph):
        raise _refuse("blocked reason", "no reason paragraph")
    reason = " ".join(first.lines).removeprefix(_NOT_ASSESSABLE).lstrip()
    if not reason:
        raise _refuse("blocked reason", "empty reason")
    _clean("blocked reason", names, reason)
    return reason


def cell(
    text: str,
) -> tuple[dict[str, object] | None, tuple[str | None, str | None] | None]:
    """One table cell as the slice's Cell, and the (unit, currency) of the figure behind `at`.

    `at` is set only when the text read as written and the text read with dates and period labels
    masked each hold exactly one figure and it is the same figure; otherwise `at` is None.
    """
    if not isinstance(text, str):
        raise TypeError("a cell is read from a str")
    if text in ("", _DASH):
        return None, None
    if isinstance(read_value(text), Gap):
        return {"kind": "gap", "reason": text}, None
    written = read_figures(text, passage=False)
    masked = read_figures(text, passage=True)
    if len(written) != 1 or len(masked) != 1:
        return {"kind": "value", "text": text, "at": None}, None
    figure = written[0]
    other = masked[0]
    same = (figure.value, figure.negative, figure.unit, figure.currency) == (
        other.value,
        other.negative,
        other.unit,
        other.currency,
    )
    if not same:
        return {"kind": "value", "text": text, "at": None}, None
    at: Decimal = figure.value.copy_negate() if figure.negative else figure.value
    return {"kind": "value", "text": text, "at": at}, (figure.unit, figure.currency)
