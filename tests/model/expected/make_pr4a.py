"""Answer key for 1B PR 4a (forecast block, strict JSON, declined), written by the controller.

Data only; every value is invented. Accepted JSON rows are checked here against the standard
library's json (valid input only); refusals are stated by rule. `render()` returns the key's
text; run this file to write `pr4a.json` next to it.
"""

import json
from pathlib import Path
from typing import Any

HEAD = """# CP-2G handoff

## Request
Forward credit model for Northbridge Synthetic Group (nbg), as of 2025-03-31. SYNTHETIC FIXTURE.

## Sources

| Source file name / supplied module | Use |
| --- | --- |
| Financial foundation (CP-1) | Upstream handoff. |

## Findings

### Bottom line

Not assessable: synthetic fixture.
Basis: Financial foundation (CP-1)

"""
TAIL = "\n## Calculations\nNone.\n\n## Gaps\n\nNone.\n\n## Next module\nNone.\n"
SECTION = "### Forecast inputs (machine-readable)\n\n"
ONE = SECTION + '```json\n{"a": 1}\n```\n'
MESSAGES = {
    "block_count": "needs exactly one `Forecast inputs` section, found {n}",
    "block_fence": "the `Forecast inputs` section needs exactly one closed fenced json block",
    "invalid": "the forecast inputs block is not valid JSON",
    "not_object": "the forecast inputs block is not a JSON object",
    "too_deep": "the forecast inputs block nests deeper than 64 levels",
    "too_long": "the forecast inputs block is longer than 200000 characters",
    "repeated": "the forecast inputs block repeats the key `{key}`",
    "fraction": "the forecast inputs block states the number {token} with a fraction or an exponent: write amounts, rates and shares as strings",
    "constant": "the forecast inputs block states {token}, which is not a number",
    "integer": "the forecast inputs block states an integer of more than 15 digits",
    "unicode": "the forecast inputs block holds a string that is not valid Unicode",
    "declined": "the handoff gives no forecast drivers, so no forecast was computed",
}
BLOCKS: list[list[Any]] = [
    ["one section", ONE, {"text": '{"a": 1}'}],
    ["two lines of json", SECTION + '```json\n{\n  "a": 1\n}\n```\n', {"text": '{\n  "a": 1\n}'}],
    [
        "prose around the fence",
        SECTION + 'Stated inputs only.\n\n```json\n{"a": 1}\n```\n\nNo figure is computed here.\n',
        {"text": '{"a": 1}'},
    ],
    ["no section", "", {"refused": ["block_count", {"n": 0}]}],
    ["two sections", ONE + "\n" + ONE, {"refused": ["block_count", {"n": 2}]}],
    ["two fences", ONE + "\n```json\n{}\n```\n", {"refused": ["block_fence", {}]}],
    ["unclosed fence", SECTION + '```json\n{"a": 1}\n', {"refused": ["block_fence", {}]}],
    ["fence without json", SECTION + '```\n{"a": 1}\n```\n', {"refused": ["block_fence", {}]}],
    ["no fence", SECTION + '{"a": 1}\n', {"refused": ["block_fence", {}]}],
]
# A string holding an escaped backslash then an escaped quote; nesting follows it.
ESCAPES = '{"a": "' + "\\" * 3 + '"", "b": '
ACCEPTED = [
    "{}",
    '{"a": 1, "b": "1.50", "c": [true, false, null], "d": {"e": -15}}',
    ' \n{"year": 2026,\n "scale": 1000}\n ',
    '{"n": 999999999999999, "m": -999999999999999, "z": -0}',
    '{"text": "caf\\u00e9 \\ud83d\\ude00 [[[[ {{{{ \\" ]"}',
    '{"a": {"a": {"a": 1}}, "b": [{"a": 1}, {"a": 2}]}',
    '{"amount": "1e3", "rate": "0.0425", "word": "NaN"}',
    ESCAPES + "[" * 63 + "]" * 63 + "}",
]
REFUSED: list[list[Any]] = [
    ["empty", "", "invalid", {}],
    ["truncated", '{"a": 1', "invalid", {}],
    ["trailing comma", '{"a": 1,}', "invalid", {}],
    ["trailing data", '{"a": 1} x', "invalid", {}],
    ["two documents", '{"a": 1}{"b": 2}', "invalid", {}],
    ["single quotes", "{'a': 1}", "invalid", {}],
    ["comment", '// c\n{"a": 1}', "invalid", {}],
    ["byte order mark", '﻿{"a": 1}', "invalid", {}],
    ["raw tab in a string", '{"a": "x\ty"}', "invalid", {}],
    ["leading zero", '{"a": 01}', "invalid", {}],
    ["plus sign", '{"a": +1}', "invalid", {}],
    ["hex", '{"a": 0x10}', "invalid", {}],
    ["an array", "[1]", "not_object", {}],
    ["null", "null", "not_object", {}],
    ["a string", '"x"', "not_object", {}],
    ["an integer", "7", "not_object", {}],
    ["NaN", '{"a": NaN}', "constant", {"token": "NaN"}],
    ["Infinity", '{"a": Infinity}', "constant", {"token": "Infinity"}],
    ["minus Infinity", '{"a": [-Infinity]}', "constant", {"token": "-Infinity"}],
    ["fraction", '{"a": 1.5}', "fraction", {"token": "1.5"}],
    ["point zero", '{"a": 1.0}', "fraction", {"token": "1.0"}],
    ["minus zero point zero", '{"a": -0.0}', "fraction", {"token": "-0.0"}],
    ["exponent", '{"a": 1e3}', "fraction", {"token": "1e3"}],
    ["capital exponent", '{"a": {"b": [2E-2]}}', "fraction", {"token": "2E-2"}],
    ["sixteen digits", '{"a": 1000000000000000}', "integer", {}],
    ["minus sixteen digits", '{"a": -1000000000000000}', "integer", {}],
    ["repeated key", '{"a": 1, "a": 2}', "repeated", {"key": "a"}],
    ["repeated nested key", '{"a": {"b": 1, "c": 2, "b": 3}}', "repeated", {"key": "b"}],
    ["repeated key in an array item", '{"a": [{"k": 1, "k": 1}]}', "repeated", {"key": "k"}],
    ["repeated key by escape", '{"a": 1, "\\u0061": 2}', "repeated", {"key": "a"}],
    ["lone surrogate value", '{"a": "\\ud800"}', "unicode", {}],
    ["lone surrogate key", '{"\\udc00": 1}', "unicode", {}],
    ["lone surrogate in a list", '{"a": ["ok", "x\\ud83dy"]}', "unicode", {}],
    ["form feed before the object", '\f{"a": 1}', "invalid", {}],
    ["no-break space after the object", '{"a": 1}\u00a0', "invalid", {}],
    ["line separator after the object", '{"a": 1}\u2028', "invalid", {}],
    [
        "an escaped backslash and quote, then 65 levels",
        ESCAPES + "[" * 64 + "]" * 64 + "}",
        "too_deep",
        {},
    ],
]
DRIVERS = [
    "revenue_growth",
    "ebitda_margin",
    "capex_pct_revenue",
    "tax_wc_pct_revenue",
    "interest_rate",
    "dividends",
    "debt_repayment",
]


def nulls(**changed: Any) -> dict[str, Any]:
    drivers: dict[str, Any] = {
        name: {
            "values": [None, None, None],
            "category": "Insufficient Information",
            "rationale": "No driver selected.",
            "limitation": "No plan supplied.",
        }
        for name in DRIVERS
    }
    drivers.update(changed)
    return drivers


LONG = "The forward model is blocked. " * 9  # 270 characters
DECLINED: list[list[Any]] = [
    [
        "every driver null",
        {
            "base_drivers": nulls(),
            "scope_limits": ["Blocked: no scenario was supplied.", "Second limit."],
        },
        "Blocked: no scenario was supplied.",
    ],
    [
        "a long first limit is cut to 200",
        {"base_drivers": nulls(), "scope_limits": [LONG]},
        LONG[:197] + "...",
    ],
    ["a limit of exactly 200", {"base_drivers": nulls(), "scope_limits": ["x" * 200]}, "x" * 200],
    ["no scope limits", {"base_drivers": nulls()}, ""],
    ["empty scope limits", {"base_drivers": nulls(), "scope_limits": []}, ""],
    ["first limit not text", {"base_drivers": nulls(), "scope_limits": [7, "text"]}, ""],
    ["scope limits not a list", {"base_drivers": nulls(), "scope_limits": "Blocked."}, ""],
    [
        "one null value per driver",
        {"base_drivers": {name: {"values": [None]} for name in DRIVERS}},
        "",
    ],
    [
        "a single all-null driver",
        {"base_drivers": {"revenue_growth": {"values": [None, None, None]}}},
        "",
    ],
]
STATED = {
    "values": ["0.05", "0.04", "0.03"],
    "category": "Analyst Interpretation",
    "rationale": "Stated.",
    "limitation": None,
}
NOT_DECLINED: list[list[Any]] = [
    ["one driver stated", {"base_drivers": nulls(revenue_growth=STATED)}],
    ["one value stated", {"base_drivers": nulls(dividends={"values": [None, "10", None]})}],
    ["a zero is a value", {"base_drivers": nulls(dividends={"values": [0, None, None]})}],
    ["no base_drivers", {"scope_limits": ["Blocked."]}],
    ["base_drivers empty", {"base_drivers": {}}],
    ["base_drivers a list", {"base_drivers": [None, None]}],
    ["base_drivers null", {"base_drivers": None}],
    ["a driver with no values", {"base_drivers": nulls(dividends={"values": []})}],
    ["a driver that is null", {"base_drivers": nulls(dividends=None)}],
    ["values not a list", {"base_drivers": nulls(dividends={"values": None})}],
    ["values missing", {"base_drivers": nulls(dividends={"category": "x"})}],
]


def line(o: object) -> str:
    return json.dumps(o, separators=(", ", ": "))


def block(name: str, rows: list[list[Any]]) -> str:
    return f' "{name}": [\n  ' + ",\n  ".join(line(r) for r in rows) + "\n ]"


ABOUT = (
    "Step 1B PR 4a answer key, written by the controller. Every value is invented. handoff.head "
    "+ a block row's middle + handoff.tail is a handoff file. A block row is [label, middle, "
    "{text} or {refused: [message name, fields]}]. json.accepted rows are texts whose value is "
    "json.loads of the text; json.refused rows are [label, text, message name, fields]. A "
    "declined row is [label, document, reason]; not_declined rows are [label, document]. "
    "Messages are formatted with str.format(**fields). Implementers do not edit this file."
)


def checked() -> None:
    """The texts the standard library must accept or refuse, as each row says."""
    for accepted in ACCEPTED:
        json.loads(accepted)
    for label, refused, kind, _ in REFUSED:
        assert kind in MESSAGES, kind
        if kind == "invalid":
            try:
                json.loads(refused)
            except ValueError:
                continue
            raise SystemExit(f"{label}: the standard library accepts this text")
        json.loads(refused)  # every other refused row is valid JSON refused by a stricter rule


def render() -> str:
    checked()
    text = (
        "{\n"
        + f' "about": {line(ABOUT)},\n "messages": {line(MESSAGES)},\n'
        + f' "handoff": {line({"head": HEAD, "tail": TAIL})},\n'
        + block("blocks", BLOCKS)
        + ",\n"
        + ' "json": {"max_nesting": 64, "max_characters": 200000, "max_integer_digits": 15,\n'
        + '  "accepted": [\n   '
        + ",\n   ".join(line(t) for t in ACCEPTED)
        + "],\n"
        + '  "refused": [\n   '
        + ",\n   ".join(line(r) for r in REFUSED)
        + "]},\n"
        + block("declined", DECLINED)
        + ",\n"
        + block("not_declined", NOT_DECLINED)
        + "\n}\n"
    )
    assert all(ord(c) < 128 for c in text.replace("\\u", "")), "non-ASCII in key"
    json.loads(text)
    return text


if __name__ == "__main__":
    Path(__file__).with_name("pr4a.json").write_text(render(), "utf-8")
