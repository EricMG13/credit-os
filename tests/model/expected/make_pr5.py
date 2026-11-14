"""Answer key for 1B PR 5 (the foundation's tables, the named cell, the sign rule), by the controller.

Every figure, name and text is invented. A row in ROWS holds inputs only: its label, the
foundation fixture and the text edits that make its handoff, the fixture whose forecast block it
reads (the foundation itself when none is named) and the ops that change that block, as in
`make_pr4b.py`. Everything else is worked here from the edited text, never copied from a row:
the foundation's tables (this script's own reading of headings, fences and table lines: Sources,
every section titled `Forecast inputs` and, when `Bottom line` is the first `###` under Findings,
the reader passages are left out whole, with their subsections), the cells at each named place,
the number each cell reads as (`fractions.Fraction`), the sign rule, and each outcome: accepted
(null), a refusal's kind, subject and message, or the handoff's own error for a repeated passage
heading. `render()` returns the key's text; run this file to write `pr5.json` next to it.
"""

import copy
import json
import re
from fractions import Fraction
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "model"
NAMES = ["foundation.md", "foundation-thousands.md", "foundation-eur.md", "forward-model.md"]
OPERANDS = [
    "revenue",
    "ebitda",
    "interest",
    "taxes",
    "wc",
    "capex",
    "fcf",
    "debt",
    "cash",
    "undrawn",
]
MAGNITUDES = ["interest", "taxes", "capex"]  # wc is the cell reversed; the rest compare signed
PASSAGES = [
    "Bottom line",
    "Key findings",
    "Contrary evidence and what would change the view",
    "Limitations",
]
HEADING = re.compile(r"(#{1,6}) +(.+)")
DIGITS = r"(?P<digits>[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)"
SIGNED = re.compile(r"(?:\+|(?P<minus>[-−]))?" + DIGITS)
BRACKETED = re.compile(r"\(" + DIGITS + r"\)")
NAMED = "base {key} must name the `row` label and either the `period` header or the `column` header it was read from"
MESSAGES = {
    "located": "base {key} states no amount, so it names no row, period or column",
    "named": NAMED,
    "none": "base {key}: no table cell of CP-1 is at {where}",
    "many": "base {key}: {where} is not one number in CP-1 ({count} cells: {shown}{more})",
    "other": "base {key} {amount} is not CP-1's cell at {where} ({cell})",
}
Doc = dict[str, Any]


class Repeated(Exception):
    """The handoff's reader refuses a repeated passage heading; the key records its text."""


def echo(text: str) -> str:
    return text if len(text) <= 80 else text[:80] + "…"


def plain(cell: str) -> str:
    return cell.strip().strip("*_`").strip()


def number(cell: str) -> Fraction | None:
    text = plain(cell)
    if (bracketed := BRACKETED.fullmatch(text)) is not None:
        return -Fraction(bracketed["digits"].replace(",", ""))
    if (signed := SIGNED.fullmatch(text)) is None:
        return None
    value = Fraction(signed["digits"].replace(",", ""))
    return -value if signed["minus"] else value


def shown_lines(text: str) -> list[tuple[int, str, bool]]:
    """(number, line, whether the line is inside a fence or is a fence line)."""
    out, fence = [], ""
    for index, line in enumerate(text.split("\n"), 1):
        marker = line.lstrip(" ")[:3]
        if fence or marker in ("```", "~~~"):
            out.append((index, line, True))
            fence = "" if fence and marker == fence else (fence or marker)
        else:
            out.append((index, line, False))
    return out


def left_out(lines: list[tuple[int, str, bool]]) -> set[int]:
    heads = []
    for index, line, fenced in lines:
        if not fenced and (match := HEADING.fullmatch(line)) is not None:
            heads.append((index, len(match[1]), match[2].strip()))
    last = len(lines) + 1
    findings = next(index for index, level, title in heads if (level, title) == (2, "Findings"))
    stop = next(index for index, level, _ in heads if index > findings and level <= 2)
    threes = [head for head in heads if findings < head[0] < stop and head[1] == 3]
    passages = bool(threes) and threes[0][2] == "Bottom line"
    seen: set[str] = set()
    for index, _, title in threes if passages else []:
        if title in PASSAGES and title in seen:
            raise Repeated(f"line {index}: passage heading `{title}` is repeated")
        seen.add(title)
    out: set[int] = set()
    for index, level, title in heads:
        passage = passages and level == 3 and findings < index < stop and title in PASSAGES
        if (level, title) == (2, "Sources") or title.startswith("Forecast inputs") or passage:
            end = next(
                (other for other, deeper, _ in heads if other > index and deeper <= level), last
            )
            out.update(range(index, end))
    return out


def cells(line: str) -> list[str]:
    return [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", line.strip()[1:-1])]


def tables(text: str) -> list[tuple[int, list[str], list[list[str]]]]:
    """The foundation's tables: header line, header cells, body rows (separator dropped)."""
    lines = shown_lines(text)
    skipped = left_out(lines)
    found: list[tuple[int, list[str], list[list[str]]]] = []
    run: list[tuple[int, str]] = []
    for index, line, fenced in lines + [(len(lines) + 1, "", False)]:
        if not fenced and line.lstrip(" ").startswith("|"):
            run.append((index, line))
            continue
        if run and run[0][0] not in skipped:
            found.append((run[0][0], cells(run[0][1]), [cells(row) for _, row in run[2:]]))
        run = []
    return found


def at(read: list[tuple[int, list[str], list[list[str]]]], row: str, header: str) -> set[str]:
    out: set[str] = set()
    for _, head, body in read:
        for column in (i for i in range(1, len(head)) if plain(head[i]) == plain(header)):
            out.update(line[column] for line in body if plain(line[0]) == plain(row))
    return out


def problem(key: str, operand: Doc, read: list[Any]) -> str | None:
    amount, row, period, column = (operand[name] for name in ("amount", "row", "period", "column"))
    if amount is None:
        located = (row, period, column) != (None, None, None)
        return MESSAGES["located"].format(key=key) if located else None
    header = period if period is not None else column
    if not plain(row) or not plain(header):
        return MESSAGES["named"].format(key=key)
    where = f"row `{echo(row)}`, {'period' if period is not None else 'column'} `{echo(header)}`"
    found = at(read, row, header)
    if not found:
        return MESSAGES["none"].format(key=key, where=where)
    values = {number(cell) for cell in found}
    if len(values) > 1 or None in values:
        shown = sorted(echo(cell) for cell in found)
        more = f" and {len(shown) - 5} more" if len(shown) > 5 else ""
        return MESSAGES["many"].format(
            key=key, where=where, count=len(found), shown=shown[:5], more=more
        )
    (value,) = values
    assert value is not None
    reads = -value if key == "wc" else abs(value) if key in MAGNITUDES else value
    if reads == Fraction(amount):
        return None
    return MESSAGES["other"].format(key=key, amount=amount, where=where, cell=echo(min(found)))


def edited(name: str, edits: list[list[str]]) -> str:
    text = (FIXTURES / name).read_text("utf-8")
    for old, new in edits:
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    return text


def block(name: str, ops: list[Any]) -> Doc:
    text = (FIXTURES / name).read_text("utf-8")
    start = text.index("```json\n") + len("```json\n")
    document: Doc = json.loads(text[start : text.index("\n```", start)])
    for path, *value in copy.deepcopy(ops):
        holder = document
        for step in path[:-1]:
            holder = holder[step]
        if value:
            holder[path[-1]] = value[0]
        else:
            del holder[path[-1]]
    return document


def outcome(row: Doc) -> list[str] | None:
    foundation: str = row.get("foundation", "foundation.md")
    source: str = row.get("source", foundation)
    try:
        read = tables(edited(foundation, row.get("edits", [])))
    except Repeated as error:
        return ["HandoffError", str(error)]
    base = block(source, row.get("ops", []))["base"]
    for key in OPERANDS:
        if (message := problem(key, base[key], read)) is not None:
            return ["cell", f"base {key}", message]
    return None


# Pieces of ROWS, written as JSON string text (`\n` is a newline once the row is read).
T = r"| Line item | FY2024 |\n| --- | --- |\n"
CALC = r"Net debt is Total Debt less Cash & Equivalents.\n"
PASSAGE = r"each tied to the reports read.\n"
SOURCES = r"| Interim report | Nine-month statements. |\n"
FORECAST = r"```\n\n## Calculations"
CONFLICT = T + r"| Revenue | 9,999 |\n"
STATED = '{"amount": null, "reason": "The facility agreement was not read.", "row": null, "period": null, "column": null}'
LONG = "Revenue from the sale of invented industrial goods and of the services that go with them"

ROWS = rf"""
{{"label": "the layer-1 block's ten operands are their FY2024 cells"}}
{{"label": "at scale 1000 each stated thousands text is its thousands cell", "foundation": "foundation-thousands.md"}}
{{"label": "the forward model's block against the foundation", "source": "forward-model.md"}}
{{"label": "the forward model's thousands block against the thousands foundation", "foundation": "foundation-thousands.md", "source": "forward-model-thousands.md"}}
{{"label": "two texts with one value are one number", "edits": [["| Total Debt | 1,250 |  |", "| Total Debt | 1250 |  |"]]}}
{{"label": "a label compares without emphasis", "edits": [["| Revenue | 1,318 |", "| **Revenue** | 1,318 |"]], "ops": [[["base", "revenue", "row"], "_Revenue_"]]}}
{{"label": "a header compares without emphasis", "edits": [["| FY2024 | 9M 2023 |", "| `FY2024` | 9M 2023 |"]]}}
{{"label": "a cell with emphasis reads as its number", "edits": [["| Cash Interest Paid | 40 | 64 |", "| Cash Interest Paid | 40 | **64** |"]]}}
{{"label": "bracketed taxes are a magnitude", "edits": [["| -29 | -37 |", "| -29 | (37) |"]]}}
{{"label": "capex with a U+2212 minus is a magnitude", "edits": [["| Capital expenditure | -65 | -72 |", "| Capital expenditure | -65 | −72 |"]]}}
{{"label": "a leading plus on a signed operand", "edits": [["| 1,318 | 1,456 |", "| 1,318 | +1,456 |"]]}}
{{"label": "interest printed negative is its magnitude", "edits": [["| 40 | 64 |", "| 40 | -64 |"]]}}
{{"label": "a working capital release is the cell reversed", "edits": [["| 6 | -19 |", "| 6 | 19 |"]], "ops": [[["base", "wc", "amount"], "-19"]]}}
{{"label": "a bracketed working capital investment is the cell reversed", "edits": [["| 6 | -19 |", "| 6 | (19) |"]]}}
{{"label": "a table under Calculations is read", "edits": [["{CALC}", "{CALC}\n{T}| Revenue check | 1,456 |\n"]], "ops": [[["base", "revenue", "row"], "Revenue check"]]}}
{{"label": "a balance named by column from a table with one row per period", "ops": [[["base", "cash", "row"], "FY2024"], [["base", "cash", "period"], null], [["base", "cash", "column"], "Cash"]]}}
{{"label": "a reason with no row, period or column names no cell", "ops": [[["base", "undrawn"], {STATED}]]}}
{{"label": "a table in the Bottom line passage is not read", "edits": [["{PASSAGE}", "{PASSAGE}\n{CONFLICT}"]]}}
{{"label": "a table under a heading inside the Bottom line passage is not read", "edits": [["{PASSAGE}", "{PASSAGE}\n#### Passage detail\n\n{CONFLICT}"]]}}
{{"label": "a table under Sources is not read", "edits": [["{SOURCES}", "{SOURCES}\n{CONFLICT}"]]}}
{{"label": "a table under a subsection of Sources is not read", "edits": [["{SOURCES}", "{SOURCES}\n### Notes on sources\n\n{CONFLICT}"]]}}
{{"label": "a table in the forecast section is not read", "edits": [["{FORECAST}", "```\n\n{CONFLICT}\n## Calculations"]]}}
{{"label": "a table under a heading inside the forecast section is not read (legacy read it)", "edits": [["{FORECAST}", "```\n\n#### Forecast notes\n\n{CONFLICT}\n## Calculations"]]}}
{{"label": "a section titled Forecast inputs at any depth is not read (legacy read it)", "edits": [["{CALC}", "{CALC}\n### Forecast inputs, earlier draft\n\n{CONFLICT}"]]}}
{{"label": "a table in a tilde fence is code, not a table", "edits": [["{CALC}", "{CALC}\n~~~\n{CONFLICT}~~~\n"]]}}
{{"label": "an escaped pipe stays in its cell", "edits": [["{CALC}", "{CALC}\n{T}| Revenue \\| total | 1,456 |\n"]], "ops": [[["base", "revenue", "row"], "Revenue | total"]]}}
{{"label": "zeros past 38 digits read exactly", "edits": [["| 1,318 | 1,456 |", "| 1,318 | 1,456.000000000000000000000000000000000000 |"]]}}
{{"label": "leading zeros read as the number", "edits": [["| Capital expenditure | -65 | -72 |", "| Capital expenditure | -65 | -0072 |"]]}}
{{"label": "a magnitude is exact past five digits", "foundation": "foundation-thousands.md", "edits": [["| -29,000 | -37,000 |", "| -29,000 | -37,000.5 |"]], "ops": [[["base", "taxes", "amount"], "37000.5"]]}}
{{"label": "a reversed working capital cell is exact past five digits", "foundation": "foundation-thousands.md", "edits": [["| 6,000 | -19,000 |", "| 6,000 | -19,000.5 |"]], "ops": [[["base", "wc", "amount"], "19000.5"]]}}
{{"label": "an amount that is not its cell", "ops": [[["base", "revenue", "amount"], "1457"]]}}
{{"label": "no table cell at the named period", "ops": [[["base", "revenue", "period"], "FY2025"]]}}
{{"label": "a label in another case names no cell", "ops": [[["base", "revenue", "row"], "revenue"]]}}
{{"label": "the first header cell is not a period", "ops": [[["base", "revenue", "period"], "Line item"]]}}
{{"label": "taxes stated negative are not the magnitude", "ops": [[["base", "taxes", "amount"], "-37"]]}}
{{"label": "a working capital release read as an outflow", "edits": [["| 6 | -19 |", "| 6 | 19 |"]]}}
{{"label": "a signed operand printed negative is not its magnitude", "edits": [["| 122 | 128 |", "| 122 | -128 |"]]}}
{{"label": "a repeated label with another value is not one number", "edits": [["{CALC}", "{CALC}\n{T}| Revenue | 1,465 |\n"]]}}
{{"label": "n.a. is not a number", "edits": [["| 1,318 | 1,456 |", "| 1,318 | n.a. |"]]}}
{{"label": "a unit suffix is not a number", "edits": [["| 1,318 | 1,456 |", "| 1,318 | 1,456m |"]]}}
{{"label": "a percentage is not a number", "edits": [["| 250 | 320 |", "| 250 | 22% |"]]}}
{{"label": "a gap is not a number", "ops": [[["base", "undrawn", "period"], "FY2023"]]}}
{{"label": "more than five cells: the first five sorted and the count", "edits": [["{CALC}", "{CALC}\n{T}| Revenue | 1,405 |\n| Revenue | 1,401 |\n| Revenue | 1,404 |\n| Revenue | 1,402 |\n| Revenue | 1,403 |\n"]]}}
{{"label": "a long row label is cut at 80 characters", "ops": [[["base", "revenue", "row"], "{LONG}"]]}}
{{"label": "a long cell is cut at 80 characters", "edits": [["| 1,318 | 1,456 |", "| 1,318 | 1,457.{"0" * 84} |"]]}}
{{"label": "a cell past 38 digits is read exactly", "edits": [["| 1,318 | 1,456 |", "| 1,318 | 1,456.000000000000000000000000000000000001 |"]]}}
{{"label": "a reason that names a row", "ops": [[["base", "undrawn", "amount"], null], [["base", "undrawn", "reason"], "The facility agreement was not read."]]}}
{{"label": "a row of emphasis only names no label", "ops": [[["base", "revenue", "row"], "**"]]}}
{{"label": "a blank period names no header", "ops": [[["base", "revenue", "period"], "   "]]}}
{{"label": "the first problem in operand order, whatever the block's order", "ops": [[["base", "revenue"]], [["base", "revenue"], {{"amount": "1457", "reason": null, "row": "Revenue", "period": "FY2024", "column": null}}], [["base", "undrawn", "amount"], "176"]]}}
{{"label": "at scale 1000 the message holds the stated thousands text", "foundation": "foundation-thousands.md", "ops": [[["base", "revenue", "amount"], "1457000"]]}}
{{"label": "a thousands block against a millions foundation", "source": "foundation-thousands.md"}}
{{"label": "a balance named by column: the message says column", "ops": [[["base", "cash", "row"], "FY2024"], [["base", "cash", "period"], null], [["base", "cash", "column"], "Cash"], [["base", "cash", "amount"], "284"]]}}
{{"label": "Bottom line not first: its tables are read (legacy did not read them)", "edits": [["## Findings\n\n### Bottom line", "## Findings\n\n### Scope\n\nThe statements cover the whole group.\n\n### Bottom line"], ["{PASSAGE}", "{PASSAGE}\n{CONFLICT}"]]}}
{{"label": "a repeated passage heading is the handoff's own refusal", "edits": [["### Period table", "### Bottom line\n\nA second bottom line.\n\n### Period table"]]}}
"""


def render() -> str:
    rows = [json.loads(line) for line in ROWS.strip().splitlines()]
    key: Doc = {
        "about": __doc__.split("\n\n")[0],
        "messages": MESSAGES,
        "tables": {name: [line for line, _, _ in tables(edited(name, []))] for name in NAMES},
        "rows": [{**row, "outcome": outcome(row)} for row in rows],
    }
    labels = [row["label"] for row in key["rows"]]
    accepted = [row for row in key["rows"] if row["outcome"] is None]
    assert len(labels) == len(set(labels)) == 55 and len(accepted) == 30
    assert key["tables"]["foundation.md"] == [21, 28, 44, 55, 64, 71, 78, 130]
    lines = ["{"]
    for name, value in key.items():
        if name == "rows":
            body = ",\n".join("  " + json.dumps(row, ensure_ascii=True) for row in value)
            lines.append(f' "rows": [\n{body}\n ]')
        else:
            lines.append(f' "{name}": {json.dumps(value, ensure_ascii=True)},')
    return "\n".join(lines + ["}"]) + "\n"


if __name__ == "__main__":
    Path(__file__).with_name("pr5.json").write_text(render(), "utf-8")
