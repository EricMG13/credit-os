# Verification record

One record, newest first, written only by the coordinator at merge. Keep it under 1,000
lines; trim the oldest entries (git history keeps them).

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

## 2026-11-14 Roadmap back end: the 1B forecast engine; a store hierarchy test

**Merged**, under the owner's delegation (decision 0006), each at the head named with every
check green on Ubuntu, Windows and the review job, and its diff read by the coordinator.

| PR | Step | Head, merge | Content |
| :--- | :--- | :--- | :--- |
| #194 | 1B PR 2 | `de9b901`, `2cb9537` | `model/forecast.py`: `Operands`, `Drivers`, `Shock`, `Year` and `forecast`, one case of three years; a key of 21 invented cases (755 lines) |
| #197 | 2A, owner's review-fix process | `80934ce`, `1d74a2b` | One test: the four mapped store errors are the set `store_error` returns and none is a subclass of another (20) |

**Reviews.** As the controller, or for #197 the PR body, reported.

| PR | Task reviews | Sweep discovery | Whole-branch (`mx-architect`, adversarial) |
| :--- | :--- | :--- | :--- |
| #194 | `mx-precise` pass, Low 2; `mx-adversary` pass, Low 3, Info 4; closed in one batch | 0 open | Pass on `de9b901`: High 0, Medium 0, Low 3, Info 6 |
| #197 | `mx-feature` PASS (test only, no production change) | not run | not run |

- #194's whole-branch review checked the Low batch with six mutants, all killed, and an
  independent oracle (36,000 figures over 600 cases, capped).
- Two of its Lows are parked for the next change to `forecast.py`: under a schedule the
  unused `debt_repayment` driver is still built into a `Value`, so one outside the range is
  refused; the source does not say a schedule pair is interest then repayment, interest
  before the shock.

**Gates and CI.** `uv run --locked python tools/gates.py` exit 0 on `de9b901` (controller)
and on #197 (its body, macOS). Mutation (`mutmut`) on `forecast.py`: 279 mutants, 243 killed,
36 not killed, all changes to exception message text.

**Ledger.**
- `1B-2 task=1 agent=mx-feature fix-rounds=0 gates-first-pass=y`

**Rulings by the coordinator.** In the 1B plan.
- The engine refuses nothing about meaning: a repayment driver larger than the debt gives a
  negative closing debt. PR 4b's schema check refuses, per case, a block whose
  `debt_repayment` drivers pass that case's base debt on the running sum, with its own
  refusal kind; equal is allowed, a missing debt is not read as zero and refuses nothing, a
  negative driver is not refused by this rule. The scheduled path is decided in PR 6.
- PR 4 is split into 4a (refusal types, the forecast block, strict JSON, the declined block)
  and 4b (schema and scale). `ForecastRefused` derives from `Exception`; integers in the
  block hold at most 15 digits and the block at most 200,000 characters; a repeated key is
  compared after escape decoding.

**Not verified.**
- #194: `Overflow` and `Underflow` on a ratio inside `forecast`; exception message text;
  driver ranges and the sign of closing debt and cash (later PRs); the merge result with
  `main` was not built before merging (no commit since its base touched the model).
- #197: a new mapped class with no new code in the error key would not be seen. No test
  applies to a test-only change.

## 2026-11-14 Roadmap back end: 1B arithmetic, 2A codecs, 2B prose checks, the home-directory redactor

**Merged**, under the owner's delegation (decision 0006), each at the head named with every
check green on Ubuntu, Windows and the review job, and its diff read by the coordinator.

| PR | Step | Head, merge | Content |
| :--- | :--- | :--- | :--- |
| #182 | 1B PR 1b | `0944788`, `cd3a6a0` (squashed) | `model/arithmetic.py`: exact sum, difference and product; the rounded ratio; `half_unit`, `beyond_rounding` (675 lines) |
| #169 | 2A PR 1b | `4aa92d5`, `0405fc4` | `store/codec.py`: money, time and event-detail codecs (675) |
| #177 | 2B PR 2 | `1856dd3`, `4c6af80` | `checks/prose.py`: the two Bottom line checks and six text checks (760) |
| #171 | 1C PR 2d | `02d244c`, `5407308` | `provider/redact.py`: the home-directory rewrite; closes the open Medium M2 of #36 (195) |
| #191 | 1C, owner's review-fix process | `52adbca`, `cdd6949` | `provider/redact.py`: a written-out apostrophe no longer ends a Windows user name (83) |

#182 was squashed at its controller's request: one commit on the branch fails a key row that a
later one corrects.

**Reviews.** Verdicts and counts are as each controller, or for #191 the PR body, reported.

| PR | Task reviews | Sweep discovery | Whole-branch (`mx-architect`, adversarial) |
| :--- | :--- | :--- | :--- |
| #182 | `mx-precise` pass; `mx-adversary` Medium 1, fixed, re-review pass | 0 open, 2 deferred | Pass on `3620669`: High 0, Medium 0, Low 4, closed in `0944788` |
| #169 | `mx-precise` and `mx-adversary` before the split, Medium 1 each, fixed, re-review PASS | 0 defects, 0 costs | PASS on `4aa92d5`: High 0, Medium 0, Low 2, Info 4 |
| #177 | `mx-precise` approved after one batch | 0 defects, 3 costs deferred | Pass on `1856dd3`: High 0, Medium 0, Low 6, Info 6 |
| #171 | `mx-adversary` check of the one authorised change: PASS, Low 2 | 0 defects | PASS on `02d244c`: High 0, Medium 0, Low 2, Info 3 |
| #191 | `mx-adversary`, five rounds in the owner's process; final PASS against `5407308` | not run | not run |

- #182's Medium: `product` made text of an unbounded integer and met Python's 4,300-digit
  limit. It now strips zeros and tests the 38-digit bound on integers, and never changes the
  interpreter's limit.
- #169's first push failed on Windows only: two test ids of 100,000 characters passed
  Windows' 32,767-character limit on an environment variable, where `pytest` keeps the id.
  The same cause failed 1D's #161 once.
- #171 is the one further round the owner authorised. One Low is a difference against the
  `main` before it: an empty-named home glued to a second home after a written-out `\n`,
  `\r` or `\t` keeps the second name (657 of about 8 million sampled strings).
- **Correction to the entry below.** #160 and #191 came from a review-fix process the owner
  runs in agent worktrees, not from the Signal or 1C controllers (asked whether those PRs were
  from a process they started, the owner answered "Yes, mine"). The adversarial pass recorded
  for #160 is that process's. #191 redacts the union of its pattern's matches and those of
  the pattern #171 left, so it cannot redact less than #171 did.

**Gates and CI.** As each controller reported. `uv run --locked python tools/gates.py` exit 0:
#182 on `3620669`; #171 on `02d244c` (2,426 passed); #177 on `3eb0a6a` (its last commit adds
four key cases); #169 on the same store files at `3707bf8` (its controller's scratch worktree
failed one unrelated path test). Mutation (`mutmut`): #171, 1,438 mutants, 1,428 killed, 10
equivalent; #169 at `959ab82`, 192, 183 killed, 9 equivalent; #182 at `3620669`, 43 not killed
(33 change message text only, 7 equivalent, 3 timeouts). Not run on #177 (not sensitive code)
or by the coordinator on #191.

**Ledger.**
- `1B-1b task=2 agent=mx-feature fix-rounds=1 gates-first-pass=y`
- `2A-1b task=1 agent=mx-feature fix-rounds=1 gates-first-pass=n`
- `2A-1b task=ci-fix agent=mx-scaffold fix-rounds=0 gates-first-pass=n/a`
- `2B-2 task=1 agent=mx-feature fix-rounds=0 gates-first-pass=n`
- `2B-2 task=assembly agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `1C-2d task=1 agent=mx-feature fix-rounds=0 gates-first-pass=y` (the owner-authorised round)

**Rulings by the coordinator.** In the plans. The ones the owner may want to see:
- 2B figure reader (PR 4, not merged): its first review found the patterns carried from the
  predecessor read money wrongly (`(USD 1,250)` as positive; `.5%` as 5%; `A$5m` as USD;
  `$5mn` with no unit). Ruled: a currency or scale that is written but not recognised matches
  nothing held, and only a figure written with none can match any; the reader reads every
  currency code the form check accepts; U+2212 is a minus.
- 1D: the measured bounds of the text readers are stated as measured: csv 17 times the file
  plus 64 MiB, text 12 times plus 4 MiB, HTML (design) 4.5 times plus 6 MiB, with the 50 MiB
  cap kept. Step 3A may set a lower cap for text and csv.
- 2A: a time is an aware datetime or epoch seconds as an int or float, never a bool; the
  coordinator's earlier "never a float" was wrong and is corrected in the plan. The store does
  not refuse a state folder owned by another user.
- 1B: the kernel sets no cap on the number of operands; the calculate tool's 128 is 3A's.

**Open, for the owner.**
- Signal's feeds (six PRs, not merged): the fresh whole-branch review found the parser's peak
  at 79.4 MiB on one element with many prefixed attributes, and 65.1 MiB on a feed of
  namespace declarations that is then read, against the 64 MiB bound. A fourth fix round is
  running, which the Signal controller reports the owner ordered.
- Signal's feed view, from the predecessor: the For you page and the new-story count cost
  stories times memberships (about 0.6 s and up to 2.5 s at 20,000 stories and 500 groups);
  the count ignores filters and counts by id while pages order by date.
- The work PC's exact Python 3.12 patch level: the HTML reader and the feed text reader follow
  3.12.14's `html.parser`.

**Not verified.**
- #191 by this track's own reviewers; a forward-slash network path and a home glued after a
  word character are still not redacted (its body).
- 2A: no caller reaches a real column or `CHECK` until PRs 2 and 3. 2B: timing above 10,000
  characters; no retained reply in the new format exists.
- 1B: the full gates were not rerun locally on `0944788`; mutation not rerun after the last
  commit.
- Every memory figure above is `tracemalloc` on macOS; nothing above 4 MiB was run for the
  readers.

## 2026-11-14 Roadmap back end: first PRs of 1B, 2A and 2B; 1C PR 2c; a Signal fix

**Merged**, under the owner's delegation (decision 0006), each at the head named with every
check green on Ubuntu, Windows and the review job, and its diff read by the coordinator.

| PR | Step | Head, merge | Content |
| :--- | :--- | :--- | :--- |
| #147 | 1C PR 2c | `d861baa`, `1c811da` | `provider/`: an exact redaction value is also matched as JSON writes it; compactions read from events (327 lines) |
| #163 | 1B PR 1 | `f6328c5`, `791c05d` | `model/value.py`: `Value`, `Missing`, the two contexts, operand text, amount text (620) |
| #162 | 2A PR 1a | `a0494c2`, `f46eca6` | `store/errors.py`: the typed errors and the SQLite error mapping (268) |
| #157 | 2B PR 1a | `30b2c25`, `a63898d` | `checks/`: `Finding`, `CheckContext`, the text views (529) |
| #170 | 2B PR 1b | `f52241f`, `77d000a` | `checks/`: the seven structure checks and `check_handoff` (624) |
| #160 | Signal S-2b | `bd608b0`, `bdc441e` | `signal/fetch.py`: a lookup thread that cannot be built frees its slot (26) |

**Reviews.** Verdicts and counts are as each controller reported; the coordinator read the
diffs and the checks.

| PR | Task reviews | Sweep discovery | Whole-branch (`mx-architect`, adversarial) |
| :--- | :--- | :--- | :--- |
| #147 | both tasks approved for what merged; every finding was in the home-directory part, since removed | 0 defects at `313faa0`, 4 costs; not rerun after the removal | PASS on `d861baa`: High 0, Medium 0, Low 3, Info 5 |
| #163 | `mx-precise` pass; `mx-adversary` Medium 2, fixed, re-review pass | 0 open, 1 deferred | Changes required on `d0214a8`: Medium 1; fixed in the key only; `mx-precise` re-review pass on `f6328c5` |
| #162 | `mx-precise` Medium 1 and `mx-adversary` Medium 1 (before the split), fixed, re-review PASS | 0 defects, 0 costs | PASS on `a0494c2`: High 0, Medium 0, Low 1, Info 3 |
| #157 | `mx-precise` approved | 1 Low defect, fixed test first | Medium 1, Low 4 on `457915d`; fixed test first; re-review pass on `30b2c25` |
| #170 | `mx-precise` Medium 1, fixed, re-review approved | 2 defects fixed test first, 1 cost deferred | Medium 1, Low 5 on `661a5bf`; fixed test first; `mx-precise` re-review pass on `f52241f` |
| #160 | `mx-adversary` PASS, no finding in the diff | not run (a 26-line review fix) | not run |

- #163's Medium: the key's operands were carried from a predecessor test table and could be
  traced to a run of a public case. The plan's ruling 9 forbids that; its answer key 4 had
  called those tables synthetic, which was the coordinator's error. The key now holds invented
  figures. The earlier commits, with the carried figures, are in the merged history.
- #163's task Mediums: the two number contexts inherited Python's default context, and the
  test could not see it. Each context is now built with every setting stated.
- #170's Medium: two `table-id` tags on one line were read as one register, so a repeated id
  there was accepted. #157's: the context's default mappings could still be changed.
- #162's Mediums: `StoreRefused` was not pinned as a `StoreError`; a very large integer in a
  detail left the codecs as a bare `ValueError` (the codecs land in PR 1b).

**The home-directory redactor (1C).** Its fix failed review three times, the limit (global
rules 1). The third round followed the coordinator's rule that the redactor fails closed and
still lost a second home path on a line that mixes a POSIX home with a backslash-led one, a
case `main` handles. The rewrite was taken out of #147, so `home_paths` on `main` is unchanged
and the open Medium M2 of #36 stays open. The owner authorised one more round (asked
"Authorise one more scoped fix round for the 1C home-directory redactor?", answered "Yes, one
round"): the reviewer's one-line change, key rows first, an adversarial check of that change
only, as its own PR (#171, a draft at this entry). Nothing further is authorised.

**Gates and CI.** As each controller reported. `uv run --locked python tools/gates.py` exit
0: #147 on `d861baa` (1,857 passed); #163 on `d0214a8` (the last commit changed the JSON key
only); #162 on `a0494c2`; #157 on `30b2c25`; #170 and #160 on their heads. CI on #162 printed
SQLite 3.53.1 on Ubuntu and 3.49.1 on Windows, both above the plan's 3.37 floor. Mutation
(`mutmut`): #147, 1,438 mutants, 1,428 killed, 10 equivalent; #163 at `d8f925e`, 204, 153
killed, 51 judged equivalent (45 change message text only); #162 at `959ab82`, 192, 183
killed, 9 equivalent. Not run on #157, #170 (not sensitive code) or #160.

**Ledger.**
- `1C-2c task=1 agent=mx-feature fix-rounds=3 gates-first-pass=y` (all three on the part removed)
- `1C-2c task=2 agent=mx-feature fix-rounds=0 gates-first-pass=n`
- `1C-2c task=remove-home agent=mx-scaffold fix-rounds=0 gates-first-pass=n`
- `1B-1 task=1 agent=mx-feature fix-rounds=1 gates-first-pass=y`
- `2A-1a task=1 agent=mx-feature fix-rounds=1 gates-first-pass=n`
- `2B-1 task=1 agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `2B-1 task=2 agent=mx-feature fix-rounds=1 gates-first-pass=y`
- `2B-1a task=sweep-defect agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `2B-1a task=review-fix agent=mx-feature fix-rounds=1 gates-first-pass=y`
- `2B-1b task=assembly agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `2B-1b task=sweep-defects agent=mx-feature fix-rounds=1 gates-first-pass=y`
- `2B-1b task=whole-branch-fix agent=mx-feature fix-rounds=1 gates-first-pass=y`

**Rulings by the coordinator.** In the plans. The ones the owner may want to see:
- 1C driver: closing a session that does not answer in 5 seconds, or whose queued events
  cannot be read, returns one compaction marked failed with no charge known; the predecessor
  returned nothing. A leftover event that carries usage is reported the same way. Events from
  a sub-agent keep their figures and make the reply not ok; the predecessor dropped them.
- 1D readers: pages are consecutive slices that rejoin to the text exactly, so page numbers
  differ from the predecessor's for the same file. A csv with semicolons is read as one cell
  per row. The HTML reader must hold a stated peak-memory bound, by a committed test.
- 1B: every key and fixture figure is invented by the controller.
- 2A: the plan's PR 1 is three PRs. 2B: PR 1 was two; PR 4 will be two.

**Not verified.**
- Any live event stream (1C); whether the runtime also reports usage for a compaction request,
  which would count it twice.
- 2A: `store_error` and `safe_text` have no caller until PR 1c, so "a SQLite error never
  leaves the store" is untested until then; the work PC's SQLite version.
- 2B: nothing was checked against a retained reply in the new format (none exists); no
  property test for the structure checks.
- 1B: builds without the C decimal module beyond one reviewer run; mutation was not repeated
  after the last test and key commits.
- #160: a real failure to create a thread (simulated only). Three leftovers in the same
  function are unchanged: a slot leaks if the outcome record cannot be built or on an
  interrupt, and a start that fails after the thread began would release twice.

## 2026-11-14 Roadmap back end: 1D PR 1e, Signal's fetch, and CI runs per pull request

**Merged**, under the owner's delegation (decision 0006), each at the head named with every
check green, and its diff read by the coordinator.

| PR | Step | Head, merge | Content |
| :--- | :--- | :--- | :--- |
| #135 | 1D PR 1e | `a6b53ae`, `c54397a` | `sources/`: the two untyped exits are typed, a failed close is reported, eight more characters refused in a name (325 lines) |
| #148 to #152 | Signal S-2b | `9f8d185`, `6c47a1b`, `5ed09aa`, `1fbb3e9`, `eb83e0a`; last merge `8978b9d` | `signal/fetch.py` (473 lines) and its tests; `signal/netpin.py` gains a limit on bytes received per connection. Five stacked PRs, each retargeted to `main` and under the 800-line cap |
| #153 | CI | `28dfa17`, `17809de` | Both workflows: a newer push to a pull request cancels that pull request's older run; each push to `main` has its own group |

After the last merge `src/credit_os/signal` and `tests/signal` on `main` equal the reviewed
head `eb83e0a` (`git diff --stat eb83e0a origin/main -- src/credit_os/signal tests/signal`,
empty).

**Reviews.** Verdicts, counts and the figures under them are as each controller reported;
the coordinator read the diffs and the checks, not the review reports' evidence.

| PR | Task reviews | Sweep discovery | Whole-branch (`mx-architect`, adversarial) |
| :--- | :--- | :--- | :--- |
| #135 | `mx-precise` PASS, Low 1; `mx-adversary` PASS, Low 1; both at `7ab69d6`, both fixed in `a6b53ae` | 0 defects introduced; 1 Low that predates the diff | PASS on `a6b53ae`: High 0, Medium 0, Low 0, Info 5 |
| #148 to #152 | `mx-precise` and `mx-adversary` PASS at `6c47a1b` | 1 Low defect (a redirect location with a tab), fixed in `1fbb3e9` | FAIL on `1fbb3e9`: Medium 1, Low 5; fixed test first; `mx-adversary` scoped re-review PASS on `588f5c6`, Low 2, fixed in `eb83e0a` |
| #153 | batched `mx-feature`: FAIL on `e90efa0`, Medium 1; fixed; scoped re-review PASS on `28dfa17` | skipped (config) | skipped (config) |

- Fetch's Medium: a chunk size of -1 made `http.client` read to the end of the connection, so
  the 2 MiB body cap did not hold (194 MiB was read). The connection now counts what it
  receives after decryption and refuses the byte after 8 MiB; a test over a real TLS
  connection on loopback is committed.
- #153's Medium: with one group for all pushes to `main`, a waiting run would have been
  replaced by a newer one and that merge commit left without a result. The group is the
  pull request's ref for a pull request and the commit otherwise. Seen working on #153
  itself: its second push cancelled the first push's two runs.
- `a6b53ae` and `eb83e0a` are Low batches after the last review, with no review round of
  their own (global rules 1). The 1D controller checked `a6b53ae` itself because a restart
  cut off its implementer after the commit.

**Gates and CI.** `uv run --locked python tools/gates.py` exit 0, each by its controller:
#135 on macOS at `a6b53ae`; fetch at `eb83e0a`, with the web gates and `mypy --platform
win32`. CI green on Ubuntu, Windows and the review job on every merged head (#135: 1,780
passed on Ubuntu, 1,765 on Windows). Mutation: #135 with `mutmut` at `7ab69d6`, 389 of 404
killed, 13 equivalent, 2 closed by tests added in `a6b53ae`; fetch by hand mutants only, 58
of 59 non-equivalent caught at `588f5c6`, the last by a test in `eb83e0a`.

**Ledger.**
- `1D-1e task=1 agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `1D-1e task=2 agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `1D-1e task=3 agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `1D-1e task=low-batch agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `S-2b task=1 agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `S-2b task=2 agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `S-2b task=3 agent=mx-feature fix-rounds=1 gates-first-pass=y`
- `CI-153 task=1 agent=mx-scaffold fix-rounds=1 gates-first-pass=n/a`

**Incident.** A fetch re-review probe started threads until the system refused, and the Mac
reached its 16,384-thread limit and panicked four times; the Signal controller re-ran that
agent after each restart without reading what it ran. The owner's rule (global rules 1,
2026-11-14) now caps any such loop at 1,000 and has the failure simulated. The probe is
capped; a second one that opens sockets until a connect fails is not to be run. The 1C, 1D,
2A and Signal controllers each report their other probes and committed tests within the
rule; the coordinator read the capped probe and the committed fetch tests, not the rest.
About 100 CI runs then queued behind duplicate pushes of the design track's stacks, which is
what #153 answers.

**Rulings by the coordinator.**
- 1D: a name that uses U+FF0F as a slash stand-in (seen in some Japanese and Chinese file
  names) refuses its folder, as do the other seven characters. PR 2's first task makes
  `cannot read (None)` name the error's class and corrects a comment in `source_path`.
- For the first layer that stores or shows a `SourceError` (2A's brief, 3A's plan): it keeps
  the error's notes, where a failed close is recorded, and decides whether the absolute path
  in the message is kept.
- Signal's ingest: one source at a time; a refusal for want of a lookup slot does not count
  against the source; a `FetchRefused` is not kept (about 8 MiB each through its traceback).
- 1C: the redactor's third and last fix round fails closed. Where the end of a home
  directory name is not decided by a separator, it redacts to the end of the string or line.
- 2A and 2B each split their PR 1 in two to hold the 800-line cap, as their plans allow.

**Accepted limits (fetch).** A flood of headers within `http.client`'s own limits peaks near
50 MiB. The lookup limit of 8 is for the whole process, so 8 stuck lookups refuse a healthy
host until they return. TLS record overhead and the handshake are not counted. A 2 MiB body
sent in 1-byte chunks is refused.

**Not verified.**
- Fetch against a real resolver, a public certificate authority or real DNS; a real refusal
  to start a thread (simulated only, by the owner's rule); other CPython 3.12 patch releases
  and OpenSSL builds; `mutmut` on fetch.
- 1D: nothing ran on Windows outside CI; a close failure is simulated, none from a real
  network share; look-alike characters beyond the eight still pass; `mutmut` on `a6b53ae`.
- #153: GitHub's replacement of a waiting run in a shared group was reasoned from its
  documentation as remembered, not observed. Observed after the change: the five fetch
  merges landed within a minute and each merge commit got its own `python` run, none
  replaced; their results were not yet in when this entry was written.

## 2026-11-14 Design track: run pages (step D2d) and the shared changes for D2b to D2e

**Merged**, on the owner's instruction (merge when the review has no High or Medium finding
and CI is green):

- **D2d, run pages**: 14 stacked PRs in order, each retargeted to `main`: #55, #56, #66,
  #67, #95, #96, #97, #98, #99, #111, #112, #113, #120, #122 (merge `e0bc511`). After the
  last merge `web/src/pages/run` and `web/fixtures/run.json` on `main` equal the reviewed
  head `998b88f` (`git diff --quiet origin/main 998b88f -- web/src/pages/run
  web/fixtures/run.json`, exit 0). The stack touches nothing else (31 files, +5529/-9).
- **Shared changes**, each on its own PR because no page group may edit a shared file:
  #51 `react-is` 19.3.0 as a direct dependency matching React (decision 0010, merge
  `c814861`); #52 the committed-fixtures test compares `data.js` with the fixtures
  (`59b0570`); #60 `Route` gains `home` and `layout: "bleed"` (`2491c3b`); #62 `ChartFrame`
  `subtitle` and `actions`, and `ChartTable` (`7ca8a23`); #73 the kit `Button` takes `href`
  and renders a link (`ab56092`).

**Delivers.** The run pages from the D1c mocks on fixture data: the five-step start flow,
run progress with its 22 module steps, activity, the unreadable and no-run states. A page
group can now own its bare address and draw edge to edge; a kit button can be a link.

**Gates.** `npm --prefix web run gates` exit 0 at `998b88f` and at `8199e37` (#73), and on
`e2de49f` (#60, before its fix round). #62's full local gates did not finish under load; CI
was its gate of record. CI green on Linux and Windows for every PR at merge. One Windows
job on #111 failed once with `EBUSY` in `web/scripts/kit-chrome.mjs` and passed on re-run
(the read race; its fix is PR #156, not merged at this entry).

**Reviews.**
- D2d: task review per task (`mx-precise`; `mx-feature` for the last batch). Sweep discovery
  (`mx-autonomous`, `2491c3b..068bfcb`): 17 rows; 6 defects and the Medium gap fixed in #120
  and #122, each test first; 8 structural rows and one Low gap go to the phase sweep.
  Whole-branch adversarial review (`mx-architect`, fresh agent, `2491c3b..998b88f`): PASS,
  High 0, Medium 0, Low 8, Info 4.
- #60: task review and adversarial review both Needs fixes (a declared home broke shared
  tests; a non-literal home skipped its visit); one fix round with rulings R1 to R4; scoped
  re-review pass. 6 Low mutant survivors ride with the next shell change.
- #62: adversarial pass, no High or Medium at merge.
- #73: task review Needs fixes (Medium 1), fixed in `8199e37`; adversarial review PASS,
  High 0, Medium 0, Low 2 (dead `data-disabled:` classes; a Tab leg of the Chrome check that
  cannot fail), Info 3.
- #51: batched review (config and a decision record); #52: task review (`mx-precise`).
- #52, #60, #62, #73 had no sweep discovery of their own (coordinator's ruling for small
  shared PRs); they go to the phase sweep.

**Live validation** (owner, 2026-11-14: every page build is walked in a real browser). D2d:
22 addresses at 1440 and 1024 on `file://` in headed Chrome, and on localhost in the app's
browser pane; flow, modal, groups, links, focus rings, motion, console and policy. #73: 22
checks in Chrome 157.

**Rulings** (coordinator, under the owner's delegation; each reversible):
- Five positioned-row chart kinds are drawn without Recharts: a departure from decision
  0003 ruling 2, for the owner.
- The rail stays Model-current on `/model/…` routes; pages that draw their own header use
  `layout: "bleed"`, restore their padding and draw the one `h1`.
- Pieces only one group needs are built in its folder as kit candidates. The sources
  switch, trace control, baseline tokens and `GapPanel` title (D2b and D2c each hold a
  working copy) are consolidated at the phase sweep, not mid-build.
- Focused invalid field: `focus` ring at 2px. Disabled input and select: 50% opacity.
- Analyst file names are exempt from the module-code check on run pages.

**Ledger** (D2d). Tasks 1 to 11, all `agent=mx-feature`: fix-rounds 0 for tasks 1, 2, 4, 8,
9, 10; 1 for tasks 3, 5, 6, 7, 11. gates-first-pass `y` for tasks 2 to 8 and 10; `n` for
task 1 (a shared test), task 9 (a cast in a new test) and task 11 (the browser timeout
under load).

**Open for the owner.** The toggle's source (run `npx untitledui@latest add toggle`, or
build on React Aria); a licence notice for copied Untitled UI and HyperUI code; the faint
selected segment and hovered tab; the Recharts departure above; pre-existing: scroll
position and focus kept across routes, `render` called as a function, no error boundary.

**Not verified.** Edge and Windows beyond CI; a screen reader; reduced motion switched on;
pointer hover states; whether delivery (3B) or the service (5C) will send the shapes D2d's
8 Low findings describe; the full gate on #73 merged with current `main`, locally (CI ran
it). D2b, D2c and D2e are not merged and are not covered by this entry.
