"""Answer key for opening the store (2A plan, PR 1e).

Written by the controller from invented values before the code existed. Implementers do not edit
this file or weaken a comparison against it. Migration lists come from `store_txn_key`.
"""

APPLICATION_ID = 1129467731  # 0x43524F53, the bytes "CROS"
MINIMUM_SQLITE = (3, 37, 0)
REQUIRED_THREADSAFETY = 3
DEFAULT_BUSY_SECONDS = 30.0
MAXIMUM_BUSY_SECONDS = 3600.0

# `journal_mode` is a property of the file, so a raw second connection reads it. `synchronous`
# and `foreign_keys` are per connection: read through the store's private connection.
JOURNAL_MODE = "delete"
SYNCHRONOUS_FULL = 2
FOREIGN_KEYS_ON = 1

# busy_seconds values refused (StoreRefused), nothing created.
REFUSED_BUSY_SECONDS: tuple[object, ...] = (
    0,
    0.0,
    -1,
    float("nan"),
    float("inf"),
    True,
    "30",
    None,
    3600.5,
    10**400,
)
ACCEPTED_BUSY_SECONDS: tuple[float, ...] = (0.2, 1, 30.0, 3600, 3600.0)

# user_version values of a file carrying our application id that every opener refuses
# (StoreUnusable, bytes unchanged) whatever the migration list: SQLite stores a signed 32-bit.
REFUSED_VERSIONS: tuple[int, ...] = (-1, -(2**31), 2**31 - 1)

# What each pragma is made to read back in turn, by a connection factory the test injects; each
# is StoreUnusable.
BAD_READ_BACKS: dict[str, object] = {"journal_mode": "wal", "synchronous": 1, "foreign_keys": 0}

# Accepted limit N4 (ruling R23): where the writable check cannot see a denial (simulated by a
# writable check that answers yes on a 0400 state file), the writer still opens, and its first
# write leaves as this class, the file's bytes unchanged.
UNSEEN_DENIAL_FILE_MODE = 0o400
UNSEEN_DENIAL_ERROR = "StoreUnusable"
# The SQLite result code on the first write's cause: SQLITE_READONLY (8, no extended code).
UNSEEN_DENIAL_CODE = 8
