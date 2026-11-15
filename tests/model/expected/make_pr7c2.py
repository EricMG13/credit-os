"""Answer key for 1B PR 7c2 (ForecastResult and run_forecast), written by the answer-key author.

An oracle in fractions, hashlib and json only: not the code under test, never imported by it. It
loads `make_pr7c1.py` (the document builder and rows), `make_pr7a2.py` (the cases) and
`make_pr7b.py` (the facility detail and limits) by path. A row is the 7c1 row shape (source,
foundation and forward documents) with the expected result: both hashes, currency, scale, spans,
stress basis, every case's years, the facility detail and every limit in order. `render()` returns
the key's text; run this file to write `pr7c2.json` next to it.
"""

import hashlib
import importlib.util
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("make_pr7c1", HERE / "make_pr7c1.py")
assert SPEC is not None and SPEC.loader is not None
C1 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C1)
A7, B7, A, line = C1.A7, C1.B7, C1.A, C1.line
doc, FWD, L1, FND_FILE, FWD_FILE = C1.doc, C1.FWD, C1.L1, C1.FND_FILE, C1.FWD_FILE
FIELDS, REASONS = A7.FIELDS, A7.REASONS
Spec = dict[str, Any]

LIMIT = (
    "Every figure is Python's arithmetic over inputs the forward credit model stated; the inputs, "
    "not the arithmetic, are unreviewed. Not analytical review."
)
LAYER1 = (
    "Every figure is Python's arithmetic over run-rate inputs the financial foundation stated, from "
    "its own figures; no forward credit model, case or shock was run. The inputs, not the "
    "arithmetic, are unreviewed. Not analytical review."
)
SCALE_TEXT = (
    "The forecast inputs state base amounts, amount drivers and facility amounts in {currency} "
    "thousands, as the financial foundation prints them (scale 1000); Python divided each by 1,000 "
    "before any calculation. Every figure here is {currency} millions."
)
HEADING = "### Forecast inputs (machine-readable)"
TLB_CELL = "| Term loan B | 640 | Reference"
REVENUE_CELL = "| Revenue | 1,318 | 1,456 | 968 |"
NO_CASES = [["upside_drivers", None], ["downside_drivers", None], ["downside_shock", None]]
SIX = [[REVENUE_CELL, REVENUE_CELL.replace("1,456", "1,456.789")]]


def sha(spec: Spec) -> str:
    return hashlib.sha256(C1.data(spec)).hexdigest()


def block_of(spec: Spec) -> dict[str, Any]:
    """The block in millions: a thousands block is divided back, as the reader does."""
    block: dict[str, Any] = C1.raw_block(spec)
    if block["scale"] == 1000:
        for path, value in A.scaled(block, F(1, 1000)):
            A.put(block, path, value)
    return block


def expected(source: str, foundation: Spec, forward: Spec | None) -> dict[str, Any]:
    block = block_of(foundation if forward is None else forward)
    cases, basis = A7.solve(block)
    limits = [LIMIT if source == FWD else LAYER1]
    limits += [SCALE_TEXT.format(currency=block["currency"])] if block["scale"] == 1000 else []
    limits += block["scope_limits"]
    detail: Any = None
    if block["facilities"]:
        left = A.unallocated(block)
        detail = {"facilities": B7.detail(block), "unallocated": A.show(left)}
        limits += [B7.FACILITY_LIMIT, *B7.unallocated_limit(left), *B7.maturity_limits(block)]
    return {
        "foundation_sha256": sha(foundation),
        "forward_sha256": None if forward is None else sha(forward),
        "currency": block["currency"],
        "scale": block["scale"],
        "spans": [[s["year"], s["start"], s["end"]] for s in block["years"]],
        "stress_basis": basis,
        "cases": cases,
        "facilities": detail,
        "limits": limits,
    }


def balance(amount: str) -> list[Spec]:
    """The forward model with Term loan B at `amount`, printed in the foundation."""
    edits = [[TLB_CELL, TLB_CELL.replace("640", amount)]]
    return [doc(FND_FILE, edits), doc(FWD_FILE, None, [["facilities.0.balance", amount]])]


def plan() -> list[tuple[str, str, Spec, Spec | None]]:
    fwd, fnd = doc(FWD_FILE), doc(FND_FILE)
    big = [["base_drivers.dividends.values", ["900", "12", "12"]]]
    scopes = NO_CASES + [["scope_limits", ["First.", "Second."]]]
    other = [["base_drivers.dividends.values", ["99"] * 3]]
    return [
        ("forward_millions", FWD, fnd, fwd),
        ("forward_thousands", FWD, doc(C1.THOUSANDS[1]), doc(C1.THOUSANDS[0])),
        ("layer1_millions", L1, fnd, None),
        ("layer1_thousands", L1, doc(C1.THOUSANDS[1]), None),
        ("r31_no_layer1_section", FWD, doc(FND_FILE, [["cut", HEADING]]), fwd),
        ("r31_foundation_block_differs", FWD, doc(FND_FILE, None, other), fwd),
        ("reference_only_two_scope_limits", FWD, fnd, doc(FWD_FILE, None, scopes)),
        ("layer1_negative_cash", L1, doc(FND_FILE, None, big), None),
        (
            "layer1_six_digit_revenue",
            L1,
            doc(FND_FILE, SIX, [["base.revenue.amount", "1456.789"]]),
            None,
        ),
        (
            "forward_eur_block_over_eur_foundation",
            FWD,
            doc("foundation-eur.md"),
            doc(FND_FILE, None, [["currency", "EUR"]]),
        ),
        ("six_digit_remainder_positive", FWD, *balance("612.345")),
        ("six_digit_unallocated_negative", FWD, *balance("812.345")),
        ("unallocated_below_one", FWD, *balance("799.2475")),
    ]


def rows() -> list[dict[str, Any]]:
    return [C1.row("accepted", n, s, f, w, expected=expected(s, f, w)) for n, s, f, w in plan()]


def figures(item: dict[str, Any], *skip: str) -> Any:
    return {k: v for k, v in item["expected"].items() if k not in skip}


def checked() -> list[dict[str, Any]]:
    done = rows()
    by = {r["name"]: r for r in done}
    sums: dict[str, str] = {}
    for text in (C1.FIXTURES / "SHA256SUMS").read_text("ascii").splitlines():
        digest, name = text.split("  ")
        sums[name] = digest
    one, two = by["forward_millions"]["expected"], by["forward_thousands"]["expected"]
    assert (one["forward_sha256"], one["foundation_sha256"]) == (sums[FWD_FILE], sums[FND_FILE])
    assert (two["forward_sha256"], two["foundation_sha256"]) == (
        sums[C1.THOUSANDS[0]],
        sums[C1.THOUSANDS[1]],
    )
    same = ("scale", "limits", "foundation_sha256", "forward_sha256")
    for thousands, millions in (
        ("forward_thousands", "forward_millions"),
        ("layer1_thousands", "layer1_millions"),
    ):
        assert figures(by[thousands], *same) == figures(by[millions], *same)
        got, want = by[thousands]["expected"]["limits"], by[millions]["expected"]["limits"]
        assert got[1] == SCALE_TEXT.format(currency="USD") and got[:1] + got[2:] == want
    assert [c[0] for c in by["layer1_thousands"]["expected"]["cases"]] == ["reference"]
    assert by["layer1_thousands"]["expected"]["forward_sha256"] is None
    for name in ("r31_no_layer1_section", "r31_foundation_block_differs"):
        assert figures(by[name], "foundation_sha256") == figures(
            by["forward_millions"], "foundation_sha256"
        )
        assert by[name]["expected"]["foundation_sha256"] != one["foundation_sha256"]
    assert any(
        isinstance(v, A.Gap) and v.code == "NEGATIVE_CASH"
        for _, years in by["layer1_negative_cash"]["expected"]["cases"]
        for year in years
        for v in year.values()
    )
    hand_checks(by)
    return done


def first_year(item: dict[str, Any]) -> dict[str, Any]:
    return {f: A.flatten(v) for f, v in item["expected"]["cases"][0][1][0].items()}


def hand_checks(by: dict[str, Any]) -> None:
    """Rows worked by hand (see the report); each figure is written, not computed."""
    one = by["forward_millions"]["expected"]
    assert one["limits"][2:] == [
        B7.FACILITY_LIMIT,
        (
            "Debt of 160 is not in a stated facility; it bears interest at the analyst's assumed "
            "rate and is not repaid in this forecast."
        ),
        (
            "Term loan B matures in FY2027 and is assumed refinanced; no repayment at maturity is "
            "modelled."
        ),
    ]
    assert first_year(by["forward_millions"])["interest"] == "87.8225"
    assert one["facilities"]["unallocated"] == "160"
    want = {
        "revenue": "1506.96",
        "ebitda": "331.5312",
        "interest": "64",
        "closing_debt": "1220",
        "closing_cash": "377.42568",
        "net_debt": "842.57432",
    }
    year = first_year(by["layer1_millions"])
    assert {k: year[k] for k in want} == want, year
    small = by["unallocated_below_one"]["expected"]
    assert small["facilities"]["unallocated"] == "0.7525"
    assert small["limits"][3].startswith("Debt of 0.7525 is not in a stated facility")
    floating = F("799.2475") * (F("0.0415") + F("0.0325"))
    interest = floating + F(450) * F("0.07125") + F("0.7525") * F("0.0525")
    assert first_year(by["unallocated_below_one"])["interest"] == A.plain(interest)


ABOUT = (
    "Step 1B PR 7c2 answer key, written by the answer-key author. Every figure, name and text is "
    "invented. Computed with fractions.Fraction and hashlib by make_pr7c2.py (not the code under "
    "test), which loads the 7c1, 7a2 and 7b oracles by path. A row is the 7c1 row shape: `source` "
    "(CP-2G or CP-1), a `foundation` document and a `forward` document (null on layer 1), each a "
    "fixture `file` with text `edits` and block `ops` (see pr7c1.json). `expected` lists both "
    "hashes, currency, scale, spans, stress basis, cases (each year a list in the order of "
    "`fields`; an amount is amount_text, a missing value is {missing: ...}), the facility detail "
    "and every limit in order. Implementers do not edit this file."
)


def render() -> str:
    parts = []
    for item in checked():
        exp = item["expected"]
        text = line({k: v for k, v in item.items() if k != "expected"})
        cases = [
            line({"name": n, "years": [[A.show(y[f]) for f in FIELDS] for y in ys]})
            for n, ys in exp["cases"]
        ]
        head = line({k: v for k, v in exp.items() if k != "cases"})
        parts.append(
            "  "
            + text[:-1]
            + ', "expected": '
            + head[:-1]
            + ', "cases": ['
            + ", ".join(cases)
            + "]}}"
        )
    kinds = Counter(r["kind"] for r in rows())
    return (
        f'{{\n "about": {line(ABOUT)},\n "fields": {line(FIELDS)},\n "reasons": {line(REASONS)},\n'
        f' "limit": {line(LIMIT)},\n "layer1_limit": {line(LAYER1)},\n'
        f' "scale_limit": {line(SCALE_TEXT)},\n "kinds": {line(dict(kinds))},\n "rows": [\n'
        + ",\n".join(parts)
        + "\n ]\n}\n"
    )


if __name__ == "__main__":
    Path(__file__).with_name("pr7c2.json").write_text(render(), "utf-8")
