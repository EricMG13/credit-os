import ast
import hashlib
import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

import orchestrator_write_key as key
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from credit_os.checks.findings import CHECKS, Finding
from credit_os.checks.lost import LostValue
from credit_os.handoff.document import parse
from credit_os.orchestrator.write import (
    MAX_WRITES,
    WRITE_TOOLS,
    ModuleWriter,
    dropped_text,
    refusal_text,
)
from credit_os.provider.types import ToolCall

LIMITED_BYTES = key.LIMITED.encode("utf-8")
AS_OF = date(2025, 3, 31)
ISSUER_NAMES = ("Northbridge Synthetic Group", "nbg")


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
        as_of=AS_OF,
        issuer_names=ISSUER_NAMES,
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
            as_of=AS_OF,
            issuer_names=ISSUER_NAMES,
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
        as_of=AS_OF,
        issuer_names=ISSUER_NAMES,
    )
    context = writer.context
    assert context.as_of == AS_OF
    assert context.issuer_names == ISSUER_NAMES
    assert context.hashes_required is True
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


@pytest.mark.parametrize("name", list(key.DROPPED_TEXTS), ids=list(key.DROPPED_TEXTS))
def test_d5_dropped_text_is_the_key_text(name: str) -> None:
    rows, text = key.DROPPED_TEXTS[name]
    assert dropped_text([LostValue(line=n, value=v, label=lb) for n, v, lb in rows]) == text


_LOST = st.builds(LostValue, line=st.integers(1, 10**6), value=_TEXT, label=_TEXT)


@settings(max_examples=100, deadline=None)
@given(st.lists(_LOST, max_size=60))
def test_d5_dropped_lines_are_bounded_ascii_json(lost: list[LostValue]) -> None:
    text = dropped_text(lost)
    if not lost:
        assert text == ""
        return
    lines = text.split("\n")[1:]
    assert len(lines) <= 21
    for line, one in zip(lines, lost[:20], strict=False):
        assert line.isascii()
        assert json.loads(line) == {"value": one.value, "line": one.line, "label": one.label}
    if len(lost) > 20:
        assert lines[20] == key.MORE.format(n=len(lost) - 20)
    else:
        assert len(lines) == len(lost)


def _run(writer: ModuleWriter, steps: Any) -> list[str]:
    results = []
    for n, (tool, arguments, bad) in enumerate(steps, 1):
        call = ToolCall(call_id=f"c{n}", name=tool, arguments=arguments, bad_arguments=bad)
        results.append(writer.call(call))
    return results


def _rows(writer: ModuleWriter) -> list[Any]:
    return [
        (
            a.number,
            a.accepted,
            None if a.dropped is None else tuple((v.line, v.value, v.label) for v in a.dropped),
            a.uncompared,
            a.dropped_error,
            tuple((e.kind, dict(e.detail)) for e in a.events),
        )
        for a in writer.attempts
    ]


@pytest.mark.parametrize("name", list(key.DROPS), ids=list(key.DROPS))
def test_c1_what_a_repair_dropped(name: str) -> None:
    steps, attempts = key.DROPS[name]
    writer = _writer()
    assert _run(writer, [call for call, _ in steps]) == [text for _, text in steps]
    assert _rows(writer) == list(attempts)


def _raiser(error: BaseException) -> Any:
    def raise_it(*args: Any, **kwargs: Any) -> Any:
        raise error

    return raise_it


def _failed(error: str) -> tuple[str, dict[str, str]]:
    return ("dropped_values_check_failed", {"error": error})


def _fail_scenario(
    monkeypatch: pytest.MonkeyPatch, error: Exception, texts: tuple[str, ...]
) -> tuple[ModuleWriter, list[str]]:
    monkeypatch.setattr("credit_os.orchestrator.write.lost_values", _raiser(error))
    writer = _writer()
    calls = [key._w(text) for text in texts]
    return writer, _run(writer, calls)


def test_d22_fault_on_an_accepted_repair_keeps_acceptance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writer, results = _fail_scenario(monkeypatch, IndexError("zebra"), (key.VALUED, key.LIMITED))
    assert results == [key.refused(2, key.CODED_RECORD), key.ACCEPTED]
    assert _rows(writer)[1] == (2, True, None, (), "IndexError", (_failed("IndexError"),))
    assert writer.document is not None
    assert writer.document.sha256 == hashlib.sha256(LIMITED_BYTES).hexdigest()
    assert writer.closed


def test_d22_fault_on_a_refused_repair_keeps_the_checkers_refusal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writer, results = _fail_scenario(monkeypatch, ValueError("zebra"), (key.VALUED, key.CODED))
    assert results[1] == key.refused(1, key.CODED_RECORD)
    assert "DROPPED" not in results[1]
    assert _rows(writer)[1] == (2, False, None, (), "ValueError", (_failed("ValueError"),))


@pytest.mark.parametrize("error", [IndexError, ValueError], ids=["index", "value"])
def test_d22_fault_is_logged_and_its_message_goes_nowhere(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, error: type[Exception]
) -> None:
    with caplog.at_level(logging.WARNING):
        writer, results = _fail_scenario(monkeypatch, error("zebra"), (key.VALUED, key.LIMITED))
    records = [r for r in caplog.records if r.name == "credit_os.orchestrator.write"]
    assert len(records) == 1
    assert records[0].levelno == logging.WARNING
    assert records[0].exc_info is not None
    assert isinstance(records[0].exc_info[1], error)
    assert not any("zebra" in text for text in results)
    assert "zebra" not in repr(writer.attempts)
    assert writer.attempts[1].dropped_error == error.__name__


def test_d22_an_interrupt_is_not_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("credit_os.orchestrator.write.lost_values", _raiser(KeyboardInterrupt()))
    writer = _writer()
    writer.call(ToolCall("c1", "write_handoff", {"markdown": key.VALUED}))
    with pytest.raises(KeyboardInterrupt):
        writer.call(ToolCall("c2", "write_handoff", {"markdown": key.LIMITED}))
    assert [(a.number, a.accepted) for a in writer.attempts] == [(1, False), (2, True)]
    last = writer.attempts[1]
    assert last.dropped is None
    assert last.dropped_error is None
    assert last.events == ()
    assert writer.document is not None
    assert writer.closed


def test_d22_a_later_fault_leaves_earlier_attempts_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    steps, attempts = key.DROPS["dropped_by_an_earlier_refused_draft_is_reported_at_acceptance"]
    writer = _writer()
    for n, (call, text) in enumerate(steps, 1):
        if n == 3:
            monkeypatch.setattr(
                "credit_os.orchestrator.write.lost_values", _raiser(IndexError("zebra"))
            )
        tool, arguments, bad = call
        assert writer.call(ToolCall(f"c{n}", tool, arguments, bad)) == text
    assert _rows(writer)[:2] == list(attempts[:2])
    assert _rows(writer)[2] == (3, True, None, (), "IndexError", (_failed("IndexError"),))


ORCHESTRATOR = Path(__file__).resolve().parents[2] / "src" / "credit_os" / "orchestrator"


def _names(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)} | {
        n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)
    }


def test_d22_the_one_catch_all_is_the_comparison() -> None:
    handlers: list[tuple[str, ast.ExceptHandler, ast.Try]] = []
    for path in sorted(ORCHESTRATOR.glob("*.py")):
        tree = ast.parse(path.read_text("utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                handlers.extend((path.name, h, node) for h in node.handlers)
    wide = [
        (name, h, t)
        for name, h, t in handlers
        if h.type is None or (isinstance(h.type, ast.Name) and h.type.id.endswith("Exception"))
    ]
    assert [(name, h.type.id if isinstance(h.type, ast.Name) else None) for name, h, _ in wide] == [
        ("write.py", "Exception")
    ]
    _, handler, attempt = wide[0]
    assert handler.name is not None
    assert len(attempt.body) == 1
    body = attempt.body[0]
    assert isinstance(body, ast.Assign)
    assert isinstance(body.value, ast.Call)
    assert not attempt.orelse
    assert not attempt.finalbody
    assert len(handler.body) == 2
    log, store = handler.body
    assert isinstance(log, ast.Expr)
    assert isinstance(log.value, ast.Call)
    assert isinstance(log.value.func, ast.Attribute)
    assert log.value.func.attr == "warning"
    assert [(k.arg, getattr(k.value, "value", None)) for k in log.value.keywords] == [
        ("exc_info", True)
    ]
    assert isinstance(store, ast.Assign)
    assert isinstance(store.value, ast.Attribute)
    assert store.value.attr == "__name__"
    assert isinstance(store.value.value, ast.Call)
    func = store.value.value.func
    assert isinstance(func, ast.Name)
    assert func.id == "type"
    arguments = store.value.value.args
    assert len(arguments) == 1
    assert isinstance(arguments[0], ast.Name)
    assert arguments[0].id == handler.name
    for part in (*attempt.body, *handler.body):
        assert not _names(part) & {"record_event", "Store"}


def test_d22_write_imports_no_store() -> None:
    tree = ast.parse((ORCHESTRATOR / "write.py").read_text("utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert "credit_os.store" not in (node.module or "")
        if isinstance(node, ast.Import):
            assert all("credit_os.store" not in alias.name for alias in node.names)
