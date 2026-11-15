"""Answer key for 1B PR 6a (units named, the currency named), 6a2 (R46), 6a3 (R49) and 6a4 (R59), by the controller.

Every figure, name and text is invented. Rows hold inputs only, as in `make_pr5.py`, whose
oracle this script loads for the foundation's tables, the cells, the numbers and the cell check;
an edit with a third element `"all"` replaces every occurrence. Worked here: the unit check
(the cells that may state a named row's unit, the unit words each names, the issue reported),
the foundation's text (this script's own reading: every kept line that is not a heading, a fence
or blank) and whether it names the block's currency, and each outcome. `words` and `currencies`
hold text forms with their expected reading written by hand from the predecessor's cases (text
forms, not figures); `render()` asserts this script's patterns give them. A foundation whose
level-2 headings are not the handoff's six, in order, is the parser's own refusal, worded as
`handoff/document.py` words it. R46 (PR 6a2): thousands, millions and billions; billions is
never a block's unit, so a row naming it, and not the block's unit, is refused under either
scale. Each of the twelve forms the 6a review found is a row under both blocks. R48: no letter
before a letter code; a bare sign takes none. R49 (PR 6a3), with R49a and R49b: marks before a
letter code, glued or after one space (capital `T` for thousands as well as `k`), `000` after a
code or sign and one space, `(000)` and `MM` standing alone, and the glued marks also name the
currency. R50: only the operand's header, the first header cell and a `Unit` or `Units` column
excuse a group; any cell can raise an issue. R51: capital `M` glued before `US$` or `$` is an
ambiguous unit, refused under both blocks. R57, R59a and R59b (PR 6a4): a table's caption is the
paragraph directly before it (this script's own `captions`), and each caption line is one more
cell of the operand's group, named `caption`, that may raise an issue but never excuses (R59f); a caption
two paragraphs up, or past a heading, is not read. Run this file to write `pr6a.json` next to it.
"""

import importlib.util
import json
import re
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("make_pr5", HERE / "make_pr5.py")
assert SPEC is not None and SPEC.loader is not None
PR5: Any = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PR5)

# R46: three units, letter boundaries by an explicit class, case folded as the code already folds
# it (no re.ASCII: that would also narrow \s), and one set of scale marks shared with the currency
# form. R48: no letter before a letter code; a bare sign takes none (`C$m`, `HK$m`, `A$000`).
CURRENCY = r"(?:(?<![A-Za-z])(?:US\$|USD|EUR|GBP)|[$€£])"
SIGN = r"(?:US\$|[$€£])"
# R51: capital `M` glued directly before `US$` or `$` (`MUS$`, `M$`) may mean thousands (Chilean
# statements) or millions: an ambiguous unit, never a block's, and never read as millions.
AMBIGUOUS = r"(?<![A-Za-z])(?-i:M)(?:US\$|\$)"
UNITS = ["ambiguous", "billions", "millions", "thousands"]
WORDS_OF = {
    "thousands": "thousands?",
    "millions": "millions?|mln|mm",
    "billions": "billions?|bln|bn",
}
MARKS = {"thousands": "k", "millions": "mln|mm|mn|m", "billions": "bln|bn"}
# R49, R49a, R49b: the marks before a code or sign (capital T is thousands too, never after a
# code), the marks glued before a letter code, and the letter codes they go before.
BEFORE = {**MARKS, "thousands": "k|(?-i:T)"}
GLUED = {"thousands": "k|(?-i:T)", "millions": "m"}
CODES = "USD|EUR|GBP"
ZEROS = "000s?"
SUFFIX = "|".join([ZEROS, *MARKS.values()])


def unit_pattern(unit: str) -> "re.Pattern[str]":
    if unit == "ambiguous":
        return re.compile(AMBIGUOUS, re.IGNORECASE)
    forms = [
        rf"(?<![A-Za-z])(?:{WORDS_OF[unit]})(?![A-Za-z])",
        rf"{CURRENCY}\s?(?:{MARKS[unit]})(?![A-Za-z])",
        rf"(?<![A-Za-z])(?!(?-i:M)(?:US\$|\$))(?:{BEFORE[unit]})\s?{SIGN}",
        rf"(?<![A-Za-z0-9])(?:{BEFORE[unit]})\s(?:{CODES})(?![A-Za-z])",
    ]
    if unit in GLUED:
        forms.append(rf"(?<![A-Za-z])(?:{GLUED[unit]})(?:{CODES})(?![A-Za-z])")
    if unit == "thousands":
        forms += [
            rf"{CURRENCY}(?:['’]|\s)?{ZEROS}(?![A-Za-z0-9])",
            rf"(?<![0-9])['’]{ZEROS}(?![A-Za-z0-9])",
            r"(?<![A-Za-z0-9.,])000s(?![A-Za-z0-9])",
            r"(?<![A-Za-z0-9])\(000\)(?![A-Za-z0-9])",
        ]
    return re.compile("|".join(forms), re.IGNORECASE)


PATTERNS = {unit: unit_pattern(unit) for unit in UNITS}
SIGNS = {"USD": r"(?i:(?<![A-Za-z])US\$)", "EUR": "€", "GBP": "£"}
MESSAGES = {
    "unit": "base {key}: row `{row}` states its {what} as `{cell}`, not the block's unit ({unit}); "
    "state a reason instead of an amount",
    "ambiguous": "base {key}: row `{row}` states its {what} as `{cell}`, whose mark is ambiguous "
    "(thousands or millions), not the block's unit ({unit}); state a reason instead of an amount",
    "currency": "CP-1 nowhere names `{currency}`: state `currency` as the three-letter code of the "
    "currency CP-1 reports its figures in.",
}
REQUIRED = ["Request", "Sources", "Findings", "Calculations", "Gaps", "Next module"]
Doc = dict[str, Any]


def skeleton(text: str) -> str | None:
    """The parser's refusal of the level-2 headings, or None when they are the six, in order."""
    lines = PR5.shown_lines(text)
    heads = [(index, PR5.HEADING.fullmatch(line)) for index, line, fenced in lines if not fenced]
    twos = [(index, m[2].strip()) for index, m in heads if m is not None and len(m[1]) == 2]
    for (index, title), required in zip(twos, REQUIRED, strict=False):
        if title != required:
            found = PR5.echo(title)
            return f"line {index}: level-2 heading `{found}` found where `{required}` is required"
    if len(twos) > len(REQUIRED):
        index, title = twos[len(REQUIRED)]
        found = PR5.echo(title)
        return f"line {index}: level-2 heading `{found}` is not allowed after `Next module`"
    if len(twos) < len(REQUIRED):
        count = len(lines) - (1 if text.endswith("\n") else 0)
        return f"line {count}: level-2 heading `{REQUIRED[len(twos)]}` is missing"
    return None


def units_named(text: str) -> list[str]:
    return [unit for unit in UNITS if PATTERNS[unit].search(text)]


def names_currency(text: str, currency: str) -> bool:
    prefix = "|".join(GLUED.values())
    forms = [rf"(?<![A-Za-z])(?i:{prefix})?{re.escape(currency)}(?i:{SUFFIX})?(?![A-Za-z0-9])"]
    forms += [SIGNS[currency]] if currency in SIGNS else []
    return re.search("|".join(forms), text) is not None


UNIT_COLUMNS = ("Unit", "Units", "Reporting unit")
LIST_ITEM = re.compile(r"[ \t]*(?:[-*+]|[0-9]{1,3}[.)])[ \t]")
TABLE_ROW = re.compile(r" {0,3}\|")
COMMENT_LINE = re.compile(r"\s*<!--.*-->\s*")


def captions(text: str) -> dict[int, list[str]]:
    """R57, R59a: for each table's header line, the stripped lines of the paragraph directly before
    it (blank lines and whole-line comments between are allowed; a heading, a list item, a code
    block or another table between is not). This script's own reading; a table with no caption has
    no entry."""
    found: dict[int, list[str]] = {}
    above: list[str] | None = None  # the paragraph that is the last block read, if it is one
    held: tuple[str, list[str]] | None = None  # the block being read: its kind and lines
    in_rows = False

    def close() -> None:
        nonlocal above, held
        if held is not None:
            above = held[1] if held[0] == "paragraph" else None
            held = None

    for index, line, fenced in PR5.shown_lines(text):
        row = not fenced and TABLE_ROW.match(line) is not None
        if row and not in_rows:
            close()
            if above is not None:
                found[index] = above
            above = None
        elif fenced or (not row and PR5.HEADING.fullmatch(line)):
            close()
            above = None
        elif not row and (not line.strip() or COMMENT_LINE.fullmatch(line)):
            close()
        elif not row:
            if LIST_ITEM.match(line):
                close()
                held = ("item", [])
            elif held is None:
                held = ("paragraph", [])
            held[1].append(
                LIST_ITEM.sub("", line, count=1).strip() if held[0] == "item" else line.strip()
            )
        in_rows = row
    return found


def unit_issues(
    row: str, kind: str, header: str, read: list[Any], above: dict[int, list[str]], block: str
) -> list[tuple[str, str]]:
    """The (what, cell) issues of the named row and header under `block`: in every group of every
    table, unless a cell that may excuse names the block. R59b: a caption line is a group cell
    named `caption` that may raise an issue and never excuses (R59f)."""
    issues: list[tuple[str, str]] = []
    for first, head, body in read:
        caption = above.get(first, [])
        for c in (i for i in range(1, len(head)) if PR5.plain(head[i]) == PR5.plain(header)):
            for line in (r for r in body if PR5.plain(r[0]) == PR5.plain(row)):
                group = [(f"{kind} header", head[c]), ("first header cell", head[0])]
                group += [(PR5.plain(head[i]), cell) for i, cell in enumerate(line) if i != c]
                group += [("caption", cell) for cell in caption]
                excuse = [head[c], head[0]]  # R59f: a caption never excuses
                excuse += [
                    cell
                    for i, cell in enumerate(line)
                    if i != c and PR5.plain(head[i]) in UNIT_COLUMNS
                ]
                if not any(block in units_named(cell) for cell in excuse):
                    issues += [(w, cell) for w, cell in group if set(units_named(cell)) - {block}]
    return issues


def unit_problem(
    key: str, operand: Doc, read: list[Any], above: dict[int, list[str]], scale: int, currency: str
) -> str | None:
    block = "thousands" if scale == 1000 else "millions"
    kind = "period" if operand["period"] is not None else "column"
    issues = unit_issues(operand["row"], kind, operand[kind], read, above, block)
    if not issues:
        return None
    what, cell = min(issues)
    unit = f"{currency} millions, scale 1" if scale == 1 else f"{currency} thousands, scale 1000"
    row = PR5.echo(PR5.plain(operand["row"]))
    message = MESSAGES["ambiguous" if "ambiguous" in units_named(cell) else "unit"]
    return message.format(
        key=key, row=row, what=PR5.echo(what), cell=PR5.echo(PR5.plain(cell)), unit=unit
    )


def text_lines(text: str) -> list[str]:
    skipped = PR5.left_out(PR5.shown_lines(text))
    return [
        line
        for index, line, fenced in PR5.shown_lines(text)
        if not fenced and index not in skipped and line.strip() and not PR5.HEADING.fullmatch(line)
    ]


def edited(name: str, edits: list[list[str]]) -> str:
    text: str = (PR5.FIXTURES / name).read_text("utf-8")
    for old, new, *every in edits:
        assert text.count(old) == 1 or (every == ["all"] and text.count(old) > 1), old
        text = text.replace(old, new)
    return text


def outcome(row: Doc) -> list[str] | None:
    foundation: str = row.get("foundation", "foundation.md")
    source: str = row.get("source", foundation)
    text = edited(foundation, row.get("edits", []))
    if (refused := skeleton(text)) is not None:
        return ["HandoffError", refused]
    try:
        read = PR5.tables(text)
    except PR5.Repeated as error:
        return ["HandoffError", str(error)]
    above = captions(text)
    block = PR5.block(source, row.get("ops", []))
    scale, currency = block["scale"], block["currency"]
    for key in PR5.OPERANDS:
        operand = block["base"][key]
        if (message := PR5.problem(key, operand, read)) is not None:
            return ["cell", f"base {key}", message]
        unit = operand["amount"] and unit_problem(key, operand, read, above, scale, currency)
        if unit:
            return ["unit", f"base {key}", unit]
    if not any(names_currency(line, currency) for line in text_lines(text)):
        return ["currency", "currency", MESSAGES["currency"].format(currency=currency)]
    return None


# Pieces of ROWS, written as JSON string text (`\n` is a newline once the row is read).
CALC = PR5.CALC
PASSAGE = PR5.PASSAGE
SOURCES = PR5.SOURCES
NO_USD = r'["USD millions", "millions", "all"], ["US$m", "millions", "all"]'
LONG = "Revenue from the sale of invented industrial goods and of the services that go with them"

ROWS = rf"""
{{"label": "every operand's row is in the block's unit"}}
{{"label": "a thousands foundation's rows are in thousands", "foundation": "foundation-thousands.md"}}
{{"label": "the forward model's thousands block over the thousands foundation", "foundation": "foundation-thousands.md", "source": "forward-model-thousands.md"}}
{{"label": "another cell of the row names the other unit", "edits": [["| 391 | USD millions |", "| 391 | USD thousands |"]]}}
{{"label": "the named period's header names the other unit", "edits": [["{CALC}", "{CALC}\n| Line item | FY2024 USD thousands |\n| --- | --- |\n| Revenue check | 1,456 |\n"]], "ops": [[["base", "revenue", "row"], "Revenue check"], [["base", "revenue", "period"], "FY2024 USD thousands"]]}}
{{"label": "the first header cell names the other unit", "edits": [["{CALC}", "{CALC}\n| Line item (USD thousands) | FY2024 |\n| --- | --- |\n| Revenue check | 1,456 |\n"]], "ops": [[["base", "revenue", "row"], "Revenue check"]]}}
{{"label": "the row's own label names the other unit", "edits": [["{CALC}", "{CALC}\n| Line item | FY2024 |\n| --- | --- |\n| Revenue in thousands | 1,456 |\n"]], "ops": [[["base", "revenue", "row"], "Revenue in thousands"]]}}
{{"label": "a row naming both units is accepted", "edits": [["| 391 | USD millions |", "| 391 | USD millions, restated from USD thousands |"]]}}
{{"label": "a row naming no unit is accepted", "edits": [["{CALC}", "{CALC}\n| Line item | FY2024 |\n| --- | --- |\n| Revenue check | 1,456 |\n"]], "ops": [[["base", "revenue", "row"], "Revenue check"]]}}
{{"label": "a second table printing the row in the other unit", "edits": [["{CALC}", "{CALC}\n| Line item | FY2024 | Unit |\n| --- | --- | --- |\n| Revenue | 1,456 | USD thousands |\n"]]}}
{{"label": "the first issue by column name, then text", "edits": [["{CALC}", "{CALC}\n| Line item | FY2024 | Unit | Note |\n| --- | --- | --- | --- |\n| Revenue check | 1,456 | USD thousands | in thousands |\n"]], "ops": [[["base", "revenue", "row"], "Revenue check"]]}}
{{"label": "two rows of the label, the second in the other unit", "edits": [["{CALC}", "{CALC}\n| Line item | FY2024 | Unit |\n| --- | --- | --- |\n| Revenue check | 1,456 | USD millions |\n| Revenue check | 1,456 | USD thousands |\n"]], "ops": [[["base", "revenue", "row"], "Revenue check"]]}}
{{"label": "two rows of the label, the first in the other unit", "edits": [["{CALC}", "{CALC}\n| Line item | FY2024 | Unit |\n| --- | --- | --- |\n| Revenue check | 1,456 | USD thousands |\n| Revenue check | 1,456 | USD millions |\n"]], "ops": [[["base", "revenue", "row"], "Revenue check"]]}}
{{"label": "a thousands block over a balance row printed in US$m", "foundation": "foundation-thousands.md", "ops": [[["base", "cash", "row"], "FY2024"], [["base", "cash", "period"], null], [["base", "cash", "column"], "Cash"], [["base", "cash", "amount"], "283"]]}}
{{"label": "a millions block reads the same US$m balance row", "ops": [[["base", "cash", "row"], "FY2024"], [["base", "cash", "period"], null], [["base", "cash", "column"], "Cash"]]}}
{{"label": "the unit message names the block's currency", "edits": [["| 391 | USD millions |", "| 391 | USD thousands |"]], "ops": [[["currency"], "EUR"]]}}
{{"label": "the unit message shows the row without emphasis, cut at 80", "edits": [["{CALC}", "{CALC}\n| Line item | FY2024 | Unit |\n| --- | --- | --- |\n| {LONG} | 1,456 | USD thousands |\n"]], "ops": [[["base", "revenue", "row"], "**{LONG}**"]]}}
{{"label": "a reason operand is not checked for its unit", "edits": [["| 391 | USD millions |", "| 391 | USD thousands |"]], "ops": [[["base", "revenue"], {{"amount": null, "reason": "Not read.", "row": null, "period": null, "column": null}}]]}}
{{"label": "the cell check comes before the unit check", "edits": [["| 391 | USD millions |", "| 391 | USD thousands |"]], "ops": [[["base", "revenue", "amount"], "1457"]]}}
{{"label": "an earlier operand's unit before a later operand's cell", "edits": [["| 391 | USD millions |", "| 391 | USD thousands |"]], "ops": [[["base", "undrawn", "amount"], "176"]]}}
{{"label": "a currency the foundation never names", "ops": [[["currency"], "GBP"]]}}
{{"label": "a EUR foundation does not name USD", "foundation": "foundation-eur.md", "source": "foundation.md"}}
{{"label": "a EUR block over the EUR foundation", "foundation": "foundation-eur.md", "source": "foundation.md", "ops": [[["currency"], "EUR"]]}}
{{"label": "USD named only in the block's own section", "edits": [{NO_USD}]}}
{{"label": "USD named only in a reader passage", "edits": [{NO_USD}, ["{PASSAGE}", "{PASSAGE}Amounts are in USD.\n"]]}}
{{"label": "USD named only under Sources", "edits": [{NO_USD}, ["{SOURCES}", "{SOURCES}\nAmounts are in USD.\n"]]}}
{{"label": "USD named only in a heading", "edits": [{NO_USD}, ["### T4.4 Income statement", "### T4.4 Income statement (USD)"]]}}
{{"label": "USD named only in code", "edits": [{NO_USD}, ["{CALC}", "{CALC}\n```\nUSD\n```\n"]]}}
{{"label": "USD named in Calculations prose", "edits": [{NO_USD}, ["{CALC}", "{CALC}\nAmounts are in USD.\n"]]}}
{{"label": "USD named in a list item", "edits": [{NO_USD}, ["{CALC}", "{CALC}\n- Amounts are in USD.\n"]]}}
{{"label": "USD named in a table label", "edits": [{NO_USD}, ["{CALC}", "{CALC}\n**Figures in USD**\n| Line item | FY2024 |\n| --- | --- |\n| Revenue check | 1,456 |\n"]]}}
{{"label": "USD named by its sign", "edits": [{NO_USD}, ["{CALC}", "{CALC}\nAmounts are in US$.\n"]]}}
{{"label": "a lower-case code names no currency", "edits": [{NO_USD}, ["{CALC}", "{CALC}\nAmounts are in usd.\n"]]}}
{{"label": "a bare dollar sign names no currency", "edits": [{NO_USD}, ["{CALC}", "{CALC}\nAmounts are in $m.\n"]]}}
{{"label": "a foundation with Request as its only top-level section", "edits": [["\n## Sources\n", "\n### Sources\n"], ["\n## Findings\n", "\n### Findings\n"], ["\n## Calculations\n", "\n### Calculations\n"], ["\n## Gaps\n", "\n### Gaps\n"], ["\n## Next module\n", "\n### Next module\n"]]}}
{{"label": "a foundation whose second top-level section is not Sources", "edits": [["\n## Sources\n", "\n### Sources\n"]]}}
{{"label": "a long period header is cut at 80 in the message", "edits": [["{CALC}", "{CALC}\n| Line item | {LONG} |\n| --- | --- |\n| Revenue check | 1,456 |\n"]], "ops": [[["base", "revenue", "row"], "Revenue check"], [["base", "revenue", "period"], "{LONG}"], [["base", "revenue", "amount"], "1457"]]}}
{{"label": "a long cell that is not a number is cut at 80 in the message", "edits": [["{CALC}", "{CALC}\n| Line item | FY2024 |\n| --- | --- |\n| Revenue check | {LONG} |\n"]], "ops": [[["base", "revenue", "row"], "Revenue check"]]}}
{{"label": "a period header compares with its case", "ops": [[["base", "revenue", "period"], "fy2024"]]}}
{{"label": "interest stated negative names the magnitude rule", "ops": [[["base", "interest", "amount"], "-64"]]}}
{{"label": "capex stated with the cell's sign names the magnitude rule", "ops": [[["base", "capex", "amount"], "-72"]]}}
{{"label": "taxes stated negative against a positive cell names the magnitude rule", "edits": [["| -29 | -37 |", "| -29 | 37 |"]], "ops": [[["base", "taxes", "amount"], "-37"]]}}
{{"label": "working capital of another size names no sign rule", "ops": [[["base", "wc", "amount"], "20"]]}}
"""

WORDS: list[Any] = [
    ["US$ thousands", ["thousands"]],
    ["USD thousands;  6.25%", ["thousands"]],
    ["In thousands", ["thousands"]],
    ["USD 858,064 thousand", ["thousands"]],
    ["$000", ["thousands"]],
    ["'000s", ["thousands"]],
    ["US$k", ["thousands"]],
    ["USD K", ["thousands"]],
    ["US$ million", ["millions"]],
    ["USD millions", ["millions"]],
    ["US$m", ["millions"]],
    ["USD m", ["millions"]],
    ["$M", ["millions"]],
    ["USD mm", ["millions"]],
    ["US$mn", ["millions"]],
    ["€mn", ["millions"]],
    ["GBP bn", ["billions"]],
    ["stated in millions", ["millions"]],
    ["USD million/billion", ["billions", "millions"]],
    ["US$ thousands; USD 37.6 million", ["millions", "thousands"]],
    ["", []],
    ["p.4", []],
    ["9M 2025", []],
    ["1,000", []],
    ["US$ and a mid-year note", []],
    ["Mmm", []],
    ["m", []],
    # R46: the twelve forms, then one text per part of each pattern, then texts that name no unit.
    ["GBP000", ["thousands"]],
    ["£000", ["thousands"]],
    ["€000", ["thousands"]],
    ["USD000", ["thousands"]],
    ["k€", ["thousands"]],
    ["_USD thousands_", ["thousands"]],
    ["in 000s", ["thousands"]],
    ["M€", ["millions"]],
    ["USD mln", ["millions"]],
    ["USD bn", ["billions"]],
    ["USD billions", ["billions"]],
    ["€bn", ["billions"]],
    ["£'000", ["thousands"]],
    ["GBP'000", ["thousands"]],
    ["’000", ["thousands"]],
    ["'000", ["thousands"]],
    ["EUR k", ["thousands"]],
    ["GBP k", ["thousands"]],
    ["£k", ["thousands"]],
    ["k$", ["thousands"]],
    ["k US$", ["thousands"]],
    ["EURm", ["millions"]],
    ["£m", ["millions"]],
    ["m£", ["millions"]],
    ["mn$", ["millions"]],
    ["mm €", ["millions"]],
    ["in mln", ["millions"]],
    ["IN MILLIONS", ["millions"]],
    ["USD bln", ["billions"]],
    ["in bn", ["billions"]],
    ["in bln", ["billions"]],
    ["a billion", ["billions"]],
    ["bn£", ["billions"]],
    ["multimillion", []],
    ["multibillion", []],
    ["millionaire", []],
    ["thousandth", []],
    ["AUSD k", []],
    ["USDkm", []],
    ["10 km", []],
    ["commitments", []],
    ["summary", []],
    ["park€", []],
    ["2000s", []],
    ["1,000s", []],
    ["USD 1,000", []],
    ["$0001", []],
    # R48: a letter before a bare sign does not hide the unit.
    ["C$m", ["millions"]],
    ["A$k", ["thousands"]],
    ["HK$m", ["millions"]],
    ["A$000", ["thousands"]],
    ["R$ mn", ["millions"]],
    ["AUS$m", ["millions"]],
    # The 6a2 reviews: a code glued to a billions mark, an apostrophe form after letters, and the
    # boundaries each surviving mutant moved.
    ["USDbn", ["billions"]],
    ["EURbln", ["billions"]],
    ["GBPbn", ["billions"]],
    ["USDbln", ["billions"]],
    ["RMB'000", ["thousands"]],
    ["Rs'000", ["thousands"]],
    ["RMB’000", ["thousands"]],
    ["1USD k", ["thousands"]],
    ["1€m", ["millions"]],
    ["bnUS$", ["billions"]],
    ["kEUR", ["thousands"]],
    ["kUSD", ["thousands"]],
    ["mm", ["millions"]],
    ["$b", []],
    ["USD b", []],
    ["GBP000x", []],
    ["'0001", []],
    ["'000x", []],
    ["1.000s", []],
    ["x000s", []],
    ["a000s", []],
    ["000s1", []],
    ["1'000", []],
    ["CAD m", []],
    ["Xthousands", []],
    ["‘000", []],
    ["5million", ["millions"]],
    ["€m1,234", ["millions"]],
    ["USD\u00a0k", ["thousands"]],
    ["€\u00a0m", ["millions"]],
    ["GBP\u00a0bn", ["billions"]],
    ["k\u00a0€", ["thousands"]],
    ["m\u00a0$", ["millions"]],
    ["bn\u00a0£", ["billions"]],
    ["USD  k", []],
    ["EUR  m", []],
    ["£  bn", ["billions"]],
    ["k  €", []],
    ["mn  $", []],
    ["bln  £", ["billions"]],
    # R49, R49b: marks before a letter code, glued or after one space; capital T; `000` after a
    # code or sign and one space; `(000)` and `MM` standing alone. Then the controls.
    ["TEUR", ["thousands"]],
    ["KEUR", ["thousands"]],
    ["TUSD", ["thousands"]],
    ["kGBP", ["thousands"]],
    ["MEUR", ["millions"]],
    ["MUSD", ["millions"]],
    ["mGBP", ["millions"]],
    ["T€", ["thousands"]],
    ["T $", ["thousands"]],
    ["TUS$", ["thousands"]],
    ["T EUR", ["thousands"]],
    ["k EUR", ["thousands"]],
    ["m EUR", ["millions"]],
    ["mn USD", ["millions"]],
    ["mm GBP", ["millions"]],
    ["bn USD", ["billions"]],
    ["€ 000", ["thousands"]],
    ["USD 000", ["thousands"]],
    ["$ 000", ["thousands"]],
    ["GBP 000s", ["thousands"]],
    ["(000)", ["thousands"]],
    ["EUR (000)", ["thousands"]],
    ["in MM", ["millions"]],
    ["MM", ["millions"]],
    ["Class T EUR", ["thousands"]],
    ["ITEM EUR", []],
    ["TEAM USD", []],
    ["from EUR", []],
    ["AT€", []],
    ["COMM", []],
    ["1 000", []],
    ["t EUR", []],
    ["tEUR", []],
    ["Class AT EUR", []],
    ["km EUR", []],
    ["5m EUR", []],
    ["EUR T", []],
    ["TEURO", []],
    ["USD 1 000", []],
    ["x(000)", []],
    ["1(000)", []],
    ["(0001)", []],
    # R51, then the 6a3 reviews: each new form's whitespace and lookarounds.
    ["MUS$", ["ambiguous"]],
    ["M$", ["ambiguous"]],
    ["MMUS$", ["millions"]],
    ["MM$", ["millions"]],
    ["MGBP", ["millions"]],
    ["kUS$", ["thousands"]],
    ["mUS$", ["millions"]],
    ["M US$", ["millions"]],
    ["AMUS$", []],
    ["T EUR", ["thousands"]],
    ["T\tEUR", ["thousands"]],
    ["EUR 000", ["thousands"]],
    ["k  EUR", []],
    ["EUR  000", []],
    ["(000)s", []],
    ["(000)1", []],
    ["ATEUR", []],
    ["AkEUR", []],
    ["5kEUR", ["thousands"]],
    ["kEUR5", ["thousands"]],
    ["k EURO", []],
    ["m EURO", []],
    ["MMUSD", []],
    ["bnEUR", []],
    ["mmEUR", []],
    ["mnEUR", []],
    # R52: the 6a3 re-review's entries for R51.
    ["5MUS$", ["ambiguous"]],
    ["Mus$", ["ambiguous"]],
]
CURRENCIES: list[Any] = [
    ["Statements (EURm)", "EUR", True],
    ["| Cash | 9 | GBPk |", "GBP", True],
    ["amounts in GBP000", "GBP", True],
    ["GBPmn and GBPbn", "GBP", True],
    ["sterling, GBP", "GBP", True],
    ["revenue of £120m", "GBP", True],
    ["revenue of €120m", "EUR", True],
    ["revenue of US$120m", "USD", True],
    ["usd millions", "USD", False],
    ["CAD millions", "CAD", True],
    ["revenue of $120m", "USD", False],
    ["revenue of C$120m", "CAD", False],
    ["USDA and GBPS", "USD", False],
    ["revenue of £120m", "USD", False],
    ["US$m", "GBP", False],
    ["no unit stated", "EUR", False],
    ["all of net debt", "ALL", False],
    ["try again", "TRY", False],
    ["ALL millions", "ALL", True],
    ["us$m", "USD", True],
    ["EURM", "EUR", True],
    ["Revenue (M€)", "EUR", True],
    ["Statements (k€)", "EUR", True],
    ["revenue 120m£", "GBP", True],
    ["AUS$ 5m", "USD", False],
    ["USD1", "USD", False],
    # R46: the currency form reads the units' marks.
    ["USDk", "USD", True],
    ["USD000", "USD", True],
    ["EUR000s", "EUR", True],
    ["USDm", "USD", True],
    ["USDmm", "USD", True],
    ["USDmn", "USD", True],
    ["USDmln", "USD", True],
    ["USDbn", "USD", True],
    ["GBPbln", "GBP", True],
    ["AUSD", "USD", False],
    ["USDkm", "USD", False],
    ["1USD", "USD", True],
    ["_USD_", "USD", True],
    ["aUSD", "USD", False],
    ["USDmillions", "USD", False],
    # R49a: a mark glued before the code names the currency too.
    ["TEUR", "EUR", True],
    ["kEUR", "EUR", True],
    ["MEUR", "EUR", True],
    ["MUSD", "USD", True],
    ["KGBP", "GBP", True],
    ["tEUR", "EUR", False],
    ["ATEUR", "EUR", False],
    ["AkEUR", "EUR", False],
    ["kmEUR", "EUR", False],
    ["TEURO", "EUR", False],
    ["MUSDA", "USD", False],
    ["mnEUR", "EUR", False],
    ["bnUSD", "USD", False],
    # R56b: the code is matched as text, never as a pattern.
    ["Amounts are in USD m.", "U.D", False],
]
# R46 rows: each form in the unit table of a `Revenue check` row, under the block whose unit it
# names (accepted) and under the other block (refused); billions is refused under both.
FORMS = [
    ["GBP000", "thousands"],
    ["£000", "thousands"],
    ["€000", "thousands"],
    ["USD000", "thousands"],
    ["k€", "thousands"],
    ["_USD thousands_", "thousands"],
    ["in 000s", "thousands"],
    ["M€", "millions"],
    ["USD mln", "millions"],
    ["USD bn", "billions"],
    ["USD billions", "billions"],
    ["€bn", "billions"],
]
FORMS_R49 = [
    ["kEUR", "thousands"],
    ["TEUR", "thousands"],
    ["T€", "thousands"],
    ["T EUR", "thousands"],
    ["MEUR", "millions"],
    ["MUSD", "millions"],
    ["m EUR", "millions"],
    ["€ 000", "thousands"],
    ["USD 000", "thousands"],
    ["(000)", "thousands"],
    ["in MM", "millions"],
]
CONTROLS_R49 = [
    ("ITEM EUR", 1000),
    ("TEAM USD", 1000),
    ("from EUR", 1000),
    ("AT€", 1),
    ("COMM", 1000),
    ("1 000", 1),
    ("t EUR", 1),
    ("Class AT EUR", 1),
    ("km EUR", 1),
]
NOT_UNITS = [("10 km", 1), ("commitments", 1000), ("1,000 shares", 1), ("multimillion", 1000)]
CALC_TEXT = json.loads(f'"{CALC}"')
NO_USD_EDITS = json.loads(f"[{NO_USD}]")


def unit_row(label: str, cell: str, scale: int, unit: str = "Unit") -> Doc:
    foundation, amount = (
        ("foundation-thousands.md", "1,456,000") if scale == 1000 else ("foundation.md", "1,456")
    )
    table = f"| Line item | FY2024 | {unit} |\n| --- | --- | --- |\n| Revenue check | {amount} | {cell} |\n"
    edits = [[CALC_TEXT, f"{CALC_TEXT}\n{table}"]]
    return {
        "label": label,
        "foundation": foundation,
        "edits": edits,
        "ops": [[["base", "revenue", "row"], "Revenue check"]],
    }


def r46_rows() -> list[Doc]:
    rows = []
    for form, unit in FORMS:
        for scale, block in ((1, "millions"), (1000, "thousands")):
            reading = "the block's unit" if unit == block else f"{unit}, not the block's {block}"
            rows.append(unit_row(f"`{form}` under a {block} block is {reading}", form, scale))
    for text, scale in NOT_UNITS:
        rows.append(unit_row(f"`{text}` at scale {scale} names no unit", text, scale))
    seventh = [["\n## Next module\n", "\n## Next module\n\n## Appendix\n"]]
    rows.append({"label": "a seventh top-level section after Next module", "edits": seventh})
    rows.append(
        unit_row("a long column header is cut at 80 in the unit message", "USD thousands", 1, LONG)
    )
    rows.append(unit_row("a starred unit cell is shown plain", "**USD thousands**", 1))
    rows.append(unit_row("a long unit cell is cut at 80", f"USD thousands, {LONG}", 1))
    rows.append(unit_row("a starred column header is shown plain", "USD thousands", 1, "**Unit**"))
    two = "| Line item | FY2024 | Unit |\n| --- | --- | --- |\n"
    two += "| Revenue check | 1,456 | USD k |\n| Revenue check | 1,456 | _USD bn_ |\n"
    rows.append(
        {
            "label": "the first unit issue is chosen by the cell as printed",
            "edits": [[CALC_TEXT, f"{CALC_TEXT}\n{two}"]],
            "ops": [[["base", "revenue", "row"], "Revenue check"]],
        }
    )
    for form, unit in FORMS_R49:
        for scale, block in ((1, "millions"), (1000, "thousands")):
            reading = "the block's unit" if unit == block else f"{unit}, not the block's {block}"
            rows.append(unit_row(f"R49: `{form}` under a {block} block is {reading}", form, scale))
    for text, scale in CONTROLS_R49:
        rows.append(unit_row(f"R49: `{text}` at scale {scale} names no unit", text, scale))
    for code, prefixed, ops in (("EUR", "MEUR", [[["currency"], "EUR"]]), ("USD", "MUSD", [])):
        for text, named in ((prefixed, "names"), (f"A{prefixed}", "does not name")):
            edits = [*NO_USD_EDITS, [CALC_TEXT, f"{CALC_TEXT}\nAmounts are in {text}.\n"]]
            label = f"R49a: `{text}` alone {named} {code}"
            rows.append({"label": label, "edits": edits, "ops": ops})
    # R50: only the operand's header, the first header cell and a `Unit`/`Units` column excuse.
    head3, rule3 = "| Line item | FY2024 | Unit |\n", "| --- | --- | --- |\n"
    note4, rule4 = "| Line item | FY2024 | Unit | Note |\n", "| --- | --- | --- | --- |\n"
    r50 = [
        (
            "a label reading `T EUR` does not excuse a Unit cell in millions",
            1000,
            "Class T EUR notes",
            head3 + rule3 + "| Class T EUR notes | 1,456,000 | EUR m |\n",
            [],
        ),
        (
            "a label reading `MM` does not excuse a Unit cell in thousands",
            1,
            "Cash and MM funds",
            head3 + rule3 + "| Cash and MM funds | 1,456 | USD k |\n",
            [],
        ),
        (
            "a value cell `(000)` does not excuse a Unit cell in millions",
            1000,
            "Revenue check",
            "| Line item | FY2024 | FY2023 | Unit |\n"
            + rule4
            + "| Revenue check | 1,456,000 | (000) | USD m |\n",
            [],
        ),
        (
            "a label reading `T $` does not excuse a Unit cell in millions",
            1000,
            "AT&T $ notes",
            head3 + rule3 + "| AT&T $ notes | 1,456,000 | USD m |\n",
            [],
        ),
        (
            "a Note cell reading `mm` does not excuse a Unit cell in thousands",
            1,
            "Revenue check",
            note4 + rule4 + "| Revenue check | 1,456 | USD k | 10 mm plate |\n",
            [],
        ),
        (
            "a `Units` column excuses a Note in the other unit",
            1,
            "Revenue check",
            "| Line item | FY2024 | Units | Note |\n"
            + rule4
            + "| Revenue check | 1,456 | USD millions | in thousands |\n",
            [],
        ),
        (
            "a column headed `unit` in lower case does not excuse",
            1,
            "Revenue check",
            "| Line item | FY2024 | unit | Note |\n"
            + rule4
            + "| Revenue check | 1,456 | USD millions | in thousands |\n",
            [],
        ),
        (
            "the first header cell excuses a Note in the other unit",
            1,
            "Revenue check",
            "| Line item (USD millions) | FY2024 | Note |\n"
            + rule3
            + "| Revenue check | 1,456 | in thousands |\n",
            [],
        ),
        (
            "the named period's header excuses a Note in the other unit",
            1,
            "Revenue check",
            "| Line item | FY2024 USD millions | Note |\n"
            + rule3
            + "| Revenue check | 1,456 | in thousands |\n",
            [[["base", "revenue", "period"], "FY2024 USD millions"]],
        ),
    ]
    for label, scale, row, table, more in r50:
        foundation = "foundation-thousands.md" if scale == 1000 else "foundation.md"
        ops = [[["base", "revenue", "row"], row], *more]
        edits = [[CALC_TEXT, f"{CALC_TEXT}\n{table}"]]
        rows.append(
            {"label": f"R50: {label}", "foundation": foundation, "edits": edits, "ops": ops}
        )
    # R51: `MUS$` and `M$` are refused under both blocks; `MMUS$` stays millions.
    for form, unit in (("MUS$", "ambiguous"), ("M$", "ambiguous"), ("MMUS$", "millions")):
        for scale, block in ((1, "millions"), (1000, "thousands")):
            reading = "the block's unit" if unit == block else f"{unit}, not the block's {block}"
            rows.append(unit_row(f"R51: `{form}` under a {block} block is {reading}", form, scale))
    # R52: the 6a3 re-review's rows for R50 and R51.
    r52 = [
        (
            "R50: a column titled `first header cell` does not excuse",
            "| Line item | FY2024 | first header cell | Unit |\n"
            + rule4
            + "| Revenue check | 1,456 | USD millions | USD k |\n",
        ),
        (
            "R51: a Note chosen before an ambiguous Unit cell takes the unit message",
            note4 + rule4 + "| Revenue check | 1,456 | MUS$ | in thousands |\n",
        ),
    ]
    for label, table in r52:
        edits = [[CALC_TEXT, f"{CALC_TEXT}\n{table}"]]
        rows.append(
            {"label": label, "edits": edits, "ops": [[["base", "revenue", "row"], "Revenue check"]]}
        )
    # R56: `Reporting unit` excuses, case-sensitively, as the model fixtures' own column does.
    # R56a: an emphasised `**Unit**` header excuses once made plain.
    liquidity = "| FY2024 | 283 | 175 | US$m | Reported |"
    noted = "| FY2024 | 283 | 175 | US$m | Reported; before the US$1.2bn disposal |"
    header = (
        "| Period | Cash | Undrawn committed facilities | Reporting unit | Basis and limitation |"
    )
    undrawn = {
        "amount": "175",
        "reason": None,
        "row": "FY2024",
        "period": None,
        "column": "Undrawn committed facilities",
    }
    r56 = [
        ("R56: a `Reporting unit` cell in the block's unit excuses a basis note in billions", []),
        (
            "R56: a column headed `Reporting Unit` with a capital U does not excuse",
            [[header, header.replace("Reporting unit", "Reporting Unit")]],
        ),
    ]
    for label, renamed in r56:
        rows.append(
            {
                "label": label,
                "edits": [[liquidity, noted], *renamed],
                "ops": [[["base", "undrawn"], undrawn]],
            }
        )
    starred = "| Line item | FY2024 | **Unit** | Note |\n" + rule4
    starred += "| Revenue check | 1,456 | USD millions | in thousands |\n"
    rows.append(
        {
            "label": "R56a: an emphasised `**Unit**` header excuses a Note in the other unit",
            "edits": [[CALC_TEXT, f"{CALC_TEXT}\n{starred}"]],
            "ops": [[["base", "revenue", "row"], "Revenue check"]],
        }
    )
    return rows


REASON = {"amount": None, "reason": "Not read.", "row": None, "period": None, "column": None}
CP1 = "../handoffs/tdg-2026-11-09/CP-1.md"
# R59: operands named from the retained public CP-1's own tables, at the places the oracle reads:
# `revenue` at table 70 (a `Unit` column naming US$m, no caption), `ebitda` at table 139 (no unit
# in its own cells; its caption names US$m) and `cash` at table 257 (its cells name no unit and its caption names none).
CP1_NAMED = {
    "revenue": ("Net Income", "FY2024 / 2024-09-30", "1715"),
    "ebitda": ("REFINANCING COSTS", "FY2023", "56"),
    "cash": ("Income tax provision", "FY2024", "500"),
}


def cp1_row(label: str, scale: int, keys: list[str]) -> Doc:
    ops: list[Any] = []
    for key in PR5.OPERANDS:
        if key in keys:
            row, period, amount = CP1_NAMED[key]
            ops += [
                [["base", key, "row"], row],
                [["base", key, "period"], period],
                [["base", key, "amount"], amount],
            ]
        else:
            ops.append([["base", key], REASON])
    source = "foundation-thousands.md" if scale == 1000 else "foundation.md"
    return {"label": label, "foundation": CP1, "source": source, "ops": ops}


def cap_row(
    label: str,
    scale: int,
    above: str,
    head: tuple[str, ...] = ("Line item", "FY2024"),
    cells: tuple[str, ...] = (),
    ops: tuple[Any, ...] = (),
) -> Doc:
    """`above` is the text between the Calculations paragraph and a table of `Revenue check`, with
    a blank line on each side of it."""
    foundation, amount = (
        ("foundation-thousands.md", "1,456,000") if scale == 1000 else ("foundation.md", "1,456")
    )
    rule = "| " + " | ".join("---" for _ in head) + " |\n"
    table = "| " + " | ".join(head) + " |\n" + rule
    table += "| " + " | ".join(["Revenue check", amount, *cells]) + " |\n"
    return {
        "label": label,
        "foundation": foundation,
        "edits": [[CALC_TEXT, f"{CALC_TEXT}\n{above}\n{table}"]],
        "ops": [[["base", "revenue", "row"], "Revenue check"], *ops],
    }


def r59_rows() -> list[Doc]:
    """R57, R59a, R59b, R59d: the caption line in the unit check, then the retained CP-1."""
    rows = []
    with_unit = ("Line item", "FY2024", "Unit")
    for scale, block, other in ((1, "millions", "thousands"), (1000, "thousands", "millions")):
        under = f"under a {block} block"
        names_other, names_block = f"Amounts in USD {other}.", f"Amounts in USD {block}."
        both = f"Amounts in USD {block}, restated from USD {other}."
        rows += [
            cap_row(
                f"R59: a caption naming {other} over a table naming no unit {under}",
                scale,
                names_other + "\n",
            ),
            cap_row(
                f"R59: a caption naming {block} over a table naming no unit {under}",
                scale,
                names_block + "\n",
            ),
            cap_row(
                f"R59: a caption naming no unit over a table naming no unit {under}",
                scale,
                "Amounts as reported.\n",
            ),
            cap_row(
                f"R59f: a caption naming {block} does not excuse a Unit cell naming {other}: refused",
                scale,
                names_block + "\n",
                with_unit,
                (f"USD {other}",),
            ),
            cap_row(
                f"R59f: a caption naming both units does not excuse a Unit cell naming {other}: refused {under}",
                scale,
                both + "\n",
                with_unit,
                (f"USD {other}",),
            ),
            cap_row(
                f"R59: a caption naming M$ is refused as ambiguous {under}",
                scale,
                "Amounts in M$.\n",
            ),
            cap_row(
                f"R59d known reading: a caption two paragraphs up is not read {under}",
                scale,
                names_other + "\n\nSee the note below.\n",
            ),
            cap_row(
                f"R59: a heading between the paragraph and the table: not read {under}",
                scale,
                names_other + "\n\n#### Detail\n",
            ),
            cap_row(
                f"R59: a caption naming {other} and a Unit cell naming {other}: the Unit cell "
                f"is the issue (capital U sorts before `caption`) {under}",
                scale,
                names_other + "\n",
                with_unit,
                (f"USD {other}",),
            ),
            cap_row(
                f"R59: a caption naming {other} and a `unit` cell naming {other}: the caption "
                f"is the issue (`caption` sorts before `unit`) {under}",
                scale,
                names_other + "\n",
                ("Line item", "FY2024", "unit"),
                (f"USD {other}",),
            ),
            cap_row(
                f"R59: a caption naming {other} and a first header cell naming {other}: the "
                f"caption is the issue (`caption` before `first header cell`) {under}",
                scale,
                names_other + "\n",
                (f"Line item (USD {other})", "FY2024"),
            ),
            cap_row(
                f"R59: a caption naming {other} and a period header naming {other}: the "
                f"caption is the issue (`caption` before `period header`) {under}",
                scale,
                names_other + "\n",
                ("Line item", f"FY2024 USD {other}"),
                ops=([["base", "revenue", "period"], f"FY2024 USD {other}"],),
            ),
            cap_row(
                f"R59: a two-line caption: the issue is the smaller cell, on its second line "
                f"{under}",
                scale,
                f"Restated in USD billions.\n{names_other}\n",
            ),
            cap_row(
                f"R59f: a two-line caption: the second line naming {block} does not excuse the first: refused "
                f"{under}",
                scale,
                f"{names_other}\nStated in USD {block}.\n",
            ),
            cap_row(
                f"R59: a bold caption naming {other} is shown plain {under}",
                scale,
                f"**Amounts in USD {other}**\n",
            ),
        ]
    # The retained public CP-1: `revenue` is a cell of a table with a Unit column and no caption,
    # `ebitda` of a table whose caption alone names US$m, `cash` of a table whose caption names no unit.
    rows += [
        cp1_row(
            "R59: the retained CP-1, all three operands, under a millions block",
            1,
            ["revenue", "ebitda", "cash"],
        ),
        cp1_row(
            "R59: the retained CP-1, a Unit-column operand, under a millions block", 1, ["revenue"]
        ),
        cp1_row(
            "R59: the retained CP-1, a captioned operand, under a millions block", 1, ["ebitda"]
        ),
        cp1_row(
            "R59: the retained CP-1, a Unit-column operand, under a thousands block",
            1000,
            ["revenue"],
        ),
        cp1_row(
            "R59: the retained CP-1, a captioned operand, under a thousands block", 1000, ["ebitda"]
        ),
        cp1_row(
            "R59: the retained CP-1, a captioned table naming no unit, under a thousands block",
            1000,
            ["cash"],
        ),
    ]
    # Adversary F2: the caption's every line is read, not only the first or the last.
    for scale, block, other in ((1, "millions", "thousands"), (1000, "thousands", "millions")):
        rows.append(
            cap_row(
                f"F2: a two-line caption naming {other} on line 1 and nothing on line 2 is refused "
                f"under a {block} block",
                scale,
                f"Amounts in USD {other}.\nSee the table below.\n",
            )
        )
    # Adversary F1 input: free prose naming millions never excuses a header naming thousands.
    rows.append(
        cap_row(
            "R59f: prose naming millions in passing does not excuse a period header naming "
            "thousands (USD 000) under a millions block",
            1,
            "The group added 2 million customers in FY2024.\n",
            ("Line item", "FY2024 (USD 000)"),
            ops=([["base", "revenue", "period"], "FY2024 (USD 000)"],),
        )
    )
    return rows


def render() -> str:
    assert all(units_named(text) == named for text, named in WORDS)
    assert all(names_currency(text, code) is named for text, code, named in CURRENCIES)
    rows = [json.loads(line) for line in ROWS.strip().splitlines()] + r46_rows() + r59_rows()
    for row in json.loads(PR5.render())[
        "rows"
    ]:  # PR 5's rows: the unit and currency steps add nothing
        assert outcome(row) == row["outcome"], row["label"]
    key: Doc = {
        "about": __doc__.split("\n\n")[0],
        "messages": MESSAGES,
        "words": WORDS,
        "currencies": CURRENCIES,
        "rows": [{**row, "outcome": outcome(row)} for row in rows],
    }
    labels = [row["label"] for row in key["rows"]]
    accepted = [row for row in key["rows"] if row["outcome"] is None]
    assert len(labels) == len(set(labels)) == 171 and len(accepted) == 65
    lines = ["{"]
    for name, value in key.items():
        if name == "rows":
            body = ",\n".join("  " + json.dumps(row, ensure_ascii=True) for row in value)
            lines.append(f' "rows": [\n{body}\n ]')
        else:
            lines.append(f' "{name}": {json.dumps(value, ensure_ascii=True)},')
    return "\n".join(lines + ["}"]) + "\n"


if __name__ == "__main__":
    Path(__file__).with_name("pr6a.json").write_text(render(), "utf-8")
