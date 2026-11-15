"""Migration 1: the runs, run_sources and events tables. Migration 2: the attempts, calls and
compactions tables.

A merged migration is never edited: its SHA-256 is in tests/store/store_schema_key.py.

Migration 2, three consequences:

- Writes to the three tables (inserts and updates of attempts and calls, inserts of compactions)
  are refused by trigger unless the run is `running` (ruling U9). A crashed run is taken over by
  `claim_run`, so take-over is claim, fail the open attempt (an open call of it stays open, D7),
  then `end_run`; on resume it is `start_run`, then fail. PR 5's settle table (migration 3) writes
  on a stopped run and is outside this gate by design.
- Provider text is stored backslashreplace-escaped, so a lone surrogate escaped and a literal
  `\\ud800` are one stored id (U12).
- Every CHECK on `calls` and `compactions` accepts every `Reply` and `Compaction` the provider's
  constructors accept, as the codecs write them (U14).
"""

from credit_os.store.txn import Migration

MIGRATION_1: Migration = (
    (
        "CREATE TABLE runs(run_id TEXT PRIMARY KEY NOT NULL CHECK (length(run_id) BETWEEN 1 "
        "AND 128 AND run_id NOT GLOB '*[^A-Za-z0-9._-]*' AND length(CAST(run_id AS BLOB)) = "
        "length(run_id)), issuer_id TEXT NOT NULL CHECK (length(issuer_id) BETWEEN 1 AND 128 "
        "AND issuer_id NOT GLOB '*[^A-Za-z0-9._-]*' AND length(CAST(issuer_id AS BLOB)) = "
        "length(issuer_id)), issuer_name TEXT NOT NULL CHECK (issuer_name <> ''), "
        "as_of TEXT CHECK (as_of IS NULL OR (length(CAST(as_of AS BLOB)) = 10 AND as_of GLOB "
        "'[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' AND date(as_of) IS as_of AND "
        "substr(as_of, 1, 4) <> '0000')), config_id TEXT NOT NULL CHECK (length(config_id) "
        "BETWEEN 1 AND 128 AND config_id NOT GLOB '*[^A-Za-z0-9._-]*' AND "
        "length(CAST(config_id AS BLOB)) = length(config_id)), cap_usd TEXT NOT NULL CHECK "
        "(cap_usd GLOB '[0-9]*' AND cap_usd NOT GLOB '*[^0-9.]*' AND cap_usd NOT GLOB "
        "'*.*.*' AND cap_usd NOT GLOB '*.' AND cap_usd NOT GLOB '0[0-9]*' AND "
        "length(cap_usd) <= 64 AND length(CAST(cap_usd AS BLOB)) = length(cap_usd)), request "
        "BLOB NOT NULL, request_sha256 TEXT NOT NULL CHECK (length(request_sha256) = 64 AND "
        "length(CAST(request_sha256 AS BLOB)) = 64 AND request_sha256 NOT GLOB "
        "'*[^0-9a-f]*'), status TEXT NOT NULL CHECK (status IN ('created', 'running', "
        "'rejected', 'finished', 'stopped', 'failed')), end_reason TEXT CHECK (end_reason IS "
        "NULL OR (length(end_reason) BETWEEN 1 AND 64 AND end_reason GLOB '[a-z]*' AND "
        "end_reason NOT GLOB '*[^a-z0-9_]*' AND length(CAST(end_reason AS BLOB)) = "
        "length(end_reason))), end_message TEXT, writer TEXT NOT NULL CHECK (length(writer) "
        "= 32 AND length(CAST(writer AS BLOB)) = 32 AND writer NOT GLOB '*[^0-9a-f]*'), "
        "created_at TEXT NOT NULL CHECK (length(CAST(created_at AS BLOB)) = 27 AND "
        "created_at GLOB "
        "'[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]Z' "
        "AND strftime('%Y-%m-%dT%H:%M:%S', substr(created_at, 1, 19)) IS substr(created_at, "
        "1, 19) AND substr(created_at, 12, 2) < '24' AND substr(created_at, 1, 4) <> "
        "'0000'), started_at TEXT CHECK (started_at IS NULL OR (length(CAST(started_at AS "
        "BLOB)) = 27 AND started_at GLOB "
        "'[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]Z' "
        "AND strftime('%Y-%m-%dT%H:%M:%S', substr(started_at, 1, 19)) IS substr(started_at, "
        "1, 19) AND substr(started_at, 12, 2) < '24' AND substr(started_at, 1, 4) <> "
        "'0000')), ended_at TEXT CHECK (ended_at IS NULL OR (length(CAST(ended_at AS BLOB)) "
        "= 27 AND ended_at GLOB "
        "'[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]Z' "
        "AND strftime('%Y-%m-%dT%H:%M:%S', substr(ended_at, 1, 19)) IS substr(ended_at, 1, "
        "19) AND substr(ended_at, 12, 2) < '24' AND substr(ended_at, 1, 4) <> '0000')), "
        "CHECK ((status IN ('rejected', 'finished', 'stopped', 'failed')) = (ended_at IS NOT "
        "NULL)), CHECK ((ended_at IS NULL) = (end_reason IS NULL)), CHECK (end_message IS "
        "NULL OR end_reason IS NOT NULL), CHECK ((status IN ('created', 'rejected')) = "
        "(started_at IS NULL))) STRICT, WITHOUT ROWID"
    ),
    (
        "CREATE TRIGGER runs_created_only BEFORE INSERT ON runs WHEN NEW.status <> 'created' "
        "BEGIN SELECT RAISE(ABORT, 'runs: a run starts as created'); END"
    ),
    (
        "CREATE TRIGGER runs_no_replace BEFORE INSERT ON runs WHEN EXISTS (SELECT 1 FROM "
        "runs WHERE run_id = NEW.run_id) BEGIN SELECT RAISE(ABORT, 'runs: a run is never "
        "replaced'); END"
    ),
    (
        "CREATE TRIGGER runs_fixed_columns BEFORE UPDATE OF run_id, issuer_id, issuer_name, "
        "as_of, config_id, cap_usd, request, request_sha256, created_at ON runs BEGIN SELECT "
        "RAISE(ABORT, 'runs: identity, cap and request never change'); END"
    ),
    (
        "CREATE TRIGGER runs_no_delete BEFORE DELETE ON runs BEGIN SELECT RAISE(ABORT, "
        "'runs: a run is never deleted'); END"
    ),
    (
        "CREATE TRIGGER runs_status_moves BEFORE UPDATE OF status ON runs WHEN NOT "
        "((OLD.status = 'created' AND NEW.status IN ('running', 'rejected')) OR (OLD.status "
        "= 'running' AND NEW.status IN ('finished', 'stopped', 'failed')) OR (OLD.status IN "
        "('stopped', 'failed') AND NEW.status = 'running')) BEGIN SELECT RAISE(ABORT, 'runs: "
        "that status move is not allowed'); END"
    ),
    (
        "CREATE TRIGGER runs_final BEFORE UPDATE ON runs WHEN OLD.status IN ('finished', "
        "'rejected') AND NEW.status = OLD.status BEGIN SELECT RAISE(ABORT, 'runs: a finished "
        "or rejected run never changes'); END"
    ),
    (
        "CREATE TRIGGER runs_started_once BEFORE UPDATE OF started_at ON runs WHEN "
        "OLD.started_at IS NOT NULL AND NEW.started_at IS NOT OLD.started_at BEGIN SELECT "
        "RAISE(ABORT, 'runs: the first start time never changes'); END"
    ),
    (
        "CREATE TABLE run_sources(run_id TEXT NOT NULL REFERENCES runs(run_id), position "
        "INTEGER NOT NULL CHECK (position >= 0), name TEXT NOT NULL CHECK (length(name) >= "
        "1), sha256 TEXT NOT NULL CHECK (length(sha256) = 64 AND length(CAST(sha256 AS "
        "BLOB)) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'), size_bytes INTEGER NOT NULL CHECK "
        "(size_bytes >= 0), kind TEXT NOT NULL CHECK (length(kind) >= 1), PRIMARY KEY "
        "(run_id, position), UNIQUE (run_id, name)) STRICT, WITHOUT ROWID"
    ),
    (
        "CREATE TRIGGER run_sources_needs_run BEFORE INSERT ON run_sources WHEN NOT EXISTS "
        "(SELECT 1 FROM runs WHERE run_id = NEW.run_id) BEGIN SELECT RAISE(ABORT, "
        "'run_sources: the run does not exist'); END"
    ),
    (
        "CREATE TRIGGER run_sources_no_replace BEFORE INSERT ON run_sources WHEN EXISTS "
        "(SELECT 1 FROM run_sources WHERE run_id = NEW.run_id AND (position = NEW.position "
        "OR name = NEW.name)) BEGIN SELECT RAISE(ABORT, 'run_sources: a pin is never "
        "replaced'); END"
    ),
    (
        "CREATE TRIGGER run_sources_no_update BEFORE UPDATE ON run_sources BEGIN SELECT "
        "RAISE(ABORT, 'run_sources: a pin never changes'); END"
    ),
    (
        "CREATE TRIGGER run_sources_no_delete BEFORE DELETE ON run_sources BEGIN SELECT "
        "RAISE(ABORT, 'run_sources: a pin is never deleted'); END"
    ),
    (
        "CREATE TRIGGER run_sources_created_only BEFORE INSERT ON run_sources WHEN (SELECT "
        "status FROM runs WHERE run_id = NEW.run_id) <> 'created' BEGIN SELECT RAISE(ABORT, "
        "'run_sources: a pin is added only while its run is created'); END"
    ),
    (
        "CREATE TABLE events(seq INTEGER PRIMARY KEY AUTOINCREMENT CHECK (seq >= 1), run_id TEXT NOT NULL "
        "REFERENCES runs(run_id), at TEXT NOT NULL CHECK (length(CAST(at AS BLOB)) = 27 AND "
        "at GLOB "
        "'[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]Z' "
        "AND strftime('%Y-%m-%dT%H:%M:%S', substr(at, 1, 19)) IS substr(at, 1, 19) AND "
        "substr(at, 12, 2) < '24' AND substr(at, 1, 4) <> '0000'), kind TEXT NOT NULL CHECK "
        "(length(kind) BETWEEN 1 AND 64 AND kind GLOB '[a-z]*' AND kind NOT GLOB "
        "'*[^a-z0-9_]*' AND length(CAST(kind AS BLOB)) = length(kind)), module_id TEXT CHECK "
        "(module_id IS NULL OR (length(module_id) BETWEEN 1 AND 128 AND module_id NOT GLOB "
        "'*[^A-Za-z0-9._-]*' AND length(CAST(module_id AS BLOB)) = length(module_id))), "
        "attempt INTEGER CHECK (attempt IS NULL OR (attempt >= 1 AND module_id IS NOT "
        "NULL)), detail TEXT NOT NULL CHECK (detail GLOB '{*}' AND length(CAST(detail AS "
        "BLOB)) = length(detail))) STRICT"
    ),
    "CREATE INDEX events_by_run ON events(run_id, seq)",
    (
        "CREATE TRIGGER events_needs_run BEFORE INSERT ON events WHEN NOT EXISTS (SELECT 1 "
        "FROM runs WHERE run_id = NEW.run_id) BEGIN SELECT RAISE(ABORT, 'events: the run "
        "does not exist'); END"
    ),
    (
        "CREATE TRIGGER events_no_replace BEFORE INSERT ON events WHEN EXISTS (SELECT 1 FROM "
        "events WHERE seq = NEW.seq) BEGIN SELECT RAISE(ABORT, 'events: an event is never "
        "replaced'); END"
    ),
    (
        "CREATE TRIGGER events_final_run BEFORE INSERT ON events WHEN (SELECT status FROM "
        "runs WHERE run_id = NEW.run_id) IN ('finished', 'rejected') BEGIN SELECT "
        "RAISE(ABORT, 'events: a finished or rejected run takes no event'); END"
    ),
    (
        "CREATE TRIGGER events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT, "
        "'events: an event never changes'); END"
    ),
    (
        "CREATE TRIGGER events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT, "
        "'events: an event is never deleted'); END"
    ),
    "PRAGMA user_version = 1",
)

MIGRATION_2: Migration = (
    (
        "CREATE TABLE attempts(run_id TEXT NOT NULL REFERENCES runs(run_id), module_id TEXT NOT "
        "NULL CHECK (length(module_id) BETWEEN 1 AND 128 AND module_id NOT GLOB "
        "'*[^A-Za-z0-9._-]*' AND length(CAST(module_id AS BLOB)) = length(module_id)), attempt "
        "INTEGER NOT NULL CHECK (attempt >= 1), request BLOB NOT NULL, request_sha256 TEXT NOT "
        "NULL CHECK (length(request_sha256) = 64 AND length(CAST(request_sha256 AS BLOB)) = 64 "
        "AND request_sha256 NOT GLOB '*[^0-9a-f]*'), state TEXT NOT NULL CHECK (state IN "
        "('open', 'replied', 'failed', 'accepted', 'rejected')), reply BLOB, reply_sha256 TEXT "
        "CHECK (reply_sha256 IS NULL OR (length(reply_sha256) = 64 AND length(CAST(reply_sha256 "
        "AS BLOB)) = 64 AND reply_sha256 NOT GLOB '*[^0-9a-f]*')), issues TEXT CHECK (issues IS "
        "NULL OR (issues GLOB '[[]*]' AND length(CAST(issues AS BLOB)) = length(issues))), "
        "fail_reason TEXT CHECK (fail_reason IS NULL OR (length(fail_reason) BETWEEN 1 AND 64 "
        "AND fail_reason GLOB '[a-z]*' AND fail_reason NOT GLOB '*[^a-z0-9_]*' AND "
        "length(CAST(fail_reason AS BLOB)) = length(fail_reason))), opened_at TEXT NOT NULL "
        "CHECK (length(CAST(opened_at AS BLOB)) = 27 AND opened_at GLOB "
        "'[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]Z' "
        "AND strftime('%Y-%m-%dT%H:%M:%S', substr(opened_at, 1, 19)) IS substr(opened_at, 1, 19) "
        "AND substr(opened_at, 12, 2) < '24' AND substr(opened_at, 1, 4) <> '0000'), replied_at "
        "TEXT CHECK (replied_at IS NULL OR (length(CAST(replied_at AS BLOB)) = 27 AND replied_at "
        "GLOB "
        "'[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]Z' "
        "AND strftime('%Y-%m-%dT%H:%M:%S', substr(replied_at, 1, 19)) IS substr(replied_at, 1, "
        "19) AND substr(replied_at, 12, 2) < '24' AND substr(replied_at, 1, 4) <> '0000')), "
        "closed_at TEXT CHECK (closed_at IS NULL OR (length(CAST(closed_at AS BLOB)) = 27 AND "
        "closed_at GLOB "
        "'[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]Z' "
        "AND strftime('%Y-%m-%dT%H:%M:%S', substr(closed_at, 1, 19)) IS substr(closed_at, 1, 19) "
        "AND substr(closed_at, 12, 2) < '24' AND substr(closed_at, 1, 4) <> '0000')), CHECK "
        "((reply IS NULL) = (reply_sha256 IS NULL)), CHECK ((state IN ('replied', 'accepted', "
        "'rejected')) = (reply IS NOT NULL)), CHECK ((reply IS NULL) = (replied_at IS NULL)), "
        "CHECK ((state IN ('accepted', 'rejected')) = (issues IS NOT NULL)), CHECK ((state = "
        "'failed') = (fail_reason IS NOT NULL)), CHECK ((state IN ('failed', 'accepted', "
        "'rejected')) = (closed_at IS NOT NULL)), PRIMARY KEY (run_id, module_id, attempt)) "
        "STRICT, WITHOUT ROWID"
    ),
    (
        "CREATE UNIQUE INDEX attempts_one_accepted ON attempts(run_id, module_id) WHERE state = "
        "'accepted'"
    ),
    (
        "CREATE TRIGGER attempts_needs_run BEFORE INSERT ON attempts WHEN NOT EXISTS (SELECT 1 "
        "FROM runs WHERE run_id = NEW.run_id) BEGIN SELECT RAISE(ABORT, 'attempts: the run does "
        "not exist'); END"
    ),
    (
        "CREATE TRIGGER attempts_running_run BEFORE INSERT ON attempts WHEN (SELECT status FROM "
        "runs WHERE run_id = NEW.run_id) <> 'running' BEGIN SELECT RAISE(ABORT, 'attempts: an "
        "attempt is opened only while its run is running'); END"
    ),
    (
        "CREATE TRIGGER attempts_no_replace BEFORE INSERT ON attempts WHEN EXISTS (SELECT 1 FROM "
        "attempts WHERE run_id = NEW.run_id AND module_id = NEW.module_id AND attempt = "
        "NEW.attempt) BEGIN SELECT RAISE(ABORT, 'attempts: an attempt is never replaced'); END"
    ),
    (
        "CREATE TRIGGER attempts_open_only BEFORE INSERT ON attempts WHEN NEW.state <> 'open' "
        "BEGIN SELECT RAISE(ABORT, 'attempts: an attempt starts open'); END"
    ),
    (
        "CREATE TRIGGER attempts_numbered BEFORE INSERT ON attempts WHEN NEW.attempt <> "
        "coalesce((SELECT max(attempt) FROM attempts WHERE run_id = NEW.run_id AND module_id = "
        "NEW.module_id), 0) + 1 BEGIN SELECT RAISE(ABORT, 'attempts: attempts are numbered from "
        "1 with no gap'); END"
    ),
    (
        "CREATE TRIGGER attempts_after_closed BEFORE INSERT ON attempts WHEN EXISTS (SELECT 1 "
        "FROM attempts WHERE run_id = NEW.run_id AND module_id = NEW.module_id AND state NOT IN "
        "('failed', 'rejected')) BEGIN SELECT RAISE(ABORT, 'attempts: the next attempt opens "
        "only after the last is rejected or failed'); END"
    ),
    (
        "CREATE TRIGGER attempts_fixed_columns BEFORE UPDATE OF run_id, module_id, attempt, "
        "request, request_sha256, opened_at ON attempts BEGIN SELECT RAISE(ABORT, 'attempts: "
        "identity and request never change'); END"
    ),
    (
        "CREATE TRIGGER attempts_state_moves BEFORE UPDATE OF state ON attempts WHEN NOT "
        "((OLD.state = 'open' AND NEW.state IN ('replied', 'failed')) OR (OLD.state = 'replied' "
        "AND NEW.state IN ('accepted', 'rejected'))) BEGIN SELECT RAISE(ABORT, 'attempts: that "
        "state move is not allowed'); END"
    ),
    (
        "CREATE TRIGGER attempts_final BEFORE UPDATE ON attempts WHEN OLD.state IN ('failed', "
        "'accepted', 'rejected') BEGIN SELECT RAISE(ABORT, 'attempts: a failed, accepted or "
        "rejected attempt never changes'); END"
    ),
    (
        "CREATE TRIGGER attempts_reply_once BEFORE UPDATE OF reply, reply_sha256, replied_at ON "
        "attempts WHEN OLD.reply IS NOT NULL BEGIN SELECT RAISE(ABORT, 'attempts: a reply never "
        "changes'); END"
    ),
    (
        "CREATE TRIGGER attempts_running_run_update BEFORE UPDATE ON attempts WHEN (SELECT "
        "status FROM runs WHERE run_id = NEW.run_id) <> 'running' BEGIN SELECT RAISE(ABORT, "
        "'attempts: an attempt changes only while its run is running'); END"
    ),
    (
        "CREATE TRIGGER attempts_no_delete BEFORE DELETE ON attempts BEGIN SELECT RAISE(ABORT, "
        "'attempts: an attempt is never deleted'); END"
    ),
    (
        "CREATE TABLE calls(run_id TEXT NOT NULL, module_id TEXT NOT NULL, attempt INTEGER NOT "
        "NULL, call_index INTEGER NOT NULL CHECK (call_index >= 0), exchange_id TEXT NOT NULL "
        "CHECK (length(exchange_id) BETWEEN 1 AND 128 AND exchange_id NOT GLOB "
        "'*[^A-Za-z0-9._-]*' AND length(CAST(exchange_id AS BLOB)) = length(exchange_id)), "
        "provider_call_index INTEGER NOT NULL CHECK (provider_call_index >= 0), hold_usd TEXT "
        "NOT NULL CHECK (hold_usd GLOB '[0-9]*' AND hold_usd NOT GLOB '*[^0-9.]*' AND hold_usd "
        "NOT GLOB '*.*.*' AND hold_usd NOT GLOB '*.' AND hold_usd NOT GLOB '0[0-9]*' AND "
        "length(hold_usd) <= 64 AND length(CAST(hold_usd AS BLOB)) = length(hold_usd)), "
        "opened_at TEXT NOT NULL CHECK (length(CAST(opened_at AS BLOB)) = 27 AND opened_at GLOB "
        "'[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]Z' "
        "AND strftime('%Y-%m-%dT%H:%M:%S', substr(opened_at, 1, 19)) IS substr(opened_at, 1, 19) "
        "AND substr(opened_at, 12, 2) < '24' AND substr(opened_at, 1, 4) <> '0000'), closed_at "
        "TEXT CHECK (closed_at IS NULL OR (length(CAST(closed_at AS BLOB)) = 27 AND closed_at "
        "GLOB "
        "'[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]Z' "
        "AND strftime('%Y-%m-%dT%H:%M:%S', substr(closed_at, 1, 19)) IS substr(closed_at, 1, 19) "
        "AND substr(closed_at, 12, 2) < '24' AND substr(closed_at, 1, 4) <> '0000')), kind TEXT "
        "CHECK (kind IS NULL OR kind IN ('ok', 'not_sent', 'sent_usage', 'sent_unknown')), "
        "error_class TEXT CHECK (error_class IS NULL OR error_class <> ''), message TEXT, "
        "input_tokens INTEGER CHECK (input_tokens IS NULL OR input_tokens >= 0), "
        "cached_read_tokens INTEGER CHECK (cached_read_tokens IS NULL OR cached_read_tokens >= "
        "0), cache_write_tokens INTEGER CHECK (cache_write_tokens IS NULL OR cache_write_tokens "
        ">= 0), output_tokens INTEGER CHECK (output_tokens IS NULL OR output_tokens >= 0), "
        "reasoning_tokens INTEGER CHECK (reasoning_tokens IS NULL OR reasoning_tokens >= 0), "
        "billed_usd TEXT CHECK (billed_usd IS NULL OR (billed_usd GLOB '[0-9]*' AND billed_usd "
        "NOT GLOB '*[^0-9.]*' AND billed_usd NOT GLOB '*.*.*' AND billed_usd NOT GLOB '*.' AND "
        "billed_usd NOT GLOB '0[0-9]*' AND length(billed_usd) <= 64 AND length(CAST(billed_usd "
        "AS BLOB)) = length(billed_usd))), started_at TEXT CHECK (started_at IS NULL OR "
        "(length(CAST(started_at AS BLOB)) = 27 AND started_at GLOB "
        "'[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]Z' "
        "AND strftime('%Y-%m-%dT%H:%M:%S', substr(started_at, 1, 19)) IS substr(started_at, 1, "
        "19) AND substr(started_at, 12, 2) < '24' AND substr(started_at, 1, 4) <> '0000')), "
        "finished_at TEXT CHECK (finished_at IS NULL OR (length(CAST(finished_at AS BLOB)) = 27 "
        "AND finished_at GLOB "
        "'[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9][0-9][0-9][0-9]Z' "
        "AND strftime('%Y-%m-%dT%H:%M:%S', substr(finished_at, 1, 19)) IS substr(finished_at, 1, "
        "19) AND substr(finished_at, 12, 2) < '24' AND substr(finished_at, 1, 4) <> '0000')), "
        "stop_reason TEXT CHECK (stop_reason IS NULL OR stop_reason IN ('end', 'tool_use', "
        "'max_tokens', 'other')), reported_model TEXT, request_id TEXT, raw BLOB, CHECK "
        "((closed_at IS NULL) = (kind IS NULL)), CHECK (kind IS NOT NULL OR (error_class IS NULL "
        "AND message IS NULL AND input_tokens IS NULL AND cached_read_tokens IS NULL AND "
        "cache_write_tokens IS NULL AND output_tokens IS NULL AND reasoning_tokens IS NULL AND "
        "billed_usd IS NULL AND started_at IS NULL AND finished_at IS NULL AND stop_reason IS "
        "NULL AND reported_model IS NULL AND request_id IS NULL AND raw IS NULL)), CHECK (kind "
        "IS NULL OR (kind = 'ok') = (stop_reason IS NOT NULL)), CHECK (kind IS NULL OR (kind = "
        "'ok') = (error_class IS NULL)), CHECK (kind IS NULL OR kind = 'ok' OR (reported_model "
        "IS NULL AND request_id IS NULL)), CHECK (kind IS NULL OR kind NOT IN ('not_sent', "
        "'sent_unknown') OR (input_tokens IS NULL AND cached_read_tokens IS NULL AND "
        "cache_write_tokens IS NULL AND output_tokens IS NULL AND reasoning_tokens IS NULL AND "
        "billed_usd IS NULL)), CHECK (kind IS NULL OR kind <> 'sent_usage' OR billed_usd IS NOT "
        "NULL OR input_tokens IS NOT NULL OR cached_read_tokens IS NOT NULL OR "
        "cache_write_tokens IS NOT NULL OR output_tokens IS NOT NULL OR reasoning_tokens IS NOT "
        "NULL), PRIMARY KEY (run_id, module_id, attempt, call_index), UNIQUE (run_id, "
        "exchange_id, provider_call_index), FOREIGN KEY (run_id, module_id, attempt) REFERENCES "
        "attempts(run_id, module_id, attempt)) STRICT, WITHOUT ROWID"
    ),
    (
        "CREATE TRIGGER calls_needs_attempt BEFORE INSERT ON calls WHEN NOT EXISTS (SELECT 1 "
        "FROM attempts WHERE run_id = NEW.run_id AND module_id = NEW.module_id AND attempt = "
        "NEW.attempt) BEGIN SELECT RAISE(ABORT, 'calls: the attempt does not exist'); END"
    ),
    (
        "CREATE TRIGGER calls_open_attempt BEFORE INSERT ON calls WHEN (SELECT state FROM "
        "attempts WHERE run_id = NEW.run_id AND module_id = NEW.module_id AND attempt = "
        "NEW.attempt) <> 'open' BEGIN SELECT RAISE(ABORT, 'calls: a call is opened only while "
        "its attempt is open'); END"
    ),
    (
        "CREATE TRIGGER calls_running_run BEFORE INSERT ON calls WHEN (SELECT status FROM runs "
        "WHERE run_id = NEW.run_id) <> 'running' BEGIN SELECT RAISE(ABORT, 'calls: a call is "
        "opened only while its run is running'); END"
    ),
    (
        "CREATE TRIGGER calls_no_replace BEFORE INSERT ON calls WHEN EXISTS (SELECT 1 FROM calls "
        "WHERE (run_id = NEW.run_id AND module_id = NEW.module_id AND attempt = NEW.attempt AND "
        "call_index = NEW.call_index) OR (run_id = NEW.run_id AND exchange_id = NEW.exchange_id "
        "AND provider_call_index = NEW.provider_call_index)) BEGIN SELECT RAISE(ABORT, 'calls: a "
        "call is never replaced'); END"
    ),
    (
        "CREATE TRIGGER calls_opened_only BEFORE INSERT ON calls WHEN NEW.closed_at IS NOT NULL "
        "BEGIN SELECT RAISE(ABORT, 'calls: a call starts open'); END"
    ),
    (
        "CREATE TRIGGER calls_numbered BEFORE INSERT ON calls WHEN NEW.call_index <> "
        "coalesce((SELECT max(call_index) FROM calls WHERE run_id = NEW.run_id AND module_id = "
        "NEW.module_id AND attempt = NEW.attempt), -1) + 1 BEGIN SELECT RAISE(ABORT, 'calls: "
        "calls are numbered from 0 with no gap'); END"
    ),
    (
        "CREATE TRIGGER calls_one_open BEFORE INSERT ON calls WHEN EXISTS (SELECT 1 FROM calls "
        "WHERE run_id = NEW.run_id AND module_id = NEW.module_id AND attempt = NEW.attempt AND "
        "closed_at IS NULL) BEGIN SELECT RAISE(ABORT, 'calls: an attempt has one open call at "
        "most'); END"
    ),
    (
        "CREATE TRIGGER calls_fixed_columns BEFORE UPDATE OF run_id, module_id, attempt, "
        "call_index, exchange_id, provider_call_index, hold_usd, opened_at ON calls BEGIN SELECT "
        "RAISE(ABORT, 'calls: identity, naming and hold never change'); END"
    ),
    (
        "CREATE TRIGGER calls_closed_once BEFORE UPDATE ON calls WHEN OLD.closed_at IS NOT NULL "
        "BEGIN SELECT RAISE(ABORT, 'calls: a closed call never changes'); END"
    ),
    (
        "CREATE TRIGGER calls_close_open_attempt BEFORE UPDATE ON calls WHEN (SELECT state FROM "
        "attempts WHERE run_id = NEW.run_id AND module_id = NEW.module_id AND attempt = "
        "NEW.attempt) <> 'open' BEGIN SELECT RAISE(ABORT, 'calls: a call is closed only while "
        "its attempt is open'); END"
    ),
    (
        "CREATE TRIGGER calls_running_run_update BEFORE UPDATE ON calls WHEN (SELECT status FROM "
        "runs WHERE run_id = NEW.run_id) <> 'running' BEGIN SELECT RAISE(ABORT, 'calls: a call "
        "is closed only while its run is running'); END"
    ),
    (
        "CREATE TRIGGER calls_no_delete BEFORE DELETE ON calls BEGIN SELECT RAISE(ABORT, 'calls: "
        "a call is never deleted'); END"
    ),
    (
        "CREATE TRIGGER attempts_reply_no_open_call BEFORE UPDATE OF state ON attempts WHEN "
        "NEW.state = 'replied' AND EXISTS (SELECT 1 FROM calls WHERE run_id = NEW.run_id AND "
        "module_id = NEW.module_id AND attempt = NEW.attempt AND closed_at IS NULL) BEGIN SELECT "
        "RAISE(ABORT, 'attempts: a reply is recorded only when no call of the attempt is open'); "
        "END"
    ),
    (
        "CREATE TABLE compactions(run_id TEXT NOT NULL REFERENCES runs(run_id), event_id TEXT "
        "NOT NULL CHECK (event_id <> ''), position INTEGER NOT NULL CHECK (position >= 0), "
        "module_id TEXT CHECK (module_id IS NULL OR (length(module_id) BETWEEN 1 AND 128 AND "
        "module_id NOT GLOB '*[^A-Za-z0-9._-]*' AND length(CAST(module_id AS BLOB)) = "
        "length(module_id))), attempt INTEGER CHECK (attempt IS NULL OR attempt >= 1), "
        "call_index INTEGER CHECK (call_index IS NULL OR call_index >= 0), input_tokens INTEGER "
        "CHECK (input_tokens IS NULL OR input_tokens >= 0), cached_read_tokens INTEGER CHECK "
        "(cached_read_tokens IS NULL OR cached_read_tokens >= 0), cache_write_tokens INTEGER "
        "CHECK (cache_write_tokens IS NULL OR cache_write_tokens >= 0), output_tokens INTEGER "
        "CHECK (output_tokens IS NULL OR output_tokens >= 0), billed_usd TEXT CHECK (billed_usd "
        "IS NULL OR (billed_usd GLOB '[0-9]*' AND billed_usd NOT GLOB '*[^0-9.]*' AND billed_usd "
        "NOT GLOB '*.*.*' AND billed_usd NOT GLOB '*.' AND billed_usd NOT GLOB '0[0-9]*' AND "
        "length(billed_usd) <= 64 AND length(CAST(billed_usd AS BLOB)) = length(billed_usd))), "
        "outcome TEXT NOT NULL CHECK (outcome IN ('done', 'failed', 'unfinished')), supersedes "
        "TEXT CHECK (supersedes IS NULL OR supersedes <> ''), CHECK ((module_id IS NULL) = "
        "(attempt IS NULL) AND (attempt IS NULL) = (call_index IS NULL)), CHECK (outcome <> "
        "'unfinished' OR (input_tokens IS NULL AND cached_read_tokens IS NULL AND "
        "cache_write_tokens IS NULL AND output_tokens IS NULL AND billed_usd IS NULL AND "
        "supersedes IS NULL)), CHECK (supersedes IS NULL OR supersedes <> event_id), PRIMARY KEY "
        "(run_id, event_id), UNIQUE (run_id, position), FOREIGN KEY (run_id, module_id, attempt, "
        "call_index) REFERENCES calls(run_id, module_id, attempt, call_index)) STRICT, WITHOUT "
        "ROWID"
    ),
    (
        "CREATE TRIGGER compactions_needs_run BEFORE INSERT ON compactions WHEN NOT EXISTS "
        "(SELECT 1 FROM runs WHERE run_id = NEW.run_id) BEGIN SELECT RAISE(ABORT, 'compactions: "
        "the run does not exist'); END"
    ),
    (
        "CREATE TRIGGER compactions_needs_call BEFORE INSERT ON compactions WHEN NEW.call_index "
        "IS NOT NULL AND NOT EXISTS (SELECT 1 FROM calls WHERE run_id = NEW.run_id AND module_id "
        "= NEW.module_id AND attempt = NEW.attempt AND call_index = NEW.call_index) BEGIN SELECT "
        "RAISE(ABORT, 'compactions: the call does not exist'); END"
    ),
    (
        "CREATE TRIGGER compactions_open_call BEFORE INSERT ON compactions WHEN NEW.call_index "
        "IS NOT NULL AND (SELECT closed_at FROM calls WHERE run_id = NEW.run_id AND module_id = "
        "NEW.module_id AND attempt = NEW.attempt AND call_index = NEW.call_index) IS NOT NULL "
        "BEGIN SELECT RAISE(ABORT, 'compactions: a closed call takes no compaction'); END"
    ),
    (
        "CREATE TRIGGER compactions_open_attempt BEFORE INSERT ON compactions WHEN "
        "NEW.call_index IS NOT NULL AND (SELECT state FROM attempts WHERE run_id = NEW.run_id "
        "AND module_id = NEW.module_id AND attempt = NEW.attempt) <> 'open' BEGIN SELECT "
        "RAISE(ABORT, 'compactions: a call takes a compaction only while its attempt is open'); "
        "END"
    ),
    (
        "CREATE TRIGGER compactions_running_run BEFORE INSERT ON compactions WHEN (SELECT status "
        "FROM runs WHERE run_id = NEW.run_id) <> 'running' BEGIN SELECT RAISE(ABORT, "
        "'compactions: a compaction is recorded only while its run is running'); END"
    ),
    (
        "CREATE TRIGGER compactions_no_replace BEFORE INSERT ON compactions WHEN EXISTS (SELECT "
        "1 FROM compactions WHERE run_id = NEW.run_id AND (event_id = NEW.event_id OR position = "
        "NEW.position)) BEGIN SELECT RAISE(ABORT, 'compactions: a compaction is never "
        "replaced'); END"
    ),
    (
        "CREATE TRIGGER compactions_numbered BEFORE INSERT ON compactions WHEN NEW.position <> "
        "coalesce((SELECT max(position) FROM compactions WHERE run_id = NEW.run_id), -1) + 1 "
        "BEGIN SELECT RAISE(ABORT, 'compactions: compactions are numbered from 0 with no gap'); "
        "END"
    ),
    (
        "CREATE TRIGGER compactions_no_update BEFORE UPDATE ON compactions BEGIN SELECT "
        "RAISE(ABORT, 'compactions: a compaction never changes'); END"
    ),
    (
        "CREATE TRIGGER compactions_no_delete BEFORE DELETE ON compactions BEGIN SELECT "
        "RAISE(ABORT, 'compactions: a compaction is never deleted'); END"
    ),
    "PRAGMA user_version = 2",
)
