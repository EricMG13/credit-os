# Verification record

One record, newest first, written only by the coordinator at merge. Keep it under 1,000
lines; trim the oldest entries (git history keeps them).

## 2026-11-14 Roadmap back end: 1A PR 2 and 1D PR 1

**Merged**, under the owner's delegation (decision 0006), each at the head named with CI green
on `ubuntu-latest`, `windows-latest` and the review job, and its diff read by the coordinator.

| PR | Step | Head, merge | Content |
| :--- | :--- | :--- | :--- |
| #41 | 1D PR 1 | `1158cea`, `046b56a` | Typed source errors, `SourcePin`, name and kind rules (427 lines) |
| #42 | 1A PR 2 | `e08e547`, `9e66434` | Tables, paragraphs, list items, code blocks; equal-length code spans (789 lines) |
| #45 | records | `9e6ec4e`, `8378d36` | The entry below and the 1C plan amendments |

**Reviews.**

| PR | Task reviews | Sweep discovery | Whole-branch (`mx-architect`, adversarial) |
| :--- | :--- | :--- | :--- |
| #41 | `mx-precise`, and `mx-adversary` on task 1 (names, links, capped read; two fix rounds on the development branch, the second in `files.py`, which is not in #41; re-review pass) | 0 confirmed defects; 3 evidence gaps, ruled below | PASS on `076aefd`: High 0, Medium 0, Low 5, Info 4. A 21-line Low batch followed with no review round |
| #42 | `mx-precise`: three tasks approved (task 1 one docs fix round) | no confirmed defect, 5 Info | FAIL on `4af30f8`: Medium 1, Low 2. Fixed in `e08e547`; scoped `mx-precise` re-review APPROVED, Medium closed |

#42's Medium: a one-line bold paragraph directly above a table was removed from the blocks and
kept only as the table's label, so a bold bottom line above a table would have lost its
paragraph. The coordinator overruled the earlier label ruling: the parser removes no text. No
table in the 27 fixtures has such a label; the rule rests on example tests.

**Gates.** `uv run --locked python tools/gates.py` exit 0, each by its controller: #41 on
`1158cea`, #42 on `e08e547` (333 tests). Mutation on #41 (`mutmut`): 35 of 35 killed at
`076aefd`, not rerun on `1158cea`, where a reviewer's harness of 39 hand mutants left none
alive.

**Ledger.**
- `1A-2 task=1 agent=mx-feature fix-rounds=1 gates-first-pass=n`
- `1A-2 task=2 agent=mx-feature fix-rounds=0 gates-first-pass=n`
- `1A-2 task=3 agent=mx-feature fix-rounds=1 gates-first-pass=n`
- `1A-2 task=4(low batch) agent=mx-feature fix-rounds=0 gates-first-pass=n`
- `1D-1 task=1 agent=mx-feature fix-rounds=2 gates-first-pass=n` (pins, name and kind rules,
  capped read; the capped read is not in #41)
- `1D-1 low batch agent=mx-feature fix-rounds=0 gates-first-pass=y`

Eight of the twelve ledger lines so far (this entry and the one below) failed the gates on the
first run, several on `ruff format` or `mypy` in the task's own tests. Briefs from here tell the implementer to run
`ruff format` and `mypy` before the full gate.

**Rulings by the coordinator.** The 1A grammar rules and the 1D name, length and kind rules are
in their plans. 1D's evidence gaps: odd characters, edge spaces and `CLOCK$` are refused; names
are capped in length; the pin stays signature-only and each reader proves its kind.

**Parked Low findings.** 1A, riding with PR 3: `read_table` called with a label and no label
line; the stray-pipe message names only spaces. 1D: none beyond the amendments.

**Not verified.**
- Table labels, escaped pipes and the stray-pipe refusal have no fixture; they rest on example
  tests. Mutation strength of the refusal branch and the label-line plumbing was not measured.
- Anything on a real Windows file system for 1D (reserved device names by CPython patch level,
  over-long paths, the refused characters on NTFS): Windows evidence is the CI run only.
- The whole-branch review of #41 read `076aefd`; the Low batch after it had no review round, by
  rule. That of #42 read `4af30f8`; the fix was re-reviewed for the findings it fixed.
- Reviewer probes live in git-ignored folders; that they were not edited rests on the
  controllers' word and file times.
- `npm --prefix web run gates` did not run for these pull requests; none changes a web file.

## 2026-11-14 Roadmap back end: phase 1 so far (1A PR 1, 1C PR 1) and Signal S-0

Written by the back-end coordinator that replaced the first one after the credit outage of
02:07 UTC. What the first coordinator did is taken from its transcript and the pull requests.

**Merged.**

| PR | Step | Head, merge | Content |
| :--- | :--- | :--- | :--- |
| #35 | 1A PR 1 | `37846d6`, `d0ca6f3` | Line splitter, one scan pass (headings, fences, comments), `HandoffError`, 27 fixtures with checksums |
| #36 | 1C PR 1 | `3b8931c`, `337e993` | Frozen provider types, `Model` protocol, redaction |
| #44 | Signal S-0 | `81b6954`, `1f303ae` | Decision 0009; `signal` in `LAYERS` and `ISOLATED`; layering test checks isolation both ways |

Each was merged under the owner's delegation (decision 0006; restated to this coordinator on
2026-11-14 as "merge PR when ready"), with CI green on `ubuntu-latest` and `windows-latest`
and the review job, at the head named. #36 and #44: source diff read by this coordinator. #35:
read by the first coordinator.

**Reviews.**

| PR | Task reviews | Sensitive-code review | Sweep discovery | Whole-branch (`mx-architect`, adversarial) |
| :--- | :--- | :--- | :--- | :--- |
| #35 | `mx-precise`: task 1 clean; task 2 one Medium (test gap), fixed, re-review clean | n/a | no new defect | PASS: High 0, Medium 0, Low 2, Info 3 |
| #36 | `mx-precise`: both approved | `mx-adversary`: task review M1 fixed, M2 open (below); a Medium in each of the first two re-reviews, both fixed; round-3 re-review found none | one Medium fixed, one legacy Low parked | PASS on `8d5274d`: High 0, Medium 0, Low 5 (all fixed), Info 3 |
| #44 | batched `mx-feature` (docs and config): PASS, Low 6 (5 applied), Info 1 | n/a | skipped (docs and config, global rules section 7) | skipped, same rule |

#36's third fix round followed the escalation route: an `mx-autonomous` root-cause plan, a
fresh `mx-feature`, then a scoped `mx-adversary` re-review. Root cause: a match ended where its
body's characters ended, so a key written directly after another kept its body; two earlier
rounds had worked only on the left edge. The re-review's own probes: 0 leaks in 2,116,188
glued chains and 1,122,384 left-context cases, text and bytes agreeing; the pre-fix pattern
fails the same probe with 757,429 leaks. The whole-branch review was not rerun on the round-3
head; the round changed 65 lines and was re-reviewed for the finding it fixed.

**Gates.** `uv run --locked python tools/gates.py` exit 0: #44 by this coordinator (225
passed); #36 by its controller on `3b8931c` (319 passed, coverage 100%, suppressions 0); #35 by
its controller on `37846d6`. Mutation on #36 (`mutmut`, fixer's run): 224 mutants, 216 killed,
8 equivalent survivors.

**Ledger.**
- `1A-1 task=1 agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `1A-1 task=2 agent=mx-feature fix-rounds=1 gates-first-pass=y`
- `1A-1 task=3(low batch) agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `1C-1 task=1 agent=mx-feature fix-rounds=0 gates-first-pass=n` (ruff failed once before the
  commit)
- `1C-1 task=2 agent=mx-feature fix-rounds=3 gates-first-pass=n` (round 3: `mx-autonomous`
  plan, fresh `mx-feature`)
- `S-0 agent=mx-scaffold fix-rounds=0 gates-first-pass=n` (two briefing errors by the
  coordinator: one wrong expected row, one pinned tuple outside the implementer's files)

**Rulings by the coordinators.**
- 1A: a `## ` line inside an open fence ends the fence (known limit, in the scan docstring).
  Inline code spans pair runs of equal length; an unmatched run is text. This replaced a
  backtracking pattern that took 5.5 s on a line of 8,000 backticks, and changes no line of the
  27 fixtures (controller's comparison, not rerun by a coordinator).
- 1C: the plan's first PR is split (types and redaction, then the canned adapter). GitHub
  token shapes are redacted with no left boundary and to the end of their word. A compaction's
  charge is never folded into a reply's `billed_usd`. A `totalNanoAiu` that arrives as a float
  is converted only when finite and whole. The end of a call stays `session.idle` or
  `session.error`. All five are in the 1C plan.
- Signal: decision 0009.

**Open Medium, merged knowingly.** #36 merged with one `mx-adversary` Medium open (M2, the
same in the predecessor): `home_paths` leaves part of a Windows user name that has a space
before `/` or the end of the line, or holds `'()`. The first coordinator deferred it to the
adapter work. Nothing calls `home_paths` yet. Ruling of this coordinator: it is fixed in
`redact.py`, test first, with the reviewer's probe `probe_redact_home_name_leak.py` as the
answer key, no later than 1C PR 3 (the session driver, the first caller), which does not merge
while that probe exits 1. The adapter also gives the home directory and the runtime path to
the redactor as exact values. This is a departure from decision 0006's "no High or Medium
open" at merge, reported to the owner.

**Parked Low findings**, for the end-of-step batch of 1C (the list in #36's body is the full
one): text after a home path up to a quote is removed, and `/users/octocat/repos` reads as a
home path; `Redactor("ab12")` iterates characters, so short values over-redact; an `sk-` key
after an unlisted escape, or glued after a letter or digit, is kept; `Decimal("-0")` is
accepted as a charge; a `ghp_` run cut to 30 to 35 characters is not redacted.

**Not verified.**
- Real GitHub token formats: the shapes come from the ruling, not from GitHub's documentation.
- The module-level redaction pattern has no mutation coverage; it rests on key rows and probes.
- The order in which SDK 1.0.8 sends `assistant.turn_end`, usage and `session.idle`, and the
  values `finishReason` takes: source reading only, until the owner's first paid run.
- The reviewer probe `wb_reply_usage_untyped.py` now stops in its own setup; its four cases
  were run by hand by the 1C controller and each is refused.
- `npm --prefix web run gates` did not run for #36 or #44, locally or in CI: the web workflow
  does not trigger on a pull request that changes no web file. #44's body says CI runs it;
  that was wrong.
- The count "Low 6 (5 applied)" for #44 is the coordinator's reading of the review.
- `main` has no branch protection, so the checks are advisory.

## 2026-11-14 Roadmap back end: step 0C part 1 (Python lock, build backend, duplication gate)

**Scope.** Configuration and one gate. `pypdf` and `github-copilot-sdk` are in the lock and
nothing imports them. Part 2 of step 0C (the web duplication script and the Edge run on
Windows CI) waits for the D2a stack.

**Merged.** #26 at `aefea3c` (branch tip `b7f4e2b`), by the owner's standing instruction of
2026-11-14. CI green on `ubuntu-latest` and `windows-latest`. The diff was read by the
coordinator before merge.

**Rulings.** Owner, 2026-11-14: `pypdf` is pinned at 6.21.4, not the work PC's 6.21.2, which
fails `pip-audit` with seven advisories; 6.21.4 is under 30 days old and is taken as a
security-fix exception (decision 0005). Owner: CP-DR's web lookup is left behind
(`docs/legacy/ports.md`). Owner: PRs merge when ready and the coordinators resolve decisions
(decision 0006). Coordinator: the Python duplication gate reuses the `jscpd` pinned in `web/`,
so the Python gates need `npm ci` in `web/` first; packages that arrive only as transitive
dependencies are not held to the 30-day rule, and `pip-audit` is the check on them.

**Gates.** `uv run --locked python tools/gates.py` exit 0 on macOS and on both CI runners,
duplication gate included.

**Review.** Task 1 (lock and decision record), batched `mx-feature`: pass after the ruling was
applied. Task 2 (duplication gate), `mx-precise`: pass, 3 Info. Sweep discovery at `b7f4e2b`:
no confirmed defect, 4 deferred. Whole-branch review, `mx-architect` running
`adversarial-reviewer`: pass, High 0, Medium 0, Low 4, Info 7. The reports stayed in the
sub-session's git-ignored workspace and are not in the repository.

**Ledger.**
- `0C-1 task=1 agent=mx-scaffold fix-rounds=0 gates-first-pass=n` (first pass failed on the
  `pip-audit` finding; fixed by the ruling, not a fix round)
- `0C-1 task=2 agent=mx-feature fix-rounds=0 gates-first-pass=n/a`

**Parked Low findings**, for the phase sweep: a `jscpd:ignore` comment or a root `.jscpd.json`
switches the duplication gate off uncounted, and the suppression counter also misses
`# fmt: off` and `# mypy: disable-error-code` (present before this change); with the `jscpd`
script present but its platform binary absent the gate exits 1, not 2; the 0C part 1 plan
still says in two places that the 6.21.2 pin stands.

**Legacy.** Checked 2026-11-14 at `cbf4400`, 20 merges past the pin; recorded in
`docs/legacy/ports.md`. Nothing is ported yet, so nothing is pending.

**Not verified.**
- The duplication gate analyses no file on today's `src`; only the canary shows it detects
  copied Python.
- The gate on a checkout with no `web/node_modules` (tested by patching the path).
- The work PC's install of `pypdf` 6.21.4.
- `github-copilot-sdk` 1.0.8 ships no licence text; MIT is from its metadata.
- Eleven packages already in the lock, and three new transitive ones, are under 30 days old.
- `npm ci` reports 10 moderate advisories in `web/`'s development packages; the web audit gate
  covers runtime packages only. Passed to the design-track coordinator.

## 2026-11-13 Design track: mocks (steps D1a to D1d) and design system 0.7

**Scope.** Mocks drawn in Claude Design and one record per screen group under
`docs/design/mocks/`. Nothing is built in React. Every mock was rendered at 1440px in one
browser only; no narrow width, Edge, keyboard or screen-reader check.

**Merged.** #8 run (`e6f8b1e`, merged by the owner's instruction in that session), #12 design
system 0.7 with the new status sets, #9 Model and Forecast, #10 Signal, #11 library, #13 run
revised to 0.7. CI green on both runners for each.

**Rulings.** The owner's review 2 rulings are in decision 0003. Six product questions are
listed there as open.

**Review.** Batched docs review of the four records, `mx-feature`: library not a pass
(5 Medium: an unapproved look source, a shape with two meanings, and three places where the
library and Model mocks disagreed); run, Model and Signal passed. After the rulings, #12, #9
and #11 were reviewed again: pass, no High or Medium. The status shapes in #11 and #13 were
checked by the coordinator by reading the records against the design system's tables.

**Ledger.**
- `D1a agent=sub-session fix-rounds=2 gates-first-pass=n/a`
- `D1b agent=sub-session fix-rounds=1 gates-first-pass=n/a`
- `D1c agent=sub-session fix-rounds=1 gates-first-pass=n/a`
- `D1d agent=sub-session fix-rounds=0 gates-first-pass=n/a`

**Not verified.**
- The mocks themselves were not opened by a reviewer; reviews read the records.
- Source sizes were read from class names and pages, not compared side by side.
- The library mock's Shadcnblocks rows copy shadcn/ui and Kibo UI base components, accepted
  for the mocks only (review 2, ruling 3).
- Whether Recharts can draw the chart forms the mocks show.

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

**Follow-up, same day.** `main` at `4fea09f`: #6 design system 0.6 (`e5ac316`) and #7
component map fixes (`4fea09f`), CI green on both runners. The owner's source-look rule (a
component from an approved source copies that page's look) is in decision 0003. An audit of
the merged map by the D0 session found 10 Medium defects, fixed in #7. The docs review of #6
found 3 Medium (source look contradicted in the file, a malformed table, states sharing a
shape); the re-review left 1 Medium in each PR (leftover "layout reference" wording; Running
drawn like Finished), fixed and checked by the coordinator by reading the changed lines.

**Ledger.**
- `D0 agent=sub-session fix-rounds=3 gates-first-pass=n/a`
- `D0b agent=sub-session fix-rounds=3 gates-first-pass=n/a`

**Parked Low findings.** The design system defines no shapes for a module's state on the
Overview tiles; it links the Claude Design project by id; the Claude Design page still shows
the earlier hand-styled samples, not the source look.

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
