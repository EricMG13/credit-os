"""Attempt and call rows on a connection: the writes run inside the caller's write transaction and
never begin, commit or roll back. Every SQL string is a static literal with `?` parameters, and
nothing here catches `sqlite3.Error`: `db` maps it. Each write's input checks run before the
transaction (`StoreRefused`); the run gate runs in `db`; then the attempt, then the state, then the
write's one clock call."""

import hashlib
import re
import sqlite3
from collections.abc import Callable, Sequence
from decimal import Decimal

from credit_os.provider.types import Compaction, Reply
from credit_os.store import runs
from credit_os.store.codec import detail_to_text, money_from_text, money_to_text, time_to_text
from credit_os.store.errors import StoreConflict, StoreRefused, safe_text
from credit_os.store.records import Claim

_SQLITE_MAX_INTEGER = 2**63 - 1
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _check_count(name: str, value: object, minimum: int) -> int:
    """Return the value when it is exactly `int` from `minimum` to 2**63 - 1; a bool is refused."""
    if type(value) is not int or not minimum <= value <= _SQLITE_MAX_INTEGER:
        raise StoreRefused(f"{name} must be an int from {minimum} to {_SQLITE_MAX_INTEGER}")
    return value


def check_open_attempt(claim: object, module_id: object, request: object) -> tuple[Claim, str]:
    """Check an `open_attempt` call: the claim, the module id, and `request` exactly `bytes`."""
    held = runs.check_claim(claim)
    module = runs.check_identifier("module_id", module_id)
    if type(request) is not bytes:
        raise StoreRefused("request must be bytes")
    return held, module


def check_open_call(
    claim: object,
    module_id: object,
    attempt: object,
    exchange_id: object,
    provider_call_index: object,
    hold_usd: object,
) -> tuple[Claim, str, int, str, int, str]:
    """Check an `open_call` call; returns the claim, module id, attempt, exchange id, provider
    call index and the hold as the codec's text. A missing hold is StoreRefused."""
    held = runs.check_claim(claim)
    module = runs.check_identifier("module_id", module_id)
    number = _check_count("attempt", attempt, 1)
    exchange = runs.check_identifier("exchange_id", exchange_id)
    index = _check_count("provider_call_index", provider_call_index, 0)
    hold = money_to_text(hold_usd) if isinstance(hold_usd, Decimal) else None
    if hold is None:
        raise StoreRefused("hold_usd must be a Decimal")
    return held, module, number, exchange, index, hold


ReplyColumns = tuple[object, ...]


def _optional_text(text: str | None) -> str | None:
    return None if text is None else safe_text(text)


def _reply_columns(reply: Reply) -> ReplyColumns:
    """The reply's call columns, in the order `close_call` writes them (store_reply_key's keys):
    kind, error class, message, the five counts, charge, two times, stop reason, reported model,
    request id, raw. Every codec refusal is StoreRefused."""
    usage, turn = reply.usage, reply.turn
    counts: tuple[int | None, ...] = (None,) * 5
    if usage is not None:
        counts = (
            usage.input_tokens,
            usage.cached_read_tokens,
            usage.cache_write_tokens,
            usage.output_tokens,
            usage.reasoning_tokens,
        )
    for count in counts:
        if count is not None:
            _check_count("a reply count", count, 0)
    if reply.raw is not None and type(reply.raw) is not bytes:
        raise StoreRefused("raw must be bytes or None")
    return (
        reply.kind,
        _optional_text(reply.error_class),
        _optional_text(reply.message),
        *counts,
        money_to_text(reply.billed_usd),
        time_to_text(reply.started_at),
        time_to_text(reply.finished_at),
        None if turn is None else turn.stop_reason,
        None if turn is None else _optional_text(turn.reported_model),
        None if turn is None else _optional_text(turn.request_id),
        reply.raw,
    )


def check_close_call(
    claim: object, module_id: object, attempt: object, call_index: object, reply: object
) -> tuple[
    Claim,
    str,
    int,
    int,
    ReplyColumns,
    tuple[tuple[str, str | None, tuple[int | None, ...], str | None, str], ...],
]:
    """Check a `close_call` call; returns the claim, module id, attempt, call index, the reply's
    call columns and its compactions as stored fields, all built before BEGIN. A reply the codecs
    cannot store is StoreRefused, so the call stays open."""
    held = runs.check_claim(claim)
    module = runs.check_identifier("module_id", module_id)
    number = _check_count("attempt", attempt, 1)
    index = _check_count("call_index", call_index, 0)
    if type(reply) is not Reply:
        raise StoreRefused("reply must be a Reply")
    columns = _reply_columns(reply)
    return (
        held,
        module,
        number,
        index,
        columns,
        tuple(_compaction_fields(item) for item in reply.compactions),
    )


def open_attempt(
    connection: sqlite3.Connection,
    run_id: str,
    module_id: str,
    request: bytes,
    now: Callable[[], str],
) -> int:
    """Open the module's next attempt and write `attempt_opened`; return its number. The latest
    attempt open with the same request bytes is returned as it is, with no write and no clock
    call (U17). The latest attempt open with other bytes, replied or accepted is StoreConflict."""
    latest = connection.execute(
        "SELECT attempt, state, request FROM attempts WHERE run_id = ? AND module_id = ?"
        " ORDER BY attempt DESC LIMIT 1",
        (run_id, module_id),
    ).fetchall()
    number = 1
    if latest:
        last, state, stored = latest[0]
        if state == "open" and stored == request:
            return int(last)
        if state in ("open", "replied", "accepted"):
            raise StoreConflict("the module's latest attempt is not closed as failed or rejected")
        number = int(last) + 1
    at = now()
    connection.execute(
        "INSERT INTO attempts(run_id, module_id, attempt, request, request_sha256, state,"
        " opened_at) VALUES (?, ?, ?, ?, ?, 'open', ?)",
        (run_id, module_id, number, request, hashlib.sha256(request).hexdigest(), at),
    )
    runs.insert_event(connection, run_id, at, "attempt_opened", {}, module_id, number)
    return number


def open_call(
    connection: sqlite3.Connection,
    run_id: str,
    module_id: str,
    attempt: int,
    exchange_id: str,
    provider_call_index: int,
    hold_usd: str,
    now: Callable[[], str],
) -> int:
    """Insert the attempt's next call, from 0, and return its index. The attempt must exist
    (StoreRefused) and be open; it must have no open call; and the run must not have used
    `(exchange_id, provider_call_index)` (each StoreConflict). No event is written."""
    states = connection.execute(
        "SELECT state FROM attempts WHERE run_id = ? AND module_id = ? AND attempt = ?",
        (run_id, module_id, attempt),
    ).fetchall()
    if not states:
        raise StoreRefused("the run has no such attempt")
    if states[0][0] != "open":
        raise StoreConflict("the attempt is not open")
    counts = connection.execute(
        "SELECT count(*), count(*) FILTER (WHERE closed_at IS NULL) FROM calls"
        " WHERE run_id = ? AND module_id = ? AND attempt = ?",
        (run_id, module_id, attempt),
    ).fetchall()[0]
    if counts[1]:
        raise StoreConflict("the attempt has an open call")
    used = connection.execute(
        "SELECT 1 FROM calls WHERE run_id = ? AND exchange_id = ? AND provider_call_index = ?",
        (run_id, exchange_id, provider_call_index),
    ).fetchall()
    if used:
        raise StoreConflict("the run has already used that exchange and provider call index")
    connection.execute(
        "INSERT INTO calls(run_id, module_id, attempt, call_index, exchange_id,"
        " provider_call_index, hold_usd, opened_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            run_id,
            module_id,
            attempt,
            counts[0],
            exchange_id,
            provider_call_index,
            hold_usd,
            now(),
        ),
    )
    return int(counts[0])


def check_compactions(
    claim: object, compactions: object
) -> tuple[Claim, tuple[tuple[str, str | None, tuple[int | None, ...], str | None, str], ...]]:
    """Check a `record_compactions` call: the claim, `compactions` a `tuple` or a `list` (never a
    `str` or `bytes`) of exact `Compaction`s. Returns the claim and each compaction as its
    stored fields: (event id, supersedes, the four counts, billed text, outcome)."""
    held = runs.check_claim(claim)
    if not isinstance(compactions, tuple | list) or type(compactions) not in (tuple, list):
        raise StoreRefused("compactions must be a tuple or a list")
    return held, tuple(_compaction_fields(item) for item in compactions)


def _compaction_fields(
    item: object,
) -> tuple[str, str | None, tuple[int | None, ...], str | None, str]:
    if type(item) is not Compaction:
        raise StoreRefused("each compaction must be a Compaction")
    usage = item.usage
    counts = (
        usage.input_tokens,
        usage.cached_read_tokens,
        usage.cache_write_tokens,
        usage.output_tokens,
    )
    for count in counts:
        if count is not None:
            _check_count("a compaction count", count, 0)
    supersedes = None if item.supersedes is None else safe_text(item.supersedes)
    return (
        safe_text(item.event_id),
        supersedes,
        counts,
        money_to_text(item.billed_usd),
        item.outcome,
    )


def insert_compactions(
    connection: sqlite3.Connection,
    run_id: str,
    compactions: Sequence[tuple[str, str | None, tuple[int | None, ...], str | None, str]],
    call_key: tuple[str, int, int] | None,
) -> None:
    """Insert each compaction in order at the run's next position, from 0, with the call key
    (module id, attempt, call index) or none. No clock call and no event: a compaction has no
    time column. A repeat is an event id whose stored text the run holds, or one stored earlier
    in this call: a no-op when the five fields are equal (compared as `Compaction` values, so
    0.0020 equals 0.002), StoreConflict when the stored id holds a backslash (U12, U16) or
    anything differs. The caller's transaction then rolls back the whole call."""
    module, attempt, index = call_key if call_key is not None else (None, None, None)
    for event_id, supersedes, counts, billed, outcome in compactions:
        stored = connection.execute(
            "SELECT input_tokens, cached_read_tokens, cache_write_tokens, output_tokens,"
            " billed_usd, outcome, supersedes FROM compactions WHERE run_id = ? AND event_id = ?",
            (run_id, event_id),
        ).fetchall()
        if stored:
            row = stored[0]
            same = (
                "\\" not in event_id
                and tuple(row[:4]) == counts
                and money_from_text(row[4]) == money_from_text(billed)
                and (row[5], row[6]) == (outcome, supersedes)
            )
            if not same:
                raise StoreConflict("the run holds a different compaction with that event id")
            continue
        position = connection.execute(
            "SELECT coalesce(max(position), -1) + 1 FROM compactions WHERE run_id = ?", (run_id,)
        ).fetchall()[0][0]
        connection.execute(
            "INSERT INTO compactions(run_id, event_id, position, module_id, attempt, call_index,"
            " input_tokens, cached_read_tokens, cache_write_tokens, output_tokens, billed_usd,"
            " outcome, supersedes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                event_id,
                position,
                module,
                attempt,
                index,
                *counts,
                billed,
                outcome,
                supersedes,
            ),
        )


def close_call(
    connection: sqlite3.Connection,
    run_id: str,
    module_id: str,
    attempt: int,
    call_index: int,
    columns: ReplyColumns,
    compactions: Sequence[tuple[str, str | None, tuple[int | None, ...], str | None, str]],
    now: Callable[[], str],
) -> None:
    """Close the call with the reply's columns and `closed_at`, after inserting the reply's
    compactions with the call's key. The attempt and the call must exist (StoreRefused); the call
    must be open and the attempt open (StoreConflict). A compaction conflict raises before the
    call's columns are written, and the caller's transaction rolls everything back. The one clock
    call (`closed_at`) follows the compactions, so a refused call never reads the clock. No event."""
    states = connection.execute(
        "SELECT state FROM attempts WHERE run_id = ? AND module_id = ? AND attempt = ?",
        (run_id, module_id, attempt),
    ).fetchall()
    if not states:
        raise StoreRefused("the run has no such attempt")
    calls = connection.execute(
        "SELECT closed_at FROM calls"
        " WHERE run_id = ? AND module_id = ? AND attempt = ? AND call_index = ?",
        (run_id, module_id, attempt, call_index),
    ).fetchall()
    if not calls:
        raise StoreRefused("the attempt has no such call")
    if calls[0][0] is not None:
        raise StoreConflict("the call is already closed")
    if states[0][0] != "open":
        raise StoreConflict("the attempt is not open")
    insert_compactions(connection, run_id, compactions, (module_id, attempt, call_index))
    closed_at = now()
    connection.execute(
        "UPDATE calls SET closed_at = ?, kind = ?, error_class = ?, message = ?,"
        " input_tokens = ?, cached_read_tokens = ?, cache_write_tokens = ?, output_tokens = ?,"
        " reasoning_tokens = ?, billed_usd = ?, started_at = ?, finished_at = ?, stop_reason = ?,"
        " reported_model = ?, request_id = ?, raw = ?"
        " WHERE run_id = ? AND module_id = ? AND attempt = ? AND call_index = ?",
        (closed_at, *columns, run_id, module_id, attempt, call_index),
    )


def check_record_reply(
    claim: object, module_id: object, attempt: object, reply: object
) -> tuple[Claim, str, int, bytes]:
    """Check a `record_reply` call: the claim, the module id, the attempt, and `reply` exactly
    `bytes`."""
    held = runs.check_claim(claim)
    module = runs.check_identifier("module_id", module_id)
    number = _check_count("attempt", attempt, 1)
    if type(reply) is not bytes:
        raise StoreRefused("reply must be bytes")
    return held, module, number, reply


def check_record_verdict(
    claim: object,
    module_id: object,
    attempt: object,
    reply_sha256: object,
    accepted: object,
    issues: object,
) -> tuple[Claim, str, int, str, bool, str]:
    """Check a `record_verdict` call; returns the claim, module id, attempt, the reply hash,
    the verdict and the issues as stored text: "[" + each item's `detail_to_text` joined by ","
    + "]"."""
    held = runs.check_claim(claim)
    module = runs.check_identifier("module_id", module_id)
    number = _check_count("attempt", attempt, 1)
    if type(reply_sha256) is not str or _SHA256.fullmatch(reply_sha256) is None:
        raise StoreRefused("reply_sha256 must be 64 lower-case hex characters")
    if type(accepted) is not bool:
        raise StoreRefused("accepted must be a bool")
    if not isinstance(issues, tuple | list) or type(issues) not in (tuple, list):
        raise StoreRefused("issues must be a tuple or a list of mappings")
    text = "[" + ",".join(detail_to_text(item) for item in issues) + "]"
    return held, module, number, reply_sha256, accepted, text


def check_fail_attempt(
    claim: object, module_id: object, attempt: object, reason: object
) -> tuple[Claim, str, int, str]:
    """Check a `fail_attempt` call: the claim, the module id, the attempt, and a name reason."""
    held = runs.check_claim(claim)
    module = runs.check_identifier("module_id", module_id)
    number = _check_count("attempt", attempt, 1)
    return held, module, number, runs.check_name("reason", reason)


def _attempt_state(
    connection: sqlite3.Connection, run_id: str, module_id: str, attempt: int
) -> tuple[str, str | None]:
    """The attempt's state and stored reply hash; StoreRefused when the run has no such attempt."""
    rows = connection.execute(
        "SELECT state, reply_sha256 FROM attempts WHERE run_id = ? AND module_id = ?"
        " AND attempt = ?",
        (run_id, module_id, attempt),
    ).fetchall()
    if not rows:
        raise StoreRefused("the run has no such attempt")
    return str(rows[0][0]), rows[0][1]


def record_reply(
    connection: sqlite3.Connection,
    run_id: str,
    module_id: str,
    attempt: int,
    reply: bytes,
    now: Callable[[], str],
) -> str:
    """Move the attempt from open to replied with the reply bytes and their SHA-256, write
    `attempt_replied`, and return the hash. The attempt must exist (StoreRefused), be open and
    have no open call (StoreConflict). The one clock call follows those checks."""
    state, _ = _attempt_state(connection, run_id, module_id, attempt)
    if state != "open":
        raise StoreConflict("the attempt is not open")
    open_calls = connection.execute(
        "SELECT count(*) FROM calls WHERE run_id = ? AND module_id = ? AND attempt = ?"
        " AND closed_at IS NULL",
        (run_id, module_id, attempt),
    ).fetchall()[0][0]
    if open_calls:
        raise StoreConflict("the attempt has an open call")
    sha = hashlib.sha256(reply).hexdigest()
    at = now()
    connection.execute(
        "UPDATE attempts SET state = 'replied', reply = ?, reply_sha256 = ?, replied_at = ?"
        " WHERE run_id = ? AND module_id = ? AND attempt = ?",
        (reply, sha, at, run_id, module_id, attempt),
    )
    runs.insert_event(connection, run_id, at, "attempt_replied", {}, module_id, attempt)
    return sha


def record_verdict(
    connection: sqlite3.Connection,
    run_id: str,
    module_id: str,
    attempt: int,
    reply_sha256: str,
    accepted: bool,
    issues: str,
    now: Callable[[], str],
) -> None:
    """Move the attempt from replied to accepted or rejected with the issues text, write the
    matching event. The attempt must exist (StoreRefused), be replied and hold that reply hash
    (StoreConflict). The one clock call follows those checks."""
    state, stored = _attempt_state(connection, run_id, module_id, attempt)
    if state != "replied":
        raise StoreConflict("the attempt is not replied")
    if stored != reply_sha256:
        raise StoreConflict("the attempt holds another reply")
    at = now()
    new_state = "accepted" if accepted else "rejected"
    connection.execute(
        "UPDATE attempts SET state = ?, issues = ?, closed_at = ?"
        " WHERE run_id = ? AND module_id = ? AND attempt = ?",
        (new_state, issues, at, run_id, module_id, attempt),
    )
    runs.insert_event(connection, run_id, at, f"attempt_{new_state}", {}, module_id, attempt)


def fail_attempt(
    connection: sqlite3.Connection,
    run_id: str,
    module_id: str,
    attempt: int,
    reason: str,
    now: Callable[[], str],
) -> None:
    """Move the attempt from open to failed with the reason, write `attempt_failed`. The attempt
    must exist (StoreRefused) and be open (StoreConflict). An open call of the attempt stays
    open: its spend is unknown until settled (D7)."""
    state, _ = _attempt_state(connection, run_id, module_id, attempt)
    if state != "open":
        raise StoreConflict("the attempt is not open")
    at = now()
    connection.execute(
        "UPDATE attempts SET state = 'failed', fail_reason = ?, closed_at = ?"
        " WHERE run_id = ? AND module_id = ? AND attempt = ?",
        (reason, at, run_id, module_id, attempt),
    )
    runs.insert_event(
        connection, run_id, at, "attempt_failed", {"reason": reason}, module_id, attempt
    )
