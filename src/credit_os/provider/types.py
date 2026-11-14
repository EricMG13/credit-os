"""Value types every model adapter speaks, and the `Model` protocol."""

from collections.abc import Mapping
from dataclasses import dataclass, fields
from decimal import Decimal
from typing import Any, Literal, Protocol, get_args

Role = Literal["system", "user", "assistant", "tool"]
StopReason = Literal["end", "tool_use", "max_tokens", "other"]
ReplyKind = Literal["ok", "not_sent", "sent_usage", "sent_unknown"]


class ProviderDataError(ValueError):
    """A value of these types is malformed."""


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: Mapping[str, Any]


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments: dict[str, Any]
    bad_arguments: str | None = None


@dataclass(frozen=True)
class Message:
    role: Role
    text: str
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None

    def __post_init__(self) -> None:
        if self.role not in get_args(Role):
            raise ProviderDataError(f"unknown role {self.role!r}")
        if self.role == "tool" and not self.tool_call_id:
            raise ProviderDataError("a tool message needs a tool_call_id")
        if self.tool_calls and self.role != "assistant":
            raise ProviderDataError(f"tool calls on a {self.role} message")


@dataclass(frozen=True)
class Usage:
    input_tokens: int | None = None
    cached_read_tokens: int | None = None
    cache_write_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ProviderDataError(f"{field.name} must be a non-negative int or None")


@dataclass(frozen=True)
class Request:
    messages: tuple[Message, ...]
    tools: tuple[ToolSpec, ...]
    max_output_tokens: int
    effort: str


@dataclass(frozen=True)
class Turn:
    text: str
    tool_calls: tuple[ToolCall, ...]
    usage: Usage
    stop_reason: StopReason
    reported_model: str | None
    request_id: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.usage, Usage):
            raise ProviderDataError("usage must be a Usage")
        if self.stop_reason not in get_args(StopReason):
            raise ProviderDataError(f"unknown stop_reason {self.stop_reason!r}")


def _check_charge_value(value: Decimal | None) -> None:
    """The one check of a charge: a `Decimal` that is finite and not negative, or `None`."""
    if value is None:
        return
    if not isinstance(value, Decimal):
        raise ProviderDataError("billed_usd must be a Decimal")
    if not value.is_finite() or value.is_signed():
        raise ProviderDataError("billed_usd must be finite and not negative")


@dataclass(frozen=True)
class Compaction:
    """One context compaction the runtime reported during a call: its own counts and its own
    charge (`None` when it could not be read)."""

    usage: Usage
    billed_usd: Decimal | None

    def __post_init__(self) -> None:
        if not isinstance(self.usage, Usage):
            raise ProviderDataError("usage must be a Usage")
        _check_charge_value(self.billed_usd)


@dataclass(frozen=True)
class Reply:
    """`ok`: a turn came back. `not_sent`: the call never left. `sent_usage`: sent, failed,
    at least one count in usage or the charge known. `sent_unknown`: may have been sent, cost
    unknown. `started_at` and `finished_at` are epoch seconds, `None` when the call never
    started or the reply was read from a recording (no times). `billed_usd` is the call's own
    charge only: a compaction's charge is never added to it and nothing in this layer sums
    them (a total with any `None` is unknown; step 3A decides)."""

    kind: ReplyKind
    turn: Turn | None
    error_class: str | None
    message: str | None
    usage: Usage | None
    billed_usd: Decimal | None
    raw: bytes | None
    started_at: float | None
    finished_at: float | None
    compactions: tuple[Compaction, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in get_args(ReplyKind):
            raise ProviderDataError(f"unknown reply kind {self.kind!r}")
        if self.usage is not None and not isinstance(self.usage, Usage):
            raise ProviderDataError("usage must be a Usage or None")
        self._check_outcome()
        self._check_usage()
        self._check_charge()
        self._check_compactions()

    def _check_outcome(self) -> None:
        if self.kind == "ok":
            if self.turn is None:
                raise ProviderDataError("an ok reply needs a turn")
            if self.error_class is not None:
                raise ProviderDataError("an ok reply has no error_class")
            if self.usage != self.turn.usage:
                raise ProviderDataError("an ok reply repeats its turn's usage")
            return
        if self.turn is not None:
            raise ProviderDataError(f"a {self.kind} reply has no turn")
        if not self.error_class:
            raise ProviderDataError(f"a {self.kind} reply needs an error_class")

    def _check_usage(self) -> None:
        if self.kind == "sent_usage" and self.usage is None:
            raise ProviderDataError("a sent_usage reply needs usage")
        if self.kind == "sent_usage" and self.billed_usd is None and not self._has_count():
            raise ProviderDataError("a sent_usage reply needs a count or a charge")
        if self.kind in ("not_sent", "sent_unknown") and self.usage is not None:
            raise ProviderDataError(f"a {self.kind} reply has no usage")

    def _has_count(self) -> bool:
        return self.usage is not None and any(
            getattr(self.usage, f.name) is not None for f in fields(self.usage)
        )

    def _check_charge(self) -> None:
        if self.billed_usd is None:
            return
        if self.kind in ("not_sent", "sent_unknown"):
            raise ProviderDataError(f"a {self.kind} reply has no charge")
        _check_charge_value(self.billed_usd)

    def _check_compactions(self) -> None:
        if not isinstance(self.compactions, tuple) or not all(
            isinstance(c, Compaction) for c in self.compactions
        ):
            raise ProviderDataError("compactions must be a tuple of Compaction")
        if self.compactions and self.kind == "not_sent":
            raise ProviderDataError("a not_sent reply has no compactions")


class Model(Protocol):
    """One model adapter. `complete` returns a `Reply` for every outcome of a call, a provider
    failure included; it raises only when it cannot answer at all (the canned adapter, for a
    request it has no reply for). `exchange_id` is the caller's name for one exchange and
    `call_index` the position of the call within it, counted from 0; together they name one
    call. `message` and `raw` are already redacted when a `Reply` leaves an adapter."""

    @property
    def config_id(self) -> str: ...

    def complete(self, request: Request, *, exchange_id: str, call_index: int) -> Reply: ...

    def close(self) -> None: ...
