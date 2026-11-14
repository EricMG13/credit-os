"""The figure reader and `figure.form`.

Masks. `read_figures` and `figure.form` mask a line with one function: every `CODE` match (a run of 16 or more hex
characters holding a letter A to F: decimal digits alone are a number) is
replaced by NUL characters of the same length (columns stay true); on the passage side (always, for
`figure.form`) `DATE` matches, period labels (`Q3`, `3Q24`, `FY2025E`, `2025E`, `LTM`) and month
counts (`9M`, when the reader would read no currency for it) are masked the same way. A masked character stays
known as masked and is never whitespace: no whitespace run (between a currency and its figure or its scale, before a unit or scale
word, after `(`, before `)`, in the month-count mask's currency test) crosses it. It is never the left
neighbour of a minus or of a leading point, and it is the left side of a range only when it touches the dash.

Letters in every word of the unit table, the currency codes and the `$` prefixes are ASCII, read
with ASCII case rules. A figure's value is `Decimal` of its digits as written, never negative,
never rounded; a figure in brackets is a negative. Arithmetic is nowhere: no float, no division.

Notes. A bracketed figure with no minus is a note, read as written (neither negative nor bracketed), when the
figure before it, read with only codes masked (on the passage side a masked date or period label counts
as that figure), is on the line, ends with only spaces or tabs before the `(` and is neither bracketed
nor a note; and the bracket's unit is `%` or `x`; or its unit is none or the one before it, the figure
before has no minus, and it is that figure rounded to fewer decimal places (half up or half even, in a
context sized from the operands) or the same digits to the same places with thousands separators the
figure before lacks. Every other bracket is a negative.

Unit and scale. One rule, `_after`, reads what follows a number: a word of the unit table directly
or after any run of whitespace; or a currency and then a scale word (`250 US$ thousands`, whitespace between each part);
or glued letters, which are an ordinal or plural ending (no unit) or the unit `unrecognised`.
`None` means nothing was written, `unrecognised` that something was. One function,
`_currency_before`, gives the currency written before a position (a symbol, a `$` with its
prefix, or a three-letter code), and `_currency_word_before` the one word that ends at a position. The reader walks back from a figure as shown over `_BEFORE_SIGNS` (a hyphen only when it is a minus) to find the currency written
before it, and the month-count mask asks the reader's own functions whether the reader would find a currency for the month count as a figure. `figure.form` judges each figure with
the currency the reader reads for it (one source, `_figure`).

`figure.form` reads passage text of a new-format document (nothing otherwise). Each `FIGURE` match
in a masked line is judged in order: a dash before it (or before its currency), glued letters, a comma
followed by a digit, more than two decimals, an unrecognised currency, a scale with no currency, then a figure with no unit and no currency that
is not a whole number below 100 or a year from 1900 to 2099. Every scan is linear in the line:
a regex step is constant-width or consumes what it scans, and each look-behind walks back over
characters that no other figure's look-behind walks over (its look-behind is amortised, not
bounded: it can cross a long run of whitespace, once).
"""

import re
import string
from bisect import bisect_left
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Context, Decimal
from typing import NamedTuple

from pydantic import Field

from credit_os.checks.findings import CheckContext, Finding, refusal
from credit_os.checks.text import passage_text, try_reader
from credit_os.handoff.document import HandoffDocument
from credit_os.handoff.scan import Node

CODE = re.compile(r"\bCP-[A-Z0-9]+\b|\bT\d+[A-Z]?\.\d+\b|\b(?=[0-9]*[A-Fa-f])[0-9A-Fa-f]{16,}\b")
_MONTH = (
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December"
    r"|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec)"
)
_ORDINAL = r"(?:st|nd|rd|th)?"
DATE = re.compile(
    rf"\b\d{{4}}-\d{{2}}-\d{{2}}\b"
    rf"|\b{_MONTH}\.?\s+(?:\d{{1,2}}{_ORDINAL},?\s+)?\d{{4}}\b"
    rf"|\b{_MONTH}\.?\s+\d{{1,2}}{_ORDINAL}\b"
    rf"|\b\d{{1,2}}{_ORDINAL}\s+{_MONTH}\b(?:,?\s+\d{{4}}\b)?"
)
PERIOD = re.compile(
    r"\b(?:[QH][1-4]|[1-4]Q(?:\d{2}|\d{4})?|[12]H(?:\d{2}|\d{4})?|FY\d{2,4}[EA]?"
    r"|(?:19|20)\d\d[EA]|LTM)\b"
)
MONTH_COUNT = re.compile(r"(?<![\d,.])(?:1[0-2]|[1-9])M(?!\w)")

_ASCII = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)
_LETTERS = frozenset(string.ascii_letters)
_SYMBOLS = {"€": "EUR", "£": "GBP", "¥": "¥"}
_DOLLARS = {"": "USD", "A": "AUD", "C": "CAD", "HK": "HKD", "NZ": "NZD", "S": "SGD"}
_LOWER_CODES = {"usd": "USD", "eur": "EUR", "gbp": "GBP"}
_ENDINGS = frozenset(("st", "nd", "rd", "th", "s"))
_SCALES = frozenset("kmbt")
_UNITS = {
    "%": "%",
    "per cent": "%",
    "percent": "%",
    "x": "x",
    "times": "x",
    "pp": "pp",
    "percentage point": "pp",
    "percentage points": "pp",
    "bp": "bp",
    "bps": "bp",
    "basis point": "bp",
    "basis points": "bp",
    "notch": "notch",
    "notches": "notch",
    "day": "day",
    "days": "day",
    "week": "week",
    "weeks": "week",
    "month": "month",
    "months": "month",
    "quarter": "quarter",
    "quarters": "quarter",
    "year": "year",
    "years": "year",
    "thousand": "k",
    "thousands": "k",
    "k": "k",
    "million": "m",
    "millions": "m",
    "mm": "m",
    "mn": "m",
    "mln": "m",
    "m": "m",
    "billion": "b",
    "billions": "b",
    "bn": "b",
    "bln": "b",
    "b": "b",
    "trillion": "t",
    "trillions": "t",
    "tn": "t",
}
_WORDS = "|".join(re.escape(word) for word in sorted(_UNITS, key=len, reverse=True))
_SCALE_WORDS = "|".join(
    re.escape(word) for word in sorted(_UNITS, key=len, reverse=True) if _UNITS[word] in _SCALES
)
_UNIT = re.compile(rf"\s*(?P<word>%|(?ai:{_WORDS})(?!\w))")
_SCALED = re.compile(
    rf"\s*(?P<currency>[A-Za-z]*\$|[€£¥]|[A-Za-z]{{3}})\s*(?P<scale>(?ai:{_SCALE_WORDS}))(?!\w)"
)

# ISO 4217 alphabetic codes in the active list.
_ISO_CODES = (
    "AED AFN ALL AMD ANG AOA ARS AUD AWG AZN BAM BBD BDT BHD BIF BMD "
    "BND BOB BOV BRL BSD BTN BWP BYN BZD CAD CDF CHE CHF CHW CLF CLP "
    "CNY COP COU CRC CUP CVE CZK DJF DKK DOP DZD EGP ERN ETB EUR FJD "
    "FKP GBP GEL GHS GIP GMD GNF GTQ GYD HKD HNL HTG HUF IDR ILS INR "
    "IQD IRR ISK JMD JOD JPY KES KGS KHR KMF KPW KRW KWD KYD KZT LAK "
    "LBP LKR LRD LSL LYD MAD MDL MGA MKD MMK MNT MOP MRU MUR MVR MWK "
    "MXN MXV MYR MZN NAD NGN NIO NOK NPR NZD OMR PAB PEN PGK PHP PKR "
    "PLN PYG QAR RON RSD RUB RWF SAR SBD SCR SDG SEK SGD SHP SLE SOS "
    "SRD SSP STN SVC SYP SZL THB TJS TMT TND TOP TRY TTD TWD TZS UAH "
    "UGX USD USN UYI UYU UYW UZS VED VES VND VUV WST XAF XAG XAU XBA "
    "XBB XBC XBD XCD XCG XDR XOF XPD XPF XPT XSU XUA YER ZAR ZMW ZWG"
)
ISO_4217 = frozenset(_ISO_CODES.split())

_FIGURE = re.compile(
    r"(?<!\w)(?<!\d[,.])(?<![A-Za-z][-−])"
    r"(?:(?P<lead>(?<![.,])\.\d+)|(?P<int>\d{1,3}(?:,\d{3})+|\d+)(?P<dec>\.\d+)?)"
    r"(?!\d|[-−][A-Za-z])"
)
_NUMBER = re.compile(
    r"(?P<lead>(?<![\w.,])\.\d+)|(?P<int>\d{1,3}(?:,\d{3})+(?!\d)|\d+)(?P<dec>\.\d+)?"
)
_DASHES = "–—"
_BEFORE_SIGNS = "(-−–—+"
_RATIOS = ("%", "x")
_PLAIN = {"negative": False, "bracketed": False}
_HYPHEN_NUMBER = re.compile(r"[-−](?:\d{1,3}(?:,\d{3})+(?!\d)|\d+)(?:\.\d+)?")
_MINUS = "Write the minus before the currency: -USD 5 million."
_COMMA = "Write the number with a decimal point, and commas only between groups of three digits."
_DECIMALS = "Round to at most two decimals."
_FORM = "Write the unit or scale in an accepted form (USD 250 million, 45%, 3.1x), or reword it."
_CURRENCY = "Write the currency as its three-letter currency code before the figure (BRL 500)."
_SCALE = "Put a currency before a scaled amount (USD 250 million), or reword a count."
_DASH = (
    "Write a negative figure with a minus sign (-5%), not a dash; a range needs a figure on "
    "both sides of the dash."
)
_BARE = (
    "A number with no unit does not belong in a reader sentence: reword it in words or move it "
    "to a table, or add a unit or currency if it is an amount or ratio."
)


class Figure(Node):
    """One figure read from a line of text."""

    value: Decimal = Field(description="The magnitude from the digits as written; never negative.")
    negative: bool = Field(description="A minus sign or brackets were written.")
    bracketed: bool = Field(description="The sign was written as brackets, not a minus.")
    unit: str | None = Field(
        description="One of % x pp bp k m b t notch day week month quarter year; "
        "`unrecognised` when letters were written that are none of these; None when nothing was."
    )
    currency: str | None = Field(
        description="An ISO 4217 code, `¥` or `unrecognised`; None when no currency was written."
    )
    shown: str = Field(description="The figure as written, from its bracket or sign to its unit.")
    column: int = Field(description="1-based position of `shown` in the text.")


class _Masked(NamedTuple):
    text: str
    hidden: bytes | bytearray


class _After(NamedTuple):
    unit: str | None
    end: int
    currency: str | None = None
    ending: bool = False


class _Prefix(NamedTuple):
    start: int
    minus: bool
    currency: str | None
    anchor: int


class _Bracket(NamedTuple):
    start: int
    close: int
    currency: str | None
    minus: bool


def _lower(word: str) -> str:
    return word.translate(_ASCII)


def _currency_word_before(text: str, end: int) -> tuple[int, str] | None:
    """The currency word that ends at `end`: its start and code, or None."""
    if end == 0:
        return None
    if text[end - 1] in _SYMBOLS:
        return end - 1, _SYMBOLS[text[end - 1]]
    if text[end - 1] == "$":
        start = end - 1
        while start > 0 and text[start - 1] in _LETTERS:
            start -= 1
        prefix = text[start : end - 1]
        us = _lower(prefix) == "us"
        return start, "USD" if us else _DOLLARS.get(prefix, "unrecognised")
    word = text[max(end - 3, 0) : end]
    if len(word) < 3 or any(letter not in _LETTERS for letter in word):
        return None
    if end > 3 and text[end - 4] in _LETTERS:
        return None
    if word in ISO_4217:
        return end - 3, word
    code = _LOWER_CODES.get(_lower(word))
    return None if code is None else (end - 3, code)


def _currency_span(text: str, position: int) -> tuple[int, str] | None:
    """The currency word written before `position`, past any whitespace: its start and code."""
    end = position
    while end > 0 and text[end - 1].isspace():
        end -= 1
    return _currency_word_before(text, end)


def _currency_before(text: str, position: int) -> str | None:
    """The currency written before `position`, past any whitespace."""
    found = _currency_span(text, position)
    return None if found is None else found[1]


def _hide(
    pattern: re.Pattern[str], text: str, hidden: bytearray, *, bare_only: bool = False
) -> str:
    def blank(found: re.Match[str]) -> str:
        if bare_only and _reads_currency(_Masked(found.string, hidden), found.start(), found.end()):
            return found[0]
        hidden[found.start() : found.end()] = b"\x01" * len(found[0])
        return "\x00" * len(found[0])

    return pattern.sub(blank, text)


def _mask(text: str, *, passage: bool) -> _Masked:
    hidden = bytearray(len(text))
    masked = _hide(CODE, text, hidden)
    if passage:
        masked = _hide(DATE, masked, hidden)
        masked = _hide(PERIOD, masked, hidden)
        masked = _hide(MONTH_COUNT, masked, hidden, bare_only=True)
    return _Masked(masked, bytes(hidden))


def _after(text: str, position: int) -> _After:
    """What the number that ends at `position` carries: unit, scale, glued letters or nothing."""
    found = _UNIT.match(text, position)
    if found is not None:
        return _After(_UNITS[_lower(found["word"])], found.end())
    scaled = _SCALED.match(text, position)
    if scaled is not None:
        word = _currency_word_before(text, scaled.end("currency"))
        if word is not None:
            return _After(_UNITS[_lower(scaled["scale"])], scaled.end(), word[1])
    end = position
    while end < len(text) and text[end].isalpha():
        end += 1
    if end == position:
        return _After(None, position)
    if _lower(text[position:end]) in _ENDINGS:
        return _After(None, position, ending=True)
    return _After("unrecognised", end)


def _find(pattern: re.Pattern[str], masked: _Masked, position: int) -> re.Match[str] | None:
    """The next number from `position`; a leading point after a masked character is skipped."""
    while (found := pattern.search(masked.text, position)) is not None:
        start = found.start()
        if not (found["lead"] and start > 0 and masked.hidden[start - 1]):
            return found
        position = start + 1
    return None


def _is_minus(masked: _Masked, start: int) -> bool:
    """A `-` or minus sign directly before `start`, after a character that is not part of a word."""
    if start == 0 or masked.text[start - 1] not in "-−":
        return False
    if start == 1:
        return True
    before = masked.text[start - 2]
    return not (before.isalnum() or before in "_)" or masked.hidden[start - 2])


def _gap(text: str, position: int) -> int:
    """`position` moved back over whitespace."""
    while position > 0 and text[position - 1].isspace():
        position -= 1
    return position


def _prefix(masked: _Masked, number: int) -> _Prefix:
    """What stands before the number at `number`: a minus, a currency, or a minus before a currency."""
    if _is_minus(masked, number):
        return _Prefix(number - 1, True, None, number - 1)
    span = _currency_span(masked.text, number)
    if span is None:
        return _Prefix(number, False, None, number)
    if _is_minus(masked, span[0]):
        return _Prefix(span[0] - 1, True, span[1], span[0] - 1)
    return _Prefix(number, False, span[1], span[0])


def _opener(text: str, anchor: int) -> tuple[int, str | None, bool] | None:
    """An opening bracket before `anchor`: its place, the currency and whether a minus written just after it."""
    place = _gap(text, anchor)
    if place > 0 and text[place - 1] == "(":
        return place - 1, None, False
    word = _currency_word_before(text, place)
    if word is None:
        return None
    minus = word[0] > 0 and text[word[0] - 1] in "-−"
    place = _gap(text, word[0] - 1 if minus else word[0])
    if place > 0 and text[place - 1] == "(":
        return place - 1, word[1], minus
    return None


def _bracket(masked: _Masked, prefix: _Prefix, end: int) -> _Bracket | None:
    """The brackets round the figure whose number and unit end at `end`, when both are written."""
    opened = _opener(masked.text, prefix.anchor)
    if opened is None:
        return None
    close = end
    while close < len(masked.text) and masked.text[close].isspace():
        close += 1
    if masked.text[close : close + 1] != ")":
        return None
    return _Bracket(opened[0], close + 1, opened[1], opened[2])


def _walk_signs(masked: _Masked, position: int) -> int:
    """`position` moved back over brackets, minus signs, dashes and `+` (a hyphen only as a minus)."""
    while position > 0 and masked.text[position - 1] in _BEFORE_SIGNS:
        if masked.text[position - 1] in "-−" and not _is_minus(masked, position):
            break
        position -= 1
    return position


def _reads_currency(masked: _Masked, number: int, end: int) -> bool:
    """The reader, reading the figure that runs from `number` to `end`, finds a currency for it."""
    prefix = _prefix(masked, number)
    bracket = _bracket(masked, prefix, end)
    if bracket is None:
        return (
            prefix.currency or _currency_before(masked.text, _walk_signs(masked, prefix.start))
        ) is not None
    inner = bracket.currency or prefix.currency
    return (inner or _currency_before(masked.text, _walk_signs(masked, bracket.start))) is not None


def _figure(masked: _Masked, found: re.Match[str], text: str) -> tuple[Figure, int]:
    line = masked.text
    prefix = _prefix(masked, found.start())
    after = _after(line, found.end())
    bracket = _bracket(masked, prefix, after.end)
    start, end, minus, inner = prefix.start, after.end, prefix.minus, prefix.currency
    if bracket is not None:
        start, end = bracket.start, bracket.close
        minus = minus or bracket.minus
        inner = bracket.currency or inner
        if after.unit is None:
            after = _after(line, end)
            end = after.end
    digits = found["lead"] or (found["int"].replace(",", "") + (found["dec"] or ""))
    figure = Figure(
        value=Decimal(digits),
        negative=minus or bracket is not None,
        bracketed=bracket is not None and not minus,
        unit=after.unit,
        currency=inner or _currency_before(line, _walk_signs(masked, start)) or after.currency,
        shown=text[start:end],
        column=start + 1,
    )
    return figure, end


def _read(text: str, masked: _Masked) -> list[Figure]:
    figures: list[Figure] = []
    position = 0
    while (found := _find(_NUMBER, masked, position)) is not None:
        figure, position = _figure(masked, found, text)
        figures.append(figure)
    return figures


def _places(value: Decimal) -> int:
    """The decimal places `value` is written to."""
    return -int(value.as_tuple().exponent)


def _rounded(value: Decimal, places: int) -> tuple[Decimal, Decimal]:
    """`value` rounded to `places` decimals, half up and half even, in a context sized from it."""
    size = len(value.as_tuple().digits) + _places(value) + places + 3
    context = Context(prec=size, Emax=size, Emin=-size)
    exponent = Decimal((0, (1,), -places))
    return (
        value.quantize(exponent, rounding=ROUND_HALF_UP, context=context),
        value.quantize(exponent, rounding=ROUND_HALF_EVEN, context=context),
    )


def _is_note(figure: Figure, before: Figure) -> bool:
    """A bracketed figure that is a ratio, or a rounding or a thousands-separated copy of `before`."""
    if figure.unit in _RATIOS:
        return True
    if figure.unit not in (None, before.unit) or before.negative:
        return False
    places, before_places = _places(figure.value), _places(before.value)
    if places == before_places:
        return figure.value == before.value and "," in figure.shown and "," not in before.shown
    return places < before_places and figure.value in _rounded(before.value, places)


def _is_note_on(text: str, figure: Figure, before: Figure, before_note: bool) -> bool:
    if not figure.bracketed or before.bracketed or before_note:
        return False
    end = before.column - 1 + len(before.shown)
    start = figure.column - 1
    if end > start or text[end:start].strip(" \t"):
        return False
    return _is_note(figure, before)


def _with_notes(text: str, figures: list[Figure], codes: list[Figure]) -> tuple[Figure, ...]:
    """`figures` with each note read as written; `codes` is the line read with only codes masked."""
    code_notes: list[bool] = []
    for index, figure in enumerate(codes):
        code_notes.append(
            index > 0 and _is_note_on(text, figure, codes[index - 1], code_notes[index - 1])
        )
    columns = [figure.column for figure in codes]
    result: list[Figure] = []
    for figure in figures:
        at = bisect_left(columns, figure.column) - 1
        noted = at >= 0 and _is_note_on(text, figure, codes[at], code_notes[at])
        result.append(figure.model_copy(update=_PLAIN) if noted else figure)
    return tuple(result)


def read_figures(text: str, *, passage: bool) -> tuple[Figure, ...]:
    """The figures of one line of text, left to right.

    Dates and period labels are read as written when `passage` is false; masked when true.
    """
    figures = _read(text, _mask(text, passage=passage))
    if not any(figure.bracketed for figure in figures):
        return tuple(figures)
    codes = _read(text, _mask(text, passage=False)) if passage else figures
    return _with_notes(text, figures, codes)


def _plain(found: re.Match[str]) -> bool:
    """A whole number below 100, or of four digits from 1900 to 2099, compared as a Decimal."""
    digits = found["int"]
    if digits is None or found["dec"] or "," in digits:
        return False
    value = Decimal(digits)
    return value < 100 or (len(digits) == 4 and 1900 <= value <= 2099)


def _comma_run(text: str, end: int) -> int | None:
    """The end of the digits, commas and points that follow a number at `end` with `,` and a digit."""
    if text[end : end + 1] != "," or not text[end + 1 : end + 2].isdecimal():
        return None
    while end < len(text) and (
        text[end].isdecimal() or (text[end] in ",." and text[end + 1 : end + 2].isdecimal())
    ):
        end += 1
    return end


def _reason(found: re.Match[str], after: _After, currency: str | None) -> str | None:
    """Why `found` is refused, or None when it passes; `currency` is the reader's for the figure."""
    if after.unit == "unrecognised":
        return _FORM
    if len(found["lead"] or found["dec"] or "") > 3:
        return _DECIMALS
    if currency == "unrecognised":
        return _CURRENCY
    if after.unit in _SCALES:
        return None if currency else _SCALE
    if after.unit is not None or currency or _plain(found):
        return None
    return _BARE


def _dash_before(text: str, start: int) -> int | None:
    """The en or em dash directly before the figure at `start` or before its currency."""
    if start > 0 and text[start - 1] in _DASHES:
        return start - 1
    span = _currency_span(text, start)
    if span is not None and span[0] > 0 and text[span[0] - 1] in _DASHES:
        return span[0] - 1
    return None


def _is_range(masked: _Masked, dash: int, previous_end: int) -> bool:
    """The dash at `dash` touches a digit, `%`, a masked character or the end of the unit before it."""
    return dash > 0 and (
        masked.text[dash - 1].isdecimal()
        or masked.text[dash - 1] == "%"
        or bool(masked.hidden[dash - 1])
        or dash == previous_end
    )


def _past_bracket(masked: _Masked, found: re.Match[str], after: _After) -> _After:
    """The unit written after a closing bracket, when the figure has none before it."""
    bracket = _bracket(masked, _prefix(masked, found.start()), after.end)
    if bracket is None or after.unit is not None:
        return after
    beyond = _after(masked.text, bracket.close)
    return after if beyond.unit is None else beyond


def _currency_minus(line: int, masked: _Masked, text: str) -> tuple[Finding, ...]:
    """A currency word directly before a hyphen or minus sign and a digit: the reader reads no minus."""
    found: list[Finding] = []
    for hyphen in _HYPHEN_NUMBER.finditer(masked.text):
        word = _currency_word_before(masked.text, hyphen.start())
        if word is None or masked.text[hyphen.start() - 1] not in _LETTERS:
            continue
        found.append(
            refusal("figure.form", line, text[word[0] : hyphen.end()], _MINUS, word[0] + 1)
        )
    return tuple(found)


def _line_findings(line: int, text: str) -> tuple[Finding, ...]:
    masked = _mask(text, passage=True)
    findings = list(_currency_minus(line, masked, text))
    position = 0
    previous_end = -1
    while (found := _find(_FIGURE, masked, position)) is not None:
        position = found.end()
        after = _after(masked.text, position)
        if after.ending:
            continue
        after = _past_bracket(masked, found, after)
        start = found.start()
        dash = _dash_before(masked.text, start)
        if dash is not None and not _is_range(masked, dash, previous_end):
            findings.append(refusal("figure.form", line, text[dash : after.end], _DASH, dash + 1))
        run = _comma_run(masked.text, position)
        end = after.end if run is None else run
        currency = _figure(masked, found, text)[0].currency
        reason = _reason(found, after, currency) if run is None else _COMMA
        if reason is not None:
            findings.append(refusal("figure.form", line, text[start:end], reason, start + 1))
        position = max(position, end)
        previous_end = end
    return tuple(findings)


def check_form(document: HandoffDocument, context: CheckContext) -> tuple[Finding, ...]:
    reader = try_reader(document)
    if reader is None or reader.format != "new":
        return ()
    return tuple(
        finding
        for line in passage_text(document, reader)
        for finding in _line_findings(line.line, line.text)
    )
