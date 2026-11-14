import dataclasses
import json
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
    reply = _ask(canned_model("copilot-sol-medium", RECORDING), at)
    assert dataclasses.asdict(reply) == key.CANNED_REPLIES[at]


def test_digits_kept_and_missing_count_not_zero() -> None:
    model = canned_model("c", RECORDING)
    for at, text in key.CANNED_BILLED_TEXT.items():
        assert str(_ask(model, at).billed_usd) == text
    for at, texts in key.CANNED_COMPACTION_BILLED_TEXT.items():
        charges = [c.billed_usd for c in _ask(model, at).compactions]
        assert tuple(None if x is None else str(x) for x in charges) == texts
    turn = _ask(model, CP1_1).turn
    assert turn is not None
    scale = turn.tool_calls[0].arguments["scale"]
    assert isinstance(scale, Decimal) and str(scale) == key.CANNED_SCALE_TEXT
    usage = _ask(model, CP1_1).usage
    assert usage is not None and (usage.cached_read_tokens, usage.input_tokens) == (0, None)


@pytest.mark.parametrize("at", key.CANNED_MISSING)
def test_missing_request_raises(at: tuple[str, int]) -> None:
    with pytest.raises(RecordingMissing) as caught:
        _ask(canned_model("c", RECORDING), at)
    assert (caught.value.exchange_id, caught.value.call_index) == at
    assert at[0] in str(caught.value) and str(at[1]) in str(caught.value)


@pytest.mark.parametrize("line", key.CANNED_BAD_LINES, ids=range(len(key.CANNED_BAD_LINES)))
def test_bad_lines_refused(tmp_path: Path, line: dict[str, Any] | str) -> None:
    with pytest.raises(RecordingError, match="line 1"):
        canned_model("c", _file(tmp_path, line))


_BASE = key.CANNED_GOOD_LINES[0]
_CALL = {"call_id": "c", "name": "n", "arguments": {}}
_EXACTLY = "{} must have exactly the keys {}".format
_USAGE_TEXT = (
    "input_tokens, cached_read_tokens, cache_write_tokens, output_tokens, reasoning_tokens"
)
_NUMBER = '{"exchange_id":"e","call_index":0,"reply":{"x":NaN}}'


def _reply(**changes: Any) -> dict[str, Any]:
    return {**_BASE, "reply": {**_BASE["reply"], **changes}}


def _turn(**changes: Any) -> dict[str, Any]:
    return _reply(turn={**_BASE["reply"]["turn"], **changes})


def _call(**changes: Any) -> dict[str, Any]:
    return _turn(tool_calls=[{**_CALL, **changes}])


# (one-line recording, the whole refusal text after "rec.jsonl line 1: ")
MESSAGES: list[tuple[dict[str, Any] | str, str]] = [
    ("[]", "line must be an object"),
    ({**_BASE, "x": 1}, _EXACTLY("line", "exchange_id, call_index, reply")),
    ({**_BASE, "exchange_id": ""}, "exchange_id must be a non-empty string"),
    ({**_BASE, "call_index": -1}, "call_index must be a non-negative integer"),
    ({**_BASE, "reply": []}, "reply must be an object"),
    (
        _reply(x=1),
        _EXACTLY("reply", "kind, turn, error_class, message, usage, billed_usd, compactions"),
    ),
    (_reply(kind="sent_known"), "unknown reply kind 'sent_known'"),
    (_reply(usage={}), "an ok reply's usage is its turn's: usage must be null"),
    (_reply(billed_usd=0.5), "billed_usd must be a decimal string or null"),
    (_reply(billed_usd="one"), "billed_usd is not a decimal"),
    (_reply(error_class=5), "error_class must be a string or null"),
    (_reply(message=5), "message must be a string or null"),
    (_reply(compactions={}), "compactions must be a list"),
    (_reply(compactions=[None]), "compaction must be an object"),
    (_reply(compactions=[{"usage": None, "billed_usd": None}]), "usage must be an object"),
    (
        _reply(compactions=[{"usage": {}, "billed_usd": None, "x": 1}]),
        _EXACTLY("compaction", "usage, billed_usd"),
    ),
    (
        _turn(x=1),
        _EXACTLY("turn", "text, tool_calls, usage, stop_reason, reported_model, request_id"),
    ),
    (_turn(text=None), "text must be a string"),
    (_turn(reported_model=6), "reported_model must be a string or null"),
    (_turn(request_id=6), "request_id must be a string or null"),
    (_turn(usage={"input_tokens": 1}), _EXACTLY("usage", _USAGE_TEXT)),
    (_turn(tool_calls={}), "tool_calls must be a list"),
    (_turn(tool_calls=[1]), "tool call must be an object"),
    (_call(x=1), _EXACTLY("tool call", "call_id, name, arguments")),
    (_call(call_id=1), "call_id must be a string"),
    (_call(name=1), "name must be a string"),
    (_call(arguments="{}"), "arguments must be an object"),
    (_call(bad_arguments=1), "bad_arguments must be a string"),
    ('{"exchange_id":"e","exchange_id":"e"}', "duplicate key 'exchange_id'"),
    (_NUMBER, "NaN is not allowed in a JSON number"),
    (_NUMBER.replace("NaN", "-Infinity"), "-Infinity is not allowed in a JSON number"),
    (_NUMBER.replace("NaN", "1e9999999999999999999999999"), "a number is out of range"),
    (_NUMBER.replace("NaN", "1" * 19), "an integer has more than 18 digits"),
    (_reply(kind="sent_usage", usage={}), _EXACTLY("usage", _USAGE_TEXT)),
    ("{not json", "not JSON: Expecting property name enclosed in double quotes"),
    ("[" * 100_000, "not JSON: nested too deeply"),
]


@pytest.mark.parametrize(("line", "message"), MESSAGES, ids=range(len(MESSAGES)))
def test_refusal_text(tmp_path: Path, line: dict[str, Any] | str, message: str) -> None:
    with pytest.raises(RecordingError, match=rf"^rec\.jsonl line 1: {re.escape(message)}$"):
        canned_model("c", _file(tmp_path, line))


def test_good_lines_accepted_and_details(tmp_path: Path) -> None:
    def load(line: dict[str, Any]) -> Reply:
        return _ask(canned_model("c", _file(tmp_path, line)), ("e", 0))

    for reply in map(load, key.CANNED_GOOD_LINES):
        assert (reply.raw, reply.started_at, reply.finished_at) == (None, None, None)
    bad = load(key.CANNED_GOOD_LINES[2])
    assert bad.turn is not None and bad.turn.tool_calls[0].bad_arguments == "[1]"
    two = load(key.CANNED_GOOD_LINES[3])
    texts = key.CANNED_COMPACTION_BILLED_TEXT[("cp1-synthetic", 0)]
    assert [str(c.billed_usd) for c in two.compactions] == [str(t) for t in texts]
    assert [str(load(key.CANNED_GOOD_LINES[i]).billed_usd) for i in (6, 7)] == ["0", "10.50"]
    null = load(_turn(reported_model=None, request_id=None, tool_calls=[_CALL]))
    assert null.turn is not None
    assert (null.turn.reported_model, null.turn.tool_calls[0].bad_arguments) == (None, None)


@pytest.mark.parametrize(
    ("lines", "text"),
    [(key.CANNED_DUPLICATE, "'e' call_index 0 is recorded"), (("", "{not json"), "not JSON")],
)
def test_error_names_its_line(tmp_path: Path, lines: tuple[Any, ...], text: str) -> None:
    with pytest.raises(RecordingError, match=rf"^rec\.jsonl line 2: {text}"):
        canned_model("c", _file(tmp_path, *lines))


def test_unreadable_paths(tmp_path: Path) -> None:
    (tmp_path / "bad.jsonl").write_bytes(b"\xff\n")
    cases = {"absent.jsonl": r"\w+", "": r"\w+", "bad.jsonl": "UnicodeDecodeError"}
    for name, error in cases.items():
        path = tmp_path / name
        with pytest.raises(RecordingError, match=rf"^{path.name}: unreadable: {error}$"):
            canned_model("c", path)


def test_config_close_and_repeat() -> None:
    model = canned_model("copilot-sol-medium", RECORDING)
    first = _ask(model, CP1_1)
    assert model.config_id == "copilot-sol-medium"
    model.close()
    assert _ask(model, CP1_1) is first
