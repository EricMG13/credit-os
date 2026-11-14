# Step 0C part 1: Python lock, build backend and duplication gate

Date: 2026-11-14. Coordinator: the Rebuild 2 session (roadmap back end; the Rebuild session
keeps the design track). This file is the plan and the sub-session's brief.

**Goal:** everything in roadmap step 0C that touches no file under `web/`, so phase 1
(1A, 1C, 1D) can start. Ends in one pull request against `main`, within 800 changed lines.

**Part 2, not in this plan:** dropping `../src` from `web/scripts/duplication.mjs` and the Edge
run of the open-from-disk check on Windows CI. Both touch files the open D2a stack (#17 to
#23) changes, so they wait for it to merge. Until then the Python package is scanned for
duplication twice, once by each gate command; that is accepted.

## Files this step may touch

`pyproject.toml`, `uv.lock`, `tools/gates.py`, `tests/test_gates.py`,
`.github/workflows/python.yml`, `docs/decisions/0005-python-gate-tools.md`. Nothing under
`web/`, nothing under `docs/design/`, not `VERIFICATION.md`, not `docs/legacy/ports.md`.

## Pre-flight (coordinator, 2026-11-14, `main` at `0acc73b`)

- `pyproject.toml` has `requires = ["hatchling"]` unpinned and one runtime dependency,
  `pydantic==2.13.4`.
- PyPI, read 2026-11-14: `pypdf` 6.21.2 (uploaded 2026-10-21, Python >=3.9, no required
  dependencies); `github-copilot-sdk` 1.0.8 (uploaded 2026-07-22, Python >=3.11, requires
  `python-dateutil>=2.9.0.post0`, `pydantic>=2.0`, `httpx>=0.24.0`); `hatchling` 1.33.0 is
  from 2026-10-28, and 1.32.4 (2026-09-20) is the newest release at least 30 days old.
- `pypdf` 6.21.2 is 24 days old, under decision 0002's 30 days. It is the version on the
  work PC and the pin in `CLAUDE.md`, so the pin stands; the record says so.
- The Python duplication scan is today `web/scripts/duplication.mjs`, which runs the pinned
  `jscpd` 5.4.1 from `web/node_modules` over `web/src` and `../src` with `--threshold 3`. It
  does not run on a pull request that changes no file under `web/` (parked Low, phase 0).
- `.github/workflows/python.yml` has no path filter and no Node step.
- No API of `pypdf` or the Copilot SDK is called in this step; their documents are fetched
  for steps 1D and 1C.
- GitNexus: this repository is not indexed; no impact run.

## Prior art (searched 2026-11-14)

- Owner's repositories: `caos-databricks/.github/workflows/ci.yml` runs
  `npx --prefix frontend --no-install jscpd --threshold 3 ...` over its Python folders from
  the front end's installed copy. Decision: adapt. `tools/gates.py` runs the copy of `jscpd`
  already pinned in `web/package.json`; no new dependency.
- Not taken: pylint's duplicate-code check (a new dev dependency for one rule); a
  hand-written token-window check (new gate code where a pinned tool exists).
- Public GitHub: not searched; the owner's own build covers it.

## Tasks

Global rules §1 apply. The sub-session is the controller and writes no code. Every brief and
review prompt carries: no stub or fake value standing in for real behaviour; no catch-all that
hides a failure; the answer key below, which the implementer does not edit; the comparison,
which the implementer does not weaken. Every report ends with a `Not verified:` line.

### Task 1: lock and decision record (`mx-scaffold`; batched `mx-feature` review)

1. `pyproject.toml`: `requires = ["hatchling==1.32.4"]`; `dependencies` gains
   `pypdf==6.21.4` and `github-copilot-sdk==1.0.8`. Run `uv lock`. Nothing imports either
   package yet.
2. `docs/decisions/0005-python-gate-tools.md`, in the form of decision 0004: a table of the
   Python gate tools and the build backend with version, release date and licence, each read
   from PyPI and the package's licence file, not from memory (`pytest-cov`, `hypothesis`,
   `complexipy`, `bandit`, `pip-audit`, `hatchling`); that they are accepted under decision
   0002, item 1; that `pypdf` 6.21.2 is under 30 days old and why the pin stands; that the
   Python duplication gate reuses the `jscpd` pinned in `web/` (decision 0001) and so the
   Python gates need `npm ci` in `web/` first. If 0005 is taken on `main` when the PR opens,
   use the next free number.

Answer key: the versions and dates in the pre-flight above; `uv lock --check` exits 0; the
resolved versions of `pypdf`, `github-copilot-sdk` and `pydantic` in `uv.lock` equal the pins.
Amended 2026-11-14 by the owner's ruling: pypdf 6.21.4, because 6.21.2 fails pip-audit (7
advisories).

### Task 2: duplication gate (`mx-feature`, test first; `mx-precise` review)

1. Tests first, in `tests/test_gates.py`:
   - `test_real_gate_set_is_pinned` expects `"duplication"` after `"pip-audit"`.
   - The duplication gate's arguments are pinned: the `jscpd` entry script under
     `web/node_modules/jscpd/`, `--threshold`, `3`, and the absolute path of `src`.
   - With `jscpd` not installed, the run exits 2 and names `jscpd` and `npm ci` in `web/`.
   - A canary that runs the real gate command against a temporary folder holding two Python
     files with the same 60 lines and expects a non-zero exit, and against a folder with two
     unlike files and expects 0. It fails, never skips, when `jscpd` or `node` is absent.
2. `tools/gates.py`: one more gate, run with `node` from `PATH`, never `npx`. A missing
   `node` or a missing `jscpd` is exit 2 (tool missing), like every other gate tool. Paths
   come from `ROOT`, never the working directory. The module docstring's exit codes stay true.
3. `.github/workflows/python.yml`: before the gates step, `actions/setup-node@v4` with Node
   24 and the npm cache keyed on `web/package-lock.json`, then `npm ci` in `web/`, on both
   runners.

Answer key: the pinned gate list and arguments above, and the canary. A change to either is a
finding, not a fix.

### Gates and review

- Per task: `uv run --locked python tools/gates.py` exits 0 (run `npm ci` in `web/` once
  first). Report exit codes.
- Before the PR is ready: `/sweep refactoring discover changed-update` on the PR, then the
  whole-branch review, `mx-architect` running `adversarial-reviewer` in a fresh agent, with
  §7's severity mapping. Verdicts and report paths go in the PR body. CI green on both
  runners.
- Fix rounds follow §1: at most two Sonnet rounds per task, then the `mx-autonomous` route,
  then the open findings come back to the coordinator.

## Done when

The PR is open against `main`, CI is green on Ubuntu and Windows, both review steps passed
with no High or Medium finding, and the sub-session's final report gives: the PR link, each
gate's exit code, the ledger lines
(`0C-1 task=<n> agent=<name> fix-rounds=<n> gates-first-pass=<y|n|n/a>`), any Low findings
parked, and a `Not verified:` line. The sub-session does not merge, and does not edit
`VERIFICATION.md` or `docs/legacy/ports.md`; the coordinator reads the diff and writes those.

## Not in scope

The other parked Low findings from phase 0 (layering-check gaps, `UV_PROJECT_ENVIRONMENT`,
complexity outside `src`, a bandit scan floor, the Windows hang-timeout skip) go to the phase
sweep.

## Not verified

- Licences and release dates of the gate tools are for Task 1 to read; none is checked here.
- Whether `jscpd` 5.4.1 exits non-zero on Python duplication at `--threshold 3` for a
  two-file folder; the canary settles it. If it does not, that is a finding for the
  coordinator, not a reason to change the canary.
- Whether `github-copilot-sdk` 1.0.8 installs on Windows with Python 3.12; CI settles it.
