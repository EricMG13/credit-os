import hashlib
import json
from typing import Any

import orchestrator_write_key as key
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.checks.findings import CHECKS, Finding
from credit_os.handoff.document import parse
from credit_os.orchestrator.write import MAX_WRITES, WRITE_TOOLS, ModuleWriter, refusal_text
from credit_os.provider.types import ToolCall

LIMITED_BYTES = key.LIMITED.encode("utf-8")


def _writer(accepted: dict[str, Any] | None = None) -> ModuleWriter:
    return ModuleWriter(
        "CP-2D",
        kind="prose",
        scored=False,
        pins=(),
        other_sources=(),
        upstream={},
        accepted=accepted or {},
        required_registers=(),
    )


@pytest.mark.parametrize("name", list(key.REASONS), ids=list(key.REASONS))
def test_d5_refusal_text_is_the_key_text(name: str) -> None:
    findings, left, text = key.REASONS[name]
    assert refusal_text(findings, left) == text


@pytest.mark.parametrize("name", list(key.SCENARIOS), ids=list(key.SCENARIOS))
def test_d4_scenario_texts_attempts_and_context(name: str) -> None:
    earlier, steps, attempts = key.SCENARIOS[name]
    accepted = {"CP-2": parse(LIMITED_BYTES)} if "LIMITED" in earlier else {}
    writer = _writer(accepted)
    for n, ((tool, arguments, bad), text) in enumerate(steps, 1):
        call = ToolCall(call_id=f"c{n}", name=tool, arguments=arguments, bad_arguments=bad)
        assert writer.call(call) == text
    assert [(a.number, a.accepted) for a in writer.attempts] == list(attempts)
    assert set(writer.context.accepted) == set(accepted)
    assert "CP-2D" not in writer.context.accepted
    if attempts and attempts[-1][1]:
        assert writer.closed
        assert writer.document is not None
        assert writer.document.sha256 == hashlib.sha256(LIMITED_BYTES).hexdigest()
        assert writer.attempts[-1].draft == LIMITED_BYTES
    elif len(attempts) == MAX_WRITES:
        assert writer.closed
        assert writer.document is None
    else:
        assert not writer.closed


def test_d4_attempt_records_findings_and_unparsed() -> None:
    writer = _writer()
    writer.call(ToolCall("c1", "write_handoff", {"markdown": "no headings here"}))
    writer.call(ToolCall("c2", "write_handoff", {"markdown": key.CODED}))
    first, second = writer.attempts
    assert first.findings == ()
    assert first.unparsed == "line 1: level-2 heading `Request` is missing"
    assert second.unparsed is None
    assert [f.check for f in second.findings] == ["prose.module-code"]
    assert second.draft == key.CODED.encode("utf-8")


@pytest.mark.parametrize("field", ["upstream", "accepted"], ids=["upstream", "accepted"])
def test_d18_own_module_is_never_in_the_context(field: str) -> None:
    document = parse(LIMITED_BYTES)
    arguments: dict[str, Any] = {"upstream": {}, "accepted": {}, field: {"CP-2D": document}}
    with pytest.raises(ValueError, match="CP-2D"):
        ModuleWriter(
            "CP-2D",
            kind="prose",
            scored=False,
            pins=(),
            other_sources=(),
            required_registers=(),
            **arguments,
        )


def test_d18_context_carries_each_argument() -> None:
    document = parse(LIMITED_BYTES)
    writer = ModuleWriter(
        "CP-2D",
        kind="data",
        scored=True,
        pins=(),
        other_sources=("context",),
        upstream={"CP-1": document},
        accepted={"CP-2": document},
        required_registers=("SYNTHETIC-REG-1",),
    )
    context = writer.context
    assert context.kind == "data"
    assert context.scored is True
    assert context.other_sources == ("context",)
    assert context.required_registers == ("SYNTHETIC-REG-1",)
    assert set(context.upstream) == {"CP-1"}
    assert set(context.accepted) == {"CP-2"}
    writer.call(ToolCall("c1", "write_handoff", {"markdown": key.CODED}))
    assert set(writer.context.accepted) == {"CP-2"}


def test_d4_write_tools_match_the_key() -> None:
    assert [tool.name for tool in WRITE_TOOLS] == ["write_handoff", "edit_handoff"]
    for tool in WRITE_TOOLS:
        assert dict(tool.parameters) == key.SPECS[tool.name]
        assert "\n" not in tool.description
        assert 0 < len(tool.description) <= 600


def test_d10_error_texts_are_one_short_line() -> None:
    texts = [
        value.format(i=100)
        for name, value in vars(key).items()
        if name.startswith("E_") and isinstance(value, str)
    ]
    assert texts
    for text in texts:
        assert text.startswith("ERROR: ")
        assert "\n" not in text
        assert len(text) <= 300


_TEXT = st.text(max_size=200)


@settings(max_examples=100, deadline=None)
@given(
    st.lists(
        st.tuples(st.sampled_from(CHECKS), st.integers(1, 10**6), _TEXT, _TEXT.filter(bool)),
        max_size=60,
    )
)
def test_d5_refusal_lines_are_bounded_ascii_json(rows: list[tuple[str, int, str, str]]) -> None:
    findings = [
        Finding(check=c, severity="refusal", line=n, column=n, quoted=q, reason=r)
        for c, n, q, r in rows
    ]
    lines = refusal_text(findings, 2).split("\n")[1:]
    assert len(lines) <= 21
    shown = findings[:20]
    for line, finding in zip(lines, shown, strict=False):
        assert line.isascii()
        assert json.loads(line) == {
            "check": finding.check,
            "line": finding.line,
            "column": finding.column,
            "quoted": finding.quoted,
            "reason": finding.reason,
        }
    if len(findings) > 20:
        assert lines[20] == key.MORE.format(n=len(findings) - 20)
    else:
        assert len(lines) == len(findings)
