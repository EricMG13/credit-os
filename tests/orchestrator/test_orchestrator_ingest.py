"""The shown and stored form of a source error (C1, D12), against the controller's answer key
(`orchestrator_ingest_key.py`)."""

import ast
from pathlib import Path
from typing import Any, cast

import orchestrator_ingest_key as key
import pytest

from credit_os import sources
from credit_os.orchestrator import ingest
from credit_os.orchestrator.ingest import SourceForms
from credit_os.sources import SourceKind, SourcePin


class LaterUnreadable(sources.SourceUnreadable):
    """A subclass the class table has never heard of."""


def _raise_class(name: str) -> type[sources.SourceError]:
    found = LaterUnreadable if name == "LaterUnreadable" else getattr(sources, name)
    assert issubclass(found, sources.SourceError)
    return found


def _pin(row: key.Pin | None) -> SourcePin | None:
    if row is None:
        return None
    name, size, kind = row
    return SourcePin(name=name, sha256=key.SHA, size_bytes=size, kind=SourceKind(kind))


@pytest.mark.parametrize("name", list(key.ERRORS), ids=list(key.ERRORS))
def test_c1_d12_shown_and_stored_form(name: str) -> None:
    folder, raised, message, notes, pin, shown, detail = key.ERRORS[name]
    error = _raise_class(raised)(message)
    for note in notes:
        error.add_note(note)
    problem = SourceForms(folder).problem(error, _pin(pin))
    assert problem.shown == shown
    assert problem.detail() == detail
    for text in key.NEVER:
        assert text not in problem.shown
        assert all(text not in str(value) for value in problem.detail().values())


def test_d12_a_non_source_error_is_a_type_error() -> None:
    with pytest.raises(TypeError):
        SourceForms(key.FOLDER).problem(cast(Any, ValueError("x")), None)


def test_d12_ingest_imports_only_sources_and_redact() -> None:
    tree = ast.parse(Path(ingest.__file__).read_text(encoding="utf-8"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules.append(node.module or "")
    own = [m for m in modules if m.split(".")[0] == "credit_os"]
    assert "credit_os.store" not in own
    for module in own:
        assert module.startswith(("credit_os.sources", "credit_os.provider.redact")), module
