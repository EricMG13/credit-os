"""Run every gate over the whole repository. Exit 0 pass, 1 a gate failed, 2 a tool is missing."""

import re
import shutil
import subprocess
import sys
import tokenize
from pathlib import Path

Gate = tuple[str, tuple[str, ...]]

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "tools" / "suppressions-baseline.txt"
AUDIT_REQUIREMENTS = ROOT / ".venv" / "audit-requirements.txt"
VENV_BIN = ROOT / ".venv" / ("Scripts" if sys.platform == "win32" else "bin")
UV_RUN_PREFIX = ("uv", "run", "--locked")
# One pattern per suppression the pinned tools honour, matched in comments only and ignoring case.
SUPPRESSION_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bnoqa\b",
        r"\btype:\s*ignore",
        r"\bnosec\b",
        r"\bpragma:?\s*no\s*cover",
        r"\bmypy:\s*ignore-errors",
    )
)
SUPPRESSION_ROOTS = ("src", "tools", "tests")

GATES: tuple[Gate, ...] = (
    ("ruff check", ("uv", "run", "--locked", "ruff", "check", ".")),
    ("ruff format", ("uv", "run", "--locked", "ruff", "format", "--check", ".")),
    ("mypy", ("uv", "run", "--locked", "mypy", "src", "tools", "tests")),
    (
        "pytest",
        (
            "uv",
            "run",
            "--locked",
            "pytest",
            "-m",
            "not live and not browser",
            "--cov=credit_os",
            "--cov-fail-under=80",
        ),
    ),
    ("uv lock", ("uv", "lock", "--check")),
    (
        "complexipy",
        ("uv", "run", "--locked", "complexipy", "src", "--max-complexity-allowed", "15"),
    ),
    ("bandit", ("uv", "run", "--locked", "bandit", "-r", "src", "-q")),
    (
        "pip-audit export",
        ("uv", "export", "--locked", "--no-emit-project", "-q", "-o", str(AUDIT_REQUIREMENTS)),
    ),
    (
        "pip-audit",
        ("uv", "run", "--locked", "pip-audit", "--strict", "-r", str(AUDIT_REQUIREMENTS)),
    ),
)


def count_suppressions(root: Path) -> int:
    total = 0
    for pattern in ("*.py", "*.pyi"):
        for path in root.rglob(pattern):
            with path.open("rb") as handle:
                for token in tokenize.tokenize(handle.readline):
                    if token.type == tokenize.COMMENT:
                        total += sum(
                            1 for rule in SUPPRESSION_PATTERNS if rule.search(token.string)
                        )
    return total


def _suppression_gate() -> int:
    baseline = int(BASELINE.read_text(encoding="utf-8").strip())
    found = sum(count_suppressions(ROOT / name) for name in SUPPRESSION_ROOTS)
    print(f"suppressions: {found} (baseline {baseline})")
    return 0 if found <= baseline else 1


def _missing_behind_uv(argv: tuple[str, ...]) -> str | None:
    """The tool a `uv run` gate names when it is not installed in the project environment."""
    if argv[: len(UV_RUN_PREFIX)] != UV_RUN_PREFIX or len(argv) <= len(UV_RUN_PREFIX):
        return None
    tool = argv[len(UV_RUN_PREFIX)]
    return None if shutil.which(tool, path=str(VENV_BIN)) else tool


def run(gates: tuple[Gate, ...]) -> int:
    if not gates:
        raise ValueError("no gates to run")
    failed = False
    for name, argv in gates:
        print(f"== {name}", flush=True)
        missing = _missing_behind_uv(argv)
        if missing:
            print(f"gate tool not found: {missing} (gate: {name})")
            return 2
        try:
            code = subprocess.run(argv, check=False, cwd=ROOT).returncode
        except OSError as error:
            print(f"gate tool could not be started: {argv[0]} (gate: {name}): {error}")
            return 2
        print(f"-- {name}: {'ok' if code == 0 else f'FAILED ({code})'}", flush=True)
        failed = failed or code != 0
    return 1 if failed else 0


def main() -> int:
    code = run(GATES)
    if code == 2:
        return 2
    print("== suppressions")
    supp = _suppression_gate()
    print(f"-- suppressions: {'ok' if supp == 0 else 'FAILED'}")
    return 1 if code or supp else 0


if __name__ == "__main__":
    sys.exit(main())
