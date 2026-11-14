"""No float in `credit_os.checks`: no float or complex literal, no `float` name, no true division."""

import ast
from pathlib import Path

import pytest

CHECKS = Path(__file__).resolve().parents[2] / "src" / "credit_os" / "checks"


def float_uses(source: str) -> list[tuple[int, str]]:
    """The (line, what) of each float or complex constant, `float` name and true division."""
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Constant) and isinstance(node.value, float | complex):
            found.append((node.lineno, f"{type(node.value).__name__} constant"))
        elif isinstance(node, ast.Name) and node.id == "float":
            found.append((node.lineno, "name float"))
        elif isinstance(node, ast.BinOp | ast.AugAssign) and isinstance(node.op, ast.Div):
            found.append((node.lineno, "true division"))
    return found


@pytest.mark.parametrize(
    "source",
    ["x = 1.5", "x = 1e3", "x = 2j", 'float("1")', "a / b", "a /= b"],
)
def test_detector_reports(source: str) -> None:
    assert len(float_uses(source)) == 1


@pytest.mark.parametrize(
    "source",
    [
        "a // b",
        'Decimal("1.5")',
        'x = "1.5"',
        "# 1.5 and float\nx = 1",
        '"""1.5 and float"""\nx = 1',
    ],
)
def test_detector_ignores(source: str) -> None:
    assert float_uses(source) == []


def test_detector_names_the_line() -> None:
    assert float_uses("a = 1\nb = 2\nc = 3 / 4") == [(3, "true division")]


def test_no_float_in_the_package() -> None:
    files = sorted(CHECKS.rglob("*.py"))
    assert len(files) >= 5
    problems = [
        f"{path.name}:{line}: {what}"
        for path in files
        for line, what in float_uses(path.read_text("utf-8"))
    ]
    assert problems == []
