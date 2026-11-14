# States 2: confidence outcomes, run end reasons and module states

## 1. Purpose and status

A design-stage document: the factual base for drawing three back-end states no merged page shows
today. Nothing is decided. The inventory (Topics 1 to 3, read 2026-11-14) is followed by the
Proposal (questions in the draft record [0013](../decisions/0013-states-2.md)), the Build outline
and [the mocks](mocks/states-2.md); no reader has seen the mocks.

Status words. **main (merged in #312)**: in code on `main`; the `confidence.py` lines were read at
`23c00a4d` (the head of #312) and the diff to `origin/main` for `src/credit_os/checks/` is empty, so
they hold on `main`. **pending #303**: in code on the open pull request #303 (head `2fdd4ebf`), not
on `main`; may change. **plan text, no code yet**: a ruling only in a plan file on `main`;
`src/credit_os/orchestrator/` holds `__init__.py` alone. `confidence_outcome` is at
`confidence.py:240`.

## Topic 1: confidence outcomes

Source for every row: `src/credit_os/checks/confidence.py` (lines as at `23c00a4d`, unchanged on
`main`). Status of every row: main (merged in #312).

| Back-end word | Source line | When it arises | What the reader needs to know |
| :--- | :--- | :--- | :--- |
| `scored` | `:64` (`state` literal); built `:94`, `:97`, `:100`; reached `:233` | 14 rows, every check passes, no finding (`:227-233`). Ruling C10 (rulings-proposed.md): carries `value` 0 to 100, `band`, `status` | A module's figure, band and status |
| `blocked` | `:64`; returned `:222` | The one row `Not assessable` / `Not supplied: <reason>` in a blocked module (`front_matter_blocked` or `is_blocked`), no finding (`:107-111`, `:220-222`; docstring `:11-13`). Rulings C7, D14 | No score was possible because the module was blocked; nothing is wrong with it |
| `absent` | `:64`; returned `:195` (no section), `:242` (earlier format) | No `confidence` data section (`:189-195`), or the earlier format, never scored (docstring `:16-17`; `:241-242`). `confidence.absent` is a finding only when `context.scored` is true (`:191-194`; ruling C1) | Nothing was asked of the module, or the document predates scoring; the word alone does not say which |
| `refused` | `:64`; returned `:195`, `:211`, `:222`, `:226`, `:231` | Any finding other than `confidence.absent` (docstring `:14-15`): front matter holds `confidence_score`, `confidence_band` or `qa_status` (`:59`, `:114-126`); a second section (`:196-200`); a misplaced or table-less section (`:203-211`); `Not assessable` row in a module not blocked (`:223-226`); wrong rows, counts or ranges (`:227-231`). Ruling R65: any `confidence.*` refusal gives `refused` and no value | The inputs were wrong; the module needs a retry. The reason is a finding, not a reader sentence (2B plan line 74: page wording is delivery's, 3B) |
| Bands: `High`, `Medium`, `Low`, `Insufficient Information` | `:66`; `_band` `:71-72`, `:73-74`, `:75-76`, `:77` | `value` at least 80; 60 to 79; 40 to 59; below 40 | Confidence 80 to 100; 60 to 79; 40 to 59; 0 to 39. The last has the words of a lineage row (`:42`) |
| Status: `Passed`, `Restricted`, `Blocked` | `:67`; `:100`, `:95-99`, `:92-94` | Scored with `CRITICAL` and `MATERIAL` both 0; `MATERIAL` above 0 and `CRITICAL` 0, value capped at 59 (`:96`); `CRITICAL` above 0, value capped at 39 (`:93`) | No cap; a material finding capped it at 59; a critical finding capped it at 39. Status `Blocked` is not outcome state `blocked` |

Also in the 2B plan (`docs/superpowers/plans/2026-11-14-phase-2b-checks.md:128`, Score row): "any
critical caps at 39 (Blocked), else any material at 59 (Restricted), else Passed ... 80 High, 60
Medium, 40 Low, below that Insufficient Information"; "a score only when scored". D14 (`:147`):
blocked is `Reader.blocked` true or front matter `module_status: blocked`.

**Blocked and scored.** A blocked module that writes the 14 rows is checked and scored like any
other: the `Not assessable` branch of `_read_table` is taken only for the one-row table
(`confidence.py:220-226`), else the code falls to `:227-233`. Sources: ruling C7 ("A blocked module
that writes the 14 rows instead is checked and scored as any other"); 3A plan D28
(`docs/superpowers/plans/2026-11-14-phase-3a-orchestrator.md:169`). So a "Not assessable" module can
hold a scored outcome with status `Blocked`, `Restricted` or `Passed`; no source says how to show
that pair.

**Run-level confidence.** The sources rule none: `confidence_outcome(document, context)` takes one
document (`confidence.py:240`); the 2B and 3A plans and the roadmap hold none; the predecessor
computed it per handoff only (`apps/issuer-library/credit_os/store.py:1070-1077`, below). No file
under `web/src` or `web/fixtures` contains the word.

## Topic 2: run end reasons

Source: 3A plan G3, `docs/superpowers/plans/2026-11-14-phase-3a-orchestrator.md:235` (coordinator,
2026-11-14), with D6 (`:147`), D7 (`:148`), D9 (`:150`), G5 (`:237`), G7 (`:239`). All **plan text,
no code yet**: `grep` of `src` finds no `stop_reason` or end-reason word outside `provider/` and
`signal/`. G3: "The set is closed and keyed in PR 3". The reasons, their sources and when each
arises are in one table under Proposal, Topic 2.

`StoreUnusable` (D9 `:150`; D29 `:170`; D30 `:171`; G3 `:235`): "always ends the run: never retried,
never swallowed, never followed by an end write", and it "writes nothing". The store holds no end
reason for it; the activity slice calls the same case an unreadable record
(`web/src/pages/run/slice-activity.ts:72`, kind `unreadable`), though no source ties the two. A run
whose total is unknown "does not resume by itself" until the owner settles the call (D7 `:148`, G7
`:239`); the plan names the action, not a state word. G3's assumption (`:214`) that the set starts
from the predecessor's six classes was not kept (names: Prior art).

**The kit's seven Run states** (`web/src/components/status/sets.ts:28-36`) and the G3 reasons each
could hold: Queued (`:29`) and Running (`:30`): none, live states. Finished (`:31`): `completed`.
Failed (`:32`): provider failure not retried; provider raised. Capped (`:33`): `stopped` (capped).
Rejected (`:34`): none in G3; the plan refuses a run at launch over 200 files or 400 MiB (D16
`:157`) but names no end reason. Interrupted (`:35`): none in G3; G4 (`:236`) uses "failed as
interrupted" for an attempt a stop left open, not the run. The three other `stopped` reasons match
no kit word, and `stopped` has no kit state; no source rules which each takes. The predecessor
(`src/deploy_workflow/inbox/runs.py:24`, `:265-286`): `delivered` is `finished`; `stopped` with
reason `budget` is `capped`; any other stop is `failed`, "stopped: <reason>"; no event and no exit
code is `interrupted`; else `failed`. Shapes and tones are in the R-A paragraph below.

The slices carry only the kit's seven words, no end reason, no `stopped`, no spend-unknown flag:
library `RunState` (`web/src/pages/library/slice.ts:11`) in `IssuerCard.state` (`:39`),
`HistoryEntry.state` (`:75`), `RunHead.state` (`:125`); run activity `RUN_STATES`, `RunState`
(`web/src/pages/run/slice-activity.ts:18-26`, `:35`) in `RunRecord.state` (`:55`) and
`ActivityLine.state` (`RunState | "Not assessable"`, `:47`); model `RunState`, `RunHeader.state`
(`web/src/pages/model/slice/types.ts:22`, `:29`). Run activity also carries `alert: RunAlert | null`
(`:38`, `:58`), allowed only for Failed, Capped, Rejected or Interrupted (`:164-167`), with a
delivered title, text and action: the one place a run's reason is a sentence today.

## Topic 3: module states

Source: 3A plan G1, `docs/superpowers/plans/2026-11-14-phase-3a-orchestrator.md:233`: "The run goes
on after a module ends unaccepted. A module whose required producer has no accepted handoff is not
run and is shown as a gap with that reason; with only an optional producer missing it runs
restricted." Both **plan text, no code yet** (plan `:212`; no code word for the first). `edge_rule`
is named by the plan (`:101`) but is in no file of `src` on `main`; the predecessor has it
(`src/deploy_vii/execution.py:48`, `:262`) at `8e3954a`. A missing required producer means the
module did not run, and why; a missing optional one, that it ran with less input than designed, its
analysis carrying that limit.

The kit's "Module state" set (`sets.ts:63-68`): Delivered (filled circle, success, `:64`), Delivered
with gaps (dashed ring, gap, `:65`), Not assessable (slashed circle, neutral, `:66`), Not run (ring,
neutral, `:67`). Rules (`docs/design/design-system.md`): "Not run" only in a run that has ended,
sharing the ring with Queued so the two never meet (`:374`, `:407-408`); the slashed circle is "Not
assessable" alone (`:359`); a module that fails inside a run reads "Not assessable" (`:405-406`);
each state in a set has its own shape (`:362-363`). The kit has no word for "runs restricted"; "Not
run" fits the first row, but no source maps the plan's missing-producer case to it.

The library slice carries `ModuleState` (`slice.ts:155`) in `ModuleItem.state` (`:161`),
`Module.state` (`:426`) and `TimingRow.state` (`:530`); `Module.body` is delivered or blocked
(`:423-428`), whose comment (`:419-422`) says "a blocked one carries 'Not assessable' or 'Not run'";
`BlockedBody` has `reason`, `note`, `gapsLink` (`:412-417`). The activity slice has its own
`ModuleWord` (`slice-activity.ts:27-36`: Queued, Running, Finished, Interrupted, Not assessable, Not
run).

**Word clash.** `Restricted` is a confidence status (2B plan `phase-2b-checks.md:128`;
`confidence.py:67`, `:98`) capping a score at 59; G1's "runs restricted" is a module that ran with
an optional producer missing. `Blocked` is a confidence status (critical finding, cap 39), a
confidence outcome (`blocked`) and, in D14, a blocked module. They must not be confused in any
wording or shape.

## Where each state would appear

Cells: the component today (file:line; ids in `component-map.md`), its slice field, or nothing.

| Place | Topic 2, run end (Topic 1: nothing drawn) | Topic 3, module states |
| :--- | :--- | :--- |
| Library home card and list; Report history; Run frame head | `StatusBadge` "Run states": `IssuerCard.tsx:24` (R10, S1), `IssuerList.tsx:179` (S1, State column), `RunFeed.tsx:27`, `:50` (R11, S1), `RunFrame.tsx:140` (N4, S1); fed by `IssuerCard.state` `slice.ts:39`, `HistoryEntry.state` `:75`, `RunHead.state` `:125` | Nothing; `progress` text only on the card (`slice.ts:45`, F4); `tabs.modulesCount` (`slice.ts:126`) |
| Overview modules list; Module page head | - | `ModuleItems.tsx:54` (R7, S1; "Module state"); `ModuleItem.state`, `slice.ts:161`; `Overview.tsx:88`; head: Delivered: `Module.tsx:181-183` ("Module state" badge). Blocked: `Module.tsx:105-122`, "Not assessable" the `Blocked` component with `body.reason` (`:115-116`), "Not run" or other a badge and the reason sentence (`:117-122`); `Module.state`, `slice.ts:426` |
| Evidence Record tab | Nothing: the library `RunRecord` (`slice.ts:558-591`) has `timings`, `hashes`, `spend` (progress text and bar), `calls`, `registers`, no run state or end reason | `EvidenceRecord.tsx:56` (S1, timings end column); `TimingRow.state`, `slice.ts:530` |
| Run started and Readiness pages | Nothing: `Started.tsx` is an info `Alert` with the cap bar (S4, F4), no state; `Readiness.tsx:13` draws "Met or not met" (R6, F4) | Nothing |
| Run activity page | `ActivityPage.tsx:163` (S1, `live` flag); `RunAlert.tsx` (S4); `RunRecord.state` `slice-activity.ts:55`, `.alert` `:58` | `ModuleSteps.tsx:44-50`, `:164` (I5 with S1; "Not assessable" and "Not run" take "Module state", every other word "Run states"); `slice-activity.ts:39`, `ModuleWord` `:27-36` |
| Model run header | `ModelShell.tsx:74` (N4, S1); `RunHeader.state`, `model/slice/types.ts:29` | Nothing; the mocks draw a "Not assessable" part outside the header (`docs/design/mocks/model.md:20`, `:69`) |

## Proposal

Nothing here is decided. Back-end words keep the inventory's status: confidence **main**, run status
words **pending #303**, run end and module words **plan text, no code yet**. A word proposed for the
reader is listed with the back-end word it stands for. Contrast figures are the design system's
(`docs/design/design-system.md:154-200`) unless marked "computed" (see Not verified).

### What the sources settle before any option

| Outcome | Makes a refusal | Can the handoff be accepted | Source |
| :--- | :--- | :--- | :--- |
| `refused` | Always, a `confidence.*` refusal | No | Every `refused` return follows a finding: `confidence.py:195` (`found` holds a front matter finding, `:187`, `:114-126`), `:211` (after `confidence.unreadable`, `:208-210`), `:222`, `:226` (after `confidence.blocked-row`, `:225`), `:231` (`if found`). Every finding is built by `refusal(...)` (`findings.py:96-99`); none is a warning. `check_handoff` runs it on a new-format document (`run.py:71`) and on one the reader refuses (`run.py:45`). "A handoff is refused when any finding is a refusal" (2B plan `:89`). All 34 `refused` cases of `tests/checks/expected/confidence.json` expect a `confidence.*` refusal |
| `absent`, `scored` true, new format | Yes, `confidence.absent` | No | `confidence.py:191-194`; state stays `absent` (`:195`; ruling R65). Key cases 23 and 49 (from 0, as the test's `CASES[60]`) |
| `absent`, `scored` false, new format | No | Yes | `confidence.py:189-195`; ruling C1 |
| `absent`, earlier format | Yes, `structure.format` | No, as a new handoff | `run.py:48-54`; `structure.py:49-64`; `confidence.py:241-242`; `test_checks_confidence.py:169-178`; 3A D19 (`:160`) |
| `blocked` | No | Yes; the module is blocked (D14) | `confidence.py:220-222` |
| `scored` | No confidence finding | Yes, if no other check refuses, a blocked module that wrote the 14 rows included | `confidence.py:227-233`; ruling C7; 3A D28 (`:169`); key case 33 (blocked, 89, High, `Passed`) |

From accepted to delivered: an attempt is "written, checked, accepted or refused ... the third
refusal ends the module" (3A D4, `:145`) and goes `replied` to `accepted` or `rejected` (2A plan
`:138`); a delivery is recorded "only when the run is `finished` or `stopped` ... and each module
named has an accepted attempt in this run whose reply has that SHA-256" (2A plan `:142`); a `failed`
run may not be admitted (2A D10, `:158`). So beside delivered content can stand `scored` and
`absent` (nothing asked); `blocked`, and `scored` in a blocked module, belong to an accepted handoff
of a blocked module (the blocked body `slice.ts:412-428` is assumed to carry it). `refused`,
`absent` while scored, and the earlier format belong to an attempt not accepted, met only as the
reason for "Not assessable" after a third refusal, and on Evidence. Four points stay open (question
6):

- Everything after `check_handoff` is plan text: `orchestrator/` and `delivery/` hold `__init__.py`
  alone, `admit_delivery` is in no file of `src` on `origin/main`, step 3B has no plan.
- A retained earlier-format run: 2B D1 (`:134`) gives as its cost "Delivery of a retained earlier
  run must not gate on findings"; the 1A plan (`:204-206`): "Delivery draws no earlier-format
  paragraph unless a reader for them is added". Whether it is ever delivered is not ruled.
- "One verdict per attempt, written once; resume does not re-judge" (2A D8, `:156`): a changed
  checker run later could make an accepted reply read `refused`.
- No source says where delivery gets the outcome: the store has no confidence column (2A plan
  `:97-103`); `scored` comes from the orchestrator's catalogue (2B D3 `:136`; 3A D1 `:142`).

**The score's status marks a ceiling, not a cut.** `Restricted` is `min(value, 59)`, `Blocked` is
`min(value, 39)` (`confidence.py:93`, `:96`), so 54, `Low`, `Restricted` is possible: words must say
"cannot be above", never "was reduced to". By `_band` (`:70-77`), `Blocked` is always `Insufficient
Information`, `Restricted` is `Low` or `Insufficient Information`, and `High` and `Medium` are
always `Passed`.

**The store's run statuses.** The 2A plan (`:137`) and #303 (`src/credit_os/store/runs.py:39-41`,
`db.py:159-172` at `2fdd4ebf`): `created`, `running`, `rejected`, `finished`, `stopped`, `failed`.
G3 writes `completed` for the store's `finished` (question 10). `rejected` is "End a created run as
rejected" (`db.py:160`); "A run with any call cannot be `rejected`" (2A plan `:137`); decision 0006
ruling 7 says when, and G3 omits it. No status is `interrupted`: a run whose process ends without an
end write stays `running`, with "no heartbeat, no operating-system lock" (2A D5, `:153`), so nothing
produces the kit's "Interrupted" for a run (question 11).

**The plan calls a module with a missing required producer "blocked"**: 3A PR 7c delivers "blocked
and restricted modules" (`:304`), its key holds "a blocked and a restricted dependant" (`:274`).
**Shown text is a fixed sentence**: "A surface an analyst sees may carry only the failure's class
and a fixed sentence, never provider text" (decision 0012 item 7; 3A D10, `:151`); every reason line
below is chosen by a closed key, with a module name or the cap amount filled in: no provider text,
check id or module code.

### Topic 1: confidence

**The reader.** A portfolio manager weighing a module's judgement needs how far its claims rest on
evidence, to know which to lean on and which to challenge in Evidence. It qualifies a judgement; it
is not a fact about the issuer, nor a state of the run or module. The score is built from claim
evidence, fields present, the source gate and findings by severity (2B plan `:128`). Run-level
confidence: none ruled; no option has a page work one out.

| | C-A: a scale beside the judgement (recommended) | C-B: one sentence at the module | C-C: wherever a module or run is listed |
| :--- | :--- | :--- | :--- |
| Reader sees | Delivered modules only. Overview row: marks and band word, or "Not scored"; nothing on a "Not assessable" or "Not run" row; if no module is scored, one sentence under the heading, "No module in this run was scored.", and no row element. Module head: caption "Confidence", marks, band word, "77 of 100", a ceiling sentence for `Restricted` or `Blocked`, the link "How this was scored"; "Not scored" and its reason if unscored; nothing on a "Not assessable" or "Not run" module | One line under the name: "Confidence: medium, 77 of 100." or "Confidence not scored: nothing was asked of this module.", same link; `small` `#474A4F` on the canvas (8.23, computed), link `#001AFF` (7.49). Nothing on the Overview | The C-A scale on every row, "Not assessable" included with "This scores the evidence for what the module did state."; on home card, list, history, run head and finished activity steps, a tally ("2 high, 2 medium, 3 low, 2 not scored") as text or a label badge (`#474A4F` on `#F4F4F5`, 8.09) |
| Component, cost | F7, "a strength on a short scale" (`component-map.md:94`), four marks; Build outline. Nothing in any other place | None; `Module` gains one sentence. Nothing in any other place | F7 and a tally; also `IssuerCard`, `HistoryEntry`, `RunHead` and the activity slice, with `library.json` and `run.json` throughout; the Evidence Record tab gains the Confidence register under all three |
| Gives up | Ranking runs or issuers by it; a blocked module's score and the status words are off findings pages | Comparing modules at a glance, the main use; easy to miss in a head of text; the "flat" presentation the owner's rules call a defect. Cheapest, closest to the predecessor | The calm of run-level places, where the reader chooses an issuer; needs a ruling that a tally is a count, not a run-level confidence, and a meaning for a blocked module's score; "3 low" beside a state badge reads as something wrong with the run |

**C-A in full.** Form, not a badge: no fill, no edge, no status colour. Marks, word and number
`#000533` on the canvas `#F6F5FF`, 18.16 (card 19.64); unfilled marks `#63676E`, 5.26 (card 5.68),
as the built piece draws them (`Rating.tsx:17`; `web/src/styles/theme.css:158`). Marks by band:
`High` 4 of 4, `Medium` 3, `Low` 2, `Insufficient Information` 1 (word "Insufficient information");
the number reads "77 of 100".

- Filled marks are the cue that does not rest on colour; the band word always sits beside them. High
  is not green and low is not a warning: confidence is not a state. The lowest band fills one mark,
  so a scored module never looks unscored. The caption "Confidence" is `caption` type in `#63676E`
  (5.26), with an info trigger opening the kit's tooltip
  (`web/src/components/base/tooltip/tooltip.tsx`, as `MetricCard.tsx:23-31`) with one delivered
  sentence on what the score measures and where the bands start. Accessible name "Confidence:
  medium, 77 of 100". The Overview row shows marks and band word only.
- **Source of the scale.** F7, read live 2026-11-14 at
  <https://www.shadcnblocks.com/components/rating>: 15 rating blocks, among them read-only ones
  ("Rating Readonly", "Rating Kibo Readonly": a non-interactive four-star display) and "Rating With
  Score" (stars plus an explicit number); every variant draws stars. The page says "accessible Radix
  UI or Base UI"; `component-map.md:94` says F7 is "built on React Aria", which the page does not
  confirm. The built `web/src/pages/signal/parts/Rating.tsx` (three `Star01` marks from
  `@untitledui/icons`, a supplied word, read-only) means no new dependency: C-A is its four-mark
  variant, moved to the kit.
- **One scale for both uses** (question 2): Signal strength and module confidence are one kind of
  information, a judgement's strength on a short ordered scale read as marks plus a word, so one kit
  scale serves both, differing only in mark count and word set, both supplied by data; the rule
  forbids one component for different kinds, not the same kind. Alternative: a different mark for
  confidence (for example filled segments), at the cost of a second component.

Status words. `Passed` shows nothing; `Restricted` and `Blocked` show one sentence under the scale,
`#474A4F` on the canvas, 8.23 (computed; card 8.90): "Cannot be above 59: a material finding was
recorded." and "Cannot be above 39: a critical finding was recorded." The words stay on Evidence:
"Blocked" would sit on a "Delivered" module and beside modules read "Not assessable" because
blocked; "Restricted" beside a module that ran restricted (Topic 3), and to this reader means a
restricted-list issuer. What a "finding" is here, and whether the word may sit near "Key findings",
the design cannot settle (question 4). No score: never a 0, never a blank beside scored modules,
never a badge; the text "Not scored" in `#63676E` (5.26 canvas, 5.68 card), as the design system
draws a missing figure (`design-system.md:127`), and a reason sentence in `#474A4F` (8.23 computed,
8.90 card). Delivery tells the two `absent` cases apart from the document's format and the
catalogue's `scored` flag.

| Outcome | Where the reader can meet it | Reason sentence (fixed) |
| :--- | :--- | :--- |
| `absent`, nothing asked (`scored` false) | A delivered module's head and row; Evidence | "No confidence score is asked of this module." |
| `absent`, earlier format | Only if a retained earlier-format run is ever delivered (question 6); Evidence | "This report was written before confidence scoring." |
| `blocked` | Evidence only: the module reads "Not assessable" with its own sentence | "The module could not make its assessment and stated no scoring inputs." |
| `refused` | Evidence only: the attempt was not accepted | "The scoring inputs of this attempt could not be read.", then the refusals as recorded |

Blocked and scored: a "Not assessable" module can hold a score, even high (key case 33). C-A shows
none for a module with no delivered judgement, so the pair never meets the reader on a findings
page; the Evidence register lists it with "Scored although the module reads Not assessable: it wrote
the fourteen inputs.", which restates the rule (question 5). If every module is `absent`, thirteen
"Not scored" rows would be noise: delivery sends one list sentence and no row element (the reader
holds the two forms apart); heads still read "Not scored".

**Evidence gains** on the Record tab ("registers as written", `component-map.md:239`) a **Confidence
register**, the R13 table in `sm` rows (`component-map.md:113`): per module, outcome as written
(`scored`, `blocked`, `absent`, `refused`), score, band, status as written (`Passed`, `Restricted`,
`Blocked`), and the reason sentence where there is no score. An open row shows the inputs as
written, as a details list (R2) in four groups: claims by evidence class (eight rows), fields
present and total, the source gate, findings by severity (three rows); for a `refused` attempt, each
refusal's check id, line and sentence. Cells are audit text, not badges: `#000533` on a card
(19.64), "n.a." `#63676E` (5.68); no intermediate formula value (`confidence.py:63-67`). A module
with no accepted handoff has a row saying so, with its last attempt's refusals.

**Recommendation: C-A.** A reader scans which judgements rest on thin evidence and reads one module
with that in view; C-A puts confidence at those two places, plainly not a state badge, with the
audit trail one link away, and needs no ruling the sources lack. C-B fails the first use; C-C
answers a question (how good is this run) no source defines. Deliberately not shown: run-level or
issuer-level confidence; the status and outcome words, inputs, check ids and refusals outside
Evidence; intermediate formula values; a change between runs (2B D4, `:137`, leaves that to step
5A).

### Topic 2: run end

**The reader.** A portfolio manager needs to know whether the library is whole and, if not, why it
ended and whether it can be read; the analyst needs the next action and the truth about money. The
back end gives three end statuses (`finished`, `stopped`, `failed`), six reasons in a closed set,
`rejected` for a run that never ran, and nothing for a run that ended without an end write. A
`stopped` run can be admitted and read, a `failed` one cannot (2A D10, `:158`; decision 0006 rulings
5, 6, 12).

| | R-A: one "Stopped" state carrying its reason (recommended) | R-B: "Capped" stays, "Stopped" joins it | R-C: a state for every reason |
| :--- | :--- | :--- | :--- |
| Run states set | Queued, Running, Finished, Failed, **Stopped**, Rejected, Interrupted | Queued, Running, Finished, Failed, Capped, **Stopped**, Rejected | Queued, Running, Finished, Failed, Capped, **Spend not known**, **Cost control**, **Stopped by the analyst**, Rejected, Interrupted |
| Reader sees | State badge, then the reason as a label badge on home card, list, history, run head (with a reason line under the header), run activity (label among the header's labels; the alert with sentence and next action; the Spend figure) and Model header; Evidence Record gains "How the run ended" (state, sentence, reason and status as the store holds them) and a spend section that can say "not known" | "Capped" as now; "Stopped" (pause bars, warning) for the other three `stopped` reasons with R-A's label and line; "Interrupted" leaves the run set; a run with no end record reads "State not known" (dashed ring); the module word "Interrupted" needs a home outside "Run states" | One badge, the reason's own state, where R-A shows two |
| Cost | `sets.ts:33` "Capped" becomes "Stopped"; no new shape or component (Build outline) | `sets.ts:35` "Interrupted" becomes "Stopped"; module word (`slice-activity.ts:31`; `ModuleSteps.tsx:49`) needs its own entry; `library.json` one place and `run.json` three that read "Interrupted" | Not costed: cannot be built inside the design system's rules |
| Gives up | "Capped", seen on merged pages and in earlier mocks; a reason readable from the shape alone; a renamed kit word with fixtures and tests | One store status (`stopped`) with two shapes; pause bars meaning a deliberate stop on a run and an interruption on a module; a run with no record loses its own word | Blocked: seven of ten shapes are used; left are the square ("settled, approved"), the dashed ring (a gap alone) and the slashed circle ("Not assessable" alone). "Ten shapes, each with one meaning" (`design-system.md:347-360`) would have to change first |

**R-A in full.** Shapes and tones are the kit's (`sets.ts:31-35`); one word changes. Finished:
filled circle, success, text `#0C6639` on `#E8FFF4` 6.74, mark `#0F8048` 4.77, store `finished` (G3
writes `completed`). Stopped: triangle, warning, text `#664F00` on `#FFF9E5` 7.43, mark `#997700`
3.99, store `stopped`, replacing "Capped" (`:33`). Failed: diamond, error, text `#8E413E` on
`#FDF0F0` 6.35, mark `#A54C48` 5.07, `failed`. Rejected: cross, neutral, `#474A4F` on `#F4F4F5`
8.09, `rejected`. Interrupted: pause bars, warning, as Stopped; no store status, the store still
holds `running`.

The reason is a label badge (the design system's qualifier form: word only, neutral, `#474A4F` on
`#F4F4F5`, 8.09; `design-system.md:342`) plus a fixed sentence; wording is proposed (question 9).

| End reason (G3, word for word), status word | Source and when it arises | State | Label | Reason line (the amount is the run's cap) |
| :--- | :--- | :--- | :--- | :--- |
| "completed", `completed` | Plan `:235`. The run finished | Finished | None | None |
| "the cap" (capped), `stopped` | `:235`. `spent + next hold <= cap` before every call, equal passes (`:179-180`); cap USD 20 (`CLAUDE.md`, decision 0002) | Stopped | Spending cap | "The run stopped before a model call that could have taken it past its USD 20.00 spending cap." |
| "unknown spend", `stopped` | `:235`; D6 `:147`. A `None` charge on a sent request, or a compaction unfinished, failed or with no charge: the total becomes unknown, never zero | Stopped | Spend not known | "The run stopped because the cost of a model call was not reported. What the run has spent is not known." |
| "a charge above its hold", `stopped` | `:235`; G5 `:237`. A known charge exceeds its hold; "the hold arithmetic is then wrong for every later call"; the charge is recorded exactly | Stopped | Cost control | "The run stopped because a model call cost more than the amount set aside for it, so the cap could no longer be relied on." |
| "a stop asked for by the operator", `stopped` | `:235`, `:361`. Decision 0006 ruling 5; "taken between calls, never inside one" | Stopped | By the analyst | "The analyst stopped the run." |
| "a provider failure that is not retried", `failed` | `:235`. The provider fails and the failure is not retried | Failed | Model service | "The model service failed and the run could not go on." |
| "an exception out of `complete`", `failed` | `:235`; D7 `:148`. `complete` raises; it "leaves its call open, so spend is unknown (D7)" | Failed | Model service, then Spend not known | "The model service returned an error during a call. That call was left open, so what the run has spent is not known." |
| A created run ended as `rejected` | Store; decision 0006 ruling 7 | Rejected | None | The sentence the pages carry today |
| No end record; the store holds `running` | `StoreUnusable`, below | Interrupted | None | "The run ended without recording why. Its last recorded activity was at 14:56." |

On the run activity page the sentence sits in the merged alert (`activity/RunAlert.tsx`), which
draws the shape on a card: Stopped `#997700` on `#FFFFFF`, 4.21; Failed `#A54C48` on `#FFFFFF`, 5.63
(computed; a mark needs 3); title `#474A4F` (8.90), text `#63676E` (5.68). A second fixed sentence
says what can be read: "Nine of thirteen modules were delivered and can be read." (stopped);
"Nothing from this run is shown." (failed; decision 0006 ruling 12).

Failed with spend unknown differs from plain Failed three ways: (1) the label "Spend not known"
follows "Model service"; (2) the Spend figure reads "n.a." in `#63676E` (5.68 on a card), no bar,
with the note "Not known: a model call was open when the service returned an error." (form exists:
`slice-activity.ts:49-50`, `activity/Summary.tsx:25-32`); (3) the alert says "This run cannot be
resumed until the cost of that call is entered." (G7, `:239`), not "Review and start again". Unknown
spend is never a 0, never the cap bar (F4 is "never used where no total is stated",
`component-map.md:92`), never a sum of known charges (the plan's total is "a `Decimal`, or unknown
with the lines that made it so", `:175`; question 12). The Evidence calls table shows each call's
own cost, the open call's cell and the total reading "n.a." (`slice.ts:537`); once the owner settles
the call (G7) the row carries "Stated by the owner" and the total is a figure.

`StoreUnusable` writes nothing, so no page can be told the end; two existing forms are used. Record
unreadable: the activity page's `unreadable` form, "State not known" (dashed ring, `#514D80` on
`#FFFFFF`, 7.71; edge `#827BCC`, 3.71), the alert "Run activity cannot be read", static skeletons,
no figure (`ActivityPage.tsx:93-122`). Record readable and still `running` with no process writing:
"Interrupted" with its sentence, spend following the store (D7 `:148`); never "Running" with its
pulse. How a writer knows no process is writing is in no source (2A D5), so "Interrupted" has no
back-end source and neither form can be chosen by rule (question 11).

**Recommendation: R-A.** The first question is whether the run ended whole, ended early leaving a
readable library, or failed: the store's three end statuses, one state and shape each; why it ended
early is a second question, answered in words beside the state. No design-system rule breaks and no
shape is added. Deliberately not shown: store status and reason identifiers outside Evidence;
provider error text; a spend figure when spend is unknown; "Running" with its pulse where the run
cannot be seen; a screen for settling an open call (G7 names the action; no source gives it a page).

### Topic 3: modules

**Reader and "ran restricted".** The reader needs to know whether there is a judgement to read and
whether how it ran should change how far to lean on it. G1 (`:233`): only an optional producer had
no accepted handoff, so the module ran with less input and is still delivered. "Restricted" stays
listed beside whatever the reader sees but is not proposed: it is also a confidence status and means
a restricted-list issuer. Proposed: **"Reduced inputs"** (back-end: "runs restricted", `edge_rule`).
Considered: "Limited inputs" (near "Limitations", a passage), "Partial inputs" (suggests "Read in
part"), "Without Peer comparison" (cannot name two producers).

| | M-A: a qualifier on the delivered state (recommended) | M-B: a fifth module state | M-C: in Limitations only |
| :--- | :--- | :--- | :--- |
| Reader sees | State stays "Delivered" or "Delivered with gaps"; the label badge "Reduced inputs" (word only, neutral, `#474A4F` on `#F4F4F5`, 8.09) after the badge on the Overview row and Module head; under the name a reason line (`#474A4F`, 8.23 computed) and a link to Limitations; Evidence timings gain an Inputs column ("Reduced inputs (restricted)", producers missing by name); the activity step reads "Finished" with the detail "Ran without Peer comparison." (`slice-activity.ts:39`). Nowhere else | "Reduced inputs" replaces the delivered state: that badge alone on the row; badge and reason line on the head; same Evidence and activity places | No mark; delivery places one sentence first among the limitations; the Inputs column on Evidence; nothing elsewhere |
| Cost | Build outline | A new shape and a rule change | Text only |
| Gives up | A second badge on some rows | The difference between restricted with gaps and without. Blocked: "Module state" and "Change state" share the Changes page, where the triangle and square belong to change state (`design-system.md:392-395`); the half-filled circle is ruled out for a delivered state (`:396-398`); the diamond, cross and pause bars mean nothing here | Any way to see, scanning the list, which judgements rest on less |

The reason line names each missing producer with its reason: "Ran without Peer comparison, which was
not delivered in this run." Delivery adds no analysis; what the module could not establish is its
own Limitations text.

**Not run for a missing required producer** (G1: "is not run and is shown as a gap with that
reason"; the plan calls it a blocked dependant, `:274`, `:304`).

| | N-A: "Not assessable", naming what it needed (recommended) | N-B: "Not run", with the reason |
| :--- | :--- | :--- |
| State, colours | Slashed circle, neutral, `#474A4F` on `#F4F4F5`, 8.09 | Ring, neutral, same colours |
| Reason line | "Not assessable: it needs Capital structure, which was not delivered in this run." | "Not run: it needs Capital structure, which was not delivered in this run." |
| Where | The badge on the Overview item, which keeps its place (`component-map.md:357`); the kit's blocked form on the Module page (`Module.tsx:104-131`; `components/gap/Blocked.tsx`); the badge in Evidence timings, no times; the badge on the activity step in a live or an ended run | The same, the Module page via its second branch (`Module.tsx:117-122`); in a live run it cannot be drawn: "Not run" exists "only in a run that has ended" and shares the ring with "Queued" so "the two never meet" (`design-system.md:374`, `:407-408`), and the slice reader refuses it (`slice-activity.ts:106-116`); under G1 the two would meet in one list |
| Rule it meets; gives up | Blocked modules are gap states "always with one sentence saying why" (`design-system.md:126`), which is how G1's "shown as a gap with that reason" is drawn today Gives up: the literal verb of G1; "Not assessable" also names a module that ran and could not assess, and the sentence carries the difference | Needs that rule changed, or a third word for the live case Gives up: a single meaning of "Not run" (today: the run ended first, and a resume may run it) |

Three reasons share "Not assessable", each a fixed sentence: the module's own (D14); "Its analysis
did not pass its checks after three attempts, so nothing from it is shown." (third refusal, D4;
where a `refused` outcome ends up); the missing producer, named. N-A needs no kit, slice or page
change: the sentence travels in `BlockedBody.reason` (`slice.ts:412-417`) and the step's `detail`.

**Recommendation: M-A and N-A.** M-A: reduced inputs qualify a judgement still delivered, and a
qualifier is the design system's form for that. N-A: the truth for this reader is that the topic
cannot be read in this run, and why; it is the existing word for a blocked module, true while the
run is live, and changes no rule. They deliberately do not show: "restricted" on a findings page; a
module code or catalogue edges outside Evidence; what the missing input cost the analysis unless the
module wrote it; a different badge for each of the three reasons for "Not assessable".

## Build outline

Not a plan; nothing decided: what C-A, R-A and M-A with N-A would change if ruled as proposed. Field
names are proposals; paths from the repository root; topic 1 confidence, 2 run end, 3 modules.

| File | Change | Topic |
| :--- | :--- | :--- |
| `web/src/components/status/sets.ts:28-36`; `sets.test.ts`, `StatusBadge.test.tsx` | "Capped" becomes "Stopped" in "Run states"; triangle and warning stay | 2 |
| `web/src/pages/signal/parts/Rating.tsx`; `signal/StoryCard.tsx:14`, `:124`; a new part beside it | `Rating` moves into `web/src/components/` as the shared scale (mark count and accessible name as arguments); the new part is the confidence line: caption and tooltip, scale, band word, number, ceiling sentence, link, and the "Not scored" form | 1 |
| `status/shapes.tsx`, `StatusBadge.tsx`, `gap/Blocked.tsx`, `gap/Missing.tsx`, `alert/Alert.tsx`, `base/badges/badges.tsx`; `design-system.md`, `component-map.md` | No kit change: no new shape, tone or badge form. The two docs are the coordinator's, after a ruling (proposed rows: design system, "Proposed (states 2, not ruled)") | all |
| `web/src/pages/library/slice.ts:161` (`ModuleItem`), `:423-428` (`Module`), `:185`, `:412-417` | Confidence member (band, not scored, or none) and the "Reduced inputs" label with reason line, only with a delivered body; `Overview.modules` gains the list sentence or `null`; `BlockedBody` unchanged, `reason` carries the missing-producer sentence | 1, 3 |
| `slice.ts:33-49`, `:72-82`, `:121-131`, `:11`, `:528-534`, `:557-595`, `:577` | `IssuerCard`, `HistoryEntry`, `RunHead` gain reason labels, `RunHead` the reason line; `RunState` follows the kit; `TimingRow` an Inputs cell; `RunRecord` the register and "How the run ended"; `spend` a no-bar form with a note | 1, 2, 3 |
| `web/src/pages/library/read.ts`, `fixtureAgreement.test.ts`, `web/fixtures/library.json` | A reader per member: a blocked body carries no confidence or label; a list with the sentence has no row element; no-bar spend carries a note; item and module agree on band and label. Fixture: four places reading "Capped"; `home.filters.state`; confidence on every module and Overview item of four runs; a register per run; one restricted module; one blocked by a missing producer; one run with spend unknown | 1, 2, 3 |
| `web/src/pages/library/Module.tsx:178-183`, `parts/ModuleItems.tsx:20-29`, `Overview.tsx:88`, `EvidenceRecord.tsx:28-59`, `:121-167`, `parts/IssuerCard.tsx:24`, `IssuerList.tsx:179`, `RunFeed.tsx:50`, `RunFrame.tsx:138-140` | Confidence line and label; scale under the lead and label after the badge; list sentence; Inputs column, register, "How the run ended", no-bar spend; reason labels after the state badge and the reason line under the run frame header | 1, 2, 3 |
| `web/src/pages/run/slice-activity.ts:18-26`, `:164-165`; `web/fixtures/run.json`; `activity/*.tsx`, `start/*.tsx`; `web/src/pages/model/slice/types.ts:24-30`, `slice/read.ts`, `parts/ModelShell.tsx:74`; `web/fixtures/model.json` | "Capped" becomes "Stopped" in the two closed lists; `:38-39`, `:49-50`, `:56-60` unchanged (`labels`, `alert`, `spend`, a step's `detail` carry the rest). Fixture: two places reading "Capped"; four new ended runs (spend unknown, cost control, by the analyst, failed with spend unknown); a reduced-inputs detail; a module blocked by a missing producer in a live run. No component change; nothing drawn on the start pages Model: `RunHeader` gains reason labels, read and drawn after the badge; the fixture's one run is "Finished", unchanged | 2, 3 |

What delivery (step 3B, no plan) would have to send. "Code": on `main`, on an open pull request, or
plan only.

| State | Field (proposed) and closed values | Back-end source | Code |
| :--- | :--- | :--- | :--- |
| Confidence scored, ceiling | Band and number text (marks follow the band by a kit table); ceiling sentence or `null` from `status` (`Passed` none, `Restricted`, `Blocked`) | `confidence_outcome`: `state`, `value`, `band`, `status` (`confidence.py:240`, `:63-67`, `:92-100`) | main (merged in #312) |
| Confidence not scored; no module scored | Reason key and sentence: nothing asked; earlier format (Evidence also: blocked, refused). The list sentence or `null` | `state`; the document's format (`handoff.reader.read_reader`); the catalogue's `scored` (3A D1, `:142`); delivery's count over the outcomes | Outcome, format: main. Catalogue, count: plan only (3B unplanned) |
| Confidence register | Per module: outcome, score, band, status, fourteen inputs as written, refusals; four states, three statuses, eight `confidence.*` ids | The outcome; the `confidence` data section (`handoff.data.read_data_sections`); a rejected attempt's issues (2A plan `:100`, `:138`) | Outcome, ids, data section: main. Attempts: plan only (2A PR 3) |
| Run state; run ended with no record | One of Queued, Running, Finished, Failed, Stopped, Rejected, Interrupted; for a run with no end write nothing can be sent, the store holds `running` | Store `runs.status` (2A plan `:137`; `src/credit_os/store/runs.py:39-41`); "Interrupted" has no source; `StoreUnusable` "writes nothing" (D9 `:150`; G3 `:235`) | Pending #303; Interrupted: none, and what tells a writer no process is live is in no source |
| Run end reason | Labels and reason line over G3's set (the cap; unknown spend; a charge above its hold; a stop asked for by the operator; a provider failure that is not retried; an exception out of `complete`) | Store `end_reason` (2A plan `:97`); identifiers keyed in 3A PR 3 (G3 `:235`), not written | Column: pending #303. Vocabulary: plan only |
| Spend; a call's cost stated by the owner | Figure with bar, or "not known" with a note; a row mark: reported by the provider, or stated by the owner | Budget total, "a `Decimal`, or unknown with the lines that made it so" (3A `:175`; D6 `:147`, D7 `:148`); G7 `:239`; store marker of 3A PR 3 (`:296`) | Plan only (3A PR 2a, PR 3) |
| Module ran restricted | "Reduced inputs" label or `null`; reason line naming each missing producer; Inputs cell | G1 (`:233`); `edge_rule` and the catalogue's edges (3A PR 1, `:293`); producers with no accepted handoff (store attempts) | Plan only |
| Module not run, producer missing | "Not assessable" and its sentence in the blocked body's `reason`; one of three fixed reasons: the module's own, not accepted after three attempts, a producer missing | G1 (`:233`); D4 (`:145`); D14 (2B plan `:147`) | D14: main (`src/credit_os/checks/structure.py`). G1, D4: plan only |

## Prior art

Predecessor `EricMG13/RBOT-HTML` at `8e3954a`, read from the local git remote `legacy` (`git show
8e3954a:<path>`) as data; port map `docs/legacy/ports.md` lines 30-31. No rendered page was opened.
Could not read: a restricted module beyond the declared-state word; pages for a stop other than
budget; any not-run module.

| What | File and line @ `8e3954a` | Behaviour | Decision and reason |
| :--- | :--- | :--- | :--- |
| Score, bands, status | `src/deploy_workflow/confidence.py:27` (BANDS), `:26` (PENALTIES), `:175-184` | Value, band, status `Blocked` (39), `Restricted` (59), `Passed` | Reuse value and band; status off findings pages. Thresholds ported exactly (2B D4); the predecessor's page did not receive the status either |
| Absent, blocked, refused apart; plain sentences | `confidence.py:88-98` (`Refused`: `reason`, `absent`, `shown`, `blocked`), `:113-117`, `:271-278`; sentences `:64-79` | `absent` means nothing asked; `blocked` its own form; other refusals a plain sentence (six fixed sentences, e.g. "the module was blocked, so no score is computed") | Adapt. The four outcomes stay apart; an unscored delivered module reads "Not scored" with a reason, since a blank reads as broken; sentences are delivery's (2B plan `:74`), keyed by outcome on findings pages, by check id on Evidence |
| What reaches the page; how it is drawn | `apps/issuer-library/credit_os/store.py:1070-1077`; `credit_os/web/views.js:567`; test `static.test.cjs:505-515` | Absent: no field. Refused or blocked: `{"confidence": {"missing": <sentence>}}`. Scored: `value`, `band` only. One text line: "Confidence 58 · Low", "Confidence not computed: <sentence>", or nothing | Adapt: ceiling sentence in place of the status, a closed reason key in place of free text. Depart on drawing (C-B is the reuse): one line cannot be scanned across thirteen modules |
| Blocked module mark | `apps/issuer-library/credit_os/web/components.js:756` (mark), `:759` (tile), `:780-781` (dot) | Grey "Not assessable" badge; warning-triangle icon in module dots | Reuse the badge; depart from the triangle, which here means caution |
| Run end states, stop classes, states on the page | `src/deploy_workflow/inbox/runs.py:24`, `:265-286`; `src/deploy_workflow/run_events.py:64-81`; `views.js:1753`, `:1757` | Seven words; budget stop `capped`, any other stop `failed`, no result `interrupted`. Six classes: budget, provider, checker, interrupted, ruling, other. Ended runs not drawn on the live panel ("decision 10") | Adapt: a budget stop is "Stopped" with "Spending cap"; "any other stop is failed" is not kept, as G3 keeps `stopped` and `failed` apart. Depart from the six classes (G3 keeps no names; a class with a fixed sentence is kept). The run activity page draws an ended run with its alert (`docs/design/mocks/run.md:59-63`) |
| Restricted module, and shown | `src/deploy_vii/contracts.py:35` (`InputStatus`); `cp4_legal.py:17-19`; `execution.py:262`; `components.js:780` | A module whose required input is blocked settles `restricted` by its edge rule, carrying the inherited limitation (a module status; word clash, Topic 3); shown as the declared state word with a tone | Adapt: step 3A ports `edge_rule`; the limitation stays the module's text. Depart on display: a neutral "Reduced inputs" beside the state, since the module is delivered and the word clashes with the confidence status |

## Not verified

- `confidence.py` was read at `23c00a4d`; its diff to `origin/main` for `src/credit_os/checks/` was
  empty on 2026-11-14 (merge `5e378d0a`), so the lines hold on `main`. Rulings C1 to C10 and R65 to
  R68 come from a side note (`rulings-proposed.md`), not a decision record; it says the coordinator
  confirmed C1 to C10, and they are still only there.
- #303 (head `2fdd4ebf`, open when read) was read only for status words in `runs.py`, `db.py`,
  `schema.py`; it may change.
- Every Topic 2 and 3 word is plan text; no code or test exercises it, and G3's set "is closed and
  keyed in PR 3". The 3A plan was read at the lines named, not in full. The chain from accepted
  handoff to delivery (3A D4, 2A admission, D10) is plan text; the `admit_delivery` search of
  `origin/main` found nothing, and a short result does not prove absence (likewise the greps for
  confidence in `web/src`, `web/fixtures` and `stop_reason` in `src`; rtk may compress).
- Predecessor code was read from git objects, not run; the mocks' states only through
  `docs/design/mocks/*.md`; the canvas under the module head and Overview list from
  `web/src/shell/Shell.tsx:26`, not seen drawn.
- Contrast rules come from `design-system.md` text. Computed here by WCAG 2.1 relative luminance,
  not the system's script: `#474A4F` on `#F6F5FF` 8.23; `#997700` on `#FFFFFF` 4.21; `#A54C48` on
  `#FFFFFF` 5.63 (the last two are pairs the merged run alert draws). The same function reproduced
  six design-system rows (8.90, 8.09, 5.68, 19.64, 3.99, 3.71).
- F7 was read live by the controller on 2026-11-14: stars throughout, "Radix UI or Base UI", against
  `component-map.md:94` "built on React Aria"; which is right is not settled.
- `tests/checks/expected/confidence.json` was tallied by script (66 cases, 34 `refused`, each a
  `confidence.*` refusal); no test of the pull request was run. The CRITICAL, MATERIAL and MINOR
  counts are known only from the predecessor's comment ("the findings by severity", `confidence.py`
  at `8e3954a`); `methods/` has no method text.
- No reader has seen the mocks (checked in a browser for layout and console errors only); whether
  the stars read as a consumer rating, whether two badges crowd an Overview row at two columns, and
  whether a reason label fits the home list's State column are untested. No analyst or portfolio
  manager has seen the proposed words.
- Sample scores were worked by script from the 2B plan's Score row, not `credit_os` (two are the
  plan's examples, `:164-167`). Which modules are scored and which producers are required or
  optional come from a catalogue not built (3A PR 1); the mock's dependencies are sample data.
- The `Blocked`-as-D14-module clash is inferred from D14's wording. "Capped the score at 59" is read
  as a ceiling (`confidence.py:96`); the kit's "Rejected: none in G3" is supplemented by the store's
  `rejected`.
