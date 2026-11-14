import dataclasses
import re
from collections.abc import Callable
from decimal import Decimal
from functools import partial
from typing import Any

import pytest

from credit_os.provider.types import (
    Compaction,
    Message,
    Model,
    ProviderDataError,
    Reply,
    Request,
    ToolCall,
    ToolSpec,
    Turn,
    Usage,
)

USAGE_FIELDS = (
    "input_tokens",
    "cached_read_tokens",
    "cache_write_tokens",
    "output_tokens",
    "reasoning_tokens",
)
CALL = ToolCall(call_id="c1", name="f", arguments={})
_TURN = Turn("t", (), Usage(input_tokens=5), "end", None, None)
_REPLY = Reply("not_sent", None, "E", "m", None, None, None, None, None)
_COMPACTION = Compaction(Usage(output_tokens=7), Decimal("0.0240831"))


def _message(**kw: Any) -> Message:
    return dataclasses.replace(Message("user", "x"), **kw)


def _compaction(**kw: Any) -> Compaction:
    return dataclasses.replace(_COMPACTION, **kw)


def _turn(**kw: Any) -> Turn:
    return dataclasses.replace(_TURN, **kw)


def _reply(**kw: Any) -> Reply:
    return dataclasses.replace(_REPLY, **kw)


def _ok(**kw: Any) -> Reply:
    turn = _turn()
    return _reply(**{"kind": "ok", "turn": turn, "error_class": None, "usage": turn.usage, **kw})


_sent = partial(_reply, kind="sent_usage", usage=Usage())

_M = {"role": "tool", "tool_call_id": "c"}
_CHARGE = "billed_usd must be a Decimal"
_FINITE = "billed_usd must be finite and not negative"
_COMPACTIONS = "compactions must be a tuple of Compaction"
# (builder, keyword arguments, fragment of the refusal message)
REFUSALS: list[tuple[Callable[..., object], dict[str, Any], str]] = [
    (_message, {"role": "bot"}, "unknown role 'bot'"),
    (_message, {"role": "tool"}, "a tool message needs a tool_call_id"),
    (_message, {"role": "tool", "tool_call_id": ""}, "a tool message needs a tool_call_id"),
    (_message, {"tool_calls": (CALL,)}, "tool calls on a user message"),
    (_message, {**_M, "tool_calls": (CALL,)}, "tool calls on a tool message"),
    (_turn, {"stop_reason": "stop"}, "unknown stop_reason 'stop'"),
    (_reply, {"kind": "sent_known"}, "unknown reply kind 'sent_known'"),
    (_reply, {"turn": _turn()}, "a not_sent reply has no turn"),
    (_sent, {"turn": _turn()}, "a sent_usage reply has no turn"),
    (_ok, {"turn": None}, "an ok reply needs a turn"),
    (_ok, {"error_class": "E"}, "an ok reply has no error_class"),
    (_reply, {"error_class": None}, "a not_sent reply needs an error_class"),
    (_reply, {"error_class": ""}, "a not_sent reply needs an error_class"),
    (_ok, {"usage": Usage(input_tokens=6)}, "an ok reply repeats its turn's usage"),
    (_ok, {"usage": None}, "an ok reply repeats its turn's usage"),
    (_reply, {"kind": "sent_usage"}, "a sent_usage reply needs usage"),
    (_sent, {}, "a sent_usage reply needs a count or a charge"),
    (_reply, {"usage": Usage()}, "a not_sent reply has no usage"),
    (_reply, {"kind": "sent_unknown", "usage": Usage()}, "a sent_unknown reply has no usage"),
    (_reply, {"billed_usd": Decimal(1)}, "a not_sent reply has no charge"),
    (
        _reply,
        {"kind": "sent_unknown", "billed_usd": Decimal(1)},
        "a sent_unknown reply has no charge",
    ),
    (_sent, {"billed_usd": 0.5}, _CHARGE),
    (_sent, {"billed_usd": 1}, _CHARGE),
    (_sent, {"billed_usd": "1"}, _CHARGE),
    (_sent, {"billed_usd": Decimal("NaN")}, _FINITE),
    (_sent, {"billed_usd": Decimal("Infinity")}, _FINITE),
    (_sent, {"billed_usd": Decimal("-0.1")}, _FINITE),
    (_sent, {"billed_usd": Decimal("-0")}, _FINITE),
    (_turn, {"usage": None}, "usage must be a Usage"),
    (_turn, {"usage": {"input_tokens": 5}}, "usage must be a Usage"),
    (_sent, {"usage": {"input_tokens": 5}}, "usage must be a Usage or None"),
    (_sent, {"usage": Message("user", "x")}, "usage must be a Usage or None"),
    (_compaction, {"usage": {"input_tokens": 5}}, "usage must be a Usage"),
    (_compaction, {"billed_usd": 0.5}, _CHARGE),
    (_compaction, {"billed_usd": Decimal("NaN")}, _FINITE),
    (_compaction, {"billed_usd": Decimal(-1)}, _FINITE),
    (_compaction, {"billed_usd": Decimal("-0")}, _FINITE),
    (_ok, {"compactions": []}, _COMPACTIONS),
    (_ok, {"compactions": ({"usage": {}},)}, _COMPACTIONS),
    (_reply, {"compactions": (_COMPACTION,)}, "a not_sent reply has no compactions"),
]
BAD_COUNTS = [-1, True, False, 1.0, "1"]
REFUSALS += [
    (Usage, {f: v}, f"{f} must be a non-negative int or None")
    for f in USAGE_FIELDS
    for v in BAD_COUNTS
]


def test_usage_has_the_five_counts() -> None:
    assert tuple(f.name for f in dataclasses.fields(Usage)) == USAGE_FIELDS


@pytest.mark.parametrize(("build", "kw", "fragment"), REFUSALS)
def test_refused(build: Callable[..., object], kw: dict[str, Any], fragment: str) -> None:
    with pytest.raises(ProviderDataError, match=f"^{re.escape(fragment)}$"):
        build(**kw)


@pytest.mark.parametrize("field", USAGE_FIELDS)
def test_usage_zero_and_none_kept(field: str) -> None:
    assert getattr(Usage(**{field: 0}), field) == 0
    assert getattr(Usage(), field) is None


def test_zero_count_is_not_missing() -> None:
    assert Usage(input_tokens=0) != Usage()


def test_assistant_message_with_tool_call() -> None:
    message = Message("assistant", "", (CALL,))
    assert (message.role, message.tool_calls) == ("assistant", (CALL,))


@pytest.mark.parametrize("charge", [None, Decimal("0.0996381"), Decimal(0)])
def test_ok_reply(charge: Decimal | None) -> None:
    assert _ok(billed_usd=charge) == Reply(
        "ok", _turn(), None, "m", Usage(input_tokens=5), charge, None, None, None
    )


def test_not_sent_reply() -> None:
    reply = _reply(error_class="TokenMissing", message="no token")
    assert reply == Reply(
        "not_sent", None, "TokenMissing", "no token", None, None, None, None, None
    )


@pytest.mark.parametrize("count", [500, 0])
def test_sent_usage_with_counts_only(count: int) -> None:
    reply = _reply(kind="sent_usage", usage=Usage(input_tokens=count))
    assert reply == Reply(
        "sent_usage", None, "E", "m", Usage(input_tokens=count), None, None, None, None
    )


@pytest.mark.parametrize("charge", [Decimal("0.1112661"), Decimal(0)])
def test_sent_usage_with_charge_only(charge: Decimal) -> None:
    reply = _sent(billed_usd=charge)
    assert reply == Reply("sent_usage", None, "E", "m", Usage(), charge, None, None, None)


def test_sent_unknown_reply() -> None:
    reply = _reply(kind="sent_unknown", error_class="Timeout", message="timed out")
    assert reply == Reply(
        "sent_unknown", None, "Timeout", "timed out", None, None, None, None, None
    )


@pytest.mark.parametrize("build", [_ok, partial(_reply, kind="sent_unknown")])
def test_reply_carries_compactions_without_taking_their_charge(
    build: Callable[..., Reply],
) -> None:
    reply = build(compactions=(_COMPACTION, _compaction(billed_usd=None)))
    assert reply.billed_usd is None
    assert [c.billed_usd for c in reply.compactions] == [Decimal("0.0240831"), None]


def test_types_are_frozen() -> None:
    instances: list[Any] = [
        ToolSpec(name="f", description="d", parameters={}),
        CALL,
        _message(),
        Usage(),
        Request((_message(),), (), 10, "medium"),
        _turn(),
        _reply(),
        _COMPACTION,
    ]
    for obj in instances:
        field = dataclasses.fields(obj)[0].name
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(obj, field, None)


class _Minimal:
    @property
    def config_id(self) -> str:
        return "cfg"

    def complete(self, request: Request, *, exchange_id: str, call_index: int) -> Reply:
        return _reply()

    def close(self) -> None:
        return None


def test_structural_model() -> None:
    model: Model = _Minimal()
    assert model.config_id == "cfg"
