"""Answer key for step 3A, PR 2a: the budget. Written by the controller before the code
existed, by hand; every sum was checked with `bc` (scale=20). Implementers do not edit this
file and do not weaken a comparison against it.

Every value is invented. Rates and holds are not any provider's price (that row is PR 2b's).

A line is a tuple the test builds (`_c` and `_k` only write the tuples compactly):
  ("call", call, state, hold_usd, billed_usd)
  ("compaction", call, event_id, outcome, supersedes, billed_usd)
Amounts are decimal strings (read with `Decimal(text)`) or None. `unknown` lists the indexes,
in the order given, of the lines that make a total unknown. A spent value is compared with
`==` against `Decimal(text)`.
"""

from typing import Any

Line = tuple[Any, ...]

HOLD = "7.17"  # an invented hold, used where the hold does not matter to the row


def _c(call: str, state: str, hold: str | None, billed: str | None) -> Line:
    return ("call", call, state, hold, billed)


def _k(call: str, event: str, outcome: str, supersedes: str | None, billed: str | None) -> Line:
    return ("compaction", call, event, outcome, supersedes, billed)


# ------------------------------------------------------------------ totals
# name -> (lines, spent text or None for unknown, unknown indexes)
TOTALS: dict[str, tuple[list[Line], str | None, list[int]]] = {
    "no_line": ([], "0", []),
    "zero_charge": ([_c("CP-0/0", "ok", HOLD, "0")], "0", []),
    "not_sent_spent_nothing": ([_c("CP-0/0", "not_sent", HOLD, None)], "0", []),
    "ok_none_unknown": ([_c("CP-0/0", "ok", HOLD, None)], None, [0]),
    "sent_usage_none_unknown": ([_c("CP-0/0", "sent_usage", HOLD, None)], None, [0]),
    "sent_unknown_none_unknown": ([_c("CP-0/0", "sent_unknown", HOLD, None)], None, [0]),
    # 0.12345678901 + 3.5 + 0.00000000001 + 0.25 = 3.87345678902 (bc)
    "exact_sum": (
        [
            _c("CP-0/0", "ok", HOLD, "0.12345678901"),
            _c("CP-0/1", "sent_usage", HOLD, "3.5"),
            _c("CP-1/0", "ok", HOLD, "0.00000000001"),
            _k("CP-1/0", "ev-1", "done", None, "0.25"),
        ],
        "3.87345678902",
        [],
    ),
    "compaction_failed_unknown": (
        [_c("CP-0/0", "ok", HOLD, "1.00"), _k("CP-0/0", "ev-1", "failed", None, None)],
        None,
        [1],
    ),
    # D6: a failed compaction makes the total unknown even when a charge was read.
    "compaction_failed_charged_unknown": (
        [_c("CP-0/0", "ok", HOLD, "1.00"), _k("CP-0/0", "ev-1", "failed", None, "0.10")],
        None,
        [1],
    ),
    "compaction_unfinished_unknown": (
        [_c("CP-0/0", "ok", HOLD, "1.00"), _k("CP-0/0", "ev-1", "unfinished", None, None)],
        None,
        [1],
    ),
    "compaction_done_none_unknown": ([_k("CP-0/0", "ev-1", "done", None, None)], None, [0]),
    # The unfinished one is superseded and dropped; its successor counts: 2 + 0.40 = 2.40.
    "superseded_with_successor": (
        [
            _c("CP-0/0", "ok", HOLD, "2"),
            _k("CP-0/0", "ev-1", "unfinished", None, None),
            _k("CP-0/1", "ev-2", "done", "ev-1", "0.40"),
        ],
        "2.40",
        [],
    ),
    # Successor listed before the line it supersedes: order does not matter.
    "successor_listed_first": (
        [
            _k("CP-0/1", "ev-2", "done", "ev-1", "0.40"),
            _k("CP-0/0", "ev-1", "unfinished", None, None),
            _c("CP-0/0", "ok", HOLD, "2"),
        ],
        "2.40",
        [],
    ),
    "superseded_without_successor": (
        [_c("CP-0/0", "ok", HOLD, "2"), _k("CP-0/0", "ev-1", "unfinished", None, None)],
        None,
        [1],
    ),
    # The unfinished one is dropped; the failed successor is itself unknown.
    "successor_failed": (
        [
            _k("CP-0/0", "ev-1", "unfinished", None, None),
            _k("CP-0/1", "ev-2", "failed", "ev-1", None),
        ],
        None,
        [1],
    ),
    # A successor whose target is not among the lines is counted by its own state.
    "successor_target_absent": ([_k("CP-0/1", "ev-2", "done", "ev-1", "0.40")], "0.40", []),
    # The rule reads state and charge, never the id (D6, C8): a driver id is like any other.
    "driver_id_done_counted": (
        [_c("CP-0/0", "ok", HOLD, "1"), _k("close", "driver:close-unread", "done", None, "0.03")],
        "1.03",
        [],
    ),
    "driver_id_unfinished_unknown": (
        [
            _c("CP-0/0", "ok", HOLD, "1"),
            _k("close", "driver:close-unread", "unfinished", None, None),
        ],
        None,
        [1],
    ),
    # D7: an open call makes spend unknown; its hold is never summed.
    "open_call_unknown": (
        [_c("CP-0/0", "ok", HOLD, "1"), _c("CP-0/1", "open", HOLD, None)],
        None,
        [1],
    ),
    "several_unknown_in_order": (
        [
            _c("CP-0/0", "ok", HOLD, None),
            _c("CP-0/1", "ok", HOLD, "1"),
            _c("CP-0/2", "open", HOLD, None),
        ],
        None,
        [0, 2],
    ),
    # A 39-digit charge (provider events: at most 39 digits, 11 after the point), summed
    # exactly: 9999999999999999999999999999.99999999999 + 0.00000000001 (bc).
    "charge_39_digits": (
        [
            _c("CP-0/0", "ok", HOLD, "9999999999999999999999999999.99999999999"),
            _c("CP-0/1", "ok", HOLD, "0.00000000001"),
        ],
        "10000000000000000000000000000.00000000000",
        [],
    ),
    # The store's money bounds at both ends (64 digits, exponent -62..63): 10^63 + 10^-62,
    # 126 significant digits, exact.
    "store_extremes_exact": (
        [_c("CP-0/0", "ok", HOLD, "1E+63"), _c("CP-0/1", "ok", HOLD, "1E-62")],
        "1" + "0" * 63 + "." + "0" * 61 + "1",
        [],
    ),
}

# ------------------------------------------------------------------ admission
# The check before every call, and at launch with no line: spent + next hold <= cap.
# name -> (lines, cap, next hold, admitted, stop or None, indexes of calls whose known
# charge is above their own hold)
Admit = tuple[list[Line], str, str, bool, str | None, list[int]]
ADMISSIONS: dict[str, Admit] = {
    "launch_equal_passes": ([], "7.17", "7.17", True, None, []),
    "launch_one_unit_short": ([], "7.16999999999", "7.17", False, "capped", []),
    "zero_cap_zero_hold": ([], "0", "0", True, None, []),
    # 12.83 + 7.17 = 20.00 (bc)
    "cap_equal_passes": ([_c("CP-0/0", "ok", "12.83", "12.83")], "20", "7.17", True, None, []),
    # 12.83000000001 + 7.17 = 20.00000000001 (bc): one unit of 1E-11 over.
    "cap_one_unit_over": (
        [_c("CP-0/0", "ok", "12.83000000001", "12.83000000001")],
        "20",
        "7.17",
        False,
        "capped",
        [],
    ),
    "not_sent_spends_nothing": (
        [_c("CP-0/0", "not_sent", "7.17", None)],
        "7.17",
        "7.17",
        True,
        None,
        [],
    ),
    "unknown_stops": ([_c("CP-0/0", "ok", HOLD, None)], "1000", "7.17", False, "spend_unknown", []),
    "open_call_stops": (
        [_c("CP-0/0", "open", HOLD, None)],
        "1000",
        "7.17",
        False,
        "spend_unknown",
        [],
    ),
    # Unknown is decided first, even when the known part alone is over the cap.
    "unknown_before_capped": (
        [_c("CP-0/0", "ok", HOLD, None), _c("CP-0/1", "ok", "19", "19")],
        "20",
        "7.17",
        False,
        "spend_unknown",
        [],
    ),
    # G5: a known charge above its own hold stops the run; the charge is kept exactly.
    "hold_exceeded": (
        [_c("CP-0/0", "ok", "7.17", "7.17000000001")],
        "1000",
        "7.17",
        False,
        "hold_exceeded",
        [0],
    ),
    "hold_equal_passes": ([_c("CP-0/0", "ok", "7.17", "7.17")], "1000", "7.17", True, None, []),
    "hold_exceeded_on_sent_usage": (
        [_c("CP-0/0", "sent_usage", "1", "1.5")],
        "1000",
        "1",
        False,
        "hold_exceeded",
        [0],
    ),
    # hold_exceeded is decided before capped: 19.5 + 1 > 20 and 19.5 > 1.
    "hold_exceeded_before_capped": (
        [_c("CP-0/0", "ok", "1", "19.5")],
        "20",
        "1",
        False,
        "hold_exceeded",
        [0],
    ),
    # spend_unknown is decided before hold_exceeded; the over line is still reported.
    "unknown_before_hold_exceeded": (
        [_c("CP-0/0", "ok", "1", "2"), _c("CP-0/1", "open", "1", None)],
        "1000",
        "1",
        False,
        "spend_unknown",
        [0],
    ),
    # A compaction's charge is outside the call's hold, but it is spent: 1 + 5 + 1 = 7 (bc).
    "compaction_outside_hold_but_spent": (
        [_c("CP-0/0", "ok", "1", "1"), _k("CP-0/0", "ev-1", "done", None, "5")],
        "7",
        "1",
        True,
        None,
        [],
    ),
    "compaction_tips_over_cap": (
        [_c("CP-0/0", "ok", "1", "1"), _k("CP-0/0", "ev-1", "done", None, "5.00000000001")],
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
VALID_CALL: Line = _c("CP-0/0", "ok", "1", "1")
VALID_COMPACTION: Line = _k("CP-0/0", "ev-1", "done", None, "1")

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
    "charge_on_not_sent": _c("CP-0/0", "not_sent", "1", "0"),
    "charge_on_open": _c("CP-0/0", "open", "1", "0"),
    "unknown_state": _c("CP-0/0", "closed", "1", "1"),
    "empty_call_name": _c("", "ok", "1", "1"),
    "hold_none": _c("CP-0/0", "ok", None, "1"),
    "charge_on_unfinished": _k("CP-0/0", "ev-1", "unfinished", None, "0"),
    "unfinished_supersedes": _k("CP-0/0", "ev-2", "unfinished", "ev-1", None),
    "unknown_outcome": _k("CP-0/0", "ev-1", "lost", None, None),
    "empty_event_id": _k("CP-0/0", "", "done", None, "1"),
    "empty_supersedes": _k("CP-0/0", "ev-1", "done", "", "1"),
    "supersedes_itself": _k("CP-0/0", "ev-1", "done", "ev-1", "1"),
    "empty_compaction_call": _k("", "ev-1", "done", None, "1"),
}

# Sets of valid lines that are refused together, by the total (BudgetDataError).
BAD_SETS: dict[str, list[Line]] = {
    "duplicate_event_id": [
        _k("CP-0/0", "ev-1", "done", None, "1"),
        _k("CP-0/1", "ev-1", "done", None, "1"),
    ],
    "two_supersede_one": [
        _k("CP-0/0", "ev-1", "unfinished", None, None),
        _k("CP-0/1", "ev-2", "done", "ev-1", "1"),
        _k("CP-0/2", "ev-3", "done", "ev-1", "1"),
    ],
    "supersedes_a_done_one": [
        _k("CP-0/0", "ev-1", "done", None, "1"),
        _k("CP-0/1", "ev-2", "done", "ev-1", "1"),
    ],
}


# ------------------------------------------------------------------ PR 9b: price rows and the first hold
# Added by the controller for PR 9b (ruling 8, `.superpowers/sdd/3a/9b/rulings.md`), by hand: each
# hold worked with `bc`: context tokens x the dearest input-side rate, plus held output tokens x the
# dearest output rate, over 1,000,000; the held output tokens are the larger of the request's output
# cap and the row's floor.
# (config id, input-side rates, output rates, context tokens, output floor tokens). Rates are
# USD per million tokens, as decimal text. In PRICE_A the dearest rate is neither the first nor
# the last input rate and is the first output rate: a hold that takes a fixed position differs.
Price = tuple[Any, Any, Any, Any, Any]
PRICE_A: Price = ("synthetic-medium", ("1.25", "3.75", "0.125"), ("12.25", "9.5"), 400000, 64000)
PRICE_B: Price = ("synthetic-plain", ("2",), ("8",), 250000, 0)
# 31 places: 400000 x this rate has 36 digits, more than the default decimal context keeps.
PRICE_C: Price = ("synthetic-fine", ("0.1234567890123456789012345678901",), ("1",), 400000, 1000)
MAX_OUTPUT = 32000  # the request's output cap of every launch row below (invented here)

# name -> (price, the request's output cap, the hold); compared with `==` on Decimal(text).
HOLDS: dict[str, tuple[Price, int, str]] = {
    # 400000 x 3.75 = 1500000; the floor 64000 is above the cap 32000: 64000 x 12.25 = 784000;
    # 2284000 / 1000000 = 2.284 (bc)
    "floor_above_the_request_cap": (PRICE_A, 32000, "2.284"),
    "floor_equal_to_the_request_cap": (PRICE_A, 64000, "2.284"),
    # the cap 100000 is above the floor: 100000 x 12.25 = 1225000; 2725000 / 1000000 = 2.725 (bc)
    "request_cap_above_the_floor": (PRICE_A, 100000, "2.725"),
    # no floor: 250000 x 2 + 16000 x 8 = 628000; / 1000000 = 0.628 (bc)
    "no_floor": (PRICE_B, 16000, "0.628"),
    # an output cap of zero and no floor: the input side alone, 500000 / 1000000 = 0.5
    "no_output_held": (PRICE_B, 0, "0.5"),
    # 400000 x 0.1234567890123456789012345678901 = 49382.71560493827156049382715604; + 1000 x 1;
    # / 1000000 (bc, scale 40). Exact: no digit is rounded away.
    "exact_past_28_digits": (PRICE_C, 1000, "0.05038271560493827156049382715604"),
}
# Ruling 6: where a refusal shows the hold it is `format(hold, "f")`, the digits the arithmetic
# carries: the finer rate's places plus six. 3.75 and 12.25 carry two places, so eight.
HOLD_A_TEXT = "2.28400000"

# `call_hold` raises BudgetDataError: name -> (price, the request's output cap).
HOLDS_REFUSED: dict[str, tuple[Price, int]] = {
    # 1 x 1E-57 over 1,000,000 has its last digit at 1E-63, outside the store's money bounds
    # (exponents -62..63): refused, never rounded.
    "does_not_fit_the_money_bounds": (("synthetic-tiny", ("1E-57",), ("1",), 1, 1), 1),
    "zero_hold": (("synthetic-free", ("0",), ("0",), 1, 1), 1),  # ruling 5: it bounds nothing
}
# Each value, put in the named field of PRICE_A, raises BudgetDataError when the row is built.
# ("decimal", text) is Decimal(text); every other value is used as written.
BAD_PRICES: dict[str, tuple[str, Any]] = {
    "config_empty": ("config_id", ""),
    "config_not_text": ("config_id", 7),
    "no_input_rate": ("input_rates", ()),
    "no_output_rate": ("output_rates", ()),
    "input_rates_a_list": ("input_rates", [("decimal", "3.75")]),
    "input_rate_text": ("input_rates", ("3.75",)),
    "input_rate_float": ("input_rates", (3.75,)),
    "input_rate_negative": ("input_rates", (("decimal", "-1"),)),
    "output_rate_nan": ("output_rates", (("decimal", "NaN"),)),
    "output_rate_int": ("output_rates", (12,)),
    "context_tokens_zero": ("context_tokens", 0),
    "context_tokens_negative": ("context_tokens", -1),
    "context_tokens_bool": ("context_tokens", True),
    "context_tokens_float": ("context_tokens", 400000.0),
    "floor_negative": ("output_floor_tokens", -1),
    "floor_bool": ("output_floor_tokens", False),
}
# The request's output cap given to `call_hold` and to `prepare`: each raises BudgetDataError.
BAD_OUTPUT_CAPS: dict[str, Any] = {"negative": -1, "bool": True, "float": 32000.0, "text": "32000"}
