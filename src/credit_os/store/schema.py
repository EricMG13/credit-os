"""Migration 1: the runs, run_sources and events tables.

A merged migration is never edited: its SHA-256 is in tests/store/store_schema_key.py.
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
        "(started_at IS NULL))) STRICT"
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
        "(run_id, position), UNIQUE (run_id, name)) STRICT"
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
