"""Answer key 4 (attempts part) of the 2A plan, PR 3b1: `open_attempt` and `open_call`.

Written by the controller before the code existed, from `pr3/api-3b-3c.md` and rulings U8 to U17.
`AttemptsModel` is the reference the tests compare the store with: after any sequence of calls the
store's run, events (kind, module_id, attempt, detail), attempts and calls equal the model's, and a
refused call changes neither. PR 3b2 and 3c add their writes to this file. Implementers do not edit
this file or weaken a comparison against it.
"""

import hashlib
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, cast

from store_status_key import Model

from credit_os.provider.types import Compaction, Reply, Turn, Usage

Event = tuple[str, str | None, int | None, dict[str, object]]  # kind, module_id, attempt, detail
_RUNNING = frozenset({"running"})


@dataclass
class Call:
    exchange_id: str
    provider_call_index: int
    open: bool = True


@dataclass
class Attempt:
    request: bytes
    state: str = "open"
    calls: list[Call] = field(default_factory=list)


@dataclass
class AttemptsModel(Model):
    """The run model (key 4, runs part) with attempts and calls. Each method returns the error
    class name or None, and the number written where the API returns one."""

    modules: dict[str, list[Attempt]] = field(default_factory=dict)
    keys: dict[int, tuple[str, int]] = field(default_factory=dict)  # event index: (module, attempt)

    def keyed_events(self) -> list[Event]:
        return [
            (kind, *self.keys.get(n, (None, None)), detail)
            for n, (kind, detail) in enumerate(self.events)
        ]

    def attempt_rows(self) -> list[tuple[str, int, str, bytes]]:
        """(module_id, attempt, state, request), ordered by module_id, then attempt."""
        return [
            (module, number, attempt.state, attempt.request)
            for module in sorted(self.modules)
            for number, attempt in enumerate(self.modules[module], 1)
        ]

    def call_rows(self) -> list[tuple[str, int, int, str, int, bool]]:
        """(module_id, attempt, call_index, exchange_id, provider_call_index, open), in key order."""
        return [
            (module, number, index, call.exchange_id, call.provider_call_index, call.open)
            for module in sorted(self.modules)
            for number, attempt in enumerate(self.modules[module], 1)
            for index, call in enumerate(attempt.calls)
        ]

    def _event(self, kind: str, module: str, number: int, detail: dict[str, object]) -> None:
        self.keys[len(self.events)] = (module, number)
        self.events.append((kind, detail))

    def _attempt(self, token: int, module: str, number: int) -> tuple[str | None, Attempt | None]:
        """The run gate first (missing run, fenced claim, status), then the attempt exists."""
        refused = self._gate(token, _RUNNING)
        if refused is not None:
            return refused, None
        attempts = self.modules.get(module, [])
        if not 1 <= number <= len(attempts):
            return "StoreRefused", None
        return None, attempts[number - 1]

    def open_attempt(
        self, token: int, module: str, request: bytes
    ) -> tuple[str | None, int | None]:
        refused = self._gate(token, _RUNNING)
        if refused is not None:
            return refused, None
        attempts = self.modules.get(module, [])
        if attempts and attempts[-1].state == "open" and attempts[-1].request == request:
            return None, len(attempts)  # U17: the open attempt, nothing written
        if attempts and attempts[-1].state in ("open", "replied", "accepted"):
            return "StoreConflict", None
        self.modules[module] = [*attempts, Attempt(request)]
        self._event("attempt_opened", module, len(attempts) + 1, {})
        return None, len(attempts) + 1

    def open_call(
        self, token: int, module: str, number: int, exchange: str, provider_index: int
    ) -> tuple[str | None, int | None]:
        refused, attempt = self._attempt(token, module, number)
        if attempt is None:
            return refused, None
        used = (exchange, provider_index) in {
            (call.exchange_id, call.provider_call_index)
            for attempts in self.modules.values()
            for each in attempts
            for call in each.calls
        }
        if attempt.state != "open" or any(call.open for call in attempt.calls) or used:
            return "StoreConflict", None
        attempt.calls.append(Call(exchange, provider_index))
        return None, len(attempt.calls) - 1


REQUESTS = {n: f"request {n}\r\n".encode() for n in range(1, 5)}
# The SHA-256 of each request, by `printf 'request N\r\n' | shasum -a 256`.
REQUEST_SHA256 = {
    1: "8fde67a491ab4d4e4d7e6e1117f3d1351c7b62ec17140f8c58469037f4e9da66",
    2: "2cc1604a38192f5b3550b48cf406c7a02567af0820bdc2d4ecf6875fd8c6a061",
    3: "73dabf07a0692ba934967264875765a2f46c35c0b03b65713fa4c53e97061173",
    4: "bdee817a965f386d609768ea671f11ac7b10665651041ba370cce461c4627ac1",
}
HOLD = Decimal("0.5")
HOLD_TEXT = "0.5"


def _call(module: str, attempt: int, exchange: str, provider_index: int) -> dict[str, object]:
    """An open_call's arguments other than the claim; every one holds HOLD."""
    return {
        "module_id": module,
        "attempt": attempt,
        "exchange_id": exchange,
        "provider_call_index": provider_index,
        "hold_usd": HOLD,
    }


def _attempt(module: str, request: int) -> dict[str, object]:
    return {"module_id": module, "request": REQUESTS[request]}


# --- The scripted run: (call, claim number, arguments, expected error class or None) ------------
# Claim 1 is create_run's; claim_run makes claim 2. The test's clock answers SCRIPT_3B1 row n
# (1-based) with datetime(2026, 9, 30, 12, 0, n, tzinfo=UTC). A refused row, and a row in
# NO_WRITE_ROWS, calls it zero times and leaves the full dump unchanged; every other row calls it
# exactly once.
SCRIPT_3B1: tuple[tuple[str, int, dict[str, object], str | None], ...] = (
    ("create", 1, {}, None),
    ("start", 1, {}, None),
    ("open_attempt", 1, _attempt("CP-1", 1), None),
    ("open_attempt", 1, _attempt("CP-1", 1), None),  # U17: the open attempt, same bytes
    ("open_attempt", 1, _attempt("CP-1", 2), "StoreConflict"),  # the open attempt, other bytes
    ("open_call", 1, _call("CP-1", 1, "ex-1", 0), None),
    ("open_call", 1, _call("CP-1", 1, "ex-1", 1), "StoreConflict"),  # call 0 is open
    ("open_attempt", 1, _attempt("CP-2", 1), None),
    ("open_call", 1, _call("CP-2", 1, "ex-1", 0), "StoreConflict"),  # ex-1/0 used in the run
    ("open_call", 1, _call("CP-2", 1, "ex-1", 1), None),
    ("claim", 2, {}, None),
    ("open_attempt", 1, _attempt("CP-3", 3), "StoreFenced"),
    ("open_call", 1, _call("CP-1", 1, "ex-3", 0), "StoreFenced"),
    ("open_attempt", 2, _attempt("CP-3", 3), None),
    ("open_call", 2, _call("CP-3", 1, "ex-2", 0), None),
    ("end", 2, {"status": "stopped", "reason": "interrupted"}, None),
    ("open_attempt", 2, _attempt("CP-4", 1), "StoreConflict"),  # the run is stopped
    ("open_call", 2, _call("CP-9", 1, "ex-3", 0), "StoreConflict"),  # status before attempt
    ("start", 2, {}, None),
    ("open_attempt", 2, _attempt("CP-1", 1), None),  # U17 after the resume
    ("open_call", 2, _call("CP-1", 1, "ex-3", 0), "StoreConflict"),  # call 0 still open (D7)
    ("open_call", 2, _call("CP-9", 1, "ex-3", 0), "StoreRefused"),  # no such attempt
    ("open_attempt", 2, _attempt("CP-4", 4), None),
    ("open_call", 2, _call("CP-4", 1, "ex-3", 0), None),
    ("open_call", 2, _call("CP-4", 2, "ex-3", 1), "StoreRefused"),  # no attempt 2
)
# The number each row returns, for the rows that return one and are not refused.
SCRIPT_3B1_RETURNS = {3: 1, 4: 1, 6: 0, 8: 1, 10: 0, 14: 1, 15: 0, 20: 1, 23: 1, 24: 0}
NO_WRITE_ROWS = (4, 20)  # U17: the number returned, nothing written, the clock never called
AFTER_3B1_STATUS = "running"
AFTER_3B1_EVENTS: tuple[Event, ...] = (
    ("run_created", None, None, {}),
    ("run_started", None, None, {"from": "created"}),
    ("attempt_opened", "CP-1", 1, {}),
    ("attempt_opened", "CP-2", 1, {}),
    ("writer_replaced", None, None, {}),
    ("attempt_opened", "CP-3", 1, {}),
    ("run_ended", None, None, {"status": "stopped", "reason": "interrupted"}),
    ("run_started", None, None, {"from": "stopped"}),
    ("attempt_opened", "CP-4", 1, {}),
)
AFTER_3B1_EVENT_ROWS = (1, 2, 3, 8, 11, 14, 16, 19, 23)  # the row whose time is each event's `at`
# Attempts after SCRIPT_3B1: (module, attempt, state, request number, opened row). Every other
# column (reply, reply_sha256, issues, fail_reason, replied_at, closed_at) is NULL.
AFTER_3B1_ATTEMPTS: tuple[tuple[str, int, str, int, int], ...] = (
    ("CP-1", 1, "open", 1, 3),
    ("CP-2", 1, "open", 1, 8),
    ("CP-3", 1, "open", 3, 14),
    ("CP-4", 1, "open", 4, 23),
)
# Calls after SCRIPT_3B1: (module, attempt, call_index, exchange_id, provider index, opened row,
# closed row or None, kind or None). Each holds HOLD_TEXT; every reply column is NULL.
AFTER_3B1_CALLS: tuple[tuple[str, int, int, str, int, int, int | None, str | None], ...] = (
    ("CP-1", 1, 0, "ex-1", 0, 6, None, None),
    ("CP-2", 1, 0, "ex-1", 1, 10, None, None),
    ("CP-3", 1, 0, "ex-2", 0, 15, None, None),
    ("CP-4", 1, 0, "ex-3", 0, 24, None, None),
)

# --- Holds: open_call on CP-1 attempt 1 of a running run, with hold_usd set; (hold, stored text) -
HOLDS: tuple[tuple[Decimal, str], ...] = (
    (Decimal(0), "0"),
    (Decimal("0.50"), "0.50"),
    (Decimal("12.5"), "12.5"),
    (Decimal("1E+2"), "100"),
)

# --- Refusals ------------------------------------------------------------------------------------
# Each on a running run whose CP-1 attempt 1 is open with no call, with the run's valid claim:
# StoreRefused before BEGIN, the clock never called, the full dump unchanged. (label, call,
# arguments other than the claim)
_BASE_CALL = _call("CP-1", 1, "ex-1", 0)
_BIG = 2**63
REFUSED_ARGUMENTS: tuple[tuple[str, str, dict[str, object]], ...] = (
    ("module id with a space", "open_attempt", {"module_id": "CP 1", "request": b"r"}),
    ("module id empty", "open_attempt", {"module_id": "", "request": b"r"}),
    ("module id not text", "open_attempt", {"module_id": 1, "request": b"r"}),
    ("request as text", "open_attempt", {"module_id": "CP-1", "request": "r"}),
    ("request a bytearray", "open_attempt", {"module_id": "CP-1", "request": bytearray(b"r")}),
    (
        "request a bytes subclass",
        "open_attempt",
        {"module_id": "CP-1", "request": type("B", (bytes,), {})(b"r")},
    ),
    ("call module id with a space", "open_call", {**_BASE_CALL, "module_id": "CP 1"}),
    ("no hold", "open_call", {**_BASE_CALL, "hold_usd": None}),
    ("hold a float", "open_call", {**_BASE_CALL, "hold_usd": 0.5}),
    ("hold an int", "open_call", {**_BASE_CALL, "hold_usd": 1}),
    ("hold negative", "open_call", {**_BASE_CALL, "hold_usd": Decimal("-0.5")}),
    ("hold infinite", "open_call", {**_BASE_CALL, "hold_usd": Decimal("Infinity")}),
    ("exchange id empty", "open_call", {**_BASE_CALL, "exchange_id": ""}),
    ("exchange id with a space", "open_call", {**_BASE_CALL, "exchange_id": "ex 1"}),
    ("provider index negative", "open_call", {**_BASE_CALL, "provider_call_index": -1}),
    ("provider index a bool", "open_call", {**_BASE_CALL, "provider_call_index": False}),
    ("provider index a float", "open_call", {**_BASE_CALL, "provider_call_index": 0.0}),
    ("provider index too large", "open_call", {**_BASE_CALL, "provider_call_index": _BIG}),
    ("attempt zero", "open_call", {**_BASE_CALL, "attempt": 0}),
    ("attempt a bool", "open_call", {**_BASE_CALL, "attempt": True}),
    ("attempt too large", "open_call", {**_BASE_CALL, "attempt": _BIG}),
)
# record_event with an attempt kind (U8), module_id "CP-1" and attempt 1, on the same running run:
# StoreRefused before BEGIN, the clock never called, the full dump unchanged.
REFUSED_NOTE_KINDS = (
    "attempt_accepted",
    "attempt_failed",
    "attempt_opened",
    "attempt_rejected",
    "attempt_replied",
)
# An attempt the run does not have, on the same running run: StoreRefused inside the transaction,
# nothing written, the clock never called. (label, call, arguments other than the claim)
MISSING: tuple[tuple[str, str, dict[str, object]], ...] = (
    ("call on attempt 2", "open_call", {**_BASE_CALL, "attempt": 2}),
    ("call on another module", "open_call", {**_BASE_CALL, "module_id": "CP-9"}),
)
# Each write of this key with a claim for MISSING_RUN_ID (no such run; token FOREIGN_TOKEN of the
# runs part): StoreRefused, the clock never called, the full dump unchanged.
MISSING_RUN_ID = "run-9"
MISSING_RUN_CALLS: tuple[tuple[str, dict[str, object]], ...] = (
    ("open_attempt", _attempt("CP-1", 1)),
    ("open_call", _BASE_CALL),
)
# Each call below on a run in each of these statuses: StoreConflict, the clock never called, the
# full dump unchanged. "created" is a new run; "rejected" was rejected from created. For the others,
# CP-1 attempt 1 was opened with REQUESTS[1] (no call) while the run ran, then end_run moved it.
# The gate refuses on status before it looks for the attempt, and U17's no-op holds only while the
# run is running. (label, call, arguments other than the claim)
NOT_RUNNING = ("created", "rejected", "stopped", "failed", "finished")
NOT_RUNNING_CALLS: tuple[tuple[str, str, dict[str, object]], ...] = (
    ("a new module's attempt", "open_attempt", _attempt("CP-2", 1)),
    ("CP-1 again, same bytes", "open_attempt", _attempt("CP-1", 1)),
    ("a call on CP-1 attempt 1", "open_call", _BASE_CALL),
)


# === Added for PR 3b2a: record_compactions, the compaction insert, and U22's money rule =======
# Rulings U12 (provider text is stored escaped), U13 (a per-run position 0, 1, ... with no gap),
# U16 (compaction repeats) and U22 (every zero is written as "0", whatever its exponent; no amount
# rounded or clipped; an amount the column cannot hold exactly is StoreRefused). record_compactions
# has no time column and never calls the clock. PR 3b2b adds close_call to this file.


def stored_text(text: str) -> str:
    """The stored text of a provider id: each lone surrogate backslash-escaped (U12)."""
    return text.encode("utf-8", "backslashreplace").decode("utf-8")


def money_text(value: Decimal) -> str:
    """U22: every zero is "0"; any other amount keeps its exponent, as format(value, "f")."""
    return "0" if value == 0 else format(value, "f")


def _counts(compaction: Compaction) -> tuple[int | None, ...]:
    usage = compaction.usage
    return (
        usage.input_tokens,
        usage.cached_read_tokens,
        usage.cache_write_tokens,
        usage.output_tokens,
    )


def same_compaction(first: Compaction, second: Compaction) -> bool:
    """U16: the five fields equal, as Compaction values (Decimal equality, so 0.0020 is 0.002)."""
    return (
        _counts(first) == _counts(second)
        and first.billed_usd == second.billed_usd
        and first.outcome == second.outcome
        and stored_text(first.event_id) == stored_text(second.event_id)
        and (first.supersedes is None) == (second.supersedes is None)
        and stored_text(first.supersedes or "") == stored_text(second.supersedes or "")
    )


CallKey = tuple[str, int, int]


@dataclass
class CompactionsModel(AttemptsModel):
    """AttemptsModel with the run's compactions, in position order."""

    compactions: list[tuple[str, CallKey | None, Compaction]] = field(default_factory=list)

    def compaction_rows(self) -> list[tuple[int, str, CallKey | None, str, str | None]]:
        """(position, stored event id, call key, outcome, billed_usd text)."""
        return [
            (
                n,
                event_id,
                key,
                c.outcome,
                None if c.billed_usd is None else money_text(c.billed_usd),
            )
            for n, (event_id, key, c) in enumerate(self.compactions)
        ]

    def _compact(self, compactions: tuple[Compaction, ...], key: CallKey | None) -> str | None:
        """Insert in order. A repeat (an event id whose stored text the run holds, or one earlier
        in this list) is a no-op when it is the same compaction and its stored id has no
        backslash; otherwise StoreConflict, and nothing of this call is kept."""
        added: list[tuple[str, CallKey | None, Compaction]] = []
        for compaction in compactions:
            event_id = stored_text(compaction.event_id)
            prior = [c for i, _, c in (*self.compactions, *added) if i == event_id]
            if not prior:
                added.append((event_id, key, compaction))
            elif "\\" in event_id or not same_compaction(prior[0], compaction):
                return "StoreConflict"
        self.compactions += added
        return None

    def record_compactions(self, token: int, compactions: tuple[Compaction, ...]) -> str | None:
        refused = self._gate(token, _RUNNING)
        return refused if refused is not None else self._compact(compactions, None)


UNFINISHED = Compaction(Usage(), None, "unfinished", "u-1", None)
FINISHED = Compaction(Usage(input_tokens=40), Decimal("0.002"), "done", "d-1", "u-1")

# --- Compaction repeats (U12, U16), each on a running run (no attempt needed) ----------------
# record_compactions((first,)), then record_compactions((second,)): (label, first, second, error
# class or None). After each row, error or not, the run holds exactly one compaction, at position
# 0, read back equal to the first (its billed_usd text as the first wrote it), and the second call
# wrote nothing and called no clock.
SURROGATE_ID = Compaction(Usage(), None, "done", "a\ud800", None)
LITERAL_ID = Compaction(Usage(), None, "done", "a\\ud800", None)
STORED_SURROGATE_ID = "a\\ud800"  # both ids are stored as this text
REPEATS: tuple[tuple[str, Compaction, Compaction, str | None], ...] = (
    ("identical", FINISHED, FINISHED, None),
    (
        "equal charge with another exponent",
        FINISHED,
        Compaction(Usage(input_tokens=40), Decimal("0.0020"), "done", "d-1", "u-1"),
        None,
    ),
    (
        "another charge",
        FINISHED,
        Compaction(Usage(input_tokens=40), Decimal("0.003"), "done", "d-1", "u-1"),
        "StoreConflict",
    ),
    (
        "another count",
        FINISHED,
        Compaction(Usage(input_tokens=41), Decimal("0.002"), "done", "d-1", "u-1"),
        "StoreConflict",
    ),
    (
        "another outcome",
        FINISHED,
        Compaction(Usage(input_tokens=40), Decimal("0.002"), "failed", "d-1", "u-1"),
        "StoreConflict",
    ),
    (
        "supersedes another",
        FINISHED,
        Compaction(Usage(input_tokens=40), Decimal("0.002"), "done", "d-1", None),
        "StoreConflict",
    ),
    ("identical, id with a backslash", LITERAL_ID, LITERAL_ID, "StoreConflict"),
    ("surrogate, then the literal", SURROGATE_ID, LITERAL_ID, "StoreConflict"),
)
# record_compactions((SURROGATE_ID, LITERAL_ID)) in one call: the second collides with the first
# after escaping, so it is a repeat whose stored id holds a backslash: StoreConflict, and neither
# is written.
SELF_COLLISION = (SURROGATE_ID, LITERAL_ID)
# record_compactions((UNFINISHED, FINISHED)) in one call: positions 0 and 1, in that order.
IN_ORDER = (UNFINISHED, FINISHED)

# --- U22: charges. record_compactions((Compaction(Usage(), charge, "done", "c-1", None),)) on a
# running run stores the text as the compaction's billed_usd: (label, charge, stored text).
STORED_CHARGES: tuple[tuple[str, Decimal, str], ...] = (
    ("zero", Decimal(0), "0"),
    ("zero, exponent +64", Decimal("0E+64"), "0"),
    ("zero, exponent -64", Decimal("0E-64"), "0"),
    ("zero with three places", Decimal("0.000"), "0"),
    ("zero, exponent of a million", Decimal("0E+1000000"), "0"),
    ("the adapter's zero", Decimal("0E-11"), "0"),
    ("64 nines", Decimal("9" * 64), "9" * 64),
    ("the largest power", Decimal("1E+63"), "1" + "0" * 63),
    ("the smallest", Decimal("1E-62"), "0." + "0" * 61 + "1"),
    ("the adapter's half", Decimal("0.50000000000"), "0.50000000000"),
)
# The provider's constructors refuse this charge (U22: "the Reply rule that already refuses it"):
# Compaction(Usage(), NEGATIVE_ZERO, "done", "c-1", None) raises ProviderDataError.
NEGATIVE_ZERO = Decimal("-0")
# Compactions the constructor accepts and the store cannot store (U14, U22): record_compactions
# with the one compaction is StoreRefused before BEGIN, the dump unchanged. (label, compaction)
_HUGE = 2**63
UNSTORABLE_COMPACTIONS: tuple[tuple[str, Compaction], ...] = (
    ("charge of 65 digits", Compaction(Usage(), Decimal("1E+64"), "done", "c-1", None)),
    ("charge of 65 characters, small", Compaction(Usage(), Decimal("1E-63"), "done", "c-1", None)),
    (
        "charge, exponent of a million",
        Compaction(Usage(), Decimal("9E+999999"), "done", "c-1", None),
    ),
    (
        "charge smaller than any column",
        Compaction(Usage(), Decimal("1E-999999"), "done", "c-1", None),
    ),
    ("count too large", Compaction(Usage(input_tokens=_HUGE), None, "done", "c-1", None)),
)

# --- Refusals of record_compactions, as REFUSED_ARGUMENTS (StoreRefused before BEGIN, the dump
# unchanged), on a running run. (label, arguments other than the claim)
REFUSED_COMPACTIONS: tuple[tuple[str, dict[str, object]], ...] = (
    ("compactions not a sequence", {"compactions": FINISHED}),
    ("compactions as text", {"compactions": "d-1"}),
    ("compactions as bytes", {"compactions": b"d-1"}),
    ("compaction not a Compaction", {"compactions": ("d-1",)}),
    ("one good, one not a Compaction", {"compactions": (FINISHED, None)}),
)
# record_compactions((FINISHED,)) on a run in each NOT_RUNNING status: StoreConflict, the dump
# unchanged. record_compactions(()) on a running run: nothing written, no error.
NOT_RUNNING_COMPACTION = (FINISHED,)

# --- Two runs in one store: positions and repeats are per run. Runs A (RUN_ID) and B
# (SECOND_RUN_ID) are each created and started, A first; then each call with its run's claim:
# (run, compactions, error class or None).
SECOND_RUN_ID = "run-2"
X_A = Compaction(Usage(input_tokens=1), Decimal("0.1"), "done", "x-1", None)
X_B = Compaction(Usage(input_tokens=2), Decimal("0.2"), "done", "x-1", None)  # same id, other run
TWO_RUNS_COMPACTIONS: tuple[tuple[str, tuple[Compaction, ...], str | None], ...] = (
    ("A", (X_A,), None),
    ("B", (X_B,), None),
    ("B", (FINISHED,), None),
    ("A", (X_B,), "StoreConflict"),  # A holds x-1 with another charge
)
# Per run, by position: (position, event_id, billed text).
AFTER_TWO_RUNS_COMPACTIONS: dict[str, tuple[tuple[int, str, str | None], ...]] = {
    "A": ((0, "x-1", "0.1"),),
    "B": ((0, "x-1", "0.2"), (1, "d-1", "0.002")),
}

# --- The gate on record_compactions (U1, U6): run A (RUN_ID) is created and started (claim 1),
# record_compactions((FINISHED,)) is accepted, then claim_run(RUN_ID) makes claim 2. Each row is
# then record_compactions with that claim number: (label, claim number, compactions, error class or
# None). A refused row calls the clock zero times and leaves the full dump unchanged. The gate
# comes before the repeat lookup, so the old claim's repeat is fenced, not a no-op.
FENCED_COMPACTIONS: tuple[tuple[str, int, tuple[Compaction, ...], str | None], ...] = (
    ("the old claim, a new compaction", 1, (UNFINISHED,), "StoreFenced"),
    ("the old claim, a repeat", 1, (FINISHED,), "StoreFenced"),
    ("the new claim", 2, (UNFINISHED,), None),
)
# After the rows, run A holds, by position: (position, event_id, billed text).
AFTER_FENCED_COMPACTIONS: tuple[tuple[int, str, str | None], ...] = (
    (0, "d-1", "0.002"),
    (1, "u-1", None),
)
# While run A runs, record_compactions(MISSING_RUN_COMPACTIONS) with Claim(MISSING_RUN_ID,
# FOREIGN_TOKEN of the runs part): StoreRefused, the clock never called, the full dump unchanged.
MISSING_RUN_COMPACTIONS = (FINISHED,)


# === Added for PR 3b2b: close_call =========================================================
# Rulings U13 (close_call inserts its reply's compactions, next in the run's positions and in the
# reply's order, and then closes the call, in one transaction), U14 and U18 (a Reply the store
# cannot store is StoreRefused before BEGIN, with the call left open: spend unknown, never a wrong
# figure), U15 (a reply's times are its own, never the store clock), U16 (compaction repeats, the
# call key aside: the first row is kept as written) and U22 (every zero is "0"). close_call calls
# the clock once (closed_at) and writes no event. The reply's columns, for every Reply kind, are
# store_reply_key's CASES; this part keys the call's life around them.


@dataclass
class CloseModel(CompactionsModel):
    """CompactionsModel with close_call."""

    def close_call(
        self, token: int, module: str, number: int, index: int, reply: Reply
    ) -> str | None:
        """The run gate, then the attempt and the call exist (StoreRefused), then the call is open
        and the attempt open (StoreConflict); then the reply's compactions with this call's key,
        and the call closes only when they are all written."""
        refused, attempt = self._attempt(token, module, number)
        if attempt is None:
            return refused
        if not 0 <= index < len(attempt.calls):
            return "StoreRefused"
        if not attempt.calls[index].open or attempt.state != "open":
            return "StoreConflict"
        refused = self._compact(reply.compactions, (module, number, index))
        if refused is None:
            attempt.calls[index].open = False
        return refused


def _ok(usage: Usage, billed: Decimal | None, compactions: tuple[Compaction, ...] = ()) -> Reply:
    turn = Turn(
        text="t", tool_calls=(), usage=usage, stop_reason="end", reported_model="m", request_id="r"
    )
    return Reply(
        kind="ok",
        turn=turn,
        error_class=None,
        message=None,
        usage=usage,
        billed_usd=billed,
        raw=None,
        started_at=None,
        finished_at=None,
        compactions=compactions,
    )


def _sent_usage(billed: Decimal) -> Reply:
    return Reply(
        kind="sent_usage",
        turn=None,
        error_class="RateLimited",
        message=None,
        usage=Usage(),
        billed_usd=billed,
        raw=None,
        started_at=None,
        finished_at=None,
    )


NOT_SENT = Reply(
    kind="not_sent",
    turn=None,
    error_class="ConnectionError",
    message=None,
    usage=None,
    billed_usd=None,
    raw=None,
    started_at=None,
    finished_at=None,
)
OK_ZERO = _ok(Usage(input_tokens=10, output_tokens=2), Decimal(0), (UNFINISHED,))
OK_PRICED = _ok(Usage(input_tokens=100, output_tokens=20), Decimal("0.0125"))


def _close(module: str, attempt: int, index: int, reply: object) -> dict[str, object]:
    return {"module_id": module, "attempt": attempt, "call_index": index, "reply": reply}


# The reply columns of a call (store_reply_key's names), by state. An open call has every one None.
OPEN_CALL_COLUMNS: dict[str, object] = {
    "kind": None,
    "error_class": None,
    "message": None,
    "input_tokens": None,
    "cached_read_tokens": None,
    "cache_write_tokens": None,
    "output_tokens": None,
    "reasoning_tokens": None,
    "billed_usd": None,
    "started_at": None,
    "finished_at": None,
    "stop_reason": None,
    "reported_model": None,
    "request_id": None,
    "raw": None,
}
NOT_SENT_COLUMNS = {**OPEN_CALL_COLUMNS, "kind": "not_sent", "error_class": "ConnectionError"}
OK_ZERO_COLUMNS = {
    **OPEN_CALL_COLUMNS,
    "kind": "ok",
    "input_tokens": 10,
    "output_tokens": 2,
    "billed_usd": "0",
    "stop_reason": "end",
    "reported_model": "m",
    "request_id": "r",
}

# --- The scripted run of PR 3b2b, as SCRIPT_3B1 (claims, the test's clock answering row n with
# second n, the dump). A refused row and a NO_WRITE_ROWS_3B2B row leave the full dump unchanged; a
# refused row, a NO_WRITE row and a CLOCKLESS row call the clock zero times; every other row calls
# it exactly once.
SCRIPT_3B2B: tuple[tuple[str, int, dict[str, object], str | None], ...] = (
    ("create", 1, {}, None),
    ("start", 1, {}, None),
    ("open_attempt", 1, _attempt("CP-1", 1), None),
    ("open_attempt", 1, _attempt("CP-1", 1), None),  # U17
    ("open_attempt", 1, _attempt("CP-1", 2), "StoreConflict"),
    ("open_call", 1, _call("CP-1", 1, "ex-1", 0), None),
    ("open_call", 1, _call("CP-1", 1, "ex-1", 1), "StoreConflict"),  # call 0 open
    ("close_call", 1, _close("CP-1", 1, 0, NOT_SENT), None),
    ("close_call", 1, _close("CP-1", 1, 0, NOT_SENT), "StoreConflict"),  # call 0 closed
    ("open_call", 1, _call("CP-1", 1, "ex-1", 0), "StoreConflict"),  # ex-1/0 used
    ("open_call", 1, _call("CP-1", 1, "ex-1", 1), None),
    ("close_call", 1, _close("CP-1", 1, 1, OK_ZERO), None),  # UNFINISHED at position 0
    ("open_call", 1, _call("CP-1", 1, "ex-1", 2), None),
    ("record_compactions", 1, {"compactions": (FINISHED,)}, None),  # position 1, no clock
    ("claim", 2, {}, None),
    ("close_call", 1, _close("CP-1", 1, 2, OK_PRICED), "StoreFenced"),
    ("close_call", 2, _close("CP-1", 1, 5, OK_PRICED), "StoreRefused"),  # no call 5
    ("open_attempt", 2, _attempt("CP-2", 1), None),
)
# The number each row returns, for the rows that return one and are not refused.
SCRIPT_3B2B_RETURNS = {3: 1, 4: 1, 6: 0, 11: 1, 13: 2, 18: 1}
NO_WRITE_ROWS_3B2B = (4,)
CLOCKLESS_ROWS_3B2B = (14,)
AFTER_3B2B_STATUS = "running"
AFTER_3B2B_EVENTS: tuple[Event, ...] = (
    ("run_created", None, None, {}),
    ("run_started", None, None, {"from": "created"}),
    ("attempt_opened", "CP-1", 1, {}),
    ("writer_replaced", None, None, {}),
    ("attempt_opened", "CP-2", 1, {}),
)
AFTER_3B2B_EVENT_ROWS = (1, 2, 3, 15, 18)  # the row whose clock time each event has
# (module, attempt, call_index, exchange_id, provider index, opened row, closed row or None, the
# call's reply columns). opened_at and closed_at are those rows' clock times.
AFTER_3B2B_CALLS: tuple[tuple[str, int, int, str, int, int, int | None, dict[str, object]], ...] = (
    ("CP-1", 1, 0, "ex-1", 0, 6, 8, NOT_SENT_COLUMNS),
    ("CP-1", 1, 1, "ex-1", 1, 11, 12, OK_ZERO_COLUMNS),
    ("CP-1", 1, 2, "ex-1", 2, 13, None, OPEN_CALL_COLUMNS),
)
# (position, event_id, call key or None, outcome, billed_usd text or None)
AFTER_3B2B_COMPACTIONS: tuple[tuple[int, str, CallKey | None, str, str | None], ...] = (
    (0, "u-1", ("CP-1", 1, 1), "unfinished", None),
    (1, "d-1", None, "done", "0.002"),
)

# --- Every Reply kind through the store. Each store_reply_key CASES row, on a fresh store with a
# running run, CP-1 attempt 1 and its open call 0: close_call writes exactly the case's CALL columns
# (closed_at the clock's one answer) and exactly its COMPACTIONS rows with call key ("CP-1", 1, 0),
# in order, from position 0. (store_reply_key's own docstring, "3b, through the store".)

# --- Repeats through close_call (U16; the record_compactions repeats are REPEATS above), on a
# running run whose CP-1 attempt 1 has call 0 open. Each row: the first call, then the second, then
# (error class of the second or None, the call-0 state after: "open" or "closed", the one row's
# call key). After each row the run holds exactly one compaction, FINISHED as written first.
REPEAT_FROM_CALL = _ok(Usage(), None, (FINISHED,))
CLOSE_REPEATS: tuple[tuple[str, str, str, str | None, str, CallKey | None], ...] = (
    # (label, first, second, error, call 0 after, the row's call key)
    ("the call first", "close", "record", None, "closed", ("CP-1", 1, 0)),
    ("the record first", "record", "close", None, "closed", None),
)
# close_call(call 0, SELF_COLLISION_REPLY): its two compactions collide after escaping, so the
# second is a repeat whose stored id holds a backslash: StoreConflict, no compaction written, call 0
# still open, the clock never called, the full dump unchanged.
SELF_COLLISION_REPLY = _ok(Usage(), None, SELF_COLLISION)
# A reply cannot repeat a compaction inside itself: the provider's Reply refuses two compactions
# with one event_id (ProviderDataError). _ok(Usage(), None, TWICE_COMPACTIONS) raises. Ids that
# differ and collide only after escaping are SELF_COLLISION_REPLY above.
TWICE_COMPACTIONS = (FINISHED, FINISHED)

# --- U22: charges through close_call, on a running run whose CP-1 attempt 1 has call 0 open. For
# each STORED_CHARGES row (label, charge, stored text): close_call(call 0, _sent_usage(charge))
# stores the text as the call's billed_usd, and close_call(call 0, _bare(charge)) stores it as the
# compaction's. A Reply with NEGATIVE_ZERO as billed_usd raises ProviderDataError.


def _bare(charge: Decimal) -> Reply:
    """An ok reply with no charge of its own, whose one compaction carries the charge."""
    return _ok(Usage(), None, (Compaction(Usage(), charge, "done", "c-1", None),))


def _unstorable(**changes: object) -> Reply:
    base: dict[str, object] = {
        "kind": "not_sent",
        "turn": None,
        "error_class": "X",
        "message": None,
        "usage": None,
        "billed_usd": None,
        "raw": None,
        "started_at": None,
        "finished_at": None,
    }
    base.update(changes)
    return Reply(**cast(dict[str, Any], base))  # the constructor checks kinds and pairings only


# Replies the provider's constructor accepts and the store cannot store (U14, U18, U22): close_call
# on call 0 is StoreRefused before BEGIN, the clock never called, the full dump unchanged, and call
# 0 reads back open (OPEN_CALL_COLUMNS, closed_at None). (label, reply)
UNSTORABLE_REPLIES: tuple[tuple[str, Reply], ...] = (
    ("error class not text", _unstorable(error_class=5)),
    ("message not text", _unstorable(message=b"m")),
    ("raw as text", _unstorable(raw="x")),
    ("start time not a number", _unstorable(started_at="soon")),
    ("start time a bool", _unstorable(started_at=True)),
    ("finish time past year 9999", _unstorable(finished_at=253402300800.0)),
    ("count too large", _unstorable(kind="sent_usage", usage=Usage(input_tokens=_BIG))),
    ("charge of 65 digits", _sent_usage(Decimal("1E+64"))),
    ("charge of 65 characters, small", _sent_usage(Decimal("1E-63"))),
    ("charge, exponent of a million", _sent_usage(Decimal("9E+999999"))),
    ("charge smaller than any column", _sent_usage(Decimal("1E-999999"))),
    ("compaction charge of 65 digits", _bare(Decimal("1E+64"))),
    (
        "compaction count too large",
        _ok(Usage(), None, (Compaction(Usage(input_tokens=_BIG), None, "done", "c-1", None),)),
    ),
)


@dataclass(frozen=True)
class _ChildReply(Reply):
    """A Reply subclass: the constructor's checks run, but the type is not exactly Reply."""


CHILD_REPLY = _ChildReply(
    kind="not_sent",
    turn=None,
    error_class="ConnectionError",
    message=None,
    usage=None,
    billed_usd=None,
    raw=None,
    started_at=None,
    finished_at=None,
)

# --- Refusals of close_call, as REFUSED_ARGUMENTS (StoreRefused before BEGIN, no clock, the dump
# unchanged), on a running run whose CP-1 attempt 1 has call 0 open. (label, call, arguments other
# than the claim)
REFUSED_ARGUMENTS_3B2B: tuple[tuple[str, str, dict[str, object]], ...] = (
    ("reply not a Reply", "close_call", _close("CP-1", 1, 0, "ok")),
    ("reply a Reply subclass", "close_call", _close("CP-1", 1, 0, CHILD_REPLY)),
    ("reply None", "close_call", _close("CP-1", 1, 0, None)),
    ("call index negative", "close_call", _close("CP-1", 1, -1, NOT_SENT)),
    ("call index a bool", "close_call", _close("CP-1", 1, True, NOT_SENT)),
    ("call index too large", "close_call", _close("CP-1", 1, _BIG, NOT_SENT)),
    ("attempt 0", "close_call", _close("CP-1", 0, 0, NOT_SENT)),
    ("module id with a space", "close_call", _close("CP 1", 1, 0, NOT_SENT)),
)
# A call the run does not have, on the same setup: StoreRefused, nothing written, no clock.
MISSING_3B2B: tuple[tuple[str, str, dict[str, object]], ...] = (
    ("close call 1", "close_call", _close("CP-1", 1, 1, NOT_SENT)),
    ("close a call of attempt 2", "close_call", _close("CP-1", 2, 0, NOT_SENT)),
    ("close a call of another module", "close_call", _close("CP-9", 1, 0, NOT_SENT)),
)
# close_call with Claim(MISSING_RUN_ID, FOREIGN_TOKEN of the runs part), while run A runs with call
# 0 open: StoreRefused, the clock never called, the full dump unchanged.
MISSING_RUN_CLOSE = _close("CP-1", 1, 0, NOT_SENT)
# As NOT_RUNNING_CALLS, with CP-1 attempt 1 and its call 0 (ex-1/0) opened while the run ran, for
# each NOT_RUNNING status ("created" and "rejected" have no attempt): close_call(call 0, NOT_SENT)
# is StoreConflict, no clock, the dump unchanged.
NOT_RUNNING_CLOSE = _close("CP-1", 1, 0, NOT_SENT)
# An attempt that is not open: none exists before 3c (record_reply, fail_attempt); 3c's key adds
# close_call on a replied or failed attempt's open call (StoreConflict).

# --- Two runs in one store (lookups, positions and repeats are per run). Runs A (RUN_ID) and B
# (SECOND_RUN_ID) are each created, started, and given CP-1 attempt 1 with REQUESTS[1] and call 0
# on ex-1/0 (the exchange pair is per run), A first. Then, each with its run's claim: (call, run,
# arguments, error class or None).
Y = Compaction(Usage(), None, "done", "y-1", None)
TWO_RUNS_CLOSE: tuple[tuple[str, str, dict[str, object], str | None], ...] = (
    ("close_call", "A", _close("CP-1", 1, 0, _ok(Usage(), None, (X_A,))), None),
    ("record_compactions", "B", {"compactions": (X_B,)}, None),
    ("close_call", "B", _close("CP-1", 1, 0, _ok(Usage(), None, (Y,))), None),
    ("record_compactions", "A", {"compactions": (Y,)}, None),
    ("close_call", "B", _close("CP-1", 1, 0, NOT_SENT), "StoreConflict"),  # B's call 0 closed
)
# Per run, by position: (position, event_id, call key, billed text).
AFTER_TWO_RUNS_CLOSE: dict[str, tuple[tuple[int, str, CallKey | None, str | None], ...]] = {
    "A": ((0, "x-1", ("CP-1", 1, 0), "0.1"), (1, "y-1", None, None)),
    "B": ((0, "x-1", None, "0.2"), (1, "y-1", ("CP-1", 1, 0), None)),
}


# === Added for PR 3c1: record_reply, record_verdict, fail_attempt ===========================
# Rulings U8 (each attempt state change appends attempt_<state> with module_id and attempt, in the
# same transaction), U9 (an attempt is failed only while the run runs; its open call stays open,
# D7), U10, U11 (issues: "[" + each item's detail_to_text joined by "," + "]", "[]" when none;
# NULL until accepted or rejected) and U17. Each write calls the clock once (replied_at or
# closed_at) and appends one event; a refused write calls it zero times and changes nothing.
# PR 3c2 adds the reads (attempts, charges).


@dataclass
class ReplyModel(CloseModel):
    """CloseModel with record_reply, record_verdict and fail_attempt."""

    shas: dict[tuple[str, int], str] = field(default_factory=dict)

    def record_reply(
        self, token: int, module: str, number: int, reply: bytes
    ) -> tuple[str | None, str | None]:
        """Open to replied; StoreConflict when the attempt is not open or a call of it is open."""
        refused, attempt = self._attempt(token, module, number)
        if attempt is None:
            return refused, None
        if attempt.state != "open" or any(call.open for call in attempt.calls):
            return "StoreConflict", None
        attempt.state = "replied"
        self.shas[(module, number)] = hashlib.sha256(reply).hexdigest()
        self._event("attempt_replied", module, number, {})
        return None, self.shas[(module, number)]

    def record_verdict(
        self, token: int, module: str, number: int, sha: str, accepted: bool
    ) -> str | None:
        """Replied to accepted or rejected; StoreConflict when not replied or the hash differs."""
        refused, attempt = self._attempt(token, module, number)
        if attempt is None:
            return refused
        if attempt.state != "replied" or self.shas.get((module, number)) != sha:
            return "StoreConflict"
        attempt.state = "accepted" if accepted else "rejected"
        self._event(f"attempt_{attempt.state}", module, number, {})
        return None

    def fail_attempt(self, token: int, module: str, number: int, reason: str) -> str | None:
        """Open to failed; an open call of the attempt stays open (D7)."""
        refused, attempt = self._attempt(token, module, number)
        if attempt is None:
            return refused
        if attempt.state != "open":
            return "StoreConflict"
        attempt.state = "failed"
        self._event("attempt_failed", module, number, {"reason": reason})
        return None


REPLIES = {n: f"reply {n}\n".encode() for n in range(1, 4)}
# The SHA-256 of each reply, by `printf 'reply N\n' | shasum -a 256`.
REPLY_SHA256 = {
    1: "030f771b188d553d5be0debc26a5aec9d89dddd22d3211d38d1700da855c2ea0",
    2: "531cd91cd07fc951089d33fa2aec26f915b51e7137b97800dd7cf71926f685d6",
    3: "7ad6bca698425105b23d597c5ce09f99d34ca154086b426e5d1fc88179e769f0",
}
ISSUES_1 = ({"code": "missing_section", "line": 3}, {"code": "figure", "line": None})
# ISSUES_1's stored text (canonical ASCII JSON, sorted keys, no spaces).
ISSUES_TEXT_1 = '[{"code":"missing_section","line":3},{"code":"figure","line":null}]'
OK_UNKNOWN = _ok(Usage(), None)


def _reply_of(module: str, attempt: int, reply: int) -> dict[str, object]:
    return {"module_id": module, "attempt": attempt, "reply": REPLIES[reply]}


def _verdict(
    module: str, attempt: int, sha: object, accepted: object, issues: object = ()
) -> dict[str, object]:
    return {
        "module_id": module,
        "attempt": attempt,
        "reply_sha256": sha,
        "accepted": accepted,
        "issues": issues,
    }


def _fail(module: str, attempt: int, reason: str = "interrupted") -> dict[str, object]:
    return {"module_id": module, "attempt": attempt, "reason": reason}


# --- The scripted run of PR 3c1, as SCRIPT_3B1 (claims; the test's clock answers row n with second
# n; a refused row calls it zero times and leaves the full dump unchanged; every other row calls it
# exactly once).
SCRIPT_3C1: tuple[tuple[str, int, dict[str, object], str | None], ...] = (
    ("create", 1, {}, None),
    ("start", 1, {}, None),
    ("open_attempt", 1, _attempt("CP-1", 1), None),
    ("open_call", 1, _call("CP-1", 1, "ex-1", 0), None),
    ("record_reply", 1, _reply_of("CP-1", 1, 1), "StoreConflict"),  # call 0 open
    ("close_call", 1, _close("CP-1", 1, 0, OK_UNKNOWN), None),
    ("record_reply", 1, _reply_of("CP-1", 1, 1), None),
    ("record_verdict", 1, _verdict("CP-1", 1, "0" * 64, False), "StoreConflict"),  # other hash
    ("record_verdict", 1, _verdict("CP-1", 1, REPLY_SHA256[1], False, ISSUES_1), None),
    ("open_attempt", 1, _attempt("CP-1", 2), None),
    ("open_call", 1, _call("CP-1", 2, "ex-1", 1), None),
    ("close_call", 1, _close("CP-1", 2, 0, NOT_SENT), None),
    ("open_call", 1, _call("CP-1", 2, "ex-1", 2), None),
    ("claim", 2, {}, None),
    ("fail_attempt", 1, _fail("CP-1", 2), "StoreFenced"),
    ("fail_attempt", 2, _fail("CP-1", 2), None),  # its call 1 stays open (D7)
    ("end", 2, {"status": "stopped", "reason": "interrupted"}, None),
    ("start", 2, {}, None),
    ("open_attempt", 2, _attempt("CP-1", 3), None),
    ("open_call", 2, _call("CP-1", 3, "ex-2", 0), None),
    ("close_call", 2, _close("CP-1", 3, 0, OK_PRICED), None),
    ("record_reply", 2, _reply_of("CP-1", 3, 3), None),
    ("record_verdict", 2, _verdict("CP-1", 3, REPLY_SHA256[3], True), None),
    ("open_attempt", 2, _attempt("CP-1", 4), "StoreConflict"),  # attempt 3 accepted
    ("end", 2, {"status": "finished", "reason": "completed"}, None),
)
# The value each row returns, for the rows that return one and are not refused.
SCRIPT_3C1_RETURNS: dict[int, object] = {
    3: 1,
    4: 0,
    7: REPLY_SHA256[1],
    10: 2,
    11: 0,
    13: 1,
    19: 3,
    20: 0,
    22: REPLY_SHA256[3],
}
AFTER_3C1_STATUS = "finished"
AFTER_3C1_EVENTS: tuple[Event, ...] = (
    ("run_created", None, None, {}),
    ("run_started", None, None, {"from": "created"}),
    ("attempt_opened", "CP-1", 1, {}),
    ("attempt_replied", "CP-1", 1, {}),
    ("attempt_rejected", "CP-1", 1, {}),
    ("attempt_opened", "CP-1", 2, {}),
    ("writer_replaced", None, None, {}),
    ("attempt_failed", "CP-1", 2, {"reason": "interrupted"}),
    ("run_ended", None, None, {"status": "stopped", "reason": "interrupted"}),
    ("run_started", None, None, {"from": "stopped"}),
    ("attempt_opened", "CP-1", 3, {}),
    ("attempt_replied", "CP-1", 3, {}),
    ("attempt_accepted", "CP-1", 3, {}),
    ("run_ended", None, None, {"status": "finished", "reason": "completed"}),
)
AFTER_3C1_EVENT_ROWS = (1, 2, 3, 7, 9, 10, 14, 16, 17, 18, 19, 22, 23, 25)
# Attempts after SCRIPT_3C1, read raw: (module, attempt, state, request number, reply, reply_sha256,
# issues text, fail_reason, opened row, replied row or None, closed row or None).
AFTER_3C1_ATTEMPTS: tuple[
    tuple[
        str,
        int,
        str,
        int,
        bytes | None,
        str | None,
        str | None,
        str | None,
        int,
        int | None,
        int | None,
    ],
    ...,
] = (
    ("CP-1", 1, "rejected", 1, REPLIES[1], REPLY_SHA256[1], ISSUES_TEXT_1, None, 3, 7, 9),
    ("CP-1", 2, "failed", 2, None, None, None, "interrupted", 10, None, 16),
    ("CP-1", 3, "accepted", 3, REPLIES[3], REPLY_SHA256[3], "[]", None, 19, 22, 23),
)
OK_UNKNOWN_COLUMNS = {
    **OPEN_CALL_COLUMNS,
    "kind": "ok",
    "stop_reason": "end",
    "reported_model": "m",
    "request_id": "r",
}
OK_PRICED_COLUMNS = {
    **OK_UNKNOWN_COLUMNS,
    "input_tokens": 100,
    "output_tokens": 20,
    "billed_usd": "0.0125",
}
# Calls after SCRIPT_3C1, as AFTER_3B2B_CALLS. The crash-left call (CP-1, 2, 1) stays open (D7).
AFTER_3C1_CALLS: tuple[tuple[str, int, int, str, int, int, int | None, dict[str, object]], ...] = (
    ("CP-1", 1, 0, "ex-1", 0, 4, 6, OK_UNKNOWN_COLUMNS),
    ("CP-1", 2, 0, "ex-1", 1, 11, 12, NOT_SENT_COLUMNS),
    ("CP-1", 2, 1, "ex-1", 2, 13, None, OPEN_CALL_COLUMNS),
    ("CP-1", 3, 0, "ex-2", 0, 20, 21, OK_PRICED_COLUMNS),
)
# No compactions are written by SCRIPT_3C1.

# --- The take-over that ends first (U9), a scripted run of its own: the open attempt waits for the
# resume's start_run. As SCRIPT_3C1.
TAKE_OVER_END_FIRST: tuple[tuple[str, int, dict[str, object], str | None], ...] = (
    ("create", 1, {}, None),
    ("start", 1, {}, None),
    ("open_attempt", 1, _attempt("CP-1", 1), None),
    ("open_call", 1, _call("CP-1", 1, "ex-1", 0), None),
    ("claim", 2, {}, None),
    ("end", 2, {"status": "stopped", "reason": "interrupted"}, None),
    ("fail_attempt", 2, _fail("CP-1", 1), "StoreConflict"),  # the run is stopped
    ("start", 2, {}, None),
    ("fail_attempt", 2, _fail("CP-1", 1), None),
    ("open_attempt", 2, _attempt("CP-1", 2), None),
)
TAKE_OVER_RETURNS = {3: 1, 4: 0, 10: 2}
AFTER_TAKE_OVER_EVENTS: tuple[Event, ...] = (
    ("run_created", None, None, {}),
    ("run_started", None, None, {"from": "created"}),
    ("attempt_opened", "CP-1", 1, {}),
    ("writer_replaced", None, None, {}),
    ("run_ended", None, None, {"status": "stopped", "reason": "interrupted"}),
    ("run_started", None, None, {"from": "stopped"}),
    ("attempt_failed", "CP-1", 1, {"reason": "interrupted"}),
    ("attempt_opened", "CP-1", 2, {}),
)
AFTER_TAKE_OVER_EVENT_ROWS = (1, 2, 3, 5, 6, 8, 9, 10)
# After it: attempt 1 failed (closed_at row 9) with its call 0 still open; attempt 2 open.
AFTER_TAKE_OVER_ATTEMPTS = (("CP-1", 1, "failed", 9), ("CP-1", 2, "open", None))
AFTER_TAKE_OVER_CALLS = (("CP-1", 1, 0, "ex-1", 0, 4, None, OPEN_CALL_COLUMNS),)

# --- Attempt states. Each setup, on a fresh store with a running run (claim 1), brings CP-1
# attempt 1 to the named state through the API: (call, arguments) in order.
STATE_SETUPS: dict[str, tuple[tuple[str, dict[str, object]], ...]] = {
    "open": (("open_attempt", _attempt("CP-1", 1)),),
    "open with call 0": (
        ("open_attempt", _attempt("CP-1", 1)),
        ("open_call", _call("CP-1", 1, "ex-1", 0)),
    ),
    "replied": (
        ("open_attempt", _attempt("CP-1", 1)),
        ("record_reply", _reply_of("CP-1", 1, 1)),
    ),
    "accepted": (
        ("open_attempt", _attempt("CP-1", 1)),
        ("record_reply", _reply_of("CP-1", 1, 1)),
        ("record_verdict", _verdict("CP-1", 1, REPLY_SHA256[1], True)),
    ),
    "rejected": (
        ("open_attempt", _attempt("CP-1", 1)),
        ("record_reply", _reply_of("CP-1", 1, 1)),
        ("record_verdict", _verdict("CP-1", 1, REPLY_SHA256[1], False)),
    ),
    "failed": (("open_attempt", _attempt("CP-1", 1)), ("fail_attempt", _fail("CP-1", 1))),
    "failed with call 0 open": (
        ("open_attempt", _attempt("CP-1", 1)),
        ("open_call", _call("CP-1", 1, "ex-1", 0)),
        ("fail_attempt", _fail("CP-1", 1)),
    ),
}
# Then one call with STATE_CALLS' arguments: (label, setup, call). Each is StoreConflict: the clock
# never called, the full dump unchanged. close_call's reply carries no compaction, so the store's
# own state check, not migration 2's trigger, must refuse it before the clock.
STATE_CALLS: dict[str, dict[str, object]] = {
    "open_call": _call("CP-1", 1, "ex-1", 1),
    "close_call": _close("CP-1", 1, 0, NOT_SENT),
    "record_reply": _reply_of("CP-1", 1, 2),
    "record_verdict": _verdict("CP-1", 1, REPLY_SHA256[1], True),
    "fail_attempt": _fail("CP-1", 1),
}
STATE_CONFLICTS: tuple[tuple[str, str, str], ...] = (
    ("call on a replied attempt", "replied", "open_call"),
    ("call on an accepted attempt", "accepted", "open_call"),
    ("call on a rejected attempt", "rejected", "open_call"),
    ("call on a failed attempt", "failed", "open_call"),
    ("close on a failed attempt", "failed with call 0 open", "close_call"),
    ("reply with call 0 open", "open with call 0", "record_reply"),
    ("reply twice", "replied", "record_reply"),
    ("reply on an accepted attempt", "accepted", "record_reply"),
    ("reply on a failed attempt", "failed", "record_reply"),
    ("verdict on an open attempt", "open", "record_verdict"),
    ("verdict twice", "accepted", "record_verdict"),
    ("verdict after a rejection", "rejected", "record_verdict"),
    ("verdict on a failed attempt", "failed", "record_verdict"),
    ("fail a replied attempt", "replied", "fail_attempt"),
    ("fail an accepted attempt", "accepted", "fail_attempt"),
    ("fail a failed attempt", "failed", "fail_attempt"),
)
# From "replied" (REPLIES[1]), record_verdict with REPLIES[2]'s hash: StoreConflict, as above.
OTHER_HASH_VERDICT = _verdict("CP-1", 1, REPLY_SHA256[2], True)

# --- open_attempt with a latest attempt (U17), from each STATE_SETUPS state: (label, setup,
# request number, error class or None, the number returned or None, whether anything is written).
# A conflict, or a number returned with nothing written, calls the clock zero times and leaves the
# full dump unchanged; a new attempt calls it once and appends attempt_opened.
OPEN_ATTEMPT_REPEATS: tuple[tuple[str, str, int, str | None, int | None, bool], ...] = (
    ("open, same bytes", "open", 1, None, 1, False),
    ("open, other bytes", "open", 2, "StoreConflict", None, False),
    ("replied, same bytes", "replied", 1, "StoreConflict", None, False),
    ("replied, other bytes", "replied", 2, "StoreConflict", None, False),
    ("accepted, same bytes", "accepted", 1, "StoreConflict", None, False),
    ("rejected, same bytes", "rejected", 1, None, 2, True),
    ("rejected, other bytes", "rejected", 2, None, 2, True),
    ("failed, same bytes", "failed", 1, None, 2, True),
    ("failed with a call open", "failed with call 0 open", 2, None, 2, True),
)

# --- Two runs in one store: each attempt lookup is per run. A (RUN_ID) and B (SECOND_RUN_ID) are
# created and started, A first, then the setups named for each, each with its run's claim; then the
# calls, each with its run's claim: (label, A setup, B setup, (call, run, arguments, error class or
# None) in order). Both orders are keyed, so a lookup that drops the run id fails whichever run it
# finds first.
TWO_RUNS_STATES: tuple[
    tuple[str, str, str, tuple[tuple[str, str, dict[str, object], str | None], ...]], ...
] = (
    (
        "A failed, B open",
        "failed with call 0 open",
        "open with call 0",
        (
            ("close_call", "B", _close("CP-1", 1, 0, NOT_SENT), None),
            ("record_reply", "B", _reply_of("CP-1", 1, 1), None),
            ("close_call", "A", _close("CP-1", 1, 0, NOT_SENT), "StoreConflict"),
        ),
    ),
    (
        "A open, B failed",
        "open with call 0",
        "failed with call 0 open",
        (
            ("close_call", "A", _close("CP-1", 1, 0, NOT_SENT), None),
            ("record_reply", "A", _reply_of("CP-1", 1, 1), None),
            ("close_call", "B", _close("CP-1", 1, 0, NOT_SENT), "StoreConflict"),
        ),
    ),
    (
        "A replied, B open",
        "replied",
        "open",
        (
            ("fail_attempt", "B", _fail("CP-1", 1), None),
            ("record_verdict", "A", _verdict("CP-1", 1, REPLY_SHA256[1], True), None),
        ),
    ),
)

# --- Refusals, StoreRefused before BEGIN: the clock never called, the full dump unchanged. On a
# running run whose CP-1 attempt 1 is replied with REPLIES[1] (record_verdict rows) or open with no
# call (the others). (label, call, arguments other than the claim)
_NOT_STR = type("S", (str,), {})


def _r(**changes: object) -> dict[str, object]:
    return {**_reply_of("CP-1", 1, 1), **changes}


def _v(**changes: object) -> dict[str, object]:
    return {**_verdict("CP-1", 1, REPLY_SHA256[1], True), **changes}


def _f(**changes: object) -> dict[str, object]:
    return {**_fail("CP-1", 1), **changes}


REFUSED_ARGUMENTS_3C1: tuple[tuple[str, str, dict[str, object]], ...] = (
    ("reply as text", "record_reply", _r(reply="text")),
    ("reply a bytearray", "record_reply", _r(reply=bytearray(b"r"))),
    ("reply a bytes subclass", "record_reply", _r(reply=type("B", (bytes,), {})(b"r"))),
    ("reply attempt 0", "record_reply", _r(attempt=0)),
    ("reply attempt too large", "record_reply", _r(attempt=_BIG)),
    ("reply module id with a space", "record_reply", _r(module_id="CP 1")),
    ("verdict accepted an int", "record_verdict", _v(accepted=1)),
    ("verdict accepted None", "record_verdict", _v(accepted=None)),
    ("verdict hash upper case", "record_verdict", _v(reply_sha256=REPLY_SHA256[1].upper())),
    ("verdict hash 63 characters", "record_verdict", _v(reply_sha256=REPLY_SHA256[1][1:])),
    ("verdict hash as bytes", "record_verdict", _v(reply_sha256=REPLY_SHA256[1].encode())),
    ("verdict hash a str subclass", "record_verdict", _v(reply_sha256=_NOT_STR(REPLY_SHA256[1]))),
    ("verdict issues a mapping", "record_verdict", _v(issues={"x": 1})),
    ("verdict issues text", "record_verdict", _v(issues="[]")),
    ("verdict issues None", "record_verdict", _v(issues=None)),
    ("verdict issue not a mapping", "record_verdict", _v(issues=("x",))),
    ("verdict issue a float", "record_verdict", _v(issues=({"x": 1.5},))),
    ("verdict issue a bool", "record_verdict", _v(issues=({"x": True},))),
    ("verdict issue key not text", "record_verdict", _v(issues=({1: "x"},))),
    ("verdict issue int too large", "record_verdict", _v(issues=({"x": _BIG},))),
    ("fail reason upper case", "fail_attempt", _f(reason="Interrupted")),
    ("fail reason empty", "fail_attempt", _f(reason="")),
    ("fail reason with a space", "fail_attempt", _f(reason="time out")),
    ("fail reason 65 characters", "fail_attempt", _f(reason="a" * 65)),
    ("fail reason a str subclass", "fail_attempt", _f(reason=_NOT_STR("x"))),
    ("fail reason not text", "fail_attempt", _f(reason=1)),
    ("fail attempt a bool", "fail_attempt", _f(attempt=True)),
)
# Accepted at the edge, from the same setups: each writes (the clock once, its event) and stores
# the text shown as the attempt's issues or fail_reason. (label, call, arguments, stored text)
ACCEPTED_EDGES_3C1: tuple[tuple[str, str, dict[str, object], str], ...] = (
    ("fail reason 64 characters", "fail_attempt", _f(reason="a" * 64), "a" * 64),
    ("issues a list", "record_verdict", _v(issues=[{"b": 1, "a": "x"}]), '[{"a":"x","b":1}]'),
    (
        "issue with a lone surrogate",
        "record_verdict",
        _v(issues=({"n": "a\ud800"},)),
        '[{"n":"a\\\\ud800"}]',
    ),
    ("issue empty", "record_verdict", _v(issues=({},)), "[{}]"),
)
# An attempt the run does not have, on a running run with CP-1 attempt 1 open: StoreRefused,
# nothing written, the clock never called.
MISSING_3C1: tuple[tuple[str, str, dict[str, object]], ...] = (
    ("reply on attempt 2", "record_reply", _reply_of("CP-1", 2, 1)),
    ("verdict on attempt 2", "record_verdict", _verdict("CP-1", 2, REPLY_SHA256[1], True)),
    ("fail attempt 2", "fail_attempt", _fail("CP-1", 2)),
    ("fail another module", "fail_attempt", _fail("CP-9", 1)),
)
# Each with Claim(MISSING_RUN_ID, FOREIGN_TOKEN of the runs part), while run A runs: StoreRefused,
# the clock never called, the full dump unchanged.
MISSING_RUN_3C1: tuple[tuple[str, dict[str, object]], ...] = (
    ("record_reply", _reply_of("CP-1", 1, 1)),
    ("record_verdict", _verdict("CP-1", 1, REPLY_SHA256[1], True)),
    ("fail_attempt", _fail("CP-1", 1)),
)
# As NOT_RUNNING_CALLS, with CP-1 attempt 1 opened while the run ran (replied first for the
# verdict row), for each NOT_RUNNING status with an attempt ("created" and "rejected" have none):
# StoreConflict, no clock, the dump unchanged.
NOT_RUNNING_3C1: tuple[tuple[str, str, dict[str, object]], ...] = (
    ("reply", "record_reply", _reply_of("CP-1", 1, 1)),
    ("verdict", "record_verdict", _verdict("CP-1", 1, REPLY_SHA256[1], True)),
    ("fail", "fail_attempt", _fail("CP-1", 1)),
)
