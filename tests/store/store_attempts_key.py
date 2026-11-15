"""Answer key 4 (attempts part) of the 2A plan, PR 3b1: `open_attempt` and `open_call`.

Written by the controller before the code existed, from `pr3/api-3b-3c.md` and rulings U8 to U17.
`AttemptsModel` is the reference the tests compare the store with: after any sequence of calls the
store's run, events (kind, module_id, attempt, detail), attempts and calls equal the model's, and a
refused call changes neither. PR 3b2 and 3c add their writes to this file. Implementers do not edit
this file or weaken a comparison against it.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from store_status_key import Model

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
