"""Answer key for the store's write transaction and migration runner (2A plan, PR 1d).

Written by the controller from invented values before the code existed. The migrations here are
test-only lists: the store's own first migration arrives with PR 2. Implementers do not edit this
file or weaken a comparison against it.
"""

# A migration is a tuple of single static statements whose last one is its literal version line.
M1 = (
    "CREATE TABLE note(id INTEGER PRIMARY KEY, body TEXT NOT NULL) STRICT",
    "PRAGMA user_version = 1",
)
M2 = (
    "ALTER TABLE note ADD COLUMN tag TEXT",
    "CREATE INDEX note_tag ON note(tag)",
    "PRAGMA user_version = 2",
)
M3 = (
    (
        "CREATE TABLE reply(id INTEGER PRIMARY KEY, "
        "note_id INTEGER NOT NULL REFERENCES note(id)) STRICT"
    ),
    "PRAGMA user_version = 3",
)

# (type, name) rows of sqlite_schema, sorted, after each version.
SCHEMA_AT: dict[int, tuple[tuple[str, str], ...]] = {
    0: (),
    1: (("table", "note"),),
    2: (("index", "note_tag"), ("table", "note")),
    3: (("index", "note_tag"), ("table", "note"), ("table", "reply")),
}
# Column names of `note`, in order, after each version.
NOTE_COLUMNS_AT: dict[int, tuple[str, ...]] = {
    1: ("id", "body"),
    2: ("id", "body", "tag"),
    3: ("id", "body", "tag"),
}

_ADD_TAG = "ALTER TABLE note ADD COLUMN tag TEXT"

# Second migrations that must fail and leave a version-1 database exactly as it was: version,
# schema, journal mode, application id and a full dump unchanged, and no transaction left open.
# Nor is anything left on the connection: no attached database, no temporary object.
# Each is StoreUnusable.
BAD_SECOND_MIGRATIONS: dict[str, tuple[str, ...]] = {
    "statement fails after an earlier one succeeded": (
        _ADD_TAG,
        "CREATE TABLE note(id INTEGER PRIMARY KEY) STRICT",
        "PRAGMA user_version = 2",
    ),
    "version line names the wrong version": (_ADD_TAG, "PRAGMA user_version = 3"),
    "no version line": (_ADD_TAG,),
    "two statements in one string": (
        "ALTER TABLE note ADD COLUMN tag TEXT; CREATE INDEX note_tag ON note(tag)",
        "PRAGMA user_version = 2",
    ),
    "empty migration": (),
    "commits by itself, then fails": (
        _ADD_TAG,
        "COMMIT",
        "CREATE TABLE note(id INTEGER PRIMARY KEY) STRICT",
        "PRAGMA user_version = 2",
    ),
    "rolls back by itself": (_ADD_TAG, "ROLLBACK", "PRAGMA user_version = 2"),
    "commits after its version line": (_ADD_TAG, "PRAGMA user_version = 2", "COMMIT"),
    "ends with END": (_ADD_TAG, "PRAGMA user_version = 2", "END"),
    "begins a transaction": ("BEGIN", _ADD_TAG, "PRAGMA user_version = 2"),
    "turns the journal off": ("PRAGMA journal_mode=OFF", _ADD_TAG, "PRAGMA user_version = 2"),
    "moves the journal to memory": (
        "PRAGMA journal_mode=MEMORY",
        _ADD_TAG,
        "PRAGMA user_version = 2",
    ),
    "changes the application id": (
        "PRAGMA application_id = 7",
        _ADD_TAG,
        "PRAGMA user_version = 2",
    ),
    "turns foreign keys off": ("PRAGMA foreign_keys=OFF", _ADD_TAG, "PRAGMA user_version = 2"),
    "an empty statement": (_ADD_TAG, "", "PRAGMA user_version = 2"),
    "upper-case pragma": ("PRAGMA JOURNAL_MODE=OFF", _ADD_TAG, "PRAGMA user_version = 2"),
    "attaches another database": (
        "ATTACH DATABASE ':memory:' AS aux",
        _ADD_TAG,
        "PRAGMA user_version = 2",
    ),
    "creates a temporary table": (
        "CREATE TEMP TABLE scratch(x INTEGER)",
        _ADD_TAG,
        "PRAGMA user_version = 2",
    ),
    "creates a temporary trigger": (
        _ADD_TAG,
        "CREATE TEMP TRIGGER swallow BEFORE INSERT ON note BEGIN SELECT RAISE(IGNORE); END",
        "PRAGMA user_version = 2",
    ),
}

# Migration lists refused as bad input (StoreRefused) before anything is touched.
REFUSED_MIGRATION_LISTS: tuple[object, ...] = (
    None,
    [M1],
    (list(M1),),
    (M1, None),
    (("CREATE TABLE a(x INTEGER) STRICT", 5),),
    ((b"PRAGMA user_version = 1",),),
    "PRAGMA user_version = 1",
)

# The Ctrl-C fail-open (owner ruling for PR 1d). CPython delivers a pending KeyboardInterrupt (or another
# exception from a signal handler) inside the helper's progress handler; its sqlite3 module clears it and
# aborts the statement. Simulated by a handler that raises once while a body statement runs: what leaves,
# and what the state file then holds (literals from probe invariants3_keyboard_interrupt.py, helper row).
INTERRUPTED_ERROR = "StoreUnusable"
INTERRUPTED_MESSAGE = "write transaction: interrupted"
INTERRUPTED_ROWS: list[tuple[object, ...]] = []

# Clearing the progress handler fails (simulated, once): the authorizer is still removed, so the rollback
# runs and no transaction is left open (probe invariants3_hook_removal.py, row clear-progress).
CLEAR_PROGRESS_NOTE_PREFIX = "progress handler not removed: "
CLEAR_PROGRESS_LEFT_OPEN = False
CLEAR_PROGRESS_ROWS: list[tuple[object, ...]] = []
