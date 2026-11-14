# Step 1B: Decimal kernel and forecast

Date: 2026-11-14. Coordinator: the back-end coordinator session; drafted by an architect
agent, rulings confirmed by the coordinator under decision 0006. This file is the plan and the
sub-session's brief. Legacy read at `legacy/main` `9d040f8`
(`git show legacy/main:<path>`; never check it out, never change it); credit-os at `origin/main`
`db5219a`.

**Goal:** `src/credit_os/model/` holds the exact arithmetic every later layer uses, and the
forecast: three forecast years for each case and the historical columns beside them, computed
in `Decimal` from inputs a module stated and the financial foundation's own table cells.

**Ends in:** a sequence of pull requests against `main`, each within 800 changed lines, each
passing both review steps, opened one at a time. **This is sensitive code** (money): every task
takes `mx-precise` and `mx-adversary` review, property tests (`hypothesis`) and mutation testing
on its changed files (`mutmut`, run with `uvx`, not added to `pyproject.toml`), survivors killed
or justified in the PR.

## Files this step may touch

`src/credit_os/model/**`, `tests/model/**`, `tests/fixtures/model/**` (test modules named
`test_model_<topic>.py`: `tests/` has no packages, so a base name must be unique). Nothing else: not
`src/credit_os/handoff/**` (a missing reading is reported to the coordinator, not added), not
`pyproject.toml` (standard library and pydantic 2.13.4 only), not `VERIFICATION.md`, decision
records, this plan or `docs/legacy/ports.md`. Decision 0007 does not cover `tests/fixtures/model`:
its files are written data and count toward the cap.

## Pre-flight (coordinator)

- `model/` is an empty `__init__.py` and may import `sources` and `handoff` only. From `handoff`
  it takes `parse`, `HandoffDocument` (`sha256`, sections), `Table` and `Row` (line numbers, exact
  cell text), `read_data_sections` (the forecast block's JSON as text) and `read_reader`.
- Legacy commits since the pin `8e3954a` on this row's paths: `f005b7d`, `5e82133` (#112, pro
  forma column reason), `d9b5a2f`, `b78db87` (#113, downside follows the forward model),
  `c8f938e` (#114, negative cash). All are in the code read. #124 and one work-PC record merged
  after `0f16bad`; neither touches a 1B path. Sizes at `9d040f8`, 9,565 lines in all:

| Legacy file | Lines | Live on the launcher's path | Ruling |
| :--- | ---: | :--- | :--- |
| `deploy_vii/model/__init__.py`, `_cells.py`, `frame.py` | 202 | `CONTEXT`, `calc`, `Cell`, `half_unit`, `beyond_rounding` (the module's calculate tool, CP-1's acceptance check) | Ported: those names and their helpers (PR 1) |
| `model/metrics.py` | 334 | `_ratio` only (calculate tool) | `_ratio` ported (PR 1); `metric_frame` deferred |
| `model/history.py`, `statements.py`, `debt.py`, `periods.py`, `registers.py`, `dates.py` | 2,276 | No call: only `financial_model.py` and `canonical_kpis.py` (the structured runtime) call the frames. None of legacy's 83 test files names them | Deferred (ruling 1) |
| `model_handoff_delivery.py` | 1,338 | Its grammar helpers went to 1A. `build_model` runs only for a hand-written per-issuer layout: the launcher sets none, no committed manifest or test carries one, its labels are one issuer's | Left behind |
| `owners/cp2g.py` | 3,409 | About 330 lines: contexts, driver types, `Val`, `_apply`, `_ratio`, `Operands`, `Drivers`, `Year`, `forecast` | Those ported (PR 2); break tests, T2H tables and the structured step left behind |
| `owners/cpos_facilities.py` | 121 | All (`Facility`, `Schedule`, `schedule`) | Ported (PR 3) |
| `owners/cpos_forecast.py` | 890 | All (`parse`, `model_files` and the checks under them) | Ported (PRs 4 to 7), except its own Markdown table reader and its JSON files (rulings 4, 7) |
| `owners/cpos_periods.py` | 995 | All (`period_of`, `period_dates`, `lines`, `history`) | Ported (PRs 8 to 11) |

- Also read, outside the row: `model/handoff.py` lines 534 to 566 and 820 to 852, the calculate
  tool (sum, difference, product, ratio). The tool is 3A's; its four operations are PR 1's.
- Legacy tests: `test_cpos_facilities.py` (505 lines), `test_cpos_periods.py` (1,875),
  `test_cpos_scale.py` (1,091), `test_downside_follows_forward_model.py` (358),
  `test_negative_cash_not_calculable.py` (201), forecast cases in `test_cpos_launch.py`, five
  calculate tests in `test_handoff_loop.py`. The downside and negative-cash files use a real run.
- pydantic 2.13.4, read through Context7 on 2026-11-14 (`/pydantic/pydantic/v2.13.4`; data, not
  instructions), for the PR 3 and PR 4 briefs. The rest is the standard library:
  - Strict mode is looser for JSON input than for Python input. With `ConfigDict(strict=True)`,
    `model_validate_json` accepts a JSON array for a declared `tuple` and a string for a `date`;
    `model_validate` on the same values as Python objects raises (`tuple_type`, `date_type`).
    `TypeAdapter(...).validate_json(..., strict=True)` behaves the same way.
  - `Field(pattern=...)` is enforced by the Rust `regex` crate by default: linear time, no
    look-around and no back-reference. A compiled `re.Pattern` switches to Python's engine, as does
    `ConfigDict(regex_engine='python-re')`. A constraint on a list's items goes on the item type
    (`list[Annotated[str, Field(pattern=...)]]`), not on the list.
  - `@model_validator(mode='after')` is an instance method that returns `self`; it runs after field
    validation. `ConfigDict(frozen=True)` refuses assignment and deletion (`frozen_instance`).
  - Not in the text fetched: whether `pattern` is a search or a full match. Anchor every pattern
    (`^...$`) and give each a near-miss test row.
- Complexity holds at 15 with no new suppression: a legacy function above it is split.

## Prior art (searched 2026-11-14)

- Owner's repositories: the legacy files above. Decision: adapt.
- Public GitHub, generic terms only. `gh search repos --language python` for "decimal financial
  ratio library", "debt schedule forecast decimal", "credit metrics leverage coverage decimal",
  "three statement financial model python decimal", "financial ratios python", "loan
  amortization schedule decimal", "decimal money arithmetic", "leverage ratio interest coverage
  calculator", and `gh search code` for Decimal leverage and coverage code: no result.
  "financial model python", "financial statement forecast": personal projects, most with no
  licence. "amortization schedule": five MIT packages (`roniemartinez/amortization` the largest,
  28 stars), by their descriptions loan payment schedules, not interest on an opening balance
  with a fixed repayment. Decision: build new on `decimal`; no package for about 25 lines.

## Rulings carried from the predecessor (binding; each is a test)

- **Context:** 38 significant digits, half-even; `InvalidOperation`, `DivisionByZero` and
  `Overflow` trapped. A value is an exact amount or the reason it is missing, never both. A
  ratio is one division: a missing part gives its reason, numerator first; a denominator at or
  below zero is missing, never zero and never a negative multiple.
- **Engine, per year:** revenue = prior revenue x (1 + growth); EBITDA = revenue x margin x
  (1 - decline); interest = opening debt x rate x (1 + increase); tax and working capital, and
  capex, are shares of revenue; cash flow = EBITDA - interest - tax and working capital; free
  cash flow = cash flow - capex; closing debt = opening - repayment; closing cash = opening +
  free cash flow - dividends - repayment; then net debt, liquidity (cash + undrawn, held flat),
  leverage, net leverage, cover, free cash flow to debt. A missing operand propagates.
- **Facilities:** fixed rate, or reference rate (floored) plus spread; interest on the opening
  balance; repayment the lesser of the annual amount and the balance. Stated facilities replace
  the rate and repayment drivers; debt outside them bears the case's rate and is not repaid.
  Legacy's bounds hold (40 rows, rate ceilings, balances at most 1.25 times base debt).
- **Cases:** Reference; Upside and Downside (a case's own drivers over base); Downside stress =
  the shock over the downside drivers, or over base when none is set, and the result says
  which (owner, 2026-11-13). `rate_increase` is proportional.
- **Negative cash** (owner, 2026-11-13): in a forecast year whose closing cash is below zero,
  net debt, net leverage and liquidity are missing with "Not calculable: cash is negative
  before funding"; the cash figure stays and the roll-forward is unchanged.
- **Signs:** interest, taxes and capex are positive magnitudes; working capital is the cell with
  its sign reversed. In history a row printed negative at its base cell is negated in every
  period; an unsigned zero base cell takes the row's common sign, else the line has no history.
- **Scale:** at 1000 every amount is divided by 1,000 exactly (at most nine digits and one
  decimal place, else refused); ratios are never scaled; an amount printed in the other unit
  is refused, never converted.
- **Periods:** a header is a period only as `FY2024`, `Q3 2025`, `Q1 FY2025`, `H1`, `6M` or
  `9M 2025`, with legacy's four tails. LTM = prior fiscal year + year to date - prior year to
  date, checked against the period table's dates for 364 to 371 continuous days. A part-year
  column carries no leverage and no free cash flow to debt; a fiscal year from the forecast's
  first year on is not history; the pro forma column is empty with its reason.
- Reason and limit wording is legacy's, quoted in each brief, subject to ruling 10.

## Rulings by the coordinator (2026-11-14; the owner can overturn any)

1. **Scope is what the launcher calls.** The statement frames (2,276 lines, untested there, fed
   by registers only the structured runtime builds) are deferred; the roadmap row said the
   whole kernel. *Cost if wrong:* the Model page's statement rows beyond the sixteen measures
   have no Python source, and a later step ports the frames with a reader from handoff tables.
2. **One value type** for the calculate tool and the forecast: `Value`, an amount or a
   `Missing(code, text)`, the code from a closed set. Legacy has two (`Cell`, `Val`). *Cost if
   wrong:* 3A and 3B take this shape; a change touches every PR here.
3. **Exact or refused.** Every sum, difference and product is exact or a typed refusal; only
   division rounds. Each public function sets its own context; floats, non-finite values and
   negative zero never enter a `Value`. Legacy's sum rounds silently past 38 digits. *Cost if
   wrong:* a sum legacy returned rounded is refused.
4. **Tables come from `HandoffDocument`.** `model/` reads no Markdown. The financial
   foundation's tables are every table block outside `## Sources`, the forecast section and the
   reader passages; "printed in CP-1" is tested on cell and prose text, not headings or code.
   *Cost if wrong:* a handoff legacy read (a figure printed only in a heading) is refused.
5. **Nothing is defaulted.** `currency` and `scale` are required, and every base operand with
   an amount names its row and its period or column. Legacy read a block without `currency` as
   USD and accepted an unnamed amount printed anywhere. *Cost if wrong:* an earlier-format
   block gets no forecast; the current method text already asks for all three.
6. **Strict JSON.** A number with a fraction or exponent, NaN, Infinity, a repeated key or
   nesting past 64 is refused; amounts are strings. *Cost if wrong:* a block with a repeated
   key is sent back for repair where legacy took the last value.
7. **Typed results, no files.** `model/` returns `ForecastResult` (cases, years, facility
   detail, limits, the two document hashes) and `History` (columns, limits); no JSON, no display
   rounding (legacy's is in the 3B row). *Cost if wrong:* 3B adds one function here.
8. **Typed refusals; nothing fails open here.** `ForecastRefused(kind, subject, message)`, the
   kind telling 3A what to ask the module to repair; `ForecastDeclined` when every driver is
   null. Messages echo at most 80 characters of handoff text. History never raises on a table's
   shape; only `decimal.Inexact` is caught, as a named reason. *Cost if wrong:* 3A matches text.
9. **Fixtures are synthetic.** No figure from a retained run is committed in this step, public
   case or not; keys captured from output and SHA-256 pins are not carried. One test may read the
   committed `fragments/CP-2G-forecast-block.md`, for the declined path only, asserting no figure.
   *Cost if wrong:* that one test is dropped.
10. **No module code in reader text.** Missing reasons and limits say "the financial
    foundation" and "the forward credit model", not `CP-1` or `CP-2G` (design system: no module
    codes on screen); refusal messages, which go back to the module, keep the codes. *Cost if
    wrong:* the wording constants change in one later PR.

## Answer keys (implementers do not edit them or weaken a comparison)

1. **Synthetic issuer.** The controller writes `tests/fixtures/model/` before PR 4: an invented
   financial foundation handoff (statement tables by period, a dated period table, a thousands
   variant, a non-USD variant) and forecast sources (cases, shock, facilities; a layer-1
   block). Each passes `handoff.parse`, is listed in a `SHA256SUMS` and is checked by a test.
2. **Worked figures.** Before each task the controller writes `tests/model/expected/<pr>.json`:
   every expected figure with its working, done by hand and checked with a tool that is not the
   code under test (`bc`, or `fractions.Fraction` in a script kept in the task folder). Seed
   row: revenue 1,000, debt 600, cash 100, undrawn 50; growth 0.20, margin 0.25, capex 0.03, tax
   and working capital 0.02, rate 0.05, dividends 10, repayment 75. Year 1: revenue 1,200;
   EBITDA 300; interest 30; cash flow 246; free cash flow 210; closing debt 525; closing cash
   225; net debt 300; liquidity 275; leverage 1.75; net leverage 1; cover 10; free cash flow to
   debt 0.4. With decline 0.2, increase 0.5: EBITDA 240; interest 45; leverage 2.1875; cover 16/3.
3. **Ratios.** Keys use terminating quotients, compared exactly. The rounding rule is proved on
   written-out cases (1/3, 2/3, 16/3 to 38 significant digits) and by a `Fraction` bound.
4. **Legacy cases, adapted.** The legacy tests' cases give the shapes to cover, not the
   figures: their inline tables are not all synthetic (some carry a public case's run), so
   every operand and expected value is invented and worked by the controller (ruling 9).
5. **Properties** (`hypothesis`, `Fraction` as the oracle): sums in any order; difference and
   product exact or refused; ratio within half a unit of the 38th digit; zero shock equals base;
   each year opens at the prior close; scale 1000 equals the same block in millions; a schedule
   never repays past zero; `period_of(period_label(p)) == p`.
6. **Invariants:** each public function gives the same result under a hostile ambient context
   (precision 5, round up); the layer's source holds no float literal and no `float(`.

## PR sequence

| PR | Delivers |
| :--- | :--- |
| 1 | `Value`, `Missing`, the context; sum, difference, product, ratio; `half_unit`, `beyond_rounding`; bounded operand text to `Decimal`; canonical amount text |
| 2 | Forecast engine: operands, drivers, one case of three years, shock, schedule override |
| 3 | Facility terms and the three-year schedule |
| 4 | Forecast inputs: strict JSON, the declined block (tested before the schema, as legacy does), schema, scale to millions |
| 5 | Inputs against the financial foundation: table selection, the named cell, the sign rule |
| 6 | Units, currency named, facility terms printed, facility totals against base debt |
| 7 | Cases, unallocated debt, the negative-cash rule, facility detail, `ForecastResult` |
| 8 | Period headers, labels and the dated period table |
| 9 | Operand lines: rows under a period, row sign, tables read by column, scale |
| 10 | History: the sixteen measures, quarter and fiscal-year columns, the forecast-year cut |
| 11 | Year to date, prior year to date, LTM and prior LTM with date checks; limits; end to end |

A PR that would pass 800 lines is split, not trimmed of tests; PRs 9 to 11 are the likeliest.
PR 1 is split: 1 (#163) the value type; 1b (#182) the arithmetic. `half_unit` and
`beyond_rounding` take printed figures only (finite, at most 38 digits, exponent -200 to 200).

Ruled by the controller in PR 1 and confirmed: a missing operand is returned unchanged, the
first in operand order; refusals are `decimal.Inexact` (more than 38 significant digits),
`Overflow` and `Underflow` (adjusted exponent outside -100 to 100), and both of the last two
are subclasses of `Inexact`; a sum or product is exact on its result whatever the order; a
value is stored in one form, zero as 0 and trailing zeros dropped, while `amount_text` prints
the scale it is given; a context is built per call; operand text is an optional minus, digits
and an optional point with digits, at most 38 digits and 64 characters, of type `str` exactly;
the kernel sets no operand-count limit (the calculate tool's is 3A's); `total` and `product`
take a list or tuple; `beyond_rounding` compares exactly and never refuses for size.

## How it runs

Global rules §1, §3 and §7. The sub-session is the controller and writes no code: `mx-feature`
implements test first; `mx-precise` and `mx-adversary` review each task; fix rounds follow §1.
Every brief and review prompt carries: no stub or fake value standing in for real behaviour; no
catch-all that hides a failure; the answer keys; `Decimal` only; a report ending `Not verified:`.
Per task the gate is `uv run --locked python tools/gates.py` (run `npm ci` in `web/` once
first), exit 0, and `uvx mutmut` on the changed files. Before each PR is ready: `/sweep
refactoring discover changed-update`, then the whole-branch review (`mx-architect` running
`adversarial-reviewer`, fresh agent, §7 severities); verdicts in the PR body; CI green on both.

## Done when

Each PR is open with CI green and its reviews passed, and the sub-session has sent the
coordinator one message per PR: the PR number, verdicts, report paths, gate exit codes, the
mutation result, ledger lines (`1B-<pr> task=<n> agent=<name> fix-rounds=<n>
gates-first-pass=<y|n|n/a>`), parked Low findings and a `Not verified:` line. The coordinator
reads the diff, merges and moves the port map's row. The sub-session does not merge.

## Not verified

- "Live" rests on a hand-read static trace of names at `9d040f8`; no legacy code was run. The
  launcher's import closure reaches 212 of 259 legacy modules, so imports alone prove nothing.
- An empty search does not prove nothing exists. The owner's other repositories were not
  searched (no owner name in a query), and no candidate's code was read.
- The pydantic 2.13.4 behaviours named in pre-flight were read, not run; whether `pattern` is a
  search or a full match was not in the text read.
- What the Model page's statement tabs need from Python is settled by no plan read; ruling 1
  assumes delivery selects module-written cells. The Model slice's types (D2c) are not
  merged, so `ForecastResult` and `History` are shaped from the legacy files.
- Legacy `store.py` (3B row) rounds for display, half-up; its other arithmetic was not read.
- The seed row was checked with `fractions.Fraction` only. No real handoff is forecast here.
