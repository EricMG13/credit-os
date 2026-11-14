"""A `Model` that replays replies from one JSON Lines recording, for tests and replays.

A request with no recorded reply raises `RecordingMissing`; nothing
is defaulted. A charge is read only from a decimal string, never a number; a tool argument with
a fraction is a float, as the SDK reads it; a count not reported stays `None`."""

import json
import math
import re
from collections.abc import Mapping
from dataclasses import fields
from decimal import Decimal
from pathlib import Path
from typing import Any

from credit_os.provider.types import (
    Compaction,
    ProviderDataError,
    Reply,
    Request,
    ToolCall,
    Turn,
    Usage,
)

_USAGE_KEYS = tuple(f.name for f in fields(Usage))
_CHARGE = re.compile(r"(0|[1-9][0-9]*)(\.[0-9]+)?")
_LINE_KEYS = ("exchange_id", "call_index", "reply")
_REPLY_KEYS = ("kind", "turn", "error_class", "message", "usage", "billed_usd", "compactions")
_TURN_KEYS = ("text", "tool_calls", "usage", "stop_reason", "reported_model", "request_id")
_CALL_KEYS = ("call_id", "name", "arguments")
_COMPACTION_KEYS = ("usage", "billed_usd", "outcome", "event_id", "supersedes")


class RecordingError(ValueError):
    """A recording file or line is malformed."""


class RecordingMissing(LookupError):
    """No reply recorded for this request; never defaulted."""

    def __init__(self, exchange_id: str, call_index: int) -> None:
        super().__init__(f"no reply recorded for exchange {exchange_id!r} call_index {call_index}")
        self.exchange_id = exchange_id
        self.call_index = call_index


class CannedModel:
    """Answers from a fixed table of replies. It observes no events, so it never holds a
    compaction: `close` returns `()` and it still answers after."""

    def __init__(self, config_id: str, replies: Mapping[tuple[str, int], Reply]) -> None:
        self._config_id = config_id
        self._replies = dict(replies)

    @property
    def config_id(self) -> str:
        return self._config_id

    def complete(self, request: Request, *, exchange_id: str, call_index: int) -> Reply:
        reply = self._replies.get((exchange_id, call_index))
        if reply is None:
            raise RecordingMissing(exchange_id, call_index)
        return reply

    def close(self) -> tuple[Compaction, ...]:
        return ()


def canned_model(config_id: str, recording: Path) -> CannedModel:
    """Read one UTF-8 JSON Lines recording. Reads no environment variable."""
    try:
        text = recording.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise RecordingError(f"{recording.name}: unreadable: {type(error).__name__}") from None
    replies: dict[tuple[str, int], Reply] = {}
    for number, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            at, reply = _parse_line(line)
            if at in replies:
                raise RecordingError(f"{at[0]!r} call_index {at[1]} is recorded twice")
        except RecordingError as error:
            raise RecordingError(f"{recording.name} line {number}: {error}") from None
        replies[at] = reply
    return CannedModel(config_id, replies)


def _refuse_constant(name: str) -> object:
    raise RecordingError(f"{name} is not allowed in a JSON number")


def _parse_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise RecordingError("a number is out of range")
    return value


def _parse_int(text: str) -> int:
    if len(text.lstrip("-")) > 18:
        raise RecordingError("an integer has more than 18 digits")
    return int(text)


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, value in pairs:
        if name in result:
            raise RecordingError(f"duplicate key {name!r}")
        result[name] = value
    return result


def _parse_line(line: str) -> tuple[tuple[str, int], Reply]:
    try:
        value = json.loads(
            line,
            parse_float=_parse_float,
            parse_int=_parse_int,
            parse_constant=_refuse_constant,
            object_pairs_hook=_no_duplicate_keys,
        )
    except json.JSONDecodeError as error:
        raise RecordingError(f"not JSON: {error.msg}") from None
    except RecursionError:
        raise RecordingError("not JSON: nested too deeply") from None
    obj = _exact(value, _LINE_KEYS, "line")
    exchange_id, call_index = obj["exchange_id"], obj["call_index"]
    if not isinstance(exchange_id, str) or not exchange_id:
        raise RecordingError("exchange_id must be a non-empty string")
    if isinstance(call_index, bool) or not isinstance(call_index, int) or call_index < 0:
        raise RecordingError("call_index must be a non-negative integer")
    try:
        return (exchange_id, call_index), _reply(obj["reply"])
    except ProviderDataError as error:
        raise RecordingError(str(error)) from None


def _exact(value: object, keys: tuple[str, ...], what: str, *optional: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RecordingError(f"{what} must be an object")
    if not set(keys) <= set(value) <= {*keys, *optional}:
        raise RecordingError(f"{what} must have exactly the keys {', '.join(keys)}")
    return value


def _text(value: object, what: str, *, nullable: bool = False) -> Any:
    if isinstance(value, str) or (nullable and value is None):
        return value
    raise RecordingError(f"{what} must be a string{' or null' if nullable else ''}")


def _list(value: object, what: str) -> list[Any]:
    if not isinstance(value, list):
        raise RecordingError(f"{what} must be a list")
    return value


def _charge(value: object) -> Decimal | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise RecordingError("billed_usd must be a decimal string or null")
    if not _CHARGE.fullmatch(value):
        raise RecordingError("billed_usd is not a decimal")
    return Decimal(value)


def _call(value: object) -> ToolCall:
    obj = _exact(value, _CALL_KEYS, "tool call", "bad_arguments")
    arguments = obj["arguments"]
    if not isinstance(arguments, dict):
        raise RecordingError("arguments must be an object")
    return ToolCall(
        _text(obj["call_id"], "call_id"),
        _text(obj["name"], "name"),
        arguments,
        _text(obj["bad_arguments"], "bad_arguments") if "bad_arguments" in obj else None,
    )


def _turn(value: object) -> Turn:
    obj = _exact(value, _TURN_KEYS, "turn")
    return Turn(
        _text(obj["text"], "text"),
        tuple(_call(c) for c in _list(obj["tool_calls"], "tool_calls")),
        Usage(**_exact(obj["usage"], _USAGE_KEYS, "usage")),
        obj["stop_reason"],
        _text(obj["reported_model"], "reported_model", nullable=True),
        _text(obj["request_id"], "request_id", nullable=True),
    )


def _compaction(value: object) -> Compaction:
    obj = _exact(value, _COMPACTION_KEYS, "compaction")
    return Compaction(
        Usage(**_exact(obj["usage"], _USAGE_KEYS, "usage")),
        _charge(obj["billed_usd"]),
        obj["outcome"],
        obj["event_id"],
        obj["supersedes"],
    )


def _reply(value: object) -> Reply:
    obj = _exact(value, _REPLY_KEYS, "reply")
    turn = None if obj["turn"] is None else _turn(obj["turn"])
    if obj["kind"] == "ok":
        if obj["usage"] is not None:
            raise RecordingError("an ok reply's usage is its turn's: usage must be null")
        usage = None if turn is None else turn.usage
    else:
        usage = (
            None if obj["usage"] is None else Usage(**_exact(obj["usage"], _USAGE_KEYS, "usage"))
        )
    return Reply(
        obj["kind"],
        turn,
        _text(obj["error_class"], "error_class", nullable=True),
        _text(obj["message"], "message", nullable=True),
        usage,
        _charge(obj["billed_usd"]),
        None,
        None,
        None,
        tuple(_compaction(c) for c in _list(obj["compactions"], "compactions")),
    )
