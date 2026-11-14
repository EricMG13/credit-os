"""Answer key for the store's message-text rule and its SQLite error classes (2A plan).

Written by the controller from invented values before the code existed. Implementers do not edit
this file or weaken a comparison against it.
"""

# --- Text ----------------------------------------------------------------------------------

# Text given -> the text stored. A lone surrogate becomes its backslash escape; nothing is cut.
SAFE_TEXT: tuple[tuple[str, str], ...] = (
    ("plain", "plain"),
    ("", ""),
    ("café ✓ \U0001f642", "café ✓ \U0001f642"),
    ("bad \ud800 text", "bad \\ud800 text"),
    ("\udfff", "\\udfff"),
    ("\ud83d alone, then a pair \U0001f642", "\\ud83d alone, then a pair \U0001f642"),
    ("already \\ud800 escaped", "already \\ud800 escaped"),
    ("nul \x00 kept", "nul \x00 kept"),
    ("line\r\nends\n", "line\r\nends\n"),
    ("x" * 5000, "x" * 5000),
)

SAFE_TEXT_REFUSED: tuple[object, ...] = (b"bytes", 5, 1.5, True)

# --- SQLite error classes ------------------------------------------------------------------

# SQLite primary result code -> the name of the store error it becomes. Extended codes map by
# their low byte (2067 SQLITE_CONSTRAINT_UNIQUE and 1811 SQLITE_CONSTRAINT_TRIGGER are 19).
ERROR_CLASS_BY_CODE: tuple[tuple[int | None, str], ...] = (
    (5, "StoreBusy"),  # SQLITE_BUSY
    (6, "StoreBusy"),  # SQLITE_LOCKED
    (261, "StoreBusy"),  # SQLITE_BUSY_RECOVERY
    (19, "StoreConflict"),  # SQLITE_CONSTRAINT
    (2067, "StoreConflict"),  # SQLITE_CONSTRAINT_UNIQUE
    (1811, "StoreConflict"),  # SQLITE_CONSTRAINT_TRIGGER
    (275, "StoreConflict"),  # SQLITE_CONSTRAINT_CHECK
    (787, "StoreConflict"),  # SQLITE_CONSTRAINT_FOREIGNKEY
    (11, "StoreCorrupt"),  # SQLITE_CORRUPT
    (267, "StoreCorrupt"),  # SQLITE_CORRUPT_VTAB
    (26, "StoreCorrupt"),  # SQLITE_NOTADB
    (1, "StoreUnusable"),  # SQLITE_ERROR
    (8, "StoreUnusable"),  # SQLITE_READONLY
    (10, "StoreUnusable"),  # SQLITE_IOERR
    (13, "StoreUnusable"),  # SQLITE_FULL
    (14, "StoreUnusable"),  # SQLITE_CANTOPEN
    (None, "StoreUnusable"),  # raised by the sqlite3 module itself, with no result code
)

# A value bound into a statement that then fails must not appear in the store error's message
# (the message is SQLite's own text). One real failure per kind, each binding this value.
BOUND_VALUE = "zz-distinct-7731"
VALUE_FREE_FAILURES: tuple[str, ...] = ("unique", "check", "not null", "foreign key", "datatype")
