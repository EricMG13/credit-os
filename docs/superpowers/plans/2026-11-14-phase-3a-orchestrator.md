# Step 3A: the orchestrator

Date: 2026-11-14. Coordinator: the back-end coordinator session; drafted by an architect agent
from the pre-flight inventory and the coordinator's rulings (`3a-orchestrator/` in the shared
notes folder), under decision 0006. This file is the plan and the sub-session's brief. Written
against `origin/main` `fe44101c` and legacy `legacy/main` `9d040f8` (`git show
legacy/main:<path>`; never check it out, never change it).

**Goal:** `src/credit_os/orchestrator/` runs one issuer's modules in dependency order through a
`Model` it is given: it pins and pages the sources, offers each module its tools, checks each
written handoff, records every call and charge in the store before and after it is sent, holds
the run under its cap, and resumes a run that stopped. It parses no Markdown and renders nothing.

**Ends in:** a sequence of pull requests against `main`, each within 800 changed lines with its
tests, each passing both review steps, opened one at a time. One that would pass the cap is
split and given a letter, never trimmed of tests.

**This is sensitive code** (money: holds, the cap, unknown spend; ordering: the module loop
against the store's one writer, resume; security: text bounds, paths, tool inputs). The section
"Sensitive code" names the second reviewer and the mutation rule for each task.

**No paid run.** `orchestrator/` takes a `Model` and constructs none. No test constructs a live
adapter, opens a socket or reads a provider key. A `live` marker stays outside the gates
(`tools/gates.py` runs `-m "not live and not browser"`). A paid run is the owner's own action.

## Files this step may touch

`src/credit_os/orchestrator/**`, `tests/orchestrator/**` (test modules named
`test_orchestrator_<topic>.py`: `tests/` has no packages, so a base name must be unique). By
named PR only, and only once the owning step's session has finished or the coordinator has
ordered it: `src/credit_os/store/**` and `tests/store/**` (PR 3); `src/credit_os/checks/**` and
`tests/checks/**` (PRs 10a to 10d); `src/credit_os/provider/canned.py` and its tests (PR 6a,
ruling C5, after 1C's PR 3-2 merges). Nothing else: step 3B runs beside this one. Not
`pyproject.toml` (standard library and pydantic only; no new dependency), `VERIFICATION.md`, a
decision record, `docs/legacy/ports.md` or this plan; those are the coordinator's (PR 0).

**Layer rule.** `orchestrator` imports `sources`, `handoff`, `model`, `provider`, `store` and
`checks` only, never `delivery` or `signal` (`credit_os.LAYERS`, `tests/test_layering.py`).
Handoff Markdown is parsed by `handoff.document.parse` and nowhere here. From `provider` it
imports `types` and `redact` only; a test reads the syntax tree and fails on any other import.

## Pre-flight (coordinator)

Read on `origin/main` at `fe44101c`. Since the inventory (`d32b08ad`) one interface moved: 2A
PR 1e merged (`store/db.py`).

- **`provider`**: `types.Model` (`config_id`, `complete(request, *, exchange_id, call_index)`,
  `close()`), `Request`, `Message`, `ToolSpec`, `ToolCall` (with `bad_arguments`), `Turn`,
  `Usage`, `Reply` (four kinds; `billed_usd` a `Decimal` or `None`), `Compaction`.
  `canned.canned_model(config_id, recording)` gives a `CannedModel`; it answers by exchange id
  and call index, ignores the request, and its `close()` returns `()`. `redact.Redactor` has
  `text`, `bytes_`, `from_environ`; `home_paths` is a function. A charge has up to 39 digits
  (`events._MAX_NANO`).
- **`store`**: `db.open_store`, `open_reader`, `Store`, `StoreReader`; `MIGRATIONS` is empty and
  `Store` has no public write method. `txn.write_transaction`, `migrate`. `errors`: `StoreError`
  with `StoreRefused`, `StoreBusy`, `StoreConflict`, `StoreCorrupt`, `StoreUnusable`. `codec`:
  money, time and detail text. `location.prepare`, `locate`.
- **`checks`**: `run.check_handoff(document, context)`; `findings.Finding`, `CheckContext`,
  `CHECKS` (a closed tuple of 32 ids; `Finding` refuses any other id), `ordered`. No figure or
  confidence module is on main.
- **`sources`**: `pin_folder`, `PinnedFolder`, `SourcePin`, `read_pinned`, `read_capped`,
  `source_path`, `MAX_BYTES` (50 MiB), `text_pages`, `csv_pages`, `Page`, `SourcePages`, the
  five error classes, `errors.shown_name`. `html.py` holds decoding and the line writer only.
- **`model`**: `value.parse_operand`, `Value`, `Missing`, `MissingCode`, `amount_text`;
  `arithmetic.total`, `difference`, `product`, `ratio`. A `Value` holds at most 38 digits.
- **`handoff`**: `document.parse`, `HandoffDocument`, `reader.read_reader`, `errors.echo` (80
  characters then U+2026), `errors.HandoffError`, the `data` views.

**Not on main: what 3A needs from each** (a need, not a signature; each PR's brief is written
against the merged code):

| Pending | 3A needs |
| :--- | :--- |
| 2A PRs 2a to 2c | Create a run with its request bytes, cap, config id and pins; claim it; start and end it with a reason; append an event |
| 2A PRs 3a to 3c | Open an attempt with request bytes; open a call before it is sent and close it with the reply and its compactions; record a reply on an attempt; one verdict with its issues; fail an attempt, one with a call left open included; read every charge line |
| 2A PR 4a | The resume read |
| 2A PR 5a | Migration 3 merged, so 3A's migration takes the next number and no merged one is edited |
| 1C PR 2h | The redactor with known paths and `message()` (decision 0012), for stored diagnostics |
| 1C PRs 3, 3b, 4 | Not built on. 3A needs three facts: whether one exchange id is one conversation kept across calls; the literal ids of driver-made compactions; the configuration's effort value and whether the output cap reaches the SDK |
| 1D PRs 2b-2 to 5 | `read_pages(folder, pin)` for every kind (HTML, xlsx, docx, PDF); a way to stop a reader at a deadline (C2); the charset-name bound (a Low for 1D) |
| 2B PRs 4a to 6 | The figure reader (`lost_values`); the single earlier-format helper (D19); the confidence outcome and which modules are scored |
| 1B PR 7; 2B part 2 | The forecast check (PR 10d); CP-1's figure check |

No library documentation is needed: 3A calls the standard library, pydantic as already used, and
this repository's layers. The price page for PR 2b is fetched by the coordinator (D8).

## Prior art

- Owner's repositories: the search is the inventory's section 6 plus the predecessor. Reused
  from main: `model/arithmetic.py` (calculate), `provider/canned.py` (test model),
  `checks/run.py`, `sources/walk.py`, `store/codec.py`, `provider/redact.py`. Signal's
  scheduling cannot be imported (decision 0009). Decision: adapt the predecessor's rules onto
  these layers; build the loop, budget and plan new.
- Public GitHub: **not searched in this draft**. The coordinator runs it with generic terms
  before PR 1's brief and records queries, findings and the decision here.

## Legacy: what happens to each part

| Legacy | Ruling | Reason |
| :--- | :--- | :--- |
| `registry.py` to line 170 (`modules`, `canonical`, `dependencies`, `edge_rule`, `plan`) | Ported | As a Python table (D1); catalogue order within each ready set |
| `registry.py` from `StepChain`; `model/loop.py` | Left behind | The structured runtime; the live path used three redaction helpers only |
| `model/handoff.py` `HandoffExecutor` | Changed | Calls are store rows written before the send; one attempt per write (D4); no catch-all round `complete` (D9) |
| `ModuleTools` list, read, search | Ported | Page numbers differ (D17) |
| `calculate` | Changed | The kernel's operand grammar (D11) |
| `write_handoff`, `edit_handoff` | Changed | Retry reason bounded and sent as data (D5); `accepted` from earlier modules only (D18). An edit that changes the draft is a write, as before |
| `score_governance`, `business_context.py` | Left behind | D23 |
| `web_*`, lookup, `strip_citation_markers`, `flag_search_queries` | Left behind | Decision 0008; hosted search |
| `model/record.py` | Left behind | The 2A tables replace `calls.jsonl`; recordings here are synthetic |
| `model/budget.py` | Changed | No marker files: state is the store's charge lines; an open call makes the total unknown (D7); no `retry_of` |
| `model/pricing.py`, Copilot rows | Changed | One row for `gpt-6-sol` from published pricing (D8); other providers left behind |
| `owners/cpos.py` `run_handoffs`, `HandoffPlan`, `request_fingerprint` | Changed | Sequential over the store; the run's request bytes and their hash replace the manifest |
| `cpos.py` `run_comparison`; `navigation`, `verify_navigation`; `replay_handoffs` | Not here | 5A; 3B or left behind; a replay is a run on a `CannedModel` |
| `cpos_launch.py` `prepare`, `pathway_modules`, `refuse_deactivated`, `upstream_scope_note`, `without_for` | Ported | PRs 1, 9b and 11 |
| `cpos_launch.checker`: as-of date, hashes, issuer; `chart_issues` and the owner tables | Ported into `checks/` | D20, D21 (PRs 10a, 10b) |
| `prose_checks.lost_values` | Ported into `checks/` | D22, with its fail-open (PR 10c) |
| `cpos_launch` `_forecast_issues`; CP-8 hold; `method_text`; `main` | Not here | After 1B PR 7; 5A; phase 6; 4X |
| `context.py`, `run_expectations.py` | Ported, the minimum | D24 (PRs 9a, 9c) |
| `run_events.stop_reason` (deferred by 2A) | Changed | The end-reason vocabulary (G3) |

**Lines for `docs/legacy/ports.md`** (each changes an outcome; the coordinator writes them):
not offered: CP-L10, `short_snapshot`, CP-MEMO, CP-OS, and CP-8 until 5A (D2); CP-DR has no
lookup (0008); calculate refuses exponent forms and anything outside the kernel grammar (D11);
page numbers differ and a read is up to about 96,000 characters (D17); the retry reason is the
first 20 refusals as data plus a count (D5); no `score_governance` (D23); one configuration, no
high effort (D25); a call left open makes spend unknown and the run waits for the owner,
as the predecessor did (D7, G7); a started module is rerun on resume, where the
predecessor refused it (G4); text and csv over 16 MiB, a run over 200 files or 400 MiB, and a
source past 120 s are refused (D13, D14, D16); sources are paged once per run, not per module
(D15); an earlier-format document gets one refusal (D19); a source message shows the name, no
path (D12); an error out of `complete` is not turned into an unknown charge (D9); the third
refusal ends the module, not the run (D4, G1). The two lines that rest on G1 and G4 are written
only once those are ruled.

## Decisions

D1 to D26 apply rulings 1 to 26 of `rulings.md`, number for number; D27 to D30 apply its closing
paragraph. Each is at least one test, named after it. None is reopened here.

| # | Decision |
| :--- | :--- |
| D1 | The module catalogue is a Python table in `orchestrator/`: module, kind, scored, required registers, edges. Data modules: CP-0, CP-PARSE, CP-1, CP-1C (in the predecessor's list CP-PARSE is CP-0's alias, not a module of its own). Phase 6 replaces the table's source, not its shape |
| D2 | Not offered: CP-L10, `short_snapshot`, CP-MEMO, CP-OS. CP-DR runs without lookup. CP-8 is 5A's |
| D3 | Modules run one at a time. A bounded fan-out is a later step with its own plan |
| D4 | A store attempt is one `write_handoff`: written, checked, accepted or refused. At most 3 writes per module; the third refusal ends the module |
| D5 | The retry reason carries each refusal's `quoted` and `reason` as escaped data fields, never inside prose or quotation marks. The first 20 refusals, then a count of the rest |
| D6 | Unknown spend makes the run's total unknown, never zero, and the run stops: a `None` charge on a sent request, or a compaction that is unfinished, failed or has no charge. The rule reads a compaction's state and charge, never its id, so the driver's own ids (`driver:close-unread` and the like, 1C) need no list here. A superseded compaction is dropped |
| D7 | A call a crash left open makes the run's spend unknown (D6): one hold is not shown to bound what the call cost, since a call may make several requests and a compaction's charge is outside `billed_usd`. The run does not resume by itself; it stays stopped until the owner settles the call. This is the predecessor's behaviour, so it needs no decision record. Decision 0006 ruling 6 (resume) holds for a run that stopped cleanly |
| D8 | The price row comes from the provider's published pricing, into a decision record, when PR 2b (this plan's cut of PR 2) is briefed; never from the predecessor. The hold is a store column by migration. No price shown for `gpt-6-sol`: PR 2b stops and the owner is asked |
| D9 | `StoreUnusable` always ends the run: never retried, never swallowed, never followed by an end write. Every store call sits outside any catch-all. An exception out of `complete` is not caught into a value either: the run ends as G3 says. The one catch-all in 3A is D22's |
| D10 | Handoff text echoed back is cut by `handoff.errors.echo`. Tool error text is capped at 300 characters. A shown surface carries a failure class and a fixed sentence only (decision 0012 item 7) |
| D11 | Calculate takes 1 to 128 operands, each read by `parse_operand`; an exponent form is a tool error |
| D12 | A source message shows `shown_name` only; no absolute path is stored or shown. Notes are kept |
| D13 | Text and csv sources are capped at 16 MiB each; other kinds keep 50 MiB |
| D14 | Each source has a 120 s deadline on an injected clock. One that passes it is refused with a reason and shown as a gap, never skipped silently. No sleep and no thread in tests |
| D15 | One source is paged at a time; text is kept, not exception objects. 3A has no fetch |
| D16 | A run takes at most 200 files and 400 MiB; over either it is refused at launch with the count, and it is never a run: nothing is stored (ruled 2026-11-14) |
| D17 | Page numbers differ from the predecessor's; a recording adapted from it says so |
| D18 | `accepted` holds earlier modules only, never the module's own document, at the first check and on resume |
| D19 | An earlier-format document gets `structure.format` only, by 2B's single helper (2B PR 6) |
| D20 | Required: the sha256 of each supplied handoff and of at least one source |
| D21 | As-of date, issuer named, owner and chart tables are ported into `checks/` as 3A PRs. The forecast check follows 1B PR 7 |
| D22 | `lost_values` is ported from the pin plus the Pending commits; `7e5a1160` is read at briefing and included or named as left out. Its fail-open is documented and logged |
| D23 | The `score_governance` tool is not ported |
| D24 | The context schema and readiness are ported, the minimum `prepare` needs |
| D25 | One configuration, `copilot-sol-medium`, for every module. 32,000 output tokens is recorded as configuration |
| D26 | Tests use `CannedModel` and synthetic recordings; no live adapter in a test; `live` is outside the gates |
| D27 | A finding's `reason` is data (2B PR 5, I-3) |
| D28 | A blocked module with 14 confidence rows is scored; an earlier-format document never is (2B PR 6) |
| D29 | `StoreUnusable` covers transient states too (2A I2) |
| D30 | A returned `Store` can sit on a read-only connection; its first write is `StoreUnusable` (2A I1) |

**Rules that follow** (each a test):

- Missing is never zero. A total is a `Decimal`, or unknown with the lines that made it so. A
  run with no charge line totals `0`, a value. A `not_sent` call spent nothing.
- The budget sums exactly, in its own decimal context with `Inexact` trapped and room for the
  store's 64-digit money text. It does not go through `model.Value` (38 digits; a charge has 39).
- The cap check is `spent + next hold <= cap`, before every call. Equal passes. A call left open
  makes spend unknown first (D7), so no open hold is ever summed.
- The module order is the plan's and nothing else's: the same selection gives the same order.
- No path is built from model text. A tool names a source by a pin's exact name; a file is
  reached only through `sources`, by pin. `orchestrator/` deletes no file.
- A search is a plain substring search; no pattern from the model is compiled.
- A tool error is one line. `Finding.message` is never sent to a model (D5).
- D22's fail-open wraps the comparison alone and holds no store call. It catches `Exception`,
  logs it, and an event outside the catch records the error's class name. The verdict stands.
- An amount, currency, unit, period or source identity is passed as written; nothing is rounded.

## Where a ruling meets the code on main

Stated for the coordinator; each is ruled in "Rulings on C1 to C8 and G1 to G8" below.

| # | Ruling | What main has | PR |
| :--- | :--- | :--- | :--- |
| C1 | D12: no absolute path stored; notes kept | `sources/files.py` puts the absolute path in `read_capped` and `source_path` messages and in the close-failure note; `StoreError`'s docstring says a source error's text, path and notes are stored whole. A note kept as written stores the path | 7a |
| C2 | D14: a 120 s deadline, no thread | `text_pages`, `csv_pages` and `read_pinned` take no clock and return only when done. 3A can time a reader after it returns; it cannot stop one | 7b |
| C3 | D16: refused at launch with the count | `pin_folder` has no bound and reads and hashes every file before it returns, so the count comes after the whole read. The 1D fix as worded cannot work as written: `html._ACCEPTED` is keyed by `codecs.lookup(...).name` (`cp1252`, `iso8859-1`), so a declared `windows-1252` or `ISO-8859-1` is known only after the lookup | 7a; 1D |
| C4 | D20 to D22: new checks in `checks/` | `CHECKS` is closed at 32 and pinned by a test; `CheckContext` has no as-of date, issuer name, earlier drafts or hash-required field; `sources.check_sha256` checks a hash only where one is written (2B D10) | 10a to 10c |
| C5 | D26: `CannedModel` only | `CannedModel.close()` always returns `()`, so D6's close-time rows cannot be reached through it; `complete` ignores the request, so a recording cannot show what 3A sent. Both need `CannedModel` extended (ruling C5) | 6a |
| C6 | D4: an attempt is one write | `Model.complete` names a call by exchange id and call index; 2A's plan numbers calls from 0 inside each attempt. One conversation spans up to three attempts, so the two indexes differ or the conversation restarts | 6a |
| C7 | D7 as first worded: "without spending past the cap" | `Reply`'s docstring: a call may make several model requests, and a compaction's charge is never in `billed_usd`. One hold is not shown to bound what an open call cost | 8 |
| C8 | D6 as first worded named `driver:release-unread` | The id is nowhere on main. `driver:close-unread` is in the 1C plan only; the driver is not merged | 2a |

## Points the rulings leave open

The plan needs each to write a key. A working assumption is given; the coordinator rules before
the PR named is briefed. Each is ruled in the next section.

| # | Point | Working assumption | PR |
| :--- | :--- | :--- | :--- |
| G1 | Does the run go on after a module ends unaccepted? The predecessor stopped the run | It goes on. A module whose required producer has no accepted handoff is not run; with only an optional one missing it runs restricted (`edge_rule`) | 7c |
| G2 | Turn and nudge bounds | 32 turns per module (the launcher's value; the loop's default was 24) and 2 nudges | 6b |
| G3 | The end-reason set and which status each takes | Capped ends as `stopped`. The set starts from the predecessor's six classes; the status of an unknown-spend or provider stop is not assumed | 3, 7c |
| G4 | Resume of a module whose last attempt is open, failed or rejected | The open attempt is failed as interrupted; the module is rerun as a new conversation; attempts already used count toward 3 | 8 |
| G5 | A known charge above its hold. The predecessor stopped the run | Not assumed | 2a |
| G6 | CP-MODEL is in five presets and is not analytical; no ruling names it | Left out of every pathway here, as `pathway_modules` did | 1 |
| G7 | Can a run whose total is unknown (D6) resume? Decision 0006 ruling 6 promises resume | It cannot: the total stays unknown | 8 |
| G8 | Tool calls and results have no column in 2A's tables | One event per tool call: name, argument and result sizes, the result's SHA-256; never the text | 6b |

## Rulings on C1 to C8 and G1 to G8 (coordinator, 2026-11-14)

| # | Ruling |
| :--- | :--- |
| C1 | What 3A stores or shows of a `SourceError` is built from its fields (its class, `shown_name`, its reason), never from its message. A note is kept only after `Redactor.message` with the source folder among the known paths (decision 0012). The `StoreError` docstring's "stored whole" line changes in 1C PR 2h, as decision 0012 item 8 orders, not in a 3A PR |
| C2 | D14 is measured, not pre-empted: a source whose read took over 120 s on the injected clock is refused after it returns, and shown as a gap. D13's 16 MiB caps bound the read meanwhile (csv about 22 s). A reader that takes a clock and stops itself is a 1D change, listed for a later step |
| C3 | 3A counts files and bytes from a directory listing, without reading a file, before it calls `pin_folder`, and refuses there. In 1D the declared charset name is matched against a literal table of accepted names and aliases before `codecs.lookup`; a name outside the table is refused and never reaches the cache. That goes to 1D as a Low |
| C4 | The new checks are added by 3A's session after 2B PR 6 merges: `CHECKS` grows by the named ids and its pinned test changes with the key; `CheckContext` gains the as-of date, the issuer name and the hash-required flag, each with a default that leaves 2B's keys unchanged; a required hash that is missing is its own check id |
| C5 | One test model: `CannedModel` is extended (in `provider/canned.py`, a 3A PR after 1C's PR 3-2 merges) to record each request it is given and to return recorded compactions from `close()`. No second test model is written |
| C6 | One conversation per module. A call is named to the provider by exchange id and a call index that runs across the module's attempts; the store keeps that index as data beside its own per-attempt ordinal. 2A's PR 3 brief states both columns |
| C7 | Settled by D7 as amended above |
| C8 | Settled by D6 as amended above: the rule reads state and charge, not ids |
| G1 | The run goes on after a module ends unaccepted. A module whose required producer has no accepted handoff is not run and is shown as a gap with that reason; with only an optional producer missing it runs restricted |
| G2 | 32 turns per module and 2 nudges, the values the predecessor ran with |
| G3 | End reasons and status: a run that ended normally has status `finished`, the merged schema's word, with end reason `completed` (clarified 2026-11-14: `completed` is the reason, not the status); a run still `running` whose process has gone is never inferred by a reader: it becomes `stopped` (interrupted) only when the operator takes it over (resume or stop, PR 8), which claims the run again, so an earlier writer's token is fenced and its later writes are refused, and writes that end before anything else; the cap is `stopped` (capped); unknown spend is `stopped` (spend unknown); a charge above its hold is `stopped` (hold exceeded); a provider failure that is not retried is `failed`; an exception out of `complete` is `failed` (provider raised) and leaves its call open, so spend is unknown (D7); a stop asked for by the operator (decision 0006 ruling 5) is `stopped` (operator), taken between calls, never inside one; `StoreUnusable` writes nothing (D9). The set is closed and keyed in PR 3 |
| G4 | An attempt a stop left open is failed as interrupted; the module is rerun as a new conversation; attempts already used count toward the 3 |
| G5 | A known charge above its hold stops the run: the hold arithmetic is then wrong for every later call. The charge is recorded exactly |
| G6 | CP-MODEL is in no pathway here. The forecast is Python's (step 1B) and is run by a later step, not as a module conversation |
| G7 | A run whose total is unknown does not resume by itself (D7). PR 8 delivers both halves: the resume is refused with the reason and the call it names, and a settle action records the charge the owner states for that call (from the provider's own billing), after which the total is known and the resume is judged as any other. The settle write is a store call from 2A PR 5; a charge the owner states is recorded as stated by the owner, distinct from one the provider reported |
| G8 | One event per tool call: its name, the sizes of its argument and result, and the result's SHA-256; never the text |

## Sensitive code

| Area | Tasks | PRs | Besides `mx-precise` |
| :--- | :--- | :--- | :--- |
| Money | Hold, totals, the unknown rule, the cap check, the launch refusal, the price row, the hold column, a crash-left call | 2a, 2b, 3, 6a, 8, 9b | `mx-adversary` |
| Ordering | Store writes round each call, attempts and verdicts, the one writer and its fencing token, `StoreUnusable`, resume | 3, 6a, 6b, 7c, 8 | `mx-invariants` |
| Security | Tool inputs, text bounds, source names and paths, launch caps, text put into instructions | 4a, 4b, 5, 7a, 7b, 11 | `mx-adversary` |
| Figures | Amounts in the context; `lost_values`; table checks that read amounts; the forecast check | 9a, 10b, 10c, 10d | `mx-adversary` |

A task in two areas gets both reviewers. **Mutation testing** is the reviewer's, on the changed
files of every sensitive task: `mutmut` through `uvx`, not added to `pyproject.toml`. A count is
valid only after three checks: the clean tests pass; a forced failing test fails the run; two
known hand-made mutants are killed. It runs with a short per-test timeout and at most 2 child
processes. Survivors are killed or justified in the PR. `mutmut` does not mutate inside a SQL
string: PR 3's statements are hand-mutated and each has a raw-connection test.

## Answer keys (implementers do not edit them or weaken a comparison)

Written by the controller before each task, from invented values and by reading; never by
running the production code or the predecessor. Each key says how its values were worked.

| PR | Key | How its values are produced |
| :--- | :--- | :--- |
| 1 | `tests/orchestrator/expected/plans.json`, `catalogue.json` | By hand from the predecessor's `methodology.json` and presets at `9d040f8`: the order and each module's producers for the seven pathways and chosen subsets; rows for an alias, an unknown module, a module not offered, CP-5's fan-in, and a cycle in a table the test supplies |
| 2a | `orchestrator_budget_key.py` | Invented rates and charges, as decimal strings worked with `fractions.Fraction` and checked with `bc`. Rows: no line (`0`); a `0` charge; `None` on `not_sent` (nothing spent); `None` on `ok`, `sent_usage`, `sent_unknown` (unknown); a failed and an unfinished compaction; a superseded one with and without its successor; a compaction carrying a driver id (the rule ignores ids and reads state and charge); an open call (spend unknown); cap equal and one unit of 1E-11 over; a 39-digit charge |
| 2b | One row in the same key | The `gpt-6-sol` figures copied from the decision record; the hold recomputed with `bc` |
| 3 | `tests/store/store_schema_key.py` (2A's key 1) | The new columns (the hold, the owner-stated marker), the allowed end reasons, and the migration text's SHA-256 by `shasum` |
| 4a | `orchestrator_tools_key.py` | Literal results over `SourcePages` built from literals: list, read (8 pages, a page out of range, an `empty` and an `unreadable` page shown as such), search (20 hits, no match stated, not empty), an unknown tool, `bad_arguments`, a 5,000-character name, `../x` as a source name, a bool for a page number |
| 4b | The same key, calculate rows | By hand and `bc`: the four operations; a null operand is not sourced, never 0; a zero operand is a value; 128 pass, 0 and 129 fail; `1e3`, `+1`, `.5`, `1,000`, 65 characters and 39 digits are tool errors; a zero or negative denominator; a product past 38 digits is a tool error, not a crash |
| 5 | `orchestrator_write_key.py`, `tests/orchestrator/fixtures/` | Synthetic handoffs marked SYNTHETIC FIXTURE. The exact retry-reason bytes for 1, 20, 21 and 5,000 refusals built from literal `Finding`s, one `quoted` holding a quotation mark and an instruction-like sentence; an unparseable draft; edit rows (no draft, old text absent or twice, no change); writes 1 to 3 and a fourth refused; a limitation that repeats only the module's own earlier text is not refused |
| 6a, 6b | `tests/orchestrator/recordings/*.jsonl`, `orchestrator_loop_key.py` | Recordings written by hand. The expected store rows and events as literals, in order, for: accepted at the first write; refused then accepted; three refusals; the turn bound; nudges; `not_sent`; `sent_unknown`; `ok` with no charge; the cap reached mid-module; a compaction on a reply; `StoreUnusable` at each write point |
| 7a | `orchestrator_ingest_key.py` | Pins with invented sizes: 200 and 201 files; 400 MiB and one byte more; text at 16 MiB and one byte more; a 50 MiB PDF. `SourceError`s whose message and note hold an absolute path, with the exact shown text |
| 7b, 7c | The same key; `orchestrator_run_key.py` | A folder built in `tmp_path` from literal bytes and a fake clock (120 s passes, more is refused). A literal for a scripted three-module run: events, module outcomes, statuses, the end reason, a blocked and a restricted dependant |
| 8 | `orchestrator_resume_key.py` | A case table by hand: each last-attempt state to kept, judged, rerun or refused; a crash-left call (refused, spend unknown) and the same call after it is settled; a changed source; a changed request; a fenced writer |
| 9a to 9c | `orchestrator_context_key.py` | Synthetic `context.json` cases adapted from the predecessor's tests: an amount of `"0"`, an absent one and an empty one kept apart; each refusal's text. Request bytes with their SHA-256 by `shasum`; a cap below, equal to and above the first hold |
| 10a to 10d | `tests/checks/expected/*.json` (2B's keys, extended) | The predecessor's test cases set in synthetic handoffs; the expected check and quoted text from its test unless a decision changes it; `fixtures.json` re-read by hand |
| 11 | `orchestrator_instructions_key.py` | The literal instruction bytes for a synthetic method and two synthetic upstream handoffs, with their SHA-256 by `shasum` |

Property tests (`hypothesis`): a total is independent of line order and equals the `Fraction`
sum; one unknown line makes it unknown wherever it sits; a plan is a topological order of any
selection and is stable; any tool input gives a result within its bounds, an error one line of
at most 300 characters; any findings give at most 20 records and a count, and the records read
back to the same data.

## PR sequence

"Now" means the PR can start on merged code only. A PR also waits for the C or G rows that name it.

| PR | Delivers | Needs | Affected tests | Start |
| :--- | :--- | :--- | :--- | :--- |
| 0 | Docs, the coordinator's: this plan and the ports lines | Nothing | None (batched `mx-feature` review) | Now |
| 1 | Catalogue and plan: modules, aliases, kinds, edges, pathways; `dependencies`, `edge_rule`, `plan` | Merged code. G6 | `test_orchestrator_catalogue.py`, `test_layering.py` | Now |
| 2a | Budget: charge lines as 3A's own type, exact totals, the unknown rule, the superseded drop, the cap check, the launch refusal; the price row passed in as data | Merged code. C8, G5 | `test_orchestrator_budget.py` | Now |
| 2b | The `gpt-6-sol` price row and its decision record | 2a; the pricing fetch (D8) | `test_orchestrator_budget.py` | Waits |
| 3 | Store migration: the hold on a call, written when the call is opened; a marker on a charge the owner stated (G7), distinct from one the provider reported; the end-reason set | 2A PRs 3c and 5a (pending); 2A's session done. G3 | `tests/store/` | Waits |
| 4a | Tool dispatch and bounds; `list_sources`, `read_pages` (8 pages), `search_source` (20 hits), over `SourcePages` given in | Merged code | `test_orchestrator_tools.py` | Now |
| 4b | `calculate` | Merged code | `test_orchestrator_calculate.py` | Now |
| 5 | `write_handoff`, `edit_handoff`, the 3-write bound, `CheckContext` built without the module's own document, the retry reason | Merged code. Its rows hold no figure in a passage and no earlier-format document, so 2B PRs 4a to 6 add no finding to them | `test_orchestrator_write.py` | Now |
| 6a | `CannedModel` records each request and returns recorded compactions from `close()` (C5). One call: the cap check, the call opened with its hold before the send, the reply and compactions closed in, the stop on a reply that is not ok or has no charge | 2A PRs 2a to 3c, 1C PR 3-2 (pending); 3A 2a, 3. C5, C6 | `test_orchestrator_call.py` | Waits |
| 6b | The module loop: turns, tools, nudges, one attempt per write, verdicts, the module's outcome | 6a, 4a, 4b, 5. G2, G8 | `test_orchestrator_loop.py` | Waits |
| 7a | Launch caps over a `PinnedFolder`; the shown and stored form of a `SourceError` | 1C PR 2h (`Redactor.message`, pending). C1, C3 | `test_orchestrator_ingest.py` | Waits |
| 7b | Ingest: one source paged at a time, every kind, the deadline, refusals as explicit gaps | 1D PR 5 and the readers before it (pending). C2 | `test_orchestrator_ingest.py` | Waits |
| 7c | The run: create and claim, the sequential plan, events, blocked and restricted modules, end reasons, `Model.close()` | 6b, 7b, 9b, 11 (PR 11 is numbered later but comes first); 2A PRs 2a to 3c (pending). G1, G3 | `test_orchestrator_run.py` | Waits |
| 8 | Resume from the resume read: kept, judged, rerun, refused; the original cap; a crash-left call refused with its reason; the settle action (G7) | 7c; 2A PR 4a and 5 (the settle write), 2B PR 6 (pending). C7, G4, G7 | `test_orchestrator_resume.py` | Waits |
| 9a | Context schema: `context/1` to a typed context, amounts, refusals | Merged code | `test_orchestrator_context.py` | Now |
| 9b | Launch admission: the request bytes, modules not offered refused, the cap against the first hold | 1, 2a, 9a (2b for the real row) | `test_orchestrator_prepare.py` | After 1, 2a, 9a |
| 9c | Readiness, the minimum | 9a, 7b | `test_orchestrator_readiness.py` | Waits |
| 10a | `checks/`: as-of date, issuer named, required hashes | 2B PR 6 (pending). C4 | `tests/checks/` | Waits |
| 10b | `checks/`: owner and chart tables (split as needed) | 10a | `tests/checks/` | Waits |
| 10c | `checks/`: `lost_values`; its call and fail-open in the write path | 2B PR 5 (pending); 10a, 5 | `tests/checks/`, `test_orchestrator_write.py` | Waits |
| 10d | `checks/`: the forecast check | 1B PR 7 (pending) | `tests/checks/` | Waits |
| 11 | Instruction assembly: system rules, the method text given as bytes, producers' handoffs inlined, tool specs, the first request | 1, 4a, 5 | `test_orchestrator_instructions.py` | After 1, 4a, 5 |

Can start now: 0, 1, 2a, 4a, 4b, 5, 9a. Then 9b and 11 on 3A's own PRs. Everything else waits
on a named pending PR. The roadmap says a phase starts when its dependencies are merged; starting
these early is the coordinator's call and is recorded in `VERIFICATION.md` by the coordinator.

## How it runs

Global rules §1, §3 and §7. The sub-session is the controller and writes no code. `mx-scaffold`
takes mechanical work with a complete spec; `mx-feature` takes everything else and implements
test first. `mx-precise` reviews each task, with the second reviewer named under "Sensitive
code". At most two Sonnet fix rounds per task; a third only as a plan written by `mx-autonomous`
and executed by a fresh `mx-feature`; no fourth without the owner. Reviewers save each probe as a
script; the fixer runs it and reports its exit code.

Every brief and review prompt carries:

- No stub or fake value standing in for real behaviour. No reader, price or store call is faked
  in source; a kind with no reader on main is not given a placeholder.
- No catch-all that hides a failure. The only one is D22's, documented and logged.
- The answer key rule: the controller writes the key first; the implementer does not edit it or
  weaken a comparison. Missing stays distinct from zero; identities and units stay exact.
- The OS-limit rule: no probe, test or script exhausts threads, processes, file descriptors,
  memory or disk. Loops are capped at 1,000. A failure is simulated (the call is patched to
  raise), never produced. A large file is stated by a pin's size, not written to disk.
- No delete on a path built from a variable. Tests write under `tmp_path` only.
- No `assert` in source. No provider, no network, no key. A report ending `Not verified:`.

Per task the affected tests named above run first. Before a task is done both project gates exit
0: `uv run --locked python tools/gates.py` (run `npm ci` in `web/` once first) and
`npm --prefix web run gates`. Before each PR is ready: `/sweep refactoring discover
changed-update`, then the whole-branch review (`mx-architect` running `adversarial-reviewer`,
fresh agent, §7 severities); verdicts and report paths in the PR body; CI green on Windows and
Ubuntu, both read before a review is dispatched. PR 0 takes the batched `mx-feature` review only.

## Done when

Each PR is open with CI green and its reviews passed, and the sub-session has sent the
coordinator one message per PR: the PR number, verdicts, report paths, gate exit codes, the
mutation result with its three validity checks, ledger lines (`3A-<pr> task=<n> agent=<name>
fix-rounds=<n> gates-first-pass=<y|n|n/a>`), parked Low findings and a `Not verified:` line. The
coordinator reads the diff and merges. The sub-session does not merge or edit shared records.

## Open items for the owner

- D3: decision 0006 ruling 9 allowed several modules at once; 3A builds one at a time.
- Scope: the roadmap's row for 3A names `orchestrator/` only. By named PR this plan also changes
  `store/` (PR 3), `checks/` (PRs 10a to 10d) and `provider/canned.py` (PR 6a).
- A stop asked for by the operator takes effect between calls, never inside one (G3).
- D23: `score_governance` was offered to every module in the predecessor; it is not ported.
- D25: the predecessor used high effort for some modules; here one configuration serves all.
- D8, if it arises: no published price can be shown for `gpt-6-sol`.
- D7: a run with a call a crash left open, or with unknown spend, does not resume by itself; the
  owner settles it by PR 8's settle action (G7). Decision 0006 ruling 6 promised resume without that exception.
- A paid run stays the owner's separate action, under a ruling that names its cap.

## Not verified

- No public search was run for this draft; the owner's repositories were searched only as far as
  the inventory's section 6 and the predecessor. An empty search would not prove nothing exists.
- No test suite, gate or mutation run was executed. Nothing was run on Windows.
- Unmerged branches (2A PRs 2a to 5b, 1C PRs 2h to 4, 1D PRs 2b-2 to 5, 2B PRs 4a to 6, 1B PR 7)
  were not read. Every need in the pending table is inferred from their plans on main.
- The legacy was read at the local `legacy/main` ref without a new fetch, and only in part:
  `methodology.json`, the presets, and passages of `handoff.py`, `budget.py`, `cpos_launch.py`
  and `run_events.py`. Nothing in it was run. The inventory's line counts were not recounted.
- Which modules are scored, each module's required registers and the names in `other_sources`
  were not traced; PR 1's and PR 5's keys take them from the predecessor by reading.
- The price, context window and effort value of `gpt-6-sol` under `copilot-sol-medium`. The
  USD 7.17 hold is the predecessor's figure for another model, recomputed here and used nowhere.
- The line split is an estimate from the predecessor's size; several PRs may need a letter.
- Peak memory of the text kept for a run of 200 files, and how long paging 400 MiB takes.
- Whether the working assumptions under G hold; whether `mutmut`'s options give the stated
  timeout and child limit in the version used.
