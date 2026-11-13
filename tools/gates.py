"""Run every gate over the whole repository. Exit 0 pass, 1 a gate failed, 2 a tool is missing."""

import subprocess
import sys
import tokenize
from pathlib import Path

Gate = tuple[str, tuple[str, ...]]

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "tools" / "suppressions-baseline.txt"
AUDIT_REQUIREMENTS = ROOT / ".venv" / "audit-requirements.txt"
SUPPRESSION_MARKERS = ("noqa", "type: ignore", "nosec", "pragma: no cover")
SUPPRESSION_ROOTS = ("src", "tools", "tests")

GATES: tuple[Gate, ...] = (
    ("ruff check", ("uv", "run", "ruff", "check", ".")),
    ("ruff format", ("uv", "run", "ruff", "format", "--check", ".")),
    ("mypy", ("uv", "run", "mypy", "src", "tools", "tests")),
    ("pytest", ("uv", "run", "pytest", "--cov=credit_os", "--cov-fail-under=80")),
    ("uv lock", ("uv", "lock", "--check")),
    ("complexipy", ("uv", "run", "complexipy", "src", "--max-complexity-allowed", "15")),
    ("bandit", ("uv", "run", "bandit", "-r", "src", "-q")),
    (
        "pip-audit export",
        ("uv", "export", "--locked", "--no-emit-project", "-q", "-o", str(AUDIT_REQUIREMENTS)),
    ),
    ("pip-audit", ("uv", "run", "pip-audit", "--strict", "-r", str(AUDIT_REQUIREMENTS))),
)


def count_suppressions(root: Path) -> int:
    total = 0
    for path in root.rglob("*.py"):
        with path.open("rb") as handle:
            for token in tokenize.tokenize(handle.readline):
                if token.type == tokenize.COMMENT:
                    total += sum(1 for marker in SUPPRESSION_MARKERS if marker in token.string)
    return total


def _suppression_gate() -> int:
    baseline = int(BASELINE.read_text(encoding="utf-8").strip())
    found = sum(count_suppressions(ROOT / name) for name in SUPPRESSION_ROOTS)
    print(f"suppressions: {found} (baseline {baseline})")
    return 0 if found <= baseline else 1


def run(gates: tuple[Gate, ...]) -> int:
    failed = False
    for name, argv in gates:
        print(f"== {name}", flush=True)
        try:
            code = subprocess.run(argv, check=False, cwd=ROOT).returncode
        except FileNotFoundError:
            print(f"gate tool not found: {argv[0]} (gate: {name})")
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
