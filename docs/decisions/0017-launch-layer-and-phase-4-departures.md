# 0017 The `launch` layer, the order of phase 4 and the reader fields delivery cannot supply

Date: 2026-11-15. Status: **accepted by the roadmap coordinator, 2026-11-15, under the owner's
instruction to resolve decisions, and under decision 0015 (deadline mode, open as #438); the
owner may change any row.** Source: the phase 4 plan for steps 4A and 4X
(`docs/superpowers/plans/2026-11-15-phase-4-4a-4x.md`), read at `origin/main` `4df574a1`.

## Why

Roadmap step 4X asks for "a new top-level entry module, named in its plan and covered by the
layering test". The plan for steps 4A and 4X names it, and records three departures and the
rulings on its open questions. A module in the package root, or a sub-package outside `LAYERS`,
fails the layering test (`tests/test_layering.py:118`, `:131`; `tests/test_package.py:10-22`), so
the module needs a place in the layer list.

## Decision

### 1. A new top-level layer `launch`

- The package is `credit_os.launch`: `launch/__init__.py`, `launch/__main__.py`, `launch/cli.py`
  (arguments, exit codes, printing), `launch/assemble.py` (the front-end copy) and
  `launch/run.py` (the sequence). `python -m credit_os.launch` starts it, as
  `src/credit_os/signal/__main__.py` starts Signal.
- `LAYERS` becomes `sources`, `handoff`, `model`, `provider`, `store`, `checks`, `orchestrator`,
  `delivery`, `launch`, `signal`. `launch` is last after `delivery`, imports the eight layers
  before it and never `signal`. Nothing imports `launch`.
- The layering test gains rows built with its `_tree` helper: `delivery` and `orchestrator`
  importing `launch` are violations (absolute, relative and `importlib.import_module`); `launch`
  importing `delivery` and `orchestrator` is allowed; `launch` importing `signal` is a violation.
  The pinned tuple in `tests/test_package.py` gains `launch` between `delivery` and `signal`.
- A new test reads the syntax tree of every file in `src/credit_os/launch/`: from
  `credit_os.provider` only `canned` and `types` are imported; no `copilot` name and no
  `subprocess` is imported; no call to `rmtree`, `unlink`, `remove` or `rmdir`. The command
  constructs `CannedModel` only and has no `--live`; a paid run stays the owner's separate action.

### 2. A departure from the roadmap's order

The roadmap puts 4X after 4A. The order is 4A-1, 4X-1, 4A-2, 4X-2 (plan Q2). The deadline brief's
key for 4A is a folder made through the canned provider, which only the command produces. 4A-1
still precedes 4X-1.

### 3. Departures D-4A-1 to D-4A-7: reader fields delivery cannot supply

No reader change is planned: every field below has a value the reader accepts today. Each is a
departure; D-4A-1 and D-4A-6 are new, the rest restate step 3B's.

| # | Field | What is written | Why | Reader line |
| :--- | :--- | :--- | :--- | :--- |
| D-4A-1 | Home card `sector`, and so the sector filter | The wording file's "Not recorded" | A run record holds no sector and no context; the request holds only the context's SHA-256 and the pathway (`store/records.py:19-33`; `orchestrator/prepare.py:67-82`) | `read.ts:254`, `:306` |
| D-4A-2 | Overview `sides` | `null` (3B X1) | No module writes two lists | `read.ts:629-637` |
| D-4A-3 | Overview `changeView` | `null` unless the lead module wrote a marked sub-heading (3B D14) | No split without a mark | `read.ts:660` |
| D-4A-4 | `head.forecastHref` | `null` (3B R7, X13) | No model run before slice contract 3 | `read.ts:431-440` |
| D-4A-5 | History entry `changes`; run `changes` | `null`; `none` (3B X7) | 5A | `read.ts:328-336`, `:721` |
| D-4A-6 | "Start a run" and "New run" on Home and History | The buttons stay and open `#/run`, for which a delivered file has no data (3B D12) | 5C wires the Run pages | `parts/links.ts:5`; `Home.tsx:62`, `:196`; `History.tsx:34`, `:59` |
| D-4A-7 | Trace `excerpt`, `qualification`; confidence | `null`; none sent (3B X4, X8) | No page-text source; states 2 | `read.ts:397-416` |

If 4A-2's test shows the reader refusing a delivered file, the fix lands in `delivery/`. The
reader changes only where delivery has no source for a field; the controller brings that case to
the coordinator before any brief touches `read.ts` or `slice.ts`.

## Rulings

Made by the roadmap coordinator on 2026-11-15, under the owner's "resolve all decisions". Every
recommendation in the plan's open questions Q1 to Q15 is accepted, with these notes:

- **Q5** was already ruled (2026-11-15, the data-module body ruling; web side merged in #404): a
  data module's delivered body carries `moduleKind: "data"` and may have no findings and no
  limitations. CP-0 and CP-1's synthetic handoffs are written as data modules, with nothing added
  to pass a check. `delivery/modules.py:107-108` keeps refusing until 3B's data-bodies round lifts
  the refusal for data modules; 4X-0 waits for that round.
- **Q1, Q8, Q10** need the 3A and 3B controllers' answers: put to the back-end coordinator with
  the plan. A step brief quotes their answers, and the merged code, before it is dispatched; it
  does not guess.
- **Q2** is recorded as a departure from the roadmap's order (point 2 above).
- **Q6:** a canned run stores 3A PR 2b's row and id. If 2b stalls for want of a published price,
  that question goes to the owner; no row is invented in `src/`.
- **Q13:** the pre-review sweep is skipped until decision 0015 lapses; each PR body says so, and
  the post-deadline sweep covers these PRs.
- **Q9:** the `loading` card and run stay in the slice, reader and pages; the reader accepts two
  states delivery never writes. Rule it with 5C's plan.
- **Q14, Q15:** accepted for the deadline (Home's sector reads "Not recorded"; the buttons open a
  Run page with no data). Afterwards the run stores its context identity, in 3A or 5C, and 5C
  wires the Run pages.

## What it costs if wrong

If `launch` stalls, it is a package nothing imports and can be removed with its layering rows
without touching another layer. If the order 4A-1, 4X-1, 4A-2, 4X-2 slips, 4A-2 waits on 4X-1.

## Not verified

- Nothing was run: no test, gate, build, browser or command. The plan was drafted from code at
  `origin/main` `4df574a1` and legacy `9d040f81` read with `git show`.
- Every "planned" row of the plan rests on plan text, not code: 3A PRs 2b, 6a, 6b, 7b, 7c and the
  delivered-folder PR, 3B PRs 9 to 12b, 2A PR 5.
- Decision 0015 was read by the plan's author on its unmerged branch (#438, `a3e16af9`); it is
  not merged.
- What `#/run`, `#/model` and `#/signal` draw from a delivered file with no such member.
