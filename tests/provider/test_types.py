import dataclasses
from collections.abc import Callable
from decimal import Decimal
from functools import partial
from typing import Any

import pytest

from credit_os.provider.types import (
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


def _message(**kw: Any) -> Message:
    return Message(**{"role": "user", "text": "x", **kw})


def _usage(field: str, value: Any) -> Usage:
    return Usage(**{field: value})


def _turn(**kw: Any) -> Turn:
    base: dict[str, Any] = {
        "text": "t",
        "tool_calls": (),
        "usage": Usage(input_tokens=5),
        "stop_reason": "end",
        "reported_model": None,
        "request_id": None,
    }
    return Turn(**{**base, **kw})


def _fields(**kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "kind": "not_sent",
        "turn": None,
        "error_class": "E",
        "message": "m",
        "usage": None,
        "billed_usd": None,
        "raw": None,
        "started_at": None,
        "finished_at": None,
    }
    return {**base, **kw}


def _reply(**kw: Any) -> Reply:
    return Reply(**_fields(**kw))


def _ok_fields(**kw: Any) -> dict[str, Any]:
    turn = _turn()
    return _fields(kind="ok", turn=turn, error_class=None, usage=turn.usage, **kw)


def _sent(**kw: Any) -> Reply:
    return _reply(kind="sent_usage", usage=Usage(), **kw)


REFUSALS: list[tuple[str, Callable[[], object]]] = [
    ("1 role", lambda: _message(role="bot")),
    ("2 tool no id", lambda: _message(role="tool")),
    ("2 tool empty id", lambda: _message(role="tool", tool_call_id="")),
    ("3 calls on user", lambda: _message(role="user", tool_calls=(CALL,))),
    ("3 calls on tool", lambda: _message(role="tool", tool_call_id="c", tool_calls=(CALL,))),
    ("8 stop_reason", lambda: _turn(stop_reason="stop")),
    ("9 kind", lambda: _reply(kind="sent_known")),
    ("10 turn on not_sent", lambda: _reply(turn=_turn())),
    ("10 turn on sent_usage", lambda: _sent(turn=_turn())),
    ("10 ok without turn", lambda: Reply(**{**_ok_fields(), "turn": None})),
    ("11 ok with error_class", lambda: Reply(**{**_ok_fields(), "error_class": "E"})),
    ("11 failed no error_class", lambda: _reply(error_class=None)),
    ("11 failed empty error_class", lambda: _reply(error_class="")),
    ("12 ok usage differs", lambda: Reply(**{**_ok_fields(), "usage": Usage(input_tokens=6)})),
    ("12 ok usage None", lambda: Reply(**{**_ok_fields(), "usage": None})),
    ("13 sent_usage no usage", lambda: _reply(kind="sent_usage")),
    ("14 not_sent usage", lambda: _reply(usage=Usage())),
    ("14 sent_unknown usage", lambda: _reply(kind="sent_unknown", usage=Usage())),
    ("15 not_sent billed", lambda: _reply(billed_usd=Decimal(1))),
    ("15 sent_unknown billed", lambda: _reply(kind="sent_unknown", billed_usd=Decimal(1))),
    ("16 float", lambda: _sent(billed_usd=0.5)),
    ("16 int", lambda: _sent(billed_usd=1)),
    ("16 str", lambda: _sent(billed_usd="1")),
    ("17 nan", lambda: _sent(billed_usd=Decimal("NaN"))),
    ("17 inf", lambda: _sent(billed_usd=Decimal("Infinity"))),
    ("17 negative", lambda: _sent(billed_usd=Decimal("-0.1"))),
]
BAD_COUNTS = [(-1, "negative"), (True, "true"), (False, "false"), (1.0, "float"), ("1", "str")]
REFUSALS += [(f"4-7 {f} {n}", partial(_usage, f, v)) for f in USAGE_FIELDS for v, n in BAD_COUNTS]


@pytest.mark.parametrize(("name", "build"), REFUSALS, ids=[r[0] for r in REFUSALS])
def test_refused(name: str, build: Callable[[], object]) -> None:
    with pytest.raises(ProviderDataError):
        build()


@pytest.mark.parametrize("field", USAGE_FIELDS)
def test_usage_zero_and_none_kept(field: str) -> None:
    assert getattr(_usage(field, 0), field) == 0
    assert getattr(Usage(), field) is None
    assert Usage(input_tokens=0) != Usage()


def test_ok_reply_with_charge() -> None:
    reply = _reply(**_ok_fields(billed_usd=Decimal("0.0996381")))
    assert reply.kind == "ok"
    assert reply.turn == _turn()
    assert reply.usage == Usage(input_tokens=5)
    assert reply.billed_usd == Decimal("0.0996381")
    assert reply.error_class is None


def test_ok_reply_without_charge() -> None:
    reply = _reply(**_ok_fields())
    assert reply.billed_usd is None
    assert reply.usage == Usage(input_tokens=5)
    assert reply.turn == _turn()


def test_ok_reply_repeats_missing_usage() -> None:
    turn = _turn(usage=Usage())
    reply = _reply(kind="ok", turn=turn, error_class=None, usage=Usage())
    assert reply.usage == Usage()


def test_not_sent_reply() -> None:
    reply = _reply(error_class="TokenMissing", message="no token")
    assert (reply.kind, reply.error_class, reply.message) == (
        "not_sent",
        "TokenMissing",
        "no token",
    )
    assert (reply.turn, reply.usage, reply.billed_usd, reply.raw) == (None, None, None, None)
    assert (reply.started_at, reply.finished_at) == (None, None)


def test_sent_usage_with_counts_only() -> None:
    reply = _reply(kind="sent_usage", usage=Usage(input_tokens=500))
    assert reply.usage == Usage(input_tokens=500)
    assert reply.billed_usd is None


def test_sent_usage_with_charge_only() -> None:
    reply = _reply(kind="sent_usage", usage=Usage(), billed_usd=Decimal("0.1112661"))
    assert reply.usage == Usage()
    assert reply.billed_usd == Decimal("0.1112661")


def test_zero_charge_is_not_missing() -> None:
    assert _sent(billed_usd=Decimal(0)).billed_usd == Decimal(0)
    assert _sent(billed_usd=Decimal(0)).billed_usd is not None


def test_sent_unknown_reply() -> None:
    reply = _reply(kind="sent_unknown", error_class="Timeout", message="timed out")
    assert (reply.kind, reply.error_class, reply.usage, reply.billed_usd) == (
        "sent_unknown",
        "Timeout",
        None,
        None,
    )


def test_types_are_frozen() -> None:
    request = Request(messages=(_message(),), tools=(), max_output_tokens=10, effort="medium")
    instances: list[Any] = [
        ToolSpec(name="f", description="d", parameters={}),
        CALL,
        _message(),
        Usage(),
        request,
        _turn(),
        _reply(),
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


def _use(model: Model) -> str:
    return model.config_id


def test_structural_model() -> None:
    assert _use(_Minimal()) == "cfg"
