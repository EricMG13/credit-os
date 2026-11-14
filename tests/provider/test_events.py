import json
from typing import Any

import provider_events_key as key
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.provider.events import reply_from_events
from credit_os.provider.redact import Redactor
from credit_os.provider.types import Reply, Usage


def _reply(events: Any, redactor: Redactor | None = None) -> Reply:
    return reply_from_events(events, model=key.MODEL, redactor=redactor or Redactor())


def _charge(reply: Reply) -> str | None:
    return None if reply.billed_usd is None else format(reply.billed_usd, "f")


@pytest.mark.parametrize(("events", "want"), key.EVENT_CASES.values(), ids=list(key.EVENT_CASES))
def test_event_cases(events: list[Any], want: dict[str, Any]) -> None:
    reply = _reply(events)
    assert [reply.kind, reply.error_class, reply.message] == [
        want[k] for k in ("kind", "error_class", "message")
    ]
    assert reply.usage == (None if want["usage"] is None else Usage(*want["usage"]))
    assert _charge(reply) == want["charge"]
    assert (reply.started_at, reply.finished_at, reply.compactions) == (None, None, ())
    if reply.error_class == "KeyReflected":
        assert reply.raw == b'"[redacted]"'
    else:
        assert reply.raw is not None
        assert json.loads(reply.raw) == events
    if want["turn"] is None:
        assert reply.turn is None
        return
    turn = reply.turn
    assert turn is not None
    calls = tuple((c.call_id, c.name, c.arguments, c.bad_arguments) for c in turn.tool_calls)
    assert (turn.text, calls, turn.stop_reason, turn.request_id) == want["turn"]
    assert turn.reported_model == key.MODEL
    assert turn.usage == reply.usage


@pytest.mark.parametrize(
    "events",
    [
        *key.BAD_SHAPES,
        None,
        "x",
        {},
        7,
        [{"id": "e", "data": {}}],
        [type("D", (dict,), {})(id="e", type="t", data={})],
        [{"id": type("S", (str,), {})("e"), "type": "t", "data": {}}],
        [{"id": "e", "type": "t", "data": type("D", (dict,), {})()}],
        type("L", (list,), {})([{"id": "e", "type": "t", "data": {}}]),
    ],
)
def test_bad_shapes(events: Any) -> None:
    reply = _reply(events)
    assert (reply.kind, reply.error_class) == ("sent_unknown", "UnparsableReply")
    assert reply.message == key.BAD_SHAPE_MESSAGE
    assert reply.raw == json.dumps(events, separators=(",", ":")).encode()


def test_events_that_are_not_json() -> None:
    reply = _reply([{"id": "e1", "type": "t", "data": {"x": {1, 2}}}])
    assert reply.raw is None
    assert (reply.kind, reply.error_class) == ("sent_unknown", "UnparsableReply")


_ROWS = [(key.nano(v), t) for v, t in key.CHARGES] + [(d, None) for d in key.NO_CHARGE_DATA]


@pytest.mark.parametrize(("data", "text"), _ROWS, ids=repr)
def test_charges(data: dict[str, Any], text: str | None) -> None:
    reply = _reply([key.usage(1, finishReason="stop", **data)])
    assert reply.kind == "ok"
    assert _charge(reply) == text


def test_an_exact_environment_value_is_redacted_too() -> None:
    events = [key.usage(1, finishReason="stop"), key.message(2, "see s3cret-value")]
    reply = _reply(events, Redactor(["s3cret-value"]))
    assert reply.error_class == "KeyReflected"
    assert reply.raw == b'"[redacted]"'


@pytest.mark.parametrize(
    ("error_type", "text", "want"),
    [("e", "x" * 600, ("e: " + "x" * 600)[:500]), ("", "boom", "boom"), (7, "boom", "boom")],
    ids=["cut", "empty", "int"],
)
def test_session_error_text(error_type: Any, text: str, want: str) -> None:
    event = {
        "id": "e1",
        "type": "session.error",
        "data": {"errorType": error_type, "message": text},
    }
    assert _reply([event]).message == want


@pytest.mark.parametrize("reason", [None, ["x"], 7])
def test_an_unreadable_finish_reason_is_other(reason: Any) -> None:
    turn = _reply([key.usage(1, finishReason=reason)]).turn
    assert turn is not None
    assert turn.stop_reason == "other"


def test_a_tool_request_that_is_not_an_object_differs() -> None:
    events = [
        key.usage(1, finishReason="tool_use"),
        key.message(2, "", toolRequests=["x"]),
        key.start(3, "c", "r"),
    ]
    assert _reply(events).message == "tool requests and tool starts differ"


def test_missing_is_not_zero() -> None:
    omitted = _reply(key.EVENT_CASES["a count one event omits is unknown, not smaller"][0]).usage
    assert omitted is not None
    assert omitted.cached_read_tokens is None is omitted.reasoning_tokens
    zero = _reply(key.EVENT_CASES["zero counts are counts"][0])
    assert zero.usage is not None
    assert zero.usage.input_tokens == 0
    assert zero.billed_usd is not None
    assert zero.billed_usd == 0


_JSON = st.recursive(
    st.none() | st.booleans() | st.integers() | st.floats() | st.text() | st.just(key.MODEL),
    lambda c: st.lists(c, max_size=3) | st.dictionaries(st.text(max_size=3), c, max_size=3),
    max_leaves=10,
)
_NAMES = ["id", "type", "data", "content", "toolRequests", "toolCallId", "toolName", "arguments"]
_NAMES += ["finishReason", "model", "inputTokens", "copilotUsage", "totalNanoAiu", "aborted"]
_TYPES = ["assistant.usage", "assistant.message", "tool.execution_start", "session.error"]
_EVENT = st.fixed_dictionaries(
    {"id": st.sampled_from(["a", "b"]) | _JSON, "type": st.sampled_from(_TYPES) | _JSON},
    optional={"data": st.dictionaries(st.sampled_from(_NAMES), _JSON, max_size=6) | _JSON},
)


@settings(max_examples=100)
@given(events=st.lists(_EVENT | _JSON, max_size=5) | _JSON)
def test_it_never_raises(events: Any) -> None:
    assert isinstance(_reply(events), Reply)
