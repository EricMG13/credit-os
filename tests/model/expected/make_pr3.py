"""Answer key for 1B PR 3 (facility terms and the three-year schedule), written by the controller.

An oracle in fractions.Fraction only: not the code under test, never imported by it. Every figure
and name is invented. `render()` returns the key's text; run this file to write `pr3.json` next
to it.
"""

import json
from fractions import Fraction as F
from pathlib import Path
from typing import Any

Facility = dict[str, Any]


def plain(v: F) -> str:
    if v == 0:
        return "0"
    sign, v, places = ("-" if v < 0 else ""), abs(v), 0
    while v.denominator != 1:
        v, places = v * 10, places + 1
        assert places < 60
    d = str(v.numerator)
    if places:
        d = d.rjust(places + 1, "0")
        d = d[:-places] + "." + d[-places:]
    return sign + d


def rate(f: Facility, t: int) -> F:
    if f["fixed_rate_pct"] is not None:
        return F(f["fixed_rate_pct"]) / 100
    ref = F(f["reference_rate"][t])
    if f["floor_pct"] is not None:
        ref = max(ref, F(f["floor_pct"]) / 100)
    return ref + F(f["spread_pct"]) / 100


def years(f: Facility) -> list[list[F]]:
    amort = F(f["annual_amortisation"] or 0)
    opening, out = F(f["balance"]), []
    for t in range(3):
        r = rate(f, t)
        repaid = min(amort, opening)
        out.append([opening, r, opening * r, repaid, opening - repaid])
        opening -= repaid
    return out


def fac(name: str, balance: str, **terms: Any) -> Facility:
    fields = ("fixed_rate_pct", "spread_pct", "floor_pct", "reference_rate")
    tail = {"annual_amortisation": terms.get("amort"), "maturity": terms.get("maturity")}
    return {"name": name, "balance": balance, **{k: terms.get(k) for k in fields}, **tail}


TERM = fac("Term loan A", "400", fixed_rate_pct="6.5", amort="25", maturity="2029-06-30")
FLOAT = fac(
    "Floating notes",
    "150.5",
    spread_pct="2.25",
    floor_pct="2",
    reference_rate=["0.0425", "0.035", "0.01"],
)
SHORT = fac("Bridge", "60", fixed_rate_pct="8", amort="40", maturity="2028-02-29")
NEG = fac(
    "Euro floater", "88.25", spread_pct="1.5", reference_rate=["-0.005", "0", "0.0100"], amort="0"
)
EDGE = fac("x" * 120, "999999.9999", fixed_rate_pct="30", amort="999999.9999")
ZERO = fac("Undrawn line", "0", spread_pct="20", floor_pct="10", reference_rate=["0", "0", "0"])
SCHEDULES = {
    "one_fixed": [TERM],
    "all": [TERM, FLOAT, SHORT, NEG],
    "edges": [EDGE, ZERO],
    "none": [],
}
OK = TERM
PATTERN = "string_pattern_mismatch"
BOTH = "a facility states a fixed rate or a floating one, not both"
NEITHER = "a facility states a fixed rate, or a reference rate with a spread"
SPACE = "facility name must not start or end with whitespace"


def all_in(value: str, year: int) -> str:
    return (
        f"all-in rate {value} in forecast year {year} is outside 0 to 0.30; "
        "reference_rate is a decimal fraction (0.04 is 4%)"
    )


def rule(label: str, base: Facility, text: str, **change: Any) -> list[Any]:
    """A facility the `after` validator refuses with `text`."""
    return [label, {**base, **change}, [], "value_error", text]


def shape(label: str, base: Facility, loc: list[Any], kind: str, **change: Any) -> list[Any]:
    """A facility pydantic refuses at `loc` with error type `kind`."""
    return [label, {**base, **change}, loc, kind, None]


REF = "reference_rate"
REFUSED = [
    rule("fixed and floating", OK, BOTH, spread_pct="2", reference_rate=["0.03", "0.03", "0.03"]),
    rule("fixed with a floor", OK, BOTH, floor_pct="1"),
    rule("no rate", OK, NEITHER, fixed_rate_pct=None),
    rule("reference without spread", FLOAT, NEITHER, spread_pct=None),
    rule("spread without reference", FLOAT, NEITHER, reference_rate=None),
    rule("fixed above 30", OK, "fixed_rate_pct 30.0001 is above 30", fixed_rate_pct="30.0001"),
    rule("spread above 20", FLOAT, "spread_pct 20.01 is above 20", spread_pct="20.01"),
    rule("floor above 10", FLOAT, "floor_pct 10.5 is above 10", floor_pct="10.5"),
    rule(
        "all-in above 0.30", FLOAT, all_in("0.3001", 2), reference_rate=["0.0425", "0.2776", "0.01"]
    ),
    rule("all-in below 0", NEG, all_in("-0.0001", 3), reference_rate=["-0.005", "0", "-0.0151"]),
    rule("name leading space", OK, SPACE, name=" Term loan A"),
    rule("name trailing newline", OK, SPACE, name="Term loan A\n"),
    rule(
        "maturity not a date",
        OK,
        "maturity 2027-02-30 is not a calendar date",
        maturity="2027-02-30",
    ),
    shape("name empty", OK, ["name"], "string_too_short", name=""),
    shape("name 121 characters", OK, ["name"], "string_too_long", name="x" * 121),
    shape("maturity short form", OK, ["maturity"], PATTERN, maturity="2027-2-3"),
    shape("maturity trailing newline", OK, ["maturity"], PATTERN, maturity="2029-06-30\n"),
    shape("maturity non-ASCII digits", OK, ["maturity"], PATTERN, maturity="٢٠٢٩-06-30"),
    shape("balance seven digits", OK, ["balance"], PATTERN, balance="1234567"),
    shape("balance five places", OK, ["balance"], PATTERN, balance="12.34567"),
    shape("balance negative", OK, ["balance"], PATTERN, balance="-5"),
    shape("balance exponent", OK, ["balance"], PATTERN, balance="1e3"),
    shape("balance non-ASCII digit", OK, ["balance"], PATTERN, balance="٣"),
    shape("balance trailing newline", OK, ["balance"], PATTERN, balance="400\n"),
    shape("balance embedded", OK, ["balance"], PATTERN, balance="x400"),
    shape("balance a number", OK, ["balance"], "string_type", balance=400),
    shape("balance null", OK, ["balance"], "string_type", balance=None),
    shape("fixed three digits", OK, ["fixed_rate_pct"], PATTERN, fixed_rate_pct="100"),
    shape("fixed non-ASCII digit", OK, ["fixed_rate_pct"], PATTERN, fixed_rate_pct="６"),
    shape("amortisation negative", OK, ["annual_amortisation"], PATTERN, annual_amortisation="-1"),
    shape(
        "reference above one", FLOAT, [REF, 1], PATTERN, reference_rate=["0.0425", "1.5", "0.01"]
    ),
    shape(
        "reference five places",
        FLOAT,
        [REF, 0],
        PATTERN,
        reference_rate=["0.04255", "0.035", "0.01"],
    ),
    shape(
        "reference non-ASCII digits",
        FLOAT,
        [REF, 2],
        PATTERN,
        reference_rate=["0.0425", "0.035", "0.٠١"],
    ),
    shape("reference two years", FLOAT, [REF, 2], "missing", reference_rate=["0.0425", "0.035"]),
    shape(
        "reference four years",
        FLOAT,
        [REF],
        "too_long",
        reference_rate=["0.0425", "0.035", "0.01", "0.01"],
    ),
    shape("unknown field", OK, ["currency"], "extra_forbidden", currency="USD"),
]
MISSING_FIELD = [
    [f"no {k}", {x: v for x, v in OK.items() if x != k}, [k], "missing", None] for k in OK
]
ABOUT = (
    "Step 1B PR 3 answer key, written by the controller. Every figure and name is invented. "
    "Schedules were computed with fractions.Fraction by the controller's oracle script (not the "
    "code under test). A row is one facility's three years, each [opening, rate, interest, "
    "repaid, closing] as amount text; totals are [interest, repayment] per year. A refused row "
    "is [label, facility, loc, pydantic error type, the ValueError text or null]. Implementers "
    "do not edit this file."
)
TERM_ROWS = [
    ["400", "0.065", "26", "25", "375"],
    ["375", "0.065", "24.375", "25", "350"],
    ["350", "0.065", "22.75", "25", "325"],
]


def line(o: object) -> str:
    return json.dumps(o, separators=(", ", ": "))


def schedule(name: str, facs: list[Facility]) -> str:
    rows = [years(f) for f in facs]
    totals = [[plain(sum((r[t][c] for r in rows), F(0))) for c in (2, 3)] for t in range(3)]
    body = ",\n     ".join(line(f) for f in facs)
    shown = ",\n     ".join(line([[plain(x) for x in y] for y in r]) for r in rows)
    return (
        f'  {line(name)}: {{"facilities": [\n     {body}],\n'
        f'   "rows": [\n     {shown}],\n   "totals": {line(totals)}}}'
    )


def render() -> str:
    parts = ",\n".join(schedule(name, facs) for name, facs in SCHEDULES.items())
    refused = ",\n  ".join(line(r) for r in REFUSED + MISSING_FIELD)
    text = (
        f'{{\n "about": {line(ABOUT)},\n "schedules": {{\n{parts}\n }},\n'
        f' "refused": [\n  {refused}\n ]\n}}\n'
    )
    key = json.loads(text)
    assert key["schedules"]["one_fixed"]["rows"][0] == TERM_ROWS
    assert all(ord(c) < 128 for c in text)
    return text


if __name__ == "__main__":
    Path(__file__).with_name("pr3.json").write_text(render(), "utf-8")
