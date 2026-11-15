"""Answer key 4 (runs part) of the 2A plan: the run status model, the fencing rules and a scripted run.

Written by the controller before the code existed. `Model` is the reference the stateful test
compares the store with: after any sequence of calls the store's run and events equal the model's,
and a refused call changes neither. Attempts join the model in PR 3. Implementers do not edit this
file or weaken a comparison against it.
"""

from dataclasses import dataclass, field

STATE_KINDS = frozenset({"run_created", "writer_replaced", "run_started", "run_ended"})
END_STATUSES = frozenset({"finished", "stopped", "failed"})
FINAL_STATUSES = frozenset({"finished", "rejected"})

# PR 3b1 (U8): runs.STATE_KINDS gains the five attempt kinds, so record_event refuses them as well.
ATTEMPT_KINDS = frozenset(
    {"attempt_opened", "attempt_replied", "attempt_failed", "attempt_accepted", "attempt_rejected"}
)
STATE_KINDS |= ATTEMPT_KINDS


def fold(events: list[tuple[str, dict[str, object]]]) -> str | None:
    """The status a run's (kind, detail) events in seq order give; None before `run_created`."""
    status: str | None = None
    for kind, detail in events:
        if kind == "run_created":
            status = "created"
        elif kind == "run_started":
            status = "running"
        elif kind == "run_ended":
            status = str(detail["status"])
    return status


@dataclass
class Model:
    """One run: its status, whether it has started, its current token and its events."""

    status: str | None = None
    started: bool = False
    token: int = 0  # which claim holds the run: 1 for create_run's, +1 per claim_run
    events: list[tuple[str, dict[str, object]]] = field(default_factory=list)

    def create(self) -> str | None:
        if self.status is not None:
            return "StoreConflict"
        self.status, self.token = "created", 1
        self.events.append(("run_created", {}))
        return None

    def claim(self) -> str | None:
        if self.status is None:
            return "StoreRefused"
        if self.status in FINAL_STATUSES:
            return "StoreConflict"
        self.token += 1
        self.events.append(("writer_replaced", {}))
        return None

    def _gate(self, token: int, allowed: frozenset[str]) -> str | None:
        if self.status is None:
            return "StoreRefused"
        if token != self.token:
            return "StoreFenced"
        return None if self.status in allowed else "StoreConflict"

    def start(self, token: int) -> str | None:
        refused = self._gate(token, frozenset({"created", "stopped", "failed"}))
        if refused is None:
            self.events.append(("run_started", {"from": self.status}))
            self.status, self.started = "running", True
        return refused

    def reject(self, token: int, reason: str) -> str | None:
        refused = self._gate(token, frozenset({"created"}))
        if refused is None:
            self.status = "rejected"
            self.events.append(("run_ended", {"status": "rejected", "reason": reason}))
        return refused

    def end(self, token: int, status: str, reason: str) -> str | None:
        if status not in END_STATUSES:
            return "StoreRefused"
        refused = self._gate(token, frozenset({"running"}))
        if refused is None:
            self.status = status
            self.events.append(("run_ended", {"status": status, "reason": reason}))
        return refused

    def note(self, token: int, kind: str, detail: dict[str, object]) -> str | None:
        if kind in STATE_KINDS:
            return "StoreRefused"
        refused = self._gate(token, frozenset({"created", "running", "stopped", "failed"}))
        if refused is None:
            self.events.append((kind, detail))
        return refused


# A scripted run: (call, claim number, arguments, error class or None). Claim 1 is create_run's.
SCRIPT: tuple[tuple[str, int, dict[str, object], str | None], ...] = (
    ("create", 1, {}, None),
    ("end", 1, {"status": "finished", "reason": "done"}, "StoreConflict"),
    ("start", 1, {}, None),
    ("note", 1, {"kind": "module_opened", "detail": {"module": "CP-1"}}, None),
    ("end", 1, {"status": "stopped", "reason": "cap_reached"}, None),
    ("claim", 2, {}, None),
    ("start", 1, {}, "StoreFenced"),
    ("start", 2, {}, None),
    ("reject", 2, {"reason": "late"}, "StoreConflict"),
    ("end", 2, {"status": "finished", "reason": "done"}, None),
    ("claim", 3, {}, "StoreConflict"),
    ("note", 2, {"kind": "late_note", "detail": {}}, "StoreConflict"),
)
# The run and its events after SCRIPT: status, started_at set, ended_at set, end_reason, and the
# events as (kind, detail) in seq order, seq 1 to 7 with no gap.
AFTER_SCRIPT_STATUS = "finished"
AFTER_SCRIPT_END_REASON = "done"
AFTER_SCRIPT_EVENTS: tuple[tuple[str, dict[str, object]], ...] = (
    ("run_created", {}),
    ("run_started", {"from": "created"}),
    ("module_opened", {"module": "CP-1"}),
    ("run_ended", {"status": "stopped", "reason": "cap_reached"}),
    ("writer_replaced", {}),
    ("run_started", {"from": "stopped"}),
    ("run_ended", {"status": "finished", "reason": "done"}),
)
# started_at is the time of the first start and never moves; a resume clears ended_at,
# end_reason and end_message until the next end.
STARTED_AT_CALL = 3  # SCRIPT row number (1-based) whose clock value is started_at

# Arguments refused before anything is written (StoreRefused): (label, call, arguments). Each runs
# with the run's valid claim on a run in a status the call otherwise allows (claim, reject: created;
# end, note: running); the clock is never called and the full dump is unchanged.
REFUSED_ARGUMENTS: tuple[tuple[str, str, dict[str, object]], ...] = (
    ("end status running", "end", {"status": "running", "reason": "done"}),
    ("end status rejected", "end", {"status": "rejected", "reason": "done"}),
    ("reason upper case", "end", {"status": "stopped", "reason": "Cap"}),
    ("reason empty", "reject", {"reason": ""}),
    ("reason too long", "end", {"status": "failed", "reason": "r" * 65}),
    ("note a state kind", "note", {"kind": "run_started", "detail": {}}),
    ("note kind with a dash", "note", {"kind": "module-opened", "detail": {}}),
    ("note detail a float", "note", {"kind": "module_opened", "detail": {"cost": 1.5}}),
    ("note attempt without module", "note", {"kind": "module_opened", "detail": {}, "attempt": 1}),
    (
        "note attempt zero",
        "note",
        {"kind": "module_opened", "detail": {}, "module_id": "CP-1", "attempt": 0},
    ),
    (
        "note attempt a bool",
        "note",
        {"kind": "module_opened", "detail": {}, "module_id": "CP-1", "attempt": True},
    ),
    (
        "note module id with a space",
        "note",
        {"kind": "module_opened", "detail": {}, "module_id": "CP 1"},
    ),
    ("end message not text", "end", {"status": "stopped", "reason": "done", "message": 5}),
    ("reject reason starting with a digit", "reject", {"reason": "1late"}),
    ("claim run id with a space", "claim", {"run_id": "run 1"}),
    ("end status a list", "end", {"status": ["finished"], "reason": "done"}),
    (
        "note attempt too large",
        "note",
        {"kind": "module_opened", "detail": {}, "module_id": "CP-1", "attempt": 2**63},
    ),
)
# A claim for another run, or with a token of the right shape that is not the writer: StoreFenced.
# Both on start_run of a created run: Claim(run_id, FOREIGN_TOKEN), and Claim(this run's id, a second
# run's real token). Nothing written; the clock never called.
FOREIGN_TOKEN = "0" * 32

# The held lock (hostile set): a second raw connection holds BEGIN IMMEDIATE; with busy_seconds
# 0.2 each write method is StoreBusy and the file's bytes are unchanged once the holder rolls back.
HELD_LOCK_BUSY_SECONDS = 0.2
HELD_LOCK_ERROR = "StoreBusy"

# --- Added for PR 2c (controller) ------------------------------------------------------------------

# The test's clock answers SCRIPT row n (1-based) with datetime(2026, 9, 30, 12, 0, n, tzinfo=UTC);
# these are the texts the store keeps. A refused row calls the clock zero times: inside the
# transaction the checks (run exists, token, status) come before a write's one clock call.
SCRIPT_ROW_TIMES = {n: f"2026-09-30T12:00:{n:02d}.000000Z" for n in range(1, len(SCRIPT) + 1)}
AFTER_SCRIPT_EVENT_ROWS = (1, 3, 4, 5, 6, 8, 10)  # the SCRIPT row whose time is each event's `at`
ENDED_AT_CALL = 10  # SCRIPT row whose time is ended_at after SCRIPT

# Resume clears the end: create, start, end_run(status="stopped", reason="cap_reached",
# message=END_MESSAGE). The run then reads end_message END_MESSAGE_STORED (a lone surrogate escaped);
# after start_run again, ended_at, end_reason and end_message are None and started_at is unchanged.
END_MESSAGE = "cap \ud800 reached"
END_MESSAGE_STORED = "cap \\ud800 reached"

# Claims refused as input by start_run on a created run (StoreRefused before BEGIN, the clock never
# called, nothing written): (label, run_id, token) passed as Claim(run_id, token), the run's own id
# where run_id is None. NOT_A_CLAIM, a plain tuple, is passed in place of a Claim.
REFUSED_CLAIMS: tuple[tuple[str, str | None, object], ...] = (
    ("token 31 hex", None, "0" * 31),
    ("token 33 hex", None, "0" * 33),
    ("token upper case", None, "A" * 32),
    ("token non-ASCII", None, "\u00e9" * 32),
    ("token not text", None, 5),
    ("run id with a space", "run 1", "0" * 32),
    ("run id empty", "", "0" * 32),
)
NOT_A_CLAIM = ("run-1", "0" * 32)

# The held lock covers every write method, each on a run in a status it allows (create: a new id).
HELD_LOCK_CALLS = ("create", "claim", "start", "reject", "end", "note")

# Notes recorded as given (record_event on a running run with its valid claim): (label, kind, detail,
# module_id, attempt). The run's last event then reads back with exactly this kind, module_id,
# attempt and detail.
ACCEPTED_NOTES: tuple[tuple[str, str, dict[str, object], str | None, int | None], ...] = (
    ("module and attempt", "module_opened", {"module": "CP-1"}, "CP-1", 2),
    ("module only", "module_closed", {}, "CP-2", None),
    ("neither", "budget_checked", {"count": 3, "left": None}, None, None),
    ("first attempt", "module_opened", {}, "CP-1", 1),
    ("largest attempt", "module_opened", {}, "CP-1", 2**63 - 1),
)

# A reject's message is stored: reject_run(claim, reason=REJECT_REASON, message=END_MESSAGE) on a
# created run reads back status "rejected", end_reason REJECT_REASON, end_message END_MESSAGE_STORED.
REJECT_REASON = "late"

# start_run from a status it may not start from, with the run's valid claim: StoreConflict, the clock
# never called, the full dump unchanged.
START_REFUSED_STATUSES = ("running", "finished", "rejected")

# --- Added for PR 3a (controller; rulings U1 and U2, under the owner's instruction of 2026-11-14
# 22:20 UTC) ----------------------------------------------------------------------------------------


class NameSubclass(str):
    """A `str` subclass. Ruling U2: a name (an event kind, an end or reject reason) must be exactly
    `str`, so any instance of this is StoreRefused, whatever its text."""


class SlyName(str):
    """A `str` subclass that hides from a set: equal to nothing and hashed as another text, so
    `SlyName("run_started") in STATE_KINDS` is False. Refused by its type alone (U2)."""

    def __eq__(self, other: object) -> bool:
        return False

    def __hash__(self) -> int:
        return hash("not a state kind")


# Refused like REFUSED_ARGUMENTS (StoreRefused before anything is written, the clock never called,
# the full dump unchanged): (label, call, arguments).
REFUSED_NAME_TYPES: tuple[tuple[str, str, dict[str, object]], ...] = (
    ("note kind a str subclass", "note", {"kind": NameSubclass("module_opened"), "detail": {}}),
    ("note kind hiding a state kind", "note", {"kind": SlyName("run_started"), "detail": {}}),
    ("end reason a str subclass", "end", {"status": "stopped", "reason": NameSubclass("done")}),
    ("reject reason a str subclass", "reject", {"reason": NameSubclass("late")}),
)

# U1: a stored writer that is not a 32-character lower-case hex token. With the store open, a raw
# second connection runs `PRAGMA ignore_check_constraints = ON` and then
# `UPDATE runs SET writer = ?` with the damaged text, on a run that is created (for claim, start and
# reject) or running (for end and note). Then each call of DAMAGED_WRITER_CALLS, made with the run's
# last valid claim, is StoreCorrupt with exactly STORED_WRITER_MESSAGE, the clock is never called,
# and runs, run_sources and events read back unchanged as bytes. `claim_run` refuses rather than
# replacing the writer; the message never holds the stored text.
DAMAGED_WRITERS: tuple[tuple[str, str], ...] = (
    ("not hex", "z" * 32),
    ("not ASCII", "é" * 16),
    ("upper case", "A" * 32),
    ("31 characters", "0" * 31),
    ("33 characters", "0" * 33),
    ("empty", ""),
)
DAMAGED_WRITER_CALLS = ("claim", "start", "reject", "end", "note")
STORED_WRITER_MESSAGE = "stored writer is not a token"
