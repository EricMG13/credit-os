"""The forecast block of a handoff: its text, strict JSON and the declined block."""

import json
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


def assert_plain_ints(value: Any) -> None:
    if isinstance(value, dict):
        for item in value.values():
            assert_plain_ints(item)
    elif isinstance(value, list):
        for item in value:
            assert_plain_ints(item)
    elif isinstance(value, int) and not isinstance(value, bool):
        assert type(value) is int


@pytest.mark.parametrize("text", KEY["json"]["accepted"])
def test_json_accepted(text: str) -> None:
    result = read_object(text)
    assert result == json.loads(text)
    assert_plain_ints(result)


@pytest.mark.parametrize("row", KEY["json"]["refused"], ids=lambda row: row[0])
def test_json_refused(row: Any) -> None:
    _, text, name, fields = row
    refused_by(lambda: read_object(text), RefusalKind.JSON, name, fields)


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


def test_length() -> None:
    base = '{"a": 1}'
    assert read_object(base + " " * (200_000 - len(base))) == {"a": 1}
    refused_by(
        lambda: read_object(base + " " * (200_001 - len(base))), RefusalKind.JSON, "too_long", {}
    )


def test_integer_digits() -> None:
    assert read_object('{"a": ' + "9" * 15 + "}") == {"a": 999999999999999}
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


@pytest.mark.parametrize("bad", [b"{}", None, 7])
def test_read_object_type(bad: Any) -> None:
    with pytest.raises(TypeError):
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
    assert [kind.value for kind in RefusalKind] == ["block", "json"]
    wrong: Any = "json"
    with pytest.raises(TypeError):
        ForecastRefused(wrong, "s", "m")
    bad_pairs: list[tuple[Any, Any]] = [(7, "m"), ("s", 7)]
    for subject, text in bad_pairs:
        with pytest.raises(TypeError):
            ForecastRefused(RefusalKind.BLOCK, subject, text)
    for subject, text in [("", "m"), (" ", "m"), ("s", ""), ("s", " \n")]:
        with pytest.raises(ValueError, match="blank"):
            ForecastRefused(RefusalKind.BLOCK, subject, text)


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
VALUES = st.recursive(
    LEAVES,
    lambda inner: st.one_of(st.lists(inner, max_size=3), st.dictionaries(TEXT, inner, max_size=3)),
    max_leaves=12,
)


@settings(max_examples=150, deadline=None)
@given(value=st.dictionaries(TEXT, VALUES, max_size=4), ascii_only=st.booleans())
def test_round_trip(value: dict[str, Any], ascii_only: bool) -> None:
    assert read_object(json.dumps(value, ensure_ascii=ascii_only)) == value
