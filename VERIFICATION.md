# Verification record

One record, newest first, written only by the coordinator at merge. Keep it under 1,000
lines; trim the oldest entries (git history keeps them).

## 2026-11-14 Roadmap back end: 1B units, 1D HTML pages, Signal's ingest

**Merged, each read by the coordinator, CI green on Ubuntu, Windows and the review job at the
head:**

| PR | Step | Head | Merge | What |
| :--- | :--- | :--- | :--- | :--- |
| #320 | 1D PR 2b-3 | `60b07861` | `b0bdf99` | `sources.html_pages`, the declared-charset table |
| #327 | 1B PR 6a | `449cc187` | `5d2187e` | unit and currency checks on the base operands |
| #328 | 1B PR 6a2 | `87c67985` | `32cd149` | the unit forms; billions a third unit |
| #329 | 1B PR 6a3 | `eefe53b1` | `aa6ee00` | prefix marks, the excuse rule, the ambiguous mark |
| #333 | Signal S-8, part 1 | `a4ad55d6` | `1ca596e` | `signal/ingest.py`: one pass over the due sources |
| #334 | Signal S-8, part 2 | `0fa8080e` | `300d403` | the ingest rules' tests |

**1B units (the 6a set).** One sequence. `check_base` now refuses a named row printed in a unit
other than the block's, and `check_currency` a foundation that nowhere names the block's currency
(`model/foundation.py`; two new refusal kinds). Rulings R45 to R52: the refusal names the sign
rule; billions is a third unit; only the letter codes take the no-letter-before rule; marks before
a code (`kEUR`, `TEUR`, `MUSD`, `m EUR`), `000` after a code, `(000)` and `mm` are read; only the
operand's header, the first header cell and a `Unit` or `Units` column excuse; `MUS$` and `M$` are
ambiguous and refused. Whole-branch review over the set (1B worktree,
`pr6a3/branch-set-review.md`): "Verdict: pass", "High 0, Medium 0, Low 3, Info 5". Mutation count
of record for the set, at `b8564a49` with `src` unchanged to the head: 420 of 420; hand mutants 98
of 98. Ledger: `1B-6a batch agent=mx-feature fix-rounds=0 gates-first-pass=y`;
`1B-6a2 agent=mx-feature fix-rounds=1 gates-first-pass=y`;
`1B-6a3 agent=mx-feature fix-rounds=1 gates-first-pass=y`; `R52 agent=mx-scaffold fix-rounds=0
gates-first-pass=y`.

**Found by that review, predating the set:** the unit check reads only a row's own group. On the
retained public CP-1, 323 of 375 number cells sit in a group that names no unit, so a unit stated
above a table is not read and a wrong-unit row can be accepted at 1000x. Nothing calls the check
yet. Ruled R57: `handoff/` gives each table its caption line and the check reads it, as PR 6a4
before PR 7.

**1D HTML pages (#320).** `html_pages` returns the visible text in pages or a refusal. A declared
charset is matched against a table of ten labels and refused if absent; the codec search is never
reached with the file's text. A zero byte and a character reference of 32 or more digits are
refused. Twenty-seven spellings the codec search used to accept are now refused: `1252`, `646`,
`8859`, `ansi-x3-4-1968`, `ansi-x3.4-1968`, `ansi-x3.4-1986`, `cp367`, `cp65001`, `cp819`,
`csascii`, `csisolatin1`, `ibm367`, `ibm819`, `iso-646.irv-1991`, `iso-8859-1-1987`,
`iso-8859-1:1987`, `iso-ir-100`, `iso-ir-6`, `iso646-us`, `iso8859`, `l1`, `latin`, `u8`, `us`,
`utf`, `utf8-ucs2`, `utf8-ucs4`. Reviews (1D worktree): security review "PASS. High 0, Medium 0,
Low 3"; whole-branch review "PASS (the skill's verdict: CLEAN). High 0, Medium 0, Low 3, Info 3";
sweep 0 defects. Mutation, count of record for `sources/`: 1,532 mutants, 1,420 killed, 10 at the
time limit, 102 survived (`html.py` 70, of which 67 equivalent and 3 killed in a second phase);
one load reading of 49.78 inside the run, every time-limit mutant and the 2 new survivors rerun
alone. Found, predating: a charset name cut at byte 4,096 is read as its prefix (`iso-8859-15` as
`iso-8859-1`, the euro sign as U+00A4); PR 2b-4 refuses a name that ends at the limit.

**Signal's ingest (S-8).** One pass handles one source at a time, starts no thread of its own and
makes no model call. A refused fetch or an unreadable feed is a failed check with its reason; a
refusal by the lookup cap records nothing and stops the pass; any other exception is logged and
recorded by type only, a documented fail-open so one source cannot starve the rest;
`StoreUnusable` is never caught. Each entry is stored, matched and posted in one transaction.
Verdict lines (shared notes, `s8/`): task review "Spec: PASS", "Quality: PASS"; security review
"PASS. No High or Medium introduced. One Medium predates"; whole-branch review "PASS. No High, no
Medium introduced by this change. 3 Low, 4 Info. Status: complete." No counted fix round. Ledger:
`S-8 task=1 agent=mx-feature fix-rounds=0 gates-first-pass=y`.

**Signal's mutation counts of record,** reruns in a slot with one worker (ruled accepted, each
with its limit): threads 166 of 173 at `3f89b9a7`, load 8.3 to 12.3, seven survivors rated
equivalent or precedence-only; ingest 74 of 81 at `bf48371f`, load 10.9 to 8.9, whose seven
survivors have tests added later that no run of record shows caught; feed view 91 of 91 and 19 of
22, load 8.7 to 15.7, in probes with no forced-failure or known-killed control.

**Rulings on Signal's predating items.** Fixed in their own PRs: the feed view's cost, a cap of
2,000 new stories per source per pass with the rest counted in the check's note, the store's read
of every same-title story under the write lock. Kept and recorded: writes for an invented name
(decision 0009, no accounts), a locked database ending one pass, `new_count` ignoring filters, two
processes on one root, the service's header and descriptor limits.

**Machine incident, 22:41 UTC, no panic.** A reviewer's loopback probe opened thousands of
connections in a row and exhausted the ephemeral ports (`Errno 49`) for about a minute. Rule 7 in
the shared slots file: at most 1,000 connections per run, `SO_LINGER (1, 0)` or one reused
connection, stop at the first `Errno 49`.

**1D PR 3b-2, a rule broken and redone.** The first fix commit on #335 was the Opus planner's
prototype copied by the implementer; the owner's rule is that Opus agents write no code. Ruled:
the source change is reverted by a commit, a fresh `mx-feature` reimplements from the written plan
without reading the prototype, and every measurement is retaken. Not merged yet.

Not verified: 1D's ledger line for PR 2b-3 was not in its ready message; that the 1B count at
`b8564a49` holds at the head rests on `src` being unchanged, read in the diff, not a rerun; the
ingest survivors' new tests under a run of record; Windows other than through CI.

## 2026-11-14 Design track: slice contract 2 (absent and pending states), states 2 rulings

**Merged**, each with gates on Ubuntu and Windows and the review job green on its head, none
cancelled, and its source diff read by the coordinator (the tests were not read line by line).
The library and model folders on `main` equal the two heads.

| PR | Head, merge | Content |
| :--- | :--- | :--- |
| #330 library | `0765705`, `4bae1e4` | `Overview.sides` and `changeView` may be null and are then not drawn; `Changes` gains `pending` (its own page state; never the issuer's only run; no history entry links it); an empty `none` or `pending` title or text is refused; a bad percent escape in a delivered address is refused instead of thrown (774 lines) |
| #331 model | `8d93e91`, `5eea548` | Portfolio fit `limits` and `scatter` may each be `{ gap }`, drawn as the gap panel; the reader holds a bad run as unreadable and reads the others (the index lists or counts it, its pages say why); `published.href` is a relative path inside the library folder, `checkFigure.href` that or a `#/` address (800 lines, at the cap) |

The web run on the merged tree (`5eea548`, run 43651469961) had not finished when this was
written.

**Reviews.** `mx-precise` per task: six tasks passed, L2 after one fix round (Medium: the new
fixture scene was partly copied from another issuer). Sweep discovery (`mx-autonomous`,
changed-update): 16 rows, none Medium or above, nothing repaired. Whole-branch (`mx-architect`,
adversarial): pass, High 0, Medium 0, Low 5, Info 5; the Lows were closed in each PR's last commit
against the reviewer's probes with no review round. Reports:
`.superpowers/sdd/2026-11-14-slice-contract-2/` (`reviews/`, `sweep/register.md`).

**Ledger** (every task `agent=mx-feature`; fix rounds, gates first pass). L1: 0, n. L2: 1, n.
L3: 0, y. LA: 0, y. LB: 0, y. M1: 0, n. M2: 0, n. M3: 0, n/a. MB: 0, y. MC: 0, y. `n` is a first
run that failed on format, lint or a load timeout and then passed.

**Gates and live validation.** `npm --prefix web run gates` exit 0 at both heads (the library's
at load 180; the file gate was rerun four times on its 60 s load timeout at `e3882db`). Headed
Chrome from disk and the app's browser pane, every new state at 1440 and 1024: one `h1`, no
horizontal scroll, clean console, visible focus; library built from `9ec67d6`, model from
`4ce1eb6` with a scratch data file. The walk was not repeated for the last commit of each PR.

**Rulings.** Owner: "Keep 'For and against' optional" (a departure from the Overview mock). Under
the owner's instruction of 2026-11-14 to the coordinators to resolve all decisions, the roadmap
coordinator ruled: the empty-title refusal and three address test rows go in #330; the defect that
predates the step (`%ff` threw a `URIError` through `readSlice`) was fixed test first in #330; no
model fixture scene for the new states; and the recommended option of every owner question of
decision 0013 (states 2), now recorded there with the back-end coordinator's three. Other rulings
of that date (sample links, Show sources, chart tick size, notices for copied code, the phase
sweep's questions) are applied by the phase sweep and recorded with it.

**To the phase sweep, wave 2:** the address rule duplicated across the two groups; the model gap
drawn three ways; "could not be read" typed in three places and matched by the file gate; the run
address template written three times; an unreachable rethrow in the model reader; the library's
Forecast address for an id holding `/` or `%` (3B contract: ids are slugs; the store's grammar
`[A-Za-z0-9._-]{1,128}` fits); an empty `overview.metrics` drawing an empty region; sample
Forecast links to model runs the fixture lacks; `%00` accepted by the address rule.

Not verified: the open-from-disk gate draws none of the new model states (page tests and the
live walk only); Edge and other widths; mutation testing beyond hand-written mutants; whether
delivery will send these states; the states 2 rulings have not been seen by a reader.

## 2026-11-14 Roadmap back end: Signal's threads, the run store's status writes; the owner's instruction

**The owner's instruction, about 22:20 UTC, given in the lead coordinator's session and read
there:** "tell coordinators to resolve all descisions". The back-end coordinator's reading (its
own): no sub-session holds for the owner; each brings its questions to the coordinator, who rules
and records the question, the ruling, why, and the cost if wrong. A round past the fix-round limit
is the coordinator's ruling, capped at one each time. Not lifted: a paid model run or a cap
change, credentials, the predecessor repository, the instruction files, repository settings, the
work PC, the content security policy, a purchase, anything a permission check refuses, a
force-push of a pushed branch, the OS-limit rule and the mutation-slot rule. No merge with a High
or Medium open and none on a red check. Earlier the same evening the owner approved, in this
session ("Approve 4th round") and the lead's ("Yes, direction 1"), a fourth fix round for 1D PR 3b
(#314) as a stacked PR 3b-2 that binds namespaces outside expat.

**Merged, each read by the coordinator, CI green on Ubuntu, Windows and the review job at the
head:**

| PR | Step | Head | Merge | What |
| :--- | :--- | :--- | :--- | :--- |
| #289 | Signal S-7, part 1 | `738aeda4` | `164bdf6` | shared helpers made public; `identity.cleaned_text` |
| #290 | Signal S-7, part 2 | `41341966` | `1c66c47` | `signal/threads.py` |
| #291 | Signal S-7, part 3 | `bfd2fb68` | `2a5329d` | the carried thread tests and the ruled behaviours |
| #292 | Signal S-7, part 4 | `7eeff990` | `98bfa71` | unread counts and their rules |
| #293 | Signal S-7, part 5 | `e23a8d80` | `68cbc8f` | the claim, pins and survivors' tests |
| #322 | 2A PR 2c (replaces #303) | `ab141ba4` | `cd55161` | the run store's status writes |

**Signal's threads (S-7).** One sequence: the later parts carry tests for code in the earlier
ones. Each head is the reviewed head plus merges of `main`, no rewrite. Verdict lines read in the
report files (shared notes, `s7/`): task review "Spec: PASS", "Quality: FAIL (2 Medium: surviving
mutants M1 ..., M2 ...)"; security review "PASS. No High or Medium introduced. 4 Low, 6 Info";
after fix round 1 "PASS. M1 and M2 fixed"; whole-branch review "PASS. No High, no Medium. 2 Low, 4
Info. Status: complete." One later commit changes a docstring's wording and two test files; no
reviewer probe was rerun after it. Two counted fix rounds. Ledger:
`S-7 task=1 agent=mx-feature fix-rounds=2 gates-first-pass=n`.

What it does: threads, comments (one level of replies, 500 a thread, a 15-minute edit window) and
three reactions inside groups. A text is cleaned and refused before any transaction; inside it
the order is visibility (a hidden target answers like a missing one), then role, then what only
the rows can tell. Only a writer or the owner starts a thread or comments; a reaction needs a
registered user; any name may read and mark read. A share that joins an automatic thread claims
it. An error text carries no caller text except a malformed cursor, cut at 120 characters.

**The run store's status writes (#322).** `claim_run` makes a new writer and fences the earlier
claim (`StoreFenced`, a sibling of the other store errors); `start_run`, `reject_run`, `end_run`
and `record_event` each check the claim, the run's writer and its status inside one write
transaction. A resume clears the end; a finished or rejected run takes no event. Whole-branch
review at `b2eb949f` (2A worktree, `pr2c/`): "PASS. High 0, Medium 0, Low 4, Info 6". L2 (three
key rows) and L3 (one assert) landed in the PR; L1 and L4 are the first task of PR 3. Ledger:
`2A-2c task=1 agent=mx-feature fix-rounds=1 gates-first-pass=y`;
`2A-2c lows agent=mx-scaffold fix-rounds=0 gates-first-pass=y`.

Mutation, count of record with its limit named (ruled under the owner's instruction): 1,074
mutants, 887 killed, 186 survived, 1 timed out; on the PR's lines 335, 282 killed, 53 survived,
none real (message wording or SQL case). One load reading was 51.69 against the limit of 40; the
timeouts were rerun alone, the kills were not.

**Rulings by the back-end coordinator** (those after 22:20 UTC under the owner's instruction).
1B: R49a, the currency check reads the prefix forms; R49b, capital `T` is a thousands mark
wherever `k` goes; R50, only the operand's header, the first header cell and a `Unit` or `Units`
column excuse a cell in another unit; R51, `MUS$` and `M$` are ambiguous and refused under both
blocks (`MMUS$`, `MUSD`, `M€` stay millions); one mutation count at the final 6a3 head stands for
6a, 6a2 and 6a3, which merge as one set. 1D: 96 MiB is a target, not a stated bound, until one
file measures all four terms; `MAX_TOKEN_BYTES` goes to 524,288 in 3b-2 (a longer start tag is
refused; no real-file evidence either way); a charset name cut at the sniff's last byte is
refused, in PR 2b-4. 1C: the sigma case forms move to a stacked PR 2h-2 merged with 2h as one
set, after a first attempt held 413.6 MB. 2A PR 3: a stored writer that is not a token is
`StoreCorrupt` and such a run cannot be claimed; names are exact `str`.

Not verified: the threads hand-mutant count (166 of 173 caught, no non-equivalent survivor) was
taken before the slot rule with no load recorded, so it is not of record; that #322's kills taken
at load 51.69 are free of load effects; Windows other than through CI; 1D's and 1C's figures
above are their controllers' reports, not read by the coordinator in a diff yet.

## 2026-11-14 Roadmap back end: Signal's feed view, the run store's Low batch

**Merged, each read by the coordinator, CI green on Ubuntu, Windows and the review job at the
head:**

| PR | Step | Head | Merge | What |
| :--- | :--- | :--- | :--- | :--- |
| #210 | Signal S-6, part 1 | `54638489` | `56492aa` | `store.read_snapshot` and the test layout |
| #211 | Signal S-6, part 2 | `d798abb6` | `05c3578` | `signal/feedview.py`: pages, search, counts, saves |
| #212 | Signal S-6, part 3 | `7bde19d3` | `bf1de71` | the feed view rules on a generated grid |
| #213 | Signal S-6, part 4 | `199e6920` | `a4d9793` | input, refusals and query plans |
| #321 | 2A PR 2b-b (replaces #302) | `1555b321` | `c2bfa6c` | the run store's Low batch |

**Signal's feed view (S-6).** The four merged as one sequence: #211 alone leaves 47 of 91 hand
mutants alive on its own tests, so it was never to sit on `main` without #212 and #213. Reviews,
verdict lines read in the report files (shared notes, `s6/`): security review "PASS on the change"
(no High or Medium introduced; one Medium, M1, predates it); whole-branch review at the first tip
"FAIL (1 Medium: W1)", a second `conftest.py` that made `mypy` refuse the tree once merged with
`main`; fixed, then `rereview-2-precise.md` "PASS (0 High, 0 Medium, 0 Low; 2 Info)". One later
commit is test-only (short parametrize ids: a long id passes Windows' 32,767-character limit on
`PYTEST_CURRENT_TEST`). Two counted fix rounds. Sweep (`s6/sweep-register.md`): 0 confirmed
defects, 6 measured structural costs for the phase sweep. Ledger:
`S-6 task=1 agent=mx-feature fix-rounds=2 gates-first-pass=n`.

What it does: one static statement serves every view and filter, a search has its own so SQLite
drives it from the full-text table; a page is read inside one read transaction
(`store.read_snapshot`, always rolled back); the groups a user can see are read once per page from
`groups.visible_group_ids`. A request-shaped error is a `ViewError`, a caller's bug a `StoreError`,
and an error text carries at most 120 characters of input. Departure from the predecessor:
`card_for` and `new_count` also read in a snapshot, so all three refuse inside a caller's open
transaction.

**For the owner (M1, predates the port):** the For you page and a count after 0 cost stories times
memberships: 610 ms for a member of 490 quiet groups at 20,000 stories (predecessor 609 ms), up to
2,483 ms for a count after 0 as a member of all 500 groups; a count after a recent id is 2.3 ms.
Kept as the predecessor's.

**The run store's Low batch (#321).** #302's content rebuilt on a fresh branch because gitleaks
flagged a made-up test literal in a commit of #302 as an API key; the coordinator refused
both a rewrite of the pushed branch and a merge on a red check. The literal is now `"ab" * 16`;
#302 is closed. Changes: stored text that is not UTF-8 is `StoreCorrupt` with no stored text in the
message; a `clock` that is not callable is `StoreRefused`; a stored `as_of` that is not a date is
`StoreCorrupt`; `repr(Claim)` no longer prints the token; the error docstring names the chained
cause and tracebacks. Reviews (2A worktree, `pr2b/`): whole-branch on #302 at `a2c4b55c` "PASS.
High 0, Medium 0, Low 4, Info 6"; scoped re-review of the rebuild at `1555b321` "PASS. Every check
holds" (gitleaks clean over the range; five of six commits patch-identical, the sixth differs by
the literal). No fix round counted for the rebuild. Ledger: `2A-2bb task=1 agent=mx-feature
fix-rounds=0 gates-first-pass=y`; `task=2 agent=mx-feature fix-rounds=0 gates-first-pass=y`;
`task=3 agent=mx-feature fix-rounds=0 gates-first-pass=n`.

**Rulings by the back-end coordinator.** 1B R48: the no-letter-before rule applies to the letter
codes only, so `C$m`, `A$k` and `HK$m` name their unit. R49: marks before a code (`kEUR`, `TEUR`,
`MEUR`), a mark word then a code (`m EUR`), `000` after a code and a space, `(000)` and `MM` are
read as units, in a PR 6a3 merged with 6a and 6a2; the currency check reads the same forms; capital
`T` is a thousands mark wherever `k` goes. 1D: a Low that predates PR 2b-3 (nothing tested the
guard that keeps a comment's body hidden) rides in its Low batch as one test row.

Not verified: Signal's hand-mutant count (91 of 91) and sweep count (17 of 22) were not rerun in a
mutation slot, so neither is of record; the plan-text test was not run on SQLite 3.49.1 other than
by Windows CI; mutmut was not rerun on `1555b321` (count of record 699/558/141 at `a2c4b55c`);
that #302's flagged literal was never a real token rests on the 2A controller's own record.

## 2026-11-14 Design track: states 2, design stage (confidence, run end, restricted modules)

**Merged:** #323, head `9da1463`, merge `de4f15d`, docs only (651 lines): `docs/design/states-2.md`
(inventory, proposal, build outline), `docs/design/mocks/states-2.md`, the draft
`docs/decisions/0013-states-2.md`, and a "Proposed (states 2, not ruled)" section of
`docs/design/design-system.md`. Gates on Ubuntu and Windows and the review job passed on that head,
none cancelled; the coordinator read the diff, and the three new files on `main` equal the head.
**Nothing is decided or built:** the owner's review of the mocks is the gate.

**Review.** Batched `mx-feature` docs review against the sources: pass, no High or Medium, 4 Low or
Info applied in `9da1463` (probes `probe_contrast`, `probe_scores`, `probe_cases`, exit 0). No sweep
and no adversarial pass: a docs-only PR. Ledger: task 1 inventory `agent=mx-feature fix-rounds=0
gates-first-pass=n/a`; task 2 proposal `agent=mx-architect fix-rounds=0 gates-first-pass=n/a`;
task 3 fix-ups and size `agent=mx-feature fix-rounds=1 gates-first-pass=n/a`; the review's Lows
`agent=mx-scaffold`. The mocks (five Claude Design
files, sample data) were drawn by the step's controller: the tools are not open to `mx` agents.

**Open for the owner (0013):** questions 1 to 9, 12, 14, 15, and a sixteenth raised after the merge:
the Run page needs a confirm step for taking over a run, because taking over a run whose process is
alive stops that process's writes.

**Ruled by the back-end coordinator after the merge** (the draft still shows them open; they enter
0013 at the owner's review). Q10: status `finished`, end reason `completed`; delivery reads the
status. Q11: the store has no lock and no heartbeat, so nothing marks a dead run; a run is `stopped`
with end reason `interrupted` only when the operator takes it over, and "Interrupted" is drawn only
from that stored state (a `running` run may show its last activity time, no judgement). Q13: a
launch refusal is never a run: a start-page message, no row.

**Found, predating the step, not fixed:** `web/fixtures/run.json` draws a capped run with a full
bar (under step 3A a capped run shows spend below the cap) and a failed run offering "Open what
finished" against decision 0006 ruling 12; the same fixture uses a real issuer name;
`docs/design/component-map.md:94` records F7 as React Aria where the live page says Radix UI or
Base UI.

Not verified: no reader has seen the mocks or the proposed words; frames were checked at 1440 px
for layout and console errors only; the run end and module words are plan text with no code; the
Claude Design tools stop working by 14 Dec 2026.

## 2026-11-14 Roadmap back end: 2B part 1 complete (the reader guard), Signal's groups

**Merged**, under the owner's delegation (decision 0006), each at the head named with every
check green on Ubuntu, Windows and the review job, and its diff read by the coordinator.

| PR | Step | Head, merge | Content |
| :--- | :--- | :--- | :--- |
| #318 | 2B reader guard | `889810b`, `149348e` | `checks/figures.py`: `_read` always advances past the number it read; a test that stalls `_figure` under a 1,000-call cap (31 lines) |
| #183 | Signal S-5, 1 of 2 | `3b8de2f`, `f108b42` | `signal/groups.py`: groups, membership and the one visibility rule (772) |
| #184 | Signal S-5, 2 of 2 | `8f375d4`, `093ccee` | the review fixes and the Low batch (742) |

With #318 step 2B's first part is complete: `check_handoff` runs every check of the plan.
Its second part waits for 1B's PR 7.

**Reviews.**

| PR | Task reviews | Sweep discovery | Whole-branch (`mx-architect`, adversarial) |
| :--- | :--- | :--- | :--- |
| #318 | `mx-precise` pass, Info 2; `mx-adversary` pass, Info 1 | none (a one-line fix; the coordinator's call) | dispatched by the coordinator on `889810b`: pass, Low 1, Info 3 |
| #183, #184 | `mx-precise`: Medium 4 (the size, test strength); `mx-adversary` pass, Low 2; fix round 1 re-review pass | registered | fail at `f09ac09`, Medium 1 (test strength; the code held); fix round 2; adversary re-review pass, Low 5, Info 2; scoped `mx-feature` re-review of the Low batch: pass, Low 1, Info 1 |

- #318's count of record (mutmut 3.8.1, the adversary, 1-minute load 20.41): `_read`, 23
  mutants, 23 killed. The mutant that stalled the loop on `main` and grew to 4.85 GB now
  fails a test at 66 MB. The owner chose that the guard be its own small PR; which reviews
  it got was the coordinator's reading, and the whole-branch review was added before merge.
- #318's Low predates it: `_read` also trusts `_find` to return a number at or after its
  position, which only a mutant of `_find` breaks, so mutation runs on `figures.py` keep the
  1.5 GB stop.
- Groups: 18 of 20 hand mutants caught (the re-review's report calls it the count of
  record; the controller's ready message says it ran with the 1-minute load well above 40,
  before the load rule, so the coordinator asked for one rerun in a slot); one survivor
  (a `NOT GLOB` in the manager check) is carried to the next groups test batch, one is
  equivalent. A caller that catches a failure inside `create_group`'s transaction and commits
  keeps a memberless group (ruled: the caller owns the transaction).
- #302 and #303 (2A) were closed unmerged: the secret scan flagged a made-up 32-hex test
  literal, never a token, in a commit no later commit could remove from the scanned range.
  No pushed branch was rewritten and no red check was accepted; their content is rebuilt on
  fresh branches as #321 and #322 with the literal changed from the first commit.

**Rulings.** For the "states 2" design step: a run that ended normally has status
`finished` and end reason `completed` (the 3A plan's G3 is clarified with this entry); an
interrupted run is never inferred by a reader: it is written `stopped` with end reason
`interrupted` only when the operator takes the run over, which claims it again and fences
the earlier writer. The coordinator's first answer named a store writer lock; the store has
none (a per-run writer token), and the answer was corrected. A launch refused for
its file count or size is never a run. 2B's confidence rulings C1 to C10 and R65 to R70 are
now in the 2B plan. 1D: a declared charset name is refused unless a literal table holds it.

**Ledger.**

- `2B-guard task=1 agent=mx-feature fix-rounds=0 gates-first-pass=n`
- `S-5 task=1 agent=mx-feature fix-rounds=2 gates-first-pass=n`

Not verified: a mutmut count for Signal's groups; the groups hand-mutant result rerun in a
slot; real memory growth in `_read` (simulated under a 1,000-call cap).

## 2026-11-14 Roadmap back end: 2B confidence, the run store's first tables, Signal's names and topics

**Merged**, under the owner's delegation (decision 0006), each at the head named with every
check green on Ubuntu, Windows and the review job, and its diff read by the coordinator.

| PR | Step | Head, merge | Content |
| :--- | :--- | :--- | :--- |
| #312 | 2B PR 6 | `23c00a4`, `5e378d0` | `checks/confidence.py`: the confidence checks and the exact score; `check_handoff` is complete (525 lines) |
| #296 | 2A PR 2a | `d5f83c9`, `a1a99f4` | `store/schema.py`: migration 1, the runs, pins and events tables (478) |
| #297 | 2A PR 2a-b | `d2e62b0`, `a20f04e` | migration 1's CHECKs and triggers tested on a raw connection (788, tests only) |
| #300 | 2A PR 2b | `eaf01a0`, `3a17fb9` | `store/runs.py`, `records.py`, `db.py`: create a run and read it back (799) |
| #164 | Signal S-4, 1 of 3 | `0645a12`, `4a976e2` | `signal/identity.py`, `topics.py`: names and topics (777) |
| #165 | Signal S-4, 2 of 3 | `917823b`, `b7076a3` | clean names and topic text, caps, short error texts (640) |
| #166 | Signal S-4, 3 of 3 | `0bf4852`, `7a3871a` | topics listed for no user; distinct kinds; surviving mutants killed (197) |

Stacked PRs were retargeted to `main` and their CI rerun there before each merge. #166's
first merge attempt stopped because its base had not moved; it was retargeted and rerun.

**Reviews.** As each controller reported; the coordinator read each quoted verdict line in
its report file.

| PR | Task reviews | Sweep discovery | Whole-branch (`mx-architect`, adversarial) |
| :--- | :--- | :--- | :--- |
| #312 | task 1: `mx-precise` Medium 1, `mx-adversary` Medium 2; fix round 1, then a key gap closed by key cases; task 2: both pass | 0 defects | pass on `23c00a4`: Low 3, Info 6 |
| #296 | `mx-precise` and `mx-invariants` on the first version: changes required, High 1 (REPLACE overwrote rows), Medium 2; two fix rounds, both re-reviews pass | as #297 | at `8395bc1`: changes required, Medium 1, Low 2, Info 5 (a REPLACE naming the hidden rowid); third round on an `mx-autonomous` plan; scoped re-review on `d5f83c9`: pass, M1 and L1 closed |
| #297 | as the stack's task reviews | registered, 0 defects | pass on `d2e62b0`: Low 2, Info 5 |
| #300 | `mx-precise` pass, Low 2; `mx-invariants` pass, Low 2 | 6 rows, 0 defects | changes required, Medium 1 (pins revalidated before the write); scoped re-review pass, Info 4 |
| #164 to #166 | `mx-precise` Medium 3 (test strength); `mx-adversary` Medium 1; fix round 1; adversary re-review pass | registered | pass at `a7227ed`: Low 6, Info 9. #166's Low batch after it: scoped `mx-feature` re-review run by the coordinator, pass, Low 1, Info 1 |

- Mutation counts of record (mutmut 3.8.1, reviewers' runs). #312: `confidence.py` 499
  mutants, 460 killed, 39 survived; the five functions task 2 changed, 174, 150 killed, 24
  survived; of those 63, 21 are shown equivalent and 42 change only reason wording (open,
  graded with the next checks change). #300, taken before its fix: 675, 526 killed, 148
  survived, 1 with no test; in its own lines 388, 290, 97, 1, all graded. #297: 184 SQL
  hand mutants, 167 killed, 16 equivalent, 1 invalid.
- #166: the whole-branch reviewer's probe caught 28 of 40 hand mutants before the Low
  batch and 39 of 40 on the merged head; the survivor (`IdentityError` made a `StoreError`)
  is carried to the service step.
- #297 and #300 were force-pushed earlier in the day (entry of #313); each merged with the
  reviewer's line that the pushed head is the content reviewed.

**Rulings.** 2B C1 to C10, R65 to R68, and R69: a confidence outcome is used only for a
document `check_handoff` returns no refusal for (a reader error does not know the format).
2A R31; migrations after the first take no hidden rowid; `repr(Claim)` must not print the
writer token (in #302's Low batch). 1B R46 (unit forms, PR 6a2 merged with 6a) and R47 (a
balance is printed only as a number of its own), both ahead of their PRs.

**Machine.** The coordinator's own measurement and actions, not a controller's report: at
20:07 UTC `uptime` gave a load average of 184 on 10 cores, and the lead coordinator had
counted seven mutation runs alive a minute earlier. From 20:10 at most two mutation runs run at a time across all sessions, queued in a
shared file; a count taken with the 1-minute load above 40 is not of record until its
timeouts are rerun alone. 1B's PR 6b count was taken above that load and is held.
Thirteen finished worktrees were removed; `.superpowers/` is git-ignored there, so a
worktree's reports are copied out before it is removed.

**Ledger.**

- `2B-6 task=1 agent=mx-feature fix-rounds=1 gates-first-pass=y`
- `2B-6 task=2 agent=mx-feature fix-rounds=0 gates-first-pass=n`
- `2B-6 task=low-batch agent=mx-feature fix-rounds=0 gates-first-pass=y` (from 2B's ready message)
- `2A-2a task=1 agent=mx-feature fix-rounds=2 gates-first-pass=y`
- `2A-2a wbr-fix=1 agent=mx-feature (mx-autonomous plan) fix-rounds=3 gates-first-pass=y`
- `2A-2b task=1 agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `2A-2b task=2 agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `2A-2b wbr-fix=1 agent=mx-feature fix-rounds=1 gates-first-pass=y`
- `S-4 task=1 agent=mx-feature fix-rounds=1 gates-first-pass=n` (from Signal's ready message)

Not verified: real model output against the confidence checks; SQLite builds other than
3.53.1 (both runners); #300's mutation count after its fix (hand mutants only); a mutmut
count for Signal's names and topics (`mutmut` was not run there); the 42 reason-wording
survivors' equivalence.

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
- CI: every PR head had `gates (ubuntu-latest)` and `review` passing and at least one passing `gates
  (windows-latest)` job before its merge, but not every Windows job passed. #140 (run 43613667245,
  17:23:45 to 17:43:47; duplicate run 43613667111 passed), #282, #284, #286, #287 and #294 each also
  carry one Windows job that ended cancelled; #168's failed job was rerun and the rerun was cancelled
  (18:04:13 to 18:24:17). Those jobs were cut off by the `web` workflow's 20-minute job limit, not by a
  failed check; omitted here because the coordinator's pre-merge check counted only failed and pending
  jobs. Measured on `main` `4a0cbdbb` (run 43624986501, Windows, attempt 2, the first rerun, started
  18:49 UTC): `npm run gates` 10 min 5 s and "Open from disk in Edge" 6 min 1 s passed; "Open from disk
  in Chrome" was cancelled after 3 min 13 s at the 20-minute mark. With all four page groups on `main`
  the Windows job no longer fits 20 minutes on a slow runner; Linux takes about 8 minutes. #58, #70,
  #83, #107 and #130 each have two Windows jobs cancelled within a minute at about 16:04 UTC (not the
  limit; cause not established) and each later has two passing Windows jobs. The other exception: #168
  was merged with one of its two Windows jobs failed: the rerun of that job (run 43622974167, attempt 2)
  never produced a result, so on #168's commit that job has one failure and no pass. The failure was
  `StatementsPage.test.tsx` "describes a missing cell by its reason, shows it on focus, and draws it
  n.a., never 0" (`Test timed out in 5000ms`, 5,130 ms), a model-pages test outside this stack (see
  "Model pages test timeout (#295)" below); the duplicate Windows job on the same commit (run
  43622974170) passed. #168's first run (43613658822) failed "Changed lines at most 800" because it
  still measured against its old base (10,753 lines against the old base, 296 against the new one); the
  D2b session closed and reopened the PR with no new commit to get runs on the right base. Earlier
  failed checks on #127 and #139 were the Windows `DevToolsActivePort` read race fixed by #156, on heads
  the end push replaced; #71 and #83 failed once in the shared kit page check and #264 and #280 had
  Windows gates cancelled under queue load, each rerun.

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

**Not verified.** That any reviewer read `3ca2f8c7` (RR-01 and RR-02 were checked against the reviewer's probe
only); that the re-review was by a fresh agent (it was the agent that wrote the review); a live walk on
`3ca2f8c7` or on merged `main` (the `b32a784` walk covers the Home list and the drawer only); per-commit gating
of the seven fix-round commits (the re-review lists it); the print preview of collapsed limitations (task 7
walk: "Not walked"); open Infos of the sweep batch review (`modulesCount` check order, a quadratic `findIndex`
on issuer ids, focus dropped by the body remount on a run change; its Low L1, the drawer across runs, was fixed
in the fix round); any CI run of a PR head merged with `main` after `718a13b4` (the stack was forwarded once;
`git merge-tree` with `9f900d53` was clean); a passing run of #168's failed Windows job on its own commit (its
rerun was cancelled); a complete Windows run of the cancelled job on each of #140, #282, #284, #286, #287 and
#294 (each has a passing duplicate job on the same commit); cancelled Windows jobs on earlier commits of the
stack's PRs (only each PR's last commit was read); the full gates at `3ca2f8c7` by the controller (the fixer ran
them); the whole-branch review did not rerun the gates (taken from the ledger), read the tests in full (about
13k lines, sampled), compare each page with its mock frame again, run WBR-12's deep tree, or probe WBR-05 for
issuer and module ids; the fixer's WBR-08 mutant; RR-01 in a real browser (judged by Node's URL parser); Edge
and Windows browsers beyond CI; screen-reader announcements; print output; the Chart sides of the missing chart
kinds; real download files; the Halden Forecast link against a model fixture holding Halden; any slice against a
real delivered run (step 3B does not exist); whether the fixture's invented issuer names match a real company;
any report kept only in the git-ignored `.superpowers/` folders of eight finished design-track worktrees
(`agent-a72a…`, `agent-aeee…`, `agent-a44c…`, `agent-ac21…`, `d2c-pr-a`, `d2c-pr-b`, `d2c-split`,
`kit-link-toggle`): the coordinator removed them at about 19:50 UTC after checking only for uncommitted tracked
files, so such reports were deleted unread (the D2b, D2c and D2e records cited in the entries were copied to the
notes folder before and are unaffected).
**Corrected, the Windows web gates on the merged tree.** On `main` `4a0cbdbb`, `python` push run 43624986619
passed; `web` push run 43624986501 passed on Linux and its Windows job was cancelled three times (the original
run and two reruns started 18:49 and 19:11 UTC), each at the 20-minute limit, none with a failed check; in the
second rerun gates took 11 min 50 s and the Edge check 6 min 17 s before the Chrome check was cut off. PR #311
(back-end coordinator, merged; `web.yml` only) raised the limit to 40 minutes. The `web` push run 43632557384 on
`main` `cb091afe` (the merge of #311; `git diff --stat 4a0cbdbb cb091afe -- web` prints nothing, checked) passed
on both systems; on Windows `npm run gates` took 10 min 37 s, the Edge check 5 min 33 s and the Chrome check 3
min 26 s.

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
