# Verification record

One record, newest first, written only by the coordinator at merge. Keep it under 1,000
lines; trim the oldest entries (git history keeps them).

## 2026-11-14 Roadmap back end: 1C PR 2 and Signal's network pin

**Merged**, under the owner's delegation (decision 0006), each at the head named with every
check green, and its diff read by the coordinator.

| PR | Step | Head, merge | Content |
| :--- | :--- | :--- | :--- |
| #63 | 1C PR 2 | `b3d2b7f`, `ee28e4a` | Compaction outcome, event id and replacement link; `close()` returns compactions; float tool arguments (339 lines) |
| #74 | Signal S-2a, 1 of 2 | `110b273`, `6489c01` | `signal/netpin.py`: public-address check and pinned https connection, carried (785 lines) |
| #75 | Signal S-2a, 2 of 2 | `ba60879`, `94c0dc3` | Review fixes: explicit ranges, strict X.509, the pin re-checks its address (380 lines) |
| #68 | records | `16a1fc6` | The entry below this one and the 1A and 1D plan rules |

**Reviews.**

| PR | Task reviews | Sweep discovery | Whole-branch (`mx-architect`, adversarial) |
| :--- | :--- | :--- | :--- |
| #63 | `mx-precise` approved; `mx-adversary` PASS; scoped `mx-adversary` on the replacement link PASS, Info 3 | 0 confirmed defects | PASS on `b838513`: High 0, Medium 0, Low 4, Info 5 |
| #74, #75 | `mx-precise` pass; `mx-adversary` Medium 1 (the handshake could take twice the time left; fixed in #74), Low 4, Info 6, re-review closed | no defect outside security | FAIL at `a0f3adc`: Medium 1, a test gap on what `connect` hands to the socket budget |

**The Medium on #75, and a second round.** The whole-branch Medium was closed by tests against
the reviewer's four mutants, and no reviewer saw that fix. The coordinator dispatched a scoped
`mx-adversary` re-review: FAIL, the gap was half closed. Four more mutants survived, one of
them the per-operation timeout and the total deadline swapped, which would refuse every fetch
in production. One test row was added (`ba60879`); the coordinator ran the reviewer's probe on
that head: 21 of 21 mutants as expected, no survivor. The first fix (`a0f3adc..16d20ec`) also
deleted the unused `_BudgetedSocket.send` and `.recv` and added `close()` to `ResponseLike`; the
re-review read that diff and found nothing at Medium or above. The second changed tests only.
The re-review's report was returned as text and is not saved as a file; its two probes are.

**Gates and CI.** `uv run --locked python tools/gates.py` exit 0, each by its controller: #63
on `b3d2b7f` (1,030 passed, coverage 100%), #75 on `ba60879`; `npm --prefix web run gates`
exit 0 for the Signal PRs. CI green on Ubuntu, Windows and the review job on each merged head; #75's
run on `ba60879` after it was retargeted to `main` is the one the coordinator read before merging. Mutation on #63 (`mutmut`, `src/credit_os/provider/`):
719 mutants, 710 killed, 9 equivalent. Signal: hand mutants only.

**Ledger.**
- `1C-2 task=1 agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `1C-2 task=1-lows agent=mx-feature fix-rounds=0 gates-first-pass=n`
- `1C-2 task=1b agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `S-2a task=1 agent=mx-feature fix-rounds=1 gates-first-pass=y`
- `S-2a task=2 agent=mx-feature fix-rounds=2 gates-first-pass=n`

**Rulings by the coordinator.** In the 1C plan and the addendum to decision 0009. The ones a
later step depends on:
- A completed compaction names the unfinished one it replaces only when exactly one is
  outstanding. Step 3A drops a replaced entry only when it is unfinished and its completing
  entry is present; the completing entry's own charge then counts, and an unknown one keeps
  the spend unknown.
- In SDK 1.0.8 a call routed to another model that succeeds first time gives no signal; the
  routing refusals can only be read from a failed call.
- Signal's fetcher tests go through the real pinned connection at least once.
- A Signal ready message says which review ran on which head, and whether any fix after the
  last review was itself reviewed.

**Not verified.**
- That runtime 1.0.108 never runs two compactions at once, and that a complete always follows
  its own start. Nothing in `provider/` has run against a live session.
- `netpin.py` on CPython 3.12.0 to 3.12.3 (simulated by patched tables), against a public
  certificate authority, or against a corporate inspection root on the work PC.
- `mutmut` on the Signal PRs. `confidence-review` and `rewrite-tournament` were not run on
  their diff.
- The Signal session reported 14 probes at exit 0 after its first fix round with wrong exit
  codes (a shell loop printed another command's status); it re-ran them through the
  reviewer's seam and reports every result holds. The coordinator did not re-run those.

## 2026-11-14 Roadmap back end: 1A PR 4 and 1D PR 1b-names

**Merged**, under the owner's delegation (decision 0006), each at the head named with every
check green, and its diff read by the coordinator.

| PR | Step | Head, merge | Content |
| :--- | :--- | :--- | :--- |
| #53 | 1A PR 4 | `41edd3d`, `d21b706` | Format detection, reader passages, Basis lines, earlier-format reader summary (741 lines) |
| #61 | 1D PR 1b-names | `3b5dec2`, `7edca04` | A reason per name rule, wider refusals, length caps, name echo bounded at 120 characters (285 lines) |
| #54 | records | `69e862a`, `50d6b4b` | The entry below this one and the 1A and 1C plan rules |

**Reviews.**

| PR | Task reviews | Sweep discovery | Whole-branch (`mx-architect`, adversarial) |
| :--- | :--- | :--- | :--- |
| #53 | `mx-precise`: Basis lines needed fixes, Medium 2 (a bare `.pdf` read as a source; a page number over 4,300 digits raised), closed in one round and re-reviewed; reader approved | no confirmed defect; Low 1, Info 8 | PASS on `aa3aa93`: High 0, Medium 0, Low 4, Info 9. Two batches followed with no review round |
| #61 | `mx-precise` PASS, Info 1; `mx-adversary` PASS, Low 3, Info 3 (both on the branch before it was split from #59 and before the echo bound) | 0 confirmed; 1 measured structural, 2 evidence gaps | PASS on `e5f8315`: High 0, Medium 0, Low 2, Info 6. One test row followed |

#53's answer keys were generated by the controller's script, so each task reviewer wrote its
own reader from the fixture bytes: no disagreement with the key or the code on the 25 full
fixtures and the 11 Basis lines. #61's adversary ran 4.78 million names against an independent
oracle at `7d22e09`, before the echo bound: each was refused with `SourceRefused` or returned unchanged.

**Gates and CI.** `uv run --locked python tools/gates.py` exit 0, each by its controller: #53
on `41edd3d` (946 tests, `credit_os.handoff` coverage 100%), #61 on `3b5dec2` (macOS). CI green
on Ubuntu, Windows and the review job on both heads. Mutation on #61 (`mutmut`, at `e5f8315`):
86 of 86 killed.

**Ledger.**
- `1A-4 task=1 agent=mx-feature fix-rounds=1 gates-first-pass=n`
- `1A-4 task=2 agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `1A-4 task=3(end batch) agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `1A-4 task=4(end batch 2) agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `1D-1b task=1(name rules) agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `1D-1b task=low-batch-1 agent=mx-scaffold then mx-feature fix-rounds=0 gates-first-pass=n`
  (`mx-scaffold` reported BLOCKED)
- `1D-1b task=echo-bound agent=mx-feature fix-rounds=0 gates-first-pass=n`

**Rulings by the coordinator.** In the 1A and 1D plans. The ones a later step depends on:
- Real replies cite a source named `context`, with no extension; #53 reads such an item as
  plain text. 1A PR 5 matches Basis items against the names in the document's own Sources
  table.
- The earlier format's bracket citations are not read. Delivery draws no earlier-format
  paragraph unless a reader for them is added to `handoff/` first.
- A reader summary that is present but unreadable is an explicit gap, never absent. 20 of the
  52 retained earlier-format replies have one; all 20 are first drafts.
- A source name that is or passes through a symbolic link is refused (in #59, not yet merged).
  `COM0` and `LPT0` join the reserved names in 1D PR 1c.
- pydantic's error output carries the whole refused name of a pin; the first layer that loads
  pin records bounds it.

**Not verified.**
- No JavaScript engine was run: the predecessor's Basis reader was compared through a Python
  port and by reading.
- A reviewer's mutant probe on #53 no longer runs after the end batch restructured `basis.py`;
  the kill of its two surviving mutants rests on the seven new rows.
- Every new-format real reply comes from one run. The reason for the empty reader summary
  heading was read in 2 of the 20 drafts.
- #61: nothing on a real Windows file system beyond the CI run; mutation was not rerun on
  `3b5dec2` (one test row after `e5f8315`); the task reviews ran before the echo bound.
- How the work PC renders `…` in a message.
- `npm --prefix web run gates` did not run for either PR; neither changes a web file.

## 2026-11-14 Roadmap back end: 1A PR 3, 1C PR 1b and step 0C part 2

**Merged**, under the owner's delegation (decision 0006), each at the head named with every
check green, and its diff read by the coordinator.

| PR | Step | Head, merge | Content |
| :--- | :--- | :--- | :--- |
| #47 | 1A PR 3 | `e29f1f2`, `9757bbd` | Front matter, section tree, six-section skeleton check, `parse` (655 lines) |
| #49 | 0C part 2 | `8a6f39a`, `9a85025` | Web duplication scans `web/src` only; open-from-disk named runs in Edge and Chrome on Windows CI |
| #50 | 1C PR 1b | `2bc089f`, `89d9056` | Canned adapter; `Compaction` and `Reply.compactions` (800 lines, at the cap) |
| #46 | records | `52fba33`, `52d4481` | The entry "1A PR 2 and 1D PR 1" and the 1A and 1D plan rules |

**Reviews.**

| PR | Task reviews | Sweep discovery | Whole-branch (`mx-architect`, adversarial) |
| :--- | :--- | :--- | :--- |
| #47 | `mx-precise`: both tasks approved, Low 4, fixed in two batches | no confirmed defect; 1 Low deferred, 8 Info | PASS on `f48aa94`: High 0, Medium 0, Low 3 (test strength, fixed in a tests-only batch), Info 5 |
| #49 | batched `mx-feature` (CI and config): PASS, no finding | skipped (config, global rules section 7) | skipped, same rule |
| #50 | `mx-precise` approved (Low 2); `mx-adversary` FAIL, Medium 1; a second Medium by the coordinator's ruling and a third found by the controller in the fix; all three closed by a scoped `mx-adversary` re-review | 0 confirmed defects | PASS on `ac733d9`: High 0, Medium 0, Low 3, Info 3. A tests-and-docstring batch followed with no review round |

#50's Mediums: a number that cannot be read escaped as an untyped error; a recorded charge was
read by `Decimal`, which accepts `'1_0'` as 10 (rated Low by the reviewer, ruled Medium because
it is money); a trimmed key check accepted an extra key named `""`. A charge is now read only
from plain digits with an optional fraction. The re-review's own probes: 21,769 charge strings
against a hand oracle, 1,978 key cases and 15,000 fuzzed lines, none escaping.

#47's answer key was generated by the controller's script, so the task reviewer wrote its own
reader of the 27 fixtures and compared it with the key and with `parse`: no disagreement.

**Gates and CI.** `uv run --locked python tools/gates.py` exit 0, each by its controller: #47
on `e29f1f2` (804 tests), #50 on `2bc089f` (622 passed, coverage 100%). #49:
`npm --prefix web run gates` exit 0 locally (implementer). Mutation on #50 (`mutmut`, at
`ac733d9`): 642 mutants, 633 killed, 9 equivalent.

**Edge.** #49's `web` run on `windows-latest`, logs read by the coordinator: the Edge step
printed `browser: C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` and 13
PASS lines, the Chrome step its own path and 13 PASS lines; the violation canary was reported
in both. This is the first Edge run of the open-from-disk check. Earlier Windows runs used
Chrome (read from the logs of three runs on `main` before #49).

**Ledger.**
- `1A-3 task=1 agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `1A-3 task=2 agent=mx-feature fix-rounds=0 gates-first-pass=n`
- `1A-3 task=3(low batch) agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `1A-3 task=4(low batch 2) agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `1C-1b task=1 agent=mx-feature fix-rounds=2 gates-first-pass=y`
- `1C-1b task=end-batch agent=mx-scaffold fix-rounds=0 gates-first-pass=n`
- `0C-2 agent=mx-scaffold fix-rounds=0 gates-first-pass=y` (the full web gate passed on its
  first run; a lint run before it failed on a stale `node_modules`, not on the change)

**Rulings by the coordinator.** In the 1A and 1C plans. The ones a later step depends on:
- Four of 63 retained drafts of one run are refused by the table rules. The predecessor refused
  three for the same fault and accepted the fourth, a module's final reply, while turning two
  calculation rows into prose; none reached a library. The refusals stand. Step 3A sends a parse refusal and its line
  back to the module as the retry reason.
- An unclosed code fence is a flag on the block, not a parse error; step 2B refuses it.
- The bound on a reply's size is step 3A's. A charge is printed with `format(d, "f")`, and a
  recorded charge has no digit or scale cap (step 3A).
- Ruled for 1C PR 2, not yet in `main`: one representation of tool arguments in both adapters,
  what the SDK gives (a float for a fraction); `Model.close()` returns the compactions observed
  and not yet delivered; a compaction carries its event id and its outcome (done, failed,
  unfinished); an unknown charge is `None` in every case; several usage events of one call
  are summed only when every one is readable. A sent reply whose charge is unknown makes the
  run's spend unknown, and step 3A's budget stops the run unless the owner rules otherwise.

**A rule breached and corrected.** #36 put two charge figures from the predecessor's test
fragments of a real run into `tests/provider/test_types.py`, against "public or synthetic
only"; #50's first key carried seven. The whole-branch review of #50 found it; all are replaced
by invented figures in #50. The predecessor repository is public and the figures identify
nothing, and they remain in this repository's history. The 1C plan no longer points at them.

**Not verified.**
- Edge on the work PC: the CI image's Edge is the nearest evidence.
- Only 5 front matter values are in #47's frozen key; the rest rest on the reviewers' readers.
- Whether runtime 1.0.108 can deliver a compaction after `session.idle`, or twice.
- Mutation on #50 was not rerun on `2bc089f`, where source changed only in a docstring. The
  Windows failure on `ac733d9` (a 100,000-character test id) was inferred from the log and
  confirmed only by the green rerun.
- The predecessor's readers were run on the four drafts with Python 3.14, not its own pin.
- `npm --prefix web run gates` did not run for #47 or #50; neither changes a web file.

## 2026-11-14 Design track: component kit and page scaffolding (step D2a)

**Merged**, on the owner's instruction (merge when the whole-branch review has no High or
Medium finding), 17 stacked PRs in order, each retargeted to `main` and merged at the head
named: #17 `a6e6c3d`, #19 `f0a6d9b`, #20 `ff3628f`, #21 `168078c`, #22 `b74ec48`, #23
`bcbe736`, #25 `6c55a41`, #27 `c3e5bbc`, #28 `27c23e6`, #30 `95b9abe`, #31 `db410ed`, #32
`03aa989`, #37 `13dc9e9`, #38 `3d182dc`, #39 `46fdaf4`, #40 `b12f99f`, #43 `891a91c` (merge
`bd534dd`). After the last merge `web/` on `main` is byte-identical to the reviewed head
`891a91c` (`git diff --quiet origin/main 891a91c -- web`, exit 0).

**Delivers.** Design tokens as Tailwind `@theme`, fonts, the app shell, the component kit on
`#/kit` (button, tooltip, badge, tabs, status shapes and gap states, cards, timeline, alert,
empty state, input, select, table, progress, drawer, modal, progress steps, file upload,
chart frame and trend chart on Recharts), the class coverage check, and the scaffolding for
D2b to D2e: route table, four empty page groups with slice readers, four fixtures, the
fixture data writer and the route visits in the open-from-disk check.

**Gates and CI.** `npm --prefix web run gates` exit 0 at each task and at `891a91c`, by the
controller. Every PR's last CI run was green on `ubuntu-latest` and `windows-latest` before
merge, read by the coordinator. The stack was built on `d0ca6f3`; the merged `main` also
holds the back-end PRs merged since, and its own CI run on `bd534dd` had not finished when
this entry was written.

**Reviews.**

| Level | Reviewer | Result |
| :--- | :--- | :--- |
| Task | `mx-precise` (as the plan sets; the ledger does not name the reviewer per task), 14 tasks | 8 approved with no fix round, 6 after one fix round and a re-review |
| Sweep discovery | `mx-autonomous`, on `d0ca6f3..b12f99f` | 5 confirmed defects (Medium 1, Low 4), 8 structural costs. D-1 (Medium), D-2, D-3, S-1, S-2 fixed in `4a7d851` |
| Whole-branch | fresh `mx-architect`, adversarial, on `d0ca6f3..4a7d851` | Needs fixes: High 0, Medium 3, Low 6, Info 3 |
| Re-review of the Medium fixes | `mx-precise`, on `891a91c` | Approved: High 0, Medium 0. Final verdict Pass |

The three Medium findings were accessibility defects that unit tests passed for the wrong
reason, because jsdom computes names differently from Chrome and applies no stylesheet: table
column headers had an empty accessible name; focus on an invalid input or select only
thickened the ring in the same colour; a loading button had no name. The open-from-disk gate
now reads names and the invalid field's focus ring in headless Chrome
(`web/scripts/kit-chrome.mjs`). The first whole-branch review agent died in a credit outage
and left nothing; the review recorded here was run from scratch. Reports and probes are in
the D2a worktree's `.superpowers/sdd/2026-11-13-design-d2a-kit/` (git-ignored, not in the
repository); the verdicts are in #43's body.

**Ledger.** One line per task, `agent=mx-feature` unless named.
- `D2a task=1 agent=mx-scaffold fix-rounds=0 gates-first-pass=y`
- `D2a task=2, 3, 4b, 5, 7b fix-rounds=0 gates-first-pass=y`
- `D2a task=4a, 7d fix-rounds=0 gates-first-pass=n`
- `D2a task=6, 7a, 7c, 7e, 7f, 8 fix-rounds=1 gates-first-pass=y`
- `D2a sweep fixes fix-rounds=0 gates-first-pass=y`
- `D2a whole-branch fixes fix-rounds=1 gates-first-pass=y`

**Rulings by the coordinator.**
- A focused invalid input or select draws the `focus` token ring at 2px; the error edge stays
  at rest. This replaces the controller's earlier ruling that kept the source's error ring.
- Disabled input and select stay at 50% opacity, as decision 0006 ruling 17 for the button.

The controller's rulings (a loading button stays focusable with `aria-disabled`; the chart
keeps Recharts' accessibility layer, named by its title) stand.

**Parked**, for the next phase sweep: sweep rows D-4 and D-5 (the class and focus-outline
checks miss some crafted forms; the shipped tree matches a TypeScript-parser oracle) and S-3
to S-8; kit files named after task numbers (`Kit7c.tsx` and others); the kit shows a state as
a dot badge; no error boundary, so a component that throws blanks the page; two names for one
text colour. **For the owner:** no licence notice travels with the 27 files copied from
Untitled UI React and the three pieces after HyperUI (both recorded as MIT, the texts not
read); the selected segment and the hovered tab are faint as the source draws them; six early
commits carry a Sonnet co-author trailer. **Before the first Bar or Pie chart:** `react-is`
17.0.2 is chosen by a test tool's dependency and needs a decision record. **Before the Run
group's live page:** 22 horizontal progress steps do not fit a 1280 or 1920 row.

**Not verified.**
- Edge, and any browser run by hand on Windows: the gate drives headless Chrome, on both CI
  runners.
- Any screen reader; mobile widths; the focus ring outside the kit page; the error mark and
  hint text while a field is focused (read in the code, not measured).
- The coordinator read the whole-branch report, the fix diff `4a7d851..891a91c` and each PR's
  check status; it did not rerun the gates or the reviewers' probes itself.
- Each stacked PR's size against the 800-line cap rests on CI; three PRs exceed 800 with lock
  files counted, and the coordinator did not recount them without.
- The route and slice scaffolding has no page built on it yet; D2b to D2e are its first use.

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
