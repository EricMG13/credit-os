"""Answer key for 1B PR 7a1 (the case pieces), written by the answer-key author.

An oracle in fractions.Fraction only: not the code under test, never imported by it. It loads
`make_pr2.py` and `make_pr3.py` by path and adds the pieces of the forecast cases: the base
operands, a case's drivers (its own where stated, else base's), the unallocated debt and the
negative-cash overlay. Every figure, name and text is invented. A row is an edit list over one
block (dotted paths; an index is a number) and the expected piece; `make_pr7a2.py` loads this file
for the shared block, edits and pieces. `render()` returns the key's text, run this file to write
`pr7a1.json` next to it.
"""

import copy
import importlib.util
import json
import re
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


PR2, PR3 = load("make_pr2"), load("make_pr3")


Gap, FIELDS, DRIVERS = PR2.Gap, PR2.FIELDS, PR2.DRIVERS


NEG_TEXT = "Not calculable: cash is negative before funding"


ZERO = "ZERO_OR_NEGATIVE_DENOMINATOR"


REASONS = {
    "NC_EBITDA": [ZERO, PR2.NC_EBITDA],
    "NC_INTEREST": [ZERO, PR2.NC_INTEREST],
    "NC_DEBT": [ZERO, PR2.NC_DEBT],
    "NEGATIVE_CASH": ["NEGATIVE_CASH", NEG_TEXT],
}


OVERLAID = ("net_debt", "net_leverage", "liquidity")


OPERANDS = ("revenue", "debt", "cash", "undrawn")


NAMES = ["revenue", "ebitda", "interest", "taxes", "wc", "capex", "fcf", "debt", "cash", "undrawn"]


THOUSANDS = re.compile(r"-?[0-9]{1,9}(\.[0-9])?")


plain = PR2.plain


def drv(values: list[str]) -> dict[str, Any]:
    return {
        "values": values,
        "category": "Analyst Interpretation",
        "rationale": "Invented for the key.",
        "limitation": None,
    }


def thrice(value: str) -> list[str]:
    return [value] * 3


BLOCK: dict[str, Any] = {
    "schema_version": "cpos-forecast-inputs/1",
    "base": {
        n: {"amount": a, "reason": None, "row": n.title(), "period": "FY2024", "column": None}
        for n, a in zip(
            NAMES, ("1000", "250", "30", "15", "5", "30", "100", "600", "100", "50"), strict=True
        )
    },
    "base_drivers": {
        "revenue_growth": drv(["0.10", "0.05", "0.04"]),
        "ebitda_margin": drv(["0.25", "0.26", "0.27"]),
        "capex_pct_revenue": drv(thrice("0.04")),
        "tax_wc_pct_revenue": drv(thrice("0.02")),
        "interest_rate": drv(["0.06", "0.065", "0.07"]),
        "dividends": drv(["10", "12", "15"]),
        "debt_repayment": drv(["20", "20", "30"]),
    },
    "downside_shock": {"ebitda_decline": "0.15", "rate_increase": "0.2"},
    "upside_drivers": {"revenue_growth": drv(["0.12", "0.10", "0.08"])},
    "downside_drivers": {
        "revenue_growth": drv(["0.02", "0", "0.01"]),
        "ebitda_margin": drv(["0.20", "0.21", "0.22"]),
    },
    "years": [
        {"year": 2025, "start": "2024-07-01", "end": "2025-06-30"},
        {"year": 2026, "start": "2025-07-01", "end": "2026-06-30"},
        {"year": 2027, "start": "2026-07-01", "end": "2027-06-30"},
    ],
    "facilities": None,
    "scale": 1,
    "currency": "USD",
    "scope_limits": ["Invented key: no issuer is forecast."],
}


FACS = [
    PR3.fac("Term loan A", "300", fixed_rate_pct="6.5", amort="25", maturity="2029-06-30"),
    PR3.fac(
        "Floater",
        "200",
        spread_pct="2.25",
        floor_pct="1",
        reference_rate=["0.0425", "0.035", "0.01"],
    ),
]


Edits = list[tuple[str, Any]]


FACE: Edits = [("facilities", FACS)]


def case(group: str, **drivers: list[str]) -> Edits:
    return [(group, {name: drv(values) for name, values in drivers.items()})]


def gone(name: str, reason: str = "Not stated in the invented source.") -> Edits:
    return [(f"base.{name}", {"amount": None, "reason": reason})]


def put(block: dict[str, Any], path: str, value: Any) -> None:
    *head, last = path.split(".")
    node: Any = block
    for step in head:
        node = node[int(step)] if isinstance(node, list) else node[step]
    node[int(last) if isinstance(node, list) else last] = copy.deepcopy(value)


def edited(edits: Edits) -> dict[str, Any]:
    block = copy.deepcopy(BLOCK)
    for path, value in edits:
        put(block, path, value)
    return block


def scaled(block: dict[str, Any], factor: F) -> Edits:
    """Every amount the thousands block prints in thousands, times `factor`."""

    def up(text: str) -> str:
        return str(plain(F(text) * factor))

    more: Edits = [
        (f"base.{k}.amount", up(o["amount"])) for k, o in block["base"].items() if o["amount"]
    ]
    for group in ("base_drivers", "upside_drivers", "downside_drivers"):
        for name in ("dividends", "debt_repayment"):
            if block[group] and block[group].get(name):
                more.append(
                    (f"{group}.{name}.values", [up(v) for v in block[group][name]["values"]])
                )
    for index, fac in enumerate(block["facilities"] or ()):
        more += [
            (f"facilities.{index}.{k}", up(fac[k]))
            for k in ("balance", "annual_amortisation")
            if fac[k]
        ]
    return more


def thousands(edits: Edits) -> Edits:
    """The same block with every amount printed in thousands and scale 1000."""
    more = scaled(edited(edits), F(1000))
    for _, value in more:
        for text in value if isinstance(value, list) else [value]:
            assert THOUSANDS.fullmatch(text), text
    return [*edits, *more, ("scale", 1000)]


def normal(edits: Edits) -> dict[str, Any]:
    """The block in millions: a thousands block is divided back, as the parser reads it."""
    block = edited(edits)
    if block["scale"] == 1000:
        for path, value in scaled(block, F(1, 1000)):
            put(block, path, value)
    return block


def merged(block: dict[str, Any], group: str | None) -> dict[str, list[str]]:
    own = block[group] if group else None
    return {
        n: (own[n]["values"] if own and own.get(n) else block["base_drivers"][n]["values"])
        for n in DRIVERS
    }


def unallocated(block: dict[str, Any]) -> Any:
    if not block["facilities"]:
        return None
    debt = block["base"]["debt"]
    if debt["amount"] is None:
        return Gap("NOT_SOURCED", debt["reason"])
    return F(debt["amount"]) - sum((F(f["balance"]) for f in block["facilities"]), F(0))


def overlay(year: dict[str, Any]) -> dict[str, Any]:
    cash = year["closing_cash"]
    if isinstance(cash, F) and cash < 0:
        return year | {n: Gap("NEGATIVE_CASH", NEG_TEXT) for n in OVERLAID}
    return year


def operands(block: dict[str, Any]) -> dict[str, Any]:
    pairs = ((k, block["base"][k]) for k in OPERANDS)
    return {
        k: {"code": "NOT_SOURCED", "text": o["reason"]} if o["amount"] is None else o["amount"]
        for k, o in pairs
    }


def flatten(v: Any) -> str | list[str]:
    return plain(v) if not isinstance(v, Gap) else [v.code, v.text]


def show(v: Any) -> Any:
    out = flatten(v)
    if isinstance(out, str):
        return out
    name = next((k for k, r in REASONS.items() if r == out), None)
    return {"missing": name} if name else {"missing": {"code": out[0], "text": out[1]}}


# (kind, name, edits); a thousands row names the row it prints in thousands.


ALL_SEVEN = {
    "revenue_growth": ["0.01", "0.02", "0.03"],
    "ebitda_margin": ["0.30", "0.31", "0.32"],
    "capex_pct_revenue": ["0.03", "0.03", "0.05"],
    "tax_wc_pct_revenue": ["0.01", "0.02", "0.03"],
    "interest_rate": ["0.08", "0.09", "0.10"],
    "dividends": ["0", "5", "50"],
    "debt_repayment": ["60", "0", "100"],
}


LOST = "Debt: 'Total  Debt' is not stated; see note 4."


def operands_rows() -> list[dict[str, Any]]:
    named = [
        ("base_amounts", []),
        ("two_reasons", gone("revenue", "R") + gone("undrawn", "U")),
        ("thousands", thousands([])),
    ]
    return [
        {
            "name": n,
            "edits": e,
            "expected": {
                k: show(F(v) if isinstance(v, str) else Gap(v["code"], v["text"]))
                for k, v in operands(normal(e)).items()
            },
        }
        for n, e in named
    ]


def drivers_rows() -> list[dict[str, Any]]:
    named: list[tuple[str, Edits, str | None]] = [
        ("base_alone", [], None),
        ("upside_one_driver", [], "upside_drivers"),
        ("downside_two_drivers", [], "downside_drivers"),
        ("all_seven", case("upside_drivers", **ALL_SEVEN), "upside_drivers"),
        ("thousands_amounts_in_millions", thousands([]), "upside_drivers"),
    ]
    return [
        {"name": n, "edits": e, "group": g, "expected": merged(normal(e), g)} for n, e, g in named
    ]


def unallocated_rows() -> list[dict[str, Any]]:
    named: list[tuple[str, Edits]] = [
        ("no_facilities", []),
        ("positive", FACE),
        ("zero", FACE + [("facilities.1.balance", "300")]),
        ("negative", FACE + [("facilities.1.balance", "400.25")]),
        ("debt_missing", FACE + gone("debt", LOST)),
        ("thousands", thousands(FACE)),
    ]
    out = []
    for n, e in named:
        left = unallocated(normal(e))
        out.append({"name": n, "edits": e, "expected": None if left is None else show(left)})
    return out


def year_of(**changes: Any) -> dict[str, Any]:
    return {f: F(i + 1) for i, f in enumerate(FIELDS)} | changes


def overlay_rows() -> list[dict[str, Any]]:
    own = {
        "net_debt": Gap("NOT_SOURCED", "d"),
        "net_leverage": Gap(ZERO, PR2.NC_EBITDA),
        "liquidity": Gap("NOT_SOURCED", "u"),
        "total_leverage": Gap(ZERO, PR2.NC_EBITDA),
    }
    named = [
        ("below_zero", year_of(closing_cash=F(-1, 10000))),
        ("zero", year_of(closing_cash=F(0))),
        ("minus_zero_text", year_of(closing_cash=F(0))),
        ("above_zero", year_of(closing_cash=F(1, 10000))),
        (
            "missing",
            year_of(closing_cash=Gap("NOT_SOURCED", "c"), net_debt=Gap("NOT_SOURCED", "c")),
        ),
        ("below_zero_replaces_own_reasons", year_of(closing_cash=F(-5), **own)),
    ]
    out = []
    for n, y in named:
        text = "-0" if n == "minus_zero_text" else None
        shown = {f: show(v) for f, v in y.items()}
        out.append(
            {
                "name": n,
                "year": shown,
                "expected": {f: show(v) for f, v in overlay(y).items()},
                "closing_cash_text": text,
            }
        )
    return out


ABOUT = (
    "Step 1B PR 7a1 answer key, written by the answer-key author. Every figure, name and text is "
    "invented. Computed with fractions.Fraction by make_pr7a1.py (not the code under test). `block` "
    "is one forecast inputs document; a row applies its dotted-path `edits` in order (a number "
    "indexes a list). An amount is amount_text; a missing value is {missing: <name in reasons>} or "
    "{missing: {code, text}}. An overlay row lists a year's fields and the fields expected after the "
    "overlay. Implementers do not edit this file."
)


def line(obj: object) -> str:
    return json.dumps(obj, separators=(", ", ": "), ensure_ascii=True)


def render() -> str:
    sections = {
        "operands": operands_rows(),
        "drivers": drivers_rows(),
        "unallocated": unallocated_rows(),
        "overlay": overlay_rows(),
    }
    extra = ",\n".join(
        f' "{k}": [\n  ' + ",\n  ".join(line(r) for r in v) + "\n ]" for k, v in sections.items()
    )
    return (
        f'{{\n "about": {line(ABOUT)},\n "fields": {line(FIELDS)},\n "reasons": {line(REASONS)},\n'
        f' "block": {line(BLOCK)},\n' + extra + "\n}\n"
    )


if __name__ == "__main__":
    Path(__file__).with_name("pr7a1.json").write_text(render(), "utf-8")
