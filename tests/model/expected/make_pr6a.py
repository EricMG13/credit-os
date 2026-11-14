"""Answer key for 1B PR 6a (units named, the currency named), by the controller.

Every figure, name and text is invented. Rows hold inputs only, as in `make_pr5.py`, whose
oracle this script loads for the foundation's tables, the cells, the numbers and the cell check;
an edit with a third element `"all"` replaces every occurrence. Worked here: the unit check
(the cells that may state a named row's unit, the unit words each names, the issue reported),
the foundation's text (this script's own reading: every kept line that is not a heading, a fence
or blank) and whether it names the block's currency, and each outcome. `words` and `currencies`
hold text forms with their expected reading written by hand from the predecessor's cases (text
forms, not figures); `render()` asserts this script's patterns give them. Run this file to write
`pr6a.json` next to it.
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

CURRENCY = r"(?:US\$|USD|EUR|GBP|[$€£])"
THOUSANDS = re.compile(rf"\bthousands?\b|[$'’]000s?\b|{CURRENCY}\s?k\b", re.IGNORECASE)
MILLIONS = re.compile(rf"\b(?:millions?|billions?)\b|{CURRENCY}\s?(?:m|mm|mn|bn)\b", re.IGNORECASE)
SIGNS = {"USD": r"(?i:(?<![A-Za-z])US\$)", "EUR": "€", "GBP": "£"}
MESSAGES = {
    "unit": "base {key}: row `{row}` states its {what} as `{cell}`, not the block's unit ({unit}); "
    "state a reason instead of an amount",
    "currency": "CP-1 nowhere names `{currency}`: state `currency` as the three-letter code of the "
    "currency CP-1 reports its figures in.",
}
Doc = dict[str, Any]


def units_named(text: str) -> list[str]:
    pairs = (("millions", MILLIONS), ("thousands", THOUSANDS))
    return sorted(name for name, pattern in pairs if pattern.search(text))


def names_currency(text: str, currency: str) -> bool:
    forms = [rf"(?<![A-Za-z]){currency}(?i:mm|mn|bn|m|k|000s?)?(?![A-Za-z0-9])"]
    forms += [SIGNS[currency]] if currency in SIGNS else []
    return re.search("|".join(forms), text) is not None


def unit_problem(key: str, operand: Doc, read: list[Any], scale: int, currency: str) -> str | None:
    block, other = ("thousands", "millions") if scale == 1000 else ("millions", "thousands")
    kind = "period" if operand["period"] is not None else "column"
    header = operand[kind]
    issues: list[tuple[str, str]] = []
    for _, head, body in read:
        for c in (i for i in range(1, len(head)) if PR5.plain(head[i]) == PR5.plain(header)):
            for line in (r for r in body if PR5.plain(r[0]) == PR5.plain(operand["row"])):
                group = [(f"{kind} header", head[c]), ("first header cell", head[0])]
                group += [(PR5.plain(head[i]), cell) for i, cell in enumerate(line) if i != c]
                if not any(block in units_named(cell) for _, cell in group):
                    issues += [(what, cell) for what, cell in group if other in units_named(cell)]
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
    ["GBP bn", ["millions"]],
    ["stated in millions", ["millions"]],
    ["USD million/billion", ["millions"]],
    ["US$ thousands; USD 37.6 million", ["millions", "thousands"]],
    ["", []],
    ["p.4", []],
    ["9M 2025", []],
    ["1,000", []],
    ["US$ and a mid-year note", []],
    ["Mmm", []],
    ["m", []],
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
]


def render() -> str:
    assert all(units_named(text) == named for text, named in WORDS)
    assert all(names_currency(text, code) is named for text, code, named in CURRENCIES)
    rows = [json.loads(line) for line in ROWS.strip().splitlines()]
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
    assert len(labels) == len(set(labels)) == 34 and len(accepted) == 12
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
