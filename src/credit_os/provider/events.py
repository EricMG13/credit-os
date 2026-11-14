"""One call's session events to a `Reply`. Pure: no I/O, clock, environment or `copilot`."""

import json
from decimal import Decimal
from typing import Any

from credit_os.provider.redact import Redactor, home_paths
from credit_os.provider.types import Reply, StopReason, ToolCall, Turn, Usage

BAD_SHAPE_MESSAGE = "an event is not an object with an id, a type and data"
_REDACTED_RAW = b'"[redacted]"'
_COUNTS = (
    ("inputTokens", "input_tokens"),
    ("cacheReadTokens", "cached_read_tokens"),
    ("cacheWriteTokens", "cache_write_tokens"),
    ("outputTokens", "output_tokens"),
    ("reasoningTokens", "reasoning_tokens"),
)
_STOPS: dict[str, StopReason] = {
    **dict.fromkeys(("stop", "end_turn"), "end"),
    **dict.fromkeys(("tool_calls", "tool_use"), "tool_use"),
    **dict.fromkeys(("length", "max_tokens"), "max_tokens"),
}
_ROUTES = {"isByok": "ByokRouted", "isAuto": "AutoRouted"}
_MAX_NANO = 10**39  # a charge has at most 39 digits
_Figures = tuple[Usage, Decimal | None]
_Problem = tuple[str, str]  # (error class, message)


def reply_from_events(given: object, *, model: str, redactor: Redactor) -> Reply:
    """The reply for the `{"id", "type", "data"}` events observed for one call. Never raises for
    events built from JSON values (dict, list, str, int, float, bool, None).

    An event equal to an earlier one (same id, type and data) is a redelivery and is ignored;
    an id reused with other type or data is read as a separate event.

    Routing limit: SDK 1.0.8 reports `isByok` and `isAuto` only on a `model.call_failure`
    event, so `ByokRouted` and `AutoRouted` are detected only for a failed model call; a
    successful call routed either way is not detected here."""
    raw = _serialise(given)
    redacted = None if raw is None else redactor.bytes_(raw)
    changed, raw = redacted != raw, redacted
    events = _as_events(given)
    if raw is None or events is None:
        return _failed(None, ("UnparsableReply", BAD_SHAPE_MESSAGE), raw)
    usage_data = _usage_data(events)
    figures = _figures(usage_data)
    text = "".join(_contents(events))
    if changed or redactor.text(text) != text:
        return _failed(figures, ("KeyReflected", "the reply reflected a key"), _REDACTED_RAW)
    if figures is None:
        return _failed(
            None, ("UnparsableReply", "a usage count is not a non-negative integer"), raw
        )
    problem = _early_problem(events, usage_data, model, redactor)
    if problem:
        return _failed(figures, problem, raw)
    stop = _stop_reason(usage_data[-1])
    calls = _tool_calls(events)
    if isinstance(calls, str):
        return _failed(figures, ("UnparsableReply", calls), raw)
    problem = _tool_problem(calls, events, stop)
    if problem:
        return _failed(figures, problem, raw)
    if stop == "max_tokens" and not calls:
        return _failed(figures, ("ReplyCut", "finishReason length or max_tokens"), raw)
    last = usage_data[-1]
    usage, charge = figures
    turn = Turn(text, tuple(calls), usage, stop, last.get("model"), _request_id(last))
    return Reply("ok", turn, None, None, usage, charge, raw, None, None)


def _serialise(events: object) -> bytes | None:
    try:
        return json.dumps(events, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, RecursionError):
        return None


def _as_events(events: object) -> list[Any] | None:
    if not isinstance(events, list):
        return None
    ok = all(
        type(e) is dict and _exact(e.get("id"), str) and _exact(e.get("type"), str) for e in events
    )
    ok = ok and all(e["id"] and _exact(e.get("data"), dict) for e in events)
    return [e for i, e in enumerate(events) if e not in events[:i]] if ok else None


def _exact(value: object, kind: type) -> bool:
    return type(value) is kind


def _failed(figures: _Figures | None, problem: _Problem, raw: bytes | None) -> Reply:
    error_class, message = problem
    usage, charge = figures or (Usage(), None)
    if charge is not None or any(v is not None for v in vars(usage).values()):
        return Reply("sent_usage", None, error_class, message, usage, charge, raw, None, None)
    return Reply("sent_unknown", None, error_class, message, None, None, raw, None, None)


def _contents(events: list[Any]) -> list[str]:
    contents = [d.get("content") for d in _of_type(events, "assistant.message")]
    return [c for c in contents if isinstance(c, str)]


def _usage_data(events: list[Any]) -> list[dict[str, Any]]:
    return _of_type(events, "assistant.usage")


def _is_count(value: object) -> bool:
    return value is None or (isinstance(value, int) and not isinstance(value, bool) and value >= 0)


def _total(values: list[Any]) -> int | None:
    return None if not values or any(v is None for v in values) else sum(values)


def _figures(usage_data: list[dict[str, Any]]) -> _Figures | None:
    if not all(_is_count(d.get(wire)) for d in usage_data for wire, _ in _COUNTS):
        return None
    counts = {field: _total([d.get(wire) for d in usage_data]) for wire, field in _COUNTS}
    nanos = _total([_nano(d) for d in usage_data])
    return Usage(**counts), (None if nanos is None else _usd(nanos))


def _nano(data: dict[str, Any]) -> int | None:
    block = data.get("copilotUsage")
    value = block.get("totalNanoAiu") if isinstance(block, dict) else None
    if isinstance(value, float) and value.is_integer() and 0 <= value <= 2**53:
        value = int(value)
    return value if type(value) is int and 0 <= value < _MAX_NANO else None


def _usd(nanos: int) -> Decimal:
    """Built from its digits, no float or rounding; totalNanoAiu counts units of 1E-11 USD."""
    return Decimal((0, tuple(int(d) for d in str(nanos)), -11))


def _early_problem(
    events: list[Any], usage_data: list[dict[str, Any]], model: str, redactor: Redactor
) -> _Problem | None:
    """Rules 4 to 9: the first that applies."""
    errors = _of_type(events, "session.error")
    if any(not isinstance(d.get("content"), str) for d in _of_type(events, "assistant.message")):
        return "UnparsableReply", "an assistant.message content is not a string"
    if errors:
        parts = [
            p
            for p in (errors[0].get("errorType"), errors[0].get("message"))
            if p and isinstance(p, str)
        ]
        return "SessionError", redactor.text(home_paths(": ".join(parts)))[:500]
    if any(d.get("aborted") is True for d in _of_type(events, "session.idle")):
        return "Aborted", "the session went idle after an abort"
    return _usage_problem(usage_data, model, _of_type(events, "model.call_failure"))


def _usage_problem(
    usage_data: list[dict[str, Any]], model: str, failures: list[dict[str, Any]]
) -> _Problem | None:
    if not usage_data:
        return "UnparsableReply", "no assistant.usage event"
    if any(d.get("model") != model for d in usage_data):
        return "ModelMismatch", "the reply was refused: ModelMismatch"
    for flag, name in _ROUTES.items():
        if any(d.get(flag) is True for d in failures):
            return name, f"the reply was refused: {name}"
    return None


def _of_type(events: list[Any], kind: str) -> list[dict[str, Any]]:
    return [e["data"] for e in events if e["type"] == kind]


def _stop_reason(last_usage: dict[str, Any]) -> StopReason:
    reason = last_usage.get("finishReason")
    return _STOPS.get(reason, "other") if isinstance(reason, str) else "other"


def _request_id(last_usage: dict[str, Any]) -> str | None:
    ids = [last_usage.get("apiCallId"), last_usage.get("providerCallId")]
    return next((i for i in ids if isinstance(i, str) and i), None)


def _non_empty(value: object) -> bool:
    return isinstance(value, str) and value != ""


def _tool_call(data: dict[str, Any]) -> ToolCall | str:
    if not _non_empty(data.get("toolCallId")):
        return "toolCallId is not a non-empty string"
    if not _non_empty(data.get("toolName")):
        return "toolName is not a non-empty string"
    if data.get("parentToolCallId") is not None:
        return "sub-agent tool call"
    args = data.get("arguments")
    bad = None if args is None or isinstance(args, dict) else json.dumps(args)
    return ToolCall(data["toolCallId"], data["toolName"], args if bad is None and args else {}, bad)


def _tool_calls(events: list[Any]) -> list[ToolCall] | str:
    calls: list[ToolCall] = []
    for data in _of_type(events, "tool.execution_start"):
        call = _tool_call(data)
        if isinstance(call, str):
            return call
        calls.append(call)
    if len({c.call_id for c in calls}) != len(calls):
        return "duplicate toolCallId"
    return calls


def _requested_ids(events: list[Any]) -> set[str | None] | None:
    lists = [
        r
        for d in _of_type(events, "assistant.message")
        if isinstance(r := d.get("toolRequests"), list)
    ]
    return (
        {
            r.get("toolCallId") if isinstance(r, dict) and _non_empty(r.get("toolCallId")) else None
            for requests in lists
            for r in requests
        }
        if lists
        else None
    )


def _tool_problem(calls: list[ToolCall], events: list[Any], stop: str) -> _Problem | None:
    requested = _requested_ids(events)
    if requested is not None and requested != {c.call_id for c in calls}:
        return "UnparsableReply", "tool requests and tool starts differ"
    if stop == "tool_use" and not calls:
        return "UnparsableReply", "stop reason tool_use with no tool call"
    if calls and stop not in ("tool_use", "max_tokens"):
        return "UnparsableReply", "tool calls without a tool stop reason"
    return None
