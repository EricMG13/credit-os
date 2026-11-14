import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools import gates
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


def _marker(*parts: str) -> str:
    return "".join(parts)


NOQA = _marker("no", "qa")
TYPE_IGNORE = _marker("type", ": ", "ignore")
PRAGMA = _marker("pragma", ": ", "no cover")


def test_missing_tool_behind_uv_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    ghost = ("uv", "run", "--locked", "no-such-tool-xyz", "--version")
    assert run((("ghost via uv", ghost),)) == 2
    assert "no-such-tool-xyz" in capsys.readouterr().out


def test_unstartable_tool_exits_two(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    not_executable = tmp_path / "plain.txt"
    not_executable.write_text("x")
    assert run((("plain", (str(not_executable),)),)) == 2
    assert "plain.txt" in capsys.readouterr().out


def test_empty_gate_list_is_refused() -> None:
    with pytest.raises(ValueError, match="no gates"):
        run(())


@pytest.mark.parametrize("code", [1, 2, 3, 5, 255])
def test_any_non_zero_exit_is_a_failure(code: int, capsys: pytest.CaptureFixture[str]) -> None:
    argv = (sys.executable, "-c", f"raise SystemExit({code})")
    assert run((("g", argv), ("after", OK))) == 1
    out = capsys.readouterr().out
    assert f"FAILED ({code})" in out
    assert "-- after: ok" in out


@pytest.mark.skipif(sys.platform == "win32", reason="signal exit codes are POSIX")
def test_signal_kill_is_a_failure() -> None:
    kill = "import os, signal; os.kill(os.getpid(), signal.SIGKILL)"
    assert run((("killed", (sys.executable, "-c", kill)),)) == 1


def test_real_gate_set_is_pinned() -> None:
    assert [name for name, _ in GATES] == [
        "ruff check",
        "ruff format",
        "mypy",
        "pytest",
        "uv lock",
        "complexipy",
        "bandit",
        "pip-audit export",
        "pip-audit",
        "duplication",
    ]


@pytest.mark.parametrize(
    "text",
    [
        f"x = 1  # {NOQA}\n",
        f"x = 1  # {NOQA.upper()}\n",
        "x = 1  # No" + "QA: F401\n",
        f"x = 1  # {NOQA}:E501\n",
        f"x = 1  # ruff: {NOQA}\n",
        f"x = 1  # {TYPE_IGNORE}\n",
        "x = 1  # type:" + "ignore[assignment]\n",
        "x = 1  # TYPE: " + "IGNORE\n",
        "x = 1  # no" + "sec\n",
        "x = 1  # NO" + "SEC: B101\n",
        f"x = 1  # {PRAGMA}\n",
        "x = 1  # pragma:" + "no cover\n",
        "x = 1  # PRAGMA: " + "NO COVER\n",
        "x = 1  # pragma " + "no cover\n",
        "# mypy: " + "ignore-errors\n",
        "# MYPY: " + "IGNORE-ERRORS\n",
    ],
)
def test_every_honoured_spelling_is_counted(tmp_path: Path, text: str) -> None:
    (tmp_path / "a.py").write_text(text)
    assert count_suppressions(tmp_path) == 1, text


def test_marker_inside_a_string_is_not_counted(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text(f's = "# {NOQA} {TYPE_IGNORE}"\n')
    assert count_suppressions(tmp_path) == 0


def test_stub_files_are_counted(tmp_path: Path) -> None:
    (tmp_path / "a.pyi").write_text(f"x: int  # {TYPE_IGNORE}\n")
    assert count_suppressions(tmp_path) == 1


def _suppression_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, baseline: str) -> Path:
    for name in ("src", "tools", "tests"):
        (tmp_path / name).mkdir()
    (tmp_path / "baseline.txt").write_text(baseline)
    monkeypatch.setattr(gates, "ROOT", tmp_path)
    monkeypatch.setattr(gates, "BASELINE", tmp_path / "baseline.txt")
    return tmp_path


def test_suppression_gate_over_at_and_under_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _suppression_tree(tmp_path, monkeypatch, "1\n")
    assert gates._suppression_gate() == 0
    (root / "src" / "a.py").write_text(f"x = 1  # {NOQA}\n")
    assert gates._suppression_gate() == 0
    (root / "src" / "b.py").write_text(f"x = 1  # {NOQA}\n")
    assert gates._suppression_gate() == 1


@pytest.mark.parametrize("folder", ["src", "tools", "tests"])
def test_suppression_gate_scans_every_root(
    folder: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _suppression_tree(tmp_path, monkeypatch, "0")
    (root / folder / "a.py").write_text(f"x = 1  # {NOQA}\n")
    assert gates._suppression_gate() == 1


def test_suppression_gate_ignores_markers_in_strings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _suppression_tree(tmp_path, monkeypatch, "0")
    (root / "src" / "a.py").write_text(f's = "# {NOQA}"\n')
    assert gates._suppression_gate() == 0


@pytest.mark.parametrize("baseline", ["", "abc", "1.5"])
def test_unusable_baseline_never_passes(
    baseline: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _suppression_tree(tmp_path, monkeypatch, baseline)
    with pytest.raises(ValueError):
        gates._suppression_gate()


def test_missing_baseline_never_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _suppression_tree(tmp_path, monkeypatch, "0")
    (root / "baseline.txt").unlink()
    with pytest.raises(FileNotFoundError):
        gates._suppression_gate()


def test_main_all_clean_exits_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _suppression_tree(tmp_path, monkeypatch, "0")
    monkeypatch.setattr(gates, "GATES", (("a", OK),))
    assert gates.main() == 0


def test_main_failed_gate_exits_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _suppression_tree(tmp_path, monkeypatch, "0")
    monkeypatch.setattr(gates, "GATES", (("a", BAD),))
    assert gates.main() == 1


def test_main_over_baseline_exits_one_when_gates_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _suppression_tree(tmp_path, monkeypatch, "0")
    (root / "tools" / "a.py").write_text(f"x = 1  # {NOQA}\n")
    monkeypatch.setattr(gates, "GATES", (("a", OK),))
    assert gates.main() == 1


def test_main_missing_tool_exits_two(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _suppression_tree(tmp_path, monkeypatch, "0")
    monkeypatch.setattr(gates, "GATES", (("ghost", ("no-such-program-xyz",)),))
    assert gates.main() == 2


def test_pytest_gate_skips_live_and_browser_tests() -> None:
    argv = dict(GATES)["pytest"]
    assert argv[argv.index("-m") + 1] == "not live and not browser"


JSCPD = gates.ROOT / "web" / "node_modules" / "jscpd" / "run-jscpd.js"


def test_duplication_gate_arguments_are_pinned() -> None:
    assert dict(GATES)["duplication"] == (
        "node",
        str((gates.ROOT / "web" / "node_modules" / "jscpd" / "run-jscpd.js").resolve()),
        "--threshold",
        "3",
        str((gates.ROOT / "src").resolve()),
    )


def test_missing_jscpd_exits_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    absent = tmp_path / "run-jscpd.js"
    gate = ("duplication", ("node", str(absent), "--threshold", "3", str(tmp_path)))
    monkeypatch.setattr(gates, "JSCPD", absent)
    assert run((gate,)) == 2
    out = capsys.readouterr().out
    assert "jscpd" in out and "npm ci" in out and "web/" in out


def test_missing_node_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    gate = ("duplication", ("node-no-such-xyz", str(JSCPD), "--threshold", "3"))
    assert run((gate,)) == 2
    assert "node-no-such-xyz" in capsys.readouterr().out


def _jscpd_exit(folder: Path) -> int:
    argv = (*dict(GATES)["duplication"][:-1], str(folder))
    assert shutil.which("node"), "node is required for the duplication canary"
    assert JSCPD.is_file(), "jscpd is required: run npm ci in web/"
    return subprocess.run(argv, check=False, cwd=folder, capture_output=True).returncode


def test_duplication_canary_flags_copied_code_and_passes_unlike_code(tmp_path: Path) -> None:
    body = "".join(f"value_{n} = compute({n}) + offset_{n} * {n + 7}\n" for n in range(60))
    twins = tmp_path / "twins"
    twins.mkdir()
    (twins / "one.py").write_text(body)
    (twins / "two.py").write_text(body)
    unlike = tmp_path / "unlike"
    unlike.mkdir()
    (unlike / "one.py").write_text(body)
    (unlike / "two.py").write_text(
        "".join(f"def f{n}(x):\n    return x - {n * 13}\n" for n in range(40))
    )
    assert _jscpd_exit(twins) != 0
    assert _jscpd_exit(unlike) == 0
