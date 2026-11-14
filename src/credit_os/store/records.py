"""What the store hands back: a claim on a run, a run row and an event row. The writer token
is in a `Claim` only; no record read from the store holds it."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Claim:
    """The right to write one run: `token` is 32 lowercase hex characters."""

    run_id: str
    token: str


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
