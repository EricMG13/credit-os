"""One-pass rows for the register-id checks (3A PR 27b): edge rows and counted rows."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from credit_os.checks import passages, structure
from credit_os.checks.findings import CheckContext
from credit_os.handoff.document import parse

KEY: dict[str, Any] = json.loads(
    (Path(__file__).resolve().parent / "expected" / "onepass.json").read_text("utf-8")
)
EDGE: list[dict[str, Any]] = KEY["edge"]
COUNTED: list[dict[str, Any]] = KEY["counted"]

_EDGE_DRAFT = (
    "## Request\nr\n## Sources\n| Source | Use |\n| --- | --- |\n| context | u |\n"
    "## Findings\n### Bottom line\n{bottom_line}### Key findings\nx\n"
    "### Contrary evidence and what would change the view\nx\n### Limitations\nx\n"
    "## Calculations\n{calculations}## Gaps\nNone.\n## Next module\nNone.\n"
)


@pytest.mark.parametrize("row", EDGE, ids=[row["name"] for row in EDGE])
def test_edge_row_findings_whole_and_in_order(row: dict[str, Any]) -> None:
    text = _EDGE_DRAFT.format(bottom_line=row["bottom_line"], calculations=row["calculations"])
    lines = text.split("\n")
    assert lines[8] == row["bottom_line"].split("\n")[0]  # bottom_line is file line 9
    assert lines[16] == row["calculations"].split("\n")[0]  # calculations is file line 17
    document = parse(text.encode("utf-8"))
    context = CheckContext(kind="prose", other_sources=("context",))
    prose = passages.check_register_id(document, context)
    found = structure.check_register_id(document, context)
    assert [[f.line, f.column, f.quoted] for f in prose] == row["prose"]
    assert [[f.line, f.quoted] for f in found] == row["structure"]
    assert all(f.check == "prose.register-id" and f.severity == "refusal" for f in prose)
    assert all(
        f.check == "structure.register-id" and f.severity == "refusal" and f.column == 1
        for f in found
    )


_COUNT_SCRIPT = r"""
import json, sys

from credit_os.checks import passages, structure
from credit_os.checks.findings import CheckContext
from credit_os.handoff.data import read_registers
from credit_os.handoff.document import parse

TOP = "## Request\nr\n## Sources\n| Source | Use |\n| --- | --- |\n| context | u |\n## Findings\n"
LEAD = (
    "### Bottom line\nThe view holds.\n### Key findings\n{key}### Contrary evidence and what "
    "would change the view\nc\n### Limitations\n- l\n"
)
END = "## Gaps\nNone.\n## Next module\nNone.\n"
TABLE = "| id | v |\n| --- | --- |\n"
DASH = chr(0x2014)
CONTEXT = CheckContext(kind="prose", other_sources=("context",))


def draft(key, calculations):
    text = TOP + LEAD.format(key=key) + "## Calculations\n" + calculations + END
    return parse(text.encode("utf-8"))


def prose(name, n):
    if name == "ids beside lines that hold none":
        key = "- x\n" * (2 * n)
        ids = [f"b{i}" for i in range(n)]
    elif name == "an id in every line":
        key = "".join(f"- A{i}\n" for i in range(n))
        ids = [f"A{i}" for i in range(n)]
    else:
        key = "".join(f"- T1 T1.{i}x T1.{i}\n" for i in range(n))
        ids = [f"T1.{i}" for i in range(n)]
    return key, TABLE + "".join(f"| {i} | x |\n" for i in ids)


def structure_text(name, n):
    h = " " + DASH + " "
    if name == "one tag id repeated on one line":
        return "<!--table-id: a1-->" * n + "\n"
    if name == "distinct tags, one to a line":
        return "".join(f"<!-- table-id: a{i} -->\n" for i in range(n))
    if name == "each heading with its own tag":
        return "".join(f"#### T{i}{h}t\n<!-- table-id: T{i} -->\n" for i in range(n))
    if name == "sibling headings of one id, then as many tags":
        return f"#### a.b{h}t\nx\n" * n + "#### End\n" + "<!-- table-id: a.b -->\n" * n
    if name == "groups of four nested headings of one id, then twice as many tags":
        group = "".join("#" * (3 + i) + f" a.b{h}t\n" for i in range(4))
        return group * n + "<!-- table-id: a.b -->\n" * (8 * n)
    return f"#### T1{h}d\nx\n" * n


class Counted(tuple):
    reads = 0

    def __iter__(self):
        for item in tuple.__iter__(self):
            Counted.reads += 1
            yield item

    def __getitem__(self, key):
        found = tuple.__getitem__(self, key)
        Counted.reads += len(found) if isinstance(key, slice) else 1
        return found


def count_events(function):
    events = 0

    def on(frame, event, arg):
        nonlocal events
        if event in ("call", "c_call"):
            events += 1

    sys.setprofile(on)
    try:
        result = function()
    finally:
        sys.setprofile(None)
    return events, result


out = {}
for row in json.loads(sys.stdin.read()):
    if row["kind"] == "prose":
        document = draft(*prose(row["name"], row["n"]))
        events, found = count_events(lambda: passages.check_register_id(document, CONTEXT))
        out[row["name"]] = {"count": events, "findings": len(found)}
    else:
        document = draft("- k\n", structure_text(row["name"], row["n"]))
        registers = Counted(read_registers(document))
        structure.read_registers = lambda _document: registers
        Counted.reads = 0
        found = structure.check_register_id(document, CONTEXT)
        out[row["name"]] = {
            "count": Counted.reads,
            "findings": len(found),
            "registers": len(registers),
        }
print(json.dumps(out))
"""


@pytest.fixture(scope="module")
def counts() -> dict[str, dict[str, int]]:
    """One fresh interpreter counts all nine rows, so neither the coverage tracer nor the
    pattern cache of `re` enters a count (as tests/provider/test_message.py does)."""
    done = subprocess.run(
        [sys.executable, "-c", _COUNT_SCRIPT],
        input=json.dumps(COUNTED),
        capture_output=True,
        text=True,
        check=True,
    )
    result: dict[str, dict[str, int]] = json.loads(done.stdout)
    return result


@pytest.mark.parametrize("row", COUNTED, ids=[row["name"] for row in COUNTED])
def test_counted_row_work_stays_within_its_bound(
    row: dict[str, Any], counts: dict[str, dict[str, int]]
) -> None:
    got = counts[row["name"]]
    assert got["findings"] == row["findings"]
    if row["kind"] == "structure":
        # The counting tuple holds what handoff.data.read_registers returned, which keeps
        # handoff/data.py out of the count until that module's own one-pass fix lands.
        assert got["registers"] == row["registers"]
    assert got["count"] <= row["bound"]
