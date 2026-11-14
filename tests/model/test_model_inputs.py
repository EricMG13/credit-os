"""The forecast inputs schema, scale to millions and the repayment bound."""

import copy
import decimal
import json
import re
import typing
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
HEAD, TAIL = (
    json.loads((HERE / "pr4a.json").read_text("utf-8"))["handoff"][k] for k in ("head", "tail")
)
VALID = KEY["valid"]
SECTION = "### Forecast inputs (machine-readable)\n\n```json\n{}\n```\n"


def put(root: Any, path: list[Any], value: Any) -> None:
    for step in path[:-1]:
        root = root[step]
    root[path[-1]] = value


def build(ops: list[Any]) -> dict[str, Any]:
    document: dict[str, Any] = copy.deepcopy(VALID)
    for op in ops:
        if op == "thousands":
            for path, value in KEY["thousands"]:
                put(document, path, value)
        elif len(op) == 1:
            holder = document
            for step in op[0][:-1]:
                holder = holder[step]
            del holder[op[0][-1]]
        else:
            put(document, op[0], op[1])
    return document


def expected_dump(row: dict[str, Any]) -> dict[str, Any]:
    return build([[path, value] for path, value in row["becomes"]])


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
    assert got.model_dump(mode="json") == expected_dump(row)
    assert stated == row["stated"]
    assert list(stated) == list(row["stated"])


@pytest.mark.parametrize("row", REFUSED, ids=label)
def test_refused(row: dict[str, Any]) -> None:
    error = refusal(build(row["ops"]))
    assert error.kind is RefusalKind(row["kind"])
    assert error.subject == row["subject"]
    assert error.message == row["message"]


def test_key_constants() -> None:
    assert list(inputs.OPERANDS) == KEY["operands"]
    assert list(typing.get_args(inputs.Category)) == KEY["categories"]
    assert inputs.SCHEMA_VERSION == VALID["schema_version"]
    assert [
        kind.value for kind in RefusalKind if kind.name in ("SCHEMA", "SCALE", "REPAYMENT")
    ] == [
        "schema",
        "scale",
        "repayment",
    ]


def test_forty_one_facilities() -> None:
    one = {"balance": "1", "fixed_rate_pct": "6.5", "spread_pct": None, "floor_pct": None}
    one |= {"reference_rate": None, "annual_amortisation": None, "maturity": None}
    document = build([[["facilities"], [one | {"name": f"F{i}"} for i in range(41)]]])
    assert refusal(document).message == KEY["forty_one"]


@pytest.mark.parametrize("bad", ["list", "string"])
def test_not_a_document(bad: str) -> None:
    given: Any = [] if bad == "list" else "{}"
    with pytest.raises(TypeError, match="^document must be a dict$"):
        parse_inputs(given)


def alternatives(items: list[Any]) -> list[Any]:
    others: list[Any] = [(item for item in items)]
    if all(isinstance(item, str) for item in items):
        others.append(set(items))
    return others


@pytest.mark.parametrize(
    ("path", "items", "loc"),
    [
        (
            ["base_drivers", "dividends", "values"],
            ["20", "20", "25"],
            "base_drivers.dividends.values",
        ),
        (["years"], VALID["years"], "years"),
        (["scope_limits"], ["a", "b"], "scope_limits"),
    ],
)
def test_sequences_are_lists_or_tuples_only(path: list[str], items: list[Any], loc: str) -> None:
    for other in alternatives(items):
        assert issues_of(build([[path, other]])) == f"{loc}: Input should be a valid tuple"
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
    items = (
        node.items()
        if isinstance(node, dict)
        else enumerate(node)
        if isinstance(node, list)
        else []
    )
    return [x for k, v in items for x in leaves(v, secret or k in SECRET_KEYS)]


@pytest.mark.parametrize("row", [r for r in REFUSED if r["kind"] == "schema"], ids=label)
def test_schema_messages_hold_no_stated_text(row: dict[str, Any]) -> None:
    document = build(row["ops"])
    assert not [text for text in leaves(document) if text in row["message"]]


def handoff(document: dict[str, Any]) -> Any:
    return parse((HEAD + SECTION.format(json.dumps(document)) + TAIL).encode("utf-8"))


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
    assert (caught.value.kind.value, caught.value.subject, caught.value.message) == (
        row["kind"],
        row["subject"],
        row["message"],
    )


HOSTILE = [r for r in ACCEPTED if r["ops"] and r["ops"][0] == [["scale"], 1000]] + [
    r for r in REFUSED if r["kind"] == "repayment"
]


def hostile_default() -> tuple[Any, Any, Any, Any]:
    default = decimal.DefaultContext
    saved = (default.prec, default.rounding, default.Emax, default.Emin)
    decimal.DefaultContext.prec, decimal.DefaultContext.rounding = 3, decimal.ROUND_DOWN
    decimal.DefaultContext.Emax, decimal.DefaultContext.Emin = 5, -5
    return saved


@pytest.mark.parametrize("row", HOSTILE, ids=label)
def test_ambient_decimal_context_is_not_used(row: dict[str, Any]) -> None:
    plain = outcome(build(row["ops"]))
    with decimal.localcontext(Context(prec=5, rounding=decimal.ROUND_UP)):
        assert outcome(build(row["ops"])) == plain
    saved = hostile_default()
    try:
        assert outcome(build(row["ops"])) == plain
    finally:
        decimal.DefaultContext.prec, decimal.DefaultContext.rounding = saved[:2]
        decimal.DefaultContext.Emax, decimal.DefaultContext.Emin = saved[2:]


def millions(tenths: int) -> str:
    scaled = Fraction(tenths, 10) / 1000 * 10000
    assert scaled.denominator == 1
    whole, part = divmod(scaled.numerator, 10000)
    return f"{whole}.{part:04d}".rstrip("0").rstrip(".")


tenths = st.integers(min_value=0, max_value=9_999_999_999)


@settings(max_examples=200, deadline=None)
@given(revenue=tenths, negative=st.booleans(), dividends=st.tuples(tenths, tenths, tenths))
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


ten_thousandths = st.integers(min_value=0, max_value=9_999_999_999)


@settings(max_examples=200, deadline=None)
@given(debt=ten_thousandths, repaid=st.tuples(ten_thousandths, ten_thousandths, ten_thousandths))
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


def one_facility(**changes: Any) -> dict[str, Any]:
    base = {"name": "T", "balance": "4", "fixed_rate_pct": "6", "spread_pct": None}
    base |= {"floor_pct": None, "reference_rate": None, "annual_amortisation": None}
    return base | {"maturity": None} | changes


def test_length_error_that_echoes_a_failed_item_is_dropped() -> None:
    both = build([[["facilities"], [one_facility(spread_pct="2")]]])
    assert (
        issues_of(both)
        == "facilities.0: Value error, a facility states a fixed rate or a floating one, not both"
    )
    assert issues_of(build([[["facilities"], []]])) == (
        "facilities: Tuple should have at least 1 item after validation, not 0"
    )


def length_error(minimum: int, actual: int) -> Any:
    ctx = {"min_length": minimum, "actual_length": actual}
    msg = f"Tuple should have at least {minimum} items after validation, not {actual}"
    return {"type": "too_short", "loc": ("f",), "msg": msg, "ctx": ctx}


def failed_item(index: int) -> Any:
    return {"type": "value_error", "loc": ("f", index), "msg": "Value error, x"}


def test_drop_rule_on_built_errors() -> None:
    echo_only = [length_error(1, 0), failed_item(0)]
    assert inputs.without_echoes(echo_only) == [failed_item(0)]
    short = [length_error(2, 0), failed_item(0)]
    assert inputs.without_echoes(short) == short
    assert inputs.without_echoes([length_error(1, 0)]) == [length_error(1, 0)]
    two_items = [length_error(2, 0), failed_item(0), failed_item(1), failed_item(1)]
    assert inputs.without_echoes(two_items) == two_items[1:]


def test_missing_value_cannot_be_unwrapped() -> None:
    missing = Value(missing=Missing(MissingCode.NOT_SOURCED, "not printed"))
    with pytest.raises(ValueError, match="^an amount is missing$"):
        inputs._plain(missing)


@pytest.mark.parametrize(
    "ops",
    [
        [[["base"], ["x"]]],
        [[["base", "debt"], "amount"]],
        [[["facilities"], ["balance"]]],
        [[["facilities"], [7]]],
    ],
)
def test_odd_holders_at_scale_1000_reach_the_schema(ops: list[Any]) -> None:
    document = build([[["scale"], 1000], *ops])
    assert refusal(document).kind is RefusalKind.SCHEMA


def test_drop_rule_names_only_length_errors() -> None:
    not_length = {**length_error(1, 0), "type": "value_error"}
    kept = [not_length, failed_item(0)]
    assert inputs.without_echoes(kept) == kept
    as_list: Any = {
        **length_error(1, 0),
        "msg": "List should have at least 1 item after validation, not 0",
    }
    assert inputs.without_echoes([as_list, failed_item(0)]) == [failed_item(0)]
