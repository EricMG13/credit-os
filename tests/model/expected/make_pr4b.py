"""Answer key for 1B PR 4b (schema, scale to millions, the repayment bound), by the controller.

Every figure, name and text is invented. A row in ROWS holds inputs only: its label, the ops that
build its document from `valid` and, for a row the schema step refuses, the issues pydantic
reports there (location and message: the rule the row tests, written out because nothing
independent of pydantic produces its wording; the texts were checked against pydantic 2.13.4 by
the controller's probe). Every other expected value is worked below from the row's document and
never copied from a row: whether the row is accepted or refused; a refusal's kind, subject and
message (the scale rule, the slot walk and its pattern, the repayment running sums in
fractions.Fraction); an accepted row's parsed form (`becomes`) and its stated map. Shorthands in
a row: {"@driver": values} is a driver with the invented category and rationale,
{"@facility": name, ...} a named facility with changes, "@name" a named value. `render()`
returns the key's text; run this file to write `pr4b.json` next to it.
"""

import copy
import json
import re
from collections.abc import Iterator
from fractions import Fraction
from pathlib import Path
from typing import Any

Doc = dict[str, Any]
Refusal = list[str]
SUBJECT = "forecast inputs"
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
OPERAND_FIELDS = ["amount", "reason", "row", "period", "column"]
DRIVERS = [
    "revenue_growth",
    "ebitda_margin",
    "capex_pct_revenue",
    "tax_wc_pct_revenue",
    "interest_rate",
    "dividends",
    "debt_repayment",
]
CATEGORIES = [
    "Documentary Fact",
    "Management Language",
    "Analyst Interpretation",
    "Insufficient Information",
]
GROWTH = r"^-?(0|1|0\.[0-9]{1,4}|1\.0{1,4})$"
SHARE = r"^(0|1|0\.[0-9]{1,4}|1\.0{1,4})$"
AMOUNT = r"^[0-9]{1,6}(\.[0-9]{1,4})?$"
SIGNED = r"^-?[0-9]{1,6}(\.[0-9]{1,4})?$"
CURRENCY = r"^[A-Z]{3}$"
IN_THOUSANDS = re.compile(r"-?[0-9]{1,9}(\.[0-9])?")
CODE = re.compile(r"[A-Z]{3}")

MESSAGES = {
    "schema": "forecast inputs: {issues}",
    "schema_many": "forecast inputs: {n} problems; first: {issues}",
    "scale": "`scale` must be 1 (CP-1 prints {code}millions) or 1000 ({code}thousands)",
    "thousands": "{slot} {text} is not an amount in thousands as CP-1 prints it (scale 1000): "
    "at most nine digits and one decimal place, no separators",
    "repayment": "{case} case: debt_repayment through forecast year {year} totals {total}, "
    "more than base debt {debt}",
}
TEXTS = {
    "one_of": "an operand states an amount or a reason, never both or neither",
    "both_headers": "an operand names the `period` header or the `column` header, not both",
    "unnamed": "an operand with an amount names its `row` and its `period` or `column`",
    "blank_reason": "an operand's reason must not be blank",
    "empty_case": "a case names at least one driver; write null for no case",
    "bad_date": "{field} {text} is not a calendar date",
    "backwards": "a year starts after it ends",
    "base_keys": "base must state exactly " + ", ".join(OPERANDS),
    "consecutive": "years must be three consecutive fiscal years",
    "contiguous": "each year must start the day after the previous one ends",
    "unique": "facility names must be unique",
}
LIB = {
    "missing": "Field required",
    "extra": "Extra inputs are not permitted",
    "string": "Input should be a valid string",
    "int": "Input should be a valid integer",
    "year_low": "Input should be greater than or equal to 1000",
    "version": "Input should be 'cpos-forecast-inputs/1'",
    "category": "Input should be 'Documentary Fact', 'Management Language', "
    "'Analyst Interpretation' or 'Insufficient Information'",
    "four": "Tuple should have at most 3 items after validation, not 4",
    "none": "Tuple should have at least 1 item after validation, not 0",
    "forty_one": "Tuple should have at most 40 items after validation, not 41",
    "model": "Input should be a valid dictionary or instance of Operand",
    "growth": f"String should match pattern '{GROWTH}'",
    "share": f"String should match pattern '{SHARE}'",
    "amount": f"String should match pattern '{AMOUNT}'",
    "signed": f"String should match pattern '{SIGNED}'",
    "currency": f"String should match pattern '{CURRENCY}'",
}


def op(
    amount: str | None,
    row: str | None = None,
    period: str | None = None,
    column: str | None = None,
    reason: str | None = None,
) -> Doc:
    return {"amount": amount, "reason": reason, "row": row, "period": period, "column": column}


def driver(values: list[str], category: str = "Analyst Interpretation") -> Doc:
    return {
        "values": values,
        "category": category,
        "rationale": "Invented for the test.",
        "limitation": None,
    }


VALID: Doc = {
    "schema_version": "cpos-forecast-inputs/1",
    "base": {
        "revenue": op("1840.5", "Revenue", "FY2025"),
        "ebitda": op("412.3", "EBITDA", "FY2025"),
        "interest": op("61.2", "Cash interest paid", "FY2025"),
        "taxes": op("38.4", "Cash taxes paid", "FY2025"),
        "wc": op(None, reason="The financial foundation prints no single working capital figure."),
        "capex": op("96", "Capital expenditure", "FY2025"),
        "fcf": op("-14.7", "Free cash flow", "FY2025"),
        "debt": op("905", "FY2025", column="Total debt"),
        "cash": op("132.6", "FY2025", column="Cash"),
        "undrawn": op("150", "FY2025", column="Undrawn facility"),
    },
    "base_drivers": {
        "revenue_growth": driver(["0.04", "0.035", "-0.01"]),
        "ebitda_margin": driver(["0.224", "0.226", "0.23"]),
        "capex_pct_revenue": driver(["0.05", "0.05", "0.048"]),
        "tax_wc_pct_revenue": driver(["0.03", "0.03", "0.03"]),
        "interest_rate": driver(["0.0675", "0.0675", "0.07"], "Documentary Fact"),
        "dividends": driver(["20", "20", "25.5"], "Management Language"),
        "debt_repayment": driver(["45", "45", "60"]),
    },
    "downside_shock": {"ebitda_decline": "0.15", "rate_increase": "0.1"},
    "upside_drivers": None,
    "downside_drivers": None,
    "years": [
        {"year": 2026, "start": "2026-01-01", "end": "2026-12-31"},
        {"year": 2027, "start": "2027-01-01", "end": "2027-12-31"},
        {"year": 2028, "start": "2028-01-01", "end": "2028-12-31"},
    ],
    "facilities": None,
    "scale": 1,
    "currency": "EUR",
    "scope_limits": ["Invented block for tests; no issuer."],
}
FIXED: Doc = {
    "name": "Term loan A",
    "balance": "400",
    "fixed_rate_pct": "6.5",
    "spread_pct": None,
    "floor_pct": None,
    "reference_rate": None,
    "annual_amortisation": "20.0005",
    "maturity": "2030-06-30",
}
FLOATING: Doc = {
    "name": "Revolving facility",
    "balance": "55.25",
    "fixed_rate_pct": None,
    "spread_pct": "3.25",
    "floor_pct": "1",
    "reference_rate": ["0.03", "0.0275", "0.025"],
    "annual_amortisation": None,
    "maturity": None,
}


def plain(value: Fraction) -> str:
    """A terminating fraction as plain digits, no trailing zeros."""
    sign = "-" if value < 0 else ""
    value = abs(value)
    for places in range(12):
        scaled = value * 10**places
        if scaled.denominator == 1:
            digits = str(scaled.numerator).rjust(places + 1, "0")
            whole, part = (digits[:-places], digits[-places:]) if places else (digits, "")
            return sign + whole + ("." + part if part else "")
    raise ValueError(value)


# The valid block's amounts stated in thousands (the row word "thousands").
THOUSANDS: list[list[Any]] = [
    [["base", key, "amount"], plain(Fraction(operand["amount"]) * 1000)]
    for key, operand in VALID["base"].items()
    if operand["amount"] is not None
] + [
    [["base_drivers", name, "values"], [plain(Fraction(v) * 1000) for v in spec["values"]]]
    for name, spec in VALID["base_drivers"].items()
    if name in ("dividends", "debt_repayment")
]
NAMED: dict[str, Any] = {
    "FIXED": FIXED,
    "FLOATING": FLOATING,
    "k81": "k" * 81,
    "z81": "z" * 81,
    "nines81": "9" * 81,
}


def built(value: Any) -> Any:
    """A row's inputs with its shorthands written out."""
    if isinstance(value, list):
        return [built(item) for item in value]
    if isinstance(value, dict):
        if "@driver" in value:
            return driver(value["@driver"])
        if "@facility" in value:
            changes = {k: v for k, v in value.items() if k != "@facility"}
            return {**NAMED[value["@facility"]], **changes}
        return {k: built(v) for k, v in value.items()}
    if isinstance(value, str) and value.startswith("@"):
        return NAMED[value[1:]]
    return value


def applied(document: Doc, ops: list[Any]) -> Doc:
    """`ops` applied in order to a deep copy: [path, value] sets, [path] deletes."""
    out = copy.deepcopy(document)
    for item in [x for entry in ops for x in (THOUSANDS if entry == "thousands" else [entry])]:
        path, holder = item[0], out
        for part in path[:-1]:
            holder = holder[part]
        if len(item) == 1:
            del holder[path[-1]]
        else:
            holder[path[-1]] = copy.deepcopy(item[1])
    return out


def echo(text: str) -> str:
    """Text as a message prints it: at most 80 characters, then an ellipsis (plan ruling 8)."""
    return text if len(text) <= 80 else text[:80] + "…"


def slots(doc: Doc) -> Iterator[tuple[str, Any, Any]]:
    """Every amount slot as (name, holder, key), in the order the brief gives."""
    base = doc.get("base")
    for key, operand in base.items() if type(base) is dict else ():
        if type(operand) is dict and "amount" in operand:
            yield f"base {echo(key)}", operand, "amount"
    for group in ("base_drivers", "upside_drivers", "downside_drivers"):
        drivers = doc.get(group)
        for name in ("dividends", "debt_repayment"):
            stated = drivers.get(name) if type(drivers) is dict else None
            values = stated.get("values") if type(stated) is dict else None
            for index in range(len(values)) if type(values) is list else ():
                yield f"{group} {name} year {index + 1}", values, index
    facilities = doc.get("facilities")
    for number, facility in enumerate(facilities if type(facilities) is list else (), 1):
        for field in ("balance", "annual_amortisation"):
            if type(facility) is dict and field in facility:
                yield f"facility {number} {field}", facility, field


def scale_step(doc: Doc) -> tuple[Refusal | None, dict[str, str]]:
    """The scale rule; at 1000 every amount slot divided by 1,000 in place, its text kept."""
    if "scale" not in doc:
        return None, {}
    scale, currency = doc["scale"], doc.get("currency")
    if type(scale) is not int or scale not in (1, 1000):
        code = currency + " " if type(currency) is str and CODE.fullmatch(currency) else ""
        return ["scale", "scale", MESSAGES["scale"].format(code=code)], {}
    stated: dict[str, str] = {}
    for name, holder, key in slots(doc) if scale == 1000 else ():
        text = holder[key]
        if type(text) is not str:
            continue
        minus_zero = text.startswith("-") and Fraction(text) == 0
        if not IN_THOUSANDS.fullmatch(text) or (minus_zero and not name.startswith("base ")):
            return ["scale", name, MESSAGES["thousands"].format(slot=name, text=echo(text))], {}
        holder[key] = plain(Fraction(text) / 1000)
        stated[name] = text
    return None, stated


def schema(issues: list[list[Any]]) -> str:
    """A [loc parts, message] list as the schema refusal words it."""
    texts = []
    for loc, said in issues:
        where = ".".join(echo(p) if isinstance(p, str) else str(p) for p in loc) or "(root)"
        message = LIB.get(said) or ("Value error, " + TEXTS[said] if said in TEXTS else said)
        texts.append(f"{where}: {message}")
    if len(texts) <= 3:
        return MESSAGES["schema"].format(issues="; ".join(texts))
    return MESSAGES["schema_many"].format(n=len(texts), issues="; ".join(texts[:3]))


def parsed(doc: Doc) -> Doc:
    """A schema-valid document as the parsed inputs dump it: left-out keys read as null."""
    out = copy.deepcopy(doc)
    for key in ("upside_drivers", "downside_drivers", "facilities"):
        out.setdefault(key, None)
    out["base"] = {k: {f: v.get(f) for f in OPERAND_FIELDS} for k, v in out["base"].items()}
    for key in ("upside_drivers", "downside_drivers"):
        if out[key] is not None:
            out[key] = {name: out[key].get(name) for name in DRIVERS}
    return out


def repayment(doc: Doc) -> Refusal | None:
    """Ruling R17: the first year a case's running repayment exceeds base debt."""
    debt = doc["base"]["debt"]["amount"]
    if debt is None:
        return None
    cases = [("base", doc["base_drivers"])]
    cases += [(case, doc[f"{case}_drivers"] or {}) for case in ("upside", "downside")]
    for case, drivers in cases:
        running = Fraction(0)
        for year, text in enumerate((drivers.get("debt_repayment") or {}).get("values", []), 1):
            running += Fraction(text)
            if running > Fraction(debt):
                total, limit = plain(running), plain(Fraction(debt))
                message = MESSAGES["repayment"].format(
                    case=case, year=year, total=total, debt=limit
                )
                return ["repayment", "debt_repayment", message]
    return None


def lookup(doc: Any, path: list[Any]) -> tuple[bool, Any]:
    for part in path:
        if (type(doc) is dict and part in doc) or (type(doc) is list and part < len(doc)):
            doc = doc[part]
        else:
            return False, None
    return True, doc


def becomes(ops: list[Any], inputs: Doc) -> list[Any]:
    """The ops that turn `valid` into the parsed inputs, at the row's own paths (last use)."""
    paths: list[list[Any]] = []
    for item in [x for entry in ops for x in (THOUSANDS if entry == "thousands" else [entry])]:
        paths = [p for p in paths if p != item[0]] + [item[0]]
    out: list[Any] = []
    for path in paths:
        (found, value), (known, before) = lookup(inputs, path), lookup(VALID, path)
        if found and (not known or value != before):
            out.append([path, value])
        elif known and not found:
            out.append([path])
    return out


def worked(row: Doc) -> tuple[str, Doc]:
    """A row's expected outcome, worked from its document."""
    ops = built(row["ops"])
    head = {"label": row["label"], "ops": ops}
    document = applied(VALID, ops)
    refusal, stated = scale_step(document)
    if refusal is None and "issues" in row:
        refusal = ["schema", SUBJECT, schema(built(row["issues"]))]
    inputs = parsed(document) if refusal is None else {}
    refusal = refusal or repayment(inputs)
    if refusal is not None:
        return "refused", head | dict(zip(("kind", "subject", "message"), refusal, strict=True))
    return "accepted", head | {"becomes": becomes(ops, inputs), "stated": stated}


ABOUT = (
    "1B PR 4b answer key (controller). Every figure, name and text is invented. A row's "
    "`ops` are applied in order to a deep copy of `valid`: [path, value] sets, [path] deletes, and "
    "the word thousands stands for the `thousands` list (the valid block's amounts stated in "
    "thousands). `accepted`: the parsed inputs dumped with model_dump(mode='json') equal `valid` "
    "with the row's `becomes` applied, and the "
    "stated-thousands map equals `stated`. `refused`: ForecastRefused with the kind, subject and "
    "message. Worked by pr4b/make_key.py (fractions.Fraction; pydantic's message texts written "
    "out)."
)
ROWS = r"""
{"label": "the valid block", "ops": []}
{"label": "case keys and facilities left out read as null", "ops": [[["upside_drivers"]], [["downside_drivers"]], [["facilities"]]]}
{"label": "operand location keys left out of a missing operand", "ops": [[["base", "wc"], {"amount": null, "reason": "Not printed."}]]}
{"label": "no shock", "ops": [[["downside_shock"], null]]}
{"label": "a downside case of one driver", "ops": [[["downside_drivers"], {"ebitda_margin": {"@driver": ["0.2", "0.19", "0.18"]}}]]}
{"label": "two facilities, one fixed and one floating", "ops": [[["facilities"], ["@FIXED", "@FLOATING"]]]}
{"label": "pattern edges", "ops": [[["base_drivers", "revenue_growth", "values"], ["-1", "1.0000", "-0.9999"]], [["base_drivers", "ebitda_margin", "values"], ["0", "1", "0.0001"]], [["base_drivers", "dividends", "values"], ["0", "999999.9999", "0.0001"]], [["base", "fcf", "amount"], "-999999.9999"], [["downside_shock"], {"ebitda_decline": "1", "rate_increase": "0"}], [["currency"], "USD"], [["scope_limits"], []]]}
{"label": "fiscal years that are not calendar years", "ops": [[["years"], [{"year": 2026, "start": "2025-07-01", "end": "2026-06-30"}, {"year": 2027, "start": "2026-07-01", "end": "2027-06-30"}, {"year": 2028, "start": "2027-07-01", "end": "2028-06-30"}]]]}
{"label": "scale 1000: the valid block in thousands", "ops": [[["scale"], 1000], "thousands"]}
{"label": "scale 1000: facilities, a case, the widest amount, a base minus zero, nulls kept", "ops": [[["scale"], 1000], "thousands", [["facilities"], [{"@facility": "FIXED", "balance": "400000", "annual_amortisation": "20000.5"}, {"@facility": "FLOATING", "balance": "55250"}]], [["upside_drivers"], {"dividends": {"@driver": ["0", "500", "0.1"]}, "debt_repayment": {"@driver": ["1500.0", "0", "0"]}}], [["base", "revenue", "amount"], "999999999.9"], [["base", "fcf", "amount"], "-0"]]}
{"label": "repayment equal to base debt by year 3", "ops": [[["base_drivers", "debt_repayment", "values"], ["400", "400", "105"]]]}
{"label": "repayment equal to base debt in year 1", "ops": [[["base_drivers", "debt_repayment", "values"], ["905", "0", "0"]]]}
{"label": "base debt missing: the bound does not apply", "ops": [[["base", "debt"], {"amount": null, "reason": "Debt is not printed.", "row": null, "period": null, "column": null}], [["base_drivers", "debt_repayment", "values"], ["999999", "999999", "999999"]]]}
{"label": "a case that keeps base repayment is not checked twice", "ops": [[["upside_drivers"], {"dividends": {"@driver": ["0", "0", "0"]}}]]}
{"label": "scale 2", "ops": [[["scale"], 2]]}
{"label": "scale 0", "ops": [[["scale"], 0]]}
{"label": "scale -1000", "ops": [[["scale"], -1000]]}
{"label": "scale as text", "ops": [[["scale"], "1000"]]}
{"label": "scale true", "ops": [[["scale"], true]]}
{"label": "scale null", "ops": [[["scale"], null]]}
{"label": "scale as a list", "ops": [[["scale"], [1]]]}
{"label": "scale 2, currency not a code", "ops": [[["scale"], 2], [["currency"], "euro"]]}
{"label": "scale 2, currency missing", "ops": [[["scale"], 2], [["currency"]]]}
{"label": "scale 2, currency not text", "ops": [[["scale"], 2], [["currency"], 7]]}
{"label": "thousands with separators", "ops": [[["scale"], 1000], "thousands", [["base", "revenue", "amount"], "1,840,500"]]}
{"label": "thousands with two decimal places", "ops": [[["scale"], 1000], "thousands", [["base", "debt", "amount"], "905000.25"]]}
{"label": "thousands of ten digits", "ops": [[["scale"], 1000], "thousands", [["base", "cash", "amount"], "1234567890"]]}
{"label": "thousands with a trailing newline", "ops": [[["scale"], 1000], "thousands", [["base", "cash", "amount"], "132600\n"]]}
{"label": "thousands in non-ASCII digits", "ops": [[["scale"], 1000], "thousands", [["base", "cash", "amount"], "\u0661\u0662\u0663"]]}
{"label": "thousands with an exponent", "ops": [[["scale"], 1000], "thousands", [["base", "cash", "amount"], "1e5"]]}
{"label": "an empty amount", "ops": [[["scale"], 1000], "thousands", [["base", "cash", "amount"], ""]]}
{"label": "a long amount is cut to 80 characters", "ops": [[["scale"], 1000], "thousands", [["base", "cash", "amount"], "@nines81"]]}
{"label": "minus zero in an amount driver", "ops": [[["scale"], 1000], "thousands", [["base_drivers", "dividends", "values"], ["20000", "-0", "25500"]]]}
{"label": "a negative facility balance", "ops": [[["scale"], 1000], "thousands", [["facilities"], [{"@facility": "FIXED", "balance": "-0.0"}]]]}
{"label": "currency left out", "ops": [[["currency"]]], "issues": [[["currency"], "missing"]]}
{"label": "scale left out", "ops": [[["scale"]]], "issues": [[["scale"], "missing"]]}
{"label": "currency in lower case", "ops": [[["currency"], "eur"]], "issues": [[["currency"], "currency"]]}
{"label": "currency with a trailing newline", "ops": [[["currency"], "EUR\n"]], "issues": [[["currency"], "currency"]]}
{"label": "another schema version", "ops": [[["schema_version"], "cpos-forecast-inputs/2"]], "issues": [[["schema_version"], "version"]]}
{"label": "an unknown key", "ops": [[["notes"], "x"]], "issues": [[["notes"], "extra"]]}
{"label": "an unknown key of 81 characters is cut", "ops": [[["@k81"], "x"]], "issues": [[["@k81"], "extra"]]}
{"label": "a base operand left out", "ops": [[["base", "undrawn"]]], "issues": [[[], "base_keys"]]}
{"label": "an extra base operand", "ops": [[["base", "equity"], {"amount": "5", "reason": null, "row": "Equity", "period": "FY2025", "column": null}]], "issues": [[[], "base_keys"]]}
{"label": "an operand that is not an object", "ops": [[["base", "debt"], "905"]], "issues": [[["base", "debt"], "model"]]}
{"label": "an empty operand under a long key", "ops": [[["base", "@z81"], {}]], "issues": [[["base", "@z81", "amount"], "missing"], [["base", "@z81", "reason"], "missing"]]}
{"label": "an operand with an amount and a reason", "ops": [[["base", "debt", "reason"], "why"]], "issues": [[["base", "debt"], "one_of"]]}
{"label": "an operand with neither", "ops": [[["base", "debt", "amount"], null]], "issues": [[["base", "debt"], "one_of"]]}
{"label": "a blank reason", "ops": [[["base", "wc", "reason"], " \t"]], "issues": [[["base", "wc"], "blank_reason"]]}
{"label": "an amount with no row", "ops": [[["base", "revenue", "row"], null]], "issues": [[["base", "revenue"], "unnamed"]]}
{"label": "an amount with no period and no column", "ops": [[["base", "revenue", "period"], null]], "issues": [[["base", "revenue"], "unnamed"]]}
{"label": "an amount with a period and a column", "ops": [[["base", "revenue", "column"], "Revenue"]], "issues": [[["base", "revenue"], "both_headers"]]}
{"label": "an empty row name", "ops": [[["base", "revenue", "row"], ""]], "issues": [[["base", "revenue", "row"], "String should have at least 1 character"]]}
{"label": "an amount as a number", "ops": [[["base", "revenue", "amount"], 1840]], "issues": [[["base", "revenue", "amount"], "string"]]}
{"label": "an amount of seven digits", "ops": [[["base", "revenue", "amount"], "1234567"]], "issues": [[["base", "revenue", "amount"], "signed"]]}
{"label": "an amount in non-ASCII digits", "ops": [[["base", "revenue", "amount"], "\u0661\u0662"]], "issues": [[["base", "revenue", "amount"], "signed"]]}
{"label": "growth above one", "ops": [[["base_drivers", "revenue_growth", "values"], ["0.04", "1.5", "0"]]], "issues": [[["base_drivers", "revenue_growth", "values", 1], "growth"]]}
{"label": "a negative share", "ops": [[["base_drivers", "ebitda_margin", "values"], ["-0.1", "0.2", "0.2"]]], "issues": [[["base_drivers", "ebitda_margin", "values", 0], "share"]]}
{"label": "a negative repayment driver (a drawing is not written here)", "ops": [[["base_drivers", "debt_repayment", "values"], ["45", "-5", "60"]]], "issues": [[["base_drivers", "debt_repayment", "values", 1], "amount"]]}
{"label": "a driver of two years", "ops": [[["base_drivers", "dividends", "values"], ["20", "20"]]], "issues": [[["base_drivers", "dividends", "values", 2], "missing"]]}
{"label": "a driver of four years", "ops": [[["base_drivers", "dividends", "values"], ["1", "2", "3", "4"]]], "issues": [[["base_drivers", "dividends", "values"], "four"]]}
{"label": "a null in a driver that is not all null", "ops": [[["base_drivers", "dividends", "values"], ["20", null, "25"]]], "issues": [[["base_drivers", "dividends", "values", 1], "string"]]}
{"label": "a category outside the four", "ops": [[["base_drivers", "dividends", "category"], "analyst_judgment"]], "issues": [[["base_drivers", "dividends", "category"], "category"]]}
{"label": "a driver left out", "ops": [[["base_drivers", "interest_rate"]]], "issues": [[["base_drivers", "interest_rate"], "missing"]]}
{"label": "the shock key left out", "ops": [[["downside_shock"]]], "issues": [[["downside_shock"], "missing"]]}
{"label": "a shock above one", "ops": [[["downside_shock", "rate_increase"], "1.5"]], "issues": [[["downside_shock", "rate_increase"], "share"]]}
{"label": "a case naming no driver", "ops": [[["upside_drivers"], {}]], "issues": [[["upside_drivers"], "empty_case"]]}
{"label": "a case with an unknown driver", "ops": [[["downside_drivers"], {"margin": {"@driver": ["0", "0", "0"]}}]], "issues": [[["downside_drivers", "margin"], "extra"]]}
{"label": "years not consecutive", "ops": [[["years", 2, "year"], 2029]], "issues": [[[], "consecutive"]]}
{"label": "a gap between years", "ops": [[["years", 1, "start"], "2027-01-02"]], "issues": [[[], "contiguous"]]}
{"label": "a year that starts after it ends", "ops": [[["years", 0, "start"], "2027-01-01"]], "issues": [[["years", 0], "backwards"]]}
{"label": "a start that is not a calendar date", "ops": [[["years", 0, "start"], "2026-02-30"]], "issues": [[["years", 0], "Value error, start 2026-02-30 is not a calendar date"]]}
{"label": "an end that is not a calendar date", "ops": [[["years", 2, "end"], "2028-13-01"]], "issues": [[["years", 2], "Value error, end 2028-13-01 is not a calendar date"]]}
{"label": "a date not written as a date", "ops": [[["years", 0, "start"], "1 January 2026"]], "issues": [[["years", 0, "start"], "String should match pattern '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'"]]}
{"label": "a year as text", "ops": [[["years", 0, "year"], "2026"]], "issues": [[["years", 0, "year"], "int"]]}
{"label": "a year as true", "ops": [[["years", 0, "year"], true]], "issues": [[["years", 0, "year"], "int"]]}
{"label": "a year of three digits", "ops": [[["years", 0, "year"], 999]], "issues": [[["years", 0, "year"], "year_low"]]}
{"label": "two years", "ops": [[["years"], [{"year": 2026, "start": "2026-01-01", "end": "2026-12-31"}, {"year": 2027, "start": "2027-01-01", "end": "2027-12-31"}]]], "issues": [[["years", 2], "missing"]]}
{"label": "an empty facility list", "ops": [[["facilities"], []]], "issues": [[["facilities"], "none"]]}
{"label": "facility names that differ only in case", "ops": [[["facilities"], ["@FIXED", {"@facility": "FLOATING", "name": "TERM LOAN A"}]]], "issues": [[[], "unique"]]}
{"label": "a facility with both rate forms", "ops": [[["facilities"], [{"@facility": "FIXED", "spread_pct": "2"}]]], "issues": [[["facilities", 0], "Value error, a facility states a fixed rate or a floating one, not both"]]}
{"label": "scope limits left out", "ops": [[["scope_limits"]]], "issues": [[["scope_limits"], "missing"]]}
{"label": "a scope limit that is not text", "ops": [[["scope_limits"], ["a", 5]]], "issues": [[["scope_limits", 1], "string"]]}
{"label": "three problems are all named", "ops": [[["currency"]], [["notes"], "x"], [["base_drivers", "dividends", "category"], "x"]], "issues": [[["base_drivers", "dividends", "category"], "category"], [["currency"], "missing"], [["notes"], "extra"]]}
{"label": "four problems: the count and the first three", "ops": [[["currency"]], [["notes"], "x"], [["base_drivers", "dividends", "category"], "x"], [["schema_version"], "v"]], "issues": [[["schema_version"], "version"], [["base_drivers", "dividends", "category"], "category"], [["currency"], "missing"], [["notes"], "extra"]]}
{"label": "over in year 1", "ops": [[["base_drivers", "debt_repayment", "values"], ["905.0001", "0", "0"]]]}
{"label": "over only by year 3", "ops": [[["base_drivers", "debt_repayment", "values"], ["400", "400", "106"]]]}
{"label": "over in year 2, not repaired by a later zero", "ops": [[["base_drivers", "debt_repayment", "values"], ["900", "5.5", "0"]]]}
{"label": "the downside case over, base under", "ops": [[["downside_drivers"], {"debt_repayment": {"@driver": ["300", "700", "0"]}}]]}
{"label": "the upside case over, base under", "ops": [[["upside_drivers"], {"debt_repayment": {"@driver": ["0", "0", "906"]}}]]}
{"label": "base is reported before a case", "ops": [[["base_drivers", "debt_repayment", "values"], ["906", "0", "0"]], [["upside_drivers"], {"debt_repayment": {"@driver": ["907", "0", "0"]}}]]}
{"label": "zero base debt and any repayment", "ops": [[["base", "debt", "amount"], "0"], [["base_drivers", "debt_repayment", "values"], ["0", "0.0001", "0"]]]}
{"label": "negative base debt: zero repayments already exceed it", "ops": [[["base", "debt", "amount"], "-5"], [["base_drivers", "debt_repayment", "values"], ["0", "0", "0"]]]}
{"label": "at scale 1000 the bound is tested and worded in millions", "ops": [[["scale"], 1000], "thousands", [["base_drivers", "debt_repayment", "values"], ["905000", "0", "0.1"]]]}
{"label": "with facilities stated the driver is still bounded", "ops": [[["facilities"], ["@FIXED"]], [["base_drivers", "debt_repayment", "values"], ["906", "0", "0"]]]}
"""


def render() -> str:
    key: Doc = {
        "about": ABOUT,
        "messages": MESSAGES,
        "texts": TEXTS,
        "operands": OPERANDS,
        "categories": CATEGORIES,
        "valid": VALID,
        "thousands": THOUSANDS,
        "forty_one": schema([[["facilities"], "forty_one"]]),
        "accepted": [],
        "refused": [],
    }
    for line in ROWS.strip().splitlines():
        bucket, entry = worked(json.loads(line))
        key[bucket].append(entry)
    labels = [row["label"] for row in key["accepted"] + key["refused"]]
    assert len(labels) == len(set(labels)) == 94 and len(key["accepted"]) == 14
    assert THOUSANDS[0] == [["base", "revenue", "amount"], "1840500"]
    assert THOUSANDS[-1][1] == ["45000", "45000", "60000"]
    lines = ["{"]
    for name, value in key.items():
        if name in ("accepted", "refused"):
            rows = ",\n".join("  " + json.dumps(row, ensure_ascii=True) for row in value)
            lines.append(f' "{name}": [\n{rows}\n ],')
        else:
            lines.append(f' "{name}": {json.dumps(value, ensure_ascii=True)},')
    lines[-1] = lines[-1].rstrip(",")
    return "\n".join(lines + ["}"]) + "\n"


if __name__ == "__main__":
    Path(__file__).with_name("pr4b.json").write_text(render(), "utf-8")
