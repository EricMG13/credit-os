"""Answer key for 1B PR 7a2 (the forecast cases), written by the answer-key author.

An oracle in fractions.Fraction only: not the code under test, never imported by it. It loads
`make_pr7a1.py` (the block, the edits and the case pieces), `make_pr2.py` (the engine oracle) and
`make_pr3.py` (the facility-schedule oracle) by path and adds the cases and their order, the
remainder interest of the unallocated debt and the stress basis. Every figure, name and text is
invented. A row is an edit list over the block and the expected cases; `render()` returns the key's
text, run this file to write `pr7a2.json` next to it.
"""

import importlib.util
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


def load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


P1 = load("make_pr7a1")
PR2, PR3, Gap, FIELDS, plain = P1.PR2, P1.PR3, P1.Gap, P1.FIELDS, P1.plain
NEG_TEXT, REASONS, BLOCK = P1.NEG_TEXT, P1.REASONS, P1.BLOCK
Edits = list[tuple[str, Any]]
FACE, ALL_SEVEN, LOST, line = P1.FACE, P1.ALL_SEVEN, P1.LOST, P1.line
case, gone, edited, normal, thousands = P1.case, P1.gone, P1.edited, P1.normal, P1.thousands
merged, unallocated, overlay, operands = P1.merged, P1.unallocated, P1.overlay, P1.operands
flatten, show, thrice = P1.flatten, P1.show, P1.thrice


NOCASE: Edits = [("upside_drivers", None), ("downside_drivers", None)]


NOSHOCK: Edits = [("downside_shock", None)]


PLAIN: Edits = NOCASE + NOSHOCK


def shock(decline: str, rate: str) -> Edits:
    return [("downside_shock", {"ebitda_decline": decline, "rate_increase": rate})]


def flat(dividends: list[str], cash: str = "100", margin: str = "0.1") -> Edits:
    """Revenue 1000 flat, EBITDA 100 a year, no interest, tax, capex or repayment."""
    zero = thrice("0")
    shape = [
        ("revenue_growth", zero),
        ("ebitda_margin", thrice(margin)),
        ("capex_pct_revenue", zero),
    ]
    shape += [("tax_wc_pct_revenue", zero), ("interest_rate", zero), ("debt_repayment", zero)]
    edits: Edits = [(f"base_drivers.{n}.values", v) for n, v in shape]
    return [
        *edits,
        ("base_drivers.dividends.values", dividends),
        ("base.cash.amount", cash),
        *PLAIN,
    ]


def schedule(block: dict[str, Any], drivers: dict[str, list[str]]) -> list[list[F]] | None:
    if not block["facilities"]:
        return None
    rest, rows, out = unallocated(block), [PR3.years(f) for f in block["facilities"]], []
    for t in range(3):
        interest = sum((r[t][2] for r in rows), F(0))
        if isinstance(rest, F) and rest > 0:
            interest += rest * F(drivers["interest_rate"][t])
        out.append([interest, sum((r[t][3] for r in rows), F(0))])
    return out


def solve(block: dict[str, Any]) -> tuple[list[tuple[str, list[dict[str, Any]]]], str | None]:
    """The cases in order, each three years after the overlay, and the stress basis."""
    plan: list[tuple[str, str | None, list[str] | None]] = [("reference", None, None)]
    for name in ("upside", "downside"):
        if block[f"{name}_drivers"]:
            plan.append((name, f"{name}_drivers", None))
    basis = "downside" if block["downside_drivers"] else "base"
    if block["downside_shock"]:
        s = block["downside_shock"]
        plan.append(
            (
                "downside_stress",
                "downside_drivers" if basis == "downside" else None,
                [s["ebitda_decline"], s["rate_increase"]],
            )
        )
    cases = []
    for name, group, hit in plan:
        drivers = merged(block, group)
        spec: dict[str, Any] = {"operands": operands(block), "drivers": drivers}
        if hit:
            spec["shock"] = hit
        if block["facilities"]:
            spec["schedule"] = schedule(block, drivers)
        cases.append((name, [overlay(y) for y in PR2.run(spec)]))
    return cases, basis if block["downside_shock"] else None


SET, DRV, SHK, REM, MISS, NEG = (
    "case_set",
    "drivers",
    "shock",
    "remainder",
    "missing",
    "negative_cash",
)


RATES = ["0.05", "0.08", "0.11"]


REMAINDER_ALL: Edits = FACE + case("upside_drivers", interest_rate=RATES)


REMAINDER_ALL += case(
    "downside_drivers",
    interest_rate=["0.07", "0.09", "0.12"],
    ebitda_margin=["0.20", "0.21", "0.22"],
)


SPECS: list[tuple[str, str, Edits]] = [
    (SET, "all_four_stress_over_downside", []),
    (SET, "upside_and_stress_over_base", [("downside_drivers", None)]),
    (SET, "upside_only", [("downside_drivers", None), *NOSHOCK]),
    (SET, "downside_only", [("upside_drivers", None), *NOSHOCK]),
    (SET, "reference_only", PLAIN),
    (SET, "downside_and_stress_no_upside", [("upside_drivers", None)]),
    (SET, "shock_only_over_base", NOCASE),
    (SET, "upside_and_downside_no_stress", NOSHOCK),
    (SET, "zero_shock_equals_downside", shock("0", "0")),
    (
        DRV,
        "one_driver_inherits_six",
        case("upside_drivers", capex_pct_revenue=["0.03", "0.03", "0.05"])
        + [("downside_drivers", None)]
        + NOSHOCK,
    ),
    (
        DRV,
        "all_seven_in_upside",
        case("upside_drivers", **ALL_SEVEN) + [("downside_drivers", None)] + NOSHOCK,
    ),
    (
        DRV,
        "dividends_and_repayment_override",
        case("upside_drivers", dividends=["0", "0", "0"])
        + case("downside_drivers", debt_repayment=thrice("100"))
        + NOSHOCK,
    ),
    (SHK, "rate_increase_without_schedule", NOCASE + shock("0", "0.5")),
    (SHK, "rate_increase_with_schedule", NOCASE + FACE + shock("0.1", "0.5")),
    (SHK, "full_ebitda_decline", NOCASE + shock("1", "0")),
    (REM, "remainder_positive", FACE + PLAIN),
    (REM, "remainder_year_varying_rate_all_cases", REMAINDER_ALL),
    (REM, "remainder_stress_over_base_rate", FACE + NOCASE),
    (REM, "remainder_zero", FACE + [("facilities.1.balance", "300")] + NOCASE),
    (REM, "remainder_negative", FACE + [("facilities.1.balance", "400")] + NOCASE),
    (REM, "remainder_debt_missing", FACE + gone("debt", LOST)),
    (REM, "remainder_fractional", FACE + [("base.debt.amount", "600.5")] + NOCASE),
    (MISS, "revenue_missing", gone("revenue")),
    (MISS, "cash_missing", gone("cash")),
    (MISS, "undrawn_missing", gone("undrawn")),
    (MISS, "revenue_and_cash_missing", gone("revenue", "no revenue") + gone("cash", "no cash")),
    (
        MISS,
        "all_four_missing_verbatim",
        gone("revenue", " A  b ")
        + gone("debt", LOST)
        + gone("cash", "c.")
        + gone("undrawn", "Ünstated"),
    ),
    (NEG, "negative_year1_then_recovers", flat(["250", "0", "0"])),
    (NEG, "negative_year2_zero_year3", flat(["0", "400", "0"])),
    (NEG, "smallest_negative", flat(["200.0001", "0", "0"])),
    (NEG, "closing_cash_exactly_zero", flat(["200", "0", "0"])),
    (NEG, "minus_zero_cash", flat(thrice("0"), cash="-0") + [("base.revenue.amount", "0")]),
    (NEG, "cash_missing_is_not_negative", flat(["250", "0", "0"]) + gone("cash")),
    (NEG, "negative_with_ebitda_zero", flat(["150", "0", "0"], margin="0")),
    (NEG, "negative_only_in_stress", flat(["160", "0", "0"]) + shock("0.5", "0")),
    (
        NEG,
        "negative_replaces_own_reasons",
        flat(["250", "0", "0"]) + gone("debt") + gone("undrawn"),
    ),
    (
        NEG,
        "negative_in_two_of_three_cases",
        flat(["250", "0", "0"])
        + case("upside_drivers", dividends=thrice("0"))
        + case("downside_drivers", ebitda_margin=thrice("0.05")),
    ),
]


SCALED = [
    ("all_four_stress_over_downside"),
    "remainder_year_varying_rate_all_cases",
    "smallest_negative",
]


def rows() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [{"kind": k, "name": n, "edits": e} for k, n, e in SPECS]
    by_name = {r["name"]: r for r in out}
    for name in SCALED:
        out.append(
            {
                "kind": "scale",
                "name": f"thousands_of_{name}",
                "edits": thousands(by_name[name]["edits"]),
                "same_as": name,
            }
        )
    return out


ABOUT = (
    "Step 1B PR 7a2 answer key, written by the answer-key author. Every figure, name and text is "
    "invented. Computed with fractions.Fraction by make_pr7a2.py (not the code under test), which "
    "loads the 7a1 pieces, the PR 2 engine oracle and the PR 3 facility oracle by path. `block` is "
    "one forecast inputs document; a row applies its dotted-path `edits` in order (a number indexes "
    "a list) and lists its cases (each year a list in the order of `fields`). An amount is "
    "amount_text; a missing value is {missing: <name in reasons>} or {missing: {code, text}}. "
    "`basis` is the stress basis or null. A row with `same_as` expects what that row expects. "
    "Implementers do not edit this file."
)


def checked() -> list[dict[str, Any]]:
    out = []
    solved: dict[str, Any] = {}
    for row in rows():
        cases, basis = solve(normal(row["edits"]))
        solved[row["name"]] = (cases, basis)
        if "same_as" in row:
            assert (flat_cases(cases), basis) == (
                flat_cases(solved[row["same_as"]][0]),
                solved[row["same_as"]][1],
            )
        out.append({**row, "basis": basis, "cases": cases})
    return out


def flat_cases(cases: list[tuple[str, list[dict[str, Any]]]]) -> list[Any]:
    return [(n, [[flatten(y[f]) for f in FIELDS] for y in ys]) for n, ys in cases]


def hand_checks(by_name: dict[str, Any]) -> None:
    """Rows worked by hand (see the report); each figure is written, not computed."""
    recover = by_name["negative_year1_then_recovers"]["cases"][0][1]
    got = [
        [
            flatten(y[f])
            for f in (
                "ebitda",
                "closing_cash",
                "net_debt",
                "liquidity",
                "total_leverage",
                "net_leverage",
            )
        ]
        for y in recover
    ]
    gap = ["NEGATIVE_CASH", NEG_TEXT]
    assert got[0] == ["100", "-50", gap, gap, "6", gap], got[0]
    assert got[1] == ["100", "50", "550", "100", "6", "5.5"], got[1]
    assert got[2][1:4] == ["150", "450", "200"], got[2]
    stress = by_name["negative_only_in_stress"]["cases"]
    assert [flatten(y["closing_cash"]) for y in stress[0][1]] == ["40", "140", "240"]
    assert [flatten(y["closing_cash"]) for y in stress[1][1]] == ["-10", "40", "90"]
    assert (
        flatten(stress[1][1][0]["liquidity"]) == gap
        and flatten(stress[0][1][0]["liquidity"]) == "90"
    )
    small = by_name["smallest_negative"]["cases"][0][1]
    assert [flatten(y["closing_cash"]) for y in small] == ["-0.0001", "99.9999", "199.9999"]
    rest = by_name["remainder_positive"]["cases"][0][1][0]
    expected = {
        "interest": "38.5",
        "cfo": "214.5",
        "fcf": "170.5",
        "repayment": "25",
        "closing_debt": "575",
        "closing_cash": "235.5",
    }
    assert {k: flatten(rest[k]) for k in expected} == expected, rest
    names = [n for n, _ in by_name["all_four_stress_over_downside"]["cases"]]
    assert names == ["reference", "upside", "downside", "downside_stress"]


def render() -> str:
    done = checked()
    hand_checks({r["name"]: r for r in done})
    parts = []
    for row in done:
        head = {
            k: row[k]
            for k in ("kind", "name", "edits", "basis") + (("same_as",) if "same_as" in row else ())
        }
        body = (
            []
            if "same_as" in row
            else [
                line({"name": n, "years": [[show(y[f]) for f in FIELDS] for y in ys]})
                for n, ys in row["cases"]
            ]
        )
        text = line(head)[:-1] + ', "cases": [' + (", ".join(body) + "]}")
        parts.append("  " + text)
    kinds = Counter(r["kind"] for r in done)
    return (
        f'{{\n "about": {line(ABOUT)},\n "fields": {line(FIELDS)},\n "reasons": {line(REASONS)},\n'
        f' "kinds": {line(dict(kinds))},\n "block": {line(BLOCK)},\n "rows": [\n'
        + ",\n".join(parts)
        + "\n ]\n}\n"
    )


if __name__ == "__main__":
    Path(__file__).with_name("pr7a2.json").write_text(render(), "utf-8")
