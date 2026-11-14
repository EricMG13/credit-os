"""Answer key for where the store's file lives and what may be opened (2A plan, PR 1c).

Written by the controller from invented values before the code existed. Implementers do not edit
this file or weaken a comparison against it.
"""

STATE_FILE_NAME = "run-state.sqlite3"
FOLDER_MODE = 0o700  # the state folder and every parent the store creates
FILE_MODE = 0o600
SQLITE_HEADER_BYTES = 100

# Folder arguments refused before anything is created (StoreRefused). Texts, so the rows are the
# same on Windows and POSIX; each is passed as `Path(text)`.
REFUSED_FOLDER_TEXTS: tuple[str, ...] = (
    "\\\\server\\share\\state",
    "//server/share/state",
    "\\\\?\\C:\\state",
    "relative/state",
    "state",
    "",
)
# Appended to an absolute temporary folder: a name the file system cannot hold. StoreRefused.
REFUSED_FOLDER_NAMES: tuple[str, ...] = ("nul\x00byte", "lone\ud800surrogate")
# Not a Path at all. StoreRefused, and nothing is made under the test's tmp_path. The text forms
# are built in the test from its own `tmp_path / "state"`, never a fixed absolute path: "str" is
# str() of it, "bytes" is os.fsencode() of it. So a mutant that accepted text writes only inside
# the test's own tree.
REFUSED_FOLDER_TEXT_FORMS: tuple[str, ...] = ("str", "bytes")
REFUSED_FOLDER_VALUES: tuple[object, ...] = (None, 5)

# Contents of an existing state file that are refused before SQLite opens it, bytes unchanged.
# (bytes, name of the error class) for the writer; a reader refuses each of these too.
TOO_SHORT_FILES: tuple[bytes, ...] = (b"x", b"S", b"SQLite format 3\x00", b"\x00" * 99)
TOO_SHORT_ERROR = "StoreCorrupt"
# A 0-byte file: the writer treats it as new; a reader refuses it as not yet a store.
EMPTY_FILE_READER_ERROR = "StoreUnusable"
# Header bytes 18 and 19 (file format write and read versions): 1 is a rollback journal, 2 is
# write-ahead. A reader refuses a write-ahead file from the header, without opening it.
HEADER_VERSION_OFFSETS = (18, 19)
HEADER_ROLLBACK = 1
HEADER_WRITE_AHEAD = 2
WRITE_AHEAD_READER_ERROR = "StoreUnusable"

# A `..` that reaches a symbolic link to a folder, appended to a temporary folder that holds the
# link `alink` (to a sibling folder) and no `new`: the closing folder check refuses it, and nothing
# is made in the link's target (review Low on PR 1c, rides in PR 1d-b).
DOTDOT_LINK_PARTS: tuple[str, ...] = ("new", "..", "alink")
DOTDOT_LINK_ERROR = "StoreRefused"
