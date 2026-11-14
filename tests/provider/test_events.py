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
    assert (reply.kind, reply.error_class, reply.message) == (
        want["kind"],
        want["error_class"],
        want["message"],
    )
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


@pytest.mark.parametrize("events", [*key.BAD_SHAPES, None, "x", {}, 7, [{"id": "e", "data": {}}]])
def test_bad_shapes(events: Any) -> None:
    reply = _reply(events)
    assert (reply.kind, reply.error_class) == ("sent_unknown", "UnparsableReply")
    assert reply.message == key.BAD_SHAPE_MESSAGE


def test_events_that_are_not_json() -> None:
    reply = _reply([{"id": "e1", "type": "t", "data": {"x": {1, 2}}}])
    assert reply.raw is None
    assert (reply.kind, reply.error_class) == ("sent_unknown", "UnparsableReply")


@pytest.mark.parametrize(("value", "text"), key.CHARGES, ids=repr)
def test_charges(value: Any, text: str | None) -> None:
    reply = _reply([key.usage(1, finishReason="stop", **key.nano(value))])
    assert reply.kind == "ok"
    assert _charge(reply) == text


@pytest.mark.parametrize("data", key.NO_CHARGE_DATA, ids=repr)
def test_no_charge_data(data: dict[str, Any]) -> None:
    reply = _reply([key.usage(1, finishReason="stop", **data)])
    assert reply.kind == "ok"
    assert reply.billed_usd is None


def test_an_exact_environment_value_is_redacted_too() -> None:
    events = [key.usage(1, finishReason="stop"), key.message(2, "see s3cret-value")]
    reply = _reply(events, Redactor(["s3cret-value"]))
    assert reply.error_class == "KeyReflected"
    assert reply.raw == b'"[redacted]"'


def test_a_session_error_message_is_cut_to_500() -> None:
    event = {"id": "e1", "type": "session.error", "data": {"errorType": "e", "message": "x" * 600}}
    assert _reply([event]).message == ("e: " + "x" * 600)[:500]


def test_missing_is_not_zero() -> None:
    omitted = _reply(key.EVENT_CASES["a count one event omits is unknown, not smaller"][0])
    assert omitted.usage is not None
    assert (omitted.usage.cached_read_tokens, omitted.usage.reasoning_tokens) == (None, None)
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
