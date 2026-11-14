import dataclasses
import json
import os
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

import provider_canned_key as key
import pytest

from credit_os.provider.canned import RecordingError, RecordingMissing, canned_model
from credit_os.provider.types import Message, Model, Reply, Request

RECORDING = Path(__file__).parent / "recordings" / "canned.jsonl"
REQUEST = Request((Message("user", "x"),), (), 10, "medium")
CP1_1 = ("cp1-synthetic", 1)


def _ask(model: Model, at: tuple[str, int]) -> Reply:
    return model.complete(REQUEST, exchange_id=at[0], call_index=at[1])


def _file(tmp_path: Path, *lines: dict[str, Any] | str) -> Path:
    path = tmp_path / "rec.jsonl"
    path.write_text("\n".join(x if isinstance(x, str) else json.dumps(x) for x in lines) + "\n")
    return path


@pytest.mark.parametrize("at", list(key.CANNED_REPLIES))
def test_recorded_replies_match_key(at: tuple[str, int]) -> None:
    model = canned_model("copilot-sol-medium", RECORDING)
    assert dataclasses.asdict(_ask(model, at)) == key.CANNED_REPLIES[at]


@pytest.mark.parametrize(("at", "text"), list(key.CANNED_BILLED_TEXT.items()))
def test_billed_digits(at: tuple[str, int], text: str) -> None:
    assert str(_ask(canned_model("c", RECORDING), at).billed_usd) == text


def test_tool_argument_keeps_decimal_digits() -> None:
    turn = _ask(canned_model("c", RECORDING), CP1_1).turn
    assert turn is not None
    scale = turn.tool_calls[0].arguments["scale"]
    assert isinstance(scale, Decimal)
    assert str(scale) == key.CANNED_SCALE_TEXT


@pytest.mark.parametrize(("at", "texts"), list(key.CANNED_COMPACTION_BILLED_TEXT.items()))
def test_compaction_charges(at: tuple[str, int], texts: tuple[str | None, ...]) -> None:
    reply = _ask(canned_model("c", RECORDING), at)
    assert (
        tuple(None if c.billed_usd is None else str(c.billed_usd) for c in reply.compactions)
        == texts
    )


def test_missing_count_is_not_zero() -> None:
    usage = _ask(canned_model("c", RECORDING), CP1_1).usage
    assert usage is not None
    assert usage.cached_read_tokens == 0
    assert usage.input_tokens is None


@pytest.mark.parametrize("at", key.CANNED_MISSING)
def test_missing_request_raises(at: tuple[str, int]) -> None:
    with pytest.raises(RecordingMissing) as caught:
        _ask(canned_model("c", RECORDING), at)
    assert (caught.value.exchange_id, caught.value.call_index) == at
    assert at[0] in str(caught.value)
    assert str(at[1]) in str(caught.value)


@pytest.mark.parametrize("line", key.CANNED_BAD_LINES)
def test_bad_lines_refused(tmp_path: Path, line: dict[str, Any] | str) -> None:
    with pytest.raises(RecordingError, match="line 1"):
        canned_model("c", _file(tmp_path, line))


_BASE = key.CANNED_GOOD_LINES[0]
_TURN = _BASE["reply"]["turn"]
_CALL = {"call_id": "c", "name": "n", "arguments": {}}
_USAGE_KEYS = (
    "input_tokens, cached_read_tokens, cache_write_tokens, output_tokens, reasoning_tokens"
)
_CHARGE = "billed_usd must be a decimal string or null"
_NUMBER = '{"exchange_id":"e","call_index":0,"reply":{"x":NaN}}'


def _reply(**changes: Any) -> dict[str, Any]:
    return {**_BASE, "reply": {**_BASE["reply"], **changes}}


def _turn(**changes: Any) -> dict[str, Any]:
    return _reply(turn={**_TURN, **changes})


def _call(**changes: Any) -> dict[str, Any]:
    return _turn(tool_calls=[{**_CALL, **changes}])


# (one-line recording, the whole refusal text after "rec.jsonl line 1: ")
MESSAGES: list[tuple[dict[str, Any] | str, str]] = [
    ("[]", "line must be an object"),
    ({**_BASE, "x": 1}, "line must have exactly the keys exchange_id, call_index, reply"),
    ({**_BASE, "exchange_id": ""}, "exchange_id must be a non-empty string"),
    ({**_BASE, "call_index": -1}, "call_index must be a non-negative integer"),
    ({**_BASE, "reply": []}, "reply must be an object"),
    (
        _reply(x=1),
        (
            "reply must have exactly the keys kind, turn, error_class, message, usage, "
            "billed_usd, compactions"
        ),
    ),
    (_reply(kind="sent_known"), "unknown reply kind 'sent_known'"),
    (_reply(usage={}), "an ok reply's usage is its turn's: usage must be null"),
    (_reply(billed_usd=0.5), _CHARGE),
    (_reply(billed_usd="one"), "billed_usd is not a decimal"),
    (_reply(error_class=5), "error_class must be a string or null"),
    (_reply(message=5), "message must be a string or null"),
    (_reply(compactions={}), "compactions must be a list"),
    (_reply(compactions=[None]), "compaction must be an object"),
    (
        _reply(compactions=[{"usage": None, "billed_usd": None}]),
        "usage must be an object",
    ),
    (
        _reply(compactions=[{"usage": {}, "billed_usd": None, "x": 1}]),
        "compaction must have exactly the keys usage, billed_usd",
    ),
    (
        _turn(x=1),
        (
            "turn must have exactly the keys text, tool_calls, usage, stop_reason, "
            "reported_model, request_id"
        ),
    ),
    (_turn(text=None), "text must be a string"),
    (_turn(reported_model=6), "reported_model must be a string or null"),
    (_turn(request_id=6), "request_id must be a string or null"),
    (_turn(usage={"input_tokens": 1}), f"usage must have exactly the keys {_USAGE_KEYS}"),
    (_turn(tool_calls={}), "tool_calls must be a list"),
    (_turn(tool_calls=[1]), "tool call must be an object"),
    (_call(x=1), "tool call must have exactly the keys call_id, name, arguments"),
    (_call(call_id=1), "call_id must be a string"),
    (_call(name=1), "name must be a string"),
    (_call(arguments="{}"), "arguments must be an object"),
    (_call(bad_arguments=1), "bad_arguments must be a string or null"),
    ('{"exchange_id":"e","exchange_id":"e"}', "duplicate key 'exchange_id'"),
    (_NUMBER, "NaN is not allowed in a JSON number"),
    (_NUMBER.replace("NaN", "-Infinity"), "-Infinity is not allowed in a JSON number"),
    ("{not json", "not JSON: Expecting property name enclosed in double quotes"),
    ("[" * 100_000, "not JSON: nested too deeply"),
]


@pytest.mark.parametrize(("line", "message"), MESSAGES)
def test_refusal_text(tmp_path: Path, line: dict[str, Any] | str, message: str) -> None:
    with pytest.raises(RecordingError, match=rf"^rec\.jsonl line 1: {re.escape(message)}$"):
        canned_model("c", _file(tmp_path, line))


def test_null_text_fields_accepted(tmp_path: Path) -> None:
    line = _turn(reported_model=None, request_id=None, tool_calls=[_CALL])
    reply = _ask(canned_model("c", _file(tmp_path, line)), ("e", 0))
    assert reply.turn is not None
    assert (reply.turn.reported_model, reply.turn.tool_calls[0].bad_arguments) == (None, None)


@pytest.mark.parametrize("line", key.CANNED_GOOD_LINES)
def test_good_lines_accepted(tmp_path: Path, line: dict[str, Any]) -> None:
    reply = _ask(canned_model("c", _file(tmp_path, line)), ("e", 0))
    assert (reply.raw, reply.started_at, reply.finished_at) == (None, None, None)


def test_good_line_details(tmp_path: Path) -> None:
    bad = _ask(canned_model("c", _file(tmp_path, key.CANNED_GOOD_LINES[2])), ("e", 0))
    assert bad.turn is not None
    assert bad.turn.tool_calls[0].bad_arguments == "[1]"
    two = _ask(canned_model("c", _file(tmp_path, key.CANNED_GOOD_LINES[3])), ("e", 0))
    assert [c.billed_usd for c in two.compactions] == [Decimal("0.0240831"), None]


def test_duplicate_refused_at_second_line(tmp_path: Path) -> None:
    with pytest.raises(RecordingError, match=r"^rec\.jsonl line 2: 'e' call_index 0 is recorded"):
        canned_model("c", _file(tmp_path, *key.CANNED_DUPLICATE))


def test_blank_lines_count(tmp_path: Path) -> None:
    with pytest.raises(RecordingError, match=r"rec\.jsonl line 2: "):
        canned_model("c", _file(tmp_path, "", "{not json"))


def test_unreadable_paths(tmp_path: Path) -> None:
    for path in (tmp_path / "absent.jsonl", tmp_path):
        with pytest.raises(RecordingError, match=rf"{path.name}: unreadable: \w+"):
            canned_model("c", path)


def test_not_utf8_refused(tmp_path: Path) -> None:
    path = tmp_path / "rec.jsonl"
    path.write_bytes(b"\xff\n")
    with pytest.raises(RecordingError, match=r"rec\.jsonl: unreadable: UnicodeDecodeError"):
        canned_model("c", path)


class _NoEnvironment:
    """Every read raises, except the two names the mutation tool itself reads."""

    def __contains__(self, name: str) -> bool:
        if name == "MUTANT_UNDER_TEST":
            return False
        raise AssertionError("environment read")

    def get(self, name: str, default: str) -> str:
        if name == "MUTMUT_DEPENDENCY_DEPTH":
            return default
        raise AssertionError("environment read")

    def __getitem__(self, name: str) -> str:
        raise AssertionError("environment read")

    def __getattr__(self, name: str) -> object:
        raise AssertionError("environment read")


def test_reads_no_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as patched:
        patched.setattr(os, "environ", _NoEnvironment())
        assert _ask(canned_model("c", RECORDING), CP1_1).kind == "ok"


def test_config_close_and_repeat() -> None:
    model = canned_model("copilot-sol-medium", RECORDING)
    first = _ask(model, CP1_1)
    assert model.config_id == "copilot-sol-medium"
    model.close()
    assert _ask(model, CP1_1) is first
