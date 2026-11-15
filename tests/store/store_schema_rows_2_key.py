"""Answer key (PR 3a-b1): migration 2's setups, inserts, attempt updates and call closes.

Written by the controller from invented values before the code existed. Each row runs through a raw
`sqlite3` connection opened with `autocommit=True` and `PRAGMA foreign_keys = ON` (unless a group
says OFF), migrated to 2 by running `schema.MIGRATION_1` then `schema.MIGRATION_2` statement by
statement, never through the store. A refused row is `sqlite3.IntegrityError` whose message starts
with the row's expected text, and every table reads back unchanged after it. Implementers do not edit
this file or weaken a comparison against it.

Setups, each built in this order on a fresh connection:
- RUNNING_RUN: `RUN` (migration 1's rows key) inserted, then `UPDATE runs SET status = 'running',
  started_at = ?` with T1.
- WITH_ATTEMPT: RUNNING_RUN, then ATTEMPT.
- WITH_CALL: WITH_ATTEMPT, then CALL.
- FULL: WITH_CALL, then COMPACTION, then ATTEMPT_2 (another module, open, no call).

The statements at the end are shared with 3a-b2's key (store_schema_triggers_2_key.py) and
3a-b3's (store_schema_masked_2_key.py), which build their rows the same way.
"""

from store_schema_rows_key import _BAD_TIMES, RUN, SHA, T1, T2

SHA_2 = "cd" * 32
CHECK = "CHECK constraint failed"

ATTEMPT: dict[str, object] = {
    "run_id": "run-001",
    "module_id": "CP-1",
    "attempt": 1,
    "request": b"request bytes\r\n",
    "request_sha256": SHA,
    "state": "open",
    "reply": None,
    "reply_sha256": None,
    "issues": None,
    "fail_reason": None,
    "opened_at": T1,
    "replied_at": None,
    "closed_at": None,
}
ATTEMPT_2: dict[str, object] = {**ATTEMPT, "module_id": "CP-2"}
CALL: dict[str, object] = {
    "run_id": "run-001",
    "module_id": "CP-1",
    "attempt": 1,
    "call_index": 0,
    "exchange_id": "ex-1",
    "provider_call_index": 0,
    "hold_usd": "0.5",
    "opened_at": T1,
}
COMPACTION: dict[str, object] = {
    "run_id": "run-001",
    "event_id": "ev-1",
    "position": 0,
    "module_id": "CP-1",
    "attempt": 1,
    "call_index": 0,
    "outcome": "done",
}
_RUN_ID = RUN["run_id"]

# --- Inserts --------------------------------------------------------------------------------------

# Accepted on FULL: (label, table, the base row with these columns replaced). Base rows: attempts
# ATTEMPT_2's module "CP-3" (a new module, attempt 1); calls CALL on ATTEMPT_2 (module "CP-2");
# compactions COMPACTION at position 1 with event_id "ev-2".
INSERT_BASES: dict[str, dict[str, object]] = {
    "attempts": {**ATTEMPT, "module_id": "CP-3"},
    "calls": {**CALL, "module_id": "CP-2", "exchange_id": "ex-2"},
    "compactions": {**COMPACTION, "event_id": "ev-2", "position": 1},
}
ACCEPTED_INSERTS: tuple[tuple[str, str, dict[str, object]], ...] = (
    ("module id of every class", "attempts", {"module_id": "Cp_7.b-x"}),
    ("module id 128 characters", "attempts", {"module_id": "m" * 128}),
    ("empty request", "attempts", {"request": b""}),
    (
        "opened at the last microsecond of a year",
        "attempts",
        {"opened_at": "2026-12-31T23:59:59.999999Z"},
    ),
    ("call with a provider index unlike its own", "calls", {"provider_call_index": 5}),
    ("largest provider index", "calls", {"provider_call_index": 2**63 - 1}),
    ("zero hold", "calls", {"hold_usd": "0"}),
    ("hold of 64 characters", "calls", {"hold_usd": "1" + "0" * 63}),
    ("hold with cents", "calls", {"hold_usd": "0.50"}),
    ("exchange id of every class, 128 characters", "calls", {"exchange_id": "Ex_7.b-" + "x" * 121}),
    (
        "same exchange, another provider index",
        "calls",
        {"exchange_id": "ex-1", "provider_call_index": 1},
    ),
    (
        "compaction from Model.close(), no call",
        "compactions",
        {"module_id": None, "attempt": None, "call_index": None},
    ),
    ("event id a space", "compactions", {"event_id": " "}),
    ("event id not ASCII", "compactions", {"event_id": "év"}),
    ("supersedes another id", "compactions", {"supersedes": "ev-1"}),
    ("supersedes an id never recorded", "compactions", {"supersedes": "ev-404"}),
    (
        "zero charge, all counts",
        "compactions",
        {
            "input_tokens": 0,
            "cached_read_tokens": 0,
            "cache_write_tokens": 0,
            "output_tokens": 0,
            "billed_usd": "0",
        },
    ),
    ("failed outcome", "compactions", {"outcome": "failed"}),
    ("unfinished, nothing known", "compactions", {"outcome": "unfinished"}),
)

_NN = "NOT NULL constraint failed: "
# Refused on FULL: (label, table, replaced columns, expected message start). Each row passes every
# trigger, so the constraint named is what refuses it.
REFUSED_INSERTS: tuple[tuple[str, str, dict[str, object], str], ...] = (
    ("module id empty", "attempts", {"module_id": ""}, CHECK),
    ("module id with a space", "attempts", {"module_id": "CP 3"}, CHECK),
    ("module id 129 characters", "attempts", {"module_id": "m" * 129}, CHECK),
    ("module id NUL tail", "attempts", {"module_id": "CP-3\x00x"}, CHECK),
    ("module id not ASCII", "attempts", {"module_id": "CP-é"}, CHECK),
    ("request missing", "attempts", {"request": None}, _NN + "attempts.request"),
    (
        "request as text",
        "attempts",
        {"request": "text"},
        "cannot store TEXT value in BLOB column attempts.request",
    ),
    ("request hash upper case", "attempts", {"request_sha256": "AB" * 32}, CHECK),
    ("request hash short", "attempts", {"request_sha256": "ab" * 31}, CHECK),
    ("request hash NUL tail", "attempts", {"request_sha256": SHA + "\x00"}, CHECK),
    ("request hash missing", "attempts", {"request_sha256": None}, _NN + "attempts.request_sha256"),
    (
        "open with a reply",
        "attempts",
        {"reply": b"r", "reply_sha256": SHA, "replied_at": T2},
        CHECK,
    ),
    ("open with a reply hash only", "attempts", {"reply_sha256": SHA}, CHECK),
    ("open with a reply time only", "attempts", {"replied_at": T2}, CHECK),
    ("open with issues", "attempts", {"issues": "[]"}, CHECK),
    ("open with a failure reason", "attempts", {"fail_reason": "interrupted"}, CHECK),
    ("open with a close time", "attempts", {"closed_at": T2}, CHECK),
    ("opened_at missing", "attempts", {"opened_at": None}, _NN + "attempts.opened_at"),
    *((f"opened at {label}", "attempts", {"opened_at": t}, CHECK) for label, t in _BAD_TIMES),
    ("exchange id empty", "calls", {"exchange_id": ""}, CHECK),
    ("exchange id with a space", "calls", {"exchange_id": "ex 2"}, CHECK),
    ("exchange id 129 characters", "calls", {"exchange_id": "e" * 129}, CHECK),
    ("exchange id NUL tail", "calls", {"exchange_id": "ex-2\x00x"}, CHECK),
    ("exchange id missing", "calls", {"exchange_id": None}, _NN + "calls.exchange_id"),
    ("provider index negative", "calls", {"provider_call_index": -1}, CHECK),
    (
        "provider index missing",
        "calls",
        {"provider_call_index": None},
        _NN + "calls.provider_call_index",
    ),
    (
        "provider index as text",
        "calls",
        {"provider_call_index": "first"},
        "cannot store TEXT value in INTEGER column calls.provider_call_index",
    ),
    ("hold missing", "calls", {"hold_usd": None}, _NN + "calls.hold_usd"),
    ("hold negative", "calls", {"hold_usd": "-1"}, CHECK),
    ("hold leading zero", "calls", {"hold_usd": "01"}, CHECK),
    ("hold leading zeros", "calls", {"hold_usd": "007"}, CHECK),
    ("hold exponent", "calls", {"hold_usd": "1e3"}, CHECK),
    ("hold no whole part", "calls", {"hold_usd": ".5"}, CHECK),
    ("hold no fraction digits", "calls", {"hold_usd": "5."}, CHECK),
    ("hold two points", "calls", {"hold_usd": "1.2.3"}, CHECK),
    ("hold empty", "calls", {"hold_usd": ""}, CHECK),
    ("hold with a space", "calls", {"hold_usd": " 1"}, CHECK),
    ("hold 65 characters", "calls", {"hold_usd": "1" * 65}, CHECK),
    ("hold NUL tail", "calls", {"hold_usd": "20\x00x"}, CHECK),
    ("call opened_at missing", "calls", {"opened_at": None}, _NN + "calls.opened_at"),
    *((f"call opened at {label}", "calls", {"opened_at": t}, CHECK) for label, t in _BAD_TIMES),
    ("open call with a kind", "calls", {"kind": "ok", "stop_reason": "end"}, CHECK),
    ("open call with a message", "calls", {"message": "x"}, CHECK),
    ("open call with a count", "calls", {"input_tokens": 1}, CHECK),
    ("open call with a charge", "calls", {"billed_usd": "0"}, CHECK),
    ("open call with raw bytes", "calls", {"raw": b""}, CHECK),
    ("open call with a start time", "calls", {"started_at": T2}, CHECK),
    ("event id empty", "compactions", {"event_id": ""}, CHECK),
    ("event id missing", "compactions", {"event_id": None}, _NN + "compactions.event_id"),
    ("call key without a call index", "compactions", {"call_index": None}, CHECK),
    ("call key with only a module", "compactions", {"attempt": None, "call_index": None}, CHECK),
    *(
        (f"compaction {c} negative", "compactions", dict[str, object]({c: -1}), CHECK)
        for c in ("input_tokens", "cached_read_tokens", "cache_write_tokens", "output_tokens")
    ),
    (
        "compaction count as text",
        "compactions",
        {"input_tokens": "one"},
        "cannot store TEXT value in INTEGER column compactions.input_tokens",
    ),
    ("compaction charge negative", "compactions", {"billed_usd": "-0.5"}, CHECK),
    ("compaction charge exponent", "compactions", {"billed_usd": "5E-1"}, CHECK),
    ("compaction charge 65 characters", "compactions", {"billed_usd": "1" * 65}, CHECK),
    ("outcome unknown", "compactions", {"outcome": "lost"}, CHECK),
    ("outcome missing", "compactions", {"outcome": None}, _NN + "compactions.outcome"),
    ("supersedes empty", "compactions", {"supersedes": ""}, CHECK),
    ("supersedes itself", "compactions", {"supersedes": "ev-2"}, CHECK),
    (
        "unfinished with a count",
        "compactions",
        {"outcome": "unfinished", "output_tokens": 1},
        CHECK,
    ),
    (
        "unfinished with a zero charge",
        "compactions",
        {"outcome": "unfinished", "billed_usd": "0"},
        CHECK,
    ),
    (
        "unfinished superseding",
        "compactions",
        {"outcome": "unfinished", "supersedes": "ev-1"},
        CHECK,
    ),
)

# --- Updates --------------------------------------------------------------------------------------

_REPLIED: dict[str, object] = {
    "state": "replied",
    "reply": b"reply\n",
    "reply_sha256": SHA_2,
    "replied_at": T2,
}
_FAILED: dict[str, object] = {"state": "failed", "fail_reason": "interrupted", "closed_at": T2}
_ACCEPTED: dict[str, object] = {"state": "accepted", "issues": "[]", "closed_at": T2}
_REJECTED: dict[str, object] = {
    "state": "rejected",
    "issues": '[{"code":"x","line":3}]',
    "closed_at": T2,
}
# How ATTEMPT reaches each state on WITH_ATTEMPT (no call): updates in order, WHERE on its key.
ATTEMPT_STATES: dict[str, tuple[dict[str, object], ...]] = {
    "open": (),
    "replied": (_REPLIED,),
    "failed": (_FAILED,),
    "accepted": (_REPLIED, _ACCEPTED),
    "rejected": (_REPLIED, _REJECTED),
}
ALLOWED_ATTEMPT_MOVES: tuple[tuple[str, str], ...] = (
    ("open", "replied"),
    ("open", "failed"),
    ("replied", "accepted"),
    ("replied", "rejected"),
)
ATTEMPT_MOVE_MESSAGE = "attempts: that state move is not allowed"
ATTEMPT_FINAL_MESSAGE = "attempts: a failed, accepted or rejected attempt never changes"
ATTEMPT_REPLY_MESSAGE = "attempts: a reply never changes"
# Every other ordered pair (source, target), a state to itself included (21 pairs), the source
# reached by ATTEMPT_STATES and the target's own update (the last one in ATTEMPT_STATES[target], or
# for "open": {"state": "open"}) applied, is refused with one of refused_move_messages(source,
# target): several triggers can apply and SQLite does not promise which fires first.


def refused_move_messages(source: str, target: str) -> tuple[str, ...]:
    """The messages a refused move may give: the move rule always; the final rule from a final
    state; the reply rule when the target sets a reply over one already held."""
    messages = [ATTEMPT_MOVE_MESSAGE]
    if source in ("failed", "accepted", "rejected"):
        messages.append(ATTEMPT_FINAL_MESSAGE)
    if target == "replied" and source in ("replied", "accepted", "rejected"):
        messages.append(ATTEMPT_REPLY_MESSAGE)
    return tuple(messages)


# Refused on WITH_ATTEMPT after ATTEMPT reaches `source`: (label, source, update, expected start).
REFUSED_ATTEMPT_UPDATES: tuple[tuple[str, str, dict[str, object], str], ...] = (
    ("replied without a reply", "open", {"state": "replied", "replied_at": T2}, CHECK),
    (
        "replied without a reply hash",
        "open",
        {"state": "replied", "reply": b"r", "replied_at": T2},
        CHECK,
    ),
    (
        "replied without a reply time",
        "open",
        {"state": "replied", "reply": b"r", "reply_sha256": SHA_2},
        CHECK,
    ),
    ("reply hash upper case", "open", {**_REPLIED, "reply_sha256": "CD" * 32}, CHECK),
    (
        "reply as text",
        "open",
        {**_REPLIED, "reply": "text"},
        "cannot store TEXT value in BLOB column attempts.reply",
    ),
    *(
        (f"replied at {label}", "open", {**_REPLIED, "replied_at": t}, CHECK)
        for label, t in _BAD_TIMES
    ),
    ("replied with a close time", "open", {**_REPLIED, "closed_at": T2}, CHECK),
    ("failed without a reason", "open", {"state": "failed", "closed_at": T2}, CHECK),
    (
        "failed without a close time",
        "open",
        {"state": "failed", "fail_reason": "interrupted"},
        CHECK,
    ),
    (
        "failed with a reply",
        "open",
        {**_FAILED, "reply": b"r", "reply_sha256": SHA_2, "replied_at": T2},
        CHECK,
    ),
    ("failed with issues", "open", {**_FAILED, "issues": "[]"}, CHECK),
    ("reason upper case", "open", {**_FAILED, "fail_reason": "Interrupted"}, CHECK),
    ("reason leading digit", "open", {**_FAILED, "fail_reason": "1x"}, CHECK),
    ("reason leading underscore", "open", {**_FAILED, "fail_reason": "_x"}, CHECK),
    ("reason 65 characters", "open", {**_FAILED, "fail_reason": "r" * 65}, CHECK),
    ("reason empty", "open", {**_FAILED, "fail_reason": ""}, CHECK),
    *(
        (f"failed closed at {label}", "open", {**_FAILED, "closed_at": t}, CHECK)
        for label, t in _BAD_TIMES
    ),
    ("accepted without issues", "replied", {"state": "accepted", "closed_at": T2}, CHECK),
    ("accepted without a close time", "replied", {"state": "accepted", "issues": "[]"}, CHECK),
    ("issues an object", "replied", {**_ACCEPTED, "issues": "{}"}, CHECK),
    ("issues not closed", "replied", {**_ACCEPTED, "issues": "[{}"}, CHECK),
    ("issues not ASCII", "replied", {**_ACCEPTED, "issues": '["é"]'}, CHECK),
    ("issues empty", "replied", {**_ACCEPTED, "issues": ""}, CHECK),
    ("rejected with a failure reason", "replied", {**_REJECTED, "fail_reason": "late"}, CHECK),
)

# Closing CALL on WITH_CALL: `UPDATE calls SET closed_at = ?, <columns>` with T2 and the row's
# columns, refused with the expected start; every table unchanged. CLOSED_OK is a valid close.
CLOSED_OK: dict[str, object] = {"kind": "ok", "stop_reason": "end"}
REFUSED_CLOSES: tuple[tuple[str, dict[str, object], str], ...] = (
    ("closed without a kind", {}, CHECK),
    (
        "kind unknown",
        {"kind": "done", "error_class": "X"},
        CHECK,
    ),  # error class set: only the kind CHECK applies
    ("ok without a stop reason", {"kind": "ok"}, CHECK),
    ("ok with an error class", {**CLOSED_OK, "error_class": "X"}, CHECK),
    ("stop reason unknown", {"kind": "ok", "stop_reason": "stop"}, CHECK),
    ("not_sent without an error class", {"kind": "not_sent"}, CHECK),
    ("error class empty", {"kind": "not_sent", "error_class": ""}, CHECK),
    (
        "not_sent with a stop reason",
        {"kind": "not_sent", "error_class": "X", "stop_reason": "end"},
        CHECK,
    ),
    (
        "not_sent with a reported model",
        {"kind": "not_sent", "error_class": "X", "reported_model": "m"},
        CHECK,
    ),
    (
        "not_sent with a request id",
        {"kind": "not_sent", "error_class": "X", "request_id": "r"},
        CHECK,
    ),
    *(
        (f"{kind} with {c}", {"kind": kind, "error_class": "X", c: 0}, CHECK)
        for kind in ("not_sent", "sent_unknown")
        for c in (
            "input_tokens",
            "cached_read_tokens",
            "cache_write_tokens",
            "output_tokens",
            "reasoning_tokens",
        )
    ),
    (
        "not_sent with a zero charge",
        {"kind": "not_sent", "error_class": "X", "billed_usd": "0"},
        CHECK,
    ),
    (
        "sent_unknown with a zero charge",
        {"kind": "sent_unknown", "error_class": "X", "billed_usd": "0"},
        CHECK,
    ),
    ("sent_usage with neither count nor charge", {"kind": "sent_usage", "error_class": "X"}, CHECK),
    (
        "sent_usage with a stop reason",
        {"kind": "sent_usage", "error_class": "X", "billed_usd": "0", "stop_reason": "end"},
        CHECK,
    ),
    *(
        (f"{c} negative", {**CLOSED_OK, c: -1}, CHECK)
        for c in (
            "input_tokens",
            "cached_read_tokens",
            "cache_write_tokens",
            "output_tokens",
            "reasoning_tokens",
        )
    ),
    (
        "count as text",
        {**CLOSED_OK, "output_tokens": "many"},
        "cannot store TEXT value in INTEGER column calls.output_tokens",
    ),
    ("charge negative", {**CLOSED_OK, "billed_usd": "-1"}, CHECK),
    ("charge leading zeros", {**CLOSED_OK, "billed_usd": "00.5"}, CHECK),
    ("charge exponent", {**CLOSED_OK, "billed_usd": "1E+3"}, CHECK),
    ("charge 65 characters", {**CLOSED_OK, "billed_usd": "0." + "1" * 63}, CHECK),
    ("raw as text", {**CLOSED_OK, "raw": "x"}, "cannot store TEXT value in BLOB column calls.raw"),
    *((f"started at {label}", {**CLOSED_OK, "started_at": t}, CHECK) for label, t in _BAD_TIMES),
    *((f"finished at {label}", {**CLOSED_OK, "finished_at": t}, CHECK) for label, t in _BAD_TIMES),
    *((f"call closed at {label}", {**CLOSED_OK, "closed_at": t}, CHECK) for label, t in _BAD_TIMES),
)
# An update that leaves CALL open but sets a reply field (no closed_at): refused, CHECK.
REFUSED_OPEN_CALL_UPDATES: tuple[tuple[str, dict[str, object]], ...] = (
    ("kind on an open call", {"kind": "ok", "stop_reason": "end"}),
    ("message on an open call", {"message": "x"}),
    ("charge on an open call", {"billed_usd": "0"}),
    ("raw on an open call", {"raw": b"x"}),
)
# In REFUSED_CLOSES the update sets closed_at to T2 unless the row names its own closed_at.

# --- Statements shared with 3a-b2 and 3a-b3 ----------------------------------------------------

Statement = tuple[str, tuple[object, ...]]
STOP = (
    "UPDATE runs SET status = 'stopped', ended_at = ?, end_reason = 'cap' WHERE run_id = 'run-001'",
    (T2,),
)
A1 = "run_id = 'run-001' AND module_id = 'CP-1' AND attempt = 1"
C0 = A1 + " AND call_index = 0"
FAIL_A1 = (
    f"UPDATE attempts SET state = 'failed', fail_reason = 'interrupted', closed_at = ? WHERE {A1}",
    (T2,),
)
REPLY_A1 = (
    f"UPDATE attempts SET state = 'replied', reply = x'72', reply_sha256 = ?, replied_at = ? WHERE {A1}",
    (SHA_2, T2),
)
ACCEPT_A1 = (
    f"UPDATE attempts SET state = 'accepted', issues = '[]', closed_at = ? WHERE {A1}",
    (T2,),
)
CLOSE_C0 = (f"UPDATE calls SET closed_at = ?, kind = 'ok', stop_reason = 'end' WHERE {C0}", (T2,))
ATTEMPT_COLUMNS = (
    "run_id, module_id, attempt, request, request_sha256, state, reply, reply_sha256, issues, fail_reason,"
    " opened_at, replied_at, closed_at"
)
ATTEMPT_INSERT = (
    f"INSERT INTO attempts({ATTEMPT_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


def attempt_values(**changes: object) -> tuple[object, ...]:
    """ATTEMPT's values in ATTEMPT_COLUMNS order, with `changes` applied."""
    row = {**ATTEMPT, **changes}
    return tuple(row[c] for c in ATTEMPT_COLUMNS.split(", "))


CALL_INSERT = (
    "INSERT INTO calls(run_id, module_id, attempt, call_index, exchange_id, provider_call_index, hold_usd,"
    " opened_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
)
CALL_INSERT_OR_REPLACE = CALL_INSERT.replace("INSERT INTO", "INSERT OR REPLACE INTO")
COMPACTION_INSERT = (
    "INSERT INTO compactions(run_id, event_id, position, module_id, attempt, call_index, outcome)"
    " VALUES (?, ?, ?, ?, ?, ?, ?)"
)
COMPACTION_INSERT_OR_REPLACE = COMPACTION_INSERT.replace("INSERT INTO", "INSERT OR REPLACE INTO")
