"""The forecast block of a handoff: its text, strict JSON and the declined block."""

import copy
import json
import pickle
import sys
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.handoff.document import parse
from credit_os.model.inputs_json import (
    check_declined,
    forecast_block,
    read_forecast_document,
    read_object,
)
from credit_os.model.refusals import ForecastDeclined, ForecastRefused, RefusalKind

HERE = Path(__file__).parent
KEY = json.loads((HERE / "expected" / "pr4a.json").read_text("utf-8"))
MESSAGES = KEY["messages"]
HEAD, TAIL = KEY["handoff"]["head"], KEY["handoff"]["tail"]
SUBJECT = "forecast inputs"


def handoff(middle: str, newline: str = "\n") -> Any:
    text = (HEAD + middle + TAIL).replace("\n", newline)
    return parse(text.encode("utf-8"))


def message(name: str, fields: dict[str, Any]) -> str:
    return str(MESSAGES[name].format(**fields))


def refused_by(call: Any, kind: RefusalKind, name: str, fields: dict[str, Any]) -> None:
    with pytest.raises(ForecastRefused) as caught:
        call()
    assert caught.value.kind is kind
    assert caught.value.subject == SUBJECT
    assert caught.value.message == message(name, fields)
    assert str(caught.value) == message(name, fields)


@pytest.mark.parametrize("row", KEY["blocks"], ids=lambda row: row[0])
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_blocks(row: Any, newline: str) -> None:
    _, middle, expected = row
    document = handoff(middle, newline)
    if "text" in expected:
        assert forecast_block(document) == expected["text"]
    else:
        name, fields = expected["refused"]
        refused_by(lambda: forecast_block(document), RefusalKind.BLOCK, name, fields)


def assert_same(got: Any, expected: Any) -> None:
    """Equal and of the same type at every node, dict keys in the same order."""
    assert type(got) is type(expected)
    if isinstance(expected, dict):
        assert list(got) == list(expected)
        for key in expected:
            assert_same(got[key], expected[key])
    elif isinstance(expected, list):
        assert len(got) == len(expected)
        for got_item, expected_item in zip(got, expected, strict=True):
            assert_same(got_item, expected_item)
    else:
        assert got == expected


@pytest.mark.parametrize("text", KEY["json"]["accepted"])
def test_json_accepted(text: str) -> None:
    assert_same(read_object(text), json.loads(text))


@pytest.mark.parametrize("row", KEY["json"]["refused"], ids=lambda row: row[0])
def test_json_refused(row: Any) -> None:
    _, text, name, fields = row
    refused_by(lambda: read_object(text), RefusalKind.JSON, name, fields)
    with pytest.raises(ForecastRefused) as caught:
        read_object(text)
    assert caught.value.message.encode("utf-8")


def test_surrogate_keys_are_unicode_not_repeated() -> None:
    refused_by(lambda: read_object('{"\\ud800": 1, "\\ud800": 2}'), RefusalKind.JSON, "unicode", {})
    refused_by(lambda: read_object('{"a": {"\\udc00": 1}}'), RefusalKind.JSON, "unicode", {})


def nested(levels: int) -> str:
    return '{"a": ' + "[" * (levels - 1) + "]" * (levels - 1) + "}"


def test_nesting() -> None:
    expected: Any = []
    for _ in range(62):
        expected = [expected]
    assert read_object(nested(64)) == {"a": expected}
    refused_by(lambda: read_object(nested(65)), RefusalKind.JSON, "too_deep", {})
    assert read_object('{"a": "' + "[" * 100 + '"}') == {"a": "[" * 100}
    assert read_object('{"a": "\\"[[["}') == {"a": '"[[['}


def test_nesting_is_counted_after_escapes_and_closes() -> None:
    escaped_quote = '{"s": "\\"", "a": ' + "[" * 64 + "]" * 64 + "}"
    refused_by(lambda: read_object(escaped_quote), RefusalKind.JSON, "too_deep", {})
    bracket_after_escape = '{"a": "\\"' + "[" * 70 + '"}'
    assert read_object(bracket_after_escape) == {"a": '"' + "[" * 70}
    reopened = '{"a": ' + "[" * 31 + "[]," + "[" * 33 + "]" * 33 + "]" * 31 + "}"
    refused_by(lambda: read_object(reopened), RefusalKind.JSON, "too_deep", {})
    siblings = '{"a": [' + ",".join(["[]"] * 70) + "]}"
    assert read_object(siblings) == {"a": [[]] * 70}


def test_only_brackets_count_as_depth() -> None:
    refused_by(lambda: read_object("X" * 65), RefusalKind.JSON, "invalid", {})
    refused_by(lambda: read_object("[" * 64 + "X[" + "]" * 65), RefusalKind.JSON, "too_deep", {})


def _arrays(count: int) -> Any:
    value: Any = []
    for _ in range(count - 1):
        value = [value]
    return value


def test_depth_after_an_escaped_backslash() -> None:
    def text(brackets: int) -> str:
        return '{"a": "x\\\\", "b": ' + "[" * brackets + "]" * brackets + "}"

    refused_by(lambda: read_object(text(64)), RefusalKind.JSON, "too_deep", {})
    assert read_object(text(63)) == {"a": "x\\", "b": _arrays(63)}


def test_keys_are_compared_exactly() -> None:
    assert list(read_object('{"A": 1, "a": 2}')) == ["A", "a"]
    both = read_object('{"\\u00e9": 1, "e\\u0301": 2}')
    assert list(both) == ["\u00e9", "e\u0301"]
    assert list(both.values()) == [1, 2]


def test_length() -> None:
    base = '{"a": 1}'
    assert read_object(base + " " * (200_000 - len(base))) == {"a": 1}
    refused_by(
        lambda: read_object(base + " " * (200_001 - len(base))), RefusalKind.JSON, "too_long", {}
    )


def test_integer_digits() -> None:
    """The int-digit limit is interpreter-wide: do not run this test in parallel in one process."""
    assert_same(read_object('{"a": ' + "9" * 15 + "}"), {"a": 999999999999999})
    long_text = '{"a": ' + "1" * 5000 + "}"
    refused_by(lambda: read_object(long_text), RefusalKind.JSON, "integer", {})
    previous = sys.get_int_max_str_digits()
    try:
        sys.set_int_max_str_digits(640)
        refused_by(lambda: read_object(long_text), RefusalKind.JSON, "integer", {})
    finally:
        sys.set_int_max_str_digits(previous)


def test_repeated_key_is_echoed() -> None:
    key = "k" * 81
    text = f'{{"{key}": 1, "{key}": 0}}'
    refused_by(lambda: read_object(text), RefusalKind.JSON, "repeated", {"key": "k" * 80 + "…"})


def test_surrogate_range_ends() -> None:
    refused_by(lambda: read_object('{"a": "\\udfff"}'), RefusalKind.JSON, "unicode", {})
    assert read_object('{"a": "\ue000 \ud7ff"}') == {"a": "\ue000 \ud7ff"}


def test_order() -> None:
    refused_by(
        lambda: read_object('{"a": 1.5, "b": 1, "b": 2}'),
        RefusalKind.JSON,
        "fraction",
        {"token": "1.5"},
    )
    refused_by(lambda: read_object(" " * 200_001 + "{"), RefusalKind.JSON, "too_long", {})
    refused_by(lambda: read_object('{"a": [' * 65), RefusalKind.JSON, "too_deep", {})
    refused_by(lambda: read_object('["\\ud800"]'), RefusalKind.JSON, "not_object", {})


def test_long_token_is_echoed() -> None:
    token = "1." + "0" * 100
    refused_by(
        lambda: read_object('{"a": ' + token + "}"),
        RefusalKind.JSON,
        "fraction",
        {"token": token[:80] + "…"},
    )
    refused_by(lambda: read_object('{"a": 1' + "0" * 20 + "}"), RefusalKind.JSON, "integer", {})


class _Text(str):
    pass


@pytest.mark.parametrize("bad", [b"{}", None, 7, _Text("{}")])
def test_read_object_type(bad: Any) -> None:
    with pytest.raises(TypeError, match="^text must be a str$"):
        read_object(bad)


def declined_message(reason: str) -> str:
    return str(MESSAGES["declined"]) + (f" ({reason})" if reason else "")


@pytest.mark.parametrize("row", KEY["declined"], ids=lambda row: row[0])
def test_declined(row: Any) -> None:
    _, document, reason = row
    with pytest.raises(ForecastDeclined) as caught:
        check_declined(document)
    assert caught.value.reason == reason
    assert str(caught.value) == declined_message(reason)


@pytest.mark.parametrize("row", KEY["not_declined"], ids=lambda row: row[0])
def test_not_declined(row: Any) -> None:
    check: Any = check_declined
    assert check(row[1]) is None


def test_declined_reason_cut() -> None:
    drivers = {"d": {"values": [None]}}
    for length, expected in [(200, "y" * 200), (201, "y" * 197 + "..."), (199, "y" * 199)]:
        with pytest.raises(ForecastDeclined) as caught:
            check_declined({"base_drivers": drivers, "scope_limits": ["y" * length]})
        assert caught.value.reason == expected


def test_committed_fragment_is_declined() -> None:
    path = HERE.parent / "fixtures" / "handoffs" / "fragments" / "CP-2G-forecast-block.md"
    lines = path.read_text("utf-8").splitlines()
    start = lines.index("```json")
    end = lines.index("```", start + 1)
    document = read_object("\n".join(lines[start + 1 : end]))
    with pytest.raises(ForecastDeclined) as caught:
        check_declined(document)
    assert isinstance(caught.value.reason, str)
    assert 0 < len(caught.value.reason) <= 200


def block(text: str) -> str:
    return "### Forecast inputs (machine-readable)\n\n```json\n" + text + "\n```\n"


def test_read_forecast_document() -> None:
    accepted = KEY["json"]["accepted"][1]
    assert read_forecast_document(handoff(block(accepted))) == json.loads(accepted)
    refused_by(
        lambda: read_forecast_document(handoff("")), RefusalKind.BLOCK, "block_count", {"n": 0}
    )
    refused_by(lambda: read_forecast_document(handoff(block("{"))), RefusalKind.JSON, "invalid", {})
    declined = KEY["declined"][0]
    with pytest.raises(ForecastDeclined) as caught:
        read_forecast_document(handoff(block(json.dumps(declined[1]))))
    assert caught.value.reason == declined[2]


def test_refused_construction() -> None:
    error = ForecastRefused(RefusalKind.JSON, "forecast inputs", "a sentence")
    assert (error.kind, error.subject, error.message) == (
        RefusalKind.JSON,
        "forecast inputs",
        "a sentence",
    )
    assert str(error) == "a sentence"
    assert isinstance(error, Exception)
    assert not isinstance(error, ValueError)
    assert [kind.value for kind in RefusalKind] == [
        "block",
        "json",
        "schema",
        "scale",
        "repayment",
        "cell",
    ]
    wrong: Any = "json"
    with pytest.raises(TypeError, match="^kind must be a RefusalKind$"):
        ForecastRefused(wrong, "s", "m")
    bad_pairs: list[tuple[Any, Any, str]] = [(7, "m", "subject"), ("s", 7, "message")]
    for subject, text, name in bad_pairs:
        with pytest.raises(TypeError, match=f"^{name} must be a str$"):
            ForecastRefused(RefusalKind.BLOCK, subject, text)
    blanks = [
        ("", "m", "subject"),
        (" ", "m", "subject"),
        ("s", "", "message"),
        ("s", " \n", "message"),
    ]
    for subject, text, name in blanks:
        with pytest.raises(ValueError, match=f"^{name} must not be blank$"):
            ForecastRefused(RefusalKind.BLOCK, subject, text)


def test_exceptions_survive_pickle_and_copy() -> None:
    errors: list[Exception] = [
        ForecastRefused(RefusalKind.JSON, "forecast inputs", "a sentence"),
        ForecastDeclined("why"),
        ForecastDeclined(""),
    ]
    for error in errors:
        for clone in (
            pickle.loads(pickle.dumps(error)),
            copy.copy(error),
            copy.deepcopy(error),
        ):
            assert type(clone) is type(error)
            assert vars(clone) == vars(error)
            assert str(clone) == str(error)


def test_declined_construction() -> None:
    plain = ForecastDeclined("")
    assert plain.reason == ""
    assert str(plain) == MESSAGES["declined"]
    assert str(ForecastDeclined("why")) == MESSAGES["declined"] + " (why)"
    assert not isinstance(plain, ForecastRefused)


TEXT = st.text(alphabet=st.characters(exclude_categories=["Cs"]), max_size=8)
LEAVES = st.one_of(
    TEXT,
    st.integers(min_value=-(10**15) + 1, max_value=10**15 - 1),
    st.booleans(),
    st.none(),
)


def _nested(levels: int) -> st.SearchStrategy[Any]:
    strategy: st.SearchStrategy[Any] = LEAVES
    for _ in range(levels):
        strategy = st.one_of(
            LEAVES, st.lists(strategy, max_size=2), st.dictionaries(TEXT, strategy, max_size=2)
        )
    return strategy


@settings(max_examples=150, deadline=None)
@given(value=st.dictionaries(TEXT, _nested(4), max_size=3))
def test_round_trip(value: dict[str, Any]) -> None:
    for ascii_only in (True, False):
        assert_same(read_object(json.dumps(value, ensure_ascii=ascii_only)), value)
