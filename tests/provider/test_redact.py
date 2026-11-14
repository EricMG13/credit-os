"""Redaction tests, compared with the controller's answer key (provider_redaction_key)."""

import ast
from pathlib import Path

import provider_redaction_key as key
import pytest
from hypothesis import given
from hypothesis import strategies as st

from credit_os.provider import redact
from credit_os.provider.redact import Redactor, home_paths


@pytest.mark.parametrize(("values", "text", "expected"), key.REDACT_TEXT)
def test_text_rows(values: tuple[str, ...], text: str, expected: str) -> None:
    assert Redactor(values).text(text) == expected


@pytest.mark.parametrize(("values", "text", "expected"), key.REDACT_TEXT)
def test_bytes_rows(values: tuple[str, ...], text: str, expected: str) -> None:
    assert Redactor(values).bytes_(text.encode()) == expected.encode()


@pytest.mark.parametrize(
    ("values", "text", "expected"), [row for row in key.REDACT_TEXT if any(row[0])]
)
def test_no_exact_value_survives_a_change(
    values: tuple[str, ...], text: str, expected: str
) -> None:
    out = Redactor(values).text(text)
    assert all(v not in out for v in values if v)


@pytest.mark.parametrize(("environ", "text", "expected"), key.REDACT_ENVIRON)
def test_environ_rows(environ: dict[str, str], text: str, expected: str) -> None:
    assert Redactor.from_environ(environ).text(text) == expected


@pytest.mark.parametrize(("text", "expected"), key.HOME_PATHS)
def test_home_paths_rows(text: str, expected: str) -> None:
    assert home_paths(text) == expected


def test_empty_redactors_leave_text_unchanged() -> None:
    assert Redactor().text("x") == "x"
    assert Redactor.from_environ({}).text("x") == "x"


def test_module_does_not_import_os() -> None:
    tree = ast.parse(Path(redact.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name.split(".")[0] != "os" for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] != "os"


_VALUES = st.text(min_size=4).filter(lambda v: "[" not in v and "]" not in v and v not in key.MARK)


@given(t=st.text(), v=_VALUES)
def test_exact_value_never_survives(t: str, v: str) -> None:
    assert v not in Redactor([v]).text(t + v + t)
    assert v.encode() not in Redactor([v]).bytes_((t + v + t).encode())
