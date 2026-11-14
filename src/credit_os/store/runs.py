"""Run rows on a connection: the writes run inside the caller's write transaction and never
begin, commit or roll back; the reads run under the caller's lock. Every SQL string is a static
literal with `?` parameters, and nothing here catches `sqlite3.Error`: `db` maps it."""

import hashlib
import re
import secrets
import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from types import MappingProxyType

from pydantic import ValidationError

from credit_os.sources.pins import SourcePin
from credit_os.store.codec import (
    detail_from_text,
    detail_to_text,
    money_from_text,
    money_to_text,
    time_from_text,
)
from credit_os.store.errors import (
    StoreConflict,
    StoreCorrupt,
    StoreFenced,
    StoreRefused,
    safe_text,
)
from credit_os.store.records import Claim, EventRecord, RunRecord

_IDENTIFIER = re.compile(r"[A-Za-z0-9._-]{1,128}")
_NAME = re.compile(r"[a-z][a-z0-9_]{0,63}")
_TOKEN = re.compile(r"[0-9a-f]{32}")
_SQLITE_MAX_INTEGER = 2**63 - 1
STATE_KINDS = frozenset({"run_created", "writer_replaced", "run_started", "run_ended"})
END_STATUSES = frozenset({"finished", "stopped", "failed"})
OPEN_STATUSES = frozenset({"created", "running", "stopped", "failed"})  # not finished or rejected
START_STATUSES = frozenset({"created", "stopped", "failed"})


@dataclass(frozen=True, slots=True)
class NewRun:
    """A `create_run` request that passed every check, as the texts the tables keep."""

    run_id: str
    issuer_id: str
    issuer_name: str
    as_of: str | None
    config_id: str
    cap_usd: str
    request: bytes
    request_sha256: str
    pins: tuple[SourcePin, ...]


def check_identifier(name: str, value: object) -> str:
    """Return the value when it is 1 to 128 of A-Z a-z 0-9 . _ -; the message never holds it."""
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise StoreRefused(f"{name} must be 1 to 128 characters of A-Z a-z 0-9 . _ -")
    return value


def _checked_pins(pins: object) -> tuple[SourcePin, ...]:
    """A snapshot of `pins`, each revalidated by the source model; a pin it refuses is StoreRefused."""
    if not isinstance(pins, tuple | list) or not all(isinstance(pin, SourcePin) for pin in pins):
        raise StoreRefused("pins must be a tuple or list of SourcePin")
    checked: list[SourcePin] = []
    for position, pin in enumerate(tuple(pins)):
        try:
            checked.append(SourcePin.model_validate(pin))
        except ValidationError as error:
            raise StoreRefused(
                f"pin {position} is refused by the source model: {_failed_fields(error)}"
            ) from None
    return tuple(checked)


def check_new_run(
    *,
    run_id: object,
    issuer_id: object,
    issuer_name: object,
    as_of: object,
    config_id: object,
    cap_usd: object,
    request: object,
    pins: object,
) -> NewRun:
    """Check every `create_run` argument; any refusal is StoreRefused and nothing is written."""
    if not isinstance(issuer_name, str) or not issuer_name:
        raise StoreRefused("issuer_name must be non-empty text")
    if as_of is not None and type(as_of) is not date:
        raise StoreRefused("as_of must be a date or None")
    if type(request) is not bytes:
        raise StoreRefused("request must be bytes")
    checked_pins = _checked_pins(pins)
    if any(pin.size_bytes > _SQLITE_MAX_INTEGER for pin in checked_pins):
        raise StoreRefused("pin size_bytes must be at most 9223372036854775807")
    if len({pin.name for pin in checked_pins}) != len(checked_pins):
        raise StoreRefused("pin names must be distinct")
    cap_text = money_to_text(cap_usd) if isinstance(cap_usd, Decimal) else None
    if cap_text is None:
        raise StoreRefused("cap_usd must be a Decimal")
    return NewRun(
        run_id=check_identifier("run_id", run_id),
        issuer_id=check_identifier("issuer_id", issuer_id),
        issuer_name=safe_text(issuer_name),
        as_of=None if as_of is None else as_of.isoformat(),
        config_id=check_identifier("config_id", config_id),
        cap_usd=cap_text,
        request=request,
        request_sha256=hashlib.sha256(request).hexdigest(),
        pins=checked_pins,
    )


def insert_run(connection: sqlite3.Connection, run: NewRun, token: str, at: str) -> None:
    """Write the run (status created, `token` its writer), its pins in order and `run_created`."""
    connection.execute(
        "INSERT INTO runs(run_id, issuer_id, issuer_name, as_of, config_id, cap_usd, request,"
        " request_sha256, status, writer, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'created', ?, ?)",
        (
            run.run_id,
            run.issuer_id,
            run.issuer_name,
            run.as_of,
            run.config_id,
            run.cap_usd,
            run.request,
            run.request_sha256,
            token,
            at,
        ),
    )
    for position, pin in enumerate(run.pins):
        connection.execute(
            "INSERT INTO run_sources(run_id, position, name, sha256, size_bytes, kind)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (run.run_id, position, pin.name, pin.sha256, pin.size_bytes, pin.kind.value),
        )
    insert_event(connection, run.run_id, at, "run_created", {})


def insert_event(
    connection: sqlite3.Connection,
    run_id: str,
    at: str,
    kind: str,
    detail: dict[str, str | int | None],
    module_id: str | None = None,
    attempt: int | None = None,
) -> None:
    connection.execute(
        "INSERT INTO events(run_id, at, kind, module_id, attempt, detail)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (run_id, at, kind, module_id, attempt, detail_to_text(detail)),
    )


def check_name(name: str, value: object) -> str:
    """Return the value when it is a lower-case name of 1 to 64 characters; the message never holds it."""
    if not isinstance(value, str) or _NAME.fullmatch(value) is None:
        raise StoreRefused(f"{name} must be a lower-case name of 1 to 64 characters")
    return value


def check_claim(claim: object) -> Claim:
    """Return the claim when it is a `Claim` of a valid run id and a 32-character lower-case hex token."""
    if (
        not isinstance(claim, Claim)
        or not isinstance(claim.token, str)
        or _TOKEN.fullmatch(claim.token) is None
    ):
        raise StoreRefused("claim must be a Claim holding a 32-character hex token")
    check_identifier("run_id", claim.run_id)
    return claim


def check_message(message: object) -> str | None:
    """Return None, or the message text with each lone surrogate escaped."""
    if message is not None and not isinstance(message, str):
        raise StoreRefused("message must be text or None")
    return None if message is None else safe_text(message)


def check_end(
    claim: object, status: object, reason: object, message: object, allowed: frozenset[str]
) -> tuple[Claim, str | None]:
    """Check a `reject_run` or `end_run` call: the status is in `allowed`, the reason a name."""
    if type(status) is not str or status not in allowed:
        raise StoreRefused("status is not one this call may set")
    check_name("reason", reason)
    return check_claim(claim), check_message(message)


def check_note(
    claim: object,
    kind: object,
    detail: Mapping[str, str | int | None],
    module_id: object,
    attempt: object,
) -> Claim:
    """Check a `record_event` call: the kind is a name and not a state kind, and so on."""
    if check_name("kind", kind) in STATE_KINDS:
        raise StoreRefused("kind must not be one of the run's state kinds")
    detail_to_text(detail)
    if module_id is not None:
        check_identifier("module_id", module_id)
    if attempt is not None and (
        type(attempt) is not int
        or attempt < 1
        or module_id is None
        or attempt > _SQLITE_MAX_INTEGER
    ):
        raise StoreRefused("attempt must be an int of at least 1, and only with a module_id")
    return check_claim(claim)


def gate(
    connection: sqlite3.Connection, run_id: str, token: str | None, allowed: frozenset[str]
) -> str:
    """Inside the write transaction: the run exists (StoreRefused), `token` is its writer unless
    None (StoreFenced), its status is in `allowed` (StoreConflict). Returns the status."""
    rows = connection.execute(
        "SELECT writer, status FROM runs WHERE run_id = ?", (run_id,)
    ).fetchall()
    if not rows:
        raise StoreRefused("no run has that run_id")
    writer, status = rows[0]
    if token is not None and not secrets.compare_digest(writer, token):
        raise StoreFenced("the claim is not the run's writer")
    if status not in allowed:
        raise StoreConflict("the run's status does not allow that write")
    return str(status)


def replace_writer(connection: sqlite3.Connection, run_id: str, token: str, at: str) -> None:
    connection.execute("UPDATE runs SET writer = ? WHERE run_id = ?", (token, run_id))
    insert_event(connection, run_id, at, "writer_replaced", {})


def start(connection: sqlite3.Connection, run_id: str, old_status: str, at: str) -> None:
    """To running: `started_at` keeps its first value; a resume clears the end."""
    connection.execute(
        "UPDATE runs SET status = 'running', started_at = coalesce(started_at, ?),"
        " ended_at = NULL, end_reason = NULL, end_message = NULL WHERE run_id = ?",
        (at, run_id),
    )
    insert_event(connection, run_id, at, "run_started", {"from": old_status})


def end(
    connection: sqlite3.Connection,
    run_id: str,
    status: str,
    reason: str,
    message: str | None,
    at: str,
) -> None:
    """End the run: `run_ended` first (a final run takes no event), then the UPDATE."""
    insert_event(connection, run_id, at, "run_ended", {"status": status, "reason": reason})
    connection.execute(
        "UPDATE runs SET status = ?, ended_at = ?, end_reason = ?, end_message = ?"
        " WHERE run_id = ?",
        (status, at, reason, message, run_id),
    )


def _stored[T](value: T | None, what: str) -> T:
    if value is None:
        raise StoreCorrupt(f"stored {what} is missing")
    return value


def _require_run(connection: sqlite3.Connection, run_id: object) -> str:
    """Return the run id when a run has it; a run is never deleted, so it stays true."""
    checked = check_identifier("run_id", run_id)
    found = connection.execute("SELECT 1 FROM runs WHERE run_id = ?", (checked,)).fetchall()
    if not found:
        raise StoreRefused("no run has that run_id")
    return checked


def read_run(connection: sqlite3.Connection, run_id: object) -> RunRecord:
    checked = _require_run(connection, run_id)
    row = connection.execute(
        "SELECT issuer_id, issuer_name, as_of, config_id, cap_usd, request, request_sha256,"
        " status, end_reason, end_message, created_at, started_at, ended_at"
        " FROM runs WHERE run_id = ?",
        (checked,),
    ).fetchall()[0]
    try:
        as_of = None if row[2] is None else date.fromisoformat(row[2])
    except ValueError:
        raise StoreCorrupt("stored as_of is not a date") from None
    return RunRecord(
        run_id=checked,
        issuer_id=row[0],
        issuer_name=row[1],
        as_of=as_of,
        config_id=row[3],
        cap_usd=_stored(money_from_text(row[4]), "cap_usd"),
        request=row[5],
        request_sha256=row[6],
        status=row[7],
        end_reason=row[8],
        end_message=row[9],
        created_at=_stored(time_from_text(row[10]), "created_at"),
        started_at=time_from_text(row[11]),
        ended_at=time_from_text(row[12]),
    )


def _failed_fields(error: ValidationError) -> str:
    """The field names a pin refusal names; the model's own check has no field and is `kind`."""
    found = error.errors(include_input=False, include_url=False)
    return ", ".join(sorted({str(item["loc"][0]) if item["loc"] else "kind" for item in found}))


def read_pins(connection: sqlite3.Connection, run_id: object) -> tuple[SourcePin, ...]:
    checked = _require_run(connection, run_id)
    rows = connection.execute(
        "SELECT position, name, sha256, size_bytes, kind FROM run_sources"
        " WHERE run_id = ? ORDER BY position",
        (checked,),
    ).fetchall()
    pins: list[SourcePin] = []
    for position, name, sha256, size_bytes, kind in rows:
        stored = {"name": name, "sha256": sha256, "size_bytes": size_bytes, "kind": kind}
        try:
            pins.append(SourcePin.model_validate(stored, strict=False))
        except ValidationError as error:
            raise StoreCorrupt(
                f"run {checked} pin {position} is refused by the source model: "
                f"{_failed_fields(error)}"
            ) from None
    return tuple(pins)


def read_events(connection: sqlite3.Connection, run_id: object) -> tuple[EventRecord, ...]:
    checked = _require_run(connection, run_id)
    rows = connection.execute(
        "SELECT seq, at, kind, module_id, attempt, detail FROM events"
        " WHERE run_id = ? ORDER BY seq",
        (checked,),
    ).fetchall()
    return tuple(
        EventRecord(
            seq=seq,
            run_id=checked,
            at=_stored(time_from_text(at), "event time"),
            kind=kind,
            module_id=module_id,
            attempt=attempt,
            detail=MappingProxyType(detail_from_text(detail)),
        )
        for seq, at, kind, module_id, attempt, detail in rows
    )
