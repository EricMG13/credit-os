"""Answer key for 1B PR 7b (facility detail and its limits), written by the answer-key author.

An oracle in fractions.Fraction and datetime only: not the code under test, never imported by it.
It loads `make_pr7a1.py` (the shared block, edits and unallocated debt) and, through it,
`make_pr3.py` (the facility schedule) by path. Every figure, name and date is invented. A row is
an edit list over the 7a1 block and the expected detail (each facility with its three fiscal years
and the five figures of a year as amount text), the unallocated debt and every limit text in
order. `render()` returns the key's text; run this file to write `pr7b.json` next to it.
"""

import importlib.util
import json
from datetime import date
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("make_pr7a1", HERE / "make_pr7a1.py")
assert SPEC is not None and SPEC.loader is not None
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)
PR3, plain = A.PR3, A.plain

FACILITY_LIMIT = (
    "Cash interest on the stated facilities and scheduled repayment are computed from the "
    "facility terms the forward credit model stated; the analyst's repayment assumption is not "
    "used."
)
BEFORE = (
    "{name} has a stated maturity of {date}, before the forecast; it is assumed refinanced and "
    "no repayment at maturity is modelled."
)
INSIDE = (
    "{name} matures in FY{year} and is assumed refinanced; no repayment at maturity is modelled."
)
MISSING = "Base debt is missing, so debt outside the stated facilities is not known."
POSITIVE = (
    "Debt of {n} is not in a stated facility; it bears interest at the analyst's assumed rate and "
    "is not repaid in this forecast."
)
NEGATIVE = (
    "Stated facility balances exceed base debt by {n}; interest is computed on the stated balances."
)

FIXED, FLOAT = A.FACS
REVOLVER = PR3.fac(
    "Revolver",
    "120.5",
    spread_pct="3.1",
    floor_pct="2",
    reference_rate=["0.01", "0.025", "0.04"],
    amort="50",
)
Edits = list[tuple[str, Any]]


def fac_with(facility: dict[str, Any], **changes: Any) -> dict[str, Any]:
    return facility | changes


def due(*dates: str | None) -> Edits:
    """The two stated facilities, each with the maturity given, in input order."""
    return [("facilities", [fac_with(f, maturity=d) for f, d in zip(A.FACS, dates, strict=True)])]


def years_from(first: int, start: str) -> Edits:
    """Three consecutive fiscal years of twelve months from `start`, a 1 July."""
    return [
        (
            f"years.{i}",
            {
                "year": first + i,
                "start": f"{int(start[:4]) + i}-07-01",
                "end": f"{int(start[:4]) + i + 1}-06-30",
            },
        )
        for i in range(3)
    ]


def detail(block: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for f in block["facilities"]:
        rows = PR3.years(f)
        out.append(
            {
                "name": f["name"],
                "years": [
                    [span["year"], [plain(x) for x in row]]
                    for span, row in zip(block["years"], rows, strict=True)
                ],
            }
        )
    return out


def maturity_limits(block: dict[str, Any]) -> list[str]:
    spans = [
        (date.fromisoformat(s["start"]), date.fromisoformat(s["end"]), s["year"])
        for s in block["years"]
    ]
    out = []
    for f in block["facilities"]:
        if f["maturity"] is None:
            continue
        day = date.fromisoformat(f["maturity"])
        if day < spans[0][0]:
            out.append(BEFORE.format(name=f["name"], date=f["maturity"]))
        elif day <= spans[2][1]:
            year = next(y for start, end, y in spans if start <= day <= end)
            out.append(INSIDE.format(name=f["name"], year=year))
    return out


def unallocated_limit(left: Any) -> list[str]:
    if isinstance(left, A.Gap):
        return [MISSING]
    if left > 0:
        return [POSITIVE.format(n=plain(left))]
    return [NEGATIVE.format(n=plain(-left))] if left < 0 else []


def row(name: str, edits: Edits) -> dict[str, Any]:
    block = A.normal(edits)
    if not block["facilities"]:
        return {"name": name, "edits": edits, "expected": None, "limits": []}
    left = A.unallocated(block)
    limits = [FACILITY_LIMIT, *unallocated_limit(left), *maturity_limits(block)]
    expected = {"facilities": detail(block), "unallocated": A.show(left)}
    return {"name": name, "edits": edits, "expected": expected, "limits": limits}


def rows() -> list[dict[str, Any]]:
    face, lost = A.FACE, A.gone("debt", A.LOST)
    named: list[tuple[str, Edits]] = [
        ("no_facilities", []),
        ("fixed_and_floating", face),
        ("floating_with_floor_and_amortisation", [("facilities", [REVOLVER])]),
        ("input_order", [("facilities", [FLOAT, FIXED, REVOLVER])]),
        ("unallocated_positive_decimal", face + [("facilities.1.balance", "200.5")]),
        ("unallocated_zero_no_limit", face + [("facilities.1.balance", "300")]),
        ("unallocated_negative", face + [("facilities.1.balance", "400.25")]),
        ("unallocated_missing", face + lost),
        ("scale_1000_in_millions", A.thousands(face)),
        ("scale_1000_negative", A.thousands(face + [("facilities.1.balance", "400.25")])),
        ("scale_1000_floating_amortisation", A.thousands([("facilities", [REVOLVER, FIXED])])),
        ("maturity_null", due(None, None)),
        ("maturity_one_day_before_first_year", due("2024-06-30", None)),
        ("maturity_first_day_of_first_year", due("2024-07-01", None)),
        ("maturity_last_day_of_first_year", due("2025-06-30", None)),
        ("maturity_first_day_of_second_year", due("2025-07-01", None)),
        ("maturity_inside_second_year", due("2025-12-15", None)),
        ("maturity_last_day_of_third_year", due("2027-06-30", None)),
        ("maturity_one_day_after_third_year", due("2027-07-01", None)),
        ("maturity_later", due("2029-06-30", None)),
        ("maturity_two_facilities_in_order", due("2026-12-31", "2024-01-31")),
        ("maturity_two_facilities_both_inside", due("2025-09-30", "2024-07-01")),
        (
            "maturity_after_unallocated_negative",
            due("2026-01-31", "2024-01-31") + [("facilities.1.balance", "400.25")],
        ),
        ("maturity_after_unallocated_missing", due("2026-01-31", None) + lost),
        ("maturity_leap_day_before_forecast", due("2024-02-29", None)),
        ("maturity_leap_day_inside_forecast", due("2028-02-29", None) + years_from(2026, "2025")),
        ("maturity_leap_day_after_forecast", due("2028-02-29", None)),
        ("years_shifted_detail", face + years_from(2026, "2025")),
    ]
    return [row(*item) for item in named]


ABOUT = (
    "Step 1B PR 7b answer key, written by the answer-key author. Every figure, name and date is "
    "invented. Computed with fractions.Fraction and datetime by make_pr7b.py (not the code under "
    "test). A row applies its dotted-path `edits` in order to the make_pr7a1.py block (a number "
    "indexes a list). `expected` is null with no facilities, else the facilities in order, each "
    "with [fiscal year, [opening, rate, interest, repaid, closing]] for three years as amount "
    "text, and the unallocated debt (amount text or {missing: ...}); `limits` is every limit text "
    "in order. Implementers do not edit this file."
)


def line(obj: object) -> str:
    return json.dumps(obj, separators=(", ", ": "), ensure_ascii=True)


def render() -> str:
    body = ",\n  ".join(line(r) for r in rows())
    return (
        f'{{\n "about": {line(ABOUT)},\n "facility_limit": {line(FACILITY_LIMIT)},\n'
        f' "reasons": {line(A.REASONS)},\n "rows": [\n  {body}\n ]\n}}\n'
    )


if __name__ == "__main__":
    Path(__file__).with_name("pr7b.json").write_text(render(), "utf-8")
