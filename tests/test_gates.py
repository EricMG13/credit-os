import sys
from pathlib import Path

import pytest

from tools.gates import GATES, count_suppressions, run

OK = (sys.executable, "-c", "raise SystemExit(0)")
BAD = (sys.executable, "-c", "raise SystemExit(1)")


def test_all_pass() -> None:
    assert run((("a", OK), ("b", OK))) == 0


def test_failure_still_runs_every_gate(capsys: pytest.CaptureFixture[str]) -> None:
    assert run((("first", OK), ("second", BAD), ("third", OK))) == 1
    out = capsys.readouterr().out
    assert "first" in out and "second" in out and "third" in out


def test_missing_tool_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    assert run((("ghost", ("no-such-program-xyz", "--version")),)) == 2
    assert "no-such-program-xyz" in capsys.readouterr().out


def test_count_suppressions(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1  # noqa\ny = 2  # noqa: E501\n")
    (tmp_path / "b.py").write_text("z = 3  # type: ignore\n")
    assert count_suppressions(tmp_path) == 3


def test_every_gate_is_a_tuple_of_strings() -> None:
    for name, argv in GATES:
        assert isinstance(name, str)
        assert isinstance(argv, tuple), name
        assert argv and all(isinstance(part, str) for part in argv), name


def test_every_uv_run_gate_is_locked() -> None:
    uv_run = [(name, argv) for name, argv in GATES if argv[:2] == ("uv", "run")]
    assert uv_run
    for name, argv in uv_run:
        assert argv[2] == "--locked", name


def test_lock_check_gate_present() -> None:
    assert ("uv", "lock", "--check") in [argv for _, argv in GATES]


def test_entry_points_launch_gates_locked() -> None:
    for name in (".pre-commit-config.yaml", ".github/workflows/python.yml"):
        text = Path(name).read_text(encoding="utf-8")
        assert "uv run --locked python tools/gates.py" in text, name
