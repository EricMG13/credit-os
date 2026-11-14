# Verification record

One record, newest first, written only by the coordinator at merge. Keep it under 1,000
lines; trim the oldest entries (git history keeps them).

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

## 2026-11-14 Roadmap back end: 1C PR 2b, 1D PR 1d, and the plans for 1B, 2A and 2B

**Merged**, under the owner's delegation (decision 0006), each at the head named with every
check green, and its diff read by the coordinator.

| PR | Step | Head, merge | Content |
| :--- | :--- | :--- | :--- |
| #102 | 1C PR 2b | `49751b4`, `4994b8d` | `provider/events.py`: one call's session events to a `Reply`, and the cost reading (800 lines, at the cap) |
| #100 | 1D PR 1d | `a9a8bba`, `b34dd6a` | `sources/walk.py`: the folder walk (800 lines, at the cap) |
| #121 | plans | `a9edbff`, `4643521` | Plans for steps 1B, 2A and 2B; ports map rows |
| #108 | records | `6e3d39b`, `176ce78` | The entry below this one and the 1A and 1D plan rules |

**Reviews.**

| PR | Task reviews | Sweep discovery | Whole-branch (`mx-architect`, adversarial) |
| :--- | :--- | :--- | :--- |
| #102 | `mx-precise` approved; `mx-adversary` FAIL, Medium 1, fixed and re-reviewed PASS | 2 confirmed defects, Medium 1 and Low 1, fixed; `mx-adversary` re-review PASS, Low 1 | PASS: High 0, Medium 0, Low 4, Info 3 |
| #100 | `mx-precise` quality PASS, Low 3 (its spec verdict failed only on the controller's 560-line estimate, ruled by the 800 cap); `mx-adversary` FAIL, High 1 (the Windows type check on a test), Low 6; fixed, re-review PASS | 0 confirmed defects, 4 measured costs | PASS on `46a502d`: High 0, Medium 0, Low 5, Info 6. One docstring and test-spelling commit followed |
| #121 | batched `mx-feature`: PASS, Low 4, three fixed (returned as text; the verdict is the PR's comment) | skipped (docs) | skipped (docs) |

- #102's two Mediums were both on money. Removing repeats by event id alone dropped a later
  usage event and its charge and could hide another model or a session error; and repeats were
  compared with Python `==`, so `100` and `100.0` merged and a charge was understated. A
  redelivery is now an event whose JSON text equals an earlier one's.
- #100's last commit corrects a sentence the coordinator had ruled into a docstring: it said
  the pin's digest guards content, and when a pin is created no digest exists yet.
- #121's reviewer recomputed the 1B seed row and the 2B worked confidence example with
  fractions: both match the plans.

**Gates and CI.** `uv run --locked python tools/gates.py` exit 0, each by its controller: #102
on `49751b4` (1,331 passed, coverage 100%), #100 on macOS. CI green on Ubuntu, Windows and the
review job on each merged head. Mutation (`mutmut`): #102 at `50b6363`, 1,275 mutants, 1,265
killed, 10 equivalent; #100 at `b0bc8bc`, 377 of 392 killed, 13 equivalent, 2 closed by tests
added after.

**Ledger.**
- `1C-2b task=1 agent=mx-feature fix-rounds=2 gates-first-pass=y`
- `1D-1d task=walk agent=mx-feature fix-rounds=1 gates-first-pass=n`
- `1D-1d task=low-batch agent=mx-feature fix-rounds=0 gates-first-pass=y`

**Plans written.** 1B (the Decimal kernel and forecast, 11 PRs), 2A (run state in SQLite, 5)
and 2B (checks, 6, with a second part after 1B). Drafted by architect agents against the
predecessor at `9d040f8`; the rulings are the coordinator's. Their sub-sessions are proposed
and wait for the owner to start them: the app does not start a session from an unattended
turn. The 1A sub-session is archived; its review reports were copied to the coordinator's
notes folder first.

**Rulings by the coordinator.** In the plans. The ones the owner may want to see:
- 1B ports what the launcher calls, about 2,500 of 9,565 legacy lines (the plan's table); the statement frames are
  deferred, so the Model page's statement rows beyond the sixteen measures have no Python
  source yet. Nothing is defaulted: a missing currency is refused (the predecessor read USD).
- 2A: a call left open by a crash stays unknown, and such a run cannot resume until the owner
  rules; an operator settle would need a decision record.
- 2B computes the confidence score exactly; the predecessor's float differs by one point in 59
  of 400,000 random sets, one a band change.
- 1C: the open Medium M2 of #36 (part of a Windows user name left by `home_paths`) is fixed in
  PR 2c, before the session driver.
- 1D: when a pin is created, a link swapped in between the path check and the open is hashed
  and pinned. Accepted as a limit.

**Not verified.**
- Any live event stream: order, per-attempt against cumulative usage on a retried turn,
  whether the runtime reuses an envelope id, that one nano-AIU is 1E-11 USD.
- The walk on a real Windows file system outside CI; on Windows CI every row for a name
  Windows normalises or cannot hold is skipped, so `notes.` beside `notes` is simulated only.
- Mutation was not rerun on `49751b4` or `a9a8bba`.
- The three plans' "live on the launcher's path" rulings rest on reading the predecessor, not
  running it; SQLite's own documentation was not fetched for 2A.

## 2026-11-14 Roadmap back end: step 1A complete (PR 5); 1D PRs 1b and 1c

**Merged**, under the owner's delegation (decision 0006), each at the head named with every
check green, and its diff read by the coordinator. Step 1A (the handoff parser) is complete.

| PR | Step | Head, merge | Content |
| :--- | :--- | :--- | :--- |
| #78 | 1A PR 5 | `15c1321`, `db5219a` | Gaps, typed data sections, registers, blocked flag, known source names, one synthetic new-format fixture (744 counted lines) |
| #59 | 1D PR 1b | `5dec6a3`, `7bf6fd0` | Capped read, path resolution, symbolic-link refusal (707 lines) |
| #82 | 1D PR 1c | `1c09ce2`, `302f5d7` | `read_capped` refuses a final link on Windows; `COM0` and `LPT0` reserved (89 lines) |
| #81 | records | `e95ef49`, `56cced5` | The entry below this one, the addendum to decision 0009, the 1C plan rules |

**Reviews.**

| PR | Task reviews | Sweep discovery | Whole-branch (`mx-architect`, adversarial) |
| :--- | :--- | :--- | :--- |
| #78 | `mx-precise`: both approved, Low 1 fixed | 0 confirmed defects | FAIL on `430e5b4`: Medium 1, Low 5, Info 7. Fixed in one round; scoped `mx-precise` re-review on `15c1321` approved |
| #59 | `mx-adversary` on the link refusal: FAIL, Medium 1, fixed and re-reviewed | 1 confirmed defect, Low, fixed test first | FAIL on `5b094bc`: High 1, Low 2, Info 4. Fixed; `mx-adversary` re-review on `5dec6a3` PASS |
| #82 | scoped `mx-adversary` PASS, Low 1, Info 3 | 0 confirmed | PASS on `1c09ce2`: High 0, Medium 0, Low 1, Info 5 |

- #78's Medium: a register heading id was recognised only in dotted form, fitted to the 25
  fixtures; a real new-format reply has `T1` to `T8`, which were silently missed.
- #59's Medium: an `OSError` from the link test escaped untyped. Its High: the Windows gate was
  red on the reviewed head, because a key row written by the controller asserted the error
  type Linux raises; the production code was right. The controller had dispatched the review
  before reading Windows CI.
- #78's reviewers each rebuilt the answer keys with their own reader: no difference on the 25
  fixtures or the new one.

**Gates and CI.** `uv run --locked python tools/gates.py` exit 0, each by its controller, on
`15c1321`, `5dec6a3` and `1c09ce2`. CI green on Ubuntu, Windows and the review job on each
merged head. On Windows every symbolic-link and junction row ran in #59 and #82; rows still
skipped there are a FIFO, opening a directory and two `chmod` rows. Mutation on #59
(`mutmut`, at `5b094bc`): 173 of 173 killed.

**Ledger.**
- `1A-5 task=0 agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `1A-5 task=1 agent=mx-feature fix-rounds=0 gates-first-pass=n`
- `1A-5 task=2 agent=mx-feature fix-rounds=0 gates-first-pass=n`
- `1A-5 task=whole-branch-M1 agent=mx-feature fix-rounds=1 gates-first-pass=n/a` (not reported)
- `1D-1b task=2(link refusal) agent=mx-feature fix-rounds=1 gates-first-pass=n`
- `1D-1b task=low-batch-2 agent=mx-feature fix-rounds=0 gates-first-pass=y`
- `1D-1b task=sweep-defect(NUL folder) agent=mx-feature fix-rounds=1 gates-first-pass=n`
- `1D-1c task=1 agent=mx-feature fix-rounds=0 gates-first-pass=n`

**Rulings by the coordinator.** In the 1A and 1D plans. The ones a later step depends on:
- A module citation `name (CP-X)` is read as a module before the Sources-table names are
  tried. Citations inside table cells have no reader; delivery's trace control (phase 4) needs
  one before it draws them.
- `Reader.blocked` is unknown, not false, for an earlier-format handoff.
- Step 2B refuses a repeated register id and checks Sources-table names against pinned sources.
- Ruled for the folder walk (#100, open, not in `main`): it refuses a folder with two names
  that differ only by case or Unicode form.
  The coordinator first ruled both are pinned as listed, against an earlier ruling; the 1D
  controller raised the conflict and the earlier ruling stands.
- The first layer that prints or stores a `SourceError` encodes with `backslashreplace`.

**A committed answer key was edited once.** #78's `data.json`: `blocked` false to null for
the 20 earlier-format files, by the controller after the coordinator's ruling; the re-review
confirmed only those 20 values changed.

**For the owner.** `main` has no branch protection: the Windows job is read by hand before
each merge.

**Not verified.**
- `npm --prefix web run gates` for #78: it fails in the 1A worktree on lint errors in web
  files the PR does not touch, cause not found; CI ran no web job on these PRs.
- No mutation tool ran on #78 or #82 (hand mutants by reviewers on #82).
- Nothing ran on a real Windows work PC: long paths, 8.3 names, OneDrive placeholders and
  other reparse points. That Windows treats `COM0` and `LPT0` as devices.
- No fixture or retained reply holds an empty cell or text on a tag's own line; the 14-row
  form of Confidence inputs is tested by synthetic rows only.
- The gap between a link check and the open is not closed.

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
