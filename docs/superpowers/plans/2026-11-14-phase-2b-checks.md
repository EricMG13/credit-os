# Step 2B: prose, figure and confidence checks on a handoff document

Date: 2026-11-14. Coordinator: the back-end coordinator session; drafted by an architect agent,
rulings confirmed by the coordinator under decision 0006. This file is the plan and the
sub-session's brief. Written against `origin/main` `db5219a` and legacy `legacy/main` `9d040f8`
(`git show legacy/main:<path>`; never check it out, never change it).

**Goal:** `src/credit_os/checks/` takes a parsed `HandoffDocument` and returns typed findings:
what a module must change before its handoff is accepted. It parses no Markdown, renders
nothing, calls no provider and knows no module by name.

**Ends in:** six pull requests against `main`, each within 800 changed lines, each passing both
review steps, opened one at a time. A second part (CP-1's figure check) waits for step 1B.

**Figure and confidence checks are sensitive code** (money): their tasks also get an
`mx-adversary` review and mutation testing (`mutmut` through `uvx`), survivors killed or justified.

## Files this step may touch

`src/credit_os/checks/**`, `tests/checks/**`. Nothing else (2A runs beside it): not
`pyproject.toml` (standard library and pydantic only), not `tests/fixtures/handoffs/**`, not
this plan, `VERIFICATION.md`, `docs/decisions/` or `docs/legacy/ports.md`. Test modules are
named `test_checks_<topic>.py`: `tests/` has no packages, so a base name must be unique.

## Pre-flight (coordinator)

- `checks/` holds an empty `__init__.py` and may import `sources`, `handoff`, `model`,
  `provider`, `store`. These six PRs import only `handoff` and `sources.pins.SourcePin`.
- `handoff/` at `db5219a` gives `parse`; `read_reader` (`format`, four passages, `summary`,
  `summary_section`, `blocked: bool | None`; it raises `HandoffError` on a repeated passage
  heading); `read_basis`, `read_value`, `sources_table`, `source_names`, `read_data_sections`,
  `read_registers`; `CodeBlock.unclosed`, `Row.line`. A block's k-th line is `block.line + k`.
- Legacy: `prose_checks.py` 1,274 lines (1,123 at the pin), `confidence.py` 278 (unchanged),
  tests 1,066 and 436 lines (95 and 25 test functions). Five commits since `8e3954a` touch
  them, all in `prose_checks.py`, all for `lost_values`: `918fa87`, `ec8708f`, `aa77949`,
  `c06ae13`, `0985bb5`. Nothing in the row moved between `0f16bad` and `9d040f8`.
- Live callers: `owners/cpos_launch.checker`, `model/handoff.py` (`lost_values`), `changes.py`,
  `owners/cpos_forecast.py`, `apps/issuer-library/credit_os/store.py` (the score on the page).
- Measured by running the legacy modules on the 26 whole fixtures (a cross-check, never an
  answer key): all 20 retained files are earlier format and fail check 1; the six synthetic
  new-format files give four issues (`SYNTHETIC-CP-1.md` line 17 "canonical"; `-CP-1A.md`
  line 24 "24"; `-CP-2.md` line 24 "38%" and "24"). No fixture holds the 14-row inputs table,
  an unclosed fence or a refused register id. The legacy accepts a passage `0%` held only by
  the cell `Not supplied: 0% is not stated`, and `USD 5 million` held only by `EUR 5 million`.
  Its float score differs from exact arithmetic in 59 of 400,000 random sets, by one point.
- The lines naming this step's duties (repeated register id, Sources names against pins) are
  in the 1A plan's "Data views (PR 5, #78)" rules.

## Prior art (searched 2026-11-14)

- Owner's repositories: the legacy files above, and the archived `confidence_score.py` of the
  Deploy V skills that `confidence.py` copies. Decision: adapt the rules, onto typed documents.
- Public GitHub, `gh search repos` for "prose lint", "prose linter", "proselint", "quantulum",
  "price parser", "table fact verification" (seven longer queries returned nothing): prose
  linters (`amperser/proselint`, BSD-3) judge style, not figures against a document's own
  tables; `nielstron/quantulum3` (MIT) and `scrapinghub/price-parser` (BSD-3) extract
  quantities but know no bracketed negative, period label or this unit list; the rest are
  trained models. Each is a new dependency. Decision: build new on `re`, `decimal`, `fractions`.

## Legacy checks: what happens to each

| Legacy | Ruling | Reason |
| :--- | :--- | :--- |
| Checks 1 to 8 and 10 (`prose_issues`, about 500 lines with the ISO list) | Ported | Live; the owner's ruling of 2026-11-11 as amended |
| Check 9, provider citation markers | Changed | Reads every text node of the document, not raw lines |
| Fidelity check (`figure_issues`, about 250 lines) | Changed | `Decimal` values; currency compared; a gap holds no figure |
| `_sections`, `_visible`, `_sentence_lines`, `_tables`, `reader_passages`, `is_earlier_format`, `bottom_line_text` (about 330 lines); `confidence.inputs` | Left behind | Second Markdown readers; `handoff/` views replace them |
| `limitation_texts`, `normalise_limitation` | Ported, public | Step 5A's comparison needs the same key |
| `DATA_MODULES`, `READER_HEADINGS` | Left behind | Module lists belong to the orchestrator (D3) |
| `lost_values` (about 250 lines) | Deferred | A record of the repair loop, not a check on one document (D11) |
| `key_figures_issues` | Left behind | CP-L10 is not offered; a new run of it is refused |
| `confidence.score` | Changed | Exact arithmetic instead of float (D4) |
| `confidence.from_handoff` refusals | Ported | Live; typed findings replace `Refused` |
| `confidence.SHOWN_*` page sentences | Left behind | Page wording is delivery's (3B), keyed by the check id |
| `cpos_launch._front_matter_score_issues` (3A's row) | Ported here | A check on the document's front matter |
| `cpos_cp1_check.py` (1,398 lines), `cpos_launch._net_debt_issues` | Deferred | Need `model/` rounding and periods (D12) |

Left with 3A's row: chart and owner-table shape checks, forecast and CP-8 checks, the as-of
date, each supplied handoff and one issuer hash being present, the issuer named in Request.

## Rulings (each is a test)

**Result type (PR 1).**
- `Finding` is a frozen pydantic model: `check` (an id from one closed tuple `CHECKS`),
  `severity` (`refusal` or `warning`), `line` (the 1-based file line of the offending node),
  `quoted` (its text as written, at most 80 code points then `…`), `reason` (one sentence
  saying what to change; any handoff text inside it is bounded the same way).
- `Finding.message` is `<check>, line <n>: "<quoted>": <reason>`. The orchestrator sends the
  refusals' messages, in order, as the retry reason. A handoff is refused when any finding is
  a refusal. A warning is kept with the attempt and never sent back. Findings are ordered by
  line, then `CHECKS` position, then column; the same input gives the same tuple.
- Each check is a pure function of `(document, context)`; `check_handoff` runs them all. No
  check raises on content. One error is converted: a `HandoffError` from `read_reader` becomes
  the refusal `structure.reader` with its line and message, and the passage checks do not run.
- `CheckContext` (frozen): `kind` (`prose` or `data`), `scored`, `pins`, `other_sources`
  (names), `upstream` and `accepted` (module code to `HandoffDocument`), `required_registers`.
- Sentence text is the lines of a `Paragraph` or `ListItem` without its Basis line; a table's
  label paragraph counts; tables and code blocks do not. Shown text is the sentence text of
  `Findings`, `Calculations` and `Gaps`, nested sections included, data sections excluded.
  Passage text is the sentence text of the four passages.
- No float: a test reads the package's syntax tree and finds no float literal and no `float`
  name. A figure's value is a `Decimal` built from its digits as written.

**Checks.** Each is a refusal unless marked. "Blocked" is D14.

| Check (PR) | Rule |
| :--- | :--- |
| `structure.format` (1) | An earlier-format document gets this one refusal, at the first level-3 heading under `Findings` or, with none, at `## Findings`, and no other check runs (D1); `Reader.blocked` of `None` is never read as false. `structure.reader-summary`, a warning: its `summary_section` is set and `summary` is `None` |
| `structure.passages` (1) | `kind` prose, not blocked: the first four level-3 sections of `Findings` are Bottom line, Key findings, Contrary evidence and what would change the view, Limitations, in that order (D2). A data or blocked module owes only Bottom line |
| `structure.fence`, `.register-id` (1) | Any `CodeBlock.unclosed`, at the block's line. Two registers with one id, at the later line; a heading register and a tag register inside that heading's section are one register (D13) |
| `structure.registers` (1) | Each id in `required_registers` is a register's id or the last dotted part of a tag's id; one refusal names all that are missing; not asked of a blocked module |
| `prose.bottom-line`, `.bottom-line-length` (2) | The first block of Bottom line is a paragraph starting with a letter, one of `"“‘'`, or `**`. `prose.bottom-line-length`: its first sentence (to the first `.`, `!` or `?` followed, after any closing quote, bracket, `*` or backtick, by whitespace or the end) has at most 45 whitespace-separated words, the passage at most 180; 45 and 180 pass |
| `prose.module-code`, `.page`, `.hash` (2) | In shown text: `\bCP-[A-Z0-9]+\b`; `\bpp?\.\s*\d`, `\bpages?\s+\d` or `\bpg\.?\s*\d` in any case; `\b[0-9a-fA-F]{12,}\b` or `sha256` |
| `prose.bracket` (2) | In shown text: one finding per pair of `[]` or `【】` holding at most 80 characters, else one per bracket |
| `prose.pipeline-wording` (2) | In shown text, any case: `handoff(s)`, `this transport`, `the pack`, `fact pack`, `source pack`, `canonical`, `re-anchor…`, `helper script(s)`, `upstream module(s)`, `downstream` before module, owner, work, analysis or use; also a token with a lower-case letter either side of `_`, and an all-capitals token holding `_` |
| `prose.provider-marker` (2) | U+E200 to U+E202 or `cite\s*turn\d+[a-z]+\d+` in any text node: titles, paragraph and list lines, table cells, code lines, front matter values, comments; a lone marker character is quoted as `U+E200` |
| `prose.register-id` (3) | In passage text, as a whole token (not touching a letter, digit, `_` or `-`): any cell holding a letter and a digit under a header that is `ID` or ends ` ID`, any case, in any table |
| `prose.limitation-repeat` (3) | A Limitations item's key is its text lower-cased, every character that is not a letter, digit or whitespace removed, whitespace collapsed; a key equal to an earlier item's here or to any item's in `accepted` is refused; an empty key is skipped |
| `sources.table`, `.name` (3) | No single table under `## Sources`, unless blocked. A row's first cell, compared exactly, is a pin's name, a name in `other_sources`, or `name (CP-X)` with CP-X in `upstream`; anything else, a web address included, is refused at its row (D9) |
| `sources.sha256`, `.type` (3) | Where a `sha256` column exists, a stated cell equals the pin's digest or the upstream document's (D10); where a `Source type` column exists, a stated cell is one of the legacy's seven types |
| `figure.form` (4) | Check 8, on passage text with dates masked. Exempt: a whole number below 100, a year 1900 to 2099, digits touching a letter or a hyphen-joined letter (`10-K`, `FY2024`). Otherwise at most two decimals, and a unit after it (`%`, `x`, `bp`, `bps`, `pp`, basis or percentage points, times, notch, day, week, month, quarter, year, with plurals) or a currency before it (one of the 176 ISO 4217 codes and a space, or `$ € £ ¥`); a scale (`thousand`, `million`, `billion`, `trillion`, `bn`, lower-case `k`, `m`) needs the currency |
| Figure reader (4) | For the rows below a figure has a `value`, a sign (a leading `-` or U+2212, or parentheses), a unit spelled one way (`%`, `x`, `pp`, `bp`, `k`, `m`, `b`, `t`) and a currency (D6); a comma between groups of three is a separator. Module codes, `T1.2` ids and hex runs of 16 or more are masked; on the passage side so are dates and period labels (`Q1`, `H1`, `FY2024`, `LTM`, `9M`), which are never amounts (D8). A bracketed figure directly after a figure is a note, read as written, when it is a ratio or that figure rounded to fewer places (half up or half even); any other bracket is a negative |
| Held figures (5) | Those of every text node outside the four passages and outside forecast inputs. A cell or paragraph that `read_value` reads as a `Gap` holds none: a passage `0%` is held by a written `0%`, never by a gap |
| `figure.not-held`, `.mismatch` (5) | No held figure has an equal value (`4.10` equals `4.1`; `4.2` is not `4.23`). Mismatch: one has, but none with the same sign (a held minus may be told as its magnitude, a held bracket may not), the same unit or none on one side, and the same currency or none on one side (D7); the reason quotes up to three held spellings |
| `confidence.absent`, `.repeated`, `.unreadable` (6) | No `confidence` data section (a refusal only when `scored`); a second one; its `table` is `None` or its title is not exactly `Confidence inputs` at level 3 under `Findings` |
| `confidence.blocked-row`, `.front-matter` (6) | The one row `Not assessable \| Not supplied: <reason>` in a module that is not blocked; in a blocked one it gives no score and no finding. `confidence.front-matter`: a front matter key `confidence_score`, `confidence_band` or `qa_status` |
| `confidence.rows`, `.count`, `.range` (6) | Exactly the 14 named rows, each once, any order; the 13 counts are ASCII digits, at most 20 (D5), an empty cell or a gap refused and never zero; Fields total at least 1, Fields present at most the total, Source gate `pass`, `partial` or `fail` after trimming and case folding |
| Score (6) | In integers and `fractions.Fraction`: E is 100 times the weighted mean of the claim counts (weights 1, 0.9, 0.5, 0.4, 0.3, 0, 0, 0; no claims gives 0); C is 100 times present over total; raw is (0.6 E + 0.4 C) times the gate (1, 0.7, 0) less 40, 15 and 3 per critical, material and minor finding; clamp to 0..100; any critical caps at 39 (Blocked), else any material at 59 (Restricted), else Passed; round half to even; 80 High, 60 Medium, 40 Low, below that Insufficient Information. The outcome has a state (`scored`, `blocked`, `absent`, `refused`) and a score only when scored |

## Rulings by the coordinator (2026-11-14; the owner can overturn any)

| # | Ruling | Cost if wrong |
| :--- | :--- | :--- |
| D1 | An earlier-format document gets one refusal and at most the summary warning | Delivery of a retained earlier run must not gate on findings; such runs get no prose checks |
| D2 | Passage presence and order are refused (the legacy checked only Bottom line) | Retries, inside the cap, for a module that drops a passage |
| D3 | Module kind, `scored`, required registers and non-file source names come from the orchestrator | Step 3A must supply them; a wrong list there mis-gates |
| D4 | Exact score, not the legacy float | One point apart in 59 of 400,000 sets, one a band change; 5A may show it against a legacy-scored run |
| D5 | Every count is ASCII digits, at most 20 (legacy: 4,000 for the two field counts) | None known |
| D6 | Currency is compared when both sides state one; `$` and `US$` read as USD, `€` EUR, `£` GBP, `¥` as written | A non-USD issuer writing `$` passes a `$` and USD mix |
| D7 | A unit column is not read: a bare cell matches any unit (legacy limit) | A scale changed against a bare cell under a unit column is accepted |
| D8 | Dates and period labels are masked, not matched against tables (legacy ruling) | A passage naming a period no table holds is accepted |
| D9 | A web row is refused as unpinned (decision 0008); the type list stays for the column | CP-DR cannot cite a public page; one rule to relax |
| D10 | The `sha256` column is checked when present, not required | A handoff naming files without hashes is accepted until 3A rules |
| D11 | `lost_values` is planned with 3A, in `checks/`, on this figure reader and typed findings | The repair loop records no dropped values until then; ports Pending `8e3954a..0985bb5` |
| D12 | CP-1's figure check and the net debt identity are 2B part 2, planned when 1B merges | 3A can start on PRs 1 to 6 but cannot accept CP-1 by the legacy figure rules until part 2 |
| D13 | A heading and a tag with one id in one section are one register | If not, retained `CP-2A.md` and `CP-2G.md` are refused |
| D14 | Blocked is `Reader.blocked` true or front matter `module_status: blocked`; it excuses the Sources table, required registers and the three later passages, and allows the one-row inputs table | A blocked module citing nothing is accepted |

## Answer keys (implementers do not edit them or weaken a comparison)

Written by the controller before each task, by reading, never by running a check or the legacy.

1. `tests/checks/expected/fixtures.json`: every finding (check, severity, line, quoted) for
   each of the 26 whole fixtures in `tests/fixtures/handoffs/`, with the context used. The 20
   retained files: one `structure.format` each. `SYNTHETIC-CP-2.md` with `SYNTHETIC-CP-1A.md`
   accepted repeats one limitation, at line 38.
2. New synthetic handoffs in `tests/checks/fixtures/`, about the existing fictional issuer and
   marked SYNTHETIC FIXTURE: a clean scored prose module, and one file per refusal that no
   fixture shows. No text or figure from a retained reply.
3. The legacy tests' cases, adapted: each snippet set in a six-section handoff, the expected
   check and quoted text taken from the legacy test unless a ruling above changes it.
4. Figure rows, hand-written: text to value, sign, unit and currency; passage figure against
   held text to held, not held or mismatch, with zero against a gap, currency and bracket rows.
5. Confidence rows worked by hand as fractions. The canon's example (8, 2 and 2 claims; 19 of
   20 fields; pass; one minor) is 89, High, Passed. Claims 6, 11, 10, 1, 9, 11, 3, 5; 35 of 40
   fields; partial; one minor: weighted claims are 24 of 56, so 0.6 E is 180/7; plus 35 is
   425/7; times 0.7 is 42.5; less 3 is 39.5, so 40, Low, Passed (the legacy float gives 39).
6. A hostile set, one test each: two headings with one id; a source name differing by case,
   by a trailing space and by one hex digit of its hash; a count in full-width digits and one
   of 21 digits; a line of 5,000 notes checked in linear time; a quoted text over 80 characters.

## PR sequence

| PR | Delivers |
| :--- | :--- |
| 1 | `Finding`, `CheckContext`, sentence and passage text; the structure checks |
| 2 | Prose checks 1 to 5, 9 and 10 |
| 3 | Prose checks 6 and 7 with the public limitation helpers; the Sources checks |
| 4 | The no-float test, the figure reader, `figure.form` (sensitive) |
| 5 | Held figures, `figure.not-held`, `figure.mismatch`, the note rule (sensitive) |
| 6 | Confidence inputs and score (sensitive); `check_handoff` and the key over all fixtures |

None of the six imports `model/`. A PR that would pass 800 lines is split, not trimmed of tests.
PR 3 (#198) is merged. Confirmed from it: the Sources headers are matched exactly as `sha256`
and `Source type`, and a stated sha256 on an `other_sources` row is refused; a row refused by
name is judged for type, not for sha256; `prose.register-id` gives one finding per match, the
id cell stripped of backticks, asterisks and spaces; a limitation item is each paragraph or
list item, quoted by its first line; the three Sources checks that read the table alone run
when `read_reader` raised. Ruled for the next checks PR, key rows first: `sources.table`
refuses a table with no rows in a module that is not blocked; a register id in underscore
emphasis is reported; the register-id reason points to the Basis line. Left and pinned:
`<anything> (CP-X)` is accepted whatever the name; a second table or a list under `## Sources`
is unread; `normalise_limitation` keeps the predecessor's key (`+5%` and `-5%` share one).

PR 1 is split: 1a (#157) `Finding`, `CheckContext` and the text helpers; 1b (#170) the
structure checks and `check_handoff`. PR 4 will be split: the reader with the no-float test,
then `figure.form`.

Ruled by the controller in PR 1 and confirmed: `Finding` has a 1-based `column`, used for
ordering only; `CHECKS` is closed at 32 ids; `check_handoff` starts in PR 1b and later PRs add
steps; passage text leaves out typed data sections and what is under them; `quoted` and
`reason` have control, format and line-separator characters replaced by a space, so a message
is one line; the context's mappings are read-only copies; a tag pairs with the nearest
preceding heading register of its id whose section holds it and that has no tag yet, and two
tags on one line are two registers; an empty required register id is always missing; an
unclosed fence in a passage gives both findings. PR 2 puts a word boundary before the
snake-case pattern, with a committed test that it matches what the plan's pattern matches.
For 3A: a finding's `quoted` is sent as data, not inside the message's quotes.

## How it runs

Global rules §1, §3 and §7. The sub-session is the controller and writes no code: `mx-feature`
implements test first; `mx-precise` reviews each task; `mx-adversary` also reviews the tasks
of PRs 4 to 6. Every brief and review prompt carries: no stub or fake value standing in for
real behaviour; no catch-all that hides a failure; no `assert` in source; the answer keys,
which the implementer does not edit; a report that ends with a `Not verified:` line.
Property tests (`hypothesis`): a figure copied from a cell is held, and is not once a digit,
sign, unit or currency changes; no gap text holds a zero; the score is 0 to 100, never rises
with a finding, is 0 on a failed gate, and is unchanged when all claim counts, or both field
counts, are multiplied by one factor. Per task the gate, exit 0, is
`uv run --locked python tools/gates.py` (run `npm ci` in `web/` once first). Before each PR is
ready: `/sweep refactoring discover changed-update`, then the whole-branch review
(`mx-architect` running `adversarial-reviewer`, fresh agent, §7 severities); verdicts and
report paths in the PR body; CI green on both runners, Windows read before a review is
dispatched. Fix rounds follow §1.

## Done when

Each PR is open with CI green and its reviews passed, and the sub-session has sent the
coordinator one message per PR: the PR number, verdicts, report paths, gate exit codes,
mutation result, ledger lines (`2B-<pr> task=<n> agent=<name> fix-rounds=<n>
gates-first-pass=<y|n|n/a>`), parked Low findings and a `Not verified:` line. The coordinator
reads the diff and merges. The sub-session does not merge and does not edit shared records.

## Not verified

- No retained new-format reply is checked: the rules rest on six synthetic handoffs, the
  legacy tests and the legacy's output on them. No fixture holds a scored inputs table.
- The legacy modules were run only on this repository's fixtures; the launcher, the repair
  loop and the end-to-end tests were read in part, not run.
- The public search used generic terms and found nothing to reuse; that does not prove
  nothing exists. No candidate's code or licence text was read beyond its listing.
- Whether the Copilot route emits check 9's markers; that 3A can supply every `CheckContext`
  field (3A is not planned); the six-PR split, an estimate from the legacy's size. The float
  comparison used random inputs with small counts, not real handoffs.
