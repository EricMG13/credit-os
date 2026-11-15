"""Answer key for step 3A, PR 2a: the budget. Written by the controller before the code
existed, by hand; every sum was checked with `bc` (scale=20). Implementers do not edit this
file and do not weaken a comparison against it.

Every value is invented. Rates and holds are not any provider's price (that row is PR 2b's).

A line is written as a tuple and the test builds it:
  ("call", call, state, hold_usd, billed_usd)
  ("compaction", call, event_id, outcome, supersedes, billed_usd)
Amounts are decimal strings (read with `Decimal(text)`) or None. `unknown` lists the indexes,
in the order given, of the lines that make a total unknown. A spent value is compared with
`==` against `Decimal(text)`.
"""

from typing import Any

Line = tuple[Any, ...]

HOLD = "7.17"  # an invented hold, used where the hold does not matter to the row

# ------------------------------------------------------------------ totals
# name -> (lines, spent text or None for unknown, unknown indexes)
TOTALS: dict[str, tuple[list[Line], str | None, list[int]]] = {
    "no_line": ([], "0", []),
    "zero_charge": ([("call", "CP-0/0", "ok", HOLD, "0")], "0", []),
    "not_sent_spent_nothing": ([("call", "CP-0/0", "not_sent", HOLD, None)], "0", []),
    "ok_none_unknown": ([("call", "CP-0/0", "ok", HOLD, None)], None, [0]),
    "sent_usage_none_unknown": ([("call", "CP-0/0", "sent_usage", HOLD, None)], None, [0]),
    "sent_unknown_none_unknown": ([("call", "CP-0/0", "sent_unknown", HOLD, None)], None, [0]),
    # 0.12345678901 + 3.5 + 0.00000000001 + 0.25 = 3.87345678902 (bc)
    "exact_sum": (
        [
            ("call", "CP-0/0", "ok", HOLD, "0.12345678901"),
            ("call", "CP-0/1", "sent_usage", HOLD, "3.5"),
            ("call", "CP-1/0", "ok", HOLD, "0.00000000001"),
            ("compaction", "CP-1/0", "ev-1", "done", None, "0.25"),
        ],
        "3.87345678902",
        [],
    ),
    "compaction_failed_unknown": (
        [
            ("call", "CP-0/0", "ok", HOLD, "1.00"),
            ("compaction", "CP-0/0", "ev-1", "failed", None, None),
        ],
        None,
        [1],
    ),
    # D6: a failed compaction makes the total unknown even when a charge was read.
    "compaction_failed_charged_unknown": (
        [
            ("call", "CP-0/0", "ok", HOLD, "1.00"),
            ("compaction", "CP-0/0", "ev-1", "failed", None, "0.10"),
        ],
        None,
        [1],
    ),
    "compaction_unfinished_unknown": (
        [
            ("call", "CP-0/0", "ok", HOLD, "1.00"),
            ("compaction", "CP-0/0", "ev-1", "unfinished", None, None),
        ],
        None,
        [1],
    ),
    "compaction_done_none_unknown": (
        [("compaction", "CP-0/0", "ev-1", "done", None, None)],
        None,
        [0],
    ),
    # The unfinished one is superseded and dropped; its successor counts: 2 + 0.40 = 2.40.
    "superseded_with_successor": (
        [
            ("call", "CP-0/0", "ok", HOLD, "2"),
            ("compaction", "CP-0/0", "ev-1", "unfinished", None, None),
            ("compaction", "CP-0/1", "ev-2", "done", "ev-1", "0.40"),
        ],
        "2.40",
        [],
    ),
    # Successor listed before the line it supersedes: order does not matter.
    "successor_listed_first": (
        [
            ("compaction", "CP-0/1", "ev-2", "done", "ev-1", "0.40"),
            ("compaction", "CP-0/0", "ev-1", "unfinished", None, None),
            ("call", "CP-0/0", "ok", HOLD, "2"),
        ],
        "2.40",
        [],
    ),
    "superseded_without_successor": (
        [
            ("call", "CP-0/0", "ok", HOLD, "2"),
            ("compaction", "CP-0/0", "ev-1", "unfinished", None, None),
        ],
        None,
        [1],
    ),
    # The unfinished one is dropped; the failed successor is itself unknown.
    "successor_failed": (
        [
            ("compaction", "CP-0/0", "ev-1", "unfinished", None, None),
            ("compaction", "CP-0/1", "ev-2", "failed", "ev-1", None),
        ],
        None,
        [1],
    ),
    # A successor whose target is not among the lines is counted by its own state.
    "successor_target_absent": (
        [("compaction", "CP-0/1", "ev-2", "done", "ev-1", "0.40")],
        "0.40",
        [],
    ),
    # The rule reads state and charge, never the id (D6, C8): a driver id is like any other.
    "driver_id_done_counted": (
        [
            ("call", "CP-0/0", "ok", HOLD, "1"),
            ("compaction", "close", "driver:close-unread", "done", None, "0.03"),
        ],
        "1.03",
        [],
    ),
    "driver_id_unfinished_unknown": (
        [
            ("call", "CP-0/0", "ok", HOLD, "1"),
            ("compaction", "close", "driver:close-unread", "unfinished", None, None),
        ],
        None,
        [1],
    ),
    # D7: an open call makes spend unknown; its hold is never summed.
    "open_call_unknown": (
        [
            ("call", "CP-0/0", "ok", HOLD, "1"),
            ("call", "CP-0/1", "open", HOLD, None),
        ],
        None,
        [1],
    ),
    "several_unknown_in_order": (
        [
            ("call", "CP-0/0", "ok", HOLD, None),
            ("call", "CP-0/1", "ok", HOLD, "1"),
            ("call", "CP-0/2", "open", HOLD, None),
        ],
        None,
        [0, 2],
    ),
    # A 39-digit charge (provider events: at most 39 digits, 11 after the point), summed
    # exactly: 9999999999999999999999999999.99999999999 + 0.00000000001 (bc).
    "charge_39_digits": (
        [
            ("call", "CP-0/0", "ok", HOLD, "9999999999999999999999999999.99999999999"),
            ("call", "CP-0/1", "ok", HOLD, "0.00000000001"),
        ],
        "10000000000000000000000000000.00000000000",
        [],
    ),
    # The store's money bounds at both ends (64 digits, exponent -62..63): 10^63 + 10^-62,
    # 126 significant digits, exact.
    "store_extremes_exact": (
        [
            ("call", "CP-0/0", "ok", HOLD, "1E+63"),
            ("call", "CP-0/1", "ok", HOLD, "1E-62"),
        ],
        "1" + "0" * 63 + "." + "0" * 61 + "1",
        [],
    ),
}

# ------------------------------------------------------------------ admission
# The check before every call, and at launch with no line: spent + next hold <= cap.
# name -> (lines, cap, next hold, admitted, stop or None, indexes of calls whose known
# charge is above their own hold)
ADMISSIONS: dict[str, tuple[list[Line], str, str, bool, str | None, list[int]]] = {
    "launch_equal_passes": ([], "7.17", "7.17", True, None, []),
    "launch_one_unit_short": ([], "7.16999999999", "7.17", False, "capped", []),
    "zero_cap_zero_hold": ([], "0", "0", True, None, []),
    # 12.83 + 7.17 = 20.00 (bc)
    "cap_equal_passes": (
        [("call", "CP-0/0", "ok", HOLD, "12.83")],
        "20",
        "7.17",
        True,
        None,
        [],
    ),
    # 12.83000000001 + 7.17 = 20.00000000001 (bc): one unit of 1E-11 over.
    "cap_one_unit_over": (
        [("call", "CP-0/0", "ok", "12.83000000001", "12.83000000001")],
        "20",
        "7.17",
        False,
        "capped",
        [],
    ),
    "not_sent_spends_nothing": (
        [("call", "CP-0/0", "not_sent", "7.17", None)],
        "7.17",
        "7.17",
        True,
        None,
        [],
    ),
    "unknown_stops": (
        [("call", "CP-0/0", "ok", HOLD, None)],
        "1000",
        "7.17",
        False,
        "spend_unknown",
        [],
    ),
    "open_call_stops": (
        [("call", "CP-0/0", "open", HOLD, None)],
        "1000",
        "7.17",
        False,
        "spend_unknown",
        [],
    ),
    # Unknown is decided first, even when the known part alone is over the cap.
    "unknown_before_capped": (
        [
            ("call", "CP-0/0", "ok", HOLD, None),
            ("call", "CP-0/1", "ok", "19", "19"),
        ],
        "20",
        "7.17",
        False,
        "spend_unknown",
        [],
    ),
    # G5: a known charge above its own hold stops the run; the charge is kept exactly.
    "hold_exceeded": (
        [("call", "CP-0/0", "ok", "7.17", "7.17000000001")],
        "1000",
        "7.17",
        False,
        "hold_exceeded",
        [0],
    ),
    "hold_equal_passes": (
        [("call", "CP-0/0", "ok", "7.17", "7.17")],
        "1000",
        "7.17",
        True,
        None,
        [],
    ),
    "hold_exceeded_on_sent_usage": (
        [("call", "CP-0/0", "sent_usage", "1", "1.5")],
        "1000",
        "1",
        False,
        "hold_exceeded",
        [0],
    ),
    # hold_exceeded is decided before capped: 19.5 + 1 > 20 and 19.5 > 1.
    "hold_exceeded_before_capped": (
        [("call", "CP-0/0", "ok", "1", "19.5")],
        "20",
        "1",
        False,
        "hold_exceeded",
        [0],
    ),
    # spend_unknown is decided before hold_exceeded; the over line is still reported.
    "unknown_before_hold_exceeded": (
        [
            ("call", "CP-0/0", "ok", "1", "2"),
            ("call", "CP-0/1", "open", "1", None),
        ],
        "1000",
        "1",
        False,
        "spend_unknown",
        [0],
    ),
    # A compaction's charge is outside the call's hold, but it is spent: 1 + 5 + 1 = 7 (bc).
    "compaction_outside_hold_but_spent": (
        [
            ("call", "CP-0/0", "ok", "1", "1"),
            ("compaction", "CP-0/0", "ev-1", "done", None, "5"),
        ],
        "7",
        "1",
        True,
        None,
        [],
    ),
    "compaction_tips_over_cap": (
        [
            ("call", "CP-0/0", "ok", "1", "1"),
            ("compaction", "CP-0/0", "ev-1", "done", None, "5.00000000001"),
        ],
        "7",
        "1",
        False,
        "capped",
        [],
    ),
}

# The closed set of stop names (store identifiers: lower case, digits, underscore).
STOPS = ("capped", "hold_exceeded", "spend_unknown")

# ------------------------------------------------------------------ refused data
# Each value, put in the named field of an otherwise valid line, raises BudgetDataError at
# construction. The value is given as ("decimal", text) for Decimal(text), or as the literal.
VALID_CALL: Line = ("call", "CP-0/0", "ok", "1", "1")
VALID_COMPACTION: Line = ("compaction", "CP-0/0", "ev-1", "done", None, "1")

BAD_AMOUNTS: dict[str, Any] = {
    "float": 0.1,
    "int": 1,
    "bool": True,
    "str": "1",
    "nan": ("decimal", "NaN"),
    "snan": ("decimal", "sNaN"),
    "infinity": ("decimal", "Infinity"),
    "negative": ("decimal", "-1"),
    "negative_zero": ("decimal", "-0"),
    "digits_65": ("decimal", "1" * 65),
    "exponent_minus_63": ("decimal", "1E-63"),
    "exponent_64": ("decimal", "1E+64"),
}
# Amounts that are accepted at the bounds (64 digits; exponents -62 and 63).
GOOD_AMOUNTS = ("0", "1" * 64, "1E-62", "1E+63", "0E-62")

# Fields each bad amount is tried in: a call's hold and charge, a compaction's charge, and
# the cap and next hold given to the admission check.
AMOUNT_FIELDS = ("call.hold_usd", "call.billed_usd", "compaction.billed_usd", "cap", "next_hold")

BAD_LINES: dict[str, Line] = {
    "charge_on_not_sent": ("call", "CP-0/0", "not_sent", "1", "0"),
    "charge_on_open": ("call", "CP-0/0", "open", "1", "0"),
    "unknown_state": ("call", "CP-0/0", "closed", "1", "1"),
    "empty_call_name": ("call", "", "ok", "1", "1"),
    "hold_none": ("call", "CP-0/0", "ok", None, "1"),
    "charge_on_unfinished": ("compaction", "CP-0/0", "ev-1", "unfinished", None, "0"),
    "unfinished_supersedes": ("compaction", "CP-0/0", "ev-2", "unfinished", "ev-1", None),
    "unknown_outcome": ("compaction", "CP-0/0", "ev-1", "lost", None, None),
    "empty_event_id": ("compaction", "CP-0/0", "", "done", None, "1"),
    "empty_supersedes": ("compaction", "CP-0/0", "ev-1", "done", "", "1"),
    "supersedes_itself": ("compaction", "CP-0/0", "ev-1", "done", "ev-1", "1"),
    "empty_compaction_call": ("compaction", "", "ev-1", "done", None, "1"),
}

# Sets of valid lines that are refused together, by the total (BudgetDataError).
BAD_SETS: dict[str, list[Line]] = {
    "duplicate_event_id": [
        ("compaction", "CP-0/0", "ev-1", "done", None, "1"),
        ("compaction", "CP-0/1", "ev-1", "done", None, "1"),
    ],
    "two_supersede_one": [
        ("compaction", "CP-0/0", "ev-1", "unfinished", None, None),
        ("compaction", "CP-0/1", "ev-2", "done", "ev-1", "1"),
        ("compaction", "CP-0/2", "ev-3", "done", "ev-1", "1"),
    ],
    "supersedes_a_done_one": [
        ("compaction", "CP-0/0", "ev-1", "done", None, "1"),
        ("compaction", "CP-0/1", "ev-2", "done", "ev-1", "1"),
    ],
}
