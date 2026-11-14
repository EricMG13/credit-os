import hashlib
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from credit_os.checks.findings import CHECKS, CheckContext, Finding, ordered
from credit_os.handoff.document import parse
from credit_os.sources.pins import SourceKind, SourcePin

HANDOFFS = Path(__file__).resolve().parent.parent / "fixtures" / "handoffs"

EXPECTED_CHECKS = [
    "structure.format",
    "structure.reader-summary",
    "structure.reader",
    "structure.passages",
    "structure.fence",
    "structure.register-id",
    "structure.registers",
    "prose.bottom-line",
    "prose.bottom-line-length",
    "prose.module-code",
    "prose.page",
    "prose.hash",
    "prose.bracket",
    "prose.pipeline-wording",
    "prose.provider-marker",
    "prose.register-id",
    "prose.limitation-repeat",
    "sources.table",
    "sources.name",
    "sources.sha256",
    "sources.type",
    "figure.form",
    "figure.not-held",
    "figure.mismatch",
    "confidence.absent",
    "confidence.repeated",
    "confidence.unreadable",
    "confidence.blocked-row",
    "confidence.front-matter",
    "confidence.rows",
    "confidence.count",
    "confidence.range",
]


def _finding(**changes: Any) -> Finding:
    values: dict[str, Any] = {
        "check": "structure.fence",
        "severity": "refusal",
        "line": 15,
        "quoted": "x = 1",
        "reason": "Close the code block with a line of three backticks.",
    }
    values.update(changes)
    return Finding(**values)


def _set(target: object, name: str, value: object) -> None:
    setattr(target, name, value)


def _context(**values: Any) -> CheckContext:
    return CheckContext(**values)


def test_checks_closed_tuple() -> None:
    assert list(CHECKS) == EXPECTED_CHECKS
    assert len(set(CHECKS)) == 32


def test_message() -> None:
    assert _finding().message == (
        'structure.fence, line 15: "x = 1": Close the code block with a line of three backticks.'
    )


def test_column_default() -> None:
    assert _finding().column == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"check": "structure.nope"},
        {"line": 0},
        {"column": 0},
        {"severity": "error"},
        {"reason": ""},
        {"extra": 1},
    ],
)
def test_refused(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        _finding(**changes)


def test_frozen() -> None:
    finding = _finding()
    with pytest.raises(ValidationError):
        _set(finding, "line", 2)


def test_quoted_80_unchanged() -> None:
    assert _finding(quoted="a" * 80).quoted == "a" * 80


def test_quoted_81_cut() -> None:
    assert _finding(quoted="a" * 81).quoted == "a" * 80 + "…"


def test_quoted_idempotent() -> None:
    once = _finding(quoted="b" * 200).quoted
    assert _finding(quoted=once).quoted == once


def test_quoted_empty() -> None:
    assert _finding(quoted="").quoted == ""


def test_quoted_cut_by_code_points() -> None:
    assert _finding(quoted="é" * 81).quoted == "é" * 80 + "…"


def test_ordered() -> None:
    a = _finding(check="structure.reader-summary", line=3, column=1)
    b = _finding(check="structure.format", line=3, column=9)
    c = _finding(check="structure.format", line=3, column=2)
    d = _finding(check="prose.page", line=1, column=5)
    e = _finding(check="structure.format", line=7, column=1)
    assert ordered([e, a, c, d, b]) == (d, c, b, a, e)


def test_ordered_stable_on_ties() -> None:
    first = _finding(reason="First.")
    second = _finding(reason="Second.")
    assert ordered([first, second]) == (first, second)
    assert ordered([second, first]) == (second, first)


def test_context_defaults() -> None:
    context = CheckContext(kind="prose")
    assert context.kind == "prose"
    assert context.scored is False
    assert context.pins == ()
    assert context.other_sources == ()
    assert context.upstream == {}
    assert context.accepted == {}
    assert context.required_registers == ()


def test_context_frozen() -> None:
    context = CheckContext(kind="data")
    with pytest.raises(ValidationError):
        _set(context, "scored", True)


def _context_with_document() -> tuple[CheckContext, dict[str, Any], Any]:
    data = (HANDOFFS / "synthetic-new-format" / "SYNTHETIC-CP-0.md").read_bytes()
    document = parse(data)
    passed: dict[str, Any] = {"CP-0": document}
    return CheckContext(kind="prose", upstream=passed, accepted=dict(passed)), passed, document


@pytest.mark.parametrize("name", ["upstream", "accepted"])
def test_context_mapping_refuses_assignment(name: str) -> None:
    context, _, document = _context_with_document()
    mapping: Any = getattr(context, name)
    with pytest.raises(TypeError):
        mapping["CP-1"] = document
    with pytest.raises(TypeError):
        mapping["CP-0"] = document
    assert list(mapping) == ["CP-0"]


@pytest.mark.parametrize("name", ["upstream", "accepted"])
def test_context_mapping_refuses_deletion(name: str) -> None:
    context, _, _ = _context_with_document()
    mapping: Any = getattr(context, name)
    with pytest.raises(TypeError):
        del mapping["CP-0"]
    assert "CP-0" in mapping


def test_context_holds_its_own_copy() -> None:
    context, passed, document = _context_with_document()
    passed["CP-9"] = document
    del passed["CP-0"]
    assert list(context.upstream) == ["CP-0"]
    assert list(context.accepted) == ["CP-0"]


def test_context_mapping_reads() -> None:
    context, _, document = _context_with_document()
    assert context.upstream["CP-0"] == document
    assert "CP-0" in context.upstream
    assert "CP-1" not in context.upstream
    assert len(context.accepted) == 1
    assert list(context.accepted) == ["CP-0"]
    assert context.upstream.get("CP-0") == document
    assert context.upstream.get("CP-1") is None


def test_context_refuses_unknown_kind_and_extra() -> None:
    with pytest.raises(ValidationError):
        _context(kind="other")
    with pytest.raises(ValidationError):
        _context(kind="data", surplus=1)


def test_context_takes_pin_and_document() -> None:
    data = (HANDOFFS / "synthetic-new-format" / "SYNTHETIC-CP-0.md").read_bytes()
    document = parse(data)
    pin = SourcePin(
        name="report.pdf",
        sha256=hashlib.sha256(b"x").hexdigest(),
        size_bytes=1,
        kind=SourceKind.PDF,
    )
    context = CheckContext(kind="prose", pins=(pin,), upstream={"CP-0": document})
    assert context.pins == (pin,)
    assert context.upstream["CP-0"] == document


@pytest.mark.parametrize("name", ["upstream", "accepted"])
def test_context_default_mapping_read_only(name: str) -> None:
    mapping: Any = getattr(CheckContext(kind="prose"), name)
    with pytest.raises(TypeError):
        mapping["CP-0"] = None
    with pytest.raises(TypeError):
        del mapping["CP-0"]


def test_context_left_out_mapping_read_only_when_other_given() -> None:
    _, passed, _ = _context_with_document()
    context = CheckContext(kind="prose", upstream=passed)
    left_out: Any = context.accepted
    with pytest.raises(TypeError):
        left_out["CP-0"] = None
    with pytest.raises(TypeError):
        del left_out["CP-0"]
    given: Any = context.upstream
    with pytest.raises(TypeError):
        given["CP-1"] = None
    assert list(context.accepted) == []


def test_context_defaults_not_shared_mutable() -> None:
    first: Any = CheckContext(kind="prose").upstream
    second: Any = CheckContext(kind="prose").upstream
    for mapping in (first, second):
        with pytest.raises(TypeError):
            mapping["CP-0"] = None
    assert first == {}
    assert second == {}


def test_quoted_one_line_newline() -> None:
    assert _finding(quoted="a\nb").quoted == "a b"


def test_quoted_one_line_controls() -> None:
    assert _finding(quoted="a\tb\x0bc\x0cd\x1be").quoted == "a b c d e"


def test_quoted_one_line_next_line_and_format() -> None:
    assert _finding(quoted="a b c\u0085d\u202ee").quoted == "a b c d e"


def test_quoted_one_line_separators() -> None:
    assert _finding(quoted="a\u2028b\u2029c").quoted == "a b c"


def test_quoted_newlines_then_cut() -> None:
    assert _finding(quoted="\n" * 100).quoted == " " * 80 + "…"


def test_quoted_keeps_quote_and_spaces() -> None:
    assert _finding(quoted='say "x"  y').quoted == 'say "x"  y'


def test_quoted_one_line_idempotent() -> None:
    once = _finding(quoted="a\nb\u202ec" * 40).quoted
    assert _finding(quoted=once).quoted == once
