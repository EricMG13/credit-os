"""What the store hands back: a claim on a run, a run row and an event row. The writer token
is in a `Claim` only; no record read from the store holds it."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from credit_os.provider.types import Compaction, Usage


@dataclass(frozen=True, slots=True)
class Claim:
    """The right to write one run: `token` is 32 lowercase hex characters."""

    run_id: str
    token: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class RunRecord:
    run_id: str
    issuer_id: str
    issuer_name: str
    as_of: date | None
    config_id: str
    cap_usd: Decimal
    request: bytes
    request_sha256: str
    status: str
    end_reason: str | None
    end_message: str | None
    created_at: datetime
    started_at: datetime | None
    ended_at: datetime | None


@dataclass(frozen=True, slots=True)
class EventRecord:
    """One event; `detail` is a read-only mapping (a `types.MappingProxyType`)."""

    seq: int
    run_id: str
    at: datetime
    kind: str
    module_id: str | None
    attempt: int | None
    detail: Mapping[str, str | int | None]


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    """One attempt of a module. Each issue is a read-only mapping (a `types.MappingProxyType`);
    `issues` is None until a verdict is stored."""

    run_id: str
    module_id: str
    attempt: int
    request: bytes
    request_sha256: str
    state: str
    reply: bytes | None
    reply_sha256: str | None
    issues: tuple[Mapping[str, str | int | None], ...] | None
    fail_reason: str | None
    opened_at: datetime
    replied_at: datetime | None
    closed_at: datetime | None


@dataclass(frozen=True, slots=True)
class CallRecord:
    """One call of an attempt. `usage` is None while the call is open and for `not_sent` and
    `sent_unknown`; otherwise a `Usage` of the five stored counts (all None is `Usage()`)."""

    run_id: str
    module_id: str
    attempt: int
    call_index: int
    exchange_id: str
    provider_call_index: int
    hold_usd: Decimal
    opened_at: datetime
    closed_at: datetime | None
    kind: str | None
    error_class: str | None
    message: str | None
    usage: Usage | None
    billed_usd: Decimal | None
    started_at: datetime | None
    finished_at: datetime | None
    stop_reason: str | None
    reported_model: str | None
    request_id: str | None
    raw: bytes | None


@dataclass(frozen=True, slots=True)
class CompactionRecord:
    """One stored compaction; the call key is None for one reported by `Model.close()`."""

    run_id: str
    position: int
    module_id: str | None
    attempt: int | None
    call_index: int | None
    compaction: Compaction


@dataclass(frozen=True, slots=True)
class Charges:
    """Every call and every compaction of a run, as stored; nothing is summed."""

    calls: tuple[CallRecord, ...]
    compactions: tuple[CompactionRecord, ...]
