"""Answer key for 1B PR 2 (the forecast engine), written by the controller.

An oracle in fractions.Fraction and integers only: not the code under test, never imported by
it. Every figure is invented; year 1 of the seed case is the plan's hand-worked row.
`render()` returns the key's text; run this file to write `pr2.json` next to it.
"""

import json
from collections.abc import Callable
from fractions import Fraction as F
from pathlib import Path
from typing import Any

NC_EBITDA = "Not calculable: EBITDA is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"
NC_INTEREST = "Not calculable: cash interest is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"
NC_DEBT = "Not calculable: debt is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"
ZERO = "ZERO_OR_NEGATIVE_DENOMINATOR"
FIELDS = [
    "revenue",
    "ebitda",
    "interest",
    "tax_wc",
    "capex",
    "cfo",
    "fcf",
    "opening_debt",
    "repayment",
    "closing_debt",
    "opening_cash",
    "dividends",
    "closing_cash",
    "undrawn",
    "liquidity",
    "total_leverage",
    "net_debt",
    "net_leverage",
    "coverage",
    "fcf_to_debt",
]
DRIVERS = [
    "revenue_growth",
    "ebitda_margin",
    "capex_pct_revenue",
    "tax_wc_pct_revenue",
    "interest_rate",
    "dividends",
    "debt_repayment",
]
REASONS = {"NC_EBITDA": NC_EBITDA, "NC_INTEREST": NC_INTEREST, "NC_DEBT": NC_DEBT}


class Gap:
    def __init__(self, code: str, text: str) -> None:
        self.code, self.text = code, text


Num = F | Gap


def plain(v: F) -> str:
    if v == 0:
        return "0"
    sign, v, places = ("-" if v < 0 else ""), abs(v), 0
    while v.denominator != 1:
        v, places = v * 10, places + 1
        assert places < 200
    d = str(v.numerator)
    if places:
        d = d.rjust(places + 1, "0")
        d = d[:-places] + "." + d[-places:]
    return sign + d


def round38(v: F) -> F:
    if v == 0:
        return v
    sign, v, shift = (-1 if v < 0 else 1), abs(v), 0
    while v >= 10**38:
        v, shift = v / 10, shift + 1
    while v < 10**37:
        v, shift = v * 10, shift - 1
    floor = v.numerator // v.denominator
    rest = v - floor
    if rest > F(1, 2) or (rest == F(1, 2) and floor % 2 == 1):
        floor += 1
    return sign * F(floor) * F(10) ** shift


def calc(fn: Callable[..., F], *xs: Num) -> Num:
    """fn over the operands, or the first missing operand in order."""
    gap = next((x for x in xs if isinstance(x, Gap)), None)
    return gap if gap is not None else fn(*xs)


def ratio(n: Num, d: Num, text: str) -> Num:
    if isinstance(n, Gap):
        return n
    if isinstance(d, Gap):
        return d
    return Gap(ZERO, text) if d <= 0 else round38(n / d)


Opening = tuple[Num, Num, Num, Num]


def year(opening: Opening, case: dict[str, Any], t: int) -> dict[str, Num]:
    revenue, debt, cash, undrawn = opening
    g, m, c, w, rate, div, rep = (F(case["drivers"][k][t]) for k in DRIVERS)
    shock = case.get("shock")
    s, k = (F(0), F(0)) if shock is None else (F(shock[0]), F(shock[1]))
    rev = calc(lambda r: r * (1 + g), revenue)
    ebitda = calc(lambda r: r * m * (1 - s), rev)
    if "schedule" not in case:
        interest = calc(lambda d: d * rate * (1 + k), debt)
    else:
        scheduled, rep = (F(x) for x in case["schedule"][t])
        interest = calc(lambda d: scheduled * (1 + k), debt)
    tax_wc = calc(lambda r: r * w, rev)
    capex = calc(lambda r: r * c, rev)
    cfo = calc(lambda e, i, x: e - i - x, ebitda, interest, tax_wc)
    fcf = calc(lambda a, b: a - b, cfo, capex)
    closing_debt = calc(lambda d: d - rep, debt)
    closing_cash = calc(lambda o, f: o + f - div - rep, cash, fcf)
    net_debt = calc(lambda d, cc: d - cc, closing_debt, closing_cash)
    figures = (rev, ebitda, interest, tax_wc, capex, cfo, fcf, debt, rep, closing_debt, cash, div)
    return dict(zip(FIELDS, figures)) | {
        "closing_cash": closing_cash,
        "undrawn": undrawn,
        "liquidity": calc(lambda cc, u: cc + u, closing_cash, undrawn),
        "total_leverage": ratio(closing_debt, ebitda, NC_EBITDA),
        "net_debt": net_debt,
        "net_leverage": ratio(net_debt, ebitda, NC_EBITDA),
        "coverage": ratio(ebitda, interest, NC_INTEREST),
        "fcf_to_debt": ratio(fcf, closing_debt, NC_DEBT),
    }


def show(v: Num) -> str | dict[str, Any]:
    if not isinstance(v, Gap):
        return plain(v)
    name = next((k for k, text in REASONS.items() if text == v.text), None)
    return {"missing": name} if name else {"missing": {"code": v.code, "text": v.text}}


def operand(v: str | dict[str, str]) -> Num:
    return Gap(v["code"], v["text"]) if isinstance(v, dict) else F(v)


def run(case: dict[str, Any]) -> list[dict[str, Num]]:
    ops = case["operands"]
    revenue, debt, cash, undrawn = (operand(ops[k]) for k in ("revenue", "debt", "cash", "undrawn"))
    opening: Opening = (revenue, debt, cash, undrawn)
    years = []
    for t in range(3):
        y = year(opening, case, t)
        years.append(y)
        opening = (y["revenue"], y["closing_debt"], y["closing_cash"], y["undrawn"])
    return years


def gap(text: str) -> dict[str, str]:
    return {"code": "NOT_SOURCED", "text": text}


SEED_OPS = {"revenue": "1000", "debt": "600", "cash": "100", "undrawn": "50"}
SEED = {
    k: [v, v, v]
    for k, v in zip(DRIVERS, ("0.20", "0.25", "0.03", "0.02", "0.05", "10", "75"), strict=True)
}
VARY = {
    "revenue_growth": ["0.10", "-0.05", "0"],
    "ebitda_margin": ["0.30", "0.28", "0.25"],
    "capex_pct_revenue": ["0.04", "0.05", "0.03"],
    "tax_wc_pct_revenue": ["0.02", "0.01", "0.03"],
    "interest_rate": ["0.06", "0.065", "0.07"],
    "dividends": ["0", "12.5", "20"],
    "debt_repayment": ["40", "0", "160"],
}
SCHEDULE = [["20", "50"], ["18", "50"], ["15", "100"]]
SHOCK = ["0.2", "0.5"]


def case(name: str, ops: dict[str, Any] | None = None, **extra: Any) -> dict[str, Any]:
    """A case over the seed: `ops` and `drivers` replace single entries of the seed's."""
    drivers = {**SEED, **extra.pop("drivers", {})}
    return {"name": name, "operands": {**SEED_OPS, **(ops or {})}, "drivers": drivers, **extra}


REV, DEBT = gap("base revenue is missing"), gap("base debt is missing")
CASH, UNDRAWN = gap("base cash is missing"), gap("base undrawn is missing")
VARYING_OPS = {"revenue": "2480.5", "debt": "1200", "cash": "310.25", "undrawn": "0"}
CASES = [
    case("seed"),
    case("seed_shock", shock=SHOCK),
    case("seed_zero_shock", shock=["0", "0"]),
    case("varying", VARYING_OPS, drivers=VARY),
    case("schedule", schedule=SCHEDULE),
    case("schedule_shock", shock=SHOCK, schedule=SCHEDULE),
    case("revenue_missing", {"revenue": REV}),
    case("debt_missing", {"debt": DEBT}),
    case("debt_missing_schedule", {"debt": DEBT}, schedule=SCHEDULE),
    case("cash_missing", {"cash": CASH}),
    case("undrawn_missing", {"undrawn": UNDRAWN}),
    case("revenue_and_debt_missing", {"revenue": REV, "debt": DEBT}),
    case("cash_and_revenue_missing", {"cash": CASH, "revenue": REV}),
    case("undrawn_and_cash_missing", {"undrawn": UNDRAWN, "cash": CASH}),
    case("zero_margin", drivers={"ebitda_margin": ["0", "0", "0"]}),
    case("negative_margin_year_2", drivers={"ebitda_margin": ["0.25", "-0.05", "0.25"]}),
    case("zero_rate", drivers={"interest_rate": ["0", "0", "0"]}),
    case("debt_repaid", drivers={"debt_repayment": ["300", "300", "0"]}),
    case("debt_overpaid", drivers={"debt_repayment": ["300", "400", "0"]}),
    case("full_decline", shock=["1", "0"]),
    case(
        "cash_goes_negative",
        {"cash": "0"},
        drivers={"ebitda_margin": ["0.05", "0.05", "0.05"], "dividends": ["100", "100", "100"]},
    ),
]
PLAN_ROW = dict(
    zip(
        [
            "revenue",
            "ebitda",
            "interest",
            "cfo",
            "fcf",
            "closing_debt",
            "closing_cash",
            "net_debt",
            "liquidity",
            "total_leverage",
            "net_leverage",
            "coverage",
            "fcf_to_debt",
        ],
        ["1200", "300", "30", "246", "210", "525", "225", "300", "275", "1.75", "1", "10", "0.4"],
        strict=True,
    )
)
ABOUT = (
    "Step 1B PR 2 answer key, written by the controller. Every figure is invented. Computed "
    "with fractions.Fraction and integer half-even rounding to 38 significant digits by the "
    "controller's oracle script (not the code under test); year 1 of seed and seed_shock is the "
    "plan's hand-worked row. Each year is a list in the order of fields. An amount is the "
    "amount_text of the Value; a missing value is {missing: <name in reasons>} with code "
    "ZERO_OR_NEGATIVE_DENOMINATOR, or {missing: {code, text}} for a missing operand carried "
    "through. Implementers do not edit this file."
)


def line(obj: object) -> str:
    return json.dumps(obj, separators=(", ", ": "))


def checked() -> list[dict[str, Any]]:
    """Every case with its three years shown, after the plan's hand-worked checks."""
    out = [{**c, "years": [{f: show(y[f]) for f in FIELDS} for y in run(c)]} for c in CASES]
    y1 = out[0]["years"][0]
    assert {k: y1[k] for k in PLAN_ROW} == PLAN_ROW, y1
    s1 = out[1]["years"][0]
    assert (s1["ebitda"], s1["interest"], s1["total_leverage"]) == ("240", "45", "2.1875")
    assert s1["coverage"] == "5." + "3" * 37, s1["coverage"]
    assert out[2]["years"] == out[0]["years"]
    for c in out:
        for a, b in zip(c["years"], c["years"][1:]):
            assert (b["opening_debt"], b["opening_cash"]) == (a["closing_debt"], a["closing_cash"])
    return out


def render() -> str:
    rows = []
    for c in checked():
        head = {k: c[k] for k in ("name", "operands", "drivers", "shock", "schedule") if k in c}
        years = ",\n    ".join(line([y[f] for f in FIELDS]) for y in c["years"])
        rows.append("  {" + line(head)[1:-1] + ', "years": [\n    ' + years + "]}")
    return (
        f'{{\n "about": {line(ABOUT)},\n "fields": {line(FIELDS)},\n'
        f' "drivers": {line(DRIVERS)},\n "reasons": {line(REASONS)},\n'
        ' "cases": [\n' + ",\n".join(rows) + "\n ]\n}\n"
    )


if __name__ == "__main__":
    Path(__file__).with_name("pr2.json").write_text(render(), "utf-8")
