# Step 3B: delivery

Date: 2026-11-14. Written by the back-end coordinator from two pre-flights, its rulings and the
merged slice contract, under decision 0006. The inputs are `preflight-inventory.md`,
`.superpowers/coord/3b/preflight-2.md`, `.superpowers/coord/3b/rulings.md`,
`slice-contract-rulings.md` and `note-for-backend.md`. Written against `origin/main` `32cd1494`.
Legacy is `legacy/main` `9d040f81` as the first inventory read it; never check it out or change it.

**Goal:** `src/credit_os/delivery/` turns an issuer's admitted runs into the library's data file.
It checks each delivered file against the store's receipt, reads each handoff through `handoff/`,
selects and orders what the modules wrote, and writes `data.js` and the downloads so that the two
merged slice readers accept them (`web/src/pages/library/read.ts`,
`web/src/pages/model/slice/read.ts`). The slice types are the contract (roadmap, "Pages are built
once").

**Reader:** a portfolio manager or credit committee member who has not read the sources. They
read judgement first. They see a source name, a file, a page or a hash only on Evidence and in the
trace control.

**What 3B does not do:** build or change a page; add analysis (no sorting into for and against, no
first-sentence split, no severity, no adjective); do arithmetic outside `model/`; parse Markdown
outside `handoff/`; call a model; open a socket; read a provider key; write HTML or a workbook;
change the content security policy (decision 0006 keeps that with the owner).

**Ends in:** a sequence of pull requests against `main`, each within 800 changed lines with its
tests, opened one at a time. One that would pass the cap is split and given a letter.

**This is sensitive code** (security: paths, the script-safe writer, hash checks, handoff text as
data; ordering: staging and replace; money: spend shown on Evidence).

## Files this step may touch

`src/credit_os/delivery/**` and `tests/delivery/**` (test modules named
`test_delivery_<topic>.py`: `tests/` has no packages, so a base name must be unique). By named PR
only: `src/credit_os/model/display.py` with `tests/model/test_model_display.py` (PRs 1a and 1b,
1B ruling 7 and R8); in `src/credit_os/handoff/`, the lead-label reader with its test (PR 4a) and
the cell-citation reader with its test (PR 8a), both ruled in R12. Pre-flight 2 shows both are
missing: `read_basis` reads only the last line of a paragraph or list item, and nothing reads a
bold lead. PR 14 adds one test file under `web/` (R16). Nothing else. Not `pyproject.toml` (standard
library and pydantic only), `VERIFICATION.md`, a decision record, `docs/legacy/ports.md` or this
plan; those are the coordinator's (PR 0).

**Layer rule.** `credit_os.LAYERS` is `sources`, `handoff`, `model`, `provider`, `store`, `checks`,
`orchestrator`, `delivery`, `signal`, with `signal` isolated (`src/credit_os/__init__.py`,
`tests/test_layering.py`). `delivery` may import the seven before it and never `signal`. It uses
`handoff`, `model`, `checks`, `store` and `orchestrator`; it imports nothing from `provider`, and
from `sources` only `pins.SourcePin`. A test reads the syntax tree and fails on any other import.
Reviewers check by reading that `delivery/` splits no handoff line, selects a table column or row
only by its exact header or label through a `handoff/` reader, compares dates only to order
them, and adds, scales or rounds no amount.

## Component boundaries

| Part | Takes | Gives | May not |
| :--- | :--- | :--- | :--- |
| Facts (`RunFacts`, `ModuleFacts`; delivery's own frozen types) | Plain values | What the builders read about a run: ids, dates, status, end reason, modules and outcomes, pins, counts, charges | Hold a connection, a path or a `Reply` |
| Store adapter | `StoreReader`, the orchestrator's total | `RunFacts` for every run of every issuer | Write to the store; compute a total |
| Admission check | Receipt bytes, the delivered folder | Verified bytes by file name, or a refusal | Parse a handoff; read a file twice |
| Builders (one per slice part) | `HandoffDocument`s, `RunFacts`, the wording file | Plain slice values with `Decimal` positions | Touch the disk; read the clock; match or split handoff text |
| Writer | The envelope value | The bytes of `data.js`, or a size refusal | Touch the disk |
| Library writer | Bytes by relative name, the target folder | The folder updated, or unchanged | Build a path from handoff text; delete a folder |

## Pre-flight (coordinator)

`preflight-2.md` holds every slice type's fields and reader rules, and each back-end name with
the step and PR that supplies it. In short: the handoff readers are merged except the two named
above; the figure reader is merged; the store has runs, pins and events only; `ForecastResult`,
`History`, attempts, calls, admission and all of 3A are pending. No library documentation is
needed (standard library only). A brief quotes the merged signature, never this plan's summary.

## Prior art

- Owner's repositories: the first inventory's section 2 (the predecessor). Reused from main:
  `handoff/` readers, `checks.figures.read_figures`, `checks.passages`, `model/`, `store/codec.py`.
  Read for behaviour: the predecessor's `platform_io.replace` and `write_atomic`, `checked_bytes`,
  `write_download`, `embedded_json`. Decision: adapt the rules, build the builders new.
- Public GitHub, searched 2026-11-14 with generic terms (`gh search repos`, Python, by stars):
  `atomic write`, `atomicwrites`, `reproducible zip`, `deterministic zip`. Found:
  `untitaker/python-atomicwrites` (MIT; its fork calls it unmaintained), `datalib/atomicio` (MIT),
  `bboe/deterministic_zip` (BSD-2-Clause), `drivendataorg/repro-zipfile`. Decision: build new on
  the standard library, no dependency and no copied code. PR 2 and PR 12a: a temp file in the
  target's folder, flush and `os.fsync`, then `os.replace` retried a bounded number of times on
  `PermissionError` (the rule of the predecessor's `platform_io.replace`). PR 12a's archive:
  `zipfile` with one `ZipInfo` per member, names sorted, a fixed `date_time`, fixed
  `create_system` and `external_attr`, stored members, no extra field and no comment. Its key
  compares the bytes on both CI runners. An empty or thin search does not prove nothing better
  exists; no candidate's code was read beyond its description.

## Legacy: what happens to each part

| Legacy | Ruling | Reason |
| :--- | :--- | :--- |
| `update_library.py` `embedded_json`, `checked_bytes`, `write_download`, staging and swap | Changed | Typed slices, not whole handoffs; one atomic replace of `data.js`; no folder swap, no delete |
| `update_library.py` CSP injection, `built_at`, the workspace path | Left behind | The policy is fixed in `web/index.html`; D5 |
| `credit_os/store.py` second Markdown parser, cash-flow grid, statement frames | Left behind | `handoff/` is the one parser; 1B ruling 1 |
| `store.py` `display_amount`, `display_date`; `ROW_CHARTS` fixed headers | Ported | PR 1a (in `model/`), PR 5, PR 8b |
| `credit_os_catalogue.py` `handoff_metrics`, `twin_of`, `pathway_title` | Ported | PRs 7 and 10; legacy `1360c215` |
| `credit_os_chips.py` locators, `MODULE_NAMES` | Changed | Trace keys and Evidence rows, not chips; names move to the module table (D9) |
| `chips.py` `read_pages`, `quote_span`, `excerpt_around`; `render.py` | Not here; left behind | No page text source, so `excerpt` is `null` (D11); React draws |
| `library_index.py` `mark_latest`, `build_library` sorting | Ported | PR 10 |
| `changes_data`, `cp8_verdicts` | Not here | 5A |

## Rulings

D1 to D12 are `rulings.md` 1 to 12. D13 to D19 are `slice-contract-rulings.md` 1 to 7. D20 to
D23 are its evening addition. D24 is the layer rule. Each is at least one test, named after it.

| # | Ruling | Cost if wrong |
| :--- | :--- | :--- |
| D1 | The library slice carries trace keys into `run.traces`; the model slice carries `#/` addresses. No narrative field carries a source name, file name, page or hash. A test scans every non-trace, non-Evidence text field of a delivered slice for source names and hash-shaped text | One test and the two address forms; no slice change |
| D2 | A passage is split only at a module-written mark (a sub-heading or a bold lead label). With none, the whole passage goes to the first field word for word and the second is empty or `null` where the slice allows; where the slice requires both, the item is refused and a stated gap is emitted. Never a first-sentence split or a cut. A finding's `number` is its position ("01") | Passages read as one block until the methods write marks; PR 4b's key |
| D3 | A cell is exact as the module wrote it. `at` and every position is the number `checks.figures` read (or the kernel's `Value`), written as a JSON number from `Decimal`, never through float. Half-up display is only for kernel-computed values, lives in `model/`, and is PR 1a | One mapping function; half-up on a module's cell would change every figure |
| D4 | Missing is `null`; a gap carries its reason word for word; withheld carries its reason. Never 0 and never an empty string for a missing value. One test per kind | One function and three key rows |
| D5 | The same admitted inputs give a byte-identical `data.js`: stated array order, fixed key order, times from the store, no clock, no absolute path, no host name | The byte-exact keys are rewritten |
| D6 | A `data.js` over 16 MiB is refused with its size. Nothing is cut to fit. Whole handoffs are never embedded | One constant; a large library is refused until it is raised |
| D7 | A blocked forecast module or `ForecastDeclined`: `forecastHref` is `null` and the run has no model run. The reason reaches the reader through the module's blocked body | The Forecast tab opens nothing for that run; a slice state would be a design step |
| D8 | Composed wording is a template of counts, dates and state words. No judgement, no adjective. Bands and labels are owner-set values in one file, not constants in code | The wording file and its key rows |
| D9 | Run id and issuer id are the store's, opaque, grammar `[A-Za-z0-9._-]{1,128}`. Module ids are slugs from one fixed table (code, slug, display name). No module code reaches a screen field | Every address and download name; a slug change breaks saved links |
| D10 | Changes is `none` only for the issuer's first report: of the issuer's runs that have a history entry, the one whose first admission event has the lowest `seq` (R10a, R10b). Every other written run is `pending` until 5A. Delivery guarantees the first report exists and that no history entry links a pending run's Changes page | One rule; 5A replaces `pending` |
| D11 | Evidence and record blocks are planned against the merged slice. `Trace.excerpt` is `null` until page text has a source | Mapping rows only |
| D12 | The `run` and `signal` members are omitted from a delivered file | Two members; 5C adds `run` |
| D13 | Overview `sides` is `null`. If modules later write two lists, delivery selects them | A section the mock shows is absent |
| D14 | Contrary evidence and change view split only at a module-written sub-heading or label. With none, the whole section goes to `contrary` and `changeView` is `null` | "What would change the view" is not drawn apart |
| D15 | Card `lead` is the lead module's Bottom line selected exactly: with no label, the whole passage word for word, never a first-sentence split (R13). "Refuse and gap" applies only where a slice field has a gap form. History `text` may be a counts template | Card and history text |
| D16 | `pending` is the third Changes state (as D10) | As D10 |
| D17 | Model `scatter` and `limits` are gaps with the reason; there is no holdings source and no substitute. Statement rows with no source are omitted | Two sections read as gaps |
| D18 | The slice was re-read after D2b's end push (pre-flight 2) | None |
| D19 | The model reader is per run. A run id is opaque text from the store, never a date | None |
| D20 | Confidence: delivery sends none. No nearest field is used | Nothing is shown until states 2 |
| D21 | Run end: "stopped for the cap" is `Capped`. Unknown spend, a charge above its hold and an operator stop have no state yet; delivery picks no nearest one, and such a run gets no history entry and no card until PR 15 (R6) | Those runs are invisible in the library until states 2 |
| D22 | A module not run because a required producer is missing is a blocked body with the reason word for word. A restricted module gets no composed sentence; it shows only what the module wrote as a limitation | One sentence a reader might expect |
| D23 | Check-written text (`reason`, `quoted`) is drawn as text only | None |
| D24 | `delivery/` sits after `orchestrator` in the layer list, parses no Markdown and does no arithmetic beyond calling `model/` | The import test's allow-list |

**Contract rules** (from the slice-contract note and the roadmap rulings; each a test):

| # | Rule |
| :--- | :--- |
| C1 | `Overview.sides` and `Overview.changeView` are always present as keys; `null` draws nothing |
| C2 | `Changes` is `none`, `pending` or `compared`. For `none` and `pending`, `title` and `text` hold a character that is not whitespace |
| C3 | The reader counts history entries only. Delivery itself proves the first report (R10a, R10b) exists and is another run before `pending`, and emits `none` only for that first report; the reader catches neither mistake |
| C4 | No history entry carries a `changes` link to a pending run; a pending run's issuer has two or more entries |
| C5 | Issuer and run ids hold no `/` and no `%`. `forecastHref` is exactly `#/model/<issuer>/<run>/forecast` or `null` |
| C6 | A delivered file address is a relative path: every segment in `[A-Za-z0-9._~@+=,-]` or `%XX`; none is `.` or `..` before or after decoding; no decoded `/` or `\`; every escape valid UTF-8 |
| C7 | Run ids are compared for equality only |
| C8 | Model `limits` and `scatter` are the chart or `{gap: {title, reason}}`, nothing beside `gap`, both texts filled; `gap.title` is unique among the page's names |
| C9 | The model slice is delivered as `{runs: [...]}`. `unreadable` is never delivered. No `(issuer, run)` pair twice |
| C10 | `published.href` is a relative path; `checkFigure.href` is a `#/` address or a relative path; every model trace and in-library link starts `#/` |
| C11 | A segment text is "<earlier or n.a.> to <later or n.a.>"; a headroom text starts with its first table cell, then a space |
| C12 | Delivery never writes `%00` in an address or a bare `#/` (both readers accept them; an open owner question) |
| C13 | P1-3: a `run` slice's first draft is at the documents step. 3B writes no `run` member (D12); the rule passes to 5C |
| C14 | P1-12: no module code, register id or hash in a narrative field. D1's scan uses the merged pattern `checks.figures.CODE` |
| C15 | States 2 (roadmap rulings, section A: questions 1, 3, 5 to 9, 12, 14, 15) binds PR 15, not the file 3B writes first |

**Departures from the mock** (for the owner; the coordinator records them; X11 and X12 were
withdrawn):

| # | Departure |
| :--- | :--- |
| X1 | For and against is not drawn (`sides: null`) until modules write it |
| X2 | Home subtitle, count lines, progress text, applied-filter labels, history text, summaries, link labels and Evidence titles are composed by delivery from counts, dates and state words |
| X3 | The holdings scatter and the exposure limits are gaps |
| X4 | No confidence is sent until the states 2 build changes the slice |
| X5 | No stop reason is sent; a run stopped for a reason other than the cap has no word |
| X6 | A restricted module carries no mark |
| X7 | Changes reads `pending` for every run after an issuer's first listed report (R10b), until 5A |
| X8 | A trace has no quoted excerpt |
| X9 | The model-calls table has no Code column (D9, R14; the fixture shows one) |
| X10 | Record blocks are sent only for chart tables and their gaps; a module table with no kind is only in the handoff download until PR 8c (R3) |
| X13 | A run that cannot meet a reader minimum has no report (R1). A run stopped for a reason with no state word is not in the library at all until states 2 (R6). No run has a Forecast until slice contract 3 (R7) |

## Mapping

Kind: **select** (module or store text, exact), **format** (a date, a state word, an address),
**count** (a whole-number count in a template), **kernel** (a value `model/` or the orchestrator's
budget computed), **config** (the wording file, `src/credit_os/delivery/wording.json`: owner-set
words, bands and labels; the states 2 build reads the same file). The lead module is the pathway's
final synthesis module, from a fixed table (R2). "Not written" means the run is left out of
`runs`, its history
entry has `report: null` and a counts text, and the delivery result names the run and the rule (R1).

| Slice field | Source | Kind | When the source is missing |
| :--- | :--- | :--- | :--- |
| `schema`; `issuers[]` | Constant; the store's issuers that have a history entry (R6), name from the newest run, sorted by id | format; select | `[]` |
| `library`, `model`; `run`, `signal` | Built; omitted (D12) | | `model` is `{runs: []}` when no run has a forecast |
| `home.subtitle`, `list.measures.*.countLine` | Counts of issuers, runs and measures recorded | count | Always present |
| `home.filters.sector`, `.pathway`, `.state` | The cards' distinct values, sorted | select | `[]` |
| `filters.appliedLabels`, `measures.*.name`, `.bands` | Wording file; first values are the mock's (R15) | config | A file that fails its schema is a refusal |
| `cards[]` | One per issuer in the library, by name then id | select | No `loading` card is ever written |
| card `state` | The status and end reason of the newest run that has a history entry, through the state table (D21) | format | A run with no state word has no entry and no card of its own (R6) |
| card `lead` | The lead module's Bottom line, of the run the card opens (D15, R13) | select | The wording file's state sentence |
| card `note` | Template, when a newer run is in progress (decision 0006 ruling 12) | count | `null` |
| card `asOf`, `pathway`, `sector` | `RunRecord.as_of`; the request's pathway by a fixed name table; the run context | format; select | "Not recorded" from the wording file, never empty |
| card `progress` | Delivered modules of planned modules | count | `max` is the planned count; a run with none planned is not carded |
| card `href` | The newest written run's id | select | `null` |
| card `measures.*` | The foundation module's `Chart data:` rows (legacy `handoff_metrics`, adjusted twin); `text` the cell; `at` by `read_figures` | select | `null`. The Home type holds no reason; the reason is on the Overview metric |
| `history.entries[]` | Every run of the issuer except those R6 leaves out; newest `as_of`, then `created_at`, then id | select | `[]` cannot occur: such an issuer is not in the library (R6) |
| entry `asOf`, `ran` | Store dates in UTC; the time is added when two entries would share both | format | `as_of` absent: "Not recorded" |
| entry `state`, `pathway`, `text` | State table; name table; counts template | format; count | A run with no state word has no entry (R6) |
| entry `report`; `changes` | The run id when the run is written; `null` until 5A | select | `null` |
| `history.latest`, `empty`, `subtitle` | The newest entry with a report; else the wording sentence; counts | select; config | Exactly one of the two |
| `run.id`, `loading` | Store run id; always `false` | select | |
| `head.*` | Issuer name, as-of, pathway, state; module count; first module's id | select; format; count | `firstModule: null` only with no module |
| `head.forecastHref` | The exact address when a model run is written for this run | format | `null` (D7) |
| `run.traces` keys | Made by delivery by position (`t-0001`); never handoff text | format | `{}` |
| trace `statement` | The passage body without its Basis line (`Basis.body`) | select | The item carries `trace: null` |
| trace `title`, `heading`, `subtitle` | Template: item label, module name, kind word, as-of | config | |
| trace `derivation` | The Calculations row a Basis item names: its name, result and steps cells; no children | select | One node, `value: null` |
| trace `excerpt`, `qualification` | None (D11); none | | `null` |
| trace `evidenceItem` | The row id (`T-0001`) of the same item | format | Always present |
| `overview.bottomLine`, `findings[]`, `limitations.items` | The lead module's `Reader` passages (D2); limitations through `limitation_texts`, deduplicated by `normalise_limitation` | select | The run is not written (R1) |
| `overview.metrics[]`, `metricsLabel` | The foundation's headline chart rows; value by the cell rule (D4); label from the wording file | select | `[]` |
| `overview.sides`; `changeView` | `null` (D13); D14 | | `null` |
| `overview.dates[]` | The `Events:` section's rows; `state` by date order against the as-of date (legacy `bd8d2b47`, `84d922ec`) | select; format | The run is not written (R1) |
| `overview.modules` | One item per module, never collapsed: display name, the module's Bottom line (or blocked reason), state; summary by count | select; count | A run with no module is not written |
| `limitations.count`, `gapsLink.label` | Item count; template naming the Evidence gap count | count | No file is written before PR 6b, so the count is never a false 0 (R4) |
| `changes` | `none` or `pending` (D10, R10a), wording from the file | config | |
| `modules[]` order, `id`, `name` | The run's plan order; the module table (D9) | select | |
| module `state` | Accepted and not blocked: "Delivered", or "Delivered with gaps" when its `## Gaps` table has a row (R5); `is_blocked` or a failed module: "Not assessable"; unstarted in an ended run: "Not run"; producer missing: D22 | format | |
| delivered body passages | The module's own `Reader`, as the Overview rows | select | No finding or no limitation: the run is not written (R1) |
| `records[]` | A `chartTable` for a `Chart data:` section whose fixed header names a chart kind; a `gap`, its reason from the wording file, for one with no readable table; nothing else (R3) | select; config | `[]` |
| blocked body | `reason`: the text after `Not assessable:`, or the store's reason; `note`, link label from the file | select; config | |
| `evidence.intro`, titles, column heads | Wording file | config | |
| `moduleFilter[]` | The run's modules; initials from the module table | select | |
| `summary` | Counts; run id; the delivery's SHA-256; the handoffs archive address | count; select | `download.href: null` with the reason |
| `sources.files[]` | The run's pins in order: name, kind, SHA-256; size read as an integer and shown in megabytes by PR 1b (R8); state and reason from 3A's ingest; readers are the modules whose Sources table names the file (`source_names`) | select; kernel | An unreadable file carries its reason |
| `sources.visible`, `moreLabel` | Wording file; count | config; count | `null` when none is held back |
| `trace.rows[]` | One per traced item and calculation, ids by position (gap rows come with PR 6b); `value` by the cell rule; `sources` the count of source items in the Basis | select; count | `emptyText` from the file |
| `gaps.groups[]` | PR 6b, after the gap-severity PR (R4a): each module's `## Gaps` rows, the gap and its effect word for word, in one group with `severity: null`. Delivery never ranks a gap (R4) | select | A run with no gap has no group |
| `record.timings` | Attempt times from the store; elapsed minutes by PR 1b (R8) | kernel | `null` cells |
| `record.hashes` | Method texts' hash, configuration id, request SHA-256, delivery SHA-256 | select | An item is left out; at least one always exists |
| `record.spend` | The orchestrator's exact total and `cap_usd` | kernel | Unknown spend: the run has no entry (R6) |
| `record.calls` | Calls, retries, tokens and cost by module, from the store; token sums by PR 1b; no Code column (R14) | count; kernel | A missing count is `null` |
| `record.registers` | `read_registers` per module: id, module name, row count; Open is the module's handoff copy | select; count | A run with none is not written (R1) |
| `jump[]` | One per figure row and calculation row; gap rows with PR 6b | select | `[]` |
| Model `header`, `links`, `forecast.tabs` | Store row; addresses built from ids; `sample` always `false` | select; format | |
| Model `cases`, `forecast.*`, bridges, comparison | `ForecastResult` (1B PR 7), the two cases the model fixture names (R7); display by PR 1a, positions by PR 1b | kernel | No model run (D7) |
| Model `statements` rows, `analysis.measures` | `History` (1B PRs 10, 11) | kernel | Rows with no source omitted (D17) |
| Model `limits`, `scatter` | None | | Gap (D17) |
| Model `ratings`, `relativeValue`, `strips`, `headroom`, `segments`, debt stack, maturities, recovery | A legacy owner table (the fixed `ROW_CHARTS` headers) where a module writes one; holdings have none (R7) | select; kernel | A `SectionGap` after slice contract 3. Until then no model run is written for any run (R7) |

An earlier-format document (`checks.text.is_earlier`) is refused: 3A never accepts one (3A D19).

## Hash checking and writing

Handoff bytes come from a delivered folder, written by the step that calls `admit_delivery` (R9)
and checked here against the 2A receipt. 3B writes the openable library folder itself; 4X copies
the built front end around it and never rewrites `data.js` (R9).

What is checked, in this order. Any failure is `DeliveryRefused` naming the run, the file's shown
name and the kind (missing, extra, changed, receipt changed, not a plain file). The whole build
is refused and the library folder is untouched.

1. A run's delivery is the one whose admission event has the highest `seq` (R10); `admitted_at`
   is shown and never ordered on. The stored receipt bytes hash to its key (`delivery_sha256`).
   The receipt is read as strict JSON and its run id is the run's.
2. The delivered folder holds exactly the receipt's files: none missing, none extra, each a plain
   file (no link, no junction, no folder). Two names equal after case folding or Unicode
   normalisation are refused.
3. Each file is read once, under a size cap, and the bytes held are hashed and compared with the
   receipt. Those same bytes are parsed and copied. No file is read a second time.
4. Each handoff's SHA-256 equals its module's accepted reply SHA-256 in the store.
5. All slices are built in memory and written to bytes. Over 16 MiB is a refusal (D6).

Writing, after every check has passed:

6. A staging folder is made beside the target, on the same volume. Every byte is written in
   binary mode, flushed and synced, then read back and hashed. A download's hash must equal its
   receipt hash; an archive's and `data.js`'s must equal the hash of the bytes built.
7. Downloads move in first. Each delivery has its own folder (S1, R20), so a name is never one an
   earlier delivery used for other bytes. A target that exists with the same hash is kept; with a
   different hash it is a refusal (an integrity check, never a replacement).
8. `data.js` moves in last, by one atomic replace. It is the only file ever replaced.
9. On any failure before step 8 the old `data.js` still names only files that are in place, so
   the old library opens as before. Staging is cleared file by file from delivery's own list, then
   its empty folder is removed. No recursive delete and no delete on a path built from a variable.

Invariants for review: I1 `data.js` never names a file that is not in place and verified. I2
Nothing delivery did not write is removed or replaced. I3 A refusal writes nothing outside
staging. I4 A crash at any point leaves a library that opens. I5 A second run on the same inputs
writes the same bytes.

## Security

| # | Row | Rule and test |
| :--- | :--- | :--- |
| S1 | Path traversal in download names | A name is built only from fixed words, a module slug from the table, and a folder key that is the first 20 hex characters of the SHA-256 of UTF-8 `<issuer>/<run>/<delivery_sha256>` (R20; the delivery hash is the store's 64 lower-case hex, checked before hashing). No handoff text, source name or raw id is a path segment. Rows: ids `.`, `..`, `a.`, `CON`, `nul.md`, two ids differing by case |
| S2 | Addresses | Every `href` is joined from segments with `/`, never from an OS path. Each is checked against C6 in Python before it is written. `#/` addresses are built from ids checked against C5; `.` and `..` as ids are refused |
| S3 | Script-safe JSON | The file is `window.CREDIT_OS_DATA = JSON.parse("...");` in the form `web/scripts/fixture-data.mjs` writes, but stricter: that writer escapes only `<`, U+2028 and U+2029, and delivery's output is ASCII only, with `<` and every non-ASCII character written as a backslash-u escape; a lone surrogate is refused. Rows: `</script>`, `<!--`, both separators, a quote, a backslash, a NUL |
| S4 | No `unsafe-inline` | Delivery writes no HTML and no script but `data.js`, loaded under `script-src 'self'` (`web/index.html`). No policy is written or changed |
| S5 | Size | D6 on `data.js`; a per-file read cap; a cap on files per delivery. A size is stated by a number in tests, never by a large file on disk |
| S6 | Handoff text is data | Every field is a JSON string. No object key comes from handoff text (trace keys and ids are made by delivery). Template values are inserted as text and never re-read as a template. Rows: `__proto__`, `constructor`, `{0}`, an instruction-like sentence, a `javascript:` address in a cell |
| S7 | Numbers | A position is a finite `Decimal` written as a plain JSON number: no exponent beyond what `JSON.parse` reads, no NaN, no Infinity, no negative zero |
| S8 | Windows paths | Binary writes, so no line-ending change and one hash on both systems. Paths stay short (hashed folder keys). No reserved device name, trailing dot or trailing space can be a segment (S1) |
| S9 | Windows replace | `os.replace` on the same volume. A sharing violation is retried a bounded number of times with the wait injected; tests patch the call to raise and never sleep. After the last retry it is a refusal and the old file stands |
| S10 | Links in the delivered folder | A symlink, junction or reparse point is refused before any read (step 2) |
| S11 | Diagnostics | A refusal shows a file's shown name, never an absolute path (3A D12) |

## Sensitive code

| Area | PRs | Besides `mx-precise` |
| :--- | :--- | :--- |
| Security: writer, paths, addresses, hash check, handoff text as data | 2, 3, 6, 6b, 12a, 12b | `mx-adversary` |
| Ordering: staging, verification, replace | 12a | `mx-invariants` |
| Money and figures: display rounding, cells, spend and call costs | 1a, 1b, 4b, 9, 13a | `mx-adversary` |

Mutation testing is the reviewer's, on the changed files of each PR above: `mutmut` through `uvx`,
valid only after the 3A plan's three checks, within the two machine-wide slots. Survivors are
killed or justified.

## Answer keys (implementers do not edit them or weaken a comparison)

The controller writes each key by hand before the task, from invented values, never by running
the code under test, the web readers or the predecessor. Every fixture is synthetic, says SYNTHETIC
FIXTURE and names no real issuer or person. A key compared byte for byte gets a `.gitattributes`
`-text` line.

| PR | Key | How its values are produced |
| :--- | :--- | :--- |
| 1a | `tests/model/expected/display.json` | Half-up rows worked by hand and checked with `bc`: ties at each place, negatives, zero, a missing value (text absent, never "0"), 38 digits; number tokens for integers, fractions and trailing zeros |
| 1b | `tests/model/expected/scales.json` | Positions, ticks, axis maxima, shares, elapsed minutes and token sums worked with `fractions.Fraction` and checked with `bc`; a missing input gives a missing result, never 0. File sizes in megabytes, half-up to one decimal: 0 bytes, 1 byte, exactly 1 MiB and a tie |
| 2 | `tests/delivery/expected/writer/*.js` | The exact bytes for six small envelopes, typed by hand; SHA-256 by `shasum`. One row each for S3's characters, key order, a `Decimal` position, and a 16 MiB-plus-one size stated by number |
| 3 | `delivery_names_key.py` | The module table copied by reading the predecessor's `MODULE_NAMES`; addresses and download names for invented ids, the folder key by `shasum`; S1's and S2's refusal rows |
| 4a | `tests/handoff/expected/lead-labels.json` | Literal paragraphs and list items: a bold lead, none, two, bold in mid-sentence, bold inside a code span |
| 4b | `tests/delivery/expected/passages.json` | By reading the committed synthetic new-format handoffs: each passage word for word; a marked and an unmarked case; each cell kind (D4); a blocked body |
| 5 | `tests/delivery/expected/wording.json` | Each template filled by hand for counts 0, 1, 2 and 13; dates for the first and last day of a year |
| 6 | `tests/delivery/expected/traces.json` | By reading the synthetic CP-2 handoff: keys, row ids, statement, derivation from its calculation row, source counts, the jump list |
| 6b | `tests/delivery/expected/gaps.json` | Written after slice contract 3 (R4): the gap rows in one `severity: null` group and the counts, by reading the same handoff |
| 7 | `tests/delivery/expected/overview.json` | A synthetic run of four modules, one blocked, with literal `RunFacts`: items, states, metrics from a synthetic foundation table with reported and adjusted columns, dates each side of the as-of date |
| 8b | `tests/delivery/expected/records.json` | A synthetic chart section per fixed header; a section with no readable table |
| 8c | The same file, extended | Written when the design step's plan gives the shape: a synthetic module table with no chart kind |
| 9 | `tests/delivery/expected/evidence.json` | Literal `RunFacts`: three pins, one unreadable; two modules' calls with one missing count; spend below and equal to the cap, sums by `bc`; registers by reading the fixtures |
| 10 | `tests/delivery/expected/home.json` | Literal `RunFacts` for three issuers: one run; two runs (`none` then `pending`); a failed only run (`empty`); two runs sharing as-of and day; a run with no state word beside another run (no entry, no card of its own) and alone on its issuer (issuer absent) (R6) |
| 11 | `delivery_facts_key.py` | Store rows written by the test through the store's public methods; the expected `RunFacts` as literals |
| 12a | `delivery_write_key.py` | A case table by hand: the folder's files and hashes after success, after a failure at each step (the call patched to raise), after a second identical run |
| 12b | `delivery_admit_key.py` | A receipt typed by hand with its SHA-256 by `shasum`; rows for a changed byte, a missing file, an extra file, a link, a changed receipt, another run's receipt, two names equal by case |
| 13a, 13b | `tests/delivery/expected/model-run.json` | Synthetic forecast inputs; every figure worked with `fractions.Fraction` and checked with `bc`, independent of `model/` |
| 14 | `tests/delivery/expected/library/data.js` | The whole file for a two-issuer, three-run synthetic library, typed by hand from the keys above; SHA-256 by `shasum` |

Property tests (`hypothesis`): any text in any field gives a file whose literal holds none of
S3's characters raw and whose parsed value equals the input; any id in the store's grammar gives
addresses that pass C5 and C6 or a refusal; output bytes do not depend on input mapping order.

## PR sequence

"Now" means the PR builds on merged code only; builders take literal `RunFacts` in tests, which
are test inputs, not stand-ins in source. A PR also follows the rulings (R1 to R16) that name it.

| PR | Delivers | Needs | Start | Review |
| :--- | :--- | :--- | :--- | :--- |
| 0 | Docs, the coordinator's: this plan, the ports lines, the departures; the mock's band values and labels listed in its body for the owner (R15); the public prior-art search | Nothing | Now | `mx-feature`, batched |
| 1a | `model/display.py`: half-up display text of a kernel `Value`; a `Decimal` as a JSON number token | Merged code | Now | P, A |
| 1b | `model/display.py`: positions, ticks, axis maxima, shares, elapsed minutes, token sums, file size in megabytes; exact `Decimal` or `Fraction` (R8) | 1a | After 1a | P, A |
| 2 | The writer: envelope, fixed key order, ASCII, the script-safe literal, the size refusal; bytes only | 1a | After 1a | P, A |
| 3 | The module table, ids, `#/` addresses, download names, the folder key, the Python check of C5 and C6 | Merged code | Now | P, A |
| 4a | `handoff/`: the lead-label reader | Merged code | Now | P |
| 4b | Passages and cells: bottom line, findings, contrary and change view, limitations, blocked body; D1's scan | 4a | After 4a | P, A |
| 5 | The wording file with its schema, the templates, display dates, the state table (the states that have a word only, R6) | Merged code (R6, R15) | Now | P |
| 6 | Traces, the Evidence trace table and the jump list; no gap rows | 4b | After 4b | P, A |
| 6b | Gap rows, groups and their trace and jump entries | 6; slice contract 3's `severity: null` part (R4) | Waits for the gap-severity PR (R4a) | P, A |
| 7 | `RunFacts`; modules, states, the Overview | 3, 4b, 5, 6; the lead-module table from 3A PR 1 (R2) | Waits for 3A PR 1 | P |
| 8a | `handoff/`: the cell-citation reader, `read_cell`, on the Basis item grammar (R21) | Merged code | Now | P |
| 8b | Record blocks: chart tables and their gaps (R3) | 8a, 4b | After 8a | P |
| 8c | Record blocks: the plain-table kind | 8b; slice contract 3 and the shape in its plan | Waits for slice contract 3 | P |
| 9 | Evidence summary, sources and record | 7, 1b | After 7 | P, A |
| 10 | Home, History, Changes `none` and `pending` | 7 | After 7 | P |
| 11 | The store adapter: `StoreReader` to `RunFacts` | 2A PRs 3c and 5b; 3A PRs 1, 2a, 7c, 9a; 2A's read of all issuers and each issuer's runs (R11) | Waits for 2A PR 5b, that read and 3A PR 7c | P |
| 12a | The library writer: staging, read-back, downloads, the archive (stored, fixed dates and order), the atomic replace, into the library folder itself (R9) | 2, 3 | After 2 and 3; its end-to-end case after 6b (R4) | P, A, I |
| 12b | The admission check against the receipt | 2A PR 5b; the delivered folder's layout from 3A's brief (R9, R10) | Waits for 2A PR 5b | P, A |
| 13a | Model slice: cases, forecast page, front page, limitations | 1B PR 7; 1a, 1b; slice contract 3. Every kernel case, two to four (R7a) | Waits for 1B PR 7 and slice contract 3 | P, A |
| 13b | Model slice: statements and measures | 1B PRs 10 and 11 | Waits for 1B PR 11 | P |
| 14 | The slice readers accept a delivered file (below) | 2 to 10 and 6b (R4, R16); 8c, 13a, 13b and 15 each extend its key | After 10 and 6b | P |
| 15 | Confidence, stop reasons, restricted modules | The states 2 build merged | Waits for states 2 | P |

Can start now: 0, 1a, 3, 4a, 5 and 8a. Review: P is `mx-precise` on every task; A adds
`mx-adversary` (security or money); I adds `mx-invariants` (staging and replace ordering). No
library folder and no delivered file is written before PR 6b has merged (R4).

**PR 14, the reader proof.** A web test reads the hand-written key
`tests/delivery/expected/library/data.js` through `readLibraryData` and both `readSlice`s and
expects `ok` with no unreadable run. A Python test proves delivery writes that key byte for byte.
So the readers accept what delivery writes, and neither side's output is the other's key. It adds
one test file under `web/src/pages/` and changes no page, reader or fixture. Ruled R16: it is in
3B, the last of its builder PRs, in a slot the roadmap coordinator gives. 4A still proves a real
delivered folder.

## How it runs

Global rules §1, §3 and §7. The sub-session is the controller and writes no code. `mx-scaffold`
takes mechanical work with a complete spec; `mx-feature` takes the rest, test first. At most two
Sonnet fix rounds per task; a third only as a plan by `mx-autonomous` run by a fresh `mx-feature`;
no fourth without the owner. Reviewers save each probe as a script under `.superpowers/sdd/`; the
fixer runs it and reports its exit code.

Every brief and review prompt carries:

- No stub or fake value standing in for real behaviour. A field with no source is `null`, a
  stated gap or a refusal, as the mapping says; never a sample value.
- No catch-all that hides a failure. 3B has none: every refusal is typed and nothing fails open.
- The answer key rule. Missing stays distinct from zero; amounts, currency, units, periods and
  source identities stay exact.
- The OS-limit rule: loops capped at 1,000; a failure is simulated by patching the call; a large
  file is a stated size. No delete on a path built from a variable; tests write under `tmp_path`.
- No `assert` in source. No provider, no network, no key. A report ending `Not verified:`.

Per task the affected tests run first. Before a task is done both gates exit 0:
`uv run --locked python tools/gates.py` (after `npm ci` in `web/`) and `npm --prefix web run
gates`. Before each PR is ready: `/sweep refactoring discover changed-update`, then the
whole-branch review (`mx-architect` running `adversarial-reviewer`, fresh agent, §7 severities);
CI green on Windows and Ubuntu, both read before a review is dispatched; gitleaks on the range
before each push.

## Done when

Each PR is open with CI green and its reviews passed, and the sub-session has sent the
coordinator one message per PR: the PR number, verdicts, report paths, gate exit codes, the
mutation result with its three validity checks, ledger lines (`3B-<pr> task=<n> agent=<name>
fix-rounds=<n> gates-first-pass=<y|n|n/a>`), parked Low findings and a `Not verified:` line. The
coordinator reads the diff and merges. A PR whose inputs are still literal `RunFacts` is built,
not done, until PR 11 and PR 12b have run it on store rows.

## Rulings on the draft's questions

All are the coordinator's, made under the owner's instruction of 2026-11-14 22:20 UTC ("resolve
all decisions"). The owner can overturn any.

| # | Ruling | Cost if wrong |
| :--- | :--- | :--- |
| R1 | A run that cannot meet a reader minimum (a bottom line, a finding, a date, a limitation, a source file, a call row, a hash item, a register row; per delivered module a finding and a limitation) is left out of `runs`. Its history entry has `report: null` and a counts text, and the delivery result names the run and the rule. Never filler. A capped run whose lead module was delivered is written (decision 0006 ruling 12); one with no lead module is left out and named. The coordinator asked the design track to read the library slice per run, as the model reader does (slice contract 3) | A run with one missing passage is absent from the library rather than shown with a gap |
| R2 | The lead module comes from a fixed table by pathway in `delivery/`: one module per pathway, ruled by the coordinator from the modules and pathways 3A PR 1's catalogue lists (that catalogue names no lead module itself); PR 7 waits for the ruling, which follows 3A PR 1's merge | One table |
| R3 | A `chartTable` block for a `Chart data:` section whose fixed header names a chart kind; a `gap` block for one with no readable table; nothing else until the methods write a mark (phase 6). The plain-table record kind the coordinator asked for is slice contract 3's, written by PR 8c | Module tables with no kind are only in the handoff download |
| R4 | Delivery never ranks a gap. The methods add a severity column in phase 6. PR 6 ships traces and the jump list; the gap rows are PR 6b, which waits for the design track's gap-severity PR (R4a: a gap group may carry `severity: null`, drawn after the ranked groups). No library folder is written before PR 6b has merged: PR 12a's end-to-end case, PR 14 and any delivered file wait for it, so a run whose modules wrote gaps never reads "0" on a screen | No library is delivered until the gap-severity PR and PR 6b have merged |
| R5 | A module is "Delivered with gaps" when its `## Gaps` table has at least one row | One rule; a module with a gap cell and no Gaps row reads "Delivered" |
| R6 | Until PR 15, a run stopped for unknown spend, a charge above its hold, or by the operator gets no history entry and no card of its own; the delivery result names it. If it is the issuer's only run, the issuer is not in the library. PR 5's state table and PR 10's key hold the other states only. Never the nearest state | Such a run is invisible in the library until states 2 |
| R7 | Until slice contract 3 widens `SectionGap` to the sections with no source and fixes the case rule, no model run is written for a run that cannot fill a required section, so `forecastHref` is `null` (D7). The holdings `strips` have no source in any run, so that is every run. PR 13a waits for slice contract 3. PR 13a therefore starts after slice contract 3 and writes every case the kernel gives, two to four (R7a). Legacy owner tables (the fixed `ROW_CHARTS` headers) are the source where a module writes one | The Forecast tab is absent for every run until slice contract 3 |
| R8 | Every derived number that needs arithmetic (elapsed minutes, sums of tokens, shares, positions, ticks, axis maxima) is a function in `model/display.py`, exact `Decimal` or `Fraction`, with hand-worked keys. A file size is read as an integer and only its display is computed (PR 1b: bytes to megabytes, half-up to one decimal, as the mock shows it). Counts are counted, not arithmetic. PR 1 splits into 1a (display text, JSON number) and 1b (positions and scales) | `model/` holds display functions that are not financial; one more PR |
| R9 | Bytes come from a delivered folder checked against the 2A receipt. Its writer is to be 3A: 3A's plan on main names no `admit_delivery` call and no folder writer yet, so the coordinator adds both to that plan before PR 12b's brief. 3B writes the openable library folder itself; 4X copies the built front end around it and never rewrites `data.js` | 3A gains a folder writer; another target would move the atomic replace into 4X |
| R10 | The delivery shown for a run is the one whose admission event has the highest `seq` (the store's event sequence is store-wide and in commit order). `admitted_at` is shown and never ordered on | One sort rule; an earlier delivery of a run is never shown |
| R10a | An issuer's first report (Changes `none`) is the run whose first admission event has the lowest `seq`. A run with no admitted delivery is never the first report | 5A changes one rule if it defines "earlier" by `as_of` |
| R11 | 2A adds, in its PR 5: the read of all issuers and each issuer's runs; and an event appended at each admission, so the store-wide `events.seq` orders admissions (the 2A plan on main has `admitted_at` only; 2A's controller has recorded both as its rulings U19 and U20, and the coordinator amends the 2A plan). `delivery/` holds no SQL. PR 11 waits for it | One 2A read |
| R12 | Both `handoff/` readers, as PRs 4a and 8a | Two small readers where the brief allowed one |
| R13 | The card lead is the whole passage, word for word. D15's "refuse and gap" applies only where a slice field has a gap form | A long unmarked Bottom line fills the card |
| R14 | The model-calls table has no Code column (X9 stands) | One column |
| R15 | The mock's band values and labels go in the wording file, each listed in PR 0's body for the owner | The home list screens on bands the owner has not confirmed |
| R16 | PR 14 is in 3B, its last PR, one test file under `web/`, in a slot the roadmap coordinator gives | One `web/` slot; the key grows with each later PR |

**Waits for slice contract 3** (the design track's answer to the coordinator's four asks; ruled
yes by the roadmap coordinator, not yet built):

| Part | What it changes for delivery | PR |
| :--- | :--- | :--- |
| Per-run reading of the library slice | R1's interim stands until then. Afterwards an unreadable run is the reader's state and delivery writes every run it can build | 7 and 10 carry R1's rule; the follow-up is named when the step merges |
| `severity: null` on a gap group, drawn after the ranked groups | Gap rows are written, unranked | 6b |
| A plain-table record kind | A module table with no chart kind becomes a block; its shape comes from the design step's plan | 8c |
| `SectionGap` on `ratings`, `relativeValue`, `strips`, `headroom`, `segments`, the debt stack, maturities and recovery; two to four cases | A model run can be written. The statements themselves stay required | 13a |

**Last rulings (the coordinator's, same instruction).**

- R10b: R10a counts only runs that have a history entry. When an issuer's earliest admitted run is
  one R6 leaves out, the earliest listed run is the first report (`none`), so no run is `pending`
  on a history of one entry. Cost: "first report" is said of a run that had an unlisted one
  before it.
- R8a: megabytes are bytes divided by 1,000,000, half-up to one decimal ("1.0 MB" for 1,048,576
  bytes). A page count beside a size has no source: it is `null` if the slice allows and otherwise
  PR 9's brief brings the field to the coordinator.
- R7a: no model run is written before slice contract 3, so the reader's present two-case rule never
  binds delivery; PR 13a writes every case the kernel gives (two to four), named as the kernel names
  them.
- R4a: the `severity: null` part is pulled forward as its own small design PR
  (`claude/gap-severity-null`): the key is always present, `null` or High, Medium, Low; ranked
  groups first, then at most one `null` group, last, headed "Not ranked"; a table whose only group
  is that one is valid. PR 6b waits for that PR, not for the whole of slice contract 3.
- R17 (PR 1a): `display_text` rounds half-up away from zero on the magnitude, groups the integer
  part with commas, pads to the places asked (0 to 6), writes no negative zero, and gives no text
  for a missing value. `json_number` writes a plain token with no exponent and refuses an amount
  out of the kernel's bounds; the token is exact, and digits past about 17 are not carried by
  `JSON.parse`, accepted because the front end computes nothing.
- R18 (PR 4a): a lead label is exactly the text inside the bold marks at the start of a block; a
  colon right after the closing mark is dropped; the trailing Basis line is left to `read_basis`.
- R19 (PR 3): the module table is 25 rows (code, slug, display name); slugs are unique ignoring
  case, none a Windows reserved name, and frozen from PR 3 on. `DeliveryRefused` lives in
  `delivery/errors.py`.
- R20 (PR 3): the folder key includes the delivery hash (S1, step 7). The 2A plan lets a run hold
  several deliveries, none replaced; without the hash a resumed run's second delivery would have
  been refused. Which delivery of a run the library shows is the latest by admission `seq` (PR 11).
- R21 (PR 8a): `read_cell` reuses `read_basis`'s item grammar. The predecessor's cell grammar
  (`credit_os_chips.py`: page markers, brackets, trailing register codes, aliases) is not carried:
  it reads a format step 3A refuses. Such a form in a cell stays a text item, never a source.
- R22 (PR 3): display names are the predecessor's `MODULE_NAMES` at `8e3954a`, character for
  character. The web fixture's names differ for CP-1A, CP-1 and CP-2E and it holds two codes that
  do not exist; it is sample data and follows in slice contract 3.
- R23 (PR 5): the wording file's entries for Home, History, Changes and Overview as the 3B
  controller proposed (W0 to W12): digits, not number words; "latest report"; history text from
  counts and state words only; a card note only for a newer run in progress; no state word for a
  stopped run with unknown spend, a charge above its hold or an operator stop, nor for
  `failed`/`provider_raised`. R23a: the history `empty` sentence adds the next action ("Start a new
  run to write the first report."). Later PRs add their own entries. Every sentence is one JSON
  entry the owner can change; PR 5's body lists them.

## Not verified

- No test, gate, reader or mutation run was executed. Nothing was run on Windows.
- Legacy was not read for this draft. The cell-citation grammar, the events table's columns, the
  fixed chart headers, `handoff_metrics`' column names and the replace retry are known only from
  the first inventory; each brief quotes the predecessor before its key is written.
- Unmerged branches were not read (2A PRs 3a to 5b, 1B PR 7 on, all of 3A). The shapes of
  `ForecastResult`, `History`, attempts, calls, the receipt and the admitted list are inferred
  from the plans on main. Which 3A PR records a source's read state and a module's not-run reason
  is inferred from its PR table.
- The public search read descriptions only. A thin search does not prove nothing better exists.
- That an ASCII-only file equals the fixture writer's output after `JSON.parse` for every input;
  that Chrome and Edge load a 16 MiB `data.js` from `file://` in acceptable time.
- That `os.replace` over an open `data.js` behaves as S9 assumes on the work PC, and what an
  antivirus scan does to the staging folder.
- That a hand-typed whole-library key (PR 14) fits a reviewable size; that the lead-label reader
  can tell a bold lead from other bold text in every committed handoff.
- Whether 3A ever admits an earlier-format document; the mapping refuses one.
- Whether 3A's budget gives a cost total per module, which `record.calls` needs.
- The admission event and its `seq` order are 2A's answers, not read in code. Slice contract 3 is
  not built; its four parts are as the coordinator stated them.
- Whether a megabyte is 1,000,000 or 1,048,576 bytes (PR 1b's brief states it); the source of
  the page count the mock shows beside a size; that the build ships `wording.json` in the package.
- The line split is an estimate. The cost column of D1 to D24 is an estimate made when the plan
  was drafted. The costs in R1 to R16 are the coordinator's estimates.
