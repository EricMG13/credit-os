# Verification record

One record, newest first, written only by the coordinator at merge. Keep it under 1,000
lines; trim the oldest entries (git history keeps them).

## 2026-11-14 Roadmap back end: 2B figures and held figures, 1D HTML engine and zip guards, 1B base operands

**Merged**, under the owner's delegation (decision 0006), each at the head named with every
check green on Ubuntu, Windows and the review job, and its diff read by the coordinator.

| PR | Step | Head, merge | Content |
| :--- | :--- | :--- | :--- |
| #250 | 2B PR 4a | `3a69ea3`, `16e6eb8` | `checks/figures.py`: the figure reader (masks, figures, units, currencies) (773 lines) |
| #254 | 2B PR 4b | `9cb41ab`, `4618b19` | `figure.form` and the test that `checks/` holds no float (605) |
| #308 | 2B PR 4c | `4484ffe`, `75a0cd4` | 16 key rows for the witnessed mutation survivors of 4a and 4b (18, tests only) |
| #301 | 2B PR 5 | `93dfede`, `489c360` | `checks/held.py`: held figures, `figure.not-held`, `figure.mismatch`, the note rule, R59 (799) |
| #249 | 1D PR 2b-2 | `cb3bca9`, `308b8c0` | `sources/html.py`: the bounded `html.parser` engine behind `_visible_text`; no caller yet (794) |
| #258 | 1D PR 3a | `2ba4b46`, `2d685b6` | `sources/ooxml.py`: the zip half of the OOXML guards (723) |
| #306 | 1D PR 3a-2 | `1d840f1`, `9967624` | rows holding the end-record reading to zipfile's; an empty zip refused (124) |
| #299 | 1B PR 5 | `971eb5f`, `853b152` | `model/foundation.py`: base operands against the foundation's named cells (798) |
| #311 | CI | `bdecf4a`, `cb091af` | `web.yml`: the gates job may take 40 minutes (5) |
| #313 | records | `042c672`, `9bb9e12` | the entry below |

Stacked PRs (#254, #308, #301, #306) were retargeted to `main` and their CI rerun there
before each merge.

**Reviews.** As each controller reported; the coordinator read each quoted verdict line in
its report file.

| PR | Task reviews | Sweep discovery | Whole-branch (`mx-architect`, adversarial) |
| :--- | :--- | :--- | :--- |
| #250, #254, #308 | `mx-precise` Medium 1 and `mx-adversary` High 1, Medium 5 on the stack; round 3 re-review pass, Low 2, Info 2 | 0 defects each | #250: fix, Medium 2; round 4 closed two and left M-3 (test strength). #254: pass, Low 1, Info 6. M-3 re-review on #308: pass, Info 4 |
| #301 | `mx-precise` and `mx-adversary`; fix round 1 re-review pass, Low 1, Info 2 | 0 defects | fix, Medium 1 (the PR body); re-review pass, Low 2, Info 6 |
| #249 | `mx-precise` pass, Low 2; `mx-adversary` pass, Low 2, Info 5 | 0 defects | pass, Low 2, Info 5 |
| #258, #306 | `mx-adversary` scoped re-review of 3a-2: pass, Low 1, Info 2 | 0 defects | pass on the pair as one change: Low 1, Info 3 |
| #299 | `mx-precise` pass; `mx-adversary` Medium 3, re-review pass | S1 to S9, 0 defects | changes required, Medium 1 (three reader passages left out by no test); re-review at `971eb5f` pass |
| #311, #313 | batched `mx-feature`: pass | none (config, record) | none |

- 2B PR 4 took three counted rounds (the third on an `mx-autonomous` plan) and a fourth,
  test-only round the owner approved; M-3 was closed by #308's key rows under the owner's
  "Yes, keys PR", so the three merged together.
- Mutation counts of record (mutmut 3.8.1, run by the reviewer, validity checked). #308:
  823 mutants, 803 killed, 6 timeouts (none counted killed), 14 survived, of which 13 are
  shown equivalent by running and one is unreachable. #249, new engine code: 426, 360
  killed, 4 timeouts, 62 survived, of which 57 are equivalent and 5 are deferred to PR 2b-3
  with a row each. #306 (`ooxml.py`): 278, 268 killed, 10 equivalent. #299: 202 of 202.
  The earlier counts for #250 and #254 could not be shown valid and are not of record.
- #301 was force-pushed before its merge (entry below); the diff merged has the patch id
  of the diff reviewed.

**Rulings.** 2B R59 to R64 and P1 to P9 (held figures, the note rule). 1B R41 to R44
(operand order, a repeated passage heading, `CELL` refusals, no digit limit), confirmed by
the coordinator at the merge, and R45, ruled then: a
refusal that differs only by the sign rule names the rule in its message (PR 6a). 1D: an
end record found in the archive comment is the conventional reading, pinned by a row in 3c;
a declared charset name is matched against a literal table and refused if absent, with no
codec lookup (PR 2b-3).

**New refusals (1D zip guards).** A zip with no members; a directory over 4 MiB; an end
record that disagrees with its directory; names that differ only by case or form; a member
with two names; a member outside the file; bytes before the first member. Memory at the
caps is measured at about 87.2 of the 96 MiB bound (extrapolated, macOS).

**Ledger.**

- `2B-4 task=round-4-ids(4a) agent=mx-feature fix-rounds=0 gates-first-pass=n`
- `2B-4 task=round-4-ids(4b) agent=mx-feature fix-rounds=0 gates-first-pass=n`
- `2B-4c task=key-rows agent=controller fix-rounds=0 gates-first-pass=y`
- `1B-5 task=1 agent=mx-feature fix-rounds=2 gates-first-pass=y`

**Lows carried.** 2B: `held._findings` runs once per check, twice per document; #254's
I-1 to I-3; the reader's progress guard (its own PR, started). 1D: N1 and the five
deferred survivors to 2b-3. 1B: four unpinned rules and an unguarded
`document.sections[1]` to PR 6a.

Not verified: a real CP-1 foundation and a caller of `check_base` (PR 7); costs of the HTML
engine at its 50 MiB cap (probes read at most 4 MiB); the zip bound on Windows; #250's and
#254's own mutation counts under the memory limits; #308's 13 equivalent survivors are shown
equivalent over 1,000 lines each, not proved for every input.

## 2026-11-14 Roadmap back end: Signal's store, the 1B model fixtures, the step 3A plan

**Merged**, under the owner's delegation (decision 0006), each at the head named with every
check green on Ubuntu, Windows and the review job, and its diff read by the coordinator.

| PR | Step | Head, merge | Content |
| :--- | :--- | :--- | :--- |
| #288 | 1B PR 5a | `8df4fe2`, `fe44101` | the synthetic model fixtures and the test that guards their bytes (670 lines, tests only; rulings R30 to R36) |
| #114 | Signal S-1, 1 of 3 | `8b25c1c`, `1f76a4d` | `signal/store.py`: the store, its migrations and story folding keys (779) |
| #115 | Signal S-1, 2 of 3 | `5b1269f`, `3de6f2c` | transaction ownership, typed refusals, a newer schema refused (799) |
| #116 | Signal S-1, 3 of 3 | `593822a`, `4d08fcf` | the ownership marker, unusable-store refusals, the review batch (358) |
| #310 | plan | `6438f8d`, `f1ffe86` | `docs/superpowers/plans/2026-11-14-phase-3a-orchestrator.md` (386) |

The three store PRs were stacked: each was retargeted to `main`, closed and reopened so its
CI ran on the merge with `main`, and merged in order. #116's head is its reviewed head
`cfc89b5` plus a merge of `main` that changed no line of the PR's own files.

**Reviews.** As each controller reported.

| PR | Task reviews | Sweep discovery | Whole-branch (`mx-architect`, adversarial) |
| :--- | :--- | :--- | :--- |
| #288 | batched `mx-feature` on `f4b3dfd`: pass, Low 2, Info 3 (the later commit changes only the attributes line and its expected bytes) | none (tests only) | none |
| #114 to #116 | `mx-precise` and `mx-adversary`; adversary re-review: pass, Low 4, Info 4 | registered on `78724e4`; its batch is in #116 | Fail on `78724e4`: High 0, Medium 1 (test strength; the store code held). Scoped `mx-precise` re-review on `cfc89b5`: pass, nothing Medium or above |
| #310 | `mx-feature` plan review: Medium 5, all applied; re-review Low 3, applied | none (plan) | none |

- Signal's store took four fix dispatches; two fixed a High or Medium and count as rounds
  (global rules section 1). 62 of 62 hand mutants caught (`mutmut` is not in the lock, so
  this is not a mutmut count of record).
- #288's Lows: its test checks drift, not correctness (PR 5's answer key checks every base
  operand against its cell).
- #310 records ruling D7 as amended: a call left by a crash makes spend unknown, and the
  run does not resume by itself.

**Ledger.**

- `S-1 task=1 agent=mx-feature fix-rounds=2 gates-first-pass=y`
- `1B-5a task=1 agent=mx-scaffold fix-rounds=0 gates-first-pass=n`

**Open for the owner.** Signal's store: `_earliest_match` took 58 s on a hostile feed (the
per-pass cap bounds one pass only); no cap on new stories per pass; a locked database aborts
a whole ingest pass; `mark_read` and `save` are names the port invented. Step 3A's
departures are listed in its plan.

**Incident.** #301 (2B PR 5) was force-pushed at 19:23 UTC (`593cb7c6` to `93dfede7`, a
rebase onto #308) against the rule that a pushed branch is not rewritten. `git range-diff`
shows its 12 commits patch-identical; its controller reports the reviewer confirmed the new head. 2A's #297 and
#300 were rewritten the same way earlier in the day; each controller now restacks by merge.

Not verified: Signal's store on SQLite builds other than the two runners'; the HTTP status
for `StoreUnusable` (the service is not built); #288's `.gitattributes` behaviour on a
Windows checkout other than the CI runner's.

## 2026-11-14 Roadmap back end: Signal's feed reader complete, the store opens, decision 0012, CI paths

**Merged**, under the owner's delegation (decision 0006), each at the head named with every
check green on Ubuntu, Windows and the review job, and its diff read by the coordinator.

| PR | Step | Head, merge | Content |
| :--- | :--- | :--- | :--- |
| #215 | Signal S-3a part 7a | `bbb6d42`, `5ff2a0a` | `signal/feeds.py`: the attribute count that bounds memory (R45) (105 lines) |
| #207 | Signal S-3a part 7b | `27b9252`, `9286842` | `signal/feeds.py`: a text field read in pieces equals the whole-field reading (R46, R47); test Lows (387) |
| #256 | 2A PR 1e | `db74bf1`, `667e1c1` | `store/db.py`: `open_store` and `open_reader`, the library check, identity, pragmas, the integrity check, the stamp (796) |
| #259 | 1B Lows | `1621ea8`, `9f900d5` | key rows and written cases for the test gaps of #243 and #214 (105, tests only) |
| #305 | decision 0012 | `9b6b8ac`, `c3b8249` | failure text is redacted by masking known paths; the claim is bounded; the 1C plan note (68) |
| #307 | CI | `3d66c4c`, `620437d` | `python.yml` skips changes to front-end files alone; the review job moves to `review.yml` (88) |

With #215 and #207 all eight parts of Signal's feed reader are on `main`. #207 showed a red
Windows check twice before it merged: both runs were built at the moment its base changed,
on the old base, and ran Python 3.12.10. Closed and reopened, it ran on the merge with
`main` on 3.12.14 and passed. A stacked PR is retargeted first and its CI triggered after.

**Reviews.** As each controller reported.

| PR | Task reviews | Sweep discovery | Whole-branch (`mx-architect`, adversarial) |
| :--- | :--- | :--- | :--- |
| #215 | `mx-adversary` scoped re-review: pass, Low 2 (two test gaps, parked with #207's RR7-1 and RR7-2 for the next feeds change) | none (a fix ordered after the whole-branch review) | the review of the feeds stack that ordered it |
| #207 | `mx-adversary` scoped re-review: no High or Medium; 0 differences in 140,146 piece readings | none | the same |
| #256 | `mx-precise` pass on `85c44c6`; Low batch by `mx-scaffold` | 7 rows, 0 defects | Pass on `db74bf1`: High 0, Medium 0, Low 6, Info 6 |
| #259 | batched `mx-feature`: pass, Info 1 | none (tests only) | none |
| #305 | batched `mx-feature`: pass, Low 1 (fixed) | none (record) | none; the design itself is from a read-only `mx-architect` review |
| #307 | batched `mx-feature`: pass, Low 2 (left for the next change to `tests/test_gates.py`) | none (config) | none |

- #256's first whole-branch review stopped at the account's usage limit with no report; it
  was rerun on the same model, not another, as the owner chose for #187 ("Wait for Fable", the reviewer's model).
  Its 6 Lows ride with PR 2b.
- #259 closes the two money test gaps of #243: 48 of 48 hand mutants killed (24 survived
  before), and 5 of 5 of #214's.
- #207 was reviewed on Python 3.12.14 only and fails on 3.12.10 (decision 0011).

**Gates and CI.** CI green on both runners at every head above (both on CPython 3.12.14).
`tools/gates.py` exit 0 as reported for #259 and #307. #256: the controller's local run
fails only on the known `web/node_modules` link in its worktree; CI passes. Mutation,
counts of record run by the reviewer with the validity checks: #256, `db.py` 284 mutants,
233 killed, 51 survived (2 killed elsewhere, 13 equivalent, 23 wording, 8 step names, 5
behaviour gaps parked as Lows for PR 2b).

**Ledger.**
- `S-3a part 7a (R45) agent=mx-feature fix-rounds=1 gates-first-pass=y`
- `S-3a part 7b (R46+W-5/W-6) agent=mx-feature fix-rounds=1 gates-first-pass=y` (3.12.14; it failed Windows CI on 3.12.10, out of range by decision 0011)
- `2A-1e task=1 agent=mx-feature fix-rounds=0 gates-first-pass=y`; `2A-1e task=2 agent=mx-scaffold fix-rounds=0 gates-first-pass=y`
- `1B-lows task=1 agent=mx-feature fix-rounds=0 gates-first-pass=y`

**The owner's answers recorded here.**
- Redaction: "Design review first", then "Adopt, rework #187" (decision 0012).
- 2B PR 4: "Yes, test-only round" for a fourth round; then, to the lead coordinator, "Yes,
  keys PR" for a tests-only PR stacked on #254 (#308, not merged). A progress guard for the
  figure reader's loop: "Own small PR after PR 4".

**What went wrong on the machine, and the rules made.**
- At about 16:08 UTC a controller's shell loop ran `rm -rf` on a path whose variable was
  empty and emptied the sessions' shared temporary folder, every session's scratch included. No
  committed work and nothing an open finding depends on was lost. Rule: no delete on a path
  built from a variable; probes and reports live under `.superpowers/sdd/`.
- A mutation run of the figure reader grew about 70 MB a second (one mutant stalls the
  reader loop, which then appends without end). It ended by itself. Rule: mutation runs
  have a short per-test timeout and at most 2 children.
- Over 100 CI runs queued for more than an hour, most of them Python gates on front-end
  pull requests; #307 is the remedy.

**Open, for the owner.**
- Signal's store (same in the predecessor, stated in #114's body): the duplicate lookup
  reads every stored story sharing a title key under the write lock; one hostile 2 MiB feed
  takes about 58 s. A cap per pass bounds one pass only; the read needs narrowing. Nothing
  caps new stories per source per pass. A locked database aborts a whole ingest pass.
- `CLAUDE.md` says CI runs the same two commands; a front-end-only pull request now runs the
  web gates and the review job only. Its Python row still says `>=3.12,<3.13`.
- 2A: no SQLite other than 3.53.1 was run, the 3.37 floor included.

**Not verified.**
- That GitHub skips `python.yml` on a front-end-only pull request: no such pull request has
  run since #307.
- #256: Windows beyond the one CI job; races beyond two processes; power loss.
- #207, #215: feeds from real publishers; other expat builds; Python 3.12.11 to 3.12.13
  never tried.

## 2026-11-14 Design track: library pages (step D2b)

**Merged** into `main` in stack order by the coordinator, 57 PRs as merge commits: #57, #58,
#70, #71, #72, #76, #77, #83, #84, #85, #103, #104, #105, #106, #107, #125, #126, #127, #128,
#129, #130, #136, #137, #138, #139, #140, #141, #142, #260, #261, #262, #263, #264, #265,
#266, #267, #268, #270, #271, #272, #273, #274, #275, #276, #277, #278, #279, #280, #281,
#168, #282, #283, #284, #285, #286, #287, #294. `main` after the last merge: `4a0cbdbb`.
`git diff --quiet origin/main 3ca2f8c7 -- web/src/pages/library web/fixtures/library.json`
exit 0: the library pages and fixture on `main` equal the final head `3ca2f8c7`. Review
coverage: the whole-branch review read `39f34eca`; the fix round is #294; the same reviewer
agent re-reviewed at `b32a784` (pass); the final head `3ca2f8c7` (33 lines, the re-review's
two Lows) was gated and checked against the reviewer's probe and had no review round of its
own, as the owner's rule for Low findings allows. No reviewer read `3ca2f8c7`.

**Order of merging.** #57 was merged at 18:04:21 UTC and #287 at 18:09:09; the fix PR #294
was merged in the same sequence, last, at 18:09:14 (`git log origin/main --merges`). The
whole stack merged in under five minutes.

- **D2b, library pages**: 57 stacked PRs, #57 on `main`, each based on the one before. The
  stack touches only `web/src/pages/library/` and `web/fixtures/library.json` (at `39f34eca`:
  89 files, 22,817 added lines against `main` `718a13b4`; #294 adds 604 changed lines against
  #287). Every PR within 800 changed lines (largest 796, #57).
- PR #168 (a contributed fix, confirmed by the owner's process) sits after #281 (task 13g),
  not after #142 where it was first placed: it entered the working branch after task 13, and
  after #142 it conflicts with 11a and four of its tests fail under task 12's Evidence
  cross-checks, so the PRs from #260 to #281 would have failed their own gates. Its head is a
  fast-forward of the contributor's branch with fix `4f35e1a` (129 lines) and a follow-up
  (31 lines) merged in; a comment on #168 records the placement.

**Delivers.** The library pages from the D1 mocks on fixture data (`web/fixtures/library.json`,
synthetic issuers): Library home (cards and a List with the predecessor's filters, sort and
count line), report history, the run header and tabs, the trace drawer and Show sources, the
Overview, Changes (Cards or Table), module pages, and the Evidence pages (Summary, Trace
register, Sources, Gaps, Record, a jump menu on Ctrl or Cmd K). The fixture holds loading,
capped and first-run runs and the no-such issuer, run and module pages. All state is in
memory; the missing chart kinds draw their Table side only.

**Coordinator pre-check** on `39f34eca` and on the final head `3ca2f8c7`, before merge: no
file outside `web/src/pages/library/` and `web/fixtures/library.json`; largest PR 796 changed
lines (cap 800); no fetch, storage, raw HTML or suppression added; one timer
(`parts/CopyToast.tsx`, dismisses the copy message, cleared on reuse; a failed copy is
shown); one `Math.ceil` (a two-column split of a list, not a figure); `git merge-tree` with
`main` `9f900d53` clean.

**Gates** (controller's and implementers' reports; the reports are kept outside the
repository, in the session notes folder `d2b-records/`; the D2b worktree was archived).
- `npm --prefix web run gates` exit 0 and the Python gates exit 0 on `39f34eca` (`main`
  `718a13b4` merged; web 120 files, 2747 tests), the controller's run. At `b32a784` the
  fixer's `gates` exit 0 (121 files, 2772 tests); the re-reviewer ran only the library
  folder's 21 test files (777 tests, exit 0). At `3ca2f8c7` the fixer's `gates` exit 0 (a
  background run; no counts recorded) and the controller reran `wbr-list-vs-run.mjs` (exit 0).
- Per task, each commit's gates exit 0 per the implementer, with exceptions. Task 1: the
  first run failed on a shared test and a route ruling; exit 0 after the rebase. Task 2: the
  full gates at `cea0796` exit 1 (`test:file:gates` died at its canary under machine load);
  every step before it exited 0 and CI decided. Task 10: one run on the first commit, the
  rest by steps after load timeouts. Task 11: commit 2 by steps. Task 12: re-cut `fba2982`
  had typecheck and its test file only, full gates left to CI. Task 13: the final tree by
  steps (the one-command run timed out under load); commits 4 to 7 only partly gated locally;
  fix `9737240` by steps (one drawer test took 5.2 s against its 5 s limit under load).
  Task 14: gates at `22f0882` and at fix `0bef3da`, not at each of the first four commits.
  Whole-branch fix round: one gates run at `b32a784`, not per commit, for the seven commits
  `2f032bd` to `b32a784`. Tasks 8 and 12 were re-cut to at most 800 lines per commit with a tree identical to the
  gated one (diff checked empty).
- CI: every PR head had `gates (ubuntu-latest)` and `review` passing and at least one passing
  `gates (windows-latest)` job before its merge, but not every Windows job passed. #282, #284,
  #286, #287 and #294 each also carry one Windows job that ended cancelled, and #168 one more
  besides the failure below. Those jobs were cut off by the `web` workflow's 20-minute job limit,
  not by a failed check; this entry omitted them because the coordinator's check before merging
  counted only failed and pending jobs. Measured on `main` `4a0cbdbb` (run 43624986501, Windows,
  first attempt of the rerun at 18:49 UTC): `npm run gates` 10 min 5 s and "Open from disk in
  Edge" 6 min 1 s passed; "Open from disk in Chrome" was cancelled after 3 min 13 s at the
  20-minute mark. With all four page groups on `main` the Windows job no longer fits 20 minutes on
  a slow runner; Linux takes about 8 minutes. The other exception: #168 was merged with one of its
  two Windows jobs failed: the rerun of that job (run 43622974167, attempt 2) ended cancelled and
  never produced a result, so on #168's commit that job has one failure and no pass. The failure
  was `StatementsPage.test.tsx` "describes a missing cell by its reason, shows it on focus, and
  draws it n.a., never 0" (`Test timed out in 5000ms`, 5,130 ms), a model-pages test outside this
  stack (see "Model pages test timeout (#295)" below); the duplicate Windows job on the
  same commit (run 43622974170) passed. #168's first run (43613658822) failed "Changed lines
  at most 800" because it still measured against its old base (10,753 lines against the old
  base, 296 against the new one); the D2b session closed and reopened the PR with no new
  commit to get runs on the right base. Earlier failed checks on #127 and #139 were the
  Windows `DevToolsActivePort` read race fixed by #156, on heads the end push replaced; #71
  and #83 failed once in the shared kit page check and #264 and #280 had Windows gates
  cancelled under queue load, each rerun.

**Reviews.**
- Task review per task, `mx-precise`; scoped re-reviews by `mx-precise`, except task 5's
  second fix and task 5b's fix (`mx-feature`). PR #168: one Medium (a test pinned a malformed
  lead, one name repeated 7,142 times, as valid), fixed, re-review approved; one Low left
  (the name split costs about 2 s on 13 very long near-miss names).
- Sweep discovery, `/sweep refactoring discover changed-update` (`mx-autonomous`, register
  `sweep/register.md`): 23 rows (Medium 3, Low 17, Info 3). Fixed in #287 (`mx-precise`:
  approve): SW-01 (ruled), SW-02 to SW-06 and the platform-only SW-09 and SW-10, remeasured
  live; SW-12 and SW-13a to d were already fixed at base. SW-07 and SW-11 are owner
  questions; SW-08 and SW-14 to SW-20 (structure, duplication, `read.ts` at 2,002 lines) go
  to the next phase sweep; SW-17 closed for two of its pairs in the fix round below.
- Whole-branch adversarial review (`mx-architect` running `adversarial-reviewer`, a fresh
  agent) on `39f34eca`: needs fixes, High 0, Medium 1, Low 8, Info 4. WBR-01 (Medium): the
  Halden List row showed net leverage 2.9x and interest coverage 4.1x as reported, and
  leverage 3.4x, against its own run's 4.6x and 2.4x on company-adjusted EBITDA and no gross
  leverage. Ruled and fixed (the row carries the run's figures, adjusted, leverage not
  recorded) with an agreement test that fails on the base fixture. Lows WBR-02 to WBR-09
  rode with it (blank home measure text; names used as keys held unique; download and Open
  addresses held to a relative path; empty run id; a changes link beside a null report;
  `tabs.sources` and `limitations.count` tied to their rows; a Changes audit-material test;
  `slice.ts` comments stating what the reader enforces), as did the drawer Low (its open
  state resets on a run change). The fix round is #294.
- Re-review by the same reviewer agent (not a fresh one) at `b32a784`: pass, High 0, Medium
  0, Low 2, Info 4; WBR-01 to WBR-09 and the drawer Low addressed. Probes rerun:
  `wbr-list-vs-run` 0, the drawer probe 0, the audit scan 0, `wbr-rr-base-fails` 0 (the
  committed tests fail on the base: 21 fail). Three probes still exit 1, accepted as stale,
  not defects: `wbr-reader.sh` (13 of 14; its WBR-02 case writes to Halden's leverage text,
  a measure that is `null` under the ruling, so it throws before the reader runs; the rule
  holds on two other measures per `wbr-rr-reader.sh` part A), `wbr-pages.sh` (2 of 3; its
  WBR-04 case looks for the download link of a slice the reader now refuses; the page draws
  the invalid notice with the path and no link, `wbr-rr-reader.sh` part C) and
  `wbr-measure.sh` (11 of 16 period pairs refused; WBR-09 asked for comment changes only, so
  its output is unchanged).
- Two new Lows from the re-review, fixed in `3ca2f8c7` against the reviewer's probe with no
  review round: RR-01 (the address rule accepted eight forms that resolve outside the
  library folder: a leading space or tab before `https://`, `//` or `/`, a tab or newline
  inside a scheme, `%2e%2e` segments; now an allow-list of relative paths; probe
  `wbr-rr-reader.sh` part B exit 1 at `b32a784`, exit 0 after, 14 of 14) and RR-02 (a Home
  test title retitled). The re-review also raised four Infos: RR-03 (module and issuer ids
  are still read with `str`, so an empty one passes), RR-04 (a Home sort test now compares
  the first two rows where it compared three; not a weakening), RR-05 (the run header
  remounts with the body on a run change) and RR-06 (unchanged from the first review: SW-07
  stands as the owner question, CI on `39f34eca` was pending).
- Deferred Infos: WBR-10 (the model-calls table styling assumes a column order the slice
  does not state), WBR-11 (the slice is validated on every render, twice; 0.59 ms at fixture
  size), WBR-12 (`readTree` and `DerivationTree` recurse without a depth bound, so a very
  deep derivation raises an uncaught error instead of `invalid`; reasoned, not run).

**Live validation** (the D2b controller, 2026-11-14; no input shows a walk by the owner).
- `file://` in headed Chrome over its debugging protocol, after tasks 1 to 3, 5, 5b, 6 and 7,
  8 to 15 and the sweep fix batch (walks named `t1` to `t15` with `t5b`, `t67` and `t8c`,
  and `sw1`, as the progress file names them; task 4 had no walk of its own), on that
  task's head. On the finished stack at `39f34eca`: 18 routes at 1440 and
  1024, 36 of 36 with one `h1`, no overflowing leaf, no horizontal scroll, no console or CSP
  problem, no request outside `file://`.
- `file://`, `b32a784` (walk `wbr`): the Halden List row reads n.a. (leverage not recorded),
  4.6x adj. and 2.4x adj. with the company-adjusted description and the three count lines;
  the trace drawer opened on 2026-09-30, closed on 2025-09-30 and still closed on return.
  This is the only live check of the fix round and covers the Home list and the drawer only.
- Localhost in the app's built-in browser pane (127.0.0.1:4612, owner-watchable),
  `39f34eca`: 20 routes, one `h1` each, no horizontal scroll, no console message; not a CSP
  proof (the content-policy and no-network checks count on `file://` only).

**Ledger** (D2b; all `agent=mx-feature`). fix-rounds 0 for tasks 1, 9, 10, 11, 12, 15 and the
sweep batch; 1 for tasks 3, 4, 5b, 6, 7, 8, 14, PR #168 and the whole-branch fix; 2 for tasks
2, 5 and 13. gates-first-pass `n` for tasks 1 and 2; `y` for the rest as recorded by the
controller (task 13's `y` rests on its step-by-step gates; see Gates). Machine restarts
between about 09:30 and 09:52 UTC killed task 9's review more than once and a merged-tree
gate run; the review then ran and approved. At 16:08 UTC another session's command emptied
the scratch directory under `/private/tmp`, removing D2b's scratch worktree `forward-1`; its
branch was already pushed (`39f34eca` local and remote) and all records were in the stage
folder: nothing lost.

**Rulings** (controller, each reversible; the full list is in the D2b progress ledger):
- Mock frames govern over the component map; the page title is the route name and the run
  header an `h2` under App's `h1`; Library home is `/library/home`.
- Missing chart kinds (gantt, liquidity walk, peer scatter and range, headroom) draw a Table
  side only, with no dead toggle, in one local card around the kit `ChartTable`.
- Predecessor list rules (adj. mark, bands, sort, count line, hidden-rows heading) are built
  on the List side; band selects count as applied filters.
- "loading" is a slice-given state drawn as a skeleton; Forecast and download addresses come
  from the slice, null draws disabled with its reason; the Forecast link is null or exactly
  `#/model/<issuer>/<run>/forecast`.
- A history agrees with its home card; the reader rejects report or changes on a Failed,
  Rejected, Interrupted, Running or Queued entry.
- Trace gains a visible `heading`; Show sources persists in memory across a run's pages for
  the session; the absent-slice sentence "This data file holds no library pages" stands.
- The capped run's many-modules state keeps its own counts (nine delivered, four not run)
  over the mock sample's "10 modules delivered"; direction gains "flat"; the module name
  carries a state badge for every state; half-width pairs go two-up from 1200px.
- The module filter appears only on Evidence tabs delivered per module; an item address
  starts its tab unfiltered. New addresses `/modules`, `/evidence`, `/evidence/trace/:item`,
  `/evidence/gaps/:item`; the Trace register starts closed and has no Value column (`value`
  stays in the slice as the fixture-agreement contract); Trace and Gaps are native tables.
- Departures: Secured leverage targets T-0104 (mock T-0016); the timings table draws its
  Module-state badge in the end column; "Ctrl K" off Apple, first jump item not highlighted
  on open; the file note reads "7 read in full, 1 read in part, 1 unreadable". Task 9:
  unanswered questions draw as plain rows, not empty details; pathway numbers come from the
  list position (a CSS counter). Task 13: Trace tab counts equal the rows held (60 / 0 / 0),
  a departure from the mock sample "148". Task 8: contrary evidence text size ("departure
  8"; computes 16px/26px in the built CSS). The final
  report lists more (per-file copy names, only rows with a calculation expand, local
  `MetricTile` and statement table); those were not rechecked against task reports.
- SW-01: "Modules N" counts the modules the run lists. SW-07 not fixed (owner question).
  WBR-01: the Halden row carries its opened run's own figures. Task 9 to 14 PR branches were
  pushed once, with one stack forward; the fix wave pushed only its new branch.

**Open for the owner.**
- Links into runs the slice does not hold (SW-07): four of the five home cards (Corvane
  Packaging, Tessaly Foods, Ardenne Cable, Lumora Health) open "No such run", and two Halden
  history links open the static loading skeleton. The Halden Forecast link opens the model
  page's "Not found for this run" (the model fixture holds TransDigm only).
- The ten delivered download and Open addresses under `downloads/` name files the built
  folder does not hold, so each opens a missing file.
- Does delivery ever write the "loading" state; the absent-slice sentence on `#` (the
  shipped `data.js` has no library member); Corvane Fasteners has no home card.
- The capped run compares "since 31 December 2025" while its history says those runs
  delivered nothing; the Trace mock's T-0068 "listed under Gaps" against the Gaps mock;
  Delivered modules holding gaps (G-04, G-06) and G-06 linked to Financial performance while
  its n.a. cell is on Capital structure.
- The reader accepts a module lead repeating a held name or counting more modules than held
  (predates D2b; SW-08: 1,105 ms for one read of a
  36,399-character lead over 13 names); mutants "none draws a mark" and "default weight
  medium" (task 8) predate the fix.
- Deferred to the next phase sweep: SW-14 to SW-20 (SW-18, two parallel reader kits, needs
  the coordinator: the model folder has another owner), WBR-10 to WBR-12, RR-03.
- Step 3B contract notes: trace `value` is required and kept though not drawn; the reader
  refuses 11 of 16 measure period pairs (`slice.ts` states the two accepted forms); delivered
  addresses must be relative paths inside the library folder; counts that name held rows are
  tied by the reader (Modules, Trace, Sources, Gaps, limitations, registers).
- Kit changes needed (final report): ChartTable node cells, per-column alignment, per-row
  emphasis, a withheld reason and a sort affordance; a toggle-less Table-only ChartFrame;
  Table `scope` and a detail row; MetricCard trace slot and Cell values; Callout title weight
  and trace slot; Timeline heading level; Alert body size; PageHeader subtitle slot; Blocked
  "Not run" wording; ProgressBar accessible name; an eslint allowance for `tabIndex` on a
  `role=region` scroller. Built locally under `parts/`: Switch, RunFeed, TraceControl,
  TraceDrawer, DerivationTree, avatar group, copy snippet and toast, command menu,
  DownloadButton, details list, numbered list panel.

**Not verified.** That any reviewer read `3ca2f8c7` (RR-01 and RR-02 were checked against the
reviewer's probe only); that the re-review was by a fresh agent (it was the agent that wrote the
review); a live walk on `3ca2f8c7` or on merged `main` (the `b32a784` walk covers the Home list and
the drawer only); per-commit gating of the seven fix-round commits (the re-review lists it); the
print preview of collapsed limitations (task 7 walk: "Not walked"); open Infos of the sweep batch
review (`modulesCount` check order, a quadratic `findIndex` on issuer ids, focus dropped by the body
remount on a run change; its Low L1, the drawer across runs, was fixed in the fix round); any CI run
of a PR head merged with `main` after `718a13b4` (the stack was forwarded once; `git merge-tree`
with `9f900d53` was clean); a passing run of #168's failed Windows job on its own commit (its rerun
was cancelled); a complete Windows run, for the job that was cancelled, on each of #282, #284, #286,
#287 and #294 (each has a passing duplicate job on the same commit); the full gates at `3ca2f8c7` by
the controller (the fixer ran them); the whole-branch review did not rerun the gates (taken from the
ledger), read the tests in full (about 13k lines, sampled), compare each page with its mock frame
again, run WBR-12's deep tree, or probe WBR-05 for issuer and module ids; the fixer's WBR-08 mutant;
RR-01 in a real browser (judged by Node's URL parser); Edge and Windows browsers beyond CI;
screen-reader announcements; print output; the Chart sides of the missing chart kinds; real download
files; the Halden Forecast link against a model fixture holding Halden; any slice against a real
delivered run (step 3B does not exist); whether the fixture's invented issuer names match a real
company; any report kept only in the git-ignored `.superpowers/` folders of eight finished
design-track worktrees (`agent-a72a…`, `agent-aeee…`, `agent-a44c…`, `agent-ac21…`, `d2c-pr-a`,
`d2c-pr-b`, `d2c-split`, `kit-link-toggle`): the coordinator removed them at about 20:15 UTC after
checking only for uncommitted tracked files, so such reports were deleted unread (the D2b, D2c and
D2e records cited in the entries were copied to the notes folder before and are not affected).
**Corrected, the Windows web gates on the merged tree.** On `main` `4a0cbdbb`, `python` push run
43624986619 passed; `web` push run 43624986501 passed on Linux and its Windows job was cancelled
three times (the original run and two reruns queued at 18:50 and 19:11 UTC), each at the 20-minute
limit, none with a failed check; in the second rerun gates took 11 min 50 s and the Edge check 6 min
17 s before the Chrome check was cut off. PR #311 (back-end coordinator, merged; `web.yml` only)
raised the limit to 40 minutes. The `web` push run 43632557384 on `main` `cb091afe` (the merge of
#311; `git diff --stat 4a0cbdbb cb091afe -- web` prints nothing, checked) passed on both systems; on
Windows `npm run gates` took 10 min 37 s, the Edge check 5 min 33 s and the Chrome check 3 min 26 s.

**Model pages test timeout (#295).** PR #295, test only
(`web/src/pages/model/StatementsPage.test.tsx`, +16/-6), merged at about 18:04 UTC. The test
named above ("describes a missing cell by its reason, shows it on focus, and draws it n.a.,
never 0") failed on Windows CI at 5,239 ms (PR #230), 5,840 ms (`main` `6bc1e5aa`, run
43609426194) and 5,130 ms (#168). Measured cause (implementer, on a loaded Mac, about 600 ms
there): no real-time wait; about 70% of the test is three renders (the first render and two
case switches, each re-rendering every chart section, including debt and recovery sections
that do not depend on the case); the row and cell helpers ran a role query per row. Change:
the helpers read the table elements directly; that one test has its own 20 s limit with the
reason in a comment; no assertion changed; no global timeout. This closes the "Open Low" recorded in the D2c
entry (the test running close to the 5 s limit on Windows CI). Review `mx-precise`: approve,
High 0, Medium 0, Low 2 (the comment says "close to" the limit where the runs were over it;
three other tests in the file estimated at 3.9 to 4.6 s on Windows), Info 1; five mutation
probes each turned the file red (probes kept in the notes folder `pr295-review/`). Gates:
`npm run gates` in `web/` exit 0 (100 files, 1,995 tests, the implementer's run); CI on the
PR green on Linux and Windows. Not verified for it: Windows timing after the change beyond
one green CI run; the speed-up from the helpers was within load noise on the Mac; the
re-render of the debt and recovery sections on a case switch is a measured cost left for the
phase sweep.

## 2026-11-14 Roadmap back end: Python 3.12.14, Signal's feed reader, 1B inputs, 2A transactions

**Merged**, under the owner's delegation (decision 0006), each at the head named with every
check green on Ubuntu, Windows and the review job, and its diff read by the coordinator.

| PR | Step | Head, merge | Content |
| :--- | :--- | :--- | :--- |
| #209 | 1D PR 2b-1 | `33185f3`, `eb8a83a` | `sources/html.py`: HTML decoding and the line writer (511 lines) |
| #226 | 2A PR 1d | `f4dbd73`, `567f088` | `store/txn.py`: the write transaction and the migration runner (778) |
| #246 | 2A PR 1d-b | `5622f25`, `d32b08a` | store scans, value-free messages, parked test rows, the fail-open docstring (145) |
| #245 | decision 0011 | `42d8410`, `a2b4f1c` | Python pinned to 3.12.14 in `pyproject.toml`, `.python-version` and both CI runners; the record |
| #244 | 1B keys (1) | `95992d1`, `970bc15` | the answer-key scripts for PR 2 and PR 3 and the test that each reproduces its key (582, tests only) |
| #255 | 1B keys (2) | `4398ab0`, `d008cc1` | the same for PR 4a and PR 4b; the PR 4b oracle uses `fractions.Fraction` and imports no `credit_os` (759, tests only) |
| #243 | 1B PR 4b | `8759d10`, `59ffc77` | `model/inputs.py`: the forecast inputs schema, scale to millions, the repayment bound (797) |
| #248 | 1C PR 2g | `c6116c3`, `68b327b` | `provider/redact.py`: a Users or home folder inside a path is redacted (198; opened by the owner's review-fix process) |
| #109, #110, #178, #179, #185, #186 | Signal S-3a, parts 1 to 6 | `f970282`, `a689fd1`, `0d4132e`, `fd4d4ab`, `56e0c3a`, `3141609`; merges `d4c9141`, `5e5d5d1`, `2cd07b5`, `2153cdb`, `718a13b`, `4a8a6d1` | `signal/feeds.py`: the feed reader on expat, DTDs and entities refused, namespaces resolved by the reader, text and HTML streamed to bounded sinks; the memory test |

The six feed PRs were stacked. Each was merged in order after its base was set to `main`, the
PR closed and reopened so CI ran on the merge with `main`, and all three checks passed at the
expected head. Parts 1 to 4 hold defects that later parts fix (a hex-looking last host label,
the memory bound), so the stack was merged only as a whole, within about an hour. Parts 7a
and 7 (#215, #207) were still in CI when this entry was written and are not recorded here.

**Reviews.** As each controller reported.

| PR | Task reviews | Sweep discovery | Whole-branch (`mx-architect`, adversarial) |
| :--- | :--- | :--- | :--- |
| #209 | `mx-precise` pass and `mx-adversary` pass on `baef6ee` (Lows only); Low batch by `mx-scaffold`, probes exit 0 | 0 defects | Pass on `33185f3`: High 0, Medium 0, Low 2, Info 4 |
| #226 | Four rounds on the task (two Sonnet, one from an `mx-autonomous` plan, one the owner's); `mx-invariants` pass on `fd66ecc` | as reported | Pass on `f4dbd73`: High 0, Medium 0, Low 2, Info 3 |
| #246 | batched `mx-feature` on `4308974`: pass, Low 1; parked Lows checked against the reviewers' probes (exit 0) | none (tests and messages) | none, by the batching rule |
| #245 | batched `mx-feature`: pass, Low 1 (fixed in `42d8410`) | none (config, record) | none |
| #244, #255 | batched `mx-feature`: #244 pass (Info only); #255 pass (Low 2, Info 2) | none (tests only) | none, by ruling R22 |
| #243 | on `a42a349`, `mx-precise` Medium 1 and `mx-adversary` Medium 2 (the same holder defect, and a base key printed in full); one fix round; `mx-precise` re-review pass on `8af69fa` | as reported | Pass on `8759d10`: High 0, Medium 0, Low 1, Info 7 |
| #248 | `mx-adversary`, two rounds: Medium 1 (a folder word in the user-name slot hid the next home), fixed in `2e4cc4d`; pass | none | none (a 198-line fix from the owner's process) |
| Feeds | `mx-precise` and `mx-adversary` on `f970282` and `d41a8f0`; `mx-adversary` re-reviews on part 3 and on `fdfb1e7`; a third round planned by `mx-autonomous`; `mx-adversary` re-review on `ae46734` (the final tree of parts 1 to 6): pass, R24 closed by construction, Info 3 | not run on these parts | on `d41a8f0`: Medium 1 and the memory bound open, both closed by parts 3 and 5 |

- #226's fourth round is the owner's ("Yes, document it", recorded in the entry below): an
  interrupt during a write leaves as `StoreUnusable`, documented and pinned, not changed.
- #243's Mediums: a tuple or model-instance holder skipped the scale step; a base key was
  printed in full in a refusal. Its parked Low is test strength: 24 of 48 hand mutants of the
  validators, field declarations and constants pass every test. Two would be silent money
  errors (downside amounts left in thousands at scale 1000; a negative case
  `debt_repayment`). The source is right on all 48. A tests-only PR closes it before PR 5.
- Feeds, R24: peak parser memory stays under 64 MiB for any body within the 2 MiB cap. The
  worst peak reached was 62.5 MiB, from expat's own attribute dictionary on a feed that is
  then refused; the controller names that margin as the weak point.
- The feeds whole-branch review predates parts 3 to 6. What covers the final tree is the
  `mx-adversary` re-review on `ae46734`, not a second `mx-architect` review.

**Gates and CI.** CI green on both runners at every head above; from #245 on, both runners
are CPython 3.12.14 (read in the Windows log of #245). `tools/gates.py` exit 0 as the
controllers reported for #209, #243, #255 and the feed parts. For #245 the implementer's
local gates report was not relied on; CI is the evidence. Mutation: #209, 736 of 775 killed,
34 survived (12 in `html.py`, equivalent, agreed by the whole-branch reviewer; the rest in
unchanged `walk.py`), 5 timeouts; #243, count of record by the whole-branch reviewer with the
clean-pass and forced-fail steps shown: `inputs.py` 332 mutants, 325 killed, 7 equivalent,
`refusals.py` 26 of 26. Feeds: hand mutants only (53 of 56 at part 2, 3 equivalent).

**Ledger.**
- `1D-2b-1 task=1 agent=mx-feature fix-rounds=0 gates-first-pass=n`; `1D-2b-1 Low batch agent=mx-scaffold fix-rounds=0 gates-first-pass=y`
- `2A-1d task=1 agent=mx-feature fix-rounds=4 gates-first-pass=n` (two Sonnet, one planned, one the owner's)
- `1B-4b task=1 agent=mx-feature fix-rounds=1 gates-first-pass=n`
- `1B-keys1 task=1 agent=mx-scaffold fix-rounds=0 gates-first-pass=y`; `1B-keys2 task=1 agent=mx-scaffold fix-rounds=0 gates-first-pass=y`

**Rulings by the coordinator.** In the plans and in decision 0011.
- Python: `requires-python` is `>=3.12.14,<3.13` after the owner's answer "3.12.14 or later".
  A reader on `html.parser` is written against 3.12.14 and its tests pin the parser
  behaviour it relies on. Signal's rework for 3.12.10 was shelved.
- A mutation count is the count of record only when the run shows the clean tests passed
  and the forced fail failed, known mutants behave as expected, and the reviewer ran it. A
  2B run had reported 786 of 786 because collection failed inside mutmut.
- 2B PR 4 (#250, #254, not merged): the owner authorised a fourth, tests-only round ("Yes,
  test-only round") for two test-strength Mediums of the whole-branch review.

**Open, for the owner.**
- `CLAUDE.md`'s target table still says Python `>=3.12,<3.13`; the pin is `>=3.12.14`.
- Redaction (#202, #248): a lower-case `\\?\unc\` lead, a lead after `:`, and a
  single-letter drive inside a URL are not handled.
- 2A: a second interrupt path (through the authorizer, `not authorized`) is accepted under
  "Yes, document it".
- 2B figure reader: `In March 1.5% growth was seen.` reads 5% in passage text (the date mask
  takes `March 1`); PR 5 refuses it as not held and pins it as a known false refusal.
- 1D: the csv reader takes about 1.4 s per MiB with no time bound; step 3A decides.

**Not verified.**
- The work PC's Python level was stated by the owner, not read from the machine; 3.12.15 and
  later are untried.
- Feeds: feeds downloaded from real publishers; operating-system memory (tracemalloc only);
  `mutmut`; other expat builds.
- #243: real model-written blocks. #226: races beyond those the reviewers probed.
- #248: mutation testing of the new pass; whitespace characters beyond those probed.

## 2026-11-14 Design track: Signal pages (step D2e)

**Merged** into `main` in stack order by the coordinator, 43 PRs as merge commits: #64, #65,
#79, #80, #93, #94, #101, #117, #118, #119, #123, #124, #131, #132, #133, #143, #144, #145,
#146, #154, #155, #172, #173, #174, #175, #188, #189, #190, #192, #193, #195, #203, #204,
#205, #206, #238, #239, #240, #241, #242, #251, #252, #253. `main` after the last merge:
`dca4981c`. `git diff --quiet origin/main cc1f8cb3 -- web/src/pages/signal
web/fixtures/signal.json` exit 0: Signal's pages and fixture on `main` equal the final head
`cc1f8cb3`. Review coverage: the whole-branch review covers `eb8a83ae..419c360a`; the scoped
re-review covers `419c360a..42ee09f8`; `cc1f8cb3` (task 18d, 17 lines, the re-review's one
Low) was gated and checked by the controller against the reviewer's probes (t18-2, t18-2b,
wb-4 exit 0) and had no review round of its own, as the owner's rule for Low findings allows.

**Order of merging.** #64 to #242 were merged at about 15:20 UTC, before the fix wave's CI
finished, so for about 15 minutes `main` (`be376a0d`) held the two Medium findings of the
whole-branch review. #251 to #253 were merged at about 15:32 UTC once their checks passed.

- **D2e, Signal pages**: 43 stacked PRs, #64 on `main`, each based on the one before. The
  stack touches only `web/src/pages/signal/` and `web/fixtures/signal.json` (75 files,
  +16219/-8 against `eb8a83ae`). Every PR within 800 changed lines.
- PR #167 (a contributed fix from an owner-started process) was placed in the stack as task 15
  (#238): its five named commits applied, its three defects confirmed by failing tests first;
  its branch's later commits were weighed in the sweep and not applied. #167 was closed as
  superseded by the lead coordinator on the owner's instruction (a comment on the PR lists
  where each commit landed): b6c8ab1e, 364d326b, 1e7e9483, 31977282 and df133331 landed as
  task 15 (#238); 06213690 in #240; 8769cf4f and fb818546 were ruled as sweep row S12, with
  repeated statuses re-announced in #242; 16351f09 and 3dea9e97 are formatting and one test.

**Delivers.** The Signal pages from the D1 mocks on fixture data: the feed (For you, Latest,
Saved; kind tabs, search, new-stories pill, older stories), the four story kinds, the name
dialog, topic pages with follow, groups and threads (comments, replies, reactions, archived and
note threads), Share to a group, digests (feed cards and the digest page), and Settings
(Groups, Thread rules, Sources, Topics, Digests, Notifications, AI and cost; a reader sees
Topics and Notifications only). Eleven fixture scenes cover the empty, loading, unreachable,
not-checked, no-sources, nothing-followed, AI-on and AI-capped states. All state is in memory;
write controls are disabled with a visible reason; AI is off by default and its toggles are
disabled in every scene.

**Coordinator pre-check** on the final head `cc1f8cb3`, before merge: no file outside
`web/src/pages/signal/` and `web/fixtures/signal.json`; no PR over 800 changed lines; no
fetch, storage, raw HTML, suppression or number formatting added; `setTimeout` appears only
in three test files (`share.test.tsx`, `sweep-fixes.test.tsx`, `thread.test.tsx`, a 50 ms wait
each); `git merge-tree` of the head with `main` clean.

**Gates** (controller's reports; the reports are kept outside the repository, in the
coordinator's session notes folder `d2e-records/`).
- `npm --prefix web run gates`: exit 0 at `419c360a` (task 17 tip) and at `cc1f8cb3` (task
  18d), and on `42ee09f8` merged with `main` `970bc152` (merge-tree clean; D2c's chart and
  model pages included). Exit 0 on the task 18 commits `7c220f83`, `c27ade8f` and `42ee09f8`
  per the implementer. Explicit gate results are recorded for task 2 (controller gates on
  `4c2501b` exit 0; implementer on both commits), task 10 (the chained run of 10a timed out
  twice in the file check; that step alone exited 0 later), task 13 (13a and 13b never passed
  the open-from-disk step locally, headless Chrome hung under load; 13c and 13d did), task 17
  (tip gates exit 0) and task 18. For tasks 1, 3 to 9, 11, 12, 14 and 16 only the ledger's
  gates-first-pass `y` is recorded; no gate result is recorded for task 15's commits. CI
  decided the heads without a local result.
- CI: every PR head green on `gates (ubuntu-latest)`, `gates (windows-latest)` and `review`
  before its merge. On #94, #143, #144, #146, #154, #188, #193 five older duplicate runs show
  as cancelled (cancelled by the coordinator earlier); each head also has five passing checks.
  On #144 (head `596af9f`) run 43581602424 (web) failed on Windows with the
  `DevToolsActivePort` read race (EBUSY) fixed on `main` by #156, all tests before it passing,
  and run 43581601758 (python) was cancelled; neither is a failure of that PR's tree, and the
  forward push replaced both. The stack was not forwarded onto `main` after `970bc152`, so no
  CI run covered a PR head merged with later `main`.

**Reviews.**
- Task review per task, `mx-precise` (18 tasks; task 15 also reviewed #167's commits).
- Sweep discovery, `/sweep refactoring discover changed-update` (`mx-autonomous`): 22 rows;
  S1 to S8 fixed in task 17 (#241, #242); S9 not a defect (ruled); S10 reopened by the whole-branch
  review and fixed in the task 18 wave (#251 to #253); S11 deferred (back-end contract note); S13 reconciled; S14 and S15 fixed at base; S16
  platform-only; S19 to S22 (structure, duplication) go to the phase sweep; S12 and S17 are kit decisions; S18 holds owner questions.
- Whole-branch adversarial review (`mx-architect`, fresh agent, `eb8a83ae..419c360a`): FAIL,
  High 0, Medium 2 (a topic or group count badge beside a page that lists nothing; a pressed
  Save forgotten when a filter hides the card), Low 6, Info 4. One fix wave (task 18, #251 to
  #253): the reviewer's probes exit 1 before and 0 after. Scoped re-review (`mx-precise`):
  PASS, High 0, Medium 0, Low 1 (Settings panel id after a section change; fixed as 18d,
  its probes exit 0), Info 2.

**Live validation** (the D2e controller, 2026-11-14). `file://` in headed Chrome over its
debugging protocol: 51 addresses at 1440 and 1024 (one `h1`, one `main`, no horizontal
scroll, no "Not built yet", `undefined` or `NaN`, console clean); per-task interaction walks
t1 to t15 replayed on the finished stack (both at `419c360a`; all pass; t2's step names an old button label, Save
verified by pointer and keyboard); the task 18 walk, on the fix wave (tab panels, Save across search, kind
tabs, group page and scenes; filled topic pages; no overflow at 1024). Localhost in the app's
browser pane (owner-watchable): feed, thread by address, digest, Sources and AI settings,
reader Settings, name dialog, topic, unreachable feed, Share dialog error and focus return.
The content-policy and no-network checks count on `file://` only.

**Rulings** (controller, each reversible; full list in the D2e ledger):
- Mock frames are the answer key over brief prose, except three safety rules (Run once now,
  Save digest and AI toggles stay disabled with their reasons).
- Reader coherence rules tie threads, thread references, digests, Settings groups and topics,
  sources and the freshness line, AI state, Saved, and count badges to the pages they sit
  beside; ids must be non-empty and fit an address.
- Settings is one column below `xl` with the section list as a tab row; the Sources table folds
  its last-check line under the source.
- The Saved badge is null while the feed loads (departure from the mock's loading frame).
- Topic counts keep the mock's values; empty topic views are filled from the scene's stories.
- A group's unread badge is null in the 9 scenes where the group holds no thread (the mock's
  nav shows 3).
- Reaction labels are Agree, Disagree and Seen (decision 0006 ruling 19) over the mock's
  "Important" and the back end's keys.
- A reply quotes its parent's whole text (no excerpt field).
- Comment counts and reaction counts are not recomputed after an in-memory action.
- Settings freshness: `freshness.failing` is non-null exactly when a source is Failing, and
  main's line reads "Sources checked 6 min ago · 1 source failing".
- The nothing-material sample moved to 13 Nov for date order.
- S11: `top` is required on Latest and Saved views and never drawn (a back-end contract note).
- `moreMembers` on one list only is accepted (Info, parked).
- The whole-branch review was dispatched while the tip's Windows web gates sat in a 75-run
  queue (the change is front-end, not sensitive code); Windows was to be read on every head
  before the report.
- The full ledger is kept in the notes folder `d2e-records/`.

**Ledger** (D2e). All `agent=mx-feature`. fix-rounds 0 for tasks 3, 6, 9, 14, 16, 17, 18;
1 for tasks 1, 4, 5, 7, 8, 11, 12, 13, 15; 2 for tasks 2 and 10. gates-first-pass `y` for
1, 3 to 9, 11, 12, 14, 16, 17, 18; `n` for 2, 10, 13, 15. Task 9 lost three implementers to
machine restarts.

**Open for the owner.**
- Frame 8 of the Settings mock says "Nothing is spent." beside USD 6.40 (drawn at
  `main/settings/ai`): keep the mock's words or change them.
- Reactions: the back end's key for a reaction; two visibility vocabularies for groups.
- No per-issue route for earlier digest rows; AI parts are not tied to the snapshot.
- Paid-call rulings for any write control.
- Predecessor features not built: Join/Leave, member management, the note dialog, new group,
  comment edit and delete, thread chips.
- Kit changes needed: EmptyState title as `h1`; segmented Tabs and the hovered vertical tab;
  Input `sm`; StatusBadge label override; ButtonGroup radio semantics; TooltipTrigger ref;
  SlideoutMenu header close label and overlay class; a kit toggle (`parts/Toggle` is the swap
  point); Select (`aria-invalid`, long names, 36px/14px, trigger ref); `Table.Head` nowrap;
  ProgressBar `valueText` and its fill transition; Alert without a fixed role; a shared trace
  control.
- Pre-existing: `App.tsx` still lists `/signal` under `NOT_BUILT` (dead since the home route).

**Not verified.** Edge and Windows beyond CI; a screen reader (I3: a status sentence written
as a modal closes may not be spoken while the overlay exits); Chrome and Edge accessibility
trees for the tab panels, and whether the Share modal's inert outside holds in real browsers
(every reviewer probe ran in jsdom only); that any reviewer read `cc1f8cb3`; that the
re-reviewer ran the new `id-rules.test.ts` and `tab-panels.test.tsx` (it read them, it did
not run them); the layout at 1440 and 1024 after the Tabs change (the re-reviewer relied on
the implementer's screenshots); a live walk on `cc1f8cb3` or on merged `main`; reduced motion switched on; pixel comparison with
the mock frames; whether the Signal service will send the shapes the reader now requires; the
Python gates on the stack (it touches no Python; CI runs them); the push runs of the `web`
and `python` workflows on `main` `dca4981c` (queued when this entry was written), and any CI
run of a PR head merged with later `main` (the stack was not forwarded after `970bc152`);
mutation testing; the whole-branch review sampled the tests rather than auditing each.

## 2026-11-14 Design track: Model and Forecast pages and the chart kinds (step D2c)

**Merged** into `main` in stack order by the coordinator, 28 PRs as merge commits: #69,
#86, #87, #88, #89, #90, #91, #92 (the chart kinds); #216 to #225 and #227 to #236 (the
pages). `main` after the last merge: `937fa9b1`. `git diff --quiet origin/main 66cd79e0 --
web` exit 0: `web/` on `main` equals the reviewed source. The controller's top head was
`fa0cd5fd` (#236), whose tree equals the reviewed working tree `66cd79e0`
(`claude/d2c-model-287748`); its base was `8ab3f387`.

**Delivers.** The Model pages (Front, Analysis, Model/statements, Portfolio fit,
Limitations, Forecast, runs index) and the chart kinds, on fixture data
(`web/fixtures/model.json`).

**Coordinator pre-check** on the final head `fa0cd5fd`, before merge: no file outside
`web/src/pages/model/`, `web/src/components/chart/`, `web/fixtures/model.json`; no PR over
800 changed lines; no fetch, timer, storage, raw HTML or suppression added; the only
rounding added is for axis label wrapping (`Math.floor`) and one CSS width (`toFixed(2)`),
not for figures.

**Gates** (controller's report; the stack report is `stack-report.md`).
- Working tree `66cd79e0`, from `web/`, one step at a time: lint 0, format:check 0,
  typecheck 0, `vitest run --coverage --testTimeout=120000` 0 (67 files, 1371 tests),
  unused 0, duplication 0, build 0, test:scripts 0, test:file:gates 1 then 0 on rerun (the
  headless-browser timeout flake). `audit` was not run in task 16 (it ran 0 in earlier
  tasks).
- Each split branch (#216 to #236): lint, format:check, typecheck, vitest with coverage,
  unused, duplication, build all 0. test:scripts and test:file:gates 0 (after the flake
  reruns) on #218 to #225 and #228 to #236; not run on #216 and #217 (chart files only) or
  #227 (no route or fixture change). `test:file:gates` hit the 60 s browser timeout on #218
  (twice), #219, #225 and #232, each passing on rerun (load average 85 to 190).
- CI: every PR head green on `gates (ubuntu-latest)`, `gates (windows-latest)` and `review`
  before its merge. Two Windows jobs failed once and passed on one rerun with no change:
  #230, `StatementsPage.test.tsx` "describes a missing cell by its reason, shows it on
  focus, and draws it n.a., never 0" timed out at 5000 ms (5239 ms; the duplicate Windows
  job on the same commit passed); #233, the "Open from disk in Chrome (Windows)" step failed
  two kit-page checks (the invalid-field focus colour, reported as "no invalid fields"
  found, and the link button role and focus ring); cause not investigated; one rerun passed
  unchanged and every later head in the stack passed that step. On #86, #88, #89, #91, #92 five
  older duplicate runs show as cancelled (by the coordinator, earlier); each head also has
  five passing checks.

**Reviews.**
- Task reviews: `mx-precise` per task, no High or Medium open at completion.
- Sweep discovery (`/sweep refactoring discover changed-update`) on the range: 27 rows;
  confirmed defects R1, R2, R3, R4, K3, R5 fixed in task 15 (`mx-precise`: approve);
  structural S1 to S8 to the next phase sweep; S9 (205 duplicated test lines) deferred
  to the phase sweep; K6 platform-only (needs a browser); K7 to K9 deferred. Report `sweep/report.md`,
  register `sweep/register.md`.
- Whole-branch review (`mx-architect` running `adversarial-reviewer`, with
  confidence-review; rewrite-tournament as judgement only) at `09a9dd87`: 0 High, 2 Medium
  (WB-S1, WB-S2), 5 Low, 5 Info. Report `whole-branch-review.md`.
- Coordinator ruling: WB-S2 (b) to (e), the slice contract states the cell-to-mark mapping
  and the reader enforces it.
- Fix round (task 16) and scoped re-review by a fresh `mx-precise`: approve; both Mediums
  and all five Lows closed against the reviewer's probes (`wb-reader-gaps` 15/15,
  `wb-table-side` 6/6). Reports `task-16-report.md`, `task-16-review.md`. No High or Medium
  open: pass.
- The reports are kept outside the repository, in the coordinator's session notes folder
  `d2c-records/`.

**Live validation** (built `web/` with fixture `data.js`, `scratch/dist-final`).
- Headed Chrome over CDP, `file://`: all 7 routes (`#/model/runs`, front, analysis,
  statements, portfolio-fit, limitations, forecast) at 1440 and 1024: one h1, one main, no
  horizontal page scroll, page drawn, no policy violation, no console error or warning, no
  off-origin request, every Tab stop with a focus indicator (6 to 46 stops per page): 105
  PASS, 0 FAIL. Log `shots/final/walk-file.txt`.
- Headed Chrome, `file://`, statements controls: sticky first column at 1024, no page
  scroll, case switch by arrow key, Bars columns one width, statement tabs by arrow keys,
  focus ring, no console error: 7 PASS.
- Headed Chrome, `file://`, every chart (15 across Analysis, Model, Portfolio fit,
  Forecast; every chart kind): Chart to Table and back by keyboard, the Table side draws
  "n.a." where missing, arrow-key readout on path, waterfall, columns, stack and scatter,
  console clean. Probe `probes/final-charts.js`.
- App's built-in browser pane, `http://localhost:8743`: 7 routes drawn with one h1 and one
  main; Downside case chosen by pointer on Forecast; Show sources on (7 trace controls
  shown); no console error.

**Ledger** (D2c; all `agent=mx-feature`): task 1 fix-rounds 2, 1b 0, 2 1, 3 0, 4 0, 5 1,
6 1, 6b 0, 7 0, 8 1, 8b 0, walk1-fix 0, 9 1, 10 2, 11 1, 12 2, 13 2, 14 0, 15 0, 16 1,
stack-split 0. gates-first-pass `y` for all except tasks 14 and 15 (knip failed once on an
export left unused, fixed by a follow-up commit) and stack-split (the browser timeout
flake above).

**Open for the owner.**
- Show sources persistence: per page, per run or per session (now reset on every route
  change).
- 12px chart tick text against the 13px page text floor.
- Whether a run may have no limitations (now refused).
- One bad run makes every run's Model pages unreadable (the slice is read all or nothing).
- Contract formats for step 3B delivery: a segment text is exactly "<earlier or n.a.> to
  <later or n.a.>"; a headroom text starts with its first table cell then a space; every
  trace and in-library link starts with "#/"; `statements.published.href` and
  `checkFigure.href` have no address rule yet.
- The Library tab strip must link Forecast to `#/model/:issuer/:run/forecast`.

**Open Low** for the next model-pages change: the `StatementsPage.test.tsx` test above runs
close to the 5 s test timeout on Windows CI.

**Not verified.** Edge; Windows rendering beyond CI; the cause of the #233 kit-page
failure; real-browser layout for K3, K4 and K6 (no Chrome or Edge run for the sweep); R1 to
R4 against real (non-fixture) deliveries; the new task 16 tests failing at the old head (the
re-review "relied on the reviewer's probes"); the zero-exposure mark in a real browser;
whether delivery will write " to "; that the scoped re-review did not rerun the full gates,
`wb-all-missing`, `wb-observe`, the exhaustive probe or the Chrome walk; that source
`66cd79e0` was not run separately from the last branch that equals it (the chain's base
was checked at merge: the stack contained main `8ab3f387` and main moved only outside `web/`
before the merges); the published-model links from
`file://` (the fixture has `published: null`); `npm run audit` on each split branch;
`npm run gates` as one command; `LimitsChart` label placement beyond the fixture; the
reader against shapes nobody built (no fuzzing); `wb-observe` (three cases stale by design
after task 16).

## 2026-11-14 Roadmap back end: 1B facilities and forecast block, 2A store location

**Merged**, under the owner's delegation (decision 0006), each at the head named with every
check green on Ubuntu, Windows and the review job, and its source diff read by the coordinator.

| PR | Step | Head, merge | Content |
| :--- | :--- | :--- | :--- |
| #200 | 1B PR 3 | `cee12ff`, `7312294` | `model/facilities.py`: `Facility` (stated terms, one rate form, ceilings), `schedule` and `Schedule.totals`, three years of interest and repayment (575 lines) |
| #214 | 1B PR 4a | `c5018b4`, `1125c42` | `model/refusals.py` (`ForecastRefused`, `ForecastDeclined`) and `model/inputs_json.py`: the forecast block, strict JSON, the declined block (641) |
| #201 | 2A PR 1c | `23c6112`, `0e14a79` | `store/location.py`: `prepare` and `locate`, the path rules and the checks on an existing file before SQLite sees it (485) |

**Reviews.** As each controller reported.

| PR | Task reviews | Sweep discovery | Whole-branch (`mx-architect`, adversarial) |
| :--- | :--- | :--- | :--- |
| #200 | `mx-precise` and `mx-adversary` on `f099430`: Medium 1 each; one fix round; `mx-precise` re-review pass on `cee12ff` | 0 open | Pass on `cee12ff`: High 0, Medium 0, Low 3, Info 8 |
| #214 | `mx-precise` pass; `mx-adversary` Medium 1 on `037d5f6`; one fix round; `mx-precise` re-review pass on `c5018b4` | 0 open | Pass on `c5018b4`: High 0, Medium 0, Low 2, Info 7 |
| #201 | Three rounds on the task before the PR (two Sonnet, one from an `mx-autonomous` plan); on `23c6112` `mx-precise` and `mx-adversary` pass | register written | Changes required on `58519bd`: Medium 1, Low 1; scoped re-review pass on `23c6112`: High 0, Medium 0 |

- #200's Mediums: `reference_rate` accepted a set, so each year's rate followed the process
  hash seed (it now takes exactly a list or a tuple of three); a property test took its
  expected totals from the code's own rows.
- #214's Medium was in a test: the integer test could not fail, since `1 == 1.0 == True`. The
  source was right.
- **#201's fourth round is the owner's.** The whole-branch review found that `prepare` set an
  existing folder to mode 0700 when the path had `..` after a missing component. Asked
  "Authorise a fourth fix round on #201 for the `..` path Medium?", the owner answered "Yes,
  one round". The controller had proposed treating the fix as a new task; the coordinator
  declined that and asked.

**Gates and CI.** `uv run --locked python tools/gates.py` exit 0: #200 on `cee12ff`, #214 on
`c5018b4`. #201: the controller's local run exits 1 on one test
(`test_duplication_gate_arguments_are_pinned`, from a linked `web/node_modules` in its
scratch worktree); CI passes it on both runners; `tests/store` 306 passed. Mutation
(`mutmut`): #200, no survivor; #214, 220 mutants, 216 killed, 4 equivalent; #201, 355, 329
killed, the one survivor in the new lines equivalent.

**Ledger.**
- `1B-3 task=1 agent=mx-feature fix-rounds=1 gates-first-pass=y`
- `1B-4a task=1 agent=mx-feature fix-rounds=1 gates-first-pass=y`
- `2A-1c task=1 agent=mx-feature fix-rounds=4 gates-first-pass=n` (two Sonnet, one planned, one
  the owner's)

**Rulings by the coordinator.** In the plans.
- 1B: tuple fields take exactly a list or a tuple (`LIST_AS_TUPLE`), never `strict=False`;
  the predecessor differs, and `docs/legacy/ports.md` says so. The answer-key scripts are
  committed in two tests-only PRs after PR 4b and with each PR from PR 5, with a test that
  each script's output equals the committed key as parsed JSON.
- 2A: the errors-test additions move to a tests-only PR 1d-b, which merges before PR 1e is
  ready. For the transaction helper (PR 1d, not merged) the owner chose to document, not
  change, that an interrupt during a write leaves as `StoreUnusable` (asked "Authorise one
  round on the transaction helper to document and pin the Ctrl-C behaviour?", answered "Yes,
  document it"); step 3A's plan will say `StoreUnusable` always ends the run.

**Open, for the owner.**
- 1B: a facility that matures before or inside the three forecast years is assumed
  refinanced; no repayment at maturity is modelled. It is the predecessor's reading and is
  stated as a limitation per facility (ported in PR 7). The assumption is the owner's to
  confirm.
- 1C driver (#187, not merged): its third round closed three redaction leaks and opened one,
  an escaped non-ASCII Windows home in failure text. With the owner: one more scoped round, or
  a reset to round 2.
- Signal's feeds (not merged): the piece-boundary fix failed on Windows CI, which runs
  Python 3.12.10 where Ubuntu runs 3.12.14; on 3.12.10 it refused ordinary markup. The
  memory fix is split out (#215) and passes both. A rework plan is written; the round is with
  the owner. `html.parser` itself reads 25 hostile shapes differently on the two levels.
- 2A: a store error message carries the operating system's error text, and so the folder
  path; where such messages may be shown is for PR 1e's brief.
- Handoff layer, no step owns these: a second json fence under a subheading of the forecast
  section is ignored; `HandoffError` cannot be pickled; the block finder differs from the
  predecessor's on tilde, long and indented fences (same text or a refusal each time).

**Not verified.**
- #200: totals near the 38-digit limit; more than 1,000 facilities; pydantic other than
  2.13.4.
- #214: nesting beyond 66 levels, texts beyond 200,001 characters; real model-written blocks.
- #201: root; NFS; races beyond two processes; the PR 1e caller.
- For all three the merge result with `main` was not built before merging; nothing else on
  `main` touched their folders.

## 2026-11-14 Roadmap back end: 1D text and csv readers, 2B passages and Sources checks, a redactor fix

**Merged**, under the owner's delegation (decision 0006), each at the head named with every
check green on Ubuntu, Windows and the review job, and its source diff read by the coordinator.

| PR | Step | Head, merge | Content |
| :--- | :--- | :--- | :--- |
| #161 | 1D PR 2 | `3be463e`, `3fe21ed` | `sources/pages.py` (`Page`, `SourcePages`, the one cut rule) and `sources/text.py` (`text_pages`, `csv_pages`); one reason rule for errors (799 lines) |
| #198 | 2B PR 3 | `14927fb`, `dc3fe1f` | `checks/passages.py` (register ids in text, repeated limitations, the limitation helpers) and `checks/sources.py` (table, name, sha256, type); underscore boundaries in `prose.py` (776) |
| #202 | 1C, owner's review-fix process | `b9a525e`, `b20bd04` | `provider/redact.py`: a UNC home path led by forward slashes is redacted; a third pattern, the union of three redacted (177) |

**Reviews.** As each controller, or for #202 the PR body, reported.

| PR | Task reviews | Sweep discovery | Whole-branch (`mx-architect`, adversarial) |
| :--- | :--- | :--- | :--- |
| #161 | `mx-precise` and `mx-adversary` on `9ae24ed`; scoped `mx-adversary` re-reviews: `1c5c0b7` fail, `af6fe41` fail (test only), `3df9f0e` pass | 0 defects on `b463fa5` | Pass on `b463fa5`: High 0, Medium 0, Low 2, Info 4; the same reviewer then checked the two literals of `3be463e`: pass stands |
| #198 | `mx-precise` approve | 0 defects, 2 costs for the phase sweep | Pass on `14927fb`: High 0, Medium 0, Low 7, Info 8; 224 hand rows and 900 generated documents against independent oracles |
| #202 | `mx-adversary`, two rounds in the owner's process; final pass | not run | not run |

- **#161 took four fix rounds on its second task.** The third round's re-review passed and
  found one more Medium, in a test only: the memory case `text-crlf-then-control` would pass a
  reader that numbers lines by building a list of them. The fourth round is the owner's: asked
  "Authorise one test-only literal change in #161 as a fourth round?", the owner answered
  "Yes, one literal". The change needed two literals, the shape and the line number in that
  case's expected message (`87382` to `65536`); the coordinator let the pair go on its own
  responsibility and told the owner. No production line changed in rounds three and four.
- #202's first round redacted less than #191 where a forward-slash head ran into a second
  Windows head; the union of three patterns fixes that. A protocol-relative URL after a quote
  is redacted as if a path (fails closed).

**Gates and CI.** `uv run --locked python tools/gates.py` exit 0: #161 on `3be463e` (fixer's
run); #202 on its branch (its body, macOS). #198: CI only on `14927fb`, `tests/checks` 975
passed. Mutation (`mutmut`): #161 on `3df9f0e`, 633 mutants, 599 killed; not rerun after two
test-only commits. Not run on #198 (hand mutants, 3 of 16 survive) or by the coordinator on
#202.

**Ledger.**
- `1D-2 task=1 agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `1D-2 task=2 agent=mx-feature fix-rounds=4 gates-first-pass=n` (the fourth is the owner's)
- `1D-2 task=low-batch agent=mx-scaffold fix-rounds=0 gates-first-pass=y`
- `2B-3 task=1 agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `2B-3 task=assembly+rulings agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `2B-2 task=low-batch agent=mx-feature fix-rounds=0 gates-first-pass=y`

**Rulings by the coordinator.** In the plans.
- 2B: a Sources table with no rows is refused in a module that is not blocked; a register id
  in underscore emphasis is reported; the register-id reason points to the Basis line. These
  land key-first in the next checks PR.
- 2B figure reader (PR 4, not merged): the controller's rulings R37 to R53 are confirmed; they
  enter the plan with PR 4a's record.
- 1D: carried to PR 2b-1 with key rows first: two mutation survivors that are not equivalent
  (`cut_stream`'s inner `>=`; `held = 1` in `csv_pages`) and an independent reference for
  `test_cut_stream_property`, which compares `cut_stream` with itself.

**Open, for the owner.**
- 2B: the limitation key drops signs, points and currency signs, as the predecessor's does, so
  a limitation that differs from an earlier one only by `+5%` against `-5%`, or `4.5x` against
  `45x`, is refused as a repeat. Left, pinned as known false refusals; step 5A reads the key.
- 2B figure reader: `USD-5 million` and `(USD−5)` are read as 5 with no sign and no currency,
  and no finding is raised.
- 1D: a csv of blank rows takes about 1.4 s per MiB (one measurement; about 75 s at the 50 MiB
  cap, extrapolated) and no time bound is stated; for step 3A's plan.
- 1D, for other layers: invisible format characters pass the text reader; the windows-1252
  fallback gives wrong characters for other single-byte encodings; a row wider than a page is
  cut inside a cell; a chained decode error holds the whole file in its `repr`.
- #202, unchanged by it: `\\?\unc\` in lower case and `\\.\UNC\` are not matched; a lead after
  `:` (`PATH=/usr/bin://srv/...`) is not redacted.

**Not verified.**
- #161: memory and time above 4 MiB; per-case peaks on Windows and Ubuntu (CI is pass or
  fail); no real issuer file was read.
- #198: inputs above 1,000 rows, ids or items; whether the Copilot route writes the Sources
  shapes ruled on (no retained reply in the new format exists; no provider run); how 3A fills
  `accepted`, `upstream` and `other_sources`.
- #202 by this track's own reviewers; how Windows tools write `file:` URLs of UNC paths.
