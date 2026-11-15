"""Answer key for 1B PR 6b (facility terms printed, facility totals against base debt), by the controller.

Every figure, name and text is invented. Rows hold inputs only, as in `make_pr5.py`; this script
loads `make_pr6a.py` (and through it `make_pr5.py`) for the cell, unit and currency steps and the
foundation's text. Worked here, in `fractions.Fraction`: whether each stated balance and rate
term is printed in that text, the balances against 1.25 times base debt, the running totals of
the three-year schedule (each year repays a facility's amortisation, at most what is left), a
case `debt_repayment` beside facilities, and each outcome in the order base, facilities,
currency. 1B-M1 (the whole-branch review's fix): a balance counts as printed only in a piece that
names no unit other than the block's, and in a table cell only when the cell, its column header,
the first header cell and the rest of its row name none either. Run this file to write
`pr6b.json` next to it.
"""

import importlib.util
import json
import re
from fractions import Fraction
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("make_pr6a", HERE / "make_pr6a.py")
assert SPEC is not None and SPEC.loader is not None
PR6A: Any = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PR6A)
PR5: Any = PR6A.PR5

MESSAGES = {
    "balance": "facility {name} balance {balance} is not printed in CP-1",
    "rate": "facility {name} {field} {value}% is not printed in CP-1",
    "balances": "facility balances total {total}, more than 1.25 times base debt {debt}{divided}; "
    "check the unit",
    "schedule": "scheduled repayments through forecast year {year} total {total}, more than base "
    "debt {debt}{divided}",
    "case": "{name} states debt_repayment, which is not used when facilities are stated",
}
RATES = ["fixed_rate_pct", "spread_pct", "floor_pct"]
Doc = dict[str, Any]


def text(value: Fraction) -> str:
    """A terminating fraction as plain decimal text, no trailing zeros, zero as 0."""
    places = 0
    while (value * 10**places).denominator != 1:
        places += 1
    digits = str(abs(value.numerator * 10**places // value.denominator)).rjust(places + 1, "0")
    whole, tail = digits[: len(digits) - places], digits[len(digits) - places :].rstrip("0")
    return ("-" if value < 0 else "") + whole + (f".{tail}" if tail else "")


# R47: a balance counts only where it stands as a number of its own: not inside a longer number,
# not glued to a letter (`FY2024`, `9M`), not part of a date (`2022-07-01`, `19/11/2031`) and not a
# percentage (`7.125%`). A number standing alone in words (`Senior notes 2029`) still counts.
ALONE_BEFORE = r"(?<![0-9.,A-Za-z])(?<![0-9][-/])"
ALONE_AFTER = r"(?![0-9]|[.,][0-9]|[A-Za-z]|[-/][0-9]| ?%)"


def printed(lines: list[str], amount: str) -> bool:
    whole, dot, fraction = amount.lstrip("-").partition(".")
    forms = {f"{whole}{dot}{fraction}", f"{int(whole):,}{dot}{fraction}"}
    pattern = "|".join(rf"{ALONE_BEFORE}{re.escape(form)}{ALONE_AFTER}" for form in forms)
    return any(re.search(pattern, line) for line in lines)


# 1B-M1 (coordinator, 2026-11-15, under the plan's Scale rule: "an amount printed in the other unit
# is refused, never converted"): a balance counts only in a piece that names no unit other than
# the block's. Prose lines and table labels are pieces of their own. A table cell counts only when
# it, its column header, the first header cell and every other cell of its row (6a's group, with
# the cell itself) name no unit other than the block's. A piece or group naming both units does
# not count. Prose naming no unit still counts (known reading until R57's caption line). Rates are
# read from every line, as before. R59c (coordinator, 2026-11-15): a table whose caption (the lines
# of the paragraph directly before it, `PR6A.captions`) names any unit other than the block's
# contributes no piece at all, in its label, headers or body cells; a caption naming only the
# block's unit, or none, changes nothing.
def balance_pieces(text: str, unit: str) -> list[str]:
    def only(*pieces: str) -> bool:
        return all(set(PR6A.units_named(piece)) <= {unit} for piece in pieces)

    lines = PR6A.text_lines(text)
    pieces = [line for line in lines if not line.lstrip(" ").startswith("|") and only(line)]
    above = PR6A.captions(text)
    for first, head, body in PR5.tables(text):
        if not only(*above.get(first, [])):  # R59c: a caption naming another unit voids the table
            continue
        pieces += [cell for cell in head if only(cell)]
        for cells in body:
            pieces += [cell for c, cell in enumerate(cells) if only(*cells, head[c], head[0])]
    return pieces


def printed_percent(lines: list[str], value: str) -> bool:
    return any(re.search(rf"(?<![0-9.,]){re.escape(value)} ?%", line) for line in lines)


def millions(amount: str, scale: int) -> Fraction:
    return Fraction(amount) / scale


def facility_problem(block: Doc, lines: list[str], pieces: list[str]) -> list[str] | None:
    facilities, scale = block["facilities"], block["scale"]
    for number, facility in enumerate(facilities, 1):
        name, subject = PR5.echo(facility["name"]), f"facility {number}"
        if not printed(pieces, facility["balance"]):
            message = MESSAGES["balance"].format(name=name, balance=facility["balance"])
            return ["facility", subject, message]
        for field in (field for field in RATES if facility[field] is not None):
            if not printed_percent(lines, facility[field]):
                message = MESSAGES["rate"].format(name=name, field=field, value=facility[field])
                return ["facility", subject, message]
    debt_text = block["base"]["debt"]["amount"]
    if debt_text is not None:
        debt = millions(debt_text, scale)
        divided = (
            f", in {block['currency']} millions after dividing by scale 1000"
            if scale == 1000
            else ""
        )
        balances = sum((millions(f["balance"], scale) for f in facilities), Fraction(0))
        if balances > Fraction(5, 4) * debt:
            message = MESSAGES["balances"].format(
                total=text(balances), debt=text(debt), divided=divided
            )
            return ["facility", "facilities", message]
        left = [millions(f["balance"], scale) for f in facilities]
        cut = [
            Fraction(0)
            if f["annual_amortisation"] is None
            else millions(f["annual_amortisation"], scale)
            for f in facilities
        ]
        running = Fraction(0)
        for year in (1, 2, 3):
            for index, amortisation in enumerate(cut):
                repaid = min(amortisation, left[index])
                left[index] -= repaid
                running += repaid
            if running > debt:
                message = MESSAGES["schedule"].format(
                    year=year, total=text(running), debt=text(debt), divided=divided
                )
                return ["repayment", "facilities", message]
    for name in ("upside_drivers", "downside_drivers"):
        case = block[name]
        if case is not None and case.get("debt_repayment") is not None:
            return ["facility", name, MESSAGES["case"].format(name=name)]
    return None


def outcome(row: Doc) -> list[str] | None:
    """The 6a outcome with the facility step between the base step and the currency step."""
    foundation: str = row.get("foundation", "foundation.md")
    source: str = row.get("source", "forward-model.md")
    row = {**row, "source": source}
    first: list[str] | None = PR6A.outcome(row)
    if first is not None and first[0] in ("cell", "unit", "HandoffError"):
        return first
    block = PR5.block(source, row.get("ops", []))
    text = PR6A.edited(foundation, row.get("edits", []))
    lines = PR6A.text_lines(text)
    pieces = balance_pieces(text, "thousands" if block["scale"] == 1000 else "millions")
    if block["facilities"] is not None and (problem := facility_problem(block, lines, pieces)):
        return problem
    return first


CALC = "Net debt is Total Debt less Cash & Equivalents.\n"
TABLE = "| Line item | FY2024 |\n| --- | --- |\n"
PASSAGE = "each tied to the reports read.\n"
SOURCES = "| Interim report | Nine-month statements. |\n"
NO_FLOOR = ["Reference rate + 3.25%, floor 0.75%;", "Reference rate + 3.25%;"]
LONG = "Term loan B of the invented group, drawn in two tranches and repaid in equal instalments"
DRIVER = {
    "values": ["10", "10", "10"],
    "category": "Analyst Interpretation",
    "rationale": "Invented.",
    "limitation": None,
}


def debt(cell: str, amount: str) -> Doc:
    """Base debt named at a Calculations row printing `cell`."""
    edit = [CALC, f"{CALC}\n{TABLE}| Debt check | {cell} |\n"]
    ops = [[["base", "debt", "row"], "Debt check"], [["base", "debt", "amount"], amount]]
    return {"edits": [edit], "ops": ops}


def amortising(tlb: str, notes: str, cell: str, amount: str) -> Doc:
    row = debt(cell, amount)
    row["ops"] += [
        [["facilities", 0, "annual_amortisation"], tlb],
        [["facilities", 1, "annual_amortisation"], notes],
    ]
    return row


def with_ops(row: Doc, *ops: list[Any]) -> Doc:
    return {**row, "ops": row["ops"] + list(ops)}


def prose(line: str) -> Doc:
    """One prose line added under Calculations."""
    return {"edits": [[CALC, f"{CALC}\n{line}\n"]]}


def floor_in(old: str, new: str) -> Doc:
    return {"edits": [NO_FLOOR, [old, new]]}


ROWS: list[Doc] = [
    {"label": "the forward model's facilities are printed and within base debt"},
    {
        "label": "at scale 1000 the stated thousands balances are printed with commas",
        "foundation": "foundation-thousands.md",
        "source": "forward-model-thousands.md",
    },
    {
        "label": "a rate printed with a space before the percent sign",
        "edits": [["Fixed 7.125%", "Fixed 7.125 %"]],
    },
    {
        "label": "base debt missing: neither bound is tested",
        "ops": [
            [
                ["base", "debt"],
                {
                    "amount": None,
                    "reason": "Not read.",
                    "row": None,
                    "period": None,
                    "column": None,
                },
            ],
            [["facilities", 0, "annual_amortisation"], "640"],
            [["facilities", 1, "annual_amortisation"], "450"],
        ],
    },
    {
        "label": "scheduled repayments equal to base debt by year 3",
        **amortising("214", "150", "1,090", "1090"),
    },
    {"label": "balances exactly 1.25 times base debt", **debt("872", "872")},
    {
        "label": "a floor printed in Calculations prose",
        **floor_in(CALC, f"{CALC}\nThe floor is 0.75%.\n"),
    },
    {"label": "a balance that is not printed", "ops": [[["facilities", 1, "balance"], "451"]]},
    {
        "label": "a balance printed only inside longer numbers",
        "ops": [[["facilities", 1, "balance"], "45"]],
    },
    {
        "label": "at scale 1000 a balance not printed is named as stated",
        "foundation": "foundation-thousands.md",
        "source": "forward-model-thousands.md",
        "ops": [[["facilities", 0, "balance"], "640001"]],
    },
    {
        "label": "a fixed rate printed only as the start of a longer one",
        "ops": [[["facilities", 1, "fixed_rate_pct"], "7.12"]],
    },
    {
        "label": "a spread stated with a trailing zero the foundation does not print",
        "ops": [[["facilities", 0, "spread_pct"], "3.250"]],
    },
    {
        "label": "a floor printed only in a reader passage",
        **floor_in(PASSAGE, f"{PASSAGE}The floor is 0.75%.\n"),
    },
    {
        "label": "a floor printed only under Sources",
        **floor_in(SOURCES, f"{SOURCES}\nThe floor is 0.75%.\n"),
    },
    {
        "label": "a floor printed only in a heading",
        **floor_in("### Debt facilities", "### Debt facilities (floor 0.75%)"),
    },
    {"label": "a floor printed only in code", **floor_in(CALC, f"{CALC}\n```\nfloor 0.75%\n```\n")},
    {
        "label": "facility 1 is checked whole before facility 2",
        "ops": [[["facilities", 0, "spread_pct"], "3.3"], [["facilities", 1, "balance"], "451"]],
    },
    {
        "label": "a long facility name is cut at 80 characters",
        "ops": [[["facilities", 0, "name"], LONG], [["facilities", 0, "balance"], "641"]],
    },
    {"label": "balances over 1.25 times base debt", **debt("871.9999", "871.9999")},
    {
        "label": "at scale 1000 the balances bound is worded in millions",
        "foundation": "foundation-thousands.md",
        "source": "forward-model-thousands.md",
        **debt("871,999.9", "871999.9"),
    },
    {
        "label": "base debt 0 with facilities: the balances bound refuses",
        **with_ops(debt("0", "0"), [["base_drivers", "debt_repayment", "values"], ["0", "0", "0"]]),
    },
    {
        "label": "scheduled repayments over base debt in year 1",
        **amortising("640", "450", "1,000", "1000"),
    },
    {
        "label": "scheduled repayments one unit of the last place over",
        **amortising("214", "150", "1,089.9999", "1089.9999"),
    },
    {
        "label": "scheduled repayments over only in year 3, equal in year 2",
        **amortising("300", "150", "900", "900"),
    },
    {
        "label": "at scale 1000 the schedule bound is worded in millions",
        "foundation": "foundation-thousands.md",
        "source": "forward-model-thousands.md",
        **amortising("300000", "150000", "900,000", "900000"),
    },
    {
        "label": "an upside debt_repayment beside facilities",
        "ops": [[["upside_drivers", "debt_repayment"], DRIVER]],
    },
    {
        "label": "both cases: the upside case is named",
        "ops": [
            [["upside_drivers", "debt_repayment"], DRIVER],
            [["downside_drivers", "debt_repayment"], DRIVER],
        ],
    },
    {
        "label": "the printed terms before the bounds",
        **with_ops(
            amortising("640", "450", "1,000", "1000"), [["facilities", 1, "balance"], "451"]
        ),
    },
    {
        "label": "the base cell before the facilities",
        "ops": [[["base", "revenue", "amount"], "1457"], [["facilities", 1, "balance"], "451"]],
    },
    {
        "label": "the facilities before the currency",
        "ops": [[["currency"], "GBP"], [["facilities", 1, "balance"], "451"]],
    },
    {"label": "the layer-1 block states no facilities to check", "source": "foundation.md"},
    {
        "label": "the spread is checked before the floor",
        "ops": [[["facilities", 0, "spread_pct"], "3.3"], [["facilities", 0, "floor_pct"], "0.8"]],
    },
    {
        "label": "the balance is checked before the rates",
        "ops": [[["facilities", 0, "balance"], "641"], [["facilities", 0, "spread_pct"], "3.3"]],
    },
    {
        "label": "the balances bound before a case debt_repayment",
        **with_ops(debt("871.9999", "871.9999"), [["upside_drivers", "debt_repayment"], DRIVER]),
    },
    {
        "label": "the schedule bound before a case debt_repayment",
        **with_ops(
            amortising("640", "450", "1,000", "1000"),
            [["upside_drivers", "debt_repayment"], DRIVER],
        ),
    },
    {
        "label": "a case debt_repayment with base debt missing",
        "ops": [
            [
                ["base", "debt"],
                {
                    "amount": None,
                    "reason": "Not read.",
                    "row": None,
                    "period": None,
                    "column": None,
                },
            ],
            [["upside_drivers", "debt_repayment"], DRIVER],
        ],
    },
    {
        "label": "a balance printed only after a comma",
        "ops": [[["facilities", 1, "balance"], "456"]],
    },
    {
        "label": "a balance printed only after a point",
        "ops": [[["facilities", 1, "balance"], "125"]],
    },
    {
        "label": "a balance printed only after a digit",
        "ops": [[["facilities", 1, "balance"], "56"]],
    },
    {
        "label": "a balance printed only before a point and a digit",
        "ops": [[["facilities", 1, "balance"], "7"]],
    },
    {
        "label": "a fixed rate printed only after a point",
        "ops": [[["facilities", 1, "fixed_rate_pct"], "25"]],
    },
    {
        "label": "a fixed rate printed only after a digit",
        "ops": [[["facilities", 1, "fixed_rate_pct"], "5"]],
    },
    # 6b fix round 1: the adversary's Medium 1 to 3 and Low 1 to 3.
    {
        "label": "a balance printed only before a comma and a digit",
        **prose("Shares issued: 457,000."),
        "ops": [[["facilities", 1, "balance"], "457"]],
    },
    {
        "label": "a balance printed at the end of a sentence",
        **prose("The drawn amount was 458."),
        "ops": [[["facilities", 1, "balance"], "458"]],
    },
    {
        "label": "a fractional balance printed with a point",
        **prose("The notes stand at 459.5."),
        "ops": [[["facilities", 1, "balance"], "459.5"]],
    },
    {
        "label": "a fractional balance printed only with a letter for the point",
        **prose("Reference 459x5."),
        "ops": [[["facilities", 1, "balance"], "459.5"]],
    },
    {
        "label": "a balance over 999 printed without commas",
        **with_ops(
            {
                "edits": [
                    *debt("2,000", "2000")["edits"],
                    [CALC, f"{CALC}\nNotes of 1450 outstanding.\n"],
                ],
                "ops": debt("2,000", "2000")["ops"],
            },
            [["facilities", 1, "balance"], "1450"],
        ),
    },
    {
        "label": "a balance printed in a cell beside other words",
        "edits": [["| Senior notes 2029 | 450 |", "| Senior notes 2029 | 450 outstanding |"]],
    },
    {
        "label": "a fixed rate printed only inside a longer number",
        "edits": [["Fixed 7.125%", "Fixed 17.125%"]],
    },
    {
        "label": "a fixed rate printed only after a comma",
        **prose("A rate of 2,5% applies elsewhere."),
        "ops": [[["facilities", 1, "fixed_rate_pct"], "5"]],
    },
    {
        "label": "a rate printed with a no-break space before the percent sign",
        "edits": [["Fixed 7.125%", "Fixed 7.125\u00a0%"]],
    },
    {
        "label": "a rate printed with two spaces before the percent sign",
        "edits": [["Fixed 7.125%", "Fixed 7.125  %"]],
    },
    {
        "label": "a rate printed only with a letter for the point",
        "edits": [["Fixed 7.125%", "Fixed 7x125%"]],
    },
    {
        "label": "a downside debt_repayment beside facilities",
        "ops": [[["downside_drivers", "debt_repayment"], DRIVER]],
    },
    {
        "label": "the printed terms before a case debt_repayment",
        "ops": [
            [["facilities", 1, "balance"], "451"],
            [["upside_drivers", "debt_repayment"], DRIVER],
        ],
    },
    {
        "label": "a long facility name is cut at 80 characters in the rate message",
        "ops": [[["facilities", 0, "name"], LONG], [["facilities", 0, "spread_pct"], "3.3"]],
    },
    {
        "label": "the running total is exact: equal to base debt by year 3 at ten-thousandths",
        **amortising("200.0001", "90.6666", "872.0001", "872.0001"),
    },
]


# R47: (where the balance is printed, the balance, the foundation text that prints it only that
# way, or None where the fixture already does, and the same number printed on its own).
# The period-label row uses FY2031, not FY2024: the fixture also prints 2024 standing alone in
# `9M 2024` and `Q3 2024`, which counts by the known reading, so 2024 is printed either way.
R47 = [
    ("glued after a period label", "2031", "Guidance for FY2031 is withdrawn.", "Guidance: 2031."),
    ("as the year of an ISO date", "2022", None, "Opened in 2022."),
    ("as the day of an ISO date", "17", "Repaid on 2031-11-17.", "Repaid: 17."),
    ("before the slash of a date", "21", "Repaid on 21/11/2031.", "Repaid: 21."),
    ("after the slash of a date", "23", "Repaid on 2031/11/23.", "Repaid: 23."),
    ("glued before a letter", "9", None, "Nine is 9."),
    ("as a percentage", "7.125", None, "The notes stand at 7.125."),
    ("glued into a facility name", "2027", "TLB2027 was repaid.", "2027 was repaid."),
]
# The 6b2 adversary review: M1 pins the letter pieces for small letters too; M2 pins the point
# before a balance, which R47's `%` piece hid in 6b's "after a point" row (`Fixed 7.125%`). These
# rows come after the controls, so the earlier rows stay as they were.
R47_REVIEW: list[tuple[str, str, str | None, str]] = [
    ("glued before a small letter", "380", "Drawn 380m.", "Drawn: 380."),
    ("glued after a small letter", "2027", "tlb2027 was repaid.", "2027 was repaid."),
    ("after a point in a longer number", "380", "Drawn 1.380.", "Drawn: 380."),
]


def r47_rows() -> list[Doc]:
    """Each R47 form refused, beside the same balance printed on its own and accepted; base debt
    3,000 keeps both bounds out of the way."""
    base = debt("3,000", "3000")
    rows = []

    def row(label: str, balance: str, *lines: str) -> Doc:
        edits = [*base["edits"], *([CALC, f"{CALC}\n{line}\n"] for line in lines)]
        ops = [*base["ops"], [["facilities", 1, "balance"], balance]]
        return {"label": f"R47: {label}", "edits": edits, "ops": ops}

    def pairs(table: list[tuple[str, str, str | None, str]]) -> None:
        for where, balance, only, alone in table:
            glued = [only] if only else []
            rows.append(row(f"a balance printed only {where} is not printed", balance, *glued))
            rows.append(
                row(
                    f"the same balance on its own beside it is printed ({where})",
                    balance,
                    *glued,
                    alone,
                )
            )

    pairs(R47)
    rows.append(
        row("known reading: a number standing alone in a name counts (Senior notes 2029)", "2029")
    )
    rows.append(
        row("a bracketed balance with a trailing zero counts", "1250.0", "Drawn (1,250.0).")
    )
    rows.append(
        row(
            "a balance printed only as a percentage with a trailing zero does not count",
            "1250.0",
            "Drawn 1,250.0%.",
        )
    )
    rows.append(
        row(
            "a balance printed only as a percentage after a space does not count",
            "1250.0",
            "Drawn 1,250.0 %.",
        )
    )
    pairs(R47_REVIEW)
    return rows


# 1B-M1 pairs, scale 1 (the block's unit is millions): the balance printed only where the named
# part of the rule names another unit, beside the same text naming millions. Base debt 3,000.
SENIOR = "| Senior notes 2029 |"
M1 = [
    ("in prose naming thousands", "Senior notes 2029: 380, in thousands.", "thousands"),
    ("in prose naming billions", "Senior notes 2029: 380, in billions.", "billions"),
    (
        "in prose naming both units",
        "Senior notes 2029: 380, in millions and thousands.",
        "and thousands",
    ),
    (
        "in a table whose Unit cell names thousands",
        f"| Facility | FY2024 | Unit |\n| --- | --- | --- |\n{SENIOR} 380 | USD thousands |",
        "USD thousands",
    ),
    (
        "in a table whose column header names thousands",
        f"| Facility | FY2024 USD thousands |\n| --- | --- |\n{SENIOR} 380 |",
        "USD thousands",
    ),
    (
        "in a table whose first header cell names thousands",
        f"| USD thousands | FY2024 |\n| --- | --- |\n{SENIOR} 380 |",
        "USD thousands",
    ),
    (
        "in a table cell that itself names thousands",
        f"| Facility | FY2024 |\n| --- | --- |\n{SENIOR} 380 thousand |",
        "thousand",
    ),
    (
        "in a table row naming both units",
        (
            f"| Facility | FY2024 | Unit | Note |\n| --- | --- | --- | --- |\n"
            f"{SENIOR} 380 | USD millions | restated from thousands |"
        ),
        " from thousands",
    ),
    (
        "in a table label naming thousands",
        f"**Senior notes 2029: USD 380 thousand**\n| Facility | Note |\n| --- | --- |\n{SENIOR} Drawn |",
        "thousand",
    ),
]
SAME = {"thousands": "millions", "billions": "millions", "and thousands": "", " from thousands": ""}
TLB = "| Term loan B | 640,000 | Reference rate + 3.25%, floor 0.75%; amortises 32,000 a year | 2026-09-30 | USD thousands |"
NOTES = "| Senior notes 2029 | 450,000 | Fixed 7.125% | 2029-03-15 | USD thousands |"
TLB_M = (
    TLB.replace("640,000", "640").replace("32,000", "32").replace("USD thousands", "USD millions")
)
NOTES_M = NOTES.replace("450,000", "450").replace("USD thousands", "USD millions")
SCALE_1000 = {"foundation": "foundation-thousands.md", "source": "forward-model-thousands.md"}
SMALL = [
    [["facilities", 0, "balance"], "640"],
    [["facilities", 1, "balance"], "450"],
    [["facilities", 0, "annual_amortisation"], "32"],
]
UNCELLED = [
    [TLB, TLB.replace("640,000", "See the note")],
    [NOTES, NOTES.replace("450,000", "See the note")],
]


MISSING = next(row for row in ROWS if row["label"].startswith("base debt missing"))["ops"][0]


def m1_rows() -> list[Doc]:
    """1B-M1: the nine scale-1 pairs, then the cases the whole-branch review reproduced."""
    base = debt("3,000", "3000")
    rows = []

    def row(label: str, line: str) -> Doc:
        edits = [*base["edits"], [CALC, f"{CALC}\n{line}\n"]]
        ops = [*base["ops"], [["facilities", 1, "balance"], "380"]]
        return {"label": f"1B-M1: {label}", "edits": edits, "ops": ops}

    for where, other, word in M1:
        same = other.replace(word, SAME.get(word, word.replace("thousand", "million")))
        rows.append(row(f"a balance printed only {where} is not printed", other))
        rows.append(row(f"the same text naming millions prints it ({where})", same))
    rows.append(
        {
            "label": "1B-M1: scale 1000, the facility table only in USD millions, is not printed",
            **SCALE_1000,
            "edits": [[TLB, TLB_M], [NOTES, NOTES_M]],
            "ops": SMALL,
        }
    )
    prose = "Term loan B of USD 640 million and Senior notes 2029 of USD 450 million were drawn."
    rows.append(
        {
            "label": "1B-M1: scale 1000, the balances only in prose naming USD millions, is not printed",
            **SCALE_1000,
            "edits": [*UNCELLED, [CALC, f"{CALC}\n{prose}\n"]],
            "ops": SMALL,
        }
    )
    neutral = "Term loan B 640 and Senior notes 2029 450 were drawn."
    rows.append(
        {
            "label": "1B-M1 known reading: scale 1000, prose naming no unit counts (640 for 640,000)",
            **SCALE_1000,
            "edits": [*UNCELLED, [CALC, f"{CALC}\n{neutral}\n"]],
            "ops": SMALL,
        }
    )
    rows.append(
        {
            "label": "1B-M1: scale 1, balances 1,000 times too large with base debt missing, is not printed",
            "edits": [[TLB_M, TLB], [NOTES_M, NOTES]],
            "ops": [
                MISSING,
                [["facilities", 0, "balance"], "640000"],
                [["facilities", 1, "balance"], "450000"],
                [["facilities", 0, "annual_amortisation"], "32000"],
            ],
        }
    )
    return rows


# R59c (coordinator ruling: the caption in the balance filter)
def r59c_rows() -> list[Doc]:
    """The facility table's caption: a unit other than the block's voids its balances, the block's
    unit or none leaves them. Base debt is missing, so the facility table's own `Total Debt` row
    is not an operand of the unit check and only the balance filter is under test. Then the M1
    prose rows again with a neutral paragraph between the prose and the debt table, since under
    R59b the prose line directly above that table is its caption (the two M1 prose rows now end
    in the unit check; see their entries)."""
    heading = "### Debt facilities\n\n"
    rows: list[Doc] = []

    def caption(label: str, text: str, scale: int) -> Doc:
        base: Doc = SCALE_1000 if scale == 1000 else {}
        return {
            "label": f"R59c: {label}",
            **base,
            "edits": [[heading, f"{heading}{text}\n\n"]],
            "ops": [MISSING],
        }

    rows.append(
        caption(
            "scale 1, the facility table's caption names thousands: not printed",
            "Amounts in USD thousands.",
            1,
        )
    )
    rows.append(
        caption(
            "scale 1, the facility table's caption names millions: printed",
            "Amounts in USD millions.",
            1,
        )
    )
    rows.append(
        caption(
            "scale 1, the facility table's caption names no unit: printed",
            "Amounts as reported.",
            1,
        )
    )
    rows.append(
        caption(
            "scale 1000, the facility table's caption names USD millions: not printed",
            "Amounts in USD millions.",
            1000,
        )
    )
    rows.append(
        caption(
            "scale 1000, the facility table's caption names USD thousands: printed",
            "Amounts in USD thousands.",
            1000,
        )
    )
    rows.append(
        caption(
            "scale 1, a caption naming both units: not printed (as a row naming both)",
            "Amounts in USD millions, restated from USD thousands.",
            1,
        )
    )
    rows.append(caption("scale 1, a caption naming M$: not printed", "Amounts in M$.", 1))
    rows.append(
        caption(
            "scale 1, a caption two paragraphs up is not read (R59d): printed",
            "Amounts in USD thousands.\n\nSee the table below.",
            1,
        )
    )
    base = debt("3,000", "3000")
    for where, other, word in M1[:2]:
        line = f"{other}\n\nSee the debt table below."
        edits = [*base["edits"], [CALC, f"{CALC}\n{line}\n"]]
        ops = [*base["ops"], [["facilities", 1, "balance"], "380"]]
        label = f"R59c: a balance printed only {where}, a neutral paragraph before the table"
        rows.append({"label": label, "edits": edits, "ops": ops})
    return rows


def render() -> str:
    rows = [
        {**row, "source": row.get("source", "forward-model.md")}
        for row in [*ROWS, *r47_rows(), *m1_rows(), *r59c_rows()]
    ]
    rows = [{**row, "outcome": outcome(row)} for row in rows]
    key: Doc = {"about": __doc__.split("\n\n")[0], "messages": MESSAGES, "rows": rows}
    labels = [row["label"] for row in rows]
    accepted = [row for row in rows if row["outcome"] is None]
    assert len(labels) == len(set(labels)) == 115 and len(accepted) == 40
    lines = ["{"]
    for name, value in key.items():
        if name == "rows":
            body = ",\n".join("  " + json.dumps(row, ensure_ascii=True) for row in value)
            lines.append(f' "rows": [\n{body}\n ]')
        else:
            lines.append(f' "{name}": {json.dumps(value, ensure_ascii=True)},')
    return "\n".join(lines + ["}"]) + "\n"


if __name__ == "__main__":
    Path(__file__).with_name("pr6b.json").write_text(render(), "utf-8")
