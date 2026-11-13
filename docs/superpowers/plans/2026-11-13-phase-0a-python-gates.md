# Phase 0A: Python skeleton and gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** an installable, empty `credit_os` package whose gates run with one command and pass on Windows and Linux in CI.

**Architecture:** one package under `src/credit_os` with eight empty layer sub-packages. A stdlib script, `tools/gates.py`, runs every gate and is the only thing CI calls. A test enforces the layer order from day one.

**Tech Stack:** Python 3.12, uv, pytest, ruff, mypy, GitHub Actions.

**Spec:** `CLAUDE.md` and `docs/superpowers/plans/2026-11-13-rebuild-roadmap.md`.

## Global Constraints

- `requires-python = ">=3.12,<3.13"`; `[tool.uv] required-version = ">=0.12.5,<0.13"`.
- Runtime dependency: `pydantic==2.13.4` only. `pypdf` and `github-copilot-sdk` are added by the phases that first import them.
- Dev dependencies, exact: `pytest==9.1.1`, `ruff==0.16.8`, `mypy==1.18.1`. Gate tools not pinned by the owner (`pytest-cov`, `hypothesis`, `complexipy`, `bandit`, `pip-audit`): pin the newest release that is at least 30 days old and supports Python 3.12, and list each chosen version in the task report.
- Ruff: `target-version = "py312"`, `line-length = 100`. Mypy: `strict = true`.
- Every gate runs over the whole repository, not changed lines.
- This step owns only: `pyproject.toml`, `uv.lock`, `.python-version`, `src/`, `tests/`, `tools/`, `.pre-commit-config.yaml`, `.github/workflows/python.yml`. It does not touch `web/`, `README.md`, `CLAUDE.md`, `.gitignore` or `docs/`.
- No stub or fake value standing in for real behaviour. No catch-all that hides a failure. Every task report ends with a `Not verified:` line.
- Scaffold with the `project-gates` skill; implement with `mx-scaffold`; review once with `mx-feature` (config-only batch).

## Review Focus

1. A gate tool is missing on the machine: `tools/gates.py` must exit 2 and name the tool, not skip it and pass.
2. A path with spaces or a Windows drive letter: every subprocess call takes an argument list, never a shell string.
3. A layer imports a later layer through a relative import (`from ..delivery import x`): the layering test must catch relative and absolute forms.
4. A new sub-package is added that is not in the layer list: the layering test must fail, not ignore it.
5. `uv.lock` resolved on macOS only: CI on Windows must install with `uv sync --locked` and fail if the lock does not cover it.

---

### Task 1: Package skeleton

**Files:**
- Create: `pyproject.toml`, `.python-version` (`3.12`), `uv.lock`
- Create: `src/credit_os/__init__.py`, and `__init__.py` in `sources`, `handoff`, `model`, `provider`, `store`, `checks`, `orchestrator`, `delivery`
- Test: `tests/test_package.py`

**Interfaces:**
- Produces: `credit_os.__version__: str` equal to `"0.1.0"`; `credit_os.LAYERS: tuple[str, ...]` equal to `("sources", "handoff", "model", "provider", "store", "checks", "orchestrator", "delivery")`.

- [ ] **Step 1: Write the failing test**

```python
import importlib

import credit_os


def test_version() -> None:
    assert credit_os.__version__ == "0.1.0"


def test_every_layer_imports() -> None:
    assert credit_os.LAYERS == (
        "sources", "handoff", "model", "provider", "store", "checks", "orchestrator", "delivery",
    )
    for name in credit_os.LAYERS:
        importlib.import_module(f"credit_os.{name}")
```

- [ ] **Step 2:** Run `uv run pytest tests/test_package.py -q`. Expected: FAIL, `ModuleNotFoundError: credit_os`.
- [ ] **Step 3:** Write `pyproject.toml` (hatchling build backend, `packages = ["src/credit_os"]`, the pins above, pytest `testpaths = ["tests"]`, `addopts = "-ra --strict-markers"`, markers `live` and `browser`) and the package files. Run `uv lock`.
- [ ] **Step 4:** Run `uv sync --locked` then `uv run pytest tests/test_package.py -q`. Expected: 2 passed.
- [ ] **Step 5:** Commit: `feat: package skeleton with eight layers`.

### Task 2: Layering test

**Files:**
- Test: `tests/test_layering.py`
- Create (fixture trees built in `tmp_path` by the test; no files committed)

**Interfaces:**
- Consumes: `credit_os.LAYERS`.
- Produces: `tests.test_layering.violations(root: Path, layers: tuple[str, ...]) -> list[str]`, one string per offending import as `"<file>:<line> <layer> imports <later layer>"`, plus one string per sub-package directory not named in `layers`.

- [ ] **Step 1: Write the failing tests.** Each builds a tiny package in `tmp_path` and calls `violations`:
  - `handoff/a.py` containing `from credit_os.delivery import x` gives exactly one violation naming `handoff` and `delivery`.
  - `handoff/a.py` containing `from ..delivery import x` gives exactly one violation.
  - `delivery/a.py` containing `import credit_os.handoff.doc` gives none.
  - a directory `extras/` with `__init__.py` gives one violation naming `extras`.
  - `test_repo_has_no_violations`: `violations(Path("src/credit_os"), credit_os.LAYERS) == []`.
- [ ] **Step 2:** Run `uv run pytest tests/test_layering.py -q`. Expected: FAIL, `violations` not defined.
- [ ] **Step 3:** Implement `violations` with `ast` (walk `Import` and `ImportFrom`, resolve relative levels against the file's package). Stdlib only.
- [ ] **Step 4:** Run the file again. Expected: 5 passed.
- [ ] **Step 5:** Commit: `test: enforce layer order`.

### Task 3: One gate command

**Files:**
- Create: `tools/gates.py`, `tools/suppressions-baseline.txt` (content `0`), `.pre-commit-config.yaml`
- Test: `tests/test_gates.py`

**Interfaces:**
- Produces: `python tools/gates.py` exits 0 when every gate passes, 1 when any gate fails, 2 when a gate tool cannot be started. `tools.gates.GATES: tuple[tuple[str, tuple[str, ...]], ...]` is the ordered list of `(name, argv)`.

The gates, in order, each as an argument list run with `uv run`:
`ruff check .` · `ruff format --check .` · `mypy src tools tests` · `pytest --cov=credit_os --cov-fail-under=80` · `uv lock --check` · `complexipy src --max-complexity-allowed 15` · `bandit -r src -q` · `pip-audit --strict` · suppression count (`noqa`, `type: ignore`, `nosec`, `pragma: no cover` across `src tools tests`) not above the baseline file.

- [ ] **Step 1: Write the failing tests** (they call `tools.gates.run(gates)` with injected argv lists, no real tools):
  - a gate whose argv is `[sys.executable, "-c", "raise SystemExit(0)"]` gives exit 0.
  - one failing gate among passing ones gives exit 1 and every gate still ran (assert on the printed names).
  - an argv naming a program that does not exist gives exit 2 and prints that program's name.
  - `count_suppressions` on a `tmp_path` tree with two `# noqa` and one `# type: ignore` returns 3.
- [ ] **Step 2:** Run `uv run pytest tests/test_gates.py -q`. Expected: FAIL.
- [ ] **Step 3:** Implement `tools/gates.py`: `run(gates) -> int`, `count_suppressions(root: Path) -> int`, `main()`. `subprocess.run(argv, check=False)` with lists only; catch `FileNotFoundError` alone, for exit 2. Add `.pre-commit-config.yaml` with `gitleaks` and a local hook running `uv run python tools/gates.py`.
- [ ] **Step 4:** Run `uv run python tools/gates.py`. Expected: every gate named, exit 0.
- [ ] **Step 5:** Commit: `feat: one gate command`.

### Task 4: CI on Windows and Linux

**Files:**
- Create: `.github/workflows/python.yml`

- [ ] **Step 1:** Write the workflow: on `pull_request` and `push` to `main`; matrix `os: [ubuntu-latest, windows-latest]`; `astral-sh/setup-uv` pinned to uv `0.12.5`; Python 3.12; steps `uv sync --locked` then `uv run python tools/gates.py`. A second job on `pull_request` only runs `gitleaks` and the 800-changed-line check from global rules §3 (lock files excluded).
- [ ] **Step 2:** Push the branch, open the PR, and read the run. Expected: both matrix jobs green. A red job is fixed here, not excused.
- [ ] **Step 3:** Commit: `ci: gates on Windows and Linux`.

## Done when

`uv run python tools/gates.py` exits 0 locally and both CI matrix jobs are green on the PR. The report lists every tool version chosen and ends with `Not verified:`.
