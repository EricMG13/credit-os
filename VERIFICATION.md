# Verification record

One record, newest first, written only by the coordinator at merge. Keep it under 1,000
lines; trim the oldest entries (git history keeps them).

## 2026-11-13 Design track: design system and component map (steps D0 and D0b)

**Scope.** Documents and a Claude Design project only. No component was installed, built or
opened from disk; no mock of a screen exists yet.

**Merged.** `main` at `40509b5`: #4 component map and Signal's screens (`e052a32`), #5 design
system (`40509b5`). CI green on `ubuntu-latest` and `windows-latest` for both.

**Rulings.** The owner's ten rulings at review 1 are in decision 0003; the brand guide is a
reference, only its colour values and the logo are fixed.

**Review.** Batched docs review, `mx-feature`: 6 Medium (the two documents disagreed on
sources, motion and gap states; Signal states and five chart kinds unmapped; components shared
across kinds), fixed in one round each and re-reviewed as resolved. Probes, exit 0 at the
merged tips: every colour is a brand hex; all contrast ratios and gray values recompute;
every screen, state, record shape and chart kind is mapped; no name, credential or served URL.

**Ledger.**
- `D0 agent=sub-session fix-rounds=1 gates-first-pass=n/a`
- `D0b agent=sub-session fix-rounds=1 gates-first-pass=n/a`

**Parked Low findings.** Signal's source states name six shapes the design system does not
define; the design system links the Claude Design project by id.

**Not verified.**
- Whether Recharts, Untitled UI React or any adopted component passes the content security
  policy; licences and paid tiers were not read from licence texts.
- The review probes were session scratch files and are not in the repository.
- Colour-blind separation was simulated, not tested with readers.
- The D0 session's statement that standalone Claude Design stops working by 2026-12-14.

## 2026-11-13 Phase 0: skeletons and gates (steps 0A and 0B)

**Scope.** Scaffolding only: an empty layered Python package and a React page that draws a
stub data file. No analytical code, no model run, nothing ported from the predecessor yet.

**Merged.** `main` at `892a600`.

| PR | Step | Merge commit |
| :--- | :--- | :--- |
| #1 | 0A Python skeleton, layering test, gate command, CI | `dde07f0` |
| #3 | 0B part 1: React skeleton, gates, open-from-disk build, policy, rebuilt npm lock | `08f35d0` |
| #2 | 0B part 2: populated-page check, violation canary, hardening | `892a600` |

**Gates on merged `main`, run by the coordinator on macOS.**

| Command | Exit | Result |
| :--- | :--- | :--- |
| `uv run --locked python tools/gates.py` | 0 | ruff, format, mypy, pytest (71 passed, 100% coverage of an empty package), lock, complexity, bandit, pip-audit, suppressions 0 of 0 |
| `npm --prefix web run gates` | 0 | eslint, prettier, tsc, vitest, audit, knip, jscpd, build, Node tests, and six open-from-disk checks in Chrome |

**CI.** Each PR's last run was green on `ubuntu-latest` and `windows-latest` (#2: runs
43500470018 and 43500469936). The open-from-disk check ran in Chrome on both runners, logs
read, not skipped; the violation canary was detected on both.

**Reviews.**

| Level | Reviewer | 0A | 0B |
| :--- | :--- | :--- | :--- |
| Task | `mx-feature` (0A), `mx-precise` (0B) | 2 Medium, fixed | 1 High, 2 Medium, fixed |
| Task, code (added after the plan review) | `mx-precise` | 5 Medium, fixed | n/a |
| Plan review | `mx-architect`, adversarial | see below | 1 Medium (policy directives), fixed |
| Pre-merge sweep discovery and whole-branch adversarial | `mx-architect` | 0 High, 1 Medium, fixed | 0 High, 2 Medium, fixed |

Every fix was re-reviewed as resolved. No High or Medium finding is open.

**Adversarial review of the plans.** Verdict BLOCK: 2 High, 17 Medium. Both High findings were
confirmed against the predecessor and corrected in the roadmap and port map (`ca7bec9`): the
method texts the live launcher sends, and the forecast arithmetic in `owners/cp2g.py`, had both
been listed as left behind. The owner's answers to the resulting questions are decision 0002.

**Findings worth remembering.**
- Vite's default build does not open from `file://` (Chrome blocks the module script); the
  build emits one classic script.
- A plain `uv run` re-locks before the gates start; the gate command needs `--locked`.
- A root-only lock-file exclusion counts a nested `web/package-lock.json` against the line cap.

**Ledger.**
- `0A agent=mx-scaffold fix-rounds=2 (+1 whole-branch wave) gates-first-pass=y`
- `0B agent=mx-feature fix-rounds=2 (+1 whole-branch wave) gates-first-pass=y`

**Rulings by the coordinator.**
- The whole-branch review's fix wave ran on a fresh Sonnet agent and was not counted against
  the two per-task rounds, because its findings were new and came with concrete fixes and
  probes. Not confirmed by the owner.
- A local plain `uv run` can still pass after a silent re-lock; accepted as Low because CI
  launches with `--locked`.
- Step 0B was split into two stacked PRs to stay within the 800-line cap.

**Parked Low findings**, for step 0C or the next phase sweep: `from importlib import
import_module as im` and a relative `__import__` with `level` are not caught by the layering
check; the gate runner's tool lookup ignores `UV_PROJECT_ENVIRONMENT`; `violations` (17) and
`count_suppressions` (16) exceed complexity 15 outside the complexity gate's `src` scope; gate
arguments (coverage floor, complexity limit) are not pinned by tests; no bandit scan floor; the
hang-timeout browser test is skipped on Windows; the Python duplication gate lives in the web
script and does not run on a Python-only PR.

**Not verified.**
- Edge: the browser check has run only in Chrome.
- The work PC: nothing has run there; package availability rests on the owner's statement.
- Pre-commit hooks were never executed.
- Whether any approved React component library works under the content security policy.
- The age of locked npm versions is not checked at gate time; it was checked once, by script.
- The plan review's full report was not saved to the repository; its findings are summarised
  here and applied in `ca7bec9`.
- `main` has no branch protection, so the checks are advisory.
