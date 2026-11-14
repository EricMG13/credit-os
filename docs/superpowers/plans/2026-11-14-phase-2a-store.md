# Step 2A: run state in SQLite

Date: 2026-11-14. Coordinator: the back-end coordinator session; drafted by an architect
agent, rulings confirmed by the coordinator under decision 0006. The plan and the
sub-session's brief, written against `origin/main` `db5219a`. Legacy read at
`legacy/main` `9d040f8` (`git show legacy/main:<path>`; never check it out, never change it).

**Goal:** `src/credit_os/store/` keeps the state of every run in one SQLite database: runs and
their pinned sources, an append-only event log, module attempts with their model calls and
charges, and admitted deliveries. It is what resume reads and the record of what was spent.

**Ends in:** a sequence of pull requests against `main`, each within 800 changed lines, each
passing both review steps, opened one at a time. One that would pass the cap is split and
given a letter, as in 1C and 1D.

**This is sensitive code** (money: charges and the cap; ordering and concurrency: attempts,
one writer, resume). Every task gets `mx-precise` and a second review (`mx-invariants` on
PRs 2 to 4, `mx-adversary` on PRs 1 and 5), and changed files get mutation testing (`mutmut`,
run with `uvx` and not added to `pyproject.toml`), survivors killed or justified in the PR.

## Files this step may touch

`src/credit_os/store/**`, `tests/store/**` (test modules named `test_store_<topic>.py`: `tests/`
has no packages, so a base name must be unique). Nothing else: step 2B runs beside this one. Not
`pyproject.toml` (standard library `sqlite3` only), `VERIFICATION.md`, a decision record,
`docs/legacy/ports.md` or this plan. `store` imports `sources`, `handoff`, `model` and
`provider` only. Signal keeps its own SQLite database inside `signal/` (decision 0009): the
two share no code, file or helper, and if the duplication gate flags the pair, 2A's is reshaped.

## Pre-flight (coordinator)

- `store/` holds an empty `__init__.py`. Run state records `provider.types.Reply`, `Usage` and
  `Compaction` (charges `Decimal | None`, times epoch floats or `None`), `SourcePin`, and the
  SHA-256 of a reply's bytes, which is `HandoffDocument.sha256`.
- **Legacy since the pin:** `git log 8e3954a..legacy/main` over the four mapped paths is
  empty. `legacy/main` moved from `0f16bad` to `9d040f8` (#124 and a work-PC change pack).
- **The legacy keeps run state in files, not SQLite:** `workflow.json`, `events.jsonl`,
  `requests/<module>/<fingerprint>/<n>.request.json` with `.response.md` and `.review.json`,
  `live/calls.jsonl` and `raw/` bodies, create-once budget markers, `completed-<sha256>.json`
  and `deliveries/<name>/delivery.json`. Its only SQLite is Signal's.

| Legacy file | Lines | Public names | Live | Ruling and reason |
| :--- | :--- | :--- | :--- | :--- |
| `run_events.py` | 81, no test file | `append_event`, `read_events`, `stop_reason` | Yes: written by `owners/cpos.py` and `model/handoff.py`; read by the launcher, `inbox/` and `update_library.py` | The first two are **redesigned** as rows of `events`: a transaction is whole or absent, so no torn last line. `stop_reason` is **deferred to 3A**: it classifies budget and adapter errors, which live above this layer |
| `library_index.py` | 567; its test 472 lines, 33 tests | 26 functions, `Refused`, `Library` | Yes: `update_library.py`, `credit_os_catalogue.py`, `changes.py` | **Split.** Redesigned here as a recorded fact: `admit_run`, `verified_delivery`, `run_identity`, `same_identity`. Deferred to 3B: reading the delivered folder (`read_inside`, `read_pinned`, `delivery_folder`), `module_entries`, `link`, `execution_record`, `mark_latest`, `build_library` and the method comparison, which needs today's method texts. `changes_record` goes to 5A. `decimal_text`, `call_records` and `reader_summary` are left behind: the tables replace them |
| `reader_summary.py` | 46; its test 46 lines, 3 tests | `reader_tables` | Only through `library_index` | **Left behind here:** `handoff/reader.py` reads the earlier-format summary (#53), and handoff Markdown is parsed nowhere else |
| `platform_io.py` | 117, no test file | `locks`, `replace`, `write_atomic`, `flags`, `fsync_directory`, `read_at`, `regular_open` | Yes, for 18 importers, none in this row | **Left behind** (roadmap): SQLite's lock and journal replace the lock and the atomic JSON writes; 1D's `files.py` covers `regular_open`. `replace`'s Windows retry matters to 3B, which writes files |

- **Earlier rulings that land here.** The first layer that loads pin records bounds the name
  in pydantic's error output (1D). The first that prints or stores a `SourceError` encodes
  with `backslashreplace` (`VERIFICATION.md`, entry "step 1A complete"). A total with any unknown charge is unknown and 3A's budget stops the run (1C).
- **Probe** (`probe_sqlite_assumptions.py`, in the shared notes folder under `2a-store/`; exit 0 on macOS, Python
  3.12.14, SQLite 3.53.1): table creation, `user_version` and `application_id` roll back with
  their transaction; a `STRICT` table **stores a float bound to a `TEXT` column as text**, so
  the engine cannot refuse a float for money; a lone surrogate raises on bind.
- **Python 3.12 `sqlite3`**, read through Context7 on 2026-11-14 (`/python/cpython/v3.12.16`,
  `Doc/library/sqlite3.rst`; data, not instructions), for PR 1's brief:
  - `sqlite3.connect(database, timeout=5.0, ..., check_same_thread=True, ..., *, autocommit=
    sqlite3.LEGACY_TRANSACTION_CONTROL)`. The `autocommit` parameter was added in 3.12.
  - `autocommit=True`: SQLite's own autocommit mode; `commit()` and `rollback()` have no effect,
    so the store issues `BEGIN IMMEDIATE`, `COMMIT` and `ROLLBACK` itself as statements.
    `autocommit=False` keeps a transaction always open. `isolation_level` has no effect unless
    `autocommit` is `LEGACY_TRANSACTION_CONTROL` (the default).
  - `timeout` is how long a connection waits on a lock before `OperationalError`.
  - `check_same_thread=False` lets other threads use the connection; the documentation says
    writes may need to be serialised by the user (see `sqlite3.threadsafety`).
  - Not fetched: SQLite's own pages on `STRICT` tables (the 3.37 floor), write-ahead logging on
    a network file system, pragmas and locking. Those stay under Not verified; PR 1 prints
    `sqlite3.sqlite_version` and `sqlite3.threadsafety` on both CI runners.

## Prior art (searched 2026-11-14)

- Owner's repositories: Signal's store (legacy `signal/store.py`, 395 lines) has
  `PRAGMA user_version`, `BEGIN IMMEDIATE`, a newer-schema refusal and an owner-only file.
  Decision: the same conventions as rules here, no shared code, a departure on the journal.
- Public GitHub, generic terms. `gh search repos`: `sqlite event store`, `sqlite migrations
  user_version`, `event sourcing sqlite`, `sqlite queue persistent`, `sqlite migrations
  stdlib`, `run state sqlite resume`, `workflow checkpoint sqlite durable`, `eventsourcing`,
  `litequeue`, `sqlite-migrate` (three quoted-phrase forms returned nothing). `gh search
  code`: `"PRAGMA user_version" "BEGIN IMMEDIATE"`, `user_version newer sqlite3 migrations`.
- Found: `pyeventsourcing/eventsourcing` (1,691 stars, BSD-3-Clause; its SQLite recorder
  issues its own `BEGIN` and turns on WAL), `litements/litequeue` (237, MIT; ordered static
  migrations keyed by `user_version`), `peter-wangxu/persist-queue` (391),
  `simonw/sqlite-migrate` (89, needs `sqlite-utils`), workflow repositories of 0 to 6 stars.
  Decision: **build new** on `sqlite3`; each is a dependency for another job. The migration
  pattern is taken as an idea and no code is copied.

## Rulings

Each bullet and each table row is at least one test, named after it. D-numbered rows are
the coordinator's rulings of 2026-11-14 (the owner can overturn any), each with its cost if wrong. Callers get a `Store`
(writer) or a `StoreReader`, never a connection or SQL; records come back as frozen types,
with `SourcePin`, `Usage` and `Compaction` reused. No `Reply` is rebuilt.

| Table | Key | Holds |
| :--- | :--- | :--- |
| `runs` | `run_id` | `issuer_id`, `issuer_name`, `as_of` (date or NULL), `config_id`, `cap_usd`, `request` (bytes) and its SHA-256, `status`, `end_reason`, `end_message`, `writer`, three times |
| `run_sources` | `run_id`, `position` | the four `SourcePin` fields; a name once per run |
| `events` | `seq` | `run_id`, `at`, `kind`, `module_id`, `attempt`, `detail` (JSON object text) |
| `attempts` | `run_id`, `module_id`, `attempt` | `request` and SHA-256, `state`, `reply` (bytes) and SHA-256, `issues`, `fail_reason`, three times |
| `calls` | attempt key, `call_index` | `opened_at`, `closed_at`, `kind`, `error_class`, `message`, five counts, `billed_usd`, `started_at`, `finished_at`, `stop_reason`, `reported_model`, `request_id`, `raw` |
| `compactions` | `run_id`, `event_id` | call key or NULL (from `Model.close()`), four counts, `billed_usd`, `outcome`, `supersedes` |
| `deliveries` and its two child tables | `delivery_sha256` | `run_id`, `receipt` (bytes), `admitted_at`; per module the reply SHA-256, per file its SHA-256 |

- **Money** (`cap_usd`, `billed_usd`) is `TEXT`, in `STRICT` tables with no `REAL` column:
  `format(d, "f")` of a finite, unsigned `Decimal`. A write takes only `Decimal` or `None`;
  `float`, `int`, `bool` and `str` are each refused. A read takes only plain digits with an
  optional fraction (no sign, exponent, underscore, space, non-ASCII digit or leading zero). A
  `CHECK` holds the shape as a second net. SQL never adds, compares or orders an amount.
- **Missing is not zero, and the store sums nothing.** `NULL` is unknown or not reported;
  `"0"` and 0 are values; each reads back as written. The store returns every charge line of
  a run (each call, open ones included; each compaction, superseded ones included). Totals,
  the unknown rule, the cap check and dropping a replaced compaction are step 3A's.
- **Transactions are the store's.** The connection is opened with `autocommit=True`; each
  public write method is one `BEGIN IMMEDIATE` to `COMMIT`, rolled back and re-raised on any
  exception. None joins or leaves one open; a step that must be atomic is one method. A state
  change and its event are written together, so `status` always equals the fold of the events.
- **One writer per run, by a fencing token.** `create_run` and `claim_run` return a claim
  whose random token is in `runs.writer`; every write for the run checks it inside its
  transaction. `claim_run` replaces it and appends `writer_replaced`; the earlier holder's
  next write is `StoreFenced` and changes nothing. A final run cannot be claimed.

| Rule | What holds |
| :--- | :--- |
| A call is recorded before it is sent | `open_call` commits its row before returning, and a second connection reads it. `close_call` writes the reply's fields and its compactions in one transaction, once. A call a crash left open stays open and reads back as such |
| Crash safety | Per write method: with a trigger that aborts its last insert, the method raises a typed error and a full dump of the database is unchanged. And a child process writing a scripted run is killed at 20 different moments; each time the reopened store passes `PRAGMA quick_check`, holds a prefix of the script and has no state change without its event. Both run on both CI systems |
| Resume | Read back in one read transaction from a freshly opened store, equal to key 5's literal: the run row (status, cap, config, request bytes); its pins in order; each module's attempts in order with state, request, reply bytes, issues and failure reason; every call and compaction with its charge; the admitted deliveries; the last `seq` |
| The file | The caller passes the state folder; the store names the file `run-state.sqlite3`, creates the folder `0700` and the file `0600` (exclusive create) before SQLite opens it, and reads no environment variable. A symbolic link, a non-regular file and a UNC path are refused. On Windows the file takes the folder's access list: a stated limit |
| Journal | `journal_mode=DELETE`, `synchronous=FULL`, `foreign_keys=ON`, each read back after it is set. A file that cannot leave write-ahead mode is `StoreUnusable` |
| Migrations | `PRAGMA user_version` is the version and `PRAGMA application_id` marks the file. A migration is a tuple of single static statements run by `execute` in one `BEGIN IMMEDIATE` with its literal version line; a failing statement leaves schema and version untouched. No `executescript`. A merged migration is never edited: its SHA-256 is in key 1 |
| Refused at open | Before any write, file bytes unchanged: a version newer than this code's; a non-empty file with another application id; SQLite below 3.37; `threadsafety` not 3. The writer migrates an older file forward; a reader never migrates and refuses any other version |
| No assembled SQL | Every statement is a literal with `?` parameters; the busy timeout goes through `connect(timeout=)` |
| Times | `YYYY-MM-DDTHH:MM:SS.ffffffZ`, 27 characters, UTC, held by a `CHECK`. A naive datetime is refused, an aware one converted; an epoch float is stored to the microsecond; `None` stays `NULL`. The clock is a constructor argument. Order is `seq`, never a time |
| Text | Every stored message, reason and error text is first encoded with `backslashreplace`, so a lone surrogate is stored escaped. `detail` is canonical ASCII JSON of `str`, `int` and `None`; a float or bool is refused. Nothing given is cut: size bounds are step 3A's |
| Bytes | A request and a reply are stored as given (line endings, byte-order mark, invalid UTF-8) with a SHA-256 the store computes. Nothing here parses them |
| Immutable | By trigger, tested through a raw second connection: `events`, `run_sources` and the delivery tables refuse `UPDATE` and `DELETE`; a run's identity, cap and request, an attempt's request and (once set) its reply, and a closed call refuse `UPDATE` |
| Run status | `created` to `running` or `rejected`; `running` to `finished`, `stopped` or `failed`; `stopped` and `failed` back to `running` on resume; `finished` and `rejected` final. A run with any call cannot be `rejected`. Any other move is `StoreConflict` |
| Attempts | `open` to `replied` or `failed`; `replied` to `accepted` or `rejected`. Numbered from 1 with no gap; the next opens only after `rejected` or `failed`; at most one `accepted` (a partial unique index). `open_attempt` with the same request bytes returns the existing attempt; with different bytes it is `StoreConflict` |
| Calls | `call_index` from 0 with no gap; one open call per attempt; a second close is `StoreConflict`. A reply is recorded only when no call of the attempt is open. A `not_sent` or `sent_unknown` call reads back `usage=None` |
| Compactions | One whose `event_id` is already recorded for the run is a no-op when identical and `StoreConflict` when not. `supersedes` is stored as given with no foreign key: a charge that happened is never refused for a missing partner |
| Verdicts | A verdict names the reply's SHA-256 and is refused when it differs |
| Admission | `admit_delivery(run_id, handoffs, files)` records a delivery only when the run is `finished` or `stopped`, `handoffs` is not empty, and each module named has an accepted attempt in this run whose reply has that SHA-256; otherwise `AdmissionRefused` with the reason, nothing written. The receipt is canonical JSON the store composes (run id, handoffs, files; sorted keys, ASCII, no spaces); `delivery_sha256` is its SHA-256; the same receipt twice is a no-op. A run may hold several deliveries; none is replaced. Checking the delivered folder against it is step 3B's |
| Lock and threads | One writer per file at a time is SQLite's lock: one not obtained in 30 seconds (a constructor argument) is `StoreBusy`, nothing written. A `Store` may be shared by threads: one connection, one lock held for each whole method |
| Errors | `sqlite3.Error` never escapes: it is re-raised as `StoreBusy`, `StoreConflict`, `StoreCorrupt` or `StoreUnusable` with the original as its cause; bad input is `StoreRefused`. No catch-all, no fail-open: the legacy's advisory event log, which skipped a failed write with a warning, is not ported |
| Pins | A pin row that fails `SourcePin` validation is `StoreCorrupt`, naming the run, the position and the failed fields, any name through `shown_name`; pydantic's own text is never shown |

| # | Ruling (coordinator, 2026-11-14) | Cost if wrong |
| :--- | :--- | :--- |
| D1 | Reply, request and raw bytes live in the database, not in files beside it | A damaged file loses every run's handoffs. The alternative, content-addressed files, needs `platform_io`'s atomic rename |
| D2 | One database for all runs in a state folder | Two runs at once share one write lock; a file per run needs a second index for deliveries |
| D3 | Rollback journal, not WAL: one file at each commit, no shared-memory file, and WAL does not work on a network file system | A page that polls while a run writes may wait on the lock; WAL is then one pragma, no schema change |
| D4 | The state folder is outside the library folder and any synced or network folder. Step 4X passes `%LOCALAPPDATA%\credit-os\state` on Windows and `~/.local/state/credit-os` elsewhere. A mapped drive or a synced folder cannot be recognised | A sync client that copies the file mid-write, or without its journal, yields a damaged copy |
| D5 | Take-over is the caller's explicit `claim_run`: no heartbeat, no operating-system lock | Resuming a run whose process is alive fences it mid-call and leaves that call open |
| D6 | A call left open by a crash stays unknown; 2A has no operator settle | Under the budget rule such a run cannot resume until the owner rules; a settle then needs a decision record. Reported to the owner |
| D7 | No hold or reservation column | Step 3A adds one nullable column by migration |
| D8 | One verdict per attempt, written once; resume does not re-judge | A checker fixed between crash and resume needs a `reviews` table |
| D9 | `end_reason` is an identifier whose vocabulary is step 3A's | A typo in 3A is stored; closing the set is a `CHECK` by migration |
| D10 | A `stopped` run may be admitted (decision 0006, rulings 5 and 12); a `failed` one may not | One status test and its key row change |
| D11 | The store has its own decimal-text reader: 1C's is private to `provider/canned.py` | Two readers of one grammar; hoisting it is a later one-file change |
| D12 | `PRAGMA quick_check` runs at every writer open; a failure is `StoreCorrupt` | Seconds at open on a large file; it can move to resume only |
| D13 | The 2A row of `docs/legacy/ports.md` follows the pre-flight table, with `platform_io.replace` and `write_atomic` left for step 3B (done with this plan) | The coordinator's edit; the code is unaffected |

## Answer keys (implementers do not edit them or weaken a comparison)

Written by the controller before each task from invented values only. No database is committed.

1. `tests/store/store_schema_key.py`: each table's columns, types and null rules, and the
   SHA-256 of each merged migration's text.
2. A money table: `Decimal` to text (`0`, `0.00`, `20`, `0.00000000001`, `1E+3` as `1000`, a
   40-digit amount) and the refused inputs (`-0`, `1_0`, `1e3`, ` 1`, `01`, `.5`, `5.`, an
   Arabic-Indic digit, NaN, Infinity, a float, an int, a bool, a str).
3. A time table (datetimes and epoch floats with their 27-character text), and a literal
   receipt with its SHA-256 computed by `shasum`.
4. A reference model of the run and attempt states, about 60 lines, for the stateful test.
5. A scripted run and its expected resume literal: two modules; attempt 1 rejected and attempt
   2 accepted; a `not_sent` call, a zero charge, an unknown charge and an open call; an
   unfinished compaction and the one that supersedes it.
6. Adapted from `tests/test_library_index.py`, the rows about recorded hashes: a handoff
   changed after delivery, a module only the manifest names, a module not answered in this
   run, a delivery for another run, and zero, missing and unknown spend kept apart.
7. A hostile set, one test each: a newer schema, another application's file, a write-ahead
   file, a symbolic link, a UNC path, a float for money, a lone surrogate, a 1,024-byte bad
   pin name, a fenced writer, a held lock, a kill mid-write, a statement failing mid-method.

## PR sequence

| PR | Delivers |
| :--- | :--- |
| 1 | Errors; money, time and text codecs; path, permission and version rules; `open_store`, `open_reader`; the migration runner, tested with migration lists the tests supply |
| 2 | Migration 1 (`runs`, `run_sources`, `events`); create, claim, start and end a run; the fencing token; events; pins read back |
| 3 | Migration 2 (`attempts`, `calls`, `compactions`); attempts, calls, replies, verdicts; charge lines |
| 4 | The resume read; the per-method rollback test, the kill test, threads and two processes |
| 5 | Migration 3 (deliveries); admission and its refusals; the admitted list |

PR 1 is split to hold the 800-line cap: 1a (#162) the errors, the SQLite error mapping and
the CI version print; 1b (#169) the codecs; then 1c `location.py` (path rules), 1d `txn.py`
(the write transaction and the migration runner) and 1e `db.py` (open).

Ruled by the controller in PR 1 and confirmed: a SQLite error maps by primary result code (5
and 6 busy; 19 conflict; 11 and 26 corrupt; anything else unusable); an error message never
contains the refused value, and the PR that gives `store_error` its first caller shows that
SQLite's own constraint message carries no stored value or reduces it to the code's name; a time is an aware datetime or epoch seconds as an `int` or
float, never a bool; detail integers fit 64 signed bits; money text is at most 64 characters and refused
before formatting beyond 64 digits or an exponent outside -62 to 63; an existing folder or
file keeps its mode; the folder is absolute; the reader refuses a WAL file. The first layer
that stores a `SourceError` keeps its notes and decides the form of the path in its message.

## How it runs

Global rules §1, §3 and §7. The sub-session is the controller and writes no code: `mx-feature`
implements test first; `mx-precise` reviews each task, with the second reviewer named above.
Every brief and review prompt carries: no stub or fake value standing in for real behaviour;
no catch-all that hides a failure; no `assert` in source; the answer keys; a report ending
`Not verified:`. Property tests (`hypothesis`): money and time round trips, time text ordered
as the instants, a receipt independent of mapping order, and the stateful test against key 4
(after any sequence the store equals the model, and a refused call changed nothing). `mutmut`
does not mutate inside a SQL string: every `CHECK`, trigger and index has its own
raw-connection test, and reviewers hand-mutate the statements. Per task the gate is
`uv run --locked python tools/gates.py` (run `npm ci` in `web/` once first), exit 0. Before
each PR is ready: `/sweep refactoring discover changed-update`, then the whole-branch review
(`mx-architect` running `adversarial-reviewer`, fresh agent, §7 severities); verdicts and
report paths in the PR body; CI green on both runners, read before a review is dispatched.
Fix rounds follow §1.

## Done when

Each PR is open with CI green and its reviews passed, and the sub-session has sent the
coordinator one message per PR: the PR number, verdicts, report paths, gate exit codes,
mutation result, ledger lines (`2A-<pr> task=<n> agent=<name> fix-rounds=<n>
gates-first-pass=<y|n|n/a>`), parked Low findings and a `Not verified:` line. The coordinator
reads the diff and merges. The sub-session does not merge and does not edit shared records.

## Not verified

- No public repository's code was run and two were read only in part; an empty or thin search
  does not prove nothing exists. Legacy liveness is from `git grep` of imports at `9d040f8`.
- The SQLite bundled with Python 3.12 on the work PC and on the CI runners; PR 1 prints it on
  both runners. The probe ran on macOS only, and nothing ran on Windows: how a virus scanner
  or a sync client holding the file affects the journal, and whether `%LOCALAPPDATA%` on the
  work PC is local and unsynced.
- SQLite's own pages were not fetched: the 3.37 floor for `STRICT`, WAL on a network file
  system and serialized threading on Windows builds are from memory.
- What step 3A needs from the resume read is inferred from the legacy loop and decision 0006;
  3A is not planned. The 2B plan was only searched for `store` (it places no duty here).
  Database size with raw bodies over a real run, and how long `quick_check` then takes.
