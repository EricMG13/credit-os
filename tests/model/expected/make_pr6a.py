"""Answer key for 1B PR 6a (units named, the currency named), 6a2 (R46) and 6a3 (R49), by the controller.

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
currency. Run this file to write `pr6a.json` next to it.
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
UNITS = ["billions", "millions", "thousands"]
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
    forms = [
        rf"(?<![A-Za-z])(?:{WORDS_OF[unit]})(?![A-Za-z])",
        rf"{CURRENCY}\s?(?:{MARKS[unit]})(?![A-Za-z])",
        rf"(?<![A-Za-z])(?:{BEFORE[unit]})\s?{SIGN}",
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
    forms = [rf"(?<![A-Za-z])(?i:{prefix})?{currency}(?i:{SUFFIX})?(?![A-Za-z0-9])"]
    forms += [SIGNS[currency]] if currency in SIGNS else []
    return re.search("|".join(forms), text) is not None


def unit_problem(key: str, operand: Doc, read: list[Any], scale: int, currency: str) -> str | None:
    block = "thousands" if scale == 1000 else "millions"
    kind = "period" if operand["period"] is not None else "column"
    header = operand[kind]
    issues: list[tuple[str, str]] = []
    for _, head, body in read:
        for c in (i for i in range(1, len(head)) if PR5.plain(head[i]) == PR5.plain(header)):
            for line in (r for r in body if PR5.plain(r[0]) == PR5.plain(operand["row"])):
                group = [(f"{kind} header", head[c]), ("first header cell", head[0])]
                group += [(PR5.plain(head[i]), cell) for i, cell in enumerate(line) if i != c]
                if not any(block in units_named(cell) for _, cell in group):
                    issues += [(w, cell) for w, cell in group if set(units_named(cell)) - {block}]
    if not issues:
        return None
    what, cell = min(issues)
    unit = f"{currency} millions, scale 1" if scale == 1 else f"{currency} thousands, scale 1000"
    row = PR5.echo(PR5.plain(operand["row"]))
    return MESSAGES["unit"].format(
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
    block = PR5.block(source, row.get("ops", []))
    scale, currency = block["scale"], block["currency"]
    for key in PR5.OPERANDS:
        operand = block["base"][key]
        if (message := PR5.problem(key, operand, read)) is not None:
            return ["cell", f"base {key}", message]
        unit = operand["amount"] and unit_problem(key, operand, read, scale, currency)
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
    return rows


def render() -> str:
    assert all(units_named(text) == named for text, named in WORDS)
    assert all(names_currency(text, code) is named for text, code, named in CURRENCIES)
    rows = [json.loads(line) for line in ROWS.strip().splitlines()] + r46_rows()
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
    assert len(labels) == len(set(labels)) == 112 and len(accepted) == 47
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
