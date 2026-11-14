"""The forecast inputs schema, scale to millions and the repayment bound."""

import contextlib
import copy
import decimal
import json
import re
import typing
from collections.abc import Iterator
from decimal import Context
from fractions import Fraction
from pathlib import Path
from typing import Any

import pydantic
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.handoff.document import parse
from credit_os.model import inputs
from credit_os.model.inputs import parse_inputs, read_inputs
from credit_os.model.refusals import ForecastDeclined, ForecastRefused, RefusalKind
from credit_os.model.value import Missing, MissingCode, Value

HERE = Path(__file__).parent / "expected"
KEY = json.loads((HERE / "pr4b.json").read_text("utf-8"))
P4A = json.loads((HERE / "pr4a.json").read_text("utf-8"))["handoff"]
VALID = KEY["valid"]


def build(ops: list[Any]) -> dict[str, Any]:
    document: dict[str, Any] = copy.deepcopy(VALID)
    for op in ops:
        for path, *value in KEY["thousands"] if op == "thousands" else [op]:
            holder = document
            for step in path[:-1]:
                holder = holder[step]
            if value:
                holder[path[-1]] = value[0]
            else:
                del holder[path[-1]]
    return document


def outcome(document: dict[str, Any]) -> tuple[Any, ...]:
    try:
        got, stated = parse_inputs(document)
    except ForecastRefused as error:
        return (error.kind, error.subject, error.message)
    return (got.model_dump(mode="json"), list(stated.items()))


def refusal(document: Any) -> ForecastRefused:
    with pytest.raises(ForecastRefused) as caught:
        parse_inputs(document)
    return caught.value


def issues_of(document: dict[str, Any]) -> str:
    error = refusal(document)
    assert (error.kind, error.subject) == (RefusalKind.SCHEMA, "forecast inputs")
    return error.message.removeprefix("forecast inputs: ")


ACCEPTED = KEY["accepted"]
REFUSED = KEY["refused"]


def label(row: dict[str, Any]) -> str:
    return str(row["label"])


@pytest.mark.parametrize("row", ACCEPTED, ids=label)
@pytest.mark.parametrize("through_json", [False, True])
def test_accepted(row: dict[str, Any], through_json: bool) -> None:
    document = build(row["ops"])
    if through_json:
        document = json.loads(json.dumps(document))
    before = copy.deepcopy(document)
    got, stated = parse_inputs(document)
    assert document == before
    assert got.model_dump(mode="json") == build(row["becomes"])
    assert stated == row["stated"]
    assert list(stated) == list(row["stated"])


@pytest.mark.parametrize("row", REFUSED, ids=label)
def test_refused(row: dict[str, Any]) -> None:
    error = refusal(build(row["ops"]))
    got = (error.kind.value, error.subject, error.message)
    assert got == (row["kind"], row["subject"], row["message"])


def test_key_constants() -> None:
    assert list(inputs.OPERANDS) == KEY["operands"]
    assert list(typing.get_args(inputs.Category)) == KEY["categories"]
    assert inputs.SCHEMA_VERSION == VALID["schema_version"]
    assert [kind.value for kind in RefusalKind][2:] == ["schema", "scale", "repayment"]


def one_facility(**changes: Any) -> dict[str, Any]:
    base = {"name": "T", "balance": "4", "fixed_rate_pct": "6", "spread_pct": None}
    base |= {"floor_pct": None, "reference_rate": None, "annual_amortisation": None}
    return base | {"maturity": None} | changes


def test_forty_one_facilities() -> None:
    document = build([[["facilities"], [one_facility(name=f"F{i}") for i in range(41)]]])
    assert refusal(document).message == KEY["forty_one"]


@pytest.mark.parametrize("given", [[], "{}"])
def test_not_a_document(given: Any) -> None:
    with pytest.raises(TypeError, match="^document must be a dict$"):
        parse_inputs(given)


@pytest.mark.parametrize(
    ("path", "items"),
    [
        (["base_drivers", "dividends", "values"], ["20", "20", "25"]),
        (["years"], VALID["years"]),
        (["scope_limits"], ["a", "b"]),
    ],
)
def test_sequences_are_lists_or_tuples_only(path: list[str], items: list[Any]) -> None:
    want = f"{'.'.join(path)}: Input should be a valid tuple"
    for other in ((i for i in items), {str(i) for i in items}):
        assert issues_of(build([[path, other]])) == want
    got, _ = parse_inputs(build([[path, tuple(items)]]))
    assert got.model_dump(mode="json") == build([[path, items]])


def test_returned_records_are_frozen() -> None:
    row = next(r for r in ACCEPTED if r["label"].startswith("two facilities"))
    got, _ = parse_inputs(build(row["ops"]))
    for target, name in (
        (got, "scale"),
        (got.base["revenue"], "amount"),
        (got.base_drivers, "dividends"),
        (got.base_drivers.dividends, "values"),
        (got.years[0], "year"),
        (got.downside_shock, "ebitda_decline"),
        ((got.facilities or ())[0], "name"),
    ):
        with pytest.raises(pydantic.ValidationError):
            setattr(target, name, None)


SECRET_KEYS = {"amount", "values", "rationale", "scope_limits", "limitation", "balance"}


def leaves(node: Any, secret: bool = False) -> list[str]:
    if isinstance(node, str):
        return [node] if secret and len(node) >= 4 else []
    if isinstance(node, dict):
        return [x for k, v in node.items() for x in leaves(v, secret or k in SECRET_KEYS)]
    return [x for v in node for x in leaves(v, secret)] if isinstance(node, list) else []


@pytest.mark.parametrize("row", [r for r in REFUSED if r["kind"] == "schema"], ids=label)
def test_schema_messages_hold_no_stated_text(row: dict[str, Any]) -> None:
    document = build(row["ops"])
    assert not [text for text in leaves(document) if text in row["message"]]


def handoff(document: dict[str, Any]) -> Any:
    section = f"### Forecast inputs (machine-readable)\n\n```json\n{json.dumps(document)}\n```\n"
    text = P4A["head"] + section + P4A["tail"]
    return parse(text.encode("utf-8"))


def test_read_inputs_end_to_end() -> None:
    got, stated = read_inputs(handoff(VALID))
    assert got.model_dump(mode="json") == VALID
    assert stated == {}
    declined = copy.deepcopy(VALID)
    for driver in declined["base_drivers"].values():
        driver["values"] = [None, None, None]
    with pytest.raises(ForecastDeclined):
        read_inputs(handoff(declined))
    row = REFUSED[0]
    with pytest.raises(ForecastRefused) as caught:
        read_inputs(handoff(build(row["ops"])))
    got_row = (caught.value.kind.value, caught.value.subject, caught.value.message)
    assert got_row == (row["kind"], row["subject"], row["message"])


HOSTILE = [r for r in ACCEPTED if r["ops"] and r["ops"][0] == [["scale"], 1000]] + [
    r for r in REFUSED if r["kind"] == "repayment"
]


@contextlib.contextmanager
def hostile_default() -> Iterator[None]:
    d = decimal.DefaultContext
    saved = (d.prec, d.rounding, d.Emax, d.Emin)
    d.prec, d.rounding, d.Emax, d.Emin = 3, decimal.ROUND_DOWN, 5, -5
    try:
        yield
    finally:
        d.prec, d.rounding, d.Emax, d.Emin = saved


@pytest.mark.parametrize("row", HOSTILE, ids=label)
def test_ambient_decimal_context_is_not_used(row: dict[str, Any]) -> None:
    plain = outcome(build(row["ops"]))
    with decimal.localcontext(Context(prec=5, rounding=decimal.ROUND_UP)):
        assert outcome(build(row["ops"])) == plain
    with hostile_default():
        assert outcome(build(row["ops"])) == plain


def millions(tenths: int) -> str:
    scaled = Fraction(tenths, 10) / 1000 * 10000
    assert scaled.denominator == 1
    whole, part = divmod(scaled.numerator, 10000)
    return f"{whole}.{part:04d}".rstrip("0").rstrip(".")


units = st.integers(min_value=0, max_value=9_999_999_999)


@settings(max_examples=200, deadline=None)
@given(revenue=units, negative=st.booleans(), dividends=st.tuples(units, units, units))
def test_scale_property(revenue: int, negative: bool, dividends: tuple[int, int, int]) -> None:
    sign = "-" if negative and revenue else ""
    thousand = [
        "thousands",
        [["scale"], 1000],
        [["base", "revenue", "amount"], f"{sign}{revenue // 10}.{revenue % 10}"],
        [["base_drivers", "dividends", "values"], [f"{t // 10}.{t % 10}" for t in dividends]],
    ]
    million = [
        [["base", "revenue", "amount"], sign + millions(revenue)],
        [["base_drivers", "dividends", "values"], [millions(t) for t in dividends]],
    ]
    got, stated = parse_inputs(build(thousand))
    base, _ = parse_inputs(build(million))
    assert got.model_dump(mode="json") == base.model_dump(mode="json") | {"scale": 1000}
    assert stated["base revenue"] == thousand[2][1]
    assert [stated[f"base_drivers dividends year {n}"] for n in (1, 2, 3)] == thousand[3][1]


@settings(max_examples=200, deadline=None)
@given(debt=units, repaid=st.tuples(units, units, units))
def test_bound_property(debt: int, repaid: tuple[int, int, int]) -> None:
    def text(units: int) -> str:
        return f"{units // 10000}.{units % 10000:04d}"

    document = build(
        [
            [["base", "debt", "amount"], text(debt)],
            [["base_drivers", "debt_repayment", "values"], [text(x) for x in repaid]],
        ]
    )
    sums = [sum(repaid[: n + 1]) for n in range(3)]
    over = [n + 1 for n, s in enumerate(sums) if s > debt]
    result = outcome(document)
    if not over:
        assert isinstance(result[0], dict)
        return
    assert result[:2] == (RefusalKind.REPAYMENT, "debt_repayment")
    assert re.search(rf"through forecast year {over[0]} totals ", result[2])


def test_length_error_that_echoes_a_failed_item_is_dropped() -> None:
    one = "facilities.0: Value error, a facility states a fixed rate or a floating one, not both"
    empty = "facilities: Tuple should have at least 1 item after validation, not 0"
    for facilities, text in (([one_facility(spread_pct="2")], one), ([], empty)):
        assert issues_of(build([[["facilities"], facilities]])) == text


def length_error(minimum: int, actual: int, kind: str = "Tuple", type_: str = "too_short") -> Any:
    ctx = {"min_length": minimum, "actual_length": actual}
    msg = f"{kind} should have at least {minimum} items after validation, not {actual}"
    return {"type": type_, "loc": ("f",), "msg": msg, "ctx": ctx}


def failed_item(index: int) -> Any:
    return {"type": "value_error", "loc": ("f", index), "msg": "Value error, x"}


DROPS = [  # errors, indexes of the errors kept
    ([length_error(1, 0), failed_item(0)], [1]),
    ([length_error(2, 0), failed_item(0)], [0, 1]),
    ([length_error(1, 0)], [0]),
    ([length_error(2, 0), failed_item(0), failed_item(1), failed_item(1)], [1, 2, 3]),
    ([length_error(1, 0, type_="value_error"), failed_item(0)], [0, 1]),
    ([length_error(1, 0, kind="List"), failed_item(0)], [1]),
]


@pytest.mark.parametrize(("errors", "kept"), DROPS)
def test_drop_rule_on_built_errors(errors: list[Any], kept: list[int]) -> None:
    assert inputs.without_echoes(errors) == [errors[i] for i in kept]


def test_missing_value_cannot_be_unwrapped() -> None:
    missing = Value(missing=Missing(MissingCode.NOT_SOURCED, "not printed"))
    with pytest.raises(ValueError, match="^an amount is missing$"):
        inputs._plain(missing)


ODD = [[["base"], 0], [["base", "wc"], "amount"], [["facilities"], ["balance"]]]


@pytest.mark.parametrize("op", ODD)
def test_odd_holders_at_scale_1000_reach_the_schema(op: list[Any]) -> None:
    assert refusal(build([[["scale"], 1000], op])).kind is RefusalKind.SCHEMA
